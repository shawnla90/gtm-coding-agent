# Chapter 13: CRM Automation and Slash Commands

**Your CRM is where good pipeline goes to die. Deals cross the 60-day line, the AE gets distracted, the SDR gets reassigned, and the record sits there going stale. This chapter shows how to wire a coding agent to HubSpot and Salesforce, then turn recurring RevOps motions into slash commands that run on demand or on a cron. One concrete example all the way through: `/stale-opportunities` — finds deals past 60 days, checks whether the contact is still at the company, scans for new hires and fresh signals, and writes the result back as custom properties on the deal.**

---

## The CRM is the graveyard

Pull up your opportunity pipeline and filter for deals with no activity in the last 60 days. Look at the list. That's the money leaking out of the bucket.

Half of those are dead for a real reason: wrong timing, wrong persona, competitor won. The other half are alive and nobody is working them. A new VP of RevOps just joined. A funding round closed last month. The original champion left for a bigger role at a bigger company. Any of those flips the deal back into playable — but nobody looked.

Everyone at a well-run company knows this. Nobody has time to do it. RevOps is drowning in reporting, AEs are working the top of their list, SDRs are chasing fresh leads. The 60-day-old qualified-but-not-now pile stays in the dark.

That is the pile a coding agent is built for. A script that runs nightly, re-enriches every stale deal, pulls current signals, and writes the useful ones back to the CRM as readable custom properties. A slash command an AE can fire at any moment: `/stale-opportunities` and the CRM gets updated with fresh intel by morning.

This chapter builds that. Three parts: connect the CRM, structure the slash command, ship the worked example.

---

## Connecting HubSpot

Three ways to talk to HubSpot from a coding agent. Use the one that fits the job.

### Option 1 — MCP (easiest, OAuth, limited)

The official HubSpot MCP server lets Claude Code search, create, and update records through natural language. Authorize once, then you can say "find all deals in stage qualified with no activity in 60 days" and the agent runs the search.

Great for ad-hoc work. Less great for scheduled automation because MCP is an interactive protocol — it sits behind your Claude Code session, not a cron.

Install:

```bash
# follow the HubSpot MCP install in your Claude Code settings
# claude mcp add hubspot
```

Good for: exploration, building prompts, dashboards a human fires on demand.

### Option 2 — Private App Token + `curl` (what I actually use)

Private apps are HubSpot's API-key equivalent for a single portal. Generate one in Settings → Integrations → Private Apps. Scope it to the objects you need (`crm.objects.deals.read`, `crm.objects.deals.write`, contacts, companies). You get a token. You put it in `.env`. You make HTTP calls.

```bash
# .env
HUBSPOT_PRIVATE_APP_TOKEN=pat-na1-xxxxxxxx

# Search deals past 60 days in qualified stage
curl -s -X POST "https://api.hubapi.com/crm/v3/objects/deals/search" \
  -H "Authorization: Bearer $HUBSPOT_PRIVATE_APP_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "filterGroups": [{
      "filters": [
        {"propertyName": "dealstage", "operator": "EQ", "value": "qualifiedtobuy"},
        {"propertyName": "hs_lastmodifieddate", "operator": "LT", "value": "'"$(date -v-60d +%s000)"'"}
      ]
    }],
    "properties": ["dealname", "amount", "hs_lastmodifieddate", "hubspot_owner_id"],
    "limit": 100
  }'
```

Good for: any scheduled script, any CI workflow, anywhere you do not want an OAuth dance.

### Option 3 — Python with `hubspot-api-client` (heavy work)

When you are paginating thousands of records, doing batch updates, or writing logic the agent will reuse across clients, drop into Python.

