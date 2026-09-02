#!/usr/bin/env python3
"""import_graded.py -- bring rows that were graded somewhere else into this starter's database, so
score.py and build_sheet.py run unchanged on them.

Use it when the grading already happened (a bigger campaign script, an older run, a colleague's
export) and you want the dashboard, the routing tabs, and the Verifier vs Moltsets comparison
without spending another record. Header names are matched case-insensitively through aliases:

  identity   first_name, last_name (or full_name), title, company, domain, email, linkedin_url, seniority
  verifier   verifier_status | zb_status | zerobounce_status | verification_status, verifier_sub_status, pool, mx_provider
  moltsets   grade | moltsets_grade | risk_score, molt_email | moltsets_email | confirmed_email, validated_at,
             molt_title, molt_company, molt_company_domain, still_at_company, linkedin_url,
             second_pass, sp_decision | second_pass_decision, sp_endpoint | second_pass_endpoint,
             corrected, other_email_domain, other_email_grade, rel_http | molt_http, graded_at
  routing    verdict, tier, route, delta_class   (recomputed with lib/reachability.py when missing)

  python3 import_graded.py results.csv                       # into data/reachability.db
  REACHABILITY_DB=data/tenk.db python3 import_graded.py results.csv --replace
  python3 score.py && python3 build_sheet.py --new --redact-names

Nothing here calls the API. The usage tab stays empty unless the ledger already has rows.
"""
import argparse
import csv
import json
import os
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from init_db import SCHEMA, _domain  # noqa: E402
from lib.reachability import classify, delta_class, norm_verifier_status  # noqa: E402

HERE = Path(__file__).resolve().parent
DB = Path(os.environ.get("REACHABILITY_DB") or HERE / "data" / "reachability.db")

ALIASES = {
    "first_name": ["first_name", "first name", "firstname", "first"],
    "last_name": ["last_name", "last name", "lastname", "last"],
    "full_name": ["full_name", "name", "full name", "contact"],
    "title": ["title", "job title", "job_title"],
    "company": ["company", "company name", "company_name", "organization"],
    "domain": ["domain", "company_domain", "company domain", "website"],
    "email": ["email", "work email", "business_email", "list_email"],
    "linkedin_url": ["linkedin_url", "linkedin", "person linkedin url", "linkedin url"],
    "seniority": ["seniority"],
    "verifier_status": ["verifier_status", "zb_status", "zerobounce_status", "verification_status", "verifier",
                        "neverbounce_result", "mv_result", "bounce_status"],
    "verifier_sub_status": ["verifier_sub_status", "zb_sub_status", "sub_status"],
    "pool": ["pool", "sending_pool", "send_pool"],
    "mx_provider": ["mx_provider", "mx", "email_provider", "mail_host", "provider"],
    "grade": ["grade", "moltsets_grade", "risk_score", "email_grade"],
    "molt_email": ["molt_email", "moltsets_email", "confirmed_email", "graded_email"],
    "grade_validated_at": ["grade_validated_at", "validated_at", "confirmed_at"],
    "molt_title": ["molt_title", "moltsets_title"],
    "molt_company": ["molt_company", "moltsets_company", "current_company"],
    "molt_company_domain": ["molt_company_domain", "moltsets_company_domain", "current_company_domain"],
    "molt_linkedin": ["molt_linkedin", "moltsets_linkedin"],
    "still_at_company": ["still_at_company", "still_there", "employment"],
    "second_pass": ["second_pass", "2nd_pass"],
    "second_pass_decision": ["second_pass_decision", "sp_decision", "2nd_pass_result"],
    "second_pass_endpoint": ["second_pass_endpoint", "sp_endpoint", "2nd_pass_endpoint"],
    "corrected": ["corrected"],
    "molt_other_email_domain": ["molt_other_email_domain", "other_email_domain"],
    "molt_other_email_grade": ["molt_other_email_grade", "other_email_grade"],
    "molt_http": ["molt_http", "rel_http", "http"],
    "verdict": ["verdict"],
    "tier": ["tier"],
    "route": ["route"],
    "delta_class": ["delta_class", "delta"],
    "graded_at": ["graded_at"],
    "source": ["source"],
}


def pick(row: dict, key: str) -> str:
    lower = {k.strip().lower(): v for k, v in row.items() if k}
    for a in ALIASES[key]:
        if a in lower and lower[a] is not None:
            return str(lower[a]).strip()
    return ""


