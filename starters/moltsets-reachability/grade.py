#!/usr/bin/env python3
"""grade.py -- the reachability waterfall. Apollo says who is still there; Moltsets grades the address.

For every contact not yet graded:
  0. (--apollo)      Apollo people/match on the LinkedIn URL. If the current company disagrees with
                     the listed one, the row is a job change: hold it, re-source, skip the stale email.
  1. reverse_email_lookup on the business email -> grade A-F. 404 = not in the graph. Free.
  2. (--second-pass) on 404 / F: search_people {query: name, company: DOMAIN}. Accept only a
                     same-domain grade A/B candidate. Cross-domain hits are a different person
                     until proven otherwise.
  3. LinkedIn-only rows (no email): linkedin_to_best_email.
  4. (--phones N)    for rows whose email is dead (grade D) or unfound: linkedin_to_mobile_phone,
                     one phone token per HIT (misses are free), capped at N hits, never below the phone floor.

Every call is logged to data/reachability.db moltsets_api_log and every row is committed as it
finishes: a crash costs one record, a rerun never re-spends. Floor guard on records_remaining_5h.

  python3 grade.py                          # first pass only
  python3 grade.py --apollo --second-pass   # the full waterfall, no phones
  python3 grade.py --phones 10              # also buy up to 10 mobiles for dead-email rows
  python3 grade.py --limit 20 --dry-run     # show what would run, spend nothing
"""
import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import moltsets_client as M  # noqa: E402
from lib import apollo_client as A  # noqa: E402
from lib.reachability import classify, companies_match, second_pass_decision  # noqa: E402

