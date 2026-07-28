#!/usr/bin/env python3
"""M0 expanding-window historical-rate baseline for a person-period table."""

from __future__ import annotations

import csv
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data/processed/person_period_daily.csv"
OUTPUT = ROOT / "data/processed/m0_forecasts.csv"


def main() -> int:
    with INPUT.open(encoding="utf-8", newline="") as handle:
        periods = list(csv.DictReader(handle))
    if not periods:
        raise SystemExit("No person-period rows found")

    # Beta(1, 1) posterior mean prevents unjustified 0/1 probabilities early on.
    positives = 0
    observed = 0
    output = []
    for row in periods:
        p_daily = (positives + 1) / (observed + 2)
        p_7d = 1 - (1 - p_daily) ** 7
        output.append({
            "issued_at_utc": row["window_start_utc"],
            "model": "M0_beta11_expanding",
            "p_24h": f"{p_daily:.8f}",
            "p_7d": f"{p_7d:.8f}",
            "label_24h": row["announcement_in_next_window"],
        })
        positives += int(row["announcement_in_next_window"])
        observed += 1

    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output[0]))
        writer.writeheader()
        writer.writerows(output)

    scored = output[1:]  # first prior-only prediction is retained but not summarized
    brier = sum(
        (float(row["p_24h"]) - int(row["label_24h"])) ** 2 for row in scored
    ) / len(scored)
    log_loss = -sum(
        int(row["label_24h"]) * math.log(max(float(row["p_24h"]), 1e-15))
        + (1 - int(row["label_24h"]))
        * math.log(max(1 - float(row["p_24h"]), 1e-15))
        for row in scored
    ) / len(scored)
    print(f"Wrote {len(output)} predictions to {OUTPUT.relative_to(ROOT)}")
    print(f"Descriptive pipeline check: Brier={brier:.6f}, LogLoss={log_loss:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

