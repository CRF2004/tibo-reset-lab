#!/usr/bin/env python3
"""Generate a compact descriptive report from gold announcement/action tables."""

from __future__ import annotations

import csv
import statistics
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANNOUNCEMENTS = ROOT / "data/processed/reset_announcements.csv"
ACTIONS = ROOT / "data/processed/reset_actions.csv"
PERIODS = ROOT / "data/processed/person_period_daily.csv"
FORECASTS = ROOT / "data/processed/m0_forecasts.csv"
OUTPUT = ROOT / "reports/descriptive_baseline_v1.md"


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def table(counter: Counter[str]) -> str:
    rows = ["| 类别 | 数量 |", "| --- | ---: |"]
    rows.extend(f"| `{key}` | {value} |" for key, value in sorted(counter.items()))
    return "\n".join(rows)


def main() -> int:
    with ANNOUNCEMENTS.open(encoding="utf-8", newline="") as handle:
        announcements = list(csv.DictReader(handle))
    with ACTIONS.open(encoding="utf-8", newline="") as handle:
        actions = list(csv.DictReader(handle))
    with PERIODS.open(encoding="utf-8", newline="") as handle:
        periods = list(csv.DictReader(handle))
    with FORECASTS.open(encoding="utf-8", newline="") as handle:
        forecasts = list(csv.DictReader(handle))[1:]

    event_times = sorted(dt(row["announced_at_utc"]) for row in announcements)
    gaps = [
        (right - left).total_seconds() / 86400
        for left, right in zip(event_times, event_times[1:])
    ]
    labels = [int(row["label_24h"]) for row in forecasts]
    probabilities = [float(row["p_24h"]) for row in forecasts]
    brier = statistics.mean((p - y) ** 2 for p, y in zip(probabilities, labels))

    month_counts = Counter(value.strftime("%Y-%m") for value in event_times)
    status_counts = Counter(row["announcement_status"] for row in announcements)
    reason_counts = Counter(row["reason_type"] for row in announcements)
    action_counts = Counter(row["action_type"] for row in actions)
    regime_counts = Counter(row["policy_regime"] for row in announcements)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        f"""# 描述统计与 M0 基线 v1

数据版本：`gold_v1`  
观察期：2025-09-17 00:00 UTC 至 2026-07-29 00:00 UTC

## 样本规模

- 严格公告帖子：{len(announcements)}
- 唯一 reset 动作：{len(actions)}
- 日级时间片：{len(periods)}
- 含公告的日级时间片：{sum(int(row['announcement_in_next_window']) for row in periods)}
- 事件日占比：{sum(int(row['announcement_in_next_window']) for row in periods) / len(periods):.3%}

## 公告间隔

- 间隔数量：{len(gaps)}
- 平均间隔：{statistics.mean(gaps):.2f} 天
- 中位间隔：{statistics.median(gaps):.2f} 天
- 最短间隔：{min(gaps):.2f} 天
- 最长间隔：{max(gaps):.2f} 天

短间隔与长沉寂并存，说明固定历史率只能作为最低基线，M1 应显式建模
`time_since_last_announcement`。

## 按月份

{table(month_counts)}

## 公告状态

{table(status_counts)}

## 原因类型

{table(reason_counts)}

## 去重动作类型

{table(action_counts)}

## 制度时期

{table(regime_counts)}

## M0 expanding-window 基线

- 评分预测点：{len(forecasts)}
- 24h Brier Score：{brier:.6f}
- 模型：历史日事件率，使用 Beta(1,1) 平滑
- 7d 概率：由当前日 hazard 按常数情景聚合，仅作为基线

M0 不能利用等待时间、日历节律、事故或里程碑，因此后续模型必须在完全相同预测点
上比较，不能改变样本窗口。

## 下一步判定

1. 实现 M1 renewal：仅使用距上次公告时间；
2. 实现 M2 calendar：M1 加星期、PT 时段和月份/制度控制；
3. 使用 expanding-window 滚动预测；
4. 同时报告相对 M0 的 Brier Skill Score；
5. 在 M1/M2 稳定前不拟合 M3 理论模型。
""",
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

