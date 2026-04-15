#!/usr/bin/env python3
"""
generate_insights.py — Turn raw signals into SDR-ready outreach briefs.

For each unprocessed signal, Claude Opus generates a brief an SDR can forward
or copy-paste as a LinkedIn/email opener to a named account. Each
insight includes:
  - A 1-line headline (why this matters right now)
  - 2-3 sentence context specific to the target operator
  - A concrete outreach angle (NaaS $0 CapEx vs Managed WiFi)
  - A copy-paste opener draft (3-4 sentences, conversational, Shawn voice)
  - A priority score (1-10)

Target accounts (companies whose employee engagement you track) are pulled from sources.relevance='named-account'
so adding new named-account sources automatically extends the targeting set.

Usage:
  python3 scripts/generate_insights.py                  # process all new signals
  python3 scripts/generate_insights.py --limit 20       # cap for cost
  python3 scripts/generate_insights.py --signal-id 42   # single signal
  python3 scripts/generate_insights.py --dry-run        # preview, no writes
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
from _decay import DECAY_RULES, DEFAULT_RULE, format_age, should_drop

MODEL = "claude-opus-4-6"
CLI_MODEL = "opus"
CLI_TIMEOUT_SEC = 180  # per signal — Opus typically responds in 20-60s


def _coerce_json(text: str) -> dict[str, Any]:
    """Parse Claude's output as JSON, tolerating markdown fences and stray prose."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip().rstrip("`").strip()
    if not text.startswith("{"):
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            text = text[start : end + 1]
    return json.loads(text)


def load_target_accounts(conn) -> list[dict]:
    """Pull target accounts from sources.relevance='named-account'.
    Falls back to empty list if no named accounts are seeded yet."""
    rows = conn.execute(
        """SELECT id, name, title, company, country, verticals, notes
           FROM sources
           WHERE relevance = 'named-account' AND status = 'active'
           ORDER BY name"""
    ).fetchall()
    return [dict(r) for r in rows]


def build_system_prompt(target_accounts: list[dict]) -> str:
    if target_accounts:
        targets = "\n".join(
            f"- {t['name']} — {t['title'] or 'contact'} at {t['company'] or t['name']}"
            + (f" ({t['country']})" if t.get('country') else "")
            + (f". Mix: {t['verticals']}" if t.get('verticals') else "")
            + (f". Notes: {t['notes']}" if t.get('notes') else "")
            for t in target_accounts
        )
    else:
        targets = "(No named accounts seeded. Target the revenue leader persona most relevant to the signal — VP Sales, CRO, Head of RevOps, or SDR Manager at a B2B SaaS company.)"

    return f"""You are an SDR enablement analyst for Apollo.io, a sales intelligence and engagement platform. You turn competitive intelligence signals into concrete, ready-to-send outreach briefs that Apollo's sales team can use to engage revenue leaders at B2B SaaS companies.

## Apollo positioning
- **Product:** Unified sales intelligence platform — contact database (275M+ contacts), engagement sequences, multi-channel outreach (email, phone, LinkedIn), buying intent signals, and CRM enrichment.
- **ICP:** Revenue leaders (VPs of Sales, CROs, Directors of Revenue Ops, SDR managers) at B2B SaaS companies with 50-1000 employees scaling outbound.
- **Key differentiators vs competitors:**
  - vs ZoomInfo: Better value (fraction of the cost), all-in-one platform (no need for separate engagement tool), stronger SMB/mid-market fit
  - vs Clay: Easier to use (no-code vs Clay's technical GTM engineering approach), built-in engagement sequences, broader contact database
  - vs Lusha/Cognism: Deeper platform (sequences + intent + enrichment in one), stronger US data coverage
  - vs Outreach/Salesloft: Apollo includes the data layer (contact intelligence) that pure engagement tools lack
- **Core message:** One platform for prospecting, enrichment, engagement, and intelligence — stop stitching together 4-5 tools.

## Target accounts (named-account contacts and companies we're tracking)
{targets}

## Your task
Given a competitive intel signal (e.g., "ZoomInfo just raised prices again" or a Reddit thread about SDRs frustrated with data quality), produce an insight brief. The brief should:

1. Pick the ONE target account most relevant to the signal. Match by: company fit (if the signal names their company), tool stack (if they use a competitor), or role fit (if the signal addresses their persona).
2. Explain in 2-3 sentences why this specific signal matters for THAT specific account or persona.
3. Propose a concrete outreach angle. Frame around Apollo's specific value prop that addresses the signal (e.g., if the signal is about ZoomInfo pricing, lead with Apollo's cost advantage; if about data quality, lead with Apollo's enrichment waterfall).
4. Draft a 3-4 sentence opener the SDR can copy-paste into LinkedIn DM or email. Opener must:
   - Reference the triggering signal naturally and SPECIFICALLY (name the competitor, the pain point, the Reddit thread, whatever triggered it)
   - Connect the signal to the target's situation with one bridge sentence
   - Deliver Apollo's angle in one concrete sentence — not a pitch deck, just the hook
   - End with a low-pressure question (NOT "quick 15 minutes?", NOT "are you the right person?")

## Writing voice (critical)
- Conversational. Punchy. Short sentences mixed with one longer one.
- Never use: "I hope this finds you well", "circling back", "quick question", "just wanted to reach out", "at the end of the day", "in today's fast-paced world", "synergies", "leverage", "align", "touch base", "move the needle"
- Never start with "Hi [Name]," — write the BODY that comes after the greeting
- Never pitch more than one thing per opener
- Never use em-dashes as sentence connectors — parens or commas instead

## Priority scoring (1-10)
- 9-10: **Fresh** (< 14d) competitor vulnerability going viral (ZoomInfo pricing complaints, Clay complexity backlash) or a named account publicly evaluating tools. Act today.
- 7-8: Actionable (< 30d) pain-point post from a revenue leader in our ICP, competitor product launch we can counter-position against, or strong content angle.
- 4-6: Industry trend relevant to Apollo's positioning, content gap worth filling.
- 1-3: Background noise, or a signal tied to a post older than 30 days. A great signal on an old post is still an old signal.

## Age is part of priority
The post age is given explicitly as "Post age: N days ago". Incorporate it:
- Posts under 14 days can earn 9-10 priority if the signal is strong
- Posts 14-30 days old cap at priority 7
- Posts 30-60 days old cap at priority 5
- Posts 60+ days old cap at priority 3 — the window has likely closed
- The opener must acknowledge the date honestly, never spin an old signal as breaking news

## Output format
Return ONLY valid JSON (no markdown fences):
{{
  "target_account": "<contact name or company from the target accounts list>",
  "vertical": "<sales-intelligence | outbound | revenue-ops | data-enrichment | engagement>",
  "headline": "<one-line why-this-matters, under 100 chars>",
  "why_it_matters": "<2-3 sentences of context SPECIFIC to the chosen target>",
  "outreach_angle": "<1-2 sentences: specific Apollo value prop framing that addresses this signal>",
  "opener_draft": "<3-4 sentences, conversational, ready to copy-paste>",
  "priority": <1-10>
}}

Rules:
- If no target account is a perfect fit, pick the closest by persona + company fit. Never return null.
- Competitor vulnerability signals (public complaints, pricing backlash, churn stories) are HIGHEST priority.
- NEVER fabricate signals or details. Only use what's in the triggering signal.
- Return ONLY JSON."""


