#!/usr/bin/env python3
"""profile_lookup.py - waterfall lookup for Reddit user identity signals.

Checks whether a Reddit username's *public* presence contains a direct company disclosure or a
search-only candidate. The waterfall starts with the person's own Reddit profile. Only evidence
published on that profile is direct disclosure; web-search matches always require human review.

  Tier 1  Reddit profile   (/user/{name}/about.json) — direct disclosure when available
  Tier 2  Exa search       ("{username}" founder OR CEO) — manual-review candidates only
  Tier 3  DuckDuckGo HTML  (free, no key) — manual-review candidates only
  Tier 4  Playwright       (browser scrape) — direct evidence from the rendered Reddit profile

Usage:
  from lib.profile_lookup import lookup_profile
  result = lookup_profile("Squared_Bear")
  # -> {review_verdict, enrichment_eligibility, evidence, domains, links, ...}

  # CLI: test a username through all tiers
  python3 -m lib.profile_lookup Squared_Bear TechnicalGirlyPop --verbose
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from html import unescape
from urllib.parse import parse_qs, quote, unquote, urlparse

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
    "redditorhistory.com", "deletedby.com", "nicheprowler.com", "lullar.com",
    "redditcommentsearch.com", "reddituserdetective.com", "think-pol.com",
    "footprintiq.app", "redditmetis.com", "camas.unddit.com", "unddit.com",
    "pushshift.io", "reveddit.com", "removeddit.com", "redective.com",
    "snoopsnoo.com", "redditinsight.com", "karmalb.com",
}
SOCIAL_DOMAINS = {"linkedin.com", "twitter.com", "x.com", "github.com"}

EXA_MAX_QUERIES = int(os.environ.get("EXA_PROFILE_MAX", "5"))
VERBOSE = False

DIRECT_DISCLOSURE = "direct_disclosure"
PLAUSIBLE_CANDIDATE = "plausible_candidate"
NO_PUBLIC_EVIDENCE = "no_public_evidence"
LOOKUP_ERROR = "lookup_error"


def _result(
    verdict: str,
    *,
    source: str,
    signal: str,
    domains: list[str] | None = None,
    links: list[str] | None = None,
    bio: str | None = None,
    evidence: list[dict] | None = None,
    tier_state: str = "hit",
    errors: list[str] | None = None,
) -> dict:
    """Build the public lookup contract.

    `disclosed` remains for backward compatibility, but is true only for an
    exact disclosure on the author's own Reddit profile. Search results are
    candidates and can never become enrichment-eligible without human review.
    """
    domains = domains or []
    links = links or []
    lookup_status = {
        DIRECT_DISCLOSURE: "self_disclosed",
        PLAUSIBLE_CANDIDATE: "candidate_found",
        NO_PUBLIC_EVIDENCE: "no_links_found",
        LOOKUP_ERROR: "lookup_error",
    }[verdict]
    eligibility = (
        "eligible_direct_disclosure"
        if verdict == DIRECT_DISCLOSURE and bool(domains)
        else "manual_review"
        if verdict == PLAUSIBLE_CANDIDATE or (verdict == DIRECT_DISCLOSURE and not domains)
        else "not_eligible"
    )
    return {
        "disclosed": verdict == DIRECT_DISCLOSURE,
        "lookup_status": lookup_status,
        "review_verdict": verdict,
        "enrichment_eligibility": eligibility,
        "domains": domains,
        "links": links,
        "bio": bio,
        "source": source,
        "signal": signal,
        "evidence": evidence or [],
        "tier_state": tier_state,
        "errors": errors or [],
    }


def _no_evidence(source: str, signal: str) -> dict:
    return _result(
        NO_PUBLIC_EVIDENCE,
        source=source,
        signal=signal,
        tier_state="no_evidence",
    )


def _lookup_error(source: str, signal: str) -> dict:
    return _result(
        LOOKUP_ERROR,
        source=source,
        signal=signal,
        tier_state="error",
        errors=[signal],
    )


def _get_secret(key: str) -> str:
    """Read provider credentials from the process environment only.

    The public engine must not assume a private workstation database or guess
    provider-specific secret files. Callers remain responsible for injecting
    the requested key into the environment.
    """
    return os.environ.get(key, "").strip()


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


# ── Tier 1: Reddit profile ─────────────────────────────────────────────────
def _reddit_profile(username: str) -> dict | None:
    """Read the author's own Reddit profile, the only direct-disclosure tier."""
    profile_url = f"https://www.reddit.com/user/{quote(username)}/"
    if not requests:
        return _lookup_error("reddit_json", "requests is not installed")
    try:
        r = requests.get(
            f"https://www.reddit.com/user/{quote(username)}/about.json",
            headers={"User-Agent": "script:clearbox-profile-lookup:v1.0"},
            timeout=10)
        if r.status_code == 404:
            return _no_evidence("reddit_json", "Reddit profile not found")
        if r.status_code != 200:
            _log(f"reddit profile: HTTP {r.status_code}")
            return _lookup_error("reddit_json", f"Reddit profile returned HTTP {r.status_code}")
        data = r.json().get("data", {})
        bio = data.get("subreddit", {}).get("public_description", "") or ""
        title = data.get("subreddit", {}).get("title", "") or ""
        text = f"{bio} {title}"
        domains = _extract_domains(text)
        links = _extract_links(text)
        if domains:
            return _result(
                DIRECT_DISCLOSURE,
                source="reddit_json",
                signal="author published a company domain on their Reddit profile",
                domains=domains,
                links=links,
                bio=bio.strip() or None,
                evidence=[{
                    "url": profile_url,
                    "kind": "reddit_profile",
                    "excerpt": text.strip()[:300],
                }],
            )
        if links:
            return _result(
                PLAUSIBLE_CANDIDATE,
                source="reddit_json",
                signal="author published a professional link but no company domain; human verification required",
                links=links,
                bio=bio.strip() or None,
                evidence=[{
                    "url": profile_url,
                    "kind": "reddit_profile_link_candidate",
                    "excerpt": text.strip()[:300],
                }],
            )
        _log("reddit profile: found but no company signals in bio")
        return _no_evidence("reddit_json", "Reddit profile found with no company signals")
    except Exception as e:
        _log(f"reddit profile error: {e}")
        return _lookup_error("reddit_json", f"{type(e).__name__}: {e}")


