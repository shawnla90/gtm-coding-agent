# Chapter 22: Headless LinkedIn Outreach

**A 280-line Playwright script on your own LinkedIn account sent 601 connection requests at 40 a day and got 299 accepted — a 49.8% accept rate — and 31 of the 35 replies came from the connection note alone, before any follow-up message ever went out. The note was the campaign. This chapter is the build, the full funnel, and the exact failure that made me pull the plug.**

---

First, the framing, because it matters: this is not "don't use HeyReach." I use HeyReach and tools like it, and they exist precisely so you don't have to build what this chapter describes. I wanted to run outreach from my own account, with my own session, my own pacing, and my own ledger — so I built it and took the risk myself. Automating your own LinkedIn account sits outside LinkedIn's terms of service and can get an account restricted or banned. That was my account and my call. If you run this, it's yours. At your own discretion.

---

## The Origin

I had a list of 1,297 GTM engineers from an Apollo export and a product writeup to put in front of them. The plan was HeyReach. Then HeyReach showed no connected sender and wanted a UI reconnect before anything could go out, and I hit the thought that started this whole build: it's my LinkedIn. The session lives in a browser on my desk. Why am I asking a third party for permission to use my own account?

So the campaign became a Playwright script driving a real Chrome window with my real logged-in session, a SQLite ledger as the single source of truth, and a launchd timer waking it every 30 minutes during business hours. No API keys, no per-seat sender fees, no reconnect screens. Also no safety net.

---

## The Stack

Everything is local and everything is already on your machine:

| Piece | Tool | What it does |
|---|---|---|
| Ledger | SQLite via `node:sqlite` (built into Node 22+) | one row per lead, every send and accept stamped |
| Import | `build_ledger.py` | Apollo CSV → normalized profile URLs, idempotent upsert |
| Login | `login.js` | one-time interactive login into a dedicated Chrome profile |
| Sender | `run.js` | connect / message / auto modes, caps, jitter, hard stops |
| Observer | `reconcile.js` | read-only sweep of connections + inbox, evidence with SHA-256 |
| Timer | launchd plist | fires `run.js --mode auto` every 30 minutes |

The load-bearing decision is the dedicated browser profile. `login.js` launches real Chrome (`channel: 'chrome'`, not bundled Chromium) with its own `pw-profile/` user-data directory, you log in by hand once, and the session cookie lives there from then on. Never headless for the sender, never a fresh context — a fresh context is a new device fingerprint and new devices are what trigger verification walls. One profile, logged in once, reused forever.

---

## The Ledger Is the Bot

The script is replaceable; the ledger is the asset. One table, one row per human:

```sql
CREATE TABLE leads(
  profile_url TEXT PRIMARY KEY,          -- normalized: linkedin.com/in/<slug>
  first_name TEXT, company TEXT, title TEXT,
  degree TEXT,                           -- 'first' | 'non' — source record, NEVER mutated
  cr_status TEXT DEFAULT 'pending',      -- pending|sent|accepted
  cr_sent_at TEXT, accepted_at TEXT,
  msg1_status TEXT DEFAULT 'pending', msg1_at TEXT,
  msg2_status TEXT DEFAULT 'pending', msg2_at TEXT,
  reply_status TEXT, replied_at TEXT, last_error TEXT
);
```

Every daily cap is a SQL count, not a variable in memory:

```js
const todayCount = (col) =>
  db.prepare(`SELECT COUNT(*) c FROM leads WHERE date(${col})=date('now','localtime')`).get().c;
```

Kill the process at any point and restart it — the ledger already knows what happened today. That property is what makes a 30-minute timer safe to run unattended. It is also, as you'll see, exactly one write too late.

---

## Pacing That Reads Human (Almost)

The sender's guards, in the order they saved me:

