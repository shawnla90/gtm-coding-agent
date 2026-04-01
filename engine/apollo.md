# Apollo

**Category:** Enrichment / Contact Database
**Connection:** API (Python wrapper)
**Cost:** Free tier gives 10,000 email credits/month with API access
**Auth:** API key from https://app.apollo.io/settings/integrations/api_keys

---

## What It Does

Apollo is a contact database and enrichment API. Free tier is the best in GTM. You give it an email, domain, or person's name and company, and it gives you back title, company data, LinkedIn URL, phone numbers, and more.

For GTM operators running from terminals, Apollo is your enrichment layer. Scrape a list of companies or followers (via Apify), then enrich them through Apollo to get contact details for outreach.

## Setup

```bash
# No CLI to install. Apollo is API-only.
# Add your key to .env
echo "APOLLO_API_KEY=your_key_here" >> .env
```

## Key Endpoints

| Endpoint | Credits | What It Does |
|----------|---------|-------------|
| `people/match` | 0 credits | Match a person by email, name+company, or LinkedIn URL. Job change detection. |
| `mixed_people/search` | 1 credit/result | Search Apollo's database by filters (title, company size, industry) |
| `organizations/enrich` | 0 credits | Enrich a company by domain (employee count, funding, industry) |

The `people/match` endpoint at 0 credits is significant. You can verify whether contacts have changed jobs, get updated titles, and confirm email validity without spending credits. This is how you keep lists clean.

## Batch Enrichment Pattern

The most common GTM workflow: take a CSV of companies or emails, enrich them through Apollo, and save results.

```python
#!/usr/bin/env python3
"""Batch enrich contacts via Apollo API with rate limiting and caching."""

import csv
import json
import os
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("APOLLO_API_KEY")
BASE_URL = "https://api.apollo.io/api/v1"
CACHE_FILE = "data/.apollo-cache.json"
BATCH_SIZE = 50
SLEEP_BETWEEN = 1.0  # seconds between batches


def load_cache():
    if Path(CACHE_FILE).exists():
        return json.loads(Path(CACHE_FILE).read_text())
    return {}


def save_cache(cache):
    Path(CACHE_FILE).parent.mkdir(parents=True, exist_ok=True)
    Path(CACHE_FILE).write_text(json.dumps(cache, indent=2))


def enrich_person(email: str, cache: dict) -> dict:
    """Enrich a single person by email. Uses cache to avoid duplicate calls."""
    if email in cache:
        return cache[email]

    resp = requests.post(
        f"{BASE_URL}/people/match",
        json={"api_key": API_KEY, "email": email},
        timeout=10
    )

    if resp.status_code == 200:
        person = resp.json().get("person", {})
        cache[email] = person or {"status": "not_found"}
    elif resp.status_code == 429:
        print("Rate limited. Sleeping 60s...")
        time.sleep(60)
        return enrich_person(email, cache)  # retry
    else:
        cache[email] = {"status": "error", "code": resp.status_code}

    return cache.get(email, {})


def enrich_csv(input_csv: str, output_csv: str):
    """Enrich a CSV of contacts, adding Apollo data."""
    cache = load_cache()

    with open(input_csv) as infile:
        reader = list(csv.DictReader(infile))

    total = len(reader)
    enriched = []

    for i, row in enumerate(reader):
        email = row.get("email", "").strip()
        if not email:
            enriched.append(row)
            continue

        person = enrich_person(email, cache)
        row["apollo_title"] = person.get("title", "")
        row["apollo_company"] = person.get("organization", {}).get("name", "")
        row["apollo_linkedin"] = person.get("linkedin_url", "")
        enriched.append(row)

        # Save cache every batch
        if (i + 1) % BATCH_SIZE == 0:
            save_cache(cache)
            print(f"  {i + 1}/{total} enriched...")
            time.sleep(SLEEP_BETWEEN)

    save_cache(cache)

    # Write output
    fieldnames = enriched[0].keys() if enriched else []
    with open(output_csv, "w", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(enriched)

    print(f"Done. {total} contacts enriched. Output: {output_csv}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python3 apollo-enrich.py input.csv output.csv")
        sys.exit(1)
    enrich_csv(sys.argv[1], sys.argv[2])
```

## Rate Limiting Strategy

- **Free tier:** 50 requests/minute, 10,000 email credits/month
- **Batch size:** Process 50 contacts, then sleep 1 second. Keeps you well under rate limits.
- **Resumable caching:** Cache every result to a JSON file. If the script crashes or you hit a limit, restart and it skips already-cached results.
- **Zero-credit endpoints first:** Use `people/match` and `organizations/enrich` (both 0 credits) before `mixed_people/search` (1 credit per result).

## Company Enrichment (0 Credits)

```python
def enrich_company(domain: str) -> dict:
    """Enrich a company by domain. 0 credits."""
    resp = requests.get(
        f"{BASE_URL}/organizations/enrich",
        params={"api_key": API_KEY, "domain": domain},
        timeout=10
    )
    if resp.status_code == 200:
        return resp.json().get("organization", {})
    return {}

# Returns: name, industry, employee_count, funding, linkedin_url, etc.
```

## Job Change Detection (0 Credits)

The `people/match` endpoint tells you if someone has moved companies since you last checked. Use this to keep your lists accurate before running campaigns.

```python
# Check if a contact still works at the same company
person = enrich_person("contact@company.com", cache)
current_company = person.get("organization", {}).get("name", "")
if current_company != expected_company:
    print(f"Job change detected: now at {current_company}")
```

Run this across your entire database periodically. It costs 0 credits and prevents you from emailing people at companies they left.

## Integration with the Pipeline

The typical flow from scrape to outreach:

```
Apify CLI (scrape followers) → JSON/CSV
    ↓
Apollo (enrich by email/domain) → enriched CSV
    ↓
Python (ICP scoring, dedup) → scored list
    ↓
Supabase or SQLite (warehouse) → queryable database
    ↓
Claude Code ("show me hot leads") → outreach list
```

Each step runs in a terminal. Each step can run in the background. The pipeline is just scripts and CLI commands.