# ── Tier 2: Exa search ───────────────────────────────────────────────────────
def _exa_search(username: str) -> dict | None:
    """Search for candidates tied to a username. Search can never prove disclosure."""
    key = _get_secret("EXA_API_KEY")
    if not requests:
        return _lookup_error("exa", "requests is not installed")
    if not key:
        _log("exa: no API key")
        return _lookup_error("exa", "EXA_API_KEY is not configured")
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
            return _lookup_error("exa", f"Exa returned HTTP {r.status_code}")
        results = r.json().get("results", [])
        if not results:
            _log("exa: no results")
            return _no_evidence("exa", "Exa returned no matching results")
        all_domains = []
        all_links = []
        bio_snippets = []
        evidence = []
        for res in results:
            url = res.get("url", "")
            text = res.get("text", "")
            title = res.get("title", "")
            combined = f"{url} {text} {title}"
            if username.casefold() not in combined.casefold():
                continue
            all_domains.extend(_extract_domains(combined))
            all_links.extend(_extract_links(combined))
            if text.strip():
                bio_snippets.append(text.strip()[:200])
            if url:
                evidence.append({
                    "url": url,
                    "kind": "web_search_candidate",
                    "excerpt": f"{title} {text}".strip()[:300],
                })
        all_domains = list(dict.fromkeys(all_domains))
        all_links = list(dict.fromkeys(all_links))
        if all_domains or all_links:
            return _result(
                PLAUSIBLE_CANDIDATE,
                source="exa",
                signal="web search found a possible company or professional profile; human verification required",
                domains=all_domains,
                links=all_links,
                bio=" | ".join(bio_snippets[:2]) if bio_snippets else None,
                evidence=evidence,
            )
        _log("exa: results found but no company signals")
        return _no_evidence("exa", "Exa found no exact-username result with company signals")
    except Exception as e:
        _log(f"exa error: {e}")
        return _lookup_error("exa", f"{type(e).__name__}: {e}")


