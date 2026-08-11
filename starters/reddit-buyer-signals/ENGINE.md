# The engine

This starter is a thin pipeline over four reusable pieces, with a client-service layer on top. Each piece does one job, holds no client data, and re-points through the Clearbox offer configuration.

## `pull.py` - the Clearbox source contract

Clearbox is the source of record for Reddit opportunities. `pull.py` imports a complete Clearbox export into local SQLite. Every row must preserve:

| Field | Contract |
|---|---|
| `id` | Stable Clearbox opportunity identifier |
| `kind` | Original `lead`, `engage`, or `competitor` disposition |
| `url` or `permalink` | Exact Reddit source URL |

The importer refuses truncated exports and missing or invalid source fields. The bundled offline fixture follows the same contract. Freckle, Base Loop, and Clay may add analysis downstream, but they may not replace the Clearbox disposition or permalink.

## `lib/relevance.py` - the vocabulary and the filters

The single file that points the whole engine at a market. Editing the lists here re-targets everything upstream and downstream.

- **`BRANDS`** the tools your buyers compare you against. `brands_in(text)` returns which ones a thread mentions, canonicalized.
- **`CATEGORY`** the category nouns that prove a thread is on-topic. `is_relevant(text)` is `True` only if the text names a brand or a category noun, which is what keeps off-topic subreddits (careers, gaming, politics) out of the database at ingest.
- **`TOPIC_KEYWORDS`** maps keywords to topic slugs. `auto_tags(text)` returns the topics a thread or quote belongs to, which is how buyer language clusters into content topics.
- **`classify(text)`** returns the buyer-language kind: `comparison`, `pain`, `recommendation`, `question`, or `None`. Comparisons and recommendations are the highest-intent buyer talk, and they drive the intent score.

`mine.py` uses this vocabulary to classify the imported source text into buyer-language themes. The Clearbox opportunity disposition remains separate and authoritative.

## `lib/sheet_engine.py` - the color-coded sheet builder

The developed, reusable piece, vendored from the market-scoring starter. A single config-driven module that turns pandas DataFrames into an interactive Google Sheet: a red-to-green score gradient, categorical color maps for tiers and kinds, banding, a frozen header, filters, sized columns, a styled dashboard tab, anyone-with-link sharing, and rebuild-in-place by sheet id so a shared link stays valid.

It is pure, with no file I/O and no argv. The thin builder (`build_sheet.py`) owns the data and the paths and calls `build(config)`. See the market-scoring starter's [ENGINE.md](../market-scoring-sheet/ENGINE.md) for the full config schema and the palette. This starter reuses it unchanged, which is the point: one styling engine, identical output across every sheet in the kit.

## The scoring model - `score.py`

Transparent rules, not a black box. Every content topic gets a 0-100 total from four dimensions, mapped to a 1-5 score and an A-D tier:

| Dimension | Range | What it rewards |
|-----------|-------|-----------------|
| search intent | 0-35 | comparisons and recommendation asks score highest |
| buyer-talk volume | 0-25 | how many threads touched the topic |
| brand fit | 0-18 | topic maps to a tool in the `CARRIED` set you can win against |
| citation potential | 0-15 | thread engagement, scaled to a fresh 30-day corpus |

`85+` is a 5 (A tier, publish first), down to `<40` for a 1 (D tier). The dimensions are four small functions; edit the point maps to weight your market differently. Each row also gets a one-line `topic_reason` stitched from the dimension labels, so the sheet explains itself.

## The client-service layer

The four pieces above are the reusable engine. These five modules sit on top and turn the scored signal into an operated client offer: which buyer questions to track, where a competitor is winning, what to send each day, which company evidence is eligible for enrichment, and the content that answers the buyer question. Each re-points by argument.

### `geo.py` - the GEO terms and their retrieval visibility

A "GEO term" is a buyer question a GTM or RevOps leader would type or ask an AI, one the brand can answer with authority. The terms come from the real buyer language the account surfaced, generated into clean queries upstream, or derived from `content_topics` as a fallback. Each term is then checked for current retrieval visibility with a hard-capped Exa pass. This shows whether the brand surfaces in Exa's result set, not whether an answer engine named or cited it. An absent Exa key degrades to terms without a retrieval score. Observed AI visibility requires a separate prompt receipt with the answer and exact citations.

