# Builder's Guide to GTM with Apollo

Turn one contact per company into a full buying committee — scored, ranked, and pushed to a color-coded Google Sheet. All searching and scoring uses free Apollo API calls. You only spend credits when you choose to reveal the winners.

::: bookmark https://github.com/shawnla90/gtm-coding-agent/tree/main/starters/apollo-prospecting

---

## The Pipeline

```
init_db.py     CSV -> SQLite
     |
expand.py      Apollo API: domains -> decision makers (FREE)
     |
score.py       Title relevance x reachability scoring
     |
reveal.py      Apollo API: reveal emails, phones, LinkedIn (PAID)
     |
build_sheet.py SQLite -> 4-tab Google Sheet
```

**init_db.py** loads your source CSV into a local SQLite database. Idempotent — re-running never double-loads.

**expand.py** calls the Apollo API to find senior decision makers at each company. Returns first names, obfuscated last names, titles, and availability flags — all at zero credit cost.

**score.py** scores every candidate: title keyword weights (RevOps = 100, VP = 25, etc.) multiplied by a reachability tier (T1 = 1.0x, T4 = 0.3x). Picks the top 5 per company with persona diversity.

**reveal.py** takes the ranked contacts and reveals actual emails, phone numbers, LinkedIn URLs, full names, and cities via Apollo's `people/match` endpoint. Costs 1 export credit per person. Use `--dry-run` to preview the cost. Use `--top 20` to only reveal the top 20. Skip this step entirely with `bash run.sh --no-reveal`.

**build_sheet.py** renders a 4-tab Google Sheet: Dashboard, Source List, Buying Committee, and Scoring Model. Emails and phones are obfuscated in the output for privacy.

---

## What's Free, What Costs Credits

> 💸 The search is free. The reveal costs credits. Score first, reveal the winners.

| Endpoint | Cost | What You Get |
|----------|------|-------------|
| `mixed_people/api_search` | **FREE** | First names, obfuscated last names, titles, email/phone availability FLAGS |
| `organizations/enrich` | **FREE** | Company info by domain |
| Email reveal | 1 export credit | Actual email address |
| Mobile reveal | 1 mobile credit | Direct-dial phone number |
| Full enrichment | 1 credit | Full name, LinkedIn URL, city, state |

The output spreadsheet marks every row with a cost indicator:
- **FREE** — search data only, no credits spent
- **$** — one reveal available (email or phone)
- **$$** — both email and phone available to reveal

25 companies x ~5 contacts each = ~125 scored contacts at zero cost. Then reveal only the top 20 by composite score. That is 20 credits instead of 125.

---

## Setup (5 Minutes)

### 1. Clone the repo

```bash
git clone https://github.com/shawnla90/gtm-coding-agent.git
cd gtm-coding-agent/starters/apollo-prospecting
```

### 2. Get your Apollo API key

