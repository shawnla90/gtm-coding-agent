#!/usr/bin/env python3
"""
scrape_x.py — Pull recent tweets from tracked X/Twitter sources.

Uses the Apify actor `apidojo/tweet-scraper` to fetch recent tweets for each
source with platform='x' and status='active'. Inserts into content_items.

Usage:
  python3 scripts/scrape_x.py                         # scrape all active X sources
  python3 scripts/scrape_x.py --source-id 7            # single source
  python3 scripts/scrape_x.py --max-posts 40           # per source
  python3 scripts/scrape_x.py --max-age-days 14        # how far back
  python3 scripts/scrape_x.py --dry-run                # plan only
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta

from _lib import (
    finish_scrape_run,
    get_apify_token,  # noqa: F401
    get_db,
    run_apify_actor,
    start_scrape_run,
)

ACTOR_TWEETS = "apidojo/tweet-scraper"


def _parse_created_at(raw: str | None) -> str | None:
    if not raw:
        return None
    try:
        dt = datetime.strptime(raw, "%a %b %d %H:%M:%S %z %Y")
        return dt.strftime("%Y-%m-%dT%H:%M:%S+00:00")
    except Exception:
        return raw


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-id", type=int)
    parser.add_argument("--relevance")
    parser.add_argument("--max-posts", type=int, default=30)
    parser.add_argument("--max-age-days", type=int, default=21)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    conn = get_db()
    conditions = ["platform = 'x'", "status = 'active'", "handle IS NOT NULL"]
    params: list = []
    if args.source_id:
        conditions.append("id = ?")
        params.append(args.source_id)
    if args.relevance:
        conditions.append("relevance = ?")
        params.append(args.relevance)
    where = " AND ".join(conditions)

    sources = [
        dict(r)
        for r in conn.execute(
            f"SELECT id, handle, name, relevance FROM sources WHERE {where} ORDER BY relevance, name",
            params,
        ).fetchall()
    ]

    if not sources:
        print("No matching X sources found.")
        return 0

    print(f"Found {len(sources)} X sources:")
    for s in sources:
        print(f"  [{s['id']:3}] {s['name']:40} @{s['handle']}")

    if args.dry_run:
        print("\n(dry-run — no Apify calls made)")
        return 0

    get_apify_token()
    end = datetime.utcnow().strftime("%Y-%m-%d")
    start = (datetime.utcnow() - timedelta(days=args.max_age_days)).strftime("%Y-%m-%d")

    run_id = start_scrape_run(
        conn,
        name="x-tweets",
        target=",".join(str(s["id"]) for s in sources),
        platforms="x",
    )

    total_ingested = 0
    for s in sources:
        handle = str(s["handle"]).lstrip("@")
        print(f"\n── @{handle} ({s['name']}) ──")
        items = run_apify_actor(
            ACTOR_TWEETS,
            {
                "twitterHandles": [handle],
                "maxItems": args.max_posts,
                "sort": "Latest",
                "start": start,
                "end": end,
            },
            timeout=600,
        )
        if items is None:
            continue
        if not items:
            print("  (no tweets returned)")
            continue

        added = 0
        for item in items:
            # Skip retweets (we want the source's own voice)
            if item.get("isRetweet") or item.get("retweetedStatus"):
                continue
            external_id = str(item.get("id") or item.get("id_str") or "")
            url = item.get("url") or item.get("twitterUrl")
            body = (item.get("text") or item.get("fullText") or "").strip()
            published_at = _parse_created_at(item.get("createdAt"))
            likes = int(item.get("likeCount") or item.get("favoriteCount") or 0)
            replies = int(item.get("replyCount") or 0)
            retweets = int(item.get("retweetCount") or 0)
            views = int(item.get("viewCount") or 0)

            if not url or not external_id:
                continue

            try:
                cur = conn.execute(
                    """INSERT OR IGNORE INTO content_items
                       (source_id, platform, external_id, url, content_type, body, published_at,
                        engagement_likes, engagement_comments, engagement_shares, engagement_views, scrape_run_id)
                       VALUES (?, 'x', ?, ?, 'post', ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        s["id"],
                        external_id,
                        url,
                        body,
                        published_at,
                        likes,
                        replies,
                        retweets,
                        views,
                        run_id,
                    ),
                )
                if cur.rowcount > 0:
                    added += 1
            except Exception as e:
                print(f"  ✗ insert failed: {e}")
        conn.commit()
        total_ingested += added
        print(f"  ✓ {added} tweets added")

    finish_scrape_run(conn, run_id, items_ingested=total_ingested)
    print(f"\nDone. {total_ingested} total tweets ingested across {len(sources)} sources.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
