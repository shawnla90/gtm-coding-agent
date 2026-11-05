# Chapter 27: Going Live on the Reply Loop

**Chapter 26 is the loop. This chapter is the cutover: keys without a HubSpot seat, the env vars, a deploy that proves 401 and 200, webhooks created beside the old sync tool, and a check that nothing in the portal assigns an owner the moment the deal exists.**

Same client as Chapter 26. A proptech / multifamily services client, a conference campaign, placeholders only.

---

## TL;DR

- The admin mints a private app token for the API and a personal access key for the CLI, and sends both privately. You chmod them `600` outside git.
- A personal access key can upload the project. It cannot read the app's client secret. That value is copied from the app's Auth tab.
- The production portal stays dark until `HUBSPOT_ALLOW_<CLIENT>_PORTAL` is the string `true` and `INSTANTLY_REPLY_TEST_MODE` is `false`.
- Webhook and cron routes return 401 without the secret and 200 with it.
- Create one Instantly webhook per event per campaign. Leave the old tool's webhooks in place.
- A hand-logged thread uses the same `hs_unique_id`, so the webhook does not log it twice.

---

## Keys without a seat

You can run this without a paid HubSpot seat. What you need is an admin who will mint two credentials and hand them over in a private channel.

| Credential | What it is | Who uses it |
|---|---|---|
| Private app token (the service key) | A static token for the CRM API. This is `HUBSPOT_ACCESS_TOKEN` on Vercel. | The Next.js app. |
| Personal access key | A key for the HubSpot CLI, scoped to the permissions of the user who created it. | You, on your machine, for `hs project upload`. |

