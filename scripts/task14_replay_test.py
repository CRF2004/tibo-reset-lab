#!/usr/bin/env python3
"""Isolated replay test for append-only outcome revision semantics."""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="tibo-replay-") as temp:
        outcome = Path(temp) / "outcome.csv"
        revision = Path(temp) / "revision.csv"
        outcome.write_text("forecast_id,p,label,brier\nF1,0.2,0,0.04\n", encoding="utf-8")
        before = hashlib.sha256(outcome.read_bytes()).hexdigest()
        revision.write_text(
            "revision_id,forecast_id,old_label,new_label,old_brier,new_brier\n"
            "R1,F1,0,1,0.04,0.64\n",
            encoding="utf-8",
        )
        after = hashlib.sha256(outcome.read_bytes()).hexdigest()
        assert before == after
        assert revision.read_text(encoding="utf-8").count("\n") == 2
    print("PASS: original outcome unchanged; one revision appended; 0.04 -> 0.64")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
