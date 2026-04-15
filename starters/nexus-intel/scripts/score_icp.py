#!/usr/bin/env python3
"""
score_icp.py — Score engagers on ICP fit (1-5 stars).

Vertical-aware ICP scoring driven by data/icp-profile.json. Each fork ships
its own profile so the scoring rules become data, not code.

Four dimensions:
  persona_fit:      Title matches a buyer-tier phrase from icp-profile.json
  company_fit:      Company keywords + internal/competitor flags
  engagement_depth: Frequency + comment depth + breadth across tracked sources
  budget_potential: Title seniority + enterprise keywords + followers

Overall is a weighted average of the four dimensions. Default weighting is
equal across all four; calibrate per-dimension weights for your vertical.

Usage:
    python3 scripts/score_icp.py                        # score unscored engagers
    python3 scripts/score_icp.py --rescore              # rescore all engagers
    python3 scripts/score_icp.py --profile <path.json>  # custom profile
    python3 scripts/score_icp.py --dry-run              # show scores without saving
"""

# SCAFFOLD: The scoring thresholds and dimension weights below are minimal
# defaults. Calibrate them for your vertical. See docs/voice-dna.md.

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from _lib import get_db

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROFILE = REPO_ROOT / "data" / "icp-profile.json"

# TODO: tune these dimension weights for your vertical.
# Must sum to 1.0. Default is equal weighting.
DIMENSION_WEIGHTS: dict[str, float] = {
    "persona": 0.25,
    "company": 0.25,
    "engagement": 0.25,
    "budget": 0.25,
}


def load_profile(path: Path) -> dict:
    if not path.exists():
        sys.exit(f"ERROR: ICP profile not found at {path}")
    return json.loads(path.read_text())


def _compile_tier_patterns(profile: dict) -> dict[int, list[re.Pattern]]:
    """Turn persona_tiers dict into compiled regex patterns keyed by tier int."""
    tiers: dict[int, list[re.Pattern]] = {}
    for tier_str, phrases in profile.get("persona_tiers", {}).items():
        tier = int(tier_str)
        tiers[tier] = [
            re.compile(r"\b" + re.escape(p.lower()) + r"\b", re.IGNORECASE)
            for p in phrases
        ]
    return tiers


def score_persona_fit(title: str | None, tier_patterns: dict[int, list[re.Pattern]]) -> int:
    """Match title against the tiered persona patterns in icp-profile.json."""
    if not title:
        return 1
    title_lower = title.lower()
    for tier in sorted(tier_patterns.keys(), reverse=True):
        for pat in tier_patterns[tier]:
            if pat.search(title_lower):
                return tier
    return 1


def score_company_fit(
    company: str | None,
    title: str | None,
    profile: dict,
    *,
    is_internal: bool = False,
    job_bucket: str | None = None,
) -> int:
    """Score company fit against ICP profile keywords.

    TODO: calibrate these thresholds for your market.
    """
    if is_internal:
        return 1

    excluded_buckets = profile.get("exclude_job_buckets", [])
    if job_bucket and job_bucket in excluded_buckets:
        return 1

    if not company:
        return 2

    company_lower = company.lower()

    for kw in profile.get("competitor_keywords", []):
        if kw.lower() in company_lower:
            return 1

    for kw in profile.get("internal_keywords", []):
        if kw.lower() in company_lower:
            return 1

    score = 2
    for kw in profile.get("target_companies_keywords", []):
        if kw.lower() in company_lower:
            score = max(score, 3)
            break

    for kw in profile.get("enterprise_company_keywords", []):
        if kw.lower() in company_lower:
            score = max(score, 4)
            break

    return score


def score_engagement_depth(engagement_count: int, comment_count: int, accounts_engaged: int) -> int:
    """Score engagement depth.

    TODO: calibrate the thresholds below for your scraped volumes.
    Default values assume B2B LinkedIn scrapes; higher-volume platforms
    will need bigger thresholds.
    """
    # TODO: replace these thresholds with ones calibrated to your data volume.
    return max(1, min(5, 1))


def score_budget_potential(
    company: str | None,
    title: str | None,
    followers: int | None,
    profile: dict,
) -> int:
    """Score budget authority based on title seniority and company markers.

    TODO: tune the title-to-budget mapping for your vertical.
    """
    # TODO: replace with your own budget-signal logic.
    return max(1, min(5, 1))


