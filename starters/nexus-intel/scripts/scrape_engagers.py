#!/usr/bin/env python3
"""
scrape_engagers.py — Pull LinkedIn post commenters as engagers.

Reads linkedin content_items from the DB, chunks them into batches, calls
`harvestapi/linkedin-post-comments` to fetch comments, and inserts commenters
into `engagers` + `engagements`. Run AFTER scrape_linkedin.py populates
content_items.

LinkedIn-only engager scraper. To extend to X/Twitter retweeters, adapt the
Apify actor reference and the normalize() function to the new platform.

Usage:
  python3 scripts/scrape_engagers.py                         # all linkedin content, last 30 days
  python3 scripts/scrape_engagers.py --source-id 7           # one source's content only
  python3 scripts/scrape_engagers.py --max-age-days 14       # narrower window
  python3 scripts/scrape_engagers.py --batch-size 15         # posts per Apify call
  python3 scripts/scrape_engagers.py --max-comments 30       # comments per post
  python3 scripts/scrape_engagers.py --dry-run               # plan only, no Apify spend
"""

from __future__ import annotations

import argparse
import sys

from _lib import (
    finish_scrape_run,
    get_apify_token,  # noqa: F401 — fail fast
    get_db,
    run_apify_actor,
    start_scrape_run,
)

ACTOR = "harvestapi/linkedin-post-comments"


def normalize_item(item: dict) -> dict:
    """Map one harvestapi/linkedin-post-comments result → engager shape."""
    actor = item.get("actor", {}) or {}
    profile_url = actor.get("linkedinUrl") or actor.get("profileUrl") or ""
    handle = profile_url.rstrip("/").split("/")[-1] if profile_url else ""
    # LinkedIn avatar URL — harvestapi's exact field name isn't guaranteed, so
    # we check a few likely shapes. See docs/icp-filter.md + LinkedInAvatar
    # component for how this is consumed.
    profile_image_url = (
        actor.get("pictureUrl")
        or actor.get("profilePictureUrl")
        or actor.get("profileImage")
        or actor.get("image")
        or actor.get("picture")
        or ""
    )
    return {
        "handle": handle,
        "name": actor.get("name") or "",
        "title": actor.get("position") or actor.get("headline") or "",
        "company": actor.get("company") or None,
        "followers": actor.get("followers"),
        "profile_url": profile_url,
        "profile_image_url": profile_image_url,
        "comment_text": item.get("commentary") or item.get("text") or "",
        "post_url": (
            item.get("query", {}).get("post", "")
            if isinstance(item.get("query"), dict)
            else item.get("query") or item.get("postUrl") or ""
        ),
        "engaged_at": item.get("createdAt") or item.get("postedAt") or "",
        "engagement_type": "comment",
    }


