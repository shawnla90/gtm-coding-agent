#!/usr/bin/env python3
"""init_db.py - create the local SQLite db for the Reddit buyer-signal pipeline (idempotent).

A real, owned, on-disk database. Re-running never drops data: every table is created IF NOT
EXISTS and every insert downstream is INSERT OR IGNORE against a unique key. Run this once
before pull.py. Safe to re-run any time.

  python3 init_db.py
"""
import sqlite3
from pathlib import Path

HERE = Path(__file__).resolve().parent
DB = HERE / "data" / "signals.db"

SCHEMA = """
-- Clearbox-classified Reddit opportunities normalized for local analysis
CREATE TABLE IF NOT EXISTS reddit_threads (
  id            INTEGER PRIMARY KEY,
  external_id   TEXT UNIQUE,     -- Clearbox opportunity id (dedup key)
  subreddit     TEXT,
  title         TEXT,
  selftext      TEXT,
  permalink     TEXT,            -- full https url
  author        TEXT,
  score         INTEGER,
  num_comments  INTEGER,
  created_utc   INTEGER,
  flair         TEXT,
  source_type   TEXT,            -- 'clearbox'
  source_query  TEXT,            -- legacy-compatible copy of the Clearbox disposition
  clearbox_kind TEXT,            -- lead | engage | competitor (source of record)
  topic_tags    TEXT,            -- CSV of auto-tagged topics
  pulled_at     TEXT
);

-- top comments on high-signal threads (buyer language lives here too)
CREATE TABLE IF NOT EXISTS thread_comments (
  id            INTEGER PRIMARY KEY,
  external_id   TEXT UNIQUE,     -- thread_id::index, dedup key
  thread_id     TEXT,            -- reddit_threads.external_id
  body          TEXT,
  author        TEXT,
  score         INTEGER
);

-- extracted buyer language: real questions, comparisons, pains, requests
CREATE TABLE IF NOT EXISTS buyer_language (
  id            INTEGER PRIMARY KEY,
  external_id   TEXT UNIQUE,     -- hash of thread+quote, dedup key
  thread_id     TEXT,
  kind          TEXT,            -- question | comparison | pain | recommendation | objection
  quote         TEXT,
  brands        TEXT,            -- CSV of brands mentioned
  permalink     TEXT,
  subreddit     TEXT,
  created_utc   INTEGER,         -- when the source thread was posted (recency)
  engagement    INTEGER          -- thread score + comments, for ranking
);

-- the content / GEO plan: topics to publish that answer real buyer questions
CREATE TABLE IF NOT EXISTS content_topics (
  id            INTEGER PRIMARY KEY,
  external_id   TEXT UNIQUE,     -- slug, dedup key
  topic         TEXT,            -- the buyer question / theme
  content_angle TEXT,            -- the page/post title to write
  intent        TEXT,            -- high | mid | low search intent
  brands        TEXT,            -- CSV of brands this maps to
  evidence      TEXT,            -- a representative buyer quote
  thread_refs   TEXT,            -- CSV of permalinks backing it
  mentions      INTEGER,         -- how many threads touched this
  engagement    INTEGER,         -- summed thread engagement
  latest_utc    INTEGER,         -- most recent source thread (recency of the demand)
  score         INTEGER,         -- 1-5 priority
  tier          TEXT,            -- A-D
  topic_reason  TEXT             -- one-line why-this-score (you keep it)
);
"""


def main():
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    con.execute("PRAGMA journal_mode = WAL;")
    con.executescript(SCHEMA)
    columns = {row[1] for row in con.execute("PRAGMA table_info(reddit_threads)")}
    if "clearbox_kind" not in columns:
        con.execute("ALTER TABLE reddit_threads ADD COLUMN clearbox_kind TEXT")
    con.commit()
    tables = [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
    print(f"db ready at {DB.relative_to(HERE)} -> tables: {', '.join(tables)}")
    con.close()


if __name__ == "__main__":
    main()
