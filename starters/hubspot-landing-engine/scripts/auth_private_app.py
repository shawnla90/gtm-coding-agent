"""Private app token loader. Single-portal auth, simplest path.

The chapter section "Connect" walks through scoping. The only scope this needs
is `content` (umbrella for CMS pages).
"""
from __future__ import annotations

import os
import sys


def get_token() -> str:
    """Return the HubSpot private app token from the environment.

    Raises SystemExit with a useful message if missing or unset. Better to fail
    early than to make four API calls before realizing the token is empty.
    """
    token = os.environ.get("HUBSPOT_PRIVATE_APP_TOKEN", "").strip()
    if not token or token == "pat-na1-replace-me":
        sys.stderr.write(
            "HUBSPOT_PRIVATE_APP_TOKEN is not set.\n"
            "Create a private app in HubSpot (Settings -> Integrations -> Private Apps), "
            "add the `content` scope, copy the token, and paste it into .env.\n"
        )
        raise SystemExit(2)
    return token


def headers() -> dict:
    """Standard auth + content-type headers for HubSpot v3 endpoints."""
    return {
        "Authorization": f"Bearer {get_token()}",
        "Content-Type": "application/json",
    }


if __name__ == "__main__":
    # Smoke test: print the auth header (token redacted) so you can verify the
    # token is loading from .env.
    from dotenv import load_dotenv

    load_dotenv()
    h = headers()
    auth = h["Authorization"]
    head, _, tail = auth.partition(" ")
    redacted = f"{head} {tail[:10]}...{tail[-4:]}" if len(tail) > 14 else f"{head} (short)"
    print(f"Authorization header looks like: {redacted}")
