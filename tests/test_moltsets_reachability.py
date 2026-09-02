import sys
import unittest
from pathlib import Path

STARTER_DIR = Path(__file__).resolve().parents[1] / "starters" / "moltsets-reachability"
sys.path.insert(0, str(STARTER_DIR))

from lib import moltsets_client as M  # noqa: E402
from lib.reachability import (GRADE_MULT, classify, companies_match, composite,  # noqa: E402
                              second_pass_decision)


class ClassifyTests(unittest.TestCase):
    def test_grade_a_same_domain_sends(self):
        self.assertEqual(classify("j@acme.com", "A", "acme.com"), ("confirmed_valid", "T1_send", "email"))

    def test_grade_b_sends(self):
        self.assertEqual(classify("j@acme.com", "B", "acme.com")[1], "T1_send")

    def test_grade_a_cross_domain_holds(self):
        v, t, r = classify("j@other.com", "A", "acme.com")
        self.assertEqual((v, t, r), ("confirmed_cross_domain", "HOLD_review", "hold"))

    def test_catch_all_goes_low_volume(self):
        self.assertEqual(classify("j@acme.com", "C", "acme.com"), ("catch_all", "T2_catchall", "email_low_volume"))

    def test_grade_d_never_emails_but_keeps_the_person(self):
        v, t, r = classify("j@acme.com", "D", "acme.com", has_linkedin=True)
        self.assertEqual((v, t, r), ("hard_invalid", "SUPPRESS", "linkedin_then_phone"))
        self.assertEqual(classify("j@acme.com", "D", "acme.com", has_linkedin=False)[2], "hold")

    def test_grade_f_is_no_data_not_invalid(self):
        v, t, r = classify("j@acme.com", "F", "acme.com")
        self.assertEqual(v, "no_data")
        self.assertEqual(r, "second_pass")
        v2, t2, r2 = classify("j@acme.com", "F", "acme.com", second_pass_done=True)
        self.assertEqual((t2, r2), ("HOLD_not_found", "linkedin"))

    def test_not_found_routes_to_second_pass_then_linkedin(self):
        self.assertEqual(classify("j@acme.com", "", "acme.com")[2], "second_pass")
        self.assertEqual(classify("j@acme.com", "", "acme.com", second_pass_done=True)[2], "linkedin")

    def test_freemail_holds(self):
        self.assertEqual(classify("j@gmail.com", "A", "acme.com")[1], "HOLD_review")

    def test_job_change_wins(self):
        self.assertEqual(classify("j@acme.com", "A", "acme.com", still_at_company="moved"),
                         ("job_changed", "HOLD_job_change", "resource"))

    def test_no_email_goes_linkedin(self):
        self.assertEqual(classify("", "", "acme.com", has_linkedin=True)[2], "linkedin")


class SecondPassTests(unittest.TestCase):
    def test_accepts_only_same_domain_a_or_b(self):
        cands = [
            {"full_name": "Jo Smith", "business_email": "jo@usfertility.com", "business_email_risk_score": "A"},
            {"full_name": "Jo Smith", "business_email": "jo@cnet.com", "business_email_risk_score": "A"},
        ]
        d, c = second_pass_decision(cands, "cnet.com", "Jo", "Smith")
        self.assertEqual(d, "accept_same_domain")
        self.assertEqual(c["business_email"], "jo@cnet.com")

    def test_same_domain_bad_grade_is_risky(self):
        cands = [{"full_name": "Jo Smith", "business_email": "jo@cnet.com", "business_email_risk_score": "D"}]
        self.assertEqual(second_pass_decision(cands, "cnet.com", "Jo", "Smith")[0], "risky_same_domain")

    def test_cross_domain_only_is_review(self):
        cands = [{"full_name": "Jo Smith", "business_email": "jo@elsewhere.com", "business_email_risk_score": "A"}]
        self.assertEqual(second_pass_decision(cands, "cnet.com", "Jo", "Smith")[0], "review_cross_domain")

    def test_wrong_name_same_domain_is_not_accepted(self):
        cands = [{"full_name": "Pat Jones", "business_email": "pat@cnet.com", "business_email_risk_score": "A"}]
        self.assertEqual(second_pass_decision(cands, "cnet.com", "Jo", "Smith")[0], "risky_same_domain")


class ScoreTests(unittest.TestCase):
    def test_multipliers(self):
        self.assertEqual(GRADE_MULT["A"], 1.0)
        self.assertEqual(GRADE_MULT["D"], 0.15)
        self.assertGreater(GRADE_MULT["F"], GRADE_MULT["D"])

    def test_composite_head_of_growth(self):
        ts, mult, comp = composite("Head of Growth", "A")
        self.assertEqual((ts, mult, comp), (100, 1.0, 100.0))
        self.assertEqual(composite("Head of Growth", "D")[2], 15.0)

    def test_companies_match(self):
        self.assertEqual(companies_match("Acme Inc", "Acme", "acme.com", "acme.com"), "yes")
        self.assertEqual(companies_match("Acme Inc", "Globex Corp"), "moved")
        self.assertEqual(companies_match("Acme", ""), "unknown")


class ResponseShapeTests(unittest.TestCase):
    def test_reverse_email_lookup_shape(self):
        res = {"work_email_confirmed": "J@Acme.com", "work_email_confirmed_risk_score": "a",
               "work_email_confirmed_status": "2026-08-01", "linkedinurl": "https://www.linkedin.com/in/j",
               "current_company": "Acme", "current_company_url": "https://www.acme.com/"}
        self.assertEqual(M.grade_of(res), "A")
        self.assertEqual(M.email_of(res), "j@acme.com")
        self.assertEqual(M.validated_at_of(res), "2026-08-01")
        self.assertEqual(M.linkedin_of(res), "https://www.linkedin.com/in/j")
        self.assertEqual(M.company_of(res), ("Acme", "acme.com"))

    def test_search_people_shape(self):
        cand = {"business_email": "j@acme.com", "business_email_risk_score": "B",
                "business_email_validated_at": "2026-07-01", "linkedin_url": "https://linkedin.com/in/j",
                "company": {"name": "Acme", "domain": "acme.com"}}
        self.assertEqual(M.grade_of(cand), "B")
        self.assertEqual(M.company_of(cand), ("Acme", "acme.com"))

    def test_best_email_shape(self):
        self.assertEqual(M.grade_of({"email": "j@acme.com", "risk_score": "C"}), "C")

    def test_fair_use_flat_and_nested(self):
        flat = M.fair_use({}, {"fair_use": {"records_remaining_5h": 14991, "records_remaining_1w": 74991}})
        self.assertEqual(flat["records_remaining_5h"], 14991)
        nested = M.fair_use({"fair_use": {"enrich": {"records": {"5h": {"remaining": 15000}, "1w": {"used": 1070, "remaining": 73930}}}},
                             "phone_token_balance": 29}, {})
        self.assertEqual(nested["pools"]["enrich"]["remaining_5h"], 15000)
        self.assertEqual(nested["phone_tokens_remaining"], 29)

    def test_budget_floors(self):
        b = M.Budget(records_floor=25, phone_floor=20)
        self.assertTrue(b.records_ok())
        b.absorb({"records_remaining_5h": 10})
        self.assertFalse(b.records_ok())
        b.absorb({"phone_tokens_remaining": 20})
        self.assertFalse(b.phone_ok())   # 20 - 1 < 20: never spend into the floor
        b.absorb({"phone_tokens_remaining": 21})
        self.assertTrue(b.phone_ok())


if __name__ == "__main__":
    unittest.main()
