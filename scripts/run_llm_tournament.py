#!/usr/bin/env python3
"""Call five diverse LLMs on one frozen public evidence packet.

The API credential is read from the ignored local .env file. It is never written
to prompts, responses, locks, logs, or CSV output.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
API_URL = "https://www.dmxapi.cn/v1/chat/completions"
ANN = ROOT / "data/processed/reset_announcements.csv"
CTX = ROOT / "data/processed/context_events.csv"
ROUNDS = ROOT / "data/processed/tournament_rounds.csv"
FORECASTS = ROOT / "data/processed/tournament_forecasts.csv"
RUN_DIR = ROOT / "community/llm_runs"

MODELS = {
    "P_LLM_DEEPSEEK_V4": "deepseek-v4-pro",
    "P_LLM_QWEN35_397B": "qwen3.5-397b-a17b",
    "P_LLM_KIMI_K25": "kimi-k2.5",
    "P_LLM_STEP35": "step-3.5-flash",
    "P_LLM_MINIMAX_M27": "MiniMax-M2.7",
}


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def stamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def load_env() -> None:
    path = ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def evidence_packet(cutoff: datetime) -> tuple[str, list[str], str]:
    with ANN.open(encoding="utf-8", newline="") as handle:
        announcements = [
            row for row in csv.DictReader(handle)
            if row["adjudication_status"] == "accepted"
            and dt(row["announced_at_utc"]) <= cutoff
        ]
    with CTX.open(encoding="utf-8", newline="") as handle:
        contexts = [
            row for row in csv.DictReader(handle)
            if row["prediction_eligible"] == "1"
            and dt(row["first_public_at_utc"]) <= cutoff
        ]
    recent_ann = sorted(announcements, key=lambda row: row["announced_at_utc"])[-12:]
    recent_ctx = sorted(contexts, key=lambda row: row["first_public_at_utc"])[-12:]
    ids = [row["announcement_id"] for row in recent_ann]
    ids += [row["context_event_id"] for row in recent_ctx]
    packet = {
        "evidence_cutoff_utc": stamp(cutoff),
        "historical_accepted_announcement_count": len(announcements),
        "recent_announcements": [{
            "id": row["announcement_id"],
            "at": row["announced_at_utc"],
            "status": row["announcement_status"],
            "reset_type": row["reset_type"],
            "reason_type": row["reason_type"],
            "policy_regime": row["policy_regime"],
        } for row in recent_ann],
        "recent_prediction_eligible_contexts": [{
            "id": row["context_event_id"],
            "first_public_at": row["first_public_at_utc"],
            "resolved_at": row["resolved_at_utc"],
            "event_type": row["event_type"],
            "incident_stage": row["incident_stage"],
            "milestone": row["milestone_label"],
            "launch": row["launch_label"],
            "strength_0_9": row["event_strength_0_9"],
            "attention_0_5": row["attention_state_0_5"],
            "official_incident": row["official_incident"],
        } for row in recent_ctx],
    }
    canonical = json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return json.dumps(packet, ensure_ascii=False, indent=2), ids, hashlib.sha256(canonical.encode()).hexdigest()


def prompt(packet: str) -> str:
    return f"""你是一个参加概率预测竞赛的独立预测者。预测目标是：
从轮次 issued_at 开始，未来24小时/168小时内，Tibo Sottiaux 或 OpenAI 官方账号是否
至少发布一条符合研究协议的 Codex/ChatGPT Work 特殊额度 reset 公告。

规则：
1. 只能使用下方冻结证据，不得联网，不得假设私有信息，不推断个人心理。
2. 区分特殊全局 reset、banked credit 与账户正常5小时/每周周期刷新。
3. 概率范围0.001到0.999，且p_168h不得低于p_24h。
4. 基准率很重要；不要因为单一相关信号给出极端概率。
5. 只输出一个JSON对象，不要Markdown：
{{"p_24h":0.12,"p_168h":0.55,"rationale_zh":"2-4句中文理由",
"supporting_evidence_ids":["..."],"counter_evidence":"一句中文反向证据",
"confidence":"low|medium|high"}}

