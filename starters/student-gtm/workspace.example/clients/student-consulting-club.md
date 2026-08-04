# Student consulting club

**Type:** campus organization, about 310 active members, six years old
**User:** the VP of membership. Junior. Works in Google Sheets and Gmail and nothing else.
**Relationship:** I am a member. That is how I got the twenty minutes.
**Status:** delivered 2026-02-13, running every Sunday since 2026-02-15
**Project:** `projects/week-01-student-consulting-club/`
**Last checked in:** 2026-03-15

## The problem, watched on 2026-02-09

The club recruits through a Google Form. Responses land in a form-responses tab nobody uses. The
roster the officers actually work from is a different sheet with different columns, maintained by
hand.

Every Sunday the VP of membership opened both, read down the new form responses, and retyped each
person into the roster: name in title case, email lowercased, committee assigned, semester joined.
About 40 minutes a week, more during recruitment weeks.

I asked to sit and watch rather than asking to build. Twenty minutes, on a Sunday night, at a table
in the student center. Two things came out of that session that would not have come out of a
conversation about requirements:

- They did it while answering texts. That is how the same person ends up on the roster twice.
- When I asked what happens next year, they said "whoever takes this over will figure it out". That
  is the real problem, and they did not say it first because it does not feel like a problem until
  May.

## The number

| | Before | After |
|---|---|---|
| Time per Sunday | ~40 min | 0 |
| Roster rows | 312 | 353 |
| New members added on the first correct run | typed by hand | 41 |
| Repeat signups caught | 0, because catching them meant reading 300 rows | 23 |
| The process, written down | nowhere | a repo the next officer can read |

The 23 is the number the club found interesting. The manual process had been adding some of those
people twice for years and there was no way to see it from inside the sheet.

Every figure above comes from row counts in their own sheet on 2026-02-13, and the sheet still has
the dated backup tab the script took before it wrote, so any of it can be re-checked in front of
somebody.

## What they said

The VP of membership, 2026-02-22, after the second clean Sunday:

> I forgot it was happening. I opened the roster on Monday and the new people were just there.

The president, 2026-03-15, which is the more useful one for me:

> Can you show the next VP how it works before you graduate?

## What it cost them

Nothing. I asked for one thing in exchange and said it plainly at the start: their name on my
portfolio page and permission to publish the code and the write-up. They said yes in about four
seconds. Free with a stated reason has never been the objection.

## The boundary

Named before they asked, which is what got the yes:

- Nothing touching dues, payroll, or student records. Permanently out of scope.
- The roster stays out of the repo. The script ships and a six-row sample file I typed myself ships
  with it.
- Append only. The script cannot edit or delete a row, which means the worst case is a row too many
  rather than six years of somebody else's work gone.

## What is still broken

It runs on my laptop. If the lid is closed on Sunday at 8pm, the sync does not run and nobody finds
out until Monday. I told them that before they said yes and it is the first entry in `me/gaps.md`.
Week 08 is the week I try to fix it.

## Next

- Walk the incoming VP of membership through it before the officer transition in May. That was the
  president's ask on 2026-03-15 and it is a better outcome than the script.
- The alumni sheet has the same shape of problem and they have mentioned it twice. Different week,
  and only after deployment, because a second thing that dies with my laptop lid is not a favor.
