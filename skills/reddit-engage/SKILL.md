---
name: reddit-engage
version: 1.0.0
description: Draft and approve Reddit comments from scouted opportunities with a hard human-in-the-loop gate. Reads an opportunity queue (a Clearbox inbox export or your own scout output), drafts voice-matched comments that add real value, and collects approve/edit/reject decisions one by one. Nothing posts without explicit approval. Use when the user types "/reddit-engage" or says "draft Reddit replies", "engage on Reddit".
---

# reddit-engage

Draft voice-matched Reddit comments from scouted opportunities, get approval, then (and only then) post.

## The queue

Input is a queue of scouted opportunities — a Clearbox opportunity inbox export, or the output of your own scout script. Each item carries: subreddit, post title, URL, why it surfaced, and a score. Track status per item: `scouted → drafted → approved | rejected → posted`.

Count and report the queue state before drafting anything. If nothing is scouted, say so and stop.

## Voice rules (what keeps an account alive)

- Write like a builder sharing what they learned, not a marketer promoting.
- Casual, direct, no corporate speak. No em-dashes as filler.
- Self-deprecating humor is fine; "as an expert" framing is not.
- No emojis unless the sub's culture uses them heavily.
- **No hard CTAs and no links to your stuff in comments.** The profile bio does that work.
- Match the energy of the thread: technical threads get technical replies.
- Reference your real experience, not your brand. Share what happened, never drop the product name unprompted.

## Steps

1. **Load the queue** and show the counts by status.
2. **Present each opportunity**: subreddit, title, score, why it matched, URL.
3. **Draft a comment per item.** Read the post first. The reply must add genuine value on its own: a tip, a "here's what worked for me", a relevant experience. 2–5 sentences for comments; longer only if the post warrants depth. If you can't draft something genuine, skip it and say why.
4. **Collect decisions one at a time**: approve / edit (user supplies the text) / reject (record the reason). **Save the queue after every decision**, not at the end — progress is never lost.
5. **Summarize**: approved / rejected / skipped, and what happens next.

## Rules

1. **Human-in-the-loop always** — nothing posts without explicit per-item approval.
2. **Save after each decision** — write the queue incrementally.
3. **Voice compliance** — run every draft through the slop filter: no "game-changer", "revolutionize", "unlock", "level up", "deep dive".
4. **No self-promotion in comments** — share experiences, not links.
5. **Skip gracefully** — 3 good comments beat 10 mid ones. If a post doesn't warrant a genuine reply, skip.
6. **Read the room** — contentious threads or threads outside your real expertise get skipped.

## Related

- `https://github.com/shawnla90/ClearboxGTM/blob/main/playbooks/how-to-win-on-reddit.md` — why the no-links, value-first rules exist
- `../../starters/reddit-buyer-signals/` — the scout/score pipeline that fills the queue
- `../../starters/reddit-buyer-signals/content.py` — batch draft generation the approval loop can start from
