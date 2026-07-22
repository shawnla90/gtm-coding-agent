#!/usr/bin/env python3
"""pull.py - pull real, recent buyer threads from Reddit into SQLite (idempotent).

TWO SOURCES, pick with REDDIT_SOURCE:
  rapidapi (default) - a quick baseline via the reddit34 RapidAPI. Fast and cheap, good enough to
      see the gap and build the first deck. Needs RAPIDAPI_KEY.
  clearbox           - the accurate, context-driven version. Clearbox classifies Reddit by buying
      intent (intent, not keywords) off real content consumption, and adds sentiment and competitor
      context. Export your Clearbox opportunities to data/clearbox_export.json and this reads them
      through the same pipeline. See the format note in load_clearbox().

RECENCY GUARDRAIL (the important part): only recent conversations ever enter the database. Default
is the last 30 days. This is the same guardrail that keeps you sincere on Reddit, you engage with
live threads, not dredged-up old ones. Set MAX_AGE_DAYS to widen it (60 for a fuller season).

  export RAPIDAPI_KEY=...
  python3 pull.py                      # rapidapi baseline, last 30 days
  MAX_AGE_DAYS=60 python3 pull.py      # widen the window to 60 days
  REDDIT_SOURCE=clearbox python3 pull.py   # read data/clearbox_export.json instead
  python3 pull.py --max 8              # cap posts kept per source (faster sample)
  python3 pull.py --no-comments        # skip the comment pass
"""
import argparse
import json
import os
import sqlite3
import time
from pathlib import Path

from lib import reddit_client as rc
from lib.relevance import is_relevant

HERE = Path(__file__).resolve().parent
DB = HERE / "data" / "signals.db"
CFG = HERE / "config"

# recency guardrail: nothing older than this enters the database. Default 30 days; 60 for a fuller
# seasonal picture. Overridable via the MAX_AGE_DAYS env var.
MAX_AGE_DAYS = int(os.environ.get("MAX_AGE_DAYS", "30"))
# data source: "rapidapi" (baseline) or "clearbox" (accurate, context-driven).
SOURCE = os.environ.get("REDDIT_SOURCE", "rapidapi").strip().lower()

# how many top threads (by engagement) get their comments pulled
COMMENT_THREADS = 40
COMMENTS_PER_THREAD = 8


def _lines(path):
    if not path.exists():
        return []
    out = []
    for ln in path.read_text().splitlines():
        s = ln.strip()
        if s and not s.startswith("#"):
            out.append(s)
    return out


def _full_permalink(p):
    perm = p.get("permalink") or ""
    if perm.startswith("http"):
        return perm
    return "https://www.reddit.com" + perm if perm.startswith("/") else perm


def _upsert_thread(con, p, source_type, source_query, cutoff):
    ext = p.get("id") or p.get("name")
    if not ext:
        return 0
    # recency gate: drop anything older than the window. No stale forum threads, ever.
    created = int(p.get("created_utc") or 0)
    if created and created < cutoff:
        return 0
    # relevance gate: a keyword search surfaces off-topic subreddits (careers, gaming, politics).
    # Keep only threads actually about the product category.
    if not is_relevant(f"{p.get('title','')} {p.get('selftext','')}"):
        return 0
    cur = con.execute(
        "INSERT OR IGNORE INTO reddit_threads "
        "(external_id, subreddit, title, selftext, permalink, author, score, num_comments, "
        " created_utc, flair, source_type, source_query, pulled_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (ext,
         p.get("subreddit") or "",
         (p.get("title") or "").strip(),
         (p.get("selftext") or "").strip(),
         _full_permalink(p),
         p.get("author") or "",
         int(p.get("score") or p.get("ups") or 0),
         int(p.get("num_comments") or 0),
         int(p.get("created_utc") or 0),
         p.get("link_flair_text") or "",
         source_type, source_query,
         time.strftime("%Y-%m-%d")),
    )
    return cur.rowcount


