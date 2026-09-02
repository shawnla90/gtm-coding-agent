#!/usr/bin/env python3
"""reachability.py -- the grade -> verdict -> tier -> route model. Pure functions, no network.

Moltsets grades (developer.moltsets.com/moltsets-data/email-risk-scores):
  A  valid: known reply, open, or click            -> send
  B  known send, no bounce                          -> probably send
  C  catch-all domain                               -> your call
  D  hard invalid: bounce, complaint, or spam trap  -> never send
  F  no data                                        -> re-verify, or treat like C

The one idea this module adds: a bad email grade is not a dead contact. It is a routing
decision. D means the mailbox is dead, the person is not. F and not_found mean the graph has
not seen this address, so you look again before you give up. Every row keeps a route.
"""
from __future__ import annotations

import re

FREEMAIL = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com", "icloud.com",
    "proton.me", "protonmail.com", "live.com", "me.com", "msn.com", "ymail.com",
}

GRADE_MEANING = {
    "A": "valid: known reply, open, or click",
    "B": "known send, no bounce",
    "C": "catch-all domain, mailbox unconfirmed",
    "D": "hard invalid: bounce, complaint, or spam trap",
    "F": "no data in the graph for this address",
    "-": "not in the graph (404 = coverage gap, not a bad email)",
}

# Reachability multiplier, same shape as the Apollo starter (T1 1.0 .. T4 0.3), now driven by the
# grade instead of Apollo's email_status flag. D is not zero: the email is dead, the person is not.
GRADE_MULT = {"A": 1.0, "B": 0.85, "C": 0.6, "F": 0.3, "-": 0.3, "D": 0.15}

# tier -> what the sheet says to do
TIER_ACTION = {
    "T1_send": "send (grade A/B, same domain as the company)",
    "T1_send_corrected": "send the corrected address (second pass found same-domain A/B)",
    "T2_catchall": "send in a small, monitored segment (catch-all)",
    "HOLD_review": "hold: grade A/B on a different domain, or a free-mail address",
    "HOLD_job_change": "hold: Apollo says they moved; re-source at the new company",
    "HOLD_not_found": "hold: not in the graph after the second pass; go LinkedIn",
    "HOLD_no_email": "hold: person found, no confirmed email; go LinkedIn",
    "SUPPRESS": "never email (grade D); route to LinkedIn, then phone (1 token per hit)",
}

ROUTES = ("email", "email_low_volume", "linkedin", "linkedin_then_phone", "second_pass", "resource", "hold")

TITLE_WEIGHTS = [
    (re.compile(r"\brev\s?ops\b|\brevenue operations\b", re.I), 100),
    (re.compile(r"\brevenue\b", re.I), 90),
    (re.compile(r"\bgrowth\b", re.I), 80),
    (re.compile(r"\bgo[\s-]?to[\s-]?market\b|\bgtm\b", re.I), 75),
    (re.compile(r"\bsales\b", re.I), 60),
    (re.compile(r"\bmarketing\b", re.I), 55),
    (re.compile(r"\bproduct\b", re.I), 50),
    (re.compile(r"\bbusiness development\b|\bbiz dev\b", re.I), 45),
    (re.compile(r"\bfounder\b|\bco-?founder\b|\bowner\b", re.I), 40),
    (re.compile(r"\bchief\b|\bC[A-Z]O\b", re.I), 30),
    (re.compile(r"\bvp\b|\bvice president\b", re.I), 25),
    (re.compile(r"\bhead of\b", re.I), 20),
    (re.compile(r"\bdirector\b", re.I), 15),
    (re.compile(r"\bmanager\b", re.I), 5),
]

PERSONA_BUCKETS = {
    "sales": re.compile(r"\b(sales|revenue|CRO|chief revenue|account exec|business develop|biz dev|SDR|BDR|partnerships)\b", re.I),
    "marketing": re.compile(r"\b(marketing|CMO|chief marketing|growth|demand gen|brand|content|SEO|comms|communications)\b", re.I),
    "product": re.compile(r"\b(product|CPO|chief product|UX|design|engineering|engineer|CTO|technical|R&D)\b", re.I),
    "founder": re.compile(r"\b(founder|co-?founder|owner|CEO|chief executive)\b", re.I),
}


def dom(email: str | None) -> str:
    return (email or "").split("@")[-1].lower().strip()


def norm_company(s: str | None) -> str:
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    stop = {"inc", "llc", "ltd", "limited", "corp", "corporation", "co", "company", "the", "io",
            "ai", "gmbh", "pty", "plc", "holdings", "group", "technologies", "technology", "labs",
            "lab", "software"}
    return " ".join(w for w in s.split() if w not in stop)


