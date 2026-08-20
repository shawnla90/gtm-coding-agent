// Reconcile the ledger against LinkedIn's own truth.
// READ-ONLY ON LINKEDIN: this script never clicks Connect, Send, or Reply.
//
// Run it from DAY ONE — accepted_at is a discovery timestamp, and this is the discoverer.
//
// Connections are matched by exact /in/ slug. Inbox rows are first narrowed by
// unique full name, then confirmed only when the opened thread contains the
// expected participant profile URL. Name-only rows become review candidates.
//
// Usage:
//   node reconcile.js --dry-run --headed --scroll 10
//   node reconcile.js --headless --capture-evidence --scroll 40
const { chromium } = require('playwright');
const { DatabaseSync } = require('node:sqlite');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

const PROFILE = path.join(__dirname, 'pw-profile');
const SHOTS = path.join(__dirname, 'screenshots');
const DB = path.join(__dirname, 'li_outreach.db');
const CONFIG_PATH = path.join(__dirname, 'config.json');
const args = process.argv.slice(2);
const has = (key) => args.includes(key);
const opt = (key, fallback) => {
  const i = args.indexOf(key);
  return i >= 0 ? args[i + 1] : fallback;
};
const DRY = has('--dry-run');
const HEADLESS = has('--headless') && !has('--headed');
const CAPTURE_EVIDENCE = has('--capture-evidence');
const SKIP_CONNECTIONS = has('--skip-connections');
const SCROLLS = parseInt(opt('--scroll', '40'), 10);
const MAX_EVIDENCE = parseInt(opt('--max-evidence', '30'), 10);

// Your own member id — the observer must know who YOU are so it never
// mistakes you for a thread participant. Refuses to run without it.
if (!fs.existsSync(CONFIG_PATH)) {
  console.error(JSON.stringify({ error: 'no_config', hint: 'cp config.example.json config.json and edit it' }));
  process.exit(1);
}
const CFG = JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));
const SELF_MEMBER_ID = CFG.self_member_id;
if (!SELF_MEMBER_ID || /PUT-YOUR/.test(SELF_MEMBER_ID)) {
  console.error(JSON.stringify({ error: 'self_member_id not set in config.json' }));
  process.exit(1);
}

fs.mkdirSync(SHOTS, { recursive: true });
const db = new DatabaseSync(DB);
db.exec(`
  CREATE TABLE IF NOT EXISTS reply_evidence (
    id INTEGER PRIMARY KEY,
    evidence_key TEXT NOT NULL UNIQUE,
    profile_url TEXT NOT NULL,
    thread_url TEXT,
    thread_id TEXT,
    participant_url TEXT,
    last_message_at TEXT,
    last_direction TEXT,
    screenshot_path TEXT,
    screenshot_sha256 TEXT,
    match_basis TEXT NOT NULL,
    match_status TEXT NOT NULL,
    captured_at TEXT NOT NULL
  );
  CREATE INDEX IF NOT EXISTS idx_reply_evidence_profile
    ON reply_evidence(profile_url, match_status);
  CREATE TABLE IF NOT EXISTS reconcile_runs (
    id INTEGER PRIMARY KEY,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    dry_run INTEGER NOT NULL,
    headless INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'running',
    connections_scanned INTEGER DEFAULT 0,
    threads_scanned INTEGER DEFAULT 0,
    accepted_new INTEGER DEFAULT 0,
    replies_confirmed INTEGER DEFAULT 0,
    review_candidates INTEGER DEFAULT 0,
    evidence_captured INTEGER DEFAULT 0,
    error TEXT
  );
`);
if (!DRY) {
  // accepted_at is the durable fact; keep the convenience status in agreement.
  db.prepare("UPDATE leads SET cr_status='accepted' WHERE accepted_at IS NOT NULL AND cr_status NOT IN ('accepted','sending')").run();
}

