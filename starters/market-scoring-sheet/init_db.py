#!/usr/bin/env python3
"""init_db.py — create the local SQLite db and load the raw market CSV (idempotent).

A real, owned, on-disk database. Re-running never double-loads: a UNIQUE(name, domain)
index plus INSERT OR IGNORE makes the load idempotent. Reports the row + distinct-domain
counts so you can see the dedup happen.

  python3 init_db.py                  # load sample_market.csv
  python3 init_db.py my_list.csv      # load your own CSV (same columns)
"""
import csv
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DB = HERE / "data" / "market.db"
CSV_PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "sample_market.csv"

SCHEMA = """
CREATE TABLE IF NOT EXISTS contacts (
  id           INTEGER PRIMARY KEY,
  company      TEXT,
  domain       TEXT,
  industry     TEXT,
  employees    INTEGER,
  title        TEXT,
  name         TEXT,
  email        TEXT,
  linkedin     TEXT,
  score        INTEGER,
  tier         TEXT,
  reachability TEXT,
  fit_reason   TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_contacts_name_domain ON contacts(name, domain);
"""


def main():
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    con.execute("PRAGMA journal_mode = WAL;")
    con.executescript(SCHEMA)

    rows = list(csv.DictReader(CSV_PATH.open()))
    inserted = 0
    for r in rows:
        emp = (r.get("employees") or "").strip()
        cur = con.execute(
            "INSERT OR IGNORE INTO contacts "
            "(company, domain, industry, employees, title, name, email, linkedin) "
            "VALUES (?,?,?,?,?,?,?,?)",
            ((r.get("company") or "").strip(),
             (r.get("domain") or "").strip().lower(),
             (r.get("industry") or "").strip(),
             int(emp) if emp.isdigit() else None,
             (r.get("title") or "").strip(),
             (r.get("name") or "").strip(),
             (r.get("email") or "").strip().lower(),
             (r.get("linkedin") or "").strip()),
        )
        inserted += cur.rowcount
    con.commit()

    total = con.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]
    domains = con.execute("SELECT COUNT(DISTINCT domain) FROM contacts").fetchone()[0]
    print(f"loaded {CSV_PATH.name}: {len(rows)} rows in file, {inserted} new inserted, "
          f"{total} total in db, {domains} distinct domains")
    con.close()


if __name__ == "__main__":
    main()
