# Student GTM

You are in school, you want a go-to-market job, and the page a hiring manager opens has nothing on it yet. This starter turns a coding agent into a public track record: your own repo with dated commits, one project a week recorded while you build it, a gotchas log that reads like an engineer's notebook, and one delivered project for a real client you already have access to on campus. Run `python3 setup.py`, answer eight questions, and it writes the workspace, runs `git init`, and makes the first commit. Every file it writes is yours to keep.

Part of the [GTM Coding Agent Starter Kit](../../README.md). Read [Chapter 21](../../chapters/21-student-gtm.md) for the reasoning, and [`modes/student.md`](../../modes/student.md) for the mode this starter runs: the stack, what to skip, and the learning path.

## What it does

```
python3 setup.py   (eight questions)
        │
        ▼
  YOUR repo, outside this one:
  CLAUDE.md · me/ · signals/config/ · projects/ · clients/ · voice/ · portfolio/ · status.md
        │
        ▼
  week NN project  ──►  one recording of the whole session  ──┬──►  the long video
  projects/week-NN-<slug>/                                    ├──►  2-3 clips
        │                                                     └──►  transcript.txt ──► voice/core-voice.md
        ▼
  push to GitHub  +  one post  +  projects/week-NN-<slug>/gotchas.md
        │
        ├──►  campus/ offer + outreach  ──►  one delivered client  ──►  clients/<org-slug>.md
        │
        ▼
     inbound
```

### The workspace `setup.py` builds

This is the tree every file in this pack describes. It lives in your own repo, outside this kit.

```
<workspace>/                     # the repo you own, and the one you link on LinkedIn
  CLAUDE.md                      # points the agent at me/, voice/, and the current week
  me/
    profile.md                   # who you are, what you are studying, what you have done
    skills.md                    # what you can do today, rated 1-4 on evidence
    gaps.md                      # what you cannot do yet. The important one.
    target-roles.md              # the roles and companies you want, and why
  signals/
    config/subreddits.txt        # the rooms where your future employer complains
    config/keywords.txt          # the phrases that mean somebody has that problem
  projects/
    week-01-<slug>/
      README.md                  # problem / input / output / result
      gotchas.md                 # this project's log
      transcript.txt             # you add this after the first recording. Committed;
                                 # it is your voice sample.
  clients/
    <org-slug>.md                # the real user, the real problem, the number
  voice/
    core-voice.md                # extracted from your own transcripts
  portfolio/README.md            # the index a hiring manager reads first
  status.md                      # what week you are on, what shipped, what is next
  .gitignore                     # data/, *.csv, .env*, recordings/, .gtm-setup.json, *.bak
  .gtm-setup.json                # your interview answers, so --redo can re-ask one section
                                 # without losing the rest. Gitignored.
```

The week-01 folder is named from the first organization on your reachable list, so "the student consulting club" becomes `projects/week-01-student-consulting-club/`, and its client file lands at `clients/student-consulting-club.md`. Leave that answer blank and the slug falls back to `first-client`.

Raw recordings live in `recordings/week-NN/` and are gitignored, because a raw screen recording is far too big for a repo. The transcript is the part that gets committed, and it sits with the project it came from at `projects/week-NN-<slug>/transcript.txt`.

### What ships in this starter

- **`setup.py`** interviews you with eight questions, writes the tree above at a path you choose, runs `git init`, makes the first commit, and prints what to do next. It writes outside this repo on purpose. The output is your repo, not a fork of somebody else's.
- **`workspace.example/`** the same tree, filled in for the example student, so you can read the shape before you run anything.
- **`config/subreddits.txt`** and **`config/keywords.txt`** the rooms where the people who would hire you complain, and the phrases that mean somebody has a problem you can answer. `setup.py` copies both into your workspace at `signals/config/`, so you start from a working list and edit from there.
- **`build-in-public/weekly-loop.md`** the recurring week written down, step by step, so you run it instead of re-deciding it every Monday.
- **`build-in-public/post-templates.md`** three formats: the gotchas post, the weekly build post, and the answer-a-question reply.
- **`campus/offer.md`** and **`campus/outreach.md`** the one-page offer for a campus organization or a local business, how to ask, and what to send after they say yes.
- **`SKILL.md`** the operating manual your agent reads when you say "student gtm".

