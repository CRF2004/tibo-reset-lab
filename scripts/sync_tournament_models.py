#!/usr/bin/env python3
"""Import eligible locked statistical forecasts into the tournament layer."""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/processed/forward_forecasts_v1.csv"
TARGET = ROOT / "data/processed/tournament_forecasts.csv"
ROUNDS = ROOT / "data/processed/tournament_rounds.csv"
EXCLUSIONS = ROOT / "data/processed/forecast_exclusions_v1.csv"
MAP = {
    "M0_beta11_v1": "P_GLOBAL",
    "M0_rolling30_v1": "P_RECENT30",
    "M1_logistic_C0.25_v1": "P_RENEWAL",
    "M2_logistic_C0.25_v1": "P_CALENDAR",
    "M3_lite_C0.25_v1": "P_THEORY",
}


def main() -> int:
    with SOURCE.open(encoding="utf-8", newline="") as handle:
        source = list(csv.DictReader(handle))
    with TARGET.open(encoding="utf-8", newline="") as handle:
        existing_rows = list(csv.DictReader(handle))
    existing = {row["tournament_forecast_id"] for row in existing_rows}
    with ROUNDS.open(encoding="utf-8", newline="") as handle:
        round_rows = list(csv.DictReader(handle))
    excluded_runs: set[str] = set()
    if EXCLUSIONS.exists():
        with EXCLUSIONS.open(encoding="utf-8", newline="") as handle:
            excluded_runs = {row["run_id"] for row in csv.DictReader(handle)}
    known_rounds = {row["round_id"] for row in round_rows}
    forecasts, new_rounds = [], []
    for row in source:
        if row["model"] not in MAP or row["run_id"] in excluded_runs:
            continue
        round_id = row["run_id"].replace("RUN7_", "ROUND_")
        if round_id not in known_rounds:
            new_rounds.append({
                "round_id": round_id,
                "issued_at_utc": row["issued_at_utc"],
                "submission_open_utc": row["issued_at_utc"],
                "submission_deadline_utc": row["issued_at_utc"],
                "status": "closed",
                "schedule_class": row["schedule_class"],
                "notes": "Imported statistical forecast round.",
            })
            known_rounds.add(round_id)
        forecast_id = "TF_" + row["forecast_id"]
        if forecast_id in existing:
            continue
        forecasts.append({
            "tournament_forecast_id": forecast_id,
            "round_id": round_id,
            "predictor_id": MAP[row["model"]],
            "participant_id": MAP[row["model"]],
            "horizon_hours": row["horizon_hours"],
            "issued_at_utc": row["issued_at_utc"],
            "submitted_at_utc": row["issued_at_utc"],
            "window_end_utc": row["window_end_utc"],
            "probability": row["probability"],
            "schedule_class": row["schedule_class"],
            "evidence_cutoff_utc": row["data_cutoff_at_utc"],
            "evidence_ids": row["payload_sha256"],
            "rationale": "Imported from immutable Task-7 statistical bundle.",
            "payload_sha256": row["payload_sha256"],
            "eligibility_status": "eligible",
        })
    if new_rounds:
        with ROUNDS.open("a", encoding="utf-8", newline="") as handle:
            csv.DictWriter(handle, fieldnames=list(new_rounds[0])).writerows(new_rounds)
    if forecasts:
        with TARGET.open("a", encoding="utf-8", newline="") as handle:
            csv.DictWriter(handle, fieldnames=list(forecasts[0])).writerows(forecasts)
    print(f"Imported {len(forecasts)} forecasts and {len(new_rounds)} rounds")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
