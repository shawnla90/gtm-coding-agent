#!/usr/bin/env python3
"""
analyze_content.py — Claude-powered signal extraction from scraped content.

For each untagged content item, produces:
  1. Topic mappings (content_topics)
  2. Competitive signals (signals) — pricing complaints, feature gaps,
     hiring moves, product launches, leadership changes, etc.

Uses Claude for competitive signal detection. Replace the taxonomy prompt
(Opus is reserved for generate_insights.py which writes user-facing briefs).

Usage:
  python3 scripts/analyze_content.py                    # analyze all unanalyzed content
  python3 scripts/analyze_content.py --source-id 7      # specific source only
  python3 scripts/analyze_content.py --platform reddit  # reddit only (goldmine for complaints)
  python3 scripts/analyze_content.py --batch-size 5     # posts per Claude call
  python3 scripts/analyze_content.py --dry-run          # preview, no writes
  python3 scripts/analyze_content.py --limit 20         # max posts this run
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from typing import Any

try:
    import anthropic
except ImportError:
    anthropic = None  # CLI backend doesn't need the SDK

from _lib import get_api_key, get_db
from _decay import decay_urgency, should_drop, urgency_hint_for_age

MODEL = "claude-haiku-4-5-20251001"
CLI_MODEL = "opus"  # claude-opus-4-6 — richer extraction when credits are blocked
DEFAULT_BATCH_SIZE = 10
CLI_TIMEOUT_SEC = 300  # per batch; Opus can be slow on 10-post batches

TOPIC_CATEGORIES = [
    "sales-intelligence",
    "gtm-engineering",
    "outbound-strategy",
    "ai-sales-tools",
    "data-enrichment",
    "revenue-ops",
    "competitor-intel",
    "content-marketing",
]

SIGNAL_TYPES = [
    "content-angle",
    "engagement-hook",
    "audience-pain-point",
    "positioning",
    "vulnerability",
    "trend",
    "product-launch",
    "content-gap",
    "opportunity",
    "partnership",
]


def build_system_prompt() -> str:
    return f"""You are a competitive intelligence analyst for Apollo.io, a sales intelligence and engagement platform competing with ZoomInfo, Clay, Lusha, and Cognism in the B2B sales tools market. Apollo's core value prop: unified sales intelligence (contact database, engagement sequences, multi-channel outreach, buying intent signals) at a price point that undercuts ZoomInfo and with GTM engineering capabilities that compete with Clay.

Your job is to read LinkedIn posts, X threads, and Reddit discussions from competitors, sales/GTM thought leaders, and named target accounts, then extract structured insights that help Apollo's GTM team identify content angles, competitive vulnerabilities, and outreach triggers.

## Topic Categories
{", ".join(TOPIC_CATEGORIES)}

## Signal Types (pick the BEST-fitting one)
content-angle — a topic or framing Apollo could use in their own content to capture attention in the sales intelligence space
engagement-hook — a post or thread generating unusually high engagement from Apollo's ICP (revenue leaders, sales ops, SDR managers) — indicates audience interest worth riding
audience-pain-point — sales professionals or revenue leaders expressing frustration with data quality, outbound tooling, sequence management, enrichment gaps, or CRM friction
positioning — a competitor shifting their narrative (e.g., Clay positioning as "GTM engineering" vs "data enrichment", ZoomInfo emphasizing intent data over contact volume)
vulnerability — a competitor weakness surfacing in public conversation (data quality complaints about ZoomInfo, pricing backlash against Lusha, feature gaps in Clay)
trend — an emerging GTM trend Apollo should be aware of (AI SDRs, waterfall enrichment, signal-based selling, multi-threading automation)
product-launch — a competitor launching a new feature, integration, or pricing tier
content-gap — a topic competitors are NOT covering that Apollo could own (e.g., multi-channel sequence best practices, SMB-focused sales intelligence)
opportunity — a concrete business opportunity: a company evaluating tools, a team scaling outbound, a leader publicly shopping for solutions
partnership — a competitor partnership, integration announcement, or ecosystem play

