#!/usr/bin/env python3
"""build_sheet.py -- render the graded list as a color-coded Google Sheet with a dashboard.

Tabs: Dashboard | Send Ready | Send Low Volume | Route: LinkedIn | Review / Hold | Suppressed |
All Contacts | Grading Model | Moltsets Usage. Grade cells are colored A green .. D red, and every
row carries a route. Emails are obfuscated unless --full-emails. Rebuilds in place so the link
never changes.

  python3 build_sheet.py                 # rebuild stored sheet or create a new one
  python3 build_sheet.py --new           # force a new sheet
  python3 build_sheet.py --full-emails   # private copy with real addresses
  python3 build_sheet.py --title "My list"
"""
import argparse
import json
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import sheet_engine as SE  # noqa: E402
from lib.reachability import GRADE_MEANING, GRADE_MULT, TIER_ACTION  # noqa: E402

HERE = Path(__file__).resolve().parent
DB = HERE / "data" / "reachability.db"
URL_FILE = HERE / "data" / "sheet_url.txt"

GRADE_COLOR = {"A": SE.GREEN, "B": SE.GREEN_LT, "C": SE.AMBER, "D": SE.RED, "F": SE.ORANGE, "-": SE.GREY_LT}
TIER_COLOR = {"T1_send": SE.GREEN, "T1_send_corrected": SE.GREEN_LT, "T2_catchall": SE.YELLOW,
              "HOLD_review": SE.AMBER, "HOLD_job_change": SE.ORANGE, "HOLD_not_found": SE.GREY,
              "HOLD_no_email": SE.GREY_LT, "SUPPRESS": SE.RED}
ROUTE_COLOR = {"email": SE.GREEN, "email_low_volume": SE.YELLOW, "linkedin": SE.BLUE,
               "linkedin_then_phone": "B4A7D6", "second_pass": SE.GREY, "resource": SE.ORANGE, "hold": SE.GREY_LT}
STILL_COLOR = {"yes": SE.GREEN_LT, "moved": SE.ORANGE, "unknown": SE.GREY_LT}
PERSONA_COLOR = {"sales": SE.GREEN, "marketing": SE.BLUE, "product": "D5A6E6", "founder": SE.YELLOW}


def stored_key():
    if URL_FILE.exists():
        m = re.search(r"/d/([A-Za-z0-9_-]+)", URL_FILE.read_text())
        return m.group(1) if m else None
    return None


def obfuscate(email):
    if not email or "@" not in email:
        return email or ""
    local, d = email.rsplit("@", 1)
    return f"{local[0]}***@{d}" if len(local) <= 2 else f"{local[0]}***{local[-1]}@{d}"


def obfuscate_phone(p):
    if not p:
        return ""
    digits = "".join(c for c in str(p) if c.isdigit())
    return f"'+{digits[:1]}-***-***-{digits[-4:]}" if len(digits) >= 4 else "***"


