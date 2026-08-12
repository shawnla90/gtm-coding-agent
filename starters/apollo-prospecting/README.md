# Apollo Prospecting Starter

Turn one contact per company into a full buying committee -- scored, ranked, and pushed to a color-coded Google Sheet. All searching and scoring uses free Apollo API calls. You only spend credits when you reveal the winners.

## Quick Start

```bash
# 1. Clone and configure
git clone https://github.com/shawnla90/gtm-coding-agent.git
cd gtm-coding-agent/starters/apollo-prospecting
cp .env.example .env
# Edit .env and paste your Apollo API key
# Get yours at: https://app.apollo.io/settings/integrations/api

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up Google Sheets (one time)
python3 setup_oauth.py

# 4. Run the pipeline
bash run.sh                    # uses sample_contacts.csv (25 companies)
bash run.sh my_list.csv        # use your own source list
bash run.sh --no-reveal        # free search data only (no credits spent)
```

## The Pipeline

```
init_db.py    CSV -> SQLite (source_contacts table)
     |
expand.py     Apollo API: companies -> decision makers (FREE)
     |
score.py      Title relevance x reachability tier scoring
     |
reveal.py     Apollo API: reveal emails, phones, LinkedIn (PAID)
     |
build_sheet.py  SQLite -> 4-tab Google Sheet via sheet_engine
```

### init_db.py

Loads your source CSV into a local SQLite database. Idempotent -- re-running never double-loads. Your CSV needs these columns: `company, domain, name, title, persona, source`.

### expand.py

The expansion play. For each company domain, resolves the org via Apollo and searches for senior decision makers across sales, marketing, and product. Writes raw candidates to the database.

```bash
python3 expand.py --all                    # all domains in the db
python3 expand.py --domains mixpanel.com   # one company (demo mode)
```

### score.py

Scores every candidate with a composite: title relevance (additive keyword weights) multiplied by a reachability tier multiplier.

### reveal.py

Reveals actual emails, phone numbers, LinkedIn URLs, full names, and cities for ranked contacts via Apollo's `people/match` endpoint. Costs 1 export credit per person.

```bash
python3 reveal.py              # reveal all ranked contacts
python3 reveal.py --top 20     # reveal only the top 20 by score
python3 reveal.py --dry-run    # preview the cost without spending credits
```

Emails and phones are obfuscated in the spreadsheet output for privacy.

| Keyword | Points |
|---------|--------|
| RevOps / Revenue Operations | 100 |
| Revenue | 90 |
| Growth | 80 |
| Go-to-Market / GTM | 75 |
| Sales | 60 |
| Marketing | 55 |
| Product | 50 |
| CxO seniority | +30 |
| VP | +25 |
| Head of | +20 |
| Director | +15 |

| Reachability Tier | Multiplier |
|-------------------|-----------|
| T1: verified email + phone | 1.0x |
| T2: verified email only | 0.85x |
| T3: catch-all / guessed | 0.6x |
| T4: unavailable | 0.3x |

Picks top 5 per company with persona diversity (at least one from sales, marketing, and product when available).

### build_sheet.py

Renders the scored data as a multi-tab Google Sheet:

- **Dashboard** -- KPIs: source contacts, expansion count, tier distribution, persona mix, cost guide
- **Source List** -- your original contacts
- **Buying Committee** -- ranked + color-coded by tier, persona, and cost (FREE / $ / $$). Columns: rank, composite_score, reachability, cost, full_name, title, persona, company, domain, email_status, has_phone, linkedin_url, city, title_score
- **Scoring Model** -- the weights table for reference

Rebuilds in place by sheet ID so the link never changes on a re-run.

## Waterfall: Grow the List with Intent Gates

`waterfall.py` takes the company list you already have and grows it with lookalikes until it hits a target size -- draining search gates from deepest intent to shallowest, so every new company arrives tagged with **why** it made the list.

Apollo does not expose its buying-intent (Bombora topic) data through the API. The gate tag is the intent layer you build yourself, from behavior the API does expose:

| Gate | Signal | Why it means intent |
|------|--------|---------------------|
| T0 | External evidence (e.g. a Reddit buyer-signal export) | Someone at the company is asking about the problem in public |
| T1 | Hiring for the pain | Job postings for the roles you configure = budget + urgency |
| T2 | Fresh funding | Latest round inside your amount window = money to spend |
| T3 | Tech-stack twins | Runs the tools your best accounts run |
| T4 | Firmographic lookalike | Right size, industry, geo -- fits the profile, no behavior signal yet |

