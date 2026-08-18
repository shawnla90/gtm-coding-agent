---
name: reply-engine
version: 1.0.0
description: Batch-draft one suggested Reddit reply template per classified opportunity, hard-gated. Wraps the reddit-buyer-signals starter's replies.py — scaffold builds suggested_replies.json from the classified ops, the agent writes each ≤18-word value-first template, check enforces the word cap and the slop gate, sheet renders a rules-pinned Suggested Replies tab with GO/REVIEW/NO-REPLY on every row, and angles feeds the daily digest. Every reply is a draft the human edits before posting; NO-REPLY rows are logged, never answered. Use when the user types "/reply-engine" or says "draft the suggested replies", "run the reply pass", "build the reply sheet".
---

# reply-engine

One gated, ≤18-word reply template per opportunity, and a recorded reason for every thread you skip.

This is the batch pass. [`../reddit-engage/`](../reddit-engage/) is the interactive mode: full 2–5 sentence comments, approved one by one. This skill runs earlier and wider: every classified op gets either a short template the human edits into a real comment, or a NO-REPLY gate with a note. The skip discipline is half the value. Wraps [`replies.py`](../../starters/reddit-buyer-signals/replies.py) in the reddit-buyer-signals starter: the script scaffolds and checks; the agent writes the words.

## Inputs

- `data/ops_classified.json` — classified opportunities (`op_id`, `lane`, `subreddit`, `summary`, `permalink`)
- Optional: a client sheet id (or `data/sheet_url.txt`) for the Suggested Replies tab
- The client's offer context and voice profile, same as every other drafting surface

## How to run

```bash
cd starters/reddit-buyer-signals
python3 replies.py scaffold --ops data/ops_classified.json --out data/suggested_replies.json
# the agent writes every empty reply slot, then:
python3 replies.py check data/suggested_replies.json --ops data/ops_classified.json
python3 replies.py sheet --ops data/ops_classified.json --replies data/suggested_replies.json --sheet-id <id>
python3 replies.py angles --ops data/ops_classified.json --replies data/suggested_replies.json --out data/engage_angles.json
```

## The 18-word cap (binding)

Target 15–18 words; **18 is the hard limit** (`wc -w` semantics: whitespace-separated words). Longer templates read contrived, and the human is going to edit anyway. Render the count as `<N>/18` next to every draft you present. Check it, don't eyeball it:

```bash
printf '%s' "<reply>" | wc -w
```

`check` enforces the same count and exits nonzero on 19+.

## Reply gates

Deterministic from the action lane; overrides beat the lane. NO-REPLY is a result, not a failure — log it and move on.

| Gate | Lane rule | Note on the row |
|---|---|---|
| **GO** | `engage_now` / `reply_now` | Timely thread. Reply when ready. |
| **REVIEW** | every other lane | Check thread age + sub self-promo rules first. |
| **NO-REPLY** | `competitor_intel` / `competitor_watch` | Log as competitor intel. Do not post. |

`gate_overrides` handles the exceptions the lanes can't see, e.g. a founder self-promoting their own tool sits in an engage lane but gets `["NO-REPLY", "Founder self-promo. Flag for partnership outreach instead."]`.

## Output shape

```json
{
  "rules": "Every reply is a draft template. Nothing posts automatically. All replies go through the account owner personally before posting. Disclose affiliation whenever the product comes up. Never DM. Check subreddit self-promo rules and thread age before posting. Gate: GO = timely, reply when ready. REVIEW = check thread age + sub rules first. NO-REPLY = log as intel, do not post.",
  "replies": {
    "op_101": "Twelve people will outgrow both boards the same way. What breaks first for you: reporting or handoffs?"
  },
  "gate_overrides": {
    "op_207": ["NO-REPLY", "Founder self-promo. Flag for partnership outreach instead."]
  }
}
```

The sheet tab (`Suggested Replies`): frozen 2 rows — row 1 is the rules string pinned above the header, row 2 is the header. Columns: `Op ID | Tier | Lane | Reply Gate | Gate Note | Subreddit | What They Want | Suggested Reply (≤18 words, edit before posting) | Reddit URL`. The gate column is color-coded GO green / REVIEW yellow / NO-REPLY red. The tab is added to the existing client sheet in place; other tabs are never touched.

## Voice rules

1. **Answer the actual ask.** One or two clipped sentences; the first responds to their literal question.
2. **Concrete nouns from the buyer's world.** Their tools, their workflows, their numbers, never category abstractions.
3. **Zero product mentions by default.** Across a whole batch, a mention is the rare exception, and naming the product triggers the disclosure rule.
4. **End with a question back or a first step they can take today.**
5. **Numbers stated plainly.** "Free tier plus two hours of setup beats a paid seat nobody opens." No hedging.
6. **Match the thread's language and register.** A Spanish thread gets a Spanish reply.
7. **No links, no DMs, no CTAs, no emojis, no "great question".**
8. **If it can't fit in 18 words, it's two thoughts. Cut one.**

## Worked examples (fictional)

| Thread (lane) | Gate | Suggested reply | Count |
|---|---|---|---|
| "Asana vs Monday for a 12-person team?" (`engage_now`) | GO | Twelve people will outgrow both boards the same way. What breaks first for you: reporting or handoffs? | 17/18 |
| "How do you keep follow-up from falling through?" (`lead_enrich`) | REVIEW | Assign every follow-up one owner and one date. Exceptions get a weekly fifteen-minute review. Start there. | 16/18 |
| "RivalPM just shipped dashboards, worth switching?" (`competitor_intel`) | NO-REPLY | *nothing drafted; logged as competitor intel* | — |
| "I built a sprint-planning tool for remote teams, feedback welcome" (`engage_now`, overridden) | NO-REPLY | *override note: Founder self-promo. Flag for partnership outreach instead.* | — |

## Rules

1. **Every reply is a draft template.** Nothing posts automatically; the human edits and posts each one personally.
2. **The gates are strong.** A NO-REPLY row never gets a reply drafted, not even a good one. `check` fails a drafted reply on a NO-REPLY op.
3. **Disclose affiliation whenever the product comes up. Never DM.**
4. **REVIEW means work**: check thread age and the sub's self-promo rules before posting, every time.
5. **`check` before ship.** A draft that fails the cap or the slop gate gets rewritten, not trimmed word-by-word into mush.
6. **Overrides are recorded, not improvised.** Every override carries its note in `gate_overrides`.

## Related

- `../../starters/reddit-buyer-signals/replies.py` — the module this wraps: scaffold, check, sheet, angles
- `../reddit-engage/` — the interactive approval loop; expand a GO template into a full comment there
- [`personalization/SKILL.md` in ClearboxGTM](https://github.com/shawnla90/ClearboxGTM/blob/main/skills/personalization/SKILL.md) — the 3-variable model, applied at template length
- `../../starters/reddit-buyer-signals/digest.py` — renders the angles file this skill exports
- [`how-to-win-on-reddit.md` in ClearboxGTM](https://github.com/shawnla90/ClearboxGTM/blob/main/playbooks/how-to-win-on-reddit.md) — why value-first and no-links are non-negotiable
