---
name: instantly-hubspot-replies
version: 1.0.0
description: Log Instantly cold-email replies into HubSpot as email engagements, open an unowned stage-1 deal on a positive reply, and go live with a portal allow flag, a test mode, webhooks, and a HubSpot card that replies from the sending mailbox. Use when the user says "log replies to hubspot", "instantly webhook", "reply loop", "unibox", "reply from the sending mailbox", "hubspot card", or "go live on the reply loop".
---

# instantly-hubspot-replies

Replies show up on the contact as one email thread. A positive reply opens an unowned deal. A second delivery of the same Instantly email id does nothing.

Wraps [`starters/instantly-hubspot-replies/`](../../starters/instantly-hubspot-replies/). The Python module decides. The Next.js app on Vercel is the thing you deploy. Read Chapters [26](../../chapters/26-replies-into-the-crm.md), [27](../../chapters/27-reply-loop-go-live.md), and [28](../../chapters/28-reply-from-the-sending-mailbox.md) before writing a record.

## Inputs

- `HUBSPOT_ACCESS_TOKEN` (private app token), `HUBSPOT_PORTAL_ID`, `HUBSPOT_ALLOW_<CLIENT>_PORTAL` (this starter uses `HUBSPOT_ALLOW_CLIENT_PORTAL`)
- `INSTANTLY_API_KEY`, `INSTANTLY_CAMPAIGN_IDS`, `INSTANTLY_CAMPAIGN_DEAL_PREFIXES`
- `HUBSPOT_MQL_PIPELINE_ID`, `HUBSPOT_MQL_STAGE_ID` (ids, not the label MQL)
- `INSTANTLY_WEBHOOK_SECRET`, `CRON_SECRET`, `HUBSPOT_APP_SECRET`
- `HUBSPOT_REPLY_ALLOWLIST` (HubSpot user emails allowed to send from the card)
- `INSTANTLY_REPLY_TEST_MODE=true` until the first hand-checked reply has been applied

## How to run

```bash
python3 -m unittest tests/test_reply_loop.py
```

Build a plan with `build_plan`. Apply with `apply_plan` only when `portal_write_allowed` returns true. Read the created records back with `read_back`. Keep the undo file.

## The loop

1. Accept `reply_received` and `lead_interested` on a webhook, one subscription per campaign. Header `X-Instantly-Secret`.
2. Poll `GET /api/v2/emails` on a cron. The list endpoint allows about 20 requests a minute. Unibox replies fire no webhook, so the poll is what catches them.
3. Log the email on the contact. `hs_unique_id` is `instantly:<email id>`. Direction is `INCOMING_EMAIL` or `EMAIL`. Associate the contact (type id 198).
4. Open a deal only after that log returns an id. Name it `(Prefix) - Person - Company`. Leave `hubspot_owner_id` unset. Search with the needle `(Prefix) - `, then match the full name.
5. `lt_interest_status` 1 or the `lead_interested` event is the positive reply. Meeting Booked stays closed. Auto-replies and bounces stay closed.

## Go live

Follow Chapter 27 in order. Keys live in chmod 600 files outside git. The route returns 401 without the secret and 200 with it. Create the new webhooks. Leave the old sync tool's webhooks until a person removes them. Confirm no workflow sets an owner on deal create. Flip `INSTANTLY_REPLY_TEST_MODE` to `false` after one real reply has been applied by hand and read back.

## The card

Chapter 28. Private static app, platform `2025.2`. `permittedUrls.fetch` and the `BACKEND` constant are `https://your-app.vercel.app`. The card says which mailbox it will send from before the button enables. The backend verifies the HubSpot v3 signature with `HUBSPOT_APP_SECRET`, checks the allowlist, then calls `POST /api/v2/emails/reply` with `eaccount` and `reply_to_uuid`.

## Do

- Run the unit tests after any change to `reply_loop.py`.
- Plan, apply, undo, read back. The first live reply is one record, with a person watching.
- Store the service key and the personal access key outside the repo. Print a boolean and a length when you have to prove a key is present.
- Copy the client secret from the app Auth tab into `HUBSPOT_APP_SECRET`. A personal access key does not reveal it.

## Don't

- Don't open a deal when the email log failed.
- Don't set `hubspot_owner_id` on a create or an update.
- Don't treat the stage label MQL as the stage id.
- Don't delete the previous vendor's webhooks as part of this skill.
- Don't subscribe to `auto_reply_received` unless the create-webhook enum lists it. Use `reply_received` plus the poll.
- Don't print tokens, portal record ids, or the webhook secret.
- Don't send from the rep's connected inbox. That is a different thread.

## Related

- `../../chapters/26-replies-into-the-crm.md`
- `../../chapters/27-reply-loop-go-live.md`
- `../../chapters/28-reply-from-the-sending-mailbox.md`
- `../../skills/dead-address-refind/SKILL.md` for a retired mailbox that is not a departure
