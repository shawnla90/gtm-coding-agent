"""POST the generated payloads to the HubSpot Pages API.

DRAFT-first by default. Slug collisions trigger an auto-rename loop (-v2, -v3).
Rate-limit aware: respects 429 + Retry-After.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from typing import Optional

import requests

from auth_private_app import headers

LANDING_PAGES_URL = "https://api.hubapi.com/cms/v3/pages/landing-pages"
PUBLISH_ACTION_URL = "https://api.hubapi.com/cms/v3/pages/landing-pages/{id}/publish-action"
MAX_SLUG_ATTEMPTS = 6


def _safe_state_for(requested: str) -> str:
    """Cap the requested state at HUBSPOT_PAGE_STATE_CAP from .env.

    Default cap is DRAFT. If you want to actually publish from the pipeline,
    set HUBSPOT_PAGE_STATE_CAP=PUBLISHED_OR_SCHEDULED in your .env. The
    two-key gate is intentional: it should take more than one config tweak
    to push pages live.
    """
    cap = (os.environ.get("HUBSPOT_PAGE_STATE_CAP") or "DRAFT").upper()
    requested = (requested or "DRAFT").upper()
    order = ["DRAFT", "PUBLISHED_OR_SCHEDULED"]
    return requested if order.index(requested) <= order.index(cap) else cap


def _bump_slug(slug: str, attempt: int) -> str:
    base = re.sub(r"-v\d+$", "", slug)
    return f"{base}-v{attempt + 1}"


def _post_with_retry(url: str, payload: dict, *, timeout: int = 15) -> requests.Response:
    """POST with one 429-aware retry."""
    for attempt in range(2):
        resp = requests.post(url, headers=headers(), json=payload, timeout=timeout)
        if resp.status_code != 429:
            return resp
        delay = int(resp.headers.get("Retry-After", 10))
        sys.stderr.write(f"[publish] 429 rate-limited, sleeping {delay}s\n")
        time.sleep(delay)
    return resp


def publish_one(payload: dict, *, requested_state: str = "DRAFT", dry_run: bool = False) -> dict:
    """Publish one landing page. Returns {id, url, status} dict.

    On 409 (slug collision), retries up to MAX_SLUG_ATTEMPTS with -v2, -v3, etc.
    """
    payload = dict(payload)
    payload["state"] = _safe_state_for(requested_state)

    if dry_run:
        return {
            "id": None,
            "url": f"DRY-RUN https://your-portal.hubspotpagebuilder.com/{payload['slug']}",
            "status": "dry-run",
            "slug": payload["slug"],
        }

    for attempt in range(MAX_SLUG_ATTEMPTS):
        resp = _post_with_retry(LANDING_PAGES_URL, payload)
        if resp.status_code in (200, 201):
            data = resp.json()
            return {
                "id": data.get("id"),
                "url": data.get("url", ""),
                "status": "ok",
                "slug": payload["slug"],
            }
        if resp.status_code == 409:
            payload["slug"] = _bump_slug(payload["slug"], attempt + 1)
            sys.stderr.write(f"[publish] 409 slug collision, retrying with '{payload['slug']}'\n")
            continue
        # Anything else: surface the error and stop.
        return {
            "id": None,
            "url": "",
            "status": f"error-{resp.status_code}",
            "slug": payload["slug"],
            "error": resp.text[:400],
        }

    return {
        "id": None,
        "url": "",
        "status": "error-slug-exhausted",
        "slug": payload["slug"],
        "error": f"could not find an available slug after {MAX_SLUG_ATTEMPTS} tries",
    }


def publish(payloads: list[dict], *, state: str = "DRAFT", dry_run: bool = False) -> list[dict]:
    results = []
    for i, payload in enumerate(payloads, 1):
        sys.stderr.write(f"[publish] {i}/{len(payloads)} -> {payload['name']}\n")
        result = publish_one(payload, requested_state=state, dry_run=dry_run)
        results.append({**result, "name": payload["name"]})
        # Small sleep between calls to stay well under the 10-second burst cap.
        time.sleep(0.5)
    return results


if __name__ == "__main__":
    import argparse
    from pathlib import Path

    from dotenv import load_dotenv

    load_dotenv()
    p = argparse.ArgumentParser(description="Publish prebuilt payloads to HubSpot.")
    p.add_argument("payload_dir", help="dir containing one JSON payload per page (outputs/{slug}/)")
    p.add_argument("--state", default="DRAFT", choices=["DRAFT", "PUBLISHED_OR_SCHEDULED"])
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    payloads = [json.loads(f.read_text()) for f in sorted(Path(args.payload_dir).glob("*.json"))]
    results = publish(payloads, state=args.state, dry_run=args.dry_run)
    print(json.dumps(results, indent=2))