## The eight modules

The curriculum is eight modules. You run them in order the first time, then they become one repeating week.

| # | Module | What it means in practice |
|---|---|---|
| M1 | The knowledge base is a folder of files | Who you are, what you are studying, what you can build, where the gaps are, who you want to sell to. You write it raw, the agent structures it. Your own codebase becomes the context every future session reads. |
| M2 | Build in public, and keep a gotchas log | Ship the unpolished version. Write down what broke and what you caught. For somebody starting out, that format is the highest-trust and lowest-friction thing you can publish honestly. |
| M3 | LinkedIn for the personal brand, GitHub for the technical portfolio | Two surfaces, two jobs. In GTM roles today, the engineering is the part that gets read. |
| M4 | A weekly project, recorded and clipped | Record the whole build session, however long it runs. That file is the long video, the clip source, and the transcript that becomes your voice profile. One recording feeds all three. |
| M5 | Use the network you already have | Campus organizations and local businesses are real clients with real problems. One automation delivered and written up beats ten personal projects. |
| M6 | Research the buyer, then answer them | Read the rooms where your future employer complains. Answer questions instead of pitching. |
| M7 | Get to inbound | Publishing is the mechanism that makes people come to you, which is worth more than any outbound sequence you can run from a dorm room. |
| M8 | Read the market you are entering | Titles do not define you, skills do. Evaluate a startup by whether it solves a real problem and whether the founders did the buyer research. |

## What it costs

Nothing, at the starter level. Python is free, git is free, GitHub is free, LinkedIn is free, and your laptop already records a screen. This starter calls no paid data provider, needs no API key, and hosts nothing. The one line item is the coding agent itself, which runs on a paid plan. Student pricing and free tiers move around, so check the current terms before you commit to one.

## Prerequisites

