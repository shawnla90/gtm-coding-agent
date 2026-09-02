# Chapter 23: Reachability Grading

**This chapter is for founders, GTM engineers, and agency operators who have a list of "verified" emails and no idea which ones will actually land. You will grade every address A through F with Moltsets, confirm the person is still at the company, and route the rows a bad grade would normally kill into a channel that still works, all in a color-coded Google Sheet you can read in ten seconds. The proving run: 200 GTM engineers, every email marked Verified in Apollo, graded twice. Keyed on the email, 60 came out send-ready. Keyed on the LinkedIn URL, the same people gave 113. 54 went to LinkedIn instead of a trash can, and 27 had already changed jobs.**

---

## TL;DR

- **A grade is a fact about a mailbox, not a verdict on a person.** Moltsets grades an address A (valid, seen replying or opening) through D (hard invalid, complaint, spam trap). F means no data. A 404 means the graph has never seen the address. Only D is a reason to stop emailing, and even D is not a reason to drop the row.
- **Relevance, timing, reachability.** Title weights score relevance. A lookup on the LinkedIn URL answers timing (still there, or moved?). The grade answers reachability. The sheet's `route` column is what you do when one of the three says no.
- **Key the graph on the URL.** `reverse_linkedin_lookup` found 196 of 200 profiles and graded 134 addresses where the email-keyed lookup found 70 and graded 60. Same people, same night.
- **Misses are free.** A Moltsets 404 consumes no record. That changes the economics of a second pass: you can afford to look again by name and company domain before you give up.
- **Every row keeps a channel.** A/B email. C small monitored segment. D LinkedIn, then a mobile if you have tokens. F and 404 second pass, then LinkedIn. Moved: re-source at the new company. Nothing is deleted because a vendor was silent.
- **Apollo, said plainly.** I used it for the employment check, then found the Moltsets library already covers that step. Both ran on all 200 and agreed 181 of 193 times. Apollo was redundant here; it still stands alone on the intent-gated company waterfall.
- **The build is `starters/moltsets-reachability/`.** Four scripts and a budget tool. Runs on the same title weights and sheet engine as the Apollo starter.

---

## The Origin

I had 1,297 GTM engineers from an Apollo export, every one with a Verified email. Verified is a snapshot: the last time Apollo checked, the mailbox accepted. It says nothing about replies, catch-all domains, or whether the person still works there. Moltsets is Adam Robinson's people-search API, keyed on business identity, and it grades addresses with delivery evidence: an A has a known reply, open, or click behind it. I had used it as a validation gate since August. What I had not built was the part after the grade. Every tool I had seen treats a bad grade as a suppression. The person is still real. The address is what died. So the sheet got a `route` column, and the route comes from the grade.

---

## What the Grades Mean