The admin creates the private app in the portal, picks the CRM scopes the loop needs (contacts, deals, emails, read and write), and copies the token once. They create the personal access key under Development, then Keys, then Personal access key. One personal access key per user per account. Scopes cannot exceed that user's own permissions. If the admin lacks developer-tools access, the key cannot upload a project. HubSpot's page on this is [personal access keys](https://developers.hubspot.com/docs/developer-tooling/local-development/hubspot-cli/personal-access-key).

They send the two values privately. You do not ask for them in a chat transcript.

On disk, outside every repo:

```bash
umask 077
mkdir -p ~/.config/gtm-keys
install -m 600 /dev/null ~/.config/gtm-keys/hubspot-service-key
install -m 600 /dev/null ~/.config/gtm-keys/hubspot-pak
# paste each value into its file in an editor. do not echo it.
chmod 600 ~/.config/gtm-keys/hubspot-service-key ~/.config/gtm-keys/hubspot-pak
```

Prove a file is non-empty without printing it:

```bash
python3 -c "from pathlib import Path; p=Path.home()/'.config/gtm-keys/hubspot-service-key'; t=p.read_text().strip(); print(bool(t), len(t))"
```

You want `True` and a length. [Chapter 04](./04-oauth-cli-apis.md) is the same rule for every other key, including the local vault if you already keep one.

The CLI auth command that takes a key is non-interactive:

```bash
set +o history
hs account auth --account client --personal-access-key "$(< ~/.config/gtm-keys/hubspot-pak)"
set -o history
```

The shell history stores the command, not the file contents. A process list can still see argv for the moment the command runs. Prefer the interactive prompt when you are at the keyboard. Use the file form when a script has to auth on its own. `~/.hscli/config.yml` then holds the key, so that file is chmod `600` too.

What the personal access key can do: `hs project upload`, `hs account`, and API calls that match the scopes chosen when the key was created.

What it cannot do: read an app's client secret. The secret lives on the app's Auth tab. The admin copies it and you put it in `HUBSPOT_APP_SECRET` on the backend. Chapter 28 needs that secret to verify signed card requests. There is no CLI call that prints it for you. If a command claims it fetched the client secret, stop and check what it actually returned.

---

## Env vars

Names only. Values stay in Vercel and in the chmod 600 files.

| Name | Role |
|---|---|
| `HUBSPOT_ALLOW_<CLIENT>_PORTAL` | Exact string `true` before any write to that portal. The starter's name is `HUBSPOT_ALLOW_CLIENT_PORTAL`. |
| `HUBSPOT_PORTAL_ID` | The portal the token must belong to. A mismatch refuses the write. |
| `HUBSPOT_ACCESS_TOKEN` | Private app token. |
| `INSTANTLY_API_KEY` | Bearer token for API v2. |
| `INSTANTLY_REPLY_TEST_MODE` | `false` only after the first hand-checked reply. Default the example to `true`. |
| `INSTANTLY_CAMPAIGN_IDS` | Comma-separated campaign ids. One prefix each. |
| `INSTANTLY_CAMPAIGN_DEAL_PREFIXES` | Comma-separated prefixes, same order and same length. `CONF` for the conference campaign. |
| `HUBSPOT_MQL_PIPELINE_ID` | Pipeline id. Not the label. |
| `HUBSPOT_MQL_STAGE_ID` | Stage id for stage 1. Not the label `MQL`. |
| `INSTANTLY_WEBHOOK_SECRET` | Compared to the `X-Instantly-Secret` header. |
| `CRON_SECRET` | Vercel sends `Authorization: Bearer <CRON_SECRET>`. |
| `HUBSPOT_APP_SECRET` | App client secret, from the Auth tab. Signature verification only. |
| `HUBSPOT_REPLY_ALLOWLIST` | HubSpot user emails allowed to send from the card. |

`campaign_prefix_map` refuses a list of ids whose length differs from the prefix list. A short prefix list would attach the wrong deal name to a campaign. Fail the boot instead.

---

## Deploy, then prove the doors

Deploy the Next.js app to Vercel at `https://your-app.vercel.app`. Set the env vars there. Do not set `INSTANTLY_REPLY_TEST_MODE` to `false` yet.

Cron, in `vercel.json`:

```json
{ "crons": [{ "path": "/api/cron/poll", "schedule": "*/10 * * * *" }] }
```

`GET /api/v2/emails` allows about 20 requests a minute. One page each time the cron wakes is inside that budget. A tight loop is how you spend the minute and miss the rest of the hour.

Check the doors before you point Instantly at them:

```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST https://your-app.vercel.app/api/instantly/webhook
curl -s -o /dev/null -w "%{http_code}\n" -X POST https://your-app.vercel.app/api/instantly/webhook \
  -H "X-Instantly-Secret: $INSTANTLY_WEBHOOK_SECRET"
curl -s -o /dev/null -w "%{http_code}\n" https://your-app.vercel.app/api/cron/poll
curl -s -o /dev/null -w "%{http_code}\n" https://your-app.vercel.app/api/cron/poll \
  -H "Authorization: Bearer $CRON_SECRET"
```

You want `401`, then `200`, then `401`, then `200`. The 200 from the cron in test mode means "accepted, wrote nothing". Read the body. `wrote` stays false until test mode is off and the allow flag is on.

---

## Webhooks, beside the old ones

Create them from the API. One subscription per event per campaign. For this cutover the events are `reply_received` and `lead_interested`.

```bash
curl -s -X POST https://api.instantly.ai/api/v2/webhooks \
  -H "Authorization: Bearer $INSTANTLY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "target_hook_url": "https://your-app.vercel.app/api/instantly/webhook",
    "event_type": "reply_received",
    "campaign": "<CAMPAIGN_ID>",
    "name": "reply loop reply_received",
    "headers": { "X-Instantly-Secret": "<INSTANTLY_WEBHOOK_SECRET>" }
  }'
```

Repeat for `lead_interested`, and for each campaign id. The scope on the key is `webhooks:create` or a wider create scope. `webhook_create_body` in the starter builds the same JSON, and `redact_webhook_body` is what you print.

The events guide also names `auto_reply_received`. On 2026-11-05 the create-webhook `event_type` enum did not include that name. `subscription_event` raises if you pass it. Retired-mailbox notices often arrive as `reply_received` anyway, which is why the poll exists. Chapter 29 is that case. Add `auto_reply_received` as its own subscription only after the enum lists it.

Leave the old sync tool's webhooks where they are. Two listeners can receive the same reply. Your idempotency key makes the double delivery a skip. Removing the old hooks is a separate decision, made by the client, after this loop has logged a few real replies.

---

## The hand-logged thread

If you already logged a thread by hand during the proof in Chapter 26, you used `hs_unique_id` of `instantly:<email id>`. When the webhook fires for that same email, the search finds the engagement and the log step is `skip`. Run that case once on purpose: hand-log a fixture email id in a test portal, or re-apply the first real reply, and confirm the contact gained no second engagement.

Deal dedupe is the full name `(Prefix) - Person - Company`, searched with the needle `(Prefix) - `. A second apply skips the deal too.

---

## Owners

This app never sends `hubspot_owner_id`. A workflow in the portal can still assign one.

Before the first real deal, open Automation, then Workflows. Look at deal-based and contact-based workflows whose trigger is "record created" or "property changed" on this pipeline. Read any action that sets Contact owner or Deal owner. A round-robin on deal create will stamp an owner on the unowned deal in the same second you create it.

If one of those workflows matches this pipeline, exclude the pipeline or turn the action off before apply. Then create the proof deal from Chapter 26 again, if you are still in a test portal, and read `hubspot_owner_id` back. Empty is the result you want. `read_back` flags a record that comes back with an owner.

---

## Order of the flip

1. Keys on disk, chmod 600, boolean and length only.
2. Env vars set. Test mode still true. Allow flag still off.
3. Deploy. 401 and 200 as above.
4. Webhooks created. Old webhooks still present.
5. One real positive reply, planned and applied by hand, read back, no owner.
6. `HUBSPOT_ALLOW_<CLIENT>_PORTAL=true` and `INSTANTLY_REPLY_TEST_MODE=false`.
7. Watch the next reply land on its own. Then watch the one after that skip if you replay it.

Part of the [GTM Coding Agent](https://github.com/shawnla90/gtm-coding-agent). Previous: [Chapter 26](./26-replies-into-the-crm.md). Next: [Chapter 28](./28-reply-from-the-sending-mailbox.md).
