# Fact-check gate

Run before anything ships to a website, Notion, or a client. Written after an audit found seven claims on a live page that the author's own database contradicted, and after a client doc nearly told someone their setup was wrong when the raw events said the opposite.

The failure was never carelessness about a single number. It was one habit: **asserting a conclusion from a proxy instead of checking the source.**

## The five rules

### 1. Every number traces to a query
Paste the query and its result next to the number. A number typed from memory, from a screenshot, or from an older draft is a number that has already drifted.

**If a database knows a number, generate it — don't type it.** In the audit that produced this rule, everything derived from a generated stats file was correct, and every hand-typed stat was wrong — drifted 2-5x in *both* directions. Two were overstated, which a monotonic counter makes impossible to defend. The fix was structural (a script emits the numbers; the page renders from its output), not editorial.

Corollary: make the wrong thing untypeable. If a metric cannot exist (Reddit does not report comment views), give it no field in your data model.

### 2. Behavioral claims come from raw events, not derived columns
Never infer what a person did from an aggregate. A derived column that looks like a timeline can be a cumulative, alphabetized set. Reading order into it produces a confident, wrong diagnosis of a live user. Read the whole event stream before writing a sentence about what someone did.

### 3. A narrow proxy never proves a broad claim
A search for one string returning zero proves that string is absent. It does not prove "zero mentions." Before asserting a category is absent, enumerate what the category actually includes. This exact substitution has shipped to production as a page's central integrity claim, and it was disprovable in 30 seconds of scrolling.

### 4. Platform mechanics get attributed or cut
Anything about how Reddit (or any third party) works internally is unverifiable unless they documented it. Publish it as your experience, or cut it.

**Your own prior writing is not a source for your claims.** A memory file, an old newsletter, and the page all saying the same thing is one assertion, cited three times. Watch for a joke laundered into a mechanism, for the page refuting itself, and for a runbook for something never actually done.

### 5. First-person claims need explicit sign-off
Anything only the operator can attest to ("never been banned", "I've seen it cited in AI answers") gets confirmed by them before publish, not assumed. Ask directly. The true number is usually the better story anyway.

## Client-doc specifics

- **Describe what works. Never render a verdict on their setup.** Best practices framed as next experiments, not corrections. If their data shows a result, open with the result.
- **Do not put surveillance in a deliverable.** Use what you know from their events to decide what to write. Never reference anything they would not recognize as their own visible result.
- **Never assert a subreddit's rules, size, or gate you have not checked.** Suggest candidates and let them verify. Checking the gate is the skill being taught.
- Style: no em-dashes, no hedges, no define-by-negation. State the claim directly.

## Before publish

- [ ] Every number has a query pasted beside it
- [ ] No number typed from a screenshot
- [ ] Behavioral claims traced to raw events
- [ ] No narrow-proxy-to-broad-claim substitutions
- [ ] Platform mechanics attributed or cut
- [ ] First-person claims signed off by the person
- [ ] Client docs: zero verdicts, zero surveillance, zero unverified sub rules
- [ ] Re-run this audit against the *rebuilt* artifact. The gate applies to the fix too.
