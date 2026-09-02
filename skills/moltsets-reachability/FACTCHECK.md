# FACTCHECK — moltsets-reachability

Hard gates. Read before writing anything about Moltsets, grades, or cost. Every line here was verified against developer.moltsets.com or a live `get_billing` / `get_account` response on 2026-09-01. Re-verify with `python3 budget.py` before quoting a number older than a week.

## Grade semantics (developer.moltsets.com/moltsets-data/email-risk-scores)

| Grade | Definition | Recommended action |
|---|---|---|
| A | valid: known reply, open, or click | send |
| B | known send with no bounce | probably send; smaller batches for cold |
| C | catch-all | your call; segment, warm at lower volume, monitor |
| D | hard invalid: bounce, complaint, or spam trap | do not send |
| F | no data available | your call; re-verify or treat like C |

Docs rules, verbatim in spirit: "suppress D at the list level" and "segment C and F away from A/B rather than dropping them; they are unknown, not bad." Revalidation window is 90 days.

**The mix-up to refuse:** earlier internal reports labeled F as "hard invalid / spam trap" and D as "known negative activity". That is backwards. F is no data. D is the hard invalid.

## What a 404 is

Not in the graph. A coverage gap. Costs nothing, consumes no record. Never a statement about the address. Free-mail addresses (gmail, yahoo, outlook, etc.) 404 on every lookup endpoint because the graph is keyed on business identity; a personal email is an output, never an input.

## The four metered units ($97 plan, `subscription_97`, verified 2026-09-01)

| Unit | Value | Source |
|---|---|---|
| Calls | unlimited count; rate-limited 75,000 requests per 5h (enrich), 37,500 per 5h (search) | `get_account.fair_use.*.requests` |
| Records, enrich pool | 15,000 per 5h, 75,000 per week | `get_account.fair_use.enrich.records` |
| Records, search pool | 7,500 per 5h, 37,500 per week | `get_account.fair_use.search.records` |
| Internal tokens | `token_balance: -1`, `unlimited: true`; `token_costs` all 1s | `get_billing` |
| Phone tokens | 50 allowance per period; 1 per mobile HIT; misses free | `get_account.phone_token_balance` / `phone_token_allowance`; docs best-practices page |

A record is consumed on a data-bearing response. A client crash mid-batch still consumes it. This is why `grade.py` commits per row and reads `records_remaining_5h` off every response.

The older "600 external tokens, 10 per phone hit" model is gone from the API. Do not quote it.

## Endpoint catalogue (25, from `get_billing.token_costs`)

Search: `search_people`, `search_companies`, `search_linkedin_profile`, `search_business_email_by_name`, `search_business_profile_by_name`
Emails: `linkedin_to_best_email`, `linkedin_to_business_email`, `linkedin_to_personal_email`, `linkedin_to_best_personal_email`, `linkedin_to_all_personal_emails`
Phone: `linkedin_to_mobile_phone`
Reverse: `reverse_email_lookup`, `reverse_linkedin_lookup`, `email_to_linkedin`
Ad audiences: `email_to_maid`, `business_email_to_sha256`, `linkedin_to_sha256`, `hem_to_email`, `hem_to_linkedin`, `ip_to_hem`, `ip_to_maid`
Visitors: `ip_to_company`
Account (free): `get_account`, `get_billing`, `get_usage`

## Response shapes (three, all normalized by `lib/moltsets_client.py`)

- `reverse_email_lookup`, `search_business_profile_by_name`: flat under `results`; grade at `work_email_confirmed_risk_score`; the confirmation DATE is at `work_email_confirmed_status` despite the name; LinkedIn at `linkedinurl` (no underscore); company at `current_company` / `current_company_url`.
- `search_people`: list under `results.results`; grade at `business_email_risk_score`; `business_email_validated_at`; `linkedin_url` (underscore); `company` is a dict `{name, domain, size}`.
- `linkedin_to_best_email`: `results.email`, `results.type`, `results.risk_score`, `results.last_validated_at`.
- Fair-use counters ride on `metadata.fair_use` for data endpoints only. `get_account` nests them under `results.fair_use.{enrich,search}.records.{5h,1w}`. Free status calls carry no `metadata.fair_use`.

## Parameter gotchas (each verified live)

- `search_people.company` expects a **domain**. A company name 404s and looks like no data.
- `search_people.location` is **not a parameter**. Silently ignored; results come back worldwide.
- `search_people.query` is fuzzy across name, title, and headline. Name-only queries return role accounts and homonyms. Filter on real first+last, title keywords, and domain agreement.
- `limit` max is 25 per docs.

## Moltsets skills library (moltsets.com/library, checked 2026-09-01)

76 Claude skills, 10 categories, 4 outcomes: verified emails and mobiles; find new prospects; ad audiences (SHA256, MAID); website visitors (IP, RB2B). Data connections listed: Claude Chat, CSV, Excel, Google Sheets, HubSpot, RB2B. Nothing in the library ships an A-F color-graded dashboard, a grade-to-channel routing table, a budget/ledger surface, or an Apollo employment pairing. Say "the library does not cover X"; do not say "Moltsets cannot do X".

## Receipts you may quote (dated)

- 2026-08-05 to 2026-08-10, Clearbox ledger: `reverse_email_lookup` 805 calls, 526 hits, 279 not found (65% hit). `search_people` 359 calls, 219 hits, 137 not found, 3 errors. 0 external tokens.
- AEO409 list (407 Apollo "Verified" addresses): 272 confirmed valid, 17 corrected, 10 risky, 26 no email, 82 not found. Grades A 297, B 2.
- Headless CRM list (1,752 people, 2026-08-31): A 1,014, B 9, C 6, D 2, F 4, LinkedIn-only 717. `linkedin_to_best_email` 0 hits in 26. `linkedin_to_mobile_phone` 29 hits in 40 calls.
- Employment sample (40 people, 2026-08-30): Apollo `people/match` 40/40; Moltsets `reverse_email_lookup` 9/40 on that GTM-engineer ICP; 8 of 8 same-address hits were grade A; the two sources agreed on still-at-company 32/40; Apollo alone caught 5 real moves.
- Tonight's 200-row run: see `data/grade_summary.json` in the starter and the Dashboard tab. Quote those numbers with the date.

Anything not on this page is not a fact yet.