From [developer.moltsets.com](https://developer.moltsets.com/moltsets-data/email-risk-scores). Read this table twice; getting D and F backwards suppresses reachable people and emails spam traps.

| Grade | Meaning | Docs say | Route in this build |
|---|---|---|---|
| A | valid: known reply, open, or click | send | `email` |
| B | known send, no bounce | probably send | `email` (smaller batches) |
| C | catch-all domain | your call | `email_low_volume` |
| D | hard invalid: bounce, complaint, or spam trap | do not send | `linkedin_then_phone` |
| F | no data | re-verify or treat like C | second pass, then `linkedin` |
| 404 | not in the graph | (costs nothing) | second pass, then `linkedin` |

The docs' own rule: suppress D at the list level; segment C and F away from A/B rather than dropping them. They are unknown, not bad.

Two more things the docs do not say loudly enough. A personal Gmail is an output of this graph, never an input; free-mail addresses 404 on every lookup. And `search_people` wants a company **domain**, not a company name. `"Bobyard"` returns nothing; `"bobyard.com"` returns the profile. Get that wrong and you get a wall of false misses that look exactly like real ones.

---

## The Stack

| Piece | Tool | What it does |
|---|---|---|
| Load | `init_db.py` | CSV (short schema or raw Apollo export) → SQLite |
| Timing | Moltsets `reverse_linkedin_lookup` (or Apollo `people/match`, or both) | LinkedIn URL → current company; disagree with the list = moved. The URL pass also returns the graded address when the graph has one |
| Grade | Moltsets `reverse_email_lookup` | business email → A-F, confirmed address, validation date |
| Second pass | Moltsets `search_people` | name + company **domain** → accept only same-domain A/B |
| LinkedIn-only | Moltsets `linkedin_to_best_email` | URL → best address + grade |
| Phones (capped) | Moltsets `linkedin_to_mobile_phone` | dead-email rows only, 1 phone token per hit |
| Score | `score.py` | title relevance × grade multiplier, top 3 per company |
| Sheet | `build_sheet.py` + vendored `sheet_engine.py` | 9 tabs, grade colors, route colors, dashboard, usage ledger |
| Budget | `budget.py` | three free calls: the two record pools, phone tokens, endpoint count |

Keys are read env-first, then `.env`, then a local SQLite vault via `SECRETS_DB`. Nothing is printed. See Chapter 04 for the vault.

---

## The Waterfall

```
for each contact:
  0. --employment  reverse_linkedin_lookup(linkedin_url)   (moltsets, default; or apollo, or both)
                   company disagrees with the list?  -> job_changed, route resource, skip the email
                   graded business email present?    -> take it, skip step 1
  1.               reverse_email_lookup(email)        -> grade, confirmed address, validated_at
  2. --second-pass grade in ('', 'F')?                -> search_people(query=name, company=DOMAIN)
                   accept ONLY same-domain A/B with a matching name
  3.               no email but a LinkedIn URL?       -> linkedin_to_best_email(url)
  4. --phones N    tier in (SUPPRESS, HOLD_not_found)? -> linkedin_to_mobile_phone(url), capped
  classify -> verdict, tier, route
  commit the row
```

Order matters. Employment first, because grading an address the person left last quarter is a wasted record and a bounce waiting to happen. Second pass only on silence or F, never on D; D is an answer. Phones last, capped, and only for rows where email is not an option.

The classifier is forty lines and pure, so it is unit-tested without a network:

```python
if still_at_company == "moved":       return "job_changed", "HOLD_job_change", "resource"
if not email:                         return "no_email", "HOLD_no_email", li_route
if dom(email) in FREEMAIL:            return "free_email", "HOLD_review", "hold"
if grade in ("A", "B"):
    if same_domain(email, company):   return "confirmed_valid", "T1_send", "email"
    return "confirmed_cross_domain", "HOLD_review", "hold"
if grade == "C":                      return "catch_all", "T2_catchall", "email_low_volume"
if grade == "D":                      return "hard_invalid", "SUPPRESS", "linkedin_then_phone"
# F or nothing: look again first, then LinkedIn
return verdict, "HOLD_not_found", "second_pass" if not second_pass_done else "linkedin"
```

A/B on a different domain than the company on your list is held, not sent. Either the person moved and Moltsets has the new address (good, re-source), or the name search found a different human with the same name (bad, and it happens). Domain agreement is the identity check.

---

## The Ledger Is the Budget

Moltsets meters four things and none of them is a per-lookup credit:

| Unit | On the $97 plan | What consumes it |
|---|---|---|
| Calls | unlimited count, rate-limited per rolling 5h window | every POST |
| Records, enrich pool | 15,000 per 5h, 75,000 per week | a data-bearing response from an enrich endpoint |
| Records, search pool | 7,500 per 5h, 37,500 per week | a data-bearing response from a search endpoint |
| Internal tokens | -1, unlimited | ignore |
| Phone tokens | 50 per month | one per mobile HIT; misses free |

A 404 consumes nothing. A crash in your own client mid-batch still consumes the record for the row it was on, with no refund, and the API keeps no history for you. So `grade.py` commits every row as it finishes, reads `records_remaining_5h` off every response, and stops at a floor. `budget.py` shows the pools with three free calls, plus your own ledger by endpoint: calls, hits, not-found, errors, tokens.

The URL-keyed run consumed 228 enrich records and 5 search records. The not-found rows cost nothing.

---

## Scoring

Same composite the Apollo starter uses, with the multiplier now driven by the grade.

| Grade | Multiplier |
|---|---|
| A | 1.0 |
| B | 0.85 |
| C | 0.6 |
| F / not found | 0.3 |
| D | 0.15 |

D is not zero on purpose. Head of Growth on a grade A address scores 100. The same Head of Growth on a D scores 15, still ranks, still shows up in the Route - LinkedIn tab with a connection note as the next step. The person's relevance did not change. The mailbox did.

---

## The Run, Twice

200 US GTM engineers from the 1,297-row export, 181 companies, 153 of them "Entry" seniority at startups. One name excluded because they were already in my pipeline. No phones.

| | Keyed on the email | Keyed on the LinkedIn URL |
|---|---|---|
| Profiles found | 70 of 182 | 196 of 200 |
| Graded addresses | 60, all A | 136: 135 A, 1 B |
| Send-ready | 60 | 113, of which 32 were a different same-domain address than the export held |
| Routed to LinkedIn | 120 | 54 |
| Job changes held | 18 | 27 |
| Second pass recovered | 2 of 112 | 0 of 54 |
| Records consumed | 70 enrich, 12 search | 228 enrich, 5 search |

Three things worth saying plainly.

**The key matters more than the ICP.** By email, 38% of these early-career startup people were in the graph. By LinkedIn URL, 98% had a profile and 68% had a graded address. A business-identity graph knows the person better than it knows the mailbox. Lead with the URL.

**When it confirms, it confirms.** Every graded address was an A except one B. `reverse_email_lookup` behaves like a confirmation endpoint: it returns the address it can stand behind. The B, C, D, and F grades show up through `search_people` and `linkedin_to_best_email`, where the API offers a candidate rather than confirming yours. And 32 of the 113 send-ready rows carried a different address than the export, on the same domain. The pattern guess was wrong; the confirmed address was right.

**The second pass rarely lands, and that is information.** 0 of 54, 2 of 112. When both lookups come back empty, the person is not in the graph under any address. Keep the second pass for the movers it catches under a new domain, and stop expecting it to rescue a list.

---

## The Sheet

Nine tabs when every tier is populated; seven tonight because nothing graded C or D.

- **Dashboard**: graded share, send-ready share, grade distribution, route mix, Apollo still / moved / unknown, first-pass hit rate, what the second pass recovered, records and tokens consumed.
- **Send Ready**: A/B on the company's domain, ranked top 3 per company with persona diversity.
- **Send Low Volume**: C, when there is any.
- **Route - LinkedIn**: the 54 rows a suppress-only tool would have deleted. Connection note first.
- **Review - Hold**: the 6 cross-domain or free-mail rows and the 27 job changes, with an agree/disagree column when two employment sources ran.
- **Suppressed**: D rows, for the sequencer's suppression list. D rows also appear in Route - LinkedIn, on purpose.
- **All Contacts**, **Grading Model** (the weights and meanings, so the sheet explains itself), **Moltsets Usage** (your ledger by endpoint).

Grade cells are colored A green, B light green, C amber, D red, F orange, unknown grey. Routes are colored too. Emails and phones are obfuscated unless you build a private copy with `--full-emails`. The sheet rebuilds in place by id, so the link never changes.

---

## The Apollo Part, Said Plainly

I used Apollo `people/match` for the still-at-the-company check because that is what I knew. Then I read the Moltsets skills library: Enrich a LinkedIn Profile, Find and Enrich by Name, Find Employees at a Company, Find Contacts at Target Accounts, HubSpot Buying Committee Expansion. I did not know those were in there, and they cover what this repo's Apollo starter does.

So the second run used `--employment both`. The two sources agreed 181 times out of 193. Apollo flagged 18 job changes, Moltsets 23, and the 12 disagreements split both ways: Moltsets sometimes lists an advisory seat or a side project as the current company, Apollo sometimes returns "Stealth". Neither is an oracle, so the sheet holds a row when either says moved. On this list Apollo was redundant for the employment step. I will be testing the rest of the library against what I still run on Apollo, and the FACTCHECK in `skills/moltsets-reachability/` keeps the overlap table current. Where Apollo stands alone for now is the intent-gated company waterfall in `starters/apollo-prospecting/waterfall.py`: job postings, funding rounds, tech-stack twins. Moltsets does not have that.

---

## Run It

```bash
cd starters/moltsets-reachability
cp .env.example .env            # or: export SECRETS_DB=~/.gtm-vault/vault.db
pip install -r requirements.txt
python3 setup_oauth.py          # once

python3 budget.py               # free; do this before any batch
bash run.sh                     # 25 fictional rows, first pass only
bash run.sh my_list.csv --full  # employment check + second pass on your list
```

Read the Dashboard back in this order: loaded, graded, send-ready; first-pass hit rate and second-pass recovery; grade distribution; route mix; still / moved; what it cost. The misses are receipts. Say "not in the graph", never "invalid".

---

## What I Would Tell Adam

The grade is the product, and the library does not have the piece after it. Twenty-six skills on moltsets.com cover enrichment, prospecting, ad audiences, and visitor identification. None of them turns a D into a LinkedIn task or puts two employment sources side by side. That is the skill in this chapter. The misses are in here too: a second pass that rarely lands, a `location` parameter the API ignores, side roles reported as the current company, and a D-versus-F table that deserves to be on every reference page.

Part of the [GTM Coding Agent](https://github.com/shawnla90/gtm-coding-agent). Starter: `starters/moltsets-reachability/`. Skill: `skills/moltsets-reachability/`.
