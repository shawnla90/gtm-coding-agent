"""Compose the HubSpot Pages API payload per enriched account.

Inputs:
  - brief (Brief instance from _load_brief)
  - enriched accounts (list[Account] with .columns filled)
  - template module-fields schema (hubspot-template/module-fields.json)

Outputs:
  - list of dicts ready to POST to /cms/v3/pages/landing-pages
  - written to outputs/{brief_slug}/{account_slug}.json for inspection
"""
from __future__ import annotations

import json
import os
import re
import unicodedata
from pathlib import Path

OUTPUTS_DIR = Path("outputs")


def slugify(text: str) -> str:
    """Stable URL-safe slug. Lowercase, ASCII, hyphenated."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text or "page"


def _resolve_variable(var: str, account, brief) -> str:
    """Resolve a {{var}} placeholder using account.columns + account fields.

    Naming convention:
      {{company_name}}              -> account.company
      {{hero_headline}}             -> account.columns["hero-copy"]["headline"]
      {{pain_point_primary_block}}  -> account.columns["pain-points"]["primary"]
      {{tech_stack_summary}}        -> account.columns["tech-stack"]["summary"]
      {{cta_block}}                 -> rendered CTA HTML built from brief
    """
    key = var.strip("{} ").lower()

    direct = {
        "company_name": account.company,
        "company_domain": account.domain,
        "contact_name": account.contact_name,
        "contact_title": account.contact_title,
    }
    if key in direct:
        return direct[key]

    if key == "cta_block":
        label = brief.frontmatter.get("cta_label", "Book a walkthrough")
        url = brief.frontmatter.get("cta_url", "#")
        return f'<a class="cta" href="{url}">{label}</a>'

    if key == "model_tier_wedge":
        return (
            "Opus-tier models per account, run against a controlled list. "
            "That economic shape is what makes the page personal in a way "
            "shared-tier tools can not match."
        )

    if key == "peer_anchor":
        # Static peer phrasing for the nurture brief. The chapter shows how
        # to replace this with an actual peer-list lookup once the user has
        # built one.
        return "a Series B SaaS with the same shaped funnel"

    # Column lookups: split on the LAST underscore for column-slug/field split,
    # since column slugs use hyphens internally (e.g., "pain-points") but the
    # placeholder uses underscores for HubL friendliness (pain_points_primary).
    aliases = {
        "hero_headline": ("hero-copy", "headline"),
        "hero_subhead": ("hero-copy", "subhead"),
        "pain_point_primary_block": ("pain-points", "primary"),
        "pain_point_root_cause": ("pain-points", "root_cause"),
        "pain_point_evidence": ("pain-points", "evidence"),
        "tech_stack_summary": ("tech-stack", "summary"),
        "hook": ("hook-angle", "hook"),
        "icp_score": ("icp-score", "score"),
        "deliverable_pitch": ("hero-copy", "body_block"),
    }
    if key in aliases:
        col, field = aliases[key]
        return str(account.columns.get(col, {}).get(field, ""))

    return ""  # unknown placeholder -> empty


_PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")


def render_body(brief, account) -> str:
    """Replace all {{var}} placeholders in the brief body with column outputs."""
    return _PLACEHOLDER_RE.sub(lambda m: _resolve_variable(m.group(0), account, brief), brief.body)


def build_layout_sections(brief, account) -> dict:
    """The HubSpot Pages API payload's `layoutSections` field.

    The starter template has a single section called `main_content` with three
    custom_widget modules: hero, body_rich_text, cta. The publisher reads this
    from hubspot-template/module-fields.json. Override per-template.
    """
    body_html = render_body(brief, account)
    hero = account.columns.get("hero-copy", {})
    cta_label = brief.frontmatter.get("cta_label", "Book a walkthrough")
    cta_url = brief.frontmatter.get("cta_url", "#")
    return {
        "main_content": {
            "name": "main_content",
            "label": "Main content",
            "rows": [
                {
                    "cells": [
                        {
                            "columnWidth": 100,
                            "widgets": [
                                {
                                    "type": "custom_widget",
                                    "name": "hero",
                                    "params": {
                                        "headline": hero.get("headline", account.company),
                                        "subhead": hero.get("subhead", ""),
                                        "cta_label": hero.get("cta_label", cta_label),
                                        "cta_url": cta_url,
                                    },
                                }
                            ],
                        }
                    ]
                },
                {
                    "cells": [
                        {
                            "columnWidth": 100,
                            "widgets": [
                                {
                                    "type": "custom_widget",
                                    "name": "body_rich_text",
                                    "params": {"html": body_html},
                                }
                            ],
                        }
                    ]
                },
            ],
        }
    }


def build_payload(brief, account, *, template_path: str) -> dict:
    """Full payload for POST /cms/v3/pages/landing-pages."""
    page_slug = slugify(f"{brief.frontmatter.get('campaign', brief.slug)}-{account.company}")
    hero = account.columns.get("hero-copy", {})
    headline = hero.get("headline") or f"Built for {account.company}"
    return {
        "name": f"LP - {account.company} - {brief.frontmatter.get('campaign', brief.slug)}",
        "htmlTitle": headline,
        "metaDescription": (hero.get("subhead") or "")[:200],
        "slug": f"lp/{page_slug}",
        "templatePath": template_path,
        "state": "DRAFT",
        "publishImmediately": False,
        "language": "en",
        "campaign": brief.frontmatter.get("campaign", ""),
        "layoutSections": build_layout_sections(brief, account),
    }


def generate(brief, accounts) -> list[dict]:
    """Build payloads for all accounts and write them to outputs/{slug}/."""
    template_path = os.environ.get("HUBSPOT_TEMPLATE_PATH", "/landing-engine/landing-page.html")
    out_dir = OUTPUTS_DIR / brief.slug
    out_dir.mkdir(parents=True, exist_ok=True)
    payloads = []
    for account in accounts:
        payload = build_payload(brief, account, template_path=template_path)
        payloads.append(payload)
        target = out_dir / f"{slugify(account.company)}.json"
        target.write_text(json.dumps(payload, indent=2))
    return payloads
