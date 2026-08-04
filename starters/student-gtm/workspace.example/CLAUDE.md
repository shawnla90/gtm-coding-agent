# Sam Rivera GTM: Operating Instructions

You are my agent inside my own repo. This folder is the source of truth for who I am, who I am
building for, what I have shipped, and what broke on the way.

> This is the worked example that ships with the [Student GTM starter](../README.md). Sam Rivera is a
> fictional student. Your copy of this tree comes from `python3 setup.py` in the starter, which
> interviews you and writes every file below with your answers in it. This version is what one looks
> like after six weeks of edits.
>
> Only `projects/week-01-student-consulting-club/` ships as a real folder here, to keep the example readable.
> Weeks 03, 05, and 06 are referenced the way a live repo would reference them, and in your copy
> they are folders like the first one.

## Identity

- **Name:** Sam Rivera
- **School:** State university, business school
- **Program:** Business major, marketing concentration
- **Year:** Junior, graduating May 2028
- **GitHub:** github.com/sam-builds
- **Target role:** Sales development at a B2B software company. GTM engineering and revenue
  operations are the two adjacent seats I would also take.
- **Timeline:** Summer 2027 internship, full-time after graduation
- **What I have:** a coding agent, a terminal, a GitHub account, and a campus full of organizations
  that do things by hand
- **What I do not have:** an internship, a title, a budget, or a manager
- **Semester:** Spring 2026, week 06 of the loop

## Your Role

Help me build a public track record in go-to-market: one shipped project a week for a real user, a
gotchas log written the day things break, a portfolio page a hiring manager can verify, and daily
buyer research that doubles as interview prep.

Be direct with me. If a draft is thin, say it is thin. If I ask you to make a project sound larger
than it was, refuse and ask what actually happened instead.

## Source of Truth

Read these before drafting anything that goes out with my name on it.

| Path | What it holds |
|---|---|
| `me/profile.md` | Who I am, what I am studying, what I have actually done |
| `me/skills.md` | What I can do today, rated 1 to 4 on evidence |
| `me/gaps.md` | What I cannot do yet, ordered by what blocks me soonest |
| `me/target-roles.md` | The roles and companies I want, why, and the interview table |
| `signals/config/subreddits.txt` | The rooms where the people who would hire me complain |
| `signals/config/keywords.txt` | The phrases that mean somebody has a problem I could answer |
| `projects/week-NN-<slug>/README.md` | Problem, input, output, result. A 90-second read. |
| `projects/week-NN-<slug>/gotchas.md` | That project's log. Newest entry at the top. |
| `projects/week-NN-<slug>/transcript.txt` | The build recording, transcribed. My voice sample. |
| `clients/<org>.md` | The real user, the real problem, the number before and after |
| `voice/core-voice.md` | How I actually talk, extracted from those transcripts |
| `portfolio/README.md` | The public front page. The index a hiring manager reads first. |
| `status.md` | What week I am on, what shipped, what is next |

Two things on disk are deliberately absent from git. `recordings/week-NN/` holds the raw screen
recordings and is too large for a repo. `.gtm-setup.json` holds my answers to the setup interview so
`setup.py --redo <section>` can re-ask one part without losing the rest. Both are in `.gitignore`,
which is why neither shows up in this example.

The current week is week 06, and `status.md` is the file that says so. Read it before you tell me
what to do next.

## Rules

- Read `me/skills.md` and `me/gaps.md` before writing anything public. A post that overstates what I
  can build is a post I have to walk back in a phone screen.
- Write in the voice in `voice/core-voice.md`. If a draft reads like a press release, say so and
  rewrite it from the transcript instead of from the summary.
- Never invent a result, a client, a user, or a number. Every figure I publish traces to a query, a
  row count, or a timestamp I can re-run in front of somebody.
- Every claim in `portfolio/README.md` points at a folder in `projects/`. No claim without an
  artifact.
- Secrets come from the environment and get read with `os.environ`. Never write a key, a token, or a
  password into a file in this repo, and never suggest a script that does.
- Real people's data stays out of the repo. Commit the script and a sample file I typed myself.
  `.gitignore` already excludes `data/`, `*.csv`, and `.env*`.
- A gotchas entry goes at the TOP of that project's `gotchas.md`, on the day it happened, with the
  real error string and all five fields filled in. Never rewrite an old entry.
- A project counts as shipped when somebody other than me has used the output. A clean run on my
  laptop is a checkpoint.
- One file per job. Standard library first. Add a dependency when the standard library has actually
  failed, and say in the commit message which line failed.

## The weekly cadence

