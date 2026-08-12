#!/usr/bin/env python3
"""waterfall.py -- gated lookalike expansion: grow a company list to a target size.

Takes the list you already have, finds lookalikes until it hits --target, and
drains search gates from deepest intent to shallowest. Every company comes out
tagged with the gate it passed through -- that tag IS your intent layer.

Apollo's buying-intent (Bombora topic) data is NOT exposed via the API, so the
layer is built from observable behavior the API does expose:

  T0  reddit buyer signal   external evidence (e.g. a Clearbox export) -- not an Apollo query
  T1  hiring for the pain   job postings for the titles you configure, recently posted
  T2  fresh funding         latest round inside your amount window (a Series B-D proxy)
  T3  tech-stack twins      running the tools your best accounts run
  T4  firmographic          industry + size + geo lookalike, no behavior yet

Every Apollo call here is mixed_companies/search -- FREE, 0 credits.

  python3 waterfall.py --target 50                          # config from waterfall_config.json
  python3 waterfall.py --seed my_list.csv --double          # target = 2x seed list
  python3 waterfall.py --clearbox clearbox_export.csv ...   # seed T0 from evidence
  python3 waterfall.py --target 50 --dry-run                # count per gate, write nothing

Bonus: search responses carry per-company intent_strength (Apollo's buying
intent score) even though you cannot FILTER by it -- so when Apollo has a
signal, it lands in the apollo_intent column for free. Headcount growth comes
along too. Staffing/recruiting noise (the classic failure mode of job-posting
gates: agencies post roles for their clients) is dropped by NAICS prefix.

Output: waterfall_output.csv -- init_db.py-compatible (company, domain, name,
title, persona, source) plus gate, gate_evidence, apollo_intent,
headcount_growth_6mo, revenue columns.
Feed it straight into the pipeline:  python3 init_db.py waterfall_output.csv
"""
import argparse
import csv
import json
import sys
import time
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.apollo_client import search_companies

HERE = Path(__file__).resolve().parent
CONFIG_PATH = HERE / "waterfall_config.json"
EXAMPLE_CONFIG_PATH = HERE / "waterfall_config.example.json"
OUTPUT = HERE / "waterfall_output.csv"

MAX_PAGES_PER_GATE = 5  # x per_page=100 = up to 500 candidates screened per gate


def load_config() -> dict:
    path = CONFIG_PATH if CONFIG_PATH.exists() else EXAMPLE_CONFIG_PATH
    print(f"config: {path.name}")
    return json.loads(path.read_text())


def seed_domains(csv_path: Path) -> set:
    rows = list(csv.DictReader(csv_path.open()))
    return {(r.get("domain") or "").strip().lower() for r in rows if r.get("domain")}


def fingerprint_filters(cfg: dict) -> dict:
    fp = cfg.get("fingerprint", {})
    filters = {}
    if fp.get("employees"):
        filters["organization_num_employees_ranges"] = fp["employees"]
    if fp.get("locations"):
        filters["organization_locations"] = fp["locations"]
    if fp.get("industries"):
        filters["q_organization_keyword_tags"] = fp["industries"]
    return filters


def build_gates(cfg: dict) -> list:
    """Returns [(tier, label, filters, evidence)] deep -> shallow. T0 is handled
    separately because it is external evidence, not an Apollo search."""
    fp = fingerprint_filters(cfg)
    gates = []

    t1 = cfg.get("gates", {}).get("T1", {})
    if t1.get("hiring_for"):
        days = int(t1.get("job_posted_days", 60))
        since = (date.today() - timedelta(days=days)).isoformat()
        gates.append((
            "T1", "hiring for the pain",
            {**fp,
             "q_organization_job_titles": t1["hiring_for"],
             "organization_job_posted_at_range": {"min": since},
             "organization_num_jobs_range": {"min": 1}},
            f"hiring {'/'.join(t1['hiring_for'])} (posted <={days}d)",
        ))

    t2 = cfg.get("gates", {}).get("T2", {})
    if t2.get("funding_min"):
        months = int(t2.get("funding_months", 24))
        since = (date.today() - timedelta(days=months * 30)).isoformat()
        lo, hi = int(t2["funding_min"]), int(t2.get("funding_max", 10**9))
        gates.append((
            "T2", "fresh funding",
            {**fp,
             "latest_funding_amount_range": {"min": lo, "max": hi},
             "latest_funding_date_range": {"min": since}},
            f"raised ${lo/1e6:.0f}M-${hi/1e6:.0f}M in last {months}mo",
        ))

    t3 = cfg.get("gates", {}).get("T3", {})
    if t3.get("technologies"):
        gates.append((
            "T3", "tech-stack twins",
            {**fp,
             "currently_using_any_of_technology_uids": t3["technologies"]},
            f"runs {'/'.join(t3['technologies'])}",
        ))

    gates.append(("T4", "firmographic lookalike", dict(fp), "fingerprint match only"))
    return gates


def excluded(org, naics_prefixes) -> bool:
    codes = org.get("naics_codes") or []
    return any(str(c).startswith(p) for c in codes for p in naics_prefixes)


