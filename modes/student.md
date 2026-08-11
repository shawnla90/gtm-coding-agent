# Student Mode

**For:** A college student with no budget, no title, and no portfolio who wants a go-to-market career and is willing to build in public for a semester.

---

## Philosophy

Trade polish for evidence. You are not competing with other students on GPA or on the name of the firm that gave you a summer internship, because that competition is already crowded and you will not win it from behind. You are competing on the one thing almost nobody in the applicant pool has: a dated public record of you solving real problems for real users. Twelve small shipped things with write-ups beats one prestigious line on a resume, and it beats it in the exact rooms you want to be in.

That means the system optimizes for weekly output over quality on any single week. Every hour goes to build, ship, write it up, publish. Nothing goes to infrastructure, tool evaluation, or a personal site nobody asked for. Start where [first-boot](https://github.com/shawnla90/first-boot) ends: Claude Code running, git working, one thing already shipped. If that is not true yet, do first-boot this weekend and come back. `chapters/21-student-gtm.md` is the reasoning behind everything below.

You do not build the workspace by hand. `starters/student-gtm/` is the runnable pack: `python3 setup.py` interviews you, writes the folder structure below to a path you choose, runs `git init`, and makes the first commit. Run it before day one, then spend day one on the answers instead of on `mkdir`.

## Recommended Stack

| Tool | Purpose | Cost |
|------|---------|------|
| Claude Code | The agent you build with | Included in a Claude plan (check current student and free tiers) |
| Git + GitHub | Version control and the public portfolio | Free |
| Python 3 | Every script you will write | Free |
| SQLite | Local database, ships with Python | Free |
| Google Sheets + Docs | Where your campus clients already keep their data | Free with your school account |
| OBS Studio | Records the weekly build session | Free |
| Whisper (local) | Transcribes the recording, on your laptop | Free |
| LinkedIn | The personal brand surface | Free |
| Reddit | Buyer signal from the market that will hire you | Free |
| Vercel (hobby) | Hosts one page when a project needs a URL | Free |
| Apollo (free tier) | Contact data when a client project needs it | Free (50 credits/mo) |

The only line with a price on it is the agent, and it is the one thing worth spending student money on. Everything else stays free at the volume you run, and it stays free for the whole semester. Resist adding paid tools. An extra subscription buys you a login to maintain, and what you actually need is another shipped project.

## Folder Structure

One repo, public from day one. Nothing here is embarrassing enough to hide. This is exactly what `setup.py` writes:

```
<workspace>/                     ← your repo, your machine, your GitHub account
  CLAUDE.md                      ← points the agent at me/, voice/, and the current week
  me/
    profile.md                   ← who you are, what you're studying, what you've done
    skills.md                    ← what you can do today, rated 1-4 on evidence
    gaps.md                      ← what you can't do yet. The important one.
    target-roles.md              ← the roles and companies you want, and why
  signals/
    config/subreddits.txt        ← the rooms where your future employer complains
    config/keywords.txt          ← the phrases that mean somebody has that problem
  projects/
    week-01-<slug>/
      README.md                  ← problem / input / output / result
      gotchas.md                 ← this project's log
      transcript.txt             ← from the recording. Committed; it's your voice sample.
  clients/
    <org-slug>.md                ← the real user, the real problem, the number
  voice/
    core-voice.md                ← extracted from your own transcripts
  portfolio/README.md            ← the index a hiring manager reads first
  status.md                      ← what week you're on, what shipped, what's next
  .gitignore                     ← data/, *.csv, .env*, recordings/, .gtm-setup.json, *.bak
```

Two things live outside that tree on purpose. Raw recordings go in `recordings/week-NN/`, gitignored, because a repo is the wrong home for a multi-gigabyte file, and the transcript is what you commit instead. `.gtm-setup.json` holds your interview answers so `python3 setup.py --redo <section>` can re-ask one part without wiping the rest, and it stays out of git with everything else in the ignore list.

Skip `campaigns/`, skip `segments/`, skip anything that models a sales pipeline. You do not have a pipeline, you have a semester and a list of campus organizations. Skip a personal website until at least week six, because a landing page with nothing behind it is a week you did not ship. And skip a database for anything other than the signal pull, since a markdown file the agent can read is faster to write and easier to change than a schema you will regret. Add structure only when a specific week's work is blocked without it.

## First Week Priorities

Run `python3 setup.py` from `starters/student-gtm/` before the week starts. It builds the tree above and makes the first commit, so Monday goes to the answers rather than to `mkdir`.

Then run the week below. It is the same week you repeat for the rest of the semester, with the one-time setup folded into Monday and Tuesday.

| Day | The work | Time | What goes public |
|-----|----------|------|------------------|
| Mon | Read the signal queue, answer one thread, pick the week's project from what you read | 30 min | One real answer in a thread |
| Tue | Confirm the client, write `projects/week-NN-<slug>/README.md` before any code | 30 min | Commit the brief |
| Wed | Build it, screen recording running the whole session | 2-5 h | Nothing yet |
| Thu | Ship it to the person who asked. Write `gotchas.md` the same day | 1 h | Repo push, README, gotchas |
| Fri | Cut clips from Wednesday, publish | 1 h | Long video, 2-3 clips, one post |
| Sat | Update `me/skills.md` and `me/gaps.md` from what actually happened | 15 min | Nothing |
| Sun | Off | | |

**Total 5 to 8 hours a week,** and the range is Wednesday. The recording runs for the whole build session, however long that is. You then publish either the full session or the best 30 to 40 minutes of it. It is not a separate 40-minute recording task on top of the build.

### Before Monday: the interview

`setup.py` asks its eight questions and fills what it can. Then open Claude Code in the workspace and have it interview you until `me/profile.md`, `me/skills.md`, `me/gaps.md`, and `me/target-roles.md` are finished, using the prompt in `chapters/21-student-gtm.md`. Rate skills on evidence, not on what you have read about, and let `gaps.md` be honest. An agent that thinks you are fluent will hand you code you cannot defend in an interview. Then wire all four files into `CLAUDE.md` using the pattern in `templates/claude-md/` so every later session starts with them loaded.

### Monday, 30 min: read the rooms, answer one thread

Week one this day is longer, because you are pointing the engine before you can read it. Use the generated `signals/config/` files as human reading and offer-research notes, configure a Clearbox offer for the market you want to work in, and run `starters/reddit-buyer-signals/run.sh --offline` first to inspect the synthetic source contract with no account access or cost. When you have a complete classified export, run the starter with `CLEARBOX_EXPORT=/absolute/path/to/export.json`; the generated `.gitignore` keeps local data out of the commit. Chapter 18 (`chapters/18-reddit-buyer-signals.md`) explains the source, recency, and human-action guardrails, and they apply to you unchanged.

Configuring that engine means naming a brand and its competitors, so write your own offer while you are in there: name, one-liner, selling points, competitors, with you as the product. The worked examples, the template, and the two rules are in the offer section of `chapters/21-student-gtm.md`.

Every Monday after that: read what the pull returned, answer one thread for real, and pick the week's project out of what you just read.

### Tuesday, 30 min: confirm the client, write the brief

Ask one student organization for one operational problem. An RSVP list maintained by hand, a recruitment funnel living in a group chat, a sponsorship pipeline in one senior's inbox. Take whatever they say yes to, even if it sounds small. `starters/student-gtm/campus/offer.md` has the scoping conversation and the one-page scope contract. Write `projects/week-01-<slug>/README.md` in the problem / input / output / result shape from Chapter 21 and commit it before you write any code.

### Wednesday, 2-5 h: build it with the recorder on

Start OBS before you start building and talk through the work for the whole session. One take, failures left in. `chapters/07-python-for-gtm.md` covers the API and CSV work you will hit.

### Thursday, 1 h: ship it, then write the gotchas entry

Deliver it to the person who asked, in a state they can run without you. Then write the gotchas entry the same day, while it is still fresh. One file per project at `projects/week-NN-<slug>/gotchas.md`, newest entry at the top, five fields every time:

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

Caught is never optional. It is the record of you checking your own work, which is the thing the format exists to demonstrate.

### Friday, 1 h: publish

Transcribe the recording locally with whisper, save it to `projects/week-01-<slug>/transcript.txt`, and feed it to the agent with the extraction prompt in `chapters/09-voice-dna-content.md` to produce `voice/core-voice.md`. Then publish three things: the repo with a real README, the long video, and one LinkedIn post about what broke. Two or three vertical clips come out of the same recording through `starters/podcast-shorts/` and `chapters/20-podcast-to-shorts.md`.

### Saturday, 15 min: update skills and gaps

Move anything you actually did this week into `me/skills.md` with the evidence attached, and rewrite `me/gaps.md` around whatever this week showed you cannot do yet. Fifteen minutes, and it is what keeps the agent useful in week nine.

## What to Skip

- **A personal website before week six.** A URL with nothing behind it is a week you did not ship.
- **Tool evaluation.** The stack above is decided. Spending Saturday comparing note apps is the highest-comfort way to avoid building.
- **Cold outbound.** A cold email from a .edu with no track record behind it loses to every other email in that inbox. Publish for twelve weeks, then send outreach that points at something.
- **Paid data and enrichment.** Campus clients have their data in a sheet already. You need a Sheets read, not a vendor.
- **Certifications.** A certificate says you finished a course. A repo says someone used your work.
- **Editing the video.** The unedited session with the dead ends in it is the content. Post the whole thing, or the best forty minutes of it, and cut clips later.
- **Anything an interviewer could ask about that you cannot answer.** If the agent wrote something you do not understand, either learn it this week or take it out of the repo.

## What You Have That Nobody Else Does

Your campus network is a client list, and it is the single asset a working professional cannot buy.

Every student organization on your campus is a small business with an operations problem and no budget for software. A club with a 400-person mailing list maintained by hand. A student-run consulting group tracking sponsors across three inboxes. A radio station whose shift spreadsheet breaks every time somebody swaps. The businesses two blocks off campus have the same problems with less time to fix them. These are real users, with real deadlines, who will say yes to a free build in about an hour, because the alternative is doing it manually again.

That access is worth more than it looks. A personal project proves you can write code. A delivered automation proves your work survived contact with a person who did not care how it was built, whose data was messy, who used it wrong on day one, and who came back with a change request. That last part is the actual job, and it is the part almost no junior candidate has ever done. One delivered automation with a named user and a number in the write-up outweighs ten tutorial projects on a portfolio site.

Log each one in `clients/<org-slug>.md`: who they are, what the problem was, what you built, what the number was before and after. If the number did not move, write that down too. An honest "this did not work and here is what I would test next" reads as more credible than a clean result, and by week twelve you have a folder of case studies instead of a list of claims.

## Learning Path

Read these chapters in this order:

1. **Chapter 21:** Student GTM (the reasoning behind this whole mode)
2. **Chapter 02:** Context Engineering (why `me/` is a folder of files and how to wire it into CLAUDE.md)
3. **Chapter 07:** Python for GTM (APIs, CSVs, and the scripts your campus clients need)
4. **Chapter 18:** Reddit Buyer Signals (the engine you point at your future employer's market)
5. **Chapter 09:** Voice DNA (turn your build transcripts into a voice profile)
6. **Chapter 20:** Podcast to Shorts (one recording into a week of distribution)
7. **Chapter 05:** Automation Agents (when a weekly script should just run itself)

Read the rest when a project needs them. Chapters 11 through 17 are company-scale problems and they will still be there when you have the company.

---

**Starter:** [`starters/student-gtm/`](../starters/student-gtm/) is the runnable pack behind this mode. `python3 setup.py` builds the workspace, `build-in-public/weekly-loop.md` is the week in detail, and `campus/offer.md` is how you get the first client.
**Chapter:** [`chapters/21-student-gtm.md`](../chapters/21-student-gtm.md) is the reasoning, the gotchas argument, and the offer exercise.

*Nobody is going to hand you the experience. Ship something small for someone real every week, write down what broke, and publish it. Twelve weeks from now the resume is a formality.*
