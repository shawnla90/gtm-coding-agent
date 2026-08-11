# Chapter 19: Company Evidence, Client Packs, and the Daily Digest

**This chapter is for the operator turning Chapter 18's classified Reddit opportunities into client work. It covers the company-evidence gate, pluggable enrichment, stable Sheet and Notion delivery, multi-account ownership, measurement, and a daily digest. The goal is not to identify anonymous people. The goal is to review company evidence without guessing and give a named human a source-linked queue.**

---

## TL;DR

- **Enrich the company, never the person.** Reddit is pseudonymous. Do not de-anonymize users.
- **Direct disclosure is narrow.** Only an exact company domain published on the author's own Reddit profile can become automatically enrichment-eligible.
- **Candidates stay candidates.** Search results, thread domains, social links, and brand-like handles require human review.
- **Errors are not absence.** A blocked or failed lookup is `lookup_error`, not `no_public_evidence`.
- **Delivery has two surfaces.** The Sheet is the working queue. One guided Notion brief explains the value, views, choices, workflow, and measurement.
- **Digest safely.** Rendering and scheduling a Slack digest can be automated. Public Reddit action and opportunity completion remain human-authorized.

---

## Four verdicts, not one boolean

The starter now returns an evidence-bearing review state:

| Verdict | Meaning | Enrichment state |
|---|---|---|
| `direct_disclosure` | Exact company domain on the author's own Reddit profile | `eligible_direct_disclosure` |
| `plausible_candidate` | Search, thread, social, or handle evidence needs review | `manual_review` |
| `no_public_evidence` | A direct source was checked successfully and no company evidence was found | `not_eligible` |
| `lookup_error` | The check could not complete | `not_eligible`, retry later |

This distinction prevents two bad outcomes:

1. enriching a company because its URL happened to appear in a comparison thread; and
2. treating a blocked lookup as proof that no public evidence exists.

---

## The gate in `unmask.py`

The gate checks evidence in this order:

1. **Reddit profile:** an exact company domain in the profile bio can qualify as direct self-disclosure.
2. **Web search:** Exa or DuckDuckGo may find a possible company or professional profile. That is a candidate only.
3. **Thread domain:** a company URL in the conversation is a candidate only. It does not prove the author owns or works for that company.
4. **Brand-like handle:** a username pattern is a candidate only.

Run the gate without enrichment first:

```bash
cd starters/reddit-buyer-signals

# collect candidates without external enrichment
python3 unmask.py --ops data/ops_classified.json --out data/unmasked.json

# add Reddit-profile and web-search evidence
python3 unmask.py --ops data/ops_classified.json --profile --out data/unmasked.json

# enrich only direct profile disclosures
python3 unmask.py --ops data/ops_classified.json --profile --enrich --out data/unmasked.json
```

Every row keeps:

- Clearbox opportunity ID and disposition
- exact Reddit permalink
- author and source excerpt
- review verdict
- enrichment eligibility
- candidate and verified domains in separate fields
- evidence URLs and lookup status

The release includes tests proving that search hits and thread domains cannot enter automatic enrichment.

---

## Pluggable enrichment

The default seam can invoke a saved Freckle workflow, but no private workflow ID or organization is baked into the public starter.

```bash
export FRECKLE_WORKFLOW_ID="YOUR_SAVED_WORKFLOW_ID"
export FRECKLE_ORG_ID="YOUR_ORG_SLUG"
```

Replace `enrich_domain()` when the operator uses Clay, Base Loop, Deepline, Apollo, or another company-enrichment system. The gate does not change when the backend changes.

The contract is:

```text
direct Reddit-profile disclosure
  -> exact domain + evidence URL
  -> company enrichment
  -> analysis and operator context

candidate evidence
  -> human review
  -> no automatic enrichment
```

Do not enrich a person because a search engine linked a pseudonymous username to a plausible professional profile. Search is a lead for review, not proof.

---

## Build the client delivery layer

The expanded [`reddit-agency` skill](../skills/reddit-agency/SKILL.md) mirrors the current operating contract from ClearboxGTM. It covers:

