#!/usr/bin/env python3
"""digest.py — the daily Slack digest of a client's Reddit opportunities.

Original daily digest pattern by Lucas. Ported to the ClearboxGTM engine.

The operated-service delivery: each day the account's engage threads (with the drafted value-first
reply), new leads, and competitor mentions land in the client's Slack, not only in a sheet. Format:
a header line, then one block per opportunity, ordered by priority, capped. v1 is a text digest with
permalinks; interactive buttons need a bot token and are a later step.

  python3 digest.py --ops data/ops_classified.json --angles data/engage_angles.json \
      --client Acme PM --out data/slack_digest.txt            # render only
  python3 digest.py ... --post --webhook-secret SLACK_WEBHOOK_YOURCLIENT   # render + post live

Posting reuses the incoming-webhook pattern (slack_post: POST {"text": ...}); the webhook URL is read
from the env var of that name (or a local secrets store as fallback). Never posts without --post.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SECRETS_DB = os.environ.get("SECRETS_DB", "")  # optional: sqlite file with a secrets(key,value) table
PRIO_RANK = {"high": 0, "med": 1, "low": 2, "": 3}


def get_secret(key: str) -> str | None:
    v = os.environ.get(key)
    if v:
        return v.strip()
    if SECRETS_DB:
        try:
            with sqlite3.connect(SECRETS_DB, timeout=10) as c:
                row = c.execute("SELECT value FROM secrets WHERE key=?", (key,)).fetchone()
                return row[0] if row else None
        except sqlite3.Error:
            return None
    return None


def slack_post(webhook_url: str, text: str) -> bool:
    body = json.dumps({"text": text}).encode()
    req = urllib.request.Request(webhook_url, data=body, method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.read().decode().strip() in ("ok", "")
    except Exception as e:
        print(f"  slack post failed: {e}")
        return False


def age(posted_at) -> str:
    try:
        dt = datetime.fromisoformat(str(posted_at).replace("Z", "+00:00"))
        days = (datetime.now(timezone.utc) - dt).days
        return "today" if days <= 0 else ("1d" if days == 1 else f"{days}d")
    except Exception:
        return ""


def build(ops: list[dict], angles: dict, client: str, date_str: str, limit: int) -> str:
    engage = [o for o in ops if o.get("lane") in ("engage_now", "engage_selective")]
    for o in engage:
        o["_prio"] = angles.get(o.get("op_id"), {}).get("priority", "")
    engage.sort(key=lambda o: (PRIO_RANK.get(o["_prio"], 3),
                               0 if o["lane"] == "engage_now" else 1))
    leads = [o for o in ops if o.get("lane") == "lead_enrich"]
    competitors = [o for o in ops if o.get("lane") == "competitor_intel"]

    lines = [f"*{client} · {date_str} · {len(engage)} to work*",
             f"_{len(leads)} new leads to enrich · {len(competitors)} competitor mentions · "
             f"reply first, value first_", ""]
    for o in engage[:limit]:
        a = angles.get(o.get("op_id"), {})
        prio = (o["_prio"] or "med").upper()
        sub = "r/" + (o.get("subreddit") or "")
        ag = age(o.get("posted_at"))
        summary = (o.get("summary") or "")[:130]
        why = o.get("reason", "")
        angle = a.get("angle", "")
        lines.append(f"*[{prio}] {sub}*{(' · ' + ag) if ag else ''}  —  {summary}")
        if why:
            lines.append(f"   _why:_ {why}")
        if angle:
            lines.append(f"   _reply:_ {angle}")
        if o.get("permalink"):
            lines.append(f"   <{o['permalink']}|open thread>")
        lines.append("")
    if len(engage) > limit:
        lines.append(f"_+{len(engage) - limit} more in the sheet._")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ops", default="data/ops_classified.json")
    ap.add_argument("--angles", default="data/engage_angles.json")
    ap.add_argument("--client", required=True)
    ap.add_argument("--date", default=datetime.now(timezone.utc).strftime("%b %-d, %Y"))
    ap.add_argument("--limit", type=int, default=8)
    ap.add_argument("--out", default="data/slack_digest.txt")
    ap.add_argument("--post", action="store_true")
    ap.add_argument("--webhook-secret", default="")
    args = ap.parse_args()

    ops = json.loads(Path(args.ops).read_text())
    angles = {}
    if Path(args.angles).exists():
        for a in json.loads(Path(args.angles).read_text()):
            angles[a.get("op_id")] = a

    text = build(ops, angles, args.client, args.date, args.limit)
    Path(args.out).write_text(text)
    print(f"digest rendered -> {args.out} ({text.count(chr(10))} lines)")

    if args.post:
        if not args.webhook_secret:
            print("  --post given but no --webhook-secret; not posting")
            return 0
        url = get_secret(args.webhook_secret)
        if not url:
            print(f"  no webhook found under '{args.webhook_secret}' (env var or SECRETS_DB); not posting")
            return 0
        ok = slack_post(url, text)
        print(f"  posted to Slack via {args.webhook_secret}: {'ok' if ok else 'failed'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
