#!/usr/bin/env python3
"""
generate_lead_reasoning.py — AI-generated "why this lead matters" per signal.

For each signal that has ICP 3+ engagers with comment text, generates a concise
reasoning brief explaining what the engagement reveals about intent and why
the person is a relevant lead.

Uses Claude Haiku for cost efficiency. Batches 5-8 leads per call.

Usage:
  python3 scripts/generate_lead_reasoning.py              # process top 50 signals
  python3 scripts/generate_lead_reasoning.py --limit 10   # cap signal count
  python3 scripts/generate_lead_reasoning.py --dry-run    # preview, no writes
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

try:
    import anthropic
except ImportError:
    sys.exit("Missing anthropic SDK. Install: pip install anthropic")

from _lib import get_api_key, get_db

MODEL = "claude-haiku-4-5-20251001"
BATCH_SIZE = 6  # leads per Claude call
MAX_PAIRS = 1000  # total lead-signal pairs cap


def get_signals_with_leads(conn, limit: int = 50) -> list[dict]:
    """Get top signals that have ICP 3+ engagers with comments.

    Returns signals ordered by urgency then lead count, with their
    associated high-ICP leads pre-loaded.
    """
    # First, find signals with qualified leads
    signals = conn.execute("""
        SELECT
            sig.id AS signal_id,
            sig.title AS signal_title,
            sig.description AS signal_description,
            sig.signal_type,
            sig.urgency,
            ci.body AS post_body,
            ci.url AS post_url,
            s.name AS source_name,
            COUNT(DISTINCT e.id) AS lead_count
        FROM signals sig
        JOIN content_items ci ON ci.id = sig.content_id
        JOIN sources s ON s.id = sig.source_id
        JOIN engagements eng ON eng.content_item_id = ci.id
        JOIN engagers e ON e.id = eng.engager_id
        JOIN icp_scores icp ON icp.engager_id = e.id
        WHERE sig.status IN ('new', 'acknowledged')
          AND icp.overall_stars >= 3
          AND eng.comment_text IS NOT NULL
          AND eng.comment_text != ''
          AND sig.id NOT IN (SELECT DISTINCT signal_id FROM lead_reasoning)
        GROUP BY sig.id
        HAVING lead_count > 0
        ORDER BY
            CASE sig.urgency
                WHEN 'act-now' THEN 1
                WHEN 'this-week' THEN 2
                WHEN 'this-month' THEN 3
                ELSE 4
            END,
            lead_count DESC
        LIMIT ?
    """, (limit,)).fetchall()

    result = []
    for sig in signals:
        sig_dict = dict(sig)
        # Load leads for this signal
        leads = conn.execute("""
            SELECT
                e.id AS engager_id,
                e.name,
                e.title,
                e.company,
                e.parsed_company,
                icp.overall_stars,
                eng.comment_text
            FROM engagements eng
            JOIN engagers e ON e.id = eng.engager_id
            JOIN icp_scores icp ON icp.engager_id = e.id
            JOIN content_items ci ON ci.id = eng.content_item_id
            WHERE ci.id = (SELECT content_id FROM signals WHERE id = ?)
              AND icp.overall_stars >= 3
              AND eng.comment_text IS NOT NULL
              AND eng.comment_text != ''
            ORDER BY icp.overall_stars DESC
        """, (sig_dict["signal_id"],)).fetchall()
        sig_dict["leads"] = [dict(l) for l in leads]
        result.append(sig_dict)

    return result


def build_batch_prompt(signal: dict, leads: list[dict]) -> str:
    post_excerpt = (signal.get("post_body") or "")[:400]
    lead_lines = []
    for i, lead in enumerate(leads, 1):
        company = lead.get("parsed_company") or lead.get("company") or "Unknown"
        comment = (lead.get("comment_text") or "")[:300]
        lead_lines.append(
            f"{i}. [{lead['engager_id']}] {lead.get('name', 'Unknown')} "
            f"— {lead.get('title', 'Unknown title')} @ {company} "
            f"(ICP {lead.get('overall_stars', '?')}★)\n"
            f"   Comment: \"{comment}\""
        )

    return f"""Signal: {signal['signal_title']}
Type: {signal['signal_type']}
Description: {signal.get('signal_description') or '(none)'}
Source: {signal.get('source_name', 'Unknown')}

Original post excerpt:
{post_excerpt or '(no post body)'}

---

Leads who engaged with this content:

{chr(10).join(lead_lines)}

---

For each lead, generate a JSON array. Each entry must have:
- "engager_id": the ID in brackets above
- "reasoning": 1-2 sentences explaining what their engagement reveals about their intent and why they're a relevant lead for Apollo.io

Return ONLY valid JSON (no markdown fences):
[{{"engager_id": 123, "reasoning": "..."}}]"""


SYSTEM_PROMPT = """You generate concise lead intelligence for Apollo.io's sales team. Given a competitive signal and a person's engagement with the underlying content, explain in 1-2 sentences what their engagement reveals about their intent and why they're a relevant lead.

Be specific about:
- What the comment text reveals about their pain points, tool evaluation, or buying intent
- How their role and company context makes them relevant to Apollo.io
- Any competitive displacement opportunities (mentions of competitor frustrations)

Do NOT be generic. "This person is a decision maker" is useless. "Their comment about ZoomInfo's pricing suggests they're actively evaluating alternatives, and as VP Sales at a 200-person SaaS company, they match Apollo's mid-market sweet spot" is useful.

Return ONLY valid JSON."""


def generate_reasoning_batch(
    client: anthropic.Anthropic,
    signal: dict,
    leads: list[dict],
) -> list[dict] | None:
    user_content = build_batch_prompt(signal, leads)
    try:
        msg = client.messages.create(
            model=MODEL,
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )
        text = "".join(
            b.text for b in msg.content if getattr(b, "type", "") == "text"
        ).strip()
        # Strip markdown fences if added
        if text.startswith("```"):
            text = text.split("```", 2)[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip().rstrip("`").strip()
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"  ✗ JSON parse error: {e}")
        return None
    except Exception as e:
        print(f"  ✗ Claude error: {e}")
        return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=50,
                        help="Max signals to process (default 50)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    conn = get_db()
    signals = get_signals_with_leads(conn, limit=args.limit)

    if not signals:
        print("No signals with ICP 3+ commented leads found.")
        return 0

    total_leads = sum(len(s["leads"]) for s in signals)
    print(f"Found {len(signals)} signals with {total_leads} qualified leads.")

    if args.dry_run:
        for s in signals[:10]:
            print(f"  signal {s['signal_id']:4} ({s['urgency']:10}) — {len(s['leads'])} leads — {s['signal_title'][:70]}")
        print("\n(dry-run — no Claude calls made)")
        return 0

    client = anthropic.Anthropic(api_key=get_api_key())

    total_inserted = 0
    total_pairs_processed = 0

    for i, signal in enumerate(signals):
        leads = signal["leads"]
        if total_pairs_processed >= MAX_PAIRS:
            print(f"\n  Reached {MAX_PAIRS} pair cap. Stopping.")
            break

        print(f"\n── [{i + 1}/{len(signals)}] signal {signal['signal_id']} — {len(leads)} leads — {signal['signal_title'][:60]}")

        # Process leads in batches
        for batch_start in range(0, len(leads), BATCH_SIZE):
            batch = leads[batch_start:batch_start + BATCH_SIZE]
            if total_pairs_processed + len(batch) > MAX_PAIRS:
                batch = batch[:MAX_PAIRS - total_pairs_processed]

            results = generate_reasoning_batch(client, signal, batch)
            if not results:
                continue

            batch_inserted = 0
            for entry in results:
                engager_id = entry.get("engager_id")
                reasoning = entry.get("reasoning", "").strip()
                if not engager_id or not reasoning:
                    continue

                # Find the comment text for this engager
                comment_text = None
                for lead in batch:
                    if lead["engager_id"] == engager_id:
                        comment_text = lead.get("comment_text")
                        break

                try:
                    conn.execute(
                        """INSERT OR REPLACE INTO lead_reasoning
                           (signal_id, engager_id, comment_text, reasoning)
                           VALUES (?, ?, ?, ?)""",
                        (signal["signal_id"], engager_id, comment_text, reasoning),
                    )
                    batch_inserted += 1
                except Exception as e:
                    print(f"    ✗ insert failed for engager {engager_id}: {e}")

            conn.commit()
            total_inserted += batch_inserted
            total_pairs_processed += len(batch)
            print(f"    ✓ batch {batch_start // BATCH_SIZE + 1}: {batch_inserted}/{len(batch)} reasoning entries")

    print(f"\nDone. {total_inserted} lead reasoning entries generated across {len(signals)} signals.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
