#!/usr/bin/env python3
"""exa_client.py — a tiny, HARD-CAPPED Exa client for retrieval checks.

Exa /search returns an independent search result set. It can show whether a brand or source is
retrievable for a buyer question, but it cannot prove that ChatGPT, Claude, Perplexity, Google, or
another answer engine named or cited that result. That requires a receipt from the answer itself.
This client runs a SMALL, capped query set so a retrieval check never burns the balance. Key from
the EXA_API_KEY env var. Every function degrades to {available: False} on any error, never raises.

CAP: MAX_QUERIES per call (default 8). A caller cannot exceed it even by passing more queries.
"""
from __future__ import annotations

import json
import os
import sqlite3
import urllib.request
from pathlib import Path

EXA_API = "https://api.exa.ai"
MAX_QUERIES = int(os.environ.get("EXA_MAX_QUERIES", "8"))  # hard cap, protects the balance
SECRETS_DB = os.environ.get("SECRETS_DB", "")  # optional: sqlite file with a secrets(key,value) table


def get_key() -> str | None:
    k = os.environ.get("EXA_API_KEY")
    if k:
        return k.strip()
    if SECRETS_DB:
        try:
            with sqlite3.connect(SECRETS_DB, timeout=10) as c:
                row = c.execute("SELECT value FROM secrets WHERE key='EXA_API_KEY'").fetchone()
                return row[0] if row else None
        except sqlite3.Error:
            return None
    return None


def _search(query: str, key: str, num: int = 10) -> dict:
    body = json.dumps({"query": query, "type": "auto", "numResults": num,
                       "contents": {"highlights": True}}).encode()
    req = urllib.request.Request(f"{EXA_API}/search", data=body, method="POST",
                                 headers={"content-type": "application/json", "x-api-key": key})
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.load(r)


def retrieval_visibility(name: str, queries: list[str], key: str | None = None) -> dict:
    """Share of buyer-intent queries where `name` surfaces in Exa results. Capped."""
    key = key or get_key()
    if not key:
        return {"available": False, "reason": "no EXA_API_KEY"}
    q = list(dict.fromkeys(queries))[:MAX_QUERIES]  # dedup + hard cap
    hits, checked, detail = 0, 0, []
    for query in q:
        try:
            res = _search(query, key)
            appears = name.lower() in json.dumps(res.get("results", [])).lower()
            hits += 1 if appears else 0
            checked += 1
            detail.append({"query": query, "appears": appears})
        except Exception:
            continue
    return {"score": round(100 * hits / checked) if checked else 0,
            "checked": checked, "capped_at": MAX_QUERIES, "queries": detail,
            "available": checked > 0}


def ai_visibility(name: str, queries: list[str], key: str | None = None) -> dict:
    """Backward-compatible alias. The evidence is retrieval visibility, not AI citation."""
    return retrieval_visibility(name, queries, key)
