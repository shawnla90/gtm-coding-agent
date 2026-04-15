#!/usr/bin/env python3
"""
scrape_linkedin.py — Pull recent LinkedIn posts from tracked sources.

Uses the Apify actor `harvestapi/linkedin-profile-posts` to fetch posts for each
source with platform='linkedin' and status='active'. Inserts into content_items.

Usage:
  python3 scripts/scrape_linkedin.py                       # scrape all active LinkedIn sources
  python3 scripts/scrape_linkedin.py --source-id 7          # single source
  python3 scripts/scrape_linkedin.py --relevance competitor # competitors only
  python3 scripts/scrape_linkedin.py --max-posts 30         # posts per source
  python3 scripts/scrape_linkedin.py --max-age-days 60      # drop posts older than N days (default 60)
  python3 scripts/scrape_linkedin.py --max-age-days 0       # disable age filter (not recommended)
  python3 scripts/scrape_linkedin.py --dry-run              # plan only, no Apify spend
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone

from _lib import (
    finish_scrape_run,
    get_apify_token,  # noqa: F401 — validates presence before we call apify CLI
    get_db,
    run_apify_actor,
    start_scrape_run,
)


def parse_published_at(value) -> datetime | None:
    """Normalize harvestapi's varied published_at shapes into a UTC datetime.

    harvestapi returns one of:
      - ISO string with Z ("2026-03-01T14:22:10.000Z")
      - ISO string with offset
      - Date-only string ("2026-03-01")
      - Unix timestamp (ms or s) — rare, fallback path
      - Dict: {"date": "...", "timestamp": ..., "postedAgoShort": "2d"} (already unwrapped upstream)

    Returns None when the value is missing or unparseable — the caller treats
    None as "old/suspicious" and skips at ingest when --max-age-days is active.
    """
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        # Unix timestamp: >1e12 means milliseconds
        ts = value / 1000 if value > 1e12 else value
        try:
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    if not isinstance(value, str):
        return None
    s = value.strip()
    if not s:
        return None
    # Normalize trailing Z to +00:00 for fromisoformat
    s_norm = s.replace("Z", "+00:00") if s.endswith("Z") else s
    try:
        dt = datetime.fromisoformat(s_norm)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        pass
    # Fall back to date-only (first 10 chars)
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None

ACTOR_PROFILE_POSTS = "harvestapi/linkedin-profile-posts"
ACTOR_COMPANY_POSTS = "harvestapi/linkedin-company-posts"


def is_company_source(source: dict) -> bool:
    """LinkedIn company pages (/company/<slug>) vs personal profiles (/in/<slug>).

    The most reliable signal is the URL. Competitors are always company pages, but
    thought-leader sources can be either — e.g., NAA and NMHC are associations with
    /company/ pages, while Bob Pinnegar and Ric Campo are individuals with /in/ profiles.
    Named-account contacts are always personal profiles.
    """
    url = (source.get("url") or "").lower()
    if "/company/" in url:
        return True
    if "/in/" in url:
        return False
    # Fallback: competitors without URL (shouldn't happen) assumed to be companies.
    return source.get("relevance") == "competitor"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-id", type=int)
    parser.add_argument("--relevance")
    parser.add_argument("--max-posts", type=int, default=30)
    parser.add_argument(
        "--max-age-days",
        type=int,
        default=60,
        help="Drop posts older than N days at ingest. 0 disables the filter (not recommended).",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    cutoff: datetime | None = None
    if args.max_age_days and args.max_age_days > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(days=args.max_age_days)
        print(f"Ingest filter: dropping posts published before {cutoff.date().isoformat()} ({args.max_age_days}d cutoff)")

    conn = get_db()
    conditions = ["platform = 'linkedin'", "status = 'active'", "handle IS NOT NULL"]
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
            f"SELECT id, handle, name, relevance FROM sources WHERE {where} ORDER BY relevance, tier, name",
            params,
        ).fetchall()
    ]

    if not sources:
        print("No matching LinkedIn sources found.")
        return 0

    print(f"Found {len(sources)} LinkedIn sources:")
    for s in sources:
        print(f"  [{s['id']:3}] {s['name']:40} ({s['relevance']}) — {s['handle']}")

    if args.dry_run:
        print("\n(dry-run — no Apify calls made)")
        return 0

    get_apify_token()  # fail fast if token missing
    run_id = start_scrape_run(
        conn,
        name="linkedin-posts",
        target=",".join(str(s["id"]) for s in sources),
        platforms="linkedin",
    )

    total_ingested = 0
    for s in sources:
        is_company = is_company_source(s)
        actor = ACTOR_COMPANY_POSTS if is_company else ACTOR_PROFILE_POSTS
        id_field = "companyPublicIdentifiers" if is_company else "profilePublicIdentifiers"
        source_type = "company" if is_company else "profile"
        print(f"\n── {s['name']} ({s['handle']}, {source_type}) ──")
        items = run_apify_actor(
            actor,
            {
                id_field: [s["handle"]],
                "maxItems": args.max_posts,
            },
            timeout=600,
        )
        if items is None:
            print("  (skipped due to error)")
            continue
        if not items:
            print("  (no posts returned)")
            continue

        added = 0
        skipped_old = 0
        skipped_unknown_date = 0
        # Opportunistic source avatar capture — if any scraped post item carries
        # an author picture, use it to backfill sources.profile_image_url. See
        # docs/icp-filter.md + LinkedInAvatar for consumption.
        source_image_url: str | None = None
        for item in items:
            # harvestapi/linkedin-profile-posts schema (2026-04):
            # id, linkedinUrl, content, postedAt{date,timestamp,postedAgoShort},
            # engagement{likes,comments,shares}
            external_id = str(item.get("id") or item.get("entityId") or item.get("shareUrn") or "")
            url = item.get("linkedinUrl") or item.get("url") or item.get("postUrl")
            body = (item.get("content") or item.get("text") or item.get("commentary") or "").strip()

            posted_at = item.get("postedAt") or item.get("publishedAt") or item.get("createdAt")
            if isinstance(posted_at, dict):
                published_at = posted_at.get("date") or posted_at.get("iso") or None
            else:
                published_at = posted_at

            # Age filter at ingest — defense in depth alongside the analyzer decay cap
            if cutoff is not None:
                pub_dt = parse_published_at(published_at)
                if pub_dt is None:
                    # Null/unparseable date — treat as suspicious (plan risk #2)
                    skipped_unknown_date += 1
                    continue
                if pub_dt < cutoff:
                    skipped_old += 1
                    continue

            # Opportunistic avatar scraping — author picture on the post item
            if not source_image_url:
                author = item.get("author") or item.get("actor") or {}
                if isinstance(author, dict):
                    source_image_url = (
                        author.get("pictureUrl")
                        or author.get("profilePictureUrl")
                        or author.get("profileImage")
                        or author.get("image")
                        or author.get("picture")
                        or None
                    )

            engagement = item.get("engagement") or {}
            if isinstance(engagement, dict):
                likes = int(engagement.get("likes") or 0)
                comments = int(engagement.get("comments") or 0)
                shares = int(engagement.get("shares") or 0)
                views = int(engagement.get("views") or engagement.get("impressions") or 0)
            else:
                likes = int(item.get("numLikes") or item.get("likes") or 0)
                comments = int(item.get("numComments") or item.get("comments") or 0)
                shares = int(item.get("numShares") or item.get("shares") or 0)
                views = int(item.get("numViews") or item.get("views") or 0)

            if not url or not external_id:
                continue

            try:
                conn.execute(
                    """INSERT OR IGNORE INTO content_items
                       (source_id, platform, external_id, url, content_type, body, published_at,
                        engagement_likes, engagement_comments, engagement_shares, engagement_views, scrape_run_id)
                       VALUES (?, 'linkedin', ?, ?, 'post', ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        s["id"],
                        external_id,
                        url,
                        body,
                        published_at,
                        likes,
                        comments,
                        shares,
                        views,
                        run_id,
                    ),
                )
                if conn.total_changes > 0:
                    added += 1
            except Exception as e:
                print(f"  ✗ insert failed: {e}")
        # Update source avatar if captured and not already set
        if source_image_url:
            conn.execute(
                """UPDATE sources
                   SET profile_image_url = COALESCE(profile_image_url, ?)
                   WHERE id = ?""",
                (source_image_url, s["id"]),
            )
        conn.commit()
        total_ingested += added
        skip_parts = []
        if skipped_old:
            skip_parts.append(f"{skipped_old} older than {args.max_age_days}d")
        if skipped_unknown_date:
            skip_parts.append(f"{skipped_unknown_date} without parseable date")
        skip_note = f" (skipped {', '.join(skip_parts)})" if skip_parts else ""
        print(f"  ✓ {added} posts added{skip_note}")

    finish_scrape_run(conn, run_id, items_ingested=total_ingested)
    print(f"\nDone. {total_ingested} total posts ingested across {len(sources)} sources.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
