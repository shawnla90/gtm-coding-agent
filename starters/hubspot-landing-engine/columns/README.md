# Columns

Each file in this folder is a focused subagent prompt. The pipeline reads the
list of columns required by the active brief (`columns_required` in its
frontmatter), then runs one subagent per account per column.

Think of each column as a Clay column - except instead of paying per credit for
a generic model, you run Opus-tier models against a controlled target list and
the per-row cost stops being the bottleneck.

## File schema

```markdown
---
column_slug: column-name           # used as the JSON output key
model: opus | sonnet | haiku        # routing hint; pipeline can override
inputs:                             # what the subagent receives
  - account.company
  - account.domain
  - account.contact_title
  - research.exa_summary
output_schema:                      # what the subagent must return
  primary: string
  rationale: string
---

You are an analyst whose only job is to {column purpose}.

Given the inputs, return ONLY a JSON object matching the output_schema above.
No prose, no markdown, no preamble.

{specific instructions...}
```

## Banned phrases (apply across all columns)

The pipeline rejects any column output that contains these. The subagent gets
one retry with the banned-phrase list re-emphasized; on second failure the
account is flagged for manual review.

- em-dashes (—, –). Spaced ` - ` only.
- "game changer", "unleash", "supercharge", "revolutionize", "transform"
- "no fluff", "no BS", "nada"
- "without further ado", "that said", "that being said"
- "let me be clear", "uncomfortable truth", "nobody tells you"
- "here's the thing", "chaos", "what do you think?", "drop a comment"
- "leverage", "synergy", "home run", "fast-paced"

This list is the canonical one from the parent repo's voice-DNA system. Keep
it in sync if you add columns of your own.

## Adding your own column

1. Copy `pain-points.md` to `your-column.md`.
2. Change the `column_slug` and rewrite the instructions for what you want.
3. Add `your-column` to the `columns_required` list in any brief that needs it.
4. Reference the output in your brief body as `{{your_column_primary}}` or
   whatever key you put in `output_schema`.

Done. The pipeline picks it up the next run.
