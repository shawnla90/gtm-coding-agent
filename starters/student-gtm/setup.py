#!/usr/bin/env python3
"""setup.py - interview a student and scaffold their public GTM workspace.

Pure standard library on purpose. It runs on a fresh machine with nothing installed, because
the first thing you should own is a folder of files, not a dependency tree.

  python3 setup.py                       # interview, scaffold ./my-gtm
  python3 setup.py my-gtm                # same, explicit target
  python3 setup.py --out ~/my-gtm        # same, target as a flag
  python3 setup.py my-gtm --force        # overwrite an existing workspace
  python3 setup.py --non-interactive     # fill every answer with the example student
  python3 setup.py --redo profile        # re-ask one section, leave the other files alone
  python3 setup.py --no-git              # skip the git init and the first commit

Prerequisite: Claude Code is already installed and you have shipped something with it. If you
have never opened a terminal, start at github.com/shawnla90/first-boot, then come back here.
That repo covers terminal, git, Claude Code, context engineering, and shipping. This pack
starts where that one ends.

The interview is eight questions. Each one shows a bracketed default from the example student,
and pressing Enter accepts it.

What it writes into the target directory:

  CLAUDE.md                      operating instructions for your agent, identity from the interview
  me/profile.md                  who you are, what you are studying, what you have done
  me/skills.md                   what you can do today, rated 1 to 4 on evidence
  me/gaps.md                     what you cannot do yet. The important one.
  me/target-roles.md             the roles and companies you want, and why
  signals/config/subreddits.txt  the rooms where your future employer complains
  signals/config/keywords.txt    the phrases that mean somebody has that problem
  projects/week-01-<slug>/       the week 1 brief and its own gotchas log
  clients/<org-slug>.md          the real user, the real problem, the number
  voice/core-voice.md            how you actually talk, pulled from your own transcripts
  portfolio/README.md            the index a hiring manager reads first
  status.md                      what week you are on, what shipped, what is next
  .gitignore                     secrets, recordings, client data, and python noise stay out
  .gtm-setup.json                your interview answers, so --redo can re-ask one section
                                 without losing the rest. Gitignored. Delete it and --redo
                                 asks everything again.

The week 1 slug comes from the first organization on your reachable list, so
"the student consulting club" becomes projects/week-01-student-consulting-club/. Give it
nothing and the slug falls back to first-client.

Raw recordings live in recordings/week-NN/ and are gitignored, because they are too big for a
repo. The transcript is committed, at projects/week-NN-<slug>/transcript.txt.

It then runs `git init` and makes the first commit, unless --no-git is passed or git is missing.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

DEFAULT_TARGET = "my-gtm"
ANSWERS_FILE = ".gtm-setup.json"
SLUG_KEY = "week01_slug"
FALLBACK_SLUG = "first-client"
STARTER_DIR = Path(__file__).resolve().parent

# The example student. Neutral on purpose: swap every one of these in the interview.
QUESTIONS = [
    ("name",
     "Your name, as it should read on the portfolio page",
     "Sam Rivera"),
    ("school",
     "School and year",
     "State University, junior"),
    ("studying",
     "What you are studying",
     "Business, marketing concentration"),
    ("can_do",
     "What you can do today (comma separated)",
     "Claude Code basics, Python scripts I can read and edit, Google Sheets, cold email copy"),
    ("gaps",
     "Where the gaps are (comma separated)",
     "APIs and auth, SQL, deploying anything, reading someone else's codebase"),
    ("target",
     "The kind of company you want to work for",
     "Seed to Series A B2B SaaS, 10 to 60 people, selling to sales and marketing teams"),
    ("network",
     "Campus organizations or local businesses you can reach this week (comma separated)",
     "the student consulting club, the entrepreneurship org, a local coffee roaster, "
     "the print shop on campus"),
    ("github",
     "Your GitHub handle",
     "sam-builds"),
]


# ---------------------------------------------------------------- interview

def ask(prompt: str, default: str) -> str:
    """One question, default shown in brackets, empty input accepts the default."""
    try:
        raw = input(f"\n{prompt}\n  [{default}]\n> ").strip()
    except EOFError:
        print("  (no input available, taking the default)")
        return default
    return raw or default


def interview(keys: list | None = None, previous: dict | None = None) -> dict:
    """Ask the questions in `keys` (all of them by default).

    Any answer already on file becomes that question's default, so pressing Enter through a
    --redo keeps what you said last time instead of reverting you to the example student.
    """
    asked = [q for q in QUESTIONS if keys is None or q[0] in keys]
    previous = previous or {}
    noun = "question" if len(asked) == 1 else "questions"
    print(f"{len(asked)} {noun}. Press Enter to accept the bracketed default.")
    answers = {}
    for key, prompt, default in asked:
        answers[key] = ask(prompt, previous.get(key, default))
    return answers


def defaults() -> dict:
    return {key: default for key, _prompt, default in QUESTIONS}


def bullets(csv: str) -> str:
    """A comma separated answer becomes a markdown list."""
    items = [part.strip() for part in csv.split(",") if part.strip()]
    if not items:
        return "- (fill this in)"
    return "\n".join(f"- {item}" for item in items)


def items(csv: str) -> list:
    return [part.strip() for part in csv.split(",") if part.strip()]


def handle(raw: str) -> str:
    return raw.strip().lstrip("@")


def slugify(raw: str, fallback: str = FALLBACK_SLUG) -> str:
    """A free-text answer becomes a safe directory name. Empty input gets the fallback."""
    text = raw.strip().lower()
    for lead in ("the ", "a ", "an ", "my ", "our "):
        if text.startswith(lead):
            text = text[len(lead):]
            break
    scrubbed = "".join(ch if (ch.isascii() and ch.isalnum()) else "-" for ch in text)
    slug = "-".join(part for part in scrubbed.split("-") if part)[:48].strip("-")
    return slug or fallback


def with_derived(answers: dict) -> dict:
    """Add the week 1 slug if it is not already on file.

    It is derived once and then persisted, so a later --redo cannot rename a directory you have
    already committed work into.
    """
    filled = dict(answers)
    if not filled.get(SLUG_KEY):
        first = items(filled.get("network", ""))
        filled[SLUG_KEY] = slugify(first[0] if first else "")
    return filled


def org_name(a: dict) -> str:
    """The first organization on the reachable list, for the week 1 client file."""
    first = items(a.get("network", ""))
    return first[0] if first else "your first client"


# ---------------------------------------------------------------- the cadence

# One table, used everywhere this pack describes the week.
CADENCE_TABLE = """| Day | The work | Time | What goes public |
|-----|----------|------|------------------|
| Mon | Read the signal queue, answer one thread, pick the week's project from what you read | 30 min | One real answer in a thread |
| Tue | Confirm the client, write `projects/week-NN-<slug>/README.md` before any code | 30 min | Commit the brief |
| Wed | Build it, screen recording running the whole session | 2-5 h | Nothing yet |
| Thu | Ship it to the person who asked. Write `gotchas.md` the same day | 1 h | Repo push, README, gotchas |
| Fri | Cut clips from Wednesday, publish | 1 h | Long video, 2-3 clips, one post |
| Sat | Update `me/skills.md` and `me/gaps.md` from what actually happened | 15 min | Nothing |
| Sun | Off | | |"""

RECORDING_RULE = """The recording runs for the whole build session, however long that is. You
then publish either the full session or the best 30 to 40 minutes of it. The recording is not a
separate 40-minute task on top of the build."""


# ---------------------------------------------------------------- templates

def claude_md(a: dict) -> str:
    gh = handle(a["github"])
    slug = a[SLUG_KEY]
    return f"""# GTM Workspace Operating Instructions

