#!/usr/bin/env python3
"""
Initialize the Nexus Intel SQLite database.

Usage:
  python3 scripts/init_db.py              # create schema + seed (idempotent)
  python3 scripts/init_db.py --drop       # drop all tables first (dev only)
  python3 scripts/init_db.py --no-seed    # schema only, skip seed
"""

import argparse
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "data" / "intel.db"
SCHEMA_PATH = REPO_ROOT / "data" / "schema.sql"
SEED_PATH = REPO_ROOT / "data" / "seed-sources.sql"


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize intel.db")
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop all tables first (dev only, destroys data)",
    )
    parser.add_argument(
        "--no-seed",
        action="store_true",
        help="Skip seeding sources",
    )
    args = parser.parse_args()

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")

    if args.drop:
        print("Dropping all tables...")
        conn.execute("PRAGMA foreign_keys = OFF;")
        tables = [
            "lead_reasoning",
            "icp_scores",
            "engagements",
            "engagers",
            "people",
            "insights",
            "content_topics",
            "signals",
            "reddit_threads",
            "content_items",
            "topics",
            "scrape_runs",
            "sources",
        ]
        for t in tables:
            conn.execute(f"DROP TABLE IF EXISTS {t}")
        for v in ("v_competitors_active", "v_leaders_active", "v_signals_active"):
            conn.execute(f"DROP VIEW IF EXISTS {v}")
        conn.commit()
        conn.execute("PRAGMA foreign_keys = ON;")

    print(f"Applying schema from {SCHEMA_PATH.relative_to(REPO_ROOT)}...")
    schema = SCHEMA_PATH.read_text()
    conn.executescript(schema)
    conn.commit()

    if not args.no_seed:
        print(f"Seeding sources from {SEED_PATH.relative_to(REPO_ROOT)}...")
        seed = SEED_PATH.read_text()
        conn.executescript(seed)
        conn.commit()

    # Report
    cur = conn.cursor()
    total_sources = cur.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
    competitors = cur.execute(
        "SELECT COUNT(*) FROM sources WHERE relevance='competitor'"
    ).fetchone()[0]
    leaders = cur.execute(
        "SELECT COUNT(*) FROM sources WHERE relevance IN ('thought-leader','founder')"
    ).fetchone()[0]
    communities = cur.execute(
        "SELECT COUNT(*) FROM sources WHERE relevance='community'"
    ).fetchone()[0]
    named_accounts = cur.execute(
        "SELECT COUNT(*) FROM sources WHERE relevance='named-account'"
    ).fetchone()[0]

    print()
    print(f"  DB: {DB_PATH}")
    print(f"  Total sources:   {total_sources}")
    print(f"    Competitors:   {competitors}")
    print(f"    Leaders:       {leaders}")
    print(f"    Communities:   {communities}")
    print(f"    Named accts:   {named_accounts}")
    print()
    print("Done.")

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
