# Fathom API

**Category:** Call intelligence / Conversation data
**Connection:** REST API + MCP
**Cost:** Free tier includes API access. Premium $20/mo for unlimited AI summaries.
**Install:** No CLI. `pip install fathom-python` or call the REST API directly.

---

## What It Does

Fathom records, transcribes, and summarizes Zoom, Google Meet, and Microsoft Teams calls. The public API gives you programmatic access to every meeting you recorded or that was shared to your team: transcripts, AI summaries, action items, and matched CRM records.

For GTM operators, this is the easiest way to turn a year of sales and customer calls into structured, queryable data. Renewal prep, QBR briefings, churn signals, competitor mentions, objection patterns: all the things that live in call recordings and nowhere else.

Fathom's API is available on the free tier. Any individual user can generate a key and start pulling data, which makes it a practical starting point if you don't have admin access to a heavier conversation intelligence platform.

## Setup

```bash
# Generate an API key at https://fathom.video/api_clients/new
# Add to .env
echo "FATHOM_API_KEY=your_key_here" >> .env
```

API keys are user-scoped. Your key can only access meetings you recorded or meetings shared to your team. Admin status does not grant access to other users' private meetings.

## Key Endpoints

| Endpoint | What It Does |
|----------|-------------|
| `GET /external/v1/meetings` | List meetings with filters (date range, attendee, recorded_by). Returns metadata, summary, action items, CRM matches. |
| `GET /external/v1/meetings` with `include_transcript=true` | Same as above but inlines full transcript. Heavier payload. |
| `GET /external/v1/recordings/{id}/transcript` | Fetch a single transcript by recording ID. Required for OAuth apps. |
| Webhooks | Push new meeting data to your endpoint as calls are processed. |

Every meeting response includes `crm_matches` with linked HubSpot/Salesforce contacts, companies, and deals (if CRM is connected on Business tier). This is the hook that makes per-account intelligence work. You can filter meetings by deal or company without maintaining a separate mapping.

## Batch Pull Pattern

The typical GTM workflow: pull all meetings for an account or date range, save locally, analyze with Claude.

```python
#!/usr/bin/env python3
"""Pull Fathom meetings into local JSONL, one file per account."""

import json
import os
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("FATHOM_API_KEY")
BASE_URL = "https://api.fathom.ai/external/v1"
OUTPUT_DIR = Path("data/fathom")
RATE_LIMIT_SLEEP = 1.1  # 60 calls/min = 1 per second, buffer it


def fetch_meetings(params: dict) -> list:
    """Fetch all meetings matching params, handling cursor pagination."""
    results = []
    cursor = None

    while True:
        if cursor:
            params["cursor"] = cursor

        resp = requests.get(
            f"{BASE_URL}/meetings",
            headers={"X-Api-Key": API_KEY},
            params=params,
            timeout=30,
        )

        if resp.status_code == 429:
            print("Rate limited. Sleeping 60s...")
            time.sleep(60)
            continue
        if resp.status_code != 200:
            print(f"Error {resp.status_code}: {resp.text}")
            break

        data = resp.json()
        results.extend(data.get("items", []))
        cursor = data.get("next_cursor")
        if not cursor:
            break

        time.sleep(RATE_LIMIT_SLEEP)

    return results


def pull_account(company_domain: str, days_back: int = 180):
    """Pull all meetings with attendees from a company domain."""
    from datetime import datetime, timedelta, timezone
    created_after = (datetime.now(timezone.utc) - timedelta(days=days_back)).isoformat()

    meetings = fetch_meetings({
        "include_transcript": "true",
        "created_after": created_after,
    })

    # Filter client-side for meetings with this company
    matched = [
        m for m in meetings
        if any(
            inv.get("email", "").endswith(f"@{company_domain}")
            for inv in m.get("calendar_invitees", [])
        )
    ]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / f"{company_domain.replace('.', '_')}.jsonl"
    with open(output_file, "w") as f:
        for m in matched:
            f.write(json.dumps(m) + "\n")

    print(f"Saved {len(matched)} meetings to {output_file}")
    return matched


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python3 pull_fathom.py <company_domain> [days_back]")
        sys.exit(1)
    domain = sys.argv[1]
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 180
    pull_account(domain, days)
```

