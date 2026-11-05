# Chapter 28: Reply from the Sending Mailbox

**HubSpot's native Reply sends from the rep's connected inbox. The cold thread lives on a different mailbox, the one Instantly used. A native reply changes the From address and breaks the thread. The card on the contact sends through Instantly, from that same mailbox, and the backend logs the send with the same idempotency key as Chapter 26.**

The build steps and the gotchas are in [`skills/instantly-hubspot-replies/SKILL.md`](../skills/instantly-hubspot-replies/SKILL.md). The card in the library is "Reply from the sending mailbox".

---

## TL;DR

- The card is a React UI extension on a private static app, HubSpot developer projects platform `2025.2`.
- It lists the thread, then shows `Sends from <mailbox> in the same thread` before the send button enables.
- A 200 with zero messages renders `No Instantly thread`. That is the empty state. A 401 or 403 is an auth failure.
- Open MQL opens the unowned deal from Chapter 26. `reply_received` alone does not.
- The card calls `https://your-app.vercel.app`. That origin is `permittedUrls.fetch` on the app, and it is the `BACKEND` constant in the card.
- The backend verifies HubSpot's v3 signature with the app client secret, checks an allowlist of the client's logged-in users by email domain, then calls `POST /api/v2/emails/reply` with `eaccount` and `reply_to_uuid`.
- Install with `hs project upload`. The admin adds the card from the card library and copies the client secret from the Auth tab.

The sample project is `starters/instantly-hubspot-replies/hubspot-card/`.

---

## Why the native button is the wrong send

The prospect replied to `sender@example.com`. That mailbox is connected to Instantly. The rep's day-to-day inbox is a different address, connected to HubSpot. HubSpot's Reply button uses the rep's inbox. The prospect sees a new From, a new thread, and no tie back to the conference email they answered.

The send you want is the Instantly reply from Chapter 26:

```json
{
  "eaccount": "sender@example.com",
  "reply_to_uuid": "<EMAIL_ID>",
  "subject": "Re: conference",
  "body": { "text": "Here is the one-pager." }
}
```

`eaccount` is the campaign mailbox. `reply_to_uuid` is the id of the message you are answering. Instantly sends it as a reply on that thread. The backend then logs the outbound engagement with `hs_email_direction` of `EMAIL` and `hs_unique_id` of `instantly:<new email id>`. The same skip rule applies if the cron sees that send again.

---

## The card

Platform `2025.2`, distribution `private`, auth `static`. One portal installs it. The card location is `crm.record.tab` on `CONTACT`.

`src/app/app-hsmeta.json` carries the allowlist HubSpot enforces before the request leaves the CRM:

```json
"permittedUrls": {
  "fetch": ["https://your-app.vercel.app"],
  "iframe": [],
  "img": []
}
```