You are the coding agent working inside this workspace. This folder is the knowledge base. Read
it before you answer anything about the person who owns it, their skills, or their market.

## Identity

- Name: {a["name"]}
- School and year: {a["school"]}
- Studying: {a["studying"]}
- GitHub: github.com/{gh}
- Building toward: {a["target"]}

## Can do today

{bullets(a["can_do"])}

The rated version, with evidence links, is `me/skills.md`.

## Gaps

{bullets(a["gaps"])}

Treat `me/gaps.md` as the backlog. Every gap that closes gets a gotchas entry and a commit.

## Reachable this week

{bullets(a["network"])}

## The files

| Path | What it holds |
|---|---|
| `me/profile.md` | Who this person is, what they are studying, what they have done. |
| `me/skills.md` | What they can do today, rated 1 to 4 on evidence. |
| `me/gaps.md` | What they cannot do yet. The backlog. |
| `me/target-roles.md` | The roles and companies they want, and why. |
| `signals/config/subreddits.txt` | The rooms where their future employer complains. |
| `signals/config/keywords.txt` | The phrases that mean somebody has that problem. |
| `projects/week-NN-<slug>/README.md` | Problem, input, output, result. Written before any code. |
| `projects/week-NN-<slug>/gotchas.md` | That project's build log. The highest-trust file here. |
| `projects/week-NN-<slug>/transcript.txt` | The build session, transcribed. Their voice sample. |
| `clients/<org-slug>.md` | The real user, the real problem, the number. |
| `voice/core-voice.md` | How they actually talk, pulled from their own transcripts. |
| `portfolio/README.md` | The index a hiring manager reads first. |
| `status.md` | What week they are on, what shipped, what is next. |

Raw recordings live in `recordings/week-NN/` and stay out of git. The transcript is committed
and lives with its project.

## How to work in here

