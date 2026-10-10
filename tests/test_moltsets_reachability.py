import sys
import unittest
from pathlib import Path

STARTER_DIR = Path(__file__).resolve().parents[1] / "starters" / "moltsets-reachability"
sys.path.insert(0, str(STARTER_DIR))
sys.modules.pop("lib", None)  # another starter's `lib` may already be imported

from lib import moltsets_client as M  # noqa: E402
from lib.reachability import (DELTA_CLASSES, DELTA_LEGEND, GRADE_MULT, HARD_FAIL, classify,  # noqa: E402
                              combine_employment, companies_match, composite, delta_class, name_matches,
                              norm_verifier_status, profile_decision, second_pass_decision)


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


class EmploymentTests(unittest.TestCase):
    def test_both_agree_still(self):
        self.assertEqual(combine_employment("yes", "yes"), ("yes", "both", "yes"))

    def test_either_moved_wins(self):
        self.assertEqual(combine_employment("yes", "moved"), ("moved", "both", "no"))
        self.assertEqual(combine_employment("moved", "unknown"), ("moved", "apollo", "n/a"))

    def test_moltsets_only(self):
        self.assertEqual(combine_employment("unknown", "yes"), ("yes", "moltsets", "n/a"))
        self.assertEqual(combine_employment(), ("unknown", "none", "n/a"))

    def test_reverse_linkedin_company_shape(self):
        res = {"title": "GTM Engineer", "company": {"name": "Acme", "website_url": "https://www.acme.com/"}}
        self.assertEqual(M.company_of(res), ("Acme", "acme.com"))


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


class VerifierNormalizeTests(unittest.TestCase):
    def test_zerobounce_vocabulary(self):
        for raw, want in [("valid", "valid"), ("catch-all", "catch-all"), ("unknown", "unknown"), ("invalid", "invalid"),
                          ("do_not_mail", "do_not_mail"), ("abuse", "abuse"), ("spamtrap", "abuse")]:
            self.assertEqual(norm_verifier_status(raw), want)

    def test_other_vendors_and_case(self):
        self.assertEqual(norm_verifier_status("Deliverable"), "valid")
        self.assertEqual(norm_verifier_status("CATCHALL"), "catch-all")
        self.assertEqual(norm_verifier_status("accept_all"), "catch-all")
        self.assertEqual(norm_verifier_status("undeliverable"), "invalid")
        self.assertEqual(norm_verifier_status("disposable"), "do_not_mail")
        self.assertEqual(norm_verifier_status("risky"), "unknown")

    def test_empty_stays_empty_and_unknown_words_are_unknown(self):
        self.assertEqual(norm_verifier_status(""), "")
        self.assertEqual(norm_verifier_status(None), "")
        self.assertEqual(norm_verifier_status("purple"), "unknown")

    def test_hard_fail_set(self):
        self.assertEqual(HARD_FAIL, {"invalid", "do_not_mail", "abuse"})


class DeltaClassTests(unittest.TestCase):
    """The thirteen classes, one assertion each, in the order of the legend."""

    def test_agree(self):
        self.assertEqual(delta_class("valid", "A"), "agree")
        self.assertEqual(delta_class("valid", "B"), "agree")

    def test_catchall_upgrade(self):
        self.assertEqual(delta_class("catch-all", "A"), "molt_upgrades_catchall")

    def test_recovers_invalid_needs_a_corrected_address(self):
        self.assertEqual(delta_class("invalid", "A", corrected="yes"), "molt_recovers_invalid")
        self.assertEqual(delta_class("do_not_mail", "B", corrected=True), "molt_recovers_invalid")

    def test_corrects_address_on_valid_or_catchall(self):
        self.assertEqual(delta_class("valid", "A", corrected="yes"), "molt_corrects_address")
        self.assertEqual(delta_class("catch-all", "A", corrected="yes"), "molt_corrects_address")

    def test_contradicts_invalid_is_review_not_send(self):
        self.assertEqual(delta_class("invalid", "A"), "molt_contradicts_invalid")

    def test_grades_unknown(self):
        self.assertEqual(delta_class("unknown", "A"), "molt_grades_unknown")
        self.assertEqual(delta_class("", "A"), "molt_grades_unknown")

    def test_downgrades_valid_to_d(self):
        self.assertEqual(delta_class("valid", "D"), "molt_downgrades_valid")

    def test_confirms_invalid(self):
        self.assertEqual(delta_class("invalid", "D"), "confirms_invalid")
        self.assertEqual(delta_class("abuse", ""), "confirms_invalid")

    def test_catchall_grade_c(self):
        self.assertEqual(delta_class("valid", "C"), "molt_catchall")

    def test_no_data_is_f(self):
        self.assertEqual(delta_class("valid", "F"), "molt_no_data")

    def test_cross_domain_splits_on_employment(self):
        self.assertEqual(delta_class("valid", "F", sp_decision="review_cross_domain", still_at_company="yes"),
                         "person_confirmed_other_email")
        self.assertEqual(delta_class("valid", "F", sp_decision="review_cross_domain", still_at_company="moved"),
                         "cross_domain_review")

    def test_not_in_graph(self):
        self.assertEqual(delta_class("valid", ""), "not_in_graph")
        self.assertEqual(delta_class("valid", "", sp_decision="name_mismatch"), "not_in_graph")

    def test_every_class_has_a_legend_line(self):
        self.assertEqual(len(DELTA_LEGEND), 13)
        for k in ("agree", "molt_upgrades_catchall", "molt_recovers_invalid", "molt_corrects_address",
                  "molt_contradicts_invalid", "molt_grades_unknown", "molt_downgrades_valid", "confirms_invalid",
                  "molt_catchall", "molt_no_data", "person_confirmed_other_email", "cross_domain_review", "not_in_graph"):
            self.assertIn(k, DELTA_CLASSES)


