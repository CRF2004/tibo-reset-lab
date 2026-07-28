#!/usr/bin/env python3
"""Fit frozen M2 and append an immutable, hash-manifested forward forecast."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
PERIODS = ROOT / "data/processed/person_period_daily.csv"
ANN = ROOT / "data/processed/reset_announcements.csv"
FORECASTS = ROOT / "data/processed/forecasts.csv"
LOCK_DIR = ROOT / "forecasts/locked"
PT = ZoneInfo("America/Los_Angeles")


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def stamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def vector(issue: datetime, last: datetime) -> list[float]:
    gap_days = (issue - last).total_seconds() / 86400
    local = issue.astimezone(PT)
    weekday = local.weekday()
    month = local.month
    return [
        math.log1p(gap_days),
        math.sin(2 * math.pi * weekday / 7),
        math.cos(2 * math.pi * weekday / 7),
        float(weekday >= 5),
        math.sin(2 * math.pi * month / 12),
        math.cos(2 * math.pi * month / 12),
        float(local >= datetime(2026, 6, 11, tzinfo=PT)),
    ]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--issued-at", help="UTC ISO timestamp; defaults to current UTC")
    args = parser.parse_args()
    issued = dt(args.issued_at) if args.issued_at else datetime.now(timezone.utc)

    with PERIODS.open(encoding="utf-8", newline="") as handle:
        all_periods = list(csv.DictReader(handle))
    periods = [
        row for row in all_periods
        if row["days_since_last_announcement"] and dt(row["window_end_utc"]) <= issued
    ]
    with ANN.open(encoding="utf-8", newline="") as handle:
        announcement_rows = [
            row for row in csv.DictReader(handle)
            if row["adjudication_status"] == "accepted"
            and dt(row["announced_at_utc"]) <= issued
        ]
    if not periods or not announcement_rows:
        raise SystemExit("Insufficient completed training periods or announcements")

    x = np.array([
        vector(
            dt(row["window_start_utc"]),
            dt(row["window_start_utc"]) - timedelta(
                days=float(row["days_since_last_announcement"])
            ),
        )
        for row in periods
    ])
    y = np.array([int(row["announcement_in_next_window"]) for row in periods])
    transform = ColumnTransformer([
        ("scale_continuous", StandardScaler(), [0, 1, 2, 4, 5]),
        ("pass_binary", "passthrough", [3, 6]),
    ])
    estimator = make_pipeline(
        transform,
        LogisticRegression(C=0.25, solver="lbfgs", max_iter=1000),
    )
    estimator.fit(x, y)

    last = max(dt(row["announced_at_utc"]) for row in announcement_rows)
    hazards = []
    for day in range(7):
        at = issued + timedelta(days=day)
        hazards.append(float(estimator.predict_proba(np.array([vector(at, last)]))[0, 1]))
    p24 = hazards[0]
    p7d = 1 - math.prod(1 - probability for probability in hazards)

    counts: dict[str, int] = {}
    for row in announcement_rows:
        counts[row["reset_type"]] = counts.get(row["reset_type"], 0) + 1
    total = sum(counts.values())
    type_probs = {key: round(value / total, 6) for key, value in sorted(counts.items())}

    issued_text = stamp(issued)
    forecast_id = "FCST_" + issued_text.replace("-", "").replace(":", "")
    row = {
        "forecast_id": forecast_id,
        "issued_at_utc": issued_text,
        "data_cutoff_at_utc": issued_text,
        "model_version": "M2_logistic_C0.25_v1",
        "feature_version": "daily_v1_exact_issue_projection",
        "p_24h": f"{p24:.8f}",
        "p_7d": f"{p7d:.8f}",
        "probability_by_reset_type_json": json.dumps(type_probs, ensure_ascii=False, separators=(",", ":")),
        "training_end_utc": max(row["window_end_utc"] for row in periods),
        "code_commit": "nogit_sha256_manifest",
    }

    LOCK_DIR.mkdir(parents=True, exist_ok=True)
    lock_path = LOCK_DIR / f"{forecast_id}.json"
    if lock_path.exists():
        raise SystemExit(f"Refusing to overwrite locked forecast: {lock_path}")
    manifest = {
        "forecast": row,
        "daily_hazards_7d": [round(value, 8) for value in hazards],
        "last_announcement_at_utc": stamp(last),
        "training_rows": len(periods),
        "input_sha256": {
            str(PERIODS.relative_to(ROOT)): digest(PERIODS),
            str(ANN.relative_to(ROOT)): digest(ANN),
            str(Path(__file__).relative_to(ROOT)): digest(Path(__file__)),
        },
        "method_note": (
            "p_7d is the complement of the product of seven projected daily "
            "non-event hazards, conditional on no intervening announcement."
        ),
    }
    lock_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with FORECASTS.open(encoding="utf-8", newline="") as handle:
        existing = list(csv.DictReader(handle))
    if any(item["forecast_id"] == forecast_id for item in existing):
        raise SystemExit(f"Duplicate forecast id: {forecast_id}")
    with FORECASTS.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row))
        writer.writerow(row)
    print(f"Locked {forecast_id}: p24={p24:.4f}, p7d={p7d:.4f}")
    print(lock_path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
