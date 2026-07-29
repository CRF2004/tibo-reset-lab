#!/usr/bin/env python3
"""Issue one immutable Task-7 forecast bundle for the cluster-first outcome."""

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

from event_units import accepted_event_times

ROOT = Path(__file__).resolve().parents[1]
PERIODS = ROOT / "data/processed/person_period_daily.csv"
ANN = ROOT / "data/processed/reset_announcements.csv"
ACTIONS = ROOT / "data/processed/reset_actions.csv"
OVERRIDES = ROOT / "data/processed/announcement_cluster_overrides.csv"
DAILY_CONTEXT = ROOT / "data/processed/daily_context_features.csv"
CONTEXT_EVENTS = ROOT / "data/processed/context_events.csv"
INDEX = ROOT / "data/processed/forward_forecasts_v1.csv"
LOCK_DIR = ROOT / "forecasts/locked_v1"
PT = ZoneInfo("America/Los_Angeles")
EVENT_UNIT = "cluster_first"


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def stamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def m2_vector(at: datetime, last: datetime) -> list[float]:
    local = at.astimezone(PT)
    weekday, month = local.weekday(), local.month
    return [
        math.log1p((at - last).total_seconds() / 86400),
        math.sin(2 * math.pi * weekday / 7),
        math.cos(2 * math.pi * weekday / 7),
        float(weekday >= 5),
        math.sin(2 * math.pi * month / 12),
        math.cos(2 * math.pi * month / 12),
        float(local >= datetime(2026, 6, 11, tzinfo=PT)),
    ]


def m3_vector(at: datetime, last: datetime, context: dict[str, float]) -> list[float]:
    return [
        math.log1p((at - last).total_seconds() / 86400),
        context["visible"], context["active"], context["resolved"],
        context["strength"], context["attention"], context["age"] / 72,
    ]


def context_at(
    at: datetime, cutoff: datetime, events: list[dict[str, str]]
) -> tuple[dict[str, float], list[str]]:
    visible = [
        row for row in events
        if dt(row["first_public_at_utc"]) <= cutoff
        and dt(row["first_public_at_utc"]) <= at
        and at - dt(row["first_public_at_utc"]) <= timedelta(hours=72)
    ]
    known_resolved = [
        row for row in visible
        if row["resolved_at_utc"] and dt(row["resolved_at_utc"]) <= cutoff
    ]
    active = [
        row for row in visible
        if not row["resolved_at_utc"] or dt(row["resolved_at_utc"]) > cutoff
        or dt(row["resolved_at_utc"]) > at
    ]
    recent = [
        row for row in known_resolved
        if timedelta(0) <= at - dt(row["resolved_at_utc"]) <= timedelta(hours=48)
    ]
    ages = [(at - dt(row["first_public_at_utc"])).total_seconds() / 3600 for row in visible]
    return {
        "visible": float(bool(visible)),
        "active": float(bool(active)),
        "resolved": float(bool(recent)),
        "strength": float(max((int(row["event_strength_0_9"]) for row in visible), default=0)),
        "attention": float(max((int(row["attention_state_0_5"]) for row in visible), default=0)),
        "age": min(ages) if ages else 72.0,
    }, sorted(row["context_event_id"] for row in visible)


