import sys
import unittest
from pathlib import Path
from unittest.mock import patch


STARTER_DIR = Path(__file__).resolve().parents[1] / "starters" / "reddit-buyer-signals"
sys.path.insert(0, str(STARTER_DIR))

from lib import profile_lookup  # noqa: E402
import unmask  # noqa: E402


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


class ProfileLookupTests(unittest.TestCase):
    def test_reddit_profile_domain_is_direct_and_eligible(self):
        response = FakeResponse(payload={
            "data": {
                "subreddit": {
                    "public_description": "I run Acme at https://acme.example.com",
                    "title": "Acme founder",
                }
            }
        })
        with patch.object(profile_lookup.requests, "get", return_value=response):
            result = profile_lookup._reddit_profile("acme_author")

        self.assertEqual(result["review_verdict"], "direct_disclosure")
        self.assertEqual(result["enrichment_eligibility"], "eligible_direct_disclosure")
        self.assertTrue(result["disclosed"])
        self.assertEqual(result["domains"], ["example.com"])
        self.assertEqual(
            result["evidence"][0]["url"],
            "https://www.reddit.com/user/acme_author/",
        )

    def test_exa_result_is_candidate_and_never_disclosed(self):
        response = FakeResponse(payload={
            "results": [{
                "url": "https://acme.com/team/reddit_author",
                "title": "reddit_author at Acme",
                "text": "A possible professional page for reddit_author.",
            }]
        })
        with (
            patch.object(profile_lookup, "_get_secret", return_value="test-key"),
            patch.object(profile_lookup.requests, "post", return_value=response),
        ):
            result = profile_lookup._exa_search("reddit_author")

        self.assertEqual(result["review_verdict"], "plausible_candidate")
        self.assertEqual(result["enrichment_eligibility"], "manual_review")
        self.assertFalse(result["disclosed"])
        self.assertIn("acme.com", result["domains"])
        self.assertEqual(
            result["evidence"][0]["url"],
            "https://acme.com/team/reddit_author",
        )

    def test_profile_social_link_without_company_domain_requires_review(self):
        response = FakeResponse(payload={
            "data": {
                "subreddit": {
                    "public_description": "Find me at https://linkedin.com/in/example-author",
                    "title": "Example author",
                }
            }
        })
        with patch.object(profile_lookup.requests, "get", return_value=response):
            result = profile_lookup._reddit_profile("example_author")

        self.assertEqual(result["review_verdict"], "plausible_candidate")
        self.assertEqual(result["enrichment_eligibility"], "manual_review")
        self.assertFalse(result["disclosed"])
        self.assertEqual(result["domains"], [])

    def test_search_candidate_does_not_hide_later_direct_profile_evidence(self):
        candidate = profile_lookup._result(
            profile_lookup.PLAUSIBLE_CANDIDATE,
            source="exa",
            signal="candidate",
            domains=["candidate.com"],
            evidence=[{"url": "https://candidate.com", "kind": "web_search_candidate", "excerpt": ""}],
        )
        direct = profile_lookup._result(
            profile_lookup.DIRECT_DISCLOSURE,
            source="playwright",
            signal="direct",
            domains=["direct.com"],
            evidence=[{"url": "https://www.reddit.com/user/test/", "kind": "reddit_profile", "excerpt": ""}],
        )
        with (
            patch.object(profile_lookup, "_exa_search", return_value=candidate),
            patch.object(profile_lookup, "_rendered_profile", return_value=direct),
            patch.object(profile_lookup.time, "sleep", return_value=None),
        ):
            result = profile_lookup.lookup_profile("test", tiers=["exa", "playwright"])

        self.assertEqual(result["review_verdict"], "direct_disclosure")
        self.assertEqual(result["domains"], ["direct.com"])

    def test_completed_tier_with_no_evidence_is_not_a_lookup_error(self):
        with (
            patch.object(
                profile_lookup,
                "_reddit_profile",
                return_value=profile_lookup._no_evidence("reddit_json", "profile has no links"),
            ),
            patch.object(
                profile_lookup,
                "_exa_search",
                return_value=profile_lookup._lookup_error("exa", "no API key"),
            ),
            patch.object(profile_lookup.time, "sleep", return_value=None),
        ):
            result = profile_lookup.lookup_profile("test", tiers=["reddit_profile", "exa"])

        self.assertEqual(result["review_verdict"], "no_public_evidence")
        self.assertEqual(result["lookup_status"], "no_links_found")
        self.assertIn("no API key", result["errors"])

    def test_search_no_match_does_not_hide_profile_lookup_failure(self):
        with (
            patch.object(
                profile_lookup,
                "_reddit_profile",
                return_value=profile_lookup._lookup_error("reddit_json", "HTTP 403"),
            ),
            patch.object(
                profile_lookup,
                "_exa_search",
                return_value=profile_lookup._no_evidence("exa", "no matches"),
            ),
            patch.object(profile_lookup.time, "sleep", return_value=None),
        ):
            result = profile_lookup.lookup_profile("test", tiers=["reddit_profile", "exa"])

        self.assertEqual(result["review_verdict"], "lookup_error")
        self.assertIn("HTTP 403", result["errors"])

    def test_all_failed_tiers_return_lookup_error(self):
        with (
            patch.object(
                profile_lookup,
                "_reddit_profile",
                return_value=profile_lookup._lookup_error("reddit_json", "HTTP 403"),
            ),
            patch.object(
                profile_lookup,
                "_exa_search",
                return_value=profile_lookup._lookup_error("exa", "no API key"),
            ),
            patch.object(profile_lookup.time, "sleep", return_value=None),
        ):
            result = profile_lookup.lookup_profile("test", tiers=["reddit_profile", "exa"])

        self.assertEqual(result["review_verdict"], "lookup_error")
        self.assertEqual(result["lookup_status"], "lookup_error")
        self.assertEqual(result["enrichment_eligibility"], "not_eligible")


