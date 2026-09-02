#!/usr/bin/env python3
"""init_db.py -- create the local SQLite db and load a contacts CSV (idempotent).

Accepts either the short schema (first_name,last_name,title,company,domain,email,linkedin_url)
or a raw Apollo people export (First Name, Last Name, Title, Company Name, Email, Email Status,
Primary Email Catch-all Status, Person Linkedin Url, Website, # Employees, Industry, Country,
Seniority). Header names are matched case-insensitively.

  python3 init_db.py                     # load sample_contacts.csv
  python3 init_db.py my_list.csv         # load your own CSV
  python3 init_db.py my_list.csv --limit 200 --country "United States"
"""
import argparse
import csv
import re
import sqlite3
from pathlib import Path

HERE = Path(__file__).resolve().parent
DB = HERE / "data" / "reachability.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS contacts (
  id            INTEGER PRIMARY KEY,
  first_name    TEXT, last_name TEXT, title TEXT,
  company       TEXT, domain TEXT,
  email         TEXT, apollo_email_status TEXT, apollo_catchall TEXT,
  linkedin_url  TEXT, seniority TEXT, industry TEXT, employees TEXT, country TEXT, source TEXT,
  -- Apollo employment check (optional)
  apollo_checked_at TEXT, apollo_current_company TEXT, apollo_current_domain TEXT,
  apollo_current_title TEXT, still_at_company TEXT,
  -- Moltsets employment check (reverse_linkedin_lookup)
  molt_current_company TEXT, molt_current_domain TEXT, molt_current_title TEXT,
  employment_source TEXT, employment_agree TEXT,
  -- Moltsets
  molt_route    TEXT, molt_http TEXT, molt_email TEXT, grade TEXT, grade_validated_at TEXT,
  molt_title    TEXT, molt_company TEXT, molt_company_domain TEXT, molt_linkedin TEXT,
  second_pass   TEXT, second_pass_decision TEXT, candidates_json TEXT,
  verdict       TEXT, tier TEXT, route TEXT,
  mobile_phone  TEXT, phone_http TEXT,
  -- scoring
  title_score   REAL, persona TEXT, reach_mult REAL, composite_score REAL, rank INTEGER,
  graded_at     TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_contacts_identity ON contacts(email, linkedin_url);
"""

ALIASES = {
    "first_name": ["first_name", "first name", "firstname", "first"],
    "last_name": ["last_name", "last name", "lastname", "last"],
    "title": ["title", "job title"],
    "company": ["company", "company name", "organization", "company_name"],
    "domain": ["domain", "website", "company domain", "company_domain"],
    "email": ["email", "work email", "business_email"],
    "apollo_email_status": ["email status", "email_status"],
    "apollo_catchall": ["primary email catch-all status", "catch_all", "catchall"],
    "linkedin_url": ["linkedin_url", "person linkedin url", "linkedin", "linkedin url"],
    "seniority": ["seniority"],
    "industry": ["industry"],
    "employees": ["# employees", "employees", "employee_count"],
    "country": ["country"],
    "source": ["source"],
}


def _domain(v: str) -> str:
    v = (v or "").strip().lower()
    v = re.sub(r"^https?://", "", v).split("/")[0]
    return v[4:] if v.startswith("www.") else v


def _pick(row: dict, key: str) -> str:
    lower = {k.strip().lower(): v for k, v in row.items() if k}
    for a in ALIASES[key]:
        if a in lower and lower[a] is not None:
            return str(lower[a]).strip()
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", nargs="?", default=str(HERE / "sample_contacts.csv"))
    ap.add_argument("--limit", type=int, default=0, help="load at most N rows (after filters)")
    ap.add_argument("--country", default="", help="keep only this country (exact match)")
    ap.add_argument("--exclude", default="", help="text file of emails or LinkedIn URLs to skip, one per line")
    ap.add_argument("--source", default="", help="tag every loaded row with this source label")
    args = ap.parse_args()

    excl = set()
    if args.exclude:
        excl = {l.strip().lower() for l in Path(args.exclude).read_text().splitlines() if l.strip()}

    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    con.execute("PRAGMA journal_mode = WAL;")
    con.executescript(SCHEMA)

    rows = list(csv.DictReader(Path(args.csv).open(encoding="utf-8-sig")))
    kept = inserted = skipped = 0
    for r in rows:
        if args.country and _pick(r, "country") != args.country:
            continue
        email = _pick(r, "email").lower()
        li = _pick(r, "linkedin_url").split("?")[0].rstrip("/")
        if (email and email in excl) or (li and li.lower() in excl):
            skipped += 1
            continue
        if not email and not li:
            continue
        kept += 1
        if args.limit and kept > args.limit:
            break
        domain = _domain(_pick(r, "domain")) or (email.split("@")[-1] if "@" in email else "")
        cur = con.execute(
            "INSERT OR IGNORE INTO contacts (first_name,last_name,title,company,domain,email,"
            "apollo_email_status,apollo_catchall,linkedin_url,seniority,industry,employees,country,source) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (_pick(r, "first_name"), _pick(r, "last_name"), _pick(r, "title"), _pick(r, "company"),
             domain, email, _pick(r, "apollo_email_status"), _pick(r, "apollo_catchall"), li,
             _pick(r, "seniority"), _pick(r, "industry"), _pick(r, "employees"), _pick(r, "country"),
             args.source or _pick(r, "source")),
        )
        inserted += cur.rowcount
    con.commit()
    total = con.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]
    domains = con.execute("SELECT COUNT(DISTINCT domain) FROM contacts").fetchone()[0]
    print(f"loaded {Path(args.csv).name}: {len(rows)} rows in file, {inserted} new inserted, "
          f"{skipped} excluded, {total} total in db, {domains} distinct domains")
    con.close()


if __name__ == "__main__":
    main()
