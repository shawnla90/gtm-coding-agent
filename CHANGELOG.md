# Changelog

All notable changes to this kit are tracked here. Everything in this repo is code and version-controlled, so every entry is something you can fork and build on. New chapters and starters ship as tagged [Releases](https://github.com/shawnla90/gtm-coding-agent/releases), so watchers and stargazers get notified.

The format follows [Keep a Changelog](https://keepachangelog.com/). Newest first.

## [0.2.0] - 2026-07-23

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