def drain_gate(tier, label, filters, evidence, seen, found, target, dry_run,
               naics_prefixes, cap=None):
    """Page through one gate until its cap is hit, the target is hit, the gate
    is exhausted, or the page cap is reached. A per-gate cap keeps one deep
    gate from filling the whole list -- so the shallower gates still get a
    turn and the intent layer stays a mix. Mutates seen/found. Returns count."""
    budget = target - len(found)
    if cap is not None:
        budget = min(budget, int(cap))
    added = 0
    dropped = 0
    for page in range(1, MAX_PAGES_PER_GATE + 1):
        data = search_companies(page=page, per_page=100, **filters)
        orgs = data.get("organizations", []) or []
        total = (data.get("pagination") or {}).get("total_entries", "?")
        if page == 1:
            cap_note = f" (cap {cap})" if cap is not None else ""
            print(f"  {tier} {label}: {total} companies match the gate{cap_note}")
            if dry_run:
                return 0
        if not orgs:
            break
        for org in orgs:
            domain = (org.get("primary_domain") or "").strip().lower()
            if not domain or domain in seen:
                continue
            if excluded(org, naics_prefixes):
                dropped += 1
                continue
            seen.add(domain)
            growth = org.get("organization_headcount_six_month_growth")
            found.append({
                "company": org.get("name", ""),
                "domain": domain,
                "name": "", "title": "", "persona": "",
                "source": f"waterfall-{tier}",
                "gate": tier,
                "gate_evidence": evidence,
                "apollo_intent": org.get("intent_strength") or "",
                "headcount_growth_6mo": f"{growth:.1%}" if growth is not None else "",
                "revenue": org.get("organization_revenue_printed") or "",
            })
            added += 1
            if added >= budget or len(found) >= target:
                if dropped:
                    print(f"     (dropped {dropped} staffing/recruiting by NAICS)")
                return added
        time.sleep(0.5)
    if dropped:
        print(f"     (dropped {dropped} staffing/recruiting by NAICS)")
    return added


def main():
    ap = argparse.ArgumentParser(description="Gated lookalike expansion with a built-in intent layer")
    ap.add_argument("--seed", default=str(HERE / "sample_contacts.csv"),
                    help="CSV of companies you already have (dedupe set + size baseline)")
    ap.add_argument("--target", type=int, help="How many NEW companies to find")
    ap.add_argument("--double", action="store_true", help="Set target = size of the seed list")
    ap.add_argument("--clearbox", help="CSV of evidence-backed domains (company, domain[, evidence]) -> tier T0")
    ap.add_argument("--dry-run", action="store_true", help="Print per-gate match counts, write nothing")
    args = ap.parse_args()

    cfg = load_config()
    seed = seed_domains(Path(args.seed))
    target = args.target or (len(seed) if args.double else cfg.get("target", 50))
    naics_prefixes = cfg.get("exclude", {}).get("naics_prefixes", [])
    print(f"seed list: {len(seed)} domains | target: {target} new companies\n")

    seen = set(seed)
    found = []

    # T0: external evidence beats any Apollo query
    if args.clearbox:
        for r in csv.DictReader(Path(args.clearbox).open()):
            domain = (r.get("domain") or "").strip().lower()
            if not domain or domain in seen:
                continue
            seen.add(domain)
            found.append({
                "company": r.get("company", domain), "domain": domain,
                "name": "", "title": "", "persona": "",
                "source": "waterfall-T0", "gate": "T0",
                "gate_evidence": r.get("evidence", "reddit buyer signal (clearbox)"),
                "apollo_intent": "", "headcount_growth_6mo": "", "revenue": "",
            })
        print(f"  T0 reddit buyer signal: {len(found)} companies from {Path(args.clearbox).name}")

    for tier, label, filters, evidence in build_gates(cfg):
        if len(found) >= target:
            break
        cap = cfg.get("gates", {}).get(tier, {}).get("cap")
        added = drain_gate(tier, label, filters, evidence, seen, found, target,
                           args.dry_run, naics_prefixes, cap=cap)
        if not args.dry_run:
            print(f"     -> +{added} new (running total {len(found)}/{target})")

    if args.dry_run:
        print("\ndry run: no file written. Searches cost 0 credits either way.")
        return

    fields = ["company", "domain", "name", "title", "persona", "source",
              "gate", "gate_evidence", "apollo_intent", "headcount_growth_6mo", "revenue"]
    with OUTPUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(found)

    print(f"\n{'='*60}")
    print("  INTENT LAYER (which gate filled the list)")
    for tier in ["T0", "T1", "T2", "T3", "T4"]:
        n = sum(1 for r in found if r["gate"] == tier)
        if n:
            print(f"  {tier}: {n:>4}  {next(r['gate_evidence'] for r in found if r['gate'] == tier)}")
    print(f"{'='*60}")
    print(f"wrote {len(found)} companies -> {OUTPUT.name}")
    print(f"next: python3 init_db.py {OUTPUT.name}  (then expand/score as usual)")


if __name__ == "__main__":
    main()
