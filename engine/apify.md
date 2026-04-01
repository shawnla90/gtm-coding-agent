# Apify CLI

**Category:** Scraping / Research
**Connection:** CLI + API
**Cost:** $25-49/month gets you 10,000+ follower scrapes, dozens of actor runs
**Install:** `npm i -g apify-cli`

---

## What It Does

Apify is a web scraping and automation platform. The CLI lets you run scraping "actors" (pre-built scrapers) from your terminal. Your coding agent can trigger a scrape, go do other work, and come back when the data is ready.

For GTM operators, this means: follower lists, company data, engagement signals, competitor analysis. All from the command line. All running in the background.

## Setup

```bash
# Install
npm i -g apify-cli

# Authenticate (uses your Apify account token)
apify login

# Verify
apify info
```

Your API token is at https://console.apify.com/account/integrations. The CLI stores it locally after login.

## Key Actors for GTM

Actors are pre-built scrapers on the Apify platform. These are the ones that matter for go-to-market work:

| Actor | What It Scrapes | Typical Cost |
|-------|----------------|-------------|
| `api-ninja/x-twitter-followers-scraper` | X/Twitter follower lists with bios | ~$5 for 10K followers |
| `apidojo/instagram-scraper` | Instagram profiles, posts, followers | ~$3-5 per batch |
| `compass/crawler-google-places` | Google Maps business data | Varies by volume |
| `apify/web-scraper` | Generic website scraping | Depends on pages |

## Running Actors from CLI

The basic pattern: create an input JSON, call the actor, fetch results.

```bash
# Run an actor with inline input
apify call api-ninja/x-twitter-followers-scraper \
  --input='{"username": "competitor_handle", "maxFollowers": 10000}'

# Run with input from a file
echo '{"username": "competitor_handle", "maxFollowers": 10000}' > input.json
apify call api-ninja/x-twitter-followers-scraper --input=input.json
```

The actor runs on Apify's cloud. Your terminal is free to do other things while it processes. When it finishes, you get a run ID.

## Fetching Results

```bash
# Get the dataset from a completed run
apify datasets get-items <dataset_id> --json > followers.json

# Or get run info first, then fetch dataset
apify runs info <run_id> --json
```

## Python Pattern (for batch work)

When you need to process results or cross-reference multiple scrapes:

```python
#!/usr/bin/env python3
"""Fetch Apify dataset results and save as JSON/CSV."""

import json
import subprocess
import csv
from pathlib import Path


def fetch_dataset(run_id: str, output_path: str):
    """Fetch dataset from a completed Apify run."""
    result = subprocess.run(
        ["apify", "datasets", "get-items", run_id, "--json"],
        capture_output=True, text=True
    )

    if result.returncode != 0:
        # Try as a run ID - get the default dataset
        result2 = subprocess.run(
            ["apify", "runs", "info", run_id, "--json"],
            capture_output=True, text=True
        )
        if result2.returncode == 0:
            run_info = json.loads(result2.stdout)
            dataset_id = run_info.get("defaultDatasetId", "")
            if dataset_id:
                result = subprocess.run(
                    ["apify", "datasets", "get-items", dataset_id, "--json"],
                    capture_output=True, text=True
                )

    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return

    data = json.loads(result.stdout)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)

    count = len(data) if isinstance(data, list) else 1
    print(f"Saved {count} records to {output_path}")
```

## GTM Use Cases

### Competitor Displacement Lists

Scrape followers of your direct competitors. Cross-reference across multiple scrapes. Companies that follow 3+ competitors are high-intent prospects.

```bash
# Scrape competitor A's followers
apify call api-ninja/x-twitter-followers-scraper \
  --input='{"username": "competitor_a", "maxFollowers": 10000}'

# Scrape competitor B's followers
apify call api-ninja/x-twitter-followers-scraper \
  --input='{"username": "competitor_b", "maxFollowers": 10000}'

# Cross-reference in Python or Claude Code
# "Find companies that appear in both follower lists"
```

Real example: we scraped 11,000 followers from a competitor displacement list. Cross-referenced against an industry tool's audience. Dozens of overlapping companies surfaced. Each overlap is a buying signal.

### Instagram Growth and Bot Detection

Low-lift, high-return. Run an Instagram scraper in the background to identify bot followers, analyze engagement patterns, or monitor competitor accounts. The scraper runs on Apify's cloud while you do other work.

See [ig-growth-engine](https://github.com/shawnla90/ig-growth-engine) for a reference implementation of automated Instagram engagement using Apify scrapers. It runs hourly via cron on a Mac Mini with minimal attention required.

Results: real engagement from the bot, reactions from actual users. The key is testing messaging and letting it run in the background while you focus on higher-priority work.

### Enrichment Signal Stacking

Combine Apify scrapes with Apollo enrichment:

1. Scrape a competitor's X followers (Apify CLI)
2. Extract company domains from bios
3. Enrich companies via Apollo API (batch, free tier)
4. Score by ICP fit
5. Push to your CRM or Supabase

This entire pipeline runs from terminals. No browser tabs. No dashboards. Just commands and scripts.

## Rate Limits and Gotchas

- **Compute costs vary by actor.** Check the actor's pricing page before large runs. Some charge per result, others per compute unit.
- **Large scrapes can take 10-30 minutes.** Run them in background terminals (tmux) and check results later.
- **X/Twitter scrapers respect API limits.** Follower lists over 10K may require multiple runs or pagination.
- **Save results immediately.** Apify datasets expire. Fetch and save to local JSON/CSV as soon as the run completes.
- **Budget tracking:** Your Apify dashboard shows spend. $25-30/month covers most GTM scraping needs.

## Integration with Claude Code

Tell Claude Code to run Apify actors directly:

```
> Scrape the followers of @competitor_handle using the X followers scraper.
> Save results to data/competitor_followers.json.
> Then cross-reference against our existing prospect list in data/prospects.csv.
> Flag any companies that appear in both.
```

Claude Code runs the CLI commands, fetches results, and does the analysis. You review the output.
