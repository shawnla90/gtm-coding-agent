// LinkedIn outreach sender — drives YOUR real session in a dedicated persistent Chrome profile.
// Read the chapter and the README before arming this. Your account, your risk.
//
// Modes:
//   connect  : send connection requests (with note) to non-connections
//   messages : msg1 to accepted connections (copy chosen by CR history, NOT degree)
//   auto     : checkAccepts -> messages -> connect, sized for a 30-min timer
//
// Guards: .armed file required, hard-stop on checkpoint, claim-before-click writes,
// human jitter, date-seeded cap wobble, per-run caps, idempotent ledger.
// NEVER mutates the degree field — it is a source record from the CSV import.
//
// Usage: node run.js --mode connect --limit 30 [--pilot 2] [--dry-run]
const { chromium } = require('playwright');
const { DatabaseSync } = require('node:sqlite');
const path = require('path');
const fs = require('fs');

const PROFILE = path.join(__dirname, 'pw-profile');
const SHOTS = path.join(__dirname, 'screenshots');
const DB = path.join(__dirname, 'li_outreach.db');
const ARMED_FILE = path.join(__dirname, '.armed');
const CONFIG_PATH = path.join(__dirname, 'config.json');

if (!fs.existsSync(CONFIG_PATH)) {
  console.log(JSON.stringify({ error: 'no_config', hint: 'cp config.example.json config.json and edit it' }));
  process.exit(1);
}
const CFG = JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));
const fill = (template, fn) => String(template).replaceAll('{firstName}', fn);

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const has = (k) => args.includes(k);
const MODE = opt('--mode', 'auto');
const LIMIT = parseInt(opt('--limit', '30'), 10);
const PILOT = opt('--pilot', null) ? parseInt(opt('--pilot'), 10) : null;
const DRY = has('--dry-run');

// Kill switch: bot does nothing unless .armed file exists.
// Create:  touch .armed      Kill:  rm .armed
if (!fs.existsSync(ARMED_FILE) && !DRY) {
  console.log(JSON.stringify({ skip: 'not_armed', hint: 'touch .armed to enable' }));
  process.exit(0);
}

fs.mkdirSync(SHOTS, { recursive: true });
const db = new DatabaseSync(DB);
const now = () => new Date().toISOString();
const rnd = (a, b) => a + Math.floor(Math.random() * (b - a));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const jitter = () => sleep(rnd(30000, 120000)); // 30-120s between actions

// Date-seeded cap wobble: same cap all day, different cap tomorrow.
// Exactly-N-every-day is a bot signature; this kills it deterministically.
function todaysCap(base) {
  const d = new Date().toLocaleDateString('en-CA');
  let h = 0;
  for (const c of d) h = (h * 31 + c.charCodeAt(0)) >>> 0;
  return Math.max(1, base - (h % Math.max(1, CFG.cap_jitter || 8)));
}

// ---------- guards ----------
async function checkpointGuard(page, tag) {
  const url = page.url();
  if (/\/checkpoint|\/uas\/|captcha|challenge/i.test(url)) {
    const p = path.join(SHOTS, `HARDSTOP_${tag}_${Date.now()}.png`);
    await page.screenshot({ path: p }).catch(() => {});
    throw new Error(`HARD_STOP checkpoint at ${url} (shot ${p})`);
  }
  const bad = await page.evaluate(() =>
    /unusual activity|verify it.?s you|security verification|are you a human/i.test(document.body.innerText || '')
  ).catch(() => false);
  if (bad) {
    const p = path.join(SHOTS, `HARDSTOP_${tag}_${Date.now()}.png`);
    await page.screenshot({ path: p }).catch(() => {});
    throw new Error(`HARD_STOP verification wall (shot ${p})`);
  }
}

async function gotoProfile(page, url) {
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await sleep(rnd(2500, 5000));
  await checkpointGuard(page, 'profile');
}

// returns 'connected' | 'not_connected' | 'pending' | 'unknown'
async function connectionState(page) {
  return await page.evaluate(() => {
    const main = document.querySelector('main') || document;
    const badges = [...main.querySelectorAll('span, div')].map((e) => (e.textContent || '').trim());
    const deg = badges.find((t) => /^(1st|2nd|3rd\+?)$/i.test(t));
    const btns = [...main.querySelectorAll('button, a')].map((b) => (b.textContent || '').trim().toLowerCase());
    if (btns.some((t) => t === 'pending')) return 'pending';
    if (deg && /1st/i.test(deg)) return 'connected';
    if (deg && /(2nd|3rd)/i.test(deg)) return 'not_connected';
    if (btns.some((t) => t === 'connect')) return 'not_connected';
    return 'unknown';
  });
}

