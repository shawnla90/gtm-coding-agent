#!/usr/bin/env python3
"""score.py — score every contact 1 to 5 on ICP fit, and write a one-line fit_reason.

Transparent rules, no black box: industry fit + buyer persona + company size + reachability,
summed to a 0-100 number and mapped to a 1-5 score and an A-D tier. Edit the maps below to
match your own ICP. The fit_reason is the part a SaaS tool hides and you get to keep.

  python3 score.py
"""
import sqlite3
from pathlib import Path

HERE = Path(__file__).resolve().parent
DB = HERE / "data" / "market.db"

SOFTWARE = ("software", "saas", "fintech", "technology", "tech")
SERVICES = ("marketing", "agency", "consulting", "advertising")
INVEST = ("venture", "vc", "private equity", "pe", "capital")

BUYER_HI = ("founder", "ceo", "chief", "cro", "cto", "coo", "president",
            "owner", "partner", "principal", "managing director")
BUYER_MD = ("vp", "vice president", "head", "director")
GTM = ("sales", "revenue", "growth", "marketing", "partnership", "gtm", "demand")


def industry_pts(ind):
    i = (ind or "").lower()
    if any(k in i for k in SOFTWARE):
        return 40, "ICP industry (software)"
    if any(k in i for k in SERVICES):
        return 28, "adjacent industry (services)"
    if any(k in i for k in INVEST):
        return 16, "investor (lower fit)"
    return 8, "out-of-ICP industry"


def persona_pts(title):
    t = (title or "").lower()
    if any(k in t for k in BUYER_HI):
        return 35, "exec buyer"
    if any(k in t for k in BUYER_MD):
        if any(k in t for k in GTM):
            return 32, "GTM leader"
        return 24, "VP/director (non-GTM)"
    return 10, "non-buyer persona"


def size_pts(emp):
    if not emp:
        return 6, "unknown size"
    if 11 <= emp <= 200:
        return 15, "right-size (11-200)"
    if 201 <= emp <= 500:
        return 11, "mid-size"
    if 1 <= emp <= 10:
        return 9, "very small"
    return 7, "enterprise"


def main():
    con = sqlite3.connect(DB)
    rows = con.execute("SELECT id, industry, title, employees, email FROM contacts").fetchall()
    for cid, ind, title, emp, email in rows:
        ip, ir = industry_pts(ind)
        pp, pr = persona_pts(title)
        sp, sr = size_pts(emp)
        reachable = bool((email or "").strip())
        reach_label = "reachable" if reachable else "no email"
        rp = 10 if reachable else 0

        total = ip + pp + sp + rp  # 0-100
        score = 5 if total >= 80 else 4 if total >= 65 else 3 if total >= 50 else 2 if total >= 35 else 1
        tier = "A" if score == 5 else "B" if score == 4 else "C" if score == 3 else "D"
        reason = f"{ir}, {pr}, {sr}, {reach_label}"
        con.execute(
            "UPDATE contacts SET score=?, tier=?, reachability=?, fit_reason=? WHERE id=?",
            (score, tier, reach_label, reason, cid),
        )
    con.commit()
    dist = con.execute("SELECT score, COUNT(*) FROM contacts GROUP BY score ORDER BY score DESC").fetchall()
    print("scored:", ", ".join(f"{s} star x{n}" for s, n in dist))
    con.close()


if __name__ == "__main__":
    main()