- **Kill switch.** The bot no-ops unless a `.armed` file exists. `touch .armed` to run, `rm .armed` to stop everything from your phone over SSH. The cheapest off button you will ever build.
- **Checkpoint hard-stop.** Before and after every profile load, check the URL for `/checkpoint|captcha|challenge` and the body for "unusual activity" / "verify it's you." Any hit: screenshot, throw, exit. It fired for real exactly once in three weeks and the campaign survived because the bot stopped instead of retrying into the wall.
- **Jitter everywhere.** 30–120s between actions, 2.5–5s after page loads, and messages typed with `box.type(text, { delay: rnd(20, 60) })` — 20 to 60 milliseconds per keystroke, because a 400-character paste arriving in one DOM event is not how humans type.
- **Business hours.** Monday to Friday only. The guard declined to run 556 times; that number is the weekends the account stayed quiet.
- **Caps.** 40 connection requests a day, checked against the ledger, with the auto mode sending at most 3 per wake-up.

Here's what I got wrong: I tuned every gap and never looked at the rhythm. The launchd timer fires every 30 minutes, each wake-up sends 2–3 CRs 30–120 seconds apart, and the result is a metronome. Pull the gaps between my 601 sends and the histogram is bimodal — 239 gaps of 60–130 seconds, 226 gaps of 30 minutes to 2 hours, and almost nothing in between. Bursts of three, half an hour of silence, all day, every business day, with the daily total landing on exactly 40 on 12 of 16 active days. A human is messy. This pattern is a confession, and any classifier LinkedIn runs can read it. Randomize the timer interval and the daily cap, not just the gaps inside a run.

---

## The Copy

Four strings, all lowercase, first name interpolated. The connection note carried the whole campaign:

> `{firstName}, building clearbox for gtm teams. it turns reddit into leads and competitor intel, read by buying intent. would value your read. mind connecting?`

The follow-up for accepted connections (only 12 ever went out — next section explains why):

> `thanks {firstName}. clearbox reads reddit by buying intent and drops the threads worth acting on into your inbox, sorted lead / competitor / engage. ran it on my own account: ~1.5M views, ~2,470 karma in 4.7 months. want the writeup?`

Notes on why this converted at 49.8% on a cold list: it names what I'm building in the first six words, it asks for a read instead of a meeting, and the list was 1,297 GTM engineers — peers who build this stuff themselves, not buyers being pitched. Copy selection keys on CR history (did they come through the connect flow or not), never on the imported `degree` field, because `degree` is a source record from the CSV and the bot never mutates source records.

---

## The Observer: Never Let the Actor Keep Score

The design decision I'd defend in front of anyone: **the thing that acts and the thing that measures are separate programs with separate permissions.** `reconcile.js` runs every 6 hours and never clicks Connect, Send, or Reply — it scrolls the connections page and the inbox, read-only, and reconciles the ledger against LinkedIn's own state.

Its matching rules are deliberately paranoid. Connections match by exact `/in/` slug. Inbox threads first narrow by unique full name, then the thread is opened and confirmed only if it resolves to the expected profile URL; name-only matches are quarantined as review candidates instead of being written as facts. Confirmed replies get a screenshot with a SHA-256 hash stored beside the row, so every reply in the funnel has evidence attached.

The observer is also what made the funnel honest. It discovered 22 accepted connections the sender never knew about and backfilled 131 accepts in its first sweep — which means `accepted_at` in my ledger is a *discovery* timestamp, not an acceptance timestamp. I cannot chart accepts per day and neither can you, unless your observer runs from day one. Run it from day one.

---

## The Numbers

Three weeks, July 23 to August 13. Every figure below is a query against the ledger, not a memory:

| Stage | Count | Rate |
|---|---|---|
| Sourced (Apollo export, GTM engineers) | 1,297 | — |
| Connection requests sent | 601 | 40/day pace |
| Accepted | 299 | **49.8%** |
| Replies | 35 | 11.7% of accepted |
| Follow-up messages sent (msg1) | 12 | — |
| Bump messages sent (msg2) | 0 | — |
| Calls booked | 2 | — |

Read the msg1 row again: **31 of the 35 replies came from people the bot never messaged.** They accepted, read the 27-word connection note, and replied to it. The three-step sequence I built — message one, like a recent post, bump message two hours later — barely ran, and the campaign produced replies, booked calls, and trials anyway. The note was the campaign. Everything after the note was optional.

That's the result I did not expect and the one worth stealing: if your connection note can't generate a reply by itself, a follow-up sequence is amplifying nothing.

---

## The Re-Hit That Killed It

The second run is why this chapter exists.

