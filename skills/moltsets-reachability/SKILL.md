---
name: moltsets-reachability
version: 1.0.0
description: Grade every email on a contact list A through F with the Moltsets API, confirm the person is still at the company with Apollo, and route the rows a bad grade would normally kill (D never emails but goes to LinkedIn then phone; F and not-found get a second pass by name and company domain before they go to LinkedIn) into a color-coded Google Sheet with a dashboard and your own usage ledger. Wraps the moltsets-reachability starter: init_db.py loads the CSV, grade.py runs the waterfall with per-row commits and fair-use floor guards, score.py applies title relevance x grade multiplier, build_sheet.py renders nine tabs, budget.py explains the four metered units with free calls. Use when the user types "/moltsets-reachability" or says "grade this list", "moltsets", "reachability sheet", "route by grade", "which of these emails can I send to", "check if they still work there".
---

# moltsets-reachability

A bad email grade is a routing decision, not a dead contact.

Relevance, timing, reachability. Title scoring covers relevance. The Apollo employment check covers timing. The Moltsets grade covers reachability, and the route column is what you do when the grade says no. Wraps [`starters/moltsets-reachability/`](../../starters/moltsets-reachability/): the scripts call the APIs and build the sheet; the agent reads the dashboard back to the user and decides what to send. Read [`FACTCHECK.md`](FACTCHECK.md) before writing a single sentence about what a grade means or what a call costs.

## Inputs

- A contact CSV: the short schema (`first_name,last_name,title,company,domain,email,linkedin_url`) or a raw Apollo people export with its original headers
- `MOLTSETS_API_KEY` (env, `.env`, or `SECRETS_DB` vault). `APOLLO_API_KEY` optional, powers `--apollo`
- `~/.config/gspread/token.json` from `setup_oauth.py`
- Optional: `--exclude <file>` of emails or LinkedIn URLs that must never be graded (people already in your pipeline)

## How to run

```bash
cd starters/moltsets-reachability
python3 budget.py                                    # free: pools, phone tokens, endpoint count. Always first.
python3 init_db.py my_list.csv --exclude pipeline.txt
python3 grade.py --limit 20 --dry-run                # shows what would run, spends nothing
python3 grade.py --apollo --second-pass              # the waterfall
python3 score.py
python3 build_sheet.py                               # prints the sheet URL; emails obfuscated
```

`bash run.sh my_list.csv --full` does the same in one line. Add `--phones 10` only when the user has said how many mobiles they want to buy.

## The waterfall (binding order)

1. **Apollo `people/match` on the LinkedIn URL** (`--apollo`). If the current company disagrees with the listed one: `job_changed`, route `resource`, and the stale email is not graded. Timing before reachability.
2. **`reverse_email_lookup`** on the business email. Grade A-F. A 404 means the address is not in the graph. It costs nothing and it is not a verdict.
3. **Second pass** (`--second-pass`) on 404 or F: `search_people {query: "First Last", company: "<domain>"}`. Accept only a same-domain grade A/B candidate whose name matches. A different domain is a different person until proven otherwise.
4. **LinkedIn-only rows**: `linkedin_to_best_email`.
5. **Phones** (`--phones N`): only for rows whose email is dead (D) or unfound, one phone token per hit, never below the floor.

## Grade to route (what the sheet says)

| Grade | Tier | Route | Sheet tab |
|---|---|---|---|
| A / B, same domain | `T1_send` | `email` | Send Ready |
| A / B, second pass | `T1_send_corrected` | `email` | Send Ready |
| C | `T2_catchall` | `email_low_volume` | Send Low Volume |
| D | `SUPPRESS` | `linkedin_then_phone` | Suppressed and Route - LinkedIn |
| F or 404, after second pass | `HOLD_not_found` | `linkedin` | Route - LinkedIn |
| A / B on another domain, free-mail | `HOLD_review` | `hold` | Review - Hold |
| Apollo says moved | `HOLD_job_change` | `resource` | Review - Hold |

D rows appear in two tabs on purpose: the suppression list for the sequencer, and the LinkedIn queue for the human.

## Reading the dashboard back

Report in this order, every time, with the numbers from the Dashboard tab:

1. Contacts loaded, graded share, send-ready share.
2. First-pass hit rate and how many the second pass recovered. Coverage gaps are receipts, not embarrassments.
3. Grade distribution A through F.
4. Route mix: how many rows kept a channel that a suppress-only tool would have deleted.
5. Apollo still / moved / unknown.
6. What it cost: records used against the two pools, phone tokens spent (usually zero).

## Do

- Run `budget.py` before any batch and quote the pool numbers to the user.
- Keep `--phones` at zero unless the user names a number.
- Pass `company` as a domain. Always.
- Leave emails obfuscated in any sheet that might be shared. `--full-emails` is for the user's private copy only.
- Say "not in the graph" for a 404. Never say "invalid".

## Don't

- Don't call F "hard invalid". F is no data. D is the hard invalid. Swapping them suppresses reachable people and emails spam traps.
- Don't drop D rows. Route them.
- Don't accept a cross-domain second-pass candidate as the person you were looking for.
- Don't put a real sheet URL, a real address, or a phone number in content. Screenshots only.
- Don't send anything. This skill grades and routes. Sending is a separate, human-authorized step.

## Related

- `../../starters/moltsets-reachability/` — the scripts this wraps
- `../../starters/apollo-prospecting/` — the title weights and the sheet engine this reuses
- `../../chapters/23-reachability-grading.md` — the build, the numbers, and why the route column exists
- [Moltsets email risk scores](https://developer.moltsets.com/moltsets-data/email-risk-scores)
- [Moltsets skills library](https://moltsets.com/library) — the 76 upstream Claude skills this one sits beside
