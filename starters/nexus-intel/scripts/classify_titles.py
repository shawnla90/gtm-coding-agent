#!/usr/bin/env python3
"""
classify_titles.py — Parse company + assign job bucket + flag internal engagers.

Title classification scaffold. Default buckets are minimal. Replace with
your vertical's persona taxonomy.

Usage:
    python3 scripts/classify_titles.py              # classify unclassified engagers only
    python3 scripts/classify_titles.py --reclassify # reclassify ALL engagers
    python3 scripts/classify_titles.py --dry-run    # preview without writing
"""

# SCAFFOLD: The GTM_BUCKETS list below is empty. Add your own job-title regex
# patterns for each persona bucket you want to track. See docs/voice-dna.md.

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from _lib import get_db

# ---------- Constants ----------

ROLE_WORDS = {
    "vp", "vice", "president", "head", "director", "manager", "engineer",
    "lead", "specialist", "coordinator", "associate", "rep", "analyst",
    "architect", "strategist", "executive", "officer", "senior", "junior",
    "intern", "founder", "cofounder", "co-founder", "ceo", "cto", "coo",
    "cmo", "cro", "cfo", "svp", "evp", "avp", "sdr", "bdr", "ae",
    "consultant", "advisor", "coach", "freelance", "fractional",
    "principal", "owner", "partner", "managing",
}

COMPANY_SUFFIXES = re.compile(
    r"\s*[.,]?\s*\b(?:inc|co|ai|io|hq|labs|llc|ltd|corp|gmbh|"
    r"com|\.com|\.io|\.ai|\.co)\b\.?\s*$",
    re.IGNORECASE,
)

EMOJI_PATTERN = re.compile(
    "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F\U0001F780-\U0001F7FF\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF"
    "\U00002600-\U000027BF\U0000FE00-\U0000FE0F\U0000200D"
    "\U00002702-\U000027B0\U000024C2-\U0001F251]+",
    flags=re.UNICODE,
)

# TODO: define your persona buckets. Each tuple is (bucket_name, [regex_patterns]).
# Patterns are evaluated top-to-bottom; the first match wins. Add a fallback
# "other" entry at the end so every engager lands in a bucket.
GTM_BUCKETS: list[tuple[str, list[str]]] = [
    # ("saas-founder",   [r"\bfounder\b", r"\bceo\b", r"\bcto\b"]),
    # ("gtm-leader",     [r"\bvp\b.*\b(sales|marketing|growth)\b", r"\bcro\b", r"\bcmo\b"]),
    # ("revops",         [r"\brevops\b", r"\brevenue\s+operations\b"]),
    ("other", []),  # fallback
]

_COMPILED = [
    (name, [re.compile(p, re.IGNORECASE) for p in patterns])
    for name, patterns in GTM_BUCKETS
]


# ---------- Helpers ----------

def _strip_emojis(text: str) -> str:
    return EMOJI_PATTERN.sub("", text)


def _is_role_word(segment: str) -> bool:
    words = set(segment.lower().split())
    if not words:
        return True
    role_count = sum(1 for w in words if w in ROLE_WORDS)
    return role_count > len(words) / 2


def _clean_company(raw: str | None) -> str | None:
    if not raw:
        return None
    cleaned = _strip_emojis(raw).strip()
    cleaned = re.sub(r"[.,;:!?\-]+$", "", cleaned).strip()
    cleaned = re.sub(r"^[.,;:!?\-]+", "", cleaned).strip()
    if len(cleaned) < 2:
        return None
    if _is_role_word(cleaned):
        return None
    return cleaned


