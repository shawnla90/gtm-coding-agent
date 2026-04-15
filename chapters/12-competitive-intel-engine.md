# Chapter 12: Build Your Competitive Intel Engine with SQLite

**Most intel stacks have three layers: a cloud master database (Supabase, Postgres), a UI or workflow tool (Clay, Airtable, Sheets, or your own app), and an orchestration layer (cron, Python, AI scripts). The missing fourth layer is version control for the data itself. SQLite committed to git is that layer. This starter ships the collector + SQLite + Claude subprocess + graph half of the stack; compose it with whatever cloud DB and UI you already use.**

---

## Why this matters

I've been running five instances of this codebase for most of the year, one per industry. Same engine, different seed, different ICP. What made the pattern worth repeating was not the scraper or the UI.

**My intel DB is a file. It lives in git.**

`git log data/intel.db` shows when every signal landed. `git checkout <sha> -- data/intel.db` time-travels to any prior snapshot. A diff between two commits is a changelog for the data. None of that exists when your intel only lives in a managed Postgres or a vendor dashboard; those are durable but not diffable.

Three other things that matter:

1. **Apify CLI + Python + Claude subprocess.** No SaaS middleware for the loop. You own the scrapers, the cadence, the prompts, and the cost.
2. **A force-directed graph beats a table for intel.** Competitive context is relational. Tables flatten that. A graph keeps it.
3. **This is the public version of what I use daily.** The only things stripped out are my calibrated weights and Claude prompts. That is where your voice lives, and no starter can pick it for you.

---

## See It Running

