#!/usr/bin/env python3
"""Minimal Apollo client for the employment check. Env-first auth, no hardcoded keys.

Only one endpoint is used here: people/match on a LinkedIn URL. It answers "is this person
still at the company on my list?" Apollo's identity graph follows the person across jobs, which
is the one thing an email-keyed graph cannot do. Optional: the pipeline runs without it.
"""
from __future__ import annotations

import json
import os
import sqlite3
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://api.apollo.io/api/v1"
SECRETS_DB = os.environ.get("SECRETS_DB", "")


def get_key() -> str | None:
    k = os.environ.get("APOLLO_API_KEY")
    if k:
        return k.strip()
    env_file = Path(__file__).resolve().parents[1] / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line.startswith("export "):
                line = line[7:]
            if line.startswith("APOLLO_API_KEY="):
                v = line.split("=", 1)[1].strip().strip('"').strip("'")
                if v and v != "your_api_key_here":
                    return v
    if SECRETS_DB:
        try:
            with sqlite3.connect(SECRETS_DB, timeout=10) as c:
                row = c.execute("SELECT value FROM secrets WHERE key='APOLLO_API_KEY'").fetchone()
                return row[0] if row else None
        except sqlite3.Error:
            return None
    return None


def people_match(linkedin_url: str, key: str | None = None) -> dict:
    """Apollo people/match by LinkedIn URL. Returns a flat dict, {} on any failure.
    Costs an enrichment credit on most plans. reveal_personal_emails stays False."""
    key = key or get_key()
    if not key or not linkedin_url:
        return {}
    body = {"linkedin_url": linkedin_url, "reveal_personal_emails": False}
    req = urllib.request.Request(
        f"{BASE}/people/match", data=json.dumps(body).encode(), method="POST",
        headers={"X-Api-Key": key, "Content-Type": "application/json", "Cache-Control": "no-cache"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        return {"http": e.code}
    except Exception:
        return {}
    p = data.get("person") or {}
    if not p:
        return {"http": 200}
    org = p.get("organization") or {}
    return {
        "http": 200,
        "email": (p.get("email") or "").lower(),
        "email_status": p.get("email_status") or "",
        "title": p.get("title") or "",
        "company": org.get("name") or "",
        "company_domain": (org.get("primary_domain") or "").lower(),
        "linkedin_url": p.get("linkedin_url") or "",
    }
