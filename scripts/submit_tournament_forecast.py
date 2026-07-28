#!/usr/bin/env python3
"""Append and hash-lock one LLM or player tournament forecast."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORECASTS = ROOT / "data/processed/tournament_forecasts.csv"
ROUNDS = ROOT / "data/processed/tournament_rounds.csv"
LOCKS = ROOT / "community/locked"


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def stamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--round-id", required=True)
    parser.add_argument("--predictor-id", choices=["P_LLM", "P_PLAYER"], required=True)
    parser.add_argument("--participant-id", required=True)
    parser.add_argument("--horizon-hours", type=int, choices=[24, 168], required=True)
    parser.add_argument("--probability", type=float, required=True)
    parser.add_argument("--submitted-at")
    parser.add_argument("--evidence-ids", default="")
    parser.add_argument("--rationale", required=True)
    args = parser.parse_args()
    submitted = dt(args.submitted_at) if args.submitted_at else datetime.now(timezone.utc)
    with ROUNDS.open(encoding="utf-8", newline="") as handle:
        rounds = {row["round_id"]: row for row in csv.DictReader(handle)}
    if args.round_id not in rounds:
        raise SystemExit("Unknown round")
    round_row = rounds[args.round_id]
    issued = dt(round_row["issued_at_utc"])
    deadline = dt(round_row["submission_deadline_utc"])
    if submitted > deadline:
        raise SystemExit("Submission arrived after deadline")
    if not 0.001 <= args.probability <= 0.999:
        raise SystemExit("Probability must be in [0.001, 0.999]")
    forecast_id = (
        f"TF_{args.round_id}_{args.predictor_id}_{args.participant_id}_{args.horizon_hours}H"
    )
    with FORECASTS.open(encoding="utf-8", newline="") as handle:
        existing = {row["tournament_forecast_id"] for row in csv.DictReader(handle)}
    if forecast_id in existing:
        raise SystemExit("Duplicate forecast")
    payload = {
        "tournament_forecast_id": forecast_id,
        "round_id": args.round_id,
        "predictor_id": args.predictor_id,
        "participant_id": args.participant_id,
        "horizon_hours": args.horizon_hours,
        "issued_at_utc": round_row["issued_at_utc"],
        "submitted_at_utc": stamp(submitted),
        "window_end_utc": stamp(issued + timedelta(hours=args.horizon_hours)),
        "probability": f"{args.probability:.8f}",
        "schedule_class": round_row["schedule_class"],
        "evidence_cutoff_utc": round_row["issued_at_utc"],
        "evidence_ids": args.evidence_ids,
        "rationale": args.rationale,
        "eligibility_status": "eligible",
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    payload["payload_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    row = {key: payload[key] for key in [
        "tournament_forecast_id", "round_id", "predictor_id", "participant_id",
        "horizon_hours", "issued_at_utc", "submitted_at_utc", "window_end_utc",
        "probability", "schedule_class", "evidence_cutoff_utc", "evidence_ids",
        "rationale", "payload_sha256", "eligibility_status",
    ]}
    LOCKS.mkdir(parents=True, exist_ok=True)
    lock = LOCKS / f"{forecast_id}.json"
    lock.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with FORECASTS.open("a", encoding="utf-8", newline="") as handle:
        csv.DictWriter(handle, fieldnames=list(row)).writerow(row)
    print(f"Locked {forecast_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
