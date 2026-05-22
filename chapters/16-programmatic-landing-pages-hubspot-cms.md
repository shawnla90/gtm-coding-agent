# Chapter 16: Programmatic Landing Pages from HubSpot CMS

**This is a chapter for marketers, RevOps engineers, and anyone in GTM
curious about coding agents. You pick a target list of 50 
accounts, write one markdown brief, and hit run. Six to ten minutes
later there are that many personalized landing pages sitting as DRAFTs
in your HubSpot portal, one per account, each with a hero block written
specifically for that company. Nothing goes live without a second,
deliberate command. This chapter walks the pieces, who edits what, and
how to fork the runnable version at `starters/hubspot-landing-engine/`.**

![90-second demo of the full play](https://raw.githubusercontent.com/shawnla90/gtm-coding-agent/main/assets/videos/ch16-main-demo.gif)

---

## TL;DR

If you do GTM, RevOps, or growth-engineering work in HubSpot and you've
been wondering whether you can run a Clay-style account-personalization
motion without paying Clay rates or learning a second tool, the short
answer is yes. This chapter is the pattern.

- **One brief, many accounts.** You write a markdown brief with
  placeholders for the personalized parts. Each placeholder gets filled
  by a focused AI step (a "column"). The starter ships five columns:
  pain points, tech stack, hook angle, ICP fit score, hero copy.
- **One HubSpot private app, one scope (`content`).** If you went
  through Chapter 13's CRM exercise you already have the app; just add
  the scope. Step-by-step walkthrough is in Part 1.
- **Six to ten minutes to fifty DRAFT pages.** Everything lands as
  DRAFT in your portal. Live publishing requires a separate, explicit
  command (two-key gate).
- **Marketers edit briefs, not code.** The brief is markdown frontmatter
  and placeholders. Optionally store briefs as HubSpot CMS Blog Posts
  under a "Brief" category so non-engineer marketers can edit them
  inside HubSpot's UI.
- **Cheap to run.** Pennies per account on direct Anthropic API, zero
  metered tokens on Claude Code Max.
- **Forkable.** Public starter, MIT licensed, runs against any HubSpot
  portal with CMS Hub.

---

## Where this engine came from

I built a version of this at a HubSpot agency I worked at before going
independent. It ran at scale for ABM cohorts and nurture revisitors,
generating personalized landing pages from the CMS, programmatically, no
drag-and-drop. When I left the agency the engine stayed there. The pattern
stayed in my head.

The model layer is the piece that's different from the original. The
original engine relied on a single AI generation call per page. This
one fans out into focused subagents — one per "column" of insight per
account — and per-account quality goes up by a step function. The
cost story still works (covered in detail under "Why not just use
Clay?" below) because you're running against a small list, not ten
thousand rows.

(If you've been reading the newsletter or the gtm-coding-agent repo,
this chapter pairs naturally with Chapter 13's CRM-side work — same
private-app pattern, one additional `content` scope, both engines
writing to the same HubSpot portal. You can read either order;
neither depends on the other.)

---

## The three pieces

```
1. BRIEF (input)
   The template-with-holes. Lives in HubSpot CMS as a Blog Post under a
   "Brief" category, or as a local markdown file. Variable placeholders like
   {{pain_point_primary_block}} mark the spots the enrichment layer fills.

2. COLUMNS (enrichment)
   One Claude subagent per "column" of insight per account. Pain points,
   tech stack, ICP score, hero copy, hook angle. Opus-tier models on
   controlled lists. The replacement for Clay's AI columns.

3. PUBLISH (output)
   HubSpot Pages API v3. Private app token, single scope ("content").
   POST /cms/v3/pages/landing-pages, state=DRAFT. Slug collisions handled
   automatically. Nothing goes live without an explicit promotion call.
```

The rest of this chapter is each piece up close. Start with Connect.

---

## Part 1: Connect

Before the engine can read or write anything in HubSpot, it needs a way
to authenticate. There are two patterns, and the right one depends on
how many HubSpot portals you're working in. We'll set up the simpler
one (a private app), which is enough for ~95% of readers, then cover
the agency case at the end.

### What a private app is, and why we use one

A private app is HubSpot's modern way to give a script permission to
read and write to your portal. It replaced the old "API keys" model
HubSpot retired in late 2022. If you've ever pasted a HubSpot API key
into a tool, a private app token is what now sits in that slot.

For everything in this chapter, a single private app with one ticked
scope is enough. The setup is a 5-minute click-through inside HubSpot's
settings.

### How to find Private Apps in HubSpot

The menu is a little buried, which is the part most tutorials skip.
Here's the path:

1. In your HubSpot portal, click the **gear icon** in the top-right
   (Settings).
2. In the left sidebar, scroll down to **Integrations**.
3. Click **Private Apps**.

If your portal still shows an "API key" entry in that menu instead, you
are in a portal that hasn't migrated yet. HubSpot will show a
deprecation banner; click through to the **Private Apps** page from
there.

On the Private Apps page, you'll see any apps you've already created,
plus a **Create a private app** button.

### Create the app (or reuse your Chapter 13 one)

**If you already have a Chapter 13 private app:** click into it, hit
**Edit details**, switch to the **Scopes** tab, search for `content`,
tick it, and click **Commit changes**. The token you already have keeps
working. Skip to "Test the token."

**If you don't have one yet:** click **Create a private app**. You'll
see two tabs:

- **Basic Info** — name (something like "Landing Page Engine") and
  description. Fill in whatever; only you see this.
- **Scopes** — the permission list. This is the tab that matters.

For this engine, you need exactly one scope:

```
content
```

Search the scopes panel for "content" and tick it. That's the umbrella
permission for reading templates, creating pages, updating drafts, and
publishing. Then click **Create app** in the top right.

HubSpot will show a confirmation modal. Click **Show token** and copy
the long string. It starts with `pat-na1-` (US data center) or
`pat-na2-` (EU). Paste it into your starter's `.env` file:

```bash
# starters/hubspot-landing-engine/.env
HUBSPOT_PRIVATE_APP_TOKEN=pat-na1-...
```

### Test the token

From a terminal, with the starter as your working directory:

```bash
curl -s -H "Authorization: Bearer $HUBSPOT_PRIVATE_APP_TOKEN" \
  "https://api.hubapi.com/cms/v3/pages/landing-pages?limit=1" | head -c 200
```

If you get JSON back, you're connected. Two failure modes to know
about:

- **401 Unauthorized** — the token is wrong. Re-copy it from HubSpot;
  the most common cause is a leading or trailing space.
- **403 Forbidden** — the token is right, but the scope is missing.
  Go back to the private app, tick `content` on the Scopes tab, click
  **Commit changes**.

### When OAuth makes more sense

Private app tokens are one-portal-only. Each token authenticates
against the single HubSpot portal it was created in. That's the right
setup if you're running this engine for your own company, or for one
client.

If you're an agency running this engine across many client portals at
once, you need OAuth instead. The starter ships an `auth_oauth.py` with
the full flow and a SQLite token store keyed by `hub_id`. Two practical
notes if you're going down that path:

- HubSpot OAuth access tokens last **30 minutes**. Refresh tokens
  never expire (unless the user uninstalls the app). The starter's
  helper auto-refreshes when an access token has 5 minutes or less
  remaining.
- The OAuth dance itself happens once per portal in a browser. After
  that, scripted runs use the stored refresh token.

**Rule of thumb:** one portal → private app. Two or more portals →
OAuth.

---

## Part 2: The engine

Three sub-stages, one CLI.

### 2a. Brief as template

A brief is a markdown file. The frontmatter declares the campaign and the
list of required columns. The body has variable placeholders.

```markdown
---
brief_slug: abm-mid-market-saas
campaign: abm-q2-mid-market
template_module: landing-page
audience: "Mid-market B2B SaaS, 50-500 employees, Series B-D"
cta_label: "Walk me through a 30-min audit"
cta_url: "https://meetings.hubspot.com/shawn/audit"
columns_required:
  - pain-points
  - hook-angle
  - hero-copy
  - tech-stack
  - icp-score
---

# {{hero_headline}}

{{hero_subhead}}

## The pile that goes stale

Every B2B SaaS at your stage has the same shaped problem:
{{pain_point_primary_block}}

Your stack probably looks like {{tech_stack_summary}}. That's the surface.
The gap underneath is where the work hides.

...
```

The brief is reusable across campaigns. The thing that changes between Q1
and Q2 is the `campaign` field and maybe the CTA. The thing that changes
between accounts is everything in the `{{}}` braces, and that's what the
columns produce.

You can store briefs either as local files (default) or as HubSpot CMS Blog
Posts under a "Brief" category. The starter supports both via the
`BRIEF_SOURCE` env var. **Local is faster to iterate; HubSpot CMS is easier
to delegate to a non-engineer marketer.** Pick the one that matches the
person who'll be editing briefs.

### 2b. Columns as subagents

A column is one focused subagent. It reads the brief, the account, and the
research, and returns one JSON object matching a schema. Five columns ship
with the starter:

| Column | What it produces | Default model |
|---|---|---|
| `pain-points` | Two-sentence pain statement specific to the account | opus |
| `tech-stack` | Detected CRM / email / sales engagement / enrichment | sonnet |
| `hook-angle` | One-sentence hero hook, under 20 words | opus |
| `icp-score` | 1-10 fit score with rationale | sonnet |
| `hero-copy` | Headline, subhead, body block, CTA label | opus |

Each lives as a markdown file in `columns/`. Adding a new column is dropping
a new `.md` file and listing it in a brief's `columns_required`. The
pipeline picks it up next run.

Under the hood, each column is invoked as a subprocess:

```bash
claude --print --model opus   # one call per column, per account
```

The pattern is documented in `engine/claude-subprocess.md`. Three things
make this approach worth the slight added complexity over a single
generation call per page:

- **Parent / child model split.** Two layers of model run in this
  pipeline, and they don't have to be the same model. The outer layer
  — the Claude Code session driving `pipeline.py` — is orchestrating:
  deciding which account is next, which column to run, where to put
  the result. That work doesn't need top-tier reasoning, so the outer
  session can sit on Haiku (fast and cheap). The inner layer is the
  writing: one Opus 4.7 subprocess per column per account. **Top-tier
  compute lives only in the writing children.** That is how "Opus 4.7
  per row" stays measurable in dimes, not dollars.
- **Subscription economics.** The starter calls Claude through the
  `claude` CLI. If you have Claude Code Max, you've already paid for
  the inference — the CLI piggybacks on that subscription, so a run
  that hits Opus 4.7 fifty times costs zero metered tokens. If you
  prefer to run this from CI or a non-Mac machine, set
  `ANTHROPIC_API_KEY` and pass `--use-sdk` to switch to direct-API
  billing.
- **Per-account model tier.** This is the real wedge against Clay
  (more in "Why not just use Clay?" below). Because you're running
  against a small list, you can afford a top-tier model on every row.
  Per-account quality goes up by a step function. Rough cost:
  **$0.12 to $0.20 per account on BYOK, zero on Max subscription.**

**One caveat to name out loud.** Max-plan subscription terms may shift
over time. The starter accepts an `ANTHROPIC_API_KEY` and a `--use-sdk`
flag specifically so the same pipeline keeps working on BYOK if the
economics change.

### 2c. Generate and publish

Once columns have run, the generator composes the HubSpot Pages API
payload per account.

```python
# scripts/_generate_pages.py
payload = {
    "name": f"LP - {account.company} - {brief.campaign}",
    "htmlTitle": hero.get("headline") or f"Built for {account.company}",
    "metaDescription": (hero.get("subhead") or "")[:200],
    "slug": f"lp/{slugify(brief.campaign + '-' + account.company)}",
    "templatePath": os.environ["HUBSPOT_TEMPLATE_PATH"],
    "state": "DRAFT",
    "publishImmediately": False,
    "campaign": brief.campaign,
    "language": "en",
    "layoutSections": build_layout_sections(brief, account),
}
```

The `layoutSections` field is where the brief body becomes HubL module
parameters. The template defines three modules (hero, body_rich_text, cta).
The generator fills each module's `params` with rendered values from the
brief body, columns, and brief metadata. Full payload schema lives in
`engine/hubspot-cms.md`.

Publishing is a separate call. `_publish_pages.py` posts each payload to
`POST /cms/v3/pages/landing-pages`. Two safety behaviors:

- **DRAFT-only by default.** The publisher caps state at `HUBSPOT_PAGE_STATE_CAP`
  in `.env`, which defaults to `DRAFT`. To actually push pages live, you have
  to set the cap AND pass `--state PUBLISHED_OR_SCHEDULED`. Two-key gate.
- **Slug collisions auto-retry.** 409 on POST means a page with that slug
  already exists. The publisher retries with `-v2`, `-v3` up to six times.
  Your existing pages are never overwritten.

---

## Part 3: The worked example

Run it on the test list that ships with the starter (Stripe, Linear, Vercel,
Clerk, Resend - all public companies, safe to research).

```bash
cd starters/hubspot-landing-engine

# Install
pip install -r requirements.txt

# Fill .env
cp .env.example .env
# Edit: paste HUBSPOT_PRIVATE_APP_TOKEN, HUBSPOT_TEMPLATE_PATH

# Upload the bundled HubL template to your portal (one-time)
hs init                                # browser auth, first run only
hs upload hubspot-template /landing-engine

# Dry-run end to end (no live publish)
python scripts/pipeline.py --step all --limit 3 --dry-run

# Real run, DRAFT state
python scripts/pipeline.py --step all --limit 3 --state DRAFT
```

What you'll see in the terminal:

```
[pipeline] step=all brief=abm-mid-market-saas limit=3 state=DRAFT
[pipeline] loaded brief: abm-mid-market-saas (abm-q2-mid-market, 5 columns)
[pipeline] loaded 3 accounts from targets/accounts.csv.example
[enrich] Stripe (stripe.com)
  + pain-points: ok
  + tech-stack: ok
  + hook-angle: ok
  + icp-score: ok
  + hero-copy: ok
[enrich] Linear (linear.app)
  ...
[publish] 1/3 -> LP - Stripe - abm-q2-mid-market
[publish] 2/3 -> LP - Linear - abm-q2-mid-market
[publish] 3/3 -> LP - Vercel - abm-q2-mid-market
```

![Personalized DRAFT landing page generated from the brief](https://raw.githubusercontent.com/shawnla90/gtm-coding-agent/main/assets/videos/ch16-page-reveal.gif)

Three DRAFT landing pages now exist in your HubSpot portal under Marketing ->
Landing Pages. Each one references the account by name, leads with a
research-anchored hero block, and links to the CTA in your brief. The bodies
mirror the brief's structure with the `{{}}` placeholders replaced by
column outputs.

**Re-runs are idempotent.** The starter caches every column output by
`(domain, column_slug)` in `cache.db`. Running the pipeline a second time
on the same target list skips the subagent calls and goes straight to
generate + publish. To force a re-enrich (after editing a column prompt),
pass `--force`.

---

## HubL templates: design once, fill many

The template is the visual decision. The brief is the content decision. The
columns are the personalization decision. Three separate jobs, three
separate artifacts.

The starter ships a minimal HubL template at
`hubspot-template/landing-page.html`. Three modules on one layout section
called `main_content`:

```html
<section class="hero">
  {% module "hero" path="@hubspot/text" label="Hero" %}
  <h1>{{ widget_data.hero.headline }}</h1>
  <p class="subhead">{{ widget_data.hero.subhead }}</p>
  <a class="cta" href="{{ widget_data.hero.cta_url }}">{{ widget_data.hero.cta_label }}</a>
</section>

<section class="body-block">
  {% module "body_rich_text" path="@hubspot/rich_text" label="Body" %}
  {{ widget_data.body_rich_text.html|safe }}
</section>

<section class="footer-cta">
  {% module "cta" path="@hubspot/cta" label="Footer CTA" %}
  <a class="cta" href="{{ widget_data.hero.cta_url }}">{{ widget_data.hero.cta_label }}</a>
</section>
```

Plain enough to read. The point isn't the design. The point is that the
template defines three named module slots, and the API fills them.

**Replacing the bundled template with your own takes three steps:**

1. Design your template in HubSpot Design Manager (drag-drop, save as
   template, copy the path).
2. Update `HUBSPOT_TEMPLATE_PATH` in `.env`.
3. Update `hubspot-template/module-fields.json` and
   `_generate_pages.py::build_layout_sections` to match your template's
   module names and fields.

That's the whole replacement surface. The brief format, the columns, the
publishing flow - all stay the same.

---

## Why not just use Clay?

Clay is the obvious comparison. Clay also enriches accounts with AI
columns and lets you fan out personalization across thousands of
records. Three real differences between this engine and a Clay-driven
motion. The biggest one isn't a feature — it's about who each tool is
built for.

### Clay is built for volume; this is built for a controlled list

Clay's whole pricing model is built on amortizing AI inference cost
across many customers running large enrichment lists. To make that
math work, Clay's AI columns default to mid-tier models on the
cheaper side of the cost curve. They have to. Top-tier models cost
too much per call to run at 10,000-row scale across an entire customer
base.

You are not running at 10,000 rows. You're running fifty. At fifty
rows, the cost difference between a mid-tier and a top-tier model is
roughly the gap between $1.50 and $20 — a number you do not notice on
a single campaign. **So you can afford the top tier on every row.**

That changes what comes out the other end. Hero copy actually grounded
in this specific company instead of a template with the company name
swapped in. Hooks that reference a real news item from last quarter
instead of "Hi Stripe, I noticed you're in fintech."

Numbers, since people ask:

| Path | Cost per row at Opus quality | Notes |
|---|---|---|
| Clay AI column | ~$0.50–$0.56 | ~7.5 Clay credits/row on current tiers |
| Direct Anthropic API | ~$0.03 | Same prompt, same model |
| Claude Code Max via `claude` CLI | $0 metered | Piggybacks on subscription |

The wedge is structural. It is not contingent on this month's pricing
— it's a function of who can afford what at what scale.

### HubSpot stays canonical

Briefs live in HubSpot. Pages publish to HubSpot. Attribution stays in
HubSpot. The whole motion fits inside the tool the rest of your team
already uses. No second product to learn, no second contract to sign,
no analytics that need to be stitched together.

### Version control

Every brief is markdown. Every column is markdown. Every generated
payload is JSON. All four artifacts live in git. When your RevOps lead
asks why the Q3 messaging is different from Q2, the answer is a diff,
not a Slack search.

**Rule of thumb:** Clay when you're operating on lists of 5,000+ and
you need shallow enrichment fast. This engine when you're operating on
lists of 50 to 500 and you need the hero copy to actually be
defensible.

---

## Security

Three rules. Same three from Chapter 04, applied to the CMS context.

**1. Token in `.env`, never in code.** The starter loads via
`python-dotenv` and the `.env.example` ships with the placeholder
`pat-na1-replace-me` so a forgotten-to-fill .env fails fast instead of
firing requests with garbage.

**2. Scope minimization.** The starter needs exactly one scope: `content`.
If you reuse the Chapter 13 private app, that one already has CRM scopes -
that's fine, the additional CMS scope sits next to them. Don't grant scopes
the starter doesn't use.

**3. DRAFT first, always.** `HUBSPOT_PAGE_STATE_CAP=DRAFT` in `.env` is the
production setting. To actually publish, you raise the cap AND pass
`--state PUBLISHED_OR_SCHEDULED` on the CLI. Two flags, both deliberate. The
gate exists because the cost of a typo in a DRAFT page is zero; the cost of
a typo in a live one is real.

One more, specific to this engine: **don't store generated payloads in
git.** `outputs/` is in `.gitignore` for a reason. The payloads contain
research outputs that may reference real customer data depending on what
columns you've added. Keep them local.

---

## Exercise

Build your own brief. The shape of the work:

1. Pick one outbound campaign or one nurture motion you run today.
2. Write the brief: define the audience, the pain focus, the CTA, the
   columns you need. Start from `briefs/_template.md`.
3. Add one new column the default starter doesn't have. Suggestions:
   `peer-anchor` (find a public peer the account would recognize),
   `category-shift` (write the contrarian framing), `objection-handler`
   (preempt one common objection).
4. Run the pipeline on five accounts from your real ICP.
5. Open the five DRAFT pages in HubSpot. Spot-check the hero block. If two
   of the five sound generic, your column prompts are too generic. Iterate
   on them, force a re-run with `--force`, repeat.

The whole loop is a 45-minute exercise the first time. Every subsequent
campaign is a 5-minute brief edit and a `pipeline.py` run.

---

## Recap

The point of this chapter, in plain English:

- You can run an account-by-account landing-page personalization motion
  out of HubSpot directly. No second tool.
- The setup is one private app, one scope (`content`), one `.env` file.
- The work is split between a marketing-editable artifact (the brief)
  and a developer-editable artifact (the column prompts). RevOps sits
  in the middle and can edit both.
- Cost stays in the dimes per account because you're running against
  small, deliberate lists. The model tier is the difference between
  generic-feeling hero copy and copy that sounds like it was written
  for this specific company.
- Nothing goes live without a second, deliberate command. DRAFT first.
- Re-runs are cheap. Cached column outputs mean a second pass against
  the same list skips the AI work.
- If you outgrow one HubSpot portal, OAuth is the upgrade path. The
  same pipeline keeps working.

---

**Next:** [Chapter 17 - Pricing Page Visitor Engines](./17-pricing-visitor-engines.md) - The third piece of the loop. Custom CMS pages have visitors. Visitors have signals. Wiring the same engine to website-visit signals, so a stranger landing on your pricing page tomorrow morning has a personalized landing page waiting by lunch.