def calculate_overall(persona: int, company: int, engagement: int, budget: int) -> int:
    """Weighted average of the four dimensions.

    Weights are defined in DIMENSION_WEIGHTS at the top of this file. Default
    is equal weighting; calibrate for your vertical.
    """
    w = DIMENSION_WEIGHTS
    weighted = (
        persona * w["persona"]
        + company * w["company"]
        + engagement * w["engagement"]
        + budget * w["budget"]
    )
    return max(1, min(5, round(weighted)))


def main() -> int:
    parser = argparse.ArgumentParser(description="Score engagers on ICP fit")
    parser.add_argument("--rescore", action="store_true", help="Rescore all engagers")
    parser.add_argument("--dry-run", action="store_true", help="Show scores without saving")
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE,
                        help="Path to ICP profile JSON (default: data/icp-profile.json)")
    args = parser.parse_args()

    profile = load_profile(args.profile)
    print(f"Loaded ICP profile: {profile.get('client', '?')} / {profile.get('vertical', '?')}")
    tier_patterns = _compile_tier_patterns(profile)

    conn = get_db()

    base_sql = """
        SELECT e.id, e.handle, e.name, e.title, e.company, e.parsed_company,
               e.is_internal, e.followers, e.platform, e.job_bucket,
               COUNT(eg.id) as engagement_count,
               SUM(CASE WHEN eg.engagement_type IN ('comment', 'reply') THEN 1 ELSE 0 END) as comment_count,
               COUNT(DISTINCT eg.source_id) as accounts_engaged
        FROM engagers e
        LEFT JOIN engagements eg ON eg.engager_id = e.id
    """

    if args.rescore:
        engagers = conn.execute(base_sql + " GROUP BY e.id").fetchall()
    else:
        engagers = conn.execute(
            base_sql + " WHERE e.id NOT IN (SELECT engager_id FROM icp_scores) GROUP BY e.id"
        ).fetchall()

    if not engagers:
        print("No engagers to score.")
        return 0

    print(f"Scoring {len(engagers)} engagers...\n")
    scores_saved = 0

    excluded_buckets = set(profile.get("exclude_job_buckets", []))

    for eng in engagers:
        effective_company = eng["company"] or eng["parsed_company"]
        persona = score_persona_fit(eng["title"], tier_patterns)
        company = score_company_fit(
            effective_company, eng["title"], profile,
            is_internal=bool(eng["is_internal"]),
            job_bucket=eng["job_bucket"],
        )
        engagement = score_engagement_depth(
            eng["engagement_count"] or 0,
            eng["comment_count"] or 0,
            eng["accounts_engaged"] or 0,
        )
        budget = score_budget_potential(
            effective_company, eng["title"], eng["followers"], profile,
        )
        overall = calculate_overall(persona, company, engagement, budget)

        if eng["job_bucket"] in excluded_buckets:
            overall = 1

        if args.dry_run or overall >= 3:
            stars = "*" * overall + "-" * (5 - overall)
            name_display = eng["name"] or eng["handle"]
            print(
                f"  {stars}  {name_display:<30} "
                f"{(eng['title'] or '-')[:35]:<35} "
                f"{(effective_company or '-')[:20]:<20}"
            )

        if not args.dry_run:
            conn.execute(
                """INSERT OR REPLACE INTO icp_scores
                   (engager_id, persona_fit, company_fit, engagement_depth,
                    budget_potential, overall_stars, scored_at)
                   VALUES (?, ?, ?, ?, ?, ?, datetime('now'))""",
                (eng["id"], persona, company, engagement, budget, overall),
            )
            scores_saved += 1

    if not args.dry_run:
        conn.commit()
        print(f"\nScored {scores_saved} engagers.")

        dist = conn.execute(
            "SELECT overall_stars, COUNT(*) as c FROM icp_scores "
            "GROUP BY overall_stars ORDER BY overall_stars DESC"
        ).fetchall()

        print("\nScore distribution:")
        for row in dist:
            stars = "*" * row["overall_stars"] + "-" * (5 - row["overall_stars"])
            print(f"  {stars}  {row['c']} engagers")

    return 0


if __name__ == "__main__":
    sys.exit(main())
