#!/usr/bin/env python3
"""build_sheet.py - render the buyer signals as a color-coded Google Sheet (the proof).

Thin builder over the vendored proof-sheet engine (lib/sheet_engine.py). Four tabs:
  Content Plan   the scored content/GEO topics (score gradient red->green, tier colors)
  Buyer Language the real questions, comparisons, and pains pulled from Reddit
  Buyer Threads  the raw high-engagement threads behind it all
  Scoring Model  the transparent point system, so nothing is a black box
Plus a Dashboard tab up top. Rebuilds IN PLACE by sheet-id so the link never changes.

Needs a Google OAuth token at ~/.config/gspread/token.json - run setup_oauth.py once first.
Set BRAND to your product name so the sheet header reads as yours (default: "Acme PM").

  python3 build_sheet.py              # rebuild the stored sheet (data/sheet_url.txt) or create new
  python3 build_sheet.py <sheet_id>   # rebuild a specific sheet
  BRAND="Your Product" python3 build_sheet.py
"""
import os
import re
import sqlite3
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.sheet_engine import build, GREEN, GREEN_LT, BLUE, YELLOW, AMBER, GREY, ORANGE  # type: ignore

HERE = Path(__file__).resolve().parent
DB = HERE / "data" / "signals.db"
URL_FILE = HERE / "data" / "sheet_url.txt"
BRAND = os.environ.get("BRAND", "Acme PM")

TIER = {"A": GREEN, "B": BLUE, "C": YELLOW, "D": GREY}
INTENT = {"high": GREEN_LT, "mid": AMBER, "low": GREY}
KIND = {"comparison": GREEN_LT, "recommendation": BLUE, "question": AMBER, "pain": ORANGE}


def stored_key():
    if URL_FILE.exists():
        m = re.search(r"/d/([A-Za-z0-9_-]+)", URL_FILE.read_text())
        return m.group(1) if m else None
    return None


def df_from(con, sql):
    cur = con.execute(sql)
    cols = [d[0] for d in cur.description]
    df = pd.DataFrame([dict(zip(cols, r)) for r in cur.fetchall()], columns=cols)
    for c in df.columns:
        df[c] = df[c].fillna("").astype(str)
    return df


