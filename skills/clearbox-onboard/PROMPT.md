# Clearbox onboarding prompt

Paste everything below the line into your coding agent (Claude Code, Codex, Cursor, whatever you use). Fill in the bracketed inputs first. It will research your company and write your Clearbox onboarding answers properly.

---

You are helping me fill out the onboarding form at clearbox.to. Clearbox monitors Reddit and scores conversations against what I write in this form, so these answers decide what I get shown every day. The form itself says "Don't rush this one." Do not rush this. Research first, write second.

## My inputs

- My domain: [DOMAIN]
- Optional, use if provided: [PASTE A PRODUCT BRIEF, OR POINT AT MY CODEBASE, OR DESCRIBE THE PRODUCT IN YOUR OWN WORDS]

Anything I supply above tells you what I want to emphasize. It does not count as a source. A claim about my product still needs to exist publicly before it goes in the form.

## Step 1: research, never assume

Do not assume what I sell from my name or my description. Verify it:

- Fetch my homepage, my pricing page, my docs, and my changelog or blog if they exist.
- Web-search "[my product] alternatives" and "[my product] vs" to find who I actually compete with.
- Capture the literal words buyers use for the problem I solve. Those words matter later.

If you cannot browse the web, stop and ask me to paste in my homepage and pricing page text and a list of my competitors.

## Step 2: the one-liner

Write a one-sentence description, 80 characters maximum. Count the characters.

Shape: "X is a [category] for [who]". Example: "HubSpot is a CRM for B2B sales teams". No adjective that does not narrow the category or the buyer. A stranger should know what the product is, and who it is for, from this sentence alone.

## Step 3: the selling points

Write 5 to 8 selling points. Each one must match one of these seven shapes exactly:

1. Unlike [competitor], X does [thing]
2. A unique feature of X is [feature]
3. X replaces [tool]
4. Only X does [thing], by [how]
5. X does [thing] better than [alternative]
6. Where [competitor] does [X], X does [Y]
7. X is the only [category] that does [thing]

Rules:

- Every competitor you name must have come out of Step 1 research, not memory.
- If you say a competitor lacks something, check their site first. That is a claim about them.
- Shapes 4 and 7 claim nobody else does the thing. That is hard to prove and easy to disprove. Use them only when you are confident; otherwise use shape 2, which only claims the feature exists.
- A shape you cannot back with a source gets skipped, not faked. 5 true points beat 8 padded ones.

## Step 4: the fields behind the form

- Keywords: about 10, lowercase, phrased the way buyers type them in Reddit posts. Category terms, pain phrasings, and "[competitor] alternative" forms. Buyer language, not my internal product language.
- Competitor brands: the real competitor names from Step 1, lowercase.
- Own brands: my product name, plus a parent brand if I have one.
- Tracked subreddits: 5 subreddits where my BUYERS post about the problem, not where my peers talk shop. Verify every one exists before suggesting it. Add 5 swap candidates. Never assert a subreddit's rules or size without checking.

## Step 5: output

Give me plain text, no markdown formatting inside the answer blocks, in this order:

1. Name
2. One-liner (with the character count)
3. Selling points (dash list)
4. Keywords
5. Competitor brands
6. Own brands
7. Tracked subreddits + swap candidates
8. Sources: a numbered list with one URL per selling point, so I can check every claim before I paste

Then tell me: "Paste these into the clearbox.to onboarding form, field by field. Read the sources first."
