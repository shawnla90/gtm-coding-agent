# Chapter 16: Programmatic Landing Pages from HubSpot CMS

**Chapter 13 wired your CRM as a command center - your terminal now talks to HubSpot directly, no browser tab, no marketplace MCP server in the loop. This chapter wires the publishing destination. The same terminal session that pulls qualified contacts and writes three custom angles back as properties now also publishes the matching landing page for each one. One concrete example all the way through: `pipeline.py --step all` reads a brief from HubSpot CMS, runs five subagents per account on a controlled target list, and posts five DRAFT landing pages back to your portal. Six to ten minutes for fifty accounts depending on column mix.**

---

## The promise we made

Three weeks ago in the outbound engine play, the Substack closed with this line:

> *content if you want the terminal to also build and publish landing pages.*

That promise has been sitting open. This chapter is the build-out. The
matching landing-page engine to the outbound engine that already shipped. Same
private app token. Same subprocess fan-out. New destination: HubSpot CMS
Pages API.

Why bother shipping the matching half? Because the CRM enrichment work is half
the loop. The other half is the linkable URL. When your SDR opens a contact
record and sees three personalized angles in custom properties, the next
question is "where do I send them?" If the answer is a generic pricing page,
you spent compute on a half-built motion. If the answer is a personalized
landing page that references their actual stack and the actual pain you
diagnosed, you closed the loop.

The other reason: this is the part that's hardest to delegate to a SaaS tool.
Clay's AI columns score, enrich, and classify. They don't write to your
CMS. Unbounce templates, even with their AI generator, give you generic copy
filled in by a generic model. The model tier matters more here than anywhere
else - and that's the wedge.

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

Every reader of this chapter already has Chapter 13's private app token set
up. If you don't, read Chapter 13's "Connecting HubSpot" section first. Same
token works here; you only need to add one scope.

---

## Part 1: Connect

The auth model for the CMS API is identical to the CRM API. Same Bearer
header, same `pat-na1-` / `pat-na2-` token format, same private-app pattern.

### Scopes you need

For landing-page CRUD, you need exactly one scope:

```
content
```

That's the umbrella scope. It covers reading templates, creating pages,
updating drafts, and publishing. If you already have the Chapter 13 private
app set up with CRM scopes, edit that app and tick `content`. No need for a
second app.

```bash
# In your starter's .env (already set if you followed Chapter 13)
HUBSPOT_PRIVATE_APP_TOKEN=pat-na1-...

# Test it from the terminal
curl -s -H "Authorization: Bearer $HUBSPOT_PRIVATE_APP_TOKEN" \
  "https://api.hubapi.com/cms/v3/pages/landing-pages?limit=1" | head -c 200
```

A successful response returns JSON. A 401 means the token is wrong. A 403
means the scope is missing - go add `content` to the private app.

### When OAuth makes sense

Private app tokens are scoped to one HubSpot portal. If you're an agency
running this engine across many client portals, you need OAuth instead. The
starter ships an `auth_oauth.py` with the full flow and a SQLite token store
keyed by `hub_id`.

Two practical notes:

- HubSpot OAuth access tokens last **30 minutes**. Refresh tokens never expire
  (unless the user uninstalls). The starter's helper auto-refreshes when an
  access token has 5 minutes or less remaining.
- The auth flow itself happens once per portal in a browser. After that,
  scripted runs use the stored refresh token. Production-shaped.

**My rule:** if you're working in one HubSpot portal, use a private app
token. If you're working in two or more, OAuth is worth the setup hour.

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

Under the hood, each subagent is a `claude --print --model {tier}`
subprocess call. The pattern is documented in
`engine/claude-subprocess.md`. Two reasons it wins for this work:

- **Subscription economics.** The CLI piggybacks on your Claude Code Max
  session. A run that hits Opus 4.7 fifty times costs zero metered tokens.
  Path B (BYOK API key) is there for CI and non-Mac runners. Set
  `ANTHROPIC_API_KEY` and pass `--use-sdk`.
- **Per-account model tier.** This is the real wedge against Clay. Clay's
  AI columns have to amortize model cost across thousands of customers, so
  they default to mid-tier models. You're running against fifty accounts at
  a time. You can afford the top tier. **Per-account quality goes up by a
  step function, and the per-account cost stays in the dimes (rough est:
  $0.12-$0.20 on BYOK, zero on Max subscription).**

**One caveat to name out loud.** Max-plan subscription terms may shift in
the next six weeks. The starter accepts an `ANTHROPIC_API_KEY` and a
`--use-sdk` flag specifically so the same pipeline keeps working on BYOK if
the economics change.

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

## Why this beats the Clay path

Three reasons, in order of how often they end up mattering.

**Model tier per row.** Clay's AI columns run against the same model for
every customer because the cost has to amortize across the customer base.
That model is rarely the top tier. Your pipeline runs against the top tier
because your list is small. On a fifty-account batch, that's roughly the
difference between a hook that references a real news item from last
quarter and a hook that says "Hi Stripe, I noticed you're in fintech."

**HubSpot stays canonical.** Briefs live in HubSpot. Pages publish to
HubSpot. Attribution stays in HubSpot. The whole motion fits inside the
tool the rest of your team already uses. No second product to learn, no
second contract to sign.

**Version control.** Every brief is markdown. Every column is markdown.
Every generated payload is JSON. All four artifacts live in git. When the
RevOps lead asks why the messaging for the Q3 launch is different from Q2,
the answer is a diff.

**My rule:** use Clay when you're operating on lists of 5,000+ and you
need shallow enrichment fast. Use this engine when you're operating on
lists of 50-500 and you need the hero copy to actually be defensible.

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

## Key Takeaways

- The same private app token from Chapter 13 powers this engine. One extra
  scope (`content`) is the only setup change.
- Briefs are templates with holes. Columns fill the holes. Templates define
  the visual frame. Three separate artifacts, one pipeline.
- Subagents on Opus-tier models per account is the move Clay can't make
  economically. Controlled lists are the unlock.
- DRAFT-first is the production setting. Two-key gate before pages go live.
- Re-runs are idempotent. The cache keys on `(domain, column_slug)`.
- OAuth is the upgrade when you run this across multiple HubSpot portals.

---

**Next:** [Chapter 17 - Pricing Page Visitor Engines](./17-pricing-visitor-engines.md) - The third piece of the loop. Custom CMS pages have visitors. Visitors have signals. Wiring the same engine to website-visit signals, so a stranger landing on your pricing page tomorrow morning has a personalized landing page waiting by lunch.
