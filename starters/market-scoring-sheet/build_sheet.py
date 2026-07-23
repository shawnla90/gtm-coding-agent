#!/usr/bin/env python3
"""build_sheet.py — render the scored market as a color-coded Google Sheet (the proof).

Thin builder over the vendored proof-sheet engine (lib/sheet_engine.py): a score gradient
(red to green), a tier color map, a dashboard tab with the funnel KPIs, and a scoring-model
tab. Rebuilds IN PLACE by sheet-id so the link never changes on a re-run.

Needs a Google OAuth token at ~/.config/gspread/token.json — run setup_oauth.py once first.

  python3 build_sheet.py              # rebuild the stored sheet (data/sheet_url.txt) or create new
  python3 build_sheet.py <sheet_id>   # rebuild a specific sheet
"""
import re
import sqlite3
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.sheet_engine import build, GREEN, BLUE, YELLOW, GREY  # type: ignore

HERE = Path(__file__).resolve().parent
DB = HERE / "data" / "market.db"
URL_FILE = HERE / "data" / "sheet_url.txt"

TIER = {"A": GREEN, "B": BLUE, "C": YELLOW, "D": GREY}
REACH = {"reachable": GREEN, "no email": GREY}


def stored_key():
    if URL_FILE.exists():
        m = re.search(r"/d/([A-Za-z0-9_-]+)", URL_FILE.read_text())
        return m.group(1) if m else None
    return None


def main():
    key = sys.argv[1] if len(sys.argv) > 1 else stored_key()
    con = sqlite3.connect(DB)
    cur = con.execute(
        "SELECT score, tier, reachability, name, title, company, domain, industry, "
        "employees, email, fit_reason FROM contacts ORDER BY score DESC, company"
    )
    cols = [d[0] for d in cur.description]
    df = pd.DataFrame([dict(zip(cols, r)) for r in cur.fetchall()], columns=cols)
    for c in df.columns:
        df[c] = df[c].fillna("").astype(str)

    total = len(df)
    a_tier = int((df.tier == "A").sum())
    b_tier = int((df.tier == "B").sum())
    reach = int((df.reachability == "reachable").sum())
    con.close()

    dash = {
        "title": "Dashboard",
        "subtitle": {"title": "MARKET SCORING (sample build)",
                     "sub": f"{total} accounts scored 1-5 · {a_tier} A-tier · {reach} reachable"},
        "entries": [
            {"kind": "section", "label": "THE MARKET"},
            {"kind": "kpi", "label": "Accounts scored", "value": str(total)},
            {"kind": "kpi", "label": "A-tier (score 5)", "value": str(a_tier)},
            {"kind": "kpi", "label": "B-tier (score 4)", "value": str(b_tier)},
            {"kind": "kpi", "label": "Reachable (has email)", "value": str(reach)},
            {"kind": "blank", "label": ""},
            {"kind": "section", "label": "HOW TO READ IT"},
            {"kind": "bullet", "label": "Green 4-5 is the spear list: top fit, reachable, worth a personal touch."},
            {"kind": "bullet", "label": "Yellow 3 is the net list: real fit, run them in volume."},
            {"kind": "bullet", "label": "Red 1-2 is logged, never deleted, re-scored on the next run."},
        ],
    }

    tabs = [{
        "title": f"Scored Market ({total})",
        "df": df,
        "cols": ["score", "tier", "reachability", "name", "title", "company", "domain",
                 "industry", "employees", "email", "fit_reason"],
        "widths": {"name": 150, "title": 180, "company": 160, "domain": 175,
                   "email": 210, "fit_reason": 330, "industry": 140},
        "numeric": ["score", "employees"],
        "cf": [{"col": "score", "type": "grad", "stops": (1, 3, 5)},
               {"col": "tier", "type": "map", "map": TIER},
               {"col": "reachability", "type": "map", "map": REACH}],
    }]

    scoring = [
        ["SCORING MODEL: score.py, edit the maps to match your ICP", ""],
        ["Dimension", "Points"],
        ["industry_fit (0-40)", "software/saas/fintech=40 · marketing/agency/consulting=28 · vc/pe=16 · else=8"],
        ["persona_fit (0-35)", "founder/C-level/owner/partner=35 · VP/head/director GTM=32 · other VP/dir=24 · non-buyer=10"],
        ["size_fit (0-15)", "11-200=15 · 201-500=11 · 1-10=9 · 500+=7"],
        ["reachability (0-10)", "has email=10 · none=0"],
        ["score 1-5", "80+=5 · 65+=4 · 50+=3 · 35+=2 · else 1"],
        ["tier", "A=5 · B=4 · C=3 · D=1-2"],
    ]
    raw_tabs = [{"title": "Scoring Model", "values": scoring, "widths": {0: 240, 1: 560}}]

    config = {"title": "Market Scoring (sample build)", "key": key, "share": "anyone_reader",
              "dashboard": dash, "tabs": tabs, "raw_tabs": raw_tabs}
    url, titles = build(config)
    URL_FILE.write_text(url + "\n")
    print("SHEET:", url)
    print("tabs:", titles)


if __name__ == "__main__":
    main()
