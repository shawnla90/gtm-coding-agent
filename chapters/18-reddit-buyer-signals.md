# Chapter 18: Reddit Buyer Signals

**This chapter is for founders, GTM engineers, and agency operators who want to turn live Reddit buyer conversations into a source-linked working queue. The goal is not to promise rankings or citations. The goal is to preserve what buyers asked, decide what deserves a human response, and keep the receipts needed to measure what surfaced later.**

---

## TL;DR

- **Start with the source record.** Every Clearbox opportunity carries an `id`, a `kind` (`lead`, `engage`, or `competitor`), and an exact Reddit URL. Downstream tools may add analysis, but they do not rewrite those fields.
- **Work current, relevant conversations.** Recency and relevance keep the queue useful. They do not guarantee moderation safety, ranking, or AI visibility.
- **Use the right analysis layer.** Freckle, Base Loop, Clay, or a local script can score and enrich the queue. Clearbox remains the source classifier.
- **Keep public action human.** Research, classification, report generation, and monitoring can be automated. Posting, voting, DMs, and marking work complete require a human decision.
- **Measure receipts, not hopes.** Search discovery, retrieval visibility, an observed AI answer, an exact citation, engagement, and a business outcome are different events.

---

## The source contract

The most important design decision is small enough to fit in one table:

| Field | Owner | Meaning |
|---|---|---|
| `id` | Clearbox | Stable opportunity identifier |
| `kind` | Clearbox | Source disposition: `lead`, `engage`, or `competitor` |
| `url` | Clearbox | Exact Reddit thread or comment permalink |
| scores, tier, action lane | Analysis layer | Prioritization and operator guidance |
| review status | Human operator | What a named person decided to do |
| evidence receipts | Reporting layer | What was later observed and captured |

This avoids a common failure mode: an enrichment table quietly changes a `lead` into an `engage` row, drops the original URL, and leaves the client with an impressive-looking report that cannot be audited.

If the analysis layer disagrees with the source disposition, preserve both values and flag the conflict for review.

---

## The loop

1. **Pull the inbox.** Read current Clearbox opportunities or import a complete Clearbox export.
2. **Preserve the source.** Keep every original disposition and exact permalink.
3. **Add analysis.** Score priority, extract buyer language, suggest a helpful reply angle, and review public company evidence.
4. **Build the working surface.** Put the queue, decisions, evidence, and attribution states into a stable Sheet.
5. **Explain it.** Use one guided Notion brief as the client-readable source of truth.
6. **Operate with human approval.** A named person reviews each public Reddit action.
7. **Re-run the benchmark.** Capture search, AI-answer, citation, and business-outcome receipts separately.

The portable starter in this repo teaches the lower-level pipeline:

```bash
cd starters/reddit-buyer-signals
bash run.sh --offline
```

