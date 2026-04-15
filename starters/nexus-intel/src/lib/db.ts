import path from "node:path";
import fs from "node:fs";
import Database from "better-sqlite3";
import type {
  SignalDrawerData,
  SignalDrawerLead,
  SourceDrawerData,
  SourceDrawerRecentContent,
  SourceDrawerSignalSummary,
  SourceDrawerEngager,
} from "@/components/drawers/types";

// Singleton connection. Readonly in prod (DB committed to git, Vercel serves it).
// Writeable when INTEL_DB_WRITABLE=1 for local admin use.
let _db: Database.Database | null = null;

function resolveDbPath(): string {
  // Try multiple locations. On Vercel, the function cwd may not be project root.
  const candidates = [
    path.join(process.cwd(), "data", "intel.db"),
    path.join(process.cwd(), "intel", "data", "intel.db"),
    // Next 16 traces files relative to project root; they end up here:
    path.join(process.cwd(), ".next", "server", "data", "intel.db"),
    // Fallback: search upward from this module
    path.resolve(__dirname, "..", "..", "data", "intel.db"),
    path.resolve(__dirname, "..", "..", "..", "data", "intel.db"),
    path.resolve(__dirname, "..", "..", "..", "..", "data", "intel.db"),
  ];
  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }
  // Fall through with the first candidate; let better-sqlite3 throw a clearer error.
  throw new Error(
    `intel.db not found. Tried: ${candidates.join(", ")}. cwd=${process.cwd()}, __dirname=${__dirname}`,
  );
}

export function getDb(): Database.Database {
  if (!_db) {
    const dbPath = resolveDbPath();
    const writable = process.env.INTEL_DB_WRITABLE === "1";
    _db = new Database(dbPath, {
      readonly: !writable,
      fileMustExist: true,
    });
    // Only set WAL on writable connections — readonly can't change journal mode.
    if (writable) {
      _db.pragma("journal_mode = WAL");
    }
  }
  return _db;
}

// -----------------------------------------------------------------
// Types
// -----------------------------------------------------------------

export type Relevance =
  | "competitor"
  | "thought-leader"
  | "founder"
  | "community"
  | "customer"
  | "named-account";

export type Platform =
  | "x"
  | "linkedin"
  | "reddit"
  | "blog"
  | "podcast"
  | "newsletter"
  | "other";

export type Tier = "tier-1" | "tier-2" | "adjacent" | "global";

export type SourceStatus = "active" | "paused" | "dismissed";

