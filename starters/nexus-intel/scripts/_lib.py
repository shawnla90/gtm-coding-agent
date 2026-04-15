"""Shared helpers for Nexus Intel scrapers + analyzer.

- get_db() — opens the intel.db SQLite connection
- get_api_key() — loads ANTHROPIC_API_KEY from env or .env.local
- run_apify_actor() — subprocess wrapper around the `apify` CLI
- start_scrape_run / finish_scrape_run — bookend entries in scrape_runs
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "data" / "intel.db"
ENV_FILE = REPO_ROOT / ".env.local"


def get_db() -> sqlite3.Connection:
    if not DB_PATH.exists():
        sys.exit(
            f"intel.db not found at {DB_PATH}. Run scripts/init_db.py first."
        )
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def _load_env_file() -> dict[str, str]:
    """Parse .env.local (if present) into a dict."""
    out: dict[str, str] = {}
    if not ENV_FILE.exists():
        return out
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def get_env(key: str, default: str | None = None) -> str | None:
    val = os.environ.get(key)
    if val:
        return val
    return _load_env_file().get(key, default)


def get_api_key() -> str:
    key = get_env("ANTHROPIC_API_KEY")
    if not key:
        sys.exit(
            "ANTHROPIC_API_KEY not found. Set it in the environment or intel/.env.local"
        )
    return key


def get_apify_token() -> str:
    token = get_env("APIFY_TOKEN")
    if not token:
        sys.exit(
            "APIFY_TOKEN not found. Set it in the environment or intel/.env.local"
        )
    return token


def run_apify_actor(
    actor_id: str,
    input_data: dict[str, Any],
    timeout: int = 600,
) -> list[dict[str, Any]] | None:
    """Run an Apify actor via the local CLI and return the dataset items.

    Assumes the user has already authenticated the CLI (`apify login`).
    Returns None on error, [] if no items.
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(input_data, f)
        input_file = f.name

    try:
        print(f"  › apify call {actor_id} (timeout={timeout}s)")
        result = subprocess.run(
            [
                "apify",
                "call",
                actor_id,
                "-f",
                input_file,
                "-o",
                "-t",
                str(timeout),
            ],
            capture_output=True,
            text=True,
            timeout=timeout + 60,
        )
        if result.returncode != 0:
            err_lines = [
                l
                for l in result.stderr.splitlines()
                if "old version" not in l and "Run npm" not in l
            ]
            if err_lines:
                print(f"  ✗ apify error: {' '.join(err_lines)[:220]}")
            return None

        stdout = result.stdout
        start = stdout.find("[{")
        if start < 0:
            if stdout.find("[]") >= 0:
                return []
            print("  ✗ no JSON in apify output")
            return None
        try:
            data = json.loads(stdout[start:])
            return data if isinstance(data, list) else [data]
        except json.JSONDecodeError as e:
            print(f"  ✗ failed to parse apify JSON: {e}")
            dump_path = REPO_ROOT / "data" / f"apify-raw-{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.txt"
            dump_path.write_text(stdout)
            print(f"    raw dump saved to {dump_path}")
            return None
    except subprocess.TimeoutExpired:
        print("  ✗ apify call timed out")
        return None
    finally:
        os.unlink(input_file)


def start_scrape_run(
    conn: sqlite3.Connection,
    name: str,
    target: str,
    platforms: str,
) -> int:
    cur = conn.execute(
        "INSERT INTO scrape_runs (name, target, platforms) VALUES (?, ?, ?)",
        (name, target, platforms),
    )
    conn.commit()
    return int(cur.lastrowid)


def finish_scrape_run(
    conn: sqlite3.Connection,
    run_id: int,
    items_ingested: int,
    sources_added: int = 0,
) -> None:
    conn.execute(
        "UPDATE scrape_runs SET items_ingested = ?, sources_added = ?, completed_at = datetime('now') WHERE id = ?",
        (items_ingested, sources_added, run_id),
    )
    conn.commit()
