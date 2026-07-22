#!/usr/bin/env python3
"""reddit_client.py - a thin, polite client for the reddit34 RapidAPI (REAL endpoint shape).

The buyer talk that AI models read and cite lives on Reddit. This client pulls it: posts by
subreddit, posts by keyword search, and the top comments on a thread. It reads the key from
RAPIDAPI_KEY, retries transient errors, and backs off on 429, so a long pull does not get you
throttled.

Confirmed working endpoints (probed live):
  getSearchPosts?query=...                       keyword search across Reddit
  getPostsBySubreddit?subreddit=...&sort=...      newest/hot posts in a subreddit
  getTopPostsBySubreddit?subreddit=...&time=...   top posts in a window
  getPostCommentsWithSortV2?post_url=<permalink>  comments on one thread (needs the FULL url)

  export RAPIDAPI_KEY=...          # set once
  python3 -c "from lib.reddit_client import search; print(search('asana vs monday')[:1])"
"""
import os
import time
from urllib.parse import quote

try:
    import requests
except ImportError:
    raise SystemExit("requests not installed. Run: pip install requests")

HOST = "reddit34.p.rapidapi.com"
BASE = f"https://{HOST}"
KEY = os.environ.get("RAPIDAPI_KEY", "").strip()
SLEEP = 0.6          # ~100 calls/min, safe on a shared RapidAPI plan
TIMEOUT = 45


def _headers():
    return {"x-rapidapi-host": HOST, "x-rapidapi-key": KEY, "Content-Type": "application/json"}


def _call(path):
    """GET {BASE}{path} with 3-attempt retry and 429 backoff. Returns parsed JSON or None."""
    if not KEY:
        raise SystemExit("no RAPIDAPI_KEY set -> export RAPIDAPI_KEY=... and re-run.")
    for attempt in range(3):
        try:
            r = requests.get(f"{BASE}{path}", headers=_headers(), timeout=TIMEOUT)
        except requests.RequestException as e:
            print("  transport error:", e)
            time.sleep(2 * (attempt + 1))
            continue
        if r.status_code == 429:
            wait = int(r.headers.get("Retry-After", 5)) or 5
            print(f"  429 backoff {wait}s")
            time.sleep(wait)
            continue
        if r.status_code != 200:
            print(f"  HTTP {r.status_code}: {r.text[:160]}")
            return None
        time.sleep(SLEEP)
        try:
            return r.json()
        except ValueError:
            print(f"  non-JSON response: {r.text[:160]}")
            return None
    return None


def _posts(payload):
    """The API wraps posts as {success, data:{cursor, posts:[{data:{...}}]}}. Flatten to a list
    of the inner post dicts, tolerating shape drift."""
    if not payload or not payload.get("success"):
        return []
    data = payload.get("data") or {}
    out = []
    for p in data.get("posts", []):
        out.append(p.get("data", p) if isinstance(p, dict) else p)
    return out


# ── public API ──
def posts_by_subreddit(subreddit, sort="hot"):
    """Newest/hot posts in a subreddit. sort ∈ hot|new."""
    return _posts(_call(f"/getPostsBySubreddit?subreddit={quote(subreddit)}&sort={sort}"))


def top_posts_by_subreddit(subreddit, time_window="year"):
    """Top posts in a window. time_window ∈ hour|day|week|month|year|all."""
    return _posts(_call(f"/getTopPostsBySubreddit?subreddit={quote(subreddit)}&time={time_window}"))


def search(query):
    """Keyword search across Reddit. This is how buyer talk gets found regardless of subreddit
    (e.g. "asana vs monday") - the exact comparison, wherever it was posted. The endpoint takes
    the query alone; extra sort/time params make it error, so we keep it clean."""
    return _posts(_call(f"/getSearchPosts?query={quote(query)}"))


def comments(post_url, sort="TOP"):
    """Top comments on one thread. post_url must be the FULL permalink
    (https://www.reddit.com/r/.../comments/ID/slug/). Returns the raw payload's data."""
    payload = _call(f"/getPostCommentsWithSortV2?post_url={quote(post_url, safe='')}&sort={sort}")
    if not payload or not payload.get("success"):
        return []
    data = payload.get("data") or {}
    # data is {cursor, comments:[...]}; hand back just the comment list
    return data.get("comments", []) if isinstance(data, dict) else (data or [])