```python
from hubspot import HubSpot
from hubspot.crm.deals import PublicObjectSearchRequest

client = HubSpot(access_token=os.environ["HUBSPOT_PRIVATE_APP_TOKEN"])

search = PublicObjectSearchRequest(
    filter_groups=[{
        "filters": [
            {"propertyName": "dealstage", "operator": "EQ", "value": "qualifiedtobuy"},
            {"propertyName": "hs_lastmodifieddate", "operator": "LT",
             "value": str(int((datetime.now() - timedelta(days=60)).timestamp() * 1000))},
        ]
    }],
    properties=["dealname", "amount", "hs_lastmodifieddate", "hubspot_owner_id"],
    limit=100,
)
result = client.crm.deals.search_api.do_search(public_object_search_request=search)
```

Good for: anything you will run more than twice.

**My rule:** MCP for exploring, private-app `curl` for one-shots, Python SDK for anything that becomes a scheduled job.

---

## Connecting Salesforce

Three patterns again.

### Option 1 — `sf` CLI

Salesforce ships a first-party CLI that covers queries, data load, and metadata. It is the cleanest way to pull data without writing auth boilerplate.

```bash
brew install salesforcedx

sf org login web --alias production
sf data query --query "SELECT Id, Name, StageName, LastModifiedDate FROM Opportunity \
  WHERE StageName = 'Qualification' AND LastModifiedDate < LAST_N_DAYS:60" \
  --target-org production --json
```

The JSON output is pipeable. A Claude Code session can call `sf data query` directly and parse the result. Great pattern for one-off reporting and quick mutations (`sf data update record`).

### Option 2 — `simple-salesforce` (Python)

For scripted work use `simple-salesforce`. SOQL in, dicts out.

```python
from simple_salesforce import Salesforce

sf = Salesforce(
    username=os.environ["SF_USER"],
    password=os.environ["SF_PASS"],
    security_token=os.environ["SF_TOKEN"],
)

query = """
SELECT Id, Name, StageName, Amount, LastActivityDate, AccountId
FROM Opportunity
WHERE StageName IN ('Qualification', 'Proposal')
  AND LastActivityDate < LAST_N_DAYS:60
"""
for opp in sf.query_all(query)["records"]:
    # enrich, score, write back
    pass
```

### Option 3 — MCP (thin, evolving)

Salesforce MCP servers exist but are less mature than HubSpot's. If you use MCP for Salesforce today, treat it as a read-only exploration layer and keep your writes on the CLI or Python path.

**My rule:** `sf` CLI for exploration, `simple-salesforce` for everything scheduled.

---

## Slash commands that move pipeline

Claude Code slash commands are just markdown files in `.claude/commands/`. The filename becomes the command. The body is the prompt. The agent runs it in the current session context.

The simplest one looks like this:

```markdown
<!-- .claude/commands/stale-opportunities.md -->

Run the stale-opportunity check:

1. Read `starters/crm-automation/stale_opportunity_check.py`
2. Execute it with `--days 60 --stages qualified,proposal --dry-run`
3. Read the output and give me the top 10 deals where the primary contact has left the company or a new ICP-match hire was detected
4. Ask me whether to run it again without --dry-run to write back to HubSpot
```

Type `/stale-opportunities` in your Claude Code session. The agent reads the file, executes the script, summarizes the output. If you want the write to happen, tell it yes. If the report looks off, tell it no and iterate on the script — the agent knows the full context because it just read the file.

Three slash commands worth building for RevOps:

1. **`/stale-opportunities`** — the 60-day check. Today's chapter builds this one all the way through.
2. **`/champion-left`** — scans your open pipeline for primary contacts whose Apollo employment record flipped in the last 14 days. Pipes the list to a Slack DM for the AE.
3. **`/new-hire-trigger`** — for every target account in your ABM list, search Apollo for new hires in the last 30 days matching your ICP titles. Flag the ones at accounts currently in your pipeline.

The pattern is the same every time: a slash command reads a Python file, runs it with flags, summarizes output, optionally executes the write.

---

## Worked example: `/stale-opportunities`

The script ships in `starters/crm-automation/stale_opportunity_check.py`. Here is the full loop.

### 1. Query stale deals from HubSpot

