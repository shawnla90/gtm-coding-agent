#!/usr/bin/env python3
"""Minimal Apollo API client. Uses env vars for auth -- no hardcoded keys."""
import os
import sys
import time

try:
    import requests
except ImportError:
    sys.exit("pip install requests")

BASE = "https://api.apollo.io/api/v1"
RATE_LIMIT_SLEEP = 30


def _key() -> str:
    key = os.environ.get("APOLLO_API_KEY")
    if not key:
        from pathlib import Path
        env_file = Path(__file__).resolve().parents[1] / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("APOLLO_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"')
        if not key:
            sys.exit("APOLLO_API_KEY not set -- export it or add to .env")
    return key


def _headers() -> dict:
    return {
        "accept": "application/json",
        "Content-Type": "application/json",
        "X-Api-Key": _key(),
    }


def post(endpoint: str, body: dict, retries: int = 1) -> dict | None:
    url = f"{BASE}/{endpoint}"
    for attempt in range(retries + 1):
        resp = requests.post(url, headers=_headers(), json=body, timeout=45)
        if resp.status_code == 429:
            print(f"  rate-limited, sleeping {RATE_LIMIT_SLEEP}s")
            time.sleep(RATE_LIMIT_SLEEP)
            continue
        if resp.status_code != 200:
            print(f"  HTTP {resp.status_code}: {resp.text[:200]}")
            return None
        return resp.json()
    return None


def search_people(org_ids: list = None, titles: list = None,
                  seniorities: list = None, per_page: int = 25,
                  page: int = 1, **extra) -> list:
    body = {"per_page": per_page, "page": page}
    if org_ids:
        body["organization_ids"] = org_ids
    if titles:
        body["person_titles"] = titles
    if seniorities:
        body["person_seniorities"] = seniorities
    body.update(extra)
    data = post("mixed_people/api_search", body)
    return (data or {}).get("people", [])


def enrich_company(domain: str) -> dict | None:
    return post("organizations/enrich", {"domain": domain})


def search_companies(page: int = 1, per_page: int = 100, **filters) -> dict:
    """mixed_companies/search -- FREE (0 credits). Returns the raw response
    dict with 'organizations' and 'pagination' keys."""
    body = {"page": page, "per_page": per_page}
    body.update(filters)
    return post("mixed_companies/search", body) or {}


def match_person(first_name: str, last_name: str = None,
                 domain: str = None, title: str = None,
                 apollo_id: str = None) -> dict | None:
    body = {"first_name": first_name, "reveal_personal_emails": False}
    if last_name:
        body["last_name"] = last_name
    if domain:
        body["domain"] = domain
    if title:
        body["title"] = title
    if apollo_id:
        body["id"] = apollo_id
    data = post("people/match", body)
    return (data or {}).get("person")
