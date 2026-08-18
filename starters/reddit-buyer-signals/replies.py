#!/usr/bin/env python3
"""replies.py - scaffold, gate, and check the suggested-reply pass.

One gated, <=18-word reply template per classified opportunity. The coding
agent writes each template; this module scaffolds the contract, enforces the
hard word cap and the shared anti-slop gate, renders the Suggested Replies
sheet tab on an existing client sheet, and exports digest-ready angles.

Usage:
    python3 replies.py scaffold --ops data/ops_classified.json --out data/suggested_replies.json
    # the agent writes every empty reply slot (<=18 words each), then:
    python3 replies.py check data/suggested_replies.json --ops data/ops_classified.json
    python3 replies.py sheet --ops data/ops_classified.json --replies data/suggested_replies.json --sheet-id <id>
    python3 replies.py angles --ops data/ops_classified.json --replies data/suggested_replies.json --out data/engage_angles.json

Gates are deterministic from the action lane; per-op overrides beat the lane.
Every reply is a draft template. A human edits and posts each one personally.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from content import slop_flags  # noqa: E402  (single banned-list source of truth)

MAX_WORDS = 18
GATES = ("GO", "REVIEW", "NO-REPLY")
_GO_LANES = {"engage_now", "reply_now"}
_NOREPLY_LANES = {"competitor_intel", "competitor_watch"}
GATE_NOTES = {
    "GO": "Timely thread. Reply when ready.",
    "REVIEW": "Check thread age + sub self-promo rules first.",
    "NO-REPLY": "Log as competitor intel. Do not post.",
}
DEFAULT_RULES = (
    "Every reply is a draft template. Nothing posts automatically. All replies go "
    "through the account owner personally before posting. Disclose affiliation whenever "
    "the product comes up. Never DM. Check subreddit self-promo rules and thread age "
    "before posting. Gate: GO = timely, reply when ready. REVIEW = check thread age + "
    "sub rules first. NO-REPLY = log as intel, do not post."
)

HEADERS = ["Op ID", "Tier", "Lane", "Reply Gate", "Gate Note", "Subreddit",
           "What They Want", "Suggested Reply (≤18 words, edit before posting)", "Reddit URL"]
_GATE_ORDER = {"GO": 0, "REVIEW": 1, "NO-REPLY": 2}


def word_count(text: str) -> int:
    """wc -w semantics: whitespace-separated tokens."""
    return len(text.split())


def op_key(op: dict) -> str:
    return str(op.get("op_id") or op.get("id") or "")


def op_lane(op: dict) -> str:
    return str(op.get("lane") or op.get("action_lane") or "")


def gate_for(op: dict, overrides: dict) -> tuple[str, str]:
    """Override wins; else the lane decides; anything unrecognized needs REVIEW."""
    ov = overrides.get(op_key(op))
    if ov is not None:
        if not isinstance(ov, (list, tuple)) or not ov:
            raise ValueError(f"override for op {op_key(op)} must be [gate, note]")
        gate, note = str(ov[0]), str(ov[1]) if len(ov) > 1 else ""
        if gate not in GATES:
            raise ValueError(f"override for op {op_key(op)} has invalid gate {gate!r} (must be one of {GATES})")
        return gate, note
    lane = op_lane(op)
    if lane in _NOREPLY_LANES:
        return "NO-REPLY", GATE_NOTES["NO-REPLY"]
    if lane in _GO_LANES:
        return "GO", GATE_NOTES["GO"]
    return "REVIEW", GATE_NOTES["REVIEW"]


def load_ops(path: str) -> list[dict]:
    rows = json.loads(Path(path).read_text())
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected a list of classified ops")
    return rows


def load_contract(path: str) -> dict:
    data = json.loads(Path(path).read_text())
    for key, kind in (("rules", str), ("replies", dict), ("gate_overrides", dict)):
        if not isinstance(data.get(key), kind):
            raise ValueError(f"{path}: key {key!r} missing or not a {kind.__name__}")
    return data


def scaffold(args) -> int:
    ops = load_ops(args.ops)
    out = Path(args.out)
    if out.exists() and not args.force:
        existing = json.loads(out.read_text())
        if any(str(v).strip() for v in existing.get("replies", {}).values()):
            print(f"{out} already holds drafted replies; use --force to overwrite")
            return 1
    counts = {g: 0 for g in GATES}
    replies: dict[str, str] = {}
    for op in ops:
        gate, _ = gate_for(op, {})
        counts[gate] += 1
        if gate != "NO-REPLY":
            replies[op_key(op)] = ""
    contract = {"rules": DEFAULT_RULES, "replies": replies, "gate_overrides": {}}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(contract, indent=2, ensure_ascii=False))
    print(f"scaffolded {out}: {len(replies)} reply slots "
          f"(GO {counts['GO']} / REVIEW {counts['REVIEW']} / NO-REPLY {counts['NO-REPLY']} gated out)")
    print("  next: the agent writes each empty reply (<=18 words), then `replies.py check`")
    return 0


def check_contract(contract: dict, ops: list[dict] | None, max_words: int) -> list[tuple[str, str]]:
    """Return (op_id, flag) pairs. Empty means the pass is shippable."""
    flags: list[tuple[str, str]] = []
    overrides = contract["gate_overrides"]
    for oid, ov in overrides.items():
        if not isinstance(ov, (list, tuple)) or len(ov) != 2 or ov[0] not in GATES or not str(ov[1]).strip():
            flags.append((oid, f"override must be [gate, note] with gate in {GATES}"))
    by_id = {op_key(o): o for o in ops} if ops is not None else None
    for oid, reply in contract["replies"].items():
        reply = str(reply)
        if by_id is not None and oid not in by_id:
            flags.append((oid, "reply key not present in --ops"))
            continue
        gate = None
        if by_id is not None:
            try:
                gate, _ = gate_for(by_id[oid], overrides)
            except ValueError as e:
                flags.append((oid, str(e)))
                continue
        if gate == "NO-REPLY":
            if reply.strip():
                flags.append((oid, "gate is NO-REPLY but a reply is drafted"))
            continue
        if not reply.strip():
            flags.append((oid, "reply slot is empty"))
            continue
        n = word_count(reply)
        if n > max_words:
            flags.append((oid, f"{n}/{max_words} words, over the hard cap"))
        if re.search(r"https?://|www\.", reply, re.IGNORECASE):
            flags.append((oid, "link in reply (no links, ever)"))
        for fl in slop_flags(reply):
            flags.append((oid, fl))
    if by_id is not None:
        for oid in overrides:
            if oid not in by_id:
                flags.append((oid, "override key not present in --ops"))
        for op in ops:
            oid = op_key(op)
            if oid in contract["replies"]:
                continue
            try:
                gate, _ = gate_for(op, overrides)
            except ValueError:
                continue  # already flagged in the override validation pass
            if gate != "NO-REPLY":
                flags.append((oid, "op has no reply slot; ops drifted since scaffold, re-run scaffold"))
    return flags


def check(args) -> int:
    contract = load_contract(args.path)
    ops = load_ops(args.ops) if args.ops else None
    overrides = contract["gate_overrides"]
    flags = check_contract(contract, ops, args.max_words)
    flagged = {oid for oid, _ in flags}
    if ops is not None:
        for op in ops:
            oid = op_key(op)
            try:
                gate, _ = gate_for(op, overrides)
            except ValueError:
                continue
            reply = str(contract["replies"].get(oid, ""))
            mark = "ok" if oid not in flagged else f"{sum(1 for f, _ in flags if f == oid)} flag(s)"
            print(f"{oid}  {word_count(reply)}/{args.max_words}  {gate}  {mark}")
    for oid, fl in flags:
        print(f"   - {oid}: {fl}")
    n_replies = sum(1 for v in contract["replies"].values() if str(v).strip())
    print(f"\n{'PASS' if not flags else 'FAIL'}: {len(flags)} flag(s) across {n_replies} drafted replies")
    return 0 if not flags else 1


def sheet_values(ops: list[dict], contract: dict) -> list[list[str]]:
    overrides = contract["gate_overrides"]
    rows = []
    for op in ops:
        gate, note = gate_for(op, overrides)
        rows.append([
            op_key(op), str(op.get("tier") or ""), op_lane(op), gate, note,
            "r/" + str(op.get("subreddit") or ""),
            str(op.get("summary") or op.get("snippet") or "")[:160],
            str(contract["replies"].get(op_key(op), "")),
            str(op.get("permalink") or op.get("url") or op.get("source_url") or ""),
        ])
    rows.sort(key=lambda r: (_GATE_ORDER.get(r[3], 9), r[1] or "Z", r[0]))
    return [[contract["rules"]] + [""] * 8, HEADERS] + rows


def sheet(args) -> int:
    ops = load_ops(args.ops)
    contract = load_contract(args.replies)
    flags = check_contract(contract, ops, args.max_words)
    if flags:
        for oid, fl in flags:
            print(f"   - {oid}: {fl}")
        print(f"FAIL: {len(flags)} flag(s); an unchecked reply never reaches a client surface")
        return 1
    sheet_id = args.sheet_id
    if not sheet_id and args.sheet_url_file:
        m = re.search(r"/d/([A-Za-z0-9_-]+)", Path(args.sheet_url_file).read_text())
        sheet_id = m.group(1) if m else Path(args.sheet_url_file).read_text().strip()
    if not sheet_id:
        print("need --sheet-id or --sheet-url-file")
        return 1

    import gspread  # deferred: scaffold/check/angles run without Google deps
    from lib.sheet_engine import AMBER, GREEN, NAVY, RED, YELLOW, cf_text, creds, r_width, rgb

    gc = gspread.authorize(creds(Path(args.token)))
    ss = gc.open_by_key(sheet_id)
    values = sheet_values(ops, contract)
    for ws in ss.worksheets():
        if ws.title == args.tab_title:
            ss.del_worksheet(ws)  # replace only this tab; every other tab is untouched
    ws = ss.add_worksheet(title=args.tab_title, rows=len(values) + 2, cols=len(HEADERS))
    ws.update(values, "A1", raw=True)
    sid = ws.id
    ncols = len(HEADERS)
    requests = [
        {"mergeCells": {"range": {"sheetId": sid, "startRowIndex": 0, "endRowIndex": 1,
                                  "startColumnIndex": 0, "endColumnIndex": ncols}, "mergeType": "MERGE_ALL"}},
        {"repeatCell": {"range": {"sheetId": sid, "startRowIndex": 0, "endRowIndex": 1,
                                  "startColumnIndex": 0, "endColumnIndex": ncols},
                        "cell": {"userEnteredFormat": {"backgroundColor": rgb(AMBER), "wrapStrategy": "WRAP",
                                 "textFormat": {"bold": True, "fontSize": 9}}},
                        "fields": "userEnteredFormat(backgroundColor,wrapStrategy,textFormat)"}},
        {"repeatCell": {"range": {"sheetId": sid, "startRowIndex": 1, "endRowIndex": 2,
                                  "startColumnIndex": 0, "endColumnIndex": ncols},
                        "cell": {"userEnteredFormat": {"backgroundColor": rgb(NAVY),
                                 "textFormat": {"foregroundColor": rgb("FFFFFF"), "bold": True, "fontSize": 10},
                                 "verticalAlignment": "MIDDLE"}},
                        "fields": "userEnteredFormat(backgroundColor,textFormat,verticalAlignment)"}},
        {"updateSheetProperties": {"properties": {"sheetId": sid, "gridProperties": {"frozenRowCount": 2}},
                                   "fields": "gridProperties.frozenRowCount"}},
        {"updateDimensionProperties": {"range": {"sheetId": sid, "dimension": "ROWS",
                                                 "startIndex": 0, "endIndex": 1},
                                       "properties": {"pixelSize": 72}, "fields": "pixelSize"}},
        r_width(sid, 4, 260), r_width(sid, 6, 320), r_width(sid, 7, 420), r_width(sid, 8, 240),
        cf_text(sid, 3, len(values), "GO", GREEN),
        cf_text(sid, 3, len(values), "REVIEW", YELLOW),
        cf_text(sid, 3, len(values), "NO-REPLY", RED),
    ]
    ss.batch_update({"requests": requests})
    print(f"wrote {len(values) - 2} rows -> tab {args.tab_title!r} on https://docs.google.com/spreadsheets/d/{sheet_id}")
    return 0


def angles(args) -> int:
    ops = load_ops(args.ops)
    contract = load_contract(args.replies)
    flags = check_contract(contract, ops, args.max_words)
    if flags:
        for oid, fl in flags:
            print(f"   - {oid}: {fl}")
        print(f"FAIL: {len(flags)} flag(s); an unchecked reply never reaches a client surface")
        return 1
    overrides = contract["gate_overrides"]
    out = []
    for op in ops:
        oid = op_key(op)
        reply = str(contract["replies"].get(oid, "")).strip()
        gate, _ = gate_for(op, overrides)
        if gate == "NO-REPLY" or not reply:
            continue
        out.append({"op_id": oid, "priority": "high" if gate == "GO" else "med", "angle": reply})
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"exported {len(out)} angles -> {args.out} (digest-ready)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    sc = sub.add_parser("scaffold", help="build the suggested_replies.json contract from the classified ops")
    sc.add_argument("--ops", default="data/ops_classified.json")
    sc.add_argument("--out", default="data/suggested_replies.json")
    sc.add_argument("--force", action="store_true", help="overwrite even if drafted replies exist")
    sc.set_defaults(fn=scaffold)

    ck = sub.add_parser("check", help="enforce the word cap, the gates, and the anti-slop scan")
    ck.add_argument("path", nargs="?", default="data/suggested_replies.json")
    ck.add_argument("--ops", default="", help="classified ops json; enables gate cross-checks")
    ck.add_argument("--max-words", type=int, default=MAX_WORDS)
    ck.set_defaults(fn=check)

    sh = sub.add_parser("sheet", help="add or replace the Suggested Replies tab on an existing sheet")
    sh.add_argument("--ops", default="data/ops_classified.json")
    sh.add_argument("--replies", default="data/suggested_replies.json")
    sh.add_argument("--sheet-id", default="")
    sh.add_argument("--sheet-url-file", default="data/sheet_url.txt")
    sh.add_argument("--tab-title", default="Suggested Replies")
    sh.add_argument("--max-words", type=int, default=MAX_WORDS)
    sh.add_argument("--token", default=str(Path.home() / ".config" / "gspread" / "token.json"))
    sh.set_defaults(fn=sheet)

    an = sub.add_parser("angles", help="export digest-compatible engage_angles.json from the drafted replies")
    an.add_argument("--ops", default="data/ops_classified.json")
    an.add_argument("--replies", default="data/suggested_replies.json")
    an.add_argument("--out", default="data/engage_angles.json")
    an.add_argument("--max-words", type=int, default=MAX_WORDS)
    an.set_defaults(fn=angles)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
