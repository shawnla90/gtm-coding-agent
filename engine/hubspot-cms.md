# HubSpot CMS

**Category:** Content publishing / Landing pages and website pages
**Connection:** REST API (private app token or OAuth)
**Cost:** Included with CMS Hub or Marketing Hub (Starter+)
**Auth:** Private app token (single portal) or OAuth 2.0 (multi-portal)

---

## What It Does

HubSpot CMS exposes its pages, blog posts, templates, and themes through a v3
REST API. You can create, update, and publish landing pages without opening
the drag-and-drop builder. The builder is for designing templates. The API is
for filling them, at scale.

For GTM operators, this is the pattern that turns a single landing-page design
into N personalized pages, one per account, generated from briefs and
target lists. Pair it with `engine/claude-subprocess.md` for the per-row
enrichment that fills the variable bits.

## Setup

### Private app token (single portal - start here)

```bash
# Settings -> Integrations -> Private Apps -> Create app
# Scopes: add "content" (the umbrella scope for CMS pages)
# Copy the token

echo "HUBSPOT_PRIVATE_APP_TOKEN=pat-na1-..." >> .env
```

Token format is `pat-na1-...`, `pat-na2-...`, or `pat-eu1-...` depending on
your account's region. Bearer header for every request:

```python
headers = {
    "Authorization": f"Bearer {os.environ['HUBSPOT_PRIVATE_APP_TOKEN']}",
    "Content-Type": "application/json",
}
```

### OAuth 2.0 (multi-portal - agency mode)

When one tool needs to write to many portals (your portal + each client
portal), private app tokens don't scale. OAuth is the upgrade. HubSpot OAuth
access tokens last 30 minutes; refresh tokens don't expire unless the user
uninstalls the app.

```python
# Authorization redirect
auth_url = (
    f"https://app.hubspot.com/oauth/authorize?"
    f"client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope=content"
)

# Exchange code for tokens
resp = requests.post("https://api.hubapi.com/oauth/v1/token", data={
    "grant_type": "authorization_code",
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "redirect_uri": REDIRECT_URI,
    "code": code,
}).json()
# -> { access_token, refresh_token, expires_in (1800) }

# Refresh before each batch (or on 401)
resp = requests.post("https://api.hubapi.com/oauth/v1/token", data={
    "grant_type": "refresh_token",
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "refresh_token": refresh_token,
}).json()
```

Store `{hub_id, access_token, refresh_token, expires_at}` per portal. SQLite
keyed by `hub_id` works. The `hubspot-landing-engine` starter does this in
`scripts/auth_oauth.py`.

## Key Endpoints (v3)

| Method | Endpoint | What it does |
|---|---|---|
| POST | `/cms/v3/pages/landing-pages` | Create a landing page |
| GET | `/cms/v3/pages/landing-pages` | List with filters and sort |
| GET | `/cms/v3/pages/landing-pages/{id}` | Read one page |
| PATCH | `/cms/v3/pages/landing-pages/{id}/draft` | Update a draft |
| POST | `/cms/v3/pages/landing-pages/{id}/publish-action` | Publish or unpublish |
| POST | `/cms/v3/pages/landing-pages/{id}/schedule` | Schedule publication |

Site pages (persistent website pages) use the same shape - swap
`landing-pages` for `site-pages` in the path. Blog posts use
`/cms/v3/blogs/posts`.

## Create a Landing Page

Minimum viable payload:

```python
import os, requests

payload = {
    "name": "LP - Acme - Q2 ABM",
    "htmlTitle": "Built for Acme | AI Revenue Ops Build",
    "metaDescription": "A 30-min walkthrough for the Acme RevOps team.",
    "slug": "lp/acme-q2-abm",
    "templatePath": "/landing-engine/landing-page.html",
    "state": "DRAFT",              # critical for batch workflows
    "publishImmediately": False,
    "campaign": "abm-q2-mid-market",
    "language": "en",
    "layoutSections": {
        "main_content": {
            "name": "main_content",
            "label": "Main content",
            "rows": [
                {
                    "cells": [{
                        "columnWidth": 100,
                        "widgets": [{
                            "type": "custom_widget",
                            "name": "hero",
                            "params": {
                                "headline": "Built for Acme",
                                "subhead": "One sentence anchored to a real Acme detail.",
                                "cta_label": "Book a walkthrough",
                                "cta_url": "https://meetings.hubspot.com/shawn/audit"
                            }
                        }]
                    }]
                }
            ]
        }
    }
}

resp = requests.post(
    "https://api.hubapi.com/cms/v3/pages/landing-pages",
    headers=headers, json=payload, timeout=15,
)
resp.raise_for_status()
page = resp.json()
print(page["id"], page["url"])
```