def fit_model(x: np.ndarray, y: np.ndarray, continuous: list[int], binary: list[int]):
    ops = [("scale_continuous", StandardScaler(), continuous)]
    if binary:
        ops.append(("pass_binary", "passthrough", binary))
    model = make_pipeline(
        ColumnTransformer(ops, remainder="drop"),
        LogisticRegression(C=0.25, solver="lbfgs", max_iter=1000),
    )
    model.fit(x, y)
    return model


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--issued-at", help="UTC timestamp; defaults to now")
    parser.add_argument("--schedule-class", choices=["scheduled", "bootstrap"], default="scheduled")
    args = parser.parse_args()
    issued = dt(args.issued_at) if args.issued_at else datetime.now(timezone.utc)
    if args.schedule_class == "scheduled" and not (
        issued.minute == issued.second == 0 and issued.hour == 17
    ):
        raise SystemExit("Scheduled forecasts must be issued exactly at 17:00:00 UTC")

    periods = [
        row for row in read_csv(PERIODS)
        if row["days_since_last_announcement"] and dt(row["window_end_utc"]) <= issued
    ]
    if not periods:
        raise SystemExit("No completed aligned training windows")
    if any(row.get("event_unit") != EVENT_UNIT for row in periods):
        raise SystemExit("Person-period data must be rebuilt with event_unit=cluster_first")
    if any(dt(row["window_start_utc"]).hour != 17 for row in periods):
        raise SystemExit("Historical person-period landmarks must be 17:00 UTC")
    if args.schedule_class == "scheduled" and max(
        dt(row["window_end_utc"]) for row in periods
    ) != issued:
        raise SystemExit("Scheduled forecast requires a completed training window ending at issuance")

    announcement_rows = read_csv(ANN)
    action_rows = read_csv(ACTIONS)
    override_rows = read_csv(OVERRIDES)
    primary_events = [
        event for event in accepted_event_times(
            announcement_rows, action_rows, override_rows, EVENT_UNIT
        ) if event <= issued
    ]
    if not primary_events:
        raise SystemExit("No accepted cluster-first events before issuance")
    last = max(primary_events)

    daily_context = {
        row["window_start_utc"]: row for row in read_csv(DAILY_CONTEXT)
    }
    context_candidates = [
        row for row in read_csv(CONTEXT_EVENTS) if row["prediction_eligible"] == "1"
    ]
    unique = {}
    for row in context_candidates:
        official = ";".join(x for x in row["source_ids"].split(";") if x.startswith("STATUS_"))
        key = (official, row["first_public_at_utc"])
        if key not in unique or int(row["event_strength_0_9"]) > int(unique[key]["event_strength_0_9"]):
            unique[key] = row
    events = list(unique.values())

    y = np.array([int(row["announcement_in_next_window"]) for row in periods])
    x1 = np.array([[math.log1p(float(row["days_since_last_announcement"]))] for row in periods])
    model1 = fit_model(x1, y, [0], [])
    x2 = np.array([
        m2_vector(
            dt(row["window_start_utc"]),
            dt(row["window_start_utc"]) - timedelta(days=float(row["days_since_last_announcement"])),
        ) for row in periods
    ])
    model2 = fit_model(x2, y, [0, 1, 2, 4, 5], [3, 6])
    x3 = np.array([
        [
            math.log1p(float(row["days_since_last_announcement"])),
            float(daily_context[row["window_start_utc"]]["official_context_visible"]),
            float(daily_context[row["window_start_utc"]]["official_incident_active"]),
            float(daily_context[row["window_start_utc"]]["official_incident_resolved_48h"]),
            float(daily_context[row["window_start_utc"]]["max_event_strength_72h"]),
            float(daily_context[row["window_start_utc"]]["max_attention_state_72h"]),
            float(daily_context[row["window_start_utc"]]["hours_since_latest_context"]) / 72
            if daily_context[row["window_start_utc"]]["hours_since_latest_context"] else 1.0,
        ] for row in periods
    ])
    model3 = fit_model(x3, y, [0, 4, 5, 6], [1, 2, 3])

    hazards = {name: [] for name in (
        "M0_beta11_v1", "M0_rolling30_v1", "M0_rolling60_v1",
        "M0_ewma_hl30_v1", "M0_regime_rate_v1", "M0_km_renewal_v1",
        "M0_same_gap30_v1", "M1_logistic_C0.25_v1",
        "M2_logistic_C0.25_v1", "M3_lite_C0.25_v1",
    )}
    context_snapshots = []
    p0 = (int(np.sum(y)) + 1) / (len(y) + 2)
    historical_labels = [int(row["announcement_in_next_window"]) for row in periods]
    for day in range(7):
        at = issued + timedelta(days=day)
        context, ids = context_at(at, issued, events)
        context_snapshots.append({"at_utc": stamp(at), **context, "context_ids": ids})
        hazards["M0_beta11_v1"].append(p0)
        projected_labels = historical_labels + [0] * day
        for window, name in ((30, "M0_rolling30_v1"), (60, "M0_rolling60_v1")):
            recent = projected_labels[-window:]
            hazards[name].append((sum(recent) + 1) / (len(recent) + 2))
        weights = np.exp(-math.log(2) * np.arange(len(projected_labels) - 1, -1, -1) / 30)
        hazards["M0_ewma_hl30_v1"].append(
            float((np.dot(weights, projected_labels) + 1) / (np.sum(weights) + 2))
        )
        same_regime_labels = [
            int(row["announcement_in_next_window"]) for row in periods
            if (dt(row["window_start_utc"]).astimezone(PT) >= datetime(2026, 6, 11, tzinfo=PT))
            == (at.astimezone(PT) >= datetime(2026, 6, 11, tzinfo=PT))
        ] + [0] * day
        hazards["M0_regime_rate_v1"].append(
            (sum(same_regime_labels) + 1) / (len(same_regime_labels) + 2)
        )
        gap = (at - last).total_seconds() / 86400
        same_bin = [
            int(row["announcement_in_next_window"]) for row in periods
            if math.floor(float(row["days_since_last_announcement"])) == math.floor(gap)
        ]
        hazards["M0_km_renewal_v1"].append((sum(same_bin) + 1) / (len(same_bin) + 2))
        nearest = sorted(
            periods, key=lambda row: abs(float(row["days_since_last_announcement"]) - gap)
        )[:30]
        hazards["M0_same_gap30_v1"].append(
            (sum(int(row["announcement_in_next_window"]) for row in nearest) + 1)
            / (len(nearest) + 2)
        )
        hazards["M1_logistic_C0.25_v1"].append(
            float(model1.predict_proba(np.array([[math.log1p(gap)]]))[0, 1])
        )
        hazards["M2_logistic_C0.25_v1"].append(
            float(model2.predict_proba(np.array([m2_vector(at, last)]))[0, 1])
        )
        hazards["M3_lite_C0.25_v1"].append(
            float(model3.predict_proba(np.array([m3_vector(at, last, context)]))[0, 1])
        )

    issued_text = stamp(issued)
    run_id = "RUN7_" + issued_text.replace("-", "").replace(":", "")
    LOCK_DIR.mkdir(parents=True, exist_ok=True)
    lock_path = LOCK_DIR / f"{run_id}.json"
    if lock_path.exists():
        raise SystemExit(f"Refusing to overwrite {lock_path}")
    with INDEX.open(encoding="utf-8", newline="") as handle:
        existing = list(csv.DictReader(handle))
    if any(row["run_id"] == run_id for row in existing):
        raise SystemExit(f"Run already indexed: {run_id}")

    payload = {
        "run_id": run_id,
        "issued_at_utc": issued_text,
        "data_cutoff_at_utc": issued_text,
        "schedule_class": args.schedule_class,
        "event_unit": EVENT_UNIT,
        "training_end_utc": max(row["window_end_utc"] for row in periods),
        "training_rows": len(periods),
        "last_primary_event_at_utc": stamp(last),
        "models": {
            name: {
                "p_24h": round(values[0], 8),
                "p_7d": round(1 - math.prod(1 - p for p in values), 8),
                "daily_hazards_7d": [round(p, 8) for p in values],
            } for name, values in hazards.items()
        },
        "context_projection_at_issue": context_snapshots,
        "input_sha256": {
            str(path.relative_to(ROOT)): sha(path)
            for path in (
                PERIODS, ANN, ACTIONS, OVERRIDES, DAILY_CONTEXT,
                CONTEXT_EVENTS, Path(__file__), ROOT / "scripts/event_units.py",
            )
        },
        "notes": [
            "Primary outcome is the first accepted announcement per action cluster.",
            "Historical and prospective 24-hour windows share the 17:00 UTC landmark.",
            "Seven-day probabilities condition on no intervening primary event.",
            "Future context resolution timestamps unknown at issuance are not used.",
        ],
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    payload_sha = hashlib.sha256(canonical.encode()).hexdigest()
    payload["payload_sha256"] = payload_sha
    lock_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    rows = []
    for model, values in hazards.items():
        for horizon, probability in (
            (24, values[0]), (168, 1 - math.prod(1 - p for p in values))
        ):
            rows.append({
                "forecast_id": f"{run_id}_{model.removesuffix('_v1').replace('.', 'p')}_{horizon}H",
                "run_id": run_id,
                "model": model,
                "horizon_hours": horizon,
                "issued_at_utc": issued_text,
                "data_cutoff_at_utc": issued_text,
                "window_end_utc": stamp(issued + timedelta(hours=horizon)),
                "probability": f"{probability:.8f}",
                "schedule_class": args.schedule_class,
                "training_end_utc": payload["training_end_utc"],
                "payload_sha256": payload_sha,
            })
    with INDEX.open("a", encoding="utf-8", newline="") as handle:
        csv.DictWriter(handle, fieldnames=list(rows[0])).writerows(rows)
    print(f"Locked {run_id} with {len(rows)} model-horizon forecasts")
    for model, values in payload["models"].items():
        print(f"{model}: p24={values['p_24h']:.4f}, p7d={values['p_7d']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
