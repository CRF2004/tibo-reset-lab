#!/usr/bin/env python3
"""Build a leakage-conscious daily person-period table from accepted announcements."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data/processed/reset_announcements.csv"
OUTPUT = ROOT / "data/processed/person_period_daily.csv"


def utc(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() != timedelta(0):
        raise ValueError(f"Expected UTC timestamp, got {value!r}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True, type=utc)
    parser.add_argument("--end", required=True, type=utc)
    args = parser.parse_args()
    if args.start >= args.end:
        parser.error("--start must be before --end")

    with INPUT.open(encoding="utf-8", newline="") as handle:
        announcements = [
            utc(row["announced_at_utc"])
            for row in csv.DictReader(handle)
            if row["adjudication_status"] == "accepted"
        ]
    announcements.sort()

    rows = []
    cursor = args.start
    last_event: datetime | None = None
    while cursor < args.end:
        window_end = min(cursor + timedelta(days=1), args.end)
        events = [event for event in announcements if cursor < event <= window_end]
        days_since = (
            "" if last_event is None else f"{(cursor - last_event).total_seconds() / 86400:.6f}"
        )
        rows.append({
            "window_start_utc": cursor.isoformat().replace("+00:00", "Z"),
            "window_end_utc": window_end.isoformat().replace("+00:00", "Z"),
            "announcement_in_next_window": int(bool(events)),
            "days_since_last_announcement": days_since,
            "event_count_in_window": len(events),
        })
        if events:
            last_event = events[-1]
        cursor = window_end

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

