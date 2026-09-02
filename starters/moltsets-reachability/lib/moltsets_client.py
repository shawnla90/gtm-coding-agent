#!/usr/bin/env python3
"""moltsets_client.py -- a small, never-raising Moltsets API client with a local ledger.

Moltsets (api.moltsets.com) is a people-search + email-grading API. Every endpoint is a POST
to https://api.moltsets.com/api/v1/tools/<endpoint> with a Bearer key. This client:

  * reads the key env-first (MOLTSETS_API_KEY), then ../.env, then an optional local vault
    (SECRETS_DB=/path/to/vault.db with a secrets(key, value) table). The key is never printed.
  * never raises on HTTP errors. 404 is a COVERAGE GAP (the person is not in the graph), not a
    bad email, and it costs nothing. You get (status, results, metadata) back every time.
  * logs every call to a local SQLite table so you have your own burn history. The API keeps
    none for you, and records ARE consumed if your client crashes mid-batch. Commit per row.
  * reads the fair-use counters off every data response and stops the batch at a floor.

Grades come back on two different field names depending on the endpoint:
  reverse_email_lookup / search_business_profile_by_name  -> results.work_email_confirmed_risk_score
  search_people (list under results.results)              -> business_email_risk_score
  linkedin_to_best_email / linkedin_to_business_email     -> results.risk_score
grade_of() normalizes all three.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://api.moltsets.com/api/v1/tools/"
SECRETS_DB = os.environ.get("SECRETS_DB", "")  # optional: sqlite file with a secrets(key,value) table
RECORDS_FLOOR = int(os.environ.get("MOLTSETS_RECORDS_FLOOR", "25"))  # stop the batch under this many 5h records
PHONE_TOKEN_COST = 1    # phone tokens per linkedin_to_mobile_phone HIT (misses are free; $97 plan = 50/month)
PHONE_FLOOR = int(os.environ.get("MOLTSETS_PHONE_FLOOR", "20"))  # never spend below this many phone tokens
SLEEP = 0.3

FREE_ENDPOINTS = ("get_account", "get_billing", "get_usage")

FREEMAIL = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com", "icloud.com",
    "proton.me", "protonmail.com", "live.com", "me.com", "msn.com", "ymail.com",
}

LOG_SCHEMA = """
CREATE TABLE IF NOT EXISTS moltsets_api_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT, endpoint TEXT, request TEXT, http_status TEXT,
  ext_tokens_used INTEGER, ext_tokens_remaining INTEGER,
  records_remaining_5h INTEGER, records_remaining_1w INTEGER,
  phone_tokens_remaining INTEGER, note TEXT
);
"""


def get_key() -> str | None:
    k = os.environ.get("MOLTSETS_API_KEY")
    if k:
        return k.strip()
    env_file = Path(__file__).resolve().parents[1] / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line.startswith("export "):
                line = line[7:]
            if line.startswith("MOLTSETS_API_KEY="):
                v = line.split("=", 1)[1].strip().strip('"').strip("'")
                if v and v != "your_api_key_here":
                    return v
    if SECRETS_DB:
        try:
            with sqlite3.connect(SECRETS_DB, timeout=10) as c:
                row = c.execute("SELECT value FROM secrets WHERE key='MOLTSETS_API_KEY'").fetchone()
                return row[0] if row else None
        except sqlite3.Error:
            return None
    return None


def dom(email: str | None) -> str:
    return (email or "").split("@")[-1].lower().strip()


def call(endpoint: str, body: dict | None = None, key: str | None = None, timeout: int = 45):
    """POST one endpoint. Returns (status, results, metadata). Never raises.

    status is an int HTTP code, or "ERR" (network/parse failure) or "NOKEY".
    results is the `results` object (dict; for search_people the list is under results["results"]).
    """
    key = key or get_key()
    if not key:
        return "NOKEY", {}, {}
    req = urllib.request.Request(
        BASE + endpoint, data=json.dumps(body or {}).encode(), method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            status, payload = r.status, json.load(r)
    except urllib.error.HTTPError as e:
        status = e.code
        try:
            payload = json.loads(e.read().decode() or "{}")
        except Exception:
            payload = {}
    except Exception as e:  # network, timeout, JSON
        status, payload = "ERR", {"error": str(e)[:200]}
    if not isinstance(payload, dict):
        payload = {}
    results = payload.get("results")
    if not isinstance(results, dict):
        results = {"results": results} if isinstance(results, list) else {}
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    return status, results, metadata


def fair_use(results: dict, metadata: dict) -> dict:
    """Pull the fair-use counters. They ride only on DATA endpoints; free status calls omit them.
    Shapes seen live: metadata.fair_use.records_remaining_5h (flat) and, on get_account,
    results.fair_use.{enrich,search}.records.{5h,1w}.remaining (nested)."""
    fu = (metadata or {}).get("fair_use") or (results or {}).get("fair_use") or {}
    if not isinstance(fu, dict):
        fu = {}
    out = {"records_remaining_5h": fu.get("records_remaining_5h"),
           "records_remaining_1w": fu.get("records_remaining_1w"),
           "ext_tokens_used": (metadata or {}).get("external_tokens_used"),
           "ext_tokens_remaining": (metadata or {}).get("external_tokens_remaining"),
           "phone_tokens_remaining": (results or {}).get("phone_token_balance"),
           "pools": {}}
    for pool in ("enrich", "search"):
        p = fu.get(pool)
        if isinstance(p, dict):
            rec = p.get("records") or {}
            out["pools"][pool] = {
                "remaining_5h": (rec.get("5h") or {}).get("remaining"),
                "used_1w": (rec.get("1w") or {}).get("used"),
                "remaining_1w": (rec.get("1w") or {}).get("remaining"),
            }
    return out


def ensure_log(con: sqlite3.Connection) -> None:
    con.executescript(LOG_SCHEMA)


def log_call(con: sqlite3.Connection, endpoint: str, body: dict, status, results: dict,
             metadata: dict, note: str = "") -> dict:
    """Append one row to the ledger and commit immediately. Returns the fair-use dict."""
    fu = fair_use(results, metadata)
    con.execute(
        """INSERT INTO moltsets_api_log (ts, endpoint, request, http_status, ext_tokens_used,
           ext_tokens_remaining, records_remaining_5h, records_remaining_1w,
           phone_tokens_remaining, note) VALUES (datetime('now'),?,?,?,?,?,?,?,?,?)""",
        (endpoint, json.dumps(body or {}), str(status), fu["ext_tokens_used"],
         fu["ext_tokens_remaining"], fu["records_remaining_5h"], fu["records_remaining_1w"],
         fu["phone_tokens_remaining"], note),
    )
    con.commit()
    return fu


def grade_of(rec: dict) -> str:
    """Normalize the A-F grade across the three response shapes. '' when absent."""
    if not isinstance(rec, dict):
        return ""
    for k in ("work_email_confirmed_risk_score", "business_email_risk_score", "risk_score"):
        v = rec.get(k)
        if v:
            return str(v).strip().upper()[:1]
    return ""


def email_of(rec: dict) -> str:
    if not isinstance(rec, dict):
        return ""
    for k in ("work_email_confirmed", "business_email", "email"):
        v = rec.get(k)
        if v:
            return str(v).strip().lower()
    return ""


def validated_at_of(rec: dict) -> str:
    if not isinstance(rec, dict):
        return ""
    # reverse_email_lookup puts the confirmation DATE under *_status, despite the name
    for k in ("work_email_confirmed_status", "business_email_validated_at", "last_validated_at"):
        v = rec.get(k)
        if v:
            return str(v)
    return ""


def linkedin_of(rec: dict) -> str:
    if not isinstance(rec, dict):
        return ""
    for k in ("linkedin_url", "linkedinurl"):
        v = rec.get(k)
        if v:
            return str(v).strip()
    return ""


def company_of(rec: dict) -> tuple[str, str]:
    """(company_name, company_domain) across shapes."""
    if not isinstance(rec, dict):
        return "", ""
    c = rec.get("company")
    if isinstance(c, dict):
        return str(c.get("name") or ""), str(c.get("domain") or "").lower()
    name = rec.get("current_company") or ""
    url = rec.get("current_company_url") or ""
    host = url.lower().replace("https://", "").replace("http://", "").split("/")[0]
    if host.startswith("www."):
        host = host[4:]
    return str(name), host


class Budget:
    """Tracks the fair-use floor and the phone-token floor across a batch."""

    def __init__(self, records_floor: int = RECORDS_FLOOR, phone_floor: int = PHONE_FLOOR):
        self.records_floor = records_floor
        self.phone_floor = phone_floor
        self.records_5h = None
        self.phone_tokens = None
        self.ext_tokens = None

    def absorb(self, fu: dict) -> None:
        if fu.get("records_remaining_5h") is not None:
            self.records_5h = fu["records_remaining_5h"]
        if fu.get("phone_tokens_remaining") is not None:
            self.phone_tokens = fu["phone_tokens_remaining"]
        if fu.get("ext_tokens_remaining") is not None:
            self.ext_tokens = fu["ext_tokens_remaining"]

    def records_ok(self) -> bool:
        return self.records_5h is None or self.records_5h > self.records_floor

    def phone_ok(self) -> bool:
        return self.phone_tokens is None or self.phone_tokens - PHONE_TOKEN_COST >= self.phone_floor


def account_snapshot(key: str | None = None) -> dict:
    """One free get_account call -> {plan, enrich/search pools, phone tokens}. Never raises."""
    st, res, md = call("get_account", {}, key=key, timeout=30)
    fu = fair_use(res, md)
    return {"http": st, "plan": res.get("plan"), "pools": fu["pools"],
            "phone_tokens_remaining": res.get("phone_token_balance"),
            "phone_token_allowance": res.get("phone_token_allowance"),
            "personal_email_available": res.get("personal_email_available")}


def pause() -> None:
    time.sleep(SLEEP)
