#!/usr/bin/env python3
"""build_sheet.py -- render the graded list as a color-coded Google Sheet with a dashboard.

Tabs: Dashboard | Send Ready | Send Low Volume | Route - LinkedIn | Review - Hold | Suppressed |
Disagreements | All Contacts | Verifier vs Moltsets | Grading Model | Moltsets Usage. Grade cells are
colored A green .. D red, every row carries a route, and when the list came in with a verifier's
verdict (ZeroBounce, NeverBounce, ...) every row also carries a delta class: how Moltsets moved it
relative to that verdict. Disagreements and Verifier vs Moltsets appear only when a verdict exists.
Emails are obfuscated unless --full-emails. Rebuilds in place so the link never changes.

  python3 build_sheet.py                 # rebuild stored sheet or create a new one
  python3 build_sheet.py --new           # force a new sheet
  python3 build_sheet.py --full-emails   # private copy with real addresses
  python3 build_sheet.py --redact-names  # public stills: last names and LinkedIn slugs masked
  python3 build_sheet.py --summary-only --share anyone_reader   # Dashboard + Verifier vs Moltsets + models, no rows
  python3 build_sheet.py --title "My list"
  REACHABILITY_DB=data/other.db python3 build_sheet.py --new   # a second list, its own sheet
"""
import argparse
import json
import os
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import sheet_engine as SE  # noqa: E402
from lib.reachability import (DELTA_LEGEND, GRADE_MEANING, GRADE_MULT, HARD_FAIL, TIER_ACTION,  # noqa: E402
                              VERIFIER_STATUSES)

HERE = Path(__file__).resolve().parent
DB = Path(os.environ.get("REACHABILITY_DB") or HERE / "data" / "reachability.db")
_stem = "" if DB == HERE / "data" / "reachability.db" else DB.stem + "_"
URL_FILE = DB.parent / f"{_stem}sheet_url.txt"
SUMMARY_URL_FILE = DB.parent / f"{_stem}summary_sheet_url.txt"
GRADE_SUMMARY = DB.parent / f"{_stem}grade_summary.json"     # written by grade.py / import_graded.py for this database

GRADE_COLOR = {"A": SE.GREEN, "B": SE.GREEN_LT, "C": SE.AMBER, "D": SE.RED, "F": SE.ORANGE, "-": SE.GREY_LT}
TIER_COLOR = {"T1_send": SE.GREEN, "T1_send_corrected": SE.GREEN_LT, "T2_catchall": SE.YELLOW,
              "HOLD_review": SE.AMBER, "HOLD_job_change": SE.ORANGE, "HOLD_not_found": SE.GREY,
              "HOLD_no_email": SE.GREY_LT, "SUPPRESS": SE.RED}
ROUTE_COLOR = {"email": SE.GREEN, "email_low_volume": SE.YELLOW, "linkedin": SE.BLUE,
               "linkedin_then_phone": "B4A7D6", "second_pass": SE.GREY, "resource": SE.ORANGE, "hold": SE.GREY_LT}
STILL_COLOR = {"yes": SE.GREEN_LT, "moved": SE.ORANGE, "unknown": SE.GREY_LT}
PERSONA_COLOR = {"sales": SE.GREEN, "marketing": SE.BLUE, "product": "D5A6E6", "founder": SE.YELLOW}
VERIFIER_COLOR = {"valid": SE.GREEN_LT, "catch-all": SE.AMBER, "unknown": SE.GREY, "invalid": SE.RED,
                  "do_not_mail": "F4CCCC", "abuse": SE.RED}
DELTA_COLOR = {"agree": SE.GREEN_LT, "molt_upgrades_catchall": SE.GREEN, "molt_recovers_invalid": SE.GREEN,
               "molt_corrects_address": SE.GREEN, "molt_contradicts_invalid": SE.AMBER, "molt_grades_unknown": SE.BLUE,
               "molt_downgrades_valid": SE.RED, "confirms_invalid": "F4CCCC", "molt_catchall": SE.AMBER,
               "molt_no_data": SE.ORANGE, "person_confirmed_other_email": SE.BLUE, "cross_domain_review": SE.YELLOW,
               "not_in_graph": SE.GREY_LT}
DELTA_ORDER = [k for k, _ in DELTA_LEGEND]
AGREEMENT_CLASSES = {"", "agree", "not_in_graph", "molt_no_data"}   # everything else is a disagreement worth a look


