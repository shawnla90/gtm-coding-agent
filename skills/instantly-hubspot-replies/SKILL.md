---
name: instantly-hubspot-replies
version: 1.1.0
description: Build the Instantly to HubSpot cold-email reply loop and the "Reply from the sending mailbox" card. Log each reply as one email thread, open an unowned MQL deal only for interested or the card's MQL button, and ship the production gotchas (campaign-name guard, vercel env pull placeholders, User-Agent, secondary email, dead-address auto-replies, workflow triggers, blocklist, seatless upload). Use when the user says "log replies to hubspot", "instantly webhook", "reply loop", "unibox", "reply from the sending mailbox", "hubspot card", "no instantly thread", "campaign name guard", "vercel env pull", "signature failure", or "go live on the reply loop".
---

# instantly-hubspot-replies

I log Instantly replies onto the HubSpot contact as real email engagements, one thread per lead. A positive reply opens an unowned deal at MQL so the team can route it. The card replies through Instantly from the same cold sending mailbox. HubSpot's own Reply button sends from the rep's inbox and breaks that thread.

The decisions are in [`reply_loop.py`](../../starters/instantly-hubspot-replies/reply_loop.py). Tests are `tests/test_reply_loop.py`. They use no network. Chapters [26](../../chapters/26-replies-into-the-crm.md), [27](../../chapters/27-reply-loop-go-live.md), and [28](../../chapters/28-reply-from-the-sending-mailbox.md) are the narrative. This skill is the build, then the gotchas I hit after it was live. Read the gotchas before you write a record. A retired mailbox is [`dead-address-refind`](../dead-address-refind/SKILL.md) and [Chapter 29](../../chapters/29-dead-address-versus-departed.md).

Names, portal ids, campaign ids, and domains below are placeholders. The client is "the client". The campaign is "a conference campaign". The guard string is `CAMPAIGN_NAME_GUARD`. The allowlist domain is `client-domain.com`.

## Inputs

