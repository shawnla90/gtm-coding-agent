# Signal Decay + Time-to-Action

**Time to action matters more than the signal itself.** A perfect insight about a 9-month-old post is worse than a mediocre insight about yesterday's. Every signal row in Nexus Intel must reference the publication date of the underlying content, not the timestamp of when we analyzed it.

## Three non-negotiables

1. **Every signal row joins to a dated content item.** Display the post publication date, not the analysis timestamp. `created_at` lies. It is when we analyzed the post, not when it was written.
2. **The analyzer and insight generator MUST see `age_days` in the Claude context.** If Claude can't see the age, Claude can't reason about freshness. Put it in the payload, reference it in the system prompt, enforce it server-side.
3. **Every signal type has a half-life plus a max-age.** Default rules live in `scripts/_decay.py` and are intentionally generic. Replace them with your own vertical's cadence.

## The decay rules

Defined in `scripts/_decay.py`:

```python
DECAY_RULES = {
    # Defaults. Override per your vertical's cadence.
    "pricing-complaint":     {"halflife_days": 30, "max_age_days": 180},
    "feature-gap":           {"halflife_days": 45, "max_age_days": 180},
    "churn-signal":          {"halflife_days": 14, "max_age_days": 90},
    "hiring-signal":         {"halflife_days": 30, "max_age_days": 120},
    "product-launch":        {"halflife_days": 14, "max_age_days": 60},
    "leadership-change":     {"halflife_days": 60, "max_age_days": 365},
    # Add your own taxonomy here. See docs/voice-dna.md.
}
```

`halflife_days` is the age at which the signal's priority score drops by 50%.
`max_age_days` is the age beyond which the signal stops triggering outreach insights entirely.

## How the age plumbing works

1. **Scrape.** Every `content_items` row gets a `published_at` from the source (LinkedIn post date, Reddit thread date, tweet date). If the source didn't expose a date, store `NULL` and the decay defaults to "treat as stale."
2. **Analyze.** `analyze_content.py` passes `age_days = (today - published_at).days` into the Claude system prompt. The prompt is constrained to reference age in its competitive-signal output.
3. **Score.** `score_icp.py` applies the half-life decay: `priority *= 0.5 ** (age_days / halflife_days)`.
4. **Display.** UI components render `published_at`, not `created_at`. `src/components/freshness-pill.tsx` shows "2d ago", "3 months ago", etc.
5. **Insights.** `generate_insights.py` refuses to emit an `act-now` brief on content older than `max_age_days`.

## When to tune

- **Your outbound motion is fast (daily touches):** shrink half-lives to 7 to 14 days. Old signals create low-quality briefs.
- **Your market is slow-moving (enterprise, regulated):** extend half-lives to 60 to 120 days. A pricing complaint from 6 months ago might still be actionable.
- **You are testing a new signal type:** start with generous defaults (30/180), watch which convert, shrink the halflife of the winners.

## Signal freshness UI conventions

- **Green (≤ halflife):** fresh, display prominently.
- **Yellow (≤ max_age):** aging, surface with a subdued visual.
- **Red (> max_age):** stale, hide from the default feed unless the user explicitly requests.

See `src/components/freshness-pill.tsx`.
