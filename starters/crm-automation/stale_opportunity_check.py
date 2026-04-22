"""
stale_opportunity_check.py — Surface and enrich stale opportunities

Finds HubSpot deals that have gone quiet past N days in the stages you pick,
re-enriches the primary contact via Apollo, scans for new ICP hires at the
account, optionally checks news signals via Exa, and writes a summary back
to four custom properties on the deal.

Usage:
    # dry run: print the summary, do not write to HubSpot
    python stale_opportunity_check.py --days 60 --stages qualifiedtobuy,presentationscheduled --dry-run

    # live run: write agent_* properties back to the deal
    python stale_opportunity_check.py --days 60 --stages qualifiedtobuy,presentationscheduled

    # mine the nurture graveyard
    python stale_opportunity_check.py --stages closedlost --disqualify-reasons bad_timing,budget_gone

    # run with fixture data (no API calls, good for first-time test)
    python stale_opportunity_check.py --mock

Requirements:
    pip install -r requirements.txt
    .env with HUBSPOT_PRIVATE_APP_TOKEN and APOLLO_API_KEY (EXA_API_KEY optional)

Custom properties expected on the Deal object:
    agent_last_enriched_at   — datetime
    agent_stale_check_status — dropdown: actionable | dead | needs_review
    agent_signals_summary    — multi-line text
    agent_disqualify_reason  — dropdown: bad_timing | wrong_persona |
                                         left_company | competitor_won | budget_gone
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
HUBSPOT_TOKEN = os.getenv("HUBSPOT_PRIVATE_APP_TOKEN", "")
APOLLO_API_KEY = os.getenv("APOLLO_API_KEY", "")
EXA_API_KEY = os.getenv("EXA_API_KEY", "")

# TODO: replace with your own ICP titles
ICP_TITLES = [
    "VP of RevOps",
    "Head of Revenue Operations",
    "Chief Revenue Officer",
    "VP of Sales",
    "Head of Growth",
    "VP of Marketing",
]

RATE_LIMIT_DELAY = 0.25
REQUEST_TIMEOUT = 20

HUBSPOT_BASE = "https://api.hubapi.com"


# --- HubSpot helpers ---

def hs_headers() -> dict:
    return {
        "Authorization": f"Bearer {HUBSPOT_TOKEN}",
        "Content-Type": "application/json",
    }


def fetch_stale_deals(days: int, stages: list[str]) -> list[dict]:
    """Return deals whose last-modified is older than cutoff AND stage is in list."""
    cutoff_ms = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
    body = {
        "filterGroups": [{
            "filters": [
                {"propertyName": "dealstage", "operator": "IN", "values": stages},
                {"propertyName": "hs_lastmodifieddate", "operator": "LT", "value": str(cutoff_ms)},
            ]
        }],
        "properties": [
            "dealname", "amount", "dealstage",
            "hs_lastmodifieddate", "hubspot_owner_id",
            "agent_disqualify_reason",
        ],
        "limit": 100,
    }
    all_deals: list[dict] = []
    after: str | None = None
    while True:
        if after:
            body["after"] = after
        r = requests.post(
            f"{HUBSPOT_BASE}/crm/v3/objects/deals/search",
            headers=hs_headers(),
            json=body,
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        all_deals.extend(data.get("results", []))
        paging = data.get("paging", {}).get("next")
        if not paging:
            break
        after = paging.get("after")
        time.sleep(RATE_LIMIT_DELAY)
    return all_deals


def get_primary_contact(deal_id: str) -> dict | None:
    r = requests.get(
        f"{HUBSPOT_BASE}/crm/v3/objects/deals/{deal_id}/associations/contacts",
        headers=hs_headers(),
        timeout=REQUEST_TIMEOUT,
    )
    if r.status_code != 200:
        return None
    results = r.json().get("results", [])
    if not results:
        return None
    contact_id = results[0]["id"]
    r2 = requests.get(
        f"{HUBSPOT_BASE}/crm/v3/objects/contacts/{contact_id}"
        "?properties=email,firstname,lastname,jobtitle,company",
        headers=hs_headers(),
        timeout=REQUEST_TIMEOUT,
    )
    if r2.status_code != 200:
        return None
    return r2.json().get("properties", {})


def get_associated_company(deal_id: str) -> dict | None:
    r = requests.get(
        f"{HUBSPOT_BASE}/crm/v3/objects/deals/{deal_id}/associations/companies",
        headers=hs_headers(),
        timeout=REQUEST_TIMEOUT,
    )
    if r.status_code != 200:
        return None
    results = r.json().get("results", [])
    if not results:
        return None
    company_id = results[0]["id"]
    r2 = requests.get(
        f"{HUBSPOT_BASE}/crm/v3/objects/companies/{company_id}"
        "?properties=name,domain,industry,numberofemployees",
        headers=hs_headers(),
        timeout=REQUEST_TIMEOUT,
    )
    if r2.status_code != 200:
        return None
    return r2.json().get("properties", {})


def update_deal_properties(deal_id: str, props: dict, dry_run: bool) -> None:
    if dry_run:
        print(f"    [dry-run] would PATCH deal {deal_id} with: {json.dumps(props, indent=6)}")
        return
    r = requests.patch(
        f"{HUBSPOT_BASE}/crm/v3/objects/deals/{deal_id}",
        headers=hs_headers(),
        json={"properties": props},
        timeout=REQUEST_TIMEOUT,
    )
    if r.status_code >= 300:
        print(f"    [error] HubSpot PATCH {deal_id}: {r.status_code} {r.text[:200]}")
    else:
        print(f"    [ok] wrote agent_* properties to deal {deal_id}")


# --- Apollo helpers ---

def apollo_match_email(email: str) -> dict:
    """Return the current employment record for a given email."""
    r = requests.post(
        "https://api.apollo.io/v1/people/match",
        headers={"X-Api-Key": APOLLO_API_KEY, "Content-Type": "application/json"},
        json={"email": email},
        timeout=REQUEST_TIMEOUT,
    )
    if r.status_code != 200:
        return {}
    return r.json().get("person", {}) or {}


def apollo_find_new_hires(domain: str, titles: list[str], within_days: int = 30) -> list[dict]:
    """Find people at a domain whose current employment started within the window."""
    r = requests.post(
        "https://api.apollo.io/v1/mixed_people/search",
        headers={"X-Api-Key": APOLLO_API_KEY, "Content-Type": "application/json"},
        json={
            "q_organization_domains": domain,
            "person_titles": titles,
            "page": 1,
            "per_page": 10,
        },
        timeout=REQUEST_TIMEOUT,
    )
    if r.status_code != 200:
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(days=within_days)
    recent: list[dict] = []
    for p in r.json().get("people", []):
        history = p.get("employment_history", [])
        if not history:
            continue
        current = history[0]
        start = current.get("start_date")
        if not start:
            continue
        try:
            start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
        except ValueError:
            continue
        if start_dt.replace(tzinfo=timezone.utc) >= cutoff:
            recent.append({
                "name": p.get("name"),
                "title": current.get("title"),
                "start_date": start,
                "linkedin_url": p.get("linkedin_url"),
            })
    return recent


# --- Exa helpers ---

def exa_news_signals(company_name: str) -> list[str]:
    if not EXA_API_KEY or not company_name:
        return []
    r = requests.post(
        "https://api.exa.ai/search",
        headers={"x-api-key": EXA_API_KEY, "Content-Type": "application/json"},
        json={
            "query": f"{company_name} funding OR layoffs OR acquisition OR product launch OR hiring",
            "num_results": 5,
            "start_published_date": (datetime.now() - timedelta(days=30)).isoformat(),
        },
        timeout=REQUEST_TIMEOUT,
    )
    if r.status_code != 200:
        return []
    return [item.get("title", "").strip() for item in r.json().get("results", []) if item.get("title")]


# --- Core scoring ---

def score_deal(deal: dict, contact: dict | None, company: dict | None,
               apollo_person: dict, new_hires: list[dict], news: list[str]) -> dict:
    """Return {status, narrative, disqualify_reason} for this deal."""
    narrative_parts: list[str] = []
    status = "needs_review"
    disqualify_reason = ""

    contact_company = (contact or {}).get("company", "").lower()
    apollo_current_company = (apollo_person.get("organization") or {}).get("name", "").lower()
    account_name = (company or {}).get("name", "").lower()

    # Employment flip?
    if apollo_current_company and contact_company:
        if apollo_current_company not in (contact_company, account_name):
            narrative_parts.append(
                f"Primary contact {contact.get('firstname','')} {contact.get('lastname','')} "
                f"now at {apollo_person.get('organization',{}).get('name','')} "
                f"as {apollo_person.get('title','')}. Original champion has left."
            )
            status = "actionable"
            disqualify_reason = "left_company"

    # New ICP hires at the account?
    if new_hires:
        lines = [
            f"{h['name']} joined as {h['title']} ({h['start_date'][:10]})"
            for h in new_hires[:3]
        ]
        narrative_parts.append("New ICP hires at the account: " + "; ".join(lines) + ".")
        status = "actionable"

    # News signals?
    if news:
        narrative_parts.append("Recent news: " + "; ".join(news[:3]) + ".")
        if status == "needs_review":
            status = "actionable"

    if not narrative_parts:
        narrative_parts.append("No material changes detected in the last 60 days.")
        status = "dead"
        disqualify_reason = disqualify_reason or "bad_timing"

    return {
        "status": status,
        "narrative": " ".join(narrative_parts),
        "disqualify_reason": disqualify_reason,
    }


# --- Mock mode for first-time test ---

def run_mock() -> None:
    fake_deals = [
        {
            "id": "1001",
            "properties": {
                "dealname": "Acme Widgets — Q3 expansion",
                "amount": "45000",
                "dealstage": "qualifiedtobuy",
                "hs_lastmodifieddate": "2026-02-10T12:00:00Z",
            },
        },
        {
            "id": "1002",
            "properties": {
                "dealname": "Globex — pilot",
                "amount": "12000",
                "dealstage": "presentationscheduled",
                "hs_lastmodifieddate": "2026-02-05T12:00:00Z",
            },
        },
    ]
    print(f"[mock] {len(fake_deals)} stale deals\n")
    for d in fake_deals:
        name = d["properties"]["dealname"]
        fake_summary = {
            "status": "actionable",
            "narrative": f"[mock] {name}: original champion left; new VP of RevOps joined 11 days ago.",
            "disqualify_reason": "",
        }
        props = {
            "agent_last_enriched_at": datetime.now().isoformat(),
            "agent_stale_check_status": fake_summary["status"],
            "agent_signals_summary": fake_summary["narrative"],
            "agent_disqualify_reason": fake_summary["disqualify_reason"],
        }
        print(f"  Deal {d['id']} — {name}")
        print(f"    status: {fake_summary['status']}")
        print(f"    {fake_summary['narrative']}")
        print(f"    [mock] would PATCH with {list(props.keys())}")
        print()


# --- Main ---

def main() -> None:
    parser = argparse.ArgumentParser(description="Surface and enrich stale HubSpot deals.")
    parser.add_argument("--days", type=int, default=60,
                        help="Deal is stale if last-modified is older than this many days")
    parser.add_argument("--stages", type=str, default="qualifiedtobuy,presentationscheduled",
                        help="Comma-separated HubSpot deal stage internal names")
    parser.add_argument("--disqualify-reasons", type=str, default="",
                        help="Comma-separated agent_disqualify_reason filter (nurture mining mode)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be written; do not PATCH HubSpot")
    parser.add_argument("--mock", action="store_true",
                        help="Use fixture data, no API calls")
    args = parser.parse_args()

    if args.mock:
        run_mock()
        return

    if not HUBSPOT_TOKEN:
        print("HUBSPOT_PRIVATE_APP_TOKEN not set. Copy .env.example to .env and fill it in.")
        sys.exit(1)
    if not APOLLO_API_KEY:
        print("APOLLO_API_KEY not set. Copy .env.example to .env and fill it in.")
        sys.exit(1)

    stages = [s.strip() for s in args.stages.split(",") if s.strip()]
    disqualify_filter = [s.strip() for s in args.disqualify_reasons.split(",") if s.strip()]

    print(f"\n--- Stale Opportunity Check ---")
    print(f"Cutoff:  {args.days} days")
    print(f"Stages:  {stages}")
    print(f"Reasons: {disqualify_filter or 'any'}")
    print(f"Mode:    {'dry-run' if args.dry_run else 'live (writes enabled)'}\n")

    deals = fetch_stale_deals(args.days, stages)
    if disqualify_filter:
        deals = [d for d in deals
                 if d.get("properties", {}).get("agent_disqualify_reason") in disqualify_filter]
    print(f"Found {len(deals)} stale deals\n")

    for i, deal in enumerate(deals, 1):
        deal_id = deal["id"]
        props = deal.get("properties", {})
        name = props.get("dealname", "(unnamed)")
        print(f"[{i}/{len(deals)}] Deal {deal_id} — {name}")

        contact = get_primary_contact(deal_id)
        company = get_associated_company(deal_id)

        apollo_person = {}
        if contact and contact.get("email"):
            apollo_person = apollo_match_email(contact["email"])

        new_hires: list[dict] = []
        if company and company.get("domain"):
            new_hires = apollo_find_new_hires(company["domain"], ICP_TITLES)

        news: list[str] = []
        if company and company.get("name"):
            news = exa_news_signals(company["name"])

        summary = score_deal(deal, contact, company, apollo_person, new_hires, news)
        print(f"    status: {summary['status']}")
        print(f"    {summary['narrative']}")

        update_deal_properties(
            deal_id,
            {
                "agent_last_enriched_at": datetime.now().isoformat(),
                "agent_stale_check_status": summary["status"],
                "agent_signals_summary": summary["narrative"],
                "agent_disqualify_reason": summary["disqualify_reason"],
            },
            dry_run=args.dry_run,
        )
        print()
        time.sleep(RATE_LIMIT_DELAY)

    print(f"Done. Processed {len(deals)} deals.\n")


if __name__ == "__main__":
    main()