# ── Tier 3: DuckDuckGo HTML search ──────────────────────────────────────────
def _ddg_search(username: str) -> dict | None:
    """Free candidate search via DuckDuckGo. Results always require review."""
    if not requests:
        return _lookup_error("duckduckgo", "requests is not installed")
    queries = [
        f'"{username}" founder OR ceo OR engineer OR "works at"',
        f'"{username}" site:linkedin.com OR site:twitter.com',
    ]
    all_domains = []
    all_links = []
    bio_text = None
    evidence = []
    completed_queries = 0
    errors = []

    def _result_url(href: str) -> str:
        href = unescape(href)
        parsed = urlparse(href)
        if "duckduckgo.com" in (parsed.hostname or ""):
            target = parse_qs(parsed.query).get("uddg", [""])[0]
            if target:
                return unquote(target)
        return href

    for query in queries:
        try:
            r = requests.get(
                f"https://html.duckduckgo.com/html/?q={quote(query)}",
                headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"},
                timeout=15)
            if r.status_code != 200:
                _log(f"ddg: HTTP {r.status_code} for query: {query[:40]}")
                errors.append(f"HTTP {r.status_code}")
                continue
            completed_queries += 1
            text = r.text
            snippets = re.findall(r'class="result__snippet">(.*?)</a>', text, re.S)
            anchors = re.findall(
                r'<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
                text,
                re.S,
            )
            if not anchors:
                anchors = re.findall(
                    r'<a[^>]+href="([^"]+)"[^>]+class="[^"]*result__a[^"]*"[^>]*>(.*?)</a>',
                    text,
                    re.S,
                )
            for index, (href, raw_title) in enumerate(anchors):
                url = _result_url(href)
                title = unescape(re.sub(r"<[^>]+>", " ", raw_title))
                snippet = (
                    unescape(re.sub(r"<[^>]+>", " ", snippets[index]))
                    if index < len(snippets)
                    else ""
                )
                combined = f"{url} {title} {snippet}"
                if username.casefold() not in combined.casefold():
                    continue
                all_domains.extend(_extract_domains(combined))
                all_links.extend(_extract_links(combined))
                if not bio_text and snippet.strip():
                    bio_text = snippet.strip()[:200]
                evidence.append({
                    "url": url,
                    "kind": "web_search_candidate",
                    "excerpt": f"{title} {snippet}".strip()[:300],
                })
            time.sleep(0.5)
        except Exception as e:
            _log(f"ddg error on query '{query[:30]}': {e}")
            errors.append(f"{type(e).__name__}: {e}")
            continue

    all_domains = list(dict.fromkeys(all_domains))
    all_links = list(dict.fromkeys(all_links))

    if all_domains or all_links:
        return _result(
            PLAUSIBLE_CANDIDATE,
            source="duckduckgo",
            signal="web search found a possible company or professional profile; human verification required",
            domains=all_domains[:5],
            links=all_links[:5],
            bio=bio_text,
            evidence=evidence[:5],
        )
    _log("ddg: no company domains found in search results")
    if completed_queries:
        return _no_evidence("duckduckgo", "DuckDuckGo found no exact-username result with company signals")
    return _lookup_error(
        "duckduckgo",
        "DuckDuckGo lookup failed" + (f": {'; '.join(errors)}" if errors else ""),
    )


