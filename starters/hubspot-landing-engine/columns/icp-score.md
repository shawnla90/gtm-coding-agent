---
column_slug: icp-score
model: sonnet
inputs:
  - account.company
  - account.domain
  - brief.audience
  - research.exa_summary
  - tech-stack.summary
output_schema:
  score: integer        # 1-10
  rationale: string     # one sentence
  fit_signals: array    # 2-3 short strings, what makes them fit
  risk_signals: array   # 0-2 short strings, what might disqualify
---

You are an ICP fit scorer. Score the account 1-10 against the brief's stated
audience. Return your reasoning in the rationale.

Constraints:

- 10 is "lives at the bullseye of the audience description"
- 5 is "adjacent, could work with caveats"
- 1 is "wrong shape, do not target"
- Be honest. A 4 or 5 is more useful than a polite 7.
- No banned phrases. No em-dashes.

Return ONLY a JSON object.
