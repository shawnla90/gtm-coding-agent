# The engine

This starter is a thin pipeline over four reusable pieces. Each one does a single job, holds no client data, and re-points at a different market by editing a list. This doc explains what they are so you can reuse them beyond this starter.

## `lib/reddit_client.py` - the Reddit source

A thin, polite client for the reddit34 RapidAPI. It pulls the buyer talk that AI models read and cite: posts by subreddit, posts by keyword search, and the top comments on a thread. It reads the key from `RAPIDAPI_KEY`, sleeps between calls to stay under the rate limit, retries transient errors, and backs off on 429, so a long pull does not get you throttled.

Four confirmed endpoints, wrapped as four functions:

| Function | Endpoint | What it returns |
|----------|----------|-----------------|
| `search(query)` | `getSearchPosts` | keyword search across all of Reddit |
| `posts_by_subreddit(sub, sort)` | `getPostsBySubreddit` | newest or hot posts in a subreddit |
| `top_posts_by_subreddit(sub, window)` | `getTopPostsBySubreddit` | top posts in a time window |
| `comments(permalink)` | `getPostCommentsWithSortV2` | top comments on one thread (needs the FULL url) |

Each returns a flat list of dicts, tolerating the API's nested shape. Swap this module for a different data source (an official API, a scraper, a Clearbox export) and the rest of the pipeline does not change, because everything downstream reads from SQLite, not from the client.

## `lib/relevance.py` - the vocabulary and the filters

The single file that points the whole engine at a market. Editing the lists here re-targets everything upstream and downstream.

- **`BRANDS`** the tools your buyers compare you against. `brands_in(text)` returns which ones a thread mentions, canonicalized.
- **`CATEGORY`** the category nouns that prove a thread is on-topic. `is_relevant(text)` is `True` only if the text names a brand or a category noun, which is what keeps off-topic subreddits (careers, gaming, politics) out of the database at ingest.
- **`TOPIC_KEYWORDS`** maps keywords to topic slugs. `auto_tags(text)` returns the topics a thread or quote belongs to, which is how buyer language clusters into content topics.
- **`classify(text)`** returns the buyer-language kind: `comparison`, `pain`, `recommendation`, `question`, or `None`. Comparisons and recommendations are the highest-intent buyer talk, and they drive the intent score.

Because `pull.py` and `mine.py` both import this file, the same definition of "relevant" gates ingestion and classification. One edit, whole engine re-pointed.

## `lib/sheet_engine.py` - the color-coded sheet builder

The developed, reusable piece, vendored from the market-scoring starter. A single config-driven module that turns pandas DataFrames into an interactive Google Sheet: a red-to-green score gradient, categorical color maps for tiers and kinds, banding, a frozen header, filters, sized columns, a styled dashboard tab, anyone-with-link sharing, and rebuild-in-place by sheet id so a shared link stays valid.

It is pure: no file I/O, no argv. The thin builder (`build_sheet.py`) owns the data and the paths and calls `build(config)`. See the market-scoring starter's [ENGINE.md](../market-scoring-sheet/ENGINE.md) for the full config schema and the palette. This starter reuses it unchanged, which is the point: one styling engine, identical output across every sheet in the kit.

## The scoring model - `score.py`

Transparent rules, not a black box. Every content topic gets a 0-100 total from four dimensions, mapped to a 1-5 score and an A-D tier:

| Dimension | Range | What it rewards |
|-----------|-------|-----------------|
| search intent | 0-35 | comparisons and recommendation asks score highest |
| buyer-talk volume | 0-25 | how many threads touched the topic |
| brand fit | 0-18 | topic maps to a tool in the `CARRIED` set you can win against |
| citation potential | 0-15 | thread engagement, scaled to a fresh 30-day corpus |

`85+` is a 5 (A tier, publish first), down to `<40` for a 1 (D tier). The dimensions are four small functions; edit the point maps to weight your market differently. Each row also gets a one-line `topic_reason` stitched from the dimension labels, so the sheet explains itself.

## The data contract

Everything flows through SQLite (`data/signals.db`), so each stage is independent and idempotent. Four tables:

- **`reddit_threads`** raw threads, deduped by `external_id`, gated by recency and relevance at insert.
- **`thread_comments`** top comments on high-engagement threads (buyer language lives here too).
- **`buyer_language`** extracted questions, comparisons, and pains, each tagged with a kind and the brands it mentions.
- **`content_topics`** the scored plan: clustered topics with intent, mentions, engagement, evidence, score, tier, and reason.

Because state lives in the database and not in memory, you can re-run any single stage. Re-mine without re-pulling, re-score without re-mining, rebuild the sheet without touching anything else.
