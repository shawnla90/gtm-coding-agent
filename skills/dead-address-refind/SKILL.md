---
name: dead-address-refind
version: 1.1.0
description: When a cold-email mailbox auto-replies that the address is no longer in use, check whether the person is still at the company and look for the new address before calling it a departure. Auto-replies fill Instantly reply status, date, and snippet and look like real replies. Learn the second domain and the pattern, run the enrichment waterfall, verify with three verifiers plus a made-up catch-all control, treat Moltsets F as no data, and swap the CRM email only with a plan, an undo file, and a human yes. Use when the user says "dead address", "re-find", "address retired", "no longer in use", "mailbox not monitored", or "he left but LinkedIn says he is still there".
---

# dead-address-refind

An auto-reply is not proof someone left. Look for the new address first.

A "this address is no longer in use" auto-reply is a dead mailbox. It is not a resignation. The company may be migrating staff onto a second domain. Learn that domain and the new pattern, run the enrichment waterfall, confirm the candidate with more than one verifier and a made-up address as a control, swap the CRM email, and only then have a person put the lead back so the campaign can send again.

The worked case is in [Chapter 29](../../chapters/29-dead-address-versus-departed.md). The decisions are in [`reply_loop.py`](../../starters/instantly-hubspot-replies/reply_loop.py): `classify`, `next_action`, `learn_initial_last`, `verifier_reading`, `treat_moltsets_grade`, `blast_radius`, `email_swap_plan`, `reply_fields_prove_interest`, `blocklist_entry_body`. Nothing in this skill sends mail or adds a lead by itself.

## It already looks like a real reply

Instantly fills reply status, reply date, and the snippet from an auto-reply. The lead row looks answered. Those three fields are not a person. `reply_fields_prove_interest` ignores them and reads the body. "No longer in use" classifies as `address_retired`. Do not open a deal. Do not write `interested` on the contact. Do not write `auto_reply` into a HubSpot lead-status property either: a workflow that enrolls on any non-empty status will create an owned deal. That trigger is gotcha 8 in [`instantly-hubspot-replies`](../instantly-hubspot-replies/SKILL.md).

Park the dead address with `POST /api/v2/block-lists-entries` (`blocklist_entry_body`). A PATCH of `lt_interest_status` can return 200 and leave the status unchanged, so it is not how you stop the sequence. Interest-status writes also fire webhooks. Do not PATCH status from the webhook that a status change just caused.

## Inputs

- The auto-reply text, or the Instantly event (`email_bounced`, `reply_received`, `lead_out_of_office`, `lead_wrong_person`)
- Whether employment sources still show the person at the company (Moltsets, Apollo, Prospeo, LinkedIn). Say which source said what.
- Other contacts at the same account, plus MX and TXT for the old domain and any candidate domain
- Verifier results from MillionVerifier, ZeroBounce, and NeverBounce, including a made-up local part on each domain
- A human yes before any CRM write or any campaign add

## Classify, then decide

| Text or event | Class | While they are still at the company | When employment says they left |
|---|---|---|---|
| Bounce status, or a 550 user-unknown body | `hard_bounce` | `stop_note_refind` | `stop_note_refind` |
| "no longer in use", "not monitored", retired mailbox | `address_retired` | `stop_note_refind` | `stop_note_refind` |
| "no longer with", "left the company" | `left_company` | `stop_note_refind` | `hold_left_company` |
| Out of office | `out_of_office` | `note_only` | `note_only` |
| Anything else, including `lead_wrong_person` with no clearer text | `other` | `human_review` | `human_review` |

`stop_note_refind` means: stop the lead so the sequence does not send again, log a CRM note, run the re-find, post the summary. It does not mean add the new address or send.

Check retired-mailbox phrases before a generic out-of-office phrase. A subject line of "automatic reply" can sit on top of "this address is no longer in use".

## Re-find

The company may be migrating staff to a second domain. Coworkers flip first. This is a mailbox move, not a job change, until employment sources say otherwise.

