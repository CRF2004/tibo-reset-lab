#!/usr/bin/env python3
"""Validate the research CSV layer without third-party dependencies."""

from __future__ import annotations

import csv
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_HEADERS = {
    "data/raw/sources.csv": [
        "source_id", "platform", "url", "author", "published_at_utc",
        "first_observed_at_utc", "raw_text", "snapshot_path",
        "deleted_or_edited", "credibility_level",
    ],
    "data/interim/annotation_candidates.csv": [
        "candidate_id", "claimed_announced_at_utc", "claimed_announcer",
        "candidate_source_id", "primary_source_url", "candidate_reset_type",
        "candidate_reason_type", "candidate_status", "annotator_1_decision",
        "annotator_2_decision", "adjudicated_decision", "notes",
    ],
    "data/processed/reset_announcements.csv": [
        "announcement_id", "announced_at_utc", "announcer", "source_id",
        "announcement_status", "reset_type", "reason_type", "eligible_plans",
        "quota_windows_affected", "explicit_scope", "policy_regime",
        "adjudication_status",
    ],
    "data/processed/context_events.csv": [
        "context_event_id", "linked_announcement_id", "start_at_utc",
        "first_public_at_utc", "resolved_at_utc", "event_type",
        "event_origin", "incident_stage", "milestone_label", "launch_label",
        "novelty_0_3", "disruption_0_3", "criticality_0_3",
        "event_strength_0_9", "attention_state_0_5", "official_incident",
        "root_cause_known", "mitigation_confirmed", "affected_scope",
        "prediction_eligible", "prediction_ineligible_reason", "confidence",
        "annotation_method", "source_ids", "scoring_rationale",
    ],
    "data/processed/community_signals.csv": [
        "window_start_utc", "window_hours", "unique_reporters",
        "new_github_issues", "new_forum_threads", "cross_platform_count",
        "complaint_velocity", "employee_replies", "duplicate_rate",
        "source_ids",
    ],
    "data/processed/reset_confirmations.csv": [
        "confirmation_id", "announcement_id", "confirmed_at_utc", "source_id",
        "account_plan", "client", "region_if_known", "applied_successfully",
        "which_window_changed", "evidence_quality",
    ],
    "data/raw/confirmation_evidence.csv": [
        "source_id", "platform", "url", "published_at_utc", "time_precision",
        "original_excerpt", "zh_translation", "evidence_kind",
    ],
    "data/processed/forecasts.csv": [
        "forecast_id", "issued_at_utc", "data_cutoff_at_utc",
        "model_version", "feature_version", "p_24h", "p_7d",
        "probability_by_reset_type_json", "training_end_utc", "code_commit",
    ],
    "data/processed/forward_forecasts_v1.csv": [
        "forecast_id", "run_id", "model", "horizon_hours", "issued_at_utc",
        "data_cutoff_at_utc", "window_end_utc", "probability",
        "schedule_class", "training_end_utc", "payload_sha256",
    ],
    "data/processed/forecast_outcomes_v1.csv": [
        "score_id", "forecast_id", "evaluated_at_utc", "window_end_utc",
        "label", "event_count", "brier", "log_loss", "outcome_status",
        "source_data_sha256",
    ],
    "data/processed/forecast_exclusions_v1.csv": [
        "exclusion_id", "run_id", "recorded_at_utc", "reason", "details",
    ],
    "data/processed/automation_runs.csv": [
        "automation_run_id", "phase", "scheduled_for_utc", "started_at_utc",
        "completed_at_utc", "status", "feed_fetched_at_utc", "feed_stale",
        "signal_post_id", "details", "log_path",
    ],
    "data/processed/missed_forecast_runs.csv": [
        "missed_run_id", "scheduled_for_utc", "recorded_at_utc", "reason",
        "recoverable", "details",
    ],
    "data/interim/live_reset_candidates.csv": [
        "candidate_id", "discovered_at_utc", "post_id", "author_handle",
        "canonical_url", "published_at_utc", "raw_text", "discovery_source",
        "candidate_status", "notes",
    ],
    "data/processed/confirmation_evidence_audit.csv": [
        "source_id", "snapshot_status", "snapshot_path", "snapshot_sha256",
        "time_precision", "reporter_identity_verified",
        "removed_or_fragile_source", "quality_grade", "independence_status",
    ],
    "data/processed/forecast_outcome_revisions_v1.csv": [
        "revision_id", "forecast_id", "recorded_at_utc", "discovered_at_utc",
        "old_label", "new_label", "old_event_count", "new_event_count",
        "old_brier", "new_brier", "old_log_loss", "new_log_loss", "reason",
        "source_data_sha256",
    ],
    "data/processed/strong_daily_baseline_forecasts.csv": [
        "issued_at_utc", "label_24h", "event_base_rate", "p_global",
        "p_rolling30", "p_rolling60", "p_ewma_hl30", "p_regime_rate",
        "p_km_renewal", "p_same_gap30", "p_m2_no_regime", "p_m2",
    ],
    "data/processed/reset_actions.csv": [
        "action_id", "action_cluster_id", "announcement_id", "action_at_utc",
        "action_type", "reason_type", "gold_version",
    ],
    "data/processed/announcement_cluster_overrides.csv": [
        "announcement_id", "action_cluster_id", "confidence", "rationale",
    ],
    "data/processed/tournament_predictors.csv": [
        "predictor_id", "display_name", "predictor_class", "model_version",
        "active", "formal_eligible", "description",
    ],
    "data/processed/community_players.csv": [
        "player_id", "display_name", "registered_at_utc", "status",
        "consent_version", "notes",
    ],
    "data/processed/tournament_rounds.csv": [
        "round_id", "issued_at_utc", "submission_open_utc",
        "submission_deadline_utc", "status", "schedule_class", "notes",
    ],
    "data/processed/tournament_forecasts.csv": [
        "tournament_forecast_id", "round_id", "predictor_id",
        "participant_id", "horizon_hours", "issued_at_utc",
        "submitted_at_utc", "window_end_utc", "probability",
        "schedule_class", "evidence_cutoff_utc", "evidence_ids", "rationale",
        "payload_sha256", "eligibility_status",
    ],
    "data/processed/tournament_scores.csv": [
        "tournament_score_id", "tournament_forecast_id", "scored_at_utc",
        "label", "event_count", "brier", "log_loss",
        "rolling30_brier_skill", "score_status", "source_data_sha256",
    ],
}

