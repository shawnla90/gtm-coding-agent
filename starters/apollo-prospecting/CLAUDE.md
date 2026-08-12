# Apollo Prospecting Starter

You are inside the Apollo prospecting starter. This pipeline turns a source list of companies into scored, ranked buying committees via the Apollo API and outputs them to a color-coded Google Sheet.

## On "help me set up"

Walk through these checks one at a time:

1. **API key**: Check for `.env` in this directory. If missing, tell them to `cp .env.example .env` and paste their Apollo API key (get it at https://app.apollo.io/settings/integrations/api). Stress: `.env` is gitignored and must never be committed. If the user keeps keys in a local secrets vault (a SQLite db outside any repo), pull it instead of asking them to paste: query the vault and pipe the value into `.env` without ever printing it — see "The secrets-vault explainer" below.

2. **Google Sheets auth**: Check for `~/.config/gspread/token.json`. If missing, run `python3 setup_oauth.py` and walk them through the OAuth consent flow. They need a Google Cloud project with Sheets + Drive APIs enabled.

3. **Dependencies**: `pip install -r requirements.txt`

4. **Source list**: They can use `sample_contacts.csv` (25 companies) or provide their own CSV with columns: `company, domain, name, title, persona, source`.

5. **Run it**: `bash run.sh` or `bash run.sh my_list.csv`

## The pipeline

```
init_db.py -> expand.py -> score.py -> reveal.py -> build_sheet.py
```

- `init_db.py` loads the CSV into SQLite at `data/apollo.db`
- `expand.py` calls Apollo API (FREE -- 0 credits) to find decision makers
- `score.py` applies title_score x reachability_mult, ranks top 5 per company
- `reveal.py` reveals actual emails, phones, LinkedIn, full names (PAID -- 1 credit per person). Supports `--top N`, `--dry-run`. Skip with `bash run.sh --no-reveal`.
- `build_sheet.py` renders a 4-tab Google Sheet via the vendored sheet_engine. Emails and phones are obfuscated.

## API cost breakdown

**FREE (0 credits):**
- `mixed_people/api_search` -- names, titles, email/phone availability flags (not actual contact info)
- `organizations/enrich` -- company info by domain

**PAID (1 export credit per reveal):**
- Email reveal -- getting the actual email address
- Mobile reveal -- from the separate mobile credit pool

The key teaching point: score first using free availability flags, then only reveal the top-ranked contacts. This is the "score first, reveal the winners" pattern.

## Waterfall (lookalike expansion with intent gates)

On "waterfall", "grow the list", "lookalike expansion", or "intent gates": `waterfall.py` grows the source list with lookalike companies until it hits `--target`, draining gates from deepest intent to shallowest. Every company comes out tagged with the gate it passed -- that tag is the user's self-built intent layer (Apollo does not expose buying intent through the API).

```
T0 external evidence -> T1 hiring for the pain -> T2 fresh funding -> T3 tech-stack twins -> T4 firmographic
```

Setup: `cp waterfall_config.example.json waterfall_config.json` and tune it to THEIR ICP (industries, employee ranges, hiring titles, funding window, technology UIDs). The real config and `waterfall_output.csv` are gitignored -- never commit either. Verify technology UIDs live before writing them into a config (search with one UID, check the count is nonzero).

Run order: `--dry-run` first to show per-gate market size, then the real run, then `python3 init_db.py waterfall_output.csv` to feed the standard pipeline. Gate queries are company searches (`mixed_companies/search`); per-gate `"cap"` values keep one deep gate from filling the whole list; staffing/recruiting noise is dropped by NAICS prefix.

## Single-company demo

For a live demo, run one company at a time:
```bash
python3 expand.py --domains mixpanel.com
python3 score.py
python3 reveal.py --top 5
python3 build_sheet.py
```

## The secrets-vault explainer (part of the demo)

When demoing this starter, the API-key step IS a teaching moment — don't skip past it. The point to land:

**"The key isn't in this repo, and it isn't in git anywhere. It lives in one local SQLite vault, outside every repository, and the agent checks it out on demand."**

Demo flow:

1. Show the key is NOT in the repo: `.env` is gitignored, `git log --all -p | grep -i apollo` returns nothing.
2. Show where it DOES live: a SQLite db in the home directory (e.g. `~/.gtm-vault/vault.db`) that no git repo contains. List key **names only** — never SELECT values to the screen: `sqlite3 <vault> "SELECT key, category FROM secrets;"`
3. Pull it live, silently — query piped straight into `.env` so the value never appears on screen or in the conversation:
   ```bash
   printf 'APOLLO_API_KEY=%s\n' "$(sqlite3 <vault> "SELECT value FROM secrets WHERE key='APOLLO_API_KEY';")" > .env
   ```
4. Verify without revealing: load with dotenv, print only a boolean and length, then smoke-test with the FREE `organizations/enrich` endpoint (0 credits).

Talk track: "Git is for code I want to share and track. Secrets are the one thing I never want shared or tracked — so they live in the opposite place. One vault, outside version control; every project's `.env` is a disposable copy the agent regenerates on demand. Rotate once, every project picks it up."

Hygiene to mention (and check): vault file is `chmod 600`, its directory `chmod 700`; values are plaintext, so full-disk encryption is the backstop; backups of the home folder carry a copy. Full walkthrough: `chapters/04-oauth-cli-apis.md`, "Level Up: The Local Secrets Vault".

## Data safety

- `.env` is gitignored. If `git log --all -p | grep APOLLO` returns anything, stop and fix.
- `data/apollo.db` is gitignored. Never commit the database.
- `sample_contacts.csv` has first names only (no last names, emails, or phone numbers).
- Expansion results in the database show first names, obfuscated last names (e.g., "Mo***m"), and availability FLAGS — not actual emails, phone numbers, or LinkedIn URLs. Full contact data requires paid enrichment/reveal.
