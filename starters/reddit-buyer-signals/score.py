#!/usr/bin/env python3
"""score.py - score every content topic 1 to 5 and write a one-line topic_reason.

Transparent rules, no black box: search intent + buyer-talk volume + brand fit + citation
potential (thread engagement), summed to a 0-100 number and mapped to a 1-5 score and an A-D
tier. The A-tier rows are what you should publish first to get found in AI answers. Edit the maps
to match your own product and the tools your buyers compare you against. The topic_reason is
yours to keep.

  python3 score.py
"""
import sqlite3
from pathlib import Path

HERE = Path(__file__).resolve().parent
DB = HERE / "data" / "signals.db"

# the tools your buyers weigh you against - a topic mapping to these is worth more, because a
# comparison you can credibly win is a page AI will cite when a buyer asks. For Acme PM, this is
# the project-management set. Swap it for your own category's competitors.
CARRIED = ("asana", "monday.com", "trello", "clickup", "notion", "jira", "basecamp", "linear",
           "airtable", "wrike", "todoist", "smartsheet")


def intent_pts(intent):
    return {"high": 35, "mid": 20, "low": 8}.get(intent, 8), f"{intent} intent"


def volume_pts(mentions):
    if mentions >= 40:
        return 25, "heavy demand"
    if mentions >= 20:
        return 20, "strong demand"
    if mentions >= 10:
        return 14, "steady demand"
    if mentions >= 5:
        return 9, "some demand"
    return 4, "thin demand"


def brand_pts(brands):
    hits = [b for b in (brands or "").split(",") if b in CARRIED]
    if hits:
        return 18, f"competes with {hits[0]}"
    return 6, "category fit"


def citation_pts(engagement):
    # scaled to a fresh, last-30-days corpus: recent threads have not had years to pile up
    # comments, so a live thread with a few hundred interactions is already high-read.
    if engagement >= 2500:
        return 15, "high-read threads"
    if engagement >= 1000:
        return 12, "well-read threads"
    if engagement >= 300:
        return 8, "read threads"
    return 4, "niche threads"


def main():
    con = sqlite3.connect(DB)
    rows = con.execute(
        "SELECT id, intent, mentions, brands, engagement FROM content_topics").fetchall()
    for tid, intent, mentions, brands, eng in rows:
        ip, ir = intent_pts(intent)
        vp, vr = volume_pts(int(mentions or 0))
        bp, br = brand_pts(brands)
        cp, cr = citation_pts(int(eng or 0))
        total = ip + vp + bp + cp  # 0-100
        score = 5 if total >= 85 else 4 if total >= 70 else 3 if total >= 55 else 2 if total >= 40 else 1
        tier = "A" if score == 5 else "B" if score == 4 else "C" if score == 3 else "D"
        reason = f"{ir}, {vr}, {br}, {cr}"
        con.execute("UPDATE content_topics SET score=?, tier=?, topic_reason=? WHERE id=?",
                    (score, tier, reason, tid))
    con.commit()
    dist = con.execute(
        "SELECT score, COUNT(*) FROM content_topics GROUP BY score ORDER BY score DESC").fetchall()
    print("scored:", ", ".join(f"{s} star x{n}" for s, n in dist) or "no topics")
    con.close()


if __name__ == "__main__":
    main()
