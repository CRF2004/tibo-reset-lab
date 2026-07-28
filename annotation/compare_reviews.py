#!/usr/bin/env python3
"""Compare two independent human review CSVs and create an adjudication queue."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

CORE_FIELDS = [
    "llm_decision",
    "eligibility_decision",
    "announcement_status",
    "primary_action",
    "secondary_actions",
    "reason_type",
    "scope_class",
    "eligible_plans",
    "quota_windows_affected",
    "context_source_ids",
    "action_cluster_id",
    "new_hard_reset_actions",
    "new_banked_reset_actions",
    "new_limit_change_actions",
]


def load(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    result = {}
    key_field = "candidate_id" if rows and "candidate_id" in rows[0] else "post_id"
    for row in rows:
        candidate_id = row[key_field]
        if candidate_id in result:
            raise ValueError(f"{path}: duplicate candidate_id {candidate_id}")
        result[candidate_id] = row
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("review_a", type=Path)
    parser.add_argument("review_b", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent / "adjudication" / "adjudication_queue.csv",
    )
    args = parser.parse_args()
    review_a, review_b = load(args.review_a), load(args.review_b)
    if review_a.keys() != review_b.keys():
        missing_a = sorted(review_b.keys() - review_a.keys())
        missing_b = sorted(review_a.keys() - review_b.keys())
        raise ValueError(f"candidate mismatch: missing in A={missing_a}; missing in B={missing_b}")

    queue = []
    for candidate_id in review_a:
        a, b = review_a[candidate_id], review_b[candidate_id]
        comparable = [field for field in CORE_FIELDS if field in a and field in b]
        disputed = [field for field in comparable if a[field].strip() != b[field].strip()]
        if disputed:
            decision_field = (
                "eligibility_decision" if "eligibility_decision" in a else "llm_decision"
            )
            queue.append({
                "candidate_id": candidate_id,
                "human_a_decision": a[decision_field],
                "human_b_decision": b[decision_field],
                "disputed_fields": ";".join(disputed),
                "human_a_values": " | ".join(f"{f}={a[f]}" for f in disputed),
                "human_b_values": " | ".join(f"{f}={b[f]}" for f in disputed),
                "final_decision": "",
                "rationale": "",
            })

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "candidate_id", "human_a_decision", "human_b_decision",
        "disputed_fields", "human_a_values", "human_b_values",
        "final_decision", "rationale",
    ]
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(queue)
    print(f"Wrote {len(queue)} disputed candidates to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
