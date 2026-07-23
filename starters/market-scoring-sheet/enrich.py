#!/usr/bin/env python3
"""enrich.py — optional Apollo enrichment for rows missing an email (REAL endpoint shape).

If APOLLO_API_KEY is set, this fills missing emails from Apollo using the SAME endpoints the
production pipeline uses: organizations/enrich to get the org id, then mixed_people/api_search
filtered by organization_ids, then people/match to reveal. If the key is NOT set, it skips
cleanly and the pipeline runs on the CSV fields alone, so you can try the whole flow first and
add Apollo later.

  APOLLO_API_KEY=... python3 enrich.py     # enrich rows missing an email
  python3 enrich.py                         # no key -> skip, use the CSV data

Apollo is a flat-rate plan; people/match consumes a credit per reveal. For B2B SaaS, Apollo is
the data layer a lot of pricier tools resell. Get Apollo: <YOUR APOLLO REFERRAL LINK>
"""
import os
import sqlite3
import time
from pathlib import Path

try:
    import requests
except ImportError:
    raise SystemExit("requests not installed. Run: pip install requests")

HERE = Path(__file__).resolve().parent
DB = HERE / "data" / "market.db"
KEY = os.environ.get("APOLLO_API_KEY", "").strip()
BASE = "https://api.apollo.io/api/v1"   # note /api/v1, not /v1
SLEEP = 0.5                              # ~120 calls/min, safe under Apollo's flat-plan limits


def _headers():
    return {"accept": "application/json", "Content-Type": "application/json",
            "Cache-Control": "no-cache", "X-Api-Key": KEY}


def _call(method, path, **kw):
    for attempt in range(3):
        try:
            r = requests.request(method, f"{BASE}{path}", headers=_headers(), timeout=45, **kw)
        except requests.RequestException as e:
            print("  transport error:", e)
            time.sleep(2 * (attempt + 1))
            continue
        if r.status_code == 429:                       # rate limited
            wait = int(r.headers.get("Retry-After", 5)) or 5
            print(f"  429 backoff {wait}s")
            time.sleep(wait)
            continue
        if r.status_code != 200:
            print(f"  HTTP {r.status_code}: {r.text[:200]}")
            return None
        time.sleep(SLEEP)
        return r.json()
    return None


def find_email(domain, title):
    org = (_call("GET", "/organizations/enrich", params={"domain": domain}) or {}).get("organization")
    if not org or not org.get("id"):
        return None
    body = {"organization_ids": [org["id"]],            # api_search only honors organization_ids
            "person_titles": [title] if title else [],
            "person_seniorities": ["c_suite", "vp", "head", "director"],
            "page": 1, "per_page": 5}
    people = (_call("POST", "/mixed_people/api_search", json=body) or {}).get("people", [])
    if not people:
        return None
    pid = people[0].get("id")
    person = (_call("POST", "/people/match", json={"id": pid, "reveal_personal_emails": False}) or {}).get("person", {})
    return person.get("email")


def main():
    if not KEY:
        print("no APOLLO_API_KEY set -> skipping enrichment (running on the CSV data). "
              "Add a key and re-run to fill missing emails.")
        return
    con = sqlite3.connect(DB)
    todo = con.execute("SELECT id, domain, title FROM contacts WHERE email='' OR email IS NULL").fetchall()
    print(f"enriching {len(todo)} rows missing an email via Apollo...")
    filled = 0
    for cid, domain, title in todo:
        if not domain:
            continue
        email = find_email(domain, title)
        if email:
            con.execute("UPDATE contacts SET email=? WHERE id=?", (email.lower(), cid))
            filled += 1
            print(f"  + {domain}: {email}")
    con.commit()
    con.close()
    print(f"filled {filled}/{len(todo)} emails.")


if __name__ == "__main__":
    main()
