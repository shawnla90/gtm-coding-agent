# HubSpot Landing Engine

**Read a content brief. Enrich a target list with Claude subagents. Publish personalized landing pages to HubSpot CMS. One command.**

This is the companion starter to Chapter 16. It deploys the matching half of the engine that Chapter 13 + the April outbound-engine drop already shipped: that one writes enrichment back to the CRM as custom properties. This one turns the same enrichment into linkable HubSpot landing pages.

## What you get

```
brief (HubSpot CMS Blog Post OR local markdown)
   │
   ▼
target list (CSV of accounts, 50-500 rows)
   │
   ▼  ← Claude subagents (one per "column": pain_points, hook_angle,
   │     hero_copy, icp_score, tech_stack). Opus 4.7 by default.
   │
   ▼
generated layoutSections payload, per account
   │
   ▼  ← HubSpot Pages API v3 (POST /cms/v3/pages/landing-pages)
   │
DRAFT landing page in your portal, live URL ready to link
```

Default state is `DRAFT`. Nothing publishes without a flag. You review in HubSpot, then promote.

## Quickstart

```bash
# 1. Clone and enter
cd starters/hubspot-landing-engine

# 2. Install
pip install -r requirements.txt

# 3. Fill .env (HubSpot private app token, optional Anthropic key)
cp .env.example .env
# Open .env, paste your HUBSPOT_PRIVATE_APP_TOKEN (pat-na1-... or pat-na2-...)

# 4. Dry-run the pipeline against the example brief + 3 sample accounts
python scripts/pipeline.py --step all --limit 3 --dry-run

# 5. Real run, draft state
python scripts/pipeline.py --step all --limit 3 --state DRAFT
```

When step 5 finishes, three DRAFT landing pages are visible in your HubSpot portal under Marketing → Landing Pages. Each one references the account by name, mirrors a pain point pulled from real research, and links to the CTA you set in the brief.

## Required HubSpot scopes (private app)

Settings → Integrations → Private Apps → Create app → Scopes:

- `content` (the umbrella scope for CMS pages, includes read/write/publish)
- `crm.objects.contacts.read` (only if you want to write the page URL back to the contact record — see `04_publish_pages.py`)

That is enough for everything the starter does. No marketing or analytics scopes.

## Required model access

Two paths.

**Path A — Claude Code Max subscription (recommended).** The starter shells out to the `claude` CLI via subprocess. Authentication piggybacks on your Claude.com session. No API key needed. Pattern lives in `scripts/claude_subagent.py` and matches the doc at `engine/claude-subprocess.md` in this repo.

**Path B — BYOK Anthropic API key.** Set `ANTHROPIC_API_KEY` in `.env` and pass `--use-sdk` to the pipeline. Routes through the official Python SDK instead. Useful if you're outside the Mac/desktop sweet spot, in a CI runner, or if Max subscription terms change.

The chapter has a longer note on when each path makes sense.

## The three pieces

### 1. Brief (input)

A brief is the template-with-holes. Lives either:

- in your HubSpot CMS as a Blog Post under a "Brief" category (set `BRIEF_SOURCE=hubspot` in `.env`), or
- locally as a markdown file in `briefs/` (default)

The frontmatter declares the campaign metadata and the template module path. The body has variable placeholders like `{{pain_point_primary}}` that the enrichment layer fills in per account.

See `briefs/_template.md` for the schema. Two runnable examples ship with the starter (`briefs/abm-mid-market-saas.md`, `briefs/nurture-pricing-revisit.md`).

### 2. Columns (enrichment)

A column is one focused subagent that runs once per account. Each column lives as a prompt file in `columns/`. Add your own by dropping a new `.md` file in that folder.

Default columns:

| File | What it produces | Default model |
|---|---|---|
| `pain-points.md` | Two-sentence pain-point statement specific to the account | opus |
| `tech-stack.md` | Detected CRM, email provider, sales engagement tool | sonnet |
| `hook-angle.md` | One-line hook for the landing page hero | opus |
| `icp-score.md` | 1-10 ICP fit score with a one-line rationale | sonnet |
| `hero-copy.md` | Full hero block: headline, subhead, CTA label | opus |

