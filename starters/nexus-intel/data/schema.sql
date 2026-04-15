-- Nexus Intel — SQLite Schema
-- Competitive intelligence for any B2B GTM vertical.
-- Focus: competitor moves, thought-leader signals, community pain points,
--        engagement patterns, and time-decayed outreach insights.

CREATE TABLE IF NOT EXISTS sources (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  platform TEXT NOT NULL CHECK(platform IN ('x', 'linkedin', 'reddit', 'blog', 'podcast', 'newsletter', 'other')),
  handle TEXT,                   -- @handle for x, profile slug for linkedin
  url TEXT,                      -- canonical profile or company url
  name TEXT NOT NULL,            -- display name (company or person)
  title TEXT,                    -- person title (null for company sources)
  company TEXT,                  -- person company (null for company sources)
  followers INTEGER,
  country TEXT,                  -- state/region code (US-FL, US-TX, etc.)
  profile_image_url TEXT,        -- linkedin/x/etc. CDN URL; see docs/icp-filter.md and LinkedInAvatar component
  relevance TEXT NOT NULL CHECK(relevance IN ('competitor', 'thought-leader', 'founder', 'community', 'customer', 'named-account')),
  tier TEXT CHECK(tier IN ('tier-1', 'tier-2', 'adjacent', 'global')),
  verticals TEXT,                -- CSV: class-a,class-b,student,senior-living,mixed-use
  status TEXT CHECK(status IN ('active', 'paused', 'dismissed')) DEFAULT 'active',
  notes TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now')),
  UNIQUE(platform, handle)
);

CREATE TABLE IF NOT EXISTS content_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_id INTEGER REFERENCES sources(id),
  platform TEXT NOT NULL,
  external_id TEXT,
  url TEXT,
  content_type TEXT CHECK(content_type IN ('post', 'thread', 'article', 'comment', 'reply', 'video', 'newsletter')),
  title TEXT,
  body TEXT,
  published_at TEXT,
  engagement_likes INTEGER DEFAULT 0,
  engagement_comments INTEGER DEFAULT 0,
  engagement_shares INTEGER DEFAULT 0,
  engagement_views INTEGER DEFAULT 0,
  scraped_at TEXT DEFAULT (datetime('now')),
  scrape_run_id INTEGER REFERENCES scrape_runs(id),
  UNIQUE(platform, external_id)
);

CREATE TABLE IF NOT EXISTS topics (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  category TEXT CHECK(category IN (
    'sales-intelligence',
    'gtm-engineering',
    'outbound-strategy',
    'ai-sales-tools',
    'data-enrichment',
    'revenue-ops',
    'competitor-intel',
    'content-marketing'
  )),
  description TEXT
);

CREATE TABLE IF NOT EXISTS content_topics (
  content_id INTEGER REFERENCES content_items(id),
  topic_id INTEGER REFERENCES topics(id),
  confidence REAL DEFAULT 1.0,
  PRIMARY KEY(content_id, topic_id)
);

CREATE TABLE IF NOT EXISTS signals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  signal_type TEXT CHECK(signal_type IN (
    'content-angle',        -- topic Apollo could use in content
    'engagement-hook',      -- high-engagement post from ICP audience
    'audience-pain-point',  -- sales pros frustrated with tooling/data
    'positioning',          -- competitor narrative shift
    'vulnerability',        -- competitor weakness surfacing publicly
    'trend',                -- emerging GTM trend
    'product-launch',       -- competitor new feature/pricing
    'content-gap',          -- topic competitors aren't covering
    'opportunity',          -- concrete business opportunity
    'partnership'           -- competitor partnership/integration
  )),
  source_id INTEGER REFERENCES sources(id),
  content_id INTEGER REFERENCES content_items(id),
  title TEXT NOT NULL,
  description TEXT,
  urgency TEXT CHECK(urgency IN ('act-now', 'this-week', 'this-month', 'backlog')) DEFAULT 'backlog',
  status TEXT CHECK(status IN ('new', 'acknowledged', 'acted-on', 'dismissed')) DEFAULT 'new',
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS scrape_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  target TEXT,
  platforms TEXT,
  items_ingested INTEGER DEFAULT 0,
  sources_added INTEGER DEFAULT 0,
  started_at TEXT DEFAULT (datetime('now')),
  completed_at TEXT
);

