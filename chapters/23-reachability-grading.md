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
- **Next to a verifier, the value is in the disagreements.** On a client's 10,088-row list already through ZeroBounce: 6,776 rows where both agreed on the same address, 819 corrected addresses, 1,380 of 1,739 catch-all rows graded A/B, 75 of 725 drops recovered, 793 job changes the verifier had passed, 7 grade D. 1,060 never seen, 1,206 F. The grade mix is the ICP, not the tool.
- **The build is `starters/moltsets-reachability/`.** Five scripts and a budget tool. Runs on the same title weights and sheet engine as the Apollo starter. Feed it a list with a `zb_status` column and it adds the Disagreements and Verifier vs Moltsets tabs.

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
| Second pass | Moltsets `search_business_profile_by_name` | name + company **domain** → one flat profile → accept only same-domain A/B (`search_people` went 0 for 181 in this role) |
| Verifier delta | `lib/reachability.py::delta_class` | your verifier's verdict x the Moltsets grade → 13 classes, no API call |
| LinkedIn-only | Moltsets `linkedin_to_best_email` | URL → best address + grade |
| Phones (capped) | Moltsets `linkedin_to_mobile_phone` | dead-email rows only, 1 phone token per hit |
| Score | `score.py` | title relevance × grade multiplier, top 3 per company |
| Sheet | `build_sheet.py` + vendored `sheet_engine.py` | 11 tabs, grade colors, route colors, delta colors, dashboard, usage ledger; `--summary-only` for a shareable receipt |
| Import | `import_graded.py` | rows graded elsewhere → same database, same sheet, no API calls |
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
  2. --second-pass grade in ('', 'F')?                -> search_business_profile_by_name(name, company=DOMAIN)
                   accept ONLY same-domain A/B with a matching name; a different domain is a
                   different person until proven otherwise (search_people: 0 for 181, see below)
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

**The second pass rarely landed, and the reason was the endpoint.** 0 of 54, 2 of 112, both with `search_people`. On the 10,088-row list in the next section `search_people` went 0 for 181 again, while `search_business_profile_by_name` on first + last + domain accepted 436 same-domain A/B addresses across 2,722 second-pass rows. Silence from the wrong endpoint is a query problem, not a coverage fact. The starter's default second pass changed accordingly; when the right endpoint comes back empty too, the person is not in the graph under any address.

---

## The Run at 10,088, Next to a Verifier

The 200-row run had nothing else checking the addresses. The next list did. A client's 10,088-contact home-services campaign list, owners, general managers, office managers, every row already through ZeroBounce and sorted into sending pools by recipient mail host: Microsoft clean, Google clean, catch-all isolated, gateway. That is the test that matters for anyone with a verifier already in the stack, because the only thing a graph can add there is what the probe cannot see: whether the address has been used, and who is using it now.

Same grader. One `reverse_email_lookup` per row, then `search_business_profile_by_name` on first + last + domain when the first call did not return A or B. 14,087 calls, 0 phone tokens, $0 marginal on the flat plan, about 75 minutes at four workers, every call in the local ledger.

| | Rows |
|---|---|
| Profile returned on the email | 8,061 (79.9%) |
| A / B / C / D / F | 7,771 / 31 / 13 / 7 / 1,206 |
| Not in the graph after both passes | 1,060 (10.5%) |
| Agree: verifier valid, Moltsets A/B, same address | 6,776 |
| Corrected: a different same-domain address with activity | 819 |
| Catch-all pool rows graded A/B | 1,380 of 1,739 |
| Verifier drops recovered with a same-domain A/B | 75 of 725 |
| Verifier hard-fail, Moltsets A/B on the exact address (review) | 189 |
| Job changes | 793 |
| LinkedIn URLs on a list that had none | 9,032 |

Where they agree, they agree hard, and those rows send first. The value is in the disagreements. The catch-all pool was isolated because an accept-everything domain turns a verifier's "valid" into a shrug; of the 1,380 rows the graph graded A or B on observed activity, 1,347 had been marked valid, which on a catch-all domain says nothing. 819 rows passed the probe on an address nobody has been seen using while a sibling address at the same domain had activity. 793 people had changed jobs, and the verifier passed every one of them, because the mailbox still accepted mail. Seven rows graded D, one of them marked valid: bounce, complaint, or trap history headed for a warming mailbox.

