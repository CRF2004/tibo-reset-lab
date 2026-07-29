#!/usr/bin/env python3
"""Replace only the generated live snapshot block in README.md."""

from __future__ import annotations

import csv
import math
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
DATA = ROOT / "data/processed"
START = "<!-- LIVE_SNAPSHOT_START -->"
END = "<!-- LIVE_SNAPSHOT_END -->"


def read(name: str) -> list[dict[str, str]]:
    with (DATA / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def pct(value: str | None) -> str:
    return "—" if value is None else f"{float(value):.1%}"


def score_rows(rows: list[dict[str, str]], field: str) -> tuple[int, float, float, float]:
    scored = [
        (int(row["label_24h"]), min(max(float(row[field]), 1e-15), 1 - 1e-15))
        for row in rows
    ]
    n = len(scored)
    brier = sum((p - y) ** 2 for y, p in scored) / n
    log_loss = -sum(y * math.log(p) + (1 - y) * math.log(1 - p) for y, p in scored) / n
    return n, brier, log_loss, sum(y for y, _ in scored) / n


def score_probability_rows(rows: list[dict[str, str]]) -> tuple[int, float, float, float]:
    scored = [
        (int(row["label"]), min(max(float(row["probability"]), 1e-15), 1 - 1e-15))
        for row in rows
    ]
    n = len(scored)
    brier = sum((p - y) ** 2 for y, p in scored) / n
    log_loss = -sum(y * math.log(p) + (1 - y) * math.log(1 - p) for y, p in scored) / n
    return n, brier, log_loss, sum(y for y, _ in scored) / n


def main() -> int:
    predictors = {row["predictor_id"]: row for row in read("tournament_predictors.csv")}
    forecasts = [
        row for row in read("tournament_forecasts.csv")
        if row["eligibility_status"] == "eligible"
    ]
    announcements = [
        row for row in read("reset_announcements.csv")
        if row["adjudication_status"] == "accepted"
    ]
    scores = read("tournament_scores.csv")
    historical = read("strong_daily_baseline_forecasts.csv")
    replay = read("historical_replay_forecasts.csv")
    scheduled = [row for row in forecasts if row["schedule_class"] == "scheduled"]
    if scheduled:
        issue = max(row["issued_at_utc"] for row in scheduled)
        selected = [row for row in scheduled if row["issued_at_utc"] == issue]
        mode = "正式 scheduled 轮次"
        warning = ""
    else:
        latest: dict[tuple[str, str], dict[str, str]] = {}
        for row in forecasts:
            key = (row["predictor_id"], row["horizon_hours"])
            if key not in latest or row["issued_at_utc"] > latest[key]["issued_at_utc"]:
                latest[key] = row
        selected = list(latest.values())
        issue = max((row["issued_at_utc"] for row in selected), default="")
        mode = "Bootstrap 演示"
        warning = (
            "> **注意：** 尚无正式 scheduled 轮次。下表来自不同时间的 bootstrap，"
            "只展示系统如何工作，不能用于比较高低，也不进入排行榜。\n"
        )
    by_predictor: dict[str, dict[str, dict[str, str]]] = {}
    for row in selected:
        by_predictor.setdefault(row["predictor_id"], {})[row["horizon_hours"]] = row
    display_order = [
        "P_GLOBAL", "P_RECENT30", "P_RENEWAL", "P_CALENDAR", "P_THEORY",
        "P_LLM_DEEPSEEK_V4", "P_LLM_QWEN35_397B", "P_LLM_KIMI_K25",
        "P_LLM_MINIMAX_M27", "P_LLM_STEP35", "P_PLAYER", "P_CROWD",
    ]
    table_rows = []
    for predictor_id in display_order:
        horizons = by_predictor.get(predictor_id)
        if not horizons:
            continue
        cutoff = max(row["evidence_cutoff_utc"] for row in horizons.values())
        table_rows.append(
            f"| {predictors[predictor_id]['display_name']} | "
            f"{pct(horizons.get('24', {}).get('probability'))} | "
            f"{pct(horizons.get('168', {}).get('probability'))} | {cutoff} |"
        )
    latest_ann = max(announcements, key=lambda row: row["announced_at_utc"])
    post_id = latest_ann["announcement_id"].removeprefix("ANN_X_")
    latest_url = f"https://x.com/thsottiaux/status/{post_id}"
    latest_at = dt(latest_ann["announced_at_utc"])
    data_at = max(
        (row["submitted_at_utc"] for row in selected),
        default=datetime.now(timezone.utc).isoformat(),
    )
    historical_fields = [
        ("p_ewma_hl30", "EWMA half-life 30d"),
        ("p_rolling30", "Recent 30-day rate"),
        ("p_rolling60", "Recent 60-day rate"),
        ("p_regime_rate", "Two-regime rate"),
        ("p_m2", "Calendar model"),
        ("p_m2_no_regime", "Calendar model without regime"),
        ("p_global", "Global event rate"),
        ("p_same_gap30", "Same-gap nearest 30"),
        ("p_km_renewal", "Discrete renewal hazard"),
    ]
    historical_scores = [
        (name, "full", *score_rows(historical, field))
        for field, name in historical_fields
    ]
    replay_display = {
        "P_LLM_DEEPSEEK_V4": "DeepSeek V4 Pro",
        "P_LLM_QWEN35_397B": "Qwen 3.5 397B",
        "P_LLM_KIMI_K25": "Kimi K2.5",
        "P_LLM_MINIMAX_M27": "MiniMax M2.7",
        "P_LLM_STEP35": "Step 3.5 Flash",
        "P_PLAYER": "Independent player",
        "P_CROWD": "Crowd aggregate",
    }
    replay_status = []
    for predictor_id, name in replay_display.items():
        rows = [
            row for row in replay
            if row["predictor_id"] == predictor_id and row["horizon_hours"] == "24"
        ]
        if rows:
            historical_scores.append((name, "limited", *score_probability_rows(rows)))
        else:
            replay_status.append(name)
    historical_scores.sort(key=lambda row: (-row[2], row[3]))
    baseline_brier = next(row[3] for row in historical_scores if row[0] == "Global event rate")
    leaderboard = "\n".join(
        f"| {rank} | {name} | {coverage} | {n} | {brier:.6f} | {log_loss:.6f} | "
        f"{(1 - brier / baseline_brier):.1%} |"
        for rank, (name, coverage, n, brier, log_loss, _prevalence) in enumerate(
            historical_scores, start=1
        )
    )
    historical_prevalence = score_rows(historical, "p_global")[3] if historical else 0
    mature_scheduled = {
        row["tournament_forecast_id"] for row in scores
        if any(
            forecast["tournament_forecast_id"] == row["tournament_forecast_id"]
            and forecast["schedule_class"] == "scheduled"
            for forecast in forecasts
        )
    }
    block = f"""{START}
## 当前预测快照

**状态：{mode}** · 数据更新至 `{data_at}` · 正式成熟预测 `{len(mature_scheduled)}` 条

{warning}
| 预测者 | 未来24小时 | 未来7天 | 证据截止（UTC） |
| --- | ---: | ---: | --- |
{chr(10).join(table_rows) if table_rows else "| 暂无有效预测 | — | — | — |"}

### 当前已知事实

- 最近一次合格公告：[原始 X 帖]({latest_url})，时间 `{latest_ann['announced_at_utc']}`；
- 类型：`{latest_ann['reset_type']}`；原因：`{latest_ann['reason_type']}`；
- 距该公告约 `{max(0, (dt(data_at) - latest_at).total_seconds() / 3600):.1f}` 小时；
- [查看中文理由、证据与完整 Dashboard](reports/community_dashboard.md)。

概率不是官方消息，也不是“重置倒计时”。Bootstrap、迟交和未成熟结果不进入正式排名。

### 统计预测者历史演练排行榜

口径：v1.2 `cluster_first`，每日 17:00 UTC landmark，24小时窗口；每个预测点只用此前数据。
统计模型使用严格 expanding-window；LLM replay 使用当前冻结上下文构建器在历史 cutoff 回放。
玩家和 Crowd 只有存在独立历史 replay 提交时才计分。

| 排名 | 预测者 | 覆盖 | N | Brier | Log Loss | Skill vs global |
| ---: | --- | --- | ---: | ---: | ---: | ---: |
{leaderboard}

共同窗口 `{historical[0]['issued_at_utc']}` 至 `{historical[-1]['issued_at_utc']}`；
正例率 `{historical_prevalence:.1%}`。这是模型开发期历史演练，不替代未来 scheduled 排行榜。
暂无可评分 replay：{", ".join(replay_status) if replay_status else "无"}。
{END}"""
    text = README.read_text(encoding="utf-8")
    if START not in text or END not in text:
        raise SystemExit("README live snapshot markers are missing")
    before, rest = text.split(START, 1)
    _, after = rest.split(END, 1)
    README.write_text(before + block + after, encoding="utf-8")
    print(f"Updated README snapshot from {len(selected)} forecasts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
