"""No network. Rules for the Instantly reply loop and the retired-mailbox re-find."""

import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "starters" / "instantly-hubspot-replies"
spec = importlib.util.spec_from_file_location("reply_loop", ROOT / "reply_loop.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

GATE = {
    "portal_id": "<PORTAL_ID>",
    "expected_portal_id": "<PORTAL_ID>",
    "allow_flag": "true",
    "test_mode": False,
}


def reply(**overrides):
    base = {
        "email_id": "email-1",
        "contact_id": "<CONTACT_ID>",
        "kind": "inbound",
        "subject": "Re: conference",
        "text": "Yes, send the one-pager.",
        "timestamp": "2026-11-05T15:00:00.000Z",
        "person": "Jordan Hale",
        "company": "Example Multifamily",
        "interest_status": 1,
        "event_type": "lead_interested",
    }
    base.update(overrides)
    return base


class IdentityTests(unittest.TestCase):
    def test_unique_id_and_direction(self):
        self.assertEqual(mod.unique_id(" email-1 "), "instantly:email-1")
        self.assertEqual(mod.email_direction("inbound"), "INCOMING_EMAIL")
        self.assertEqual(mod.email_direction("outbound"), "EMAIL")

    def test_deal_name_and_needle(self):
        self.assertEqual(
            mod.deal_name("CONF", "Jordan Hale", "Example Multifamily"),
            "(CONF) - Jordan Hale - Example Multifamily",
        )
        self.assertEqual(mod.dedupe_needle("CONF"), "(CONF) - ")

    def test_stage_label_is_refused(self):
        with self.assertRaises(ValueError):
            mod.require_stage_ids("MQL", "<STAGE_ID>")
        with self.assertRaises(ValueError):
            mod.require_stage_ids("<PIPELINE_ID>", "")


class DealGateTests(unittest.TestCase):
    def test_interested_opens_only_after_the_email_lands(self):
        opened, reason = mod.should_open_deal(email_logged=True, interest_status=1)
        self.assertTrue(opened)
        self.assertEqual(reason, "interested")
        opened, reason = mod.should_open_deal(email_logged=False, event_type="lead_interested")
        self.assertFalse(opened)
        self.assertEqual(reason, "email log failed")

    def test_meeting_booked_auto_reply_and_bounce_stay_closed(self):
        for kwargs in (
            {"meeting_booked": True},
            {"event_type": "lead_meeting_booked"},
            {"is_auto_reply": True, "interest_status": 1},
            {"is_bounce": True, "event_type": "lead_interested"},
        ):
            opened, _reason = mod.should_open_deal(email_logged=True, **kwargs)
            self.assertFalse(opened)

    def test_owner_field_is_visible(self):
        self.assertTrue(mod.payload_sets_owner({"hubspot_owner_id": "1"}))
        self.assertFalse(mod.payload_sets_owner({"dealname": "(CONF) - Jordan Hale - Example Multifamily"}))


class PortalTests(unittest.TestCase):
    def test_test_mode_and_allow_flag(self):
        ok, reason = mod.portal_write_allowed(
            portal_id="<PORTAL_ID>",
            expected_portal_id="<PORTAL_ID>",
            allow_flag="true",
            test_mode=True,
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "test mode")
        ok, reason = mod.portal_write_allowed(
            portal_id="<PORTAL_ID>",
            expected_portal_id="<PORTAL_ID>",
            allow_flag="yes",
            test_mode=False,
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "portal not explicitly allowed")

    def test_portal_mismatch(self):
        ok, reason = mod.portal_write_allowed(
            portal_id="999",
            expected_portal_id="<PORTAL_ID>",
            allow_flag="true",
            test_mode=False,
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "portal id mismatch")


class PlanTests(unittest.TestCase):
    def test_apply_writes_email_then_deal_and_reads_back(self):
        plan = mod.build_plan(
            [reply()],
            prefix="CONF",
            pipeline_id="<PIPELINE_ID>",
            stage_id="<STAGE_ID>",
        )
        calls = []

        def writer(step):
            calls.append(step["op"])
            self.assertNotIn("hubspot_owner_id", step["properties"])
            return {"id": "rec-" + step["op"]}

        undo = mod.apply_plan(plan, GATE, writer)
        self.assertEqual(calls, ["log_email", "create_deal"])
        fetched = {
            "rec-log_email": {"hs_unique_id": "instantly:email-1"},
            "rec-create_deal": {"dealname": "(CONF) - Jordan Hale - Example Multifamily"},
        }
        self.assertEqual(mod.read_back(undo, fetched), [])

    def test_failed_email_log_does_not_open_a_deal(self):
        plan = mod.build_plan(
            [reply()],
            prefix="CONF",
            pipeline_id="<PIPELINE_ID>",
            stage_id="<STAGE_ID>",
        )

        def writer(step):
            if step["op"] == "log_email":
                return None
            raise AssertionError("deal writer should not run")

        with self.assertRaises(mod.PlanError):
            mod.apply_plan(plan, GATE, writer)

    def test_existing_unique_id_skips_the_second_log(self):
        plan = mod.build_plan(
            [reply()],
            prefix="CONF",
            pipeline_id="<PIPELINE_ID>",
            stage_id="<STAGE_ID>",
            existing_unique_ids={"instantly:email-1"},
            existing_dealnames=["(CONF) - Jordan Hale - Example Multifamily"],
        )
        self.assertEqual(plan["steps"][0]["action"], "skip")
        self.assertEqual(plan["steps"][1]["action"], "skip")

        def writer(step):
            raise AssertionError(step)

        self.assertEqual(mod.apply_plan(plan, GATE, writer), [])

    def test_duplicate_report_does_not_delete(self):
        report = mod.duplicate_deal_report(
            [
                {"id": "a", "dealname": "(CONF) - Jordan Hale - Example Multifamily"},
                {"id": "b", "dealname": "(CONF) - Jordan Hale - Example Multifamily"},
                {"id": "c", "dealname": "(CONF) - Avery Nguyen - Example Multifamily"},
            ]
        )
        self.assertEqual(report["(CONF) - Jordan Hale - Example Multifamily"], ["a", "b"])
        self.assertNotIn("(CONF) - Avery Nguyen - Example Multifamily", report)


class HttpTests(unittest.TestCase):
    def test_webhook_and_cron_status(self):
        self.assertEqual(mod.webhook_http_status(None, "secret"), 401)
        self.assertEqual(mod.webhook_http_status("secret", "secret"), 200)
        self.assertEqual(mod.cron_http_status("Bearer secret", "secret"), 200)
        self.assertEqual(mod.cron_http_status("secret", "secret"), 401)

    def test_signature_and_allowlist(self):
        secret = "app-client-secret"
        method, uri, body, stamp = "POST", "https://your-app.vercel.app/api/hubspot/reply", "{}", "1700000000000"
        raw = f"{method}{uri}{body}{stamp}".encode()
        import base64
        import hashlib
        import hmac

        presented = base64.b64encode(hmac.new(secret.encode(), raw, hashlib.sha256).digest()).decode()
        self.assertTrue(
            mod.signature_is_valid(
                secret=secret,
                method=method,
                uri=uri,
                body=body,
                timestamp=stamp,
                presented=presented,
                now_ms=1700000000000,
            )
        )
        self.assertFalse(
            mod.signature_is_valid(
                secret=secret,
                method=method,
                uri=uri,
                body=body,
                timestamp=stamp,
                presented=presented,
                now_ms=1700000000000 + mod.MAX_SIGNATURE_AGE_MS + 1,
            )
        )
        self.assertTrue(mod.user_can_reply("Rep@example.com", ["rep@example.com"]))
        self.assertFalse(mod.user_can_reply("other@example.com", ["rep@example.com"]))

    def test_reply_body_and_webhook_redaction(self):
        body = mod.instantly_reply_body(
            eaccount="sender@example.com",
            reply_to_uuid="email-1",
            subject="Re: conference",
            text="Here is the one-pager.",
        )
        self.assertEqual(body["eaccount"], "sender@example.com")
        self.assertEqual(body["reply_to_uuid"], "email-1")
        created = mod.webhook_create_body(
            target_url="https://your-app.vercel.app/api/instantly/webhook",
            event_type="reply_received",
            campaign_id="<CAMPAIGN_ID>",
            secret="whsec",
        )
        self.assertEqual(mod.redact_webhook_body(created)["headers"]["X-Instantly-Secret"], "<redacted>")
        with self.assertRaises(ValueError):
            mod.subscription_event("auto_reply_received")

    def test_poll_budget(self):
        self.assertTrue(mod.poll_has_budget(19))
        self.assertFalse(mod.poll_has_budget(20))


class RefindTests(unittest.TestCase):
    def test_retired_mailbox_is_not_a_departure_when_he_is_still_there(self):
        text = (
            "This email address is no longer in use and is not monitored. "
            "Please contact a colleague."
        )
        label = mod.classify("reply_received", text)
        self.assertEqual(label, "address_retired")
        self.assertEqual(mod.next_action(label, still_at_company=True), "stop_note_refind")
        self.assertNotIn("send", mod.AUTOMATION_ACTIONS)

    def test_left_company_holds_when_employment_agrees(self):
        label = mod.classify_text("Jordan Hale is no longer with Example Multifamily.")
        self.assertEqual(label, "left_company")
        self.assertEqual(mod.next_action(label, still_at_company=False), "hold_left_company")
        self.assertEqual(mod.next_action(label, still_at_company=True), "stop_note_refind")

    def test_pattern_mx_and_verifiers(self):
        samples = [
            ("Avery", "Nguyen", "anguyen@example.net"),
            ("Riley", "Chen", "rchen@example.net"),
        ]
        self.assertEqual(mod.learn_initial_last(samples), "initial_last")
        self.assertEqual(mod.candidate_address("Jordan", "Hale", "example.net"), "jhale@example.net")
        self.assertIsNone(
            mod.learn_initial_last([("Avery", "Nguyen", "avery.nguyen@example.net")])
        )
        self.assertTrue(
            mod.looks_like_microsoft_365(
                "10 example-net.mail.protection.outlook.com",
                "v=spf1 include:spf.protection.outlook.com -all",
            )
        )
        verified = mod.verifier_reading(
            {"millionverifier": "valid", "zerobounce": "valid", "neverbounce": "valid"},
            {"millionverifier": "invalid", "zerobounce": "invalid", "neverbounce": "invalid"},
        )
        self.assertEqual(verified, "verified")
        catch_all = mod.verifier_reading(
            {"millionverifier": "valid", "zerobounce": "valid", "neverbounce": "valid"},
            {"millionverifier": "valid", "zerobounce": "invalid", "neverbounce": "invalid"},
        )
        self.assertEqual(catch_all, "catch_all")

    def test_grade_f_and_blast_radius_and_swap(self):
        self.assertEqual(mod.treat_moltsets_grade("F"), "C")
        self.assertFalse(mod.grade_is_hard_invalid("F"))
        self.assertTrue(mod.grade_is_hard_invalid("D"))
        leads = [
            {"account_id": "acct-1", "email": "jordan.hale@example.com"},
            {"account_id": "acct-1", "email": "avery.nguyen@example.com"},
            {"account_id": "acct-2", "email": "other@example.com"},
        ]
        found = mod.blast_radius(leads, account_id="acct-1", old_domain="example.com")
        self.assertEqual(len(found), 2)
        plan = mod.email_swap_plan(old_email="jordan.hale@example.com", new_email="jhale@example.net")
        self.assertEqual(plan["email"], "jhale@example.net")
        self.assertEqual(plan["hs_additional_emails"], "jordan.hale@example.com")
        self.assertNotIn("hubspot_owner_id", plan)


class TreeTests(unittest.TestCase):
    def test_public_tree_has_no_em_dash_or_secret_shape(self):
        paths = [ROOT / "reply_loop.py", ROOT / "README.md"]
        paths += list((ROOT / "routes").glob("*.mjs"))
        paths += [path for path in (ROOT / "hubspot-card").rglob("*") if path.is_file()]
        chapter_dir = ROOT.parents[1] / "chapters"
        paths += [
            chapter_dir / "26-replies-into-the-crm.md",
            chapter_dir / "27-reply-loop-go-live.md",
            chapter_dir / "28-reply-from-the-sending-mailbox.md",
            chapter_dir / "29-dead-address-versus-departed.md",
            ROOT.parents[1] / "skills" / "instantly-hubspot-replies" / "SKILL.md",
            ROOT.parents[1] / "skills" / "dead-address-refind" / "SKILL.md",
        ]
        banned = ("\u2014", "pat-na1-", "whsec_live", "@leadalchemy")
        for path in paths:
            self.assertTrue(path.is_file(), f"missing {path}")
            text = path.read_text()
            for token in banned:
                self.assertNotIn(token, text, f"{token} in {path}")

    def test_card_contract(self):
        jsx = (ROOT / "hubspot-card" / "src" / "app" / "cards" / "ReplyCard.jsx").read_text()
        meta = json.loads((ROOT / "hubspot-card" / "src" / "app" / "app-hsmeta.json").read_text())
        self.assertIn("https://your-app.vercel.app", jsx)
        self.assertIn("Sends from", jsx)
        self.assertIn("hubspot.fetch", jsx)
        self.assertIn("const BACKEND", jsx)
        self.assertEqual(meta["config"]["permittedUrls"]["fetch"], ["https://your-app.vercel.app"])
        self.assertEqual(meta["config"]["distribution"], "private")
        self.assertEqual(meta["config"]["auth"]["type"], "static")


if __name__ == "__main__":
    unittest.main()