```bash
python3 geo.py --brand "Acme PM" --db data/signals.db --out data/geo_terms.json
```

### `competitor.py` - the competitor narrative from the classification

Clearbox classifies every opportunity as engage, lead, or competitor against the offer's own and competitor brands, so the classification itself is the relevant-mention signal and there is no literal brand-string counting. This rolls the classified ops into a share-of-voice view: where a competitor is the relevant answer versus where the client's category is the open opening, plus a generated sentiment read. Reddit opportunities carry no sentiment field, so the sentiment is produced upstream and labeled as generated.

```bash
python3 competitor.py --own "Acme PM" --competitor "Rival PM" --out data/competitor_analysis.json
```

### `digest.py` - the daily client digest

The operated-service delivery. Each day the account's engage threads (with the drafted, value-first reply), new leads, and competitor mentions land in the client's Slack, as a header line and then one block per opportunity, ordered by priority and capped. It renders to a text file by default; add `--post --webhook-secret <SECRET_NAME>` and it posts to an incoming webhook, with the URL read from the environment variable of that name or an optional `SECRETS_DB` SQLite store. It never posts without `--post`.

```bash
python3 digest.py --client "Acme PM" --out data/slack_digest.txt
python3 digest.py --client "Acme PM" --out data/slack_digest.txt --post --webhook-secret SLACK_WEBHOOK_YOURCLIENT
```

### `unmask.py` - the profile review gate and company enrichment

Reddit is pseudonymous, so this enriches the company, never the person. Only an exact company domain published on the author's own Reddit profile, preserved with its evidence URL and excerpt, is automatically eligible. Search results, domains mentioned in a thread, social links, and brand-like handles are plausible candidates that require manual review. `no_public_evidence` and `lookup_error` remain separate states. Add `--profile` to run the full lookup and `--enrich` to send only eligible domains through the pluggable backend: Freckle by default, swappable for Base Loop, Clay, Deepline, Apollo, or another waterfall. It never enriches without `--enrich`.

```bash
python3 unmask.py --ops data/ops_classified.json --out data/unmasked.json
python3 unmask.py --ops data/ops_classified.json --profile --out data/unmasked.json
python3 unmask.py --ops data/ops_classified.json --profile --out data/unmasked.json --enrich
```

### `content.py` - scaffold and anti-slop-check a content pack

The coding agent writes the words in the brand voice; this scaffolds the pack so the agent has everything it needs, then checks the result. `scaffold` builds three drafts from one buyer question (a LinkedIn post, a Reddit post as a draft, and a long-tail blog with a TL;DR answer block and a Frequently Asked Questions section that emits FAQPage schema), plus a `BRIEF.md` generation brief and a `manifest.json`. The pack is client-scoped, so its manifest disables dispatch and the content stays in the client package. `check` scans a finished draft or a whole pack for banned words, em-dashes, and structural slop, returning a nonzero exit on any flag, which is what makes it usable in a pre-ship gate.

```bash
python3 content.py scaffold --client "Acme PM" --topic "how to keep one source of truth across two CRMs" --out content/pack-01
python3 content.py check content/pack-01/linkedin.md
```

## The data contract

Everything flows through SQLite (`data/signals.db`), so each stage is independent and idempotent. Four tables:

- **`reddit_threads`** Clearbox opportunities, deduped by `external_id`, with `clearbox_kind` and the exact source URL preserved.
- **`thread_comments`** top comments on high-engagement threads (buyer language lives here too).
- **`buyer_language`** extracted questions, comparisons, and pains, each tagged with a kind and the brands it mentions.
- **`content_topics`** the scored plan: clustered topics with intent, mentions, engagement, evidence, score, tier, and reason.

Because state lives in the database and not in memory, you can re-run any single stage. Re-mine without re-pulling, re-score without re-mining, rebuild the sheet without touching anything else.