def main():
    key = sys.argv[1] if len(sys.argv) > 1 else stored_key()
    con = sqlite3.connect(DB)

    topics = df_from(con,
        "SELECT score, tier, intent, mentions, engagement, "
        "date(latest_utc,'unixepoch') AS latest_post, topic, content_angle, brands, "
        "evidence, topic_reason FROM content_topics ORDER BY score DESC, engagement DESC")
    lang = df_from(con,
        "SELECT kind, brands, subreddit, date(created_utc,'unixepoch') AS posted, "
        "engagement, quote, permalink FROM buyer_language "
        "WHERE length(quote) > 20 ORDER BY created_utc DESC, engagement DESC LIMIT 120")
    threads = df_from(con,
        "SELECT subreddit, date(created_utc,'unixepoch') AS posted, score, num_comments, "
        "title, topic_tags, permalink FROM reddit_threads "
        "WHERE topic_tags != '' ORDER BY created_utc DESC, (score + num_comments) DESC LIMIT 120")

    n_topics = len(topics)
    a_tier = int((topics.tier == "A").sum())
    n_lang = con.execute("SELECT COUNT(*) FROM buyer_language").fetchone()[0]
    n_threads = con.execute("SELECT COUNT(*) FROM reddit_threads").fetchone()[0]
    n_subs = con.execute("SELECT COUNT(DISTINCT subreddit) FROM reddit_threads").fetchone()[0]
    n_comp = con.execute("SELECT COUNT(*) FROM buyer_language WHERE kind='comparison'").fetchone()[0]
    span = con.execute("SELECT date(MIN(created_utc),'unixepoch'), date(MAX(created_utc),'unixepoch') "
                       "FROM reddit_threads WHERE created_utc > 0").fetchone()
    oldest, newest = span[0] or "", span[1] or ""
    con.close()

    dash = {
        "title": "Dashboard",
        "subtitle": {"title": f"{BRAND.upper()} - REDDIT BUYER SIGNALS",
                     "sub": f"{n_threads} recent threads across {n_subs} communities · "
                            f"{n_lang} buyer-language signals · posts from {oldest} to {newest}"},
        "entries": [
            {"kind": "section", "label": "THE SIGNAL"},
            {"kind": "kpi", "label": "Recent threads mined", "value": str(n_threads)},
            {"kind": "kpi", "label": "Freshness window", "value": f"{oldest} to {newest}"},
            {"kind": "kpi", "label": "Communities covered", "value": str(n_subs)},
            {"kind": "kpi", "label": "Buyer-language signals", "value": str(n_lang)},
            {"kind": "kpi", "label": "Head-to-head comparisons", "value": str(n_comp)},
            {"kind": "kpi", "label": "Content topics scored", "value": str(n_topics)},
            {"kind": "kpi", "label": "A-tier (publish first)", "value": str(a_tier)},
            {"kind": "blank", "label": ""},
            {"kind": "section", "label": "HOW TO READ IT"},
            {"kind": "bullet", "label": "Content Plan is the map: every A-tier (green 5) topic answers real buyer questions and maps to a tool buyers compare you against. Publish those first to get cited in AI answers."},
            {"kind": "bullet", "label": "Buyer Language is the proof and the wording: the exact questions, comparisons, and pains buyers post. Write in their words, not marketing words."},
            {"kind": "bullet", "label": "Buyer Threads is the receipts: the real high-engagement threads behind every topic, each linked so you can go read and reply."},
            {"kind": "bullet", "label": "Re-run weekly. New threads flow in, topics re-score, the plan stays current."},
        ],
    }

    tabs = [
        {
            "title": f"Content Plan ({n_topics})",
            "df": topics,
            "cols": ["score", "tier", "intent", "mentions", "engagement", "latest_post", "topic",
                     "content_angle", "brands", "evidence", "topic_reason"],
            "widths": {"latest_post": 110, "topic": 150, "content_angle": 360, "brands": 200,
                       "evidence": 340, "topic_reason": 330},
            "numeric": ["score", "mentions", "engagement"],
            "cf": [{"col": "score", "type": "grad", "stops": (1, 3, 5)},
                   {"col": "tier", "type": "map", "map": TIER},
                   {"col": "intent", "type": "map", "map": INTENT}],
        },
        {
            "title": f"Buyer Language ({min(120, n_lang)})",
            "df": lang,
            "cols": ["kind", "brands", "subreddit", "posted", "engagement", "quote", "permalink"],
            "widths": {"kind": 120, "brands": 160, "subreddit": 130, "posted": 110, "quote": 500,
                       "permalink": 240},
            "numeric": ["engagement"],
            "cf": [{"col": "kind", "type": "map", "map": KIND}],
        },
        {
            "title": f"Buyer Threads ({len(threads)})",
            "df": threads,
            "cols": ["subreddit", "posted", "score", "num_comments", "title", "topic_tags", "permalink"],
            "widths": {"subreddit": 140, "posted": 110, "title": 430, "topic_tags": 220, "permalink": 240},
            "numeric": ["score", "num_comments"],
            "cf": [],
        },
    ]

    scoring = [
        ["SCORING MODEL: score.py, edit the maps to match your product's competitors", ""],
        ["Dimension", "Points"],
        ["search_intent (0-35)", "high (comparisons + recommendation asks)=35 · mid=20 · low=8"],
        ["buyer-talk volume (0-25)", "40+ mentions=25 · 20+=20 · 10+=14 · 5+=9 · else 4"],
        ["brand fit (0-18)", "maps to a tool buyers compare you against (Asana, Monday, ClickUp...)=18 · category only=6"],
        ["citation potential (0-15)", "thread engagement 2500+=15 · 1000+=12 · 300+=8 · else 4"],
        ["score 1-5", "85+=5 · 70+=4 · 55+=3 · 40+=2 · else 1"],
        ["tier", "A=5 (publish first) · B=4 · C=3 · D=1-2"],
    ]
    raw_tabs = [{"title": "Scoring Model", "values": scoring, "widths": {0: 260, 1: 620}}]

    config = {"title": f"{BRAND} - Reddit Buyer Signals", "key": key, "share": "anyone_reader",
              "dashboard": dash, "tabs": tabs, "raw_tabs": raw_tabs}
    url, titles = build(config)
    URL_FILE.write_text(url + "\n")
    print("SHEET:", url)
    print("tabs:", titles)


if __name__ == "__main__":
    main()
