#!/usr/bin/env python3
"""Run isolated policy-level fault drills for Task 8 without issuing forecasts."""

from __future__ import annotations

import csv
import json
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from task8_daily_run import feed_gate

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "reports/task11_fault_drill.md"


def main() -> int:
    now = datetime.now(timezone.utc)
    known = {"123"}
    base = {
        "fetched_at": now.isoformat().replace("+00:00", "Z"),
        "stale": False,
        "signal": {"tweet_id": "123"},
    }
    drills = []
    cases = [
        ("fresh_known_signal", base, True, "passed"),
        ("stale_flag", {**base, "stale": True}, False, "feed_stale"),
        ("old_feed", {**base, "fetched_at": (now - timedelta(minutes=31)).isoformat().replace("+00:00", "Z")}, False, "feed_stale"),
        ("missing_signal", {**base, "signal": {}}, False, "feed_missing_signal"),
        ("unknown_signal", {**base, "signal": {"tweet_id": "999"}}, False, "unreviewed_signal:999"),
    ]
    for name, feed, expected_pass, expected_reason in cases:
        passed, reason = feed_gate(feed, now, known)
        ok = passed == expected_pass and reason == expected_reason
        drills.append((name, ok, reason))

    # Isolated append-only revision replay: original bytes must remain unchanged.
    with tempfile.TemporaryDirectory(prefix="tibo-fault-drill-") as temp:
        original = Path(temp) / "outcomes.csv"
        revisions = Path(temp) / "revisions.csv"
        original.write_text("forecast_id,label,brier\nF1,0,0.04000000\n", encoding="utf-8")
        before = original.read_bytes()
        revisions.write_text(
            "revision_id,forecast_id,old_label,new_label,reason\n"
            "R1,F1,0,1,late_discovered_event\n",
            encoding="utf-8",
        )
        drills.append(("revision_does_not_overwrite_original", original.read_bytes() == before, "append_only"))

    duplicate = subprocess.run(
        [
            "python3", "scripts/issue_task7_forecast.py",
            "--issued-at", "2026-07-28T07:42:56Z", "--schedule-class", "bootstrap",
        ],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    drills.append(("duplicate_lock_rejected", duplicate.returncode != 0, duplicate.stdout.strip()))
    off_schedule = subprocess.run(
        [
            "python3", "scripts/issue_task7_forecast.py",
            "--issued-at", "2026-07-28T17:01:00Z", "--schedule-class", "scheduled",
        ],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    drills.append(("off_schedule_rejected", off_schedule.returncode != 0, off_schedule.stdout.strip()))

    rows = "\n".join(
        f"| {name} | {'PASS' if passed else 'FAIL'} | `{detail}` |"
        for name, passed, detail in drills
    )
    OUTPUT.write_text(
        f"""# 任务 11：自动化故障演练

执行时间：{now.isoformat().replace("+00:00", "Z")}。

| 场景 | 结果 | 系统响应 |
| --- | --- | --- |
{rows}

演练在临时目录或既有不可覆盖锁上进行，没有创建 scheduled 预测，也没有修改任何
冻结概率。总计 {len(drills)} 项，通过 {sum(item[1] for item in drills)} 项。

尚不能在无人值守测试中安全模拟的外部条件是 Windows 完全退出登录和网络长期中断；
生产策略是在这种情况下由计划任务结果或 missed-run 审计暴露缺口。
""",
        encoding="utf-8",
    )
    print(json.dumps({"drills": len(drills), "passed": sum(x[1] for x in drills)}))
    return int(not all(item[1] for item in drills))


if __name__ == "__main__":
    raise SystemExit(main())
