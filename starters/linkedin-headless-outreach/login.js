// One-time interactive login into a DEDICATED persistent Chrome profile.
// Uses the real Google Chrome binary with its own userDataDir (does NOT touch
// your daily Chrome profiles). Session persists in pw-profile/ for the runner.
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const PROFILE = path.join(__dirname, 'pw-profile');
const SHOTS = path.join(__dirname, 'screenshots');

(async () => {
  fs.mkdirSync(SHOTS, { recursive: true });
  const ctx = await chromium.launchPersistentContext(PROFILE, {
    headless: false,
    channel: 'chrome',
    viewport: null,
    args: ['--disable-blink-features=AutomationControlled', '--start-maximized'],
  });
  const page = ctx.pages()[0] || (await ctx.newPage());
  await page.goto('https://www.linkedin.com/feed/', { waitUntil: 'domcontentloaded' }).catch(() => {});
  console.log('>>> Log into LinkedIn in the window that opened. Waiting up to 10 min...');

  let ok = false;
  for (let i = 0; i < 120; i++) {
    const url = page.url();
    const loggedIn = await page
      .evaluate(() => !!document.querySelector('img.global-nav__me-photo, .global-nav__me, button[aria-label*="View" i][aria-label*="profile" i]'))
      .catch(() => false);
    if (loggedIn && !url.includes('/login') && !url.includes('/checkpoint') && !url.includes('/uas/')) {
      ok = true;
      break;
    }
    await page.waitForTimeout(5000);
  }

  await page.screenshot({ path: path.join(SHOTS, 'login_state.png') }).catch(() => {});
  console.log(JSON.stringify({ logged_in: ok }));
  await ctx.close();
  process.exit(ok ? 0 : 2);
})();