def stored_key(url_file=URL_FILE):
    if url_file.exists():
        m = re.search(r"/d/([A-Za-z0-9_-]+)", url_file.read_text())
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


def outcome(grade):
    return grade if grade in ("A", "B", "C", "D", "F") else "not_found"


def verifier_tables(df, usage):
    """The Verifier vs Moltsets tab as a value grid plus formatting hints. Vendor-neutral wording."""
    v = df[df["verifier_status"] != ""]
    n, nv = len(df), len(v)
    grades = Counter(outcome(g) for g in df["grade"].replace("-", ""))
    vgrades = Counter(outcome(g) for g in v["grade"].replace("-", ""))
    delta = Counter(v["delta_class"])
    ab = grades["A"] + grades["B"]
    corrected = int((df["corrected"] == "yes").sum())
    catchall_ab = int((v["verifier_status"].eq("catch-all") & v["grade"].isin(["A", "B"])).sum())
    catchall_rows = int(v["verifier_status"].eq("catch-all").sum())
    hardfail_rows = int(v["verifier_status"].isin(HARD_FAIL).sum())
    f_on_valid = int((v["verifier_status"].eq("valid") & v["grade"].eq("F")).sum())
    moved = int((df["still_at_company"] == "moved").sum())
    li = int(((df["linkedin_url"] != "") | (df["molt_linkedin"] != "")).sum())
    sp_rows = int((df["second_pass"] == "yes").sum())
    sp_ok = int((df["second_pass_decision"] == "accept_same_domain").sum())
    calls = sum(u[1] for u in usage)
    phone_hits = sum(u[2] for u in usage if u[0] == "linkedin_to_mobile_phone")

    kpis = [
        ("Rows on the list", n),
        ("Rows with a verifier verdict", nv),
        ("Graded by Moltsets (A to F)", pct(sum(grades[g] for g in "ABCDF"), n)),
        ("A/B send-confirmed on observed activity", pct(ab, n)),
        ("F: person known, address never seen in use", pct(grades["F"], n)),
        ("Not in the graph after all passes", pct(grades["not_found"], n)),
        ("Agree: verifier valid, Moltsets A/B on the same address (send first)", delta["agree"]),
        ("Corrected: Moltsets prefers a different same-domain address", corrected),
        ("Verifier catch-all rows graded A/B (the verifier could not grade these)", f"{catchall_ab} of {catchall_rows}"),
        ("Verifier hard-fail rows recovered with a same-domain A/B address", f"{delta['molt_recovers_invalid']} of {hardfail_rows}"),
        ("Verifier hard-fail, Moltsets A/B on the exact address (review, re-probe)", delta["molt_contradicts_invalid"]),
        ("Verifier valid downgraded to D by Moltsets (suppress)", delta["molt_downgrades_valid"]),
        ("F on a verifier-valid address (unproven, not bad)", f_on_valid),
        ("Job changes flagged (current company differs)", moved),
        ("Rows with a LinkedIn URL after the run", pct(li, n)),
        ("Second-pass rows / accepted same-domain A/B", f"{sp_rows} / {sp_ok}"),
        ("API calls in this project's ledger", calls),
        ("Phone tokens spent (1 per mobile hit)", phone_hits),
    ]

    statuses = [s for s in VERIFIER_STATUSES if (v["verifier_status"] == s).any()]
    gcols = [g for g in ["A", "B", "C", "D", "F", "not_found"] if vgrades.get(g)]
    matrix = [["verifier \\ Moltsets"] + gcols + ["Total"]]
    for s in statuses:
        sub = v[v["verifier_status"] == s]
        oc = Counter(outcome(g) for g in sub["grade"].replace("-", ""))
        matrix.append([s] + [oc.get(g, 0) for g in gcols] + [len(sub)])
    matrix.append(["Total"] + [vgrades.get(g, 0) for g in gcols] + [nv])

    pools = [p for p in sorted(set(df["pool"])) if p]
    pool_tbl = []
    if pools:
        pools = [p for p in pools if "DROP" not in p] + [p for p in pools if "DROP" in p]
        pool_tbl = [["Pool", "Rows", "A/B", "A/B %", "C", "D", "F", "Not found", "Corrected", "Recovered",
                     "Downgraded to D", "Job changes", "LinkedIn URL"]]
        for p in pools:
            sub = df[df["pool"] == p]
            oc = Counter(outcome(g) for g in sub["grade"].replace("-", ""))
            pab = oc["A"] + oc["B"]
            pool_tbl.append([p, len(sub), pab, f"{100 * pab / len(sub):.1f}%" if len(sub) else "0%", oc["C"], oc["D"],
                             oc["F"], oc["not_found"], int((sub["corrected"] == "yes").sum()),
                             int((sub["delta_class"] == "molt_recovers_invalid").sum()),
                             int((sub["delta_class"] == "molt_downgrades_valid").sum()),
                             int((sub["still_at_company"] == "moved").sum()),
                             int(((sub["linkedin_url"] != "") | (sub["molt_linkedin"] != "")).sum())])

    delta_tbl = [["Delta class", "Rows", "Meaning"]] + [[k, delta.get(k, 0), meaning] for k, meaning in DELTA_LEGEND]

    values, bold, cell_colors = [], [], {}
    values.append([f"VERIFIER VS MOLTSETS: {n} rows, {nv} with a verifier verdict", "", ""])
    bold.append(0)
    values.append(["The verifier answers whether the mailbox accepts mail. Moltsets answers whether anyone has been seen "
                   "using the address, and where the person works today. The value is in the disagreements.", "", ""])
    values.append([""])
    values.append(["RECEIPTS", "", ""]); bold.append(len(values) - 1)
    for k, val in kpis:
        values.append([k, str(val)])
    values.append([""])
    values.append(["VERIFIER STATUS x MOLTSETS OUTCOME", "", ""]); bold.append(len(values) - 1)
    hdr = len(values)
    for i, row in enumerate(matrix):
        values.append([str(x) for x in row])
        if i == 0:
            bold.append(len(values) - 1)
            for j, g in enumerate(row[1:-1], start=1):
                cell_colors[(hdr, j)] = GRADE_COLOR.get(g, SE.GREY_LT)
        else:
            cell_colors[(len(values) - 1, 0)] = VERIFIER_COLOR.get(row[0], SE.GREY_LT)
    if pool_tbl:
        values.append([""])
        values.append(["PER POOL (your list's sending pools, if it had them)", "", ""]); bold.append(len(values) - 1)
        for i, row in enumerate(pool_tbl):
            values.append([str(x) for x in row])
            if i == 0:
                bold.append(len(values) - 1)
    values.append([""])
    values.append(["DELTA CLASSES (the Delta column on the Disagreements and All Contacts tabs)", "", ""]); bold.append(len(values) - 1)
    for i, row in enumerate(delta_tbl):
        values.append([str(x) for x in row])
        if i == 0:
            bold.append(len(values) - 1)
        else:
            cell_colors[(len(values) - 1, 0)] = DELTA_COLOR.get(row[0], SE.GREY_LT)
    values.append([""])
    values.append(["HOW TO READ IT", "", ""]); bold.append(len(values) - 1)
    values.append(["Agree rows go first: two vendors, one address, observed engagement on top of an SMTP pass.", "", ""])
    values.append(["Corrected and recovered rows go back into the list under the Moltsets address. Re-probe them with your verifier before sending; they have never been SMTP-checked.", "", ""])
    values.append(["Catch-all rows graded A/B have been seen in use. The verifier could not tell you that. Graduating them is your call.", "", ""])
    values.append(["Contradictions (verifier hard-fail, Moltsets A/B on the same address) are a review pile, not a send pile.", "", ""])
    values.append(["F is unproven, not bad. Not in the graph is a coverage gap, not a verdict. The verifier's word stands on those rows.", "", ""])
    widths = {0: 520, 1: 120, 2: 120, 3: 110, 4: 90, 5: 90, 6: 110, 7: 110, 8: 110, 9: 120, 10: 120, 11: 110, 12: 110}
    return {"title": "Verifier vs Moltsets", "values": values, "widths": widths, "header": False,
            "bold_rows": bold, "cell_colors": cell_colors, "align": "LEFT"}, kpis, delta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--new", action="store_true")
    ap.add_argument("--full-emails", action="store_true")
    ap.add_argument("--redact-names", action="store_true", help="public stills: last names and LinkedIn slugs masked")
    ap.add_argument("--summary-only", action="store_true",
                    help="Dashboard + Verifier vs Moltsets + Grading Model + Usage only, no contact rows (safe to share)")
    ap.add_argument("--title", default="Moltsets Reachability Sheet")
    ap.add_argument("--share", default="none", choices=["none", "anyone_reader"])
    args = ap.parse_args()
    url_file = SUMMARY_URL_FILE if args.summary_only else URL_FILE

    con = sqlite3.connect(DB)
    cur = con.execute("SELECT * FROM contacts ORDER BY composite_score DESC, company")
    cols = [d[0] for d in cur.description]
    df = pd.DataFrame([dict(zip(cols, r)) for r in cur.fetchall()], columns=cols)
    if df.empty:
        sys.exit("no contacts. run init_db.py and grade.py first (or import_graded.py).")
    for c in ("molt_current_company", "molt_current_domain", "employment_source", "employment_agree", "verifier_status",
              "verifier_sub_status", "pool", "mx_provider", "delta_class", "corrected", "second_pass_endpoint",
              "molt_other_email_domain", "molt_other_email_grade", "molt_linkedin", "mobile_phone", "second_pass",
              "second_pass_decision", "molt_route", "still_at_company", "linkedin_url", "grade", "tier", "route"):
        if c not in df.columns:
            df[c] = ""
    for c in df.columns:
        df[c] = df[c].fillna("").astype(str)
    df["full_name"] = (df["first_name"].str.strip() + " " + df["last_name"].str.strip()).str.strip()
    df["grade"] = df["grade"].replace("", "-")
    df["still_at_company"] = df["still_at_company"].replace("", "unknown")
    df["action"] = df["tier"].map(lambda t: TIER_ACTION.get(t, ""))
    has_verifier = bool((df["verifier_status"] != "").any())
    has_pool = bool((df["pool"] != "").any())
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
           FROM moltsets_api_log GROUP BY endpoint ORDER BY 2 DESC""").fetchall() \
        if con.execute("SELECT name FROM sqlite_master WHERE name='moltsets_api_log'").fetchone() else []
    con.close()
    gs = json.loads(GRADE_SUMMARY.read_text()) if GRADE_SUMMARY.exists() else {}
    stats = gs.get("stats", {})

    n = len(df)
    grades = Counter(df["grade"])
    tiers = Counter(df["tier"])
    routes = Counter(df["route"])
    still = Counter(df["still_at_company"])
    graded = int((df["grade"] != "-").sum())
    sendable = tiers.get("T1_send", 0) + tiers.get("T1_send_corrected", 0)
    rel_calls, rel_hit = stats.get("rel_calls", 0), stats.get("rel_hit", 0)
    sp_endpoints = sorted({e for e in df["second_pass_endpoint"] if e}) or ["search_business_profile_by_name"]

    entries = [
        {"kind": "section", "label": "THE LIST"},
        {"kind": "kpi", "label": "Contacts loaded", "value": str(n)},
        {"kind": "kpi", "label": "Graded by Moltsets (any grade)", "value": pct(graded, n)},
        {"kind": "kpi", "label": "Send ready (A/B, same domain)", "value": pct(sendable, n)},
        {"kind": "kpi", "label": "  of which recovered by the second pass",
         "value": str(int((df["molt_route"].isin(["search_people", "search_business_profile_by_name"]) & df["tier"].isin(["T1_send", "T1_send_corrected"])).sum()))},
        {"kind": "kpi", "label": "Send low volume (C catch-all)", "value": str(tiers.get("T2_catchall", 0))},
        {"kind": "kpi", "label": "Never email (D), routed to LinkedIn", "value": str(tiers.get("SUPPRESS", 0))},
        {"kind": "kpi", "label": "Unproven after all passes (F or not in the graph)", "value": str(tiers.get("HOLD_not_found", 0))},
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

    vtab, vkpis, delta = (None, [], Counter())
    if has_verifier:
        vtab, vkpis, delta = verifier_tables(df, usage)
        disagree = sum(c for k, c in delta.items() if k not in AGREEMENT_CLASSES)
        entries += [{"kind": "blank"}, {"kind": "section", "label": "VERIFIER AGREEMENT (your list came in with a verdict per row)"}]
        for label, val in vkpis[6:13]:
            entries.append({"kind": "kpi", "label": f"  {label}", "value": str(val)})
        entries.append({"kind": "kpi", "label": "  Rows where the two vendors disagree (see Disagreements tab)", "value": pct(disagree, n)})

    entries += [{"kind": "blank"}, {"kind": "section", "label": "WATERFALL RECEIPTS (this run)"}]
    if rel_calls:
        entries.append({"kind": "kpi", "label": "reverse_email_lookup hit rate", "value": pct(rel_hit, rel_calls)})
        entries.append({"kind": "kpi", "label": "  404 = not in graph (free)", "value": str(stats.get("rel_404", 0))})
    if stats.get("sp_calls"):
        entries.append({"kind": "kpi", "label": f"second pass: {', '.join(sp_endpoints)} calls", "value": str(stats["sp_calls"])})
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
    if has_verifier:
        entries.append({"kind": "bullet", "label": "Delta = how Moltsets moved the row against your verifier: agree, corrected address, catch-all graded, drop recovered, valid downgraded to D, F on valid. Legend on the Verifier vs Moltsets tab."})

    base_cols = ["rank", "composite_score", "grade", "tier", "route", "full_name", "title", "persona",
                 "company", "domain", "email", "molt_email", "grade_validated_at", "still_at_company",
                 "employment_agree", "molt_current_company", "apollo_current_company", "linkedin_url",
                 "mobile_phone", "action"]
    if has_verifier:
        base_cols[5:5] = ["verifier_status", "delta_class"] + (["pool"] if has_pool else [])
    widths = {"full_name": 170, "title": 220, "company": 160, "domain": 150, "email": 200,
              "molt_email": 200, "grade_validated_at": 120, "apollo_current_company": 160,
              "molt_current_company": 160, "employment_agree": 110, "verifier_status": 110, "delta_class": 210, "pool": 70,
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
        {"col": "verifier_status", "type": "map", "map": VERIFIER_COLOR},
        {"col": "delta_class", "type": "map", "map": DELTA_COLOR},
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
    if has_verifier:
        dis = df[~df["delta_class"].isin(AGREEMENT_CLASSES)].copy()
        dis["_o"] = dis["delta_class"].map(lambda k: DELTA_ORDER.index(k) if k in DELTA_ORDER else 99)
        dis = dis.sort_values(["_o", "composite_score"], ascending=[True, False]).drop(columns="_o")
        if len(dis):
            tabs.append(tab("Disagreements", dis))
    tabs.append(tab("All Contacts", df))
    if args.summary_only:
        tabs = []

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
    if not usage:
        usage_tab.append(["(no calls in this database's ledger: rows were imported already graded)", "", "", "", "", ""])
    usage_tab += [["", "", "", "", "", ""],
                  ["A 404 costs nothing and consumes no record. Only data-bearing calls count against the 5h pools.", "", "", "", "", ""],
                  [f"records_remaining_5h after run: {gs.get('records_remaining_5h')}   phone tokens: {gs.get('phone_tokens_remaining')}", "", "", "", "", ""]]

    if has_verifier:
        disagree = sum(c for k, c in delta.items() if k not in AGREEMENT_CLASSES)
        sub = (f"{n} contacts, {sendable} send ready, {delta.get('agree', 0)} where the verifier and Moltsets agree on the same address, "
               f"{disagree} where they do not | the verifier asks whether the mailbox accepts mail, Moltsets asks whether anyone has used it "
               f"and where the person works today | Built with the Clearbox GTM OS - clearbox.to")
    else:
        sub = (f"{n} contacts, {sendable} send ready, {routes.get('linkedin', 0) + routes.get('linkedin_then_phone', 0)} rows routed to LinkedIn instead of deleted "
               f"| the LinkedIn URL confirms the person, Moltsets grades the address, the sheet picks the channel "
               f"| Built with the Clearbox GTM OS - clearbox.to")

    raw_tabs = []
    if vtab:
        raw_tabs.append(vtab)
    raw_tabs += [{"title": "Grading Model", "values": model, "widths": {0: 220, 1: 520, 2: 110}},
                 {"title": "Moltsets Usage", "values": usage_tab, "widths": {0: 260, 1: 80, 2: 80, 3: 90, 4: 70, 5: 120}}]

    config = {
        "title": args.title + (" (summary)" if args.summary_only and "summary" not in args.title.lower() else ""),
        "key": None if args.new else stored_key(url_file),
        "share": None if args.share == "none" else args.share,
        "dashboard": {"title": "Dashboard",
                      "subtitle": {"title": "REACHABILITY: RELEVANCE x TIMING x A GRADED ADDRESS" + (" x YOUR VERIFIER" if has_verifier else ""),
                                   "sub": sub},
                      "entries": entries},
        "tabs": tabs,
        "raw_tabs": raw_tabs,
    }
    url, titles = SE.build(config)
    url_file.parent.mkdir(parents=True, exist_ok=True)
    url_file.write_text(url + "\n")
    print("SHEET:", url)
    print("tabs:", titles)


if __name__ == "__main__":
    main()
