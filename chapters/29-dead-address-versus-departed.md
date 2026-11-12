# Chapter 29: Dead Address versus Departed

**A mailbox auto-replied that the address was no longer in use and was not monitored, and asked us to contact a colleague. The first read was "he left." Moltsets, Apollo, Prospeo, and LinkedIn all still had him at the company, and the operator knew he had not left. The company was moving staff onto a second Microsoft 365 domain. The old mailbox had been retired. The new address was first initial plus last name on that domain.**

The client is the same proptech / multifamily services client, on the same conference campaign. The person in the walkthrough is Jordan Hale. The domains are `example.com` and `example.net`. None of these are the client's records.

---

## TL;DR

- An auto-reply is not proof of a departure. Instantly can still fill reply status, reply date, and a snippet, so the lead looks answered. Check employment, then look for the new address.
- Find the second domain from other contacts at the account, and from MX, TXT, and SPF.
- Learn the pattern from known-good addresses. Run the email waterfall against the new domain. Verify with MillionVerifier, ZeroBounce, and NeverBounce, plus a made-up address on each domain as a catch-all control.
- A dead mailbox can still come back "valid". It exists, and it auto-replies.
- Moltsets grade F means no data. Treat it like C. D is the hard invalid.
- Swap only with a yes: PATCH the new primary, then PUT the old address back through the legacy secondary-email endpoint. `hs_additional_emails` is read-only on v3. Plan, undo file, read-back. Then re-add the lead and read the skipped and blocklisted counts.
- The later automation may stop the lead, write the note, re-find, and post a summary. It does not add, and it does not send.

The recipe is `skills/dead-address-refind/SKILL.md`. The functions are in `starters/instantly-hubspot-replies/reply_loop.py`. Grades are [Chapter 23](./23-reachability-grading.md). The reply loop's gotchas, including the workflow that fires on any lead status, are in `skills/instantly-hubspot-replies/SKILL.md`.

---

## The reply

The body was the usual retired-mailbox note: this email address is no longer in use and is not monitored, please contact a colleague.

That sentence is about the mailbox. It does not say he resigned. It does not name a new employer. The first pass treated it as a job change anyway, because "no longer" sounds like "gone".

Instantly had already stored a reply status, a reply date, and a snippet. The row looked like a person had written back. `reply_fields_prove_interest` ignores those three fields and reads the body. This body is `address_retired`. It does not open a deal, and it is not a reason to write `interested` on the contact. Writing `auto_reply` into a lead-status property is its own problem: Chapter 27, the workflow that enrolls on any non-empty status.

Then the other sources lined up the other way. Moltsets, Apollo, Prospeo, and LinkedIn still had him current. The operator already knew he had not left. Four data sources and a person who knew the account beat one auto-reply.

`classify("reply_received", text)` returns `address_retired` for that wording. `next_action` with `still_at_company=True` returns `stop_note_refind`. Stop the sequence so it does not mail the dead box again. Write a note. Look for the new address. Post the summary. Do not call it a departure yet.

If the text really says he left ("no longer with", "left the company") and the employment sources agree he is gone, the action is `hold_left_company`. You do not invent a new address at the old company for someone who has left. If the text says he left and the employment sources still say he is there, you are back to `stop_note_refind`. The text is not proof.

---

## The second domain

Other contacts at the same account had already started showing up on `example.net`. That is the first place to look. People move domain by domain during a tenant migration, and the coworkers often flip before the person you are stuck on.

Then the DNS:

```bash
dig MX example.net +short
dig TXT example.net +short
dig MX example.com +short
dig TXT example.com +short
```

A Microsoft 365 domain tends to show an MX host ending in `mail.protection.outlook.com`, and an SPF record that includes `spf.protection.outlook.com`. `looks_like_microsoft_365` checks for those two strings. A hit means "this domain receives mail on Microsoft 365". It does not mean the candidate address exists.

On this account the new domain was the second Microsoft 365 tenant, and the pattern on known-good addresses was first initial plus last name: `anguyen@example.net`, `rchen@example.net`. `learn_initial_last` returns the pattern only when every sample matches. One address in `first.last` form and the function returns nothing. You stop and look, instead of guessing a pattern the samples do not share.

Jordan Hale on that pattern is `jhale@example.net`. That string is a hypothesis until the waterfall and the verifiers say otherwise.

---

## Waterfall, then three verifiers

Run the email waterfall you already use against the new domain. In this build that waterfall is Floqer. Point it at `example.net`, not at the old domain. You are trying to find the new mailbox, and the old one will keep "finding" the address that just auto-replied.

Then verify. Three vendors: MillionVerifier, ZeroBounce, NeverBounce. On each domain, include a made-up local part as a control, `not-a-person-zz99@example.com` and `not-a-person-zz99@example.net`.

| Candidate | Control on that domain | Reading |
|---|---|---|
| All three say valid | All three say invalid | `verified` |
| All three say valid | Any one says valid | `catch_all` |
| Mixed or unknown | Anything | `not_proof` |

`verifier_reading` is that table. A catch-all domain accepts mail for names that do not exist, so "valid" on the candidate is the same answer the control got. You do not swap on that.