Model routing happens in `claude_subagent.py`. Override per-column via the frontmatter in each column file.

### 3. Pages API (output)

The publisher reads the brief, the enriched account data, and the template-module schema (`hubspot-template/module-fields.json`), then composes a `layoutSections` payload and POSTs it to `/cms/v3/pages/landing-pages`. State defaults to `DRAFT`. Slug collision is handled by appending `-v2`, `-v3`, etc.

Full payload schema and `layoutSections` examples live in `engine/hubspot-cms.md`.

## The HubL template

This starter ships with a working HubL template at `hubspot-template/landing-page.html`. It's intentionally plain — three modules (hero, body, CTA) on a single layout section called `main_content`. Designed to be replaced by your own template once you've seen the pattern.

To use your own template:

1. Design it in HubSpot Design Manager (drag-drop or HubL, your call).
2. Right-click the template → Copy path. You'll get something like `@hubspot/growth/templates/your-template.html` or `/my-templates/lp-v2.html`.
3. Update `HUBSPOT_TEMPLATE_PATH` in `.env`.
4. Update `hubspot-template/module-fields.json` to mirror your template's modules. The publisher reads this file to know which fields to populate.

## Costs and economics

For a 50-account batch with the default column set (5 columns × 50 accounts = 250 subagent calls):

- **Path A (Claude Code Max):** No per-call API cost. Wall-clock around 6-10 minutes.
- **Path B (BYOK Anthropic API):** Opus 4.7 columns cost roughly $0.04-0.06 per account on heavy columns; Sonnet columns about $0.005 each. A 50-account run on the default mix is in the $1.50-$3 range.
- **HubSpot API calls:** 50 page creates, well under any tier's daily quota.

Re-runs of the same account are SQLite-cached in `cache.db`. Idempotent by `(account_domain, column_slug)`.

## Production safety

- `.env` is gitignored. Never commit your token.
- `briefs-private/` (if you create it) is gitignored — keep client-specific briefs out of the repo.
- `outputs/` is gitignored except for `.gitkeep`. Generated artifacts stay local.
- DRAFT-first is the default. The publisher accepts `--state PUBLISHED_OR_SCHEDULED` only when you opt in.
- Slug collisions return a 409 and the publisher retries with an incremented suffix. The original page is never overwritten.

## Where the parts come from

| Component | Origin |
|---|---|
| Subprocess fan-out pattern | `engine/claude-subprocess.md` (Chapter 12 / Nexus Intel) |
| Private-app token + scope minimization | Chapter 13 (CRM Automation and Slash Commands) |
| SQLite cache pattern | Same chapter, `apollo-enrich.py` reference |
| Voice rules injection into model prompts | Chapter 09 (Voice DNA + Content) + Chapter 14 (Voice Invocation) |
| Brief-as-template, column-as-subagent | Chapter 16 (this one) |
| HubSpot Pages API v3 contract | `engine/hubspot-cms.md` (this drop) |

## Troubleshooting

**`401 Unauthorized`** — Token is invalid or expired. Regenerate the private app token in HubSpot Settings.

**`403 Forbidden`** — Token is valid but missing scopes. Add `content` scope to the private app.

**`409 Conflict`** on POST — Slug already exists. The publisher will automatically retry with `-v2`, `-v3`. If you're seeing this repeatedly, your brief is generating non-unique slugs; check `_generate_pages.py:slugify()`.

**`429 Too Many Requests`** — Hit a rate limit. Pipeline will sleep and retry once. If repeated, lower `--limit` or add `--sleep 2` to slow the loop.

**`claude: command not found`** when running Path A — install the Claude Code CLI (`brew install anthropic/tap/claude-code` on Mac) and run `claude login`. Or switch to Path B with `--use-sdk`.

**Generated copy reads bland** — your columns are too generic. Add concrete instructions in each column file. The model is doing exactly what you asked.

## License

MIT, same as the parent repo.