![Nexus Intel demo walkthrough](https://raw.githubusercontent.com/shawnla90/gtm-coding-agent/main/assets/videos/nexus-intel-demo-2x.gif)

_41 second 2x speed walkthrough. [Download full-quality MP4 with audio](https://github.com/shawnla90/gtm-coding-agent/releases/download/v0.2.0-chapter-12/nexus-intel-demo-2x.mp4) (5.3 MB)._

## The Database Stack

Most people skip one of the four layers below. The power shows up when they compose.

```
┌─ UI / workflow layer ─────────────────────┐
│ Clay  Airtable  Sheets  Retool            │  read, enrich, route, share
│ your own Next.js or desktop app           │
└───────────────────────────────────────────┘
              ↑
┌─ Cloud master DB (multi-user, durable) ───┐
│ Supabase  Postgres  Neon  BigQuery        │  team access, backups, scale
│ Firestore  DynamoDB                       │
└───────────────────────────────────────────┘
              ↑
┌─ Version-controlled local DB ─────────────┐
│ data/intel.db  (SQLite, committed to git) │  diffable, forkable, audit-trailed
│ better-sqlite3 (Node)  rusqlite / sqlx    │
│ (Rust desktop apps)                       │
└───────────────────────────────────────────┘
              ↑
┌─ Collectors / orchestration ──────────────┐
│ Apify CLI actors  Python scripts          │  scrape, normalize, insert
│ Claude subprocess  cron                   │
└───────────────────────────────────────────┘
```

**What each layer is for:**

- **Collectors.** Apify actors and Python scripts pull data from LinkedIn, X, Reddit. Normalize the output. Insert into SQLite.
- **Version-controlled local DB.** SQLite as a single file. Commit it to git. `git log data/intel.db` is the audit trail. `git checkout <sha> -- data/intel.db` time-travels to any prior snapshot. This is the layer most stacks skip.
- **Cloud master DB.** Push the SQLite rows into Supabase or Postgres for multi-user access, team dashboards, and historical warehousing. The cloud DB is durable but not diffable; SQLite gives you the git-like version control.
- **UI / workflow layer.** Clay for enrichment waterfalls. Airtable or Sheets for manual review. Retool or your own Next.js app for a branded dashboard. Read from Supabase for the live view; read from SQLite for the auditable snapshot.

**Why SQLite specifically:**

- One file. `scp` it, email it, commit it. No migrations step.
- `better-sqlite3` reads synchronously from Next.js server components. 50ms queries, no network hop.
- Port to Postgres when you cross 500 MB or need multi-user writes. The schema ports cleanly.
- Rust desktop apps get the same `data/intel.db` via `rusqlite` or `sqlx`. Same data, different client.

**Why not just Supabase for everything?** Managed Postgres is the right default for production. But it does not replace the use case of "my analysis dataset as a diffable file." Use both: Supabase for the warehouse, SQLite in git for the snapshot.

---

## The Architecture

Three layers, each independently replaceable.

```
[Apify CLI]  →  [Python scripts]  →  [SQLite]  →  [Next.js + d3-force]
   (scrape)       (orchestrate)       (store)        (render)
                                         ↓
                                  [Claude subprocess]
                                   (analyze + insights)
```

**Apify CLI.** You call actors with `apify call <actor-id> --input <json>` and they return normalized JSON. No SDK, no API middleware. A CLI that shells out to the Apify platform. You own the cadence and the cost.

**Python scripts.** Read from DB, call scraper, normalize, insert into DB. Plain files. Run from cron. Pipe into each other. `_lib.py` has the shared helpers; `scrape_*.py` are the per-platform connectors.

**SQLite.** `data/intel.db` is one file, committed to git. `better-sqlite3` reads it synchronously in Next.js server components. No API layer, no round-trip, 50ms queries. When your DB crosses 500 MB or you need multi-user writes, port to Postgres. Until then, SQLite is enough.

**Next.js 16 + d3-force.** Server components fetch from SQLite directly, build the graph payload, send it to the browser. `force-nexus.tsx` is the implementation.

**Claude subprocess.** `scripts/analyze_content.py` spawns `claude --print` with a long context payload (full content item, `age_days`, your signal taxonomy) and parses the JSON response. Same thing for `generate_insights.py`. Cheaper than paying per-token on a hosted API when you run large batches.

---

## What Goes in SQLite

```
sources            competitors, thought leaders, subreddits you track
content_items      every post/thread/tweet you scrape
topics             Claude-extracted topic tags per content item
signals            competitive signals keyed to a content item
engagers           people who comment / react / reply
icp_scores         per-engager ICP fit ratings (4-dim)
insights           Claude-generated outreach briefs
```

Full schema in `data/schema.sql`.

## The Nexus Graph

The UI surface at `/nexus` renders sources, signals, and engagers as a force-directed graph. Drag a node to pin it. Hover opens the detail drawer. The layout recomputes as your scrape brings in new content.

`src/components/force-nexus.tsx` is the implementation. d3-force for physics, d3-zoom for panning, d3-drag for pinning, d3-selection for updates. Swap it for a table if you prefer. The data layer does not care.

---

## Setting It Up

```bash
git clone git@github.com:shawnla90/gtm-coding-agent.git
cd gtm-coding-agent/starters/nexus-intel

# 1. Install
npm install
pip3 install -r scripts/requirements.txt
npm i -g apify-cli && apify login

# 2. Env
cp .env.example .env.local
# Fill in APIFY_TOKEN + ANTHROPIC_API_KEY. AUTH_USER/AUTH_PASS blank for local.

# 3. Database
python3 scripts/init_db.py

# 4. Run
npm run dev
# → http://localhost:3009
```

The demo DB ships seeded with 17 public sales-intel companies, 16 public thought leaders, and 8 subreddits so the dashboard renders something the moment you boot it. Swap the seed in `data/seed-sources.sql` for your own ICP when you are ready.

---

## Scraping for the First Time

```bash
python3 scripts/scrape_linkedin.py    # harvestapi actors for LinkedIn posts
python3 scripts/scrape_x.py           # apidojo/tweet-scraper for X
python3 scripts/scrape_reddit.py      # trudax/reddit-scraper-lite for threads
```

Each script reads the relevant `platform` rows from `sources`, calls the Apify actor, normalizes the output, and `INSERT OR IGNORE`s into `content_items` or `reddit_threads`. Idempotent, safe to re-run.

First scrape on 41 sources takes about 10 minutes and costs around $3 in Apify credits. Cron it nightly.

---

## Analyzing + Generating Insights

```bash
python3 scripts/analyze_content.py         # topics + signals
python3 scripts/generate_insights.py       # SDR-ready outreach briefs
python3 scripts/decay_signals.py           # age-based priority decay
python3 scripts/score_icp.py               # engager ICP ratings
```

`analyze_content.py` spawns a Claude subprocess with each untagged content item. The prompt gives Claude the signal taxonomy, the content, and `age_days`. Output is JSON with topics and signals; we write straight to SQLite.

`generate_insights.py` picks the top-N signals by priority, asks Claude to write an outreach brief, and writes to `insights`. Each insight is one ready-to-paste LinkedIn or email opener.

The prompts in these two files are scaffolds. Default taxonomies work. Real calibration is yours. See [`docs/voice-dna.md`](../starters/nexus-intel/docs/voice-dna.md) in the starter for how to tune them.

---

## Deploy

Railway is the recommended target. Push to git, Railway pulls, basic-auth gate via `src/proxy.ts`. Committed `data/intel.db` ships with the deploy; `next.config.ts` handles the serverless bundling so `better-sqlite3` can read it at request time. [`docs/railway-deploy.md`](../starters/nexus-intel/docs/railway-deploy.md) has the step-by-step.

The DB is read-only on Railway (`INTEL_DB_WRITABLE=0`). All writes happen on your local machine. When you want new data on prod, run the scrape locally, commit the updated DB, push.

---

## What This Is Not

- **Not a Clay replacement.** Clay handles enrichment waterfalls, multi-step workflows, and async data orchestration. This handles signal intelligence, graph visualization, and time-decayed insights. Use both.
- **Not a hosted SaaS.** You run it. You own it. The DB is yours.
- **Not finished.** Fifth iteration of the same starter, used daily across five instances. Will keep evolving.

---

## What's Next

Fork it. Seed it with your ICP. Tune the prompts. Ship something from it. If you build something with it, open an issue or DM me. I'm collecting the best forks to feature in Chapter 13.
