# Chapter 04: OAuth, CLI, and APIs

**Every GTM tool you want your agent to use connects in one of three ways: OAuth, CLI, or API. Pick the right one and integration takes minutes. Pick the wrong one and you'll burn a day debugging authentication.**

---

## The Three Connection Patterns

Your coding agent is powerful, but it's only as useful as the tools it can reach. Need to pull contacts from HubSpot? Check a prospect's recent funding on Crunchbase? Send a Slack alert when a target account visits your site? Each of those requires connecting an external tool to your agent workflow.

There are exactly three ways to do this. Every integration you'll ever build falls into one of these patterns.

---

## Pattern 1: OAuth — "Sign In With..."

You've used OAuth a hundred times. "Sign in with Google." "Connect your HubSpot account." You click a button, authorize access, and the tool stays connected until you revoke it.

In the agent world, OAuth is how **MCP servers** connect to SaaS tools. MCP — Model Context Protocol — is the new standard for connecting AI agents to external services. Think of it as USB for AI. Instead of writing custom code for every tool, MCP provides a standard interface.

Here's how it works:

1. An MCP server exists for a tool (e.g., HubSpot, Google Calendar, Salesforce)
2. You configure it in your agent's settings
3. It prompts you to authorize via OAuth — you sign in once
4. The agent can now read and write data through that connection

**Best for:** CRM access, email, calendar, any SaaS tool with an MCP server.

**Example:** The HubSpot MCP server lets Claude Code search contacts, create deals, update properties, and pull reports — all through natural language commands. You authorize once, and the agent can say "find all contacts with the title VP of Engineering who were created this month" and actually do it.

**The catch:** MCP is still early. The ecosystem is growing fast, but many tools don't have MCP servers yet. When one exists, use it. When it doesn't, move to Pattern 2 or 3.

---

## Pattern 2: CLI — Command-Line Tools

CLI tools are programs you install on your machine and run from the terminal. Your coding agent can run them directly, just like you would.

The big ones for GTM operators:

| CLI Tool | What It Does | Install |
|----------|-------------|---------|
| `gh` | GitHub — repos, issues, PRs | `brew install gh` |
| `gcloud` | Google Cloud — BigQuery, Cloud Functions | `brew install google-cloud-sdk` |
| `aws` | AWS — S3 storage, Lambda, SES email | `brew install awscli` |
| `apify` | Apify — web scraping, follower lists, data extraction | `npm i -g apify-cli` |
| `vercel` | Vercel — deploy websites | `npm i -g vercel` |
| `wrangler` | Cloudflare — Workers, Pages, R2 storage | `npm i -g wrangler` |
| `supabase` | Supabase — database, auth, storage | `npm i -g supabase` |
| `sqlite3` | SQLite — local database queries | Pre-installed on macOS |

For detailed documentation on specific tools, see the `engine/` folder — `engine/apify.md` and `engine/apollo.md` cover the full setup, use cases, and scripts for scraping and enrichment workflows.

Here's the pattern: you install the CLI, authenticate once (`gh auth login`, `gcloud auth login`), and then your coding agent can run commands through it.

```bash
# Your agent can run this directly
gh issue list --repo your-org/your-repo --label "gtm"

# Or this
gcloud bigquery query --use_legacy_sql=false \
  'SELECT email, company FROM `dataset.contacts` WHERE score > 80'
```

**Best for:** Developer tools, cloud services, deployment, anything with an official CLI.

**Why it's powerful for agents:** Claude Code runs in your terminal. It can execute any CLI command you can. When you say "deploy the landing page," the agent runs `vercel --prod`. When you say "upload this CSV to S3," the agent runs `aws s3 cp`. No API wrapper needed.

---

## Pattern 3: API — HTTP Calls from Scripts

When there's no MCP server and no CLI tool, you write a script that calls the API directly. This is the most flexible pattern and the one you'll use most for GTM-specific tools.

Most enrichment, research, and outbound tools expose REST APIs. Apollo, Clearbit, Exa, Firecrawl, Instantly, Smartlead — they all work this way. You send an HTTP request with your API key, you get data back.

Here's the standard Python pattern:

```python
import requests
import os
from dotenv import load_dotenv

load_dotenv()  # Load API key from .env file

def enrich_company(domain):
    """Get company data from an enrichment API."""
    response = requests.get(
        "https://api.enrichment-tool.com/v1/company",
        headers={"Authorization": f"Bearer {os.getenv('ENRICHMENT_API_KEY')}"},
        params={"domain": domain}
    )
    response.raise_for_status()
    return response.json()

# Use it
data = enrich_company("stripe.com")
print(f"Company: {data['name']}, Employees: {data['employee_count']}")
```

This pattern is the same regardless of the API. Swap out the URL, headers, and params, and you can connect to any tool that has a REST API.

**Best for:** Enrichment (Apollo, Clearbit), research (Exa, Firecrawl), outbound tools (Instantly, Smartlead), anything without an MCP server or CLI.

---

## MCP: The New Standard

MCP deserves its own section because it's changing the game.

Before MCP, connecting an agent to a tool meant writing a custom API wrapper, handling authentication, parsing responses, dealing with rate limits — for every single tool. MCP standardizes all of that.

An MCP server is a lightweight service that:
- Handles authentication with the external tool
- Exposes a set of actions the agent can take (search, create, update, delete)
- Returns structured data the agent can understand
- Manages rate limits and error handling

