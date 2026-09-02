#!/usr/bin/env python3
"""score.py -- title relevance x grade multiplier, then top N per company with persona diversity.

Same composite the Apollo starter uses (additive title keyword weights x a reachability multiplier),
with the multiplier now driven by the Moltsets grade: A 1.0, B 0.85, C 0.6, F / not found 0.3,
D 0.15. D is not zero because the person is still reachable on LinkedIn; the sheet routes them.

  python3 score.py            # score all, rank top 3 per company
  python3 score.py --top 5
"""
import argparse
import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.reachability import classify_persona, composite  # noqa: E402

HERE = Path(__file__).resolve().parent
DB = Path(os.environ.get("REACHABILITY_DB") or HERE / "data" / "reachability.db")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=3)
    args = ap.parse_args()

    con = sqlite3.connect(DB)
    rows = con.execute("SELECT id, title, grade, domain FROM contacts").fetchall()
    print(f"scoring {len(rows)} contacts...")
    for cid, title, grade, _domain in rows:
        ts, mult, comp = composite(title, grade)
        con.execute("UPDATE contacts SET title_score=?, persona=?, reach_mult=?, composite_score=?, rank=NULL WHERE id=?",
                    (ts, classify_persona(title), mult, comp, cid))
    con.commit()

    domains = [r[0] for r in con.execute("SELECT DISTINCT domain FROM contacts").fetchall()]
    ranked = 0
    for d in domains:
        cands = con.execute(
            "SELECT id, persona FROM contacts WHERE domain=? AND route IN ('email','email_low_volume') "
            "ORDER BY composite_score DESC, id", (d,)).fetchall()
        chosen, seen = [], set()
        for cid, persona in cands:          # first pass: one per persona
            if len(chosen) >= args.top:
                break
            if persona not in seen:
                chosen.append(cid)
                seen.add(persona)
        for cid, _p in cands:               # fill the rest by score
            if len(chosen) >= args.top:
                break
            if cid not in chosen:
                chosen.append(cid)
        for i, cid in enumerate(chosen, 1):
            con.execute("UPDATE contacts SET rank=? WHERE id=?", (i, cid))
        ranked += len(chosen)
    con.commit()

    print(f"ranked top {args.top} sendable per company across {len(domains)} domains: {ranked} contacts")
    for tier, n in con.execute("SELECT tier, COUNT(*) FROM contacts GROUP BY tier ORDER BY 2 DESC"):
        print(f"  {tier or '(ungraded)':20} {n}")
    con.close()


if __name__ == "__main__":
    main()
