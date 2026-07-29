#!/usr/bin/env python3
"""Shared event-unit construction for historical training and prospective scoring.

The primary outcome is the first accepted public announcement in each reset action
cluster.  All accepted announcement posts remain available as a secondary outcome.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Iterable


def utc(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() != timedelta(0):
        raise ValueError(f"Expected UTC timestamp, got {value!r}")
    return result


def accepted_event_times(
    announcements: Iterable[dict[str, str]],
    actions: Iterable[dict[str, str]],
    overrides: Iterable[dict[str, str]],
    event_unit: str = "cluster_first",
) -> list[datetime]:
    """Return sorted event times under a declared analysis unit.

    ``announcement_post`` keeps every accepted qualifying post. ``cluster_first``
    maps posts to action clusters and keeps the earliest accepted post per cluster.
    An explicit override table handles promises that precede the action record.
    """
    accepted = [
        row for row in announcements if row.get("adjudication_status") == "accepted"
    ]
    if event_unit == "announcement_post":
        return sorted(utc(row["announced_at_utc"]) for row in accepted)
    if event_unit != "cluster_first":
        raise ValueError(f"Unknown event_unit={event_unit!r}")

    cluster_by_announcement: dict[str, str] = {}
    for row in actions:
        announcement_id = row["announcement_id"]
        cluster_id = row["action_cluster_id"]
        existing = cluster_by_announcement.get(announcement_id)
        if existing is not None and existing != cluster_id:
            raise ValueError(
                f"Announcement {announcement_id} maps to multiple clusters: "
                f"{existing} and {cluster_id}"
            )
        cluster_by_announcement[announcement_id] = cluster_id

    for row in overrides:
        announcement_id = row["announcement_id"]
        cluster_id = row["action_cluster_id"]
        existing = cluster_by_announcement.get(announcement_id)
        if existing is not None and existing != cluster_id:
            raise ValueError(
                f"Override conflicts for {announcement_id}: {existing} vs {cluster_id}"
            )
        cluster_by_announcement[announcement_id] = cluster_id

    missing = sorted(
        row["announcement_id"]
        for row in accepted
        if row["announcement_id"] not in cluster_by_announcement
    )
    if missing:
        raise ValueError(
            "Accepted announcements missing an action cluster mapping: "
            + ", ".join(missing)
        )

    times_by_cluster: dict[str, list[datetime]] = defaultdict(list)
    for row in accepted:
        times_by_cluster[cluster_by_announcement[row["announcement_id"]]].append(
            utc(row["announced_at_utc"])
        )
    return sorted(min(values) for values in times_by_cluster.values())
