#!/usr/bin/env python3
"""One-shot migration: add profile_image_url column to engagers, sources, people.

ALTER TABLE ... ADD COLUMN is idempotent-by-try/except on SQLite — running this
twice is a no-op. Safe to re-run.

Usage:
    python3 scripts/migrate_avatars.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path


DB_PATH = Path(__file__).resolve().parents[1] / "data" / "intel.db"

TABLES = ("engagers", "sources", "people")


def column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r[1] == column for r in rows)


def main() -> int:
    if not DB_PATH.exists():
        print(f"ERROR: {DB_PATH} does not exist", file=sys.stderr)
        return 1

    conn = sqlite3.connect(DB_PATH)
    added: list[str] = []
    skipped: list[str] = []

    for table in TABLES:
        if column_exists(conn, table, "profile_image_url"):
            skipped.append(table)
            continue
        conn.execute(f"ALTER TABLE {table} ADD COLUMN profile_image_url TEXT")
        added.append(table)

    conn.commit()
    conn.close()

    if added:
        print(f"Added profile_image_url to: {', '.join(added)}")
    if skipped:
        print(f"Already present on: {', '.join(skipped)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
