#!/usr/bin/env python3
"""Backfill profile_image_url for engagers that have a profile_url but no
captured avatar yet.

This is a one-shot, idempotent script. Re-runs are safe — it only hits Apify
for rows where profile_image_url IS NULL.

Budget guardrail: --budget-cap defaults to $10 USD. The script aborts before
making any Apify call if the estimated cost exceeds the cap. It also prints a
dry-run summary by default; pass --apply to actually spend money.

Current estimate per batch (harvestapi/linkedin-profile-scraper, 2026-04):
  ~$0.002 per profile → ~$1 per 500 engagers
  batches of 50, progress checkpointed to stdout

Usage:
    python3 scripts/enrich_avatars.py               # dry-run, no spend
    python3 scripts/enrich_avatars.py --apply       # actually scrape
    python3 scripts/enrich_avatars.py --budget-cap 5 --apply

Status: v1 stub — field names need confirmation via a one-off manual Apify
call against harvestapi/linkedin-profile-scraper before --apply is safe. See
W3.2 "Apify field name confirmation" in the pre-launch plan.
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path


DB_PATH = Path(__file__).resolve().parents[1] / "data" / "intel.db"

# Cost estimate per profile lookup. Update after the first live run lands us
# real numbers. Keep conservative — hitting $10 cap is a hard stop.
COST_PER_PROFILE_USD = 0.002


def select_candidates(conn: sqlite3.Connection, limit: int) -> list[tuple[int, str, str]]:
    rows = conn.execute(
        """SELECT id, handle, profile_url
           FROM engagers
           WHERE platform = 'linkedin'
             AND profile_url IS NOT NULL AND profile_url != ''
             AND (profile_image_url IS NULL OR profile_image_url = '')
           ORDER BY id
           LIMIT ?""",
        (limit,),
    ).fetchall()
    return [(r[0], r[1], r[2]) for r in rows]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="Actually run Apify (default: dry-run only)")
    parser.add_argument("--budget-cap", type=float, default=10.0,
                        help="Hard stop on Apify spend in USD (default 10)")
    parser.add_argument("--batch-size", type=int, default=50,
                        help="Engagers per Apify call (default 50)")
    parser.add_argument("--limit", type=int, default=1000,
                        help="Max engagers to process total (default 1000)")
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"ERROR: {DB_PATH} does not exist", file=sys.stderr)
        return 1

    conn = sqlite3.connect(DB_PATH)
    candidates = select_candidates(conn, args.limit)
    conn.close()

    if not candidates:
        print("No engagers need avatar enrichment — nothing to do.")
        return 0

    estimated_cost = len(candidates) * COST_PER_PROFILE_USD
    print(f"Found {len(candidates)} engagers missing profile_image_url")
    print(f"Estimated Apify cost: ${estimated_cost:.2f} (${COST_PER_PROFILE_USD}/profile)")
    print(f"Budget cap: ${args.budget_cap:.2f}")

    if estimated_cost > args.budget_cap:
        print(f"\nABORT: estimated cost exceeds budget cap. "
              f"Lower --limit or raise --budget-cap.", file=sys.stderr)
        return 2

    if not args.apply:
        print("\nDry-run only. Pass --apply to actually spend and write.")
        print("First 5 candidates:")
        for row in candidates[:5]:
            print(f"  [{row[0]}] {row[1]} — {row[2]}")
        return 0

    # v1 stub — surface that the Apify field shape must be confirmed first.
    print("\nERROR: Avatar backfill not wired to an Apify actor yet.", file=sys.stderr)
    print("See W3.2 in ~/.claude/plans/sequential-mapping-thunder.md —", file=sys.stderr)
    print("we need to confirm the field name on harvestapi/linkedin-profile-scraper", file=sys.stderr)
    print("against a live response before burning budget.", file=sys.stderr)
    return 3


if __name__ == "__main__":
    sys.exit(main())
