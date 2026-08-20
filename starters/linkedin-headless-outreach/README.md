# LinkedIn Headless Outreach Starter

The runnable kit behind [Chapter 22](../../chapters/22-headless-linkedin-outreach.md): a self-hosted Playwright sender + SQLite ledger + read-only reconcile observer for LinkedIn outreach from **your own account**.

## Read this first

Automating your LinkedIn account is outside LinkedIn's terms of service and can get the account restricted or banned. This is not a recommendation against HeyReach or any managed tool — those exist so you don't have to carry this risk. I built this to run on my own account, took the risk myself, and stopped when the signals said stop. If you run it, that decision and that risk are yours. **At your own discretion.**

What the original campaign produced (three weeks, 40 CRs/day): 601 connection requests → 299 accepted (49.8%) → 35 replies → 2 calls booked. 31 of the 35 replies came from the connection note alone. Full story, including the double-send incident this starter fixes, in the chapter.

## What's in the box

| File | What it does |
|---|---|
| `config.example.json` | your copy, caps, and member id — copy to `config.json` (gitignored) |
| `build_ledger.py` | prospect CSV → SQLite ledger (`li_outreach.db`), idempotent upsert |
| `login.js` | one-time interactive login into a dedicated Chrome profile |
| `run.js` | the sender: `connect` / `messages` / `auto` modes, with the claim-before-click fix |
| `reconcile.js` | read-only observer: syncs accepts + replies from LinkedIn's own pages, SHA-256 evidence |
| `ledger_status.js` | funnel JSON + rows stuck in `sending` (manual-review queue) |
| `launchd/` | macOS timer templates for sender (30 min) and observer (6 h) |

## Setup

```bash
cd starters/linkedin-headless-outreach
npm install playwright && npx playwright install chrome   # real Chrome, not Chromium
cp config.example.json config.json                        # then edit: copy, caps, member id
python3 build_ledger.py --csv your_prospects.csv          # needs first_name + linkedin_url columns
node login.js                                             # log in by hand, once
node run.js --mode connect --pilot 2 --dry-run            # rehearse
touch .armed                                              # arm the kill switch
node run.js --mode auto                                   # or install the launchd timers
```

`config.json` needs your own LinkedIn member id (`self_member_id`) — open your profile, view source, search `ACoAA`. The observer refuses to run without it so it can never mistake you for a participant.

## The safety rails (all on by default)

- **Kill switch:** no `.armed` file, no actions. `rm .armed` stops everything.
- **Checkpoint hard-stop:** any checkpoint/captcha/verification URL or body text → screenshot, throw, exit. Never retry into a wall.
- **Claim-before-click:** rows are marked `sending` *before* the browser acts and `sent` only after. A crash strands the row in `sending` for review instead of re-arming a duplicate send. Every attempt lands in an `attempts` table. This is the fix for the incident in the chapter.
- **Jitter + human typing:** 30–120s between actions, 20–60ms per keystroke.
- **Cadence noise:** the daily cap wobbles per day (deterministic, date-seeded) and each wake-up randomly sits out ~20% of the time, so your gap histogram and daily totals stop being a metronome. Exactly-40-every-day is a signature; don't recreate it.
- **Business hours:** Mon–Fri only, configurable window.
- **Single instance:** `.run.lock` with a 30-minute staleness window.

## Reviewing stuck rows

```bash
node ledger_status.js            # funnel + anything stuck in 'sending'
sqlite3 li_outreach.db "SELECT profile_url,last_error FROM leads WHERE msg1_status='sending' OR cr_status='sending';"
```

Check the person's page/thread on LinkedIn by hand, then resolve the row to `sent` or back to `pending`. Never bulk-reset `sending` to `pending` without looking — that re-arms the exact double-send this table exists to prevent.

## Run the observer from day one

`accepted_at` is a *discovery* timestamp. If `reconcile.js` isn't running from the first send, your accepts-per-day chart is fiction. The observer never clicks Connect/Send/Reply, matches connections by exact `/in/` slug, confirms inbox threads against the participant's profile URL, and stores a screenshot + SHA-256 per confirmed reply.
