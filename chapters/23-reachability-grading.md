# Chapter 23: Reachability Grading

**This chapter is for founders, GTM engineers, and agency operators who have a list of "verified" emails and no idea which ones will actually land. You will grade every address A through F with Moltsets, confirm the person is still at the company with Apollo, and route the rows a bad grade would normally kill into a channel that still works, all in a color-coded Google Sheet you can read in ten seconds. The proving run: 200 GTM engineers, every email marked Verified in Apollo. 60 came out send-ready. 120 came out with a LinkedIn route instead of a trash can. 18 had already changed jobs.**

---

## TL;DR

- **A grade is a fact about a mailbox, not a verdict on a person.** Moltsets grades an address A (valid, seen replying or opening) through D (hard invalid, complaint, spam trap). F means no data. A 404 means the graph has never seen the address. Only D is a reason to stop emailing, and even D is not a reason to drop the row.
- **Relevance, timing, reachability.** Title weights score relevance. Apollo `people/match` on the LinkedIn URL answers timing (still there, or moved?). The Moltsets grade answers reachability. The sheet's `route` column is what you do when one of the three says no.
- **Misses are free.** A Moltsets 404 consumes no record. That changes the economics of a second pass: you can afford to look again by name and company domain before you give up.
- **Every row keeps a channel.** A/B email. C small monitored segment. D LinkedIn, then a mobile if you have tokens. F and 404 second pass, then LinkedIn. Moved: re-source at the new company. Nothing is deleted because a vendor was silent.
- **The build is `starters/moltsets-reachability/`.** Four scripts and a budget tool. Runs on the same title weights and sheet engine as the Apollo starter.

---

## The Origin

I had 1,297 GTM engineers from an Apollo export, every one with a Verified email, and a campaign to run against them. Verified is a snapshot: the last time Apollo checked, the mailbox accepted. It does not say whether the mailbox has ever seen a reply, whether the domain accepts everything, or whether the person still works there.

Moltsets is Adam Robinson's people-search API. It is keyed on business identity and it grades addresses with delivery evidence, not SMTP pings: an A has a known reply, open, or click behind it. I had been using it as a validation gate on other lists since August (805 reverse lookups, 526 hits, 0 errors, 0 tokens spent). What I had not built was the part after the grade. Every tool I had seen treats a bad grade as a suppression. The person is still real. The address is what died.

So the sheet got a `route` column, and the route comes from the grade.

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
| Timing | Apollo `people/match` | LinkedIn URL → current company; disagree with the list = moved |
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
  0. --apollo      people/match(linkedin_url)
                   company disagrees with the list?  -> job_changed, route resource, skip the email
  1.               reverse_email_lookup(email)        -> grade, confirmed address, validated_at
  2. --second-pass grade in ('', 'F')?                -> search_people(query=name, company=DOMAIN)
                   accept ONLY same-domain A/B with a matching name
  3.               no email but a LinkedIn URL?       -> linkedin_to_best_email(url)
  4. --phones N    tier in (SUPPRESS, HOLD_not_found)? -> linkedin_to_mobile_phone(url), capped
  classify -> verdict, tier, route
  commit the row