def pct(n, d):
    return f"{n} ({100 * n / d:.0f}%)" if d else "0"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--new", action="store_true")
    ap.add_argument("--full-emails", action="store_true")
    ap.add_argument("--redact-names", action="store_true", help="public stills: last names and LinkedIn slugs masked")
    ap.add_argument("--title", default="Moltsets Reachability Sheet")
    ap.add_argument("--share", default="none", choices=["none", "anyone_reader"])
    args = ap.parse_args()

    con = sqlite3.connect(DB)
    cur = con.execute("SELECT * FROM contacts ORDER BY composite_score DESC, company")
    cols = [d[0] for d in cur.description]
    df = pd.DataFrame([dict(zip(cols, r)) for r in cur.fetchall()], columns=cols)
    if df.empty:
        sys.exit("no contacts. run init_db.py and grade.py first.")
    for c in ("molt_current_company", "molt_current_domain", "employment_source", "employment_agree"):
        if c not in df.columns:
            df[c] = ""
    for c in df.columns:
        df[c] = df[c].fillna("").astype(str)
    df["full_name"] = (df["first_name"].str.strip() + " " + df["last_name"].str.strip()).str.strip()
    df["grade"] = df["grade"].replace("", "-")
    df["still_at_company"] = df["still_at_company"].replace("", "unknown")
    df["action"] = df["tier"].map(lambda t: TIER_ACTION.get(t, ""))
    if args.redact_names:
        df["last_name"] = df["last_name"].map(lambda v: (v[:1] + "***") if v else "")
        df["full_name"] = (df["first_name"].str.strip() + " " + df["last_name"]).str.strip()
        df["linkedin_url"] = df["linkedin_url"].map(lambda v: "linkedin.com/in/***" if v else "")
        df["molt_linkedin"] = df["molt_linkedin"].map(lambda v: "linkedin.com/in/***" if v else "")
    if not args.full_emails:
        df["email"] = df["email"].apply(obfuscate)
        df["molt_email"] = df["molt_email"].apply(obfuscate)
        df["mobile_phone"] = df["mobile_phone"].apply(obfuscate_phone)

    # usage tab from the ledger
    usage = con.execute(
        """SELECT endpoint, COUNT(*), SUM(CASE WHEN http_status LIKE '2%' THEN 1 ELSE 0 END),
                  SUM(CASE WHEN http_status='404' THEN 1 ELSE 0 END),
                  SUM(CASE WHEN http_status NOT LIKE '2%' AND http_status!='404' THEN 1 ELSE 0 END),
                  COALESCE(SUM(ext_tokens_used),0)
           FROM moltsets_api_log GROUP BY endpoint ORDER BY 2 DESC""").fetchall()
    con.close()
    summary_path = HERE / "data" / "grade_summary.json"
    gs = json.loads(summary_path.read_text()) if summary_path.exists() else {}
    stats = gs.get("stats", {})

    n = len(df)
    grades = Counter(df["grade"])
    tiers = Counter(df["tier"])
    routes = Counter(df["route"])
    still = Counter(df["still_at_company"])
    graded = int((df["grade"] != "-").sum())
    sendable = tiers.get("T1_send", 0) + tiers.get("T1_send_corrected", 0)
    rel_calls, rel_hit = stats.get("rel_calls", 0), stats.get("rel_hit", 0)

    entries = [
        {"kind": "section", "label": "THE LIST"},
        {"kind": "kpi", "label": "Contacts loaded", "value": str(n)},
        {"kind": "kpi", "label": "Graded by Moltsets (any grade)", "value": pct(graded, n)},
        {"kind": "kpi", "label": "Send ready (A/B, same domain)", "value": pct(sendable, n)},
        {"kind": "kpi", "label": "  of which recovered by the second pass", "value": str(int(((df["molt_route"] == "search_people") & df["tier"].isin(["T1_send", "T1_send_corrected"])).sum()))},
        {"kind": "kpi", "label": "Send low volume (C catch-all)", "value": str(tiers.get("T2_catchall", 0))},
        {"kind": "kpi", "label": "Never email (D), routed to LinkedIn", "value": str(tiers.get("SUPPRESS", 0))},
        {"kind": "kpi", "label": "Not in the graph after all passes", "value": str(tiers.get("HOLD_not_found", 0))},
        {"kind": "kpi", "label": "Job changed (either source), re-source", "value": str(tiers.get("HOLD_job_change", 0))},
        {"kind": "blank"},
        {"kind": "section", "label": "GRADE DISTRIBUTION"},
    ]
    for g in ["A", "B", "C", "D", "F", "-"]:
        if grades.get(g):
            entries.append({"kind": "kpi", "label": f"  {g}: {GRADE_MEANING[g]}", "value": pct(grades[g], n)})
    entries += [{"kind": "blank"}, {"kind": "section", "label": "ROUTE MIX (every row keeps a channel)"}]
    for rt in ["email", "email_low_volume", "linkedin", "linkedin_then_phone", "resource", "second_pass", "hold"]:
        if routes.get(rt):
            entries.append({"kind": "kpi", "label": f"  {rt}", "value": pct(routes[rt], n)})
    entries += [{"kind": "blank"}, {"kind": "section", "label": "WATERFALL RECEIPTS (this run)"}]
    if rel_calls:
        entries.append({"kind": "kpi", "label": "reverse_email_lookup hit rate", "value": pct(rel_hit, rel_calls)})
        entries.append({"kind": "kpi", "label": "  404 = not in graph (free)", "value": str(stats.get("rel_404", 0))})
    if stats.get("sp_calls"):
        entries.append({"kind": "kpi", "label": "second pass: search_people calls", "value": str(stats["sp_calls"])})
        entries.append({"kind": "kpi", "label": "  recovered same-domain A/B", "value": pct(stats.get("sp_recovered", 0), stats["sp_calls"])})
    agree = Counter(df["employment_agree"])
    entries.append({"kind": "kpi", "label": "still at company / moved / unknown",
                    "value": f"{still.get('yes', 0)} / {still.get('moved', 0)} / {still.get('unknown', 0)}"})
    if stats.get("rll_calls"):
        entries.append({"kind": "kpi", "label": "Moltsets reverse_linkedin_lookup (URL key) hit rate", "value": pct(stats.get("rll_hit", 0), stats["rll_calls"])})
        entries.append({"kind": "kpi", "label": "  of which returned a graded business email", "value": str(stats.get("rll_graded", 0))})
    if stats.get("apollo_checked"):
        entries.append({"kind": "kpi", "label": "Apollo people/match checks", "value": str(stats["apollo_checked"])})
    if agree.get("yes") or agree.get("no"):
        entries.append({"kind": "kpi", "label": "Apollo vs Moltsets on employment: agree / disagree",
                        "value": f"{agree.get('yes', 0)} / {agree.get('no', 0)}"})
    if stats.get("phone_calls"):
        entries.append({"kind": "kpi", "label": "mobile lookups (1 phone token per hit)", "value": f"{stats['phone_hit']} hits / {stats['phone_calls']} calls"})
    phone_hits = sum(u[2] for u in usage if u[0] == "linkedin_to_mobile_phone")
    entries.append({"kind": "kpi", "label": "phone tokens spent (1 per mobile hit)", "value": str(phone_hits)})
    entries += [
        {"kind": "blank"},
        {"kind": "section", "label": "HOW TO READ IT"},
        {"kind": "bullet", "label": "Green A = valid, seen replying or opening. Send. Light green B = delivered before, no bounce. Send in smaller batches."},
        {"kind": "bullet", "label": "Amber C = catch-all domain. The mailbox may not exist. Small monitored segment, or LinkedIn first."},
        {"kind": "bullet", "label": "Red D = hard invalid, complaint, or spam trap. Never email. The row stays: LinkedIn, then phone if you have tokens (1 phone token per hit, misses free)."},
        {"kind": "bullet", "label": "Orange F and grey dash = no data. The graph has not seen this address. That is a coverage gap, not a verdict. Second pass, then LinkedIn."},
        {"kind": "bullet", "label": "Score = title relevance x grade multiplier (A 1.0, B 0.85, C 0.6, F 0.3, D 0.15). Rank = top 3 sendable per company."},
    ]

    base_cols = ["rank", "composite_score", "grade", "tier", "route", "full_name", "title", "persona",
                 "company", "domain", "email", "molt_email", "grade_validated_at", "still_at_company",
                 "employment_agree", "molt_current_company", "apollo_current_company", "linkedin_url",
                 "mobile_phone", "action"]
    widths = {"full_name": 170, "title": 220, "company": 160, "domain": 150, "email": 200,
              "molt_email": 200, "grade_validated_at": 120, "apollo_current_company": 160,
              "molt_current_company": 160, "employment_agree": 110,
              "linkedin_url": 230, "mobile_phone": 130, "action": 340, "tier": 150, "route": 150}
    AGREE_COLOR = {"yes": SE.GREEN_LT, "no": SE.ORANGE, "n/a": SE.GREY_LT}
    cfs = [
        {"col": "composite_score", "type": "grad", "stops": (0, 60, 150)},
        {"col": "employment_agree", "type": "map", "map": AGREE_COLOR},
        {"col": "grade", "type": "map", "map": GRADE_COLOR},
        {"col": "tier", "type": "map", "map": TIER_COLOR},
        {"col": "route", "type": "map", "map": ROUTE_COLOR},
        {"col": "still_at_company", "type": "map", "map": STILL_COLOR},
        {"col": "persona", "type": "map", "map": PERSONA_COLOR},
    ]

    def tab(title, frame):
        return {"title": f"{title} ({len(frame)})", "df": frame, "cols": base_cols, "widths": widths,
                "numeric": ["composite_score", "rank"], "cf": cfs}

    send_df = df[df["tier"].isin(["T1_send", "T1_send_corrected"])]
    low_df = df[df["tier"] == "T2_catchall"]
    li_df = df[df["route"].isin(["linkedin", "linkedin_then_phone"])]
    hold_df = df[df["tier"].isin(["HOLD_review", "HOLD_job_change", "HOLD_no_email"]) |
                 ((df["tier"] == "HOLD_not_found") & (df["route"] == "hold"))]
    sup_df = df[df["tier"] == "SUPPRESS"]
    tabs = [t for t in [tab("Send Ready", send_df), tab("Send Low Volume", low_df),
                        tab("Route - LinkedIn", li_df), tab("Review - Hold", hold_df),
                        tab("Suppressed", sup_df)] if len(t["df"])]
    tabs.append(tab("All Contacts", df))

    model = [["GRADING MODEL: lib/reachability.py", "", ""],
             ["Grade", "Meaning (developer.moltsets.com)", "Multiplier"]]
    for g in ["A", "B", "C", "D", "F", "-"]:
        model.append([g, GRADE_MEANING[g], f"{GRADE_MULT[g]}x"])
    model += [["", "", ""], ["TIER", "ACTION", ""]]
    for t, a in TIER_ACTION.items():
        model.append([t, a, ""])
    model += [["", "", ""], ["TITLE WEIGHTS (additive)", "RevOps 100 / Revenue 90 / Growth 80 / GTM 75 / Sales 60 / Marketing 55 / Product 50 / BizDev 45 / Founder 40 / Chief 30 / VP 25 / Head of 20 / Director 15 / Manager 5", ""],
              ["EXAMPLE", "Head of Growth, grade A: (80 + 20) x 1.0 = 100.0", ""],
              ["EXAMPLE", "Head of Growth, grade D: (80 + 20) x 0.15 = 15.0, route linkedin_then_phone", ""]]

    usage_tab = [["MOLTSETS USAGE (this project's ledger)", "", "", "", "", ""],
                 ["endpoint", "calls", "hit", "not_found", "error", "external tokens"]]
    usage_tab += [[u[0], str(u[1]), str(u[2]), str(u[3]), str(u[4]), str(u[5])] for u in usage]
    usage_tab += [["", "", "", "", "", ""],
                  ["A 404 costs nothing and consumes no record. Only data-bearing calls count against the 5h pools.", "", "", "", "", ""],
                  [f"records_remaining_5h after run: {gs.get('records_remaining_5h')}   phone tokens: {gs.get('phone_tokens_remaining')}", "", "", "", "", ""]]

    config = {
        "title": args.title,
        "key": None if args.new else stored_key(),
        "share": None if args.share == "none" else args.share,
        "dashboard": {"title": "Dashboard",
                      "subtitle": {"title": "REACHABILITY: RELEVANCE x TIMING x A GRADED ADDRESS",
                                   "sub": f"{n} contacts, {sendable} send ready, {routes.get('linkedin', 0) + routes.get('linkedin_then_phone', 0)} rows routed to LinkedIn instead of deleted "
                                          f"| the LinkedIn URL confirms the person, Moltsets grades the address, the sheet picks the channel "
                                          f"| Built with the Clearbox GTM OS - clearbox.to"},
                      "entries": entries},
        "tabs": tabs,
        "raw_tabs": [{"title": "Grading Model", "values": model, "widths": {0: 220, 1: 520, 2: 110}},
                     {"title": "Moltsets Usage", "values": usage_tab, "widths": {0: 260, 1: 80, 2: 80, 3: 90, 4: 70, 5: 120}}],
    }
    url, titles = SE.build(config)
    URL_FILE.parent.mkdir(parents=True, exist_ok=True)
    URL_FILE.write_text(url + "\n")
    print("SHEET:", url)
    print("tabs:", titles)


if __name__ == "__main__":
    main()
