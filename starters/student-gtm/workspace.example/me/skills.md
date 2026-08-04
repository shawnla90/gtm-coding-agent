# Skills: Sam Rivera

What I can do today, rated on evidence rather than on what I have read about. Updated every
Saturday in fifteen minutes, from what actually happened that week.

**Updated 2026-03-21.** Last change: cron moved from 2 to 3 after the week 05 timezone break, which
I found and fixed myself. It stays at 3 until something I scheduled survives a month without me
checking on it.

## The scale

| Rating | What it means |
|---|---|
| **1** | I have read about it. I have never run it. |
| **2** | I have run somebody else's version. I could not rebuild it from an empty file. |
| **3** | I built it with the agent explaining each line, and I can read the result and change it. |
| **4** | I shipped it for somebody who is not me, and I fixed it myself when it broke. |

The rule that makes the ratings worth anything: a rating moves up when a project produces the
evidence, and the evidence goes in the row. No row is allowed to cite a tutorial.

## Python and data

| Skill | Rating | Evidence |
|---|---|---|
| Read a Google Sheet from Python and write rows back | 4 | week-01, week-03, week-05, all live |
| Normalize and dedupe messy contact data (case, whitespace, repeat signups) | 4 | week-01 caught 23 repeats, week-03 collapsed 1,140 rows to 612 |
| Google OAuth end to end: scopes, consent, token refresh | 4 | week-01, after breaking it twice in one morning. `projects/week-01-student-consulting-club/gotchas.md`, 2026-02-10 |
| Write a script that refuses to write until you pass `--write` | 4 | every script since 2026-02-12, which is the day I learned why |
| Read a CSV, reconcile it against a second source, and report what did not match | 4 | week-03, 31 people who had no email address at all |
| SQLite: schema, inserts, and a join I keep re-running | 3 | week-03. I can read the query and change a column. I would not design a second table alone yet. |
| Pull from a public API and page through the results | 2 | week-06. I pulled the first page of local businesses from a public directory API and typed the rest in by hand, because I could not make the second page work. |
| Parse and compare timestamps across timezones | 3 | week-05, after the 8am summary sent at 3am for two days |

## Shipping and tooling

| Skill | Rating | Evidence |
|---|---|---|
| git: branch, commit, push, and read the diff before pushing | 4 | every repo. The habit caught an OAuth token staged for a public commit on 2026-02-14. |
| Write a README a stranger can follow without asking me a question | 4 | week-01, week-03, week-05. Two people cloned week-03 and ran it against the sample file. |
| cron: schedule a job and read its log when it fails silently | 3 | week-01 runs every Sunday. Week 05 taught me cron has its own timezone. It stays at 3 until something I scheduled survives a month unattended. |
| Keep credentials out of a repo and read them with `os.environ` | 4 | every script, plus the token I moved out of the project root on 2026-02-14 |
| Record a full build session and hand the file off for clipping | 4 | weeks 01, 03, 05, 06. Four long videos, twelve clips. |

## Go-to-market

| Skill | Rating | Evidence |
|---|---|---|
| Sit with somebody for twenty minutes and watch them do the manual version | 4 | four organizations. It is where every acceptance criterion I have written came from. |
| Write an acceptance criterion that describes their behavior instead of my code | 4 | week-01: two Sundays without opening the form-responses tab. Met 2026-02-22. |
| Ask an organization for the work and get a yes | 4 | asked five, four said yes, one has not answered |
| Answer a public question in full without pitching | 4 | 34 answers since 2026-02-09, four of which turned into direct messages |
| Read a signal queue and pull the question worth answering out of it | 3 | daily since 2026-02-09. I still over-pick the threads I already know the answer to. |
| Say what I do in one sentence a stranger understands | 3 | the version in `target-roles.md` is on its fourth rewrite and it is the first one that landed |
| Book a meeting for a company that is paying for meetings | 1 | none. This is the gap that matters for the seat I want first. |

## The one-sentence version

I can wire a Google Sheet to a Python script and schedule it. I cannot deploy anything yet.

That sentence is what I say out loud when somebody asks. It is short enough to be checked, and every
word of it traces to a row above.