ENUMS = {
    "credibility_level": {
        "primary", "archived_primary", "independent_secondary",
        "community_report", "unknown",
    },
    "candidate_status": {
        "unreviewed", "needs_primary", "needs_human_review", "annotated", "accepted",
        "rejected", "uncertain", "needs_primary_llm_review",
    },
    "candidate_reset_type": {
        "hard_global", "banked_credit", "targeted_or_conditional",
        "extension_or_multiplier", "promise_only",
    },
    "candidate_reason_type": {
        "incident_compensation", "milestone_celebration",
        "launch_promotion", "community_response", "mixed_or_unclear",
    },
    "announcement_status": {"promised", "in_progress", "claimed_done"},
    "reset_type": {
        "hard_global", "banked_credit", "targeted_or_conditional",
        "extension_or_multiplier", "promise_only",
    },
    "reason_type": {
        "incident_compensation", "milestone_celebration",
        "launch_promotion", "community_response", "mixed_or_unclear",
    },
    "policy_regime": {
        "pre_banked_reset", "banked_reset_rollout", "post_banked_reset",
    },
    "adjudication_status": {"accepted", "uncertain"},
}

TIME_COLUMNS = {
    "published_at_utc", "first_observed_at_utc", "claimed_announced_at_utc",
    "announced_at_utc", "start_at_utc", "first_public_at_utc",
    "resolved_at_utc", "window_start_utc", "confirmed_at_utc",
    "issued_at_utc", "data_cutoff_at_utc", "training_end_utc",
    "window_end_utc", "evaluated_at_utc", "recorded_at_utc",
    "scheduled_for_utc", "started_at_utc", "completed_at_utc",
    "feed_fetched_at_utc", "discovered_at_utc",
    "registered_at_utc", "submission_open_utc", "submission_deadline_utc",
    "submitted_at_utc", "evidence_cutoff_utc", "scored_at_utc",
}


def parse_utc(value: str) -> None:
    if not value:
        return
    if not value.endswith("Z"):
        raise ValueError("must end in Z")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.utcoffset().total_seconds() != 0:
        raise ValueError("must be UTC")


def read_rows(relative: str) -> list[dict[str, str]]:
    with (ROOT / relative).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        expected = REQUIRED_HEADERS.get(relative)
        if expected and reader.fieldnames != expected:
            raise ValueError(
                f"{relative}: header mismatch\nexpected={expected}\nactual={reader.fieldnames}"
            )
        return list(reader)


