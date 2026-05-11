# Chapter 15: Meta Ad Intelligence

**Every competitor ad in the public library is a declared strategy bet. The library does not give you performance metrics. It gives you a decoded map of who they are targeting, what pain they are agitating, and how long they have been willing to pay for that message. This chapter builds the scraper, the classifier, and the dashboard that turns those bets into competitive intelligence.**

---

## Why Public Ad Libraries

Meta Ad Library, Google Ads Transparency Center, TikTok Creative Center, LinkedIn sponsored posts. All transparency tools. All free. All showing you things companies wish you would not look at too carefully.

What they expose:

- Creative text and visual assets
- Landing page URLs
- Platform targeting (Facebook, Instagram, Messenger, Audience Network)
- Run status (active / inactive)
- Start dates (sometimes end dates)
- Advertiser identity

What they do not expose:

- CTR, CPA, ROAS, conversion rate
- Pipeline generated, demos booked
- Backend attribution, audience size
- Budget or spend (except political/social ads in some regions)

The gap between those two lists is the whole point. You cannot know which ad is winning. You can know which message they are betting on. And you can infer performance from duration. An ad running sixty days is either working, branded, or forgotten. Two out of three are useful.

---

## The Taxonomy

Scraping ads is easy. Making them queryable is the hard part. A Notion board full of screenshots does not produce insights. A structured table with eighteen classified columns does.

Here is the schema:

```
advertiser_name        who is running the ad
ad_platform            meta | instagram | messenger | audience-network
ad_url                 link to the ad in the library
landing_page_url       where the ad sends traffic
primary_hook           the first message or angle
persona_targeted       founder | marketer | sales-leader | revops | developer | ...
pain_point             what problem the ad agitates
promised_outcome       what the ad claims you will get
offer_type             demo | free-trial | report | template | webinar | product-signup | ...
funnel_stage           awareness | education | comparison | conversion | retargeting
proof_used             customer-logos | stats | testimonials | case-study | none
category_narrative     what bigger market story they attach to
ad_longevity_signal    new-test | scaling | long-running | unknown
creative_pattern       founder-video | static-graphic | ugc | meme | teardown | carousel | ...
messaging_angle        fear | speed | cost-savings | growth | simplicity | status | urgency | category-shift
counter_positioning    where your product can take the opposite side
content_opportunity    what post or newsletter this insight produces
outbound_angle         how this turns into a cold email or micro-campaign
```

The first fifteen columns are observational. They describe what the ad is. The last three are strategic. They describe what you can do about it.

---

## The Scraper

The Meta Ad Library at `facebook.com/ads/library` is fully public. No login. No API key. Playwright loads the page, scrolls to get lazy-loaded cards, and extracts text content, start dates, and landing page URLs.

```python
AD_LIBRARY_BASE = "https://www.facebook.com/ads/library/"

def build_ad_library_url(search_term: str) -> str:
    params = {
        "active_status": "active",
        "ad_type": "all",
        "country": "US",
        "q": search_term,
    }
    query = "&".join(f"{k}={quote_plus(str(v))}" for k, v in params.items())
    return f"{AD_LIBRARY_BASE}?{query}"
```

Search by advertiser name. Wait for results. Scroll to load more. Extract per card.

The scraper uses the same stealth pattern from the newsletter follower scraper in Chapter 12. Override `navigator.webdriver`, set a real User-Agent, add `human_pause()` between navigations. Meta does light bot detection on the library, but nowhere near as aggressive as LinkedIn.

```bash
# Single company
python3 scripts/scrape_meta_ads.py --company "Apollo.io"

# All targets
python3 scripts/scrape_meta_ads.py --all

# Dry-run
python3 scripts/scrape_meta_ads.py --all --dry-run
```

Target list is a dictionary of company names to search terms. Add yours:

```python
TARGET_COMPANIES = {
    "Reddit": {"search": "Reddit", "source_match": "reddit"},
    "Clay": {"search": "Clay", "source_match": "clay"},
    "Apollo.io": {"search": "Apollo.io", "source_match": "apollo"},
    # Add your competitors here
}
```

Dedup is handled by a UNIQUE constraint. Re-runs do not double-count.

---

## The Classifier

Raw ads are text. Classified ads are intelligence. Claude does the classification.

The system prompt describes all eighteen taxonomy fields with enumerated options where they exist. The model receives the creative text, advertiser name, and landing page URL, and returns structured JSON.

The classifier uses `claude -p --model sonnet` as a subprocess. Same pattern from Chapter 14. The CLI binary inherits your Claude Code Max auth, so classification bills against your subscription, not the API. No API key needed.

```python
def classify_batch(ads):
    full_prompt = f"{SYSTEM_PROMPT}\n\n---\n\n{format_ads(ads)}"
    result = subprocess.run(
        ["claude", "-p", "--model", "sonnet"],
        input=full_prompt,
        capture_output=True, text=True, timeout=120,
    )
    return json.loads(result.stdout)
```

Five ads per batch. Each ad is roughly 200-500 tokens. Output is a JSON array matching the taxonomy. Total cost: zero marginal, billed against the subscription you already pay for.

The three strategic columns — counter-positioning, content opportunity, outbound angle — are the payload. The prompt instructs Claude to generate them specifically for your company's positioning. Generic output is useless. The prompt needs to know who you are and what you sell.

```bash
# Classify all unclassified ads
python3 scripts/classify_meta_ads.py

# Specific advertiser
python3 scripts/classify_meta_ads.py --advertiser Clay

# Preview only
python3 scripts/classify_meta_ads.py --dry-run
```

