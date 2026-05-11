# Voice-Drift Analyzer Prompt

A reusable prompt for running drift analysis on a single meeting transcript against your existing voice DNA. Paste this into Claude Code along with your principles file, your example corpus, and the new transcript. Output is a markdown report you save to `voice/drafts/YYYY-MM-DD_<slug>_voice-update.md` for human review.

---

## When to use

- A new meeting transcript has landed and you want to know whether you sounded like yourself
- You want to grow the voice corpus over time without rewriting `core-voice.md` from scratch
- You want a structured audit that flags drift candidates AND signature reinforcements

## What this is NOT

- Not a content generator — it does not write blog posts or LinkedIn posts. Use the `content-repurpose.md` prompt for that. This prompt only analyzes the voice signal.
- Not an auto-applier. The output stages a proposal. You merge.

---

## Inputs the prompt expects

1. **Principles file** — the canonical voice rules (`templates/voice/core-voice.md` + `templates/voice/anti-slop.md`)
2. **Reference corpus** — past transcripts in `examples/voice-dna/` where the voice came through clean
3. **New transcript** — the markdown transcript of the new meeting

Paste all three into the chat in that order, then paste the prompt below.

---

## The prompt

```
You are a voice-drift analyzer.

I am about to give you three things in order:

1. My current voice principles file (rules + anti-slop list)
2. My reference corpus (one or more past transcripts that exemplify my voice)
3. A new meeting transcript to analyze

Your job is to produce a drift report. Not a content draft. Not advice. A structured analysis with five sections.

## Section 1: New Phrasings (drift candidates)

Extract every phrasing from the new transcript that meets ALL of these criteria:
- Recurs three or more times in the transcript (one or two could be transcription noise)
- Does NOT appear in the reference corpus
- Is not a generic English phrase ("you know", "like", "right" are filler, skip them unless they are part of a longer signature pattern)

For each phrasing, output:
- The phrasing itself (in quotes)
- One direct transcript excerpt where it appears (verbatim, in a markdown blockquote)
- Context: what is the speaker actually saying when they use this phrasing? What concept is it attached to?
- Recommendation: "add to corpus", "drop because [reason]", or "edge case — sit on it"

## Section 2: Reinforced Patterns (already in corpus)

Phrasings or cadence patterns that recur in the new transcript AND already exist in the reference corpus. List the top 3-5. Note the count of new occurrences. This is the positive signal — the voice is consistent.

## Section 3: Verbal Tics (strip in writing, do not imitate)

Filler words and phrases that appear frequently in spoken English but should not be carried into written content. List with rough counts. ("Right?", "you know", "long story short", "again", "but again", etc.)

## Section 4: Principles Tension

Anything in the new transcript that contradicts an existing rule in the principles file. If the principles file says "no three-part lists" and the speaker used three-part lists naturally in this conversation, flag it. The resolution is not automatic — it is a decision for the human reviewer.

If no tensions exist, state "No banned phrases detected" and "No new principles changes recommended — drift is additive only".

## Section 5: Suggested Action

One paragraph. Should this transcript be added to the reference corpus? Why or why not? If yes, what mode does it represent (pitch-mode, advisory-mode, collab-mode, casual)?

---

Output format: clean markdown. Use H2 (##) for section headers and H3 (###) for individual phrasings. Use markdown blockquotes for transcript excerpts. Do not use bullet lists for the drift candidates themselves — each phrasing gets a small structured block (phrasing, excerpt, context, recommendation).

Do not generate any content drafts. Do not propose new principles rules unless explicitly recommended in Section 4. Do not auto-apply anything to the principles file.

End with: "Staged for human review. Do not auto-apply to principles.md."
```

---

## What you do with the output

1. Read the report top to bottom.
2. For each Section 1 candidate, decide: merge, drop, or sit on it.
3. Merges go into the reference corpus as a new example file (or as a phrasing line in the principles file, depending on what the candidate is).
4. Section 4 tensions trigger a principles edit only if the tension is real and you want the new rule.
5. Section 5 tells you whether the new transcript itself is corpus-worthy.

This loop runs every meeting. The corpus grows. The principles file stays small. The voice stays consistent at scale.

---

## Reference

- Chapter 09 — Voice DNA & Content (the static profile this prompt audits against)
- Chapter 14 — Voice-Invocation (the full automation that runs this prompt on every transcript)
- `templates/voice/core-voice.md` — the principles file the prompt expects as input #1
- `examples/voice-dna/` — the reference corpus the prompt expects as input #2