const now = () => new Date().toISOString();
const rnd = (a, b) => a + Math.floor(Math.random() * (b - a));
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const norm = (value) => String(value || '').toLowerCase().replace(/\s+/g, ' ').trim();
const slugOf = (url) => {
  const match = String(url || '').match(/\/in\/([^/?#]+)/i);
  return match ? match[1].toLowerCase() : null;
};
const threadIdOf = (url) => {
  const match = String(url || '').match(/\/messaging\/thread\/([^/?#]+)/i);
  return match ? decodeURIComponent(match[1]) : null;
};
const safeSlug = (value) => String(value || 'unknown').replace(/[^a-z0-9_-]+/gi, '_').slice(0, 80);
const sha256 = (file) => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');

const leads = db.prepare(
  'SELECT profile_url, first_name, last_name, cr_status, accepted_at, reply_status FROM leads'
).all();
const bySlug = new Map();
const byName = new Map();
for (const row of leads) {
  const slug = slugOf(row.profile_url);
  if (slug) bySlug.set(slug, row);
  const full = norm(`${row.first_name} ${row.last_name === '-' ? '' : row.last_name}`);
  if (!byName.has(full)) byName.set(full, []);
  byName.get(full).push(row);
}

const runResult = db.prepare(
  'INSERT INTO reconcile_runs(started_at,dry_run,headless) VALUES (?,?,?)'
).run(now(), DRY ? 1 : 0, HEADLESS ? 1 : 0);
const runId = Number(runResult.lastInsertRowid);

function finishRun(status, summary, error = null) {
  db.prepare(`UPDATE reconcile_runs SET finished_at=?, status=?, connections_scanned=?,
    threads_scanned=?, accepted_new=?, replies_confirmed=?, review_candidates=?,
    evidence_captured=?, error=? WHERE id=?`).run(
      now(), status, summary.connections_scanned, summary.threads_scanned,
      summary.accepted_new.length, summary.replies_confirmed.length,
      summary.review_candidates.length, summary.evidence_captured.length,
      error ? String(error).slice(0, 1000) : null, runId
    );
}

function assertAccountSafe(page) {
  const url = page.url();
  if (/\/login|\/authwall|\/checkpoint|challenge/i.test(url)) {
    throw new Error(`ACCOUNT_RISK_STOP:${url}`);
  }
}

async function captureThreadEvidence(page, thread, lead, inbound) {
  const expectedSlug = slugOf(lead.profile_url);
  if (!expectedSlug) {
    return { matchStatus: 'name_only_candidate', matchBasis: 'unique_name', participantUrl: null };
  }

  let resolvedThreadUrl = thread.threadUrl;
  if (resolvedThreadUrl) {
    await page.goto(resolvedThreadUrl, { waitUntil: 'domcontentloaded', timeout: 45000 });
  } else {
    const item = page.locator('li.msg-conversation-listitem, li[class*="convo-item"]')
      .filter({ hasText: thread.name });
    if (await item.count() !== 1) {
      return { matchStatus: 'name_only_candidate', matchBasis: 'unique_name', participantUrl: null };
    }
    await item.first().click({ timeout: 15000 });
  }
  await sleep(rnd(1200, 2200));
  assertAccountSafe(page);
  resolvedThreadUrl = /\/messaging\/thread\//i.test(page.url()) ? page.url() : resolvedThreadUrl;
  const details = await page.evaluate((selfMemberId) => {
    const links = [...new Set([...document.querySelectorAll('a[href*="/in/"]')]
      .map((link) => link.href.split('?')[0].replace(/\/$/, '')))];
    const participants = links.filter((href) => {
      const memberId = String(href || '').match(/\/in\/([^/?#]+)/i)?.[1];
      return memberId && memberId !== selfMemberId;
    });
    const times = [...document.querySelectorAll('time[datetime]')]
      .map((el) => el.getAttribute('datetime'))
      .filter(Boolean);
    return {
      memberUrl: participants.length === 1 ? participants[0] : null,
      lastMessageAt: times.length ? times[times.length - 1] : null,
    };
  }, SELF_MEMBER_ID).catch(() => ({ memberUrl: null, lastMessageAt: null }));

  let participantUrl = null;
  if (details.memberUrl) {
    const verifyPage = await page.context().newPage();
    try {
      await verifyPage.goto(details.memberUrl, { waitUntil: 'domcontentloaded', timeout: 45000 });
      await sleep(rnd(900, 1500));
      assertAccountSafe(verifyPage);
      const canonical = await verifyPage.evaluate(() =>
        document.querySelector('link[rel="canonical"]')?.getAttribute('href')
        || document.querySelector('meta[property="og:url"]')?.getAttribute('content')
        || location.href
      ).catch(() => verifyPage.url());
      participantUrl = String(canonical || verifyPage.url()).split('?')[0].replace(/\/$/, '');
    } finally {
      await verifyPage.close().catch(() => {});
    }
  }

  const confirmed = slugOf(participantUrl) === expectedSlug;
  const matchStatus = confirmed ? 'confirmed_profile_url' : 'name_only_candidate';
  const matchBasis = confirmed ? 'member_url_resolved_to_profile' : 'unique_name';
  const evidenceKey = `${lead.profile_url}|${resolvedThreadUrl || thread.name}`;
  const existing = db.prepare(
    "SELECT screenshot_path FROM reply_evidence WHERE evidence_key=? AND match_status='confirmed_profile_url'"
  ).get(evidenceKey);
  let screenshotPath = existing?.screenshot_path || null;
  let screenshotSha = null;
  if (confirmed && CAPTURE_EVIDENCE && !DRY && !screenshotPath) {
    screenshotPath = path.join(SHOTS, `reply_${safeSlug(expectedSlug)}_${Date.now()}.png`);
    await page.screenshot({ path: screenshotPath, fullPage: false });
    screenshotSha = sha256(screenshotPath);
  } else if (screenshotPath && fs.existsSync(screenshotPath)) {
    screenshotSha = sha256(screenshotPath);
  }

  if (!DRY) {
    db.prepare(`INSERT INTO reply_evidence(
      evidence_key,profile_url,thread_url,thread_id,participant_url,last_message_at,
      last_direction,screenshot_path,screenshot_sha256,match_basis,match_status,captured_at
    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    ON CONFLICT(evidence_key) DO UPDATE SET
      thread_id=excluded.thread_id, participant_url=excluded.participant_url,
      last_message_at=COALESCE(excluded.last_message_at,reply_evidence.last_message_at),
      last_direction=excluded.last_direction,
      screenshot_path=COALESCE(excluded.screenshot_path,reply_evidence.screenshot_path),
      screenshot_sha256=COALESCE(excluded.screenshot_sha256,reply_evidence.screenshot_sha256),
      match_basis=excluded.match_basis, match_status=excluded.match_status,
      captured_at=excluded.captured_at`).run(
        evidenceKey, lead.profile_url, resolvedThreadUrl, threadIdOf(resolvedThreadUrl),
        participantUrl, details.lastMessageAt, inbound ? 'in' : 'out', screenshotPath, screenshotSha,
        matchBasis, matchStatus, now()
      );
  }
  return { matchStatus, matchBasis, participantUrl, screenshotPath };
}

(async () => {
  const LOCK = path.join(__dirname, '.run.lock');
  const summary = {
    accepted_new: [],
    replies_confirmed: [],
    review_candidates: [],
    evidence_captured: [],
    connections_scanned: 0,
    threads_scanned: 0,
  };
  if (fs.existsSync(LOCK) && Date.now() - fs.statSync(LOCK).mtimeMs < 30 * 60 * 1000) {
    finishRun('skipped_locked', summary);
    console.log(JSON.stringify({ skip: 'locked' }));
    process.exit(0);
  }
  fs.writeFileSync(LOCK, String(process.pid));
  process.on('exit', () => { try { fs.unlinkSync(LOCK); } catch {} });

  let ctx;
  try {
    ctx = await chromium.launchPersistentContext(PROFILE, {
      headless: HEADLESS,
      channel: 'chrome',
      viewport: HEADLESS ? { width: 1440, height: 1000 } : null,
      args: ['--disable-blink-features=AutomationControlled'],
    });
    const page = ctx.pages()[0] || (await ctx.newPage());
    await page.goto('https://www.linkedin.com/feed/', { waitUntil: 'domcontentloaded', timeout: 45000 });
    await sleep(2500);
    const cookies = await ctx.cookies('https://www.linkedin.com').catch(() => []);
    if (!cookies.some((cookie) => cookie.name === 'li_at')) {
      throw new Error(`NOT_LOGGED_IN:${page.url()}`);
    }
    assertAccountSafe(page);

    if (!SKIP_CONNECTIONS) {
      // A) exact profile-slug acceptance reconciliation
      await page.goto('https://www.linkedin.com/mynetwork/invite-connect/connections/', {
        waitUntil: 'domcontentloaded', timeout: 45000,
      });
      await sleep(rnd(2200, 3400));
      assertAccountSafe(page);
      const seenSlugs = new Set();
      let stable = 0;
      let last = 0;
      for (let i = 0; i < SCROLLS && stable < 4; i += 1) {
        const found = await page.evaluate(() => {
          const links = [...document.querySelectorAll('a[href*="/in/"]')];
          if (links.length) links[links.length - 1].scrollIntoView({ block: 'end' });
          return links.map((link) => link.href);
        }).catch(() => []);
        for (const href of found) {
          const slug = slugOf(href);
          if (slug) seenSlugs.add(slug);
        }
        if (seenSlugs.size === last) stable += 1;
        else { stable = 0; last = seenSlugs.size; }
        await sleep(rnd(800, 1300));
      }
      summary.connections_scanned = seenSlugs.size;
      for (const slug of seenSlugs) {
        const lead = bySlug.get(slug);
        if (lead && !lead.accepted_at) {
          summary.accepted_new.push(`${lead.first_name} ${lead.last_name}`);
          if (!DRY) {
            db.prepare(`UPDATE leads SET cr_status='accepted',
              accepted_at=COALESCE(accepted_at,?), updated_at=? WHERE profile_url=?`)
              .run(now(), now(), lead.profile_url);
          }
        }
      }
    }

    // B) inbox candidates, followed by deterministic participant verification
    await page.goto('https://www.linkedin.com/messaging/', {
      waitUntil: 'domcontentloaded', timeout: 45000,
    });
    await sleep(rnd(2800, 4200));
    assertAccountSafe(page);
    for (let i = 0; i < 20; i += 1) {
      await page.evaluate(() => {
        const items = document.querySelectorAll('li.msg-conversation-listitem, li[class*="convo-item"]');
        if (items.length) items[items.length - 1].scrollIntoView({ block: 'end' });
      }).catch(() => {});
      await sleep(rnd(550, 950));
    }
    const threads = await page.evaluate(() => {
      const items = [...document.querySelectorAll('li.msg-conversation-listitem, li[class*="convo-item"]')];
      return items.map((item) => {
        const lines = (item.innerText || '').split('\n').map((s) => s.trim()).filter(Boolean)
          .filter((s) => !/^status is/i.test(s) && !/press return/i.test(s));
        const isTime = (s) => /^\d{1,2}:\d{2}\s?(am|pm)?$/i.test(s)
          || /^\d{1,2}\/\d{1,2}/.test(s) || /^\w{3} \d/.test(s);
        const snippet = [...lines].reverse().find((s) => /:\s/.test(s)) || '';
        const name = lines.find((s) => !isTime(s) && s !== snippet) || '';
        const anchor = item.querySelector('a[href*="/messaging/thread/"]');
        return { name, snippet, threadUrl: anchor ? anchor.href : null };
      }).filter((thread) => thread.name && thread.snippet);
    }).catch(() => []);
    summary.threads_scanned = threads.length;

    let evidenceAttempts = 0;
    for (const thread of threads) {
      const rows = byName.get(norm(thread.name));
      if (!rows || rows.length !== 1) continue;
      const lead = rows[0];
      const inbound = !/^you\s*:/i.test(thread.snippet.trim());
      if (!inbound) continue;
      const alreadyEvidenced = db.prepare(
        "SELECT 1 FROM reply_evidence WHERE profile_url=? AND match_status='confirmed_profile_url' LIMIT 1"
      ).get(lead.profile_url);
      if (alreadyEvidenced && lead.reply_status === 'replied') continue;
      if (evidenceAttempts >= MAX_EVIDENCE) break;
      evidenceAttempts += 1;
      const evidence = await captureThreadEvidence(page, thread, lead, inbound);
      if (evidence.matchStatus === 'confirmed_profile_url') {
        summary.replies_confirmed.push(`${lead.first_name} ${lead.last_name}`);
        if (evidence.screenshotPath) summary.evidence_captured.push(evidence.screenshotPath);
        if (!DRY && inbound && lead.reply_status !== 'replied') {
          db.prepare(`UPDATE leads SET reply_status='replied', replied_at=COALESCE(replied_at,?),
            cr_status=CASE WHEN cr_status='pending' THEN 'accepted' ELSE cr_status END,
            accepted_at=COALESCE(accepted_at,?), updated_at=? WHERE profile_url=?`)
            .run(now(), now(), now(), lead.profile_url);
        }
      } else {
        summary.review_candidates.push(`${lead.first_name} ${lead.last_name}`);
      }
      await sleep(rnd(700, 1300));
    }

    await ctx.close();
    finishRun('ok', summary);
    console.log(JSON.stringify({ dry: DRY, headless: HEADLESS, ...summary }, null, 1));
    process.exit(0);
  } catch (error) {
    if (ctx) await ctx.close().catch(() => {});
    finishRun('error', summary, error);
    console.error(JSON.stringify({ error: String(error), ...summary }, null, 1));
    process.exit(3);
  }
})();
