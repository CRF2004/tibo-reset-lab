#!/usr/bin/env python3
"""Create an auditable equal-weight logit pool from eligible human players."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORECASTS = ROOT / "data/processed/tournament_forecasts.csv"
ROUNDS = ROOT / "data/processed/tournament_rounds.csv"
PLAYERS = ROOT / "data/processed/community_players.csv"


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def main() -> int:
    with FORECASTS.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
        fields = handle.seek(0) or next(csv.reader(handle), None)
    with ROUNDS.open(encoding="utf-8", newline="") as handle:
        rounds = {row["round_id"]: row for row in csv.DictReader(handle)}
    with PLAYERS.open(encoding="utf-8", newline="") as handle:
        active = {row["player_id"] for row in csv.DictReader(handle) if row["status"] == "active"}
    existing = {row["tournament_forecast_id"] for row in rows}
    groups: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in rows:
        if (
            row["predictor_id"] == "P_PLAYER"
            and row["eligibility_status"] == "eligible"
            and row["participant_id"] in active
        ):
            groups.setdefault((row["round_id"], row["horizon_hours"]), []).append(row)
    created = []
    for (round_id, horizon), candidates in groups.items():
        round_row = rounds[round_id]
        deadline = dt(round_row["submission_deadline_utc"])
        latest_by_player = {
            row["participant_id"]: row
            for row in candidates
            if dt(row["submitted_at_utc"]) <= deadline
        }
        if len(latest_by_player) < 3:
            continue
        forecast_id = f"TF_{round_id}_P_CROWD_{horizon}H"
        if forecast_id in existing:
            continue
        source = list(latest_by_player.values())
        logits = [math.log(float(row["probability"]) / (1 - float(row["probability"]))) for row in source]
        mean_logit = sum(logits) / len(logits)
        probability = min(0.999, max(0.001, 1 / (1 + math.exp(-mean_logit))))
        payload = {
            "tournament_forecast_id": forecast_id,
            "round_id": round_id,
            "predictor_id": "P_CROWD",
            "participant_id": "P_CROWD",
            "horizon_hours": horizon,
            "issued_at_utc": round_row["issued_at_utc"],
            "submitted_at_utc": round_row["submission_deadline_utc"],
            "window_end_utc": source[0]["window_end_utc"],
            "probability": f"{probability:.8f}",
            "schedule_class": round_row["schedule_class"],
            "evidence_cutoff_utc": round_row["issued_at_utc"],
            "evidence_ids": ";".join(sorted(row["tournament_forecast_id"] for row in source)),
            "rationale": f"Equal-weight logit pool of {len(source)} eligible independent players.",
            "eligibility_status": "eligible",
        }
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        payload["payload_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
        created.append(payload)
    if created:
        fieldnames = list(created[0])
        with FORECASTS.open("a", encoding="utf-8", newline="") as handle:
            csv.DictWriter(handle, fieldnames=fieldnames).writerows(created)
    print(f"Created {len(created)} crowd forecasts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
