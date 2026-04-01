# Chapter 08 — The GTM Tools Ecosystem

**Every GTM tool is either a warehouse (stores your data) or a workbench (transforms it). Know which is which and you'll stop overpaying for tools that overlap.**

---

## Two Types of Tools

Before evaluating any GTM tool, classify it:

**Warehouses** store your source of truth. Your CRM, your database, your master spreadsheet. Data lives here long-term. You query it, report from it, and sync everything back to it. You want exactly one warehouse for each data type. Two CRMs is a nightmare. Two sources of truth is zero sources of truth.

**Workbenches** process and transform data. Enrichment tools, sequencing platforms, research tools, scraping services. Data passes through them. They take input, do something useful, and produce output that goes back to your warehouse.

The mistake most GTM teams make: treating a workbench like a warehouse. They enrich data in Clay, leave it there, and never sync it back. Then they enrich more data in Apollo and leave it there too. Now their prospect data lives in three places and none of them agree.

The rule: **workbenches feed warehouses.** Always. Data flows through workbenches and lands in your warehouse.

```
[Raw Data] → [Workbench: Enrich] → [Workbench: Score] → [Warehouse: CRM]
                                                                ↑
[Workbench: Sequence] ← [Workbench: Personalize] ← ────────────┘
```

## The Tools You Should Know

### Apify

Web scraping platform with a CLI. Run pre-built scrapers ("actors") from your terminal for follower lists, company data, engagement signals. The CLI runs scrapes on Apify's cloud while your terminal is free to do other work. $25-30/month covers most GTM scraping needs. The key GTM use case: scrape competitor followers, cross-reference against industry tools, and surface overlapping companies as buying signals. See `engine/apify.md` for full setup and scripts.

```bash
# Scrape 10K followers from a competitor's X account
apify call api-ninja/x-twitter-followers-scraper \
  --input='{"username": "competitor_handle", "maxFollowers": 10000}'
```

### Apollo

Contact database + email sequencing. Best free tier in GTM: 10,000 email credits/month with API access. Enrich people by email or LinkedIn URL, enrich companies by domain, search their database by filters. Rate limit: 50 req/min on free tier. Your first stop when you have a domain and need to find the right person. Data quality drops outside US/UK — verify with a second source if selling internationally.

The batch enrichment pattern is critical: take a CSV from an Apify scrape, run it through Apollo in batches with resumable caching, and push enriched data to your warehouse. The `people/match` endpoint costs 0 credits and handles job-change detection across your entire database. See `engine/apollo.md` for the full batch script and rate limiting strategy.

```python
# Apollo person enrichment — the call you'll make most often
response = requests.post("https://api.apollo.io/api/v1/people/match",
    json={"api_key": APOLLO_KEY, "email": "cto@targetcompany.com"})
person = response.json().get("person", {})
```

### Clay

Waterfall enrichment + workflow builder. Think of it as a spreadsheet that can call 75+ data providers in sequence — tries Provider A, falls back to B, then C. Great for ABM research where you're going deep on 50 accounts. API lets you trigger workflows via webhook and push/pull data from tables.

**The honest question:** "Am I using Clay's waterfall logic, or am I just using it as a UI for one API?" If the answer is one API, a Python script does the same thing for free. Paid plans start around $150/month and credits deplete fast.

### Exa

AI-powered web search. Instead of keyword search, you describe what you want in natural language. Transformative for ICP research — instead of "series B fintech SF," you search "companies building financial infrastructure for startups that recently raised Series B" and get meaningfully better results. Also great for `find_similar` (give it a competitor URL, get similar companies) and signal detection.

```python
from exa_py import Exa
exa = Exa(api_key=EXA_KEY)
results = exa.search("B2B SaaS companies automating outbound prospecting",
    num_results=20, type="company")
```

### Firecrawl

Web scraping API. Give it a URL, get clean markdown or structured JSON back. No HTML parsing. Use it for pricing page monitoring, extracting team info from "About" pages, tracking job postings for hiring signals, and pulling competitor feature lists. LLM-powered extraction handles messy HTML gracefully.

```python
from firecrawl import FirecrawlApp
app = FirecrawlApp(api_key=FIRECRAWL_KEY)
result = app.scrape_url("https://competitor.com/pricing", params={"formats": ["markdown"]})
```

### Google Workspace (via APIs)

Programmatic access to Gmail, Calendar, Drive, and Sheets — free if you already have Workspace. Gmail API for sending/reading email, Sheets API as a lightweight CRM alternative, Calendar API for scheduling automation. Setup uses OAuth 2.0 (see Chapter 04). Takes 30 minutes initially, then unlimited free access. Use it any time you're manually doing something in Google apps that follows a pattern.

