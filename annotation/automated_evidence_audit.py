#!/usr/bin/env python3
"""Audit objective evidence fields so humans only review judgment calls."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "annotation/evidence/historical_x_posts.csv"
RAW_DIR = ROOT / "annotation/evidence/oembed_raw"
OUTPUT = ROOT / "annotation/evidence/objective_audit.csv"
ALLOWED = {"thsottiaux": "Tibo", "OpenAI": "OpenAI"}


def snowflake_time(post_id: str) -> str:
    milliseconds = (int(post_id) >> 22) + 1288834974657
    return (
        datetime.fromtimestamp(milliseconds / 1000, timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def main() -> int:
    with EVIDENCE.open(encoding="utf-8", newline="") as handle:
        evidence = list(csv.DictReader(handle))

    results = []
    for row in evidence:
        post_id = row["post_id"]
        raw_path = RAW_DIR / f"{post_id}.json"
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
        canonical = f"https://x.com/{row['author_handle']}/status/{post_id}"
        checks = {
            "post_id_numeric": post_id.isdigit(),
            "author_allowed": row["author_handle"] in ALLOWED,
            "canonical_url_matches": row["canonical_url"] == canonical,
            "snowflake_time_matches": row["published_at_utc"] == snowflake_time(post_id),
            "retrieval_ok": row["retrieval_status"] == "ok",
            "raw_snapshot_exists": raw_path.exists(),
            "oembed_url_matches": raw.get("url", "").rstrip("/") == canonical,
            "oembed_author_matches": raw.get("author_name") == ALLOWED.get(
                row["author_handle"]
            ),
            "oembed_text_nonempty": bool(row["oembed_text"].strip()),
        }
        failed = [name for name, passed in checks.items() if not passed]
        results.append({
            "post_id": post_id,
            **{name: int(passed) for name, passed in checks.items()},
            "all_objective_checks_pass": int(not failed),
            "failed_checks": ";".join(failed),
        })

    fields = list(results[0])
    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)

    failures = [row for row in results if not row["all_objective_checks_pass"]]
    print(f"Audited {len(results)} posts; objective failures={len(failures)}")
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())

