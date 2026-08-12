#!/usr/bin/env python3
"""build_sheet.py -- render the scored buying committee as a multi-tab Google Sheet.

Uses the vendored sheet_engine for color-coded output with a dashboard, source list,
ranked buying committee, and scoring model reference. Rebuilds in place so the link
never changes.

  python3 build_sheet.py                 # rebuild stored sheet or create new
  python3 build_sheet.py <sheet_id>      # rebuild a specific sheet
"""
import re
import sqlite3
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.sheet_engine import build, GREEN, GREEN_LT, BLUE, YELLOW, GREY, RED  # type: ignore

HERE = Path(__file__).resolve().parent
DB = HERE / "data" / "apollo.db"
URL_FILE = HERE / "data" / "sheet_url.txt"


def stored_key():
    if URL_FILE.exists():
        m = re.search(r"/d/([A-Za-z0-9_-]+)", URL_FILE.read_text())
        return m.group(1) if m else None
    return None


def main():
    key = sys.argv[1] if len(sys.argv) > 1 else stored_key()
    con = sqlite3.connect(DB)

    # --- Tab 2: Source List ---
    src_cur = con.execute(
        "SELECT company, domain, name, title, persona, source "
        "FROM source_contacts ORDER BY company"
    )
    src_cols = [d[0] for d in src_cur.description]
    src_df = pd.DataFrame([dict(zip(src_cols, r)) for r in src_cur.fetchall()], columns=src_cols)
    for c in src_df.columns:
        src_df[c] = src_df[c].fillna("").astype(str)

    # --- Tab 3: Buying Committee (ranked only) ---
    exp_cur = con.execute(
        "SELECT composite_score, rank, reachability, persona, first_name, last_name, "
        "title, company, domain, title_score, email_status, has_phone, "
        "email, phone, linkedin_url, city "
        "FROM expanded_contacts WHERE rank IS NOT NULL "
        "ORDER BY composite_score DESC, company"
    )
    exp_cols = [d[0] for d in exp_cur.description]
    exp_df = pd.DataFrame([dict(zip(exp_cols, r)) for r in exp_cur.fetchall()], columns=exp_cols)
    for c in exp_df.columns:
        exp_df[c] = exp_df[c].fillna("").astype(str)

    exp_df["full_name"] = (exp_df["first_name"].str.strip() + " " + exp_df["last_name"].str.strip()).str.strip()

    def _obfuscate_email(email):
        if not email or "@" not in email:
            return email
        local, domain = email.rsplit("@", 1)
        if len(local) <= 2:
            return f"{local[0]}***@{domain}"
        return f"{local[0]}***{local[-1]}@{domain}"

    def _obfuscate_phone(phone):
        if not phone:
            return phone
        digits = "".join(c for c in phone if c.isdigit())
        if len(digits) < 4:
            return "***"
        return f"+{digits[:1]}-***-***-{digits[-4:]}"

    exp_df["email"] = exp_df["email"].apply(_obfuscate_email)
    exp_df["phone"] = exp_df["phone"].apply(_obfuscate_phone)

    def _cost(row):
        has_email = row.get("email_status") in ("verified", "available")
        has_phone = row.get("has_phone") == "yes"
        if has_email and has_phone:
            return "$$"
        if has_email or has_phone:
            return "$"
        return "FREE"

    exp_df["cost"] = exp_df.apply(_cost, axis=1)

    # --- KPIs ---
    total_source = len(src_df)
    total_expanded = len(exp_df)
    source_domains = int(con.execute("SELECT COUNT(DISTINCT domain) FROM source_contacts").fetchone()[0])
    t1 = int((exp_df.reachability == "T1").sum()) if len(exp_df) else 0
    t2 = int((exp_df.reachability == "T2").sum()) if len(exp_df) else 0
    t3 = int((exp_df.reachability == "T3").sum()) if len(exp_df) else 0
    t4 = int((exp_df.reachability == "T4").sum()) if len(exp_df) else 0

    persona_sales = int((exp_df.persona == "sales").sum()) if len(exp_df) else 0
    persona_mktg = int((exp_df.persona == "marketing").sum()) if len(exp_df) else 0
    persona_prod = int((exp_df.persona == "product").sum()) if len(exp_df) else 0
    con.close()

    dash = {
        "title": "Dashboard",
        "subtitle": {
            "title": "APOLLO EXPANSION PLAY",
            "sub": (f"{total_source} source contacts across {source_domains} companies "
                    f"-> {total_expanded} ranked buying committee members "
                    f"| Built with the Clearbox GTM OS - clearbox.to"),
        },
        "entries": [
            {"kind": "section", "label": "SOURCE"},
            {"kind": "kpi", "label": "Source contacts", "value": str(total_source)},
            {"kind": "kpi", "label": "Unique companies", "value": str(source_domains)},
            {"kind": "blank", "label": ""},
            {"kind": "section", "label": "EXPANSION"},
            {"kind": "kpi", "label": "Buying committee (ranked)", "value": str(total_expanded)},
            {"kind": "kpi", "label": "T1 (email + phone)", "value": str(t1)},
            {"kind": "kpi", "label": "T2 (email only)", "value": str(t2)},
            {"kind": "kpi", "label": "T3 (catch-all)", "value": str(t3)},
            {"kind": "kpi", "label": "T4 (unavailable)", "value": str(t4)},
            {"kind": "blank", "label": ""},
            {"kind": "section", "label": "PERSONA MIX"},
            {"kind": "kpi", "label": "Sales / Revenue", "value": str(persona_sales)},
            {"kind": "kpi", "label": "Marketing / Growth", "value": str(persona_mktg)},
            {"kind": "kpi", "label": "Product / Engineering", "value": str(persona_prod)},
            {"kind": "blank", "label": ""},
            {"kind": "section", "label": "HOW TO READ IT"},
            {"kind": "bullet", "label": "Green (T1) = verified email + phone. These are your spear list."},
            {"kind": "bullet", "label": "Blue (T2) = email only. Solid for sequences."},
            {"kind": "bullet", "label": "Yellow (T3) = catch-all. Test before sending."},
            {"kind": "bullet", "label": "Grey (T4) = no verified channel yet. LinkedIn first."},
            {"kind": "blank", "label": ""},
            {"kind": "section", "label": "COST GUIDE"},
            {"kind": "bullet", "label": "FREE = names, titles, email/phone availability flags (0 credits)"},
            {"kind": "bullet", "label": "$ = one paid reveal available (email OR phone)"},
            {"kind": "bullet", "label": "$$ = both email + phone available to reveal"},
            {"kind": "bullet", "label": "Score first, reveal the winners. The search is free; the reveal costs credits."},
        ],
    }

    TIER_MAP = {"T1": GREEN, "T2": BLUE, "T3": YELLOW, "T4": GREY}
    PERSONA_MAP = {"sales": GREEN, "marketing": BLUE, "product": "D5A6E6"}
    COST_MAP = {"FREE": GREEN_LT, "$": YELLOW, "$$": "F4A460"}

    source_tab = {
        "title": f"Source List ({total_source})",
        "df": src_df,
        "cols": ["company", "domain", "name", "title", "persona", "source"],
        "widths": {"company": 160, "domain": 160, "name": 140, "title": 240, "persona": 100},
        "cf": [{"col": "persona", "type": "map", "map": PERSONA_MAP}],
    }

    committee_tab = {
        "title": f"Buying Committee ({total_expanded})",
        "df": exp_df,
        "cols": ["rank", "composite_score", "reachability", "cost", "full_name",
                 "title", "persona", "company", "domain",
                 "email", "phone", "linkedin_url", "city", "title_score"],
        "widths": {"full_name": 180, "title": 240, "company": 160, "domain": 160,
                   "city": 120, "cost": 80, "email": 200, "phone": 140,
                   "linkedin_url": 240},
        "numeric": ["composite_score", "rank", "title_score"],
        "cf": [
            {"col": "composite_score", "type": "grad", "stops": (0, 80, 200)},
            {"col": "reachability", "type": "map", "map": TIER_MAP},
            {"col": "persona", "type": "map", "map": PERSONA_MAP},
            {"col": "cost", "type": "map", "map": COST_MAP},
        ],
    }

    scoring_model = [
        ["SCORING MODEL: score.py", ""],
        ["Keyword", "Points (additive)"],
        ["RevOps / Revenue Operations", "100"],
        ["Revenue", "90"],
        ["Growth", "80"],
        ["Go-to-Market / GTM", "75"],
        ["Sales", "60"],
        ["Marketing", "55"],
        ["Product", "50"],
        ["Business Development", "45"],
        ["Chief / CxO (seniority)", "+30"],
        ["VP / Vice President", "+25"],
        ["Head of", "+20"],
        ["Director", "+15"],
        ["Manager", "+5"],
        ["", ""],
        ["REACHABILITY MULTIPLIER", ""],
        ["Tier", "Multiplier"],
        ["T1: verified email + phone", "1.0x"],
        ["T2: verified email only", "0.85x"],
        ["T3: catch-all / guessed", "0.6x"],
        ["T4: unavailable", "0.3x"],
        ["", ""],
        ["EXAMPLE", ""],
        ["VP of Revenue Operations", ""],
        ["  RevOps: 100 + Revenue: 90 + VP: 25 = 215", ""],
        ["  T1 (email + phone): 215 x 1.0 = 215.0", ""],
    ]

    config = {
        "title": "Apollo Expansion Play",
        "key": key,
        "share": "anyone_reader",
        "dashboard": dash,
        "tabs": [source_tab, committee_tab],
        "raw_tabs": [{"title": "Scoring Model", "values": scoring_model, "widths": {0: 300, 1: 200}}],
    }

    url, titles = build(config)
    URL_FILE.parent.mkdir(parents=True, exist_ok=True)
    URL_FILE.write_text(url + "\n")
    print("SHEET:", url)
    print("tabs:", titles)


if __name__ == "__main__":
    main()