冻结证据：
{packet}
"""


def parse_response(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise ValueError("response contains no JSON object")
    data = json.loads(match.group(0))
    p24, p168 = float(data["p_24h"]), float(data["p_168h"])
    if not 0.001 <= p24 <= 0.999 or not 0.001 <= p168 <= 0.999:
        raise ValueError("probability outside [0.001, 0.999]")
    if p168 < p24:
        raise ValueError("p_168h must be >= p_24h")
    data["p_24h"], data["p_168h"] = p24, p168
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--round-id", required=True)
    parser.add_argument("--cutoff-at", help="Defaults to current UTC time")
    parser.add_argument(
        "--predictor-id", action="append", choices=list(MODELS),
        help="Run only selected predictor(s); repeat flag as needed.",
    )
    args = parser.parse_args()
    load_env()
    api_key = os.environ.get("dmx_api_key") or os.environ.get("DMX_API_KEY")
    if not api_key:
        raise SystemExit("Missing dmx_api_key/DMX_API_KEY in ignored .env")
    with ROUNDS.open(encoding="utf-8", newline="") as handle:
        rounds = {row["round_id"]: row for row in csv.DictReader(handle)}
    if args.round_id not in rounds:
        raise SystemExit("Unknown round")
    cutoff = dt(args.cutoff_at) if args.cutoff_at else datetime.now(timezone.utc)
    if cutoff > dt(rounds[args.round_id]["submission_deadline_utc"]):
        raise SystemExit("LLM run would occur after the round deadline")
    packet, evidence_ids, packet_sha = evidence_packet(cutoff)
    model_prompt = prompt(packet)
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    with FORECASTS.open(encoding="utf-8", newline="") as handle:
        existing_pairs = {
            (row["round_id"], row["predictor_id"], row["horizon_hours"])
            for row in csv.DictReader(handle)
        }
    failures = []
    selected = set(args.predictor_id or MODELS)
    for predictor_id, model in MODELS.items():
        if predictor_id not in selected:
            continue
        if all(
            (args.round_id, predictor_id, str(horizon)) in existing_pairs
            for horizon in (24, 168)
        ):
            print(f"{model}: already locked; skipped")
            continue
        try:
            response = requests.post(
                API_URL,
                headers={
                    "Accept": "application/json",
                    "Authorization": api_key,
                    "User-Agent": "TiboResetLab/1.0",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "temperature": 0,
                    "messages": [
                        {"role": "system", "content": "Follow the forecasting protocol exactly."},
                        {"role": "user", "content": model_prompt},
                    ],
                },
                timeout=120,
            )
            response.raise_for_status()
            envelope = response.json()
            raw_text = envelope["choices"][0]["message"]["content"]
            parsed = parse_response(raw_text)
            completed = datetime.now(timezone.utc)
            if completed > dt(rounds[args.round_id]["submission_deadline_utc"]):
                raise ValueError("model response arrived after the round deadline")
            run_record = {
                "round_id": args.round_id,
                "predictor_id": predictor_id,
                "provider_model": model,
                "called_at_utc": stamp(cutoff),
                "completed_at_utc": stamp(completed),
                "evidence_packet_sha256": packet_sha,
                "raw_response_sha256": hashlib.sha256(raw_text.encode()).hexdigest(),
                "parsed_response": parsed,
            }
            path = RUN_DIR / f"{args.round_id}_{predictor_id}.json"
            path.write_text(json.dumps(run_record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            rationale = (
                parsed["rationale_zh"] + " 反向证据：" + str(parsed.get("counter_evidence", "未提供"))
            )
            used_ids = parsed.get("supporting_evidence_ids") or evidence_ids
            for horizon, probability in ((24, parsed["p_24h"]), (168, parsed["p_168h"])):
                command = [
                    sys.executable, str(ROOT / "scripts/submit_tournament_forecast.py"),
                    "--round-id", args.round_id,
                    "--predictor-id", predictor_id,
                    "--participant-id", model,
                    "--horizon-hours", str(horizon),
                    "--probability", str(probability),
                    "--submitted-at", stamp(completed),
                    "--evidence-cutoff", stamp(cutoff),
                    "--evidence-ids", ";".join(used_ids),
                    "--rationale", rationale,
                ]
                subprocess.run(command, cwd=ROOT, check=True)
            print(f"{model}: p24={parsed['p_24h']:.3f}, p168={parsed['p_168h']:.3f}")
        except Exception as exc:
            failures.append(f"{model}: {type(exc).__name__}: {exc}")
            print(f"FAILED {failures[-1]}", file=sys.stderr)
    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
