# Sam Rivera

**I build small go-to-market tools for organizations that have a real problem and no budget. Three
of them are running right now, on a schedule, in other people's hands.**

Every project below has a named user who is not me, a number I can re-run in front of you, and the
written log of what broke while I built it.

Business major, junior, state university. Aiming at sales development at a B2B software company.

[LinkedIn](#) · [github.com/sam-builds](#) · sam.rivera@example.edu

---

## Shipped

### 1. Member signup sync, student consulting club

Delivered 2026-02-13. Running every Sunday since.
[Code and write-up](../projects/week-01-student-consulting-club/) · [Build log](../projects/week-01-student-consulting-club/gotchas.md) · [Build recording](#)

The club recruits through a Google Form. Every Sunday an officer opened two sheets and retyped the
new signups into the roster by hand, about 40 minutes a week. The form now feeds the roster
directly: normalize, dedupe on email, snapshot the tab, append only.

- **41** new members synced on the first correct run
- **23** repeat signups caught, people the manual process had been entering twice for years
- **40 minutes a week** of retyping, gone
- The process now lives in a repo the next officer can read, instead of leaving in May with the one
  who built it

Python, Google Sheets API over OAuth, cron.

**What broke:** the first live run appended 23 duplicate rows into the club's live roster, because
the email comparison was case sensitive and there was no dry-run mode. I cleaned it by hand that
night, then made dry-run the default and added a dated backup tab before any write. Both are now in
every script I write.
[Full write-up](../projects/week-01-student-consulting-club/gotchas.md).

### 2. Event signup dedupe and mailing-list push, campus marketing club

Delivered 2026-02-27.
Code, write-up, and build log live in `projects/week-03-event-dedupe/` in the real repo. Only week 01 ships inside this example.

Event signups came out of the sign-in tool as a CSV that somebody hand-cleaned before every single
event: the same people across different events, name casing all over the place, and three columns
the mailing list needed that the export did not have.

- **1,140** rows across 7 events collapsed to **612** unique people
- **~90 minutes** of cleanup per event, removed from the pre-event checklist
- 4 events have run through it since

Python, SQLite, Google Sheets API, the mailing-list provider's import format.

**What broke:** I matched people on email and lost 31 of them, because a chunk of the signups came
from a paper sheet at the door where nobody wrote an email at all. Second key on normalized name
plus phone. The real lesson was that I built the matcher before I looked at 20 raw rows.

### 3. Custom order triage, screen-printing shop near campus

Delivered 2026-03-13.
Code, write-up, and build log live in `projects/week-05-order-triage/` in the real repo. Only week 01 ships inside this example.

Custom order requests arrive through a form on the shop's site and land in the owner's inbox between
customers. They sat. Requests now land in a triage sheet with hours-waiting as the first column,
sorted oldest first, and the owner gets one summary email at 8am.

- Median time to first reply went from **31 hours to 6 hours** across three weeks
- That number comes from the "replied" column in their own sheet, which the owner ticks. It is their
  measurement rather than mine, and three weeks is a direction rather than a fact.

Python, Google Sheets API, a scheduled morning summary.

**What broke:** the 8am summary sent at 8am UTC for two days, which is 3am where the shop is. I had
never set a timezone on a cron job and did not know I was supposed to.

---

## The gotchas logs

One log per project, in the project folder. 31 entries since 2026-02-09. What broke, why, the fix,
what caught it, and what it cost me in hours. Written the day it happened, including the entries
where I was wrong for two hours in the wrong console.

Start with [week 01](../projects/week-01-student-consulting-club/gotchas.md). It has the run that put 23
duplicate rows into a live roster, the token that had the wrong scopes all morning, and the Saturday
I found an OAuth token staged for a commit to a public repo.

Every entry has a **Caught** field, and that field is the reason the format exists. It is the record
of me checking my own work before it reached a real person. Working code is easy to show. The logs
show how I get from broken to working and how long that actually takes me.

## What I can do

Rated on evidence in [`me/skills.md`](../me/skills.md), where 4 means I shipped it for somebody who
is not me and fixed it myself when it broke.

| | |
|---|---|
| **4** | Read and write Google Sheets from Python. Google OAuth end to end, scopes and token refresh included. Normalize and dedupe messy contact data. Write a script that refuses to write until you pass `--write`. Git, and a README a stranger can follow. Sit with somebody for twenty minutes and watch them do the manual version. |
| **3** | SQLite schemas and a join. cron, including the timezone it has of its own. Timestamps across zones. |
| **2** | Paging through a public API. Booking a meeting for a company that pays for meetings is a **1**, and it is the honest number. |

The way I say it out loud: I can wire a Google Sheet to a Python script and schedule it. I cannot
deploy anything yet.

## What I cannot do yet

This section stays on the page on purpose. Ordered by what blocks me soonest, in full in
[`me/gaps.md`](../me/gaps.md). It is shorter than it was in February.

- **Deploy.** Everything runs on my laptop. If the lid is closed on Sunday, the club's sync does not
  run, and they know that.
- **Make a script fail loudly.** Week 01 exited 0 while writing 23 duplicate rows.
- **SQL past a single join.** It is what week 06 is currently stuck on.
- **Tests.** I check by running it and reading the output.
- **Front ends.** When somebody needs to see output, I hand them a Google Sheet.

## How I work

- One project a week, for somebody who already has the problem and is doing it by hand.
- Twenty minutes watching them do it manually before I write a line.
- One acceptance criterion, written Tuesday, describing their behavior rather than my code.
- Wednesday's build recorded start to finish, breaks included, however long it takes.
- Shipped Thursday whether it is pretty or not.
- The log gets written the same day it breaks, before I know how it ends.

## Now

Week 06 went out on 2026-03-19: a list of local sponsors for the campus entrepreneurship club,
deduped against every business three officers had contacted before, so the list survives the
transition in May. 214 businesses down to 173, 41 of them already contacted in a previous year.

It shipped without the scoring I promised on Tuesday, because I could not write the query. Week 07
is that query, going back to the same person. Current state is in [`status.md`](../status.md), and
the gap is item 3 in [`me/gaps.md`](../me/gaps.md).

---

*Sam Rivera is the fictional worked example that ships with the `student-gtm` starter in the GTM
Coding Agent Starter Kit. The projects and numbers show the shape of a real result rather than a
record of one, and only `projects/week-01-student-consulting-club/` is included in the example, so the week 03
and week 05 links are illustrative. Your version of this page carries your projects and your
numbers, and every one of them should trace to a file you can open in front of somebody.*
