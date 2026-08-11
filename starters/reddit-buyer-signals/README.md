# Reddit Buyer Signals

This portable curriculum starter turns Clearbox-classified Reddit opportunities into a local, source-linked content plan. Clearbox owns the opportunity disposition and exact permalink. The starter teaches the import, mining, scoring, and reporting pattern without adding a parallel Reddit discovery source.

The maintained eleven-view client-pack builder, public demo, Notion guide, and agency operations live in [ClearboxGTM](https://github.com/shawnla90/ClearboxGTM).

## The architecture

```text
Clearbox offer
    ↓
complete opportunity export
    ↓
id + kind + exact Reddit permalink
    ↓
local SQLite → buyer language → topic scores
    ↓
Google Sheet + optional deck
```

## Source contract

Every imported opportunity must keep:

- `id`: stable Clearbox opportunity identifier
- `kind`: `lead`, `engage`, or `competitor`
- `url` or `permalink`: exact Reddit source URL

`pull.py` refuses truncated exports, missing identifiers, invalid dispositions, and missing source URLs. It imports data only. It does not discover Reddit content, post, vote, send DMs, or mark work complete.

## Run the synthetic offline path

```bash
cd starters/reddit-buyer-signals
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
bash run.sh --offline
```

The bundled fixture is a synthetic Clearbox export. The offline run includes every fixture date so the demo remains stable as it ages. It follows the same source contract as a real build and does not overwrite `data/clearbox_export.json`; live exports still use the recency window.

## Run from a complete Clearbox export

```bash
CLEARBOX_EXPORT=/absolute/path/to/clearbox-opportunities.json bash run.sh
```

The default path is `data/clearbox_export.json`. The local market-read pipeline keeps the last 30 days by default; set `MAX_AGE_DAYS=60` for a wider window.

## What each module does

- **`init_db.py`** creates or migrates the local SQLite database.
- **`pull.py`** imports and validates the complete Clearbox export.
- **`mine.py`** extracts buyer questions, comparisons, pains, and topic clusters.
- **`score.py`** scores topics from 1 to 5 with a visible reason.
- **`build_sheet.py`** renders the lower-level Google Sheet.
- **`build_deck.py`** optionally builds an editable Slides deck.
- **`geo.py`** checks retrieval visibility. It does not claim an AI answer or citation.
- **`competitor.py`** summarizes Clearbox competitor dispositions and labeled generated sentiment.
- **`unmask.py`** applies the public company-disclosure review gate before enrichment.
- **`content.py`** scaffolds drafts and keeps publishing human-authorized.
- **`digest.py`** renders the operator digest and posts only with an explicit flag.

See [ENGINE.md](ENGINE.md) for the data and scoring contracts.

## Connect Google Workspace

Run the one-time OAuth setup before publishing the Sheet or deck:

```bash
python3 setup_oauth.py
```

Rebuilds use the stored document identifiers so shared links remain stable.

## Add an analysis layer

Freckle, Base Loop, Clay, or a local script can add priority scores, tiers, action lanes, buyer language, reply angles, and evidence fields. Those tools do not own the source record. Preserve the Clearbox `id`, `kind`, and exact permalink, and flag any proposed disposition conflict for human review.

For the complete API-to-eleven-view-Sheet-and-Notion workflow, use the [ClearboxGTM client value-pack guide](https://github.com/shawnla90/ClearboxGTM/blob/main/skills/reddit-agency/CLIENT-VALUE-PACK.md).

## Measurement boundary

Keep these receipts separate:

1. exact Reddit artifact health
2. search discovery
3. retrieval visibility
4. observed AI answer appearance
5. exact source citation
6. engagement or business outcome

A retrieval result is not an AI citation. A citation is not proof that one comment caused a recommendation. Every claim stays attached to its own receipt.

## Automation boundary

Importing, analyzing, rebuilding reports, and monitoring may be scheduled. Account creation, Reddit posting, replies, voting, DMs, and completion state remain human-authorized.

---

**Powered by [Clearbox](https://clearbox.to)**. The broader skill pack is in [ClearboxGTM](https://github.com/shawnla90/ClearboxGTM).