class UnmaskGateTests(unittest.TestCase):
    def test_only_exact_profile_disclosure_is_enrichment_eligible(self):
        direct = profile_lookup._result(
            profile_lookup.DIRECT_DISCLOSURE,
            source="reddit_json",
            signal="profile domain",
            domains=["acme.com"],
            evidence=[{
                "url": "https://www.reddit.com/user/acme_author/",
                "kind": "reddit_profile",
                "excerpt": "I run acme.com",
            }],
        )
        with patch.object(profile_lookup, "lookup_profile", return_value=direct):
            result = unmask.disclose({"author": "acme_author"}, use_profile=True)

        self.assertTrue(result["disclosed"])
        self.assertEqual(result["domain"], "acme.com")
        self.assertEqual(result["enrichment_eligibility"], "eligible_direct_disclosure")

    def test_search_candidate_is_manual_review_and_has_no_enrichment_domain(self):
        candidate = profile_lookup._result(
            profile_lookup.PLAUSIBLE_CANDIDATE,
            source="exa",
            signal="possible match",
            domains=["possible.com"],
            evidence=[{
                "url": "https://possible.com/team/reddit_author",
                "kind": "web_search_candidate",
                "excerpt": "possible match",
            }],
        )
        with patch.object(profile_lookup, "lookup_profile", return_value=candidate):
            result = unmask.disclose({"author": "reddit_author"}, use_profile=True)

        self.assertFalse(result["disclosed"])
        self.assertIsNone(result["domain"])
        self.assertEqual(result["candidate_domain"], "possible.com")
        self.assertEqual(result["enrichment_eligibility"], "manual_review")

    def test_thread_domain_is_candidate_not_direct_disclosure(self):
        result = unmask.disclose({
            "author": "anonymous_user",
            "snippet": "Has anyone compared vendor-example.com with the incumbent?",
            "url": "https://reddit.com/r/example/comments/123",
        })

        self.assertFalse(result["disclosed"])
        self.assertIsNone(result["domain"])
        self.assertEqual(result["candidate_domain"], "vendor-example.com")
        self.assertEqual(result["review_verdict"], "plausible_candidate")

    def test_lookup_error_is_distinct_from_no_public_evidence(self):
        failure = profile_lookup._lookup_error("none", "all tiers failed")
        with patch.object(profile_lookup, "lookup_profile", return_value=failure):
            result = unmask.disclose({"author": "anonymous_user"}, use_profile=True)

        self.assertEqual(result["review_verdict"], "lookup_error")
        self.assertEqual(result["enrichment_eligibility"], "not_eligible")


if __name__ == "__main__":
    unittest.main()
