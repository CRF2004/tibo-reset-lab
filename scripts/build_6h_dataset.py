#!/usr/bin/env python3
"""Build the 6-hour person-period table and prediction-safe context snapshots."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timedelta
from pathlib import Path

from event_units import accepted_event_times

ROOT = Path(__file__).resolve().parents[1]
ANNOUNCEMENTS = ROOT / "data/processed/reset_announcements.csv"
ACTIONS = ROOT / "data/processed/reset_actions.csv"
OVERRIDES = ROOT / "data/processed/announcement_cluster_overrides.csv"
CONTEXTS = ROOT / "data/processed/context_events.csv"
OUTPUT = ROOT / "data/processed/person_period_6h.csv"


def utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.utcoffset() != timedelta(0):
        raise ValueError(f"Expected UTC timestamp, got {value!r}")
    return parsed


def stamp(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2025-09-17T00:00:00Z", type=utc)
    parser.add_argument("--end", default="2026-07-29T00:00:00Z", type=utc)
    args = parser.parse_args()
    if args.start >= args.end:
        parser.error("--start must be before --end")

    with ANNOUNCEMENTS.open(encoding="utf-8", newline="") as handle:
        announcements = list(csv.DictReader(handle))
    with ACTIONS.open(encoding="utf-8", newline="") as handle:
        actions = list(csv.DictReader(handle))
    with OVERRIDES.open(encoding="utf-8", newline="") as handle:
        overrides = list(csv.DictReader(handle))
    event_times = accepted_event_times(
        announcements, actions, overrides, event_unit="cluster_first"
    )
    with CONTEXTS.open(encoding="utf-8", newline="") as handle:
        candidates = [
            row for row in csv.DictReader(handle)
            if row["prediction_eligible"] == "1"
        ]

    # Collapse repeated announcement links to one underlying official incident.
    unique: dict[tuple[str, str], dict[str, str]] = {}
    for row in candidates:
        official_ids = ";".join(
            source for source in row["source_ids"].split(";")
            if source.startswith("STATUS_")
        )
        key = (official_ids, row["first_public_at_utc"])
        prior = unique.get(key)
        if prior is None or int(row["event_strength_0_9"]) > int(prior["event_strength_0_9"]):
            unique[key] = row
    contexts = list(unique.values())

    rows = []
    cursor = args.start
    last_event = max((event for event in event_times if event <= cursor), default=None)
    while cursor < args.end:
        window_end = min(cursor + timedelta(hours=6), args.end)
        events = [event for event in event_times if cursor < event <= window_end]
        visible = [
            event for event in contexts
            if utc(event["first_public_at_utc"]) <= cursor
            and cursor - utc(event["first_public_at_utc"]) <= timedelta(hours=72)
        ]
        active = [
            event for event in visible
            if not event["resolved_at_utc"] or utc(event["resolved_at_utc"]) > cursor
        ]
        resolved = [
            event for event in visible
            if event["resolved_at_utc"]
            and timedelta(0) <= cursor - utc(event["resolved_at_utc"]) <= timedelta(hours=48)
        ]
        ages = [
            (cursor - utc(event["first_public_at_utc"])).total_seconds() / 3600
            for event in visible
        ]
        rows.append({
            "window_start_utc": stamp(cursor),
            "window_end_utc": stamp(window_end),
            "announcement_in_next_window": int(bool(events)),
            "hours_since_last_announcement": (
                "" if last_event is None
                else f"{(cursor - last_event).total_seconds() / 3600:.6f}"
            ),
            "event_count_in_window": len(events),
            "official_context_visible": int(bool(visible)),
            "official_incident_active": int(bool(active)),
            "official_incident_resolved_48h": int(bool(resolved)),
            "max_event_strength_72h": (
                max(int(event["event_strength_0_9"]) for event in visible) if visible else 0
            ),
            "max_attention_state_72h": (
                max(int(event["attention_state_0_5"]) for event in visible) if visible else 0
            ),
            "hours_since_latest_context": f"{min(ages):.3f}" if ages else "",
            "visible_context_ids": ";".join(
                sorted(event["context_event_id"] for event in visible)
            ),
            "event_unit": "cluster_first",
        })
        if events:
            last_event = events[-1]
        cursor = window_end

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} 6-hour periods")
    print(f"Positive cluster-first periods: {sum(int(row['announcement_in_next_window']) for row in rows)}")
    print(f"Context-visible periods: {sum(int(row['official_context_visible']) for row in rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
