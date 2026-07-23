#!/usr/bin/env python3
"""competitor.py — the competitor narrative, read straight from Clearbox's own classification.

Clearbox classifies every opportunity as engage / lead / competitor against the offer's own and
competitor brands, so the classification IS the relevant-mention signal (no literal brand-string
counting). This rolls the classified ops into a share-of-voice view: where a competitor is the
relevant answer vs where the client is the open opening, plus a generated sentiment read (Reddit
data carries no sentiment field, so it is produced upstream and labeled as generated).

  python3 competitor.py --ops data/ops_classified.json --gen data/competitor_gen.json \
      --own Acme PM --competitor Rival PM --out data/competitor_analysis.json

Read-only except the --out file.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from statistics import mean


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ops", default="data/ops_classified.json")
    ap.add_argument("--gen", default="data/competitor_gen.json")
    ap.add_argument("--own", required=True)
    ap.add_argument("--competitor", required=True)
    ap.add_argument("--out", default="data/competitor_analysis.json")
    args = ap.parse_args()

    ops = json.loads(Path(args.ops).read_text())
    kinds = Counter((o.get("kind") or "").lower() for o in ops)
    total = len(ops)
    competitor_n = kinds.get("competitor", 0)
    opening_n = kinds.get("engage", 0) + kinds.get("lead", 0)  # where the client's category is live

    gen = {}
    if Path(args.gen).exists():
        try:
            gen = json.loads(Path(args.gen).read_text())
        except Exception:
            gen = {}

    # the competitor conversations, straight from the classification
    competitor_ops = [
        {"subreddit": "r/" + (o.get("subreddit") or ""), "summary": o.get("summary"),
         "permalink": o.get("permalink"), "author": o.get("author")}
        for o in ops if (o.get("kind") or "").lower() == "competitor"
    ]

    sentiment = gen.get("sentiment", [])
    sent_dist = Counter((s.get("sentiment") or "").lower() for s in sentiment)
    scores = [float(s.get("sentiment_score")) for s in sentiment
              if isinstance(s.get("sentiment_score"), (int, float))]

    result = {
        "client": args.own,
        "competitor": args.competitor,
        "share_of_voice": {
            "basis": "Clearbox opportunity classification (the relevant-mention signal, not literal counting)",
            "total_opportunities": total,
            "competitor_is_the_answer": competitor_n,
            "client_category_is_the_opening": opening_n,
            "competitor_share_pct": round(100 * competitor_n / total) if total else 0,
            "reading": (f"across {total} live conversations, a competitor is the relevant answer in "
                        f"{competitor_n}; the client's category is the open opening in {opening_n}. "
                        f"The room is wide open for {args.own} to be the answer."),
        },
        "sentiment": {
            "generated": True,
            "note": "Reddit opportunities carry no sentiment field; this is an LLM read over the op summaries",
            "distribution": dict(sent_dist),
            "avg_score": round(mean(scores), 2) if scores else None,
            "per_op": sentiment,
        },
        "competitor_conversations": competitor_ops,
        "narrative": gen.get("narrative", ""),
    }
    Path(args.out).write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"competitor analysis: {competitor_n}/{total} competitor ops · {opening_n} openings · "
          f"sentiment {dict(sent_dist)} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