The maintained end-to-end client-pack builder and visual demo live in [ClearboxGTM](https://github.com/shawnla90/ClearboxGTM). The [latest ClearboxGTM release](https://github.com/shawnla90/ClearboxGTM/releases/latest) shows the complete API to analysis to eleven-view Sheet to guided Notion workflow.

---

## The Clearbox input path

Clearbox is the source classifier. The portable starter imports a complete opportunity export; the maintained client-pack builder reads the account API. Both paths preserve the same source contract and stop rather than presenting a truncated response as a full account.

### Clearbox opportunity API

For an existing account, use the account-scoped API URL from the Clearbox dashboard:

```bash
export CLEARBOX_ACCOUNT_URL="https://api.clearbox.to/a/YOUR_ACCOUNT_TOKEN"
```

The client-pack builder reads `GET /inbox?status=all` and individual opportunity detail. The account token is part of the URL path, so keep it in the environment. Never put the account URL into a public Sheet, Notion page, screenshot, or repository.

Treat the API as the classification layer:

- `lead`: buying or comparison intent that may justify company-evidence review.
- `engage`: a useful public conversation where a subject-matter expert may help.
- `competitor`: category or alternative evidence worth monitoring.

If an inbox response reports `truncated: true`, stop or label the build partial. Do not present the first returned page as a complete account.

### Complete Clearbox export

The portable starter reads a JSON list or an object containing `opportunities`, `rows`, or `data`:

```bash
cd starters/reddit-buyer-signals
CLEARBOX_EXPORT=/absolute/path/to/clearbox-opportunities.json bash run.sh
```

Each row must include `id`, `kind`, and the exact `url` or `permalink`. The importer rejects missing fields and invalid dispositions. `bash run.sh --offline` uses a synthetic Clearbox export with the same contract.

---

## Add Freckle, Base Loop, or Clay

The analysis backend is replaceable. The output contract is not.

Every backend must retain the Clearbox opportunity ID so its result can join back to the source row. Useful added fields include:

- priority score and A/B/C tier
- action lane and analysis reason
- buyer question and buyer language
- content topic and helpful reply angle
- profile review verdict and enrichment eligibility
- operator notes

Freckle, Base Loop, and Clay are three compatible routes. None of them owns the original disposition or permalink.

For Clay, the table pattern is:

1. Pull `GET /inbox?status=all` through an HTTP source.
2. Spread `opportunities[]` into rows.
3. Keep `id`, `kind`, and `url` unchanged.
4. Route analysis by `kind`.
5. Add the normalized fields above.
6. Sync or export the result for the client-pack builder.

The reporting path can run on a schedule. Reddit actions cannot.

---

## The eleven-view client pack

The focused builder produces one Google Sheet with eleven working views:

1. **Dashboard:** current value, source counts, analysis coverage, offer choice, evidence ladder, and next actions.
2. **Plan Setup:** offer path, payer, and readiness decisions.
3. **Operator Console:** ranked queue plus human review status.
4. **Signals:** original dispositions, timestamps, snippets, and exact permalinks.
5. **Buyer Language:** questions, pains, jobs, outcomes, and objections.
6. **Content Topics:** source-backed themes and helpful reply angles.
7. **Competitor Sentiment:** competitor rows and clearly labeled analysis.
8. **GEO Terms:** buyer questions and separate search, retrieval, AI-answer, and citation fields.
9. **Disclosure Audit:** profile evidence, verdict, and enrichment eligibility.
10. **Research Workflow:** client-safe source and analysis fields.
11. **Action Legend:** the vocabulary behind every state.

The Sheet is the working surface. The Notion brief is the readable source of truth: what was uncovered, where the working data lives, what each view means, what the client must decide, and how success will be measured.

Use stable Sheet and Notion IDs so a refresh updates the same URLs.

---

## GEO and the evidence ladder

A GEO term is a real buyer question worth tracking. The starter's Exa check asks whether the brand appears in an independent retrieval result set for that question.

That result is **retrieval visibility**, not an observed AI answer and not a citation.

```bash
python3 geo.py --brand "Acme PM" --db data/signals.db --out data/geo_terms.json
# GEO terms: 22 · retrieval-checked 8 · brand retrieved 1 · score 12 -> data/geo_terms.json
```

Use this evidence ladder:

1. **Artifact health:** the exact Reddit contribution is live, with permalink, date, author, disclosure, and screenshot.
2. **Search discovery:** a dated query found the thread or exact comment phrase.
3. **Retrieval visibility:** a search API returned the brand or exact artifact.
4. **Observed AI answer:** a captured answer named the brand.
5. **Exact citation:** that answer cited the exact Reddit thread or comment URL.
6. **Business outcome:** a source-linked referral, conversation, opportunity, pipeline event, or revenue event occurred.

Do not promote evidence from one level to another. A search result does not prove an AI citation. A citation does not prove that one comment caused a recommendation. A referral does not prove sourced revenue without the attribution record.

---

## Content and engagement

The content layer starts from real buyer language. It can scaffold a LinkedIn draft, a Reddit draft, and a long-tail article. Structured answers, clear headings, FAQ blocks, and source-backed claims make a page easier to understand and retrieve. They do not guarantee indexing, ranking, recommendation, or citation.

The public Reddit contribution should still be useful if it never mentions the client and is never cited anywhere else.

The automation boundary is simple:

- **Automate:** reading, classification, scoring, drafting, reporting, and monitoring.
- **Human-authorize:** account creation, posting, replies, voting, DMs, and completion state.

No quota, karma threshold, account age, browser profile, VPN, or IP setup guarantees safety. Community rules and transparent identity still govern the work.

---

## Why this belongs in a coding-agent GTM repo

Reddit buyer talk is unstructured. The useful pattern is turning it into small, inspectable records a coding agent can reason over:

- source fields that never change silently
- scripts that each do one job
- visible workflow state
- exact URLs as receipts
- pluggable analysis backends
- human approval where judgment matters

This repository teaches that portable pattern. [ClearboxGTM](https://github.com/shawnla90/ClearboxGTM) is the focused, maintained Reddit-growth implementation with the client-pack builder, agency operations, measurement scorecard, and release-ready visual demo.

---

> **Clearbox** is the source-classification engine behind the focused workflow. See the market at [clearbox.to](https://clearbox.to), then use the public skills to build the operating layer around it.
