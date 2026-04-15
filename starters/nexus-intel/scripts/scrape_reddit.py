#!/usr/bin/env python3
"""
scrape_reddit.py — Pull recent threads from tracked subreddits.

Uses the Apify actor `trudax/reddit-scraper-lite` to fetch top threads from
each source with platform='reddit' and status='active'. Inserts into
reddit_threads.

Usage:
  python3 scripts/scrape_reddit.py                      # all active subreddits
  python3 scripts/scrape_reddit.py --subreddit LocalLLaMA  # single subreddit
  python3 scripts/scrape_reddit.py --window week        # day|week|month|year|all
  python3 scripts/scrape_reddit.py --max-items 50       # per subreddit
  python3 scripts/scrape_reddit.py --dry-run            # plan only
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime

from _lib import (
    finish_scrape_run,
    get_apify_token,  # noqa: F401
    get_db,
    run_apify_actor,
    start_scrape_run,
)

ACTOR_REDDIT = "trudax/reddit-scraper-lite"
VALID_WINDOWS = {"hour", "day", "week", "month", "year", "all"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--subreddit")
    parser.add_argument("--window", default="week", choices=sorted(VALID_WINDOWS))
    parser.add_argument("--sort", default="top", choices=["top", "new", "hot", "rising"])
    parser.add_argument("--max-items", type=int, default=40)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    conn = get_db()
    conditions = ["platform = 'reddit'", "status = 'active'", "handle IS NOT NULL"]
    params: list = []
    if args.subreddit:
        conditions.append("handle = ?")
        params.append(args.subreddit)
    where = " AND ".join(conditions)

    subs = [
        dict(r)
        for r in conn.execute(
            f"SELECT id, handle, name FROM sources WHERE {where} ORDER BY handle",
            params,
        ).fetchall()
    ]

    if not subs:
        print("No matching subreddit sources found.")
        return 0

    print(f"Found {len(subs)} subreddits:")
    for s in subs:
        print(f"  [{s['id']:3}] r/{s['handle']}")

    if args.dry_run:
        print("\n(dry-run — no Apify calls made)")
        return 0

    get_apify_token()
    run_id = start_scrape_run(
        conn,
        name="reddit-threads",
        target=",".join(s["handle"] for s in subs),
        platforms="reddit",
    )

    total_ingested = 0
    for s in subs:
        sub = s["handle"]
        url = f"https://www.reddit.com/r/{sub}/{args.sort}/?t={args.window}"
        print(f"\n── r/{sub} ({args.sort}, t={args.window}) ──")
        items = run_apify_actor(
            ACTOR_REDDIT,
            {
                "startUrls": [{"url": url}],
                "maxItems": args.max_items,
                "scrollTimeout": 40,
                "includeNSFW": False,
                "skipComments": True,
                "searchPosts": True,
                "searchComments": False,
                "searchCommunities": False,
                "searchUsers": False,
            },
            timeout=600,
        )
        if items is None:
            continue
        if not items:
            print("  (no threads returned)")
            continue

        added = 0
        for item in items:
            # Filter to post rows only; the actor also emits community + user metadata rows
            data_type = str(item.get("dataType") or "").lower()
            if data_type not in ("post", "", "thread"):
                continue
            external_id = str(
                item.get("id") or item.get("postId") or item.get("parsedId") or ""
            )
            title = (item.get("title") or "").strip()
            if not title:
                continue
            thread_url = (
                item.get("url")
                or item.get("postUrl")
                or (f"https://www.reddit.com{item.get('permalink')}" if item.get("permalink") else "")
            )
            permalink = item.get("permalink")
            author = item.get("username") or item.get("author")
            body = (item.get("body") or item.get("text") or "").strip()
            score = int(item.get("upVotes") or item.get("score") or 0)
            num_comments = int(item.get("numberOfComments") or item.get("numComments") or 0)
            created = item.get("createdAt") or item.get("created") or item.get("createdAtFormatted")
            if isinstance(created, (int, float)):
                created = datetime.utcfromtimestamp(created).strftime("%Y-%m-%dT%H:%M:%S+00:00")

            thread_eid = external_id or f"{sub}-{title[:60]}"
            try:
                cur = conn.execute(
                    """INSERT OR IGNORE INTO reddit_threads
                       (external_id, subreddit, title, url, permalink, author, body,
                        score, num_comments, created_utc, scrape_run_id)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        thread_eid,
                        sub,
                        title,
                        thread_url or permalink or "",
                        permalink,
                        author,
                        body,
                        score,
                        num_comments,
                        created,
                        run_id,
                    ),
                )
                if cur.rowcount > 0:
                    added += 1
                # Also insert into content_items so analyze_content.py picks it up.
                # This is how Reddit threads flow into the signal extraction pipeline.
                # Combine title + body so the analyzer has the full post context.
                composite_body = (title + "\n\n" + body).strip() if body else title
                conn.execute(
                    """INSERT OR IGNORE INTO content_items
                       (source_id, platform, external_id, url, content_type,
                        title, body, published_at,
                        engagement_likes, engagement_comments, engagement_shares, engagement_views,
                        scrape_run_id)
                       VALUES (?, 'reddit', ?, ?, 'thread', ?, ?, ?, ?, ?, 0, 0, ?)""",
                    (
                        s["id"],
                        f"reddit-{thread_eid}",
                        thread_url or permalink or "",
                        title,
                        composite_body,
                        created,
                        score,
                        num_comments,
                        run_id,
                    ),
                )
            except Exception as e:
                print(f"  ✗ insert failed: {e}")
        conn.commit()
        total_ingested += added
        print(f"  ✓ {added} threads added")

    finish_scrape_run(conn, run_id, items_ingested=total_ingested)
    print(f"\nDone. {total_ingested} total threads ingested across {len(subs)} subreddits.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
