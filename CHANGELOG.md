# Changelog

All notable changes to this kit are tracked here. Everything in this repo is code and version-controlled, so every entry is something you can fork and build on. New chapters and starters ship as tagged [Releases](https://github.com/shawnla90/gtm-coding-agent/releases), so watchers and stargazers get notified.

The format follows [Keep a Changelog](https://keepachangelog.com/). Newest first.

## [0.14.0] - 2026-11-05

Cold email replies into HubSpot without a sync vendor, the go-live, a card that replies from the sending mailbox, and a re-find for a retired mailbox that is not a departure. The story is a proptech / multifamily services client on a conference campaign. Portal ids, campaign ids, and prospect addresses in the chapters are placeholders. Chapter numbers start at 26 so Chapter 25 can be the Stream Deck command center (written as Chapter 24 on `chapter-24-stream-deck`) without colliding with Chapter 24, Enrichment on the Go.

### Added

- **Chapter 26: Cold Email Replies into the CRM.** A webhook plus a cron poll. `GET /api/v2/emails` (about 20 requests a minute) and `POST /api/v2/emails/reply` with `eaccount` and `reply_to_uuid`. HubSpot email engagements use `hs_email_direction` `EMAIL` or `INCOMING_EMAIL`, the contact association, and `hs_unique_id` `instantly:<email id>`. A positive reply (`lt_interest_status` 1 or `lead_interested`) opens an unowned deal named `(Prefix) - Person - Company` after the email log returns an id. Meeting Booked, auto-replies, and bounces do not. Pipeline and stage are ids. Test mode and a portal allow flag refuse writes. Plan, apply, undo, read back.
- **Chapter 27: Going Live on the Reply Loop.** Service key and personal access key without a HubSpot seat, chmod 600, non-interactive `hs account auth`, and the limit of a personal access key (it cannot read the app client secret). Env var names, 401 without the secret and 200 with it, one Instantly webhook per event per campaign, old sync webhooks left in place, the hand-logged thread skipped by the same `hs_unique_id`, and a check that no workflow assigns an owner.
- **Chapter 28: Reply from the Sending Mailbox.** Private static HubSpot UI extension on platform 2025.2. The card shows which mailbox will send before the button enables, calls the backend through `permittedUrls.fetch` and a `BACKEND` constant, and the backend verifies the v3 signature and an email allowlist before it replies via Instantly.
- **Chapter 29: Dead Address versus Departed.** A retired mailbox auto-reply, employment sources that still say current, a second Microsoft 365 domain, an initial-plus-last-name pattern, three verifiers with made-up catch-all controls, Moltsets F treated like C, blast radius on the old domain, and a human-gated swap. The later worker may stop, note, re-find, and post a summary. It does not add or send.
- **`skills/instantly-hubspot-replies/`** and **`skills/dead-address-refind/`**.
- **`starters/instantly-hubspot-replies/`**. Pure rules in `reply_loop.py`, copy-in route files, and a minimal `hubspot-card/` project. No network in the tests.
- **Production gotchas on the same loop.** The skill's Build section is the end-to-end recreation. Its Gotchas section is what failed in production: the card's `No Instantly thread` empty state is a 200 with zero messages; deals open only for `lead_interested` / interest status 1 or the card's Open MQL button; a campaign-name guard (`CAMPAIGN_NAME_GUARD`) runs only while `INSTANTLY_REPLY_TEST_MODE` is on; `vercel env pull` is not a source for `HUBSPOT_APP_SECRET`; `GET /api/v2/emails?lead=` needs a User-Agent and you cannot pin a sending mailbox on lead create; a v3 email PATCH drops the old address and the legacy secondary-email PUT puts it back; a retired-mailbox auto-reply can fill Instantly reply status, date, and snippet; writing `auto_reply` / `bounce` / `out_of_office` into a lead-status property can trip a workflow that enrolls on any non-empty value; a lead-status PATCH can return 200 and change nothing, so the blocklist is how you park a lead; the IT admin's service key plus personal access key is enough to upload the card, and Send is an allowlist of the client's users by email domain; every HubSpot write is plan, apply, undo file, read-back, and the first positive reply is by hand. `skills/dead-address-refind/` carries the auto-reply and the two-call swap.

### Changed

- `README.md`, `CLAUDE.md`, and `skills/README.md` index chapters 26 to 29, the two skills, and the starter. The anatomy tree's "through chapter 24" lines are left in place so this branch and the Stream Deck renumber can merge in either order. Chapters 26 to 29 are listed in their own block.

### Verification

- `python3 -m unittest tests/test_reply_loop.py`
- `node --check` on `starters/instantly-hubspot-replies/routes/*.mjs`

## [Unreleased]

### Added

- **nexus-intel LinkedIn provider switch.** `starters/nexus-intel/scripts/scrape_linkedin.py` keeps harvestapi as the default and opts into `johnvc/linkedin-posts-api` when `LINKEDIN_POSTS_PROVIDER=johnvc`. Same `content_items` writes; dry-run prints the planned Actor + payload. Unit tests in `tests/test_nexus_linkedin_provider.py` (no Apify network). Docs: `engine/apify.md`, `starters/nexus-intel/docs/adding-connectors.md`.
- **Chapter 24: Enrichment on the Go.** Hold your own Prospeo key and call the current API (V2) from Claude Code or a Grok agent. Search (`/search-person`) returns a `person_id` and leaves email and mobile masked. Enrich (`/enrich-person`, `/bulk-enrich-person`) reveals a verified email (1 credit per hit) or a verified mobile (10 credits per hit; a miss is not charged). `GET /account-information` is the free balance check. The call waterfall verifies email first, then asks Prospeo for a verified mobile, then a phone-type check, then a do-not-call match on a SHA-256 of the number, and routes `cleared-to-call` or `email-only`.
- **`examples/scripts/prospeo_enrich.py`**, **`examples/scripts/.env.example`**, **`examples/scripts/sample_contacts.csv`**. Dry-run sends nothing. `--limit` defaults to 5. The client reads `X-KEY` from `PROSPEO_API_KEY`, retries `429` from the reset headers, and stops when the daily bucket is empty. Output CSVs are gitignored.
- **`tests/test_prospeo_enrich.py`**. Payload shape, route order, masked numbers, rate-limit retry, and a dry-run that must not touch the network.

### Changed

- `README.md` and `CLAUDE.md` now index 24 chapters, including the learning-path row and the "prospeo" / "enrichment on the go" router.
- Cross-links from Chapters 04, 06, 07, 08, and 23, and a pointer in `examples/scripts/enrich-skeleton.py`.

## [0.13.0] - 2026-11-05

Chapter 25 and a new starter: the Stream Deck+ as a command center for a GTM coding agent. The whole profile is generated from Python instead of dragged together in Elgato's editor, so the deck is a file your agent can edit, preview, and deploy. One key opens Claude Code in the right repo with the right model, effort, session name, and first prompt, with GitHub scoped to that one terminal. The chapter also covers the content kickoff pipeline (Claude drafts, a second model critiques via the clipboard, Codex renders, a human decides), Elgato's MCP server with an open-only page, a usage dial plugin, and the deploy-in-place rule learned by losing two profiles to a backup restore.

This chapter was written as Chapter 24 on `chapter-24-stream-deck` (2026-10-09, commit a516462). Main already shipped Enrichment on the Go as Chapter 24, so this renumber lands it as Chapter 25. Chapters 26 and up stay free for the reply-loop work.

### Added

- **`chapters/25-stream-deck-command-center.md`**: the `.streamDeckProfile` format and a generator with deterministic UUIDs and a dead-key check; real key art from `.app` bundles and favicons; the deploy-in-place rule (never move or delete a live profile folder, swap pages inside the same profile UUID with the app quit); Claude Code command keys (`/compact`, `/effort max`, `/model`, Esc, Shift+Tab); project launcher keys with per-terminal `GH_TOKEN` instead of a global `gh auth switch`; agentic content kickoffs with a human gate; Elgato MCP; a usage dial plugin sketch; gotchas (macOS privacy and `~/Documents`, the MCP Deck UUID changing, synthetic GUI clicks, npm 11 install scripts).
- **`starters/stream-deck-command-center/`**: `profile/build_profile.py` (HOME, CLAUDE, PROJECTS with one folder per project, KICKOFF; `--mcp` for the MCP Deck; device block read live, nothing machine-specific committed), `profile/icons.py` (single, grid, glyph, and back styles with a letter-tile fallback), `profile/preview.py` (contact sheet), `profile/deploy_live.sh` (backup, clean quit, in-place page swap, log check for a restore), `profile/projects.py`, `icons/fetch_icons.sh`, `launchers/claude-project.command` and friends, `kickoffs/` (content-new, content-critique, content-render, content-open), `build_apps.sh`, `config.example.sh`, `projects.example.toml`, `mcp/claude-mcp-config.example.json`.

### Changed

- `README.md` (chapter tree, starters block, What You'll Learn) and `CLAUDE.md` (learning path, ongoing-behavior trigger, reference paths) now index Chapter 25 and the new starter. The "through chapter 24" range line is left as-is so this branch and the chapters 26-29 branch can merge in either order.

### Verification

- `bash -n` / `zsh -n` clean on every launcher, kickoff, and script. From a scratch copy with the example config: `build_apps.sh` built 4 apps, `build_profile.py` wrote a 7-page profile for 3 example projects plus 6 generated wrappers, `build_profile.py --mcp` wrote the MCP Deck profile, `preview.py` rendered the contact sheet. `deploy_live.sh` was not run against a device for this release. Those checks are the author's from 2026-10-09. This renumber re-runs the syntax checks only.

## [0.12.0] - 2026-09-02

The reachability starter learns to sit next to the verifier you already run. If your list carries a ZeroBounce (or NeverBounce, MillionVerifier, Bouncer) verdict, every row now gets a delta class: how Moltsets moved it relative to that verdict. The proving run was a client's 10,088-contact home-services list, already verified and pooled by ZeroBounce: 8,061 profiles returned (79.9%), 7,802 A/B (77.3%), 1,206 F, 1,060 never seen. Where the two agreed on the same address: 6,776 rows. Where they did not: 819 corrected same-domain addresses, 1,380 of 1,739 catch-all rows graded A/B on observed activity, 75 of 725 ZeroBounce drops recovered, 793 job changes, 7 grade D (one marked valid). 9,032 LinkedIn URLs on a list that shipped with none. 14,087 calls, 0 phone tokens, $0 marginal, about 75 minutes. Two corrections to 0.11.0 fall out of it: the grade mix is a property of the ICP (the 200 GTM engineers graded all A; this list graded 77% A with 12% F), and the second pass lands when it is `search_business_profile_by_name` (436 recovered of 2,722; `search_people` went 0 for 181, as it had gone 0 for 54 and 2 for 112 before).

### Added

- **Verifier column.** `init_db.py` detects `verifier_status` / `zb_status` / `zerobounce_status` / `verification_status` (plus `pool` and `mx_provider`) by header alias and normalizes any vendor's vocabulary to `valid | catch-all | unknown | invalid | do_not_mail | abuse` (`lib/reachability.py::norm_verifier_status`). No flag needed.
- **Delta classes.** `lib/reachability.py::delta_class` (pure, 13 classes, `DELTA_LEGEND`): `agree` · `molt_upgrades_catchall` · `molt_recovers_invalid` · `molt_corrects_address` · `molt_contradicts_invalid` · `molt_grades_unknown` · `molt_downgrades_valid` · `confirms_invalid` · `molt_catchall` · `molt_no_data` · `person_confirmed_other_email` · `cross_domain_review` · `not_in_graph`. `grade.py` writes one per row when a verdict exists.
- **Two new tabs in `build_sheet.py`.** *Disagreements*: every row whose delta is not agree, not in graph, or no data, sorted by class then score. *Verifier vs Moltsets*: receipts, the verifier-status x Moltsets-outcome matrix, a per-pool table when the list had sending pools, the delta legend with counts, and how to read it. The Dashboard gains a VERIFIER AGREEMENT block. Eleven tabs when everything is populated.
- **`build_sheet.py --summary-only`**: Dashboard + Verifier vs Moltsets + Grading Model + Usage, no contact rows. With `--share anyone_reader` it is a linkable receipt with no PII.
- **`import_graded.py`**: bring rows graded elsewhere (a campaign script, an older run, a colleague's export) into the starter database by header alias; routing and delta classes are recomputed when missing. `score.py` and `build_sheet.py` run unchanged on them. Nothing calls the API.
- **`REACHABILITY_DB`** environment override on every script, so a second list gets its own database and its own sheet URL file.
- `lib/moltsets_client.py::title_of`; `lib/sheet_engine.py::raw_tab` accepts `row_colors`, `bold_rows`, `cell_colors`.
- 26 new unit tests (`VerifierNormalizeTests`, `DeltaClassTests`, `ProfileDecisionTests`, `ImportGradedTests`): 52 total, no network.

### Changed

- **Second pass endpoint.** `grade.py --second-pass` now calls `search_business_profile_by_name {name, company: DOMAIN}` and decides with `lib/reachability.py::profile_decision` (accept same-domain A/B · risky same-domain · profile without an email · cross-domain review, never adopted · name mismatch · no candidate). `--second-pass-endpoint people` keeps `search_people` for comparison; `run.sh --people` maps to it.
- `sample_contacts.csv` carries a fictional `verifier_status` column so the sample renders the new tabs.
- Chapter 23: new section "The Run at 10,088, Next to a Verifier"; "The Waterfall" and "The Run, Twice" corrected on the second pass; "The Sheet" lists eleven tabs; "What I Would Tell Adam" carries the four new questions. `skills/moltsets-reachability/SKILL.md` and `FACTCHECK.md`, the starter `README.md` and `CLAUDE.md`, and the repo indexes updated to match.

### Verification

- `python3 -m unittest discover -s tests -p "test_moltsets*.py"`: 52 tests OK. `python3 -m compileall starters/moltsets-reachability` clean. `bash -n run.sh` clean.
- Live 2026-09-02: the fictional sample, 25 rows, graded end to end on free 404s (23 `reverse_email_lookup`, 24 `search_business_profile_by_name`, 1 `reverse_linkedin_lookup`, 1 `linkedin_to_best_email`; 0 records, 0 phone tokens). `import_graded.py` on the 10,088-row export reproduced the campaign memo row for row (every delta class, 819 corrections, 793 job changes, 9,032 LinkedIn URLs, all tiers). `build_sheet.py` produced the 11-tab private sheet in 21 s and the 4-tab summary sheet in 7 s.

## [0.11.0] - 2026-09-02

Chapter 23, a sixth skill, and a new starter: email reachability graded A through F by Moltsets, the person confirmed still at the company, and every bad grade routed to another channel instead of deleted. The proving run graded the same 200 Apollo-Verified GTM engineers twice. Keyed on the email: 70 profiles, 60 graded (all A), 60 send-ready, 120 routed to LinkedIn. Keyed on the LinkedIn URL with `reverse_linkedin_lookup`: 196 profiles, 136 graded (135 A, 1 B), 113 send-ready (32 with a corrected same-domain address), 54 routed to LinkedIn, 27 job changes held. Apollo `people/match` ran alongside for the comparison and agreed with Moltsets on employment 181 of 193 times; on this list Apollo was redundant for that step, and the chapter says so.

### Added

- **`chapters/23-reachability-grading.md`** — the grade semantics from the Moltsets docs (A valid, B delivered, C catch-all, D hard invalid, F no data; F is not D), the four metered units (calls, two record pools, internal tokens, phone tokens), the grade-to-route table, the two-key run side by side, and "The Apollo Part, Said Plainly": which library skills overlap the Apollo starter, the 181/193 agreement, and where Apollo still stands alone (the intent-gated company waterfall).
- **`starters/moltsets-reachability/`** — `init_db.py` (short schema or raw Apollo export), `grade.py` (`--employment moltsets|apollo|both`: `reverse_linkedin_lookup` for current company + graded address → `reverse_email_lookup` → second pass `search_people` by name + DOMAIN accepting only same-domain A/B → `linkedin_to_best_email` for LinkedIn-only rows → capped `linkedin_to_mobile_phone`; per-row commits, fair-use floor guard, every call logged), `score.py` (title relevance × grade multiplier, A 1.0 / B 0.85 / C 0.6 / F 0.3 / D 0.15), `build_sheet.py` (Dashboard, Send Ready, Send Low Volume, Route - LinkedIn, Review - Hold, Suppressed, All Contacts, Grading Model, Moltsets Usage; `--redact-names` for public stills), `budget.py` (the four units from three free calls), `lib/moltsets_client.py` (never-raising client, three response shapes normalized, env → `.env` → `SECRETS_DB` vault), `lib/reachability.py` (pure classify/route/score/combine-employment functions), vendored `lib/sheet_engine.py`, fictional `sample_contacts.csv`.
- **`skills/moltsets-reachability/`** — `SKILL.md` (the waterfall order, the grade-to-route table, how to read the dashboard back) and `FACTCHECK.md` (grade semantics, the 25-endpoint catalogue, the metered units, parameter gotchas, the 26-skill library and its overlap with Apollo, dated receipts).
- **`tests/test_moltsets_reachability.py`** — 26 unit tests for classify, second-pass acceptance, employment combination, multipliers, the response-shape parsers, and the budget floors. No network.

### Changed

- `README.md` (chapter tree, skills and starters blocks, What You'll Learn, chapter counts), `CLAUDE.md` (learning path, ongoing-behavior trigger, reference paths), and `skills/README.md` now index 23 chapters, six skills, and the new starter.

### Verification

- `python3 -m unittest discover -s tests -p "test_moltsets*.py"`: 26 tests OK. `python3 -m compileall starters/moltsets-reachability` clean. `bash -n run.sh` clean.
- Live 2026-09-01: `budget.py` against `get_account` / `get_billing` / `get_usage` (plan `subscription_97`, enrich 15,000/5h, search 7,500/5h, phone tokens 29/50). `grade.py --employment apollo --second-pass` then `--employment both --second-pass --redo` on the same 200 rows; enrich `records_remaining_5h` 15,000 → 14,702 across both runs, search 7,500 → 7,483, phone tokens unchanged. `build_sheet.py` produced 7 tabs. Library enumerated at moltsets.com/library: 26 skills. Sheet URLs, database, logs, and CSVs are gitignored.

## [0.10.0] - 2026-08-20

Chapter 22 and its starter: headless LinkedIn outreach from your own account. A three-week campaign against 1,297 GTM engineers — 601 connection requests, 299 accepted (49.8%), 35 replies — where 31 of the 35 replies came from the connection note alone, before any follow-up message existed. The chapter is the build, the full funnel, and the double-send incident that ended the campaign; the starter ships the fix.

### Added

- **`chapters/22-headless-linkedin-outreach.md`** — the build (dedicated Chrome profile, SQLite ledger, launchd timer, read-only reconcile observer), the copy, the verified funnel, and "The Re-Hit That Killed It": a write-after-send race that let a crash re-send a message, invisible to single-value status columns afterward. Frames the ToS/ban risk plainly — own account, own call, not a knock on managed tools.
- **`starters/linkedin-headless-outreach/`** — runnable kit: `build_ledger.py` (CSV → ledger + `attempts` table), `login.js`, `run.js` (connect/messages/auto with **claim-before-click**: rows marked `sending` before the browser acts, stranded for review on crash instead of re-armed, plus date-seeded daily-cap wobble and random wake-up skips so the cadence stops being a metronome), `reconcile.js` (read-only, exact-slug + participant-URL-confirmed reply evidence with SHA-256), `ledger_status.js`, `config.example.json`, and macOS launchd templates.

### Changed

- `README.md` (chapter tree, What You'll Learn table, chapter counts) and `CLAUDE.md` (learning path, ongoing-behavior trigger, reference paths) now index 22 chapters and the new starter.

### Verification

- `node --check` clean on all four scripts; `python3 -m py_compile` clean on `build_ledger.py`; `plutil -lint` clean on both plists; `config.example.json` parses. Every funnel figure re-queried against the live ledger on 2026-08-20.

## [0.9.0] - 2026-08-18

The fifth installable skill: the batch reply pass. One gated, ≤18-word suggested-reply template per classified opportunity — the agent drafts, `replies.py check` enforces the hard cap and the slop gate, the human edits and posts. NO-REPLY rows are logged with a reason, never answered. The maintained version lives in [ClearboxGTM](https://github.com/shawnla90/ClearboxGTM).

### Added

- **`skills/reply-engine/`** — the ≤18-word binding cap (15–18 target, `wc -w` semantics, `<N>/18` rendered per draft), deterministic GO/REVIEW/NO-REPLY gates with per-op overrides, the `suggested_replies.json` contract, the rules-pinned Suggested Replies sheet tab schema, distilled voice rules, and fictional worked examples with word counts, including a NO-REPLY and an override case.
- **`starters/reddit-buyer-signals/replies.py`** — the runnable module: `scaffold` (contract from the classified export), `check` (cap + slop + gate validity, nonzero exit), `sheet` (adds only the Suggested Replies tab to an existing sheet), `angles` (feeds `digest.py`).

### Changed

- `skills/README.md` and the README anatomy now index five skills.

### Verification

- Every worked example verified at ≤18 words with `wc -w`; `replies.py check` run green against the examples; `python3 -m compileall` clean on the starter.

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
