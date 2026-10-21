# Chapter 07 — Python for GTM

**Python is the duct tape of GTM ops. It connects everything, transforms anything, and your coding agent writes most of it for you.**

---

## Why Python

Every GTM tool you care about has a Python SDK or a REST API that Python can call in three lines. Need to enrich a list of 500 domains? Python. Need to pull deals from HubSpot, cross-reference with LinkedIn data, and output a prioritized CSV? Python. Need to generate 200 personalized email first lines? Python.

Here's why it wins for GTM work specifically:

- **Simple syntax.** If you can read English, you can read Python. `for company in companies:` means exactly what it looks like.
- **Massive library ecosystem.** 400,000+ packages. Someone already solved your problem.
- **Every API has a Python SDK.** Apollo, HubSpot, Salesforce, Clay, Exa, OpenAI — all have official or community Python libraries.
- **AI/ML native.** When you want to score leads, classify intent, or generate content, the tooling is Python-first.
- **Your coding agent is fluent in it.** Claude Code writes Python better than most junior developers. It's the language with the most training data.

## You Don't Need to Be a Developer

Let's get this out of the way: you are not becoming a software engineer. You're becoming someone who can:

1. Describe what you want in plain English
2. Let Claude Code write the first draft
3. Read the script and understand what it does
4. Run it
5. Ask Claude to fix what's wrong

That's the workflow. You're a pilot, not a mechanic. You need to know what the instruments do. You don't need to build the engine.

The scripts in this chapter are all things you'd tell Claude Code to write. I'm showing them to you so you can recognize the patterns when they come back.

## Environment Setup

You need three things:

### 1. Python 3.10+

Check what you have:

```bash
python3 --version
```

If it's 3.10 or higher, you're good. If not, install it:

```bash
# macOS
brew install python@3.12

# Or download from python.org
```

### 2. Virtual Environments (venv)

A virtual environment is a sandboxed folder where your project's packages live. It keeps your projects from stepping on each other.

```bash
# Create a venv in your project folder
python3 -m venv .venv

# Activate it (you'll do this every time you work on this project)
source .venv/bin/activate

# Your terminal prompt will show (.venv) — that means it's active
```

Always activate your venv before installing packages or running scripts. If you forget, packages install globally and things break in confusing ways.

### 3. pip for Packages

pip is Python's package manager. With your venv active:

```bash
pip install requests pandas python-dotenv
```

Save your dependencies so others (or future you) can replicate:

```bash
pip freeze > requirements.txt
```

Restore them later:

```bash
pip install -r requirements.txt
```

## The Essential Packages

You'll use these in almost every GTM script:

| Package | What It Does | Install |
|---------|-------------|---------|
| `requests` | Makes HTTP/API calls | `pip install requests` |
| `pandas` | Data manipulation (CSVs, filtering, joins) | `pip install pandas` |
| `python-dotenv` | Loads API keys from `.env` files | `pip install python-dotenv` |
| `csv` | Read/write CSV files (built-in, no install needed) | — |
| `json` | Parse JSON responses (built-in) | — |
| `time` | Rate limit delays (built-in) | — |

Before you install anything else, these six cover 80% of GTM scripting.

## Keeping Secrets Safe

Never hardcode API keys in your scripts. Use a `.env` file:

```bash
# .env (add this file to .gitignore — never commit it)
APOLLO_API_KEY=your-key-here
OPENAI_API_KEY=sk-your-key-here
HUBSPOT_API_KEY=pat-your-key-here
```

Then load them: `load_dotenv()` + `os.getenv("APOLLO_API_KEY")`. If the value comes back `None`, you misspelled the variable or forgot to create the file.

The same rule, run against Prospeo from the repo or from a phone agent, is [Chapter 24](./24-enrichment-on-the-go.md). The script there has a dry-run, so the first pass spends nothing.

## Pattern 1 — API Enrichment

**The scenario:** You have a CSV of 200 company domains. You want to enrich each one with employee count, industry, and funding data from Apollo.

```python
import requests
import csv
import os
import time
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("APOLLO_API_KEY")
INPUT_FILE = "domains.csv"
OUTPUT_FILE = "enriched_domains.csv"

def enrich_domain(domain):
    """Call Apollo's enrichment API for a single domain."""
    url = "https://api.apollo.io/api/v1/organizations/enrich"
    headers = {"Content-Type": "application/json", "Cache-Control": "no-cache"}
    params = {"api_key": API_KEY, "domain": domain}

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        data = response.json().get("organization", {})
        return {
            "domain": domain,
            "name": data.get("name", ""),
            "employee_count": data.get("estimated_num_employees", ""),
            "industry": data.get("industry", ""),
            "annual_revenue": data.get("annual_revenue_printed", ""),
        }
    return {"domain": domain, "name": "FAILED", "employee_count": "", "industry": "", "annual_revenue": ""}

# Read domains, enrich, write results
with open(INPUT_FILE) as infile:
    domains = [row["domain"] for row in csv.DictReader(infile)]

results = []
for i, domain in enumerate(domains):
    print(f"Enriching {i+1}/{len(domains)}: {domain}")
    results.append(enrich_domain(domain))
    time.sleep(0.5)  # respect rate limits

with open(OUTPUT_FILE, "w", newline="") as outfile:
    writer = csv.DictWriter(outfile, fieldnames=results[0].keys())
    writer.writeheader()
    writer.writerows(results)

print(f"Done. {len(results)} companies written to {OUTPUT_FILE}")
```