For the first two weeks the message arm was effectively idle — 2 messages total while the CR arm did its 40 a day. On August 13 I restarted it against the backlog: 287 people sitting accepted-and-unmessaged, some for three weeks. Ten of the twelve messages the bot ever sent went out on August 13–14. During that window I watched it double-message someone.

Then I went to the ledger to confirm what I'd seen, and the ledger said everything was fine: 12 messages, 12 people, one row each. The ledger wasn't lying. The ledger was *incapable of recording the truth*, and understanding why is the durable lesson of this whole build.

The message flow selected on `msg1_status='pending'` and marked the row `sent` only **after** the send click succeeded:

```js
const res = await sendMessage(page, text);   // clicks Send on LinkedIn
db.prepare(`UPDATE leads SET msg1_status=?, msg1_at=? ...`)  // written AFTER
```

Anything that dies between those two lines — a selector timeout, the compose box scrolled out of the viewport, Chrome closing mid-run — leaves a message delivered on LinkedIn and a row still reading `pending`. The next wake-up, 30 minutes later, picks the same row and sends again. The logs show exactly this failure class in that window: the compose-box locator retried 51 times and hard-stopped, and the same profiles were re-visited up to four times by the equivalent retry loop on the connect side. And because `msg1_status` is a single column with no attempt history, a double-send writes the same `sent` over itself. Clean ledger, dirty inbox.

The fix is one inversion: **claim before you click.** Write `msg1_status='sending'` *before* touching the browser, exclude `sending` rows from selection, and confirm to `sent` after. A crash now strands a row in `sending` for a human to review instead of re-arming a duplicate. The starter ships with this fix and an `attempts` table, because the version that ran is the version that taught me.

So: one double message witnessed, a send rhythm any classifier could flag, and one verification wall already on record from week one. Any one of those alone, maybe you keep going. Together they're the account asking you to stop. I renamed both launchd plists to `.disabled`, removed `.armed`, and the campaign ended with the funnel above. Could it have gotten me banned? I don't know. It didn't. I took that risk on my own account so you can read the numbers without taking it.

---

## Anti-Patterns

- **Writing the ledger after the irreversible action.** Claim first, act second, confirm third. This ordering is the entire difference between "idempotent" and "sends twice under failure."
- **Perfect daily totals.** Exactly 40, twelve days running, is a signature. Randomize the cap, not just the gaps.
- **A metronome timer.** Fixed 30-minute wake-ups produce a bimodal gap histogram no human makes.
- **Letting the actor keep score.** The sender grading its own homework missed 22 connections and every reply; the read-only observer found them all.
- **Fresh or headless browser contexts on your real account.** New fingerprint, instant checkpoint. One persistent profile, logged in once, reused forever.
- **Building the sequence before the note earns it.** 31 of 35 replies needed no follow-up. Prove the note, then automate the rest.

---

## Closing Exercise

Don't send anything. Build the measurement half first — it's read-only and it's where all the honesty lives:

1. Export your existing LinkedIn connections list and any prospect CSV you have. Run `build_ledger.py` against it and look at the funnel of outreach you've *already done* — the accepted-but-never-followed-up count will surprise you.
2. Read `run.js` in the starter and find the claim-before-click pattern in `doMessages`. Now find the same class of bug in any automation you already run: what state do you write *after* the irreversible action?
3. Compute your own gap histogram from any sender you use, self-hosted or SaaS. If it's bimodal, so is your risk.

---

## Key Takeaways

- The connection note did all the work: 601 CRs → 299 accepts (49.8%) → 35 replies, 31 of them before any follow-up message existed. Prove the note before building the sequence.
- One SQLite ledger with timestamps is what turns "I think it went fine" into a funnel you can publish. The ledger is the asset; the script is replaceable.
- Claim before you click. State written after an irreversible action is a double-send waiting for a crash, and single-value status columns will hide it from you afterward.
- Separate the actor from the observer. A read-only reconcile pass with URL-confirmed evidence is what makes your numbers real.
- Human-shaped gaps are not enough — the *rhythm* (fixed timer, exact daily totals) is a fingerprint too.
- Tools like HeyReach exist so you don't have to carry this risk. I ran it on my own account, once, deliberately, and stopped when the account told me to. Your account, your call.

---

Runnable version of everything above, with the double-send fix already in: `starters/linkedin-headless-outreach/`.