def pull_threads(con, max_per_source):
    keywords = _lines(CFG / "keywords.txt")
    subs = _lines(CFG / "subreddits.txt")
    cutoff = int(time.time()) - MAX_AGE_DAYS * 86400
    print(f"pulling: {len(keywords)} keyword searches + {len(subs)} subreddits "
          f"(hot+top, last {MAX_AGE_DAYS} days only)")

    added = 0
    for kw in keywords:
        posts = rc.search(kw)
        kept = posts[:max_per_source] if max_per_source else posts
        n = sum(_upsert_thread(con, p, "search", kw, cutoff) for p in kept)
        added += n
        print(f"  search '{kw}': {len(posts)} found, {n} kept (recent + relevant)")
    con.commit()

    for sub in subs:
        posts = rc.posts_by_subreddit(sub, "hot") + rc.top_posts_by_subreddit(sub, "month")
        # dedup within this source by id before capping
        seen, uniq = set(), []
        for p in posts:
            pid = p.get("id") or p.get("name")
            if pid and pid not in seen:
                seen.add(pid)
                uniq.append(p)
        kept = uniq[:max_per_source] if max_per_source else uniq
        n = sum(_upsert_thread(con, p, "subreddit", sub, cutoff) for p in kept)
        added += n
        print(f"  r/{sub}: {len(uniq)} unique, {n} kept")
    con.commit()
    return added


def load_clearbox(con, cutoff):
    """Read Clearbox opportunities from data/clearbox_export.json and ingest them through the same
    recency + relevance gates. Expected format: a JSON list of objects, each with at least
    {id, subreddit, title, selftext, permalink, created_utc, score, num_comments}. Clearbox already
    classified these by buying intent, so this is a higher-signal input than a raw keyword pull.
    Export from the Clearbox app (your filtered opportunity inbox) to this path."""
    path = HERE / "data" / "clearbox_export.json"
    if not path.exists():
        print("no data/clearbox_export.json found. Export your Clearbox opportunity inbox to that "
              "path (JSON list of posts), then re-run with REDDIT_SOURCE=clearbox. A sample file "
              "ships at data/clearbox_export.sample.json - cp it over to try the flow offline.")
        return 0
    items = json.loads(path.read_text())
    added = sum(_upsert_thread(con, p, "clearbox", p.get("subreddit", "clearbox"), cutoff)
                for p in items)
    con.commit()
    print(f"clearbox: {len(items)} opportunities read, {added} kept (recent + relevant)")
    return added


def pull_comments(con):
    rows = con.execute(
        "SELECT external_id, permalink FROM reddit_threads "
        "ORDER BY (score + num_comments) DESC LIMIT ?", (COMMENT_THREADS,)).fetchall()
    print(f"pulling comments on the top {len(rows)} threads by engagement")
    added = 0
    for tid, perm in rows:
        if not perm:
            continue
        items = rc.comments(perm)
        for i, c in enumerate(items[:COMMENTS_PER_THREAD]):
            if not isinstance(c, dict):
                continue
            body = (c.get("body") or "").strip()
            if not body or body in ("[deleted]", "[removed]"):
                continue
            cur = con.execute(
                "INSERT OR IGNORE INTO thread_comments (external_id, thread_id, body, author, score) "
                "VALUES (?,?,?,?,?)",
                (f"{tid}::{i}", tid, body, c.get("author") or "", int(c.get("score") or 0)))
            added += cur.rowcount
    con.commit()
    return added


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=0, help="cap posts kept per source (0 = keep all)")
    ap.add_argument("--no-comments", action="store_true", help="skip the comment pass")
    args = ap.parse_args()

    con = sqlite3.connect(DB)
    cutoff = int(time.time()) - MAX_AGE_DAYS * 86400
    print(f"source: {SOURCE} | recency guardrail: last {MAX_AGE_DAYS} days")
    if SOURCE == "clearbox":
        added = load_clearbox(con, cutoff)
    else:
        added = pull_threads(con, args.max)
    # the comment pass needs the RapidAPI key. Skip it when asked, or when running the Clearbox
    # export with no key set (so the offline sample runs end to end with no network and no key).
    skip_comments = args.no_comments or (SOURCE == "clearbox" and not rc.KEY)
    ct = 0 if skip_comments else pull_comments(con)

    total = con.execute("SELECT COUNT(*) FROM reddit_threads").fetchone()[0]
    subs = con.execute("SELECT COUNT(DISTINCT subreddit) FROM reddit_threads").fetchone()[0]
    print(f"done: {added} new threads this run, {ct} comments, "
          f"{total} threads total across {subs} subreddits.")
    con.close()


if __name__ == "__main__":
    main()
