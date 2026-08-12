# GTM Coding Agent Starter Kit

**Build your go-to-market engine with coding agents, Python scripts, and structured context.**

Open this repo in [Claude Code](https://claude.ai/code) and type `help me set up`. The AI walks you through building a personalized GTM workspace — ICP, positioning, outbound sequences, content, automation — all from your terminal.

Structured context + coding agents + Python scripts. Build alongside the tools you already use.

---

## New: build the Reddit client pack end to end

<p align="center"><a href="https://github.com/shawnla90/ClearboxGTM/releases/latest"><img src="https://raw.githubusercontent.com/shawnla90/ClearboxGTM/main/assets/gallery/client-pack-tour.gif" alt="ClearboxGTM client value pack: API dispositions to eleven-view Sheet and guided Notion brief" width="100%"></a></p>

Chapters 18 and 19 now teach the current contract: Clearbox owns the source disposition and exact Reddit permalink; Freckle, Base Loop, or Clay may add analysis; the client receives one eleven-view working Sheet and one guided Notion brief; and retrieval, observed AI appearance, exact citation, engagement, and business outcomes remain separate receipts.

This repo carries the broader GTM curriculum and portable starter. The complete maintained Reddit-growth implementation lives in **[ClearboxGTM](https://github.com/shawnla90/ClearboxGTM)**. See the **[latest ClearboxGTM release](https://github.com/shawnla90/ClearboxGTM/releases/latest)** for the live synthetic Sheet and Notion demo, visual walkthrough, agency skill, multi-account guide, attribution scorecard, fixtures, and builder.

---

## Anatomy of This Repo

```
gtm-coding-agent/
│
├── CLAUDE.md                              # interactive onboarding         ← START HERE
├── README.md                              # you are here
│
├── chapters/                              # 21 educational chapters
│   ├── 01-coding-agents-vs-editors.md     #   agents vs cursor vs chatgpt
│   ├── 02-context-engineering.md          #   CLAUDE.md, structured context
│   ├── 03-token-efficiency.md             #   200K context, cost, subagents
│   ├── 04-oauth-cli-apis.md               #   3 ways tools connect
│   ├── 05-automation-agents.md            #   cron, n8n, trigger.dev
│   ├── 06-local-first-gtm.md             #   your mac as a GTM server
│   ├── 07-python-for-gtm.md              #   APIs, CSVs, enrichment
│   ├── 08-tools-ecosystem.md             #   apollo, clay, exa, firecrawl
│   ├── 09-voice-dna-content.md           #   voice extraction, anti-slop
│   ├── 10-terminal-mastery.md            #   tmux, SSH, multiplexing
│   ├── 11-build-your-dashboard.md        #   Next.js + Supabase signals dashboard
│   ├── 12-competitive-intel-engine.md    #   SQLite-in-git + d3-force + Claude subprocess
│   ├── 13-crm-automation-slash-commands.md  #  HubSpot + Salesforce + /stale-opportunities
│   ├── 14-voice-invocation.md           #   transcript → voice-drift + content fan-out to Discord
│   ├── 15-meta-ad-intelligence.md       #   Meta Ad Library scraper + Claude taxonomy + dashboard
│   ├── 16-programmatic-landing-pages-hubspot-cms.md  #  HubSpot CMS Pages API + subagent columns
│   ├── 17-client-onboarding-miro-boards.md  #  Miro onboarding boards + client docs package
│   ├── 18-reddit-buyer-signals.md          #   Reddit buyer signals + GEO/competitor/content
│   ├── 19-lead-unmasking-and-slack-digest.md  #  company-evidence gate + client packs + digest
│   ├── 20-podcast-to-shorts.md             #   one recording → captioned vertical clip drafts
│   └── 21-student-gtm.md                   #   campus network → public GTM track record
│
├── skills/                                # installable Claude Code skills (the Reddit motion)
│   ├── clearbox-onboard/                  #   domain → researched Clearbox offer pack + pastable prompt
│   ├── reddit-onboard/                    #   personalized route through the public playbook → Notion
│   ├── reddit-engage/                     #   value-first replies, approve-each-one human gate
│   └── reddit-agency/                     #   11-view Sheet + guided brief + multi-account scorecard
│
├── starters/                              # runnable starter folders (CLI + data)
│   ├── apollo-prospecting/                #   Apollo waterfall: 5 intent gates → color-coded sheet (v0.8.0)
│   ├── reddit-buyer-signals/              #   Reddit signals + GEO/competitor/unmask/digest (Ch 18-19)
│   ├── hubspot-landing-engine/            #   brief → subagent columns → HubSpot CMS DRAFT pages (Ch 16)
│   ├── market-scoring-sheet/              #   CSV → color-coded 1-5 scored Google Sheet
│   ├── client-onboarding-miro/            #   Miro board templates (Ch 17)
│   ├── podcast-shorts/                    #   recording → word-timed captioned vertical drafts (Ch 20)
│   └── student-gtm/                       #   interview → your own build-in-public repo (Ch 21)
│
├── engine/                                # tool documentation (living, updated regularly)
│   ├── apify.md                           #   Apify CLI: scraping, actors, follower lists
│   ├── apollo.md                          #   Apollo: batch enrichment, job change detection
│   ├── claude-subprocess.md               #   Claude CLI as a subprocess — batch analysis pattern
│   ├── hubspot-cms.md                     #   HubSpot CMS Pages API v3 + HubL templates
│   └── _tool-template.md                  #   template for adding new tools
│
├── gtm-os/                                # operational skeleton
│   ├── CLAUDE.md                          #   GTM-OS operating instructions
│   ├── demand/                            #   ICP, positioning, competitors
│   ├── messaging/                         #   attack angles, value props
│   ├── segments/                          #   target account segments
│   ├── engine/                            #   tool integrations + docs
│   │   └── prompts/                       #   reusable AI prompts
│   ├── campaigns/active/                  #   live campaign tracking
│   ├── content/                           #   content pipeline
│   ├── status.md                          #   current GTM status
│   └── log.md                             #   decision log
│
├── modes/                                 # persona-based starter configs
│   ├── solo-founder.md                    #   one person, full stack GTM
│   ├── agency.md                          #   multiple clients
│   ├── single-client.md                   #   GTM eng at one company
│   └── abm-outbound.md                   #   target account pipeline
│
├── templates/                             # reusable templates
│   ├── claude-md/                         #   3 CLAUDE.md variants
│   ├── voice/                             #   voice DNA, anti-slop rules
│   ├── content/                           #   blog, content drop, SEO brief
│   └── partner/                           #   per-client folder structure
│
├── examples/                              # worked examples (anonymized)
│   ├── voice-dna/                         #   filled-in voice profile
│   ├── icp/                               #   example ICP for B2B SaaS
│   ├── prompts/                           #   qualification, gap analysis
│   └── scripts/                           #   Python enrichment patterns
│
├── prompts/                               # ready-to-use AI prompts
│   ├── icp-builder.md                     #   define ideal customer profile
│   ├── positioning-workshop.md            #   positioning & differentiation
│   ├── competitor-analysis.md             #   competitive landscape
│   ├── signal-mapping.md                  #   buying signals → actions
│   ├── email-sequence.md                  #   outbound email sequences
│   └── content-repurpose.md              #   1 piece → 5 formats
│
├── starters/                              # deployable starter projects
│   ├── signals-dashboard/                 #   Next.js + Supabase signals dashboard (Chapter 11)
│   │   ├── schema/                        #     SQL schemas + seed data
│   │   ├── pipeline/                      #     Python signal scoring pipeline
│   │   └── src/                           #     dashboard app (5 pages, dark theme)
│   ├── nexus-intel/                       #   SQLite-in-git competitive intel engine (Chapter 12)
│   │   ├── src/                           #     Next.js app with d3-force Nexus graph
│   │   ├── scripts/                       #     Apify CLI scrapers + Claude subprocess analyzers
│   │   └── data/                          #     SQLite schema, public seed, committed intel.db
│   └── crm-automation/                    #   HubSpot stale-opportunity engine (Chapter 13)
│       ├── stale_opportunity_check.py     #     surface 60-day deals, re-enrich, write custom props
│       ├── .claude/commands/              #     /stale-opportunities slash command
│       └── README.md                      #     setup + HubSpot custom property schema
│
└── social/                                # launch content
    ├── reddit-post.md
    ├── linkedin-post.md
    └── carousel-slides.md
```

---

## How It All Connects

| | |
|---|---|
| **Interactive Onboarding** | **Educational Chapters** |
| `CLAUDE.md` asks 6 questions, then builds your workspace. Recommends tools, mode, and learning path — all personalized. | 21 chapters from "what is a coding agent" to "decode competitor ad strategy via the public Meta Ad Library." Read in order or jump to what you need. |
| **GTM-OS Skeleton** | **Modes** |
| A working folder structure for ICP, positioning, segments, campaigns, and content. Fork it. Fill it in. Run GTM from it. | 5 personas: solo founder, agency, single-client, ABM outbound, student. Each mode configures the skeleton differently. |
| **Templates** | **Prompts** |
| CLAUDE.md variants, voice DNA, content formats, partner structures. Copy into your projects, fill in the blanks. | 6 battle-tested AI prompts for ICP building, positioning, competitor analysis, signal mapping, email sequences, and content repurposing. |
| **Starter Projects** | |
| Ten forkable starters. **Apollo prospecting** (v0.8.0) grows a seed list through five intent gates, deepest intent first, and ships a color-coded Google Sheet; searches are free, credits only on reveal. **Reddit buyer signals** (Ch 18-19) preserves Clearbox dispositions and exact permalinks, measures Exa retrieval without calling it an AI citation, and enriches only exact company domains self-disclosed on the author's Reddit profile; search, thread, and handle matches stay in manual review. **Signals dashboard** (Ch 11) is Next.js + Supabase with 5 operational pages. **Nexus Intel** (Ch 12) is a Clay-companion intel engine with SQLite-in-git, d3-force graph, Apify CLI scrapers, and Claude subprocess analysis. **CRM Automation** (Ch 13) re-enriches 60-day-old HubSpot deals and writes the verdict back as custom properties. **Podcast to Shorts** (Ch 20) turns one recording into captioned vertical clips staged as drafts, cut against a word-timestamped transcript. **Student GTM** (Ch 21) interviews a student and scaffolds their own repo, weekly recording loop, gotchas log, and campus client offer. Deploy any of them in minutes. | |

---

## Read the Web Guide

Prefer reading to forking? The full playbook is available as a book-style web guide:

**[The GTM Coding Agent Playbook on shawnos.ai](https://shawnos.ai/guide/gtm-coding-agent)**

21 chapters, expanded with narrative, examples, and Shawn's perspective. The web version is for reading cover to cover. This repo is for forking and building.

---

## Powered by Clearbox

🟧 The Reddit buyer-signal engine in this kit (Chapters 18 and 19) runs on **Clearbox**. Clearbox reads what your market is actually asking across Reddit, classifies each thread by buying intent, and hands you the leads, the competitor mentions, and the conversations worth joining. The kit is the open-source how. Clearbox is the engine that makes it live.

The full Reddit motion has its own repo: **[ClearboxGTM](https://github.com/shawnla90/ClearboxGTM)**. It contains the maintained buyer-signal engine, client-pack builder, Freckle/Base Loop/Clay analysis path, public agency skills, multi-account controls, evidence scorecard, generated proof, and the visual client delivery system you can hand to a client or run for your own.

**See your market. Move first.** Start a 7-day free trial at **[clearbox.to](https://clearbox.to)**.

---

## See It In Action

**Chapters 18–19 - Reddit client value pack:**

[![ClearboxGTM client pack walkthrough](https://raw.githubusercontent.com/shawnla90/ClearboxGTM/main/assets/gallery/client-pack-tour-poster.png)](https://github.com/shawnla90/ClearboxGTM/releases/latest)

*Clearbox API dispositions → optional Freckle, Base Loop, or Clay analysis → eleven-view Sheet → guided Notion brief. The demo uses synthetic fixtures.*

**Chapter 11 - Signals Dashboard (Supabase + Recharts):**

https://github.com/user-attachments/assets/295f3b1b-37e1-4686-8de3-9b2b9219c8cb

*The signals dashboard running against a live Supabase database. 5 pages, dark theme, real-time polling.*

**Chapter 12 - Nexus Intel (SQLite + d3-force, 2x speed):**

![Nexus Intel demo](https://raw.githubusercontent.com/shawnla90/gtm-coding-agent/main/assets/videos/nexus-intel-demo-2x.gif)

*The competitive intel engine. Clone, seed, boot, see signals.*

---

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/shawnla90/gtm-coding-agent.git
cd gtm-coding-agent

# 2. Open in Claude Code
claude

# 3. Type this
> help me set up
```

Claude reads the CLAUDE.md, asks you 6 questions about your GTM, then:
- Recommends whether to start with Cursor or Claude Code
- Picks your mode (solo founder, agency, etc.)
- Builds your folder structure
- Copies the right templates
- Gives you a 3-5 chapter learning path

---

## Who This Is For

**You should use this if:**
- You're a founder, GTM engineer, or agency operator
- You want to use coding agents (Claude Code, Cursor, Codex) for GTM — not just chat
- You want to understand what's happening under the hood of your GTM stack
- You want a system you can build on, not just configure

**You probably don't need this if:**
- You have a 50-person marketing team with established tooling
- You're looking for a no-code solution
- You want a pre-built product, not a learning system

---

## The Philosophy

A GTM tool usually sells you a dashboard. This gives you a workspace.

The difference: a workspace is files you control, prompts you can edit, scripts you can modify, and context an AI agent can read. When your ICP, positioning, voice, and tooling all live in structured markdown files, a coding agent becomes your GTM co-pilot.

I still use HubSpot and Instantly. This is not about replacing tools. It's about understanding how things work and being able to build the pieces that don't exist yet. You'll learn how it works, then make it yours.

## This Is a Living Repo

This repo gets updated with real workflows I'm actively using and stress testing. Apify CLI scraping patterns, Apollo batch enrichment, Instagram growth automation, terminal multiplexing setups. If it's in here, I've run it. If it broke, I documented how.

New commits land regularly as I discover better patterns, new CLI tools ship, or existing workflows evolve. The `engine/` folder has detailed tool documentation (Apify, Apollo, and more coming) with working scripts you can run today.

If you learn from this and want to help it grow, star it, fork it, open a PR. This is how we build a GTM coding agents community. Not through courses. Through shared systems that actually work.

## Get notified when new chapters drop

New chapters and starters ship as tagged **[Releases](https://github.com/shawnla90/gtm-coding-agent/releases)**. Because everything here is code and version-controlled, each release is something you can fork and build on the same day. To catch them: **star** the repo (releases from repos you star surface in your GitHub home feed), and **Watch → Custom → Releases** for an email on each drop.

---

## What You'll Learn

| Chapter | You'll Be Able To |
|---------|-------------------|
| 01 - Coding Agents vs Editors | Choose the right AI tool for your GTM workflow |
| 02 - Context Engineering | Structure CLAUDE.md files that make agents 10x more useful |
| 03 - Token Efficiency | Manage context windows without burning money |
| 04 - OAuth, CLI, and APIs | Connect any GTM tool to your agent |
| 05 - Automation Agents | Set up scripts that run your GTM on autopilot |
| 06 - Local-First GTM | Turn your Mac into a GTM server |
| 07 - Python for GTM | Write enrichment scripts, API calls, CSV pipelines |
| 08 - Tools Ecosystem | Evaluate and integrate Apollo, Apify, Clay, Exa, Firecrawl |
| 09 - Voice DNA & Content | Extract your voice, kill slop, create content that sounds like you |
| 10 - Terminal Mastery | tmux, SSH, multiplexing for running multiple agent sessions |
| 11 - Build Your Dashboard | Build and deploy a real-time GTM dashboard with Next.js, Supabase, and signal intelligence |
| 12 - Competitive Intel Engine | Build a Clay-companion intel engine: SQLite-in-git, Apify CLI scrapers, Claude-as-subprocess analysis, d3-force Nexus graph |
| 13 - CRM Automation & Slash Commands | Wire HubSpot and Salesforce to your agent, build `/stale-opportunities`, and mine the nurture graveyard AEs abandoned |
| 14 - Voice-Invocation | Auto-run voice-drift on every meeting transcript, fan out content + signals to typed Discord channels for review |
| 15 - Meta Ad Intelligence | Scrape the Meta Ad Library, classify creatives via Claude subprocess, pair declared strategy with demand signals |
| 16 - Programmatic Landing Pages | Brief + subagent columns + HubSpot CMS Pages API v3. Personalized DRAFT landing pages, one command, controlled list |
| 17 - Client Onboarding Miro Boards | Build a client-visible GTM engine map, docs package, and screenshot QA loop before kickoff |
| 18 - Reddit Buyer Signals | Preserve classified buyer signals and exact permalinks, add Freckle/Base Loop/Clay analysis, build the eleven-view client pack, and measure each evidence level separately |
| 19 - Company Evidence, Client Packs & Digest | Separate direct Reddit-profile disclosure from candidates and lookup errors, enrich only verified companies, then deliver stable client surfaces and the daily queue |
| 20 - Podcast to Shorts | Turn one recording into captioned vertical clips staged as drafts, cut against a word-timestamped transcript |
| 21 - Student GTM | Build a public go-to-market track record in one semester with no budget, no title, and the campus network you already have |

---

## Built With

- [Claude Code](https://claude.ai/code) — AI coding agent (primary)
- [Cursor](https://cursor.com) — AI code editor (recommended for beginners)
- Python 3.10+ — scripting and automation
- Markdown — everything is structured text
- [Next.js](https://nextjs.org) + [React](https://react.dev) — dashboard starters
- [Supabase](https://supabase.com) — Postgres for the signals dashboard
- [better-sqlite3](https://github.com/WiseLibs/better-sqlite3) + [d3-force](https://d3js.org/d3-force) — Nexus Intel starter
- [Apify CLI](https://apify.com) — scraping actors for both starters
- [Recharts](https://recharts.org) + [shadcn/ui](https://ui.shadcn.com) — charts and components

---

## Contributing

This is a living educational repo. If you've built GTM workflows with coding agents and want to contribute:

1. Fork the repo
2. Add your example to `examples/` or your tool doc to `engine/` (anonymize client data)
3. Open a PR with context on what GTM problem it solves
4. Star the repo if it helped you. That's how others find it.

---

## License

MIT — use it, fork it, make it yours.

---

<p align="center">
  <em>Stop renting GTM tools. Start building GTM systems.</em>
  <br/><br/>
  🟧 <strong>Clearbox</strong> &middot; See your market. Move first. &middot; <a href="https://clearbox.to">clearbox.to</a>
</p>