1. Read `me/profile.md` and `me/target-roles.md` before drafting anything public.
2. Match `voice/core-voice.md`. While that file is thin, ask for a transcript before writing in
   the first person.
3. Every project ships something a person outside this repo can use. A deliverable is something
   another human runs or receives.
4. When something breaks, write the gotcha first, then the fix. The broken part is the content.
5. Credentials never enter the repo. Keys live in environment variables, read at runtime with
   `os.environ`, and a missing key fails loudly with a clear message.

## The weekly cadence

{CADENCE_TABLE}

Total 5 to 8 hours a week.

{RECORDING_RULE}

One recording becomes three artifacts: the long video, the clips, and the transcript. Clipping
is handled by `starters/podcast-shorts` (Chapter 20) in the GTM Coding Agent kit. The transcript
goes to `projects/week-NN-<slug>/transcript.txt` and feeds `voice/core-voice.md`.

## Week 1 is live

- Brief: `projects/week-01-{slug}/README.md`
- Log: `projects/week-01-{slug}/gotchas.md`
- Client: `clients/{slug}.md`

## What good output looks like

- A README a stranger can run without asking a single question.
- A gotcha written in the first person, with the real error text pasted in.
- A post that answers a question someone actually asked, with the receipt attached.

## Rules

- Direct language. No hype words.
- Show the work, including the parts that failed.
- Publish before it is polished. The version that ships teaches more than the version that waits.
"""


def profile_md(a: dict) -> str:
    gh = handle(a["github"])
    return f"""# Profile

Who you are, what you are studying, and what you have done. The agent reads this before it
writes anything in the first person. Keep it current: a stale profile produces generic output.

## Who

{a["name"]}. {a["school"]}. Studying {a["studying"]}.
GitHub: github.com/{gh}

## What I have done

One row a week. This table is the resume, and the rest of the resume is commentary. A row counts
once a person outside this repo has used the thing.

| Week | What shipped | For whom | Result | Link |
|---|---|---|---|---|
| 01 | | | | |

## Who I can reach this week

{bullets(a["network"])}

These are real organizations with real operational problems, and they are your first clients.
One automation delivered to one of them outranks ten projects built for an audience of one.
Each one you actually work with gets a file in `clients/`.

## The rest of me

- What I can do today, rated on evidence: `me/skills.md`
- What I cannot do yet: `me/gaps.md`
- The roles and companies I am building toward: `me/target-roles.md`
"""


def skills_md(a: dict) -> str:
    return f"""# Skills

What you can do today, rated 1 to 4 on evidence. Update it Saturday, from what actually happened
that week, and never from what you read about.

## The scale

| Rating | What it means | The proof |
|---|---|---|
| 1 | I have read about it and followed a tutorial | Nothing to link yet |
| 2 | I did it once with the agent driving | A commit, and I could not repeat it alone |
| 3 | I did it alone on a real task | A commit and a project README |
| 4 | I shipped it to someone else and supported it after they hit a problem | A project README, a gotchas entry, and a quote from the person who used it |

The rating is about evidence, not confidence. If you cannot link the proof column, the rating is
one lower than you want it to be. A 4 you can defend in an interview is worth more than six 3s
you cannot.

## The table

Seeded from the interview at rating 2, because that is the honest starting point for anything
you have not yet linked. Move a row up the moment you can link the proof.

| Skill | Rating | Evidence (link) | Last used |
|---|---|---|---|
{skills_rows(a["can_do"])}

## How a row moves

A row moves up when a week produces the proof, and it never moves up because time passed. When a
row hits 4, copy the one-line version into `portfolio/README.md`, since that is the file a hiring
manager reads first.

## What to add

Add a row the first time you touch something in a real project, at rating 1 or 2. A skill you
have never used in a project does not belong here at all. It belongs in `me/gaps.md`.
"""


def skills_rows(csv: str) -> str:
    rows = [f"| {item} | 2 | | |" for item in items(csv)]
    return "\n".join(rows) if rows else "| | | | |"


def gaps_md(a: dict) -> str:
    return f"""# Gaps

What you cannot do yet. This is the important one.

Anyone can list what they know. A written, current, specific list of what you cannot do yet is
rare, and it does two things at once: it gives the agent a backlog to work against, and it gives
a hiring manager the one signal they cannot get from a resume, which is that you can assess your
own work honestly.

## The backlog

Each gap is a project waiting to happen. Rank them by how often they block a week.

| Gap | Why it blocks me | The project that would close it | Closed |
|---|---|---|---|
{gap_rows(a["gaps"])}

## How a gap closes

A gap closes when you have shipped something that required it and it worked for someone else.
Then, in the same sitting:

1. Tick the Closed column with the date.
2. Add the skill to `me/skills.md` at the rating the evidence supports.
3. Link the commit or the project README in the evidence column there.
4. Write the gotchas entry, in `projects/week-NN-<slug>/gotchas.md`, for whatever broke on the way.

