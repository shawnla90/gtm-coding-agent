#!/usr/bin/env python3
"""grade.py -- the reachability waterfall. Confirm the person is still there; grade the address.

For every contact not yet graded:
  0. employment check (--employment moltsets|apollo|both, default moltsets)
       moltsets: reverse_linkedin_lookup on the LinkedIn URL -> current company + title, and the
                 graded business email when the graph has one. The graph is keyed far better on the
                 URL than on the address, so this is also the first grading pass.
       apollo:   Apollo people/match on the LinkedIn URL -> current company.
       both:     run both, store both, and record whether they agree.
     If the current company disagrees with the listed one, the row is a job change: hold, re-source,
     skip the stale email.
  1. reverse_email_lookup on the business email (when step 0 did not already grade it).
  2. (--second-pass) on 404 / F: search_business_profile_by_name {name, company: DOMAIN} (default;
     --second-pass-endpoint people swaps in search_people, which went 0 for 181 and 0 for 54 on two
     lists). Accept only a same-domain grade A/B result whose name matches. A different domain is a
     different person until proven otherwise.
  3. LinkedIn-only rows with no email after all that: linkedin_to_best_email.
  4. (--phones N) dead-email rows only: linkedin_to_mobile_phone, one phone token per HIT, capped.

If the list carried a verifier verdict (init_db.py detects zb_status / verifier_status), every row also
gets a delta class: how Moltsets moved it relative to the verifier (agree, corrects the address,
recovers a drop, upgrades a catch-all, downgrades a valid to D, ...). The value is in the disagreements.

Every call is logged to data/reachability.db moltsets_api_log and every row is committed as it
finishes: a crash costs one record, a rerun never re-spends. Floor guard on records_remaining_5h.

  python3 grade.py                                    # moltsets employment check + email grade
  python3 grade.py --employment both --second-pass    # compare Apollo and Moltsets on employment
  python3 grade.py --phones 10                        # also buy up to 10 mobiles for dead-email rows
  python3 grade.py --limit 20 --dry-run               # show what would run, spend nothing
"""
import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import moltsets_client as M  # noqa: E402
from lib import apollo_client as A  # noqa: E402
from lib.reachability import (classify, combine_employment, companies_match, delta_class,  # noqa: E402
                              profile_decision, second_pass_decision)

HERE = Path(__file__).resolve().parent
DB = Path(os.environ.get("REACHABILITY_DB") or HERE / "data" / "reachability.db")

NEW_COLUMNS = {"molt_current_company": "TEXT", "molt_current_domain": "TEXT", "molt_current_title": "TEXT",
               "employment_source": "TEXT", "employment_agree": "TEXT",
               # v0.12.0: verifier column + delta classes + business-profile second pass
               "verifier_status": "TEXT", "verifier_sub_status": "TEXT", "verifier_raw": "TEXT", "pool": "TEXT",
               "mx_provider": "TEXT", "second_pass_endpoint": "TEXT", "corrected": "TEXT",
               "molt_other_email_domain": "TEXT", "molt_other_email_grade": "TEXT", "delta_class": "TEXT"}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def redact(email):
    if not email or "@" not in email:
        return email or "-"
    local, d = email.rsplit("@", 1)
    return f"{local[:1]}***@{d}"


