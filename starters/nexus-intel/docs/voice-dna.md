# Voice DNA + Scoring Calibration

The starter ships with generic defaults in the scoring and prompt layers. Replace them with your own calibration. Calibration is why two instances of Nexus Intel never surface the same signals.

## What to calibrate

| File | What's in it | What you change |
|---|---|---|
| `scripts/score_icp.py` | 4-dim ICP scoring scaffold | Coefficient weights for persona, company, engagement, budget |
| `scripts/_decay.py` | Signal half-life table | Half-life and max-age for each signal type in your taxonomy |
| `scripts/classify_titles.py` | Job title to bucket map | Your persona buckets (e.g. `saas-founder`, `revops-leader`) |
| `scripts/analyze_content.py` | Claude prompt for signal extraction | Your signal taxonomy and voice rules |
| `scripts/generate_insights.py` | Claude prompt for outreach briefs | Your voice, your CTA style, your account-specific context |
| `data/icp-profile.json` | Persona keywords and competitor list | Your ICP config |

## The four dimensions of ICP

Every engager gets scored on four axes (1 to 5 stars each):

1. **Persona.** Is this the right job title, role, and seniority?
2. **Company.** Is the employer the right size, vertical, and stage?
3. **Engagement.** Are they actively discussing your space? Posting, commenting, sharing?
4. **Budget.** Can they (or do they influence) the buying decision?

`overall_stars` is the average of the four, rounded to nearest half. A 3 is "worth outreach." A 5 is "stop everything."

## Signal taxonomy

The default `_decay.py` ships with six generic signals: pricing-complaint, feature-gap, churn-signal, hiring-signal, product-launch, leadership-change.

Replace with your own. For a vendor of observability tooling, it might be: outage-postmortem, alerting-fatigue, cost-creep, k8s-migration. For an HR tech vendor: attrition-spike, comp-freeze, ATS-switch, hiring-hold.

A good signal taxonomy has:

- **5 to 12 signal types.** Fewer misses opportunities; more is noise.
- **Mutually exclusive categories.** If a post could be tagged with three types, your taxonomy is ambiguous.
- **An obvious "act-now" subset.** At most 2 to 3 types should trigger high-priority outreach; the rest are context.

## Claude prompt rules

The prompts in `analyze_content.py` and `generate_insights.py` are where your voice lives. Principles that hold across verticals:

1. **Give Claude the signal taxonomy inline in the system prompt.** Don't assume it will infer.
2. **Give Claude `age_days`.** Fresh signals matter more than old ones. The model can't reason about freshness without seeing it.
3. **Constrain output to JSON with a schema.** Free-form text is expensive to post-process.
4. **Show 3 to 5 few-shot examples.** Calibration is easier than instruction.
5. **Keep voice rules terse.** A prompt over 400 tokens is usually hiding a taxonomy problem.

## Anti-slop rules

If you are generating outbound copy from these insights, layer an anti-slop pass. Patterns to catch:

- Em dashes (a dead AI giveaway).
- "Game changer", "no fluff", "chaos": overused in AI output.
- Opening with "I came across your profile..." kills reply rates.
- Closing with "Looking forward to hearing back" is filler.
- Multi-clause sentences that bury the ask.

Implement as a post-generation validator that flags patterns and either auto-rewrites or rejects back to Claude for another pass.

## Calibration workflow

1. **Ship with generic weights.** Run a scrape. Look at the top 20 signals by priority.
2. **Hand-label 20 of them.** "Would I actually reach out?" Yes/no.
3. **Adjust the coefficients** to match your labels. Usually it is one dimension (engagement, say) weighted too high.
4. **Re-run.** Look at the new top 20. Iterate until the top-20 match your yes/no labels at > 70% precision.
5. **Lock the weights for 2 weeks.** Run daily scrapes, send outreach based on the output, measure reply rate.
6. **Re-calibrate monthly.** Verticals drift, signal value changes, your own positioning evolves.

## Where voice DNA lives across the repo

- `scripts/analyze_content.py`: competitive signal detection voice.
- `scripts/generate_insights.py`: outbound brief voice.
- `data/icp-profile.json`: who you sell to, in your words.
- `scripts/classify_titles.py`: your persona language.

Keep them in sync. If `icp-profile.json` names a persona as "growth-leader" but `classify_titles.py` buckets it as "marketing-leader", the filter cascade misfires.
