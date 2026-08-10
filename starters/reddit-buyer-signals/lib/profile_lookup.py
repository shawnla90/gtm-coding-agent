#!/usr/bin/env python3
"""profile_lookup.py - waterfall lookup for Reddit user identity signals.

Checks whether a Reddit username's *public* presence discloses a company, website, or social
profile. This is identity the author chose to publish — not de-anonymization. The waterfall
tries cheap/fast tiers first and stops at the first hit:

  Tier 1  Reddit JSON API  (/user/{name}/about.json) — free, fast, but 403 since mid-2025
  Tier 2  Exa search       ("{username}" site:reddit.com) — paid (~$0.01), finds linked presence
  Tier 3  DuckDuckGo HTML  (free, no key) — coarser but catches personal sites and LinkedIn
  Tier 4  Playwright       (browser scrape) — reads the rendered profile page, heavy fallback

Usage:
  from lib.profile_lookup import lookup_profile
  result = lookup_profile("Squared_Bear")
  # -> {disclosed: bool, domains: [...], links: [...], bio: str|None, source: str, signal: str}

  # CLI: test a username through all tiers
  python3 -m lib.profile_lookup Squared_Bear TechnicalGirlyPop --verbose
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from urllib.parse import quote

try:
    import requests
except ImportError:
    requests = None

DOMAIN_RE = re.compile(r"\b([a-z0-9][a-z0-9-]{1,63}\.(?:com|io|ai|co|team|app|dev|net|org|xyz|me|so|to))\b", re.I)
IGNORE_DOMAINS = {
    "reddit.com", "redd.it", "redditstatic.com", "redditmedia.com", "reddithelp.com",
    "google.com", "youtube.com", "github.com", "gitlab.com",
    "linkedin.com", "twitter.com", "x.com", "facebook.com", "instagram.com",
    "notion.so", "medium.com", "substack.com", "loom.com",
    "imgur.com", "gfycat.com", "giphy.com", "tenor.com",
    "wikipedia.org", "archive.org", "web.archive.org",
    "duckduckgo.com", "bing.com", "exa.ai", "rapidapi.com",
    # Reddit user lookup/analysis tools — show up in search results about usernames
    "redditorhistory.com", "deletedby.com", "nicheprowler.com", "lullar.com",
    "redditcommentsearch.com", "reddituserdetective.com", "think-pol.com",
    "footprintiq.app", "redditmetis.com", "camas.unddit.com", "unddit.com",
    "pushshift.io", "reveddit.com", "removeddit.com", "redective.com",
    "snoopsnoo.com", "redditinsight.com", "karmalb.com",
}
SOCIAL_DOMAINS = {"linkedin.com", "twitter.com", "x.com", "github.com"}

EXA_MAX_QUERIES = int(os.environ.get("EXA_PROFILE_MAX", "5"))
VERBOSE = False


def _get_secret(key: str) -> str:
    val = os.environ.get(key, "").strip()
    if val:
        return val
    try:
        import sqlite3
        db = os.path.expanduser("~/.niobot/data/niobot.db")
        if os.path.exists(db):
            row = sqlite3.connect(db).execute(
                "SELECT value FROM secrets WHERE key=?", (key,)).fetchone()
            if row:
                return row[0].strip()
    except Exception:
        pass
    env_file = os.path.expanduser(f"~/.env.{key.lower().replace('_api_key', '').replace('_key', '')}")
    if os.path.exists(env_file):
        for line in open(env_file):
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1].strip()
    return ""


def _extract_domains(text: str) -> list[str]:
    found = []
    seen = set()
    for m in DOMAIN_RE.finditer(text):
        dom = m.group(1).lower()
        root = ".".join(dom.split(".")[-2:])
        if root not in IGNORE_DOMAINS and root not in seen:
            seen.add(root)
            found.append(dom)
    return found


def _extract_links(text: str) -> list[str]:
    urls = re.findall(r"https?://[^\s\"'<>\)]+", text)
    out = []
    for u in urls:
        u = u.rstrip(".,;:!?)")
        try:
            from urllib.parse import urlparse
            host = urlparse(u).hostname or ""
            root = ".".join(host.split(".")[-2:])
            if root not in IGNORE_DOMAINS or root in SOCIAL_DOMAINS:
                out.append(u)
        except Exception:
            pass
    return out


def _log(msg: str):
    if VERBOSE:
        print(f"  [profile] {msg}", file=sys.stderr)


# ── Tier 1: Reddit JSON API ──────────────────────────────────────────────────
def _reddit_json(username: str) -> dict | None:
    """Try Reddit's public JSON API. Returns 403 since mid-2025 but costs nothing to try."""
    if not requests:
        return None
    try:
        r = requests.get(
            f"https://www.reddit.com/user/{quote(username)}/about.json",
            headers={"User-Agent": "script:gtm-profile-lookup:v1.0 (by /u/shawnla90)"},
            timeout=10)
        if r.status_code != 200:
            _log(f"reddit JSON: HTTP {r.status_code}")
            return None
        data = r.json().get("data", {})
        bio = data.get("subreddit", {}).get("public_description", "") or ""
        title = data.get("subreddit", {}).get("title", "") or ""
        text = f"{bio} {title}"
        domains = _extract_domains(text)
        links = _extract_links(text)
        if domains or links:
            return {
                "disclosed": True,
                "domains": domains,
                "links": links,
                "bio": bio.strip() or None,
                "source": "reddit_json",
                "signal": f"company {'domain' if domains else 'link'} in Reddit profile",
            }
        _log(f"reddit JSON: profile found but no company signals in bio")
        return None
    except Exception as e:
        _log(f"reddit JSON error: {e}")
        return None


