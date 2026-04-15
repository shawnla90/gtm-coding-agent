# Architecture

Three layers, each independently replaceable.

```
[Apify CLI]  →  [Python scripts]  →  [SQLite]  →  [Next.js + d3-force]
   (scrape)       (orchestrate)       (store)        (render)
                                         ↓
                                  [Claude subprocess]
                                   (analyze + insights)
```

## Where this fits in your stack

This starter is the collector + SQLite half of a bigger stack. It plays nicely with:

- **Cloud master DB (Supabase, Postgres, Neon):** for multi-user access, team dashboards, or historical warehousing. Push SQLite rows into a cloud DB on a cadence.
- **UI / workflow tools (Clay, Airtable, Sheets, Retool):** for enrichment waterfalls, manual review, or a branded interface. Read from Supabase for live state, read from SQLite for diffable snapshots.
- **Rust desktop apps (rusqlite, sqlx):** the exact same `data/intel.db` file, different client.

SQLite is the version-controlled layer. Supabase is the durable multi-user layer. The UI tool is whatever gets the data in front of humans. This starter gives you the scrape-to-SQLite half; wire in the rest per your needs.

## Why each layer

**Apify CLI.** Actors are versioned, cheap, and swappable. No SaaS middleware fee for the core scrape.

**Python scripts.** Plain files you can read, run from cron, pipe into each other. Uses `apify call` via subprocess, normalizes the JSON, inserts into SQLite.

**SQLite.** The whole DB is one file. It goes in git. `data/intel.db` is diffable, forkable, revertable. Run a SQL query from your terminal in 50ms with no network.

**Next.js (SSR, Next 16).** Server Components read directly from better-sqlite3. No API layer. The d3-force graph renders client-side against a JSON payload built server-side.

**Claude as a subprocess.** `scripts/analyze_content.py` spawns the `claude` CLI with `--print` to get the full model in-context without paying per-token round-trips from a hosted API. Results go back into SQLite.

## Data flow walkthrough

1. **Seed.** `scripts/init_db.py` reads `data/schema.sql` and `data/seed-sources.sql` and builds `data/intel.db`. Run once.
2. **Scrape.** `scripts/scrape_linkedin.py` (or `_x.py`, `_reddit.py`) calls an Apify actor via `apify call ...`. Output gets normalized and written into `content_items`.
3. **Analyze.** `scripts/analyze_content.py` pulls every new `content_item`, sends it to Claude with the signal taxonomy prompt, parses the JSON response, writes to `signals` and `topics`.
4. **Score.** `scripts/score_icp.py` rates each engager on the 4-dim ICP model, writes to `icp_scores`.
5. **Decay.** `scripts/decay_signals.py` applies time-based priority decay using rules in `scripts/_decay.py`.
6. **Insights.** `scripts/generate_insights.py` picks the top-N signals by priority, asks Claude to write an outreach brief, writes to `insights`.
7. **Render.** Next.js reads SQLite on every request (it is fast, local), builds the graph payload, renders.

## Schema (abridged)

```
sources         competitors, thought leaders, communities you track
content_items   every post/thread/tweet you scrape
topics          Claude-extracted topic tags per content item
signals         competitive signals keyed to a content item
engagers        people who commented / reacted / replied
icp_scores      per-engager ICP fit ratings
insights        Claude-generated outreach briefs
```

Full schema in `data/schema.sql`.

## Why SQLite, not Supabase

Supabase is a great default. Managed, it scales, auth and RLS. But for this use case:

- The data is competitive intel you own. No multi-tenant requirement.
- The DB size is under 100 MB for most verticals. Tiny on modern disks.
- `git log data/intel.db` as an audit trail is hard to replicate in managed Postgres.
- `git checkout <sha> -- data/intel.db` to time-travel is a superpower.
- Deploying is `git push` plus `railway up`. No migrations dance.

If your DB crosses 500 MB or you need multi-user writes, graduate to Supabase or Postgres. The schema is standard SQL. The port is mechanical.

## Why a graph, not a table

Competitive intel is not flat. A pricing complaint on X from a thought-leader who shares an audience with your top competitor is structurally different from the same complaint on a random blog. Tables flatten that topology. A force-directed graph keeps it visible.

Drag a node to pin it. Hover opens the detail drawer. The layout recomputes as new content lands from your scrape.