```bash
# 1. Configure your ICP (the config is gitignored -- your ICP stays local)
cp waterfall_config.example.json waterfall_config.json
# Edit: industries, employee ranges, hiring titles, funding window, tech UIDs

# 2. Size the market per gate before committing to anything
python3 waterfall.py --target 150 --dry-run

# 3. Fill the list, deepest intent first
python3 waterfall.py --target 150
python3 waterfall.py --seed my_list.csv --double         # target = 2x your list
python3 waterfall.py --clearbox evidence.csv --target 150  # seed T0 from evidence

# 4. Feed it straight into the pipeline
python3 init_db.py waterfall_output.csv
```

Details that matter in practice:

- **Per-gate caps.** A deep gate with thousands of matches would fill the whole list; an optional `"cap"` per gate in the config keeps the mix (e.g. 60/40/30, remainder from T4).
- **Staffing-agency filter.** Job-posting gates attract staffing and recruiting firms posting roles for their clients. They're dropped by NAICS prefix (`5613`, `541612` by default).
- **Bonus columns.** Search responses carry Apollo's per-company `intent_strength`, six-month headcount growth, and printed revenue -- they land in the output when present.
- **Cost.** Every gate query is a company search; reveals are the step that draws credits, later in the pipeline, and the scripts print what they're about to spend first.

Output: `waterfall_output.csv` (gitignored) with `init_db.py`-compatible columns plus `gate`, `gate_evidence`, `apollo_intent`, `headcount_growth_6mo`, `revenue`.

## What Costs Credits (and What Does Not)

| Endpoint | Cost | What you get |
|----------|------|-------------|
| `mixed_people/api_search` | **Free** | First names, obfuscated last names, titles, email/phone availability FLAGS |
| `organizations/enrich` | **Free** | Company info by domain |
| Email reveal | 1 export credit | Actual email address |
| Mobile reveal | 1 mobile credit | Direct-dial phone number |
| Full enrichment | 1 credit | Full last name, LinkedIn URL, city, state |

The output sheet marks every row: **FREE** (search data only), **$** (one reveal available), or **$$** (both email + phone available). Score first using the free availability flags, then only reveal the winners. 25 companies with 5 contacts each = 125 scored contacts at zero credit cost. Reveal only the top 20 by composite score = 20 credits instead of 125.

## Protect Your API Key

Your key lives in `.env` (gitignored, never committed). The `.env.example` template shows what to set. The test: `git log --all -p | grep APOLLO` should return nothing.

```
.env          <- your real key (gitignored)
.env.example  <- template with placeholders (committed)
.gitignore    <- blocks .env and .env.* from being tracked
```

### Level Up: Pull the Key from a Local Vault

Pasting keys into `.env` files works for one project. Past a few projects, the better pattern is a **local secrets vault**: one SQLite database in your home directory, outside every git repo, holding all your keys. When a project needs one, your agent queries the vault and pipes the value straight into the gitignored `.env` — the key never appears on screen and never touches version control at either end:

```bash
printf 'APOLLO_API_KEY=%s\n' \
  "$(sqlite3 ~/.gtm-vault/vault.db "SELECT value FROM secrets WHERE key='APOLLO_API_KEY';")" \
  > .env
```

Rotate a key once in the vault and every project re-pulls the fresh copy. The full build-your-own walkthrough (schema, permissions, caveats) is in [Chapter 04](../../chapters/04-oauth-cli-apis.md#level-up-the-local-secrets-vault).

## Your Own Source List

Create a CSV with these columns and pass it to the pipeline:

```csv
company,domain,name,title,persona,source
Acme Corp,acme.com,Jordan,VP of Sales,sales,linkedin
```

Then: `bash run.sh my_list.csv`

## Links

- [Apollo Anywhere](https://www.apollo.io/anywhere?utm_campaign=parent_apolloanywhere&utm_medium=referral&utm_source=shawn_tenam&utm_content=influencer) -- API, CLI, and MCP
- [Apollo API Reference](https://docs.apollo.io/reference/apollo-api)
- [GTM Coding Agent](https://github.com/shawnla90/gtm-coding-agent) -- the full kit

---

Part of the [GTM Coding Agent](https://github.com/shawnla90/gtm-coding-agent) kit. For a managed version with ongoing campaign operations, see [clearbox.to](https://clearbox.to).