CREATE TABLE IF NOT EXISTS reddit_threads (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  external_id TEXT UNIQUE,       -- reddit thread id (t3_xxx)
  subreddit TEXT NOT NULL,
  title TEXT NOT NULL,
  url TEXT NOT NULL,
  permalink TEXT,
  author TEXT,
  body TEXT,
  score INTEGER DEFAULT 0,
  num_comments INTEGER DEFAULT 0,
  created_utc TEXT,
  topic_tags TEXT,               -- CSV of topic names
  scraped_at TEXT DEFAULT (datetime('now')),
  scrape_run_id INTEGER REFERENCES scrape_runs(id)
);

-- SDR-actionable insights generated from signals by generate_insights.py
-- Each insight is a ready-to-share brief: headline, context, outreach angle, opener.
CREATE TABLE IF NOT EXISTS insights (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  signal_id INTEGER REFERENCES signals(id),
  source_id INTEGER REFERENCES sources(id),
  target_account TEXT,           -- target company or persona to pitch
  vertical TEXT,                 -- sales-intelligence | outbound | revenue-ops | data-enrichment | engagement
  headline TEXT NOT NULL,        -- 1-line "why this matters"
  why_it_matters TEXT,           -- 2-3 sentence context specific to target
  outreach_angle TEXT NOT NULL,  -- specific pitch angle (Apollo value prop framing)
  opener_draft TEXT NOT NULL,    -- copy-paste LinkedIn/email opener (3-4 sentences, Shawn voice)
  priority INTEGER NOT NULL DEFAULT 5,  -- 1-10 (10 = most urgent)
  status TEXT DEFAULT 'new' CHECK(status IN ('new', 'shared', 'dismissed')),
  created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_insights_priority ON insights(priority DESC);
CREATE INDEX IF NOT EXISTS idx_insights_status ON insights(status);
CREATE INDEX IF NOT EXISTS idx_insights_signal ON insights(signal_id);

-- ------------------------------------------------------------------
-- Engager + People stack — cross-platform identity and ICP scoring
-- ------------------------------------------------------------------

-- People: cross-platform identity (canonical name + company)
CREATE TABLE IF NOT EXISTS people (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  canonical_name TEXT NOT NULL,
  canonical_company TEXT,
  stage TEXT CHECK(stage IN (
    'stranger','aware','interested','engaged','conversing','warm','client'
  )) DEFAULT 'stranger',
  stage_updated_at TEXT DEFAULT (datetime('now')),
  notes TEXT,
  profile_image_url TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_people_stage ON people(stage);
CREATE INDEX IF NOT EXISTS idx_people_name ON people(canonical_name);

-- Engagers: individuals who commented/liked on tracked content
CREATE TABLE IF NOT EXISTS engagers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  platform TEXT NOT NULL CHECK(platform IN ('linkedin','x','reddit')),
  handle TEXT NOT NULL,
  name TEXT,
  title TEXT,
  company TEXT,
  parsed_company TEXT,
  job_bucket TEXT,
  is_internal INTEGER DEFAULT 0,
  followers INTEGER,
  profile_url TEXT,
  profile_image_url TEXT,
  person_id INTEGER REFERENCES people(id),
  created_at TEXT DEFAULT (datetime('now')),
  UNIQUE(platform, handle)
);
CREATE INDEX IF NOT EXISTS idx_engagers_person ON engagers(person_id);
CREATE INDEX IF NOT EXISTS idx_engagers_bucket ON engagers(job_bucket);
CREATE INDEX IF NOT EXISTS idx_engagers_internal ON engagers(is_internal);

-- Engagements: join engagers to content_items (one row per comment/repost/like)
CREATE TABLE IF NOT EXISTS engagements (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  engager_id INTEGER NOT NULL REFERENCES engagers(id),
  content_item_id INTEGER REFERENCES content_items(id),
  source_id INTEGER REFERENCES sources(id),  -- denormalized: the author being engaged with
  engagement_type TEXT CHECK(engagement_type IN ('comment','repost','like','reply')),
  comment_text TEXT,
  post_url TEXT,
  engaged_at TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  UNIQUE(engager_id, post_url, engagement_type)
);
CREATE INDEX IF NOT EXISTS idx_engagements_engager ON engagements(engager_id);
CREATE INDEX IF NOT EXISTS idx_engagements_content ON engagements(content_item_id);
CREATE INDEX IF NOT EXISTS idx_engagements_source ON engagements(source_id);

-- ICP scores: 1-5 across 4 dimensions, per-engager
CREATE TABLE IF NOT EXISTS icp_scores (
  engager_id INTEGER PRIMARY KEY REFERENCES engagers(id),
  persona_fit INTEGER CHECK(persona_fit BETWEEN 1 AND 5),
  company_fit INTEGER CHECK(company_fit BETWEEN 1 AND 5),
  engagement_depth INTEGER CHECK(engagement_depth BETWEEN 1 AND 5),
  budget_potential INTEGER CHECK(budget_potential BETWEEN 1 AND 5),
  overall_stars INTEGER CHECK(overall_stars BETWEEN 1 AND 5),
  notes TEXT,
  scored_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_icp_overall ON icp_scores(overall_stars DESC);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_sources_relevance ON sources(relevance);
CREATE INDEX IF NOT EXISTS idx_sources_status ON sources(status);
CREATE INDEX IF NOT EXISTS idx_content_source ON content_items(source_id);
CREATE INDEX IF NOT EXISTS idx_content_published ON content_items(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_signals_source ON signals(source_id);
CREATE INDEX IF NOT EXISTS idx_signals_status ON signals(status);
CREATE INDEX IF NOT EXISTS idx_signals_urgency ON signals(urgency);
CREATE INDEX IF NOT EXISTS idx_reddit_subreddit ON reddit_threads(subreddit);
CREATE INDEX IF NOT EXISTS idx_reddit_created ON reddit_threads(created_utc DESC);

-- Per-lead AI reasoning: explains WHY each ICP lead appeared under each signal
CREATE TABLE IF NOT EXISTS lead_reasoning (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  signal_id INTEGER NOT NULL,
  engager_id INTEGER NOT NULL,
  comment_text TEXT,
  reasoning TEXT NOT NULL,
  created_at TEXT DEFAULT (datetime('now')),
  UNIQUE(signal_id, engager_id)
);

-- Views
CREATE VIEW IF NOT EXISTS v_competitors_active AS
SELECT
  s.id, s.name, s.platform, s.handle, s.country, s.tier, s.verticals, s.followers,
  COUNT(DISTINCT ci.id) as content_count,
  COUNT(DISTINCT sig.id) as signal_count,
  MAX(ci.published_at) as latest_post_at
FROM sources s
LEFT JOIN content_items ci ON ci.source_id = s.id
LEFT JOIN signals sig ON sig.source_id = s.id AND sig.status IN ('new', 'acknowledged')
WHERE s.relevance = 'competitor' AND s.status = 'active'
GROUP BY s.id
ORDER BY signal_count DESC, latest_post_at DESC;

CREATE VIEW IF NOT EXISTS v_leaders_active AS
SELECT
  s.id, s.name, s.platform, s.handle, s.title, s.company, s.country, s.followers, s.verticals,
  COUNT(DISTINCT ci.id) as content_count,
  MAX(ci.published_at) as latest_post_at
FROM sources s
LEFT JOIN content_items ci ON ci.source_id = s.id
WHERE s.relevance IN ('thought-leader', 'founder') AND s.status = 'active'
GROUP BY s.id
ORDER BY latest_post_at DESC, s.followers DESC;

-- v_signals_active — active signal list with post-age plumbing.
-- See docs/freshness.md for the decay rules this view supports.
-- Note: CREATE VIEW IF NOT EXISTS does NOT replace an existing view — if you
-- modified this file on an existing DB, run:
--   DROP VIEW IF EXISTS v_signals_active; .read data/schema.sql
-- or use scripts/decay_signals.py which does its own inline queries.
CREATE VIEW IF NOT EXISTS v_signals_active AS
SELECT
  sig.id, sig.signal_type, sig.title, sig.description, sig.urgency, sig.status,
  s.name as source_name, s.platform, s.relevance as source_relevance, s.tier,
  sig.created_at,
  ci.published_at as post_published_at,
  CAST((julianday('now') - julianday(COALESCE(ci.published_at, ci.scraped_at))) AS INTEGER) as post_age_days
FROM signals sig
LEFT JOIN sources s ON sig.source_id = s.id
LEFT JOIN content_items ci ON ci.id = sig.content_id
WHERE sig.status IN ('new', 'acknowledged')
ORDER BY
  CASE sig.urgency
    WHEN 'act-now' THEN 1
    WHEN 'this-week' THEN 2
    WHEN 'this-month' THEN 3
    ELSE 4
  END,
  post_age_days ASC,
  sig.created_at DESC;
