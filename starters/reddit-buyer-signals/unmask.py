#!/usr/bin/env python3
"""unmask.py - the lead-unmasking pass over a client's classified Reddit opportunities.

Three-step review gate, then enrichment. Reddit is pseudonymous, so you enrich the COMPANY, never the
person. Only an exact company domain published on the author's own Reddit profile is automatically
eligible. Search, thread-domain, and brand-handle matches are manual-review candidates. Pseudonymous
threads stay Reddit conversations. This does not de-anonymize anyone.

The gate checks three things, in order:
  1. Reddit profile (--profile)  exact self-disclosure can become enrichment-eligible
  2. Web/thread candidates       search or thread domains require manual review
  3. Brand-handle heuristic      username patterns require manual review

  # gate only (default, no external calls): collect thread and handle candidates
  python3 unmask.py --ops data/ops_classified.json --out data/unmasked.json

  # gate with profile lookup: direct profile evidence, candidates, absence, or errors
  python3 unmask.py --ops data/ops_classified.json --profile --out data/unmasked.json

  # gate + live enrich only exact profile-disclosed domains through your backend
  python3 unmask.py --ops data/ops_classified.json --profile --enrich --out data/unmasked.json

Enrichment backend is pluggable. The default shells the Freckle CLI (saved workflow
"enrich-domain-score-icp-contacts-omnibound", org clearbox): invoke -> poll -> inspect, returning the
company, the ICP tier, and the buying-role contacts. Swap enrich_domain() for Clay, Base Loop, Apollo,
Deepline, or any waterfall a client already runs. Never enriches without --enrich.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

# The saved Freckle workflow: domain -> company + ICP tier + buying-role contacts.
# Set both to YOUR workflow id and org slug (freckle workflow saved list): no defaults ship here.
FRECKLE_WORKFLOW = os.environ.get("FRECKLE_WORKFLOW_ID", "")
FRECKLE_ORG = os.environ.get("FRECKLE_ORG_ID", "")

DOMAIN_RE = re.compile(r"\b([a-z0-9][a-z0-9-]{1,}\.(?:com|io|ai|co|team|app|dev|net|org))\b", re.I)
BRAND_HANDLE_RE = re.compile(
    r"(technolog|labs?|systems|software|agency|studio|solutions|-ai|-io|-hq|-inc)$", re.I)
# domains that appear in threads but are never the author's own company
IGNORE_DOMAINS = {"reddit.com", "redd.it", "google.com", "youtube.com", "github.com",
                  "linkedin.com", "twitter.com", "x.com", "notion.so", "medium.com",
                  "substack.com", "loom.com", "imgur.com"}


def _gate_result(
    verdict: str,
    *,
    signal: str,
    source: str,
    domain: str | None = None,
    candidate_domains: list[str] | None = None,
    evidence: list[dict] | None = None,
    profile_lookup_status: str = "not_checked",
) -> dict:
    candidate_domains = candidate_domains or []
    direct = verdict == "direct_disclosure" and bool(domain)
    return {
        "disclosed": direct,
        "review_verdict": verdict,
        "enrichment_eligibility": "eligible_direct_disclosure" if direct else (
            "manual_review" if verdict == "plausible_candidate" else "not_eligible"
        ),
        "profile_lookup_status": profile_lookup_status,
        "signal": signal,
        "source": source,
        "domain": domain if direct else None,
        "candidate_domain": candidate_domains[0] if candidate_domains else None,
        "candidate_domains": candidate_domains,
        "evidence": evidence or [],
        "action": (
            "reply first, then enrich the company"
            if direct
            else "review the evidence; do not enrich yet"
            if verdict == "plausible_candidate"
            else "retry the lookup before deciding"
            if verdict == "lookup_error"
            else "stays a Reddit conversation, reply on the thread"
        ),
    }


def disclose(op: dict, use_profile: bool = False) -> dict:
    """The three-step disclosure gate.

    Step 1 (--profile): exact evidence on the author's Reddit profile may qualify.
    Search-only matches are candidates. Step 2 thread domains and Step 3 brand-like
    handles are also candidates because neither proves the author owns the company.
    """
    author = op.get("author") or ""
    profile_status = "not_checked"
    profile_error = None
    candidates = []

    # Step 1: profile lookup (opt-in)
    if use_profile and author:
        try:
            from lib.profile_lookup import lookup_profile
            result = lookup_profile(author)
            profile_status = result.get("lookup_status", "lookup_error")
            if (
                result.get("review_verdict") == "direct_disclosure"
                and result.get("enrichment_eligibility") == "eligible_direct_disclosure"
                and result.get("domains")
                and result.get("evidence")
            ):
                return _gate_result(
                    "direct_disclosure",
                    signal=f"Reddit profile self-disclosure ({result['source']}): {result['signal']}",
                    source=result.get("source", "reddit_profile"),
                    domain=result["domains"][0],
                    evidence=result.get("evidence", []),
                    profile_lookup_status=profile_status,
                )
            if result.get("review_verdict") == "plausible_candidate":
                candidates.append({
                    "source": result.get("source", "web_search"),
                    "domains": result.get("domains", []),
                    "signal": result.get("signal", "search candidate"),
                    "evidence": result.get("evidence", []),
                })
            elif result.get("review_verdict") == "lookup_error":
                profile_error = result.get("signal", "profile lookup failed")
        except ImportError:
            profile_status = "lookup_error"
            profile_error = "profile lookup module unavailable"

    # Step 2: in-thread domains are candidates, not proof of ownership.
    text = f"{op.get('summary', '')} {op.get('snippet', '')}"
    thread_domains = []
    for m in DOMAIN_RE.finditer(text):
        dom = m.group(1).lower()
        root = ".".join(dom.split(".")[-2:])
        if root in IGNORE_DOMAINS or dom in thread_domains:
            continue
        thread_domains.append(dom)
    if thread_domains:
        candidates.append({
            "source": "thread_domain",
            "domains": thread_domains,
            "signal": "company domain appeared in the thread; ownership is not established",
            "evidence": [{
                "url": op.get("permalink") or op.get("url"),
                "kind": "thread_domain_candidate",
                "excerpt": text.strip()[:300],
            }],
        })

    # Step 3: a brand-like handle is a candidate only.
    if BRAND_HANDLE_RE.search(author):
        candidates.append({
            "source": "brand_handle",
            "domains": [],
            "signal": "author handle looks like a brand; ownership is not established",
            "evidence": [{
                "url": f"https://www.reddit.com/user/{author}/",
                "kind": "brand_handle_candidate",
                "excerpt": author,
            }],
        })

    if candidates:
        candidate_domains = []
        evidence = []
        for candidate in candidates:
            candidate_domains.extend(candidate["domains"])
            evidence.extend(candidate["evidence"])
        candidate_domains = list(dict.fromkeys(candidate_domains))
        return _gate_result(
            "plausible_candidate",
            signal="; ".join(candidate["signal"] for candidate in candidates),
            source="+".join(candidate["source"] for candidate in candidates),
            candidate_domains=candidate_domains,
            evidence=evidence,
            profile_lookup_status=profile_status,
        )

    if use_profile and profile_error:
        return _gate_result(
            "lookup_error",
            signal=profile_error,
            source="profile_lookup",
            profile_lookup_status=profile_status,
        )
    return _gate_result(
        "no_public_evidence",
        signal="no direct disclosure or candidate found in the checked sources",
        source="none",
        profile_lookup_status=profile_status,
    )


def is_lead(op: dict) -> bool:
    """A lead-classified op, in either the raw Clearbox shape (kind) or the classified shape (lane)."""
    return (op.get("kind") or "").lower() == "lead" or op.get("lane") == "lead_enrich"


def enrich_domain(domain: str, timeout_s: int = 240) -> dict:
    """Invoke the enrichment backend for one domain and return its result (or a plain error dict).

    Pluggable seam: this is the one function to replace with your orchestration tool. The default
    shells the Freckle CLI. Swap it for Clay, Base Loop, Deepline, Apollo, or your own waterfall.
    """
    if not shutil.which("freckle"):
        return {"domain": domain, "error": "freckle CLI not found; plug your enrichment backend into "
                                            "enrich_domain() (Clay, Base Loop, Deepline, Apollo, or your own waterfall)"}
    if not FRECKLE_WORKFLOW or not FRECKLE_ORG:
        return {"domain": domain, "error": "set FRECKLE_WORKFLOW_ID and FRECKLE_ORG_ID to your saved "
                                            "workflow (freckle workflow saved list)"}
    try:
        inv = subprocess.run(
            ["freckle", "workflow", "saved", "invoke", FRECKLE_WORKFLOW,
             "--org", FRECKLE_ORG, "--json", json.dumps({"domain": domain})],
            capture_output=True, text=True, timeout=90)
        out = (inv.stdout or "") + "\n" + (inv.stderr or "")
        m = re.search(r"\b([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\b", out)
        if not m:
            return {"domain": domain, "error": "no runId returned from invoke", "raw": out.strip()[:800]}
        run_id = m.group(1)
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            insp = subprocess.run(
                ["freckle", "workflow", "runs", "inspect", run_id, "--org", FRECKLE_ORG],
                capture_output=True, text=True, timeout=60)
            body = insp.stdout or ""
            if re.search(r"\bstatus:\s*completed\b", body) or '"status": "completed"' in body:
                return {"domain": domain, "run_id": run_id, "status": "completed", "result": body.strip()}
            if re.search(r"\bstatus:\s*(failed|errored)\b", body):
                return {"domain": domain, "run_id": run_id, "status": "failed", "result": body.strip()}
            time.sleep(8)
        return {"domain": domain, "run_id": run_id, "status": "timeout"}
    except subprocess.TimeoutExpired:
        return {"domain": domain, "error": "freckle CLI timed out"}
    except Exception as e:  # noqa: BLE001 - the backend is external, report and continue
        return {"domain": domain, "error": f"{type(e).__name__}: {e}"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ops", default="data/ops_classified.json")
    ap.add_argument("--out", default="data/unmasked.json")
    ap.add_argument("--profile", action="store_true",
                    help="run profile lookup (web search for the author's public identity)")
    ap.add_argument("--enrich", action="store_true", help="live-enrich each disclosed domain")
    ap.add_argument("--limit", type=int, default=25, help="max domains to enrich in one run")
    args = ap.parse_args()

    ops = json.loads(Path(args.ops).read_text())
    leads = [o for o in ops if is_lead(o)]

    rows = []
    for o in leads:
        d = disclose(o, use_profile=args.profile)
        rows.append({
            "op_id": o.get("op_id") or o.get("id"),
            "subreddit": "r/" + (o.get("subreddit") or ""),
            "author": o.get("author"),
            "summary": (o.get("summary") or "")[:160],
            "permalink": o.get("permalink") or o.get("url"),
            **d,
        })

    disclosed = [r for r in rows if r["enrichment_eligibility"] == "eligible_direct_disclosure"]
    maybe = [r for r in rows if r["enrichment_eligibility"] == "manual_review"]
    lookup_errors = [r for r in rows if r["review_verdict"] == "lookup_error"]
    stays = [r for r in rows if r["review_verdict"] == "no_public_evidence"]

    enrichment = []
    if args.enrich:
        seen = set()
        for r in disclosed:
            dom = r["domain"]
            if dom in seen:
                continue
            seen.add(dom)
            if len(seen) > args.limit:
                print(f"  reached --limit {args.limit}; {len(disclosed) - len(seen) + 1} domains left")
                break
            print(f"  enriching {dom} ...")
            enrichment.append(enrich_domain(dom))

    result = {
        "leads_total": len(leads),
        "disclosed_company": len(disclosed),
        "manual_review_candidates": len(maybe),
        "lookup_errors": len(lookup_errors),
        "stays_on_reddit": len(stays),
        "profile_lookup": args.profile,
        "gate": ("only exact company-domain evidence published on the author's Reddit profile is "
                 "enrichment-eligible; search, thread, and handle matches require manual review"),
        "rows": rows,
        "enrichment": enrichment,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"unmask: {len(leads)} leads -> {len(disclosed)} disclosed a company, "
          f"{len(maybe)} manual-review candidates, {len(lookup_errors)} lookup errors, "
          f"{len(stays)} stay on Reddit"
          f"{' (profile lookup on)' if args.profile else ''}"
          f"{' · enriched ' + str(len(enrichment)) if args.enrich else ''} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
