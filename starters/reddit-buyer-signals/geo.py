#!/usr/bin/env python3
"""geo.py — the GEO terms a client should own, with current retrieval visibility.

"GEO term" = a buyer question a RevOps/GTM leader would type or ask an AI, that the client can answer
authoritatively. The terms come from the real buyer language the account surfaced (generated into
clean queries upstream, or derived from content_topics here as a fallback). Each term is then checked
for CURRENT retrieval visibility with a HARD-CAPPED Exa pass (does the client show up in an independent
search result set for this question?), so the output is both the plan and a leading indicator. It does
not prove an AI answer named or cited the client.

  python3 geo.py --gen data/geo_terms_gen.json --brand Acme PM --db reddit-buyer-signals/data/signals.db --out data/geo_terms.json

Read-only except the --out file. Exa is capped by lib/exa_client.MAX_QUERIES; absent key degrades to
terms without a visibility score.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from lib.exa_client import retrieval_visibility, get_key  # type: ignore


def load_generated(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, list) else data.get("terms", [])
    except Exception:
        return []


def load_from_db(db: Path) -> list[dict]:
    """Fallback: use the mined content_topics as term candidates."""
    if not db.exists():
        return []
    con = sqlite3.connect(str(db))
    rows = con.execute(
        "SELECT content_angle, intent, mentions, evidence FROM content_topics "
        "ORDER BY mentions DESC, engagement DESC").fetchall()
    con.close()
    return [{"term": (r[0] or "").lower(), "intent": r[1] or "mid",
             "evidence": r[3] or "", "why": f"{r[2]} buyer threads touch this"}
            for r in rows if r[0]]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen", default="data/geo_terms_gen.json")
    ap.add_argument("--brand", required=True)
    ap.add_argument("--db", default="reddit-buyer-signals/data/signals.db")
    ap.add_argument("--out", default="data/geo_terms.json")
    ap.add_argument("--check", type=int, default=8, help="how many top terms to visibility-check (capped)")
    args = ap.parse_args()

    terms = load_generated(Path(args.gen)) or load_from_db(Path(args.db))
    if not terms:
        print("no GEO terms available (no generated file, no content_topics)")
        return 0

    # rank: high intent first, then by whatever order upstream gave
    order = {"high": 0, "mid": 1, "low": 2}
    terms.sort(key=lambda t: order.get((t.get("intent") or "mid").lower(), 1))

    # capped retrieval check on the top terms only
    check_terms = [t["term"] for t in terms[: args.check] if t.get("term")]
    vis = retrieval_visibility(args.brand, check_terms) if get_key() else {"available": False}
    appears_by_q = {d["query"]: d["appears"] for d in vis.get("queries", [])}

    out = []
    for t in terms:
        term = t.get("term", "")
        checked = term in appears_by_q
        out.append({
            "term": term,
            "intent": t.get("intent", "mid"),
            "why_you_own_it": t.get("why", ""),
            "buyer_evidence": (t.get("evidence") or "")[:180],
            "currently_retrieved_by_exa": ("yes" if appears_by_q[term] else "no") if checked else "not checked",
        })

    result = {
        "brand": args.brand,
        "retrieval_visibility_score": vis.get("score") if vis.get("available") else None,
        "retrieval_checked": vis.get("checked", 0),
        "note": ("share of checked buyer questions where the brand surfaces in Exa search results; "
                 "this is not an observed AI answer or citation"
                 if vis.get("available") else "Exa retrieval unavailable; terms listed without a live score"),
        "terms": out,
    }
    Path(args.out).write_text(json.dumps(result, indent=2, ensure_ascii=False))
    retrieved = sum(1 for t in out if t["currently_retrieved_by_exa"] == "yes")
    print(f"GEO terms: {len(out)} · retrieval-checked {vis.get('checked', 0)} · "
          f"brand retrieved {retrieved} · score {result['retrieval_visibility_score']} -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
