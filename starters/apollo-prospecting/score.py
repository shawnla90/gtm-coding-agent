#!/usr/bin/env python3
"""score.py -- score and rank the expanded buying committee.

Composite score = title_score (additive keyword weights) x reachability_mult.
Then picks top N per company ensuring persona diversity.

  python3 score.py              # score all, top 5 per company
  python3 score.py --top 3      # top 3 per company
"""
import argparse
import re
import sqlite3
from pathlib import Path

HERE = Path(__file__).resolve().parent
DB = HERE / "data" / "apollo.db"

TOP_N = 5

PERSONA_BUCKETS = {
    "sales": re.compile(
        r"\b(sales|revenue|CRO|chief revenue|account exec|business develop|biz dev|SDR|BDR|partnerships)\b", re.I
    ),
    "marketing": re.compile(
        r"\b(marketing|CMO|chief marketing|growth|demand gen|brand|content|SEO|comms|communications)\b", re.I
    ),
    "product": re.compile(
        r"\b(product|CPO|chief product|UX|design|engineering|CTO|technical|R&D)\b", re.I
    ),
}

TITLE_WEIGHTS = [
    (re.compile(r"\brev\s?ops\b|\brevenue operations\b", re.I), 100),
    (re.compile(r"\brevenue\b", re.I), 90),
    (re.compile(r"\bgrowth\b", re.I), 80),
    (re.compile(r"\bgo[\s-]?to[\s-]?market\b|\bgtm\b", re.I), 75),
    (re.compile(r"\bsales\b", re.I), 60),
    (re.compile(r"\bmarketing\b", re.I), 55),
    (re.compile(r"\bproduct\b", re.I), 50),
    (re.compile(r"\bbusiness development\b|\bbiz dev\b", re.I), 45),
    (re.compile(r"\bchief\b|\bC[A-Z]O\b", re.I), 30),
    (re.compile(r"\bvp\b|\bvice president\b", re.I), 25),
    (re.compile(r"\bhead of\b", re.I), 20),
    (re.compile(r"\bdirector\b", re.I), 15),
    (re.compile(r"\bmanager\b", re.I), 5),
]

REACHABILITY = {
    "T1": 1.0,
    "T2": 0.85,
    "T3": 0.6,
    "T4": 0.3,
}


def score_title(title):
    if not title:
        return 0
    return sum(w for pat, w in TITLE_WEIGHTS if pat.search(title))


def classify_persona(title):
    if not title:
        return "other"
    for bucket, pat in PERSONA_BUCKETS.items():
        if pat.search(title):
            return bucket
    return "other"


def reachability_tier(email_status, has_phone):
    es = (email_status or "").lower()
    hp = has_phone == "yes"
    if es in ("verified", "available") and hp:
        return "T1"
    if es in ("verified", "available"):
        return "T2"
    if es in ("guessed", "catch_all", "catch-all"):
        return "T3"
    return "T4"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--top", type=int, default=TOP_N)
    args = parser.parse_args()

    con = sqlite3.connect(DB)
    rows = con.execute(
        "SELECT id, title, email_status, has_phone, source_domain FROM expanded_contacts"
    ).fetchall()

    print(f"scoring {len(rows)} contacts...")

    for row_id, title, email_status, has_phone, source_domain in rows:
        ts = score_title(title)
        persona = classify_persona(title)
        tier = reachability_tier(email_status, has_phone)
        mult = REACHABILITY[tier]
        composite = round(ts * mult, 1)

        con.execute(
            "UPDATE expanded_contacts SET title_score=?, persona=?, "
            "reachability=?, composite_score=? WHERE id=?",
            (ts, persona, tier, composite, row_id),
        )

    con.commit()

    # rank: top N per company with persona diversity
    domains = [r[0] for r in con.execute(
        "SELECT DISTINCT source_domain FROM expanded_contacts"
    ).fetchall()]

    total_ranked = 0
    for domain in domains:
        candidates = con.execute(
            "SELECT id, persona, composite_score FROM expanded_contacts "
            "WHERE source_domain = ? ORDER BY composite_score DESC",
            (domain,),
        ).fetchall()

        selected_ids = []
        buckets_seen = set()
        for cid, persona, score in candidates:
            if len(selected_ids) >= args.top:
                break
            if persona not in buckets_seen or len(selected_ids) >= args.top - (3 - len(buckets_seen)):
                selected_ids.append(cid)
                if persona != "other":
                    buckets_seen.add(persona)

        if len(selected_ids) < args.top:
            for cid, persona, score in candidates:
                if cid not in selected_ids:
                    selected_ids.append(cid)
                if len(selected_ids) >= args.top:
                    break

        for rank, cid in enumerate(selected_ids, 1):
            con.execute("UPDATE expanded_contacts SET rank = ? WHERE id = ?", (rank, cid))

        total_ranked += len(selected_ids)

    con.commit()

    # summary
    tier_counts = {}
    for (tier, cnt) in con.execute(
        "SELECT reachability, COUNT(*) FROM expanded_contacts WHERE rank IS NOT NULL GROUP BY reachability"
    ).fetchall():
        tier_counts[tier] = cnt

    print(f"ranked top {args.top} per company across {len(domains)} domains: {total_ranked} contacts")
    for tier in ["T1", "T2", "T3", "T4"]:
        if tier in tier_counts:
            print(f"  {tier}: {tier_counts[tier]}")
    con.close()


if __name__ == "__main__":
    main()
