---
brief_slug: your-brief-slug
campaign: your-campaign-name
template_module: landing-page
audience: "Who this brief targets (one sentence)"
pain_points_focus:
  - "primary pain"
  - "secondary pain"
cta_label: "Book a 15-min walkthrough"
cta_url: "https://meetings.hubspot.com/yourname/walkthrough"
deliverable_theme: "what-you-build"
brand_tone: "practitioner, not salesy"
length_hint: 400
columns_required:
  - pain-points
  - hook-angle
  - hero-copy
  - tech-stack
---

# Hero frame (the variable part of the page)

{{hero_headline}}

{{hero_subhead}}

# Section 1 — diagnostic

{{pain_point_primary_block}}

# Section 2 — what we'd build

{{deliverable_pitch}}

The brief body is the **template-with-holes**. Each `{{variable}}` is filled per
account by one of the columns declared in `columns_required` above.

Plain markdown around the variables stays as-is. The generator passes the filled
body to the HubSpot template's `body_rich_text` module.

## Notes for the column agents

This section is read by the column subagents as context for the brief. Tell them
what success looks like, what to avoid, what brand voice to hold.

- Voice: practitioner. No hype, no superlatives.
- Specificity: every claim should reference something real about the account.
- Length: keep the hero subhead under 25 words. Diagnostic block 60-90 words.
- Banned phrases: see `columns/README.md` for the canonical list.
