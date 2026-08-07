# Changelog

All notable changes to this kit are tracked here. Everything in this repo is code and version-controlled, so every entry is something you can fork and build on. New chapters and starters ship as tagged [Releases](https://github.com/shawnla90/gtm-coding-agent/releases), so watchers and stargazers get notified.

The format follows [Keep a Changelog](https://keepachangelog.com/). Newest first.

## [0.5.0] - 2026-08-06

### Added

- **`skills/` — four installable Claude Code skills, the complete Reddit motion:**
  - `clearbox-onboard` — a website domain in, a researched Clearbox offer pack out: the one-liner, selling points in the form's seven template shapes, keywords, competitors, and verified subreddits, every claim traced to a URL. Ships `PROMPT.md`, a standalone pastable version that runs in any coding agent.
  - `reddit-onboard` — a personalized route through the public playbook ([shawnos.ai/reddit](https://shawnos.ai/reddit)) for a new signup, grounded in their real data, pushed to Notion. Comes with the FACTCHECK gate: every number traces to a query, behavioral claims come from raw events, and a client doc describes what works instead of grading their setup.
  - `reddit-engage` — value-first reply drafting from a scouted queue with a hard approve-each-one human gate. Nothing posts on its own.
  - `reddit-agency` — the win-a-client package: color-coded buyer-signal sheet, pitch deck, and a Notion command center of real, linked, stable docs. Run it for clients; they can run it for theirs.
- **[ClearboxGTM](https://github.com/shawnla90/ClearboxGTM)** — a new sibling repo: the same four skills plus this kit's buyer-signals engine, the orchestration playbooks (Freckle enrichment loop, Deepline trust model, Notion command center, the account-quality benchmark), and generated proof. The how-to-win-on-Reddit repo, Clearbox-branded, built to hand to a client.

### Changed

- README: `skills/` added to the repo anatomy; Powered by Clearbox now links ClearboxGTM.

## [0.4.0] - 2026-08-04

### Added
- **Chapter 20: Podcast to Shorts.** One recording becomes seventeen captioned vertical clips, because the transcript is the interface: with word-level timestamps, "the story about the $10,000 API bill" is a text search rather than a scrub through a timeline. Includes the audio lesson that cost three rebuilds, where a filter-graph master carries a hidden timestamp jump that every player hides and one careless re-encode turns into seconds of silence.
- **`podcast-shorts` starter:** transcribe with word timestamps, anchor each cut on the words it must open and close on, render the captioned overlay, composite in one ffmpeg pass, then a QA gate that compares every delivery against its master on silence regions, audio cross-correlation, packet timing, and duration before anything gets hosted. Stages drafts on TikTok, Instagram Reels, and YouTube Shorts through the Buffer API. `SKILL.md` doubles as an installable Claude Code skill, so you can cut an episode by describing the moment out loud.
- **Chapter 21: Student GTM.** The track record a student builds in one semester with no budget, no title, and no portfolio: the `me/` folder as a knowledge base, the gotchas log as the format that needs no authority, one weekly recording that becomes the long video, the clips, and the voice profile, and the campus network as the first client list. Runnable configuration in `modes/student.md`, which starts where [first-boot](https://github.com/shawnla90/first-boot) ends.
- **`student-gtm` starter:** an interview (`python3 setup.py`) that scaffolds the student's own repo outside this one, with `CLAUDE.md`, a `me/` folder (`profile.md`, `skills.md`, `gaps.md`, `target-roles.md`), `signals/config/`, `voice/core-voice.md`, `clients/`, `portfolio/README.md`, and the first week's project folder carrying its own `gotchas.md`. Ships the weekly build-in-public loop, three post templates, the campus offer and outreach pages, and the subreddit and keyword config pointed at the market that would hire them. No API key, no paid provider, nothing hosted.

### Changed
- README and CLAUDE.md indexes reconciled: 21 chapters, nine starters, five personas, updated learning paths and routers.

## [0.3.0] - 2026-07-23

### Added
- **Chapter 19: Lead Unmasking and the Daily Slack Digest.** The operated-service layer. A disclosure gate that enriches the company (never the person) only when an author self-discloses, then the daily Slack digest of the threads worth working.
- **Reddit intelligence layer** in `starters/reddit-buyer-signals/`:
  - `geo.py` ("what are the GEO terms"): the buyer questions to own, each checked for current answer-engine visibility via a hard-capped Exa pass.
  - `competitor.py` ("competitor analysis"): the competitor narrative read straight from Clearbox's opportunity classification, plus a generated sentiment read and a share-of-voice view.
  - `content.py` ("create content"): scaffold a LinkedIn, Reddit, and long-tail blog pack from one buyer question, with an anti-slop check.
  - `unmask.py` ("unmask the leads"): the disclosure gate then a pluggable enrichment backend (Freckle by default, swap Clay or Apollo) that returns the company, ICP tier, and buying-role contacts.
  - `digest.py` ("slack digest"): the daily digest of engage threads, new leads, and competitor mentions, render-only by default.
- **`market-scoring-sheet` starter:** a CSV to a color-coded, 1-to-5 scored Google Sheet.
- **Clearbox branding and CTA** across the README, the Reddit starter, and Chapters 18 and 19.
- **Release workflow** (`.github/workflows/release-on-chapter.yml`): new chapters and starters draft a GitHub Release automatically, so a drop reaches everyone watching or starring.

### Changed
- **Chapter 18** expands with the GEO, competitor, and content skills and the pull-only Clearbox opportunity API.
- README and CLAUDE.md indexes reconciled: 19 chapters, seven starters, updated learning paths and routers.

## [0.1.0] - 2026-07-21

### Added
- Initial public kit: Chapters 01 to 18, the GTM-OS skeleton, persona modes, templates, prompts, and the signals-dashboard, nexus-intel, crm-automation, hubspot-landing-engine, client-onboarding-miro, and reddit-buyer-signals starters.