## What belongs here

Things you have hit and could not do. "Auth on a third-party API" belongs here the first week an
auth error stops you for an hour. Write the gap in the words the error used, because that is how
you will search for it later, and it is what makes the entry worth reading.

Do not pad this list with everything you have never tried. Four to eight live gaps is a working
backlog. Thirty is a wish list, and nobody works from a wish list.
"""


def gap_rows(csv: str) -> str:
    rows = [f"| {item} | | | |" for item in items(csv)]
    return "\n".join(rows) if rows else "| | | | |"


def target_roles_md(a: dict) -> str:
    return f"""# Target Roles

The roles and companies you want, and why. Refine this as you learn. Three passes is normal, and
the third one is usually the useful one.

## The kind of company

{a["target"]}

### Signals a company fits

- Ships product changes weekly and says so in public
- Has a named GTM or revenue operations person, or visibly needs one
- Founders answer questions with specifics rather than positioning
- You can explain the problem they solve to a friend in one sentence

### Signals to walk away

- The pitch describes a category and never a customer
- No public evidence that anyone uses the product
- The founders cannot say who the buyer is when asked directly

That last one matters more than the funding number. A team that did the buyer research has a job
for someone who can talk to buyers. A team that skipped it has a job that evaporates in a quarter.

## The roles

- Founder or co-founder at pre-Series A, as the first GTM hire
- Head of Growth, Head of GTM, Revenue Operations
- Sales Development Manager
- Whoever runs the team's data, whatever their title says

Titles move fast in this market. A GTM engineer at one company is a growth ops analyst at the
next. Evaluate the work, then the label.

## The twenty companies

Fill this in yourself. Twenty is the number, because ten is a shortlist you will exhaust in a
month and fifty is a list you will never read. Add a row every time one of the rooms in
`signals/config/subreddits.txt` surfaces a company that fits.

| Company | Why it fits | Who I would work for | Signal I saw | Where |
|---|---|---|---|---|
| | | | | |

## Your own offer

You are the product here. Write the offer before you point a signal tool at a market, because
the tool asks you what you sell and to whom, and you will not get a clean answer out of it until
you can give a clean answer to that.

The worked examples to study first are in Chapter 21 (`chapters/21-student-gtm.md`) and in
`modes/student.md`. Read those, then fill this in.

**Name:**

**One-liner:** (what you do, for whom, in one sentence a stranger understands)

**Selling points:** (three, each one provable)
1.
2.
3.

**Competitors:** (who else they would hire instead, and what they get from you that they do not
get there)

Two rules. Say it out loud first and then type what you said, because the spoken version is
always clearer. And use no adjective you cannot prove: "detail-oriented" means nothing, while
"I hand it back inside a week, working, with a README" means something.

Ask the agent to interview you for this and to push back on anything you have not actually done.

## Questions they ask out loud

Log the real ones here, in their words, with a link. This becomes the content calendar.

| Date | Question (their words) | Where | Answered? |
|---|---|---|---|
| | | | |

Answering beats pitching. One answer with a working artifact attached does the job of a hundred
cold emails you were never getting a reply to.
"""


def status_md(a: dict) -> str:
    slug = a[SLUG_KEY]
    return f"""# Status

What week you are on, what shipped, and what is next. Update it Saturday, in five minutes,
before you close the laptop. It is the first file to read when you come back after a bad week.

## Right now

- **Week:** 01
- **Project:** `projects/week-01-{slug}/`
- **Client:** `clients/{slug}.md`
- **Shipped so far:** nothing yet. Week 1 closes when a person outside this repo has used the
  output at least once and their reaction is quoted, with a date, in the project README.

## The log

One row a week, written Saturday. The Result column is a number or a direct quote, and an empty
Result column means the week is still open.

| Week | Project | Client | Result | Published |
|---|---|---|---|---|
| 01 | week-01-{slug} | {org_name(a)} | | |

## Next

- [ ] Confirm the week 1 client and write `projects/week-01-{slug}/README.md` before any code
- [ ] Read the rooms in `signals/config/subreddits.txt` and answer one thread
- [ ] Build it with the screen recording running, then ship it the same week
- [ ] Write the gotchas entry the day it ships
- [ ] Update `me/skills.md` and `me/gaps.md` from what actually happened

## Blocked

Anything that stopped a week, and who can unblock it. An empty list here for three weeks in a
row usually means the projects are scoped too small.
"""


def core_voice_md(a: dict) -> str:
    return """# Core Voice

How you actually talk. The agent reads this before writing anything in your name.

It is thin right now, and it should be. Voice does not come out of a personality quiz. It comes
out of transcripts of you explaining something out loud to someone who did not already know it.

## How to fill it

