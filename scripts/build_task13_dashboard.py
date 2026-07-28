#!/usr/bin/env python3
"""Build a read-only prospective operations dashboard."""

from __future__ import annotations

import csv
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "reports/task13_dashboard.md"


def rows(relative: str) -> list[dict[str, str]]:
    with (ROOT / relative).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    runs = rows("data/processed/automation_runs.csv")
    forecasts = rows("data/processed/forward_forecasts_v1.csv")
    outcomes = rows("data/processed/forecast_outcomes_v1.csv")
    exclusions = {row["run_id"] for row in rows("data/processed/forecast_exclusions_v1.csv")}
    missed = rows("data/processed/missed_forecast_runs.csv")
    candidates = rows("data/interim/live_reset_candidates.csv")
    scheduled_runs = {
        row["run_id"] for row in forecasts
        if row["schedule_class"] == "scheduled" and row["run_id"] not in exclusions
    }
    mature_24 = [row for row in outcomes if row["forecast_id"].endswith("_24H")]
    positives = sum(int(row["label"]) for row in mature_24)
    score_lines = []
    model_tokens = {
        "M0 global": "_M0_beta11_24H",
        "Rolling 30d": "_M0_rolling30_24H",
        "M2": "_M2_logistic_C0p25_24H",
        "M3-lite": "_M3_lite_C0p25_24H",
    }
    for model, token in model_tokens.items():
        selected = [row for row in mature_24 if token in row["forecast_id"]]
        value = f"{statistics.mean(float(row['brier']) for row in selected):.6f}" if selected else "尚无"
        score_lines.append(f"| {model} | {len(selected)} | {value} |")
    last = runs[-1] if runs else {}
    OUTPUT.write_text(
        f"""# 任务 13：前瞻运行看板

## 当前状态

- 最近自动化：`{last.get('automation_run_id', '无')}` / `{last.get('status', '无')}`
- 有效 scheduled 签发：{len(scheduled_runs)} / 180
- 24h 前瞻正例：{positives} / 20
- 已成熟 24h 模型预测：{len(mature_24)}
- missed runs：{len(missed)}
- excluded runs：{len(exclusions)}
- 待审定 live candidates：{sum(row['candidate_status'] != 'accepted' for row in candidates)}

## 累计 24h Brier

| 模型 | 已评分数 | 平均 Brier |
| --- | ---: | ---: |
{chr(10).join(score_lines)}

正式比较必须同时达到 180 个有效 scheduled 日和 20 个 24h 前瞻正例。当前没有
达到停止条件，不作模型胜负判断。
""",
        encoding="utf-8",
    )
    print(f"Dashboard: scheduled={len(scheduled_runs)}, positives={positives}, missed={len(missed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
