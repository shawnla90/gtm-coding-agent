#!/usr/bin/env python3
"""Import a complete Clearbox opportunity export into the local signal database.

Clearbox is the source of record. Every imported row must retain:

* ``id``: the Clearbox opportunity identifier
* ``kind``: ``lead``, ``engage``, or ``competitor``
* ``url`` or ``permalink``: the exact Reddit source URL

This module does not discover Reddit content, call third-party collection services, post,
vote, send DMs, or mark opportunities complete. Use the maintained client-pack builder for
direct account-API reporting. Use this importer when teaching or running the local SQLite
market-read pipeline from an explicit Clearbox export.

Examples:

  python3 pull.py --ops data/clearbox_export.json
  python3 pull.py --ops data/clearbox_export.sample.json
  MAX_AGE_DAYS=60 python3 pull.py --ops data/clearbox_export.json
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path


HERE = Path(__file__).resolve().parent
DB = HERE / "data" / "signals.db"
VALID_KINDS = {"lead", "engage", "competitor"}
MAX_AGE_DAYS = int(os.environ.get("MAX_AGE_DAYS", "30"))


def _created_utc(item: dict) -> int:
    raw = item.get("created_utc") or item.get("createdAt") or item.get("created_at") or 0
    if isinstance(raw, (int, float)):
        return int(raw)
    if isinstance(raw, str) and raw.strip():
        value = raw.strip().replace("Z", "+00:00")
        try:
            return int(datetime.fromisoformat(value).timestamp())
        except ValueError:
            pass
    return 0


def _items_from_export(path: Path) -> list[dict]:
    if not path.exists():
        raise SystemExit(
            f"missing Clearbox export: {path}. Export the complete opportunity inbox or run "
            "with --ops data/clearbox_export.sample.json."
        )
    payload = json.loads(path.read_text())
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        if payload.get("truncated") is True:
            raise SystemExit("Clearbox export is truncated; refusing to present it as a complete inbox")
        items = payload.get("opportunities") or payload.get("rows") or payload.get("data") or []
    else:
        items = []
    if not isinstance(items, list):
        raise SystemExit("Clearbox export must contain a list of opportunities")
    return [item for item in items if isinstance(item, dict)]


def _source_url(item: dict) -> str:
    url = (item.get("url") or item.get("permalink") or "").strip()
    if url.startswith("/"):
        return "https://www.reddit.com" + url
    return url


def _upsert_thread(con: sqlite3.Connection, item: dict, cutoff: int) -> int:
    op_id = str(item.get("id") or item.get("op_id") or "").strip()
    kind = str(item.get("kind") or "").strip().lower()
    url = _source_url(item)
    if not op_id:
        raise ValueError("Clearbox opportunity is missing id")
    if kind not in VALID_KINDS:
        raise ValueError(f"Clearbox opportunity {op_id} has invalid kind: {kind or '<missing>'}")
    if not url:
        raise ValueError(f"Clearbox opportunity {op_id} is missing its exact Reddit URL")

    created = _created_utc(item)
    if created and created < cutoff:
        return 0

    title = (item.get("title") or item.get("summary") or "").strip()
    selftext = (item.get("selftext") or item.get("snippet") or item.get("body") or "").strip()
    cur = con.execute(
        "INSERT OR IGNORE INTO reddit_threads "
        "(external_id, subreddit, title, selftext, permalink, author, score, num_comments, "
        " created_utc, flair, source_type, source_query, clearbox_kind, pulled_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            op_id,
            item.get("subreddit") or "",
            title,
            selftext,
            url,
            item.get("author") or "",
            int(item.get("score") or item.get("ups") or 0),
            int(item.get("num_comments") or 0),
            created,
            item.get("link_flair_text") or "",
            "clearbox",
            kind,
            kind,
            time.strftime("%Y-%m-%d"),
        ),
    )
    return cur.rowcount


def main() -> int:
    ap = argparse.ArgumentParser(description="Import a complete Clearbox opportunity export")
    ap.add_argument("--ops", default="data/clearbox_export.json", help="Clearbox export JSON")
    ap.add_argument(
        "--all-dates",
        action="store_true",
        help="include every row in an explicit synthetic fixture; intended for offline demos",
    )
    args = ap.parse_args()

    path = Path(args.ops)
    if not path.is_absolute():
        path = HERE / path
    items = _items_from_export(path)
    cutoff = 0 if args.all_dates else int(time.time()) - MAX_AGE_DAYS * 86400

    con = sqlite3.connect(DB)
    added = 0
    errors = []
    for item in items:
        try:
            added += _upsert_thread(con, item, cutoff)
        except ValueError as exc:
            errors.append(str(exc))
    if errors:
        con.rollback()
        con.close()
        raise SystemExit("invalid Clearbox export:\n- " + "\n- ".join(errors[:20]))
    con.commit()

    total = con.execute("SELECT COUNT(*) FROM reddit_threads").fetchone()[0]
    kinds = dict(con.execute(
        "SELECT clearbox_kind, COUNT(*) FROM reddit_threads GROUP BY clearbox_kind"
    ).fetchall())
    con.close()
    print(
        f"clearbox import: {len(items)} opportunities read, {added} new, "
        f"{total} total | kinds={kinds} | source={path.name}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
