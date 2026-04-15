# Nexus Intel, Competitive Recon Starter

A local-first competitive intelligence engine built on SQLite, Apify CLI, Claude as a subprocess, and a d3-force graph. Your intel DB lives in git. Every scrape is a commit. Version control the data, not just the code. Compose it with whatever cloud database (Supabase, Postgres) and UI layer (Clay, Airtable, Sheets, your own app) you already run.

**Part of the [GTM Coding Agent Starter Kit](../../README.md).** Read [Chapter 12](../../chapters/12-competitive-intel-engine.md) for the walkthrough and demo video.

---

## Why this, why now

Most intel stacks have three layers: a cloud database (Supabase, Postgres), a UI or workflow tool (Clay, Airtable, Sheets, or your own app), and an orchestration layer (cron, scripts, AI). The fourth layer that is almost always missing is version control for the data itself. This starter adds that layer.

- **SQLite is committed to git.** `data/intel.db` is a file. Diffable. Forkable. `git log data/intel.db` is your audit trail.
- **Apify CLI + Python + Claude subprocess.** No SaaS middle layer for the core loop. You own the actors, the cadence, the cost.
- **A force-directed graph for intel.** Competitive context is relational. A graph keeps the relationships visible. Tables flatten them.
- **Stack-friendly.** Supabase handles the cloud master DB. Clay handles enrichment workflows. Sheets handles manual review. SQLite-in-git handles the diffable snapshot. They compose.

---

## Quick Start

```bash
# 1. Install JS + Python deps
npm install
pip3 install -r scripts/requirements.txt
npm i -g apify-cli && apify login   # separate

# 2. Env vars (fill in API keys, leave AUTH_USER/AUTH_PASS blank for local)
cp .env.example .env.local

# 3. Build the database
python3 scripts/init_db.py

# 4. Dev server
npm run dev
# → http://localhost:3009
```

The demo DB ships seeded with 17 public B2B sales-intel companies and 16 public thought leaders, so the dashboard renders something the moment you boot it.

---

## What's in here

| Path | Purpose |
|---|---|
| `src/app/page.tsx` | Overview page: hero, KPI strip, momentum chart, recent signals |
| `src/app/signals/` | Filterable signals feed |
| `src/app/nexus/` | The d3-force graph |
| `src/app/leads/` | Cards for engagers that match your ICP filter |
| `src/components/force-nexus.tsx` | The force-directed graph component |
| `src/components/drawers/` | Signal, source, engager detail drawers |
| `src/components/ui/` | shadcn primitives |
| `src/components/unlumen/` | Motion primitives (tilt-card, magnetic-button, animate-count) |
| `src/lib/db.ts` | better-sqlite3 connection and query helpers |
| `data/schema.sql` | sources, content_items, topics, signals, insights, engagers |
| `data/seed-sources.sql` | Public starter seed (swap for your own ICP) |
| `data/intel.db` | The database. Committed to git; Railway reads it at build time |
| `data/icp-profile.json` | Your ICP config (personas, keywords, competitors) |
| `scripts/init_db.py` | Build `data/intel.db` from schema + seed |
| `scripts/scrape_linkedin.py` | Apify `harvestapi` actors for LinkedIn posts |
| `scripts/scrape_x.py` | Apify `apidojo/tweet-scraper` for X |
| `scripts/scrape_reddit.py` | Apify `trudax/reddit-scraper-lite` for threads |
| `scripts/analyze_content.py` | Claude subprocess for topic + signal extraction |
| `scripts/generate_insights.py` | Claude subprocess for outreach brief generation |
| `scripts/score_icp.py` | ICP scoring scaffold (bring your own weights, see `docs/voice-dna.md`) |
| `scripts/_decay.py` | Signal decay scaffold (bring your own half-lives) |
| `src/proxy.ts` | Basic-auth gate for deployed previews (Next 16 `proxy.ts` convention) |

---

## Architecture

```
                     ┌────────────────────────────────┐
                     │   Apify CLI (you own actors)   │
                     └──────────┬─────────────────────┘
                                │ stdout JSON
                                ▼
        ┌────────────────────────────────────────────┐
        │ Python scrapers (scripts/scrape_*.py)      │
        └──────────┬─────────────────────────────────┘
                   │ INSERT
                   ▼
        ┌────────────────────────────────────────────┐
        │ SQLite (data/intel.db, committed to git)   │
        └──────┬─────────────────────────────┬───────┘
               │ better-sqlite3              │ subprocess
               ▼                             ▼
  ┌──────────────────────┐     ┌───────────────────────────┐
  │ Next.js 16 (SSR)     │     │ Claude subprocess         │
  │ - d3-force graph     │     │ - analyze_content.py      │
  │ - signal feed        │     │ - generate_insights.py    │
  │ - lead cards         │     │ → writes back to SQLite    │
  └──────────────────────┘     └───────────────────────────┘
```

More detail in [docs/architecture.md](docs/architecture.md).

---

## Stack

- Next.js 16, React 19, TypeScript
- Tailwind CSS v4 + shadcn/ui
- better-sqlite3 12 for local reads, committed DB
- d3-force, d3-zoom, d3-drag for the graph
- @anthropic-ai/sdk, Claude Opus 4.6 via subprocess
- Apify CLI for scraper orchestration
- Recharts for momentum and topic charts

---

## Make it yours

This is a starter, not a finished product. The intended workflow:

1. **Fork it.** Rename the repo. Change the branding in `src/components/app-sidebar.tsx`.
2. **Replace `data/seed-sources.sql`** with your own competitors, thought leaders, and communities.
3. **Rewrite `data/icp-profile.json`**: personas, keywords, competitor list for your vertical.
4. **Calibrate the scoring.** Fill in `scripts/score_icp.py` and `scripts/_decay.py` with weights and half-lives that fit your signals. See [docs/voice-dna.md](docs/voice-dna.md).
5. **Tune the Claude prompts.** In `scripts/analyze_content.py` and `scripts/generate_insights.py`, replace the default prompts with your own signal taxonomy and voice rules.
6. **Deploy to Railway.** See [docs/railway-deploy.md](docs/railway-deploy.md).
7. **Run `scripts/scrape_*.py` on a cron.** Nightly is fine for most verticals.

---

## Deploy

Railway is the recommended target. The repo ships with `.railwayignore` preconfigured. See [docs/railway-deploy.md](docs/railway-deploy.md).

Vercel also works if you prefer. The `better-sqlite3` plus `outputFileTracingIncludes` setup in `next.config.ts` handles the serverless bundling.

Gate the deployed preview with `AUTH_USER` and `AUTH_PASS` in your env. `src/proxy.ts` enforces basic auth on every request.

---

## License

MIT. Fork it. Clone it. Remix it. Ship something from it.

---

## Contributing

Issues and PRs welcome. The [Chapter 12 walkthrough](../../chapters/12-competitive-intel-engine.md) is the source of truth for architecture decisions.
