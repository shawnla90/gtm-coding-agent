# Skills

Installable Claude Code skills. Drop any directory into `~/.claude/skills/` (or point your agent at it in place) and the skill becomes invocable. Each one is self-contained: the SKILL.md is the instruction set, and sibling files (FACTCHECK gates, templates, pastable prompts) are its working parts.

These four are the Reddit motion, end to end. They also live in [ClearboxGTM](https://github.com/shawnla90/ClearboxGTM), the Clearbox-branded how-to-win-on-Reddit repo, alongside the orchestration playbooks and proof.

| Skill | What it does | Pairs with |
|---|---|---|
| [`clearbox-onboard/`](clearbox-onboard/) | Domain in → researched Clearbox offer pack out: one-liner, selling points in the form's seven template shapes, keywords, competitors, verified subreddits. Ships `PROMPT.md`, a standalone pastable version for any coding agent. | The clearbox.to onboarding form |
| [`reddit-onboard/`](reddit-onboard/) | A personalized route through the public playbook for a new signup, grounded in their real data, pushed to Notion. | [shawnos.ai/reddit](https://shawnos.ai/reddit) |
| [`reddit-engage/`](reddit-engage/) | Value-first Reddit reply drafting with a hard approve-each-one human gate. Nothing posts on its own. | Chapter 18 + the [`reddit-buyer-signals`](../starters/reddit-buyer-signals/) starter |
| [`reddit-agency/`](reddit-agency/) | The win-a-client package: buyer-signal sheet, pitch deck, Notion command center. You run it for clients; they can run it for theirs. | Chapters 18–19 |

The rule all four share: every claim traces to a source, and every send is a human pressing send.