The old mailbox is the trap inside the verifiers. `jordan.hale@example.com` still exists. It auto-replies. Verifiers that check "does this box accept or answer" can mark it valid. Valid here means the server responded. It does not mean a person reads it. Keep that result in the notes so the next pass does not "fix" the contact back to the dead address.

Moltsets did not know `jhale@example.net` yet. The grade came back F. F is no data. [Chapter 23](./23-reachability-grading.md) already says to treat F like an unknown, and the Moltsets docs say to treat F like C rather than drop it. `treat_moltsets_grade("F")` returns `C`. D is the hard invalid: bounce, complaint, or spam trap. An F on a brand-new corporate address is what you expect the week the tenant flips. It is not a reason to throw the address out.

---

## Who else is on the old domain

Before the swap, list the other campaign leads at the same account whose email is still `@example.com`. `blast_radius` does that match. Those people may be a week behind on the same migration, or they may have already bounced. The summary names the count and the addresses. Each one gets the same classify step. You do not bulk-rewrite them because one coworker moved.

---

## The swap, with a yes

The human reads the summary: class, employment sources, new domain, pattern, verifier reading, Moltsets grade, blast radius. Then yes or no.

On yes, the CRM write is two calls. I tried to do it as one, and the old address disappeared.

A v3 `PATCH` of `email` sets the new primary and drops the previous one. It does not move the old address onto `hs_additional_emails`. That property is read-only. Putting it on the PATCH returns `READ_ONLY_VALUE`, and the old address is still gone. `email_swap_plan` refuses a swap where the two addresses are the same, and it returns the PATCH plus the legacy PUT. Do this around those two calls:

1. Search the new address. If another contact already has it, stop. Changing primary can merge two records.
2. Write both addresses into the undo file. Omit `hubspot_owner_id`.
3. `PATCH /crm/v3/objects/contacts/<CONTACT_ID>` with `{"properties": {"email": "jhale@example.net"}}`.
4. `PUT /contacts/v1/secondary-email/<CONTACT_ID>/email/jordan.hale%40example.com` on the legacy contacts API. That call puts the old address back as a secondary email. The reference is the [legacy secondary-email PUT](https://developers.hubspot.com/docs/api-reference/legacy/crm/objects/contacts/v1/put-contacts-v1-secondary-email-vid-email-email).

Use the plan, apply, undo file, and read-back from [Chapter 26](./26-replies-into-the-crm.md). Read `email` and `hs_additional_emails`. Primary is `jhale@example.net`. The old address is on the secondary list. Owner is unchanged. Add a note that nothing was sent.

Stop the sequence against the dead box with a blocklist entry, `POST /api/v2/block-lists-entries` and `{"bl_value": "jordan.hale@example.com"}`. A lead-status PATCH that returns 200 may have changed nothing. `status_write_stuck` is that check. Do not park him by writing interest status. That write fires webhooks.

Then re-add him to the same campaign as a new lead, so the sequence can send to the new address. Instantly keys the lead on the email, so updating the old lead in place is how you keep mailing the retired box. The API still cannot pin a sending mailbox on that add. `assigned_to` is a workspace user id. The campaign chooses the mailbox. The bulk-add endpoint is [add leads in bulk](https://developer.instantly.ai/api-reference/lead/add-leads-in-bulk-to-a-campaign-or-list). Read the skipped count and the blocklisted count in the response. A skip or a blocklist hit means he is not in the sequence, whatever the HTTP status was. If you blocklisted the old address, confirm the new address is the one on the add. Fix a skip before anyone expects a send. This re-add is a human step. It is not part of `next_action`. The worker does not send.

---

## What to automate later

The reply loop in Chapter 26 already has a webhook and a poll. Extend the subscriptions:

| Event | Why it is on the list |
|---|---|
| `email_bounced` | Hard bounce. Stop, note, re-find. |
| `lead_out_of_office` | Note only. |
| `lead_wrong_person` | Human review, unless the body clearly says they left or the mailbox is retired. |
| `reply_received` | Retired-mailbox copy often shows up as a normal reply. |
| Poll `GET /api/v2/emails` | The same backup as Chapter 26. Unibox and a missed webhook still land here. |

`auto_reply_received` is on Instantly's events guide. It was not a create-webhook `event_type` when this chapter was written (the enum is copied in `SUBSCRIBABLE_EVENTS`, dated 2026-11-05). Subscribe to it when the list endpoint for event types shows it. Until then, `reply_received` plus the poll is the net.

The worker's classifier returns one of five classes: hard bounce, address retired, left company, out of office, other. For address retired or hard bounce it may stop the lead, log the CRM note, run the re-find, and post the summary for a person to approve.

It does not add the new address to the campaign. It does not send.

---

## The lesson

Read the auto-reply as a statement about the mailbox. Ask the employment sources whether the person is still there. If they are, look for the new domain and the new pattern before you archive the lead as a departure.

Part of the [GTM Coding Agent](https://github.com/shawnla90/gtm-coding-agent). Skill: `skills/dead-address-refind/`. Previous in this series: [Chapter 28](./28-reply-from-the-sending-mailbox.md).
