#!/usr/bin/env python3
"""Open an idempotent tournament round before its evidence cutoff."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUNDS = ROOT / "data/processed/tournament_rounds.csv"


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def stamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--issued-at", required=True)
    parser.add_argument("--schedule-class", choices=["scheduled", "bootstrap"], default="scheduled")
    parser.add_argument("--notes", default="Open community tournament round.")
    args = parser.parse_args()
    issued = dt(args.issued_at)
    round_id = "ROUND_" + stamp(issued).replace("-", "").replace(":", "")
    with ROUNDS.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if any(row["round_id"] == round_id for row in rows):
        print(f"Round already exists: {round_id}")
        return 0
    opened = datetime.now(timezone.utc)
    if opened > issued:
        raise SystemExit("Cannot open a round after its submission deadline")
    row = {
        "round_id": round_id,
        "issued_at_utc": stamp(issued),
        "submission_open_utc": stamp(opened),
        "submission_deadline_utc": stamp(issued),
        "status": "open",
        "schedule_class": args.schedule_class,
        "notes": args.notes,
    }
    with ROUNDS.open("a", encoding="utf-8", newline="") as handle:
        csv.DictWriter(handle, fieldnames=list(row)).writerow(row)
    print(f"Opened {round_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