# ── Tier 2: Exa search ───────────────────────────────────────────────────────
def _exa_search(username: str) -> dict | None:
    """Search Exa for web presence tied to this Reddit username."""
    key = _get_secret("EXA_API_KEY")
    if not key or not requests:
        _log("exa: no API key or requests not installed")
        return None
    try:
        r = requests.post(
            "https://api.exa.ai/search",
            headers={"x-api-key": key, "Content-Type": "application/json"},
            json={
                "query": f"\"{username}\" founder OR CEO OR engineer OR \"works at\" OR company",
                "numResults": 5,
                "type": "keyword",
                "contents": {"text": {"maxCharacters": 800}},
            },
            timeout=30)
        if r.status_code != 200:
            _log(f"exa: HTTP {r.status_code}")
            return None
        results = r.json().get("results", [])
        if not results:
            _log("exa: no results")
            return None
        all_domains = []
        all_links = []
        bio_snippets = []
        for res in results:
            url = res.get("url", "")
            text = res.get("text", "")
            title = res.get("title", "")
            combined = f"{url} {text} {title}"
            all_domains.extend(_extract_domains(combined))
            all_links.extend(_extract_links(combined))
            if text.strip():
                bio_snippets.append(text.strip()[:200])
        all_domains = list(dict.fromkeys(all_domains))
        all_links = list(dict.fromkeys(all_links))
        if all_domains:
            return {
                "disclosed": True,
                "domains": all_domains,
                "links": all_links,
                "bio": " | ".join(bio_snippets[:2]) if bio_snippets else None,
                "source": "exa",
                "signal": f"company domain found via web search: {', '.join(all_domains[:3])}",
            }
        if all_links:
            return {
                "disclosed": True,
                "domains": [],
                "links": all_links,
                "bio": " | ".join(bio_snippets[:2]) if bio_snippets else None,
                "source": "exa",
                "signal": f"social/professional profile linked to username",
            }
        _log("exa: results found but no company signals")
        return None
    except Exception as e:
        _log(f"exa error: {e}")
        return None