Run it:

```bash
python3 pull_fathom.py acme-corp.com 180
```

You get a JSONL file with every meeting involving anyone from that domain in the last 180 days. Each line is a full meeting object with transcript, summary, action items, and CRM links.

## Rate Limiting

- **60 calls per minute** across all your API keys. No higher tier available.
- Space requests at ~1.1 seconds apart to stay under the ceiling with a small buffer.
- The API returns `429` when you exceed the limit. Back off for 60 seconds and retry.
- For large historical pulls, run overnight. A year of meetings for an active rep is maybe 200-500 calls to the API.

## GTM Use Cases

### Per-Account Intelligence

Pull every call for a single account, compile into a per-account knowledge base, generate briefings before renewals or QBRs. This is the CSM account wiki pattern.

```bash
# Pull the last 12 months of meetings for one account
python3 pull_fathom.py acme-corp.com 365

# Compile into a structured briefing with Claude
claude --print --model opus < prompts/account_briefing.md
```

The briefing prompt reads the JSONL, pulls out stakeholder changes, open action items, recent objections, expansion signals, and anything mentioned more than twice. Output lands in `accounts/acme-corp/briefings/` as markdown.

### Churn Signal Detection

Sweep all customer calls weekly looking for churn signals: frustration, competitor mentions, executive sponsor changes, reduced attendance, specific phrases like "evaluate alternatives" or "budget review."

```python
# Pull all customer calls from the last 7 days
meetings = fetch_meetings({
    "include_transcript": "true",
    "created_after": one_week_ago,
    "meeting_type": "external",
})

# Feed each transcript to Claude with a signal taxonomy
# Flag accounts where signals fire
```

Pair with the Claude subprocess pattern (see `engine/claude-subprocess.md`) to run this as a nightly batch job. You wake up to a list of accounts to check in on.

### Objection Pattern Mining

Pull 90 days of discovery and demo calls. Have Claude extract every objection raised, cluster by theme, count frequency. Feed the output to your positioning and sales enablement work.

Real example: running this across a few months of customer calls surfaced that in-person and conference room meetings weren't being captured. Individual reps and CSMs each only saw it occasionally, so nobody raised it. In aggregate it meant entire accounts looked quiet for weeks at a time when they were actually meeting with us regularly. That's a hidden usage signal worth catching early.

### Handoff Briefings

When a new CSM takes over an account, feed Claude all the historical calls and ask for a handoff doc: who the stakeholders are, what they care about, what's been promised, open action items, landmines. Ten minutes of compute replaces a week of shadowing.

## Integration with Claude Code

Fathom ships an MCP endpoint at `https://api.fathom.ai/mcp`. Connect it to Claude Code and you can query meetings in natural language:

```
> Pull every meeting with anyone from acme-corp.com in the last 90 days.
> Identify the three biggest concerns they raised.
> Cross-reference against the open deals in HubSpot for that account.
> Draft a renewal prep brief.
```

Claude Code calls Fathom via MCP, pulls transcripts, reasons over them, writes the brief. For batch work outside Claude Code, use the REST API pattern above.

## Gotchas

- **API keys only see your meetings plus team-shared meetings.** If you need org-wide access, use OAuth or have the relevant users share to your team.
- **Transcripts are large.** A one-hour call runs 10-20 KB of text. For batch analysis, use stdin piping into the Claude CLI rather than command-line args.
- **CRM matches require Business tier.** Free and Team tiers return meeting data but no HubSpot/Salesforce links.
- **AI summaries are capped on Free.** The free plan only generates advanced AI summaries for 5 calls per month. The API still returns basic chronological summaries for other calls. If you need unlimited structured summaries, Premium is $20/mo.
- **Meeting types matter for filters.** Use `meeting_type=external` to get customer-facing calls, `internal` for internal syncs. Filter at the API level to save on pagination.
