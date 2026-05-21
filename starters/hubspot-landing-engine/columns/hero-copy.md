---
column_slug: hero-copy
model: opus
inputs:
  - account.company
  - account.contact_title
  - hook-angle.hook
  - pain_points.primary
  - brief.cta_label
  - brief.brand_tone
output_schema:
  headline: string      # the hook, polished for hero display
  subhead: string       # one sentence, under 25 words
  cta_label: string     # the button text, 2-5 words
  body_block: string    # 2-3 sentence pitch for the page body, anchored to pain
---

You are writing the landing-page hero block for the named account. You have
already received the hook from hook-angle. Polish it for hero display and
extend with a subhead and a body block.

Constraints:

- `headline` is the hook lightly polished. Do not redo it from scratch.
- `subhead` is one sentence under 25 words. It must add specificity, not
  restate the headline.
- `cta_label` defaults to the brief's cta_label. Override only if a
  shorter, more-specific verb fits.
- `body_block` is two or three short sentences. Practitioner voice. No
  superlatives. No hype.
- No em-dashes. No banned phrases.

Return ONLY a JSON object.