```python
def fetch_stale_deals(client, days: int, stages: list[str]) -> list[dict]:
    cutoff_ms = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
    search = PublicObjectSearchRequest(
        filter_groups=[{
            "filters": [
                {"propertyName": "dealstage", "operator": "IN", "values": stages},
                {"propertyName": "hs_lastmodifieddate", "operator": "LT", "value": str(cutoff_ms)},
            ]
        }],
        properties=["dealname", "amount", "dealstage", "hs_lastmodifieddate", "hubspot_owner_id"],
        limit=100,
    )
    return client.crm.deals.search_api.do_search(public_object_search_request=search).results
```

### 2. For each deal, pull the primary contact

```python
def get_primary_contact(client, deal_id: str) -> dict | None:
    assoc = client.crm.deals.associations_api.get_all(deal_id, "contacts")
    if not assoc.results:
        return None
    contact_id = assoc.results[0].id
    return client.crm.contacts.basic_api.get_by_id(
        contact_id, properties=["email", "firstname", "lastname", "jobtitle", "company"]
    )
```

### 3. Check employment via Apollo

```python
def check_employment(email: str) -> dict:
    r = requests.post(
        "https://api.apollo.io/v1/people/match",
        json={"email": email},
        headers={"X-Api-Key": APOLLO_API_KEY},
        timeout=15,
    )
    person = r.json().get("person", {})
    return {
        "still_at_company": person.get("organization", {}).get("name") == original_company,
        "current_title": person.get("title"),
        "current_company": person.get("organization", {}).get("name"),
        "departed_at": person.get("departure_date"),  # if present
    }
```

If the `current_company` differs from the deal's account name, the champion is gone. That alone is a reason to re-open the deal with a new contact, or close it out cleanly.

### 4. Look for new ICP hires at the account

```python
def find_new_hires(company_domain: str, icp_titles: list[str], within_days: int = 30) -> list[dict]:
    r = requests.post(
        "https://api.apollo.io/v1/mixed_people/search",
        json={
            "q_organization_domains": company_domain,
            "person_titles": icp_titles,
            "page": 1,
            "per_page": 10,
        },
        headers={"X-Api-Key": APOLLO_API_KEY},
        timeout=15,
    )
    recent = [
        p for p in r.json().get("people", [])
        if p.get("employment_history", [{}])[0].get("start_date", "") > since_iso(within_days)
    ]
    return recent
```

A new VP of Sales, new CRO, new Head of RevOps — any of those changes the buying context enough to justify a re-pitch. You are looking for any hire whose employment start date at the account is within the last 30 days and whose title matches your ICP.

### 5. Scan for news signals (optional)

```python
def check_news_signals(company_name: str) -> list[str]:
    if not EXA_API_KEY:
        return []
    r = requests.post(
        "https://api.exa.ai/search",
        json={
            "query": f"{company_name} funding OR layoffs OR acquisition OR product launch",
            "num_results": 5,
            "start_published_date": (datetime.now() - timedelta(days=30)).isoformat(),
        },
        headers={"x-api-key": EXA_API_KEY},
        timeout=15,
    )
    return [item["title"] for item in r.json().get("results", [])]
```

### 6. Write the summary back to the deal

```python
def update_deal_properties(client, deal_id: str, summary: dict):
    props = {
        "agent_last_enriched_at": datetime.now().isoformat(),
        "agent_stale_check_status": summary["status"],  # actionable | dead | needs_review
        "agent_signals_summary": summary["narrative"],
        "agent_disqualify_reason": summary.get("disqualify_reason", ""),
    }
    client.crm.deals.basic_api.update(
        deal_id,
        simple_public_object_input={"properties": props},
    )
```

Every field is readable text. An AE opens the deal, sees `agent_signals_summary: "VP of RevOps joined 11 days ago (Maya Chen, from Gong). Funding round closed last week. Original champion Jen Rios now at Rippling."` and knows in three seconds whether to re-engage.

---

## Custom property schema

Add these four properties to your Deal object in HubSpot (Settings → Properties → Create Property). Same schema works in Salesforce as custom fields on Opportunity.