The ecosystem is growing fast. As of now, you'll find MCP servers for:
- **CRMs:** HubSpot, Salesforce
- **Productivity:** Google Drive, Slack, Notion, Linear
- **Developer tools:** GitHub, GitLab, Sentry
- **Data:** PostgreSQL, BigQuery
- **Search:** Brave Search, Exa

Check [modelcontextprotocol.io](https://modelcontextprotocol.io) for the current list. New servers ship weekly.

---

## The Decision Framework

When you need to connect a tool to your agent workflow, work through this in order:

```
1. Does an MCP server exist?
   → Yes: Use it. Fastest path. Best integration.
   → No: Continue.

2. Does a CLI tool exist?
   → Yes: Install it, authenticate, script it.
   → No: Continue.

3. Does the tool have a REST API?
   → Yes: Write a Python wrapper.
   → No: Check if there's a Zapier/webhook integration
         you can trigger from a script.
```

In practice for GTM work:
- **HubSpot, Salesforce** → MCP server (OAuth)
- **GitHub, AWS, Google Cloud** → CLI
- **Apollo, Clearbit, Exa, Firecrawl** → Python API wrapper
- **Instantly, Smartlead** → Python API wrapper
- **Your internal Postgres** → MCP server or direct `psql` CLI

---

## Practical Example: Building an Enrichment Script

Let's walk through connecting a hypothetical enrichment tool via API — the full pattern you'd use for Apollo, Clearbit, or any similar service.

**Step 1: Set up your environment.**

Create a `.env` file in your project root (this file should be in `.gitignore` — never commit API keys):

```
ENRICHMENT_API_KEY=your_key_here
```

**Step 2: Write the enrichment function.**

```python
# scripts/enrich.py
import requests
import csv
import os
import time
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("ENRICHMENT_API_KEY")
BASE_URL = "https://api.example.com/v1"

def enrich_person(email):
    """Enrich a single contact by email."""
    resp = requests.get(
        f"{BASE_URL}/person",
        headers={"Authorization": f"Bearer {API_KEY}"},
        params={"email": email},
        timeout=10
    )
    if resp.status_code == 200:
        return resp.json()
    elif resp.status_code == 404:
        return None  # Person not found
    else:
        resp.raise_for_status()

def enrich_list(input_csv, output_csv):
    """Enrich a CSV of contacts, adding company and title data."""
    with open(input_csv) as infile, open(output_csv, "w", newline="") as outfile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames + ["company", "title", "linkedin_url"]
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()

        for row in reader:
            data = enrich_person(row["email"])
            if data:
                row["company"] = data.get("company", "")
                row["title"] = data.get("title", "")
                row["linkedin_url"] = data.get("linkedin_url", "")
            writer.writerow(row)
            time.sleep(0.5)  # Respect rate limits

if __name__ == "__main__":
    enrich_list("contacts.csv", "contacts_enriched.csv")
    print("Done. Enriched contacts saved to contacts_enriched.csv")
```

**Step 3: Run it from your agent.**

Now you can tell Claude Code: "Enrich the contacts in contacts.csv using the enrichment script." The agent reads the script, runs it, and reports the results. Next time, you can say "enrich this new list" and the agent knows the pattern.

---

## Security: API Keys Are Not Optional

Three rules. Follow all three.

**1. API keys go in `.env` files, never in code.**

```python
# Wrong — key is in the code, visible to anyone who reads it
headers = {"Authorization": "Bearer sk-abc123xyz"}

# Right — key loaded from environment
headers = {"Authorization": f"Bearer {os.getenv('API_KEY')}"}
```

**2. `.env` is in `.gitignore`.**

Every project in this repo already has `.env` in `.gitignore`. Verify it. If you create a new project, add it before your first commit.

**3. Use the system keychain when possible.**

CLI tools like `gh`, `gcloud`, and `aws` store credentials in your system keychain — not in plaintext files. This is more secure than `.env` files. When a tool supports keychain auth, use it.

```bash
# These store credentials securely
gh auth login
gcloud auth login
aws configure
```

---

## Exercise: Map Your Tool Connections

Take your current GTM stack and categorize each tool:

| Tool | Connection Type | Status |
|------|----------------|--------|
| HubSpot | MCP (OAuth) | MCP server available |
| GitHub | CLI (`gh`) | Install and auth |
| Apollo | API (Python) | Need API key |
| Google BigQuery | CLI (`gcloud`) | Install and auth |
| Exa | API (Python) | Need API key |

Fill this out for your stack. For each tool, note whether you need to: install an MCP server, install a CLI tool, or write an API wrapper. That's your integration roadmap.

---

## Key Takeaways

- Three patterns: OAuth (MCP servers), CLI (terminal tools), API (Python scripts). Every integration is one of these.
- MCP is the future — use it when a server exists. CLI is the workhorse for cloud services. API wrappers are your fallback for everything else.
- API keys live in `.env`, never in code. CLI credentials go in the keychain. No exceptions.
- The decision framework is simple: MCP server exists? Use it. CLI exists? Script it. Neither? Write a Python wrapper.

---

**Next:** [Chapter 05 - Automation Agents](./05-automation-agents.md) — How to make your GTM workflows run on autopilot with cron, n8n, and Trigger.dev.