---

## The Schema

The `meta_ads` table is standalone. It does not extend `content_items` from Chapter 12. Eighteen taxonomy columns do not belong in a general-purpose content table where they would be NULL for every non-ad row.

```sql
CREATE TABLE meta_ads (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  advertiser_name TEXT NOT NULL,
  source_id INTEGER REFERENCES sources(id),
  ad_platform TEXT DEFAULT 'meta',
  ad_url TEXT,
  landing_page_url TEXT,
  ad_start_date TEXT,
  creative_text TEXT,
  -- 13 taxonomy columns (Claude-classified)
  primary_hook TEXT,
  persona_targeted TEXT,
  pain_point TEXT,
  -- ...
  counter_positioning TEXT,
  content_opportunity TEXT,
  outbound_angle TEXT,
  -- housekeeping
  classified_at TEXT,
  batch_id INTEGER REFERENCES refresh_batches(id) DEFAULT 0,
  UNIQUE(advertiser_page_id, ad_url)
);
```

The `batch_id` column follows the same approval gate from Chapter 12. New scrapes are held until you approve the batch. The `source_id` FK links to your existing competitors in the `sources` table when a match exists.

Ad longevity is computed locally, not by Claude. Delta between `ad_start_date` and scrape date. Under seven days: `new-test`. Seven to thirty: `scaling`. Over thirty: `long-running`. This keeps the classifier focused on the semantic analysis and avoids wasting tokens on date math.

---

## The Dashboard

A new page at `/competitive/ads` in the Next.js app. Server component, same pattern as the threats page.

```
KPI row: Total Ads | Advertisers | Classified | Content Opps
Filters: Funnel stage badges, advertiser badges
Grid:    2-column ad cards with taxonomy badges and strategic columns
```

Query functions follow the same `approvedBatchClause` pattern from the rest of the competitive dashboard. Read-only `getDb()`. Color maps for funnel stages, creative patterns, messaging angles, and longevity signals.

The page surfaces the strategic output front-and-center. Counter-positioning opportunities in green. Content opportunities in cyan. Outbound angles in amber. The observational taxonomy is context. The three strategic columns are the action items.

---

## Pairing Ads with Demand Signals

This is the edge Chapter 12 did not cover.

Ads tell you what competitors are saying. Reddit threads tell you what the market is actually asking. GitHub stars tell you what developers care about. Newsletter engagement tells you what buyers read.

When a competitor runs a "find your customers on Reddit" ad and three active threads on r/startups say "how do I find where my users hang out," you have something no ad library gives you alone: a validated attack angle.

The comparison:

```
Declared strategy (ads)    What competitors want the market to believe
Actual demand (Reddit)     What the market says when nobody is selling to them
Your positioning           The gap between those two
```

Cross-reference your `meta_ads` table with the `content_items` table from Chapter 12. Look for pain points that appear in both competitor ads and community discussions. Those intersections are where your next campaign lives.

A competitor running a "growth" messaging angle when the market is actually asking about "simplicity" is a positioning gap you can exploit. The ad tells you they are pushing growth. The threads tell you buyers want less complexity. Your counter-position writes itself.

---

## Anti-patterns

**Copying creative instead of decoding strategy.** The point is not to steal the ad. The point is to understand the bet behind it.

**Treating longevity as absolute.** Some companies forget to pause ads. Some run evergreen brand campaigns. Duration is a signal, not a verdict.

**Over-indexing on one competitor.** Map the full landscape. Five competitors with ads targeting the same persona and pain point tells you the category narrative. One competitor with a unique angle tells you they see something others do not.

**Scraping daily.** Once a week is enough. Ads do not change hourly. Weekly scrapes give you trend data. Daily scrapes give you noise.

**Saving screenshots instead of structured data.** A screenshot is a record. A classified row is intelligence. The difference is whether you can query it.

---

## Closing Exercise

Run the scraper against one competitor. Twenty minutes. No classifier yet.

1. Pick one competitor who runs Meta ads. Search their name in the Ad Library manually to confirm.
2. Run `python3 scripts/scrape_meta_ads.py --company "CompanyName" --dry-run` to see what the scraper extracts.
3. Run it live: `python3 scripts/scrape_meta_ads.py --company "CompanyName"`.
4. Query the output: `sqlite3 data/content-intel.db "SELECT advertiser_name, creative_text, ad_start_date FROM meta_ads LIMIT 5"`.
5. Read the creative text. Before running the classifier, write down your own guess for persona, pain point, and funnel stage. Then run `python3 scripts/classify_meta_ads.py` and compare.

The gap between your guess and the classifier's output tells you whether the taxonomy is calibrated for your market. Adjust the system prompt if it is not.

---

## Key Takeaways

- Public ad libraries give you creative, landing pages, platforms, and duration. They do not give you performance metrics. That is the feature, not the bug.
- Eighteen columns turn a raw ad into queryable intelligence. The first fifteen are observational. The last three are strategic.
- Duration is the one performance proxy in the public library. Under seven days is a test. Over thirty days is a declared bet.
- The scraper is Playwright, not an API. The library is public. No auth needed.
- Claude classifies in batches. Five ads per call. The strategic columns need your company context in the prompt to be useful.
- The real play is pairing ads with demand signals. Declared strategy versus actual demand. The gap is your positioning.

---

**Next:** Return to the [README.md](../README.md) for chapter selection, or revisit [Chapter 12 - Competitive Intel Engine](./12-competitive-intel-engine.md) which provides the database and dashboard this chapter extends.
