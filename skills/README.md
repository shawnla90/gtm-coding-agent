# Skills

Installable Claude Code skills. Drop any directory into `~/.claude/skills/` (or point your agent at it in place) and the skill becomes invocable. Each one is self-contained: the SKILL.md is the instruction set, and sibling files (FACTCHECK gates, templates, pastable prompts) are its working parts.

These five are the portable Reddit motion. The focused implementation lives in [ClearboxGTM](https://github.com/shawnla90/ClearboxGTM), alongside the maintained client-pack builder, orchestration playbooks, multi-account operations, measurement scorecard, visual demo, and proof. Start with the [latest ClearboxGTM release](https://github.com/shawnla90/ClearboxGTM/releases/latest).

| Skill | What it does | Pairs with |
|---|---|---|
| [`clearbox-onboard/`](clearbox-onboard/) | Domain in → researched Clearbox offer pack out: one-liner, selling points in the form's seven template shapes, keywords, competitors, verified subreddits. Ships `PROMPT.md`, a standalone pastable version for any coding agent. | The clearbox.to onboarding form |
| [`reddit-onboard/`](reddit-onboard/) | A personalized route through the public playbook for a new signup, grounded in their real data, pushed to Notion. | [shawnos.ai/reddit](https://shawnos.ai/reddit) |
| [`reddit-engage/`](reddit-engage/) | Value-first Reddit reply drafting with a hard approve-each-one human gate. Nothing posts on its own. | Chapter 18 + the [`reddit-buyer-signals`](../starters/reddit-buyer-signals/) starter |
| [`reddit-agency/`](reddit-agency/) | The agency pack: source-linked eleven-view Sheet, guided Notion brief, Freckle/Base Loop/Clay analysis contract, multi-account setup, offer guidance, and evidence scorecard. | Chapters 18–19 + [ClearboxGTM](https://github.com/shawnla90/ClearboxGTM) |
| [`reply-engine/`](reply-engine/) | The batch reply pass: one gated ≤18-word draft template per classified op, a hard `wc -w`-checked cap, GO/REVIEW/NO-REPLY gates with overrides, and a rules-pinned Suggested Replies sheet tab. Nothing posts automatically. | [`reddit-engage/`](reddit-engage/) + the [`reddit-buyer-signals`](../starters/reddit-buyer-signals/) starter |

The rule all five share: every claim traces to a source, retrieval is not citation, and every public Reddit action is human-authorized.
