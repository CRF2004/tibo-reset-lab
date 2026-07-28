#!/usr/bin/env python3
"""Paired Brier block-bootstrap sensitivity for daily and six-hour forecasts."""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DAILY = ROOT / "data/processed/strong_daily_baseline_forecasts.csv"
SIX = ROOT / "data/processed/rolling_6h_forecasts.csv"
REPORT = ROOT / "reports/bootstrap_sensitivity_v1.md"


def read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def ci(rows, challenger, baseline, block_rows, seed):
    rng = np.random.default_rng(seed)
    blocks = [rows[i:i + block_rows] for i in range(0, len(rows), block_rows)]
    stats = []
    for _ in range(4000):
        sample = [r for j in rng.integers(0, len(blocks), len(blocks)) for r in blocks[j]]
        stats.append(np.mean([
            (float(r[challenger]) - int(r["label_24h" if "label_24h" in r else "label_6h"])) ** 2
            - (float(r[baseline]) - int(r["label_24h" if "label_24h" in r else "label_6h"])) ** 2
            for r in sample
        ]))
    return np.quantile(stats, [0.025, 0.975])


def main() -> int:
    daily, six = read(DAILY), read(SIX)
    lines = []
    for days in (7, 14, 21):
        for scale, rows, challenger, baseline, multiplier in [
            ("daily M2-global", daily, "p_m2", "p_global", 1),
            ("daily M2-rolling60", daily, "p_m2", "p_rolling60", 1),
            ("6h M2-M0", six, "p_m2", "p_m0", 4),
            ("6h M3-M2", six, "p_m3", "p_m2", 4),
        ]:
            low, high = ci(rows, challenger, baseline, days * multiplier, 20260728 + days)
            lines.append(f"| {scale} | {days} | {low:.6f} | {high:.6f} |")
    REPORT.write_text(
        """# Block bootstrap 敏感性

负值代表前一个模型 Brier 更低。每种设置 4000 次 paired percentile bootstrap。

| 比较 | block 天数 | 2.5% | 97.5% |
| --- | ---: | ---: | ---: |
""" + "\n".join(lines) + """

7、14、21 天区块共同用于检查连续重置聚集、168 小时窗口重叠和较长产品事件相关性。
单条约 315 日序列下区间仍可能不稳定；这些区间是敏感性分析，不是独立重复实验。
""",
        encoding="utf-8",
    )
    print("Wrote 7/14/21-day block sensitivity")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