class ProfileDecisionTests(unittest.TestCase):
    """search_business_profile_by_name returns one flat profile; the domain is the identity check."""

    def _res(self, email="jo@acme.com", grade="A", first="Jo", last="Smith"):
        return {"first_name": first, "last_name": last, "title": "Head of Growth",
                "work_email_confirmed": email, "work_email_confirmed_risk_score": grade,
                "work_email_confirmed_status": "2026-08-01", "linkedinurl": "https://www.linkedin.com/in/jo",
                "current_company": "Acme", "current_company_url": "https://acme.com"}

    def test_accepts_same_domain_a(self):
        d, snap = profile_decision(self._res(), 200, "acme.com", "", "Jo", "Smith")
        self.assertEqual(d, "accept_same_domain")
        self.assertEqual(snap["grade"], "A")
        self.assertEqual(snap["company_domain"], "acme.com")

    def test_same_domain_f_is_risky(self):
        self.assertEqual(profile_decision(self._res(grade="F"), 200, "acme.com")[0], "risky_same_domain")

    def test_no_email_means_person_known_address_unproven(self):
        self.assertEqual(profile_decision(self._res(email=""), 200, "acme.com")[0], "profile_no_email")

    def test_other_domain_is_review_never_adopted(self):
        self.assertEqual(profile_decision(self._res(email="jo@elsewhere.com"), 200, "acme.com")[0], "review_cross_domain")

    def test_corporate_domain_also_counts_as_same(self):
        self.assertEqual(profile_decision(self._res(email="jo@parent.com"), 200, "acme.com", "parent.com")[0],
                         "accept_same_domain")

    def test_wrong_person_is_name_mismatch(self):
        self.assertEqual(profile_decision(self._res(first="Pat", last="Jones"), 200, "acme.com", "", "Jo", "Smith")[0],
                         "name_mismatch")

    def test_404_and_empty_are_no_candidate(self):
        self.assertEqual(profile_decision({}, 404, "acme.com"), ("no_candidate", {}))
        self.assertEqual(profile_decision(None, 200, "acme.com")[0], "no_candidate")

    def test_name_matching_tolerances(self):
        self.assertTrue(name_matches("Chris", "Lee", "Christopher", "Lee"))
        self.assertTrue(name_matches("Ana", "Garcia-Lopez", "Ana", "Lopez"))
        self.assertTrue(name_matches("Jo", "Smith", "", ""))
        self.assertFalse(name_matches("Bob", "Smith", "Robert", "Smith"))


class ImportGradedTests(unittest.TestCase):
    def test_import_recomputes_routing_and_delta(self):
        import csv
        import os
        import sqlite3
        import subprocess
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            csv_path = Path(td) / "graded.csv"
            with csv_path.open("w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=["full_name", "title", "company", "domain", "email", "zb_status",
                                                  "grade", "molt_email", "still_at_company", "rel_http", "pool"])
                w.writeheader()
                w.writerow({"full_name": "Jo Smith", "title": "Head of Growth", "company": "Acme", "domain": "acme.com",
                            "email": "jo@acme.com", "zb_status": "valid", "grade": "A", "molt_email": "jo@acme.com",
                            "still_at_company": "yes", "rel_http": "200", "pool": "A"})
                w.writerow({"full_name": "Pat Jones", "title": "CRO", "company": "Acme", "domain": "acme.com",
                            "email": "pat@acme.com", "zb_status": "invalid", "grade": "A", "molt_email": "pjones@acme.com",
                            "still_at_company": "yes", "rel_http": "404", "pool": "dropped"})
                w.writerow({"full_name": "Sam Lee", "title": "VP Sales", "company": "Acme", "domain": "acme.com",
                            "email": "sam@acme.com", "zb_status": "valid", "grade": "", "molt_email": "",
                            "still_at_company": "moved", "rel_http": "200", "pool": "A"})
            db = Path(td) / "t.db"
            env = dict(os.environ, REACHABILITY_DB=str(db))
            out = subprocess.run([sys.executable, str(STARTER_DIR / "import_graded.py"), str(csv_path)],
                                 env=env, capture_output=True, text=True)
            self.assertEqual(out.returncode, 0, out.stderr)
            con = sqlite3.connect(db)
            rows = {r[0]: r for r in con.execute("SELECT email, first_name, last_name, verifier_status, tier, route, delta_class, corrected FROM contacts")}
            self.assertEqual(rows["jo@acme.com"][1:3], ("Jo", "Smith"))
            self.assertEqual(rows["jo@acme.com"][3:], ("valid", "T1_send", "email", "agree", "no"))
            self.assertEqual(rows["pat@acme.com"][3:], ("invalid", "T1_send_corrected", "email", "molt_recovers_invalid", "yes"))
            self.assertEqual(rows["sam@acme.com"][4:7], ("HOLD_job_change", "resource", "not_in_graph"))
            self.assertTrue((Path(td) / "t_grade_summary.json").exists())   # per-database receipts: <stem>_grade_summary.json


if __name__ == "__main__":
    unittest.main()