def import_batch(conn, results: list[dict], url_to_meta: dict[str, dict]) -> tuple[int, int]:
    engager_count = 0
    engagement_count = 0

    for raw in results or []:
        item = normalize_item(raw)
        handle = item["handle"]
        if not handle:
            continue

        meta = url_to_meta.get(item["post_url"], {}) if item["post_url"] else {}
        source_id = meta.get("source_id")
        content_item_id = meta.get("content_item_id")

        # Upsert engager
        row = conn.execute(
            "SELECT id FROM engagers WHERE platform = 'linkedin' AND handle = ?",
            (handle,),
        ).fetchone()

        if row:
            engager_id = row["id"]
            # Lightweight update — fill in missing fields. profile_image_url
            # uses COALESCE(NULLIF) so we don't stomp existing values with "".
            conn.execute(
                """UPDATE engagers
                   SET name = COALESCE(NULLIF(?, ''), name),
                       title = COALESCE(NULLIF(?, ''), title),
                       company = COALESCE(?, company),
                       followers = COALESCE(?, followers),
                       profile_url = COALESCE(NULLIF(?, ''), profile_url),
                       profile_image_url = COALESCE(NULLIF(?, ''), profile_image_url)
                   WHERE id = ?""",
                (item["name"], item["title"], item["company"],
                 item["followers"], item["profile_url"],
                 item["profile_image_url"], engager_id),
            )
        else:
            cur = conn.execute(
                """INSERT INTO engagers
                   (platform, handle, name, title, company, followers, profile_url, profile_image_url)
                   VALUES ('linkedin', ?, ?, ?, ?, ?, ?, ?)""",
                (handle, item["name"], item["title"], item["company"],
                 item["followers"], item["profile_url"],
                 item["profile_image_url"] or None),
            )
            engager_id = cur.lastrowid
            engager_count += 1

        # Insert engagement (UNIQUE constraint on engager_id+post_url+type handles dedup)
        try:
            conn.execute(
                """INSERT OR IGNORE INTO engagements
                   (engager_id, content_item_id, source_id, engagement_type,
                    comment_text, post_url, engaged_at)
                   VALUES (?, ?, ?, 'comment', ?, ?, ?)""",
                (engager_id, content_item_id, source_id,
                 item["comment_text"], item["post_url"], item["engaged_at"]),
            )
            if conn.total_changes > 0:
                engagement_count += 1
        except Exception as e:
            print(f"    ✗ engagement insert failed: {e}")

    conn.commit()
    return engager_count, engagement_count


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-id", type=int, help="Scrape only this source's content")
    parser.add_argument("--max-age-days", type=int, default=30,
                        help="Only scrape content newer than N days (default 30)")
    parser.add_argument("--batch-size", type=int, default=15,
                        help="Posts per Apify call (default 15)")
    parser.add_argument("--max-comments", type=int, default=30,
                        help="Max comments per post (default 30)")
    parser.add_argument("--limit", type=int, default=200,
                        help="Max content items to scrape (default 200)")
    parser.add_argument("--dry-run", action="store_true", help="Plan only, no Apify spend")
    args = parser.parse_args()

    conn = get_db()

    # Pull content_items that are LinkedIn posts, recent, with a URL
    sql = """
        SELECT ci.id as content_item_id, ci.source_id, ci.url, ci.published_at,
               s.name as source_name, s.relevance
        FROM content_items ci
        JOIN sources s ON s.id = ci.source_id
        WHERE ci.platform = 'linkedin'
          AND ci.url IS NOT NULL
          AND ci.url != ''
          AND (ci.published_at IS NULL
               OR (strftime('%s', 'now') - strftime('%s', ci.published_at)) <= ? * 86400)
    """
    params: list = [args.max_age_days]
    if args.source_id:
        sql += " AND ci.source_id = ?"
        params.append(args.source_id)
    sql += " ORDER BY ci.engagement_comments DESC, ci.published_at DESC LIMIT ?"
    params.append(args.limit)

    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    if not rows:
        print("No matching content_items to scrape.")
        return 0

    # Build url → meta map so we can attribute engagers back to source_id + content_item_id
    url_to_meta = {
        r["url"]: {
            "source_id": r["source_id"],
            "content_item_id": r["content_item_id"],
            "source_name": r["source_name"],
        }
        for r in rows
    }

    print(f"Found {len(rows)} LinkedIn posts to scrape comments from")
    print(f"  Top 5:")
    for r in rows[:5]:
        print(f"    [{r['source_name'][:30]:<30}] {r['url'][:80]}")

    if args.dry_run:
        print("\n(dry-run — no Apify calls made)")
        return 0

    get_apify_token()
    run_id = start_scrape_run(
        conn,
        name="linkedin-engagers",
        target=",".join(str(r["content_item_id"]) for r in rows[:50]),
        platforms="linkedin",
    )

    total_engagers = 0
    total_engagements = 0

    # Chunk into batches
    for i in range(0, len(rows), args.batch_size):
        batch = rows[i : i + args.batch_size]
        batch_urls = [r["url"] for r in batch]
        print(f"\n── batch {i // args.batch_size + 1} ({len(batch)} posts) ──")

        results = run_apify_actor(
            ACTOR,
            {
                "posts": batch_urls,
                "maxItems": args.max_comments,
                "scrapeReplies": True,
                "profileScraperMode": "short",
            },
            timeout=600,
        )
        if results is None:
            print("  (skipped due to error)")
            continue
        if not results:
            print("  (no comments returned)")
            continue

        eng_added, engmt_added = import_batch(conn, results, url_to_meta)
        total_engagers += eng_added
        total_engagements += engmt_added
        print(f"  ✓ {eng_added} new engagers, {engmt_added} engagements")

    finish_scrape_run(conn, run_id, items_ingested=total_engagements)
    print(
        f"\nDone. {total_engagers} new engagers, {total_engagements} engagements "
        f"across {len(rows)} posts."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
