#!/usr/bin/env python3
"""content.py - scaffold and anti-slop-check a client content pack from a real buyer question.

The coding agent writes the words (in the client's voice); this scaffolds the pack so it has
everything it needs, and checks the result. Two subcommands:

  # build the skeleton + a generation brief from one opportunity + the client voice profile
  python3 content.py scaffold --client "Acme PM" --voice ../voice/core-voice.md \
      --topic "how to keep one source of truth across HubSpot and Salesforce" --out content/pack-01

  # scan a finished draft for slop / banned words before it ships
  python3 content.py check content/pack-01/linkedin.md

A pack is three drafts from one buyer question: a LinkedIn post, a Reddit post (draft only), and a
long-tail blog with a TL;DR answer block and a `## Frequently Asked Questions` section (### questions)
that emits FAQPage schema. Client-scoped: the manifest disables dispatch, because client-voice content
stays in the client package and never goes to a public content channel.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# best-effort import of the house anti-slop scanner; fall back to a small built-in list if absent
_DISPATCH = Path.home() / "content" / "dispatch"
try:
    sys.path.insert(0, str(_DISPATCH))
    from formatters import common as _common  # type: ignore
except Exception:  # noqa: BLE001
    _common = None

# explicit banned-word list (the house scanner catches structural slop, not these single-word bans)
_BANNED = [
    "most", "notice", "noticed", "leverage", "unlock", "game-changer", "game changer",
    "seamless", "delve", "in today's fast-paced", "supercharge", "revolutionize", "elevate",
    "thoughts?", "dm me", "follow for more", "let that sink in",
]


def strip_frontmatter(text: str) -> str:
    """Drop a leading YAML frontmatter block. It is metadata (key: value), not prose to scan."""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            nl = text.find("\n", end + 1)
            return text[nl + 1:] if nl != -1 else ""
    return text


def slop_flags(text: str) -> list[str]:
    """Merge the house structural scanner (when present) with the explicit single-word bans."""
    flags: list[str] = []
    if _common is not None and hasattr(_common, "anti_slop_flags"):
        try:
            for item in _common.anti_slop_flags(text):
                flags.append(f"{item[0]}: {item[1]}" if isinstance(item, tuple) else str(item))
        except Exception:  # noqa: BLE001
            pass
    low = text.lower()
    flags += [f"banned word: {w}" for w in _BANNED if re.search(r"(?<![a-z])" + re.escape(w), low)]
    if "—" in text:  # em-dash
        flags.append("em-dash present (use commas, periods, colons)")
    return flags


def _stub(platform: str, topic: str, client: str) -> str:
    guide = {
        "linkedin": ("A LinkedIn post in the client's voice. The hook delivers immediately: the next "
                     "line pays it off, no bait. Real list bullets are fine, fake listicles are not. "
                     "No CTA-slop ending."),
        "reddit": ("A value-first Reddit comment/post, draft only, never auto-posted. Answer the "
                   "actual question like a practitioner. No pitch, no link-drop."),
        "blog": ("A long-tail blog. Buyer-query H1, a TL;DR answer block up top, real best-practices, "
                 "and a `## Frequently Asked Questions` section with `### question` headings so it "
                 "emits FAQPage schema. HowTo-shaped steps where it is a procedure."),
    }[platform]
    fm = f"---\nplatform: {platform}\nclient: {client}\ntopic: {topic}\n---\n\n"
    return fm + f"<!-- WRITE HERE. {guide} Source buyer question: {topic!r}. -->\n"


def scaffold(args) -> int:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", args.client.lower()).strip("-") + "-reddit-content"

    (out / "linkedin.md").write_text(_stub("linkedin", args.topic, args.client))
    (out / "reddit.md").write_text(_stub("reddit", args.topic, args.client))
    (out / "blog.md").write_text(_stub("blog", args.topic, args.client))

    voice = Path(args.voice)
    voice_txt = voice.read_text() if voice.exists() else "(voice profile not found; write plainly)"
    (out / "BRIEF.md").write_text(
        f"# Generation brief: {args.client}\n\n"
        f"**Buyer question (the seed):** {args.topic}\n\n"
        f"Write all three drafts from this one question, in the voice below. Anti-slop enforced: "
        f"no em-dashes, no banned words, no define-by-negation, no CTA-slop. Every claim traces to "
        f"something real. Reddit is draft only.\n\n"
        f"## Voice profile\n\n{voice_txt}\n")

    manifest = {
        "pack_slug": slug,
        "summary": (f"CLIENT-SCOPED pack for {args.client}, drafted in {args.client}'s voice from a "
                    f"real Reddit buyer question. Stays in the client package. Do NOT dispatch to a "
                    f"public content channel; client-voice content never goes to the public content OS."),
        "client": args.client,
        "voice_profile": args.voice,
        "dispatch": "disabled_client_scoped",
        "items": [
            {"channel": "linkedin-content", "platform": "linkedin", "subtype": "feed",
             "body_path": "linkedin.md", "strip_md": True},
            {"channel": "reddit-posts", "platform": "reddit", "subtype": "draft",
             "body_path": "reddit.md", "strip_md": True},
            {"channel": "blog-newsletters", "platform": "blog", "subtype": "long-tail",
             "body_path": "blog.md", "strip_md": False},
        ],
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"scaffolded content pack -> {out}/ (BRIEF.md + linkedin/reddit/blog.md + manifest.json)")
    print("  next: the agent writes each draft from BRIEF.md, then `content.py check <file>`")
    return 0


def check(args) -> int:
    target = Path(args.path)
    files = sorted(target.rglob("*.md")) if target.is_dir() else [target]
    total = 0
    for f in files:
        flags = slop_flags(strip_frontmatter(f.read_text()))
        total += len(flags)
        mark = "ok" if not flags else f"{len(flags)} flag(s)"
        print(f"{f}: {mark}")
        for fl in flags:
            print(f"   - {fl}")
    print(f"\n{'PASS' if total == 0 else 'FAIL'}: {total} flag(s) across {len(files)} file(s)")
    return 0 if total == 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sc = sub.add_parser("scaffold")
    sc.add_argument("--client", required=True)
    sc.add_argument("--voice", default="../voice/core-voice.md")
    sc.add_argument("--topic", required=True, help="the real buyer question the pack answers")
    sc.add_argument("--out", default="content/pack-01")
    sc.set_defaults(fn=scaffold)
    ck = sub.add_parser("check")
    ck.add_argument("path", help="a .md file or a pack directory")
    ck.set_defaults(fn=check)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