1. Record the build session. The recording runs for the whole session, however long that is.
2. Transcribe it, and commit the transcript to `projects/week-NN-<slug>/transcript.txt`.
3. Pull ten to fifteen lines where you explained something. Those lines are the voice. The rest
   is filler.
4. Paste them below, verbatim. Keep the false starts. They are the tell that a human said it.

Do this for four weeks and you have a voice profile a model can match. One recording feeds the
long video, the clips, and this file.

## Verbatim lines

<!-- paste your own lines here, one per bullet, exactly as you said them -->

## Patterns to keep

Fill this in once you have thirty lines. Look for:

- Sentence length when you are explaining, versus when you are excited
- The words you reach for over and over
- How you open when you are correcting a wrong assumption
- What you say where a writer would put a transition word

## Words to strike

Words that turn up in agent drafts and never in your mouth. Add one every time you catch one.
The three categories that produce them:

- The verbs a landing page reaches for when it will not say what the product does
- The adjective that would describe every company in the category equally well
- Any word you would not say to a friend across a table

## Ground rules

- First person, past tense, about things that actually happened.
- Attach the receipt. A claim without a link is an opinion.
- If a draft could have been written about anyone, it is not in your voice yet.
"""


def week01_readme_md(a: dict) -> str:
    slug = a[SLUG_KEY]
    org = org_name(a)
    return f"""# Week 01: ship one automation for someone you already know

Write this file before you open an editor. Tuesday is for the brief, Wednesday is for the build.
A brief written after the fact is a report, and a report does not stop you building the wrong
thing.

## The assignment

Pick one organization from the reachable list in `me/profile.md`. This workspace was scaffolded
with **{org}** as the week 1 client. Ask them one question:

> What do you do every week by hand that takes more than an hour?

Build the thing that removes that hour. Deliver it. Fill in this file.

## Why this one first

A personal project proves you can code. A delivered automation proves you can find a problem,
talk to the person who has it, and hand back something they use on Monday. The second one is the
job you are applying for, and you already have the access: campus organizations and local
businesses are real clients with real operational problems, and they will tell you what hurts if
you ask.

## Scope guardrails

- One hour of their time back, and not a platform.
- Ships this week, or it was scoped too big.
- They can run it without you in the room, or you run it for them on a schedule. Either counts.
- No credentials in the repo. Environment variables only, read with `os.environ`.

---

## Problem

Whose problem, in their words, with the date you asked. Paste the sentence they actually said.

## Input

What goes in. The sheet, the export, the inbox, the form. Where it comes from, who owns it, and
what it looks like when it arrives dirty.

## Output

What comes out, and who receives it. Be specific enough that a stranger could check whether it
worked.

## Result

The number, and the quote with a date. This section is empty until a person outside this repo
has used the output at least once. That is the whole bar for week 1, and a script that only ever
ran on your laptop is week 1 unfinished.

- **Time given back per week:**
- **Their reaction (quote plus date):**

---

## How to run it

The commands, in order, that a stranger would type. Include the environment variables it needs
and what happens when one is missing.

```
export SOME_API_KEY=...    # read with os.environ, never committed
python3 run.py
```

## What broke

The short version. The full version, with the error text pasted in, goes in `gotchas.md` next to
this file.

## What I would do differently

## Session record

- **Recording:** `recordings/week-01/` (gitignored, too big for the repo)
- **Transcript:** `transcript.txt` next to this file, committed, because it is your voice sample

The recording runs for the whole build session, however long that is. You then publish either
the full session or the best 30 to 40 minutes of it. The recording is not a separate 40-minute
task on top of the build.

## Publish checklist

- [ ] Brief written before the build (this file, top half)
- [ ] Delivered to {org} and watched them use it once
- [ ] `gotchas.md` written the same day it shipped
- [ ] `transcript.txt` committed
- [ ] Row added to `portfolio/README.md` and `status.md`
- [ ] `clients/{slug}.md` filled in with the number
"""


def week01_gotchas_md(a: dict) -> str:
    return """# Gotchas: week 01

Running log of what broke and what got caught, for this project only. Newest entry at the top.
Append entries and never edit the history.

This is the highest-trust file in the repo, because it is the only one that costs something to
write. Anyone can publish a win. A build log with the failures left in is verifiable, and it is
the easiest honest thing a beginner can publish. You do not need to be an expert to write down
what the error said.

## Format

Every entry is a dated H3 with exactly these five bolded fields:

- **What broke:** the symptom, with the actual error text pasted in
- **Why:** the real cause, once you found it
- **The fix:** what you changed
- **Caught:** how you saw it before the client did
- **Cost:** the time it took

Paste real error strings. A paraphrased error helps nobody and cannot be searched for.

The **Caught** field is never optional. It is the record of you checking your own work, and
checking your own work is the thing this format exists to demonstrate.

<!-- newest entry goes directly below this line -->

### 2026-09-11 The scheduled run wrote nothing and said nothing

