# Instantly replies into HubSpot

Companion to Chapters 26, 27, and 28, with the re-find rules from Chapter 29 in the same module.

A proptech / multifamily services client was running a conference campaign. A paid sync tool stopped logging replies. This starter is the generic version of the replacement: pure rules, a copy-in webhook, a cron poll, and a private HubSpot card. It does not ship a deployable Next.js app. Copy the route files into the app you deploy at `https://your-app.vercel.app`.

Nothing here calls Instantly or HubSpot. `python3 -m unittest tests/test_reply_loop.py` from the repo root is the whole test.

## What the rules refuse

- Writes while `INSTANTLY_REPLY_TEST_MODE` is on.
- Writes unless `HUBSPOT_ALLOW_CLIENT_PORTAL` is the exact string `true` and the portal id matches `HUBSPOT_PORTAL_ID`. In the chapter this flag is `HUBSPOT_ALLOW_<CLIENT>_PORTAL`. `CLIENT` is a slug you choose.
- Any payload that sets `hubspot_owner_id`.
- A deal when the email log did not return an id.
- A second email log when `hs_unique_id` is already `instantly:<email id>`.
- A pipeline or stage value of `MQL`. Pass ids.
- A deal on `reply_received` alone. Interest status 1, `lead_interested`, or `manual_mql` opens one.
- A campaign-name guard while `INSTANTLY_REPLY_TEST_MODE` is off. `campaign_suppressed_by_guard` is the check. The placeholder guard is `CAMPAIGN_NAME_GUARD`.
- `eaccount` (or any sending mailbox) on lead create.
- A HubSpot lead-status write for `auto_reply`, `bounce`, or `out_of_office`.
- Treating a 200 from a lead-status PATCH as proof the status changed. Park with `blocklist_entry_body`.
- A v3 PATCH that sets `hs_additional_emails`. That property is read-only. `email_swap_plan` PATCHes the new primary, then PUTs the old address through the legacy secondary-email endpoint.

The card renders `No Instantly thread` when the thread route is a 200 with zero messages. `thread_view` maps a non-200 to `auth_failure`. Send is allowed for logged-in HubSpot users on `@client-domain.com` via `user_can_reply`. Do not fill `HUBSPOT_APP_SECRET` from `vercel env pull`.

The Build section and the Gotchas section are `skills/instantly-hubspot-replies/SKILL.md`. The retired-mailbox case is `skills/dead-address-refind/SKILL.md`.

## Layout

| Path | What it is |
|---|---|
| `reply_loop.py` | The decisions. Portal gate, idempotency, deal open, plan/apply/read-back, signature, re-find. |
| `routes/*.mjs` | HTTP status shape to copy into Next.js route handlers. |
| `hubspot-card/` | Private static app on platform `2025.2`. `permittedUrls.fetch` and a `BACKEND` constant. |
| `.env.example` | Env var names. Values stay out of git. |

## Plan, then apply

```bash
cd starters/instantly-hubspot-replies
python3 -c "
import json
from reply_loop import build_plan
plan = build_plan([{
  'email_id': 'email-1',
  'contact_id': '<CONTACT_ID>',
  'person': 'Jordan Hale',
  'company': 'Example Multifamily',
  'interest_status': 1,
  'text': 'Yes, send the one-pager.',
  'subject': 'Re: conference',
  'timestamp': '2026-11-05T15:00:00.000Z',
}], prefix='CONF', pipeline_id='<PIPELINE_ID>', stage_id='<STAGE_ID>')
print(json.dumps(plan, indent=2))
"
```

`apply_plan` takes that plan, a gate dict, and a writer you supply. The writer is where your app calls HubSpot. The undo list is the created record ids. `read_back` checks the unique id, the deal name, and an empty owner.

Deal search uses the needle `(CONF) - `. The deal that counts as a duplicate is the full name `(CONF) - Jordan Hale - Example Multifamily`. One prefix can hold many prospects. Two records with that same full name are a race. `duplicate_deal_report` lists them and deletes nothing.

## Webhooks

Create one webhook per event per campaign. For the reply loop that is `reply_received` and `lead_interested`. `webhook_create_body` builds the POST to `https://api.instantly.ai/api/v2/webhooks` with header `X-Instantly-Secret`. Print `redact_webhook_body` in logs. `auto_reply_received` is not in the create-webhook enum this file copied on 2026-11-05. Subscribe to `reply_received` and poll `GET /api/v2/emails` (20 requests a minute, one page per cron wake).

Leave the old sync tool's webhooks in place until a person turns them off.

## Card

From `hubspot-card/`, after `hs account auth`:

```bash
hs project upload
```

`permittedUrls.fetch` is `https://your-app.vercel.app`. The card's `BACKEND` constant is the same origin. `hs project install-deps` fills `node_modules` locally. Do not commit them.
