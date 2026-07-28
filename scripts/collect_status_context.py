#!/usr/bin/env python3
"""Collect official status incidents and retain Codex-related positive/negative contexts."""

from __future__ import annotations

import csv
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://status.openai.com"
RAW_DIR = ROOT / "data/raw/status_snapshots"
OUTPUT = ROOT / "data/raw/status_context_universe.csv"


def fetch(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "tibo-research/0.1"})
    with urllib.request.urlopen(request, timeout=25) as response:
        return response.read().decode("utf-8", errors="replace")


def incident_links(history: str) -> list[str]:
    return list(dict.fromkeys(re.findall(r'href="(/incidents/[^"?/]+)', history)))


def parse(link: str, body: str) -> dict[str, str]:
    incident_id = link.rsplit("/", 1)[-1]
    name_match = re.search(
        rf'\\"id\\":\\"{re.escape(incident_id)}\\"\}},?\]?,?\\"id\\":\\"{re.escape(incident_id)}\\",\\"name\\":\\"(.*?)\\"',
        body,
    )
    if not name_match:
        name_match = re.search(r'<title>(.*?) - OpenAI Status</title>', body)
    name = name_match.group(1) if name_match else ""
    name = name.replace(r"\u0026", "&").replace(r"\"", '"')
    published = sorted(set(re.findall(r'\\"published_at\\":\\"([^"\\]+)', body)))
    lower_name = name.lower()
    # The shared page shell mentions Codex on every incident page; using the full
    # HTML would therefore mark every incident as Codex-related. V0.1 keeps the
    # conservative set whose incident title explicitly names Codex.
    codex_related = int("codex" in lower_name)
    return {
        "status_incident_id": f"STATUS_{incident_id.upper()}",
        "name": name,
        "first_public_at_utc": published[0] if published else "",
        "last_update_at_utc": published[-1] if published else "",
        "source_url": BASE + link,
        "codex_related": codex_related,
        "has_rate_limit_language": int(
            any(token in lower_name for token in ("rate limit", "usage limit", "usage rate"))
        ),
        "collection_status": "ok",
    }


def collect_one(link: str) -> dict[str, str]:
    incident_id = link.rsplit("/", 1)[-1]
    try:
        body = fetch(BASE + link)
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        (RAW_DIR / f"{incident_id}.html").write_text(body, encoding="utf-8")
        return parse(link, body)
    except Exception as exc:
        return {
            "status_incident_id": f"STATUS_{incident_id.upper()}",
            "name": "",
            "first_public_at_utc": "",
            "last_update_at_utc": "",
            "source_url": BASE + link,
            "codex_related": 0,
            "has_rate_limit_language": 0,
            "collection_status": f"error:{type(exc).__name__}",
        }


def main() -> int:
    history = fetch(BASE + "/history")
    links = incident_links(history)
    with ThreadPoolExecutor(max_workers=8) as pool:
        rows = list(pool.map(collect_one, links))
    rows.sort(key=lambda row: row["first_public_at_utc"])
    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Collected {len(rows)} official incidents")
    print(f"Codex-related pages: {sum(int(r['codex_related']) for r in rows)}")
    print(f"Collection errors: {sum(not r['collection_status'].startswith('ok') for r in rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
