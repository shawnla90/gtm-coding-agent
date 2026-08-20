#!/usr/bin/env python3
"""Build the LinkedIn outreach ledger from a prospect CSV.

Normalizes profile URLs, splits first-degree (message flow) vs non-connection
(CR flow), and upserts on profile_url so re-running is always safe.

Usage:
  python3 build_ledger.py --csv prospects.csv
  python3 build_ledger.py --csv prospects.csv --url-col "Person Linkedin Url" --first-col "First Name"

Expected columns (override with flags): linkedin_url, first_name, last_name,
company, title, and optionally is_first_degree (1/true/yes for existing connections).
"""
import argparse, csv, re, sqlite3
from pathlib import Path

DB = Path(__file__).with_name("li_outreach.db")

def norm_url(u):
    u = (u or "").strip()
    if not u:
        return None
    u = u.split("?")[0].rstrip("/")
    m = re.search(r"linkedin\.com/(?:.*/)?in/([^/?#]+)", u, re.I)
    if not m:
        return None
    slug = m.group(1)
    if not slug or slug.lower().startswith("pub"):
        return None
    return f"https://www.linkedin.com/in/{slug}"

def truthy(v):
    return str(v).strip().lower() in ("1", "true", "yes")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--url-col", default="linkedin_url")
    ap.add_argument("--first-col", default="first_name")
    ap.add_argument("--last-col", default="last_name")
    ap.add_argument("--company-col", default="company")
    ap.add_argument("--title-col", default="title")
    ap.add_argument("--degree-col", default="is_first_degree")
    args = ap.parse_args()

    con = sqlite3.connect(DB)
    con.execute("PRAGMA busy_timeout=15000")
    con.execute("""CREATE TABLE IF NOT EXISTS leads(
        profile_url TEXT PRIMARY KEY,
        first_name TEXT, last_name TEXT, company TEXT, title TEXT,
        degree TEXT,                       -- 'first' | 'non' — source record, never mutated
        cr_status TEXT DEFAULT 'pending',  -- pending|sending|sent|accepted|withdrawn|skip
        cr_sent_at TEXT, accepted_at TEXT,
        msg1_status TEXT DEFAULT 'pending', msg1_at TEXT,
        msg2_status TEXT DEFAULT 'pending', msg2_at TEXT,
        reply_status TEXT, replied_at TEXT,
        last_error TEXT, updated_at TEXT DEFAULT (datetime('now'))
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS attempts(
        id INTEGER PRIMARY KEY,
        profile_url TEXT NOT NULL,
        action TEXT NOT NULL,              -- 'cr' | 'msg1' | 'msg2'
        status TEXT NOT NULL,              -- 'claimed' | 'confirmed' | 'failed_before_send'
        detail TEXT,
        created_at TEXT NOT NULL
    )""")

    n = dup = nourl = first = non = 0
    seen = set()
    with open(args.csv) as f:
        for r in csv.DictReader(f):
            pu = norm_url(r.get(args.url_col))
            if not pu:
                nourl += 1
                continue
            if pu in seen:
                dup += 1
                continue
            seen.add(pu)
            fn = (r.get(args.first_col) or "").strip() or "there"
            ln = (r.get(args.last_col) or "").strip() or "-"
            comp = (r.get(args.company_col) or "").strip()
            title = (r.get(args.title_col) or "").strip()
            degree = "first" if truthy(r.get(args.degree_col)) else "non"
            if degree == "first":
                first += 1
            else:
                non += 1
            # first-degree: CR not applicable — mark accepted so the message flow can run
            cr = "accepted" if degree == "first" else "pending"
            con.execute("""INSERT INTO leads(profile_url,first_name,last_name,company,title,degree,cr_status)
                VALUES(?,?,?,?,?,?,?)
                ON CONFLICT(profile_url) DO UPDATE SET
                  first_name=excluded.first_name,last_name=excluded.last_name,
                  company=excluded.company,title=excluded.title,degree=excluded.degree""",
                (pu, fn, ln, comp, title, degree, cr))
            n += 1
    con.commit()
    print(f"ledger rows: {n}  (first-degree {first}, non-connection {non})")
    print(f"skipped: no/invalid URL {nourl}, duplicate URL {dup}")
    print("db:", DB)
    con.close()

if __name__ == "__main__":
    main()