def parse_company(title: str) -> str | None:
    """Extract company name from a LinkedIn headline."""
    if not title:
        return None

    clean_title = _strip_emojis(title).strip()
    if len(clean_title) < 2:
        return None

    # Pattern 1: "at Company" or "@ Company"
    m = re.search(
        r"(?:^|\s)(?:at|@)\s+(.+?)(?:\s*[|,\-]|$)",
        clean_title,
        re.IGNORECASE,
    )
    if m:
        result = _clean_company(m.group(1))
        if result:
            return result

    # Pattern 2: split by delimiters and pick the best company-looking segment
    segments = re.split(r"\s*[|,]\s*", clean_title)
    if len(segments) >= 2:
        candidates = [
            seg.strip() for seg in segments
            if seg.strip() and len(seg.strip()) >= 2 and not _is_role_word(seg.strip())
        ]
        if candidates:
            best = min(candidates, key=len)
            result = _clean_company(best)
            if result:
                return result

    # Pattern 3: trailing comma pattern — "Role, Company"
    m = re.search(r",\s+([A-Z][\w\s&.]+?)\s*$", clean_title)
    if m:
        result = _clean_company(m.group(1))
        if result:
            return result

    return None


def classify_bucket(title: str) -> str:
    """Assign a job-function bucket based on title keywords."""
    if not title:
        return "other"

    lowered = title.lower()
    for bucket_name, patterns in _COMPILED:
        if not patterns:
            continue
        for pat in patterns:
            if pat.search(lowered):
                return bucket_name
    return "other"


def normalize_company(name: str) -> str:
    lowered = name.lower().strip()
    lowered = COMPANY_SUFFIXES.sub("", lowered).strip()
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered


# ---------- Main ----------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Classify engager titles: parse company, assign job bucket, flag internal.",
    )
    parser.add_argument("--reclassify", action="store_true",
                        help="Reclassify ALL engagers (not just unclassified)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview results without writing to the database")
    args = parser.parse_args()

    conn = get_db()

    # Load sources for internal-flag detection. The sources table can store
    # (id, name, company, handle); no author_handle/author_company.
    source_rows = conn.execute(
        """SELECT id, name, company
           FROM sources
           WHERE (name IS NOT NULL OR company IS NOT NULL)
             AND relevance IN ('competitor', 'thought-leader', 'founder', 'named-account')"""
    ).fetchall()
    source_companies = {}
    for s in source_rows:
        for label in (s["company"], s["name"]):
            if label:
                source_companies[s["id"]] = normalize_company(label)
                break

    if args.reclassify:
        engagers = conn.execute(
            "SELECT id, title FROM engagers WHERE title IS NOT NULL AND title != ''"
        ).fetchall()
    else:
        engagers = conn.execute(
            "SELECT id, title FROM engagers "
            "WHERE title IS NOT NULL AND title != '' AND job_bucket IS NULL"
        ).fetchall()

    print(f"Classifying {len(engagers)} engagers...")

    stats = {"company_parsed": 0, "internal": 0, "buckets": {}}

    for eng in engagers:
        company = parse_company(eng["title"])
        bucket = classify_bucket(eng["title"])

        is_internal = 0
        if company:
            stats["company_parsed"] += 1
            norm_company = normalize_company(company)
            engaged_source_ids = conn.execute(
                "SELECT DISTINCT source_id FROM engagements "
                "WHERE engager_id = ? AND source_id IS NOT NULL",
                (eng["id"],),
            ).fetchall()
            for row in engaged_source_ids:
                src_norm = source_companies.get(row["source_id"])
                if src_norm and (src_norm in norm_company or norm_company in src_norm):
                    is_internal = 1
                    stats["internal"] += 1
                    break

        stats["buckets"][bucket] = stats["buckets"].get(bucket, 0) + 1

        if not args.dry_run:
            conn.execute(
                "UPDATE engagers SET job_bucket = ?, parsed_company = ?, is_internal = ? WHERE id = ?",
                (bucket, company, is_internal, eng["id"]),
            )

    if not args.dry_run:
        conn.commit()

    print(f"\nCompanies parsed: {stats['company_parsed']}/{len(engagers)}")
    print(f"Internal flagged: {stats['internal']}")
    print("\nJob bucket distribution:")
    for bucket, count in sorted(stats["buckets"].items(), key=lambda x: -x[1]):
        print(f"  {bucket}: {count}")

    if args.dry_run:
        print("\n[DRY RUN; no changes written]")

    return 0


if __name__ == "__main__":
    sys.exit(main())
