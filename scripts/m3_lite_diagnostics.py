#!/usr/bin/env python3
"""Diagnose M3-lite errors and a post-hoc context-readiness sensitivity window."""

from __future__ import annotations

import csv
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORECASTS = ROOT / "data/processed/rolling_baseline_forecasts.csv"
CONTEXTS = ROOT / "data/processed/daily_context_features.csv"
OUTPUT = ROOT / "reports/m3_lite_diagnostics_v1.md"


def scores(rows: list[dict[str, str]], model: str) -> tuple[float, float, float]:
    probabilities = [float(row[f"p_{model}"]) for row in rows]
    labels = [int(row["label_24h"]) for row in rows]
    brier = statistics.mean((p - y) ** 2 for p, y in zip(probabilities, labels))
    log_loss = statistics.mean(
        -(y * math.log(max(p, 1e-15)) + (1 - y) * math.log(max(1 - p, 1e-15)))
        for p, y in zip(probabilities, labels)
    )
    return brier, log_loss, statistics.mean(probabilities)


def main() -> int:
    with FORECASTS.open(encoding="utf-8", newline="") as handle:
        forecasts = list(csv.DictReader(handle))
    with CONTEXTS.open(encoding="utf-8", newline="") as handle:
        contexts = {
            row["window_start_utc"]: row for row in csv.DictReader(handle)
        }

    visible = [
        row for row in forecasts
        if contexts[row["issued_at_utc"]]["official_context_visible"] == "1"
    ]
    hidden = [
        row for row in forecasts
        if contexts[row["issued_at_utc"]]["official_context_visible"] == "0"
    ]
    # Post-hoc sensitivity only: by this date the expanding history contains at
    # least 20 visible-context observations, three positives, and five negatives.
    mature = [
        row for row in forecasts if row["issued_at_utc"] >= "2026-05-24T00:00:00Z"
    ]

    rows = []
    for label, group in [
        ("全部共同窗口", forecasts),
        ("官方情境可见", visible),
        ("官方情境不可见", hidden),
        ("情境样本成熟后（敏感性）", mature),
    ]:
        for model in ("m0", "m1", "m2", "m3"):
            brier, log_loss, mean_p = scores(group, model)
            rows.append(
                f"| {label} | {model.upper()} | {len(group)} | "
                f"{sum(int(r['label_24h']) for r in group)} | "
                f"{brier:.6f} | {log_loss:.6f} | {mean_p:.3%} |"
            )

    excess = sorted(
        forecasts,
        key=lambda row: (
            (float(row["p_m3"]) - int(row["label_24h"])) ** 2
            - (float(row["p_m1"]) - int(row["label_24h"])) ** 2
        ),
        reverse=True,
    )[:5]
    error_rows = "\n".join(
        f"| {row['issued_at_utc']} | {row['label_24h']} | "
        f"{float(row['p_m1']):.3%} | {float(row['p_m3']):.3%} | "
        f"`{contexts[row['issued_at_utc']]['visible_context_ids']}` |"
        for row in excess
    )

    OUTPUT.write_text(
        """# M3-lite 诊断 v1

## 分组表现

| 窗口 | 模型 | N | 正例 | Brier | Log Loss | 平均预测概率 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
"""
        + "\n".join(rows)
        + """

“情境样本成熟后”是看过主结果后的敏感性分析，不替代 248 点主结果。即使从
2026-05-24 开始评分，M3-lite 仍未优于 M1。

## 最大额外损失

| 日期 | 标签 | M1 | M3-lite | 可见情境 |
| --- | ---: | ---: | ---: | --- |
"""
        + error_rows
        + """

## 解释

M3-lite 在早期遇到严重冷启动：第一次“官方事故可见 → 次日重置”后，事故强度、
注意力和情境年龄只有极少量非零训练样本，导致随后已解决事故窗口出现过高概率。
二元变量未做标准化，连续/有序变量只在训练窗内标准化；随着负例增加，冷启动现象
减弱，但事故变量仍未产生稳定样本外增益。

当前证据更支持：

1. 官方事故并非重置的充分条件；
2. 事故阶段和与公告的滞后需要更细粒度建模；
3. 状态历史的早期负例覆盖不完整；
4. 在补齐数据前，应保留当前得分最好的 M2 为工作基线，不发布 M3-lite 实时概率。
""",
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
