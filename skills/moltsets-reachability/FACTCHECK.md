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

## Second pass endpoint (verified on two lists, 2026-09-01 and 2026-09-02)

| Endpoint | Body | Shape back | As a second pass |
|---|---|---|---|
| `search_business_profile_by_name` | `{name: "First Last", company: "<domain>"}` | one flat profile (same keys as `reverse_email_lookup`) | 2,722 rows → 436 same-domain A/B accepted (16%), 37 of them on rows the verifier had dropped; 490 profiles with no confirmed email (F), 422 cross-domain (review), 77 name mismatches |
| `search_people` | `{query: "First Last", company: "<domain>", limit: 5}` | list under `results.results` | 0 for 181 (home-services owners), 0 for 54 and 2 for 112 (GTM engineers). Not a second pass. |

Decision rules live in `lib/reachability.py::profile_decision`: `accept_same_domain` (A/B on the queried or corporate domain, name matches) · `risky_same_domain` (C/D/F on the domain) · `profile_no_email` (person known, no work address; grade F) · `review_cross_domain` (graded address on another domain; never adopted, recorded as `molt_other_email_domain/grade`) · `name_mismatch` · `no_candidate` (404). Only on silence or F. Never on D.

## Verifier deltas (v0.12.0)

Normalization (`lib/reachability.py::norm_verifier_status`): valid / deliverable / ok / safe → `valid` · catch-all / catch_all / catchall / accept_all → `catch-all` · unknown / risky / timeout → `unknown` · invalid / undeliverable / bounce → `invalid` · do_not_mail / disposable / toxic → `do_not_mail` · abuse / spamtrap / spam_trap → `abuse`. Hard-fail set = `invalid, do_not_mail, abuse`. Empty stays empty (no verifier on that row); an unrecognized word is `unknown`.

Delta classes are pure functions of (verifier status, grade, second-pass decision, corrected, still-at-company); they never call the API. The thirteen classes and their meanings are `DELTA_LEGEND`. Say "the verifier's verdict stands" for `not_in_graph`, `molt_no_data`, and `person_confirmed_other_email`. Say "review" for `molt_contradicts_invalid` and `cross_domain_review`. Never describe a corrected or recovered address as verified; it has not been SMTP-probed.

## Moltsets skills library (moltsets.com/library, enumerated 2026-09-01)

26 skills: 25 cards plus the featured "Email Finder". Categories seen on the cards: Enrichment, Prospecting, Ad Audience, Identity Resolution, IP Intelligence. Four outcome groups: verified emails and mobiles; find new prospects; ad audiences (SHA256, MAID); website visitors (IP, RB2B). Authors: MoltSets (22), Robb Clarke (4 RB2B skills). Data connections listed: Claude Chat, CSV, Excel, Google Sheets, HubSpot, RB2B.

**Overlap with what this repo uses Apollo for (say this plainly):**

| Apollo use in this repo | Library skill that covers it | Verified? |
|---|---|---|
| `people/match` on a LinkedIn URL (still at the company?) | Enrich a LinkedIn Profile (`reverse_linkedin_lookup`) | Yes, 2026-09-01: 12/12 profiles returned, agreed with Apollo on 6/8 job changes and 4/4 stays |
| `people/match` by name + domain | Find & Enrich by Name (`search_linkedin_profile` + email); `search_business_email_by_name` | Endpoint shape verified (name + company domain; `count_only: true` is free); not yet run at volume |
| Buying-committee expansion per company (apollo-prospecting starter) | Find Employees at a Company · Find Contacts at Target Accounts · HubSpot Buying Committee Expansion | Not yet tested |
| `mixed_people/api_search` | Search B2B Prospects (`search_people`) | Used since August |

**Not covered by the library or the API (Apollo still needed):** the intent-gated company waterfall in `starters/apollo-prospecting/waterfall.py` (job postings, funding rounds, tech-stack twins) and Apollo's saved-search filters. Nothing in the library ships an A-F color-graded dashboard, a grade-to-channel routing table, a budget/ledger surface, or an employment-vs-address comparison. Say "the library does not cover X"; do not say "Moltsets cannot do X".

## The LinkedIn URL is the better key (verified 2026-09-01)

`reverse_linkedin_lookup {linkedin_url}` returned a profile (current company, title, seniority, `current_role_start_date`) for 12/12 people whose business emails had 404'd on `reverse_email_lookup`. 4 of the 12 also carried a graded business email (2 the same address Apollo held, 2 on a different domain). Response `company` is a dict `{name, website_url, linkedin_url, industry, revenue}`; there is no `domain` key, derive it from `website_url`. It consumes an enrich-pool record on a hit. `search_linkedin_profile` takes `name` + company domain, not a URL (422 otherwise).

## Receipts you may quote (dated)

- 2026-08-05 to 2026-08-10, Clearbox ledger: `reverse_email_lookup` 805 calls, 526 hits, 279 not found (65% hit). `search_people` 359 calls, 219 hits, 137 not found, 3 errors. 0 external tokens.
- AEO409 list (407 Apollo "Verified" addresses): 272 confirmed valid, 17 corrected, 10 risky, 26 no email, 82 not found. Grades A 297, B 2.
- Headless CRM list (1,752 people, 2026-08-31): A 1,014, B 9, C 6, D 2, F 4, LinkedIn-only 717. `linkedin_to_best_email` 0 hits in 26. `linkedin_to_mobile_phone` 29 hits in 40 calls.
- Employment sample (40 people, 2026-08-30): Apollo `people/match` 40/40; Moltsets `reverse_email_lookup` 9/40 on that GTM-engineer ICP; 8 of 8 same-address hits were grade A; the two sources agreed on still-at-company 32/40; Apollo alone caught 5 real moves.
- 2026-09-01, 200 US GTM engineers (Apollo export, all Verified), graded twice. Email key: 70 profiles / 60 graded (all A) / 60 send-ready / 120 to LinkedIn / 18 job changes (Apollo). URL key (`reverse_linkedin_lookup`): 196 profiles / 136 graded (135 A, 1 B) / 113 send-ready (32 corrected same-domain addresses) / 54 to LinkedIn / 27 job changes / 6 hold. Apollo vs Moltsets employment: agree 181 of 193; Apollo 18 moves, Moltsets 23; 12 disagreements split both ways (advisory or side roles listed as current vs "Stealth"). Second pass 2/112 then 0/54. Records 228 enrich + 5 search for the URL run, 0 phone tokens.
- 2026-09-02, 10,088 home-services contacts on a client campaign list already verified and pooled by ZeroBounce (client anonymized in public copy). `reverse_email_lookup` 8,061 profiles (79.9%), 2,027 not found. Grades A 7,771 / B 31 / C 13 / D 7 / F 1,206; 1,060 not found after both passes (10.5%). Agree with ZB valid on the same address 6,776; corrected same-domain addresses 819; catch-all pool rows graded A/B 1,380 of 1,739 (28 ZB catch-all, 1,347 ZB valid); ZB drops recovered with a same-domain A/B 75 of 725; ZB hard-fail with Moltsets A/B on the exact address 189 (review, re-probe); job changes 793; LinkedIn URLs filled 9,032. Second pass `search_business_profile_by_name` (first + last + domain): 2,722 rows, 436 same-domain A/B accepted (16%), 37 on ZB-dropped rows; `search_people` 0 of 181. 14,087 calls, 0 phone tokens, $0 marginal, about 9.6k weekly enrich records, about 75 min at 4 workers. Grade mix is ICP-dependent: the 200 GTM engineers graded all A; this list graded 77% A with 12% F.

Anything not on this page is not a fact yet.