Go to [Apollo Settings > Integrations > API](https://app.apollo.io/settings/integrations/api) and copy your key.

### 3A. Create your .env file (quick start)

```bash
cp .env.example .env
# Edit .env and paste your Apollo API key
```

> ⚠️ Your key lives in `.env`, which is gitignored. It never touches version control. The test: `git log --all -p | grep APOLLO` should return nothing.

This is all the repo requires — the scripts read `APOLLO_API_KEY` from the environment or `.env` and nothing else. If you're setting up for the first time, do 3A and move on. Come back to 3B when you have keys in more than one project.

### 3B. Level up: pull the key from a local secrets vault (more secure)

The problem with pasting keys: every project gets its own copy, and when you rotate the key you have to remember every place it lives. The fix is one SQLite vault **outside every git repo**, holding all your keys. Each project's `.env` becomes a disposable copy your coding agent regenerates on demand.

One-time vault setup:

```bash
mkdir -p ~/.gtm-vault && chmod 700 ~/.gtm-vault
sqlite3 ~/.gtm-vault/vault.db \
  "CREATE TABLE IF NOT EXISTS secrets (key TEXT PRIMARY KEY, value TEXT, category TEXT);"
chmod 600 ~/.gtm-vault/vault.db
sqlite3 ~/.gtm-vault/vault.db \
  "INSERT OR REPLACE INTO secrets VALUES ('APOLLO_API_KEY', 'paste-your-key-here', 'apollo');"
```

Then in any project that needs the key, regenerate `.env` without the value ever appearing on screen:

```bash
printf 'APOLLO_API_KEY=%s\n' \
  "$(sqlite3 ~/.gtm-vault/vault.db \
     "SELECT value FROM secrets WHERE key='APOLLO_API_KEY';")" > .env
```

Verify without revealing — print only that it loaded and how long it is:

```bash
python3 -c "
from dotenv import load_dotenv; import os
load_dotenv()
k = os.getenv('APOLLO_API_KEY','')
print('key loaded:', bool(k), '| length:', len(k))"
```

Why this is the better pattern:

- **Git is for code you want shared and tracked. Secrets are the opposite** — so they live in the opposite place.
- **Rotate once, every project picks it up.** Update the vault row, regenerate each `.env` on demand.
- **Your agent can fetch keys silently.** Ask it to "pull the Apollo key from the vault" — the value pipes straight into `.env` and never appears in the conversation or on screen.
- **List key names, never values.** To see what's in the vault: `sqlite3 ~/.gtm-vault/vault.db "SELECT key, category FROM secrets;"`

Hygiene: the vault file is `chmod 600`, its directory `chmod 700`, and values are plaintext — so full-disk encryption (FileVault) is the backstop, and remember home-folder backups carry a copy. Full walkthrough: Chapter 04, "Level Up: The Local Secrets Vault."

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Set up Google Sheets (one time)

```bash
python3 setup_oauth.py
```

This walks you through the OAuth consent flow. You need a Google Cloud project with the Sheets and Drive APIs enabled. The token saves to `~/.config/gspread/token.json`.

---

## Running the Pipeline

### Full run (all companies + reveal)

```bash
bash run.sh                    # uses sample_contacts.csv (25 companies)
bash run.sh my_list.csv        # use your own source list
bash run.sh --no-reveal        # free search data only (no credits spent)
```

### Single-company demo

```bash
python3 init_db.py
python3 expand.py --domains mixpanel.com
python3 score.py
python3 reveal.py --top 5      # reveal only the top 5 (or skip for free data only)
python3 build_sheet.py
```

---

## Reading the Output

### Dashboard Tab

KPIs at a glance: how many source contacts, how many expanded, the tier distribution (T1/T2/T3/T4), and the persona mix (sales, marketing, product). Includes a cost guide explaining the FREE / $ / $$ indicators.

### Source List Tab

Your original CSV — the input to the pipeline. One contact per company with the domain, title, persona, and where they came from.

### Buying Committee Tab

The ranked output. Columns left to right:

| Column | What It Means |
|--------|--------------|
| rank | Position within their company (1 = top pick) |
| composite_score | Title relevance x reachability multiplier |
| reachability | T1 (email+phone), T2 (email), T3 (catch-all), T4 (unavailable) |
| cost | FREE / $ / $$ — what it costs to reveal this person's contact info |
| full_name | First + last name (revealed via enrichment; obfuscated before reveal) |
| title | Their role at the company |
| persona | sales, marketing, or product |
| company | Company name |
| domain | Company domain |
| email | Obfuscated email (e.g., c\*\*\*r@company.com) — populated after reveal |
| phone | Obfuscated phone — populated after reveal (requires mobile credits) |
| linkedin_url | LinkedIn profile URL — populated after reveal |
| city | Location — populated after reveal |
| title_score | Raw keyword score before the reachability multiplier |

> 🎯 Green rows (T1) = verified email + phone. These are your spear list. Blue rows (T2) = email only, solid for sequences. Yellow (T3) = catch-all, test before sending. Grey (T4) = no verified channel yet, go LinkedIn first.

### Scoring Model Tab

The full weights table so you can see exactly how every score was computed. Customize these weights in `score.py` to match your ICP.

---

## The Scoring Model

### Title Keywords (Additive)

| Keyword | Points |
|---------|--------|
| RevOps / Revenue Operations | 100 |
| Revenue | 90 |
| Growth | 80 |
| Go-to-Market / GTM | 75 |
| Sales | 60 |
| Marketing | 55 |
| Product | 50 |
| Business Development | 45 |
| CxO (seniority bonus) | +30 |
| VP / Vice President | +25 |
| Head of | +20 |
| Director | +15 |
| Manager | +5 |

### Reachability Multiplier

| Tier | Condition | Multiplier |
|------|-----------|-----------|
| T1 | Verified email + phone | 1.0x |
| T2 | Verified email only | 0.85x |
| T3 | Catch-all / guessed | 0.6x |
| T4 | Unavailable | 0.3x |

### Worked Example

**VP of Revenue Operations** at a company with verified email + phone:
- RevOps: 100 + Revenue: 90 + VP: 25 = **215 title score**
- T1 multiplier: 215 x 1.0 = **215.0 composite score**

---

## Protecting Your API Key

```
.env          <- your real key (gitignored, never committed)
.env.example  <- template with placeholders (committed, safe)
.gitignore    <- blocks .env and data/*.db from version control
```

The verification test:
```bash
git log --all -p | grep APOLLO
# Should return nothing. If it does, rotate your key immediately.
```

Running the vault pattern from Step 3B? Then `.env` is just a disposable copy — the real key lives in `~/.gtm-vault/vault.db`, outside every repo, and this test should still return nothing.

---

## Using Your Own Source List

Create a CSV with these columns:

```csv
company,domain,name,title,persona,source
Acme Corp,acme.com,Jordan,VP of Sales,sales,linkedin
```

Then run:
```bash
bash run.sh my_list.csv
```

The pipeline handles deduplication. If you re-run with the same domains, it skips companies already expanded.

---

## Next Steps

- **Reveal the winners**: Take your top-scored T1 contacts and use Apollo's reveal to get actual emails and phone numbers
- **Customize scoring**: Edit the keyword weights in `score.py` to match your ICP
- **Scale up**: The sample has 25 companies. Load your full target account list — same pipeline, same cost structure
- **Integrate with sequences**: Export the revealed contacts into Apollo sequences or your outreach tool of choice

---

> 🚀 Part of the [GTM Coding Agent](https://github.com/shawnla90/gtm-coding-agent) kit. For a managed version with ongoing campaign operations, see [clearbox.to](https://clearbox.to).
