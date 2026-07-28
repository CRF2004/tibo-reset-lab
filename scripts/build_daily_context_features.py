#!/usr/bin/env python3
"""Convert prediction-safe context events into daily time-varying features."""

from __future__ import annotations

import csv
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PERIODS = ROOT / "data/processed/person_period_daily.csv"
CONTEXT = ROOT / "data/processed/context_events.csv"
OUTPUT = ROOT / "data/processed/daily_context_features.csv"


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def main() -> int:
    with PERIODS.open(encoding="utf-8", newline="") as handle:
        periods = list(csv.DictReader(handle))
    with CONTEXT.open(encoding="utf-8", newline="") as handle:
        contexts = [
            row for row in csv.DictReader(handle)
            if row["prediction_eligible"] == "1"
        ]

    # The same official incident can support multiple later announcements. Deduplicate
    # by its status source and public start time before building predictor snapshots.
    unique = {}
    for row in contexts:
        official_ids = ";".join(
            source for source in row["source_ids"].split(";")
            if source.startswith("STATUS_")
        )
        key = (official_ids, row["first_public_at_utc"])
        previous = unique.get(key)
        if previous is None or int(row["event_strength_0_9"]) > int(
            previous["event_strength_0_9"]
        ):
            unique[key] = row
    events = list(unique.values())

    output = []
    for period in periods:
        snapshot = dt(period["window_start_utc"])
        visible = [
            event for event in events
            if dt(event["first_public_at_utc"]) <= snapshot
            and snapshot - dt(event["first_public_at_utc"]) <= timedelta(hours=72)
        ]
        active = [
            event for event in visible
            if not event["resolved_at_utc"] or dt(event["resolved_at_utc"]) > snapshot
        ]
        recently_resolved = [
            event for event in visible
            if event["resolved_at_utc"]
            and timedelta(0) <= snapshot - dt(event["resolved_at_utc"]) <= timedelta(hours=48)
        ]
        ages = [
            (snapshot - dt(event["first_public_at_utc"])).total_seconds() / 3600
            for event in visible
        ]
        output.append({
            "window_start_utc": period["window_start_utc"],
            "official_context_visible": int(bool(visible)),
            "official_incident_active": int(bool(active)),
            "official_incident_resolved_48h": int(bool(recently_resolved)),
            "max_event_strength_72h": (
                max(int(event["event_strength_0_9"]) for event in visible)
                if visible else 0
            ),
            "max_attention_state_72h": (
                max(int(event["attention_state_0_5"]) for event in visible)
                if visible else 0
            ),
            "hours_since_latest_context": f"{min(ages):.3f}" if ages else "",
            "visible_context_ids": ";".join(
                sorted(event["context_event_id"] for event in visible)
            ),
            "announcement_in_next_window": period["announcement_in_next_window"],
        })

    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output[0]))
        writer.writeheader()
        writer.writerows(output)
    print(f"Wrote {len(output)} daily context snapshots")
    print(f"Snapshots with visible context: {sum(int(r['official_context_visible']) for r in output)}")
    print(f"Positive labels among visible: {sum(int(r['announcement_in_next_window']) for r in output if r['official_context_visible'] == 1)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

