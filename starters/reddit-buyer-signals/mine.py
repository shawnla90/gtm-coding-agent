#!/usr/bin/env python3
"""mine.py - turn raw threads into buyer language and a content/GEO plan (hybrid).

Two layers, so it works out of the box and gets sharper with an LLM:
  1. HEURISTIC (always runs, no key): auto-tag every thread by topic + brand, then pull the real
     buyer questions, brand comparisons, and pain phrases out of titles, bodies, and comments into
     buyer_language. Cluster those into content_topics - the pages to publish that answer them.
  2. RICH (--cli, optional): shell out to `claude -p` on your Claude Code subscription to rewrite
     each content_angle as a clean, publishable title. Falls back silently to the heuristic angle
     if the CLI is unavailable, so a run never breaks.

  python3 mine.py                 # heuristic only
  python3 mine.py --cli           # + Claude polish on the top topics (subscription, no API key)
  python3 mine.py --cli --top 25  # how many topics to polish
"""
import argparse
import hashlib
import json
import re
import sqlite3
import subprocess
from pathlib import Path

from lib.relevance import brands_in, auto_tags, is_relevant, classify

HERE = Path(__file__).resolve().parent
DB = HERE / "data" / "signals.db"
CLI_TIMEOUT = 90


def _hash(*parts):
    return hashlib.sha1("||".join(str(p) for p in parts).encode()).hexdigest()[:16]


def tag_threads(con):
    rows = con.execute("SELECT external_id, title, selftext FROM reddit_threads").fetchall()
    tagged = 0
    for ext, title, body in rows:
        tags = auto_tags(f"{title} {body}")
        if tags:
            con.execute("UPDATE reddit_threads SET topic_tags=? WHERE external_id=?",
                        (",".join(tags), ext))
            tagged += 1
    con.commit()
    return tagged