- the eleven-view Google Sheet
- one guided Notion value brief
- Plan Setup for the current offer or a separate client offer
- Freckle, Base Loop, and Clay analysis paths
- multi-account ownership and disclosure
- AI visibility and business-outcome receipts
- stable report automation

The maintained executable builder lives in [ClearboxGTM](https://github.com/shawnla90/ClearboxGTM). Its [latest release](https://github.com/shawnla90/ClearboxGTM/releases/latest) includes the current dashboard, live synthetic Sheet and Notion demo, GIF walkthrough, source, fixtures, tests, and verification gate.

The client-facing relationship is simple:

- **Sheet:** the ranked working queue and evidence ledger.
- **Notion:** the readable source of truth explaining what was found, where the value is, what each view means, how the workflow runs, what choices remain, and how success will be measured.
- **Message:** a short TLDR with the value, recommended next step, and the two stable links.

Do not send a private processing workspace to the client. Freckle, Base Loop, and Clay are analysis layers behind the delivery, not the client-facing product.

---

## Multi-account and multi-offer operations

Keep six records separate:

1. Clearbox account
2. client offer
3. plan
4. public Reddit identity
5. named human operator
6. payer decision

One client or genuinely separate service line should have one isolated offer. Plan Setup may explain that a separate client offer can be added and the client can pay for it. Do not expose provider-specific billing mechanics or admin controls in client copy.

The operated agency offering and multi-offer enablement currently require contacting Clearbox at **partners@clearbox.to**. The skills, attribution model, and Freckle/Base Loop/Clay methods are public.

For Reddit accounts:

- the client controls recovery and 2FA
- the public identity and material connection are clear
- the operator is named
- managed accounts do not coordinate votes or enter a thread to support one another
- a browser profile is operational hygiene, not proof of technical separation
- a VPN, proxy, dedicated IP, account age, or karma number is not a safety guarantee

Read the full [`MULTI-ACCOUNT-OPERATIONS.md`](../skills/reddit-agency/MULTI-ACCOUNT-OPERATIONS.md) before designing access or publishing responsibilities.

---

## The daily Slack digest

`digest.py` turns the current queue into a human-readable daily handoff:

- engage opportunities with source link and draft angle
- lead opportunities with company-evidence state
- competitor opportunities worth monitoring
- exact permalinks and priority

Render first:

```bash
python3 digest.py --ops data/ops_classified.json --render-only
```

The scheduling boundary matters:

- the queue pull, analysis merge, Sheet rebuild, Notion refresh, and digest render may be scheduled
- Slack delivery may be scheduled when the correct client webhook and approval are configured
- Reddit publishing, voting, DMs, and completion remain human-authorized

One client should have one account token, one private workspace, one Sheet, one Notion page, and one destination channel. Never mix records across clients.

---

## Measure the full evidence ladder

Use one benchmark row per buyer question:

```text
buyer question | Reddit artifact | search discovery | retrieval visibility | observed AI answer | exact citation | business outcome
```

Examples of distinct receipts:

- exact Reddit comment permalink still live at day 30
- dated Google query finding the thread
- Exa retrieving the brand or exact artifact
- captured ChatGPT, Claude, Perplexity, or Google answer naming the brand
- that answer citing the exact Reddit URL
- a referral visit, qualified conversation, opportunity, pipeline event, or revenue event linked to its source

Never turn `not checked`, `not exposed`, or `no receipt` into zero. Never call an Exa result an AI citation. Never claim one Reddit contribution caused a later recommendation without direct evidence.

Start from [`AI-VISIBILITY-SCORECARD.csv`](../skills/reddit-agency/AI-VISIBILITY-SCORECARD.csv) so benchmark prompts, engines, dates, citations, Reddit artifacts, and business outcomes stay comparable across runs.

---

## Why this belongs in the broader kit

The reusable GTM pattern is bigger than Reddit:

- keep the source system authoritative
- let analysis tools add fields without rewriting the source
- separate candidates, facts, errors, and unknowns
- give operators a stable working surface
- give clients one readable source of truth
- automate reporting, not judgment
- tie outcomes back to exact receipts

This repository teaches that pattern across GTM systems. [ClearboxGTM](https://github.com/shawnla90/ClearboxGTM) is where the complete Reddit-growth implementation continues to evolve.