# ── Tier 3: DuckDuckGo HTML search ───────────────────────────────────────────
def _ddg_search(username: str) -> dict | None:
    """Free web search via DuckDuckGo HTML endpoint. No API key needed.

    Searches for the username to find their presence outside Reddit — personal sites,
    LinkedIn profiles, company pages. Filters out Reddit analysis tools that pollute results.
    """
    if not requests:
        return None
    # Search specifically for their identity, not for Reddit lookup tools
    queries = [
        f'"{username}" founder OR ceo OR engineer OR "works at"',
        f'"{username}" site:linkedin.com OR site:twitter.com',
    ]
    all_domains = []
    all_links = []
    bio_text = None

    for query in queries:
        try:
            r = requests.get(
                f"https://html.duckduckgo.com/html/?q={quote(query)}",
                headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"},
                timeout=15)
            if r.status_code != 200:
                _log(f"ddg: HTTP {r.status_code} for query: {query[:40]}")
                continue
            text = r.text
            snippets = re.findall(r'class="result__snippet">(.*?)</a>', text, re.S)
            urls_raw = re.findall(r'class="result__url"[^>]*>(.*?)</a>', text, re.S)
            combined = " ".join(re.sub(r"<[^>]+>", " ", s) for s in snippets)
            combined += " " + " ".join(re.sub(r"<[^>]+>", " ", u) for u in urls_raw)
            all_domains.extend(_extract_domains(combined))
            all_links.extend(_extract_links(combined))
            if not bio_text and snippets:
                bio_text = re.sub(r"<[^>]+>", "", snippets[0])[:200]
            time.sleep(0.5)
        except Exception as e:
            _log(f"ddg error on query '{query[:30]}': {e}")
            continue

    all_domains = list(dict.fromkeys(all_domains))
    all_links = list(dict.fromkeys(all_links))

    if all_domains:
        return {
            "disclosed": True,
            "domains": all_domains[:5],
            "links": all_links[:5],
            "bio": bio_text,
            "source": "duckduckgo",
            "signal": f"company domain found via DuckDuckGo: {', '.join(all_domains[:3])}",
        }
    _log("ddg: no company domains found in search results")
    return None


