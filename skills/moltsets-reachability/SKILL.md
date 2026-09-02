---
name: moltsets-reachability
version: 1.1.0
description: Grade every email on a contact list A through F with the Moltsets API, confirm the person is still at the company from the LinkedIn URL, and route the rows a bad grade would normally kill (D never emails but goes to LinkedIn then phone; F and not-found get a second pass by name and company domain before they go to LinkedIn) into a color-coded Google Sheet with a dashboard and your own usage ledger. If the list already carries a verifier's verdict (ZeroBounce, NeverBounce, MillionVerifier), every row also gets a delta class and the sheet adds Disagreements and Verifier vs Moltsets tabs. Wraps the moltsets-reachability starter: init_db.py loads the CSV (verifier column detected by alias), grade.py runs the waterfall with per-row commits and fair-use floor guards, score.py applies title relevance x grade multiplier, build_sheet.py renders eleven tabs, import_graded.py brings rows graded elsewhere, budget.py explains the four metered units with free calls. Use when the user types "/moltsets-reachability" or says "grade this list", "moltsets", "reachability sheet", "route by grade", "which of these emails can I send to", "check if they still work there", "compare with zerobounce", "moltsets next to my verifier".
---

# moltsets-reachability

A bad email grade is a routing decision, not a dead contact.

Relevance, timing, reachability. Title scoring covers relevance. The Apollo employment check covers timing. The Moltsets grade covers reachability, and the route column is what you do when the grade says no. Wraps [`starters/moltsets-reachability/`](../../starters/moltsets-reachability/): the scripts call the APIs and build the sheet; the agent reads the dashboard back to the user and decides what to send. Read [`FACTCHECK.md`](FACTCHECK.md) before writing a single sentence about what a grade means or what a call costs.

## Inputs

- A contact CSV: the short schema (`first_name,last_name,title,company,domain,email,linkedin_url`) or a raw Apollo people export with its original headers
- `MOLTSETS_API_KEY` (env, `.env`, or `SECRETS_DB` vault). `APOLLO_API_KEY` optional, powers `--employment apollo|both`
- `~/.config/gspread/token.json` from `setup_oauth.py`
- Optional: `--exclude <file>` of emails or LinkedIn URLs that must never be graded (people already in your pipeline)
- Optional, no flag: a verifier verdict column on the CSV (`zb_status`, `zerobounce_status`, `verifier_status`, `verification_status`; plus `pool`, `mx_provider`). Detected by alias, normalized to `valid | catch-all | unknown | invalid | do_not_mail | abuse`. Turns on delta classes and the two comparison tabs.
- Optional: a CSV of rows already graded elsewhere for `import_graded.py` (grade, molt_email, still_at_company, zb_status, tier, route, delta_class by alias)

## How to run

```bash
cd starters/moltsets-reachability
python3 budget.py                                    # free: pools, phone tokens, endpoint count. Always first.
python3 init_db.py my_list.csv --exclude pipeline.txt
python3 grade.py --limit 20 --dry-run                # shows what would run, spends nothing
python3 grade.py --second-pass                       # the waterfall (Moltsets employment check)
python3 grade.py --employment both --second-pass     # add Apollo people/match and an agree column
python3 score.py
python3 build_sheet.py                               # prints the sheet URL; emails obfuscated
python3 build_sheet.py --summary-only --share anyone_reader   # Dashboard + Verifier vs Moltsets, no rows: safe to link
REACHABILITY_DB=data/other.db python3 import_graded.py results.csv   # rows graded elsewhere, own database, no API calls
```

`bash run.sh my_list.csv --full` does the same in one line (`--people` swaps the second pass to `search_people` for a comparison). Add `--phones 10` only when the user has said how many mobiles they want to buy.

## The waterfall (binding order)

1. **`reverse_linkedin_lookup` on the LinkedIn URL** (default; `--employment apollo` or `both` to compare). Returns the current company and, when the graph has one, the graded business email. If the current company disagrees with the listed one: `job_changed`, route `resource`, and the stale email is not graded. Timing before reachability. On 200 rows this found 196 profiles and graded 134 addresses where the email-keyed lookup found 70.
2. **`reverse_email_lookup`** on the business email, only when step 1 did not grade it. A 404 means the address is not in the graph. It costs nothing and it is not a verdict.
3. **Second pass** (`--second-pass`) on 404 or F: `search_business_profile_by_name {name: "First Last", company: "<domain>"}`. One flat profile comes back. Accept only a same-domain grade A/B whose name matches; a profile with no confirmed email is F (person known, address unproven); a graded address on another domain is `review_cross_domain` and is never adopted. `search_people` is not a second pass (0 for 181, 0 for 54); `--second-pass-endpoint people` keeps it for comparison only.
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
5. Still / moved / unknown, and the Apollo-vs-Moltsets agree count when both ran. Say plainly which library skill covers each Apollo step you replaced (see FACTCHECK).
6. What it cost: records used against the two pools, phone tokens spent (usually zero).
7. When a verifier verdict exists: the VERIFIER AGREEMENT block, then the Verifier vs Moltsets tab (below).

## Reading the Verifier vs Moltsets tab

Only present when the list carried a verdict. Report the disagreements, because that is where the campaign changes:

1. **Agree** (verifier valid, Moltsets A/B, same address): the core of the send, goes first.
2. **Corrected addresses**: the verifier accepted an address nobody has been seen using; Moltsets prefers a sibling on the same domain. Send to the one with activity, after a re-probe.
3. **Catch-all rows graded A/B**: the verifier could not grade these; observed activity can. Graduating them out of the isolated pool is the user's call. Say so.
4. **Drops recovered / contradictions**: recovered rows come back under a new same-domain address; contradictions (verifier hard-fail, Moltsets A/B on the exact address) are a review pile, never a send pile.
5. **Valid downgraded to D**: pull before the first send. Each one is a bounce, complaint, or trap headed for a warming mailbox.
6. **Job changes**: the verifier passed every one of them, because the mailbox still accepts mail. Hold and re-source.
7. **The misses**: F on a verifier-valid address is unproven, not bad; not in the graph is a coverage gap. On both, the verifier's word stands.

One sentence to keep: Moltsets earns a seat after the verifier, not instead of it. Never suggest replacing the probe.

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
- Don't put a real sheet URL, a real address, or a phone number in content. Screenshots only, or a `--summary-only` sheet with no rows.
- Don't suppress on vendor silence. A 404 or an F on a verifier-valid row keeps the verifier's verdict; it does not overrule it.
- Don't send to a corrected or recovered address without re-probing it. Those addresses have never been SMTP-checked.
- Don't use `search_people` as the second pass and call the silence a coverage fact.
- Don't send anything. This skill grades and routes. Sending is a separate, human-authorized step.

## Related

- `../../starters/moltsets-reachability/` — the scripts this wraps
- `../../starters/apollo-prospecting/` — the title weights and the sheet engine this reuses
- `../../chapters/23-reachability-grading.md` — the build, the numbers, and why the route column exists
- [Moltsets email risk scores](https://developer.moltsets.com/moltsets-data/email-risk-scores)
- [Moltsets skills library](https://moltsets.com/library) — the 26 upstream Claude skills this one sits beside
