#!/usr/bin/env python3
"""init_db.py -- create the local SQLite db and load the source contacts CSV (idempotent).

  python3 init_db.py                     # load sample_contacts.csv
  python3 init_db.py my_list.csv         # load your own CSV (same columns)
"""
import csv
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DB = HERE / "data" / "apollo.db"
CSV_PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "sample_contacts.csv"

SCHEMA = """
CREATE TABLE IF NOT EXISTS source_contacts (
  id       INTEGER PRIMARY KEY,
  company  TEXT,
  domain   TEXT,
  name     TEXT,
  title    TEXT,
  persona  TEXT,
  source   TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_source_name_domain
  ON source_contacts(name, domain);

CREATE TABLE IF NOT EXISTS expanded_contacts (
  id            INTEGER PRIMARY KEY,
  source_domain TEXT,
  company       TEXT,
  domain        TEXT,
  first_name    TEXT,
  title         TEXT,
  persona       TEXT,
  email_status  TEXT,
  has_phone     TEXT,
  linkedin_url  TEXT,
  city          TEXT,
  title_score   REAL,
  reachability  TEXT,
  composite_score REAL,
  rank          INTEGER
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_expanded_name_domain_title
  ON expanded_contacts(first_name, domain, title);
"""


def main():
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    con.execute("PRAGMA journal_mode = WAL;")
    con.executescript(SCHEMA)

    rows = list(csv.DictReader(CSV_PATH.open()))
    inserted = 0
    for r in rows:
        cur = con.execute(
            "INSERT OR IGNORE INTO source_contacts "
            "(company, domain, name, title, persona, source) "
            "VALUES (?,?,?,?,?,?)",
            ((r.get("company") or "").strip(),
             (r.get("domain") or "").strip().lower(),
             (r.get("name") or "").strip(),
             (r.get("title") or "").strip(),
             (r.get("persona") or "").strip(),
             (r.get("source") or "").strip()),
        )
        inserted += cur.rowcount
    con.commit()

    total = con.execute("SELECT COUNT(*) FROM source_contacts").fetchone()[0]
    domains = con.execute("SELECT COUNT(DISTINCT domain) FROM source_contacts").fetchone()[0]
    print(f"loaded {CSV_PATH.name}: {len(rows)} rows in file, {inserted} new inserted, "
          f"{total} total in db, {domains} distinct domains")
    con.close()


if __name__ == "__main__":
    main()
