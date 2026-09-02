# Moltsets Reachability Starter

Grade every email on a list A through F, route the bad ones to another channel instead of dropping them, and read the result in a color-coded Google Sheet. Apollo confirms the person is still at the company. Moltsets grades the address. The sheet picks the channel.

Relevance, timing, and reachability are the three things a list has to get right. Title scoring covers relevance. The Apollo employment check covers timing. The Moltsets grade covers reachability, and the route column is what you do when the grade says no.

## Quick Start

```bash
git clone https://github.com/shawnla90/gtm-coding-agent.git
cd gtm-coding-agent/starters/moltsets-reachability
cp .env.example .env            # paste MOLTSETS_API_KEY (and APOLLO_API_KEY, optional)
pip install -r requirements.txt
python3 setup_oauth.py          # one time: Google Sheets consent

python3 budget.py               # three free calls: pools, phone tokens, endpoint count
bash run.sh                     # sample_contacts.csv, first pass only
bash run.sh my_list.csv --full  # your list: Apollo employment check + second pass
```

Or skip the paste and read the key from a local vault: `export SECRETS_DB=~/.gtm-vault/vault.db`.

## The Pipeline

```
init_db.py     CSV -> SQLite (short schema or a raw Apollo export)
     |
grade.py       Apollo people/match (still there?) -> Moltsets reverse_email_lookup (A-F)
               -> on 404/F: search_people by name + DOMAIN, accept same-domain A/B only
               -> LinkedIn-only rows: linkedin_to_best_email
               -> optional capped linkedin_to_mobile_phone for dead-email rows
     |
score.py       title relevance x grade multiplier, top 3 sendable per company
     |
build_sheet.py 9-tab color-coded Google Sheet with a dashboard and a usage ledger
```

### Grades and what they mean

From [developer.moltsets.com](https://developer.moltsets.com/moltsets-data/email-risk-scores):

| Grade | Meaning | Sheet color | Route |
|---|---|---|---|
| A | valid: known reply, open, or click | green | `email` |
| B | known send, no bounce | light green | `email` |
| C | catch-all domain, mailbox unconfirmed | amber | `email_low_volume` |
| D | hard invalid: bounce, complaint, or spam trap | red | `linkedin_then_phone` |
| F | no data | orange | second pass, then `linkedin` |
| 404 | not in the graph | grey | second pass, then `linkedin` |

D is never emailed. D is also never dropped: the mailbox is dead, the person is not. F and a 404 mean the graph has not seen the address, which is a coverage gap, not a verdict, so the second pass looks again by name and company domain before the row goes to LinkedIn.

### Scoring

Same composite as the Apollo starter: additive title keyword weights times a reachability multiplier. The multiplier now comes from the grade.

| Grade | Multiplier |
|---|---|
| A | 1.0x |
| B | 0.85x |
| C | 0.6x |
| F / not found | 0.3x |
| D | 0.15x |

Title weights: RevOps 100, Revenue 90, Growth 80, GTM 75, Sales 60, Marketing 55, Product 50, BizDev 45, Founder 40, Chief 30, VP 25, Head of 20, Director 15, Manager 5. Example: Head of Growth on a grade A address is (80 + 20) x 1.0 = 100. The same person on a grade D address scores 15 and routes to LinkedIn.

### The sheet

- **Dashboard**: graded share, send-ready share, grade distribution, route mix, and the receipts from this run (hit rate on the first pass, what the second pass recovered, Apollo still/moved counts, tokens spent).
- **Send Ready**: A/B on the company's domain, ranked.
- **Send Low Volume**: catch-all.
- **Route - LinkedIn**: D grades plus everyone the graph never found. The rows other tools throw away.
- **Review - Hold**: free-mail addresses, A/B on a different domain, job changes.
- **Suppressed**: the D rows, for the suppression list.
- **All Contacts**, **Grading Model** (the weights and meanings), **Moltsets Usage** (your own call ledger by endpoint).

Rebuilds in place by sheet id so the link never changes. Emails and phones are obfuscated unless `--full-emails`.

## What It Costs

Moltsets meters four things and none of them is a per-lookup credit:

| Unit | On the $97 plan | Notes |
|---|---|---|
| Calls | unlimited count, rate-limited per 5h window | one HTTP POST each |
| Records | enrich 15,000 per 5h (75,000 per week), search 7,500 per 5h (37,500 per week) | the real meter; a 404 consumes nothing |
| Internal tokens | -1 (unlimited) | ignore on paid plans |
| Phone tokens | 50 per month | one per mobile HIT, misses free |

`grade.py` reads the fair-use counters off every response, stops the batch at a floor, and never spends phone tokens below `MOLTSETS_PHONE_FLOOR`. `budget.py` shows all of it with free calls. Your own ledger lives in `data/reachability.db` (`moltsets_api_log`); the API keeps no history for you.

## Apollo + Moltsets, not Apollo or Moltsets

Apollo's identity graph follows a person across jobs. Moltsets' graph is keyed on the business address and grades whether it delivers. Neither answers the other's question. `--apollo` runs `people/match` on the LinkedIn URL first; if the current company disagrees with the one on your list, the row is a job change, the stale email is skipped, and the route says `resource`. On a 40-person sample the two sources agreed on still-at-company 32 times out of 40, and Apollo alone caught 5 real moves.

## Gotchas (each one produces a wall of false misses)

- `search_people` `company` is a **domain**, not a name.
- Free-mail addresses 404 on every lookup. A personal Gmail is an output, never an input.
- A name-only match is a lead, not an identity. Accept only a candidate on the domain you already hold.
- `location` is not a parameter. It is silently ignored.
- Grades arrive on three different field names; the client normalizes them.

## Your Own List

Short schema:

```csv
first_name,last_name,title,company,domain,email,linkedin_url
Jordan,Lee,Head of Growth,Acme,acme.com,jordan@acme.com,https://www.linkedin.com/in/jordanlee
```

Or drop in a raw Apollo people export; the loader reads its headers. Then `bash run.sh my_list.csv --full`.

## Links

- [Moltsets](https://moltsets.com) and the [API docs](https://developer.moltsets.com)
- [Email risk scores](https://developer.moltsets.com/moltsets-data/email-risk-scores)
- [Apollo starter](../apollo-prospecting/) for the title weights this reuses
- [GTM Coding Agent](https://github.com/shawnla90/gtm-coding-agent)

---

Part of the [GTM Coding Agent](https://github.com/shawnla90/gtm-coding-agent) kit. For a managed version with ongoing campaign operations, see [clearbox.to](https://clearbox.to).