The misses, plainly. 1,060 rows were never in the graph; on those the verifier's word is the only word. 1,206 rows graded F, person known, address never seen in use, 953 of them verifier-valid. F is unproven, not bad, and it is the largest ambiguity in the run. The dropped pool graded A/B at 44.3% against 76 to 81% for the clean pools: the graph recovers some of what a verifier drops, not the majority. 422 second-pass rows came back on a different domain and 320 of them sit in review, because a person with the same name at a company with a similar name is a real failure mode.

Two claims from the 200-row run did not survive. "All A" was a property of Apollo-verified GTM engineers, not of the grader; here the mix was 77% A and 12% F. And "the second pass rarely lands" was the endpoint, as the section above now says.

This is what the verifier column is for. Load a list that carries `zb_status`, or any verifier's status column, and every row gets a delta class next to its grade: agree, corrected address, catch-all graded, drop recovered, valid downgraded to D, F on valid, not in graph. The Disagreements tab is the rows worth a human's time. The Verifier vs Moltsets tab is the matrix. Moltsets earns a seat after the verifier, not instead of it. The probe answers whether the mailbox accepts mail. The graph answers whether anyone has used it, and where that person works today.

---

## The Sheet

Eleven tabs when every tier is populated and the list carries a verifier verdict; seven on the 200-row night, because nothing graded C or D and no verifier had run.

- **Dashboard**: graded share, send-ready share, grade distribution, route mix, Apollo still / moved / unknown, first-pass hit rate, what the second pass recovered, records and tokens consumed.
- **Send Ready**: A/B on the company's domain, ranked top 3 per company with persona diversity.
- **Send Low Volume**: C, when there is any.
- **Route - LinkedIn**: the 54 rows a suppress-only tool would have deleted. Connection note first.
- **Review - Hold**: the 6 cross-domain or free-mail rows and the 27 job changes, with an agree/disagree column when two employment sources ran.
- **Suppressed**: D rows, for the sequencer's suppression list. D rows also appear in Route - LinkedIn, on purpose.
- **Disagreements** (when a verifier verdict exists): every row whose delta is not agree, not in graph, or no data, sorted by class then score. The rows worth a human's time.
- **Verifier vs Moltsets** (same condition): the receipts, the verifier-status x Moltsets-outcome matrix, a per-pool table when the list had sending pools, the delta legend with counts, and how to read it.
- **All Contacts**, **Grading Model** (the weights and meanings, so the sheet explains itself), **Moltsets Usage** (your ledger by endpoint).

Grade cells are colored A green, B light green, C amber, D red, F orange, unknown grey. Routes are colored too, and so are delta classes: green for agree and every recovery, amber for review, red for a downgrade, grey for not in graph. Emails and phones are obfuscated unless you build a private copy with `--full-emails`. `--summary-only` builds a sheet with the Dashboard and the Verifier vs Moltsets tab and no contact rows, which is the version you can share. The sheet rebuilds in place by id, so the link never changes.

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

# a list that already carries your verifier's verdict (zb_status / verifier_status column): same command,
# every row gets a delta class, the sheet adds Disagreements + Verifier vs Moltsets
python3 import_graded.py results.csv                          # rows graded elsewhere -> same sheet, no API calls
python3 build_sheet.py --summary-only --share anyone_reader   # a linkable receipt with no contact rows
```

Read the Dashboard back in this order: loaded, graded, send-ready; first-pass hit rate and second-pass recovery; grade distribution; route mix; still / moved; verifier agreement when there is one; what it cost. The misses are receipts. Say "not in the graph", never "invalid".

---

## What I Would Tell Adam

The grade is the product, and the library does not have the piece after it. Twenty-six skills on moltsets.com cover enrichment, prospecting, ad audiences, and visitor identification. None of them turns a D into a LinkedIn task, puts two employment sources side by side, or lays the grades next to the verifier a customer already pays for. That is the skill in this chapter, and the 10,088-row run is its case study: Moltsets next to ZeroBounce, not instead of it.

Four questions came out of that run. Is a split coming inside F between "seen, never engaged" and "never seen", because two very different send decisions hide in one grade. Is `search_business_profile_by_name` the intended second pass for SMB and owner ICPs, because it beat `search_people` 436 to 0 and the docs should lead with it. Is a batch endpoint on the roadmap, because 14,087 sequential calls is 75 minutes. And could name-search results carry a same-company-as-input flag, because 422 cross-domain returns needed a human. The misses are in here too: 10.5% of a list the graph has never seen, a `location` parameter the API ignores, side roles reported as the current company, and a D-versus-F table that deserves to be on every reference page.

Part of the [GTM Coding Agent](https://github.com/shawnla90/gtm-coding-agent). Starter: `starters/moltsets-reachability/`. Skill: `skills/moltsets-reachability/`.
