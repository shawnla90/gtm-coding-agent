#!/usr/bin/env python3
"""Unit tests for nexus-intel LinkedIn provider switch (no Apify network)."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

SCRIPTS = (
    Path(__file__).resolve().parents[1]
    / "starters"
    / "nexus-intel"
    / "scripts"
)


def _load_scrape_linkedin():
    """Load scrape_linkedin.py without executing its CLI main."""
    path = SCRIPTS / "scrape_linkedin.py"
    sys.path.insert(0, str(SCRIPTS))
    try:
        spec = importlib.util.spec_from_file_location("scrape_linkedin", path)
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        if str(SCRIPTS) in sys.path:
            sys.path.remove(str(SCRIPTS))


class LinkedInProviderTests(unittest.TestCase):
    """Cover harvestapi default and johnvc opt-in input mapping."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load_scrape_linkedin()

    def test_default_provider_is_harvestapi(self) -> None:
        """Unset env keeps harvestapi as the default provider."""
        import os

        os.environ.pop("LINKEDIN_POSTS_PROVIDER", None)
        self.assertEqual(self.mod.linkedin_posts_provider(), "harvestapi")

    def test_unknown_provider_raises(self) -> None:
        """Reject unrecognized LINKEDIN_POSTS_PROVIDER values early."""
        import os

        os.environ["LINKEDIN_POSTS_PROVIDER"] = "not-a-provider"
        with self.assertRaises(ValueError):
            self.mod.linkedin_posts_provider()
        os.environ.pop("LINKEDIN_POSTS_PROVIDER", None)

    def test_harvestapi_profile_input(self) -> None:
        """harvestapi person sources use profilePublicIdentifiers + maxItems."""
        source = {
            "id": 1,
            "handle": "satyanadella",
            "url": "https://www.linkedin.com/in/satyanadella",
            "relevance": "thought-leader",
        }
        actor, payload = self.mod.actor_call_for_source(source, 30, provider="harvestapi")
        self.assertEqual(actor, "harvestapi/linkedin-profile-posts")
        self.assertEqual(payload, {"profilePublicIdentifiers": ["satyanadella"], "maxItems": 30})

    def test_harvestapi_company_input(self) -> None:
        """harvestapi company sources use companyPublicIdentifiers."""
        source = {
            "id": 2,
            "handle": "microsoft",
            "url": "https://www.linkedin.com/company/microsoft",
            "relevance": "competitor",
        }
        actor, payload = self.mod.actor_call_for_source(source, 10, provider="harvestapi")
        self.assertEqual(actor, "harvestapi/linkedin-company-posts")
        self.assertEqual(payload, {"companyPublicIdentifiers": ["microsoft"], "maxItems": 10})

    def test_johnvc_profile_input(self) -> None:
        """johnvc uses one Actor with profileUrls for person pages."""
        source = {
            "id": 1,
            "handle": "satyanadella",
            "url": "https://www.linkedin.com/in/satyanadella/",
            "relevance": "thought-leader",
        }
        actor, payload = self.mod.actor_call_for_source(source, 30, provider="johnvc")
        self.assertEqual(actor, "johnvc/linkedin-posts-api")
        self.assertEqual(
            payload,
            {
                "profileUrls": ["https://www.linkedin.com/in/satyanadella"],
                "maxPostsPerProfile": 30,
            },
        )

    def test_johnvc_company_input_from_handle(self) -> None:
        """johnvc builds a company URL when sources.url is missing."""
        source = {
            "id": 3,
            "handle": "apify",
            "url": None,
            "relevance": "competitor",
        }
        actor, payload = self.mod.actor_call_for_source(source, 20, provider="johnvc")
        self.assertEqual(actor, "johnvc/linkedin-posts-api")
        self.assertEqual(
            payload,
            {
                "profileUrls": ["https://www.linkedin.com/company/apify"],
                "maxPostsPerProfile": 20,
            },
        )


if __name__ == "__main__":
    unittest.main()