## Signal Urgency
act-now — fresh competitive vulnerability, public tool evaluation, or high-engagement pain point post; respond within 24h
this-week — competitor product launch, trending topic in Apollo's space, or named account activity; respond within 7 days
this-month — positioning shift, industry trend, or content gap worth planning around
backlog — worth noting, not urgent

## Post age matters
Each post is tagged `AGE: Nd` (days since publication) and a `urgency-cap` hint. Time to action is non-negotiable — an old post is old news. Apply these ceilings regardless of how juicy the signal reads:
- Posts < 14 days old: can be `act-now` / `this-week` / `this-month` / `backlog` depending on specifics
- Posts 14–30 days old: cap at `this-week`
- Posts 30–60 days old: cap at `this-month`
- Posts 60–180 days old: only `backlog` — extraction is optional, skip if the signal wouldn't matter in the backlog
- Posts 180+ days old: skip extraction entirely unless the signal is a major product launch or partnership

Never emit `act-now` for a post older than 14 days. A 3-month-old competitor vulnerability is NOT `this-week` — they've likely patched or responded by now. A 2-month-old pain point post is NOT `this-week` — the poster has moved on. Trust the AGE tag in the context more than the emotional pull of the signal text.

## Output Format
Return ONLY valid JSON (no markdown fences):
{{
  "posts": [
    {{
      "post_id": <int>,
      "topics": [{{"name": "<short topic>", "category": "<from list above>"}}],
      "signals": [
        {{
          "signal_type": "<from list>",
          "title": "<short punchy title under 80 chars — name the company/person if possible>",
          "description": "<1-2 sentences explaining WHY this matters to Apollo. Reference competitive positioning, ICP engagement patterns, or content strategy implications.>",
          "urgency": "<urgency>"
        }}
      ]
    }}
  ]
}}