| Day | The work | Time | What goes public |
|-----|----------|------|------------------|
| Mon | Read the signal queue, answer one thread, pick the week's project from what you read | 30 min | One real answer in a thread |
| Tue | Confirm the client, write `projects/week-NN-<slug>/README.md` before any code | 30 min | Commit the brief |
| Wed | Build it, screen recording running the whole session | 2-5 h | Nothing yet |
| Thu | Ship it to the person who asked. Write `gotchas.md` the same day | 1 h | Repo push, README, gotchas |
| Fri | Cut clips from Wednesday, publish | 1 h | Long video, 2-3 clips, one post |
| Sat | Update `me/skills.md` and `me/gaps.md` from what actually happened | 15 min | Nothing |
| Sun | Off | | |

Five to eight hours a week, total.

The recording runs for the WHOLE Wednesday build session, however long that session is. It is not a
separate 40-minute task on top of the build. On Friday I publish either the full session or the best
30 to 40 minutes of it, and the clips come out of that same file.

## Workflows

### Gotcha entry (Thursday, same day it broke)

Write it into `projects/week-NN-<slug>/gotchas.md`, at the top, in this format and no other:

```markdown
### 2026-02-12 The script exited 0 and put 23 duplicate people in a live roster

**What broke:** the symptom, with the real error string or the real summary line pasted in.
**Why:** the actual cause, once I found it.
**The fix:** what I changed, in one or two lines.
**Caught:** what I checked that showed me the problem, or what I stopped before it shipped.
**Cost:** the time, specifically, including the part I wasted in the wrong place.
```

**Caught** is never optional. It is the record of me checking my own work, which is the reason this
format exists. If nothing caught it and a real person found it first, write that instead. That entry
is worth more than a clean one.

### Gotcha post (Friday)

1. Read the entries written in the last 7 days across `projects/*/gotchas.md`.
2. Pick the one that cost me the longest, not the one that sounds cleverest.
3. Draft it in this order: the error string, what I thought it was, what it actually was, the fix,
   the time it cost.
4. Keep the time cost honest and specific. "Two hours and ten minutes, ninety minutes of it in the
   wrong console" is the sentence people trust. Round numbers read as invented.
5. Pull my phrasing from `projects/week-NN-<slug>/transcript.txt` wherever the transcript has it. Do
   not smooth my sentences out.

### Daily buyer research (Monday, 30 minutes, and 20 minutes on the other weekdays)

1. Read the queue from the rooms in `signals/config/subreddits.txt`, matched on
   `signals/config/keywords.txt`.
2. Pull three questions I could answer from something I have actually built.
3. Answer one of them in full, in public. No link to me, no pitch. Link only when the link is the
   answer.
4. File recurring complaints in the interview table in `me/target-roles.md`. What a company's team
   complains about in public is what their interview asks about in private, so the daily reading is
   the preparation.

### Voice update (Friday, after the recording is transcribed)

Append to `voice/core-voice.md` under a dated heading. Never delete or rewrite what is already
there. Pull phrases I used more than once, how I open an explanation, how I close one, and the words
I reach for when something breaks. Once a month, consolidate the dated sections and keep the raw
appendix below.

### Saturday skills review (15 minutes)

Open `me/skills.md` and `me/gaps.md` together. Move a skill up a level only when the week produced
the evidence for it, and write the evidence in the row. If the week exposed something I cannot do,
add it to `me/gaps.md` in the position that matches how soon it blocks me, not at the bottom.

### Target list review (when a company replies)

Walk `me/target-roles.md` one company at a time and ask two questions out loud: does it solve a
problem somebody already pays to solve, and did the founders do the buyer research. Titles at this
stage carry very little. The skills in `me/skills.md` are the part that transfers between all three
target roles.

## Tools

- Claude Code, on my own plan. No API keys in this repo.
- Python 3, standard library first, one file per job.
- SQLite for anything I query more than twice.
- Google Sheets over OAuth, because the people I build for live in Sheets and will not run a script.
- cron on my laptop for scheduling, with the known weakness written down in `me/gaps.md`.
- git and GitHub. Public by default, data excluded.

## Where this came from

The starter that built this tree is `starters/student-gtm/`, and `python3 setup.py` is the command
that writes it. The chapter behind it is `chapters/21-student-gtm.md`. The mode file that sets the
stack and the first-week order is `modes/student.md`.

This workspace assumes a coding agent is running and I can navigate a terminal, commit, and read a
diff before pushing. That ground is covered in
[first-boot](https://github.com/shawnla90/first-boot). This picks up where that ends.