async function sendConnect(page, fn) {
  const esc = String(fn).replace(/["\\\]]/g, ' ').trim();
  let btn = page.locator(
    `main a[aria-label^="Invite"][aria-label*="${esc}"][aria-label$="to connect"], ` +
    `main button[aria-label^="Invite"][aria-label*="${esc}"][aria-label$="to connect"]`
  ).first();
  if (!(await btn.count())) {
    const more = page.locator('main').getByRole('button', { name: /^more$/i }).first();
    if (await more.count()) { await more.click(); await sleep(1200); }
    btn = page.locator(`[aria-label^="Invite"][aria-label*="${esc}"][aria-label$="to connect"]`).first();
  }
  if (!(await btn.count())) return 'no_connect_button';
  await btn.click();
  await sleep(rnd(1500, 3000));
  const addNote = page.getByRole('button', { name: /add a note/i }).first();
  if (await addNote.count()) {
    await addNote.click();
    await sleep(1000);
    const ta = page.locator('textarea#custom-message, textarea[name="message"]').first();
    if (await ta.count()) { await ta.fill(fill(CFG.copy.cr_note, fn)); await sleep(rnd(800, 1600)); }
  }
  const send = page.getByRole('button', { name: /^send( invitation)?$/i }).first();
  if (await send.count()) {
    if (await send.isDisabled().catch(() => false)) return 'send_disabled';
    await send.click();
    await sleep(rnd(1500, 2500));
    return 'sent';
  }
  return 'send_button_missing';
}

async function sendMessage(page, text) {
  const main = page.locator('main');
  let btn = main.getByRole('button', { name: /^message/i }).first();
  if (!(await btn.count())) btn = main.getByRole('link', { name: /^message/i }).first();
  if (!(await btn.count())) btn = main.locator('button:has-text("Message"), a:has-text("Message")').first();
  if (!(await btn.count())) return 'no_message_button';
  await btn.click();
  await sleep(rnd(1800, 3200));
  const box = page.locator('div.msg-form__contenteditable[contenteditable="true"]').first();
  await box.waitFor({ timeout: 8000 }).catch(() => {});
  if (!(await box.count())) return 'no_compose_box';
  await box.click();
  await box.type(text, { delay: rnd(20, 60) });
  await sleep(rnd(900, 1800));
  let send = page.locator('button.msg-form__send-button, button.msg-form__send-btn').first();
  if (!(await send.count())) send = page.locator('.msg-form__right-actions button, button[type="submit"]:has-text("Send")').first();
  if (!(await send.count())) return 'send_missing';
  if (await send.isDisabled().catch(() => false)) return 'send_disabled';
  await send.click();
  await sleep(rnd(1200, 2200));
  return 'sent';
}

// ---------- claim-before-click ----------
// The lesson from the original campaign: write state BEFORE the irreversible action.
// 'sending' rows are excluded from selection; only pre-send failures (nothing typed,
// nothing clicked) release the claim. A crash after the click strands the row in
// 'sending' for a human — that stranding IS the feature. See README "Reviewing stuck rows".
const PRE_SEND_FAILURES = new Set([
  'no_connect_button', 'no_message_button', 'no_compose_box', 'send_missing',
  'send_disabled', 'send_button_missing',
]);
const attempt = db.prepare(
  'INSERT INTO attempts(profile_url,action,status,detail,created_at) VALUES (?,?,?,?,?)'
);
function claim(profileUrl, action, statusCol) {
  db.prepare(`UPDATE leads SET ${statusCol}='sending', updated_at=? WHERE profile_url=?`).run(now(), profileUrl);
  attempt.run(profileUrl, action, 'claimed', null, now());
}
function resolve(profileUrl, action, statusCol, atCol, res) {
  if (res === 'sent') {
    db.prepare(`UPDATE leads SET ${statusCol}='sent', ${atCol}=?, last_error=NULL, updated_at=? WHERE profile_url=?`)
      .run(now(), now(), profileUrl);
    attempt.run(profileUrl, action, 'confirmed', null, now());
  } else if (PRE_SEND_FAILURES.has(res)) {
    db.prepare(`UPDATE leads SET ${statusCol}='pending', last_error=?, updated_at=? WHERE profile_url=?`)
      .run(res, now(), profileUrl);
    attempt.run(profileUrl, action, 'failed_before_send', res, now());
  }
  // anything else: leave the row in 'sending' — do not re-arm
}

// ---------- main ----------
(async () => {
  const LOCK = path.join(__dirname, '.run.lock');
  if (fs.existsSync(LOCK) && Date.now() - fs.statSync(LOCK).mtimeMs < 30 * 60 * 1000) {
    console.log(JSON.stringify({ skip: 'locked' }));
    process.exit(0);
  }
  fs.writeFileSync(LOCK, String(process.pid));
  process.on('exit', () => { try { fs.unlinkSync(LOCK); } catch (e) {} });

  db.exec(`CREATE TABLE IF NOT EXISTS attempts(
    id INTEGER PRIMARY KEY, profile_url TEXT NOT NULL, action TEXT NOT NULL,
    status TEXT NOT NULL, detail TEXT, created_at TEXT NOT NULL)`);

  const CR_CAP = todaysCap(CFG.daily_cr_cap || 30);
  const MSG_CAP = todaysCap(CFG.daily_msg_cap || 30);

  const ctx = await chromium.launchPersistentContext(PROFILE, {
    headless: false, channel: 'chrome', viewport: null,
    args: ['--disable-blink-features=AutomationControlled'],
  });
  const page = ctx.pages()[0] || (await ctx.newPage());
  await page.goto('https://www.linkedin.com/feed/', { waitUntil: 'domcontentloaded' }).catch(() => {});
  await sleep(3500);
  await checkpointGuard(page, 'boot');
  const url = page.url();
  const cookies = await ctx.cookies('https://www.linkedin.com').catch(() => []);
  const hasLiAt = cookies.some((c) => c.name === 'li_at');
  const onAuthwall = /\/login|\/authwall|\/uas\/login|\/checkpoint/i.test(url);
  if (!hasLiAt || onAuthwall) {
    console.log(JSON.stringify({ error: 'NOT_LOGGED_IN', hasLiAt, url })); await ctx.close(); process.exit(3);
  }

  const log = [];
  const todayCount = (col) => db.prepare(`SELECT COUNT(*) c FROM leads WHERE date(${col})=date('now','localtime')`).get().c;

  // GUARD: only CR degree='non' leads that were never accepted and aren't mid-send
  async function doConnect(limit) {
    if (limit <= 0) return;
    const rows = db.prepare(`SELECT * FROM leads WHERE degree='non' AND cr_status='pending' AND accepted_at IS NULL ORDER BY RANDOM() LIMIT ?`).all(limit);
    for (const r of rows) {
      await gotoProfile(page, r.profile_url);
      const state = await connectionState(page);
      if (state === 'connected') { db.prepare(`UPDATE leads SET cr_status='accepted',accepted_at=?,updated_at=? WHERE profile_url=?`).run(now(), now(), r.profile_url); log.push([r.first_name, 'already_connected']); continue; }
      if (state === 'pending') { db.prepare(`UPDATE leads SET cr_status='sent',cr_sent_at=?,updated_at=? WHERE profile_url=?`).run(now(), now(), r.profile_url); log.push([r.first_name, 'already_pending']); continue; }
      if (state === 'unknown') { log.push([r.first_name, 'state_unknown_skip']); continue; }
      if (DRY) { log.push([r.first_name, 'DRY connect']); continue; }
      claim(r.profile_url, 'cr', 'cr_status');
      const res = await sendConnect(page, r.first_name);
      await page.screenshot({ path: path.join(SHOTS, `cr_${r.first_name}_${res}_${Date.now()}.png`) }).catch(() => {});
      resolve(r.profile_url, 'cr', 'cr_status', 'cr_sent_at', res);
      log.push([r.first_name, res]);
      await jitter();
    }
  }

  async function doMessages(limit) {
    if (limit <= 0) return;
    const due = db.prepare(`SELECT * FROM leads WHERE cr_status='accepted' AND msg1_status='pending' ORDER BY (degree='first') DESC, RANDOM() LIMIT ?`).all(limit);
    for (const r of due) {
      await gotoProfile(page, r.profile_url);
      // Trust DB: if accepted_at exists (reconcile confirmed), skip the unreliable DOM check
      let proceed = r.accepted_at != null;
      if (!proceed) {
        const state = await connectionState(page);
        if (state === 'connected') {
          proceed = true;
        } else {
          // NEVER mutate degree — log the mismatch and move on
          db.prepare(`UPDATE leads SET last_error=?,updated_at=? WHERE profile_url=?`).run('accepted_but_dom_disagrees', now(), r.profile_url);
          log.push([r.first_name, 'review_connection_state']);
        }
      }
      if (!proceed) continue;
      // Pick copy by CR history: through the CR flow -> "thanks". Otherwise peer intro.
      const wentThroughCR = r.cr_sent_at != null;
      const text = fill(wentThroughCR ? CFG.copy.msg1_accepted : CFG.copy.msg1_first, r.first_name);
      if (DRY) { log.push([r.first_name, 'DRY msg1', text.slice(0, 40)]); continue; }
      claim(r.profile_url, 'msg1', 'msg1_status');
      const res = await sendMessage(page, text);
      await page.screenshot({ path: path.join(SHOTS, `msg1_${r.first_name}_${res}_${Date.now()}.png`) }).catch(() => {});
      resolve(r.profile_url, 'msg1', 'msg1_status', 'msg1_at', res);
      log.push([r.first_name, 'msg1:' + res]);
      await jitter();
    }
  }

  async function doCheckAccepts(limit) {
    if (limit <= 0) return;
    const sent = db.prepare(`SELECT * FROM leads WHERE cr_status='sent' AND msg1_status='pending' ORDER BY cr_sent_at ASC LIMIT ?`).all(limit);
    for (const r of sent) {
      await gotoProfile(page, r.profile_url);
      const state = await connectionState(page);
      if (state === 'connected') {
        db.prepare(`UPDATE leads SET cr_status='accepted',accepted_at=?,updated_at=? WHERE profile_url=?`).run(now(), now(), r.profile_url);
        log.push([r.first_name, 'ACCEPTED']);
      }
      await sleep(rnd(4000, 9000));
    }
  }

  try {
    if (MODE === 'auto') {
      const bh = CFG.business_hours || { days: [1, 2, 3, 4, 5], start_hour: 8, end_hour: 20 };
      const d = new Date();
      if (!bh.days.includes(d.getDay()) || d.getHours() < bh.start_hour || d.getHours() >= bh.end_hour) {
        console.log(JSON.stringify({ skip: 'outside_business_hours', hour: d.getHours(), day: d.getDay() }));
        await ctx.close(); process.exit(0);
      }
      // Randomly sit out some wake-ups so the timer stops being a metronome.
      if (Math.random() < (CFG.wakeup_skip_probability ?? 0.2)) {
        console.log(JSON.stringify({ skip: 'cadence_noise' }));
        await ctx.close(); process.exit(0);
      }
      const msgLeft = Math.max(0, MSG_CAP - todayCount('msg1_at'));
      const crLeft = Math.max(0, CR_CAP - todayCount('cr_sent_at'));
      await doCheckAccepts(6);
      await doMessages(Math.min(msgLeft, 4));
      await doConnect(Math.min(crLeft, 3));
      log.push(['caps', `msgLeft=${msgLeft} crLeft=${crLeft} (today's caps: cr=${CR_CAP} msg=${MSG_CAP})`]);
    } else if (MODE === 'connect') {
      const limit = PILOT != null ? PILOT : Math.min(LIMIT, Math.max(0, CR_CAP - todayCount('cr_sent_at')));
      await doConnect(limit);
    } else {
      const limit = PILOT != null ? PILOT : Math.min(LIMIT, Math.max(0, MSG_CAP - todayCount('msg1_at')));
      await doMessages(limit);
    }
  } catch (e) {
    console.log(JSON.stringify({ HARD_STOP: String(e.message || e), done: log }));
    await ctx.close();
    process.exit(9);
  }
  console.log(JSON.stringify({ mode: MODE, actioned: log.length, log }));
  await ctx.close();
  process.exit(0);
})();