def extract_language(con):
    con.execute("DELETE FROM buyer_language")
    # thread titles + bodies
    threads = con.execute(
        "SELECT external_id, subreddit, title, selftext, permalink, score, num_comments, created_utc "
        "FROM reddit_threads").fetchall()
    added = 0
    for ext, sub, title, body, perm, score, ncom, created in threads:
        eng = int(score or 0) + int(ncom or 0)
        for text in (title, body):
            text = (text or "").strip()
            if len(text) < 12 or len(text) > 400:
                continue
            if not is_relevant(text):
                continue
            kind = classify(text)
            if not kind:
                continue
            bl = brands_in(text)
            cur = con.execute(
                "INSERT OR IGNORE INTO buyer_language "
                "(external_id, thread_id, kind, quote, brands, permalink, subreddit, created_utc, engagement) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (_hash(ext, text[:60]), ext, kind, text, ",".join(bl), perm, sub, int(created or 0), eng))
            added += cur.rowcount
    # comments (only the buyer-language ones, keep them tight)
    comments = con.execute(
        "SELECT c.thread_id, c.body, c.score, t.subreddit, t.permalink, t.score, t.num_comments, t.created_utc "
        "FROM thread_comments c JOIN reddit_threads t ON t.external_id=c.thread_id").fetchall()
    for tid, body, cscore, sub, perm, tscore, tncom, created in comments:
        body = (body or "").strip()
        if len(body) < 25 or len(body) > 400:
            continue
        if not is_relevant(body):
            continue
        kind = classify(body)
        if not kind:
            continue
        bl = brands_in(body)
        eng = int(tscore or 0) + int(tncom or 0)
        cur = con.execute(
            "INSERT OR IGNORE INTO buyer_language "
            "(external_id, thread_id, kind, quote, brands, permalink, subreddit, created_utc, engagement) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (_hash(tid, body[:60]), tid, kind, body, ",".join(bl), perm, sub, int(created or 0), eng))
        added += cur.rowcount
    con.commit()
    return added


# map a buyer-language topic key to a default publishable angle. These are the pages Acme PM would
# publish to answer the questions buyers actually post. Edit them for your own product and market.
TOPIC_ANGLES = {
    "kanban-boards": "The best kanban tools for small teams: an honest breakdown",
    "gantt-charts": "Gantt charts without the bloat: which PM tools do timelines right",
    "task-management": "Task management for small teams: what actually keeps work moving",
    "sprint-planning": "Sprint planning tools compared: what small agile teams really need",
    "all-in-one-vs-focused": "All-in-one vs focused: when a simple PM tool beats a do-everything suite",
    "free-vs-paid": "Free vs paid project management: where the free plans stop working",
    "integrations": "The integrations that make a PM tool stick (Slack, API, automations)",
    "team-collaboration": "Project management for remote teams: collaboration that does not slow you down",
    "switching-tools": "Switching project management tools: how to migrate without losing the team",
    "time-tracking": "Time tracking inside your PM tool: what small agencies should look for",
    "brand-comparison": "Head-to-head: the PM-tool comparison buyers keep asking about",
}


def build_topics(con):
    con.execute("DELETE FROM content_topics")
    rows = con.execute(
        "SELECT kind, quote, brands, permalink, subreddit, created_utc, engagement "
        "FROM buyer_language").fetchall()
    buckets = {}
    for kind, quote, brands, perm, sub, created, eng in rows:
        keys = auto_tags(quote)
        if not keys and kind == "comparison":
            keys = ["brand-comparison"]
        if not keys:
            continue
        for key in keys:
            b = buckets.setdefault(key, {"quotes": [], "brands": {}, "perms": set(), "eng": 0,
                                         "kinds": {}, "latest": 0})
            b["quotes"].append((eng, quote, kind))
            b["perms"].add(perm)
            b["eng"] += int(eng or 0)
            b["latest"] = max(b["latest"], int(created or 0))
            b["kinds"][kind] = b["kinds"].get(kind, 0) + 1
            for br in (brands or "").split(","):
                if br:
                    b["brands"][br] = b["brands"].get(br, 0) + 1

    added = 0
    for key, b in buckets.items():
        mentions = len(b["quotes"])
        top_brands = sorted(b["brands"], key=b["brands"].get, reverse=True)[:5]
        best = sorted(b["quotes"], reverse=True)[0][1]
        # intent: comparisons + recommendation questions are the highest-intent buyer talk
        rec = b["kinds"].get("recommendation", 0) + b["kinds"].get("comparison", 0)
        intent = "high" if rec >= 5 else "mid" if rec >= 1 else "low"
        angle = TOPIC_ANGLES.get(key, key.replace("-", " ").title())
        con.execute(
            "INSERT OR IGNORE INTO content_topics "
            "(external_id, topic, content_angle, intent, brands, evidence, thread_refs, "
            " mentions, engagement, latest_utc) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (_hash("topic", key), key.replace("-", " "), angle, intent, ",".join(top_brands),
             best[:280], ",".join(list(b["perms"])[:8]), mentions, b["eng"], b["latest"]))
        added += con.execute("SELECT changes()").fetchone()[0]
    con.commit()
    return added


def polish_with_cli(con, top):
    """Optional: rewrite the top content angles with `claude -p` (subscription, no API key)."""
    rows = con.execute(
        "SELECT external_id, topic, content_angle, brands, evidence FROM content_topics "
        "ORDER BY score DESC, engagement DESC LIMIT ?", (top,)).fetchall()
    if not rows:
        return 0
    payload = [{"id": r[0], "topic": r[1], "angle": r[2], "brands": r[3], "evidence": r[4]} for r in rows]
    system = ("You are a SEO and GEO content strategist for a project-management SaaS aimed at "
              "small teams. For each item, rewrite 'angle' as ONE clean, specific, non-clickbait "
              "article title a buyer would search and an AI would cite. No em-dashes. Return ONLY "
              "a JSON array of {id, title}.")
    user = "Rewrite these angles:\n\n" + json.dumps(payload, indent=2)
    cmd = ["claude", "-p", "--model", "opus", "--dangerously-skip-permissions",
           "--no-session-persistence", "--append-system-prompt", system, user]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=CLI_TIMEOUT)
        if res.returncode != 0 or not res.stdout.strip():
            print("  (claude CLI unavailable, keeping heuristic angles)")
            return 0
        text = res.stdout.strip()
        m = re.search(r"\[.*\]", text, re.DOTALL)
        items = json.loads(m.group(0) if m else text)
    except Exception as e:
        print(f"  (claude CLI skipped: {e}); keeping heuristic angles")
        return 0
    n = 0
    for it in items:
        if it.get("id") and it.get("title"):
            con.execute("UPDATE content_topics SET content_angle=? WHERE external_id=?",
                        (it["title"].replace("—", "-").strip(), it["id"]))
            n += 1
    con.commit()
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cli", action="store_true", help="polish top angles with claude -p")
    ap.add_argument("--top", type=int, default=20, help="how many topics to polish with --cli")
    args = ap.parse_args()

    con = sqlite3.connect(DB)
    tt = tag_threads(con)
    bl = extract_language(con)
    tp = build_topics(con)
    print(f"tagged {tt} threads · extracted {bl} buyer-language items · built {tp} content topics")
    if args.cli:
        pol = polish_with_cli(con, args.top)
        print(f"polished {pol} content angles with Claude")
    con.close()


if __name__ == "__main__":
    main()