def get_unprocessed_signals(
    conn,
    signal_id: int | None = None,
    limit: int | None = None,
) -> list[dict]:
    """Pull signals ready for insight generation.

    Joins content_items to compute post age so we can filter stale signals and
    inject the age into Claude's context. The ORDER BY puts fresh signals first
    so the budget gets spent on the most actionable work.
    """
    sql = """
        SELECT sig.id, sig.signal_type, sig.title, sig.description, sig.urgency,
               sig.source_id, sig.content_id,
               s.name as source_name, s.relevance as source_relevance,
               s.tier as source_tier, s.verticals as source_verticals,
               ci.body as post_body, ci.url as post_url, ci.published_at as post_published_at,
               CAST((julianday('now') - julianday(COALESCE(ci.published_at, ci.scraped_at))) AS INTEGER) AS post_age_days
        FROM signals sig
        JOIN sources s ON s.id = sig.source_id
        LEFT JOIN content_items ci ON ci.id = sig.content_id
        WHERE sig.id NOT IN (SELECT signal_id FROM insights WHERE signal_id IS NOT NULL)
          AND sig.status IN ('new', 'acknowledged')
    """
    params: list = []
    if signal_id:
        sql += " AND sig.id = ?"
        params.append(signal_id)
    sql += """ ORDER BY
        CASE sig.urgency WHEN 'act-now' THEN 1 WHEN 'this-week' THEN 2 WHEN 'this-month' THEN 3 ELSE 4 END,
        post_age_days ASC,
        sig.created_at DESC"""
    if limit:
        sql += " LIMIT ?"
        params.append(limit)
    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]

    # Post-filter: drop signals whose post is past the signal-type max_age.
    # This is an age-aware generation guard — stale signals get cascade-deleted
    # by decay_signals.py separately, but if the user hasn't run that yet we still
    # don't want to burn Opus budget generating briefs for dead content.
    fresh: list[dict] = []
    stale_dropped = 0
    for r in rows:
        age = r.get("post_age_days")
        if age is None:
            # Unknown age — let it through; the brief can note the uncertainty
            fresh.append(r)
            continue
        rule = DECAY_RULES.get(r["signal_type"], DEFAULT_RULE)
        if age >= rule["max_age"]:
            stale_dropped += 1
            continue
        fresh.append(r)
    if stale_dropped:
        print(f"  (age filter dropped {stale_dropped} stale signals before Opus calls)")
    return fresh


