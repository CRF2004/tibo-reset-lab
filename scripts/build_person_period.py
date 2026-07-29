#!/usr/bin/env python3
"""Build leakage-conscious landmark person-period data.

The default primary outcome is the first accepted announcement per reset action
cluster. Historical rows must use the same 17:00 UTC landmark and 24-hour horizon
as prospective forecasts.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timedelta
from pathlib import Path

from event_units import accepted_event_times, utc

ROOT = Path(__file__).resolve().parents[1]
ANNOUNCEMENTS = ROOT / "data/processed/reset_announcements.csv"
ACTIONS = ROOT / "data/processed/reset_actions.csv"
OVERRIDES = ROOT / "data/processed/announcement_cluster_overrides.csv"
OUTPUT = ROOT / "data/processed/person_period_daily.csv"


def build_rows(
    events: list[datetime], start: datetime, end: datetime, event_unit: str
) -> list[dict[str, object]]:
    if start >= end:
        raise ValueError("start must be before end")
    if (end - start).total_seconds() % 86400:
        raise ValueError("Daily landmark range must contain complete 24-hour windows")

    events = sorted(events)
    previous = [event for event in events if event <= start]
    last_event = previous[-1] if previous else None
    rows: list[dict[str, object]] = []
    cursor = start
    while cursor < end:
        window_end = cursor + timedelta(days=1)
        future_events = [event for event in events if cursor < event <= window_end]
        days_since = (
            ""
            if last_event is None
            else f"{(cursor - last_event).total_seconds() / 86400:.6f}"
        )
        rows.append({
            "window_start_utc": cursor.isoformat().replace("+00:00", "Z"),
            "window_end_utc": window_end.isoformat().replace("+00:00", "Z"),
            "announcement_in_next_window": int(bool(future_events)),
            "days_since_last_announcement": days_since,
            "event_count_in_window": len(future_events),
            "event_unit": event_unit,
        })
        if future_events:
            last_event = future_events[-1]
        cursor = window_end
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True, type=utc)
    parser.add_argument("--end", required=True, type=utc)
    parser.add_argument(
        "--event-unit",
        choices=["cluster_first", "announcement_post"],
        default="cluster_first",
        help="Primary independent decision clusters or secondary all-post outcome.",
    )
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()

    with ANNOUNCEMENTS.open(encoding="utf-8", newline="") as handle:
        announcements = list(csv.DictReader(handle))
    with ACTIONS.open(encoding="utf-8", newline="") as handle:
        actions = list(csv.DictReader(handle))
    with OVERRIDES.open(encoding="utf-8", newline="") as handle:
        overrides = list(csv.DictReader(handle))

    events = accepted_event_times(
        announcements, actions, overrides, event_unit=args.event_unit
    )
    rows = build_rows(events, args.start, args.end, args.event_unit)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {args.output}")
    print(f"Event unit: {args.event_unit}; accepted event times: {len(events)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