Entries are prefixes. `https://your-app.vercel.app` allows `https://your-app.vercel.app/api/hubspot/reply`. A URL missing from the list fails in the CRM with 403, before your server sees it. Wildcards are not accepted, and `localhost` is not a permitted fetch URL. The guide is [fetching data for UI extensions](https://developers.hubspot.com/docs/apps/developer-platform/add-features/ui-extensions/fetching-data).

In `ReplyCard.jsx` the origin is one constant:

```jsx
const BACKEND = "https://your-app.vercel.app";

const response = await hubspot.fetch(`${BACKEND}/api/hubspot/reply`, {
  method: "POST",
  body: { contactId, replyToUuid, eaccount, subject, text }
});
```

Use `hubspot.fetch`. `window.fetch` is not available in the card, and a relative path is not a legal URL for this call.

The card loads the thread first. Until `eaccount` is on screen, the send button stays disabled. The line the rep reads is `Sends from sender@example.com in the same thread.` That sentence is the check. If the mailbox is wrong, they do not send.

The thread route calls `GET /api/v2/emails?lead=` with a `User-Agent`. Without the header Instantly returns 403, and a 403 is not an empty thread. `thread_view` maps a 200 and an empty list to `no_instantly_thread`. The card text is `No Instantly thread`. Send and Open MQL stay disabled. There is nothing to answer, and there is no email id to hang a deal on.

Open MQL posts `{ contactId, manualMql: true, replyToUuid }` to the same reply route. The handler verifies the signature, checks the allowlist, and runs `should_open_deal` with `manual_mql` set. It does not call Instantly to send. The deal is unowned, at the MQL stage id. An auto-reply still does not open one.

A campaign-name guard that is still on will hide this thread, disable Send, and skip the poll for a live campaign whose name contains `CAMPAIGN_NAME_GUARD`. `campaign_suppressed_by_guard` is true only while `INSTANTLY_REPLY_TEST_MODE` is on. Chapter 26 is that bug. Call the same function here, in the webhook, and in the cron.

---

## Signed requests

HubSpot signs the `hubspot.fetch` call. The backend verifies version 3 before it reads the body as a command.

Headers: `X-HubSpot-Signature-v3` and `X-HubSpot-Request-Timestamp`. The secret is the app client secret, `HUBSPOT_APP_SECRET`, the value from the Auth tab in Chapter 27.

The check, from HubSpot's [request validation](https://developers.hubspot.com/docs/apps/developer-platform/build-apps/authentication/request-validation) page:

1. Reject a timestamp more than 5 minutes from now.
2. Build the string `method + uri + body + timestamp`. Decode the URL-encoded characters HubSpot lists (`%3A` back to `:`, and the rest of that table). Leave the `?` that starts the query string encoded as it arrived.
3. HMAC-SHA256 that string with the client secret. Base64-encode the digest.
4. Compare to the header with a constant-time compare.

`signature_is_valid` in the starter is that check. A bad signature is 401. The card never sees the client secret.

When the check fails, do not pull `HUBSPOT_APP_SECRET` with `vercel env pull` and hash that. Sensitive values come back empty or as the literal `[SENSITIVE]`. `pulled_secret_is_usable` rejects both, and a pull that looks non-empty can still be a placeholder. Copy the client secret from the Auth tab into the Vercel dashboard, redeploy, and retry the card. Chapter 27 has the same warning. Print a boolean and a length, not the secret.

After the signature, check the HubSpot user email against `HUBSPOT_REPLY_ALLOWLIST`. Anyone else gets 403 and a disabled composer. The allowlist is the security boundary. Hiding the button in the card is a convenience. The server still checks.

Then the server calls Instantly, logs the outbound email, and returns. Test mode and the portal allow flag from Chapter 26 still apply. A signed request from an allowed user writes nothing while test mode is on.

---

## Install

The CLI is authenticated with the personal access key from Chapter 27.

```bash
cd starters/instantly-hubspot-replies/hubspot-card
hs project install-deps
hs project upload
```

`hs project upload` builds and deploys. The docs for the card flow are [create an app card](https://developers.hubspot.com/docs/apps/developer-platform/add-features/ui-extensions/extension-points/app-cards/create-an-app-card). Pass `--account` when the default CLI account is a different portal.

Then, in the portal:

1. Install the app. Private static distribution installs into the one portal the project targets.
2. Open a contact. Customize record, then Card library, then App cards. Add "Reply from the sending mailbox".
3. The admin opens the app's Auth tab, copies the client secret, and puts it in `HUBSPOT_APP_SECRET` on Vercel. Redeploy so the function sees it.

The sample `*-hsmeta.json` files omit the preview image the CLI template usually adds. `hs project add` (choose Card) on a fresh project writes that image for you. Keep this folder as the shape to compare, and let the CLI fill the boilerplate when you are uploading for real.

`node_modules` stays untracked. The `package.json` in `cards/` names `@hubspot/ui-extensions` and React. `hs project install-deps` is what resolves them.

---

## Who can send

`HUBSPOT_REPLY_ALLOWLIST` is the client's own logged-in HubSpot users. An entry of `@client-domain.com` allows every user whose login email is on that domain. A full email allows that one user. `user_can_reply` compares them case-insensitively, and it does not treat `client-domain.com.evil.example` as the client's domain. An empty list means nobody sends.

The email you check is the one HubSpot signed, from `context.user.email` in the signed body. Do not trust an email that arrived on an unsigned request.

The rep can still read the thread when they are off the list. They cannot send. Sending stays on the campaign mailbox either way, so a person on the list is not "replying as themselves". The From address is `eaccount`. Say that in the sentence on the card every time.

---

## For the coding agent

1. Read this chapter, the files under `hubspot-card/`, and the Build and Gotchas sections in `skills/instantly-hubspot-replies/SKILL.md`. Confirm `BACKEND` and `permittedUrls.fetch` are the same https origin.
2. Do not put the client secret, the private app token, or a personal access key in the project files.
3. Verify the v3 signature before the Instantly call. Reject a stale timestamp.
4. Enforce the allowlist on the server.
5. Log the outbound email with `hs_unique_id` and without `hubspot_owner_id`.
6. Show the mailbox on the card before enabling send.

Part of the [GTM Coding Agent](https://github.com/shawnla90/gtm-coding-agent). Previous: [Chapter 27](./27-reply-loop-go-live.md). The retired-mailbox case is [Chapter 29](./29-dead-address-versus-departed.md).
