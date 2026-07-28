#!/usr/bin/env python3
"""Promote the human-accepted historical LLM annotations to gold tables."""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANNOTATIONS = ROOT / "annotation/llm/historical_llm_annotations_v1.csv"
EVIDENCE = ROOT / "annotation/evidence/historical_x_posts.csv"
ANNOUNCEMENTS = ROOT / "data/processed/reset_announcements.csv"
ACTIONS = ROOT / "data/processed/reset_actions.csv"


def main() -> int:
    with ANNOTATIONS.open(encoding="utf-8", newline="") as handle:
        annotations = list(csv.DictReader(handle))
    with EVIDENCE.open(encoding="utf-8", newline="") as handle:
        evidence = {row["post_id"]: row for row in csv.DictReader(handle)}

    accepted = [
        row for row in annotations
        if row["llm_decision"] == "accept_reset_announcement"
    ]
    announcements = []
    actions = []

    for row in accepted:
        post_id = row["post_id"]
        source = evidence[post_id]
        primary = row["primary_action"]
        reset_type = primary
        if primary == "targeted_or_conditional":
            reset_type = "targeted_or_conditional"
        announcements.append({
            "announcement_id": f"ANN_X_{post_id}",
            "announced_at_utc": row["published_at_utc"],
            "announcer": source["author_handle"],
            "source_id": f"SRC_X_{post_id}",
            "announcement_status": row["announcement_status"],
            "reset_type": reset_type,
            "reason_type": row["reason_type"],
            "eligible_plans": "",
            "quota_windows_affected": "",
            "explicit_scope": "",
            "policy_regime": (
                "pre_banked_reset"
                if row["published_at_utc"] < "2026-06-12T00:11:11.119Z"
                else "post_banked_reset"
            ),
            "adjudication_status": "accepted",
        })

        if int(row["new_hard_reset_actions"]):
            hard_type = (
                primary
                if primary in {"hard_global", "targeted_or_conditional"}
                else "hard_global"
            )
            actions.append({
                "action_id": f"ACT_{row['action_cluster_id']}_HARD",
                "action_cluster_id": row["action_cluster_id"],
                "announcement_id": f"ANN_X_{post_id}",
                "action_at_utc": row["published_at_utc"],
                "action_type": hard_type,
                "reason_type": row["reason_type"],
                "gold_version": "gold_v1",
            })
        if int(row["new_banked_reset_actions"]):
            actions.append({
                "action_id": f"ACT_{row['action_cluster_id']}_BANKED",
                "action_cluster_id": row["action_cluster_id"],
                "announcement_id": f"ANN_X_{post_id}",
                "action_at_utc": row["published_at_utc"],
                "action_type": "banked_credit",
                "reason_type": row["reason_type"],
                "gold_version": "gold_v1",
            })

    with ANNOUNCEMENTS.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(announcements[0]))
        writer.writeheader()
        writer.writerows(announcements)
    with ACTIONS.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(actions[0]))
        writer.writeheader()
        writer.writerows(actions)

    print(f"Promoted {len(announcements)} announcement posts")
    print(f"Promoted {len(actions)} unique reset actions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