**What broke:** the 6am run finished with exit code 0 and an empty sheet. Running it by hand
printed `gspread.exceptions.APIError: [403] The caller does not have permission`, which the
scheduled run had swallowed.
**Why:** two problems stacked. The sheet was created under a different Google account than the
one the token belonged to, so every write was denied. And my script caught the exception to keep
the run alive, which turned a hard failure into a silent one.
**The fix:** shared the sheet with the account email printed by the credentials file, then
removed the blanket `except`. Added a preflight that prints which account the token belongs to
before anything else runs, so the next 403 takes ten seconds to diagnose.
**Caught:** I printed the row count after the write and compared it to the row count before. A
run that adds zero rows now exits nonzero and prints the error, so a failed run is loud. Without
that check the club would have stared at a stale sheet all week and told me about it themselves.
**Cost:** 90 minutes. The 403 took ten of them. The other 80 went to working out why the
scheduled run had never said a word about it.
"""


def client_md(a: dict) -> str:
    org = org_name(a)
    return f"""# {org}

The real user, the real problem, the number. One file per organization you actually work with.
Copy this file for the next one and name it after them.

## Who

- **Organization:** {org}
- **My contact:** name, role, and how I reach them
- **How I know them:** the honest version, since "I am in the club" is a stronger opening than
  any cold email you could write

## The problem

In their words, with the date you asked. Paste the sentence they said.

>

## What they were doing by hand

The steps, in order, with the time each one takes. Write this down before you build anything,
because the step that hurts is rarely the step they complain about first.

1.
2.
3.

**Time per week, before:**

## What I built

One sentence, plus a link to the project.

- Project: `projects/week-01-{a[SLUG_KEY]}/README.md`
- Code:
- Runs: on demand, or on a schedule, and who triggers it

## The number

The only section a hiring manager reads twice. Fill it in with something you can defend.

- **Time given back per week:**
- **Volume handled:** rows, emails, records, whichever applies
- **Measured how:** the before number, the after number, and where each one came from

## Their words

The quote, with a date. Ask for it directly the day after they use it, since asking on delivery
day gets you politeness rather than a verdict.

>

## What happened after

The part that separates a delivery from a demo. Did they still use it three weeks later? What
broke once you were gone? Did they ask for a second thing?

## Permission

What I am allowed to publish. Ask before you post their name, and record the answer here.

- [ ] Can name the organization publicly
- [ ] Can share the code publicly
- [ ] Can quote them by name
- [ ] Sample data in the repo is invented, and their real data stays out of git
"""


def portfolio_md(a: dict) -> str:
    gh = handle(a["github"])
    slug = a[SLUG_KEY]
    return f"""# {a["name"]}

{a["school"]}, studying {a["studying"]}. I build go-to-market automations with coding agents and
ship one every week for someone who has the problem.

github.com/{gh}

## What is going on here

Every week I find one real operational problem, build the thing that fixes it, deliver it to the
person who has that problem, and publish the build log with the failures left in.

The build logs live next to each project, at `projects/week-NN-<slug>/gotchas.md`. Start there.
It is the fastest read on how I work, and it is the honest one.

## Shipped

| Week | What | For whom | Result | Code | Log |
|---|---|---|---|---|---|
| 01 | | | | [brief](../projects/week-01-{slug}/README.md) | [gotchas](../projects/week-01-{slug}/gotchas.md) |

<!-- one row per week. Result is a number or a direct quote from the person who used it. -->

## What I can do today

{bullets(a["can_do"])}

Rated on evidence, with links, in [`../me/skills.md`](../me/skills.md).

## What I am learning next

{bullets(a["gaps"])}

The live version is [`../me/gaps.md`](../me/gaps.md). It is public on purpose.

## Who I am building toward

{a["target"]}

If that describes your team and something here is useful, the code is open and the log is honest.
Reach out.

## Contact

- GitHub: github.com/{gh}
- LinkedIn: add your profile URL here
"""


# ------------------------------------------------- config files, copied over

FALLBACK_SUBREDDITS = """# Communities to read weekly if you are aiming at B2B SaaS sales and GTM roles.
# One per line. Blank lines and # comments are ignored.
#
# Verify any subreddit you add yourself before you rely on it. Open it in a browser and confirm
# it exists, is public, and has posts from this month. A dead or private subreddit returns an
# empty result set with no error, so your run looks fine and finds nothing.

salesdevelopment
gtmengineering
b2b_sales
saas
ai_agents
"""

FALLBACK_KEYWORDS = """# Search queries to run across public communities. One query per line.
# Blank lines and # comments are ignored.
#
# Group 1 tells you what the work is really called. Group 2 is the sound of your future
# employer having a bad week, and those are the threads to answer.

what does a gtm engineer actually do
how to become a gtm engineer
entry level sales development role
portfolio for a sales job

