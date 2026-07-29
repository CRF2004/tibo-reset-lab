from __future__ import annotations

import csv
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_person_period import build_rows  # noqa: E402
from event_units import accepted_event_times  # noqa: E402
from score_mature_forecasts import should_score_forecast  # noqa: E402


def t(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def rows(path: str) -> list[dict[str, str]]:
    with (ROOT / path).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


class EventUnitTests(unittest.TestCase):
    def test_cluster_first_collapses_promise_and_execution(self) -> None:
        announcements = [
            {"announcement_id": "A1", "announced_at_utc": "2026-01-01T10:00:00Z", "adjudication_status": "accepted"},
            {"announcement_id": "A2", "announced_at_utc": "2026-01-02T10:00:00Z", "adjudication_status": "accepted"},
        ]
        actions = [{"announcement_id": "A2", "action_cluster_id": "C1"}]
        overrides = [{"announcement_id": "A1", "action_cluster_id": "C1"}]
        self.assertEqual(
            accepted_event_times(announcements, actions, overrides, "cluster_first"),
            [t("2026-01-01T10:00:00Z")],
        )
        self.assertEqual(
            len(accepted_event_times(announcements, actions, overrides, "announcement_post")),
            2,
        )

    def test_missing_cluster_mapping_fails_closed(self) -> None:
        announcements = [
            {"announcement_id": "A1", "announced_at_utc": "2026-01-01T10:00:00Z", "adjudication_status": "accepted"}
        ]
        with self.assertRaisesRegex(ValueError, "missing an action cluster"):
            accepted_event_times(announcements, [], [], "cluster_first")

    def test_landmark_excludes_start_and_includes_end(self) -> None:
        start = t("2026-07-01T17:00:00Z")
        end = t("2026-07-03T17:00:00Z")
        events = [
            t("2026-07-01T17:00:00Z"),
            t("2026-07-02T17:00:00Z"),
            t("2026-07-03T17:00:00Z"),
        ]
        built = build_rows(events, start, end, "cluster_first")
        self.assertEqual([row["announcement_in_next_window"] for row in built], [1, 1])
        self.assertEqual([row["event_count_in_window"] for row in built], [1, 1])
        self.assertEqual(built[0]["days_since_last_announcement"], "0.000000")

    def test_real_gold_has_41_posts_and_40_primary_clusters(self) -> None:
        announcements = rows("data/processed/reset_announcements.csv")
        actions = rows("data/processed/reset_actions.csv")
        overrides = rows("data/processed/announcement_cluster_overrides.csv")
        posts = accepted_event_times(announcements, actions, overrides, "announcement_post")
        clusters = accepted_event_times(announcements, actions, overrides, "cluster_first")
        self.assertEqual(len(posts), 41)
        self.assertEqual(len(clusters), 40)
        self.assertLessEqual(max(clusters), max(posts))

    def test_partial_daily_window_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "complete 24-hour windows"):
            build_rows(
                [],
                datetime(2026, 7, 1, 17, tzinfo=timezone.utc),
                datetime(2026, 7, 2, 16, tzinfo=timezone.utc),
                "cluster_first",
            )

    def test_bootstrap_forecasts_are_not_formally_scored(self) -> None:
        forecast = {
            "run_id": "RUN_BOOTSTRAP",
            "forecast_id": "FC_BOOTSTRAP",
            "schedule_class": "bootstrap",
            "window_end_utc": "2026-07-29T17:00:00Z",
        }
        self.assertFalse(
            should_score_forecast(
                forecast, set(), set(), t("2026-07-30T17:00:00Z")
            )
        )

        forecast["schedule_class"] = "scheduled"
        self.assertTrue(
            should_score_forecast(
                forecast, set(), set(), t("2026-07-30T17:00:00Z")
            )
        )


if __name__ == "__main__":
    unittest.main()