def split_name(full: str) -> tuple[str, str]:
    parts = (full or "").strip().split()
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--replace", action="store_true", help="empty the contacts table first")
    ap.add_argument("--source", default="imported", help="source label written on every row")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    con.execute("PRAGMA journal_mode = WAL;")
    con.executescript(SCHEMA)
    have = {r[1] for r in con.execute("PRAGMA table_info(contacts)")}
    for col in ("verifier_status", "verifier_sub_status", "verifier_raw", "pool", "mx_provider", "second_pass_endpoint",
                "corrected", "molt_other_email_domain", "molt_other_email_grade", "delta_class"):
        if col not in have:
            con.execute(f"ALTER TABLE contacts ADD COLUMN {col} TEXT")
    if args.replace:
        con.execute("DELETE FROM contacts")

    rows = list(csv.DictReader(Path(args.csv).open(encoding="utf-8-sig")))
    if args.limit:
        rows = rows[: args.limit]
    stats = Counter()
    inserted = 0
    for r in rows:
        first, last = pick(r, "first_name"), pick(r, "last_name")
        if not first and not last:
            first, last = split_name(pick(r, "full_name"))
        email = pick(r, "email").lower()
        li = pick(r, "linkedin_url").split("?")[0].rstrip("/")
        molt_li = pick(r, "molt_linkedin")
        if not email and not li:
            stats["skipped_no_key"] += 1
            continue
        domain = _domain(pick(r, "domain")) or (email.split("@")[-1] if "@" in email else "")
        vraw = pick(r, "verifier_status")
        vstat = norm_verifier_status(vraw)
        grade = pick(r, "grade").upper()[:1]
        if grade not in ("A", "B", "C", "D", "F"):
            grade = ""
        molt_email = pick(r, "molt_email").lower()
        still = (pick(r, "still_at_company") or "unknown").lower()
        second_pass = (pick(r, "second_pass") or "no").lower()
        sp_decision = pick(r, "second_pass_decision")
        corrected = pick(r, "corrected").lower()
        if corrected not in ("yes", "no"):
            corrected = "yes" if (molt_email and email and molt_email != email) else "no"
        verdict, tier, route = pick(r, "verdict"), pick(r, "tier"), pick(r, "route")
        if not (verdict and tier and route):
            verdict, tier, route = classify(molt_email or email, grade, domain, has_linkedin=bool(li or molt_li),
                                            second_pass_done=(second_pass == "yes"), still_at_company=still)
            if corrected == "yes" and tier == "T1_send":
                verdict, tier = "corrected", "T1_send_corrected"
            if route == "second_pass":
                route = "linkedin" if (li or molt_li) else "hold"
            stats["routing_recomputed"] += 1
        dc = pick(r, "delta_class")
        if not dc and vstat:
            dc = delta_class(vstat, grade, pick(r, "molt_http"), sp_decision, corrected, still)
            stats["delta_recomputed"] += 1
        http = pick(r, "molt_http")
        sp_endpoint = pick(r, "second_pass_endpoint")
        if sp_decision == "accept_same_domain" and sp_endpoint:
            molt_route = sp_endpoint                      # the dashboard counts second-pass recoveries off this
        elif http == "200":
            molt_route = "reverse_email_lookup"
        else:
            molt_route = "imported"
        cur = con.execute(
            "INSERT OR IGNORE INTO contacts (first_name,last_name,title,company,domain,email,linkedin_url,seniority,source,"
            "verifier_status,verifier_sub_status,verifier_raw,pool,mx_provider,"
            "molt_http,molt_email,grade,grade_validated_at,molt_title,molt_company,molt_company_domain,molt_linkedin,"
            "still_at_company,second_pass,second_pass_decision,second_pass_endpoint,corrected,"
            "molt_other_email_domain,molt_other_email_grade,verdict,tier,route,delta_class,graded_at,molt_route) "
            "VALUES (?,?,?,?,?,?,?,?,?, ?,?,?,?,?, ?,?,?,?,?,?,?,?, ?,?,?,?,?, ?,?,?,?,?,?,?,?)",
            (first, last, pick(r, "title"), pick(r, "company"), domain, email, li or molt_li, pick(r, "seniority"),
             pick(r, "source") or args.source,
             vstat, pick(r, "verifier_sub_status"), vraw, pick(r, "pool").upper(), pick(r, "mx_provider").lower(),
             http, molt_email, grade, pick(r, "grade_validated_at"), pick(r, "molt_title"), pick(r, "molt_company"),
             _domain(pick(r, "molt_company_domain")), molt_li,
             still, second_pass, sp_decision, sp_endpoint, corrected,
             pick(r, "molt_other_email_domain"), pick(r, "molt_other_email_grade"), verdict, tier, route, dc,
             pick(r, "graded_at") or now(), molt_route),
        )
        inserted += cur.rowcount
        if http == "200":
            stats["rel_hit"] += 1
        elif http == "404":
            stats["rel_404"] += 1
        if http in ("200", "404"):
            stats["rel_calls"] += 1
        if second_pass == "yes":
            stats["sp_calls"] += 1
            if sp_decision == "accept_same_domain":
                stats["sp_recovered"] += 1
        if li or molt_li:
            stats["linkedin_filled"] += 1
        if still == "moved":
            stats["job_change_flags"] += 1
        if dc:
            stats[f"delta_{dc}"] += 1
    con.commit()

    total = con.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]
    with_v = con.execute("SELECT COUNT(*) FROM contacts WHERE COALESCE(verifier_status,'')!=''").fetchone()[0]
    grades = Counter(g or "-" for (g,) in con.execute("SELECT grade FROM contacts"))
    con.close()

    # the dashboard reads this for the waterfall receipts; imported runs get counts, not API stats
    stem = "" if DB == HERE / "data" / "reachability.db" else DB.stem + "_"
    summary = DB.parent / f"{stem}grade_summary.json"
    summary.write_text(json.dumps({"ran_at": now(), "employment": "imported", "imported_from": str(args.csv),
                                   "stats": dict(stats), "account": {}, "records_remaining_5h": None,
                                   "phone_tokens_remaining": None}, indent=2))
    print(f"imported {inserted} of {len(rows)} rows into {DB} ({total} total, {with_v} with a verifier verdict)")
    print("grades:", dict(sorted(grades.items())))
    print("stats:", dict(stats))
    print(f"wrote {summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