1. List other contacts at the account. A second domain often shows up there before it shows up on this person.
2. Read MX and TXT. A Microsoft 365 tenant tends to show `mail.protection.outlook.com` on the MX and `include:spf.protection.outlook.com` on the SPF.
3. Learn the pattern from known-good addresses on that domain. `learn_initial_last` accepts the pattern only when every sample matches first initial plus last name. If the samples disagree, stop and ask.
4. Build the candidate. For Jordan Hale on `example.net` the initial-last form is `jhale@example.net`.
5. Run the email waterfall (Floqer, when that is the waterfall you already use) against the new domain.
6. Verify the candidate and a made-up control (`not-a-person-zz99@` the same domain) on MillionVerifier, ZeroBounce, and NeverBounce.
   - All three say the candidate is valid, and all three say the control is invalid: `verified`.
   - The control comes back valid: `catch_all`. A valid candidate is not proof.
   - Anything else: `not_proof`.
7. The old mailbox can still verify as valid. It exists, and it auto-replies. A valid verdict on the old address is a reason to stop trusting "valid" by itself.
8. Moltsets grade F on the new address is no data. `treat_moltsets_grade` maps F to C. D is the hard invalid. Do not swap those.

## Blast radius and the swap

`blast_radius` lists other campaign leads at the same account whose email is still on the old domain. Put that list in the summary.

The swap, after a yes. A v3 PATCH of `email` drops the old primary. `hs_additional_emails` is read-only on v3, and writing it returns `READ_ONLY_VALUE` while the old address is still gone. `email_swap_plan` builds the two HubSpot calls in steps 2 and 3. Do the whole swap in this order:

1. Search the new address first. If another contact already owns it, stop. A primary change can merge records.
2. `PATCH /crm/v3/objects/contacts/{contactId}` with `properties.email` set to the new address. Record both addresses in the undo file before this call. Leave `hubspot_owner_id` unset.
3. `PUT /contacts/v1/secondary-email/{contactId}/email/{oldEmail}` on the legacy contacts API. URL-encode the old address. This puts it back as a secondary email.
4. Read `email` and `hs_additional_emails` back. Primary is the new address. The old address is on the secondary list. Owner is unchanged. Add a note. Apply with the same plan, undo file, and read-back as Chapter 26.
5. Re-add the person to the same campaign as a new lead so the sequence can send to the new address. Instantly will not pin a sending mailbox on that add (`assigned_to` is a user id). Read the skipped count and the blocklisted count. A 200 with a skip is not "they are in the sequence". Blocklist the dead address first, or the add can bounce off it.
6. Do this add only after the human yes. The automation posts the summary and stops. It does not send.

## Later automation

Subscribe to `email_bounced`, `lead_out_of_office`, `lead_wrong_person`, and `reply_received`, plus the poll in Chapter 26. Some retired-mailbox notices arrive as normal replies. `auto_reply_received` is named in Instantly's events guide and was not a create-webhook `event_type` on 2026-11-05. Add it only when the enum lists it.

The worker may stop the lead, write the note, run the re-find, and post the summary. It may not add the lead and it may not send.

## Do

- Quote the auto-reply class and the employment sources in the same summary.
- Keep made-up controls on every domain you verify.
- Show the blast-radius list before asking for the swap.

## Don't

- Don't call a retired mailbox a job change because the wording felt like "he left".
- Don't drop the old address off the contact. The v3 email PATCH will drop it unless you PUT it back through the legacy secondary-email endpoint.
- Don't treat Instantly reply status, reply date, or a snippet as proof a person wrote. Auto-replies fill all three.
- Don't auto-add the new address to the campaign, and don't auto-send.
- Don't treat Moltsets F as a bad address.
- Don't treat a verifier "valid" on a live auto-reply mailbox as proof a person reads it.

## Related

- `../../chapters/29-dead-address-versus-departed.md`
- `../../chapters/23-reachability-grading.md` for the A-F grades
- `../../skills/instantly-hubspot-replies/SKILL.md` for the reply loop the events arrive on
