---
name: clearbox-onboard
version: 1.0.0
description: Turn a website domain into a complete Clearbox offer pack — one-liner, selling points in the form's fixed template shapes, keywords, competitor brands, own brands, and suggested tracked subreddits — grounded in real research and paste-ready for the clearbox.to onboarding form. No API submission; the user pastes. Use when the user says "clearbox onboard <domain>", "/clearbox-onboard", "build a clearbox offer pack for <company>", or "write my clearbox onboarding".
---

# clearbox-onboard

One domain in, a full Clearbox offer pack out, every claim sourced.

The clearbox.to onboarding form asks for a name, a one-liner (80 chars max), and selling points, and warns: "Don't rush this one. Clearbox scores Reddit content against what you write here." This skill is the not-rushing. It researches the company first, then fills the form's exact shapes plus the fields behind the form (keywords, competitors, tracked subreddits). The stakes are structural: your keywords and competitors drive the matching, and the subreddit suggestion pass runs once at onboarding and is never re-run. Write these fields like they are permanent, because they mostly are. Output is pasted by the user into the form; there is no API path today.

## Inputs

A website domain (e.g. `acme.com`); optionally any of: a knowledge brief, a codebase path, or the company's own-words description — whatever is supplied gets read first.

## Before you write a word

Read `FACTCHECK.md` in this directory and hold every output to it. Short version: every selling point traces to a URL, "Unlike X" claims need a source on X too, never assume the category from the name, the user's brief is intent not fact, absence claims ("only X does...") are traps, and no invented subreddit or brand names.

## The standard

The form's own example one-liner is the shape: "HubSpot is a CRM for B2B sales teams." The bar to clear: a stranger reads one sentence and knows what the product is, who uses it, and why it matters. Twenty-five words or fewer usually gets there; 80 characters is the hard limit.

## Steps

### 1. Read what the user gave you

Brief, codebase, own-words description — read it all before researching, so you know the positioning *intent*.

> **Gotcha:** user materials are authoritative on positioning intent, never on public claims. A claim the company makes about itself still needs to exist on their site (or somewhere public) before it enters a scored field. If it exists nowhere public, flag it: "publish this first or it stays out."

### 2. Research the company (never assume)

Fetch their website and web-search them. Confirm what they **actually** sell, who the buyer is, and who they actually compete with. In one reference build, a client looked like an "engines and generators" business from the name and turned out to be an outdoor power equipment dealer; the wrong assumption would have poisoned everything.

- Fetch: homepage, `/pricing`, `/docs`, `/changelog` or `/blog` (whichever exist).
- Search: `"<name> alternatives"`, `"<name> vs <competitor>"`, and the category head terms.
- Capture as you go: what they sell, who buys, competitor names, and the literal words buyers use for the problem — those words become the keywords.

### 3. Draft the one-liner

Hard limit 80 characters. Check it, don't eyeball it:

```bash
printf '%s' "<one-liner>" | wc -c
```

Shape: "X is a [category] for [who]". No adjective that doesn't narrow the category or the buyer.

### 4. Fill the selling-point slots

The form accepts points in seven fixed shapes. Use the shapes verbatim; write 5–8 points:

1. `Unlike [competitor], X does [thing]`
2. `A unique feature of X is [feature]`
3. `X replaces [tool]`
4. `Only X does [thing], by [how]`
5. `X does [thing] better than [alternative]`
6. `Where [competitor] does [X], X does [Y]`
7. `X is the only [category] that does [thing]`

Rules: every competitor named must have come out of step 2. A slot you can't source gets skipped, not faked — slots 4 and 7 assert category-wide absence and are the easiest to falsify (FACTCHECK rule 5: downgrade to slot 2 when unsure). Lead with the differentiation slots (1, 4, 6, 7); feature-breadth slots carry the tail.

### 5. Keywords, competitor brands, own brands

- **keywords** (~10): lowercase, phrased the way buyers type in Reddit posts — category terms, pain phrasings, and `<competitor> alternative` forms.
- **competitorBrands**: lowercase brand tokens from step 2 only.
- **ownBrands**: the product name plus any parent brand.

> **Gotcha:** matching runs on your domain + competitors + keywords. Buyer language beats internal product language every time — "cold email deliverability", not "multi-channel orchestration".

### 6. Suggest tracked subreddits

Five, plus a swap-candidates list of ~5 more. Buyer rooms over practitioner rooms: where the *buyer* complains about the problem, then the business layer around them, local subs only if geography matters.

Never assert a sub's rules, size, or gate you haven't checked, and never invent a sub name — verify each exists (fetch `reddit.com/r/<name>` or search it) or cut it.

> **Gotcha:** this field is the one-shot. The suggestion pass at onboarding never re-runs. This step justifies the whole research pass — do not pad it with plausible-sounding subs.

### 7. Assemble and save the artifact

Copy the structure of `TEMPLATE.md` (this directory) to a per-company folder, e.g.:

```
workspaces/<domain-slug>/offer-pack.md
workspaces/<domain-slug>/clearbox-offer.json
```

The JSON mirrors the offer record behind the form: `name`, `description` (the one-liner and selling points serialized into one string, `"<Name> - <tag>\n\nOne-liner: ...\n\nSelling points:\n- ..."`), `keywords[]`, `competitorBrands[]`, `ownBrands[]`, `trackedSubreddits[]`, `domains[]`. Validate with `jq .`. Keep real client workspaces out of any public repo.

### 8. Hand over the paste block

Run the FACTCHECK "Before paste" checklist. Then give the user the paste blocks as plain text (no markdown emphasis — on macOS, pipe through `pbcopy`) and say where they go: "Paste into the clearbox.to onboarding form, field by field. Read the sources first."

## Never

- Never submit to any API or database on the user's behalf. Paste-only.
- Never invent a subreddit or a competitor brand.
- Never pad the selling points to hit a count; 5 sourced beats 8 with filler.
- Never let a template slot force a false claim; skip the slot instead.
- Style rules for all prose fields: no em-dashes, no hedge words, state claims directly.

## Related

- `FACTCHECK.md` — the gate (this directory)
- `TEMPLATE.md` — the artifact skeleton (this directory)
- `PROMPT.md` — the standalone pastable version of this skill for any coding agent
- `../reddit-onboard/` — what happens after the account exists
- `https://github.com/shawnla90/ClearboxGTM/blob/main/playbooks/how-to-win-on-reddit.md` — the method this feeds
