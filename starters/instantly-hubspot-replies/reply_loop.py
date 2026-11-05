"""Rules for logging Instantly replies into HubSpot, and for a retired mailbox.

No network. Routes, the backfill, and the re-find all call these functions.
A write is refused unless test mode is off and the portal allow flag is the
string "true" for the expected portal id. Owner fields are refused.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
from urllib.parse import quote

INTERESTED_STATUS = 1
EMAIL_TO_CONTACT = 198
UNIQUE_PREFIX = "instantly:"
MAX_SIGNATURE_AGE_MS = 5 * 60 * 1000
LIST_EMAILS_PER_MINUTE = 20
INSTANTLY_USER_AGENT = "gtm-reply-loop/1.0"
# Placeholder only. A live campaign name must not be hardcoded here.
CAMPAIGN_NAME_GUARD = "CAMPAIGN_NAME_GUARD"
PULLED_SECRET_PLACEHOLDER = "[SENSITIVE]"
WRITABLE_LEAD_STATUSES = frozenset({"interested", "lead_interested", "1"})
_MAILBOX_FIELDS_ON_LEAD_CREATE = frozenset(
    {"eaccount", "sending_account", "email_account", "from_address", "mailbox"}
)

# Create-webhook event_type enum, checked against the public API on 2026-11-05.
# auto_reply_received is a payload the events guide names. It is not in this enum.
SUBSCRIBABLE_EVENTS = frozenset(
    {
        "all_events",
        "email_sent",
        "email_opened",
        "email_link_clicked",
        "reply_received",
        "email_bounced",
        "lead_unsubscribed",
        "campaign_completed",
        "account_error",
        "lead_neutral",
        "lead_interested",
        "lead_not_interested",
        "lead_meeting_booked",
        "lead_meeting_completed",
        "lead_closed",
        "lead_out_of_office",
        "lead_wrong_person",
        "lead_no_show",
        "supersearch_enrichment_completed",
    }
)

REPLY_LOOP_EVENTS = ("reply_received", "lead_interested")
REFIND_EVENTS = (
    "email_bounced",
    "lead_out_of_office",
    "lead_wrong_person",
    "reply_received",
)

AUTOMATION_ACTIONS = frozenset(
    {"note_only", "human_review", "hold_left_company", "stop_note_refind"}
)


class PlanError(RuntimeError):
    pass


def unique_id(email_id: str) -> str:
    cleaned = str(email_id or "").strip()
    if not cleaned:
        raise ValueError("email id required")
    return f"{UNIQUE_PREFIX}{cleaned}"


def email_direction(kind: str) -> str:
    if kind == "inbound":
        return "INCOMING_EMAIL"
    if kind == "outbound":
        return "EMAIL"
    raise ValueError("kind must be inbound or outbound")


def portal_write_allowed(
    *,
    portal_id: str,
    expected_portal_id: str,
    allow_flag: str,
    test_mode: bool,
) -> tuple[bool, str]:
    if test_mode:
        return False, "test mode"
    if allow_flag != "true":
        return False, "portal not explicitly allowed"
    expected = str(expected_portal_id or "").strip()
    actual = str(portal_id or "").strip()
    if not expected or actual != expected:
        return False, "portal id mismatch"
    return True, "allowed"


def deal_name(prefix: str, person: str, company: str) -> str:
    prefix = (prefix or "").strip()
    person = (person or "").strip()
    company = (company or "").strip()
    if not prefix or not person or not company:
        raise ValueError("prefix, person, and company required")
    return f"({prefix}) - {person} - {company}"


def dedupe_needle(prefix: str) -> str:
    prefix = (prefix or "").strip()
    if not prefix:
        raise ValueError("prefix required")
    return f"({prefix}) - "


def require_stage_ids(pipeline_id: str, stage_id: str) -> None:
    for label, value in (("pipeline", pipeline_id), ("stage", stage_id)):
        cleaned = str(value or "").strip()
        if not cleaned or cleaned.upper() == "MQL":
            raise ValueError(f"{label} must be an id")


def should_open_deal(
    *,
    email_logged: bool,
    interest_status=None,
    event_type: str | None = None,
    is_auto_reply: bool = False,
    is_bounce: bool = False,
    meeting_booked: bool = False,
    manual_mql: bool = False,
) -> tuple[bool, str]:
    """Open a deal for interested / lead_interested, or the card's MQL button.

    reply_received on its own is an email log. It is not a deal.
    """
    if not email_logged:
        return False, "email log failed"
    if is_auto_reply or is_bounce:
        return False, "auto reply or bounce"
    if meeting_booked or event_type == "lead_meeting_booked":
        return False, "meeting booked"
    if manual_mql:
        return True, "manual mql"
    interested = str(interest_status) == str(INTERESTED_STATUS) or event_type == "lead_interested"
    if interested:
        return True, "interested"
    if event_type == "reply_received":
        return False, "reply received is not a deal"
    return False, "not a positive reply"


def payload_sets_owner(properties: dict) -> bool:
    return "hubspot_owner_id" in properties


def campaign_prefix_map(campaign_ids: str, prefixes: str) -> dict[str, str]:
    ids = [part.strip() for part in (campaign_ids or "").split(",") if part.strip()]
    names = [part.strip() for part in (prefixes or "").split(",") if part.strip()]
    if len(ids) != len(names):
        raise ValueError("campaign ids and deal prefixes must be the same length")
    return dict(zip(ids, names))


def log_or_skip(email_id: str, existing_unique_ids: set[str]) -> str:
    if unique_id(email_id) in existing_unique_ids:
        return "skip"
    return "create"


def deal_already_open(existing_dealnames: list[str], prefix: str, person: str, company: str) -> bool:
    want = deal_name(prefix, person, company)
    return want in existing_dealnames


def duplicate_deal_report(deals: list[dict]) -> dict[str, list[str]]:
    """Group record ids that share one deal name. Report only. Delete nothing."""
    grouped: dict[str, list[str]] = {}
    for deal in deals:
        name = deal.get("dealname") or ""
        grouped.setdefault(name, []).append(str(deal.get("id")))
    return {name: ids for name, ids in grouped.items() if name and len(ids) > 1}


def poll_has_budget(requests_this_minute: int, limit: int = LIST_EMAILS_PER_MINUTE) -> bool:
    return requests_this_minute < limit


def subscription_event(event_type: str) -> str:
    if event_type not in SUBSCRIBABLE_EVENTS:
        raise ValueError(
            f"{event_type} is not a create-webhook event_type. "
            "Use reply_received and the poll for auto-replies that arrive as normal replies."
        )
    return event_type


def webhook_create_body(*, target_url: str, event_type: str, campaign_id: str, secret: str) -> dict:
    subscription_event(event_type)
    if not target_url.startswith("https://"):
        raise ValueError("target url must be https")
    if not campaign_id or not secret:
        raise ValueError("campaign id and secret required")
    return {
        "target_hook_url": target_url,
        "event_type": event_type,
        "campaign": campaign_id,
        "headers": {"X-Instantly-Secret": secret},
    }


def redact_webhook_body(body: dict) -> dict:
    redacted = dict(body)
    headers = dict(body.get("headers") or {})
    if "X-Instantly-Secret" in headers:
        headers["X-Instantly-Secret"] = "<redacted>"
    redacted["headers"] = headers
    return redacted


def webhook_http_status(presented_secret: str | None, expected_secret: str) -> int:
    if not expected_secret or presented_secret != expected_secret:
        return 401
    return 200


def cron_http_status(authorization: str | None, expected_secret: str) -> int:
    if not expected_secret or authorization != f"Bearer {expected_secret}":
        return 401
    return 200


def user_can_reply(email: str | None, allowlist: list[str]) -> bool:
    """Allow a logged-in HubSpot user by full email, or by @client-domain.com."""
    if not email or "@" not in email:
        return False
    normalized = email.strip().lower()
    domain = normalized.split("@", 1)[1]
    for item in allowlist:
        token = (item or "").strip().lower()
        if not token:
            continue
        if token.startswith("@") and token[1:] == domain:
            return True
        if token == normalized:
            return True
    return False


def instantly_reply_body(*, eaccount: str, reply_to_uuid: str, subject: str, text: str) -> dict:
    if not eaccount or not reply_to_uuid or not subject or not text:
        raise ValueError("eaccount, reply_to_uuid, subject, and text required")
    return {
        "eaccount": eaccount,
        "reply_to_uuid": reply_to_uuid,
        "subject": subject,
        "body": {"text": text},
    }


def hubspot_email_properties(*, email_id: str, kind: str, subject: str, text: str, timestamp: str) -> dict:
    return {
        "hs_timestamp": timestamp,
        "hs_email_direction": email_direction(kind),
        "hs_email_status": "SENT",
        "hs_email_subject": subject,
        "hs_email_text": text,
        "hs_unique_id": unique_id(email_id),
    }


def contact_association(contact_id: str) -> dict:
    return {
        "to": {"id": contact_id},
        "types": [
            {
                "associationCategory": "HUBSPOT_DEFINED",
                "associationTypeId": EMAIL_TO_CONTACT,
            }
        ],
    }


def build_plan(
    replies: list[dict],
    *,
    prefix: str,
    pipeline_id: str,
    stage_id: str,
    existing_unique_ids: set[str] | None = None,
    existing_dealnames: list[str] | None = None,
) -> dict:
    require_stage_ids(pipeline_id, stage_id)
    existing_unique_ids = existing_unique_ids or set()
    existing_dealnames = existing_dealnames or []
    steps = []
    for reply in replies:
        email_id = reply["email_id"]
        uid = unique_id(email_id)
        log_action = log_or_skip(email_id, existing_unique_ids)
        properties = hubspot_email_properties(
            email_id=email_id,
            kind=reply.get("kind", "inbound"),
            subject=reply.get("subject", ""),
            text=reply.get("text", ""),
            timestamp=reply.get("timestamp", ""),
        )
        steps.append(
            {
                "op": "log_email",
                "action": log_action,
                "hs_unique_id": uid,
                "contact_id": reply["contact_id"],
                "properties": properties,
            }
        )
        open_deal, reason = should_open_deal(
            email_logged=True,
            interest_status=reply.get("interest_status"),
            event_type=reply.get("event_type"),
            is_auto_reply=bool(reply.get("is_auto_reply")),
            is_bounce=bool(reply.get("is_bounce")),
            meeting_booked=bool(reply.get("meeting_booked")),
            manual_mql=bool(reply.get("manual_mql")),
        )
        person = reply.get("person") or ""
        company = reply.get("company") or ""
        if open_deal and deal_already_open(existing_dealnames, prefix, person, company):
            open_deal = False
            reason = "deal already open"
        deal_step = {
            "op": "create_deal",
            "action": "create" if open_deal else "skip",
            "reason": reason,
            "after_unique_id": uid,
            "properties": {},
        }
        if open_deal:
            deal_step["properties"] = {
                "dealname": deal_name(prefix, person, company),
                "pipeline": pipeline_id,
                "dealstage": stage_id,
            }
        steps.append(deal_step)
    return {"steps": steps}


def apply_plan(plan: dict, gate: dict, writer) -> list[dict]:
    ok, reason = portal_write_allowed(**gate)
    if not ok:
        raise PermissionError(reason)
    undo = []
    logged = set()
    for step in plan["steps"]:
        properties = step.get("properties") or {}
        if payload_sets_owner(properties):
            raise PermissionError("refusing to set an owner")
        if step["action"] == "skip":
            if step["op"] == "log_email":
                logged.add(step["hs_unique_id"])
            continue
        if step["op"] == "create_deal" and step["after_unique_id"] not in logged:
            raise PlanError("refusing to open a deal without a logged email")
        result = writer(step)
        if step["op"] == "log_email":
            if not result or not result.get("id"):
                raise PlanError("email log failed")
            logged.add(step["hs_unique_id"])
            undo.append(
                {
                    "object": "emails",
                    "id": result["id"],
                    "hs_unique_id": step["hs_unique_id"],
                }
            )
        elif step["op"] == "create_deal":
            if not result or not result.get("id"):
                raise PlanError("deal create failed")
            undo.append(
                {
                    "object": "deals",
                    "id": result["id"],
                    "dealname": properties["dealname"],
                }
            )
    return undo


def read_back(undo: list[dict], fetched_by_id: dict) -> list[str]:
    problems = []
    for row in undo:
        got = fetched_by_id.get(row["id"])
        if not got:
            problems.append(f"{row['id']} missing")
            continue
        if got.get("hubspot_owner_id"):
            problems.append(f"{row['id']} owner set")
        if row["object"] == "emails" and got.get("hs_unique_id") != row["hs_unique_id"]:
            problems.append(f"{row['id']} unique id")
        if row["object"] == "deals" and got.get("dealname") != row["dealname"]:
            problems.append(f"{row['id']} deal name")
    return problems


def hubspot_v3_signature(*, secret: str, method: str, uri: str, body: str, timestamp: str) -> str:
    raw = f"{method}{uri}{body}{timestamp}".encode()
    digest = hmac.new(secret.encode(), raw, hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


def signature_is_valid(
    *,
    secret: str,
    method: str,
    uri: str,
    body: str,
    timestamp: str,
    presented: str,
    now_ms: int,
) -> bool:
    try:
        stamp = int(timestamp)
    except (TypeError, ValueError):
        return False
    if abs(now_ms - stamp) > MAX_SIGNATURE_AGE_MS:
        return False
    expected = hubspot_v3_signature(
        secret=secret, method=method, uri=uri, body=body, timestamp=timestamp
    )
    return hmac.compare_digest(expected, presented or "")


def classify_text(text: str) -> str:
    folded = (text or "").lower()
    bounce_bits = ("user unknown", "550 5.1.1", "mailbox not found", "address rejected")
    retired_bits = (
        "no longer in use",
        "not monitored",
        "mailbox has been retired",
        "address is no longer",
    )
    left_bits = ("no longer with", "left the company", "no longer employed", "is no longer at")
    ooo_bits = ("out of the office", "out of office", "ooo until")
    if any(bit in folded for bit in bounce_bits):
        return "hard_bounce"
    if any(bit in folded for bit in retired_bits):
        return "address_retired"
    if any(bit in folded for bit in left_bits):
        return "left_company"
    if any(bit in folded for bit in ooo_bits):
        return "out_of_office"
    return "other"


def classify(event_type: str | None, text: str) -> str:
    if event_type == "email_bounced":
        return "hard_bounce"
    if event_type == "lead_out_of_office":
        return "out_of_office"
    return classify_text(text)


def next_action(text_class: str, *, still_at_company: bool | None) -> str:
    """Human-gated next step. Adding a lead or sending mail is not an action here."""
    if text_class == "out_of_office":
        return "note_only"
    if text_class == "other":
        return "human_review"
    if text_class == "left_company" and still_at_company is False:
        return "hold_left_company"
    if text_class in ("address_retired", "hard_bounce", "left_company"):
        return "stop_note_refind"
    return "human_review"


def candidate_address(first: str, last: str, domain: str) -> str:
    first_clean = (first or "").strip().lower()
    last_clean = (last or "").strip().lower()
    domain_clean = (domain or "").strip().lower().lstrip("@")
    if not first_clean or not last_clean or not domain_clean or "." not in domain_clean:
        raise ValueError("first, last, and domain required")
    return f"{first_clean[0]}{last_clean}@{domain_clean}"


def learn_initial_last(samples: list[tuple[str, str, str]]) -> str | None:
    """Return the pattern name when every known-good address matches it."""
    if not samples:
        return None
    for first, last, email in samples:
        domain = email.split("@", 1)[1]
        if email.lower() != candidate_address(first, last, domain):
            return None
    return "initial_last"


def looks_like_microsoft_365(mx_text: str, txt_text: str) -> bool:
    blob = f"{mx_text}\n{txt_text}".lower()
    return "mail.protection.outlook.com" in blob or "spf.protection.outlook.com" in blob


def verifier_reading(candidate: dict, control: dict) -> str:
    names = ("millionverifier", "zerobounce", "neverbounce")
    if any(control.get(name) == "valid" for name in names):
        return "catch_all"
    candidate_ok = all(candidate.get(name) == "valid" for name in names)
    control_dead = all(control.get(name) == "invalid" for name in names)
    if candidate_ok and control_dead:
        return "verified"
    return "not_proof"


def treat_moltsets_grade(grade: str) -> str:
    """F is no data. Handle it like C. D stays the hard invalid."""
    cleaned = (grade or "").strip().upper()
    if cleaned == "F":
        return "C"
    return cleaned


def grade_is_hard_invalid(grade: str) -> bool:
    return (grade or "").strip().upper() == "D"


def blast_radius(leads: list[dict], *, account_id: str, old_domain: str) -> list[dict]:
    suffix = "@" + old_domain.strip().lower()
    return [
        lead
        for lead in leads
        if lead.get("account_id") == account_id and str(lead.get("email", "")).lower().endswith(suffix)
    ]


def email_swap_plan(*, old_email: str, new_email: str, contact_id: str = "<CONTACT_ID>") -> dict:
    """Two calls. A v3 PATCH of email drops the old primary and cannot set hs_additional_emails.

    Re-add the old address with the legacy contacts API after the PATCH.
    """
    if not old_email or not new_email or old_email.lower() == new_email.lower():
        raise ValueError("old and new email must both be present and different")
    if "@" not in old_email or "@" not in new_email:
        raise ValueError("old and new email must both be addresses")
    contact_id = str(contact_id or "").strip()
    if not contact_id:
        raise ValueError("contact id required")
    quoted = quote(old_email.strip(), safe="")
    return {
        "contact_id": contact_id,
        "primary_email": new_email,
        "secondary_email": old_email,
        "steps": [
            {
                "op": "set_primary_email",
                "method": "PATCH",
                "path": f"/crm/v3/objects/contacts/{contact_id}",
                "properties": {"email": new_email},
            },
            {
                "op": "readd_secondary_email",
                "method": "PUT",
                "path": f"/contacts/v1/secondary-email/{contact_id}/email/{quoted}",
            },
        ],
        "read_back_properties": ["email", "hs_additional_emails"],
        "note": (
            "Primary email moved after a retired-mailbox re-find. "
            "The v3 PATCH drops the previous primary. "
            "hs_additional_emails is read-only on v3. "
            "The legacy PUT puts the old address back as a secondary email. "
            "Nothing was sent."
        ),
    }


def campaign_suppressed_by_guard(name: str, *, test_mode: bool, guard: str) -> bool:
    """A name guard is a test-mode block. It does not run when test mode is off.

    Leaving the match unconditional hides the thread, blocks Send, and skips
    the poll and the webhook for a live campaign whose name contains the guard.
    """
    if not test_mode:
        return False
    needle = (guard or "").strip().lower()
    if not needle:
        return False
    return needle in (name or "").lower()


def campaign_in_scope(
    *,
    campaign_id: str,
    campaign_name: str,
    allowed_ids: list[str],
    test_mode: bool,
    name_guard: str,
) -> tuple[bool, str]:
    """Campaign ids are always filtered. The name guard is not."""
    allowed = {item.strip() for item in allowed_ids if item and str(item).strip()}
    if not campaign_id or str(campaign_id).strip() not in allowed:
        return False, "campaign id not configured"
    if campaign_suppressed_by_guard(campaign_name, test_mode=test_mode, guard=name_guard):
        return False, "test mode name guard"
    return True, "in scope"


def thread_view(*, http_status: int, messages: list | None) -> str:
    """200 and an empty list is the empty state. Anything else is not that state."""
    if http_status != 200:
        return "auth_failure"
    if not messages:
        return "no_instantly_thread"
    return "thread"


def instantly_list_emails_request(*, lead: str = "", campaign_id: str = "") -> dict:
    """GET /api/v2/emails. ?lead= returns 403 when User-Agent is missing."""
    params: dict[str, str] = {}
    if lead:
        params["lead"] = lead
    if campaign_id:
        params["campaign_id"] = campaign_id
    return {
        "method": "GET",
        "path": "/api/v2/emails",
        "params": params,
        "headers": {
            "Accept": "application/json",
            "User-Agent": INSTANTLY_USER_AGENT,
        },
    }


def reject_mailbox_on_lead_create(payload: dict) -> dict:
    """Create-lead has no sending mailbox. assigned_to is a workspace user id.

    Pin the mailbox later, on POST /api/v2/emails/reply, with eaccount.
    """
    found = _MAILBOX_FIELDS_ON_LEAD_CREATE.intersection(payload)
    if found:
        raise ValueError(
            "lead create cannot assign a sending mailbox. "
            "assigned_to is a workspace user id. "
            "Pin the mailbox with eaccount on POST /api/v2/emails/reply."
        )
    return payload


def should_write_lead_status(status: str) -> bool:
    """Write the HubSpot lead-status property for a positive status only.

    auto_reply, bounce, and out_of_office are non-empty. A workflow that
    enrolls on any non-empty value will open an owned deal off those writes.
    """
    return str(status or "").strip().lower() in WRITABLE_LEAD_STATUSES


def status_write_stuck(*, http_status: int, requested, observed) -> bool:
    """True when Instantly returned 200 and the lead status did not change."""
    return http_status == 200 and str(requested) != str(observed)


def blocklist_entry_body(email: str) -> dict:
    """POST /api/v2/block-lists-entries. This is what parks a lead. A status PATCH is not."""
    cleaned = (email or "").strip().lower()
    if "@" not in cleaned:
        raise ValueError("email required")
    return {"bl_value": cleaned}


def pulled_secret_is_usable(value: str | None) -> bool:
    """False for the empty string and the [SENSITIVE] marker vercel env pull writes.

    A sensitive HUBSPOT_APP_SECRET from that pull is still not the client secret
    when this returns true. Do not debug a signature with a pulled value.
    """
    cleaned = (value or "").strip()
    if not cleaned or cleaned == PULLED_SECRET_PLACEHOLDER:
        return False
    return True


def reply_fields_prove_interest(*, text: str, interest_status=None, event_type: str | None = None) -> bool:
    """Reply status, reply date, and snippet can be filled by an auto-reply.

    Those fields are not arguments here on purpose. The body class plus a
    positive interest signal is the proof.
    """
    if classify(event_type, text) != "other":
        return False
    return str(interest_status) == str(INTERESTED_STATUS) or event_type == "lead_interested"
