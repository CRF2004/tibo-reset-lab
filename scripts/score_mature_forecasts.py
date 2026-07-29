#!/usr/bin/env python3
"""Append outcomes for mature Task-7 forecasts without editing their locks."""

from __future__ import annotations

import argparse
import csv
import hashlib
import math
from datetime import datetime, timezone
from pathlib import Path

from event_units import accepted_event_times

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "data/processed/forward_forecasts_v1.csv"
OUTCOMES = ROOT / "data/processed/forecast_outcomes_v1.csv"
ANN = ROOT / "data/processed/reset_announcements.csv"
ACTIONS = ROOT / "data/processed/reset_actions.csv"
OVERRIDES = ROOT / "data/processed/announcement_cluster_overrides.csv"
EXCLUSIONS = ROOT / "data/processed/forecast_exclusions_v1.csv"


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def stamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def source_hash() -> str:
    digest = hashlib.sha256()
    for path in (ANN, ACTIONS, OVERRIDES):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evaluated-at", help="UTC timestamp; defaults to now")
    args = parser.parse_args()
    evaluated = dt(args.evaluated_at) if args.evaluated_at else datetime.now(timezone.utc)
    forecasts = read_csv(INDEX)
    existing = read_csv(OUTCOMES)
    scored = {row["forecast_id"] for row in existing}
    excluded_runs = {row["run_id"] for row in read_csv(EXCLUSIONS)}
    events = accepted_event_times(
        read_csv(ANN), read_csv(ACTIONS), read_csv(OVERRIDES), "cluster_first"
    )
    source_sha = source_hash()
    rows = []
    for forecast in forecasts:
        if (
            forecast["run_id"] in excluded_runs
            or forecast["forecast_id"] in scored
            or dt(forecast["window_end_utc"]) > evaluated
        ):
            continue
        start, end = dt(forecast["issued_at_utc"]), dt(forecast["window_end_utc"])
        observed = [event for event in events if start < event <= end]
        label = int(bool(observed))
        p = min(max(float(forecast["probability"]), 1e-15), 1 - 1e-15)
        rows.append({
            "score_id": "SCORE_" + forecast["forecast_id"],
            "forecast_id": forecast["forecast_id"],
            "evaluated_at_utc": stamp(evaluated),
            "window_end_utc": forecast["window_end_utc"],
            "label": label,
            "event_count": len(observed),
            "brier": f"{(p - label) ** 2:.8f}",
            "log_loss": f"{-(label * math.log(p) + (1 - label) * math.log(1 - p)):.8f}",
            "outcome_status": "mature_complete_cluster_first",
            "source_data_sha256": source_sha,
        })
    if rows:
        with OUTCOMES.open("a", encoding="utf-8", newline="") as handle:
            csv.DictWriter(handle, fieldnames=list(rows[0])).writerows(rows)
    print(f"Appended {len(rows)} mature cluster-first forecast outcomes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
