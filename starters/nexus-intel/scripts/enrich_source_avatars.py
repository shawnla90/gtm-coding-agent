#!/usr/bin/env python3
"""Backfill profile_image_url for sources (companies + subreddits + targets).

Strategy — $0 per-platform fallback chain using stdlib HTTP only:
- reddit:   GET https://www.reddit.com/r/{handle}/about.json → community_icon
- linkedin: GET company page, extract <meta property="og:image">, icon.horse fallback
- other:    hardcoded handle → domain map feeding icon.horse

Logo API: icon.horse/icon/{domain} — free, high-quality, no key required.
Clearbit's logo API was deprecated; do not restore it.

No Apify. No new deps. Safe to re-run — only touches rows where
profile_image_url IS NULL or empty.

Usage:
    python3 scripts/enrich_source_avatars.py            # dry-run (default)
    python3 scripts/enrich_source_avatars.py --apply    # commit writes
    python3 scripts/enrich_source_avatars.py --limit 10 # test smaller batch
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _lib import get_db  # noqa: E402


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
REQ_TIMEOUT = 15
RATE_LIMIT_S = 1.5   # polite delay between LinkedIn fetches

# LinkedIn's known "missing logo" placeholder — reject if og:image contains this
LINKEDIN_PLACEHOLDER_MARKERS = ("ghost-company", "ghost_company", "ghost%20company")

# "Other" placeholder sources — handle → canonical domain for Clearbit lookup
OTHER_HANDLE_TO_DOMAIN = {
    "apollo-target":   "apollo.io",
    "zoominfo-target": "zoominfo.com",
    "clay-target":     "clay.com",
    "outreach-target": "outreach.io",
    "hubspot-target":  "hubspot.com",
    "gong-target":     "gong.io",
}

# Known LinkedIn handle → domain mappings (Clearbit fallback when og:image fails)
LINKEDIN_HANDLE_TO_DOMAIN = {
    "apolloio":       "apollo.io",
    "zoominfo":       "zoominfo.com",
    "clay-hq":        "clay.com",
    "seamlessai":     "seamless.ai",
    "cognism":        "cognism.com",
    "clearbit":       "clearbit.com",
    "leadiq-inc":     "leadiq.com",
    "rocketreach.co": "rocketreach.co",
    "lushadata":      "lusha.com",
    "orumhq":         "orum.com",
    "6sense":         "6sense.com",
    "gongio":         "gong.io",
    "outreach-io":    "outreach.io",
    "salesforce":     "salesforce.com",
    "hubspot":        "hubspot.com",
    "salesloft":      "salesloft.com",
}


def _http_get(url: str, accept: str = "text/html,*/*") -> str:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": accept},
    )
    with urllib.request.urlopen(req, timeout=REQ_TIMEOUT) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def fetch_reddit_icon(handle: str) -> str | None:
    """Return subreddit community_icon or icon_img URL, or None."""
    url = f"https://www.reddit.com/r/{handle}/about.json"
    try:
        body = _http_get(url, accept="application/json")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        print(f"    ! reddit fetch failed: {e}")
        return None
    try:
        data = json.loads(body).get("data", {})
    except json.JSONDecodeError:
        return None
    # community_icon is the higher-res square logo; icon_img is the legacy snoo-style
    icon = data.get("community_icon") or data.get("icon_img")
    if not icon:
        return None
    # Reddit appends signing params after a ?. Stripping them keeps the static CDN URL.
    icon = icon.split("?")[0]
    # HTML-entity cleanup (reddit returns &amp; in JSON sometimes)
    icon = icon.replace("&amp;", "&")
    return icon if icon.startswith("http") else None


_OG_IMAGE_RE = re.compile(
    r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)


def fetch_linkedin_og_image(url: str) -> str | None:
    """Return og:image URL from a LinkedIn company page, or None if placeholder/blocked."""
    try:
        html = _http_get(url)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        print(f"    ! linkedin fetch failed: {e}")
        return None
    match = _OG_IMAGE_RE.search(html)
    if not match:
        return None
    logo = match.group(1).replace("&amp;", "&")
    if any(marker in logo for marker in LINKEDIN_PLACEHOLDER_MARKERS):
        return None
    return logo if logo.startswith("http") else None


def domain_logo_url(domain: str) -> str:
    """icon.horse — free, higher-quality than Google favicons. No key required."""
    return f"https://icon.horse/icon/{domain}"


def resolve_logo(platform: str, handle: str, url: str | None) -> tuple[str | None, str]:
    """Return (logo_url, method_name)."""
    if platform == "reddit":
        icon = fetch_reddit_icon(handle)
        return (icon, "reddit-api") if icon else (None, "reddit-api-miss")

    if platform == "linkedin" and url:
        logo = fetch_linkedin_og_image(url)
        if logo:
            return logo, "linkedin-og"
        # Fallback: domain-logo API by known handle → domain
        domain = LINKEDIN_HANDLE_TO_DOMAIN.get(handle)
        if domain:
            return domain_logo_url(domain), "linkedin-icon-horse"
        return None, "linkedin-no-mapping"

    if platform == "other":
        domain = OTHER_HANDLE_TO_DOMAIN.get(handle)
        if domain:
            return domain_logo_url(domain), "other-icon-horse"
        return None, "other-no-mapping"

    return None, "unknown-platform"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="Actually write to the DB (default: dry-run)")
    parser.add_argument("--limit", type=int, default=100,
                        help="Max sources to process (default 100)")
    args = parser.parse_args()

    conn = get_db()
    rows = conn.execute(
        """SELECT id, platform, handle, url
             FROM sources
            WHERE profile_image_url IS NULL OR profile_image_url = ''
            ORDER BY platform, id
            LIMIT ?""",
        (args.limit,),
    ).fetchall()

    if not rows:
        print("All sources already have avatars — nothing to do.")
        conn.close()
        return 0

    print(f"Processing {len(rows)} sources (mode: {'APPLY' if args.apply else 'DRY-RUN'})")
    print(f"{'─' * 72}")

    wins: list[tuple[str, str, str]] = []
    losses: list[tuple[str, str, str]] = []

    for row in rows:
        sid = row["id"]
        platform = row["platform"]
        handle = row["handle"]
        url = row["url"] or None

        logo, method = resolve_logo(platform, handle, url)

        if logo:
            print(f"  ✓ [{platform:8s}] {handle:30s} {method:22s} → {logo[:60]}")
            if args.apply:
                conn.execute(
                    "UPDATE sources SET profile_image_url = ?, "
                    "updated_at = datetime('now') WHERE id = ?",
                    (logo, sid),
                )
            wins.append((platform, handle, method))
        else:
            print(f"  ✗ [{platform:8s}] {handle:30s} {method}")
            losses.append((platform, handle, method))

        # Polite rate-limit only for platforms that hit a real origin per call
        if platform in ("reddit", "linkedin"):
            time.sleep(RATE_LIMIT_S)

    if args.apply:
        conn.commit()
    conn.close()

    print(f"{'─' * 72}")
    print(f"Done — {len(wins)} enriched, {len(losses)} failed")

    if losses:
        print("\nFailures by method:")
        by_method: dict[str, int] = {}
        for _, _, m in losses:
            by_method[m] = by_method.get(m, 0) + 1
        for method, count in sorted(by_method.items(), key=lambda x: -x[1]):
            print(f"  {count:3d}  {method}")

    if not args.apply:
        print("\nDry-run only. Re-run with --apply to commit writes.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
