#!/usr/bin/env python3
"""Build LLM/rule-assisted historical context events with leakage flags."""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANN = ROOT / "data/processed/reset_announcements.csv"
EVIDENCE = ROOT / "annotation/evidence/historical_x_posts.csv"
OUTPUT = ROOT / "data/processed/context_events.csv"
STATUS_UNIVERSE = ROOT / "data/raw/status_context_universe.csv"
STATUS_BACKFILL = ROOT / "data/raw/status_context_backfill.csv"


def score(reason: str, text: str) -> tuple[int, int, int, str]:
    lower = text.lower()
    if reason == "incident_compensation":
        if "global outage" in lower:
            return 2, 3, 3, "Near/global outage: novel, highly disruptive, core reliability."
        if "outage" in lower or "blocked" in lower:
            return 1, 2, 3, "Service outage/blocking affected core Codex operation."
        if "latenc" in lower or "slow" in lower:
            return 1, 2, 2, "Degradation/latency disrupted use without clear global unavailability."
        return 1, 2, 2, "Confirmed or claimed product shortfall with moderate disruption."
    if reason == "milestone_celebration":
        return 1, 0, 2, "Growth/anniversary milestone is expected, non-disruptive, strategically salient."
    if reason == "launch_promotion":
        return 2, 0, 2, "New product/model/plan launch is novel and strategically salient."
    if reason == "community_response":
        return 1, 1, 2, "Aggregated public reports create visibility but limited proven disruption."
    return 1, 0, 1, "No single explicit event mechanism; weak contextual event."