HERE = Path(__file__).resolve().parent
DB = HERE / "data" / "reachability.db"


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def redact(email):
    if not email or "@" not in email:
        return email or "-"
    local, d = email.rsplit("@", 1)
    return f"{local[:1]}***@{d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apollo", action="store_true", help="run the Apollo employment check first")
    ap.add_argument("--second-pass", action="store_true", help="search_people by name + domain on 404 / F")
    ap.add_argument("--phones", type=int, default=0, help="buy up to N mobile numbers for dead-email rows")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--redo", action="store_true", help="re-grade rows that already have a verdict")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--note", default="reachability", help="tag written to the api log")
    args = ap.parse_args()

    con = sqlite3.connect(DB, timeout=30)
    con.execute("PRAGMA journal_mode = WAL;")
    M.ensure_log(con)
    con.row_factory = sqlite3.Row

    where = "1=1" if args.redo else "verdict IS NULL"
    rows = con.execute(f"SELECT * FROM contacts WHERE {where} ORDER BY id").fetchall()
    if args.limit:
        rows = rows[: args.limit]
    print(f"{len(rows)} contacts to grade "
          f"(apollo={'on' if args.apollo else 'off'}, second_pass={'on' if args.second_pass else 'off'}, "
          f"phones={args.phones})")
    if args.dry_run:
        for r in rows[:25]:
            print(f"  would grade: {r['first_name']} {r['last_name'][:1]}. @ {r['domain']}  {redact(r['email'])}")
        return 0
    if not M.get_key():
        sys.exit("MOLTSETS_API_KEY not set: export it, add it to .env, or point SECRETS_DB at your vault")

    snap = M.account_snapshot()
    print(f"plan={snap.get('plan')} pools={json.dumps(snap.get('pools'))} phone_tokens={snap.get('phone_tokens_remaining')}")
    budget = M.Budget()
    budget.phone_tokens = snap.get("phone_tokens_remaining")

    stats = {"apollo_checked": 0, "apollo_moved": 0, "rel_calls": 0, "rel_hit": 0, "rel_404": 0,
             "sp_calls": 0, "sp_recovered": 0, "li_email_calls": 0, "li_email_hit": 0,
             "phone_calls": 0, "phone_hit": 0, "floor_stops": 0}
    phones_left = args.phones

    for i, r in enumerate(rows, 1):
        cid, email, li = r["id"], (r["email"] or "").lower(), r["linkedin_url"] or ""
        upd = {"graded_at": now(), "second_pass": "no"}
        still = "unknown"

        # 0. employment check
        if args.apollo and li:
            ap_res = A.people_match(li)
            stats["apollo_checked"] += 1
            if ap_res.get("http") == 200 and (ap_res.get("company") or ap_res.get("company_domain")):
                still = companies_match(r["company"], ap_res.get("company"), r["domain"], ap_res.get("company_domain"))
                upd.update(apollo_checked_at=now(), apollo_current_company=ap_res.get("company"),
                           apollo_current_domain=ap_res.get("company_domain"),
                           apollo_current_title=ap_res.get("title"), still_at_company=still)
                if still == "moved":
                    stats["apollo_moved"] += 1
            else:
                upd.update(apollo_checked_at=now(), still_at_company="unknown")

        grade, molt_email, validated, route_used, http = "", "", "", "none", ""
        molt_title = molt_company = molt_cdom = molt_li = ""
        if still != "moved":
            if not budget.records_ok():
                stats["floor_stops"] += 1
                print(f"[{i}/{len(rows)}] ! floor guard: records_remaining_5h={budget.records_5h}. stopping.")
                break
            if email and M.dom(email) not in M.FREEMAIL:
                # 1. reverse_email_lookup
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
                # 2. second pass
                if args.second_pass and (not grade or grade == "F") and r["domain"] and budget.records_ok():
                    q = f"{r['first_name']} {r['last_name']}".strip()
                    body = {"query": q, "company": r["domain"], "limit": 5}
                    st2, res2, md2 = M.call("search_people", body)
                    budget.absorb(M.log_call(con, "search_people", body, st2, res2, md2, note=args.note + " second-pass"))
                    stats["sp_calls"] += 1
                    cands = res2.get("results") if isinstance(res2, dict) else []
                    cands = cands if isinstance(cands, list) else []
                    decision, cand = second_pass_decision(cands, r["domain"], r["first_name"], r["last_name"])
                    upd.update(second_pass="yes", second_pass_decision=decision,
                               candidates_json=json.dumps(cands[:3]))
                    if decision == "accept_same_domain" and cand:
                        stats["sp_recovered"] += 1
                        grade, molt_email = M.grade_of(cand), M.email_of(cand)
                        validated, molt_li = M.validated_at_of(cand), M.linkedin_of(cand)
                        molt_title = cand.get("title") or ""
                        molt_company, molt_cdom = M.company_of(cand)
                        route_used = "search_people"
                    M.pause()
            elif li and not email:
                # 3. LinkedIn-only rows
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

        # classify
        corrected = bool(molt_email and email and molt_email != email)
        verdict, tier, route = classify(email or molt_email, grade, r["domain"], has_linkedin=bool(li or molt_li),
                                        second_pass_done=(upd.get("second_pass") == "yes"), still_at_company=still)
        if route_used == "search_people" and tier == "T1_send" and corrected:
            verdict, tier = "corrected", "T1_send_corrected"
        if route == "second_pass" and not args.second_pass:
            route = "linkedin" if (li or molt_li) else "hold"   # second pass not requested this run

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
        print(f"[{i}/{len(rows)}] {mark} {(r['first_name'] or '?')[:14]:14} {r['domain'][:26]:26} "
              f"{grade or '-':1} {tier:18} {route:18} still={still}")

    print("\n" + "=" * 64)
    for k, v in stats.items():
        print(f"  {k:16} {v}")
    print(f"  records_remaining_5h (last seen) {budget.records_5h}  phone_tokens {budget.phone_tokens}")
    summary = HERE / "data" / "grade_summary.json"
    summary.write_text(json.dumps({"ran_at": now(), "stats": stats, "account": snap,
                                   "records_remaining_5h": budget.records_5h,
                                   "phone_tokens_remaining": budget.phone_tokens}, indent=2))
    print(f"wrote {summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
