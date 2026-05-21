#!/usr/bin/env python3
"""HubSpot Landing Engine - CLI orchestrator.

Five steps, one CLI:

  python pipeline.py --step load     <brief_slug>     # parse and validate brief
  python pipeline.py --step enrich   <brief_slug>     # run column subagents
  python pipeline.py --step generate <brief_slug>     # build payloads
  python pipeline.py --step publish  <brief_slug>     # POST to HubSpot
  python pipeline.py --step all      <brief_slug>     # everything in sequence

Defaults:
  --accounts targets/accounts.csv.example
  --limit    no limit
  --state    DRAFT
  --dry-run  off  (set to print payloads without publishing)
  --use-sdk  off  (set to route Claude through the SDK, not the CLI)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from _enrich_accounts import enrich, load_accounts
from _generate_pages import generate
from _load_brief import load_brief
from _publish_pages import publish


def main():
    load_dotenv()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--step", default="all", choices=["load", "enrich", "generate", "publish", "all"])
    p.add_argument("brief_slug", nargs="?", default="abm-mid-market-saas")
    p.add_argument("--accounts", default="targets/accounts.csv.example")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--state", default="DRAFT", choices=["DRAFT", "PUBLISHED_OR_SCHEDULED"])
    p.add_argument("--dry-run", action="store_true", help="skip the publish HTTP call")
    p.add_argument("--use-sdk", action="store_true", help="use the anthropic SDK instead of the claude CLI")
    p.add_argument("--force", action="store_true", help="ignore column cache, re-enrich all rows")
    p.add_argument("--skip-research", action="store_true", help="skip the Exa research step")
    args = p.parse_args()

    sys.stderr.write(f"[pipeline] step={args.step} brief={args.brief_slug} limit={args.limit} state={args.state} dry-run={args.dry_run}\n")

    brief = load_brief(args.brief_slug)
    sys.stderr.write(f"[pipeline] loaded brief: {brief.slug} ({brief.campaign}, {len(brief.columns_required)} columns)\n")

    if args.step == "load":
        print(json.dumps(brief.frontmatter, indent=2, default=str))
        return

    accounts = load_accounts(Path(args.accounts), limit=args.limit)
    sys.stderr.write(f"[pipeline] loaded {len(accounts)} accounts from {args.accounts}\n")

    if args.step in ("enrich", "all"):
        enrich(
            brief, accounts,
            use_sdk=args.use_sdk, force=args.force, skip_research=args.skip_research,
        )
    if args.step == "enrich":
        print(json.dumps([a.__dict__ for a in accounts], indent=2, default=str))
        return

    if args.step in ("generate", "all"):
        payloads = generate(brief, accounts)
        sys.stderr.write(f"[pipeline] generated {len(payloads)} payloads -> outputs/{brief.slug}/\n")
    else:
        # publish-only mode reads from disk
        out_dir = Path("outputs") / brief.slug
        payloads = [json.loads(f.read_text()) for f in sorted(out_dir.glob("*.json"))]
        sys.stderr.write(f"[pipeline] loaded {len(payloads)} payloads from {out_dir}\n")

    if args.step == "generate":
        print(json.dumps(payloads, indent=2))
        return

    if args.step in ("publish", "all"):
        results = publish(payloads, state=args.state, dry_run=args.dry_run)
        print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
