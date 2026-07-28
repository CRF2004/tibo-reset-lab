#!/usr/bin/env python3
"""Collect a frozen oEmbed snapshot for the known historical reset-post universe."""

from __future__ import annotations

import csv
import html
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "annotation/evidence/historical_x_posts.csv"
RAW = ROOT / "annotation/evidence/oembed_raw"

# Union of codex-resets.com, codex-reset.com API, direct searches, and GitHub citations.
# Items not ultimately eligible remain valuable negative/boundary examples.
POSTS = [
    ("thsottiaux", post_id, discovery)
    for post_id, discovery in [
        ("1968163721034994139", "codex-resets"),
        ("1983973493864894739", "reddit-history"),
        ("1986166501435711936", "codex-resets"),
        ("1986863197803192782", "codex-reset-api"),
        ("1992370994028388670", "codex-resets"),
        ("1995988609896513743", "codex-resets"),
        ("2001114683047317723", "codex-resets"),
        ("2002137269134819610", "codex-resets"),
        ("2004100061933064395", "codex-resets"),
        ("2028649088594436225", "codex-resets"),
        ("2029308599835738218", "codex-resets"),
        ("2030474136024400173", "codex-resets"),
        ("2031216405266481489", "codex-resets"),
        ("2031605592352313567", "codex-resets"),
        ("2037346989244096581", "codex-resets"),
        ("2039248564967424483", "codex-resets"),
        ("2041655710346572085", "codex-resets"),
        ("2042299371602264319", "codex-resets"),
        ("2044943514832871564", "codex-resets"),
        ("2046367145588916687", "codex-resets"),
        ("2048997818673537399", "codex-resets"),
        ("2055707616605835333", "codex-resets"),
        ("2058280452851638313", "codex-resets"),
        ("2061106703446450392", "codex-resets"),
        ("2062329981548802523", "codex-resets"),
        ("2065468501750649006", "github-28811"),
        ("2066956441173323943", "github-28811"),
        ("2067399435009622521", "codex-resets"),
        ("2070653282440405046", "codex-resets"),
        ("2071381664853319742", "codex-resets"),
        ("2071740419030053227", "codex-resets"),
        ("2075330198887940337", "codex-resets"),
        ("2075641131002700120", "codex-resets"),
        ("2075820987833274448", "codex-resets"),
        ("2076365965915467978", "direct-verification"),
        ("2076418567143408112", "codex-resets"),
        ("2076735790567338203", "codex-resets"),
        ("2077114635308986427", "codex-resets"),
        ("2077607697487188198", "codex-resets"),
        ("2078320950488297917", "codex-resets"),
        ("2079609157934886975", "codex-resets"),
        ("2081096447718723984", "codex-resets"),
        ("2081899343091843463", "codex-reset-api"),
        ("2081940052154933696", "codex-resets"),
    ]
] + [("OpenAI", "2065225362544726371", "github-28811")]


def snowflake_time(post_id: str) -> str:
    milliseconds = (int(post_id) >> 22) + 1288834974657
    value = datetime.fromtimestamp(milliseconds / 1000, timezone.utc)
    return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def text_from_embed(embed_html: str) -> tuple[str, int]:
    match = re.search(r"<p[^>]*>(.*?)</p>", embed_html, re.DOTALL)
    if not match:
        return "", 0
    value = re.sub(r"<br\s*/?>", "\n", match.group(1), flags=re.I)
    value = re.sub(r"<[^>]+>", "", value)
    value = html.unescape(value).strip()
    # X commonly appends a t.co URL after an ellipsis, so the ellipsis is not
    # necessarily the final character of the extracted text.
    truncated = int("…" in value or value.endswith("..."))
    return value, truncated


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    rows = []
    retrieved_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    for handle, post_id, discovery in POSTS:
        url = f"https://x.com/{handle}/status/{post_id}"
        endpoint = "https://publish.twitter.com/oembed?" + urllib.parse.urlencode({
            "url": url, "omit_script": "true", "dnt": "true",
        })
        status, author_name, text, truncated, error = "ok", "", "", 0, ""
        raw = {}
        try:
            request = urllib.request.Request(endpoint, headers={"User-Agent": "tibo-research/0.1"})
            with urllib.request.urlopen(request, timeout=20) as response:
                raw = json.load(response)
            author_name = raw.get("author_name", "")
            text, truncated = text_from_embed(raw.get("html", ""))
        except Exception as exc:
            status, error = "error", f"{type(exc).__name__}: {exc}"
        (RAW / f"{post_id}.json").write_text(
            json.dumps(raw or {"error": error}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        rows.append({
            "post_id": post_id,
            "author_handle": handle,
            "author_name": author_name,
            "canonical_url": url,
            "published_at_utc": snowflake_time(post_id),
            "retrieved_at_utc": retrieved_at,
            "retrieval_status": status,
            "oembed_text": text,
            "is_text_truncated": truncated,
            "discovery_source": discovery,
            "collection_notes": error,
        })
        time.sleep(0.1)

    fields = list(rows[0])
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} posts to {OUT.relative_to(ROOT)}")
    print(f"Retrieval errors: {sum(row['retrieval_status'] != 'ok' for row in rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