def main() -> int:
    errors: list[str] = []
    tables: dict[str, list[dict[str, str]]] = {}
    for relative in REQUIRED_HEADERS:
        try:
            tables[relative] = read_rows(relative)
        except Exception as exc:  # report all structural failures together
            errors.append(str(exc))

    for relative, rows in tables.items():
        seen: set[str] = set()
        headers = REQUIRED_HEADERS[relative]
        id_column = next((c for c in headers if c.endswith("_id")), None)
        for line, row in enumerate(rows, start=2):
            if id_column and row[id_column]:
                if row[id_column] in seen:
                    errors.append(f"{relative}:{line}: duplicate {id_column}")
                seen.add(row[id_column])
            for column, value in row.items():
                if value and column in ENUMS and value not in ENUMS[column]:
                    errors.append(f"{relative}:{line}: invalid {column}={value!r}")
                if value and column in TIME_COLUMNS:
                    try:
                        parse_utc(value)
                    except ValueError as exc:
                        errors.append(f"{relative}:{line}: {column} {exc}")

    source_ids = {
        row["source_id"] for row in tables.get("data/raw/sources.csv", [])
    }
    historical_evidence = ROOT / "annotation/evidence/historical_x_posts.csv"
    if historical_evidence.exists():
        with historical_evidence.open(encoding="utf-8", newline="") as handle:
            source_ids.update(
                f"SRC_X_{row['post_id']}" for row in csv.DictReader(handle)
            )
    for line, row in enumerate(
        tables.get("data/interim/annotation_candidates.csv", []), start=2
    ):
        if row["candidate_source_id"] not in source_ids:
            errors.append(
                f"data/interim/annotation_candidates.csv:{line}: "
                "unknown candidate_source_id"
            )
    for line, row in enumerate(
        tables.get("data/processed/reset_announcements.csv", []), start=2
    ):
        if row["source_id"] not in source_ids:
            errors.append(
                f"data/processed/reset_announcements.csv:{line}: unknown source_id"
            )
    action_announcement_ids = {
        row["announcement_id"]
        for row in tables.get("data/processed/reset_actions.csv", [])
    }
    override_ids = set()
    for line, row in enumerate(
        tables.get("data/processed/announcement_cluster_overrides.csv", []), start=2
    ):
        if row["announcement_id"] not in announcement_ids:
            errors.append(
                f"data/processed/announcement_cluster_overrides.csv:{line}: "
                "unknown announcement_id"
            )
        if row["announcement_id"] in action_announcement_ids:
            errors.append(
                f"data/processed/announcement_cluster_overrides.csv:{line}: "
                "override duplicates an action-derived mapping"
            )
        if row["announcement_id"] in override_ids:
            errors.append(
                f"data/processed/announcement_cluster_overrides.csv:{line}: "
                "duplicate announcement override"
            )
        override_ids.add(row["announcement_id"])

    accepted_ids = {
        row["announcement_id"]
        for row in tables.get("data/processed/reset_announcements.csv", [])
        if row["adjudication_status"] == "accepted"
    }
    missing_cluster = sorted(accepted_ids - action_announcement_ids - override_ids)
    if missing_cluster:
        errors.append(
            "Accepted announcements missing action cluster mapping: "
            + ", ".join(missing_cluster)
        )

    confirmation_source_ids = {
        row["source_id"]
        for row in tables.get("data/raw/confirmation_evidence.csv", [])
    }
    announcement_ids = {
        row["announcement_id"]
        for row in tables.get("data/processed/reset_announcements.csv", [])
    }
    for line, row in enumerate(
        tables.get("data/processed/reset_confirmations.csv", []), start=2
    ):
        if row["source_id"] not in confirmation_source_ids:
            errors.append(
                f"data/processed/reset_confirmations.csv:{line}: unknown source_id"
            )
        if row["announcement_id"] not in announcement_ids:
            errors.append(
                f"data/processed/reset_confirmations.csv:{line}: "
                "unknown announcement_id"
            )
        if row["applied_successfully"] not in {"0", "1"}:
            errors.append(
                f"data/processed/reset_confirmations.csv:{line}: "
                "applied_successfully must be 0 or 1"
            )
    forward_ids = {
        row["forecast_id"]
        for row in tables.get("data/processed/forward_forecasts_v1.csv", [])
    }
    for line, row in enumerate(
        tables.get("data/processed/forward_forecasts_v1.csv", []), start=2
    ):
        try:
            probability = float(row["probability"])
            if not 0 <= probability <= 1:
                raise ValueError
        except ValueError:
            errors.append(
                f"data/processed/forward_forecasts_v1.csv:{line}: "
                "probability must be in [0, 1]"
            )
        if row["schedule_class"] not in {"scheduled", "bootstrap"}:
            errors.append(
                f"data/processed/forward_forecasts_v1.csv:{line}: "
                "invalid schedule_class"
            )
    for line, row in enumerate(
        tables.get("data/processed/forecast_outcomes_v1.csv", []), start=2
    ):
        if row["forecast_id"] not in forward_ids:
            errors.append(
                f"data/processed/forecast_outcomes_v1.csv:{line}: "
                "unknown forecast_id"
            )

    if errors:
        print("\n".join(f"ERROR: {error}" for error in errors), file=sys.stderr)
        return 1
    count = sum(len(rows) for rows in tables.values())
    print(f"OK: validated {len(tables)} tables and {count} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
