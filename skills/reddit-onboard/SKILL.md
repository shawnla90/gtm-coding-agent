---
name: reddit-onboard
version: 1.0.0
description: Build a personalized Reddit onboarding doc for a new Clearbox signup or client, grounded in their real product data, and push it to Notion. Routes them through the public playbook at shawnos.ai/reddit instead of re-explaining it. Use when the user says "onboard <name> to Reddit", "reddit doc for <name>", or "/reddit-onboard".
---

# reddit-onboard

Turns a new signup into a personalized Notion doc that routes them through the public Reddit playbook.

**The division of labor:** `shawnos.ai/reddit` is the method, public and free. The Notion doc is *their route through it* — what to read first, what their real data says, what applies to their market. Never re-explain the playbook in the doc. Link to it.

## Inputs

A name, email, or company. Everything else comes from your records.

## Before you write a word

**Read `FACTCHECK.md` in this directory.** Every rule in it maps to a claim that shipped once and was false. The short version: every number traces to a query, behavioral claims come from raw analytics events rather than derived columns, a narrow proxy never proves a broad claim, platform mechanics get attributed or cut, and a client doc describes what works instead of grading their setup.

## Steps

### 1. Pull their real record

Query your CRM or signup store for the person: name, email, offer description, tracked keywords, tracked subreddits, tier, signup date, first-result date, activity.

> **Gotcha:** read the primary record, not an enrichment table. Enrichment providers routinely miss small and local operators; a workflow keyed on an enrichment row will report that a real signup does not exist. Read the source table directly.

### 2. Read their event stream before forming any opinion

**Never write about what someone did from a summary row alone.** Pull the raw event stream from your product analytics, ordered by timestamp, and read the whole thing before writing a sentence about their behavior.

You are looking for the moment the product worked for them, and what preceded it. That moment is the opening of the doc.

> One trial user's summary row implied their subreddit setup was wrong. The raw stream showed they had added three subs and gotten their first opportunity **19 minutes later**. The first draft of the doc would have told them their setup was broken half an hour after it produced their first result. Derived columns lie; events do not.

### 3. Suggest rings, never verdicts

Compare what they track against their own offer description. Signups often track **practitioner subs** — rooms where *they* work — which are genuinely useful for reading competitors and saturation. Say that. Then suggest a second ring where their *buyers* talk, framed as an experiment to run:

buyer's trade → the business layer → local (only if geography is a real advantage).

Lift the pain in their own words out of their offer description and point out it is a thing people post, not a thing to write copy about.

**Never assert a sub's rules, size, or gate you have not checked.** Suggest candidates and make them verify. Checking the gate is the skill you're teaching; doing it for them removes the lesson. Never invent names — if you can't verify it, cut it.

### 4. Write the doc

Structure that works: open with their real result (or the fastest path to a first result), then their two rings, then a reading order through the playbook with deep links, then next experiments. Keep it short; the playbook carries the method.

Hard style rules: no em-dashes, no hedge words, no define-by-negation, no invented anecdotes. State claims directly.

### 5. Verify the deep links

The doc deep-links `shawnos.ai/reddit#<anchor>` sections. Verify every anchor against the live page before shipping — section numbering shifts when sections are added.

Anchors: `journey` `account-ramp` `karma-engine` `post-types` `comments` `karma-gating` `link-map` `the-ask` `staying-alive` `ai-citations` `llmo` `delegation` `newsletter`

### 6. Push to Notion

```bash
python3 https://github.com/shawnla90/ClearboxGTM/blob/main/scripts/push_notion.py --file doc.md --title "<Name> · Reddit for <Company>" --parent <page_id>
```

Re-publish without breaking a shared URL:

```bash
python3 https://github.com/shawnla90/ClearboxGTM/blob/main/scripts/push_notion.py --file doc.md --inplace <page_id>
```

Gotchas:
- Token: `NOTION_API_TOKEN` env var (or `~/.env.notion`).
- The integration must be shared into the parent page or it 401s.
- **Share-to-web is a manual UI toggle.** The API can't publish. Flip it yourself.
- Custom markdown: `> 🎯 text` → colored callout, `- [ ]` → checkbox, `::: bookmark <url>` → card.

## Never

- Re-explain the playbook in the doc. Link to it. The page is the method.
- **Tell them their setup is wrong.** Describe what works and what to try next. If their data shows a result, open with the result.
- **Put their event stream in the deliverable.** You will know things from their analytics they would not recognize as their own visible result. Use that to decide what to write; reference only what they'd recognize.
- Ship a doc without reading the raw event stream first (step 2).

## Related

- `FACTCHECK.md` — the gate. Read it first.
- `shawnos.ai/reddit` — the public playbook the doc routes through
- `../clearbox-onboard/` — the offer pack that precedes this (form fields done right)
- `https://github.com/shawnla90/ClearboxGTM/blob/main/scripts/push_notion.py` — the publish mechanic