def build_user_content(signal: dict) -> str:
    post_excerpt = (signal.get("post_body") or "")[:600]
    age_days = signal.get("post_age_days")
    post_date = signal.get("post_published_at") or "(unknown date)"
    if age_days is not None:
        age_line = f"Post age: {age_days} days ago ({format_age(age_days)}) — published {post_date}"
    else:
        age_line = f"Post age: unknown — published {post_date}"

    return f"""Signal to analyze:

Type: {signal['signal_type']}
Urgency: {signal['urgency']}
Title: {signal['title']}
Description: {signal['description']}

Source: {signal['source_name']} ({signal['source_relevance']}{f", tier={signal['source_tier']}" if signal.get('source_tier') else ""})
Source verticals: {signal.get('source_verticals') or '—'}

{age_line}

Original post excerpt:
{post_excerpt or '(no post body captured)'}

Generate the SDR outreach brief now. The opener MUST reference the post date naturally (e.g., "saw your post from last week about..." or "the [Month] announcement about..."). If the post is more than 30 days old, do NOT pretend it's fresh — frame the signal as follow-up rather than breaking news. Return ONLY JSON."""


def generate_insight(
    client: "anthropic.Anthropic",
    signal: dict,
    system_prompt: str,
) -> dict[str, Any] | None:
    user_content = build_user_content(signal)
    try:
        msg = client.messages.create(
            model=MODEL,
            max_tokens=1200,
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


def generate_insight_cli(
    signal: dict,
    system_prompt: str,
    model: str = CLI_MODEL,
) -> dict[str, Any] | None:
    """Subprocess-backed generator. Invokes `claude -p` with Opus so the work
    runs on the Claude Code subscription instead of the API key in .env.local."""
    user_content = build_user_content(signal)
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


def insert_insight(conn, signal: dict, brief: dict) -> int:
    """Insert the brief, applying a server-side age-aware priority decay.

    Returns the final priority actually written (after age decay) so the caller
    can print it.
    """
    raw_priority = int(brief.get("priority") or 5)
    age_days = signal.get("post_age_days")
    if age_days is not None:
        # Floor: -1 priority tier per two weeks of age, clamped [1, 10]
        decayed = raw_priority - (int(age_days) // 14)
        # Hard age-based ceilings per the system prompt (double-enforced server-side)
        if age_days >= 60:
            decayed = min(decayed, 3)
        elif age_days >= 30:
            decayed = min(decayed, 5)
        elif age_days >= 14:
            decayed = min(decayed, 7)
        final_priority = max(1, min(10, decayed))
    else:
        final_priority = max(1, min(10, raw_priority))

    conn.execute(
        """INSERT INTO insights
           (signal_id, source_id, target_account, vertical, headline,
            why_it_matters, outreach_angle, opener_draft, priority)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            signal["id"],
            signal["source_id"],
            (brief.get("target_account") or "").strip() or None,
            (brief.get("vertical") or "").strip() or None,
            (brief.get("headline") or "").strip()[:240],
            (brief.get("why_it_matters") or "").strip(),
            (brief.get("outreach_angle") or "").strip(),
            (brief.get("opener_draft") or "").strip(),
            final_priority,
        ),
    )
    conn.commit()
    return final_priority


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--signal-id", type=int)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Route each signal through `claude -p --model opus` subprocess instead of "
             "the Anthropic SDK. Use when .env.local's ANTHROPIC_API_KEY is out of credit.",
    )
    args = parser.parse_args()

    conn = get_db()
    signals = get_unprocessed_signals(
        conn, signal_id=args.signal_id, limit=args.limit
    )

    if not signals:
        print("No unprocessed signals.")
        return 0

    backend = "claude CLI (Opus)" if args.cli else f"Anthropic SDK ({MODEL})"
    print(f"Found {len(signals)} signals to process (backend: {backend}).")
    if args.dry_run:
        for s in signals[:10]:
            print(f"  [{s['id']:4}] {s['urgency']:10} {s['signal_type']:15} {s['title'][:80]}")
        print("\n(dry-run — no Claude calls made)")
        return 0

    client = None
    if not args.cli:
        if anthropic is None:
            sys.exit("Missing anthropic SDK. Install: pip install anthropic  (or use --cli)")
        client = anthropic.Anthropic(api_key=get_api_key())
    target_accounts = load_target_accounts(conn)
    print(f"Loaded {len(target_accounts)} named target accounts.")
    system_prompt = build_system_prompt(target_accounts)

    added = 0
    for i, signal in enumerate(signals):
        age = signal.get("post_age_days")
        age_tag = f" [{format_age(age)} old]" if age is not None else ""
        print(f"\n── [{i + 1}/{len(signals)}] signal {signal['id']}{age_tag} — {signal['title'][:70]}")
        if args.cli:
            brief = generate_insight_cli(signal, system_prompt)
        else:
            brief = generate_insight(client, signal, system_prompt)
        if not brief:
            continue
        try:
            final_pri = insert_insight(conn, signal, brief)
            added += 1
            target = brief.get("target_account") or "—"
            raw_pri = int(brief.get("priority") or 0)
            decay_note = f" (Claude said {raw_pri}, aged to {final_pri})" if final_pri != raw_pri else ""
            print(f"  ✓ pri={final_pri}{decay_note} target={target} — {brief.get('headline', '')[:70]}")
        except Exception as e:
            print(f"  ✗ insert failed: {e}")

    print(f"\nDone. {added} insights generated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
