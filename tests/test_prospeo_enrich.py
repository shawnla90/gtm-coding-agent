"""No network. The Prospeo client is exercised with a fake session."""

import importlib.util
import json
import sys
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "examples" / "scripts" / "prospeo_enrich.py"
SAMPLE = SCRIPT.with_name("sample_contacts.csv")

spec = importlib.util.spec_from_file_location("prospeo_enrich", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class FakeResponse:
    def __init__(self, status, body, headers=None):
        self.status_code = status
        self._body = body
        self.headers = headers or {}

    def json(self):
        if isinstance(self._body, Exception):
            raise self._body
        return self._body


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, headers=None, json=None, timeout=None):
        self.calls.append({"method": method, "url": url, "headers": headers, "json": json})
        if not self.responses:
            raise AssertionError("unexpected request")
        return self.responses.pop(0)


class MatchTests(unittest.TestCase):
    def test_minimum_datapoints(self):
        self.assertTrue(mod.matchable({"linkedin_url": "https://www.linkedin.com/in/example"}))
        self.assertTrue(mod.matchable({"email": "a@example.com"}))
        self.assertTrue(mod.matchable({"person_id": "abc"}))
        self.assertTrue(mod.matchable({
            "first_name": "Jordan", "last_name": "Hale", "company_website": "example.com",
        }))
        self.assertFalse(mod.matchable({"first_name": "Sam"}))
        self.assertFalse(mod.matchable({"full_name": "Sam Patel"}))
        self.assertTrue(mod.company_name_only({
            "full_name": "Jordan Hale", "company_name": "Example",
        }))

    def test_domain_strips_scheme_and_www(self):
        self.assertEqual(mod.normalize_domain("https://www.example.com/about"), "example.com")


class BodyTests(unittest.TestCase):
    def test_email_and_mobile_flags(self):
        email = mod.enrich_body([{"identifier": "1", "email": "a@example.com"}], "email")
        self.assertEqual(email["only_verified_email"], True)
        self.assertNotIn("only_verified_mobile", email)
        mobile = mod.enrich_body([{"identifier": "1", "linkedin_url": "https://www.linkedin.com/in/example"}], "mobile")
        self.assertEqual(mobile["only_verified_mobile"], True)
        self.assertNotIn("enrich_mobile", mobile)

    def test_search_body_uses_documented_filters(self):
        body = mod.build_search_body(
            ["https://www.example.com"], ["C-Suite"], ["VP Operations"], True, False, 1,
        )
        self.assertEqual(body["page"], 1)
        self.assertEqual(body["filters"]["company"]["websites"]["include"], ["example.com"])
        self.assertEqual(body["filters"]["person_seniority"]["include"], ["C-Suite"])
        self.assertEqual(body["filters"]["person_job_title"]["match_mode"], "CONTAINS")
        self.assertEqual(body["filters"]["person_contact_details"]["mobile"], ["VERIFIED"])
        self.assertNotIn("operator", body["filters"]["person_contact_details"])

    def test_bad_seniority_is_rejected(self):
        with self.assertRaises(mod.ProspeoError):
            mod.build_search_body(["example.com"], ["Boss"], None, False, False, 1)

    def test_bulk_refuses_over_50(self):
        client = mod.ProspeoClient("k", session=FakeSession([]))
        records = [{"identifier": str(i), "email": "a@example.com"} for i in range(51)]
        with self.assertRaises(mod.ProspeoError):
            client.enrich_bulk(records, "email")
        self.assertEqual(client.session.calls, [])