# ── Tier 4: Playwright browser scrape ────────────────────────────────────────
def _playwright_scrape(username: str) -> dict | None:
    """Scrape the Reddit profile page via an existing Chrome session (CDP) or headless fallback.

    Reddit blocks headless browsers. To use this tier, launch Chrome with remote debugging:
      /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        _log("playwright not installed")
        return _lookup_error("playwright", "playwright is not installed")

    def _scrape_page(page) -> dict | None:
        page.goto(f"https://www.reddit.com/user/{username}/", timeout=15000)
        page.wait_for_timeout(3000)

        body_text = page.inner_text("body") or ""
        if "blocked by network security" in body_text.lower():
            _log("playwright: blocked by Reddit bot detection")
            return _lookup_error("playwright", "rendered Reddit profile was blocked")

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

        if domains:
            return _result(
                DIRECT_DISCLOSURE,
                source="playwright",
                signal="author published a company domain on their Reddit profile",
                domains=domains[:5],
                links=links[:10],
                bio=profile_text[:300] if profile_text else None,
                evidence=[{
                    "url": f"https://www.reddit.com/user/{quote(username)}/",
                    "kind": "reddit_profile",
                    "excerpt": profile_text[:300],
                }],
            )
        if links:
            return _result(
                PLAUSIBLE_CANDIDATE,
                source="playwright",
                signal="author published a professional link but no company domain; human verification required",
                links=links[:10],
                bio=profile_text[:300] if profile_text else None,
                evidence=[{
                    "url": f"https://www.reddit.com/user/{quote(username)}/",
                    "kind": "reddit_profile_link_candidate",
                    "excerpt": profile_text[:300],
                }],
            )
        _log(f"playwright: bio={bool(profile_text)}, no company signals")
        return _no_evidence("playwright", "rendered Reddit profile had no company signals")

    try:
        with sync_playwright() as p:
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

            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            result = _scrape_page(page)
            browser.close()
            return result
    except Exception as e:
        _log(f"playwright error: {e}")
        return _lookup_error("playwright", f"{type(e).__name__}: {e}")


# ── Public API ───────────────────────────────────────────────────────────────
def lookup_profile(username: str, tiers: list[str] | None = None) -> dict:
    """Run the waterfall and return a direct disclosure, candidate, absence, or error.

    Args:
        username: Reddit username (without u/ prefix)
        tiers: optional list of tier names to try (default: all in order)

    Returns:
        dict with disclosure verdict, eligibility, evidence, and compatibility fields
    """
    username = username.lstrip("u/").strip()
    if not username:
        return _lookup_error("none", "empty username")

    tier_map = {
        "reddit_profile": _reddit_profile,
        "exa": _exa_search,
        "duckduckgo": _ddg_search,
        "playwright": _playwright_scrape,
    }
    run_tiers = tiers or ["reddit_profile", "exa", "duckduckgo", "playwright"]
    attempts = []
    first_candidate = None
    direct_profile_completed_without_evidence = False
    errors = []

    for tier_name in run_tiers:
        fn = tier_map.get(tier_name)
        if not fn:
            continue
        _log(f"trying tier: {tier_name}")
        result = fn(username)
        if not result:
            result = _lookup_error(tier_name, "tier returned no result")
        attempts.append({
            "source": result.get("source", tier_name),
            "state": result.get("tier_state", "error"),
            "signal": result.get("signal", ""),
        })
        verdict = result.get("review_verdict")
        if verdict == DIRECT_DISCLOSURE:
            result["attempts"] = attempts
            _log(f"direct disclosure on tier {tier_name}: {result.get('domains', [])}")
            return result
        if verdict == PLAUSIBLE_CANDIDATE and first_candidate is None:
            first_candidate = result
        if verdict == NO_PUBLIC_EVIDENCE and tier_name in {"reddit_profile", "playwright"}:
            direct_profile_completed_without_evidence = True
        if verdict == LOOKUP_ERROR:
            errors.extend(result.get("errors") or [result.get("signal", "lookup error")])
        time.sleep(0.3)

    if first_candidate:
        first_candidate["attempts"] = attempts
        first_candidate["errors"] = errors
        return first_candidate
    if direct_profile_completed_without_evidence:
        result = _result(
            NO_PUBLIC_EVIDENCE,
            source="none",
            signal=f"no public company evidence found across {len(run_tiers)} checked tiers",
            tier_state="no_evidence",
            errors=errors,
        )
    else:
        result = _result(
            LOOKUP_ERROR,
            source="none",
            signal=f"profile lookup could not complete across {len(run_tiers)} tiers",
            tier_state="error",
            errors=errors,
        )
    result["attempts"] = attempts
    return result


# ── CLI ──────────────────────────────────────────────────────────────────────
def main():
    import argparse
    ap = argparse.ArgumentParser(description="Look up Reddit profile disclosures and search candidates")
    ap.add_argument("usernames", nargs="+", help="Reddit usernames to look up")
    ap.add_argument("--verbose", "-v", action="store_true")
    ap.add_argument("--tier", choices=["reddit_profile", "exa", "duckduckgo", "playwright"],
                    help="test a single tier only")
    ap.add_argument("--json", action="store_true", help="output as JSON")
    args = ap.parse_args()

    global VERBOSE
    VERBOSE = args.verbose

    tiers = [args.tier] if args.tier else None
    results = {}

    for username in args.usernames:
        if not args.json:
            print(f"\n{'='*60}")
            print(f"  {username}")
            print(f"{'='*60}")
        result = lookup_profile(username, tiers=tiers)
        results[username] = result

        if args.json:
            continue

        verdict = result["review_verdict"]
        if verdict == DIRECT_DISCLOSURE:
            print(f"  DIRECT DISCLOSURE via {result['source']}")
            if result["domains"]:
                print(f"  domains: {', '.join(result['domains'])}")
            if result["links"]:
                print(f"  links: {', '.join(result['links'][:5])}")
            if result["bio"]:
                print(f"  bio: {result['bio'][:200]}")
            print(f"  signal: {result['signal']}")
        elif verdict == PLAUSIBLE_CANDIDATE:
            print(f"  CANDIDATE via {result['source']} (manual review required)")
            if result["domains"]:
                print(f"  candidate domains: {', '.join(result['domains'])}")
            print(f"  signal: {result['signal']}")
        elif verdict == LOOKUP_ERROR:
            print(f"  LOOKUP ERROR — {result['signal']}")
        else:
            print(f"  NO PUBLIC EVIDENCE — {result['signal']}")

    if args.json:
        import json
        print(json.dumps(results, indent=2, ensure_ascii=False))

    if not args.json:
        disclosed = sum(1 for r in results.values() if r["review_verdict"] == DIRECT_DISCLOSURE)
        candidates = sum(1 for r in results.values() if r["review_verdict"] == PLAUSIBLE_CANDIDATE)
        errors = sum(1 for r in results.values() if r["review_verdict"] == LOOKUP_ERROR)
        print(f"\n--- {disclosed} direct · {candidates} candidates · {errors} errors · {len(results)} checked ---")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
