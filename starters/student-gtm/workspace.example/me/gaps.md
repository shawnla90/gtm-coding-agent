# Gaps: Sam Rivera

What I cannot do yet, ordered by what blocks me soonest. This is the file that does the work. An
agent that thinks I am fluent hands me code I cannot defend in an interview, so this list stays
honest even when it is embarrassing.

**Updated 2026-03-21.** Last change: SQL moved above front ends, because week 06 went out missing a
scoring query and no week has gone out missing an interface yet.

It stays on the portfolio page on purpose. It is shorter than it was in February.

## 1. Deployment

**What it blocks:** everything I have shipped runs on my laptop, on my cron. If the lid is closed on
Sunday at 8pm, the club's sync does not run and nobody finds out until Monday. Three organizations
depend on a machine that goes in a backpack.

**What closing it looks like:** the week-01 sync runs somewhere that is not my laptop, the club
stops being able to tell the difference, and I can explain in one sentence what is running it.

**When:** week 08. It is a whole week on its own, and I told all three organizations about the
weakness before they said yes.

## 2. Making a script fail loudly

**What it blocks:** the moment anything runs unattended, which is now. My scripts assume the happy
path. Week 01 wrote 23 duplicate rows into a live roster and exited 0 while doing it, and the
summary line said `skipped 0` in a tone of complete confidence.

**What closing it looks like:** every scheduled script exits nonzero on a failure, prints what it
was doing when it stopped, and puts a line somewhere I will actually read on Monday.

**When:** it goes in alongside the deployment week, because a job running on a server that fails
silently is worse than a laptop that fails silently.

## 3. SQL past a single join

**What it blocks:** week 06 shipped on Thursday without it. The sponsor list needs past contacts
scored by recency and by who talked to them, and I can write the join but not the grouping. What
went out instead has a priority column the VP of finance fills in by hand, which is the thing I was
supposed to remove.

**What closing it looks like:** I write the scoring query, I can explain each line without the
agent, and the scored list goes back to the same person.

**When:** Monday, first thing in week 07. It is the only piece of work I currently owe somebody.

## 4. Tests

**What it blocks:** the second edit of any script. I check by running it and reading the output,
which caught nothing in week 01 and everything in week 05, so the sample size on my own judgment is
two and I would not bet on it.

**What closing it looks like:** the dedupe function in week 01 has a test file with the three cases
that actually broke, and it runs before I push.

**When:** week 09. Nothing is blocked on it yet, and that is the only reason it sits here rather
than higher.

## 5. Front ends

**What it blocks:** the day a Google Sheet stops being enough for somebody. It has been enough three
times, and the print shop owner has already asked whether the triage list could be "a page on the
phone".

**What closing it looks like:** one page, one table, deployed, no framework I cannot explain.

**When:** after deployment, because a page that only exists on my laptop is worth nothing to
anybody.

## 6. Scale

**What it blocks:** nothing today. The largest thing I have processed is 1,140 rows, and I do not
know what breaks at a million. I have not claimed otherwise anywhere.

**What closing it looks like:** knowing which line falls over first, because I made it fall over.

**When:** unscheduled. It goes on the list so that I say "1,140 rows" in an interview instead of
"large datasets".

## 7. The sales part of sales

**What it blocks:** the interview for the seat I want first, rather than any build. I have booked
zero meetings for a company that pays for meetings. I have asked five organizations for work and
four said yes, which is a sample size of five and a different motion entirely.

**What closing it looks like:** an outbound rep at a target company lets me sit in for an afternoon,
or the print shop owner introduces me to one of their suppliers and I run the conversation.

**When:** I have asked twice and I will keep asking. This one is not fully in my control, and
writing that down beats pretending it is a scheduling problem.