def companies_match(listed: str | None, current: str | None,
                    listed_domain: str = "", current_domain: str = "") -> str:
    """'yes' | 'moved' | 'unknown'. Domain agreement wins; else normalized-name containment."""
    ld, cd = (listed_domain or "").lower().strip(), (current_domain or "").lower().strip()
    if ld and cd:
        if ld == cd or ld.endswith("." + cd) or cd.endswith("." + ld):
            return "yes"
    a, b = norm_company(listed), norm_company(current)
    if not a or not b:
        return "unknown"
    if a == b or a in b or b in a:
        return "yes"
    return "moved"


def combine_employment(apollo: str = "unknown", moltsets: str = "unknown") -> tuple[str, str, str]:
    """(still_at_company, employment_source, employment_agree) from two independent checks.
    Conservative: if either source says moved, the row is a job change (hold + re-source)."""
    a, m = (apollo or "unknown"), (moltsets or "unknown")
    if a != "unknown" and m != "unknown":
        agree = "yes" if a == m else "no"
        source = "both"
    elif m != "unknown":
        agree, source = "n/a", "moltsets"
    elif a != "unknown":
        agree, source = "n/a", "apollo"
    else:
        return "unknown", "none", "n/a"
    if "moved" in (a, m):
        return "moved", source, agree
    return "yes", source, agree


def score_title(title: str | None) -> int:
    if not title:
        return 0
    return sum(w for pat, w in TITLE_WEIGHTS if pat.search(title))


def classify_persona(title: str | None) -> str:
    if not title:
        return "other"
    for bucket, pat in PERSONA_BUCKETS.items():
        if pat.search(title):
            return bucket
    return "other"


def classify(email: str | None, grade: str | None, company_domain: str | None,
             has_linkedin: bool = True, second_pass_done: bool = False,
             still_at_company: str = "unknown") -> tuple[str, str, str]:
    """(verdict, tier, route) for one contact after the first (or second) Moltsets pass.

    grade '' means the graph returned nothing (404 or no grade). second_pass_done says whether the
    name + domain search already ran, which decides between 'second_pass' and 'linkedin'.
    """
    g = (grade or "").strip().upper()[:1]
    e = (email or "").strip().lower()
    d = dom(e)
    cdom = (company_domain or "").lower().strip()
    li_route = "linkedin" if has_linkedin else "hold"

    if still_at_company == "moved":
        return "job_changed", "HOLD_job_change", "resource"
    if not e:
        return "no_email", "HOLD_no_email", li_route
    if d in FREEMAIL:
        return "free_email", "HOLD_review", "hold"
    if g in ("A", "B"):
        if not cdom or d == cdom or d.endswith("." + cdom) or cdom.endswith("." + d):
            return "confirmed_valid", "T1_send", "email"
        return "confirmed_cross_domain", "HOLD_review", "hold"
    if g == "C":
        return "catch_all", "T2_catchall", "email_low_volume"
    if g == "D":
        return "hard_invalid", "SUPPRESS", "linkedin_then_phone" if has_linkedin else "hold"
    if g == "F" or not g:
        verdict = "no_data" if g == "F" else "not_in_graph"
        if second_pass_done:
            return verdict, "HOLD_not_found", li_route
        return verdict, "HOLD_not_found", "second_pass"
    return "unknown", "HOLD_review", "hold"


def second_pass_decision(candidates: list[dict], company_domain: str, first: str = "",
                         last: str = "") -> tuple[str, dict | None]:
    """Pick from search_people results. Accept ONLY a same-domain grade A/B candidate; a different
    domain is a different person until proven otherwise (the cnet.com -> usfertility.com guard).
    Returns (decision, candidate). decision in accept_same_domain | risky_same_domain |
    review_cross_domain | no_candidate."""
    cdom = (company_domain or "").lower().strip()
    best, best_c = "no_candidate", None
    want = f"{first} {last}".strip().lower()
    for c in candidates or []:
        be = str(c.get("business_email") or "").strip().lower()
        if not be:
            continue
        g = str(c.get("business_email_risk_score") or "").upper()[:1]
        name_ok = (not want) or (str(c.get("full_name") or "").strip().lower() == want)
        if dom(be) == cdom and cdom:
            if g in ("A", "B") and name_ok:
                return "accept_same_domain", c
            if best != "risky_same_domain":
                best, best_c = "risky_same_domain", c
        elif best == "no_candidate":
            best, best_c = "review_cross_domain", c
    return best, best_c


def composite(title: str | None, grade: str | None) -> tuple[int, float, float]:
    """(title_score, multiplier, composite)."""
    ts = score_title(title)
    g = (grade or "-").strip().upper()[:1] or "-"
    mult = GRADE_MULT.get(g, GRADE_MULT["-"])
    return ts, mult, round(ts * mult, 1)