| Property | Type | Purpose |
|----------|------|---------|
| `agent_last_enriched_at` | Date/time | When the agent last ran against this deal |
| `agent_stale_check_status` | Dropdown: `actionable`, `dead`, `needs_review` | One-word verdict from the script |
| `agent_signals_summary` | Multi-line text | Narrative summary written by the script |
| `agent_disqualify_reason` | Dropdown: `bad_timing`, `wrong_persona`, `left_company`, `competitor_won`, `budget_gone` | Set when status = dead |

Four properties is the floor. Add more as the motion matures — I use a fifth called `agent_priority_score` that weights new-hire presence, funding signals, and contact-availability into a 0-100 number my dashboard sorts by.

---

## Wiring it to a workflow

Two patterns. Pick one, or run both.

**Pattern A — cron.** A nightly `launchd` job on your Mac or a GitHub Action runs the script against every deal in the qualified/proposal stages past 60 days. The script writes back. The AE opens HubSpot in the morning and sees fresh properties.

```bash
# ~/Library/LaunchAgents/com.yourname.stale-opps.plist
# schedules: python3 /path/to/stale_opportunity_check.py at 06:00 daily
```

**Pattern B — HubSpot workflow webhook.** A HubSpot workflow fires when `hs_lastmodifieddate > 60 days AND dealstage IN (qualified, proposal)`. The workflow calls a webhook. Your local server (or a cheap Cloudflare Worker) receives the webhook and runs the script against that one deal. Real-time, one-at-a-time, cleaner audit trail.

Salesforce equivalent: a Flow with the same criteria fires an outbound message to your webhook endpoint.

Cron is simpler to stand up. Webhooks scale better once you cross thousands of deals.

---

## The Salesforce nurture mining motion

This is the motion I have made the most pipeline from, and it is the one nobody runs.

Every sales team has a graveyard of closed-lost and closed-abandoned deals. Half the time the reason they died was timing — the buyer was not ready, the budget was not there, the exec sponsor had not joined yet. A year later every one of those reasons has potentially inverted, and nobody is going back to look.

Run the same script above against the closed-lost filter instead of the 60-day filter. Filter further to deals where the `disqualify_reason` was `bad_timing` or `budget_gone`. For each: re-enrich the contact (are they still there? promoted? moved?), scan the account (new exec? funding? layoffs in the buyer's department?), then re-score.

What comes back is a short list of accounts where the blocker that killed the deal last year may not exist this year. You hand that to your best AE, not your newest SDR. The hit rate on a mined-nurture list is higher than a cold-sourced list because the relationship was warm and the disqualification was time-bound.

The whole motion is one extra flag on the slash command: `/stale-opportunities --stages closed_lost --disqualify-reasons bad_timing,budget_gone`.

---

## What this is, what this isn't

**This is not a replacement for your SDR.** It is a way to make your SDR's list shorter and sharper. The script generates the list of deals worth a human's attention. The human still writes the email.

**This is not a replacement for your RevOps person.** It is a way to hand them back the hours they currently spend pulling lists and updating fields. What RevOps does with those hours is better segmentation, better forecasting, better plays — the work that is actually rev-ops-shaped.

**This is not a replacement for your marketer.** It is a signal feed marketers can trigger campaigns off of. New VP of RevOps joined at a stale account → that is a perfect moment for a marketing play, and now the signal exists.

The ones who adopt this become something different than what they were. The ones who do not will be replaced by the ones who did. That is the actual delta, and the tool is the smallest part of it.

---

## What's next

The starter script and slash-command file ship in `starters/crm-automation/`. Clone, add your tokens to `.env`, run with `--dry-run` first. When the output looks right, rerun without the flag and watch the deals update.

The next chapter extends the pattern to multi-agent RevOps orchestration — one agent running stale-opportunity checks, another running champion-change detection, a third running new-hire triggers, all writing to the same set of custom properties with different signal types. The CRM becomes the shared canvas. Coming soon.
