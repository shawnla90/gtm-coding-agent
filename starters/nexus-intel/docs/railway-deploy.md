# Deploy to Railway

Railway is the recommended target. The committed `data/intel.db` plus `better-sqlite3` setup means you deploy by pushing code. No DB migrations, no seed step.

## One-time setup

1. **Install Railway CLI.** `brew install railway` (or `npm i -g @railway/cli`).
2. **Login.** `railway login`.
3. **Create a project.** `railway init` and choose "Empty Project".
4. **Link the repo.** `railway link`.

## Environment variables

Set these in the Railway dashboard (`Variables` tab) or via CLI:

```bash
railway variables set APIFY_TOKEN=<your-token>
railway variables set ANTHROPIC_API_KEY=<your-key>
railway variables set AUTH_USER=<gate-username>
railway variables set AUTH_PASS=<gate-password>
railway variables set INTEL_DB_WRITABLE=0    # read-only in prod
```

`AUTH_USER` plus `AUTH_PASS` enable the basic-auth gate in `src/proxy.ts`. Leave them blank during local dev.

## Deploy

```bash
railway up
```

Railway reads `.railwayignore` (already included), skips `node_modules`, `.env*`, logs, and build artifacts. It runs `npm install && npm run build` and serves the production Next.js app.

The committed `data/intel.db` ships with the deploy. Next 16's `outputFileTracingIncludes` in `next.config.ts` ensures the file is included in the serverless bundle.

## Nightly scrape cron

Scraping requires `apify-cli` plus Python, which don't run inside Railway's web runtime. Two recommended patterns:

**Pattern A: Cron on your own machine (simplest).** Run the scrape pipeline on your dev machine or a dedicated VPS, then `git add data/intel.db && git commit && git push`. Railway redeploys on push. Free, auditable in git history.

**Pattern B: Railway cron worker.** Add a second Railway service with a Python runtime, set a cron schedule, run `scripts/scrape_*.py` followed by a git push. Costs a few dollars a month. Example in `docs/adding-connectors.md`.

## Gotchas

- **Basic auth is the only gate.** If you forget `AUTH_USER` plus `AUTH_PASS`, your dashboard is publicly scrapeable. Set them.
- **SQLite is read-only on Railway.** `INTEL_DB_WRITABLE=0` (the default) makes every SQL write fail loudly. All mutations happen on your local machine, then get committed and pushed.
- **Railway scales down to zero.** Cold starts can be around 3s for a Next app. Not great for public-facing dashboards; fine for an internal intel tool.
- **Log volume.** Turn on `NEXT_TELEMETRY_DISABLED=1` to keep logs clean.

## Swap to Vercel (if you prefer)

Delete `.railwayignore`. Add a `vercel.json`:

```json
{
  "framework": "nextjs",
  "buildCommand": "next build",
  "outputDirectory": ".next"
}
```

`next.config.ts` already configures `outputFileTracingIncludes` for the SQLite file, so Vercel's serverless bundling includes `data/intel.db`. Deploy with `vercel --prod`.