- `HUBSPOT_ACCESS_TOKEN` (private app service key), `HUBSPOT_PORTAL_ID`, `HUBSPOT_ALLOW_<CLIENT>_PORTAL` (this starter uses `HUBSPOT_ALLOW_CLIENT_PORTAL`)
- `INSTANTLY_API_KEY`, `INSTANTLY_CAMPAIGN_IDS`, `INSTANTLY_CAMPAIGN_DEAL_PREFIXES`
- `INSTANTLY_TEST_CAMPAIGN_GUARD` (placeholder value `CAMPAIGN_NAME_GUARD`). Honored only while test mode is on. See gotcha 3.
- `HUBSPOT_MQL_PIPELINE_ID`, `HUBSPOT_MQL_STAGE_ID` (ids, not the label MQL)
- `INSTANTLY_WEBHOOK_SECRET`, `CRON_SECRET`, `HUBSPOT_APP_SECRET` (from the app Auth tab, never from `vercel env pull`)
- `HUBSPOT_REPLY_ALLOWLIST` (`@client-domain.com`, or full emails of the client's logged-in HubSpot users)
- `INSTANTLY_REPLY_TEST_MODE=true` until the first hand-checked reply has been applied

## How to run

```bash
python3 -m unittest tests/test_reply_loop.py
```

Build a plan with `build_plan`. Apply with `apply_plan` only when `portal_write_allowed` returns true. Read the created records back with `read_back`. Keep the undo file.

## Build

Do these in order. Do not flip test mode off in the middle.

### 1. Keys, without a HubSpot seat

The client's IT admin mints two credentials and sends them in a private channel. You do not need a paid seat, and the client does no developer work.

| Credential | Env or CLI | What it is for |
|---|---|---|
| Private app token, the service key | `HUBSPOT_ACCESS_TOKEN` on Vercel | CRM reads and writes from the app. Scopes: contacts, deals, and emails, read and write. |
| Personal access key | `hs account auth` on your machine | `hs project upload` of the card. One key per user. Scopes cannot exceed that user's permissions. |

Store both outside git, chmod `600`, as Chapter 27 shows. Print a boolean and a length when you have to prove a file is non-empty. Do not print the key.

The personal access key cannot read the app client secret. After the app exists, the admin copies that secret from the app Auth tab into `HUBSPOT_APP_SECRET` on Vercel. There is no CLI call that prints it.

### 2. The Vercel app

Deploy a Next.js app at `https://your-app.vercel.app`. Copy `routes/webhook.mjs`, `routes/cron.mjs`, and `routes/hubspot-reply.mjs` into the route handlers. The Python module decides. The route returns 401 without the shared secret and 200 with it. Test mode still writes nothing.

Cron in `vercel.json`, one page per wake:

```json
{ "crons": [{ "path": "/api/cron/poll", "schedule": "*/10 * * * *" }] }
```

Set every name in `.env.example`. Leave `INSTANTLY_REPLY_TEST_MODE=true` and the portal allow flag unset until step 7.

### 3. Log the email on the contact

Accept `reply_received` and `lead_interested`. Create one Instantly webhook per event per campaign via `POST /api/v2/webhooks`, with header `X-Instantly-Secret`. `webhook_create_body` builds the JSON. Print `redact_webhook_body`. Leave the old sync tool's webhooks in place.

The cron polls `GET /api/v2/emails` because a reply typed in the Unibox fires no webhook. Use `instantly_list_emails_request`. It sets `User-Agent`. Without that header, `?lead=` returns 403. The list endpoint allows about 20 requests a minute. One page per wake stays inside that budget.

For each message, search HubSpot emails for `hs_unique_id` equal to `instantly:<email id>` (`unique_id`). A hit is `skip`. A miss is `POST /crm/v3/objects/emails`:

| Property | Value |
|---|---|
| `hs_timestamp` | When the email happened. |
| `hs_email_direction` | `INCOMING_EMAIL` for the prospect. `EMAIL` for a send from the campaign mailbox. |
| `hs_email_status` | `SENT` for a message that exists. |
| `hs_email_subject`, `hs_email_text` | Subject and body. |
| `hs_unique_id` | `instantly:<email id>`. |

Associate the contact in the same call. Association type id 198 (`email_to_contact`), from `contact_association`. Leave `hubspot_owner_id` out. Every reply on that lead is another engagement on the same contact, so the timeline is one thread. Do not log a note in place of the email.

Call `campaign_in_scope` before the webhook handler and before the poll writes anything. The id list is always on. The name guard is not. Gotcha 3.

### 4. Open the deal, or don't

`should_open_deal` is the whole rule:

- The email log returned an id. A failed log does not open a deal.
- `lead_interested`, or `lt_interest_status` 1, opens the deal.
- The card's Open MQL button opens the deal. Pass `manual_mql=true`. That is a person deciding, not the webhook.
- `reply_received` alone does not open a deal. It only logs the email. Reason string: `reply received is not a deal`.
- Auto-replies, bounces, and Meeting Booked stay closed, including when someone hits Open MQL on an auto-reply.

Deal name is `(Prefix) - Person - Company`. For a conference campaign the prefix is `CONF`. `pipeline` and `dealstage` are `HUBSPOT_MQL_PIPELINE_ID` and `HUBSPOT_MQL_STAGE_ID`. Omit `hubspot_owner_id` so the deal is unowned and the team routes it. Search with the needle from `dedupe_needle`, then match the full name.

Do not write a HubSpot property such as `instantly_lead_status` for `auto_reply`, `bounce`, or `out_of_office`. `should_write_lead_status` is true only for `interested`, `lead_interested`, and `1`. Gotcha 8.

### 5. The card

Private static app, developer platform `2025.2`. Project: `starters/instantly-hubspot-replies/hubspot-card/`. Card name in the library: "Reply from the sending mailbox". Location `crm.record.tab` on `CONTACT`.

`permittedUrls.fetch` and the `BACKEND` constant are both `https://your-app.vercel.app`. Use `hubspot.fetch`. The card shows `Sends from <mailbox> in the same thread` before Send enables.

From your machine, with the personal access key:

```bash
cd starters/instantly-hubspot-replies/hubspot-card
hs project install-deps
hs project upload
```

The admin installs the app and adds the card from the card library. That is a CRM click. They do not edit the project.

Thread load: `GET` your `/api/hubspot/thread`. `thread_view` maps the result.

- HTTP 200 and zero messages: render `No Instantly thread`. Send and Open MQL stay disabled. This is the empty state, not an auth failure.
- Anything other than 200: auth or signature failure. Do not label that as an empty thread.

Send: `POST /api/hubspot/reply` with `eaccount`, `reply_to_uuid`, `subject`, and `text`. The backend verifies the HubSpot v3 signature (`signature_is_valid`, 5 minute window, client secret), then `user_can_reply` against `HUBSPOT_REPLY_ALLOWLIST`, then `POST https://api.instantly.ai/api/v2/emails/reply`. Log the outbound engagement with `hs_email_direction` `EMAIL` and `hs_unique_id` `instantly:<new email id>`.

Open MQL: the same route with `manualMql: true`. No Instantly send. Same plan, apply, undo file, and read-back. No owner.

The user email is the one HubSpot signed, from `context.user.email` in the signed body. An allowlist entry of `@client-domain.com` allows every logged-in user on that domain. An empty list means nobody sends.

### 6. The first positive reply, by hand

I logged the first positive reply by hand before the automation was allowed to write.

1. `build_plan` with test mode still on. Read the JSON. Direction, unique id, deal name, stage id, no owner.
2. Turn the portal allow flag on for that one apply. Leave the cron and the live webhook path writing nothing.
3. `apply_plan`. Keep the undo file (created email ids and deal ids).
4. `read_back`. One engagement, one unowned deal, a second apply that skips.

`apply_plan` raises if a step includes `hubspot_owner_id`. Undo archives the ids in the undo file and leaves every other record, and every owner, alone.

### 7. Flip it

After that read-back looks right: `HUBSPOT_ALLOW_<CLIENT>_PORTAL=true` and `INSTANTLY_REPLY_TEST_MODE=false`. Watch the next reply land on its own. Replay it and watch the unique id skip.

Confirm `campaign_suppressed_by_guard` is false for the live campaign name once test mode is off, including when that name contains `CAMPAIGN_NAME_GUARD`. Gotcha 3.

## Gotchas

These are the failures from the live loop. Each one is silent if you only test the happy path.

### 1. "No Instantly thread" is a 200 with zero messages

The card exists because HubSpot's Reply sends from the rep's connected inbox. The cold thread lives on the Instantly sending mailbox. A native reply changes From and starts a different conversation. The card replies through Instantly, `eaccount` plus `reply_to_uuid`, same mailbox, same thread.

When the lead has no cold mail, Instantly's list call succeeds and returns no messages. The backend returns 200 and an empty list. The card copy is `No Instantly thread`. Send stays off. A 401 or 403 is a different screen: signature, secret, or allowlist. Do not treat the empty list as a bad token, and do not treat a 401 as "this contact was never emailed."

`thread_view(http_status=200, messages=[])` is `no_instantly_thread`. `thread_view(http_status=401, messages=[])` is `auth_failure`.

### 2. What is allowed to open a deal

Webhooks to subscribe, per campaign: `reply_received` and `lead_interested`. Header `X-Instantly-Secret`. The cron is the backstop, including Unibox replies.

Every message is an email engagement. Dedupe key `hs_unique_id` = `instantly:<id>`. Same contact, so it is one thread.

The deal opens at MQL, unowned, only when:

- the event is `lead_interested` or `lt_interest_status` is 1, or
- the rep pressed Open MQL on the card (`manual_mql`)

`reply_received` alone logs the email and stops. I had the first version open a deal on every reply. Auto-replies and "thanks, not now" became pipeline. `should_open_deal` is the gate. The deal still waits until the email log returns an id.

### 3. The campaign-name guard is test-mode only

I had a block that skipped any campaign whose name contained `CAMPAIGN_NAME_GUARD`. It was there so a test deploy would not touch that campaign. I left the match unconditional. Test mode had nothing to do with it.

Effect on a live campaign whose name contained the guard: the card hid the thread, Send never enabled, and both the poll and the webhooks dropped the events. No error. The campaign looked quiet.

The guard runs only when `INSTANTLY_REPLY_TEST_MODE` is on:

```python
if test_mode and "CAMPAIGN_NAME_GUARD" in campaign_name:
    return  # hide, block Send, skip poll and webhook
```

`campaign_suppressed_by_guard` returns false as soon as test mode is off, even if the live name still contains the guard. `campaign_in_scope` always filters by `INSTANTLY_CAMPAIGN_IDS`. That id list is not the name guard. Call the same function from the thread loader, Send, the webhook, and the cron. A guard on one of those paths still breaks the other three.

Deleting the env var is not the fix if the string is hardcoded. The flag check has to be in the code.

### 4. `vercel env pull` is not the client secret

Signature failures send you looking at `HUBSPOT_APP_SECRET`. `vercel env pull` does not return sensitive production values. Depending on the CLI, the file gets an empty string or the literal `[SENSITIVE]`. `pulled_secret_is_usable` rejects both. An older pull can also hand you a non-empty placeholder that is still not the secret.

I hashed the placeholder and called the signature code wrong. The deployed function was using a different value, or the right one, and I could not tell from the file.

Copy the client secret from the app Auth tab again. Set it in the Vercel dashboard. Redeploy. Debug against a live signed card request. Print a boolean and a length. Do not print the secret, and do not paste a pulled `HUBSPOT_APP_SECRET` into a local HMAC script. The same rule applies to every other sensitive var in that file.

### 5. `GET /api/v2/emails?lead=` wants a User-Agent, and you cannot pin the mailbox on the lead

A request with no `User-Agent` gets 403 on `GET /api/v2/emails?lead=`. The default client in a lot of runtimes sends none. `instantly_list_emails_request` sets `User-Agent: gtm-reply-loop/1.0`. Send one on the campaign poll too. Budget is about 20 requests a minute. A tight loop spends the minute and the rest of the hour is blind.

The Instantly API cannot assign a specific sender mailbox to a lead. Create-lead has `assigned_to`, and that field is a workspace user id, not an email account. There is no `eaccount` on lead create. `reject_mailbox_on_lead_create` raises if you try to pass one. The mailbox is chosen by the campaign. You pin it at reply time, on `POST /api/v2/emails/reply`, with `eaccount` set to the cold sending mailbox and `reply_to_uuid` set to the message you are answering. The docs prose has misspelled that field. The schema field is `reply_to_uuid`.

### 6. Changing the primary email drops the old one

A CRM v3 `PATCH` of `email` replaces the primary and removes the previous address from the contact. It does not move it to `hs_additional_emails`. That property is read-only on v3. Including it on the PATCH returns `READ_ONLY_VALUE` and still drops the old address.

`email_swap_plan` is two calls, in this order, after a search shows the new address is not already on a different contact:

1. `PATCH /crm/v3/objects/contacts/{contactId}` with `properties.email` set to the new address.
2. `PUT /contacts/v1/secondary-email/{contactId}/email/{oldEmail}` on the legacy contacts API. URL-encode the old address (`@` is `%40`).

Read `email` and `hs_additional_emails` back. Primary is the new address. The old one is on the secondary list. Owner is unchanged. The undo file has both addresses before the first call. Chapter 29 and `dead-address-refind` are the full swap, including the human yes.

### 7. "No longer in use" is a dead address, and it looks like a reply

An auto-reply that says the address is no longer in use does not mean the person left. I treated the first one as a departure. Employment sources still had them at the company. The company was moving staff onto a second domain.

Instantly will fill reply status, reply date, and a snippet from that auto-reply. The lead looks answered. `reply_fields_prove_interest` ignores those three fields. Classify the body. A retired mailbox is not `lead_interested` and it does not open a deal.

Follow [`dead-address-refind`](../dead-address-refind/SKILL.md): stop mailing the dead box, learn the new domain and the pattern from known-good addresses, run the enrichment waterfall, confirm with more than one verifier plus a made-up address on the same domain as a catch-all control, swap the CRM email with the two-call plan in gotcha 6, then have a person re-add the lead so the campaign can send again. The worker does not add and does not send.

### 8. The client's existing workflows fire on any status

The portal already had workflows. One of them was the "positive responses, then deal creation" style: enrollment was any non-empty Instantly lead-status, not the value `interested`. Writing `auto_reply`, `bounce`, or `out_of_office` into that property enrolled the contact. The workflow created an owned deal and emailed people on the team. My code never set `hubspot_owner_id`. The workflow did.

`should_write_lead_status` writes the property only for a positive status (`interested` / `lead_interested` / `1`). Leave it blank for everything else.

The other fix belongs to the client: change the enrollment trigger to the value `interested` before you write the wider set. Audit Automation, then Workflows, before the first property write and before the first deal. Chapter 27 has the owner check. This is the same pass. Read every workflow whose trigger is "property is known" or "has ever been equal to" on the lead-status field, and every one that sets an owner on deal create.

### 9. A 200 on lead status can be a no-op, and interest writes loop

`PATCH /api/v2/leads/{id}` with `lt_interest_status` can return 200 while the status on the lead is unchanged. `status_write_stuck` is that case. I treated the 200 as "the lead is parked" and the sequence kept sending.

The reliable park is a blocklist entry: `POST /api/v2/block-lists-entries` with `{"bl_value": "prospect@example.com"}`. `blocklist_entry_body` builds it. Scope `block_list_entries:create`. Read the entry back. A skip or a blocklist hit on a later campaign add means they are not in the sequence, whatever the HTTP status was.

Interest-status changes fire webhooks (`lead_interested` and the rest). Those webhooks write HubSpot fields. If your handler writes interest status back to Instantly, you loop. Log the email, maybe open the deal, and do not PATCH Instantly interest from the webhook that the PATCH just caused. The email unique id stops a second engagement. It does not stop a status ping-pong.

### 10. No seat, and who is allowed to press Send

Access is the service key plus the personal access key from the client's IT admin. That pair is enough to call the API and to upload the card from the builder's own machine. The client does not need a developer on the project. They add the card from the library after the upload.

Send is not "anyone who can see the contact." `HUBSPOT_REPLY_ALLOWLIST` is the client's own logged-in HubSpot users, matched by email domain (`@client-domain.com`) or by full email. `user_can_reply` does that check on the server. Hiding the button is a convenience. A user off the domain gets 403. The From address is still `eaccount`, not the rep.

### 11. Every HubSpot write is plan, apply, undo, read-back

I did not turn the automation on against an empty portal and hope. The first positive reply was one record: plan file, apply, undo file, read-back of the unique id, the deal name, and an empty owner. Then the flag flipped.

Same shape for the email swap, the manual MQL deal, and a backfill. Never set `hubspot_owner_id` on a create or an update. Never "fix" an owner that a workflow stamped. That is a workflow change, gotcha 8, not a second write.

## Do

- Run the unit tests after any change to `reply_loop.py`.
- Plan, apply, undo, read back. The first live reply is one record, with a person watching.
- Store the service key and the personal access key outside the repo. Print a boolean and a length when you have to prove a key is present.
- Copy the client secret from the app Auth tab into `HUBSPOT_APP_SECRET`.
- Call `campaign_in_scope` from the thread loader, Send, the webhook, and the cron.
- Send a `User-Agent` on every `GET /api/v2/emails`.
- Park a lead with the blocklist. Read the lead back if you also tried a status PATCH.

## Don't

- Don't open a deal on `reply_received` alone, or when the email log failed.
- Don't set `hubspot_owner_id` on a create or an update.
- Don't treat the stage label MQL as the stage id.
- Don't leave a campaign-name guard running when `INSTANTLY_REPLY_TEST_MODE` is false.
- Don't debug a signature with a secret from `vercel env pull`.
- Don't write `auto_reply`, `bounce`, or `out_of_office` into the lead-status property until the workflow trigger is `interested`.
- Don't treat a 200 from a lead-status PATCH as proof the status changed.
- Don't assign `eaccount` on lead create. Instantly will not pin that mailbox.
- Don't delete the previous vendor's webhooks as part of this skill.
- Don't subscribe to `auto_reply_received` unless the create-webhook enum lists it. Use `reply_received` plus the poll.
- Don't print tokens, portal record ids, or the webhook secret.
- Don't send from the rep's connected inbox. That is a different thread.
- Don't render a 200 with zero messages as an auth error, or a non-200 as "No Instantly thread".

## Related

- `../../chapters/26-replies-into-the-crm.md`
- `../../chapters/27-reply-loop-go-live.md`
- `../../chapters/28-reply-from-the-sending-mailbox.md`
- `../../chapters/29-dead-address-versus-departed.md`
- `../../skills/dead-address-refind/SKILL.md` for a retired mailbox that is not a departure
