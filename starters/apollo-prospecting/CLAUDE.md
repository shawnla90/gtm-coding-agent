# Apollo Prospecting Starter

You are inside the Apollo prospecting starter. This pipeline turns a source list of companies into scored, ranked buying committees via the Apollo API and outputs them to a color-coded Google Sheet.

## On "help me set up"

Walk through these checks one at a time:

1. **API key**: Check for `.env` in this directory. If missing, tell them to `cp .env.example .env` and paste their Apollo API key (get it at https://app.apollo.io/settings/integrations/api). Stress: `.env` is gitignored and must never be committed.

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

## Single-company demo

For a live demo, run one company at a time:
```bash
python3 expand.py --domains mixpanel.com
python3 score.py
python3 reveal.py --top 5
python3 build_sheet.py
```

## Data safety

- `.env` is gitignored. If `git log --all -p | grep APOLLO` returns anything, stop and fix.
- `data/apollo.db` is gitignored. Never commit the database.
- `sample_contacts.csv` has first names only (no last names, emails, or phone numbers).
- Expansion results in the database show first names, obfuscated last names (e.g., "Mo***m"), and availability FLAGS — not actual emails, phone numbers, or LinkedIn URLs. Full contact data requires paid enrichment/reveal.
