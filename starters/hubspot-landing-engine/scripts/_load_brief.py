"""Load a brief from local markdown OR from a HubSpot CMS Blog Post.

Brief format: YAML frontmatter + markdown body with `{{variable}}` placeholders.

When BRIEF_SOURCE=local (default), reads from `briefs/{slug}.md`.
When BRIEF_SOURCE=hubspot, fetches Blog Posts with state=PUBLISHED and the
"Brief" category, matches by name == slug.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests
import yaml

from auth_private_app import headers


@dataclass
class Brief:
    slug: str
    frontmatter: dict
    body: str

    @property
    def campaign(self) -> str:
        return self.frontmatter.get("campaign", "")

    @property
    def template_module(self) -> str:
        return self.frontmatter.get("template_module", "landing-page")

    @property
    def columns_required(self) -> list[str]:
        return list(self.frontmatter.get("columns_required", []))


_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


def _parse_brief_text(slug: str, text: str) -> Brief:
    m = _FRONTMATTER_RE.match(text)
    if not m:
        raise ValueError(f"brief '{slug}' missing YAML frontmatter")
    fm = yaml.safe_load(m.group(1)) or {}
    return Brief(slug=slug, frontmatter=fm, body=m.group(2).strip())


def _load_local(slug: str, briefs_dir: Path = Path("briefs")) -> Brief:
    path = briefs_dir / f"{slug}.md"
    if not path.exists():
        raise FileNotFoundError(f"brief not found at {path}")
    return _parse_brief_text(slug, path.read_text())


def _load_hubspot(slug: str) -> Brief:
    # Find a published blog post whose name matches the slug, in any blog under
    # the "Brief" category. Two queries: list blog posts filtered by name.
    resp = requests.get(
        "https://api.hubapi.com/cms/v3/blogs/posts",
        headers=headers(),
        params={"name": slug, "state": "PUBLISHED", "limit": 5},
        timeout=15,
    )
    resp.raise_for_status()
    results = resp.json().get("results", [])
    if not results:
        raise LookupError(
            f"no published Blog Post named '{slug}' found in HubSpot. "
            "Confirm the post exists and the name field matches the slug exactly."
        )
    post = results[0]
    # Blog posts return content in postBody (rich HTML). For our use, we
    # expect briefs to be written as markdown in the post body, between
    # `---` frontmatter fences, with HTML left as-is. The simplest contract:
    # the Blog Post's `postBody` IS the frontmatter+body text as plain markdown
    # wrapped in <pre> or similar. The user controls how they paste it.
    text = post.get("postBody") or post.get("postSummary") or ""
    # Strip outer <p>/<pre> if present, then parse.
    text = re.sub(r"<pre[^>]*>|</pre>", "", text)
    text = re.sub(r"<p[^>]*>|</p>", "", text).strip()
    if not text.startswith("---"):
        raise ValueError(
            f"HubSpot Blog Post '{slug}' postBody does not start with `---` frontmatter."
        )
    return _parse_brief_text(slug, text)


def load_brief(slug: str, *, source: Optional[str] = None) -> Brief:
    source = (source or os.environ.get("BRIEF_SOURCE") or "local").lower()
    if source == "hubspot":
        return _load_hubspot(slug)
    return _load_local(slug)


if __name__ == "__main__":
    import argparse

    from dotenv import load_dotenv

    load_dotenv()
    p = argparse.ArgumentParser(description="Load a brief and print frontmatter.")
    p.add_argument("slug")
    p.add_argument("--source", choices=["local", "hubspot"], default=None)
    args = p.parse_args()

    brief = load_brief(args.slug, source=args.source)
    print(f"slug:       {brief.slug}")
    print(f"campaign:   {brief.campaign}")
    print(f"template:   {brief.template_module}")
    print(f"columns:    {', '.join(brief.columns_required)}")
    print(f"body bytes: {len(brief.body)}")