def migrate(con):
    have = {r[1] for r in con.execute("PRAGMA table_info(contacts)")}
    for col, typ in NEW_COLUMNS.items():
        if col not in have:
            con.execute(f"ALTER TABLE contacts ADD COLUMN {col} {typ}")
    con.commit()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--employment", choices=["moltsets", "apollo", "both", "none"], default=None,
                    help="who answers 'still at the company?' (default moltsets)")
    ap.add_argument("--apollo", action="store_true", help="shorthand for --employment apollo")
    ap.add_argument("--second-pass", action="store_true", help="name + domain search on 404 / F (business-profile endpoint)")
    ap.add_argument("--second-pass-endpoint", choices=["profile", "people"], default="profile",
                    help="profile = search_business_profile_by_name (default, recovers); people = search_people (0 for 181 on the last list)")
    ap.add_argument("--phones", type=int, default=0, help="buy up to N mobile numbers for dead-email rows")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--redo", action="store_true", help="re-grade rows that already have a verdict")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--note", default="reachability", help="tag written to the api log")
    args = ap.parse_args()
    employment = args.employment or ("apollo" if args.apollo else "moltsets")
    use_apollo = employment in ("apollo", "both")
    use_molt_li = employment in ("moltsets", "both")

    con = sqlite3.connect(DB, timeout=30)
    con.execute("PRAGMA journal_mode = WAL;")
    M.ensure_log(con)
    migrate(con)
    con.row_factory = sqlite3.Row

    where = "1=1" if args.redo else "verdict IS NULL"
    rows = con.execute(f"SELECT * FROM contacts WHERE {where} ORDER BY id").fetchall()
    if args.limit:
        rows = rows[: args.limit]
    print(f"{len(rows)} contacts to grade (employment={employment}, second_pass={'on' if args.second_pass else 'off'}, phones={args.phones})")
    if args.dry_run:
        for r in rows[:25]:
            print(f"  would grade: {r['first_name']} {(r['last_name'] or '')[:1]}. @ {r['domain']}  {redact(r['email'])}")
        return 0
    if not M.get_key():
        sys.exit("MOLTSETS_API_KEY not set: export it, add it to .env, or point SECRETS_DB at your vault")
    if use_apollo and not A.get_key():
        sys.exit("APOLLO_API_KEY not set but --employment includes apollo")

    snap = M.account_snapshot()
    print(f"plan={snap.get('plan')} pools={json.dumps(snap.get('pools'))} phone_tokens={snap.get('phone_tokens_remaining')}")
    budget = M.Budget()
    budget.phone_tokens = snap.get("phone_tokens_remaining")

    stats = {"apollo_checked": 0, "apollo_moved": 0, "rll_calls": 0, "rll_hit": 0, "rll_graded": 0, "rll_moved": 0,
             "employment_agree": 0, "employment_disagree": 0,
             "rel_calls": 0, "rel_hit": 0, "rel_404": 0, "sp_calls": 0, "sp_recovered": 0,
             "li_email_calls": 0, "li_email_hit": 0, "phone_calls": 0, "phone_hit": 0, "floor_stops": 0}
    phones_left = args.phones

    for i, r in enumerate(rows, 1):
        cid, email, li = r["id"], (r["email"] or "").lower(), r["linkedin_url"] or ""
        upd = {"graded_at": now(), "second_pass": "no", "second_pass_decision": None, "candidates_json": None}
        still_a = still_m = "unknown"
        grade, molt_email, validated, route_used, http = "", "", "", "none", ""
        molt_title = molt_company = molt_cdom = molt_li = ""

        if not budget.records_ok():
            stats["floor_stops"] += 1
            print(f"[{i}/{len(rows)}] ! floor guard: records_remaining_5h={budget.records_5h}. stopping.")
            break

        # 0a. Apollo employment check
        if use_apollo and li:
            ap_res = A.people_match(li)
            stats["apollo_checked"] += 1
            if ap_res.get("http") == 200 and (ap_res.get("company") or ap_res.get("company_domain")):
                still_a = companies_match(r["company"], ap_res.get("company"), r["domain"], ap_res.get("company_domain"))
                upd.update(apollo_checked_at=now(), apollo_current_company=ap_res.get("company"),
                           apollo_current_domain=ap_res.get("company_domain"), apollo_current_title=ap_res.get("title"))
                if still_a == "moved":
                    stats["apollo_moved"] += 1
            else:
                upd.update(apollo_checked_at=now())

        # 0b. Moltsets employment check (and first grading pass) on the LinkedIn URL
        if use_molt_li and li:
            body = {"linkedin_url": li}
            st, res, md = M.call("reverse_linkedin_lookup", body)
            budget.absorb(M.log_call(con, "reverse_linkedin_lookup", body, st, res, md, note=args.note))
            stats["rll_calls"] += 1
            if st == 200 and res:
                stats["rll_hit"] += 1
                cname, cdom = M.company_of(res)
                still_m = companies_match(r["company"], cname, r["domain"], cdom) if (cname or cdom) else "unknown"
                upd.update(molt_current_company=cname, molt_current_domain=cdom, molt_current_title=res.get("title") or "")
                if still_m == "moved":
                    stats["rll_moved"] += 1
                if M.email_of(res) and M.grade_of(res):
                    stats["rll_graded"] += 1
                    grade, molt_email, validated = M.grade_of(res), M.email_of(res), M.validated_at_of(res)
                    molt_title, molt_company, molt_cdom, molt_li = res.get("title") or "", cname, cdom, M.linkedin_of(res) or li
                    route_used, http = "reverse_linkedin_lookup", str(st)
            M.pause()

        still, emp_source, emp_agree = combine_employment(still_a, still_m)
        if emp_agree == "yes":
            stats["employment_agree"] += 1
        elif emp_agree == "no":
            stats["employment_disagree"] += 1
        upd.update(still_at_company=still, employment_source=emp_source, employment_agree=emp_agree)

        if still != "moved":
            # 1. reverse_email_lookup on the business email (unless the URL pass already graded it)
            if email and M.dom(email) not in M.FREEMAIL and not grade and budget.records_ok():
                body = {"email": email}
                st, res, md = M.call("reverse_email_lookup", body)
                budget.absorb(M.log_call(con, "reverse_email_lookup", body, st, res, md, note=args.note))
                stats["rel_calls"] += 1
                http, route_used = str(st), "reverse_email_lookup"
                if st == 200 and res:
                    stats["rel_hit"] += 1
                    grade, molt_email, validated = M.grade_of(res), M.email_of(res), M.validated_at_of(res)
                    molt_title, molt_li = res.get("title") or "", M.linkedin_of(res)
                    molt_company, molt_cdom = M.company_of(res)
                elif st == 404:
                    stats["rel_404"] += 1
                M.pause()
            # 2. second pass: name + company DOMAIN. Only on silence or F, never on D (D is an answer).
            if args.second_pass and email and (not grade or grade == "F") and r["domain"] and budget.records_ok():
                q = f"{r['first_name'] or ''} {r['last_name'] or ''}".strip()
                if args.second_pass_endpoint == "profile":
                    # one flat profile back (same shape as reverse_email_lookup); the domain is the identity check
                    body = {"name": q, "company": r["domain"]}
                    st2, res2, md2 = M.call("search_business_profile_by_name", body)
                    budget.absorb(M.log_call(con, "search_business_profile_by_name", body, st2, res2, md2,
                                             note=args.note + " second-pass"))
                    stats["sp_calls"] += 1
                    decision, snap = profile_decision(res2 if st2 == 200 else {}, st2, r["domain"], "",
                                                      r["first_name"] or "", r["last_name"] or "")
                    upd.update(second_pass="yes", second_pass_decision=decision,
                               second_pass_endpoint="search_business_profile_by_name",
                               candidates_json=json.dumps(snap)[:4000])
                    if decision in ("accept_same_domain", "risky_same_domain", "profile_no_email", "review_cross_domain"):
                        g2, e2 = M.grade_of(res2), M.email_of(res2)
                        molt_li = molt_li or M.linkedin_of(res2)
                        molt_title = molt_title or M.title_of(res2)
                        c2, cd2 = M.company_of(res2)
                        molt_company, molt_cdom = molt_company or c2, molt_cdom or cd2
                        if decision == "profile_no_email":
                            grade = grade or "F"          # person known, no confirmed work address
                        elif decision == "review_cross_domain":
                            # person found; the graded address lives on another domain. Never adopt it.
                            upd.update(molt_other_email_domain=M.dom(e2), molt_other_email_grade=g2)
                            grade = grade or "F"
                        else:
                            grade, molt_email, validated = (g2 or "F"), e2, M.validated_at_of(res2)
                            route_used = "search_business_profile_by_name"
                            if decision == "accept_same_domain":
                                stats["sp_recovered"] += 1
                else:
                    body = {"query": q, "company": r["domain"], "limit": 5}
                    st2, res2, md2 = M.call("search_people", body)
                    budget.absorb(M.log_call(con, "search_people", body, st2, res2, md2, note=args.note + " second-pass"))
                    stats["sp_calls"] += 1
                    cands = res2.get("results") if isinstance(res2, dict) else []
                    cands = cands if isinstance(cands, list) else []
                    decision, cand = second_pass_decision(cands, r["domain"], r["first_name"] or "", r["last_name"] or "")
                    upd.update(second_pass="yes", second_pass_decision=decision, second_pass_endpoint="search_people",
                               candidates_json=json.dumps(cands[:3]))
                    if decision == "accept_same_domain" and cand:
                        stats["sp_recovered"] += 1
                        grade, molt_email = M.grade_of(cand), M.email_of(cand)
                        validated, molt_li = M.validated_at_of(cand), M.linkedin_of(cand)
                        molt_title = M.title_of(cand)
                        molt_company, molt_cdom = M.company_of(cand)
                        route_used = "search_people"
                stats[f"sp_{decision}"] = stats.get(f"sp_{decision}", 0) + 1
                M.pause()
            # 3. LinkedIn-only rows
            if li and not email and not grade and budget.records_ok():
                body = {"linkedin_url": li}
                st, res, md = M.call("linkedin_to_best_email", body)
                budget.absorb(M.log_call(con, "linkedin_to_best_email", body, st, res, md, note=args.note))
                stats["li_email_calls"] += 1
                http, route_used = str(st), "linkedin_to_best_email"
                if st == 200 and M.email_of(res):
                    stats["li_email_hit"] += 1
                    grade, molt_email, validated = M.grade_of(res), M.email_of(res), M.validated_at_of(res)
                    email = molt_email
                M.pause()

        corrected = bool(molt_email and email and molt_email != email)
        verdict, tier, route = classify(email or molt_email, grade, r["domain"], has_linkedin=bool(li or molt_li),
                                        second_pass_done=(upd.get("second_pass") == "yes"), still_at_company=still)
        if route_used in ("search_people", "search_business_profile_by_name", "reverse_linkedin_lookup") \
                and tier == "T1_send" and corrected:
            verdict, tier = "corrected", "T1_send_corrected"
        if route == "second_pass" and not args.second_pass:
            route = "linkedin" if (li or molt_li) else "hold"

        # verifier delta: only when the list carried a verdict for this row
        vstat = r["verifier_status"] if "verifier_status" in r.keys() else ""
        dc = delta_class(vstat, grade, http, upd.get("second_pass_decision") or "",
                         "yes" if corrected else "no", still) if vstat else ""
        upd.update(corrected="yes" if corrected else "no", delta_class=dc)
        if dc:
            stats[f"delta_{dc}"] = stats.get(f"delta_{dc}", 0) + 1

        # 4. phones for dead-email rows only
        if phones_left > 0 and (li or molt_li) and tier in ("SUPPRESS", "HOLD_not_found") and budget.phone_ok():
            body = {"linkedin_url": li or molt_li}
            st3, res3, md3 = M.call("linkedin_to_mobile_phone", body)
            budget.absorb(M.log_call(con, "linkedin_to_mobile_phone", body, st3, res3, md3, note=args.note + " phone"))
            stats["phone_calls"] += 1
            upd["phone_http"] = str(st3)
            phone = (res3 or {}).get("mobile_phone") or (res3 or {}).get("phone") or ""
            if st3 == 200 and phone:
                stats["phone_hit"] += 1
                phones_left -= 1
                upd["mobile_phone"] = str(phone)
            M.pause()

        upd.update(molt_route=route_used, molt_http=http, molt_email=molt_email, grade=grade,
                   grade_validated_at=validated, molt_title=molt_title, molt_company=molt_company,
                   molt_company_domain=molt_cdom, molt_linkedin=molt_li, verdict=verdict, tier=tier, route=route)
        if not r["email"] and molt_email:
            upd["email"] = molt_email
        sets = ", ".join(f"{k}=?" for k in upd)
        con.execute(f"UPDATE contacts SET {sets} WHERE id=?", (*upd.values(), cid))
        con.commit()   # per-row flush: a crash costs one record, never the batch

        mark = {"T1_send": "+", "T1_send_corrected": "+", "T2_catchall": "~", "SUPPRESS": "X",
                "HOLD_not_found": "?", "HOLD_job_change": ">"}.get(tier, ".")
        agree_txt = f" agree={emp_agree}" if employment == "both" else ""
        delta_txt = f" {dc}" if dc else ""
        print(f"[{i}/{len(rows)}] {mark} {(r['first_name'] or '?')[:14]:14} {(r['domain'] or '')[:26]:26} "
              f"{grade or '-':1} {tier:18} {route:18} still={still}{agree_txt}{delta_txt}")

    print("\n" + "=" * 64)
    for k, v in stats.items():
        print(f"  {k:20} {v}")
    print(f"  records_remaining_5h (last seen) {budget.records_5h}  phone_tokens {budget.phone_tokens}")
    stem = "" if DB == HERE / "data" / "reachability.db" else DB.stem + "_"
    summary = DB.parent / f"{stem}grade_summary.json"      # per database, so two lists never share receipts
    summary.write_text(json.dumps({"ran_at": now(), "employment": employment, "stats": stats, "account": snap,
                                   "records_remaining_5h": budget.records_5h,
                                   "phone_tokens_remaining": budget.phone_tokens}, indent=2))
    print(f"wrote {summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
