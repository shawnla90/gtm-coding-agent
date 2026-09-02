#!/usr/bin/env python3
"""budget.py -- what a Moltsets run costs, in the four units that actually meter it. Free calls only.

  calls            one HTTP POST each; unlimited in count on paid plans, rate-limited per 5h window
  records          the real data meter: two 5h pools on the $97 plan, enrich 15k/5h and search 7.5k/5h,
                   with weekly caps. A 404 does not consume a record. A client crash mid-batch does.
  internal tokens  get_billing.token_costs is all 1s and the balance is -1 (unlimited) on paid plans.
  phone tokens     the scarce pool. linkedin_to_mobile_phone = 1 per HIT, 0 on a miss; 50 per month on the
                   $97 plan. get_account reports phone_token_balance / phone_token_allowance.

  python3 budget.py             # status: pools, phone tokens, your own ledger
  python3 budget.py --json
"""
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import moltsets_client as M  # noqa: E402

HERE = Path(__file__).resolve().parent
DB = HERE / "data" / "reachability.db"


def ledger(con):
    M.ensure_log(con)
    rows = con.execute(
        """SELECT endpoint, COUNT(*) n,
                  SUM(CASE WHEN http_status LIKE '2%' THEN 1 ELSE 0 END) ok,
                  SUM(CASE WHEN http_status='404' THEN 1 ELSE 0 END) miss,
                  SUM(CASE WHEN http_status NOT LIKE '2%' AND http_status!='404' THEN 1 ELSE 0 END) err
           FROM moltsets_api_log GROUP BY endpoint ORDER BY n DESC""").fetchall()
    ext = con.execute("SELECT COALESCE(SUM(ext_tokens_used),0) FROM moltsets_api_log").fetchone()[0]
    return rows, ext


def main():
    if not M.get_key():
        sys.exit("MOLTSETS_API_KEY not set: export it, add it to .env, or point SECRETS_DB at your vault")
    out = {}
    for ep in M.FREE_ENDPOINTS:
        st, res, md = M.call(ep, {}, timeout=30)
        out[ep] = {"http": st, "results": res, "metadata": md}
    if "--json" in sys.argv:
        print(json.dumps(out, indent=2))
        return 0

    acct = out["get_account"]["results"] or {}
    bill = out["get_billing"]["results"] or {}
    fu = M.fair_use(acct, out["get_account"]["metadata"])
    print(f"MOLTSETS BUDGET  plan={bill.get('plan') or acct.get('plan')}  status={bill.get('subscription_status', '?')}"
          f"  period ends {bill.get('current_period_end', '?')}")
    print("=" * 72)
    for pool, p in fu["pools"].items():
        print(f"  {pool:7} records  5h remaining {p.get('remaining_5h')}   week used {p.get('used_1w')}  week remaining {p.get('remaining_1w')}")
    print(f"  phone tokens   {acct.get('phone_token_balance')} of {acct.get('phone_token_allowance')} "
          f"(= {(acct.get('phone_token_balance') or 0) // M.PHONE_TOKEN_COST} more mobile hits; misses are free)")
    print(f"  internal tokens {acct.get('token_balance')} (-1 = unlimited)   personal emails: {acct.get('personal_email_available')}")
    tc = bill.get("token_costs") or {}
    print(f"  endpoint catalogue: {len(tc)} endpoints")
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB, timeout=30)
    rows, ext = ledger(con)
    print("\nYOUR LEDGER (data/reachability.db moltsets_api_log; the API keeps no history for you)")
    if not rows:
        print("  no calls logged yet")
    for ep, n, ok, miss, err in rows:
        print(f"  {ep:28} {n:5} calls  {ok:5} hit  {miss:4} not-found  {err:3} err")
    print(f"  external tokens spent (logged): {ext}")
    print("\n  not-found = coverage gap, free. errors = records may have been consumed; counters unreported.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
