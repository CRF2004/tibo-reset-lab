#!/usr/bin/env python3
"""Snapshot and quality-audit confirmation evidence without changing labels."""

from __future__ import annotations

import csv
import hashlib
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data/raw/confirmation_evidence.csv"
SNAPSHOTS = ROOT / "data/raw/confirmation_snapshots"
OUTPUT = ROOT / "data/processed/confirmation_evidence_audit.csv"
REPORT = ROOT / "reports/task12_evidence_quality.md"


def fetch(row: dict[str, str]) -> dict[str, str]:
    path = SNAPSHOTS / f"{row['source_id']}.html"
    status, digest = "error", ""
    try:
        request = urllib.request.Request(row["url"], headers={"User-Agent": "tibo-research/1.0"})
        with urllib.request.urlopen(request, timeout=25) as response:
            body = response.read()
        path.write_bytes(body)
        status, digest = "ok", hashlib.sha256(body).hexdigest()
    except Exception as exc:
        status = f"error:{type(exc).__name__}"
    precise = row["time_precision"] in {"exact", "snowflake_exact"}
    removed = "/removed/" in row["url"]
    grade = "A" if status == "ok" and precise else "B" if status == "ok" and not removed else "C"
    return {
        "source_id": row["source_id"],
        "snapshot_status": status,
        "snapshot_path": str(path.relative_to(ROOT)) if path.exists() else "",
        "snapshot_sha256": digest,
        "time_precision": row["time_precision"],
        "reporter_identity_verified": 0,
        "removed_or_fragile_source": int(removed),
        "quality_grade": grade,
        "independence_status": "unverified_reporter_identity",
    }


def main() -> int:
    SNAPSHOTS.mkdir(parents=True, exist_ok=True)
    with INPUT.open(encoding="utf-8", newline="") as handle:
        evidence = list(csv.DictReader(handle))
    with ThreadPoolExecutor(max_workers=6) as pool:
        rows = list(pool.map(fetch, evidence))
    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    counts = {grade: sum(row["quality_grade"] == grade for row in rows) for grade in "ABC"}
    REPORT.write_text(
        f"""# 任务 12：兑现证据质量审计

共审计 {len(rows)} 条：A 级 {counts['A']}、B 级 {counts['B']}、C 级 {counts['C']}。

- A：页面快照成功且时间精确；
- B：页面快照成功，但时间只有日期或顺序精度；
- C：页面不可抓取、已删除或来源脆弱。

当前所有社区记录都缺少稳定的 reporter ID，因此 `independence_status` 统一为
`unverified_reporter_identity`。同一讨论串中的多条评论不能在正式分析中直接当作
统计独立样本。快照 SHA-256 已写入审计表；原始标签没有修改。

正式延迟分析仍只允许 A 级且精确时间的记录。B/C 级只能用于失败模式和边界案例。
""",
        encoding="utf-8",
    )
    print(f"Audited {len(rows)} evidence rows; grades={counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