Rules:
- 1-3 topics per post. Create new topic names freely but keep the category from the fixed list.
- 0-3 signals per post. Not every post has a signal. Only emit signals Apollo's marketing or sales leadership would want to see.
- Reddit pain-point threads (r/sales, r/prospecting) about data quality, outbound tooling, or CRM friction are HIGH VALUE — always extract them.
- Competitor vulnerability signals (public complaints about ZoomInfo pricing, Clay complexity, Lusha data accuracy) are the MOST ACTIONABLE signal type.
- Signal descriptions must be SPECIFIC to Apollo's competitive context (sales intelligence, engagement platform, contact data, sequence automation).
- Do NOT emit generic "thought leadership" signals. This is actionable recon, not a newsletter.
- Return ONLY JSON."""


def get_unanalyzed_content(
    conn,
    source_id: int | None = None,
    platform: str | None = None,
    limit: int | None = None,
) -> list[dict]:
    sql = """
        SELECT ci.id, ci.body, ci.engagement_likes, ci.engagement_comments,
               ci.engagement_shares, ci.source_id, ci.url, ci.platform,
               ci.published_at,
               CAST((julianday('now') - julianday(COALESCE(ci.published_at, ci.scraped_at))) AS INTEGER) AS age_days,
               s.name as source_name, s.relevance, s.tier
        FROM content_items ci
        JOIN sources s ON s.id = ci.source_id
        WHERE ci.id NOT IN (SELECT content_id FROM content_topics)
          AND ci.body IS NOT NULL AND ci.body != ''
          -- Pre-filter: skip posts older than 1 year, no signal is worth extracting from ancient content
          AND (julianday('now') - julianday(COALESCE(ci.published_at, ci.scraped_at))) < 365
    """
    params: list = []
    if source_id:
        sql += " AND ci.source_id = ?"
        params.append(source_id)
    if platform:
        sql += " AND ci.platform = ?"
        params.append(platform)
    # Newest first — fresh content gets analyzed before we burn budget on stale stuff
    sql += " ORDER BY age_days ASC, ci.engagement_likes DESC"
    if limit:
        sql += " LIMIT ?"
        params.append(limit)
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def get_or_create_topic(conn, name: str, category: str) -> int:
    row = conn.execute("SELECT id FROM topics WHERE name = ?", (name,)).fetchone()
    if row:
        return int(row["id"])
    cat = category if category in TOPIC_CATEGORIES else "competitor-intel"
    cur = conn.execute(
        "INSERT INTO topics (name, category) VALUES (?, ?)",
        (name, cat),
    )
    return int(cur.lastrowid)


def format_batch(batch: list[dict]) -> str:
    lines: list[str] = []
    for p in batch:
        body = (p["body"] or "")[:1200]
        age = p.get("age_days")
        age_str = f"{age}d" if age is not None else "?"
        lines.append(
            f"POST {p['id']} | AGE: {age_str} | source: {p['source_name']} ({p['relevance']}"
            + (f"/{p['tier']}" if p["tier"] else "")
            + f") | platform: {p['platform']} | likes: {p['engagement_likes']}"
            + (f" | urgency-cap: {urgency_hint_for_age(age or 0)}" if age is not None else "")
        )
        lines.append(body)
        lines.append("---")
    return "\n".join(lines)


def _coerce_json(text: str) -> dict[str, Any]:
    """Parse Claude's output as JSON, stripping any markdown fences or prose that
    leaked in around the object."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip().rstrip("`").strip()
    # If the model added any commentary before/after, clip to the outermost braces
    if not text.startswith("{"):
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            text = text[start : end + 1]
    return json.loads(text)


def analyze_batch(
    client: "anthropic.Anthropic",
    batch: list[dict],
    system_prompt: str,
) -> dict[str, Any] | None:
    user_content = (
        "Analyze the following posts. Return JSON with topics + signals for each.\n\n"
        + format_batch(batch)
    )
    try:
        msg = client.messages.create(
            model=MODEL,
            max_tokens=3500,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )
        text = "".join(
            b.text for b in msg.content if getattr(b, "type", "") == "text"
        ).strip()
        return _coerce_json(text)
    except json.JSONDecodeError as e:
        print(f"  ✗ JSON parse error: {e}")
        return None
    except Exception as e:
        print(f"  ✗ Claude error: {e}")
        return None


def analyze_batch_cli(
    batch: list[dict],
    system_prompt: str,
    model: str = CLI_MODEL,
) -> dict[str, Any] | None:
    """Alternate backend: shell out to `claude -p` with Opus so the work runs on
    the user's Claude Code subscription instead of the API key in .env.local.
    Falls back here when the Anthropic API reports insufficient credit."""
    user_content = (
        "Analyze the following posts. Return ONLY the JSON object (no markdown, "
        "no prose) with topics + signals for each post.\n\n"
        + format_batch(batch)
    )
    # Do NOT pass --bare — that forces ANTHROPIC_API_KEY auth and skips the
    # user's Claude Code OAuth/keychain entry (which is the whole point of this path).
    cmd = [
        "claude",
        "-p",
        "--model", model,
        "--dangerously-skip-permissions",
        "--no-session-persistence",
        "--append-system-prompt", system_prompt,
        user_content,
    ]
    text = ""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=CLI_TIMEOUT_SEC,
        )
        if result.returncode != 0:
            err = (result.stderr or result.stdout or "")[:300].strip()
            print(f"  ✗ Claude CLI exit={result.returncode}: {err}")
            return None
        text = (result.stdout or "").strip()
        if not text:
            print("  ✗ Claude CLI returned empty output")
            return None
        return _coerce_json(text)
    except subprocess.TimeoutExpired:
        print(f"  ✗ Claude CLI timeout after {CLI_TIMEOUT_SEC}s")
        return None
    except json.JSONDecodeError as e:
        print(f"  ✗ JSON parse error: {e}")
        print(f"    stdout preview: {text[:200]!r}")
        return None
    except Exception as e:
        print(f"  ✗ Claude CLI error: {e}")
        return None


def apply_result(conn, result: dict[str, Any]) -> tuple[int, int, int]:
    topics_added = 0
    signals_added = 0
    signals_dropped = 0  # dropped by should_drop (post too ancient)
    for p in result.get("posts", []):
        pid = p.get("post_id")
        if not pid:
            continue
        for t in p.get("topics", []):
            tid = get_or_create_topic(conn, t.get("name", "").strip(), t.get("category", ""))
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO content_topics (content_id, topic_id) VALUES (?, ?)",
                    (pid, tid),
                )
                topics_added += 1
            except Exception:
                pass
        # Look up source_id + post age for the signal (server-side decay cap)
        row = conn.execute(
            """SELECT source_id,
                      CAST((julianday('now') - julianday(COALESCE(published_at, scraped_at))) AS INTEGER) AS age_days
               FROM content_items WHERE id = ?""",
            (pid,),
        ).fetchone()
        source_id = row["source_id"] if row else None
        age_days = int(row["age_days"]) if row and row["age_days"] is not None else 0
        for s in p.get("signals", []):
            signal_type = s.get("signal_type")
            if signal_type not in SIGNAL_TYPES:
                continue
            # Server-side decay: Claude may still over-flag despite prompt guidance.
            # 1. Drop outright if the post is past 2× max_age (ancient news).
            if should_drop(signal_type, age_days):
                signals_dropped += 1
                continue
            # 2. Cap urgency by age + signal-type half-life.
            raw_urgency = s.get("urgency", "backlog")
            urgency = decay_urgency(signal_type, age_days, raw_urgency)
            try:
                conn.execute(
                    """INSERT INTO signals
                       (signal_type, source_id, content_id, title, description, urgency)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        signal_type,
                        source_id,
                        pid,
                        (s.get("title") or "").strip()[:240],
                        (s.get("description") or "").strip(),
                        urgency,
                    ),
                )
                signals_added += 1
            except Exception as e:
                print(f"  ✗ signal insert failed: {e}")
    conn.commit()
    return topics_added, signals_added, signals_dropped


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-id", type=int)
    parser.add_argument("--platform", choices=["linkedin", "x", "reddit"])
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Route batches through `claude -p --model opus` subprocess instead of "
             "the Anthropic SDK. Use when .env.local's ANTHROPIC_API_KEY is out of credit "
             "but your Claude Code subscription is funded.",
    )
    args = parser.parse_args()

    conn = get_db()
    posts = get_unanalyzed_content(
        conn,
        source_id=args.source_id,
        platform=args.platform,
        limit=args.limit,
    )

    if not posts:
        print("No unanalyzed content found.")
        return 0

    backend = "claude CLI (Opus)" if args.cli else f"Anthropic SDK ({MODEL})"
    print(f"Found {len(posts)} posts to analyze (batch size {args.batch_size}, backend: {backend}).")
    if args.dry_run:
        for p in posts[:10]:
            print(f"  [{p['id']:4}] {p['source_name']} — {(p['body'] or '')[:80]}")
        print("\n(dry-run — no Claude calls made)")
        return 0

    system_prompt = build_system_prompt()
    client = None
    if not args.cli:
        if anthropic is None:
            sys.exit("Missing anthropic SDK. Install: pip install anthropic  (or use --cli)")
        client = anthropic.Anthropic(api_key=get_api_key())

    total_topics = 0
    total_signals = 0
    total_dropped = 0
    for i in range(0, len(posts), args.batch_size):
        batch = posts[i : i + args.batch_size]
        print(f"\n── batch {i // args.batch_size + 1} ({len(batch)} posts) ──")
        if args.cli:
            result = analyze_batch_cli(batch, system_prompt)
        else:
            result = analyze_batch(client, batch, system_prompt)
        if not result:
            continue
        t, s, d = apply_result(conn, result)
        total_topics += t
        total_signals += s
        total_dropped += d
        drop_note = f", {d} dropped (ancient)" if d else ""
        print(f"  ✓ {t} topic mappings, {s} signals{drop_note}")

    drop_summary = f" ({total_dropped} dropped as ancient)" if total_dropped else ""
    print(f"\nDone. {total_topics} topic mappings, {total_signals} signals added{drop_summary}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
