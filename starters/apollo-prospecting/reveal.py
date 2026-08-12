#!/usr/bin/env python3
"""reveal.py -- reveal actual emails and phones for ranked contacts.

Calls Apollo's people/match endpoint (1 export credit per person) to get
real contact data. Stores the results in the DB and prints a credit summary.

  python3 reveal.py                # reveal all ranked contacts
  python3 reveal.py --top 20       # reveal only the top 20 by score
  python3 reveal.py --dry-run      # show what would be revealed without spending credits
"""
import argparse
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.apollo_client import match_person

HERE = Path(__file__).resolve().parent
DB = HERE / "data" / "apollo.db"


def main():
    parser = argparse.ArgumentParser(description="Reveal contact data for ranked contacts")
    parser.add_argument("--top", type=int, help="Only reveal the top N by composite score")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be revealed")
    args = parser.parse_args()

    if not DB.exists():
        sys.exit(f"Database not found at {DB}. Run the pipeline first.")

    con = sqlite3.connect(DB)

    query = (
        "SELECT id, apollo_id, first_name, domain, title "
        "FROM expanded_contacts "
        "WHERE rank IS NOT NULL AND email IS NULL "
        "ORDER BY composite_score DESC"
    )
    rows = con.execute(query).fetchall()

    if args.top:
        rows = rows[:args.top]

    if not rows:
        print("No contacts to reveal (all ranked contacts already have email data).")
        con.close()
        return

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Revealing {len(rows)} contacts...\n")

    if args.dry_run:
        for row_id, apollo_id, first_name, domain, title in rows:
            print(f"  would reveal: {first_name} @ {domain} — {title}")
        print(f"\nEstimated cost: {len(rows)} export credits")
        con.close()
        return

    revealed = 0
    failed = 0
    for row_id, apollo_id, first_name, domain, title in rows:
        person = match_person(
            first_name=first_name,
            domain=domain,
            title=title,
            apollo_id=apollo_id,
        )

        if not person:
            print(f"  no match: {first_name} @ {domain}")
            failed += 1
            continue

        email = person.get("email") or ""
        last_name = person.get("last_name") or ""
        linkedin_url = person.get("linkedin_url") or ""
        city = person.get("city") or ""
        state = person.get("state") or ""
        country = person.get("country") or ""

        phones = person.get("phone_numbers") or []
        phone = ""
        for ph in phones:
            raw = ph.get("sanitized_number") or ph.get("raw_number") or ""
            if raw:
                phone = raw
                break

        con.execute(
            "UPDATE expanded_contacts SET "
            "email=?, phone=?, last_name=COALESCE(NULLIF(?,''),(last_name)), "
            "linkedin_url=COALESCE(NULLIF(?,''),(linkedin_url)), "
            "city=COALESCE(NULLIF(?,''),(city)), "
            "state=COALESCE(NULLIF(?,''),(state)), "
            "country=COALESCE(NULLIF(?,''),(country)) "
            "WHERE id=?",
            (email, phone, last_name, linkedin_url, city, state, country, row_id),
        )
        revealed += 1
        status = []
        if email:
            status.append("email")
        if phone:
            status.append("phone")
        if linkedin_url:
            status.append("linkedin")
        print(f"  {first_name} @ {domain} — got {', '.join(status) or 'match only'}")
        time.sleep(0.3)

    con.commit()

    total_with_email = con.execute(
        "SELECT COUNT(*) FROM expanded_contacts WHERE rank IS NOT NULL AND email != ''"
    ).fetchone()[0]
    total_with_phone = con.execute(
        "SELECT COUNT(*) FROM expanded_contacts WHERE rank IS NOT NULL AND phone != ''"
    ).fetchone()[0]

    print(f"\n{'='*60}")
    print(f"  DONE: {revealed} revealed, {failed} failed")
    print(f"  {total_with_email} contacts with email, {total_with_phone} with phone")
    print(f"  Credits used: ~{revealed} export credits")
    print(f"{'='*60}")
    con.close()


if __name__ == "__main__":
    main()