That `time.sleep(0.5)` matters. APIs have rate limits. Hit them too fast and you get blocked. Half a second between calls is a safe default for most GTM APIs.

## Pattern 2 — CSV Pipeline

**The scenario:** You have a raw list of 1,000 companies. You want to filter to companies with 50-500 employees in SaaS, then score them by how well they match your ICP.

```python
import pandas as pd

# Read the raw list
df = pd.read_csv("raw_companies.csv")

# Filter: 50-500 employees, SaaS industry
filtered = df[
    (df["employee_count"] >= 50) &
    (df["employee_count"] <= 500) &
    (df["industry"].str.contains("software|saas", case=False, na=False))
]

# Score: simple weighted model
def icp_score(row):
    score = 0
    if 100 <= row["employee_count"] <= 300:
        score += 40  # sweet spot for your product
    if row.get("funding_stage") in ["Series A", "Series B"]:
        score += 30  # funded but not enterprise yet
    if row.get("tech_stack") and "hubspot" in str(row["tech_stack"]).lower():
        score += 30  # they use a tool you integrate with
    return score

filtered = filtered.copy()
filtered["icp_score"] = filtered.apply(icp_score, axis=1)

# Sort by score, output the top tier
output = filtered.sort_values("icp_score", ascending=False)
output.to_csv("scored_companies.csv", index=False)

print(f"Filtered to {len(output)} companies. Top score: {output['icp_score'].max()}")
```

This is the kind of script that replaces a $300/month data tool. It runs in seconds, and you control every filter and scoring criterion.

## Pattern 3 — Email Personalization

**The scenario:** You have 50 qualified prospects. You want a personalized first line for each one, generated by an LLM, ready to paste into your sequencer.

```python
import csv
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_first_line(name, company, role, recent_signal):
    """Generate a personalized cold email opening line."""
    prompt = f"""Write a cold email first line for:
- Name: {name}
- Company: {company}
- Role: {role}
- Recent signal: {recent_signal}

Rules:
- One sentence only
- Reference the signal naturally
- No flattery, no "I saw that you..."
- Sound like a peer, not a vendor"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=60,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()

# Read prospects, generate first lines, write output
with open("prospects.csv") as f:
    prospects = list(csv.DictReader(f))

for p in prospects:
    p["first_line"] = generate_first_line(
        p["name"], p["company"], p["role"], p.get("signal", "")
    )
    print(f"  {p['name']}: {p['first_line']}")

with open("prospects_with_lines.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=prospects[0].keys())
    writer.writeheader()
    writer.writerows(prospects)
```

50 personalized first lines in under a minute, for about $0.02 in API costs. That's the math that makes Python + APIs unbeatable.

## Error Handling Basics

Scripts fail. APIs go down. CSVs have weird encoding. Here's how to not lose an hour of enrichment when row 847 hits an error:

```python
import time, logging

logging.basicConfig(filename="enrichment.log", level=logging.INFO)

def safe_enrich(domain, max_retries=3):
    for attempt in range(max_retries):
        try:
            result = enrich_domain(domain)
            logging.info(f"OK: {domain}")
            return result
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:  # rate limited
                time.sleep(2 ** attempt)       # backoff: 1s, 2s, 4s
            else:
                logging.error(f"HTTP error on {domain}: {e}")
                return None
        except Exception as e:
            logging.error(f"Error on {domain}: {e}")
            return None
    return None
```

The key patterns: **try/except** wraps anything that can fail. **Retry with backoff** handles rate limits (wait 1s, then 2s, then 4s). **Logging** writes to a file so you can debug after a long run. **Return None** instead of crashing so the rest of your list still processes.

## The Workflow in Practice

1. **You tell Claude Code:** "I have a CSV of 300 domains. Enrich each one with Apollo, filter to 50+ employees, output a scored list."
2. **Claude Code writes the script.** Looks like Patterns 1 and 2 combined.
3. **You read through it.** Does it load your `.env`? Does the scoring match your ICP?
4. **You run it:** `python3 enrich_and_score.py`
5. **Something breaks.** You tell Claude what went wrong. Claude fixes it. Run again.

That loop — describe, generate, review, run, iterate — is the entire skill.

## Exercise

Ask Claude Code to write a script that:

1. Reads a CSV with columns: `name`, `email`, `company`, `domain`
2. Calls a free API (like `https://api.hunter.io/v2/domain-search`) to verify the domain exists
3. Filters out rows where the domain doesn't resolve
4. Writes the clean list to `verified_leads.csv`

You don't need to run it against a real API. Just get the script written, read through it, and make sure you understand each section.

---

**Next:** [Chapter 08 — The GTM Tools Ecosystem](./08-tools-ecosystem.md) — which tools to use, which to skip, and when a Python script replaces a $200/month subscription.