our crm data is a mess
lead routing is broken
spending hours on manual list building
our reporting takes a full day every week
"""


def starter_config(filename: str, fallback: str) -> str:
    """The starter's own config file, so the student begins from a working list.

    Falls back to a built-in copy when setup.py has been moved away from the pack.
    """
    try:
        return (STARTER_DIR / "config" / filename).read_text(encoding="utf-8")
    except OSError:
        return fallback


def subreddits_txt(a: dict) -> str:
    return starter_config("subreddits.txt", FALLBACK_SUBREDDITS)


def keywords_txt(a: dict) -> str:
    return starter_config("keywords.txt", FALLBACK_KEYWORDS)


def workspace_gitignore(a: dict) -> str:
    return """# secrets stay out of git, always. keys live in environment variables.
# .env* covers .env, .env.local, and .envrc, because direnv files hold keys too.
.env*
*.key
credentials.json
token.json
client_secret*.json

# real client data stays out of a public repo. commit the script and a row you made up,
# never the club's member list. this is the rule that keeps week 1 from becoming a leak.
data/
*.csv

# raw recordings are large. publish the clips and the links, keep the source local.
# the transcript is committed, and it lives with its project.
recordings/
*.mp4
*.mov
*.wav
*.m4a

# python
venv/
.venv/
__pycache__/
*.pyc

# setup.py's own state and the backups it takes before a --redo
.gtm-setup.json
*.bak