class ContactParsingTests(unittest.TestCase):
    def test_masked_and_unrevealed_stay_blank(self):
        status, value = mod.usable_contact({
            "status": "VERIFIED", "revealed": False, "mobile": "+1 415-3**-****",
        })
        self.assertEqual((status, value), ("VERIFIED", ""))
        status, value = mod.usable_contact({
            "status": "VERIFIED", "revealed": True, "email": "jordan.hale@example.com",
        })
        self.assertEqual(value, "jordan.hale@example.com")

    def test_company_switchboard_is_not_the_mobile(self):
        flat = mod.flatten_person(
            {"person_id": "p1", "full_name": "Jordan Hale", "mobile": {
                "status": "VERIFIED", "revealed": False, "mobile": "+1 555-01**-****",
            }},
            {"domain": "example.com", "phone_hq": {"phone_hq": "+15550199"}},
        )
        self.assertEqual(flat["mobile"], "")
        self.assertEqual(flat["company_phone_hq"], "+15550199")
        self.assertNotEqual(flat["mobile"], flat["company_phone_hq"])


class RouteTests(unittest.TestCase):
    def test_waterfall_order(self):
        self.assertEqual(mod.route_contact(
            email_verified=True, mobile_number="", mobile_status="", phone_type=None, dnc_match=None,
        ), mod.EMAIL_ONLY)
        self.assertEqual(mod.route_contact(
            email_verified=False, mobile_number="", mobile_status="", phone_type=None, dnc_match=None,
        ), mod.NO_CHANNEL)
        self.assertEqual(mod.route_contact(
            email_verified=True, mobile_number="+15550100", mobile_status="VERIFIED",
            phone_type=None, dnc_match=None,
        ), mod.PENDING)
        self.assertEqual(mod.route_contact(
            email_verified=True, mobile_number="+15550100", mobile_status="VERIFIED",
            phone_type="landline", dnc_match=None,
        ), mod.EMAIL_ONLY)
        self.assertEqual(mod.route_contact(
            email_verified=True, mobile_number="+15550100", mobile_status="VERIFIED",
            phone_type="mobile", dnc_match=None,
        ), mod.PENDING)
        self.assertEqual(mod.route_contact(
            email_verified=True, mobile_number="+15550100", mobile_status="VERIFIED",
            phone_type="mobile", dnc_match=True,
        ), mod.EMAIL_ONLY)
        self.assertEqual(mod.route_contact(
            email_verified=True, mobile_number="+15550100", mobile_status="VERIFIED",
            phone_type="mobile", dnc_match=False,
        ), mod.CLEARED)

    def test_stale_phone_type_does_not_clear_a_new_number(self):
        phone, dnc = mod.checks_for(
            {"mobile": "", "phone_type": "mobile", "dnc_match": "false"},
            "+15550100",
            None,
        )
        self.assertIsNone(phone)
        self.assertIsNone(dnc)

    def test_hash_file_match(self):
        number = "+15550100"
        digest = mod.hash_number(number)
        path = Path(__file__).with_name("_dnc_hashes.txt")
        path.write_text(digest + "\n")
        try:
            self.assertTrue(mod.dnc_file_match(number, str(path)))
            self.assertFalse(mod.dnc_file_match("+15550101", str(path)))
            self.assertIsNone(mod.dnc_file_match(number, None))
        finally:
            path.unlink()