# ── Tier 4: Playwright browser scrape ─────────────────────────────────────────
def _playwright_scrape(username: str) -> dict | None:
    """Scrape the Reddit profile page via an existing Chrome session (CDP) or headless fallback.

    Reddit blocks headless browsers with "blocked by network security." To use this tier,
    launch Chrome with remote debugging:
      /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222

    The function tries CDP first (port 9222), then headless as a fallback (usually blocked).
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        _log("playwright not installed")
        return None

    def _scrape_page(page) -> dict | None:
        page.goto(f"https://www.reddit.com/user/{username}/", timeout=15000)
        page.wait_for_timeout(3000)

        # Check for bot block
        body_text = page.inner_text("body") or ""
        if "blocked by network security" in body_text.lower():
            _log("playwright: blocked by Reddit bot detection")
            return None

        profile_text = ""
        for selector in [
            '[data-testid="profile-description"]',
            '[id="profile--id-card--profile-description"]',
            'div[class*="profileDescription"]',
            'shreddit-profile-header',
        ]:
            el = page.query_selector(selector)
            if el:
                profile_text += " " + (el.inner_text() or "")

        social_links = []
        for selector in [
            'a[data-testid="profile-social-link"]',
            'a[href*="linktr.ee"]',
            'a[class*="socialLink"]',
        ]:
            for el in page.query_selector_all(selector):
                href = el.get_attribute("href")
                if href and not any(ig in href for ig in IGNORE_DOMAINS):
                    social_links.append(href)

        content = page.content()
        bio_match = re.search(r'"public_description"\s*:\s*"([^"]*)"', content)
        if bio_match:
            profile_text += " " + bio_match.group(1)

        profile_text = profile_text.strip()
        combined = profile_text + " " + " ".join(social_links)
        domains = _extract_domains(combined)
        links = _extract_links(combined) + social_links
        links = list(dict.fromkeys(links))

        if domains or links:
            return {
                "disclosed": True,
                "domains": domains[:5],
                "links": links[:10],
                "bio": profile_text[:300] if profile_text else None,
                "source": "playwright",
                "signal": f"identity in rendered Reddit profile: {', '.join(domains[:3]) if domains else 'social links found'}",
            }
        _log(f"playwright: bio={bool(profile_text)}, no company signals")
        return None

    try:
        with sync_playwright() as p:
            # Tier 4a: try existing Chrome session via CDP
            try:
                browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
                _log("playwright: connected to existing Chrome via CDP")
                ctx = browser.contexts[0] if browser.contexts else browser.new_context()
                page = ctx.new_page()
                result = _scrape_page(page)
                page.close()
                browser.close()
                if result:
                    return result
            except Exception as e:
                _log(f"playwright CDP: {e}")

            # Tier 4b: headless fallback (usually blocked by Reddit)
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            result = _scrape_page(page)
            browser.close()
            return result
    except Exception as e:
        _log(f"playwright error: {e}")
        return None


# ── Public API ────────────────────────────────────────────────────────────────
def lookup_profile(username: str, tiers: list[str] | None = None) -> dict:
    """Run the waterfall and return the first tier that finds identity signals.

    Args:
        username: Reddit username (without u/ prefix)
        tiers: optional list of tier names to try (default: all in order)

    Returns:
        dict with keys: disclosed, domains, links, bio, source, signal
    """
    username = username.lstrip("u/").strip()
    if not username:
        return _empty("empty username")

    tier_map = {
        "reddit_json": _reddit_json,
        "exa": _exa_search,
        "duckduckgo": _ddg_search,
        "playwright": _playwright_scrape,
    }
    run_tiers = tiers or ["reddit_json", "exa", "duckduckgo", "playwright"]

    for tier_name in run_tiers:
        fn = tier_map.get(tier_name)
        if not fn:
            continue
        _log(f"trying tier: {tier_name}")
        result = fn(username)
        if result and (result.get("domains") or result.get("links")):
            _log(f"hit on tier {tier_name}: {result.get('domains', [])}")
            return result
        time.sleep(0.3)

    return _empty(f"no identity signals found across {len(run_tiers)} tiers")


def _empty(reason: str) -> dict:
    return {
        "disclosed": False,
        "domains": [],
        "links": [],
        "bio": None,
        "source": "none",
        "signal": reason,
    }


# ── CLI ───────────────────────────────────────────────────────────────────────
def main():
    import argparse
    ap = argparse.ArgumentParser(description="Look up Reddit user identity signals")
    ap.add_argument("usernames", nargs="+", help="Reddit usernames to look up")
    ap.add_argument("--verbose", "-v", action="store_true")
    ap.add_argument("--tier", choices=["reddit_json", "exa", "duckduckgo", "playwright"],
                    help="test a single tier only")
    ap.add_argument("--json", action="store_true", help="output as JSON")
    args = ap.parse_args()

    global VERBOSE
    VERBOSE = args.verbose

    tiers = [args.tier] if args.tier else None
    results = {}

    for username in args.usernames:
        print(f"\n{'='*60}")
        print(f"  {username}")
        print(f"{'='*60}")
        result = lookup_profile(username, tiers=tiers)
        results[username] = result

        if args.json:
            continue

        if result["disclosed"]:
            print(f"  DISCLOSED via {result['source']}")
            if result["domains"]:
                print(f"  domains: {', '.join(result['domains'])}")
            if result["links"]:
                print(f"  links: {', '.join(result['links'][:5])}")
            if result["bio"]:
                print(f"  bio: {result['bio'][:200]}")
            print(f"  signal: {result['signal']}")
        else:
            print(f"  NOT DISCLOSED — {result['signal']}")

    if args.json:
        import json
        print(json.dumps(results, indent=2, ensure_ascii=False))

    disclosed = sum(1 for r in results.values() if r["disclosed"])
    print(f"\n--- {disclosed}/{len(results)} disclosed ---")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
