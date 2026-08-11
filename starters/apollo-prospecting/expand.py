#!/usr/bin/env python3
"""expand.py -- the expansion play: source companies -> buying committee via Apollo API.

For each company domain in source_contacts, resolves the org and searches for
senior decision makers across sales, marketing, and product. Writes raw results
to expanded_contacts (scoring happens in score.py).

All API calls here are FREE (0 credits):
  - organizations/enrich  -> company info by domain
  - mixed_people/api_search -> names, titles, email/phone availability FLAGS

  python3 expand.py --all                    # expand every domain in the db
  python3 expand.py --domains mixpanel.com   # expand one company (demo mode)
"""
import argparse
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.apollo_client import search_people, enrich_company

HERE = Path(__file__).resolve().parent
DB = HERE / "data" / "apollo.db"

SEARCH_TITLES = [
    "VP Sales", "VP Marketing", "VP Growth", "VP Product", "VP Revenue",
    "Head of Sales", "Head of Marketing", "Head of Growth", "Head of Product",
    "Director of Sales", "Director of Marketing", "Director of Product",
    "CRO", "CMO", "CPO", "CTO",
    "RevOps", "Revenue Operations", "Sales Operations",
    "Growth", "Demand Gen", "Business Development",
]

SENIORITIES = ["c_suite", "vp", "head", "director"]


def already_expanded(con, domain):
    row = con.execute(
        "SELECT COUNT(*) FROM expanded_contacts WHERE source_domain = ?", (domain,)
    ).fetchone()
    return row[0] > 0


def expand_domain(con, domain):
    print(f"\n{'='*60}")
    print(f"  {domain}")
    print(f"{'='*60}")

    data = enrich_company(domain)
    org = (data or {}).get("organization")
    if not org:
        print(f"  could not resolve {domain}")
        return 0

    org_id = org["id"]
    org_name = org.get("name", domain)
    emp_count = org.get("estimated_num_employees")
    print(f"  {org_name} ({emp_count or '?'} employees) -> org {org_id}")

    people = search_people(
        org_ids=[org_id],
        titles=SEARCH_TITLES,
        seniorities=SENIORITIES,
        per_page=50,
    )
    print(f"  found {len(people)} candidates")

    if not people:
        return 0

    inserted = 0
    for p in people:
        title = p.get("title", "")
        first_name = p.get("first_name", "")
        phones = p.get("phone_numbers") or []
        has_phone = bool(
            p.get("has_direct_phone") == "Yes"
            or p.get("has_mobile_phone") == "Yes"
            or (phones and any(ph.get("raw_number") for ph in phones))
        )
        has_email = p.get("has_email", False)
        es = p.get("email_status") or ("available" if has_email else "")

        cur = con.execute(
            "INSERT OR IGNORE INTO expanded_contacts "
            "(source_domain, company, domain, first_name, title, persona, "
            " email_status, has_phone, linkedin_url, city) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (domain, org_name, domain, first_name, title, "",
             es, "yes" if has_phone else "no",
             p.get("linkedin_url", ""), p.get("city", "")),
        )
        inserted += cur.rowcount

    con.commit()
    print(f"  inserted {inserted} new contacts")
    return inserted


def main():
    parser = argparse.ArgumentParser(description="Expand source companies into buying committees")
    parser.add_argument("--all", action="store_true", help="Expand all domains in source_contacts")
    parser.add_argument("--domains", nargs="+", help="Specific domain(s) to expand")
    args = parser.parse_args()

    if not args.all and not args.domains:
        parser.error("provide --all or --domains")

    if not DB.exists():
        sys.exit(f"Database not found at {DB}. Run init_db.py first.")

    con = sqlite3.connect(DB)

    if args.domains:
        domains = args.domains
    else:
        rows = con.execute("SELECT DISTINCT domain FROM source_contacts").fetchall()
        domains = [r[0] for r in rows]

    print(f"Expanding {len(domains)} companies...\n")

    total = 0
    skipped = 0
    for domain in domains:
        if already_expanded(con, domain):
            print(f"  skipping {domain} (already expanded)")
            skipped += 1
            continue
        count = expand_domain(con, domain)
        total += count
        time.sleep(0.5)

    expanded_total = con.execute("SELECT COUNT(*) FROM expanded_contacts").fetchone()[0]
    print(f"\n{'='*60}")
    print(f"  DONE: {total} new contacts inserted, {skipped} domains skipped")
    print(f"  {expanded_total} total in expanded_contacts")
    print(f"{'='*60}")
    con.close()


if __name__ == "__main__":
    main()