### The fields that matter

| Field | Notes |
|---|---|
| `name` | Internal name shown in HubSpot UI. Max 255 chars. |
| `templatePath` | **The hardest one to find.** Use the HubSpot Design Manager: hover a template -> right-click -> Copy path. Looks like `/landing-engine/landing-page.html` for custom, `@hubspot/growth/templates/...` for built-ins. |
| `slug` | URL slug. 409 collision if it exists. Retry with `-v2`, `-v3`. |
| `state` | `DRAFT` for batch workflows. `PUBLISHED_OR_SCHEDULED` only after you've reviewed the draft. |
| `publishImmediately` | Almost always `false`. Reserve `true` for hand-published one-offs. |
| `layoutSections` | The module-fill object. Top-level keys are section IDs from your template. Each section has rows -> cells -> widgets. |

### Finding your templatePath

```
1. HubSpot -> Marketing -> Files and Templates -> Design Tools
2. In the left tree, locate your template
3. Hover over the file, right-click -> Copy path
4. Paste into .env as HUBSPOT_TEMPLATE_PATH
```

If your template is in a theme, the path looks like
`@your-theme/templates/landing-page.html`. If it's a coded file in your
portal, it looks like `/landing-engine/landing-page.html`.

## Publish a Draft

Create-with-DRAFT then explicit publish is the safer pattern:

```python
# Step 1: create as DRAFT (above)
# Step 2: review in HubSpot
# Step 3: publish via separate POST

resp = requests.post(
    f"https://api.hubapi.com/cms/v3/pages/landing-pages/{page_id}/publish-action",
    headers=headers,
    json={"action": "PUBLISH"},     # or "UNPUBLISH"
    timeout=15,
)
```

To schedule:

```python
resp = requests.post(
    f"https://api.hubapi.com/cms/v3/pages/landing-pages/{page_id}/schedule",
    headers=headers,
    json={"action": "PUBLISH", "publish_date": "2026-06-01T13:00:00Z"},
    timeout=15,
)
```

## HubL Templates (one design, fill many)

A template is the container. Modules are the fields the API can populate. The
contract between the API and the template lives in module-field definitions.

Three module types cover 90% of landing-page work:

```html
{# Text - short copywriting, no HTML #}
{% module "hero_headline" path="@hubspot/text" label="Headline" %}

{# Rich text - longer copy, allow HTML and lists #}
{% module "body_section" path="@hubspot/rich_text" label="Body" %}

{# URL - the destination of a CTA button #}
{% module "cta_button" path="@hubspot/url" label="CTA URL" %}
```

For repeatable content blocks, use a custom widget with named fields and
reference its `params` from `layoutSections`. The `hubspot-landing-engine`
starter ships a working example.

## Rate Limits

| Tier | Per 10 sec | Daily |
|---|---|---|
| Free / Starter | 100 | 250,000 |
| Pro | 190 | 625,000 |
| Enterprise | 190 | 1,000,000 |

Response headers include `X-HubSpot-RateLimit-Remaining` and
`X-HubSpot-RateLimit-Daily-Remaining`. On 429, respect `Retry-After` and
back off.

## Common HTTP Status Codes

| Code | Means | Fix |
|---|---|---|
| 201 | Page created | continue |
| 401 | Bad token | regenerate private app token; for OAuth, refresh |
| 403 | Wrong scope | add `content` scope to private app |
| 409 | Slug collision | retry with `-v2`, `-v3` suffix |
| 429 | Rate limited | sleep `Retry-After`, retry once |

## Python SDK

Official client is `hubspot-api-client`. Useful when you write a lot of repeat
CRUD; raw `requests` is fine for one-shots.

```bash
pip install --upgrade hubspot-api-client
```

```python
from hubspot import HubSpot
from hubspot.cms.pages import LandingPagesApi

client = HubSpot(access_token=os.environ["HUBSPOT_PRIVATE_APP_TOKEN"])
page = client.cms.pages.landing_pages_api.create(body=payload)
print(page.id, page.url)
```

## Sources

- https://developers.hubspot.com/docs/guides/api/cms/pages
- https://developers.hubspot.com/docs/guides/apps/authentication/private-app-access-tokens
- https://developers.hubspot.com/docs/guides/apps/authentication/working-with-oauth
- https://developers.hubspot.com/docs/guides/cms/content/templates
- https://developers.hubspot.com/docs/developer-tooling/platform/usage-guidelines
