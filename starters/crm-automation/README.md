# CRM Automation Starter

Companion to Chapter 13. Surfaces stale HubSpot deals, re-enriches via Apollo, flags actionable ones, writes the result back as four custom properties on the deal.

## What it does

- Searches HubSpot for deals older than N days in the stages you specify
- For each deal: re-checks the primary contact's current employment (Apollo)
- For each account: looks for new ICP-match hires in the last 30 days (Apollo)
- Optionally scans recent news (Exa) for funding, layoffs, acquisitions, launches
- Writes a short narrative summary back to the deal as `agent_*` custom properties

## Setup

```bash
cd starters/crm-automation
pip install -r requirements.txt
cp .env.example .env
# fill in HUBSPOT_PRIVATE_APP_TOKEN and APOLLO_API_KEY (EXA_API_KEY optional)
```

### Required HubSpot private-app scopes

- `crm.objects.deals.read`
- `crm.objects.deals.write`
- `crm.objects.contacts.read`
- `crm.objects.companies.read`
- `crm.schemas.deals.write` (only needed to create the custom properties)

### Custom properties to create on the Deal object

| Name | Type | Options |
|------|------|---------|
| `agent_last_enriched_at` | Date/time | — |
| `agent_stale_check_status` | Dropdown | `actionable`, `dead`, `needs_review` |
| `agent_signals_summary` | Multi-line text | — |
| `agent_disqualify_reason` | Dropdown | `bad_timing`, `wrong_persona`, `left_company`, `competitor_won`, `budget_gone` |

Create them once in Settings → Properties → Create Property. Salesforce: same four as custom fields on the Opportunity object.

## Usage

```bash
# First-time sanity check — no API calls, no writes
python stale_opportunity_check.py --mock

# Dry run — real HubSpot/Apollo queries, no writes
python stale_opportunity_check.py --days 60 --stages qualifiedtobuy,presentationscheduled --dry-run

# Live run
python stale_opportunity_check.py --days 60 --stages qualifiedtobuy,presentationscheduled

# Nurture mining — mine closed-lost deals where reason was bad timing or budget
python stale_opportunity_check.py --stages closedlost --disqualify-reasons bad_timing,budget_gone
```

### Flags

- `--days N` — deal is stale if `hs_lastmodifieddate < now - N days`. Default 60.
- `--stages a,b,c` — comma-separated HubSpot stage internal names.
- `--disqualify-reasons a,b` — filter by existing `agent_disqualify_reason` (nurture-mining).
- `--dry-run` — log what would change, do not write.
- `--mock` — ignore the env, run on fixture data, no network.

## Slash command

`/stale-opportunities` is defined in `.claude/commands/stale-opportunities.md`. Fire it from Claude Code to run the script in your current session.

## Running on a schedule

### launchd (macOS, what I use)

Drop this plist in `~/Library/LaunchAgents/com.yourname.stale-opps.plist` and `launchctl load` it.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>            <string>com.yourname.stale-opps</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/python3</string>
    <string>/Users/YOU/path/to/stale_opportunity_check.py</string>
    <string>--days</string><string>60</string>
    <string>--stages</string><string>qualifiedtobuy,presentationscheduled</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>           <integer>6</integer>
    <key>Minute</key>         <integer>0</integer>
  </dict>
  <key>StandardOutPath</key>  <string>/tmp/stale-opps.log</string>
  <key>StandardErrorPath</key><string>/tmp/stale-opps.err</string>
</dict>
</plist>
```

### HubSpot workflow → webhook

Alternative: a HubSpot workflow fires when a deal crosses 60 days in a target stage, calls a webhook you own, and the endpoint runs the script against that one deal. Cleaner audit trail, better once you pass ~1,000 active deals.

## Tuning

Open `stale_opportunity_check.py` and edit:

- `ICP_TITLES` — the titles that count as "new ICP hire" for your business
- `score_deal()` — the status/reason logic. Current default: any contact-flip or new-hire-match marks the deal `actionable`. Adjust for your team's taste.
- `exa_news_signals()` query — add or remove keywords for the news scan

## What this is not

Not a replacement for your SDR. A filter that turns 500 stale deals into the 30 worth a human's attention. The human still writes the email.