# os noise
.DS_Store
"""


# ---------------------------------------------------------------- file plan

# Files whose whole content is a render of the interview answers. These are the only ones any
# --redo section is allowed to rewrite.
STATIC_FILES = [
    ("CLAUDE.md", claude_md),
    ("me/profile.md", profile_md),
    ("me/skills.md", skills_md),
    ("me/gaps.md", gaps_md),
    ("me/target-roles.md", target_roles_md),
    ("portfolio/README.md", portfolio_md),
    ("status.md", status_md),
    ("signals/config/subreddits.txt", subreddits_txt),
    ("signals/config/keywords.txt", keywords_txt),
    (".gitignore", workspace_gitignore),
]


def file_plan(a: dict) -> list:
    """Every file this run writes, in the order it writes them.

    The week 1 project directory and the client file are named from the derived slug, so the
    plan depends on the answers.
    """
    slug = a[SLUG_KEY]
    plan = list(STATIC_FILES)
    plan.extend([
        (f"projects/week-01-{slug}/README.md", week01_readme_md),
        (f"projects/week-01-{slug}/gotchas.md", week01_gotchas_md),
        (f"clients/{slug}.md", client_md),
        ("voice/core-voice.md", core_voice_md),
    ])
    return plan


IDENTITY_KEYS = ["name", "school", "studying", "can_do", "gaps", "github"]

# --redo <section>: which questions get re-asked, and which files get rewritten from the answers.
# gotchas, the voice file, the client file and the week READMEs are yours to hand-edit, so no
# section ever touches them.
SECTIONS = {
    "profile": (IDENTITY_KEYS,
                ["me/profile.md", "me/skills.md", "me/gaps.md", "CLAUDE.md"]),
    "target-roles": (["target", "network"],
                     ["me/target-roles.md", "CLAUDE.md", "status.md"]),
    "portfolio": ([key for key, _p, _d in QUESTIONS],
                  ["portfolio/README.md"]),
}

# Older name for the target-roles section, kept working so a link written against the first
# version of this pack still does what it says.
SECTION_ALIASES = {"icp": "target-roles", "roles": "target-roles"}


# ---------------------------------------------------------------- scaffold

def occupied(target: Path) -> bool:
    """True when the target exists and already holds something."""
    return target.exists() and any(target.iterdir())


def save_answers(target: Path, answers: dict) -> None:
    (target / ANSWERS_FILE).write_text(
        json.dumps(answers, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_answers(target: Path) -> dict:
    """Whatever a previous run wrote. Missing or corrupt file means we ask again, not crash."""
    path = target / ANSWERS_FILE
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def scaffold(target: Path, answers: dict, only: list | None = None) -> list:
    """Write the files. `only` limits it to a --redo section.

    Returns a list of (relpath, 'created' | 'overwrote'). On a --redo, a file that already
    exists is copied to <name>.bak first, so a redo can never silently eat a table you filled
    in by hand.
    """
    written = []
    for rel, render in file_plan(answers):
        if only is not None and rel not in only:
            continue
        path = target / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        action = "created"
        if path.exists():
            action = "overwrote"
            if only is not None:
                backup = path.with_suffix(path.suffix + ".bak")
                backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        path.write_text(render(answers), encoding="utf-8")
        written.append((rel, action))
    return written


# ---------------------------------------------------------------- git

def git(target: Path, *args: str) -> bool:
    """Run one git command in the workspace. False on any failure, and never raises."""
    try:
        done = subprocess.run(("git", "-C", str(target)) + args,
                              capture_output=True, text=True)
    except (OSError, ValueError):
        return False
    return done.returncode == 0


def git_bootstrap(target: Path) -> str:
    """git init plus the first commit. Returns a one-line status for the summary."""
    message = "gtm workspace: me, target roles, signals, week 01"
    try:
        subprocess.run(("git", "--version"), capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return "git not found, so no repo was created. Install git, then run `git init` here."

    if (target / ".git").exists():
        return "already a git repo, left the history alone."

    if not (git(target, "init", "-b", "main") or git(target, "init")):
        return "`git init` failed. Run it by hand in this folder."

    if not git(target, "add", "-A"):
        return "repo created, but `git add` failed. Run `git add .` by hand."

    if not git(target, "commit", "-m", message):
        return ("repo created and staged, but the commit failed. Git usually wants an identity "
                "first:\n  git config --global user.name \"Your Name\"\n"
                "  git config --global user.email \"you@example.com\"\n"
                f"  git commit -m \"{message}\"")

    return "repo created and the first commit is in."


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Interview a student and scaffold their public GTM workspace.")
    parser.add_argument("target", nargs="?", default=None,
                        help=f"where to scaffold the workspace (default: ./{DEFAULT_TARGET})")
    parser.add_argument("--out", dest="out", default=None,
                        help="same as the positional target, for people who prefer a flag")
    parser.add_argument("--force", action="store_true",
                        help="overwrite an existing non-empty target")
    parser.add_argument("--non-interactive", action="store_true",
                        help="skip the interview and use the example student's answers")
    parser.add_argument("--redo", choices=sorted(set(SECTIONS) | set(SECTION_ALIASES)),
                        metavar="SECTION",
                        help="re-ask one section and rewrite only its files: "
                             + ", ".join(sorted(SECTIONS)))
    parser.add_argument("--no-git", action="store_true",
                        help="skip the git init and the first commit")
    args = parser.parse_args()

    if args.target and args.out and args.target != args.out:
        print(f"Two different targets given: '{args.target}' and --out '{args.out}'. Pick one.",
              file=sys.stderr)
        return 2

    raw_target = args.out or args.target or DEFAULT_TARGET
    target = Path(raw_target).expanduser()
    shown = raw_target.rstrip("/") or "."

    # ---- --redo: one section, in place, everything else untouched
    if args.redo:
        section = SECTION_ALIASES.get(args.redo, args.redo)
        if not target.exists():
            print(f"'{shown}' does not exist yet, so there is nothing to redo. Run setup.py "
                  f"without --redo first.", file=sys.stderr)
            return 2
        keys, section_files = SECTIONS[section]
        previous = load_answers(target)
        print(f"Redoing the '{section}' section of '{shown}'. "
              f"Only {', '.join(section_files)} gets rewritten.")
        if args.non_interactive:
            answers = {**defaults(), **previous}
            print("Non-interactive run, keeping the answers already on file.")
        else:
            answers = {**defaults(), **previous, **interview(keys, previous)}
        answers = with_derived(answers)
        save_answers(target, answers)
        written = scaffold(target, answers, only=section_files)
        print(f"\n{shown}/")
        for rel, action in written:
            print(f"  {action:<9} {rel}")
        print("\nThe previous version of each rewritten file is next to it as a .bak. "
              "Delete those once you have checked the result.")
        return 0

    # ---- full scaffold
    if occupied(target) and not args.force:
        print(f"'{shown}' already has files in it. Re-run with --force to overwrite, use "
              f"--redo <section> to redo one part, or pick another target directory.",
              file=sys.stderr)
        return 2

    print(f"Scaffolding a GTM workspace in '{shown}'.")
    if args.non_interactive:
        answers = defaults()
        print("Non-interactive run, using the example student's answers.")
    else:
        answers = interview()

    answers = with_derived(answers)
    written = scaffold(target, answers)
    save_answers(target, answers)

    print(f"\n{shown}/")
    for rel, action in written:
        print(f"  {action:<9} {rel}")

    git_note = "skipped, --no-git" if args.no_git else git_bootstrap(target)

    print(f"""
{len(written)} files. Read CLAUDE.md first, then fill the blanks in me/profile.md, me/gaps.md,
and me/target-roles.md. status.md tells you where you are every time you come back.

Week 1 is already scaffolded at projects/week-01-{answers[SLUG_KEY]}/, with its client file at
clients/{answers[SLUG_KEY]}.md. Write the brief before you write any code.

git: {git_note}

Next, make it public in one line, from inside '{shown}':

  gh repo create gtm-workspace --public --source=. --push

Or point it at a repo you already created on GitHub:

  git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPO.git
  git push -u origin main

That push is your first public artifact. Do it before you write another line of anything.""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