def main() -> int:
    with ANN.open(encoding="utf-8", newline="") as handle:
        announcements = list(csv.DictReader(handle))
    with EVIDENCE.open(encoding="utf-8", newline="") as handle:
        evidence = {row["post_id"]: row for row in csv.DictReader(handle)}

    rows = []
    for ann in announcements:
        post_id = ann["announcement_id"].removeprefix("ANN_X_")
        source = evidence[post_id]
        text = source["oembed_text"]
        reason = ann["reason_type"]
        novelty, disruption, criticality, rationale = score(reason, text)
        event_type = {
            "incident_compensation": "product_incident",
            "milestone_celebration": "milestone",
            "launch_promotion": "product_launch_or_promotion",
            "community_response": "community_signal",
            "mixed_or_unclear": "mixed_or_unclear",
        }[reason]
        milestone = {
            "2041655710346572085": "3M weekly users",
            "2044943514832871564": "1-year anniversary",
            "2076365965915467978": "6M active users",
            "2076735790567338203": "7M active users",
            "2077114635308986427": "8M active users",
            "2077607697487188198": "9M active users",
            "2079609157934886975": "10M active users",
        }.get(post_id, "")
        launch = ""
        for marker in ("plugins", "$100 plan", "GPT-5.5", "ChatGPT Work"):
            if marker.lower() in text.lower() and reason == "launch_promotion":
                launch = marker
                break

        incident_stage = ""
        root_known = 0
        mitigation = 0
        if event_type == "product_incident":
            if any(token in text.lower() for token in ("resolved", "fixed", "back up")):
                incident_stage = "resolved"
                mitigation = 1
            elif "investigat" in text.lower():
                incident_stage = "investigating"
            else:
                incident_stage = "reported_or_retrospective"
            root_known = int(any(
                token in text.lower()
                for token in ("root caused", "caused", "optimization", "underlying system")
            ))

        # Default: the reset announcement itself is the first source, so context is
        # explanatory only and must not enter a pre-announcement forecast.
        start = ann["announced_at_utc"]
        first_public = ann["announced_at_utc"]
        resolved = ""
        prediction_eligible = 0
        ineligible_reason = "Context first observed in the reset announcement itself."
        source_ids = ann["source_id"]
        official_incident = 0
        attention = 4 if event_type in {"milestone", "product_launch_or_promotion"} else 3
        confidence = "medium"

        official_prior = {
            "2030474136024400173": (
                "2026-03-06T18:35:16Z", "2026-03-07T01:00:41Z",
                "STATUS_01KK26XE1W536H7DQV2EXM3GHE",
            ),
            "2046367145588916687": (
                "2026-04-20T22:57:00Z", "2026-04-20T23:13:00Z",
                "STATUS_01KPPJX4KHFAWS8YQE3KW235X7",
            ),
            "2058280452851638313": (
                "2026-05-22T16:37:50Z", "2026-05-23T10:58:20Z",
                "STATUS_TCC95QA3",
            ),
            "2062329981548802523": (
                "2026-06-03T04:58:00Z", "2026-06-03T11:09:42Z",
                "STATUS_01KT5XJ5ATD6RMYP908WS69FVD",
            ),
            "2070653282440405046": (
                "2026-06-26T17:04:02Z", "2026-06-29T17:06:33Z",
                "STATUS_6ENF4645",
            ),
            "2071381664853319742": (
                "2026-06-26T17:04:02Z", "2026-06-29T17:06:33Z",
                "STATUS_6ENF4645",
            ),
            "2071740419030053227": (
                "2026-06-26T17:04:02Z", "2026-06-29T17:06:33Z",
                "STATUS_6ENF4645",
            ),
            "2081096447718723984": (
                "2026-07-25T09:17:49Z", "2026-07-25T11:57:02Z",
                "STATUS_01KYC921K145JTR1JK7DYKGWH1;"
                "STATUS_01KYCGY017EG43XZS6GFVXA8VH",
            ),
        }
        if post_id in official_prior:
            status_start, status_resolved, status_ids = official_prior[post_id]
            start = status_start
            first_public = status_start
            resolved = status_resolved
            prediction_eligible = 1
            ineligible_reason = ""
            source_ids = status_ids + ";" + ann["source_id"]
            official_incident = 1
            attention = 3
            incident_stage = (
                "resolved"
                if status_resolved < ann["announced_at_utc"]
                else "investigating_or_monitoring"
            )
            mitigation = int(status_resolved < ann["announced_at_utc"])
            confidence = "high"

        rows.append({
            "context_event_id": f"CTX_{post_id}",
            "linked_announcement_id": ann["announcement_id"],
            "start_at_utc": start,
            "first_public_at_utc": first_public,
            "resolved_at_utc": resolved,
            "event_type": event_type,
            "event_origin": (
                "product_or_infrastructure"
                if event_type == "product_incident"
                else "organization_or_community"
            ),
            "incident_stage": incident_stage,
            "milestone_label": milestone,
            "launch_label": launch,
            "novelty_0_3": novelty,
            "disruption_0_3": disruption,
            "criticality_0_3": criticality,
            "event_strength_0_9": novelty + disruption + criticality,
            "attention_state_0_5": attention,
            "official_incident": official_incident,
            "root_cause_known": root_known,
            "mitigation_confirmed": mitigation,
            "affected_scope": "",
            "prediction_eligible": prediction_eligible,
            "prediction_ineligible_reason": ineligible_reason,
            "confidence": confidence,
            "annotation_method": "llm_rule_assisted_v0.1",
            "source_ids": source_ids,
            "scoring_rationale": rationale,
        })

    represented_status_ids = {
        source
        for row in rows
        for source in row["source_ids"].split(";")
        if source.startswith("STATUS_")
    }
    represented_status_starts = {
        row["first_public_at_utc"][:19]
        for row in rows
        if row["official_incident"] == 1 and row["first_public_at_utc"]
    }
    status_rows = []
    for path in (STATUS_BACKFILL, STATUS_UNIVERSE):
        if path.exists():
            with path.open(encoding="utf-8", newline="") as handle:
                status_rows.extend(csv.DictReader(handle))
    if status_rows:
        for status in status_rows:
            if status["codex_related"] != "1":
                continue
            status_id = status["status_incident_id"]
            if (
                status_id in represented_status_ids
                or status["first_public_at_utc"][:19] in represented_status_starts
            ):
                continue
            name = status["name"]
            lower = name.lower()
            disruption = 2 if any(
                token in lower
                for token in ("unable", "high failure", "high error", "elevated error")
            ) else 1
            criticality = 3 if "unable" in lower else 2
            rows.append({
                "context_event_id": f"CTX_{status_id}",
                "linked_announcement_id": "",
                "start_at_utc": status["first_public_at_utc"],
                "first_public_at_utc": status["first_public_at_utc"],
                "resolved_at_utc": status["last_update_at_utc"],
                "event_type": "product_incident",
                "event_origin": "product_or_infrastructure",
                "incident_stage": "resolved",
                "milestone_label": "",
                "launch_label": "",
                "novelty_0_3": 1,
                "disruption_0_3": disruption,
                "criticality_0_3": criticality,
                "event_strength_0_9": 1 + disruption + criticality,
                "attention_state_0_5": 3,
                "official_incident": 1,
                "root_cause_known": 0,
                "mitigation_confirmed": 1,
                "affected_scope": "",
                "prediction_eligible": 1,
                "prediction_ineligible_reason": "",
                "confidence": "high",
                "annotation_method": (
                    "official_status_search_backfill_v0.1"
                    if status["collection_status"].startswith("official_")
                    else "official_status_title_v0.1"
                ),
                "source_ids": status_id,
                "scoring_rationale": (
                    "Official Codex status incident; strength conservatively "
                    "scored from the incident title."
                ),
            })

    rows.sort(key=lambda row: (row["first_public_at_utc"], row["context_event_id"]))
    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} context events")
    print(f"Prediction-eligible: {sum(int(row['prediction_eligible']) for row in rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
