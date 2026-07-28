#!/usr/bin/env python3
"""Task 8 preflight/forecast runner with explicit completeness gates and logs."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import traceback
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEED_URL = "https://codex-reset.com/api/feed"
SNAPSHOTS = ROOT / "automation/snapshots"
LOGS = ROOT / "automation/logs"
RUNS = ROOT / "data/processed/automation_runs.csv"
MISSED = ROOT / "data/processed/missed_forecast_runs.csv"
CANDIDATES = ROOT / "data/interim/live_reset_candidates.csv"
ANN = ROOT / "data/processed/reset_announcements.csv"
PREFLIGHT = ROOT / "automation/latest_preflight.json"


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def stamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def append(path: Path, row: dict[str, object]) -> None:
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row))
        writer.writerow(row)


def scheduled_time(now: datetime, phase: str) -> datetime:
    target = now.replace(hour=17, minute=0, second=0, microsecond=0)
    if phase == "forecast" and now < target - timedelta(minutes=20):
        target -= timedelta(days=1)
    return target


def fetch_feed(now: datetime) -> tuple[dict, Path]:
    request = urllib.request.Request(FEED_URL, headers={"User-Agent": "tibo-research/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        feed = json.load(response)
    SNAPSHOTS.mkdir(parents=True, exist_ok=True)
    path = SNAPSHOTS / f"feed_{stamp(now).replace(':', '').replace('-', '')}.json"
    path.write_text(json.dumps(feed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return feed, path


def known_announcements() -> set[str]:
    with ANN.open(encoding="utf-8", newline="") as handle:
        return {
            row["announcement_id"].removeprefix("ANN_X_")
            for row in csv.DictReader(handle)
            if row["adjudication_status"] == "accepted"
        }


def feed_gate(feed: dict, now: datetime, known: set[str]) -> tuple[bool, str]:
    if not feed.get("fetched_at"):
        return False, "feed_missing_fetched_at"
    if feed.get("stale") or now - dt(feed["fetched_at"]) > timedelta(minutes=30):
        return False, "feed_stale"
    signal_id = str((feed.get("signal") or {}).get("tweet_id", ""))
    if not signal_id:
        return False, "feed_missing_signal"
    if signal_id not in known:
        return False, f"unreviewed_signal:{signal_id}"
    return True, "passed"


def add_candidate(feed: dict, now: datetime) -> None:
    signal = feed.get("signal") or {}
    post_id = str(signal.get("tweet_id", ""))
    if not post_id:
        return
    with CANDIDATES.open(encoding="utf-8", newline="") as handle:
        existing = {row["post_id"] for row in csv.DictReader(handle)}
    if post_id in existing:
        return
    append(CANDIDATES, {
        "candidate_id": f"LIVE_X_{post_id}",
        "discovered_at_utc": stamp(now),
        "post_id": post_id,
        "author_handle": feed.get("profile", {}).get("handle", ""),
        "canonical_url": signal.get("url", ""),
        "published_at_utc": signal.get("at", ""),
        "raw_text": signal.get("summary", ""),
        "discovery_source": "codex-reset.com/api/feed",
        "candidate_status": "needs_primary_llm_review",
        "notes": "Third-party discovery only; verify original X/oEmbed before gold promotion.",
    })


def run_command(command: list[str], log) -> None:
    result = subprocess.run(
        command, cwd=ROOT, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, check=False,
    )
    log.write("$ " + " ".join(command) + "\n" + result.stdout + "\n")
    if result.returncode:
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(command)}")


def run_optional_command(command: list[str], log) -> bool:
    """Run a non-blocking tournament component without invalidating research issuance."""
    result = subprocess.run(
        command, cwd=ROOT, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, check=False,
    )
    log.write("$ optional " + " ".join(command) + "\n" + result.stdout + "\n")
    return result.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["preflight", "forecast", "score"], required=True)
    parser.add_argument("--scheduled-for", help="Explicit UTC 17:00 timestamp for testing")
    args = parser.parse_args()
    now = datetime.now(timezone.utc)
    scheduled = dt(args.scheduled_for) if args.scheduled_for else scheduled_time(now, args.phase)
    run_id = f"AUTO_{args.phase.upper()}_{stamp(now).replace(':', '').replace('-', '')}"
    LOGS.mkdir(parents=True, exist_ok=True)
    log_path = LOGS / f"{run_id}.log"
    status, details, feed = "failed", "", {}
    started = now

    try:
        with log_path.open("w", encoding="utf-8") as log:
            log.write(f"run={run_id}\nphase={args.phase}\nscheduled={stamp(scheduled)}\n")
            if args.phase in {"preflight", "forecast"}:
                feed, snapshot = fetch_feed(now)
                log.write(f"feed_snapshot={snapshot.relative_to(ROOT)}\n")
                passed, gate_reason = feed_gate(feed, now, known_announcements())
                signal_id = str((feed.get("signal") or {}).get("tweet_id", ""))
                if gate_reason.startswith("unreviewed_signal"):
                    add_candidate(feed, now)
                if not passed:
                    raise RuntimeError(gate_reason)

            if args.phase == "preflight":
                PREFLIGHT.parent.mkdir(parents=True, exist_ok=True)
                PREFLIGHT.write_text(json.dumps({
                    "scheduled_for_utc": stamp(scheduled),
                    "checked_at_utc": stamp(now),
                    "status": "passed",
                    "signal_post_id": (feed.get("signal") or {}).get("tweet_id", ""),
                    "feed_fetched_at_utc": feed.get("fetched_at", ""),
                }, indent=2) + "\n", encoding="utf-8")
                run_command([
                    "python3", "scripts/open_tournament_round.py",
                    "--issued-at", stamp(scheduled), "--schedule-class", "scheduled",
                    "--notes", "Opened by the passed Task-8 preflight gate.",
                ], log)
                llm_ok = run_optional_command([
                    "python3", "scripts/run_llm_tournament.py",
                    "--round-id", "ROUND_" + stamp(scheduled).replace("-", "").replace(":", ""),
                ], log)
                status = "passed"
                details = (
                    "Feed fresh; latest signal accepted; five LLM forecasts locked."
                    if llm_ok else
                    "Feed fresh and accepted; LLM tournament partially/fully unavailable (non-blocking)."
                )
            elif args.phase == "forecast":
                if scheduled.hour != 17 or scheduled.minute or scheduled.second:
                    raise RuntimeError("scheduled_for must be exactly 17:00:00 UTC")
                if not PREFLIGHT.exists():
                    raise RuntimeError("missing successful preflight")
                preflight = json.loads(PREFLIGHT.read_text(encoding="utf-8"))
                if (
                    preflight.get("status") != "passed"
                    or preflight.get("scheduled_for_utc") != stamp(scheduled)
                    or now - dt(preflight["checked_at_utc"]) > timedelta(minutes=30)
                ):
                    raise RuntimeError("preflight missing, mismatched, or older than 30 minutes")
                period_end = (scheduled + timedelta(days=1)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                for command in (
                    ["python3", "scripts/collect_status_context.py"],
                    ["python3", "scripts/build_context_events.py"],
                    [
                        "python3", "scripts/build_person_period.py",
                        "--start", "2025-09-17T00:00:00Z",
                        "--end", stamp(period_end),
                    ],
                    ["python3", "scripts/build_daily_context_features.py"],
                    ["python3", "scripts/validate_data.py"],
                    [
                        "python3", "scripts/issue_task7_forecast.py",
                        "--issued-at", stamp(scheduled), "--schedule-class", "scheduled",
                    ],
                    ["python3", "scripts/sync_tournament_models.py"],
                    ["python3", "scripts/aggregate_crowd.py"],
                    ["python3", "scripts/score_mature_forecasts.py"],
                    ["python3", "scripts/score_tournament.py"],
                    ["python3", "scripts/build_task13_dashboard.py"],
                    ["python3", "scripts/build_community_dashboard.py"],
                    ["python3", "scripts/update_readme_snapshot.py"],
                ):
                    run_command(command, log)
                status, details = "passed", "Validated, signed scheduled bundle, and scored mature forecasts."
            else:
                run_command(["python3", "scripts/score_mature_forecasts.py"], log)
                run_command(["python3", "scripts/sync_tournament_models.py"], log)
                run_command(["python3", "scripts/aggregate_crowd.py"], log)
                run_command(["python3", "scripts/score_tournament.py"], log)
                run_command(["python3", "scripts/build_task13_dashboard.py"], log)
                run_command(["python3", "scripts/build_community_dashboard.py"], log)
                run_command(["python3", "scripts/update_readme_snapshot.py"], log)
                status, details = "passed", "Scored mature forecasts and refreshed dashboard."
    except Exception as exc:
        details = f"{type(exc).__name__}: {exc}"
        with log_path.open("a", encoding="utf-8") as log:
            log.write(details + "\n" + traceback.format_exc())
        if args.phase == "forecast":
            missed_id = "MISSED_" + stamp(scheduled).replace("-", "").replace(":", "")
            with MISSED.open(encoding="utf-8", newline="") as handle:
                existing = {row["missed_run_id"] for row in csv.DictReader(handle)}
            if missed_id not in existing:
                append(MISSED, {
                    "missed_run_id": missed_id,
                    "scheduled_for_utc": stamp(scheduled),
                    "recorded_at_utc": stamp(datetime.now(timezone.utc)),
                    "reason": "completeness_gate_failed",
                    "recoverable": 0,
                    "details": details,
                })
    completed = datetime.now(timezone.utc)
    append(RUNS, {
        "automation_run_id": run_id,
        "phase": args.phase,
        "scheduled_for_utc": stamp(scheduled),
        "started_at_utc": stamp(started),
        "completed_at_utc": stamp(completed),
        "status": status,
        "feed_fetched_at_utc": feed.get("fetched_at", ""),
        "feed_stale": int(bool(feed.get("stale"))) if feed else "",
        "signal_post_id": (feed.get("signal") or {}).get("tweet_id", "") if feed else "",
        "details": details,
        "log_path": str(log_path.relative_to(ROOT)),
    })
    print(f"{run_id}: {status}: {details}")
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