class ClientTests(unittest.TestCase):
    def test_account_is_a_get_and_post_sends_the_key_header(self):
        session = FakeSession([
            FakeResponse(200, {"error": False, "response": {"current_plan": "STARTER", "remaining_credits": 99}}),
        ])
        client = mod.ProspeoClient("secret-key", session=session, sleep=lambda _s: None)
        info = client.account()
        self.assertEqual(info["remaining_credits"], 99)
        call = session.calls[0]
        self.assertEqual(call["method"], "GET")
        self.assertEqual(call["url"], "https://api.prospeo.io/account-information")
        self.assertEqual(call["headers"]["X-KEY"], "secret-key")
        self.assertNotIn("Content-Type", call["headers"])

    def test_retries_429_then_reads_reset_header(self):
        slept = []
        session = FakeSession([
            FakeResponse(429, {"error": True, "error_code": "Rate limit exceeded"}, {
                "x-minute-request-left": "0",
                "x-minute-reset-seconds": "3",
                "x-daily-request-left": "10",
            }),
            FakeResponse(200, {"error": False, "free": False, "results": [], "pagination": {}}),
        ])
        client = mod.ProspeoClient("secret-key", session=session, sleep=slept.append)
        payload = client.search_page({"page": 1, "filters": {}})
        self.assertEqual(payload["free"], False)
        self.assertEqual(slept, [3.0])
        self.assertEqual(session.calls[1]["headers"]["Content-Type"], "application/json")

    def test_daily_limit_does_not_sleep_until_tomorrow(self):
        session = FakeSession([
            FakeResponse(429, {"error": True}, {
                "x-daily-request-left": "0",
                "x-daily-reset-seconds": "80000",
            }),
        ])
        client = mod.ProspeoClient("secret-key", session=session, sleep=lambda _s: None)
        with self.assertRaises(mod.ProspeoError) as caught:
            client.account()
        self.assertEqual(caught.exception.code, "RATE_LIMIT")
        self.assertEqual(len(session.calls), 1)

    def test_key_is_redacted_from_errors(self):
        session = FakeSession([
            FakeResponse(400, {"error": True, "error_code": "INVALID_FILTERS", "filter_error": "bad secret-key"}),
        ])
        client = mod.ProspeoClient("secret-key", session=session, sleep=lambda _s: None)
        with self.assertRaises(mod.ProspeoError) as caught:
            client.search_page({"page": 1, "filters": {}})
        self.assertNotIn("secret-key", str(caught.exception))
        self.assertIn("[redacted]", str(caught.exception))

    def test_no_match_is_a_row_error(self):
        session = FakeSession([
            FakeResponse(400, {"error": True, "error_code": "NO_MATCH"}),
        ])
        client = mod.ProspeoClient("secret-key", session=session, sleep=lambda _s: None)
        with self.assertRaises(mod.ProspeoError) as caught:
            client.enrich_one({"identifier": "1", "full_name": "Jordan Hale", "company_website": "example.com"}, "email")
        self.assertEqual(caught.exception.code, "NO_MATCH")
        self.assertEqual(session.calls[0]["url"], "https://api.prospeo.io/enrich-person")
        self.assertEqual(session.calls[0]["json"]["only_verified_email"], True)
        self.assertNotIn("identifier", session.calls[0]["json"]["data"])


class DryRunTests(unittest.TestCase):
    def test_commands_send_nothing_and_hide_the_key(self):
        import os
        os.environ["PROSPEO_API_KEY"] = "super-secret-value"
        stdout = []
        real = sys.stdout

        class Grab:
            def write(self, text):
                stdout.append(text)

            def flush(self):
                pass

        sys.stdout = Grab()
        try:
            self.assertEqual(mod.main([
                "enrich", str(SAMPLE), "--mode", "email", "--dry-run", "--limit", "5",
            ]), 0)
            self.assertEqual(mod.main([
                "route", str(SAMPLE), "--dry-run", "--limit", "5",
            ]), 0)
            self.assertEqual(mod.main([
                "search", "--domain", "example.com", "--seniority", "C-Suite", "--has-mobile", "--dry-run",
            ]), 0)
        finally:
            sys.stdout = real
            os.environ.pop("PROSPEO_API_KEY", None)
        text = "".join(stdout)
        self.assertNotIn("super-secret-value", text)
        self.assertIn("https://api.prospeo.io/bulk-enrich-person", text)
        self.assertIn("no request sent", text)
        self.assertIn("only_verified_mobile", text)
        body = json.loads(
            text.split("dry-run. POST https://api.prospeo.io/search-person", 1)[1]
            .split("search does not reveal", 1)[0]
        )
        self.assertEqual(body["filters"]["company"]["websites"]["include"], ["example.com"])

    def test_spend_guard_blocks_a_live_batch_under_the_ceiling(self):
        with self.assertRaises(mod.ProspeoError):
            mod.guard_spend(5, "mobile", yes=False, account={"current_plan": "STARTER", "remaining_credits": 20})


if __name__ == "__main__":
    unittest.main()
