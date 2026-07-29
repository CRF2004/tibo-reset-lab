#!/usr/bin/env python3
"""Score mature tournament forecasts against cluster-first reset events."""

from __future__ import annotations

import csv
import hashlib
import math
import argparse
from datetime import datetime, timezone
from pathlib import Path

from event_units import accepted_event_times

ROOT = Path(__file__).resolve().parents[1]
FORECASTS = ROOT / "data/processed/tournament_forecasts.csv"
SCORES = ROOT / "data/processed/tournament_scores.csv"
ANN = ROOT / "data/processed/reset_announcements.csv"
ACTIONS = ROOT / "data/processed/reset_actions.csv"
OVERRIDES = ROOT / "data/processed/announcement_cluster_overrides.csv"


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
    now = dt(args.evaluated_at) if args.evaluated_at else datetime.now(timezone.utc)
    events = accepted_event_times(
        read_csv(ANN), read_csv(ACTIONS), read_csv(OVERRIDES), "cluster_first"
    )
    forecasts = read_csv(FORECASTS)
    scored = {row["tournament_forecast_id"] for row in read_csv(SCORES)}
    by_key = {
        (row["round_id"], row["horizon_hours"], row["predictor_id"]): row
        for row in forecasts
    }
    created = []
    for row in forecasts:
        if (
            row["tournament_forecast_id"] in scored
            or row["eligibility_status"] != "eligible"
            or dt(row["window_end_utc"]) > now
        ):
            continue
        start, end = dt(row["issued_at_utc"]), dt(row["window_end_utc"])
        event_count = sum(start < event <= end for event in events)
        label = int(event_count > 0)
        p = min(0.999, max(0.001, float(row["probability"])))
        brier = (p - label) ** 2
        log_loss = -(label * math.log(p) + (1 - label) * math.log(1 - p))
        baseline = by_key.get((row["round_id"], row["horizon_hours"], "P_RECENT30"))
        skill = ""
        if baseline:
            baseline_error = (float(baseline["probability"]) - label) ** 2
            if baseline_error > 0:
                skill = f"{1 - brier / baseline_error:.8f}"
        created.append({
            "tournament_score_id": "TS_" + row["tournament_forecast_id"].removeprefix("TF_"),
            "tournament_forecast_id": row["tournament_forecast_id"],
            "scored_at_utc": stamp(now),
            "label": label,
            "event_count": event_count,
            "brier": f"{brier:.8f}",
            "log_loss": f"{log_loss:.8f}",
            "rolling30_brier_skill": skill,
            "score_status": "final_cluster_first",
            "source_data_sha256": source_hash(),
        })
    if created:
        with SCORES.open("a", encoding="utf-8", newline="") as handle:
            csv.DictWriter(handle, fieldnames=list(created[0])).writerows(created)
    print(f"Scored {len(created)} cluster-first tournament forecasts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
