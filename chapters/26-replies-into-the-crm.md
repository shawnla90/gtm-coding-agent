# Chapter 26: Cold Email Replies into the CRM

**A paid sync tool, the OutboundSync style of product, stopped logging replies and nobody noticed until a prospect had already said yes. The replacement is a small Next.js app on Vercel. Instantly tells it about the reply. It writes a real email engagement on the HubSpot contact, in the same thread, and a positive reply opens an unowned deal at stage 1. The idempotency key makes a second delivery a no-op.**

This chapter is the build. Chapter 27 is the cutover. Chapter 28 is the card that replies from the sending mailbox. The client in the story is a proptech / multifamily services client running a conference campaign. Names, portal ids, and campaign ids below are placeholders.

---

## TL;DR

- Log every reply as a HubSpot email engagement on the contact. `hs_unique_id` is `instantly:<email id>`.
- Open a deal only after that log returns an id. Name it `(Prefix) - Person - Company`. Leave it unowned.
- Open that deal for `lt_interest_status` 1 (Interested) or the `lead_interested` event. Meeting Booked stays closed. Auto-replies and bounces stay closed.
- A webhook misses replies typed in the Instantly Unibox. Poll `GET /api/v2/emails`. That endpoint allows about 20 requests a minute.
- Test mode and a portal allow flag refuse writes, including writes aimed at the production portal, until you turn them on.
- The first real positive reply is applied by hand, then read back, before the switch flips.

The rules are `starters/instantly-hubspot-replies/reply_loop.py`. Tests are `tests/test_reply_loop.py`. They use no network.

---

## What broke

The sync tool was supposed to mirror Instantly into HubSpot. It stopped. The campaign kept sending. Replies sat in the Unibox. The contact timeline in HubSpot stayed quiet, so the sales pipeline never saw the yes.

Two things had to be true on the contact after a reply:

1. The reply shows up as an email engagement, inbound or outbound, on one thread a rep can open.
2. A positive reply opens a deal at stage 1 of the sales pipeline. On this portal that stage is the MQL stage. The deal has no owner until a person takes it.

A second run of the same reply must not create a second engagement or a second deal.

---

## The shape

```
Instantly
  reply_received webhook --------+
  lead_interested webhook -------+--> Next.js on Vercel --> HubSpot email engagement
  cron: GET /api/v2/emails ------+         |                      |
                                           |                      +--> deal, only after the email id comes back
                                           +--> plan / apply / undo file
```

The webhook is the fast path. The cron is the backup, and it is the only path for a reply someone typed in the Unibox. Those sends do not fire a webhook.

The leads list endpoint can lag the mailbox. A reply can be sitting in `GET /api/v2/emails` while the lead's interest field is still empty. Use the email as the fact that a reply happened. Use `lead_interested`, or `lt_interest_status` 1 when you do read it, as the fact that it was positive. Do not wait on the leads list to decide that the reply exists.

---

## Instantly