- Claude Code (or another coding agent) already running on your machine
- Python 3.9+
- A GitHub account, and a LinkedIn account
- A screen recorder with audio (QuickTime, OBS, or whatever you already have)
- If you have never opened a terminal, start at [first-boot](https://github.com/shawnla90/first-boot). It covers the terminal, git, Claude Code, context engineering, and shipping your first thing. This starter picks up where that one ends and assumes you have an agent running.

## Setup

### 1. Clone and enter the starter

```bash
git clone https://github.com/shawnla90/gtm-coding-agent.git
cd gtm-coding-agent/starters/student-gtm
```

### 2. Check Python, and skip the install for now

```bash
python3 --version
```

`setup.py` is pure standard library, so there is nothing to install before you run it. `requirements.txt` holds one package, `requests`, and it is only for the optional signal steps later. Install it when you get there:

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### 3. Run the interview

```bash
python3 setup.py                 # interview, then build ./my-gtm
python3 setup.py --out ~/my-gtm  # same, at a path you pick
```

It asks eight questions, one at a time, each with a bracketed default you can accept by pressing Enter:

1. Your name, as it should read on the portfolio page
2. School and year
3. What you are studying
4. What you can do today, comma separated
5. Where the gaps are, comma separated
6. The kind of company you want to work for
7. Campus organizations or local businesses you can reach this week, comma separated
8. Your GitHub handle

Answer like you are texting a friend, not writing a cover letter. Raw answers structure better than polished ones, and the agent tightens them later.

The interview does not ask for your three target job titles or your twenty target companies. Those are a judgment call you make after you have read the market for a week, and they go into `me/target-roles.md` by hand. Doing that list on day one produces a list you cannot defend.

`setup.py` writes every file in the tree above, fills them from your answers, copies the starter's signal lists into `signals/config/`, seeds the week-01 `gotchas.md` with the five-field format and one worked example entry to write over, saves your answers to `.gtm-setup.json`, then runs `git init` and makes the first commit. That commit is the first public thing you own.

The flags:

| Flag | What it does |
|---|---|
| `--out <path>` | Where to build the workspace. Same thing as the positional argument, for people who prefer a flag. Default is `./my-gtm`. |
| `--force` | Overwrite a target directory that already has files in it. Without this, a non-empty target stops the run. |
| `--redo <section>` | Re-ask one section and rewrite only that section's files. Every file it touches is copied to `<name>.bak` first, so a redo cannot eat a table you filled in by hand. Answers already on file become the defaults, so Enter keeps what you said last time. |
| `--non-interactive` | Skip the interview and fill every answer with the example student. Useful for seeing the output shape before you commit to your own answers. |
| `--no-git` | Skip the `git init` and the first commit. |

The sections `--redo` accepts today are `profile`, `target-roles`, and `portfolio`, and `python3 setup.py --help` prints the current list. Sections only cover the files that are pure renders of your answers. Your gotchas entries, your voice file, your client files, and your project READMEs are hand-written, and no section ever overwrites them.

### 4. Push it

`setup.py` already made the first commit, so this is the remote and the push:

```bash
cd ~/my-gtm
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPO.git
git push -u origin main
```

Create the empty repo on GitHub first. Public, no README, since you already have one. `setup.py` also prints the GitHub CLI one-liner, `gh repo create gtm-workspace --public --source=. --push`, which does the create and the push in one step if you have `gh` installed. Either way, that URL is the link you put on LinkedIn.

### 5. Write your own offer

`setup.py` has already put a working `signals/config/subreddits.txt` and `signals/config/keywords.txt` in your workspace. Your job is to re-point them at the market you want to be hired into rather than a market you want to sell to. Before you edit a single line of those files, write the offer.

Setting a buyer-signal tool up means writing an offer: a name, a one-liner, the selling points, and the competitors. Those four fields are a positioning exercise, and doing it for yourself is the highest-value first rep in this pack. Saying what something does, for whom, in one sentence a stranger understands, is the skill the job is actually made of.

**Two worked examples first.** Both are real, both are public, and you can check every line of them yourself.

**ChatGPT (OpenAI)**

- **Name:** ChatGPT
- **One-liner:** An assistant you talk to in plain language, and it writes, explains, and works through problems with you.
- **Selling points:** Free tier that does real work; answers in seconds instead of a search-and-read session; handles text, code, and images in the same conversation; runs in a browser with nothing to install.
- **Competitors:** Claude, Gemini, Copilot, a search engine plus your own reading time.

**Cal AI**

- **Name:** Cal AI
- **One-liner:** Point your phone camera at a plate of food and it logs the calories, so tracking takes a photo instead of five minutes of typing.
- **Selling points:** Photo instead of manual entry; works on food that has no barcode and no database row; built by a teenager who posted the whole build publicly while it grew, which is why anyone heard about it at all.
- **Competitors:** MyFitnessPal, Lose It, a paper notebook, giving up in week two.

Read those two and note what they have in common: a one-liner a stranger understands with no context, and selling points that are checkable facts rather than adjectives.

**Now write yours.** You are the product.

```markdown
**Name:**            <your name, or the handle your work ships under>

**One-liner:**       I build <what> for <who> using <how>, and they get <result>.
                     One sentence. A stranger has to get it on the first read.

**Selling points:**  3 to 5 lines, each one a fact with a date, a number,
                     a link, or a named organization behind it.
                     - <thing you shipped> for <named org>, <the number it moved>
                     - <skill> demonstrated at <link to the commit or the repo>
                     - <cadence you have actually held, with the commit history to show it>

**Competitors:**     Who else is in the stack of resumes on that desk, and what
                     they show up with. Be specific and be honest. "Every other
                     junior applicant" is not an answer; "candidates with a summer
                     internship and no public code" is.
```

Two rules for writing it:

1. **Say it out loud first, then type what you said.** Explain it to a roommate, record the ten seconds on your phone if that helps, and write down the version that came out of your mouth. The spoken version is always shorter and clearer than the version you compose in a text box.
2. **No adjective you cannot prove.** "Detail-oriented" means nothing and every applicant claims it. "I hand it back inside a week, working, with a README" means something, and it is falsifiable, which is exactly why it lands.

Then hand it to the agent and make it argue with you:

```
Read me/profile.md, me/skills.md, and me/gaps.md.

Interview me for my offer: name, one-liner, selling points, competitors.
Ask one question at a time. Push back on any claim I cannot point at a
commit, a link, a date, or a named person for. If I use an adjective,
ask me what evidence makes it true, and if I do not have any, cut it.

Write the result to me/target-roles.md under an "Offer" heading. Use my
words. Do not smooth them out.
```

Keep the offer next to your target roles, because it is the same document from two angles: who you want to work for, and what you say when you get in front of them. Re-read it every four weeks. By week six it will have real numbers in it, and the version you wrote in week one will read like somebody else.

## The week

One week, one project, one recording. This is the cadence the whole pack is built around. The step-by-step version, with the prompts, is in [`build-in-public/weekly-loop.md`](build-in-public/weekly-loop.md).

| Day | The work | Time | What goes public |
|-----|----------|------|------------------|
| Mon | Read the signal queue, answer one thread, pick the week's project from what you read | 30 min | One real answer in a thread |
| Tue | Confirm the client, write `projects/week-NN-<slug>/README.md` before any code | 30 min | Commit the brief |
| Wed | Build it, screen recording running the whole session | 2-5 h | Nothing yet |
| Thu | Ship it to the person who asked. Write `gotchas.md` the same day | 1 h | Repo push, README, gotchas |
| Fri | Cut clips from Wednesday, publish | 1 h | Long video, 2-3 clips, one post |
| Sat | Update `me/skills.md` and `me/gaps.md` from what actually happened | 15 min | Nothing |
| Sun | Off | | |

**Total 5 to 8 hours a week.**

About the recording, because this is the part people get wrong: it runs for the whole build session, however long that is. You are not adding a 40-minute filming task on top of a three-hour build. You press record before you open the editor and stop it when the thing works. Afterward you publish either the full session or the best 30 to 40 minutes of it, and the transcript of the whole thing goes to `projects/week-NN-<slug>/transcript.txt`.

Week two is the same week, plus `campus/outreach.md`. That is when the personal project becomes a client project, and when the `clients/<org-slug>.md` file setup.py started gets a real number written into it.

## The gotchas format

One format, in every project folder, newest entry at the top of `projects/week-NN-<slug>/gotchas.md`. Every entry is a dated H3 with exactly these five bolded fields:

```markdown
### 2026-09-14 Duplicate reminders went to 40 people

**What broke:** 40 rows had a trailing space on the email, so my dedupe missed them
and those people were queued twice.
**Why:** I compared raw strings instead of normalizing first.
**The fix:** `.strip().lower()` before building the set.
**Caught:** I printed the recipient count before sending and it was 28 higher than
the sheet's row count. That is why I saw it before the client did.
**Cost:** 40 minutes.
```

The **Caught** field is the one that is never optional. It is the record of you checking your own work, which is the whole reason this format exists and the reason a hiring manager reads the file at all.

## Make it yours

The starter ships pointed at a generic student. Point it at you with four edits, and the example below shows what each one looks like filled in.

Sam is a business student at a state university, junior year, marketing major, and can write Python when the agent explains what each line does.

1. **`me/skills.md` and `me/gaps.md`** what you can build unassisted, what you can build with the agent, and what you cannot build yet. Sam's skills file says "I can wire a Google Sheet to a Python script and schedule it," rated 3 because there is a commit behind it. Sam's gaps file says "I cannot deploy anything yet," rated honestly, and that gap is week four's project.
2. **`me/target-roles.md`** the three titles and twenty companies, plus the offer from step 5. Sam listed GTM engineer, revenue operations analyst, and growth associate, at seed and Series A B2B software companies in one metro area.
3. **`signals/config/subreddits.txt`** and **`signals/config/keywords.txt`** the rooms and phrases. Sam is reading the operations and sales-engineering communities where people complain about the exact stack those twenty companies run.
4. **`campus/offer.md` and `clients/<org-slug>.md`** the one client. The consulting club Sam belongs to collects member signups in a Google Form and retypes them into a spreadsheet by hand every week. That is week one: the sync script, delivered, written up, and credited to a named organization instead of a personal repo.

One delivered project with a real user beats ten toy projects, and it is the only line on the page a hiring manager can verify by asking someone.

## Take it further

- **Clip the weekly recording.** The loop hands off to `starters/podcast-shorts/` for transcript-anchored vertical clips. That starter and its chapter ship on their own branch, so if the folder is not in your checkout yet, keep recording anyway and clip the backlog when it lands.
- **Score the rooms before you post in them.** `starters/reddit-buyer-signals/` ([Chapter 18](../../chapters/18-reddit-buyer-signals.md)) pulls the recent threads in your subreddits and scores them, so your Monday goes to the conversations that are actually live. Copy it into `signals/` and keep the database out of git.
- **Put the portfolio on a URL.** `portfolio/README.md` is already the index. GitHub Pages renders it for free, and a link reads better on a resume than a repo tree.
- **Grow the voice profile.** Every recording produces a transcript. Feed them into `voice/core-voice.md` using [Chapter 09](../../chapters/09-voice-dna-content.md) so your posts sound like you talking, because they are.
- **Automate the reminder.** A cron job that opens `weekly-loop.md` every Monday morning costs one line and removes the decision ([Chapter 05](../../chapters/05-automation-agents.md)).
- **Add the second client.** `campus/offer.md` re-points by editing the organization name and the problem statement. The delivery is the same, and `clients/` gets another file.

## Troubleshooting

- **`python3: command not found`**: the toolchain is not installed yet. Go do [first-boot](https://github.com/shawnla90/first-boot) first, then come back.
- **`'my-gtm' already has files in it`**: the target directory is not empty. Re-run with `--force` to overwrite it, `--redo <section>` to redo one part, or `--out <other-path>` to build somewhere else.
- **`Permission denied`** writing the workspace: the path you passed is not writable by your user. `setup.py` writes wherever you point it and does no checking of the location for you, so pass a path you own, such as `--out ~/my-gtm`.
- **`fatal: not a git repository`**: `setup.py` runs `git init` and the first commit itself, so this means one of three things. You passed `--no-git`; git was missing when you ran it, in which case setup.py said so in its summary; or you are running the command outside the workspace folder. Fix: `cd` into the workspace, then run `git init` there if setup.py told you it skipped it.
- **`Author identity unknown`** or a failed first commit: git wants a name and an email before it will commit. setup.py prints the two `git config --global` commands when this happens. Run them, then run the commit it printed.
- **`remote: Repository not found`** on your first push: create the empty repo on GitHub before you add the remote, and check the username in the URL.
- **`ModuleNotFoundError: requests`** on a signal script: you skipped the optional install. Run `source venv/bin/activate`, then `pip install -r requirements.txt`. `setup.py` itself imports nothing outside the standard library, so it never causes this.
- **`setup.py` wrote a profile that reads like a cover letter**: you answered in resume language. Run `python3 setup.py --redo profile` and answer in plain sentences.
- **`gotchas.md` is still empty on Thursday**: you are polishing before you publish. Log the break at the moment it breaks, fill in **Caught** while you still remember what tipped you off, and clean up the wording later.
- **The recording has no audio**: check the input device before the take, not after. A silent session costs you the video, the clips, and the transcript in one go, and there is no fixing it afterward.

## Build vs buy

This is build versus buy, with eyes open, and as a student you are on the build side of it by default. You have time and no money, which is the exact inverse of the company you want to work for. That is the arbitrage: you can spend a semester building the thing a team would buy, and arrive already knowing what the purchase would have bought them. When the time-versus-money math flips, and it does flip the day you get hired, buying the data layer starts making sense. That is what [Clearbox](https://clearbox.to) does.

---

> 🟧 **Clearbox** is the engine behind this starter kit. See your market. Move first. Start a 7-day free trial at [clearbox.to](https://clearbox.to).