```

Order matters. Apollo first, because grading an address the person left last quarter is a wasted record and a bounce waiting to happen. Second pass only on silence or F, never on D; D is an answer. Phones last, capped, and only for rows where email is not an option.

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

Tonight's run consumed 70 enrich records for 70 hits and 12 search records for 122 second-pass calls. The 112 misses cost nothing.

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

## The Run

200 US GTM engineers from the 1,297-row export, 181 companies, 153 of them "Entry" seniority at startups. One name excluded because they were already in my pipeline. `bash run.sh gtme.csv --full`, no phones.

| Step | Result |
|---|---|
| Apollo `people/match` | 200 checked: 180 still there, 18 moved, 2 unknown |
| `reverse_email_lookup` | 182 calls (the 18 movers were skipped): 70 profiles found, 112 not in the graph |
| Grades on the first pass | 60 confirmed work emails, every one grade A; 10 profiles came back without a confirmed address |
| Second pass by name + domain | 122 calls: 2 recovered as same-domain A, 4 cross-domain (held), 116 no candidate |
| Send ready | 60 |
| Held | 2 A's on a different domain than the listed company, 18 job changes |
| Routed to LinkedIn | 120 |
| Records consumed | 70 enrich, 12 search. Phone tokens: 0 of 29 remaining. Errors: 0. |

Three things worth saying plainly.

**The graph is thin on this ICP.** 38% found. On a list of marketing leaders at agencies the same endpoint found 65%. Early-career people at companies under 100 employees are where a business-identity graph has the least to work with. A 22% first-pass rate on a 40-person sample of the same list two nights earlier said the same thing.

**When it hits, it hits.** Every confirmed address was an A. On 407 Apollo-Verified addresses on another list, the grades were A 297, B 2, and 82 not found. Apollo Verified plus a Moltsets A has not bounced for me yet. `reverse_email_lookup` behaves like a confirmation endpoint: it returns the address it can stand behind. The B, C, D, and F grades show up through `search_people` and `linkedin_to_best_email`, where the API is offering you a candidate rather than confirming yours.

**The second pass rarely lands, and that is information.** 2 of 112. When the reverse lookup says 404 on this ICP, the person is not in the graph under any address. Build the second pass, keep it, and stop expecting it to rescue the list. Its real job is catching the job-changers Moltsets knows about under a new domain, which is a hold, not a send.

---

## The Sheet

Nine tabs when every tier is populated; seven tonight because nothing graded C or D.

- **Dashboard**: graded share, send-ready share, grade distribution, route mix, Apollo still / moved / unknown, first-pass hit rate, what the second pass recovered, records and tokens consumed.
- **Send Ready**: A/B on the company's domain, ranked top 3 per company with persona diversity.
- **Send Low Volume**: C, when there is any.
- **Route - LinkedIn**: the 120 rows a suppress-only tool would have deleted. Connection note first.
- **Review - Hold**: the 2 cross-domain A's and the 18 job changes.
- **Suppressed**: D rows, for the sequencer's suppression list. D rows also appear in Route - LinkedIn, on purpose.
- **All Contacts**, **Grading Model** (the weights and meanings, so the sheet explains itself), **Moltsets Usage** (your ledger by endpoint).

Grade cells are colored A green, B light green, C amber, D red, F orange, unknown grey. Routes are colored too. Emails and phones are obfuscated unless you build a private copy with `--full-emails`. The sheet rebuilds in place by id, so the link never changes.

---

## Apollo and Moltsets Are Not the Same Question

Apollo's identity graph follows a person across jobs. That is what made `people/match` on a LinkedIn URL the right first step: it caught 18 movers tonight and 5 of 40 on the earlier sample, and Moltsets caught none of those because its graph is keyed on the address the person had. Moltsets grades whether an address delivers, with reply and open evidence Apollo does not have. Use each for its question. The sheet is where the two answers meet.

---

## Run It

```bash
cd starters/moltsets-reachability
cp .env.example .env            # or: export SECRETS_DB=~/.gtm-vault/vault.db
pip install -r requirements.txt
python3 setup_oauth.py          # once

python3 budget.py               # free; do this before any batch
bash run.sh                     # 25 fictional rows, first pass only
bash run.sh my_list.csv --full  # Apollo check + second pass on your list
```

Read the Dashboard back in this order: loaded, graded, send-ready; first-pass hit rate and second-pass recovery; grade distribution; route mix; still / moved; what it cost. The misses are receipts. Say "not in the graph", never "invalid".

---

## What I Would Tell Adam

The grade is the product, and the library does not have the piece after it. Seventy-six skills on moltsets.com cover enrichment, prospecting, ad audiences, and visitor identification, with Google Sheets listed as a data connection. None of them turns a D into a LinkedIn task or an F into a second look. That is the skill in this chapter. The misses are in here too, on purpose: coverage on early-career startup people, a second pass that rarely lands, a `location` parameter the API ignores, and a D/F table that deserves to be on every reference page.

Part of the [GTM Coding Agent](https://github.com/shawnla90/gtm-coding-agent). Starter: `starters/moltsets-reachability/`. Skill: `skills/moltsets-reachability/`.
