"""Multi-portal OAuth flow for agency/managed mode.

Private app tokens (auth_private_app.py) are scoped to ONE HubSpot portal.
Agencies running a single tool across many client portals want OAuth instead.

This module implements the minimum viable OAuth handshake plus a SQLite-backed
token store keyed by hub_id. The chapter has a section on when to graduate
to this; most readers stay on private app tokens.

Reference: https://developers.hubspot.com/docs/guides/apps/authentication/working-with-oauth
"""
from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path
from typing import Optional

import requests

AUTH_URL = "https://app.hubspot.com/oauth/authorize"
TOKEN_URL = "https://api.hubapi.com/oauth/v1/token"
DB_PATH = Path(os.environ.get("OAUTH_DB", "oauth_tokens.db"))
ACCESS_TOKEN_TTL_SEC = 1800  # HubSpot OAuth access tokens last 30 minutes
REFRESH_WINDOW_SEC = 300     # refresh 5 min before expiry


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS oauth_tokens (
            hub_id INTEGER PRIMARY KEY,
            access_token TEXT NOT NULL,
            refresh_token TEXT NOT NULL,
            expires_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        )
        """
    )
    return c


def authorize_url(client_id: str, redirect_uri: str, scopes: list[str]) -> str:
    """Build the URL you send the user to for portal authorization."""
    scope_str = " ".join(scopes)
    return (
        f"{AUTH_URL}?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&scope={scope_str}"
    )


def exchange_code(client_id: str, client_secret: str, redirect_uri: str, code: str) -> dict:
    """Exchange an auth code for access + refresh tokens. Returns the full payload."""
    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "code": code,
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def store_tokens(hub_id: int, payload: dict) -> None:
    """Persist tokens for a portal. Call after exchange_code or refresh."""
    now = int(time.time())
    expires_at = now + int(payload.get("expires_in", ACCESS_TOKEN_TTL_SEC))
    with _conn() as c:
        c.execute(
            """
            INSERT INTO oauth_tokens (hub_id, access_token, refresh_token, expires_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(hub_id) DO UPDATE SET
                access_token = excluded.access_token,
                refresh_token = excluded.refresh_token,
                expires_at    = excluded.expires_at,
                updated_at    = excluded.updated_at
            """,
            (hub_id, payload["access_token"], payload["refresh_token"], expires_at, now),
        )


def get_access_token(hub_id: int, client_id: str, client_secret: str) -> Optional[str]:
    """Return a valid access token for the portal. Refreshes if near expiry."""
    with _conn() as c:
        row = c.execute(
            "SELECT access_token, refresh_token, expires_at FROM oauth_tokens WHERE hub_id = ?",
            (hub_id,),
        ).fetchone()
    if row is None:
        return None
    access_token, refresh_token, expires_at = row
    now = int(time.time())
    if expires_at - now > REFRESH_WINDOW_SEC:
        return access_token
    # refresh
    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
        },
        timeout=10,
    )
    resp.raise_for_status()
    payload = resp.json()
    store_tokens(hub_id, payload)
    return payload["access_token"]


def headers_for_hub(hub_id: int) -> dict:
    """Convenience: bearer headers for an arbitrary portal."""
    client_id = os.environ["HUBSPOT_CLIENT_ID"]
    client_secret = os.environ["HUBSPOT_CLIENT_SECRET"]
    token = get_access_token(hub_id, client_id, client_secret)
    if token is None:
        raise RuntimeError(
            f"No stored tokens for hub_id={hub_id}. Run the auth flow first."
        )
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