### HubSpot

CRM with one of the most generous free tiers in SaaS. Contacts, companies, deals, tasks — full API access, official Python SDK. Rate limit: 100 req/10 seconds. HubSpot is your warehouse. Everything flows back here. With the HubSpot MCP server, Claude Code can talk to your CRM directly — "find all deals closing this month" works from the terminal.

## The Tool Evaluation Framework

Before paying for any GTM tool, run it through these questions:

### 1. Does it have an API?

If no, it's a dead end for automation. You'll be stuck doing manual exports forever. This is a dealbreaker.

### 2. What are the rate limits?

A tool with an API but a 10-requests-per-minute limit will bottleneck your workflows. Check the docs before you commit.

| Tier | Typical Limit | What It Means |
|------|--------------|---------------|
| Generous | 100+ req/min | Batch workflows work fine |
| Moderate | 20-50 req/min | Fine for small lists, add sleep() for large ones |
| Restrictive | <10 req/min | Only useful for real-time, one-at-a-time lookups |

### 3. What does it cost per API call?

Some tools charge per seat. Others charge per credit/call. Calculate your actual unit economics:

- **I need to enrich 1,000 companies/month.** At $0.05/credit, that's $50. At $0.50/credit, that's $500. Same feature, 10x price difference.
- **Compare to the Python alternative.** Can you call a free or cheaper API directly and get 80% of the same data?

### 4. How's the data quality?

Test with 20 records you already know the answers to. If a tool gets email addresses right 60% of the time, it's not saving you work — it's creating cleanup work.

### 5. Can I replace it with a Python script?

This is the honest question. Many $200/month tools are a UI wrapped around an API you can call directly. If the tool's value is "it calls Apollo and Clearbit for me," you can build that in an afternoon with Claude Code.

Tools earn their price when they provide:
- Data you can't get elsewhere (proprietary databases)
- Logic that's hard to replicate (waterfall enrichment across 50 providers)
- Maintenance you don't want to handle (keeping OAuth tokens fresh, handling API changes)

## Build vs. Buy: The Decision Framework

Here's a practical way to decide:

**Build it yourself when:**
- The workflow is a straight-line script (input → transform → output)
- You're calling 1-2 APIs you already have keys for
- The tool's UI doesn't add value beyond what a CSV gives you
- You'd spend more on the tool per month than the API costs per year
- You want full control over the logic (scoring, filtering, formatting)

**Buy the tool when:**
- It aggregates 10+ data sources you'd have to manage separately
- The UI saves you meaningful time (visual pipeline builders, drag-and-drop)
- It handles auth, rate limits, and error recovery across many providers
- Your team needs access and they won't use a Python script
- The data is proprietary — you can't get it any other way

**The $20/month test:** If you can write a Python script in a single Claude Code session that does what the tool does, and it costs under $20/month in API fees to run, build it. You'll learn more, own the code, and save money.

## Exercise: Evaluate a Tool

Pick one tool from your current stack (or one you're considering). Run it through the framework:

1. **Does it have an API?** Find the docs. Link them.
2. **Rate limits?** What's the ceiling for your volume?
3. **Cost per call?** Calculate your monthly cost at your expected volume.
4. **Data quality?** Test 20 records. What's the accuracy?
5. **Python replacement?** Could Claude Code write a script that does 80% of what this tool does? How long would it take?

Write your answers in `gtm-os/engine/` as a tool evaluation file. You'll build a library of these over time, and they'll inform every tool decision going forward.

## Putting It Together

Your GTM stack should look like this:

```
WAREHOUSE (one source of truth)
├── HubSpot CRM (or Salesforce, or even a well-structured Google Sheet)
│
WORKBENCHES (data flows through these)
├── Apollo          → contact discovery + enrichment
├── Exa             → ICP research + company discovery
├── Firecrawl       → web scraping + competitive intel
├── Python scripts   → custom pipelines, scoring, personalization
├── Claude Code      → the orchestrator that builds and runs everything
│
OUTPUTS
├── Sequencer (Apollo, Instantly, etc.)  → sends the emails
├── Google Workspace                      → calendar, docs, sheets
└── Content pipeline                      → blog, LinkedIn, email
```

Every workbench pushes data back to the warehouse. Every output pulls from the warehouse. No orphaned data sitting in a tool you'll forget about in three months.

---

**Next:** [Chapter 09 — Voice DNA & Content](./09-voice-dna-content.md) — extract your writing voice, kill AI slop, and create content that sounds like you instead of a chatbot.
