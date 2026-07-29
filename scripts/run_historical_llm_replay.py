#!/usr/bin/env python3
"""Replay LLM forecasters on historical 17:00 UTC evidence packets.

This writes to a separate replay table and never mutates the prospective
tournament ledger.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from event_units import accepted_event_times
from run_llm_tournament import MODELS, API_URL, evidence_packet, load_env, parse_response, prompt

ROOT = Path(__file__).resolve().parents[1]
PERIODS = ROOT / "data/processed/person_period_daily.csv"
ANN = ROOT / "data/processed/reset_announcements.csv"
ACTIONS = ROOT / "data/processed/reset_actions.csv"
OVERRIDES = ROOT / "data/processed/announcement_cluster_overrides.csv"
OUTPUT = ROOT / "data/processed/historical_replay_forecasts.csv"


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def stamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def label_for(events: list[datetime], start: datetime, horizon: int) -> tuple[int, int]:
    end = start + timedelta(hours=horizon)
    observed = [event for event in events if start < event <= end]
    return int(bool(observed)), len(observed)


def loss(probability: float, label: int) -> tuple[float, float]:
    p = min(max(probability, 1e-15), 1 - 1e-15)
    return (p - label) ** 2, -(label * math.log(p) + (1 - label) * math.log(1 - p))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-points", type=int, default=12)
    parser.add_argument("--stride", type=int, default=7)
    parser.add_argument("--timeout-seconds", type=int, default=45)
    parser.add_argument("--predictor-id", action="append", choices=list(MODELS))
    parser.add_argument("--start-at", help="Earliest issued_at_utc to replay")
    parser.add_argument("--end-at", help="Latest issued_at_utc to replay")
    args = parser.parse_args()

    load_env()
    api_key = os.environ.get("dmx_api_key") or os.environ.get("DMX_API_KEY")
    if not api_key:
        raise SystemExit("Missing dmx_api_key/DMX_API_KEY in ignored .env")

    periods = [row for row in read_csv(PERIODS) if row["days_since_last_announcement"]]
    if args.start_at:
        periods = [row for row in periods if row["window_start_utc"] >= args.start_at]
    if args.end_at:
        periods = [row for row in periods if row["window_start_utc"] <= args.end_at]
    selected_periods = periods[:: args.stride][-args.max_points :]

    existing = {row["replay_forecast_id"] for row in read_csv(OUTPUT)}
    events = accepted_event_times(
        read_csv(ANN), read_csv(ACTIONS), read_csv(OVERRIDES), "cluster_first"
    )
    selected_models = {
        predictor_id: MODELS[predictor_id]
        for predictor_id in (args.predictor_id or list(MODELS))
    }
    fieldnames = [
        "replay_forecast_id", "predictor_id", "participant_id", "issued_at_utc",
        "horizon_hours", "window_end_utc", "probability", "label",
        "event_count", "brier", "log_loss", "evidence_cutoff_utc",
        "evidence_ids", "rationale", "replay_method", "payload_sha256",
    ]
    for period in selected_periods:
        issued = dt(period["window_start_utc"])
        packet, evidence_ids, packet_sha = evidence_packet(issued)
        model_prompt = prompt(packet)
        for predictor_id, model in selected_models.items():
            replay_base_id = (
                "REPLAY_"
                + period["window_start_utc"].replace("-", "").replace(":", "")
                + "_"
                + predictor_id
            )
            if all(f"{replay_base_id}_{horizon}H" in existing for horizon in (24, 168)):
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
                            {"role": "system", "content": "Follow the historical replay protocol exactly."},
                            {"role": "user", "content": model_prompt},
                        ],
                    },
                    timeout=args.timeout_seconds,
                )
                response.raise_for_status()
                raw_text = response.json()["choices"][0]["message"]["content"]
                parsed = parse_response(raw_text)
            except Exception as exc:
                print(f"WARNING {period['window_start_utc']} {model}: {type(exc).__name__}: {exc}")
                continue
            rationale = (
                str(parsed.get("rationale_zh", ""))
                + " 反向证据："
                + str(parsed.get("counter_evidence", "未提供"))
            )
            used_ids = parsed.get("supporting_evidence_ids") or evidence_ids
            rows = []
            for horizon, probability in ((24, parsed["p_24h"]), (168, parsed["p_168h"])):
                label, event_count = label_for(events, issued, horizon)
                brier, log_loss = loss(probability, label)
                payload = {
                    "replay_forecast_id": f"{replay_base_id}_{horizon}H",
                    "predictor_id": predictor_id,
                    "participant_id": model,
                    "issued_at_utc": stamp(issued),
                    "horizon_hours": str(horizon),
                    "window_end_utc": stamp(issued + timedelta(hours=horizon)),
                    "probability": f"{probability:.8f}",
                    "label": str(label),
                    "event_count": str(event_count),
                    "brier": f"{brier:.8f}",
                    "log_loss": f"{log_loss:.8f}",
                    "evidence_cutoff_utc": stamp(issued),
                    "evidence_ids": ";".join(used_ids),
                    "rationale": rationale,
                    "replay_method": "current_context_builder_llm_replay_v1",
                }
                canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                payload["payload_sha256"] = hashlib.sha256(
                    (packet_sha + canonical).encode()
                ).hexdigest()
                if payload["replay_forecast_id"] not in existing:
                    rows.append(payload)
                    existing.add(payload["replay_forecast_id"])
            if rows:
                with OUTPUT.open("a", encoding="utf-8", newline="") as handle:
                    csv.DictWriter(handle, fieldnames=fieldnames).writerows(rows)
            print(f"{period['window_start_utc']} {model}: p24={parsed['p_24h']:.3f} p168={parsed['p_168h']:.3f}")
    print("Historical LLM replay complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