export interface Source {
  id: number;
  platform: Platform;
  handle: string | null;
  url: string | null;
  name: string;
  title: string | null;
  company: string | null;
  followers: number | null;
  country: string | null;
  profile_image_url: string | null;
  relevance: Relevance;
  tier: Tier | null;
  verticals: string | null;
  status: SourceStatus;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface CompetitorRow extends Source {
  content_count: number;
  signal_count: number;
  latest_post_at: string | null;
}

export interface LeaderRow extends Source {
  content_count: number;
  latest_post_at: string | null;
}

export interface SignalRow {
  id: number;
  signal_type: string;
  title: string;
  description: string | null;
  urgency: "act-now" | "this-week" | "this-month" | "backlog";
  status: "new" | "acknowledged" | "acted-on" | "dismissed";
  source_name: string | null;
  platform: Platform | null;
  source_relevance: Relevance | null;
  tier: Tier | null;
  created_at: string;
  // Freshness plumbing (see docs/freshness.md). post_published_at is the
  // *post* date, not the analysis date; post_age_days is computed in SQL via
  // COALESCE(published_at, scraped_at). See scripts/_decay.py for the rules.
  post_published_at: string | null;
  post_age_days: number | null;
}

// -----------------------------------------------------------------
// Source queries
// -----------------------------------------------------------------

export interface SourceFilters {
  relevance?: Relevance | "all";
  platform?: Platform | "all";
  tier?: Tier | "all";
  status?: SourceStatus | "all";
  search?: string;
  limit?: number;
}

export function getSources(filters: SourceFilters = {}): Source[] {
  const db = getDb();
  const conditions: string[] = [];
  const params: (string | number)[] = [];

  if (filters.relevance && filters.relevance !== "all") {
    conditions.push("relevance = ?");
    params.push(filters.relevance);
  }
  if (filters.platform && filters.platform !== "all") {
    conditions.push("platform = ?");
    params.push(filters.platform);
  }
  if (filters.tier && filters.tier !== "all") {
    conditions.push("tier = ?");
    params.push(filters.tier);
  }
  if (filters.status && filters.status !== "all") {
    conditions.push("status = ?");
    params.push(filters.status);
  }
  if (filters.search) {
    conditions.push("(name LIKE ? OR company LIKE ? OR handle LIKE ?)");
    const term = `%${filters.search}%`;
    params.push(term, term, term);
  }

  const where = conditions.length > 0 ? `WHERE ${conditions.join(" AND ")}` : "";
  const limit = filters.limit ?? 500;

  return db
    .prepare(
      `SELECT * FROM sources ${where} ORDER BY relevance, tier NULLS LAST, name LIMIT ?`,
    )
    .all(...params, limit) as Source[];
}

export function getSourceById(id: number): Source | null {
  const db = getDb();
  return (db.prepare("SELECT * FROM sources WHERE id = ?").get(id) as Source) ?? null;
}

export interface SourceCounts {
  total: number;
  competitors: number;
  leaders: number;
  communities: number;
  named_accounts: number;
  active: number;
  dismissed: number;
}

export function getSourceCounts(): SourceCounts {
  const db = getDb();
  const row = db
    .prepare(
      `SELECT
        COUNT(*) as total,
        SUM(CASE WHEN relevance = 'competitor' THEN 1 ELSE 0 END) as competitors,
        SUM(CASE WHEN relevance IN ('thought-leader', 'founder') THEN 1 ELSE 0 END) as leaders,
        SUM(CASE WHEN relevance = 'community' THEN 1 ELSE 0 END) as communities,
        SUM(CASE WHEN relevance = 'named-account' THEN 1 ELSE 0 END) as named_accounts,
        SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active,
        SUM(CASE WHEN status = 'dismissed' THEN 1 ELSE 0 END) as dismissed
       FROM sources`,
    )
    .get() as SourceCounts;
  return row;
}

// -----------------------------------------------------------------
// Source mutations (require INTEL_DB_WRITABLE=1)
// -----------------------------------------------------------------

export interface NewSourceInput {
  platform: Platform;
  handle?: string;
  url?: string;
  name: string;
  title?: string;
  company?: string;
  country?: string;
  relevance: Relevance;
  tier?: Tier;
  verticals?: string;
  notes?: string;
}

export function insertSource(input: NewSourceInput): number {
  const db = getDb();
  const stmt = db.prepare(
    `INSERT INTO sources
      (platform, handle, url, name, title, company, country, relevance, tier, verticals, notes)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
  );
  const result = stmt.run(
    input.platform,
    input.handle ?? null,
    input.url ?? null,
    input.name,
    input.title ?? null,
    input.company ?? null,
    input.country ?? null,
    input.relevance,
    input.tier ?? null,
    input.verticals ?? null,
    input.notes ?? null,
  );
  return Number(result.lastInsertRowid);
}

export function updateSourceStatus(id: number, status: SourceStatus): void {
  const db = getDb();
  db.prepare(
    "UPDATE sources SET status = ?, updated_at = datetime('now') WHERE id = ?",
  ).run(status, id);
}

export function deleteSource(id: number): void {
  const db = getDb();
  db.prepare("DELETE FROM sources WHERE id = ?").run(id);
}

// -----------------------------------------------------------------
// Competitors (view-backed)
// -----------------------------------------------------------------

export function getCompetitors(filters: {
  tier?: Tier | "all";
  platform?: Platform | "all";
  hasFreshSignal?: boolean;
}): CompetitorRow[] {
  const db = getDb();
  const conditions: string[] = [];
  const params: (string | number)[] = [];
  if (filters.tier && filters.tier !== "all") {
    conditions.push("tier = ?");
    params.push(filters.tier);
  }
  if (filters.platform && filters.platform !== "all") {
    conditions.push("platform = ?");
    params.push(filters.platform);
  }
  if (filters.hasFreshSignal) {
    conditions.push("signal_count > 0");
  }
  const where = conditions.length > 0 ? `WHERE ${conditions.join(" AND ")}` : "";
  return db
    .prepare(`SELECT * FROM v_competitors_active ${where}`)
    .all(...params) as CompetitorRow[];
}

// -----------------------------------------------------------------
// Thought Leaders & Founders (view-backed)
// -----------------------------------------------------------------

export function getLeaders(filters: {
  platform?: Platform | "all";
  vertical?: string;
}): LeaderRow[] {
  const db = getDb();
  const conditions: string[] = [];
  const params: (string | number)[] = [];
  if (filters.platform && filters.platform !== "all") {
    conditions.push("platform = ?");
    params.push(filters.platform);
  }
  if (filters.vertical) {
    conditions.push("verticals LIKE ?");
    params.push(`%${filters.vertical}%`);
  }
  const where = conditions.length > 0 ? `WHERE ${conditions.join(" AND ")}` : "";
  return db
    .prepare(`SELECT * FROM v_leaders_active ${where}`)
    .all(...params) as LeaderRow[];
}

// -----------------------------------------------------------------
// Content
// -----------------------------------------------------------------

export interface ContentItem {
  id: number;
  source_id: number;
  platform: Platform;
  external_id: string | null;
  url: string | null;
  content_type: string | null;
  title: string | null;
  body: string | null;
  published_at: string | null;
  engagement_likes: number;
  engagement_comments: number;
  engagement_shares: number;
  engagement_views: number;
  scraped_at: string;
}

export function getContentForSource(sourceId: number, limit = 30): ContentItem[] {
  const db = getDb();
  return db
    .prepare(
      `SELECT * FROM content_items WHERE source_id = ? ORDER BY published_at DESC, scraped_at DESC LIMIT ?`,
    )
    .all(sourceId, limit) as ContentItem[];
}

// -----------------------------------------------------------------
// Signals (view-backed)
// -----------------------------------------------------------------

// Shared column list for signal queries — JOINed inline so we always carry the
// post-date freshness fields through the stack. We intentionally do NOT read
// from v_signals_active any more: the existing prod DB ships with the legacy
// view (no post_published_at), and modifying a view requires DROP+CREATE which
// would break a readonly Vercel deploy. Inline SQL sidesteps that entirely.
const SIGNAL_SELECT = `
  SELECT
    sig.id,
    sig.signal_type,
    sig.title,
    sig.description,
    sig.urgency,
    sig.status,
    s.name          AS source_name,
    s.platform      AS platform,
    s.relevance     AS source_relevance,
    s.tier          AS tier,
    sig.created_at  AS created_at,
    ci.published_at AS post_published_at,
    CAST((julianday('now') - julianday(COALESCE(ci.published_at, ci.scraped_at))) AS INTEGER) AS post_age_days
  FROM signals sig
  LEFT JOIN sources s       ON s.id = sig.source_id
  LEFT JOIN content_items ci ON ci.id = sig.content_id
`;

export function getSignals(filters: {
  urgency?: "act-now" | "this-week" | "this-month" | "backlog" | "all";
  signalType?: string;
  sourceRelevance?: Relevance | "all";
  /**
   * Hide signals whose post is past the signal-type-specific staleness window
   * (default: 60 days — matches the universal `this-month` ceiling in _decay.py).
   * Set to `false` to show everything.
   */
  hideStale?: boolean;
  limit?: number;
} = {}): SignalRow[] {
  const db = getDb();
  const conditions: string[] = ["sig.status IN ('new', 'acknowledged')"];
  const params: (string | number)[] = [];
  if (filters.urgency && filters.urgency !== "all") {
    conditions.push("sig.urgency = ?");
    params.push(filters.urgency);
  }
  if (filters.signalType) {
    conditions.push("sig.signal_type = ?");
    params.push(filters.signalType);
  }
  if (filters.sourceRelevance && filters.sourceRelevance !== "all") {
    conditions.push("s.relevance = ?");
    params.push(filters.sourceRelevance);
  }
  if (filters.hideStale !== false) {
    // Default ON — stale signals (>60d post age) are hidden unless explicitly shown
    conditions.push(
      "(ci.published_at IS NULL OR (julianday('now') - julianday(ci.published_at)) < 60)",
    );
  }
  const where = conditions.length > 0 ? `WHERE ${conditions.join(" AND ")}` : "";
  const limit = filters.limit ?? 100;
  return db
    .prepare(
      `${SIGNAL_SELECT} ${where}
       ORDER BY
         CASE sig.urgency WHEN 'act-now' THEN 1 WHEN 'this-week' THEN 2 WHEN 'this-month' THEN 3 ELSE 4 END,
         post_age_days ASC,
         sig.created_at DESC
       LIMIT ?`,
    )
    .all(...params, limit) as SignalRow[];
}

export function getSignalsForSource(sourceId: number, limit = 20): SignalRow[] {
  const db = getDb();
  return db
    .prepare(
      `${SIGNAL_SELECT}
       WHERE sig.status IN ('new', 'acknowledged')
         AND sig.source_id = ?
       ORDER BY
         CASE sig.urgency WHEN 'act-now' THEN 1 WHEN 'this-week' THEN 2 WHEN 'this-month' THEN 3 ELSE 4 END,
         post_age_days ASC
       LIMIT ?`,
    )
    .all(sourceId, limit) as SignalRow[];
}

/** Count of signals whose underlying post is < 14 days old — used for the KPI strip. */
export function getFreshSignalCount(): number {
  const db = getDb();
  const row = db
    .prepare(
      `SELECT COUNT(*) AS c
       FROM signals sig
       LEFT JOIN content_items ci ON ci.id = sig.content_id
       WHERE sig.status IN ('new', 'acknowledged')
         AND ci.published_at IS NOT NULL
         AND (julianday('now') - julianday(ci.published_at)) < 14`,
    )
    .get() as { c: number };
  return row?.c ?? 0;
}

export function getSignalCountsByType(): { signal_type: string; count: number }[] {
  const db = getDb();
  return db
    .prepare(
      `SELECT signal_type, COUNT(*) as count FROM signals
       WHERE status IN ('new', 'acknowledged')
       AND created_at >= datetime('now', '-7 days')
       GROUP BY signal_type ORDER BY count DESC`,
    )
    .all() as { signal_type: string; count: number }[];
}

// -----------------------------------------------------------------
// Reddit threads
// -----------------------------------------------------------------

export interface RedditThread {
  id: number;
  external_id: string | null;
  subreddit: string;
  title: string;
  url: string;
  permalink: string | null;
  author: string | null;
  body: string | null;
  score: number;
  num_comments: number;
  created_utc: string | null;
  topic_tags: string | null;
  scraped_at: string;
}

export function getRedditThreads(filters: {
  subreddit?: string;
  since?: string;
  limit?: number;
} = {}): RedditThread[] {
  const db = getDb();
  const conditions: string[] = [];
  const params: (string | number)[] = [];
  if (filters.subreddit) {
    conditions.push("subreddit = ?");
    params.push(filters.subreddit);
  }
  if (filters.since) {
    conditions.push("(created_utc >= ? OR scraped_at >= ?)");
    params.push(filters.since, filters.since);
  }
  const where = conditions.length > 0 ? `WHERE ${conditions.join(" AND ")}` : "";
  const limit = filters.limit ?? 100;
  return db
    .prepare(
      `SELECT * FROM reddit_threads ${where} ORDER BY COALESCE(created_utc, scraped_at) DESC LIMIT ?`,
    )
    .all(...params, limit) as RedditThread[];
}

// -----------------------------------------------------------------
// Topics
// -----------------------------------------------------------------

export function getTopicsForSource(sourceId: number): { name: string; category: string; count: number }[] {
  const db = getDb();
  return db
    .prepare(
      `SELECT t.name, t.category, COUNT(*) as count
       FROM topics t
       JOIN content_topics ct ON ct.topic_id = t.id
       JOIN content_items ci ON ci.id = ct.content_id
       WHERE ci.source_id = ?
       GROUP BY t.id
       ORDER BY count DESC
       LIMIT 20`,
    )
    .all(sourceId) as { name: string; category: string; count: number }[];
}

// -----------------------------------------------------------------
// Overview / KPI / Charts
// -----------------------------------------------------------------

export interface KpiDeltas {
  signals_total: number;
  signals_this_week: number;
  signals_last_week: number;
  signals_delta: number;
  content_this_week: number;
  content_last_week: number;
  content_delta: number;
  active_threats: number;
  active_threats_last_week: number;
  active_threats_delta: number;
  fresh_competitors: number;
  fresh_competitors_last_week: number;
  fresh_competitors_delta: number;
  signals_sparkline: number[];
  content_sparkline: number[];
  threats_sparkline: number[];
  competitors_sparkline: number[];
}

export function getKpiDeltas(): KpiDeltas {
  const db = getDb();

  const bucket = (d: number) =>
    `(strftime('%s', 'now') - strftime('%s', created_at)) <= ${d * 86400}`;
  const contentBucket = (d: number) =>
    `(strftime('%s', 'now') - strftime('%s', scraped_at)) <= ${d * 86400}`;

  const signals_total = (db.prepare("SELECT COUNT(*) as c FROM signals").get() as { c: number }).c;
  const signals_this_week = (db.prepare(`SELECT COUNT(*) as c FROM signals WHERE ${bucket(7)}`).get() as { c: number }).c;
  const signals_last_week = (db.prepare(
    `SELECT COUNT(*) as c FROM signals WHERE ${bucket(14)} AND NOT ${bucket(7)}`,
  ).get() as { c: number }).c;

  const content_this_week = (db.prepare(`SELECT COUNT(*) as c FROM content_items WHERE ${contentBucket(7)}`).get() as { c: number }).c;
  const content_last_week = (db.prepare(
    `SELECT COUNT(*) as c FROM content_items WHERE ${contentBucket(14)} AND NOT ${contentBucket(7)}`,
  ).get() as { c: number }).c;

  const active_threats = (db
    .prepare("SELECT COUNT(*) as c FROM signals WHERE urgency IN ('act-now', 'this-week') AND status IN ('new', 'acknowledged')")
    .get() as { c: number }).c;
  const active_threats_last_week = (db
    .prepare(
      `SELECT COUNT(*) as c FROM signals WHERE urgency IN ('act-now', 'this-week') AND ${bucket(14)} AND NOT ${bucket(7)}`,
    )
    .get() as { c: number }).c;

  const fresh_competitors = (db
    .prepare(
      `SELECT COUNT(DISTINCT s.id) as c FROM sources s
       JOIN content_items ci ON ci.source_id = s.id
       WHERE s.relevance = 'competitor' AND ${contentBucket(7).replaceAll("scraped_at", "ci.scraped_at")}`,
    )
    .get() as { c: number }).c;
  const fresh_competitors_last_week = (db
    .prepare(
      `SELECT COUNT(DISTINCT s.id) as c FROM sources s
       JOIN content_items ci ON ci.source_id = s.id
       WHERE s.relevance = 'competitor'
         AND ${contentBucket(14).replaceAll("scraped_at", "ci.scraped_at")}
         AND NOT ${contentBucket(7).replaceAll("scraped_at", "ci.scraped_at")}`,
    )
    .get() as { c: number }).c;

  // 7-day sparkline rows (last 7 days, one bucket per day)
  const daily = (table: string, dateCol: string, where = "") => {
    const rows = db
      .prepare(
        `SELECT CAST(strftime('%j', ${dateCol}) AS INTEGER) as day, COUNT(*) as c
         FROM ${table}
         WHERE (strftime('%s','now') - strftime('%s', ${dateCol})) <= 7 * 86400
           ${where ? `AND ${where}` : ""}
         GROUP BY day
         ORDER BY day`,
      )
      .all() as { day: number; c: number }[];
    // normalize to 7-length array
    if (rows.length === 0) return [0, 0, 0, 0, 0, 0, 0];
    return rows.map((r) => r.c);
  };

  return {
    signals_total,
    signals_this_week,
    signals_last_week,
    signals_delta: signals_this_week - signals_last_week,
    content_this_week,
    content_last_week,
    content_delta: content_this_week - content_last_week,
    active_threats,
    active_threats_last_week,
    active_threats_delta: active_threats - active_threats_last_week,
    fresh_competitors,
    fresh_competitors_last_week,
    fresh_competitors_delta: fresh_competitors - fresh_competitors_last_week,
    signals_sparkline: daily("signals", "created_at"),
    content_sparkline: daily("content_items", "scraped_at"),
    threats_sparkline: daily(
      "signals",
      "created_at",
      "urgency IN ('act-now','this-week')",
    ),
    competitors_sparkline: daily(
      "content_items",
      "scraped_at",
      "source_id IN (SELECT id FROM sources WHERE relevance='competitor')",
    ),
  };
}

export interface TrendPoint {
  week_start: string;
  likes: number;
  comments: number;
  posts: number;
}

export function getEngagementTrend(weeks = 8): TrendPoint[] {
  const db = getDb();
  // Bucket by ISO week-start. published_at is sometimes null; fall back to scraped_at.
  return db
    .prepare(
      `SELECT
        date(COALESCE(published_at, scraped_at), 'weekday 0', '-6 days') as week_start,
        SUM(engagement_likes) as likes,
        SUM(engagement_comments) as comments,
        COUNT(*) as posts
       FROM content_items
       WHERE COALESCE(published_at, scraped_at) >= date('now', ?)
       GROUP BY week_start
       ORDER BY week_start ASC`,
    )
    .all(`-${weeks * 7} days`) as TrendPoint[];
}

export interface HeroSource {
  id: number;
  name: string;
  company: string | null;
  platform: Platform;
  handle: string | null;
  relevance: Relevance;
  tier: Tier | null;
  latest_signal_title: string | null;
  latest_signal_description: string | null;
  latest_signal_urgency: string | null;
  latest_signal_type: string | null;
  latest_post_body: string | null;
  latest_post_url: string | null;
  latest_post_at: string | null;
  latest_post_likes: number | null;
  latest_post_comments: number | null;
}

export function getTopCompetitorMove(): HeroSource | null {
  const db = getDb();
  // Hero filter: the highlighted move must be tied to a post < 30 days old.
  // Ancient competitor moves on the homepage destroy trust — filter out stale items.
  const row = db
    .prepare(
      `SELECT s.id, s.name, s.company, s.platform, s.handle, s.relevance, s.tier,
              sig.title as latest_signal_title,
              sig.description as latest_signal_description,
              sig.urgency as latest_signal_urgency,
              sig.signal_type as latest_signal_type,
              ci.body as latest_post_body,
              ci.url as latest_post_url,
              ci.published_at as latest_post_at,
              ci.engagement_likes as latest_post_likes,
              ci.engagement_comments as latest_post_comments
       FROM sources s
       LEFT JOIN signals sig ON sig.source_id = s.id AND sig.status IN ('new', 'acknowledged')
       LEFT JOIN content_items ci ON ci.source_id = s.id
       WHERE s.relevance = 'competitor' AND s.status = 'active'
         AND ci.published_at IS NOT NULL
         AND (julianday('now') - julianday(ci.published_at)) < 30
       ORDER BY
         CASE sig.urgency WHEN 'act-now' THEN 1 WHEN 'this-week' THEN 2 WHEN 'this-month' THEN 3 ELSE 4 END,
         sig.created_at DESC NULLS LAST,
         ci.engagement_likes DESC NULLS LAST
       LIMIT 1`,
    )
    .get() as HeroSource | undefined;
  return row ?? null;
}

export function getTopLeaderVoice(): HeroSource | null {
  const db = getDb();
  const row = db
    .prepare(
      `SELECT s.id, s.name, s.company, s.platform, s.handle, s.relevance, s.tier,
              NULL as latest_signal_title,
              NULL as latest_signal_description,
              NULL as latest_signal_urgency,
              NULL as latest_signal_type,
              ci.body as latest_post_body,
              ci.url as latest_post_url,
              ci.published_at as latest_post_at,
              ci.engagement_likes as latest_post_likes,
              ci.engagement_comments as latest_post_comments
       FROM sources s
       JOIN content_items ci ON ci.source_id = s.id
       WHERE s.relevance IN ('thought-leader', 'founder') AND s.status = 'active'
         AND ci.published_at IS NOT NULL
         AND (julianday('now') - julianday(ci.published_at)) < 30
       ORDER BY ci.engagement_likes DESC, ci.published_at DESC
       LIMIT 1`,
    )
    .get() as HeroSource | undefined;
  return row ?? null;
}

export function getTopThreat(): HeroSource | null {
  const db = getDb();
  // Threat hero: only fresh act-now signals. Anything older has already been
  // capped to this-week or lower by the analyzer decay, so this filter is
  // defense-in-depth in case the DB hasn't been decay-cleaned yet.
  const row = db
    .prepare(
      `SELECT s.id, s.name, s.company, s.platform, s.handle, s.relevance, s.tier,
              sig.title as latest_signal_title,
              sig.description as latest_signal_description,
              sig.urgency as latest_signal_urgency,
              sig.signal_type as latest_signal_type,
              ci.body as latest_post_body,
              ci.url as latest_post_url,
              ci.published_at as latest_post_at,
              ci.engagement_likes as latest_post_likes,
              ci.engagement_comments as latest_post_comments
       FROM signals sig
       JOIN sources s ON s.id = sig.source_id
       LEFT JOIN content_items ci ON ci.id = sig.content_id
       WHERE sig.urgency = 'act-now' AND sig.status IN ('new', 'acknowledged')
         AND ci.published_at IS NOT NULL
         AND (julianday('now') - julianday(ci.published_at)) < 14
       ORDER BY sig.created_at DESC
       LIMIT 1`,
    )
    .get() as HeroSource | undefined;
  return row ?? null;
}

export function getPlatformBreakdown(): Record<string, number> {
  const db = getDb();
  const rows = db
    .prepare(
      `SELECT platform, COUNT(*) as c FROM content_items GROUP BY platform`,
    )
    .all() as { platform: string; c: number }[];
  const out: Record<string, number> = {};
  for (const r of rows) {
    out[r.platform] = (out[r.platform] ?? 0) + r.c;
  }
  return out;
}

export function getTopicBreakdown(): { category: string; item_count: number; topic_count: number }[] {
  const db = getDb();
  return db
    .prepare(
      `SELECT t.category,
              COUNT(DISTINCT ct.content_id) as item_count,
              COUNT(DISTINCT t.id) as topic_count
       FROM topics t
       JOIN content_topics ct ON ct.topic_id = t.id
       WHERE t.category IS NOT NULL
       GROUP BY t.category
       ORDER BY item_count DESC`,
    )
    .all() as { category: string; item_count: number; topic_count: number }[];
}

export interface EngagementAuthor {
  author_name: string | null;
  platform: string;
  total_likes: number;
  avg_likes: number;
  post_count: number;
}

export function getEngagementLeaderboard(limit = 10): EngagementAuthor[] {
  const db = getDb();
  return db
    .prepare(
      `SELECT s.name as author_name,
              s.platform,
              SUM(ci.engagement_likes) as total_likes,
              AVG(ci.engagement_likes) as avg_likes,
              COUNT(ci.id) as post_count
       FROM sources s
       JOIN content_items ci ON ci.source_id = s.id
       GROUP BY s.id
       ORDER BY total_likes DESC
       LIMIT ?`,
    )
    .all(limit) as EngagementAuthor[];
}

export function getLatestScrapeTime(): string | null {
  const db = getDb();
  const row = db
    .prepare(
      `SELECT MAX(completed_at) as ts FROM scrape_runs WHERE completed_at IS NOT NULL`,
    )
    .get() as { ts: string | null };
  return row.ts;
}

export function getTotalTrackedCount(): number {
  const db = getDb();
  const row = db
    .prepare("SELECT COUNT(*) as c FROM sources WHERE status = 'active'")
    .get() as { c: number };
  return row.c;
}

// -----------------------------------------------------------------
// Insights (SDR-actionable briefs)
// -----------------------------------------------------------------

export interface Insight {
  id: number;
  signal_id: number | null;
  source_id: number | null;
  target_account: string | null;
  vertical: string | null;
  headline: string;
  why_it_matters: string | null;
  outreach_angle: string;
  opener_draft: string;
  priority: number;
  status: "new" | "shared" | "dismissed";
  created_at: string;
  // JOINed fields
  source_name: string | null;
  signal_type: string | null;
  signal_urgency: string | null;
  signal_title: string | null;
  post_url: string | null;
  // Freshness plumbing — the age of the post that triggered this brief
  post_published_at: string | null;
  post_age_days: number | null;
}

export function getInsights(filters: {
  status?: "new" | "shared" | "dismissed" | "all";
  vertical?: string | "all";
  minPriority?: number;
  limit?: number;
} = {}): Insight[] {
  const db = getDb();
  const conditions: string[] = [];
  const params: (string | number)[] = [];
  if (filters.status && filters.status !== "all") {
    conditions.push("i.status = ?");
    params.push(filters.status);
  } else if (!filters.status) {
    conditions.push("i.status IN ('new', 'shared')");
  }
  if (filters.vertical && filters.vertical !== "all") {
    conditions.push("i.vertical = ?");
    params.push(filters.vertical);
  }
  if (typeof filters.minPriority === "number") {
    conditions.push("i.priority >= ?");
    params.push(filters.minPriority);
  }
  const where = conditions.length > 0 ? `WHERE ${conditions.join(" AND ")}` : "";
  const limit = filters.limit ?? 100;
  return db
    .prepare(
      `SELECT i.*,
              s.name as source_name,
              sig.signal_type,
              sig.urgency as signal_urgency,
              sig.title as signal_title,
              ci.url as post_url,
              ci.published_at as post_published_at,
              CAST((julianday('now') - julianday(COALESCE(ci.published_at, ci.scraped_at))) AS INTEGER) AS post_age_days
       FROM insights i
       LEFT JOIN sources s ON s.id = i.source_id
       LEFT JOIN signals sig ON sig.id = i.signal_id
       LEFT JOIN content_items ci ON ci.id = sig.content_id
       ${where}
       ORDER BY
         (CASE WHEN ci.published_at IS NULL THEN 1 ELSE 0 END),
         post_age_days ASC,
         i.priority DESC,
         i.created_at DESC
       LIMIT ?`,
    )
    .all(...params, limit) as Insight[];
}

export function getInsightsForSource(sourceId: number, limit = 10): Insight[] {
  const db = getDb();
  return db
    .prepare(
      `SELECT i.*,
              s.name as source_name,
              sig.signal_type, sig.urgency as signal_urgency, sig.title as signal_title,
              ci.url as post_url,
              ci.published_at as post_published_at,
              CAST((julianday('now') - julianday(COALESCE(ci.published_at, ci.scraped_at))) AS INTEGER) AS post_age_days
       FROM insights i
       LEFT JOIN sources s ON s.id = i.source_id
       LEFT JOIN signals sig ON sig.id = i.signal_id
       LEFT JOIN content_items ci ON ci.id = sig.content_id
       WHERE i.source_id = ? AND i.status IN ('new', 'shared')
       ORDER BY post_age_days ASC, i.priority DESC, i.created_at DESC
       LIMIT ?`,
    )
    .all(sourceId, limit) as Insight[];
}

export function getEngagementTrendForSource(sourceId: number, weeks = 8): TrendPoint[] {
  const db = getDb();
  return db
    .prepare(
      `SELECT
        date(COALESCE(published_at, scraped_at), 'weekday 0', '-6 days') as week_start,
        SUM(engagement_likes) as likes,
        SUM(engagement_comments) as comments,
        COUNT(*) as posts
       FROM content_items
       WHERE source_id = ?
         AND COALESCE(published_at, scraped_at) >= date('now', ?)
       GROUP BY week_start
       ORDER BY week_start ASC`,
    )
    .all(sourceId, `-${weeks * 7} days`) as TrendPoint[];
}

export function getTopicBreakdownForSource(
  sourceId: number,
): { category: string; item_count: number; topic_count: number }[] {
  const db = getDb();
  return db
    .prepare(
      `SELECT t.category,
              COUNT(DISTINCT ct.content_id) as item_count,
              COUNT(DISTINCT t.id) as topic_count
       FROM topics t
       JOIN content_topics ct ON ct.topic_id = t.id
       JOIN content_items ci ON ci.id = ct.content_id
       WHERE ci.source_id = ? AND t.category IS NOT NULL
       GROUP BY t.category
       ORDER BY item_count DESC`,
    )
    .all(sourceId) as { category: string; item_count: number; topic_count: number }[];
}

export interface SourceStats {
  total_posts: number;
  total_likes: number;
  total_comments: number;
  signal_count: number;
  insight_count: number;
  latest_post_at: string | null;
}

export function getSourceStats(sourceId: number): SourceStats {
  const db = getDb();
  const row = db
    .prepare(
      `SELECT COUNT(ci.id) as total_posts,
              COALESCE(SUM(ci.engagement_likes), 0) as total_likes,
              COALESCE(SUM(ci.engagement_comments), 0) as total_comments,
              MAX(ci.published_at) as latest_post_at
       FROM content_items ci
       WHERE ci.source_id = ?`,
    )
    .get(sourceId) as Omit<SourceStats, "signal_count" | "insight_count">;
  const signal_count = (db
    .prepare("SELECT COUNT(*) as c FROM signals WHERE source_id = ?")
    .get(sourceId) as { c: number }).c;
  const insight_count = (db
    .prepare(
      "SELECT COUNT(*) as c FROM insights WHERE source_id = ? AND status IN ('new','shared')",
    )
    .get(sourceId) as { c: number }).c;
  return { ...row, signal_count, insight_count };
}

export interface InsightCounts {
  total: number;
  new_count: number;
  by_vertical: Record<string, number>;
  by_account: Record<string, number>;
}

// -----------------------------------------------------------------
// Engagers + People + ICP — cross-platform identity and scoring
// -----------------------------------------------------------------

export interface Engager {
  id: number;
  platform: "linkedin" | "x" | "reddit";
  handle: string;
  name: string | null;
  title: string | null;
  company: string | null;
  parsed_company: string | null;
  job_bucket: string | null;
  is_internal: number;
  followers: number | null;
  profile_url: string | null;
  profile_image_url: string | null;
  person_id: number | null;
  created_at: string;
  // Aggregates (from JOINs)
  engagement_count?: number;
  comment_count?: number;
  accounts_engaged?: number;
  overall_stars?: number | null;
  persona_fit?: number | null;
  company_fit?: number | null;
  engagement_depth?: number | null;
  budget_potential?: number | null;
}

export interface EngagerFilters {
  minStars?: number;
  sourceId?: number;
  platform?: string;
  jobBucket?: string;
  hideInternal?: boolean;
  search?: string;
  limit?: number;
  offset?: number;
  /**
   * When true (default), restrict to ICP engagers per the canonical predicate:
   *   COALESCE(icp.overall_stars, 0) >= 3
   * Pass false to include non-ICP (used by ?icp=all toggle). See docs/icp-filter.md.
   */
  icpOnly?: boolean;
}

// Canonical ICP predicate. Used by getEngagers/getEngagerCount/getEngagerBucketCounts
// and composed into getPeople/getPersonCoEngagers via EXISTS subqueries.
// Requires `e` (engagers) and `icp` (icp_scores LEFT JOIN) aliases in scope.
const ICP_ENGAGER_PREDICATE =
  "(COALESCE(icp.overall_stars, 0) >= 3)";

export function getEngagers(filters: EngagerFilters = {}): Engager[] {
  const db = getDb();
  const conditions: string[] = [];
  const params: (string | number)[] = [];

  if (filters.minStars) {
    conditions.push("icp.overall_stars >= ?");
    params.push(filters.minStars);
  }
  if (filters.icpOnly !== false) {
    conditions.push(ICP_ENGAGER_PREDICATE);
  }
  if (filters.sourceId) {
    conditions.push("e.id IN (SELECT engager_id FROM engagements WHERE source_id = ?)");
    params.push(filters.sourceId);
  }
  if (filters.platform) {
    conditions.push("e.platform = ?");
    params.push(filters.platform);
  }
  if (filters.jobBucket) {
    conditions.push("e.job_bucket = ?");
    params.push(filters.jobBucket);
  }
  if (filters.hideInternal) {
    conditions.push("(e.is_internal = 0 OR e.is_internal IS NULL)");
  }
  if (filters.search) {
    conditions.push("(e.name LIKE ? OR e.company LIKE ? OR e.parsed_company LIKE ? OR e.handle LIKE ?)");
    const term = `%${filters.search}%`;
    params.push(term, term, term, term);
  }
  const where = conditions.length ? `WHERE ${conditions.join(" AND ")}` : "";
  const limit = filters.limit ?? 100;
  const offset = filters.offset ?? 0;

  return db
    .prepare(
      `SELECT e.*,
              COUNT(eg.id) as engagement_count,
              SUM(CASE WHEN eg.engagement_type IN ('comment','reply') THEN 1 ELSE 0 END) as comment_count,
              COUNT(DISTINCT eg.source_id) as accounts_engaged,
              icp.overall_stars, icp.persona_fit, icp.company_fit,
              icp.engagement_depth, icp.budget_potential
       FROM engagers e
       LEFT JOIN engagements eg ON eg.engager_id = e.id
       LEFT JOIN icp_scores icp ON icp.engager_id = e.id
       ${where}
       GROUP BY e.id
       ORDER BY COALESCE(icp.overall_stars, 0) DESC, engagement_count DESC
       LIMIT ? OFFSET ?`,
    )
    .all(...params, limit, offset) as Engager[];
}

export function getEngagerCount(filters: Omit<EngagerFilters, "limit" | "offset"> = {}): number {
  const db = getDb();
  const conditions: string[] = [];
  const params: (string | number)[] = [];
  if (filters.minStars) {
    conditions.push("icp.overall_stars >= ?");
    params.push(filters.minStars);
  }
  if (filters.icpOnly !== false) {
    conditions.push(ICP_ENGAGER_PREDICATE);
  }
  if (filters.sourceId) {
    conditions.push("e.id IN (SELECT engager_id FROM engagements WHERE source_id = ?)");
    params.push(filters.sourceId);
  }
  if (filters.platform) {
    conditions.push("e.platform = ?");
    params.push(filters.platform);
  }
  if (filters.jobBucket) {
    conditions.push("e.job_bucket = ?");
    params.push(filters.jobBucket);
  }
  if (filters.hideInternal) {
    conditions.push("(e.is_internal = 0 OR e.is_internal IS NULL)");
  }
  const where = conditions.length ? `WHERE ${conditions.join(" AND ")}` : "";
  return (db
    .prepare(
      `SELECT COUNT(DISTINCT e.id) as c
       FROM engagers e
       LEFT JOIN icp_scores icp ON icp.engager_id = e.id
       ${where}`,
    )
    .get(...params) as { c: number }).c;
}

export function getEngagerBucketCounts(
  hideInternal = true,
  icpOnly = true,
): { job_bucket: string; count: number }[] {
  const db = getDb();
  const conditions: string[] = [];
  if (hideInternal) conditions.push("(e.is_internal = 0 OR e.is_internal IS NULL)");
  if (icpOnly) conditions.push(ICP_ENGAGER_PREDICATE);
  const where = conditions.length ? `WHERE ${conditions.join(" AND ")}` : "";
  return db
    .prepare(
      `SELECT COALESCE(e.job_bucket, 'other') as job_bucket, COUNT(DISTINCT e.id) as count
       FROM engagers e
       LEFT JOIN icp_scores icp ON icp.engager_id = e.id
       ${where}
       GROUP BY e.job_bucket
       ORDER BY count DESC`,
    )
    .all() as { job_bucket: string; count: number }[];
}

export interface Person {
  id: number;
  canonical_name: string;
  canonical_company: string | null;
  stage: "stranger" | "aware" | "interested" | "engaged" | "conversing" | "warm" | "client";
  stage_updated_at: string;
  notes: string | null;
  profile_image_url: string | null;
  created_at: string;
  // Aggregates
  platforms?: string;
  engager_count?: number;
  engagement_count?: number;
  max_stars?: number | null;
}

export function getPersonById(id: number): Person | undefined {
  const db = getDb();
  return db
    .prepare(
      `SELECT p.*,
              COALESCE((SELECT GROUP_CONCAT(DISTINCT e.platform) FROM engagers e WHERE e.person_id = p.id), '') as platforms,
              (SELECT COUNT(*) FROM engagers e WHERE e.person_id = p.id) as engager_count,
              (SELECT COUNT(*) FROM engagements eg JOIN engagers e ON eg.engager_id = e.id WHERE e.person_id = p.id) as engagement_count,
              (SELECT MAX(icp.overall_stars) FROM icp_scores icp JOIN engagers e ON icp.engager_id = e.id WHERE e.person_id = p.id) as max_stars
       FROM people p
       WHERE p.id = ?`,
    )
    .get(id) as Person | undefined;
}

export function getPeople(
  filters: {
    platform?: string;
    stage?: string;
    limit?: number;
    minStars?: number;
    /** Default true — restrict to people with at least one ICP engager. See docs/icp-filter.md. */
    icpOnly?: boolean;
  } = {},
): Person[] {
  const db = getDb();
  const conditions: string[] = [];
  const params: (string | number)[] = [];
  if (filters.stage) {
    conditions.push("p.stage = ?");
    params.push(filters.stage);
  }
  if (filters.platform) {
    conditions.push("EXISTS (SELECT 1 FROM engagers e WHERE e.person_id = p.id AND e.platform = ?)");
    params.push(filters.platform);
  }
  if (filters.icpOnly !== false) {
    // A person is ICP if any of their engagers satisfies the canonical predicate.
    // (Subquery uses local `e`/`icp` aliases — matches ICP_ENGAGER_PREDICATE shape.)
    conditions.push(`EXISTS (
      SELECT 1 FROM engagers e
      LEFT JOIN icp_scores icp ON icp.engager_id = e.id
      WHERE e.person_id = p.id
        AND ${ICP_ENGAGER_PREDICATE}
    )`);
  }
  const where = conditions.length ? `WHERE ${conditions.join(" AND ")}` : "";
  const having = filters.minStars
    ? `HAVING max_stars >= ${Number(filters.minStars)}`
    : "";
  const limit = filters.limit ?? 500;
  return db
    .prepare(
      `SELECT p.*,
              COALESCE((SELECT GROUP_CONCAT(DISTINCT e.platform) FROM engagers e WHERE e.person_id = p.id), '') as platforms,
              (SELECT COUNT(*) FROM engagers e WHERE e.person_id = p.id) as engager_count,
              (SELECT COUNT(*) FROM engagements eg JOIN engagers e ON eg.engager_id = e.id WHERE e.person_id = p.id) as engagement_count,
              (SELECT MAX(icp.overall_stars) FROM icp_scores icp JOIN engagers e ON icp.engager_id = e.id WHERE e.person_id = p.id) as max_stars
       FROM people p
       ${where}
       ${having}
       ORDER BY max_stars DESC NULLS LAST, engagement_count DESC
       LIMIT ?`,
    )
    .all(...params, limit) as Person[];
}

/**
 * Count of people matching filters. Mirrors getPeople's predicates; used by
 * /people header to show "{icpCount} ICP · {totalCount} total" when the filter
 * is active.
 */
export function getPeopleCount(
  filters: { platform?: string; stage?: string; icpOnly?: boolean } = {},
): number {
  const db = getDb();
  const conditions: string[] = [];
  const params: (string | number)[] = [];
  if (filters.stage) {
    conditions.push("p.stage = ?");
    params.push(filters.stage);
  }
  if (filters.platform) {
    conditions.push("EXISTS (SELECT 1 FROM engagers e WHERE e.person_id = p.id AND e.platform = ?)");
    params.push(filters.platform);
  }
  if (filters.icpOnly !== false) {
    conditions.push(`EXISTS (
      SELECT 1 FROM engagers e
      LEFT JOIN icp_scores icp ON icp.engager_id = e.id
      WHERE e.person_id = p.id
        AND ${ICP_ENGAGER_PREDICATE}
    )`);
  }
  const where = conditions.length ? `WHERE ${conditions.join(" AND ")}` : "";
  return (db
    .prepare(`SELECT COUNT(*) as c FROM people p ${where}`)
    .get(...params) as { c: number }).c;
}

export function getEngagersForPerson(personId: number | null, fallbackEngagerId?: number): {
  id: number;
  platform: string;
  handle: string;
  profile_url: string | null;
}[] {
  const db = getDb();
  if (personId) {
    return db
      .prepare(
        "SELECT id, platform, handle, profile_url FROM engagers WHERE person_id = ? ORDER BY platform",
      )
      .all(personId) as { id: number; platform: string; handle: string; profile_url: string | null }[];
  }
  if (fallbackEngagerId !== undefined) {
    return db
      .prepare("SELECT id, platform, handle, profile_url FROM engagers WHERE id = ?")
      .all(fallbackEngagerId) as { id: number; platform: string; handle: string; profile_url: string | null }[];
  }
  return [];
}

export interface PersonEngagement {
  id: number;
  engager_platform: string;
  engagement_type: string;
  comment_text: string | null;
  post_url: string | null;
  engaged_at: string | null;
  source_id: number | null;
  source_name: string | null;
  source_relevance: string | null;
  source_post_body: string | null;
}

export function getPersonEngagements(personId: number, limit = 20): PersonEngagement[] {
  const db = getDb();
  return db
    .prepare(
      `SELECT eg.id,
              e.platform as engager_platform,
              eg.engagement_type,
              eg.comment_text,
              eg.post_url,
              eg.engaged_at,
              eg.source_id,
              s.name as source_name,
              s.relevance as source_relevance,
              SUBSTR(ci.body, 1, 200) as source_post_body
       FROM engagements eg
       JOIN engagers e ON eg.engager_id = e.id
       LEFT JOIN content_items ci ON eg.content_item_id = ci.id
       LEFT JOIN sources s ON eg.source_id = s.id
       WHERE e.person_id = ?
       ORDER BY COALESCE(eg.engaged_at, '') DESC
       LIMIT ?`,
    )
    .all(personId, limit) as PersonEngagement[];
}

export interface CoEngager {
  person_id: number;
  name: string | null;
  company: string | null;
  shared_posts: number;
  platforms: string;
  max_stars: number | null;
}

export function getPersonCoEngagers(
  personId: number,
  limit = 10,
  icpOnly = true,
): CoEngager[] {
  const db = getDb();
  // Filter co-engager `p` to ICP people by default — the sidebar shouldn't surface noise.
  // Uses the same canonical predicate as getEngagers/getPeople (see docs/icp-filter.md).
  const icpFilter = icpOnly
    ? `AND EXISTS (
         SELECT 1 FROM engagers e
         LEFT JOIN icp_scores icp ON icp.engager_id = e.id
         WHERE e.person_id = p.id
           AND ${ICP_ENGAGER_PREDICATE}
       )`
    : "";
  return db
    .prepare(
      `SELECT p.id as person_id,
              p.canonical_name as name,
              p.canonical_company as company,
              COUNT(DISTINCT eg2.content_item_id) as shared_posts,
              COALESCE((SELECT GROUP_CONCAT(DISTINCT e.platform) FROM engagers e WHERE e.person_id = p.id), '') as platforms,
              (SELECT MAX(icp.overall_stars) FROM icp_scores icp JOIN engagers e ON icp.engager_id = e.id WHERE e.person_id = p.id) as max_stars
       FROM engagements eg1
       JOIN engagers e1 ON eg1.engager_id = e1.id
       JOIN engagements eg2 ON eg2.content_item_id = eg1.content_item_id
         AND eg2.engager_id != eg1.engager_id
       JOIN engagers e2 ON eg2.engager_id = e2.id
       JOIN people p ON p.id = e2.person_id
       WHERE e1.person_id = ?
         AND e2.person_id IS NOT NULL
         AND e2.person_id != ?
         ${icpFilter}
       GROUP BY p.id
       ORDER BY shared_posts DESC, max_stars DESC NULLS LAST
       LIMIT ?`,
    )
    .all(personId, personId, limit) as CoEngager[];
}

export interface PersonTopic {
  name: string;
  category: string;
  count: number;
}

export function getPersonTopics(personId: number, limit = 5): PersonTopic[] {
  const db = getDb();
  return db
    .prepare(
      `SELECT t.name, t.category, COUNT(*) as count
       FROM engagements eg
       JOIN engagers e ON eg.engager_id = e.id
       JOIN content_topics ct ON ct.content_id = eg.content_item_id
       JOIN topics t ON t.id = ct.topic_id
       WHERE e.person_id = ?
       GROUP BY t.id
       ORDER BY count DESC
       LIMIT ?`,
    )
    .all(personId, limit) as PersonTopic[];
}

export interface PersonSourceAuthor {
  handle: string;
  name: string | null;
  platform: string;
  shared_posts: number;
}

export function getPersonSourceAuthors(personId: number, limit = 5): PersonSourceAuthor[] {
  const db = getDb();
  return db
    .prepare(
      `SELECT s.handle, s.name, s.platform,
              COUNT(DISTINCT eg.content_item_id) as shared_posts
       FROM engagements eg
       JOIN engagers e ON eg.engager_id = e.id
       JOIN sources s ON eg.source_id = s.id
       WHERE e.person_id = ?
       GROUP BY s.id
       ORDER BY shared_posts DESC
       LIMIT ?`,
    )
    .all(personId, limit) as PersonSourceAuthor[];
}

export function updatePersonStage(personId: number, stage: string): void {
  const db = getDb();
  db.prepare(
    "UPDATE people SET stage = ?, stage_updated_at = datetime('now') WHERE id = ?",
  ).run(stage, personId);
}

// -----------------------------------------------------------------
// Named Accounts — specific companies/contacts you track for employee engagement
// -----------------------------------------------------------------

export interface NamedAccountRow extends Source {
  content_count: number;
  signal_count: number;
  insight_count: number;
  latest_post_at: string | null;
  last_signal_at: string | null;
}

export function getNamedAccounts(): NamedAccountRow[] {
  const db = getDb();
  return db
    .prepare(
      `SELECT s.*,
              COUNT(DISTINCT ci.id) as content_count,
              COUNT(DISTINCT sig.id) as signal_count,
              (SELECT COUNT(*) FROM insights WHERE target_account = s.company
                 OR target_account = s.name
                 OR source_id = s.id) as insight_count,
              MAX(ci.published_at) as latest_post_at,
              MAX(sig.created_at) as last_signal_at
       FROM sources s
       LEFT JOIN content_items ci ON ci.source_id = s.id
       LEFT JOIN signals sig ON sig.source_id = s.id AND sig.status IN ('new','acknowledged')
       WHERE s.relevance = 'named-account' AND s.status = 'active'
       GROUP BY s.id
       ORDER BY last_signal_at DESC NULLS LAST, s.name ASC`,
    )
    .all() as NamedAccountRow[];
}

export function getNamedAccountById(id: number): NamedAccountRow | null {
  const db = getDb();
  const row = db
    .prepare(
      `SELECT s.*,
              COUNT(DISTINCT ci.id) as content_count,
              COUNT(DISTINCT sig.id) as signal_count,
              (SELECT COUNT(*) FROM insights WHERE target_account = s.company
                 OR target_account = s.name
                 OR source_id = s.id) as insight_count,
              MAX(ci.published_at) as latest_post_at,
              MAX(sig.created_at) as last_signal_at
       FROM sources s
       LEFT JOIN content_items ci ON ci.source_id = s.id
       LEFT JOIN signals sig ON sig.source_id = s.id
       WHERE s.id = ? AND s.relevance = 'named-account'
       GROUP BY s.id`,
    )
    .get(id) as NamedAccountRow | undefined;
  return row ?? null;
}

export function getInsightsForAccount(account: NamedAccountRow, limit = 10): Insight[] {
  const db = getDb();
  const candidates = [account.company, account.name].filter(Boolean) as string[];
  const placeholders = candidates.map(() => "?").join(", ");
  return db
    .prepare(
      `SELECT i.*,
              s.name as source_name,
              sig.signal_type, sig.urgency as signal_urgency, sig.title as signal_title,
              ci.url as post_url,
              ci.published_at as post_published_at,
              CAST((julianday('now') - julianday(COALESCE(ci.published_at, ci.scraped_at))) AS INTEGER) AS post_age_days
       FROM insights i
       LEFT JOIN sources s ON s.id = i.source_id
       LEFT JOIN signals sig ON sig.id = i.signal_id
       LEFT JOIN content_items ci ON ci.id = sig.content_id
       WHERE (i.source_id = ? OR i.target_account IN (${placeholders}))
         AND i.status IN ('new','shared')
       ORDER BY post_age_days ASC, i.priority DESC, i.created_at DESC
       LIMIT ?`,
    )
    .all(account.id, ...candidates, limit) as Insight[];
}

export function getInsightCounts(): InsightCounts {
  const db = getDb();
  const total = (db.prepare("SELECT COUNT(*) as c FROM insights").get() as { c: number }).c;
  const new_count = (db
    .prepare("SELECT COUNT(*) as c FROM insights WHERE status='new'")
    .get() as { c: number }).c;
  const vRows = db
    .prepare(
      "SELECT vertical, COUNT(*) as c FROM insights WHERE vertical IS NOT NULL GROUP BY vertical",
    )
    .all() as { vertical: string; c: number }[];
  const by_vertical: Record<string, number> = {};
  for (const r of vRows) by_vertical[r.vertical] = r.c;
  const aRows = db
    .prepare(
      "SELECT target_account, COUNT(*) as c FROM insights WHERE target_account IS NOT NULL GROUP BY target_account ORDER BY c DESC",
    )
    .all() as { target_account: string; c: number }[];
  const by_account: Record<string, number> = {};
  for (const r of aRows) by_account[r.target_account] = r.c;
  return { total, new_count, by_vertical, by_account };
}

// =================================================================
// System Nexus — bird's-eye view of engager ↔ source ↔ signal network
// Consumed by /nexus page + src/components/system-nexus-graph.tsx
// =================================================================

export interface NexusEngagerNode {
  id: number;
  name: string | null;
  company: string | null;
  job_bucket: string | null;
  stars: number | null;
  platform: "linkedin" | "x" | "reddit";
  profile_image_url: string | null;
  source_count: number;
}

export interface NexusSourceNode {
  id: number;
  name: string;
  relevance: Relevance;
  tier: Tier | null;
  platform: Platform;
  profile_image_url: string | null;
  engager_count: number;
  signal_count: number;
}

export interface NexusSignalNode {
  id: number;
  signal_type: string;
  title: string;
  urgency: "act-now" | "this-week" | "this-month" | "backlog";
  source_id: number;
  post_age_days: number | null;
}

export interface NexusEdge {
  id: string;
  source: string; // e.g., "engager-42"
  target: string; // e.g., "source-17"
  weight: number;
}

export interface NexusData {
  engagers: NexusEngagerNode[];
  sources: NexusSourceNode[];
  signals: NexusSignalNode[];
  edges: NexusEdge[];
}

/**
 * System-wide relationship map for the /nexus page.
 *
 * Scope rules:
 * - Top 30 ICP engagers (uses the same predicate as WS1 — see docs/icp-filter.md),
 *   ranked by how many distinct sources they've touched.
 * - Sources those engagers have engaged with (capped to ~20).
 * - Fresh signals on those sources (< 30 days per freshness.md), capped to ~25.
 * - Edges: engager→source (weight = engagement count), source→signal.
 *
 * Not paginated — nexus is always a snapshot. If node count grows past 80 we
 * should tighten limits or add drill-down, not stream more nodes.
 */
export function getNexusData(): NexusData {
  const db = getDb();

  // 1. Top ICP engagers with at least one engagement
  const engagers = db
    .prepare(
      `SELECT e.id, e.name, e.company, e.job_bucket,
              e.platform, e.profile_image_url,
              icp.overall_stars as stars,
              COUNT(DISTINCT eg.source_id) as source_count
       FROM engagers e
       LEFT JOIN icp_scores icp ON icp.engager_id = e.id
       LEFT JOIN engagements eg ON eg.engager_id = e.id
       WHERE (e.is_internal = 0 OR e.is_internal IS NULL)
         AND ${ICP_ENGAGER_PREDICATE}
       GROUP BY e.id
       HAVING source_count > 0
       ORDER BY source_count DESC, stars DESC NULLS LAST
       LIMIT 30`,
    )
    .all() as NexusEngagerNode[];

  if (engagers.length === 0) {
    return { engagers: [], sources: [], signals: [], edges: [] };
  }

  const engagerIds = engagers.map((e) => e.id);
  const engagerIdPlaceholders = engagerIds.map(() => "?").join(",");

  // 2. Sources reached by those engagers (engagement-weighted)
  const sources = db
    .prepare(
      `SELECT s.id, s.name, s.relevance, s.tier, s.platform, s.profile_image_url,
              COUNT(DISTINCT eg.engager_id) as engager_count,
              (SELECT COUNT(*) FROM signals sig
                 LEFT JOIN content_items ci ON ci.id = sig.content_id
               WHERE sig.source_id = s.id
                 AND sig.status IN ('new','acknowledged')
                 AND (ci.published_at IS NULL
                      OR (julianday('now') - julianday(ci.published_at)) < 30)) as signal_count
       FROM engagements eg
       JOIN sources s ON s.id = eg.source_id
       WHERE eg.engager_id IN (${engagerIdPlaceholders})
         AND s.status = 'active'
       GROUP BY s.id
       ORDER BY engager_count DESC, signal_count DESC
       LIMIT 20`,
    )
    .all(...engagerIds) as NexusSourceNode[];

  const sourceIds = sources.map((s) => s.id);

  // 3. Fresh signals on those sources (freshness.md: < 30 days)
  const signals = sourceIds.length
    ? (db
        .prepare(
          `SELECT sig.id, sig.signal_type, sig.title, sig.urgency, sig.source_id,
                  CAST(julianday('now') - julianday(ci.published_at) AS INTEGER) as post_age_days
           FROM signals sig
           LEFT JOIN content_items ci ON ci.id = sig.content_id
           WHERE sig.status IN ('new','acknowledged')
             AND sig.source_id IN (${sourceIds.map(() => "?").join(",")})
             AND (ci.published_at IS NULL
                  OR (julianday('now') - julianday(ci.published_at)) < 30)
           ORDER BY
             CASE sig.urgency WHEN 'act-now' THEN 1 WHEN 'this-week' THEN 2 WHEN 'this-month' THEN 3 ELSE 4 END,
             post_age_days ASC
           LIMIT 25`,
        )
        .all(...sourceIds) as NexusSignalNode[])
    : [];

  // 4. Edges — engager→source (weighted) + source→signal (one per signal)
  const sourceIdSet = new Set(sourceIds);
  const engagerSourceRows = db
    .prepare(
      `SELECT eg.engager_id, eg.source_id, COUNT(*) as weight
       FROM engagements eg
       WHERE eg.engager_id IN (${engagerIdPlaceholders})
       GROUP BY eg.engager_id, eg.source_id`,
    )
    .all(...engagerIds) as { engager_id: number; source_id: number; weight: number }[];

  const edges: NexusEdge[] = [];
  for (const row of engagerSourceRows) {
    if (!row.source_id || !sourceIdSet.has(row.source_id)) continue;
    edges.push({
      id: `e-${row.engager_id}-s-${row.source_id}`,
      source: `engager-${row.engager_id}`,
      target: `source-${row.source_id}`,
      weight: row.weight,
    });
  }
  for (const sig of signals) {
    edges.push({
      id: `s-${sig.source_id}-sig-${sig.id}`,
      source: `source-${sig.source_id}`,
      target: `signal-${sig.id}`,
      weight: 1,
    });
  }

  return { engagers, sources, signals, edges };
}

// -----------------------------------------------------------------
// Signal-to-Leads (Apollo flagship: actionable signals with ICP people)
// -----------------------------------------------------------------

export interface SignalWithContent extends SignalRow {
  content_url: string | null;
  content_body: string | null;
  content_likes: number;
  content_comments: number;
  lead_count: number;
}

export function getSignalsWithLeadCounts(filters: {
  urgency?: "act-now" | "this-week" | "this-month" | "backlog" | "all";
  signalType?: string;
  limit?: number;
} = {}): SignalWithContent[] {
  const db = getDb();
  const conditions: string[] = ["sig.status IN ('new', 'acknowledged')"];
  const params: (string | number)[] = [];

  if (filters.urgency && filters.urgency !== "all") {
    conditions.push("sig.urgency = ?");
    params.push(filters.urgency);
  }
  if (filters.signalType) {
    conditions.push("sig.signal_type = ?");
    params.push(filters.signalType);
  }
  // Default: hide stale (>60d)
  conditions.push(
    "(ci.published_at IS NULL OR (julianday('now') - julianday(ci.published_at)) < 60)"
  );

  const where = `WHERE ${conditions.join(" AND ")}`;
  const limit = filters.limit ?? 50;

  return db
    .prepare(
      `SELECT
        sig.id, sig.signal_type, sig.title, sig.description, sig.urgency, sig.status,
        s.name AS source_name, s.platform AS platform, s.relevance AS source_relevance, s.tier AS tier,
        sig.created_at AS created_at,
        ci.published_at AS post_published_at,
        CAST((julianday('now') - julianday(COALESCE(ci.published_at, ci.scraped_at))) AS INTEGER) AS post_age_days,
        ci.url AS content_url,
        ci.body AS content_body,
        COALESCE(ci.engagement_likes, 0) AS content_likes,
        COALESCE(ci.engagement_comments, 0) AS content_comments,
        (SELECT COUNT(DISTINCT e2.id)
         FROM engagements eg2
         JOIN engagers e2 ON e2.id = eg2.engager_id
         JOIN icp_scores icp2 ON icp2.engager_id = e2.id
         WHERE eg2.content_item_id = ci.id AND icp2.overall_stars >= 3
        ) AS lead_count
       FROM signals sig
       LEFT JOIN sources s ON s.id = sig.source_id
       LEFT JOIN content_items ci ON ci.id = sig.content_id
       ${where}
       ORDER BY
         CASE sig.urgency WHEN 'act-now' THEN 1 WHEN 'this-week' THEN 2 WHEN 'this-month' THEN 3 ELSE 4 END,
         lead_count DESC,
         post_age_days ASC
       LIMIT ?`
    )
    .all(...params, limit) as SignalWithContent[];
}

export interface SignalLead {
  id: number;
  name: string | null;
  title: string | null;
  company: string | null;
  profile_url: string | null;
  platform: string;
  overall_stars: number;
}

export function getLeadsForSignal(signalId: number, limit = 8): SignalLead[] {
  const db = getDb();
  return db
    .prepare(
      `SELECT DISTINCT e.id, e.name, e.title, e.company, e.profile_url, e.platform,
              icp.overall_stars
       FROM engagers e
       JOIN icp_scores icp ON icp.engager_id = e.id
       JOIN engagements eg ON eg.engager_id = e.id
       JOIN content_items ci ON ci.id = eg.content_item_id
       JOIN signals sig ON sig.content_id = ci.id
       WHERE sig.id = ? AND icp.overall_stars >= 3
       ORDER BY icp.overall_stars DESC, e.name
       LIMIT ?`
    )
    .all(signalId, limit) as SignalLead[];
}

/**
 * Signal drawer composition — joins signal + content + source + top 5 ICP leads
 * (with profile_image_url for avatars) + highest-priority insight.
 * Return shape matches drawers/types `SignalDrawerData`.
 */
export function getSignalDrawerData(signalId: number): SignalDrawerData | null {
  const db = getDb();
  const row = db
    .prepare(
      `SELECT
         sig.id, sig.title, sig.description, sig.signal_type, sig.urgency,
         s.id AS source_id, s.name AS source_name, s.platform AS platform,
         ci.published_at AS post_published_at,
         CAST((julianday('now') - julianday(COALESCE(ci.published_at, ci.scraped_at))) AS INTEGER) AS post_age_days,
         ci.url AS content_url, ci.body AS content_body,
         COALESCE(ci.engagement_likes, 0) AS content_likes,
         COALESCE(ci.engagement_comments, 0) AS content_comments
       FROM signals sig
       LEFT JOIN sources s ON s.id = sig.source_id
       LEFT JOIN content_items ci ON ci.id = sig.content_id
       WHERE sig.id = ?`,
    )
    .get(signalId) as Omit<SignalDrawerData, "outreach_angle" | "opener_draft" | "leads"> | undefined;

  if (!row) return null;

  const leads = db
    .prepare(
      `SELECT DISTINCT e.id, e.name, e.title, e.company, e.profile_url, e.profile_image_url, e.platform,
              icp.overall_stars
       FROM engagers e
       JOIN icp_scores icp ON icp.engager_id = e.id
       JOIN engagements eg ON eg.engager_id = e.id
       JOIN content_items ci ON ci.id = eg.content_item_id
       JOIN signals sig ON sig.content_id = ci.id
       WHERE sig.id = ? AND icp.overall_stars >= 3
       ORDER BY icp.overall_stars DESC, e.name
       LIMIT 5`,
    )
    .all(signalId) as SignalDrawerLead[];

  const insight = db
    .prepare(
      `SELECT outreach_angle, opener_draft
       FROM insights
       WHERE signal_id = ? AND status IN ('new', 'shared')
       ORDER BY priority DESC
       LIMIT 1`,
    )
    .get(signalId) as { outreach_angle: string; opener_draft: string } | undefined;

  return {
    ...row,
    outreach_angle: insight?.outreach_angle ?? null,
    opener_draft: insight?.opener_draft ?? null,
    leads,
  };
}

/**
 * Source drawer composition — profile + stats + recent content + signals + top ICP engagers.
 * Return shape matches drawers/types `SourceDrawerData`.
 */
export function getSourceDrawerData(sourceId: number): SourceDrawerData | null {
  const db = getDb();

  const src = db
    .prepare(
      `SELECT id, name, title, company, handle, platform, relevance,
              url, profile_image_url, followers
       FROM sources
       WHERE id = ?`,
    )
    .get(sourceId) as
    | {
        id: number;
        name: string;
        title: string | null;
        company: string | null;
        handle: string | null;
        platform: string;
        relevance: string | null;
        url: string | null;
        profile_image_url: string | null;
        followers: number | null;
      }
    | undefined;

  if (!src) return null;

  const recentContent = db
    .prepare(
      `SELECT id, title, body, url, published_at,
              COALESCE(engagement_likes, 0) AS engagement_likes,
              COALESCE(engagement_comments, 0) AS engagement_comments
       FROM content_items
       WHERE source_id = ?
       ORDER BY COALESCE(published_at, scraped_at) DESC
       LIMIT 5`,
    )
    .all(sourceId) as SourceDrawerRecentContent[];

  const signals = db
    .prepare(
      `SELECT sig.id, sig.title, sig.signal_type, sig.urgency,
              CAST((julianday('now') - julianday(COALESCE(ci.published_at, ci.scraped_at))) AS INTEGER) AS post_age_days
       FROM signals sig
       LEFT JOIN content_items ci ON ci.id = sig.content_id
       WHERE sig.source_id = ? AND sig.status IN ('new', 'acknowledged')
       ORDER BY
         CASE sig.urgency WHEN 'act-now' THEN 1 WHEN 'this-week' THEN 2 WHEN 'this-month' THEN 3 ELSE 4 END,
         post_age_days ASC
       LIMIT 5`,
    )
    .all(sourceId) as SourceDrawerSignalSummary[];

  const topEngagers = db
    .prepare(
      `SELECT e.id, e.name, e.title, e.company, e.profile_url, e.profile_image_url, e.platform,
              icp.overall_stars
       FROM engagers e
       JOIN icp_scores icp ON icp.engager_id = e.id
       JOIN engagements eg ON eg.engager_id = e.id
       WHERE eg.source_id = ? AND icp.overall_stars >= 3
       GROUP BY e.id
       ORDER BY icp.overall_stars DESC, e.name
       LIMIT 8`,
    )
    .all(sourceId) as SourceDrawerEngager[];

  const postCount = db
    .prepare(`SELECT COUNT(*) AS c FROM content_items WHERE source_id = ?`)
    .get(sourceId) as { c: number };
  const signalCount = db
    .prepare(`SELECT COUNT(*) AS c FROM signals WHERE source_id = ?`)
    .get(sourceId) as { c: number };
  const icpEngagerCount = db
    .prepare(
      `SELECT COUNT(DISTINCT e.id) AS c
       FROM engagers e
       JOIN icp_scores icp ON icp.engager_id = e.id
       JOIN engagements eg ON eg.engager_id = e.id
       WHERE eg.source_id = ? AND icp.overall_stars >= 3`,
    )
    .get(sourceId) as { c: number };

  return {
    id: src.id,
    name: src.name,
    title: src.title,
    company: src.company,
    handle: src.handle,
    platform: src.platform,
    relevance: src.relevance,
    profileUrl: src.url,
    profileImageUrl: src.profile_image_url,
    followers: src.followers,
    stats: {
      total_posts: postCount.c,
      signal_count: signalCount.c,
      icp_engager_count: icpEngagerCount.c,
    },
    recentContent,
    signals,
    topEngagers,
  };
}

// -----------------------------------------------------------------
// Lead reasoning (per-lead "why this person matters" briefs)
// -----------------------------------------------------------------

export interface LeadReasoningRow {
  id: number;
  signal_id: number;
  engager_id: number;
  comment_text: string | null;
  reasoning: string;
  created_at: string;
}

/** All reasoning rows for a single engager (used by nexus drawer). */
export function getLeadReasoning(engagerId: number): LeadReasoningRow[] {
  const db = getDb();
  return db
    .prepare(
      `SELECT lr.*, sig.title as signal_title
       FROM lead_reasoning lr
       LEFT JOIN signals sig ON sig.id = lr.signal_id
       WHERE lr.engager_id = ?
       ORDER BY lr.created_at DESC`,
    )
    .all(engagerId) as (LeadReasoningRow & { signal_title?: string })[];
}

/** Engagements for a single engager with post context (used by nexus drawer). */
export function getEngagerEngagements(engagerId: number, limit = 20): {
  id: number;
  engagement_type: string;
  comment_text: string | null;
  post_url: string | null;
  engaged_at: string | null;
  content_title: string | null;
  content_body: string | null;
  source_name: string | null;
}[] {
  const db = getDb();
  return db
    .prepare(
      `SELECT eg.id, eg.engagement_type, eg.comment_text, eg.post_url, eg.engaged_at,
              ci.title as content_title, SUBSTR(ci.body, 1, 200) as content_body,
              s.name as source_name
       FROM engagements eg
       LEFT JOIN content_items ci ON ci.id = eg.content_item_id
       LEFT JOIN sources s ON eg.source_id = s.id
       WHERE eg.engager_id = ?
       ORDER BY COALESCE(eg.engaged_at, '') DESC
       LIMIT ?`,
    )
    .all(engagerId, limit) as {
    id: number;
    engagement_type: string;
    comment_text: string | null;
    post_url: string | null;
    engaged_at: string | null;
    content_title: string | null;
    content_body: string | null;
    source_name: string | null;
  }[];
}

/**
 * Lead reasoning keyed by signal → engager for the signal accordion.
 * Returns a nested map: { signalId: { engagerId: reasoning } }
 */
export function getLeadReasoningForSignals(
  signalIds: number[],
): Record<number, Record<number, string>> {
  if (signalIds.length === 0) return {};
  const db = getDb();
  const placeholders = signalIds.map(() => "?").join(",");
  const rows = db
    .prepare(
      `SELECT signal_id, engager_id, reasoning
       FROM lead_reasoning
       WHERE signal_id IN (${placeholders})`,
    )
    .all(...signalIds) as { signal_id: number; engager_id: number; reasoning: string }[];

  const map: Record<number, Record<number, string>> = {};
  for (const r of rows) {
    if (!map[r.signal_id]) map[r.signal_id] = {};
    map[r.signal_id][r.engager_id] = r.reasoning;
  }
  return map;
}

/**
 * Engagement comments keyed by signal → engager for the signal accordion.
 * Returns: { signalId: { engagerId: comment_text } }
 */
export function getCommentsForSignals(
  signalIds: number[],
): Record<number, Record<number, string>> {
  if (signalIds.length === 0) return {};
  const db = getDb();
  const placeholders = signalIds.map(() => "?").join(",");
  const rows = db
    .prepare(
      `SELECT sig.id as signal_id, eg.engager_id, eg.comment_text, eg.engagement_type
       FROM signals sig
       JOIN content_items ci ON ci.id = sig.content_id
       JOIN engagements eg ON eg.content_item_id = ci.id
       JOIN icp_scores icp ON icp.engager_id = eg.engager_id
       WHERE sig.id IN (${placeholders})
         AND icp.overall_stars >= 3`,
    )
    .all(...signalIds) as {
    signal_id: number;
    engager_id: number;
    comment_text: string | null;
    engagement_type: string;
  }[];

  const map: Record<number, Record<number, string>> = {};
  for (const r of rows) {
    if (!map[r.signal_id]) map[r.signal_id] = {};
    // Prefer actual comment text; fall back to engagement type description
    map[r.signal_id][r.engager_id] =
      r.comment_text ?? (r.engagement_type === "like" ? "Liked this post" : "Reposted");
  }
  return map;
}

/**
 * Pipeline-generated insights keyed by signal_id for the signal accordion.
 * Returns: { signalId: { outreach_angle, opener_draft } }
 */
export function getInsightsForSignals(
  signalIds: number[],
): Record<number, { outreach_angle: string; opener_draft: string }> {
  if (signalIds.length === 0) return {};
  const db = getDb();
  const placeholders = signalIds.map(() => "?").join(",");
  const rows = db
    .prepare(
      `SELECT signal_id, outreach_angle, opener_draft
       FROM insights
       WHERE signal_id IN (${placeholders})
         AND status IN ('new', 'shared')
       ORDER BY priority DESC`,
    )
    .all(...signalIds) as {
    signal_id: number;
    outreach_angle: string;
    opener_draft: string;
  }[];

  const map: Record<number, { outreach_angle: string; opener_draft: string }> = {};
  for (const r of rows) {
    // First (highest priority) insight wins per signal
    if (!map[r.signal_id]) {
      map[r.signal_id] = {
        outreach_angle: r.outreach_angle,
        opener_draft: r.opener_draft,
      };
    }
  }
  return map;
}

/** Full engager record by ID (used by nexus drawer). */
export function getEngagerById(engagerId: number): Engager | null {
  const db = getDb();
  const row = db
    .prepare(
      `SELECT e.*,
              COUNT(eg.id) as engagement_count,
              icp.overall_stars, icp.persona_fit, icp.company_fit,
              icp.engagement_depth, icp.budget_potential
       FROM engagers e
       LEFT JOIN engagements eg ON eg.engager_id = e.id
       LEFT JOIN icp_scores icp ON icp.engager_id = e.id
       WHERE e.id = ?
       GROUP BY e.id`,
    )
    .get(engagerId) as Engager | undefined;
  return row ?? null;
}
