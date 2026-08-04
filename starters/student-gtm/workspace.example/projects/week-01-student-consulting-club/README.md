# Roster sync, student consulting club

A student consulting club recruits through a Google Form. Every Sunday the VP of membership opened
two sheets and retyped each new signup into the roster by hand: name in title case, email lowercased,
committee assigned, semester joined. About 40 minutes a week, more during recruitment weeks, and
people who signed up in a previous semester were getting entered twice with nobody able to catch it.

**Input:** the form-responses tab of the club's signup sheet (Sheets API, read)
**Output:** new members appended to the roster tab, normalized and deduped on email, with a dated
backup tab taken before every write
**Result:** 41 new members synced, 23 repeat signups caught, 40 minutes a week gone. Running every
Sunday since 2026-02-15. See [`gotchas.md`](gotchas.md) for what broke.

Run it:

```bash
export GTM_GOOGLE_TOKEN=~/.config/student-gtm/token.json
python3 sync.py --sheet-id $CLUB_ROSTER_SHEET_ID --dry-run
```

`--dry-run` is the default. Writing requires `--write`, typed on purpose. There is a
`sample_responses.csv` in this folder with six rows I made up, so the repo runs without touching
anybody's data.

---

**Week of 2026-02-09 to 2026-02-15**
**Client:** the student consulting club I belong to. Full notes in `clients/student-consulting-club.md`.
**User:** the VP of membership
**Status:** delivered 2026-02-13. Acceptance criterion met 2026-02-22.

Everything above the line was written Tuesday, before any code, except the Result line. The Result
section at the bottom was added ten days later. That order is the point: a project with the finish
line written down on Tuesday is a project that ends on Thursday.

## The goal, in one sentence

> New member signups from the club's Google Form land in the roster sheet, deduped, without anyone
> retyping them.

## The problem underneath the problem

Two things go wrong with the manual version, and the second one is why this is worth a week rather
than an afternoon:

1. People who signed up last semester sign up again and get entered twice. Nobody catches it,
   because catching it means reading 300 rows.
2. When the VP of membership graduates in May, the process leaves with them. There is no written
   version of it anywhere.

Point 2 is the one the club cares about and did not say out loud. I got it by watching them do it
once and asking what happens next year.

## The person

Junior, VP of membership, does this on Sunday nights around coursework. Works in Google Sheets and
Gmail and nothing else. Will never run a Python script, and should not have to. So the output has to
be a sheet that changes on its own, and my involvement has to be invisible after Friday.

## What I built

`sync.py`, one file:

1. Read the form-responses tab.
2. Normalize each row: strip whitespace, lowercase the email, title-case the name, parse the
   timestamp.
3. Build a dedupe key from the normalized email, compare against every email already on the roster.
4. Snapshot the roster tab to a dated backup tab.
5. Append only the rows that are new. Touch nothing that already exists.
6. Print one summary line: rows read, rows appended, rows skipped as duplicates.

Scheduled with cron on my laptop, Sundays at 8pm. That is a known weakness, it is the first entry in
`me/gaps.md`, and I told the club about it before they said yes.

## Out of scope

- **Editing or deleting existing roster rows.** Append is the one operation that cannot destroy six
  years of somebody else's work.
- The alumni sheet. Different problem, different week.
- Anything with a user interface.
- Running anywhere except my laptop. Deployment is a gap, and week 1 is the wrong week to close it.

## Acceptance criterion

One criterion, and "the script runs clean" is not it.

> The VP of membership goes two Sundays in a row without opening the form-responses tab, and the
> roster is still correct on Monday.

The criterion describes their behavior rather than my code. A clean run on my machine is a
checkpoint. The week passes when the manual step stops happening and nobody has to think about it.

How I check it: the roster tab has a "source" column. Rows the script adds say `sync`. Rows a human
types say nothing. If two Sundays pass with no blank-source rows and no complaints, it passed.

## Data rules

- The roster is real people. It stays out of the repo. `.gitignore` excludes `data/` and `*.csv`.
- The repo ships `sample_responses.csv`: six rows I typed myself, fake names, `example.edu`
  addresses. Anyone can clone this and run it against that. It is the one file that gets past the
  `*.csv` rule, and it took `git add -f sample_responses.csv` to put it there. I read
  `git status --short` afterward, because an exception I made once is an exception I will forget I
  made.
- Credentials come from the environment. `GTM_GOOGLE_TOKEN` points at a token file that lives
  outside this repo, and `os.environ` is the only way anything reads it. No key, no token, no client
  secret in any file here. That rule has a Saturday morning behind it, in `gotchas.md`.

## The recording

The screen recording ran for the whole Wednesday build session, 3 hours and 40 minutes, screen and
mic, starting from an empty folder. It is not a separate 40-minute task on top of the build, it is
the build with the record button on. Audio tested for ten seconds first.

On Friday I published the best 34 minutes of it and cut three vertical clips out of that same file.
Unlisted, because it is week 1.

Timestamps written on paper during the build, for the clipper:

- **0:38:12** the first 403, and me reading it wrong out loud
- **1:52:40** the dedupe comparison that looked right and was not
- **3:11:05** the first dry run that printed what I expected

The long cut and the clips went through `starters/podcast-shorts/` (Chapter 20). The transcript is
saved next to this file as `transcript.txt`. It feeds Friday's post and `voice/core-voice.md`.

## What the week actually looked like

The cadence says ship Thursday. Week 1 shipped Thursday and then shipped again Friday, because
Thursday's live run put 23 duplicate rows into the club's roster and I spent that night taking them
back out by hand. Both entries are in `gotchas.md`, written the same day, before I knew how it
ended.

I also started building on Tuesday instead of Wednesday, which is how the scopes failure ended up
dated 2026-02-10. Week 1 was the week I learned the cadence rather than the week I followed it.

---

## Result, written 2026-02-22

Delivered Friday 2026-02-13.

**The numbers**

- Roster before: 312 rows
- Form responses: 64
- New people appended: 41
- Repeat signups skipped: 23
- Roster after: 353

The 23 repeat signups are the number the club found interesting. The manual process had been adding
some of those people twice for years, and nobody had a way to see it.

**What broke**

Thursday's first live run appended all 64 rows, putting 23 duplicates into the live roster, because
the email comparison was case sensitive and the script had no dry-run mode. Forty minutes of manual
cleanup on a Thursday night, which is exactly the work this was built to end. Full write-up in
`gotchas.md`, 2026-02-12. Two rules came out of it that are now in every script I write: dry run by
default, and snapshot before any write.

The scopes failure at 0:38:12 in the recording is `gotchas.md`, 2026-02-10.

**Against the criterion**

Two Sundays clean: 2026-02-15 and 2026-02-22. No blank-source rows on either Monday, and the VP of
membership did not open the form-responses tab either week. Criterion met.

The 40 minutes a week is gone. The bigger one is that the process is now written down in a repo the
next officer can read, which was the problem underneath the problem.

**What is still broken**

It runs on my laptop. If my lid is closed Sunday at 8pm, nothing happens and nobody finds out until
Monday. The club knows. Fixing it means learning to deploy something, which is the first entry in
`me/gaps.md` and is going to be its own week.
