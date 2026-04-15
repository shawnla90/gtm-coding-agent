#!/usr/bin/env python3
"""
merge_people.py — Soft-merge engagers into `people` rows.

Matches on
(LOWER(TRIM(name)), LOWER(TRIM(parsed_company or company))) to create one
`people` row per human, then backfills engagers.person_id.

Idempotent — re-runs only touch engagers with NULL person_id.

Single-word-name safety rule: engagers whose name has < 2 words AND no company
get their own __solo__<id>__ key and never merge, to prevent false collisions
on common names like "Mark" or "Chris".

Usage:
    python3 scripts/merge_people.py
    python3 scripts/merge_people.py --dry-run
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict

from _lib import get_db


def canonical_key(name: str, company: str, engager_id: int) -> tuple[str, str]:
    n = (name or "").strip().lower()
    c = (company or "").strip().lower()
    has_full_name = len(n.split()) >= 2
    if not has_full_name and not c:
        return (f"__solo__{engager_id}__", "")
    return (n, c)


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge engagers into people by (name, company)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    conn = get_db()

    engagers = conn.execute(
        """SELECT id, name, COALESCE(parsed_company, company) AS co
           FROM engagers
           WHERE name IS NOT NULL AND TRIM(name) != ''
             AND person_id IS NULL"""
    ).fetchall()

    print(f"Loaded {len(engagers)} unmerged engagers with names")

    groups: dict[tuple[str, str], list[int]] = defaultdict(list)
    skipped = 0
    for e in engagers:
        key = canonical_key(e["name"], e["co"], e["id"])
        if not key[0]:
            skipped += 1
            continue
        groups[key].append(e["id"])

    print(f"Grouped into {len(groups)} unique (name, company) pairs ({skipped} skipped)")

    if args.dry_run:
        multi = [(k, v) for k, v in groups.items() if len(v) > 1]
        print(f"{len(multi)} groups have 2+ engager rows (potential cross-platform)")
        for (name, co), ids in list(multi)[:10]:
            engs = conn.execute(
                f"SELECT platform, handle FROM engagers WHERE id IN ({','.join('?'*len(ids))})",
                ids,
            ).fetchall()
            plats = ",".join(f"{e['platform']}:@{e['handle']}" for e in engs)
            print(f"  {name or '(no name)'} @ {co or '(no co)'}  →  {plats}")
        return 0

    inserted = 0
    linked = 0
    cur = conn.cursor()

    for (name, co), ids in groups.items():
        is_solo = name.startswith("__solo__")
        if is_solo:
            existing = None
        else:
            existing = cur.execute(
                "SELECT id FROM people "
                "WHERE LOWER(canonical_name)=? "
                "AND COALESCE(LOWER(canonical_company),'')=?",
                (name, co or ""),
            ).fetchone()

        if existing:
            person_id = existing["id"]
        else:
            rep = cur.execute(
                "SELECT name, COALESCE(parsed_company, company) AS co "
                "FROM engagers WHERE id=?",
                (ids[0],),
            ).fetchone()
            cur.execute(
                "INSERT INTO people (canonical_name, canonical_company) VALUES (?, ?)",
                (rep["name"], rep["co"]),
            )
            person_id = cur.lastrowid
            inserted += 1

        cur.execute(
            f"UPDATE engagers SET person_id=? WHERE id IN ({','.join('?'*len(ids))})",
            [person_id, *ids],
        )
        linked += cur.rowcount

    conn.commit()

    total_people = cur.execute("SELECT COUNT(*) FROM people").fetchone()[0]
    cross_platform = cur.execute(
        """SELECT COUNT(*) FROM (
             SELECT person_id FROM engagers
             WHERE person_id IS NOT NULL
             GROUP BY person_id
             HAVING COUNT(DISTINCT platform) > 1
           )"""
    ).fetchone()[0]

    print(f"✓ Inserted {inserted} new people rows ({total_people} total)")
    print(f"✓ Linked {linked} engagers to people")
    print(f"✓ {cross_platform} people have engager rows on 2+ platforms")

    return 0


if __name__ == "__main__":
    sys.exit(main())
