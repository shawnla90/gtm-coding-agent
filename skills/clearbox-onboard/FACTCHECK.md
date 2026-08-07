# Fact-check gate

Run before anything is pasted into the clearbox.to form. The form itself says "Don't rush this one. Clearbox scores Reddit content against what you write here." These fields are the scoring substrate: keywords and competitors drive what gets matched, and the subreddit suggestion pass runs once at onboarding and never again. A wrong claim here does not just embarrass, it mis-scores every opportunity the account ever sees.

The failure mode this gate exists for: **asserting a conclusion from a proxy instead of checking the source.**

## The six rules

### 1. Every selling point traces to a URL
Their site, their docs, their changelog, or the competitor's site. The URL goes in the artifact's Sources section, keyed to the point number. A claim from memory, from the user's pitch deck, or from what the category "usually" does is a claim that has already drifted.

### 2. "Unlike [competitor]" claims need a source on the competitor
A statement about what a rival lacks or does differently is a claim about the rival. Check their site or docs before writing it. Your model of the competitor is not a source.

### 3. Never assume the category from the name
A real client looked like an "engines and generators" business from the name. It was an outdoor power equipment dealer. The wrong assumption would have poisoned every downstream deliverable. Fetch the site and web-search before forming any opinion about what the company is.

### 4. The user's brief is intent, not fact
When the company supplies its own brief, codebase, or own-words description, that material is authoritative on *positioning intent* (what they want to emphasize, who they think the buyer is). It is never authoritative on *public claims*. A factual claim they make about themselves still needs to exist somewhere public before it goes into a scored field. If it only exists in their heads, tell them to publish it first or cut it.

### 5. Absence claims are narrow-proxy traps
"Only X does [thing]" and "X is the only [category] that [thing]" assert a category-wide absence. Not finding a counterexample in one search does not prove one. These two slots are the easiest to falsify and the first thing a Reddit commenter will dunk on. When unsure, downgrade to "A unique feature of X is [feature]", which only asserts presence.

### 6. No invented names
Every subreddit verified to exist (fetch `reddit.com/r/<name>` or search it) or cut. Every competitor brand confirmed as a real product in this category or cut. An invented name in the competitor or subreddit fields silently corrupts matching forever.

## Before paste

- [ ] One-liner counted, not eyeballed: `printf '%s' "<line>" | wc -c` returns 80 or less
- [ ] Every selling point matches one of the seven template slots verbatim
- [ ] Every selling point has a Sources line with a URL
- [ ] No "Only X" / "the only [category]" claim that rests on absence-of-evidence
- [ ] Competitor brands are real, lowercase tokens that came out of research
- [ ] All 5 tracked subreddits verified to exist; swap candidates too
- [ ] Prose fields read like a person wrote them: no em-dashes, no hedges, claims stated directly
- [ ] The offer JSON parses (`jq .`)
