# Adding a Connector

A connector is a Python script that calls an external data source and writes normalized rows into SQLite. Follow this shape for consistency.

## The three existing connectors

| File | Apify actor | Writes to |
|---|---|---|
| `scripts/scrape_linkedin.py` | `harvestapi/*` | `content_items` (platform='linkedin') |
| `scripts/scrape_x.py` | `apidojo/tweet-scraper` | `content_items` (platform='x') |
| `scripts/scrape_reddit.py` | `trudax/reddit-scraper-lite` | `reddit_threads` |

## The connector contract

Every connector should:

1. **Read a source list from the DB.** `SELECT handle, url FROM sources WHERE platform = ?`. Don't hardcode.
2. **Call the scraper.** Most use `apify call <actor-id> --input-file <json>` via subprocess.
3. **Parse and normalize.** Extract `published_at`, `author`, `content`, `url`, `engagement`. Handle missing fields gracefully.
4. **Dedupe on (source_id, url).** Prevent re-inserting the same post on every run.
5. **Use `INSERT OR IGNORE`.** Safe to re-run without breaking.
6. **Write to `content_items`** (or `reddit_threads` for Reddit, which has thread-level structure).
7. **Log what happened.** `print(f"  +{new} new, {skipped} skipped, {failed} failed")`.

## Skeleton for a new connector

```python
#!/usr/bin/env python3
"""
scrape_<platform>.py: pull content from <platform> via Apify, write to SQLite.
"""
import json
import subprocess
import sys
from pathlib import Path

from _lib import open_db, today_iso

DB_PATH = Path(__file__).parent.parent / "data" / "intel.db"
APIFY_ACTOR = "some-org/some-actor"  # change me


def fetch_posts(handles: list[str]) -> list[dict]:
    """Call the Apify actor with a list of handles. Return list of post dicts."""
    input_payload = {"handles": handles, "max_items_per_handle": 30}
    result = subprocess.run(
        ["apify", "call", APIFY_ACTOR, "--input", json.dumps(input_payload)],
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


def normalize(post: dict) -> dict:
    """Map the actor's output into content_items columns."""
    return {
        "platform": "<platform>",
        "source_handle": post["handle"],
        "url": post["url"],
        "published_at": post.get("publishedAt"),
        "content": post.get("text", ""),
        "author": post.get("authorName"),
        "engagement_likes": post.get("likes", 0),
        "engagement_comments": post.get("comments", 0),
    }


def main() -> None:
    db = open_db(DB_PATH)
    handles = [r["handle"] for r in db.execute(
        "SELECT handle FROM sources WHERE platform = '<platform>'"
    ).fetchall()]

    if not handles:
        print("No sources configured. Add rows to `sources` with platform = '<platform>'.")
        return

    posts = fetch_posts(handles)
    new, skipped = 0, 0
    for post in posts:
        row = normalize(post)
        cur = db.execute("""
            INSERT OR IGNORE INTO content_items
              (platform, source_handle, url, published_at, content, author,
               engagement_likes, engagement_comments, scraped_at)
            VALUES (:platform, :source_handle, :url, :published_at, :content,
                    :author, :engagement_likes, :engagement_comments, :scraped_at)
        """, {**row, "scraped_at": today_iso()})
        if cur.rowcount:
            new += 1
        else:
            skipped += 1
    db.commit()
    print(f"  +{new} new, {skipped} deduped")


if __name__ == "__main__":
    main()
```

## Testing without spending money

Every connector should support a `--dry-run` flag that reads a fixture JSON instead of calling Apify:

```bash
python3 scripts/scrape_linkedin.py --dry-run --fixture tests/fixtures/linkedin-sample.json
```

Keep a 5 to 10 row fixture per platform in `tests/fixtures/` so anyone cloning the repo can verify the pipeline without burning real scrape credits.

## Adding a non-Apify source

If the source doesn't have an Apify actor (custom API, RSS feed, public JSON endpoint), skip the subprocess layer and just `requests.get(...)`. Same contract: read from `sources`, normalize, dedupe, insert, log.

## When to graduate from SQLite

If a new connector pushes the DB over 500 MB or you start hitting SQLite write contention during parallel scrapes, port `_lib.py`'s `open_db()` to open a Postgres connection instead. The schema in `data/schema.sql` is standard SQL. The port is mechanical.
