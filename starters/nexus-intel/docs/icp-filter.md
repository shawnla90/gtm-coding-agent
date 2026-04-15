# ICP Filter Cascade

Every engager surface filters to ICP by default. The raw DB is noisy. Scraped commenters include students, retirees, competitors' employees, bots, and people who are just loud. Surfacing non-ICP hurts outreach quality and wastes operator attention.

## Canonical predicate

An engager is ICP if **either** of these holds:

1. `icp_scores.overall_stars >= 3`: strong fit across the 4-dim ICP model (persona, company, engagement, budget), OR
2. `engagers.job_bucket LIKE '<your-primary-vertical>-%'`: persona match even if not star-scored yet.

Stored in `src/lib/db.ts` as `ICP_ENGAGER_PREDICATE`. Do not inline the string elsewhere. Extend the constant if the rule evolves.

### Why a union, not just stars

Only about 10% of engagers have `overall_stars >= 3` by default. Scraped commenters who haven't been run through `score_icp.py` sit at 0 stars, but their `job_bucket` classification already encodes "is this the right persona." The union catches both "scored and strong" and "not yet scored but clearly the right fit."

## Where the filter applies (default ON)

| Function in `src/lib/db.ts` | Default | How to override |
|---|---|---|
| `getEngagers()` | ICP only | Pass `{ includeNonIcp: true }` |
| `getLeads()` | ICP only | Pass `{ includeNonIcp: true }` |
| `getTopEngagersForSource()` | ICP only | Pass `{ includeNonIcp: true }` |
| `getSignalsByEngager()` | All (for admin views) | N/A |

## Tuning the cascade for your vertical

Replace the default persona prefix with your primary bucket. Define those buckets in `scripts/classify_titles.py`:

```python
JOB_BUCKETS = {
    "saas-founder": ["founder", "ceo", "cto"],
    "gtm-leader":   ["vp sales", "vp marketing", "cro", "cmo"],
    "revops":       ["revenue operations", "rev ops", "gtm ops"],
    # Add your vertical's primary buckets.
}
```

Then update the predicate in `src/lib/db.ts`:

```typescript
export const ICP_ENGAGER_PREDICATE = `
  (icp.overall_stars >= 3 OR e.job_bucket LIKE 'saas-founder-%')
`;
```

## When the filter is the wrong default

- **Admin views** (sources management, raw data inspection) should show everything. Use `includeNonIcp: true`.
- **New-dataset bootstrapping:** when your DB has < 500 engagers, `overall_stars >= 3` hasn't hit statistical weight yet. Loosen to `>= 2` temporarily.
- **Experimental persona** you're testing: add a new job bucket and include it in the union before you have scored data.

## How to audit the filter's effect

```bash
sqlite3 data/intel.db "SELECT COUNT(*) FROM engagers"
sqlite3 data/intel.db "SELECT COUNT(*) FROM engagers e LEFT JOIN icp_scores icp ON e.id = icp.engager_id WHERE (icp.overall_stars >= 3 OR e.job_bucket LIKE 'your-prefix-%')"
```

The ratio is your ICP density. < 20% means the raw DB is too noisy, revisit your scrape targets. > 60% means the filter is too loose, tighten it.
