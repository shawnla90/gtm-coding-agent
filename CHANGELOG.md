# Changelog

All notable changes to this kit are tracked here. Everything in this repo is code and version-controlled, so every entry is something you can fork and build on. New chapters and starters ship as tagged [Releases](https://github.com/shawnla90/gtm-coding-agent/releases), so watchers and stargazers get notified.

The format follows [Keep a Changelog](https://keepachangelog.com/). Newest first.

## [0.8.0] - 2026-08-12

The Apollo starter learns to grow the list itself. `waterfall.py` expands a source list with lookalike companies through gated searches that drain from deepest intent to shallowest — job postings for the pain, fresh funding, tech-stack twins, then plain firmographics — so every company arrives tagged with why it made the list. Apollo does not expose buying intent through the API; the gate tag is the intent layer you build yourself.

### Added

- **`waterfall.py`:** gated lookalike expansion to a target list size. Gates: T0 external evidence (`--clearbox` CSV), T1 hiring-for-the-pain (job titles + posting recency), T2 fresh funding (amount window as a round-stage proxy), T3 tech-stack twins (verified technology UIDs), T4 firmographic fingerprint. Flags: `--target`, `--double` (target = seed-list size), `--seed`, `--dry-run` (per-gate market sizing, writes nothing). Output is `init_db.py`-compatible, so it feeds the existing expand → score → reveal → sheet pipeline directly.
- **`waterfall_config.example.json`:** copy to the gitignored `waterfall_config.json` and tune to your ICP. Optional per-gate `cap` keeps one deep gate from filling the whole list, so the output stays a mix of intent tiers.
- **`search_companies()`** in the starter's Apollo client (`mixed_companies/search` — company search, no credits drawn).
- **Bonus columns:** per-company `intent_strength` (populates when the plan carries intent), six-month headcount growth, and printed revenue land in the output when Apollo returns them.

### Fixed

- **Staffing-agency noise in job-posting gates:** staffing/recruiting firms post roles for their clients and would otherwise flood any hiring gate; they are dropped by NAICS prefix (`5613`, `541612` by default, configurable).

## [0.7.2] - 2026-08-11

The API-key story now goes past "put it in `.env`": the curriculum teaches the local secrets vault — one SQLite database outside every git repository, from which coding agents check keys out into gitignored `.env` files on demand. The Apollo starter demos the pattern live.

### Added

- **Chapter 04 "Level Up: The Local Secrets Vault":** build a `~/.gtm-vault/vault.db` in two minutes — schema, `chmod 600/700` permissions, store/check-out one-liners, why one vault beats `.env` sprawl (single source of truth, disposable runtime copies, queryable inventory), and the honest caveats (plaintext at rest, full-disk encryption as backstop, backups carry a copy, upgrade paths to keychain/SQLCipher/1Password CLI).
- **Apollo starter vault demo:** the starter's agent instructions now treat the API-key step as a teaching moment — show the key is in no repo, list vault key names only, pipe the value silently into `.env`, verify with a boolean + length, smoke-test on the free `organizations/enrich` endpoint. README links the full chapter walkthrough.

### Changed

- **Apollo starter setup:** the agent pulls the key from a local vault when one exists instead of asking the user to paste it.

## [0.7.1] - 2026-08-10

The Reddit curriculum now matches the maintained ClearboxGTM architecture: Clearbox is the only opportunity source, and the portable starter imports a complete classified export while preserving the original disposition and exact permalink.

### Changed

- **Chapter 18 source path:** replaced the parallel keyword baseline with one Clearbox input contract covering both the account API and complete export.
- **Portable starter:** `pull.py` now validates `id`, `kind`, and exact source URL, rejects truncated exports, and uses the bundled synthetic Clearbox export for offline runs.
- **Agency skill:** Freckle, Base Loop, and Clay are explicitly downstream analysis layers; none can replace the Clearbox source record.
- **Student route:** market setup now starts from a researched Clearbox offer and classified export rather than provider credentials and hand-written discovery files.
- **Profile evidence terminology:** the optional Playwright tier is a rendered-profile check, separate from Reddit opportunity collection.

### Removed

- **Legacy Reddit discovery path:** removed the retired source client, provider-key setup, and keyword/subreddit input files from the Reddit starter and curriculum.

### Verification

- Added source-import regression coverage for complete export shapes, truncation refusal, invalid fields, and exact source preservation.

## [0.7.0] - 2026-08-10

Build the Reddit client pack: the broader GTM curriculum now carries the current Clearbox source, analysis, company-evidence, client-delivery, multi-account, and measurement contracts, while routing the complete maintained implementation to [ClearboxGTM v0.10.0](https://github.com/shawnla90/ClearboxGTM/releases/tag/v0.10.0).

### Added

- **Expanded `reddit-agency` skill pack:** the eleven-view Google Sheet, guided Notion value brief, Plan Setup, Freckle/Base Loop/Clay adapter contract, multi-account operations guide, evidence ledger, and reusable AI visibility scorecard now ship with the broader skill library.
- **Visual Reddit-growth entry point:** the README now shows the end-to-end client-pack walkthrough and links directly to the focused ClearboxGTM release, live synthetic demo, builder, and verification assets.
- **Profile-gate regression tests:** direct Reddit-profile disclosure, search-only candidates, thread-domain candidates, no-evidence states, and lookup errors are covered independently.

### Changed

- **Chapters 18 and 19:** replaced ranking and citation promises with the source-to-receipt operating model: Clearbox owns `id`, `kind`, and the exact Reddit URL; analysis tools add fields; public actions stay human-authorized; and retrieval, observed AI appearance, exact citation, engagement, and business outcomes remain separate evidence levels.
- **Reddit starter disclosure gate:** only an exact company domain published on the author's own Reddit profile is automatically enrichment-eligible. Search, thread, social, and brand-handle matches now require manual review, and lookup failures remain distinct from no public evidence.
- **GEO measurement:** Exa output is now labeled `retrieval_visibility`, not AI answer visibility or citation. Environment-based secret loading replaces private workstation assumptions.
- **Repository routing:** README, `CLAUDE.md`, skill discovery, starter docs, and both Reddit chapters now distinguish this repo's portable curriculum from the maintained focused implementation in ClearboxGTM.

## [0.6.0] - 2026-08-10

### Added

- **Profile lookup waterfall (`lib/profile_lookup.py`):** a new disclosure source for the lead-unmasking pipeline. Checks whether a Reddit username's public web presence (profile, search results, social links) discloses a company. Four-tier waterfall: Reddit JSON API (stub for when it returns), Exa search (working, finds company blogs and LinkedIn), DuckDuckGo (free fallback), and Playwright via CDP (connects to an existing Chrome session). Pass `--profile` to `unmask.py` to enable.
- **Security and risk section in Chapter 19:** honest documentation of what is and is not de-anonymization, LinkedIn headless scraping risks (the bot works but violates ToS, here is what reduces risk and what increases it), and a clear line on what you should not do.
- **Updated disclosure flow:** `unmask.py` now supports a three-step gate: in-thread domain scan, profile lookup (opt-in), and brand-handle heuristic. The mermaid diagram and worked examples in Chapter 19 reflect the new flow.

### Changed

- Chapter 19 expanded from 272 to ~400 lines: profile lookup section, security guidance, updated code examples and CLI usage, revised mermaid diagram showing the three-step gate.
- README: Chapter 19 description updated to reflect profile lookup and risk docs.
- CLAUDE.md: routing for "unmask the leads" now mentions `--profile` flag.

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
