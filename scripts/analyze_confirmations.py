#!/usr/bin/env python3
"""Summarize announcement-to-application confirmations without false precision."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANN = ROOT / "data/processed/reset_announcements.csv"
CONF = ROOT / "data/processed/reset_confirmations.csv"
RAW = ROOT / "data/raw/confirmation_evidence.csv"
REPORT = ROOT / "reports/reset_application_v0.1.md"


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def main() -> int:
    with ANN.open(encoding="utf-8", newline="") as handle:
        announcements = {row["announcement_id"]: row for row in csv.DictReader(handle)}
    with CONF.open(encoding="utf-8", newline="") as handle:
        confirmations = list(csv.DictReader(handle))
    with RAW.open(encoding="utf-8", newline="") as handle:
        evidence = {row["source_id"]: row for row in csv.DictReader(handle)}

    exact_delays = []
    detail = []
    for row in confirmations:
        source = evidence[row["source_id"]]
        ann = announcements[row["announcement_id"]]
        delay = (dt(row["confirmed_at_utc"]) - dt(ann["announced_at_utc"])).total_seconds() / 60
        exact = source["time_precision"] in {"exact", "snowflake_exact"}
        if exact:
            exact_delays.append(delay)
        detail.append(
            f"| {row['confirmation_id']} | {row['applied_successfully']} | "
            f"{row['which_window_changed']} | "
            f"{delay:.1f}{'' if exact else '（近似，不进入延迟统计）'} | "
            f"[证据]({source['url']}) |"
        )

    successes = sum(row["applied_successfully"] == "1" for row in confirmations)
    failures = len(confirmations) - successes
    mismatch_tokens = ("instead", "shifted", "overwrote", "did_not_stack")
    mismatches = sum(
        row["applied_successfully"] == "1"
        and any(token in row["which_window_changed"] for token in mismatch_tokens)
        for row in confirmations
    )
    clean_or_unspecified = successes - mismatches
    exact_text = (
        f"{exact_delays[0]:.1f} 分钟" if len(exact_delays) == 1
        else f"{len(exact_delays)} 个精确观测"
    )
    REPORT.write_text(
        f"""# 重置宣布到实际应用：初步兑现审计 v0.1

数据截止：2026-07-28。当前有 {len(confirmations)} 条公开个案报告：
{clean_or_unspecified} 条报告到账且未明确报告机制错误，{mismatches} 条到账但报告窗口
或 hard/banked 机制不符，{failures} 条报告未成功。

唯一具有精确发布时刻、可计算延迟的到账报告发生在宣布后 {exact_text}。GitHub
只显示开帖日期的记录统一以当日 12:00 UTC 占位，其延迟不得进入均值、中位数或
生存分析。

| confirmation_id | 成功 | 观察到的变化 | 宣布后分钟 | 原始证据 |
| --- | ---: | --- | ---: | --- |
{chr(10).join(detail)}

## 判读

- `applied_successfully=1` 仅表示该报告者观察到了某种额度变化，不代表所有账户到账。
- `hard_instead_of_banked` 是“发生了变化但机制与预期不一致”，不能与完全成功合并。
- `0` 包括额度未恢复、只有计时器变化以及明确遗漏的账户。
- 这些是自选择的公开报告，不能估计总体失败率；其作用是识别兑现延迟和失败模式。
- 原文及中文翻译保存在 `data/raw/confirmation_evidence.csv`。
""",
        encoding="utf-8",
    )
    print(f"Wrote confirmation audit: {len(confirmations)} reports")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
