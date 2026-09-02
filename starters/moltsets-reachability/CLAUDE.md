# Moltsets Reachability Starter

You are inside the Moltsets reachability starter. It takes a contact list, asks Apollo whether each person is still at the company, asks Moltsets to grade the email address A through F, and renders a color-coded Google Sheet where every row keeps a channel. A bad grade is a routing decision, not a dead contact.

## On "help me set up"

Walk through these checks one at a time:

1. **Moltsets key**: Check for `.env` in this directory. If missing, `cp .env.example .env` and paste the key from app.moltsets.com. `.env` is gitignored and must never be committed. If the user keeps keys in a local secrets vault (a SQLite db outside any repo), do not ask them to paste: `export SECRETS_DB=~/.gtm-vault/vault.db` and the scripts read `secrets(key, value)` from there. See "The secrets-vault explainer" below.

2. **Apollo key (optional)**: Same file or vault, `APOLLO_API_KEY`. It powers `--employment apollo|both`, a second employment source for comparison. The pipeline runs without it.

3. **Google Sheets auth**: Check for `~/.config/gspread/token.json`. If missing, `python3 setup_oauth.py` and walk them through the consent flow. They need a Google Cloud project with the Sheets and Drive APIs enabled.

4. **Dependencies**: `pip install -r requirements.txt`

5. **Contacts**: `sample_contacts.csv` (25 fictional rows on `.example` domains) or their own CSV. The loader accepts the short schema (`first_name,last_name,title,company,domain,email,linkedin_url`) or a raw Apollo people export with its original headers.

6. **Budget first**: `python3 budget.py`. Three free calls. Shows the two record pools, the phone-token balance, and the endpoint catalogue. Do this before any batch.

7. **Run it**: `bash run.sh` (first pass only) or `bash run.sh my_list.csv --full` (employment check + second pass).

## The pipeline

```
init_db.py -> grade.py -> score.py -> build_sheet.py
```

- `init_db.py` loads the CSV into SQLite at `data/reachability.db`. Idempotent. `--country`, `--limit`, `--exclude <file>` filter the load.
- `grade.py` is the waterfall. Per contact: `reverse_linkedin_lookup` on the LinkedIn URL (still there, or moved? plus the graded address when present; `--employment apollo|both` swaps in or adds Apollo `people/match`) -> Moltsets `reverse_email_lookup` when still ungraded -> on 404 or F, optional `search_people` by name + company DOMAIN (accept only same-domain A/B) -> LinkedIn-only rows go to `linkedin_to_best_email` -> optional capped `linkedin_to_mobile_phone` for dead-email rows. Every call is logged; every row is committed as it finishes.
- `score.py` computes title relevance x grade multiplier and ranks the top 3 sendable per company with persona diversity.
- `build_sheet.py` renders 9 tabs via the vendored `lib/sheet_engine.py`. Emails obfuscated by default.
- `budget.py` explains the four units that meter Moltsets, using free calls only.

## What Moltsets grades mean (from developer.moltsets.com)

| Grade | Meaning | Action |
|---|---|---|
| A | valid: known reply, open, or click | send |
| B | known send, no bounce | send, smaller batches |
| C | catch-all domain | your call: small monitored segment |
| D | hard invalid: bounce, complaint, or spam trap | never send |
| F | no data | re-verify, or treat like C |
| 404 | not in the graph | a coverage gap, not a verdict; costs nothing |

The docs' rule: suppress D at the list level; segment C and F away from A/B rather than dropping them. Note the common mix-up: F is "no data", D is the hard invalid. Do not swap them.

## What the route column means

| Route | Who lands here | What to do |
|---|---|---|
| `email` | A/B on the company's domain | sequence them |
| `email_low_volume` | C catch-all | small segment, watch bounces |
| `linkedin` | not found after the second pass, or no email | connection note first |
| `linkedin_then_phone` | grade D | never email; LinkedIn, then a mobile if tokens allow |
| `resource` | Apollo says they moved | find them at the new company; the old email is stale |
| `second_pass` | 404 or F and the second pass has not run yet | run `grade.py --second-pass` |
| `hold` | free-mail address, or A/B on a different domain | a human looks |

## Cost model (four units, none interchangeable)

- **Calls**: unlimited in count on paid plans, rate-limited per rolling 5h window.
- **Records**: the real meter. Two 5h pools on the $97 plan: enrich 15,000/5h (75,000/week) and search 7,500/5h (37,500/week). A 404 consumes nothing. A client crash mid-batch does, with no refund, which is why every row commits as it finishes.
- **Internal tokens**: `token_costs` is all 1s and the balance is -1 (unlimited) on paid plans. Ignore.
- **Phone tokens**: 50 per month on the $97 plan, one per mobile HIT, misses free. `grade.py --phones N` caps hits and never spends below `MOLTSETS_PHONE_FLOOR` (default 20).

## Gotchas that produce walls of false misses

- `company` in `search_people` expects a **domain**, not a company name. `"Bobyard"` 404s; `"bobyard.com"` returns the profile.
- A personal Gmail is an **output**, never an input. Free-mail addresses 404 on every lookup endpoint.
- A name-only `search_people` match is a lead, not an identity. Corroborate the domain you already hold; a different domain is `review_cross_domain`, not a hit.
- `location` is not a `search_people` parameter. It is silently ignored and returns worldwide results.
- Grades ride on three different field names depending on the endpoint. `lib/moltsets_client.grade_of()` normalizes them.
- Fair-use counters ride only on data responses. Free status calls omit them.

## Single-company demo

```bash
python3 init_db.py sample_contacts.csv
python3 grade.py --limit 5 --dry-run     # shows what would run, spends nothing
python3 grade.py --limit 5 --second-pass
python3 score.py
python3 build_sheet.py
```

## The secrets-vault explainer (part of the demo)

The key step is a teaching moment. Land this: **"The key isn't in this repo, and it isn't in git anywhere. It lives in one local SQLite vault, outside every repository, and the agent checks it out on demand."**

1. Prove absence: `git log --all -p | grep -i moltsets_api` returns nothing.
2. List key names only, never values: `sqlite3 <vault> "SELECT key, category FROM secrets;"`
3. Point the scripts at the vault without copying anything: `export SECRETS_DB=~/.gtm-vault/vault.db`
4. Verify without revealing: `python3 budget.py` succeeds on three free calls.

Hygiene: vault `chmod 600`, directory `chmod 700`, full-disk encryption as the backstop. Full walkthrough: `chapters/04-oauth-cli-apis.md`, "Level Up: The Local Secrets Vault".

## Data safety

- `.env`, `data/*.db`, `data/sheet_url.txt`, `data/grade_summary.json`, and any CSV in `data/` are gitignored.
- `sample_contacts.csv` is fictional: first names only, `.example` domains.
- The sheet obfuscates emails and phones unless `--full-emails`. Never share a `--full-emails` sheet publicly.
- Never publish a real sheet URL in content. Screenshots only.
- Treat the user's list as confidential. It never appears in any output that might be shared.
