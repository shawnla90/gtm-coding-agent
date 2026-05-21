"""Run column subagents per account. SQLite-cached, idempotent.

Inputs:
  - brief (from _load_brief)
  - accounts CSV (default targets/accounts.csv.example)
  - optional Exa research blob per account (skipped if EXA_API_KEY is unset)

Outputs:
  - enriched_accounts list of dicts, each containing all column outputs
  - cache.db persisted between runs
"""
from __future__ import annotations

import csv
import json
import os
import sqlite3
import sys
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional

from claude_subagent import ColumnSpec, load_column, run_column

CACHE_PATH = Path(os.environ.get("CACHE_DB", "cache.db"))


@dataclass
class Account:
    company: str
    domain: str
    contact_name: str = ""
    contact_title: str = ""
    owner: str = ""
    notes: str = ""
    research: dict = field(default_factory=dict)
    columns: dict = field(default_factory=dict)


def _cache() -> sqlite3.Connection:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(CACHE_PATH)
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS column_cache (
            domain TEXT,
            column_slug TEXT,
            output_json TEXT,
            updated_at INTEGER,
            PRIMARY KEY (domain, column_slug)
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS research_cache (
            domain TEXT PRIMARY KEY,
            research_json TEXT,
            updated_at INTEGER
        )
        """
    )
    return c


def load_accounts(csv_path: Path, limit: Optional[int] = None) -> list[Account]:
    rows = []
    with open(csv_path) as f:
        for i, r in enumerate(csv.DictReader(f)):
            if limit is not None and i >= limit:
                break
            rows.append(
                Account(
                    company=r.get("company", "").strip(),
                    domain=r.get("domain", "").strip(),
                    contact_name=r.get("contact_name", "").strip(),
                    contact_title=r.get("contact_title", "").strip(),
                    owner=r.get("owner", "").strip(),
                    notes=r.get("notes", "").strip(),
                )
            )
    return rows


def research_with_exa(account: Account) -> dict:
    """Hit Exa for a quick company summary. No-ops if EXA_API_KEY is unset."""
    api_key = os.environ.get("EXA_API_KEY", "").strip()
    if not api_key:
        return {"exa_summary": "", "note": "EXA_API_KEY not set; research skipped"}

    # Cache hit?
    with _cache() as c:
        row = c.execute(
            "SELECT research_json FROM research_cache WHERE domain = ?",
            (account.domain,),
        ).fetchone()
    if row:
        return json.loads(row[0])

    try:
        from exa_py import Exa

        exa = Exa(api_key=api_key)
        r = exa.search_and_contents(
            query=f"What does {account.company} ({account.domain}) do? Recent news, funding, hiring, GTM stack.",
            num_results=4,
            text=True,
        )
        snippets = [
            {"title": item.title, "url": item.url, "text": (item.text or "")[:1500]}
            for item in (r.results or [])
        ]
        out = {"exa_summary": json.dumps(snippets)[:6000]}
    except Exception as e:
        out = {"exa_summary": "", "note": f"exa error: {e}"}

    with _cache() as c:
        c.execute(
            "INSERT OR REPLACE INTO research_cache (domain, research_json, updated_at) VALUES (?, ?, ?)",
            (account.domain, json.dumps(out), int(time.time())),
        )
    return out


def _cached_column(domain: str, column_slug: str) -> Optional[dict]:
    with _cache() as c:
        row = c.execute(
            "SELECT output_json FROM column_cache WHERE domain = ? AND column_slug = ?",
            (domain, column_slug),
        ).fetchone()
    return json.loads(row[0]) if row else None


def _save_column(domain: str, column_slug: str, output: dict) -> None:
    with _cache() as c:
        c.execute(
            "INSERT OR REPLACE INTO column_cache (domain, column_slug, output_json, updated_at) VALUES (?, ?, ?, ?)",
            (domain, column_slug, json.dumps(output), int(time.time())),
        )


def _build_context(account: Account, brief, prior_columns: dict) -> dict:
    return {
        "account": {
            "company": account.company,
            "domain": account.domain,
            "contact_title": account.contact_title,
            "contact_name": account.contact_name,
            "notes": account.notes,
        },
        "brief": {
            "audience": brief.frontmatter.get("audience", ""),
            "pain_points_focus": brief.frontmatter.get("pain_points_focus", []),
            "brand_tone": brief.frontmatter.get("brand_tone", ""),
            "cta_label": brief.frontmatter.get("cta_label", ""),
        },
        "research": account.research,
        **prior_columns,
    }


def enrich(
    brief,
    accounts: list[Account],
    *,
    columns_dir: Path = Path("columns"),
    use_sdk: bool = False,
    force: bool = False,
    skip_research: bool = False,
) -> list[Account]:
    """Run every required column for every account. Resume-friendly."""
    column_files = {c: columns_dir / f"{c}.md" for c in brief.columns_required}
    missing = [c for c, p in column_files.items() if not p.exists()]
    if missing:
        raise FileNotFoundError(
            f"brief requires columns {missing} but no matching prompt files in {columns_dir}"
        )
    specs: dict[str, ColumnSpec] = {c: load_column(p) for c, p in column_files.items()}

    for account in accounts:
        sys.stderr.write(f"[enrich] {account.company} ({account.domain})\n")
        if not skip_research:
            account.research = research_with_exa(account)

        for slug in brief.columns_required:
            cached = None if force else _cached_column(account.domain, slug)
            if cached:
                account.columns[slug] = cached
                sys.stderr.write(f"  - {slug}: cache hit\n")
                continue
            ctx = _build_context(account, brief, account.columns)
            try:
                out = run_column(specs[slug], ctx, use_sdk=use_sdk)
            except Exception as e:
                sys.stderr.write(f"  ! {slug}: {e}\n")
                out = {"_error": str(e)}
            account.columns[slug] = out
            _save_column(account.domain, slug, out)
            sys.stderr.write(f"  + {slug}: ok\n")
    return accounts


if __name__ == "__main__":
    import argparse

    from dotenv import load_dotenv

    from _load_brief import load_brief

    load_dotenv()
    p = argparse.ArgumentParser(description="Run column subagents over a target list.")
    p.add_argument("brief_slug")
    p.add_argument("--accounts", default="targets/accounts.csv.example")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--use-sdk", action="store_true")
    p.add_argument("--force", action="store_true", help="ignore cache, re-run all columns")
    p.add_argument("--skip-research", action="store_true")
    args = p.parse_args()

    brief = load_brief(args.brief_slug)
    accounts = load_accounts(Path(args.accounts), limit=args.limit)
    enriched = enrich(
        brief, accounts, use_sdk=args.use_sdk, force=args.force, skip_research=args.skip_research
    )
    print(json.dumps([asdict(a) for a in enriched], indent=2, default=str))
