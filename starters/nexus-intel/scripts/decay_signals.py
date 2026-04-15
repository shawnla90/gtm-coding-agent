#!/usr/bin/env python3
"""
decay_signals.py — Retroactive signal decay + cleanup.

Walks every signal in the DB, joins `content_items.published_at` to compute
post age, then:

  1. Demotes urgency per `_decay.decay_urgency()` (half-life + max-age caps)
  2. Optionally deletes signals whose post is past 2× the type's max-age
     when `--delete-ancient` is passed (cascade-deletes tied insights)

Run this ONCE after applying the analyzer/ingest decay patches to clean up
the existing staleness accumulated before the guards were in place. Safe to
re-run — idempotent.

Usage:
  python3 scripts/decay_signals.py                       # demote stale signals in place
  python3 scripts/decay_signals.py --dry-run             # preview only, no writes
  python3 scripts/decay_signals.py --delete-ancient      # also DELETE signals > 2× max_age
  python3 scripts/decay_signals.py --dry-run --delete-ancient  # preview both
  python3 scripts/decay_signals.py --verbose             # print per-signal decisions
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter

from _decay import decay_urgency, format_age, should_drop
from _lib import get_db


def fetch_signals(conn) -> list[dict]:
    """Pull every signal with its post age_days, regardless of status.

    Includes signals in any state (new/acknowledged/acted-on/dismissed) so
    the decay pass is truly comprehensive. We never re-enliven a dismissed
    signal — only demote.
    """
    rows = conn.execute(
        """
        SELECT sig.id, sig.signal_type, sig.urgency, sig.status,
               sig.content_id, sig.title,
               ci.published_at,
               CAST((julianday('now') - julianday(COALESCE(ci.published_at, ci.scraped_at))) AS INTEGER) AS age_days
        FROM signals sig
        LEFT JOIN content_items ci ON ci.id = sig.content_id
        ORDER BY age_days DESC NULLS LAST
        """
    ).fetchall()
    return [dict(r) for r in rows]


def plan_decay(signals: list[dict], delete_ancient: bool) -> dict:
    """Compute the set of UPDATE/DELETE operations. Does not touch the DB."""
    to_update: list[tuple[int, str, str, int]] = []  # (id, old, new, age_days)
    to_delete: list[tuple[int, str, int]] = []       # (id, signal_type, age_days)
    unchanged = 0
    unknown_age = 0

    for s in signals:
        age = s.get("age_days")
        if age is None:
            unknown_age += 1
            continue
        age_int = int(age)

        # Ancient path: past 2× max_age → delete (or skip if not --delete-ancient)
        if delete_ancient and should_drop(s["signal_type"], age_int):
            to_delete.append((s["id"], s["signal_type"], age_int))
            continue

        # Decay path: compute new urgency, skip UPDATE if unchanged
        new_urgency = decay_urgency(
            s["signal_type"], age_int, s.get("urgency") or "backlog"
        )
        if new_urgency != (s.get("urgency") or "backlog"):
            to_update.append(
                (s["id"], s.get("urgency") or "backlog", new_urgency, age_int)
            )
        else:
            unchanged += 1

    return {
        "to_update": to_update,
        "to_delete": to_delete,
        "unchanged": unchanged,
        "unknown_age": unknown_age,
    }


def print_plan(plan: dict, signals: list[dict], verbose: bool) -> None:
    total = len(signals)
    print(f"Total signals scanned: {total}")
    print(f"  Unknown age (null published_at + scraped_at): {plan['unknown_age']}")
    print(f"  Unchanged: {plan['unchanged']}")
    print(f"  To demote: {len(plan['to_update'])}")
    print(f"  To delete: {len(plan['to_delete'])}")

    if plan["to_update"]:
        # Summarize demotions by (old → new)
        moves: Counter = Counter()
        for _id, old, new, _age in plan["to_update"]:
            moves[(old, new)] += 1
        print("\nDemotion breakdown:")
        for (old, new), n in moves.most_common():
            print(f"  {old:12} → {new:12}  ×{n}")

    if plan["to_delete"]:
        by_type: Counter = Counter()
        for _id, stype, _age in plan["to_delete"]:
            by_type[stype] += 1
        print("\nDeletion breakdown (by signal_type):")
        for stype, n in by_type.most_common():
            print(f"  {stype:25} ×{n}")

    if verbose:
        if plan["to_update"]:
            print("\n── Per-signal demotions ──")
            for sid, old, new, age in plan["to_update"][:50]:
                print(f"  [{sid:5}] {old:12} → {new:12} (age={format_age(age)})")
            if len(plan["to_update"]) > 50:
                print(f"  ... {len(plan['to_update']) - 50} more")
        if plan["to_delete"]:
            print("\n── Per-signal deletions ──")
            for sid, stype, age in plan["to_delete"][:50]:
                print(f"  [{sid:5}] {stype:25} age={format_age(age)}")
            if len(plan["to_delete"]) > 50:
                print(f"  ... {len(plan['to_delete']) - 50} more")


def apply_plan(conn, plan: dict) -> tuple[int, int, int]:
    """Execute the plan in a single transaction. Returns (updated, deleted, insights_cascaded)."""
    updated = 0
    deleted = 0
    insights_cascaded = 0

    if not plan["to_update"] and not plan["to_delete"]:
        return (0, 0, 0)

    try:
        conn.execute("BEGIN")
        for sid, _old, new, _age in plan["to_update"]:
            conn.execute("UPDATE signals SET urgency = ? WHERE id = ?", (new, sid))
            updated += 1
        if plan["to_delete"]:
            ids = [sid for sid, _t, _a in plan["to_delete"]]
            placeholders = ",".join("?" * len(ids))
            # Cascade: delete insights tied to doomed signals first
            cur = conn.execute(
                f"DELETE FROM insights WHERE signal_id IN ({placeholders})",
                ids,
            )
            insights_cascaded = cur.rowcount or 0
            cur = conn.execute(
                f"DELETE FROM signals WHERE id IN ({placeholders})",
                ids,
            )
            deleted = cur.rowcount or 0
        conn.execute("COMMIT")
    except Exception as e:
        conn.execute("ROLLBACK")
        sys.exit(f"  ✗ decay apply failed, rolled back: {e}")

    return (updated, deleted, insights_cascaded)


def main() -> int:
    parser = argparse.ArgumentParser(description="Retroactively apply decay rules to existing signals.")
    parser.add_argument("--dry-run", action="store_true", help="Preview the plan, do not write.")
    parser.add_argument(
        "--delete-ancient",
        action="store_true",
        help="DELETE signals past 2× the signal-type max_age (and their insights). Default: demote only.",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Print per-signal decisions.")
    args = parser.parse_args()

    conn = get_db()
    signals = fetch_signals(conn)
    if not signals:
        print("No signals in the DB. Nothing to do.")
        return 0

    plan = plan_decay(signals, delete_ancient=args.delete_ancient)
    print_plan(plan, signals, verbose=args.verbose)

    if args.dry_run:
        print("\n(dry-run — no changes written)")
        return 0

    if not plan["to_update"] and not plan["to_delete"]:
        print("\nNothing to do — the DB is already aligned with the decay rules.")
        return 0

    updated, deleted, insights_cascaded = apply_plan(conn, plan)
    print(f"\n✓ {updated} signals demoted")
    print(f"✓ {deleted} signals deleted")
    if insights_cascaded:
        print(f"✓ {insights_cascaded} insights cascade-deleted")
    return 0


if __name__ == "__main__":
    sys.exit(main())
