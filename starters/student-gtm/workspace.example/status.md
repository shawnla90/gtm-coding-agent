# Status

**Saturday 2026-03-21. Week 06 of the loop, spring 2026.**

Today is the Saturday square on the cadence: fifteen minutes updating `me/skills.md` and
`me/gaps.md` from what actually happened. Both are updated as of this morning. The full cadence
table is in `CLAUDE.md`.

## Where week 06 ended

**Project:** `projects/week-06-sponsor-list/`, a scored list of local sponsors for the campus
entrepreneurship club, deduped against every business the club has contacted before.

Shipped Thursday 2026-03-19 without the scoring. The dedupe works: 214 businesses collapsed to 173,
with 41 of them already contacted by an officer in a previous year, which the club could not see
before because the history lived in three officers' personal contacts. What went over was that list
with a priority column the VP of finance fills in by hand.

The score was supposed to be a query and I could not write it. That is `me/gaps.md` item 3 and it is
the first thing on Monday. Shipping the smaller version on Thursday beat holding it for a week, and
the club is using the deduped list right now either way.

First Thursday in six weeks where what went out was smaller than what was promised on Tuesday. I
told them Tuesday's version and Thursday's version out loud, in that order, so there was nothing to
walk back.

## The record

| Week | What shipped | Who uses it | Delivered |
|---|---|---|---|
| 01 | Google Form to roster sync, deduped, append only | Student consulting club | 2026-02-13 |
| 02 | Nothing. Two midterms. | | |
| 03 | Event signup dedupe and mailing-list push | Campus marketing club | 2026-02-27 |
| 04 | Nothing. The project I picked needed access to a payment system, which is out of scope, and I found that out on Wednesday instead of on Tuesday. | | |
| 05 | Custom order triage sheet and an 8am summary | Screen-printing shop | 2026-03-13 |
| 06 | Sponsor list, deduped against past contacts, no scoring yet | Campus entrepreneurship club | 2026-03-19 |

Four shipped out of six. The two blank weeks stay in the table. Week 04 is the more useful one to
read, because the lesson was to ask what systems the work touches on Tuesday rather than finding out
on Wednesday.

**Running on a schedule right now:** three, all on my laptop.
**Gotchas entries:** 31 across the project logs since 2026-02-09.
**Public answers in the signal rooms:** 34, four of which turned into a direct message.
**Recordings:** four full build sessions, four long cuts published, twelve clips. The recording runs
for the whole build, then Friday publishes either the full session or the best 30 to 40 minutes of
it.

## Next

**Week 07, 2026-03-23 to 2026-03-29.** Write the scoring query for the entrepreneurship club and
deliver the scored version back to the same VP of finance. Same client, second delivery, and the
first time I will have gone back to somebody with the piece I owed them.

**Week 08.** Deployment. The club sync moves off my laptop. It is item 1 in `me/gaps.md`, three
organizations depend on a machine that goes in a backpack, and every week I put it off is a week I
am one closed lid away from finding out on a Monday.

## The client queue

Who I can serve next. An organization qualifies when a named person does it by hand on a schedule,
the output lives in a spreadsheet or an inbox, I can get twenty minutes to watch them do it, and the
work finishes in one sitting.

| Organization | The person | What they do by hand | Status |
|---|---|---|---|
| Student consulting club | VP of membership | Retyped form signups into the roster, ~40 min a week | Delivered week 01. Notes in `clients/student-consulting-club.md`. |
| Campus marketing club | Events chair | Hand-cleaned the event CSV before every event, ~90 min each | Delivered week 03 |
| Screen-printing shop, two blocks from campus | Owner | Custom order requests sat in an inbox between customers | Delivered week 05 |
| Campus entrepreneurship club | VP of finance | Sponsor outreach ran off three officers' personal contacts | Delivered week 06, scoring owed |
| Intramural sports office | Student coordinator | Team rosters across 11 spreadsheets, one per league | Asked 2026-03-16, no answer. Asking once more on 2026-03-30, then dropping it. |
| Bike shop near campus | Owner | Service appointments in a paper book | Not asked. Walking distance, and I have not been in yet. |

Five asked, four yes, one unanswered. That is a sample size of five and I say it that way out loud.

## What is still broken, across everything

- Three deliveries run on cron on my laptop. Closed lid on a Sunday means the club's sync does not
  run and nobody finds out until Monday.
- Nothing I have written exits nonzero when it fails, so a silent failure stays silent.
- Week 06 owes a scoring query.
- Zero meetings booked for a company that pays for meetings. That is the seat I want first and the
  one thing here I cannot practice on campus.