Public docs: [list email](https://developer.instantly.ai/api-reference/email/list-email), [reply to an email](https://developer.instantly.ai/api-reference/email/reply-to-an-email), [create webhook](https://developer.instantly.ai/api-reference/webhook/create-webhook), [webhook events](https://developer.instantly.ai/guides/webhook-events).

Host is `https://api.instantly.ai`. Authorization is `Bearer` plus the API key.

| Call | Use |
|---|---|
| `GET /api/v2/emails` | List messages, including Unibox replies. Filter with `campaign_id`. About 20 requests a minute. One page per cron wake. |
| `POST /api/v2/emails/reply` | Send from the same mailbox, in the same thread. Required fields: `eaccount`, `reply_to_uuid`, `subject`, `body`. |

`eaccount` is the sending mailbox connected to the workspace. `reply_to_uuid` is the `id` of the email you are answering. The docs page spells that field `reyply_to_uuid` in the prose. The schema field is `reply_to_uuid`. Send the schema field.

Chapter 28 is the card that calls this reply endpoint. This chapter only logs what already happened.

---

## The HubSpot email

Create the engagement with `POST /crm/v3/objects/emails`. The properties that matter:

| Property | Value |
|---|---|
| `hs_timestamp` | When the email happened. |
| `hs_email_direction` | `INCOMING_EMAIL` for the prospect. `EMAIL` for a send from the campaign mailbox. |
| `hs_email_status` | `SENT` for a message that exists. |
| `hs_email_subject`, `hs_email_text` | Subject and body. |
| `hs_unique_id` | `instantly:<email id>`. |

Associate the contact in the same call. HubSpot's default email-to-contact association type id is 198 (`email_to_contact`). The guide is the [emails activity API](https://developers.hubspot.com/docs/api-reference/legacy/crm/activities/emails/guide).

Leave `hubspot_owner_id` out of the body. Setting it stamps a creator on the timeline. This build does not assign owners.

Before the create, search emails for `hs_unique_id` equal to `instantly:<email id>`. A hit means the message is already on the contact. Skip the create. That is also why a thread someone logged by hand does not get a twin when the webhook shows up later. Chapter 27 checks that on purpose.

---

## The deal

Open a deal when all of these are true:

- The email log returned an id. A failed log stops the function. The deal call does not run.
- The reply is a positive one: `lt_interest_status` is 1, or the event is `lead_interested`.
- It is not an auto-reply, and it is not a bounce.
- It is not Meeting Booked. A scheduling link already creates the meeting. Opening a deal here would stack a second record on top of that one.

The deal name is `(Prefix) - Person - Company`. For the conference campaign the prefix is `CONF`, so a fictional prospect looks like `(CONF) - Jordan Hale - Example Multifamily`.

`pipeline` and `dealstage` are ids from `HUBSPOT_MQL_PIPELINE_ID` and `HUBSPOT_MQL_STAGE_ID`. A search for the label `MQL` misses a stage whose label is `Intro Call Scheduled / MQL (3%)`. The id is the stable value. `require_stage_ids` in the starter refuses the bare label `MQL`.

The deal is unowned. Omit `hubspot_owner_id`.

Dedupe searches deals whose name contains the needle `(CONF) - `, prefix plus ` - `. The needle keeps `(CONF)` from matching some other prefix that merely starts with the same letters. The record that counts as "already open" is the full name. One conference can have many deals. Two deals with the same full name are a race: the webhook and the cron both missed the search and both created. `duplicate_deal_report` lists those ids. It does not delete them. A person merges or archives the extra.

---

## Safety rails

Two switches have to agree before a write.

| Switch | Writes happen when |
|---|---|
| `INSTANTLY_REPLY_TEST_MODE` | The value is `false`. Anything else, including an empty value, is test mode. Test mode builds the plan and writes nothing. |
| `HUBSPOT_ALLOW_<CLIENT>_PORTAL` | The value is the exact string `true`, and the portal id on the token matches `HUBSPOT_PORTAL_ID`. The starter spells the flag `HUBSPOT_ALLOW_CLIENT_PORTAL`. `CLIENT` is a slug you pick. |

The production portal is refused until that flag is `true`. `yes`, `TRUE`, and `1` stay refused. A token for a different portal stays refused even when the flag is on. That is the whole point of naming the portal in the env: the app will not discover a second portal and write there.

Manual backfill uses the same gate.

1. **Plan.** `build_plan` writes the email steps and the deal steps to a file. You read it.
2. **Apply.** `apply_plan` runs the writer and returns an undo file: the created email ids and deal ids.
3. **Read back.** `read_back` loads those records and checks the unique id, the deal name, and an empty owner.
4. **Undo.** Archive the ids in the undo file. Leave every other record alone. Leave owners alone even then.

`apply_plan` raises if a step includes `hubspot_owner_id`. The tests cover a failed email log, a skipped second log, and a deal that must not open.

---

## The first real yes

Pick the first positive reply you are willing to show a teammate. One email id.

1. Plan it with test mode still on. Read the JSON. Confirm the direction, the unique id, the deal name, the stage id, and the missing owner.
2. Turn the allow flag on for that one apply. Keep the webhook cron off.
3. Apply. Read the contact timeline and the deal back from HubSpot.
4. Confirm one engagement, one deal, no owner, and a second apply that skips.

That read-back is the proof. Chapter 27 is the rest of the cutover, after this one reply looks right.

---

## For the coding agent

1. Read this chapter and `starters/instantly-hubspot-replies/reply_loop.py`. Run `python3 -m unittest tests/test_reply_loop.py`.
2. Keep tokens, portal ids, campaign ids, and webhook secrets out of the repo and out of the chat. Placeholders: `<PORTAL_ID>`, `<CAMPAIGN_ID>`, `<CONTACT_ID>`, `prospect@example.com`, `https://your-app.vercel.app`.
3. Copy `routes/webhook.mjs` and `routes/cron.mjs` into the Next.js app. A missing secret is 401. A matching secret is 200. Test mode still writes nothing.
4. Search by `hs_unique_id` before creating an email. Create the deal only after the email id comes back.
5. Pass pipeline and stage ids. Leave `hubspot_owner_id` off every body.
6. Do not delete the old sync tool's webhooks. Chapter 27 creates the new ones beside them.
7. The first live apply is one reply, with a person reading the record afterward.

Part of the [GTM Coding Agent](https://github.com/shawnla90/gtm-coding-agent). Starter: `starters/instantly-hubspot-replies/`.
