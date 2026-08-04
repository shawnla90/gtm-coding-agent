---
name: student-gtm
description: Scaffold a student's own GTM repo and run the weekly build-in-public loop that turns a coding agent into a public go-to-market track record. Invoke on "student gtm", "set up my student workspace", "/student-gtm", "I'm a student and I want to break into GTM", "how do I get a GTM job with no experience", or when someone still in school, with nothing public to point at yet, asks how to get hired into go-to-market.
---

# student-gtm: a public track record before you have the title

Interview → the student's own repo → one weekly project → one recording of the whole build
that feeds a video, clips, and a voice profile → commits and posts → one delivered campus
client → inbound.

Read alongside [Chapter 21](../../chapters/21-student-gtm.md), which is the reasoning behind
every step here, and [`modes/student.md`](../../modes/student.md), which is the mode this
starter runs: the free stack, what to skip, and the chapter order. This file is the operating
manual for the runnable pack; those two are the why and the semester plan.

## When to invoke

- A student (or a career switcher with the same starting conditions) has a coding agent running and wants a GTM job, and has nothing public to point at yet.
- Someone asks what to build to get hired, and the honest answer is a repeating weekly loop rather than one impressive project.
- An existing student workspace needs its next week planned, its gotchas entry written, or its portfolio index rebuilt.

Do NOT invoke for terminal, git, or first-agent-setup teaching. That is [first-boot](https://github.com/shawnla90/first-boot), and this skill assumes it is done. Also do not invoke for a funded company's GTM build, a client engagement, or any workspace that already has a paid data stack.

## Layout

The pack itself:

```
starters/student-gtm/
  SKILL.md                       # this file, the operating manual
  README.md                      # the human front door
  setup.py                       # the interview + scaffolder (writes OUTSIDE this repo)
  requirements.txt               # one package, for the optional signal steps only
  .gitignore
  workspace.example/             # the tree below, filled in for the example student
  config/
    subreddits.txt               # the rooms the future employer complains in
    keywords.txt                 # the phrases that mean somebody has the problem
  build-in-public/
    weekly-loop.md               # the recurring week, written down
    post-templates.md            # gotchas post, weekly build post, answer-a-question reply
  campus/
    offer.md                     # the one-page offer for a campus org or local business
    outreach.md                  # how to ask, and what to send after they say yes
```

What `python3 setup.py` writes into the student's own repo, and the tree every file in this
pack refers to:

```
<workspace>/                     # the student's repo, outside this kit
  CLAUDE.md                      # points the agent at me/, voice/, and the current week
  me/
    profile.md                   # who they are, what they study, what they have done
    skills.md                    # what they can do today, rated 1-4 on evidence
    gaps.md                      # what they cannot do yet. The important one.
    target-roles.md              # the roles and companies they want, and why
  signals/
    config/subreddits.txt        # the rooms where their future employer complains
    config/keywords.txt          # the phrases that mean somebody has that problem
  projects/
    week-01-<slug>/
      README.md                  # problem / input / output / result
      gotchas.md                 # this project's log
      transcript.txt             # added after the first recording. Committed; it is
                                 # the voice sample.
  clients/
    <org-slug>.md                # the real user, the real problem, the number
  voice/
    core-voice.md                # extracted from their own transcripts
  portfolio/README.md            # the index a hiring manager reads first
  status.md                      # what week they are on, what shipped, what is next
  .gitignore                     # data/, *.csv, .env*, recordings/, .gtm-setup.json, *.bak
  .gtm-setup.json                # the interview answers, so --redo can re-ask one section
                                 # without losing the rest. Gitignored.
```

The week-01 folder and the client file are named from the first organization on their reachable
list ("the student consulting club" gives `projects/week-01-student-consulting-club/` and
`clients/student-consulting-club.md`), falling back to `first-client` when that answer is empty.
The signal lists are copied out of this pack's `config/`, so the workspace starts from a working
list rather than an empty file.

Raw recordings live in `recordings/week-NN/` and are gitignored, because the files are too
large for a repo. The transcript is what gets committed, and it sits with its project.

## The eight modules

The workflow below runs these in order the first time, then repeats steps 6 through 10 weekly.

- **M1 The knowledge base is a folder of files.** Who they are, what they study, what they can do, where the gaps are, who they want to sell to. They write it raw, you structure it. Their codebase becomes their knowledge base.
- **M2 Build in public, and keep a gotchas log.** Ship the unpolished version. The gotchas format (what broke, what they caught) is the highest-trust and lowest-friction thing a beginner can publish honestly.
- **M3 LinkedIn for the personal brand, GitHub for the technical portfolio.** In GTM roles today, the engineering is the part that gets read.
- **M4 A weekly project, recorded and clipped.** One recording of the whole build session produces the long video, the clips, and the transcript that becomes the voice profile.
- **M5 Use the network you already have.** Campus organizations and local businesses are real clients with real problems. One delivered automation beats ten personal projects.
- **M6 Research the buyer, then answer them.** Read the rooms, answer questions, do not pitch.
- **M7 Get to inbound.** Publishing is the mechanism that makes people come to them.
- **M8 Read the market you are entering.** Titles do not define them, skills do. Judge a startup by whether it solves a real problem and whether the founders did the buyer research.

## Workflow

1. **Confirm the prerequisite.** They need a coding agent running and a terminal they can use. If they have never opened one, stop and send them to first-boot. Do not re-teach terminal basics inside this skill, and do not scaffold a workspace they cannot navigate.

2. **Run the interview (M1).** `python3 setup.py`, or `python3 setup.py --out ~/<their-repo>` to pick the path up front. It asks eight questions: their name as it should read on the portfolio page, school and year, what they are studying, what they can do today, where the gaps are, the kind of company they want to work for, the campus organizations or local businesses they can reach this week, and their GitHub handle. Each one has a bracketed default that Enter accepts. Tell them to answer in plain sentences, because resume language structures badly.

   The other flags: `--force` overwrites a target that already has files in it, `--redo <section>` re-asks one section and rewrites only that section's files (backing each one up to `<name>.bak` first, and using the answers already on file as the defaults), `--non-interactive` fills every answer with the example student, and `--no-git` skips the git step. The sections are `profile`, `target-roles`, and `portfolio`, and `python3 setup.py --help` prints the current list.

   The interview does not collect three job titles or twenty target companies. Those go into `me/target-roles.md` by hand, after a week of reading the market. Say so plainly rather than letting them wait for a question that is not coming.

3. **Structure what they wrote, do not replace it (M1).** Read `me/profile.md`, `me/skills.md`, `me/gaps.md`, and `me/target-roles.md` back to them, tighten the wording, and keep their facts and their phrasing. Rate skills on evidence: a 3 needs a commit behind it. Let `gaps.md` stay honest, because an agent that thinks they are fluent hands them code they cannot defend in an interview. A profile you wrote from scratch is a profile they cannot defend either.

4. **Push the repo.** `setup.py` already ran `git init` and made the first commit, so this step is the remote only: empty public repo on GitHub, `git remote add origin`, `git push -u origin main`. That commit is the first public artifact and it should exist before any project starts. If setup.py reported that git was missing or that the commit failed, fix that here before moving on.

5. **Write the offer before touching the signal config (M6).** `setup.py` has already written `signals/config/subreddits.txt` and `signals/config/keywords.txt` from this pack's lists. Re-pointing them at the market that hires them means describing what they are aiming at it: a name, a one-liner, selling points, and competitors. That is a positioning exercise and it is the highest-value first rep in the pack, because saying what something does, for whom, in one sentence a stranger understands, is the skill the job is made of. Here the student is the product.

   Have them study two real offers first, both public and both checkable: **ChatGPT** ("an assistant you talk to in plain language, and it writes, explains, and works through problems with you," competing with Claude, Gemini, Copilot, and a search engine plus your own reading time) and **Cal AI** ("point your phone camera at a plate of food and it logs the calories," competing with MyFitnessPal, Lose It, and a paper notebook, and known at all because a teenager built it publicly while it grew). Both have a one-liner a stranger gets on the first read, and selling points that are checkable facts.

   Then interview them for their own, one question at a time, and push back on anything they have not actually done. Every selling point needs a commit, a link, a date, or a named organization behind it. If they reach for an adjective, ask what evidence makes it true, and cut it when there is none. Two rules to give them out loud: say it out loud first and then type what they said, because the spoken version is always clearer; and no adjective they cannot prove. "Detail-oriented" means nothing. "I hand it back inside a week, working, with a README" means something. Write the result into `me/target-roles.md` under an Offer heading, in their words.

6. **Pick the week's project, client first (M5).** Prefer a real problem at a campus organization or a local business over a personal toy. If they have one, open `campus/offer.md` and `campus/outreach.md` and get the ask sent this week. Write `projects/week-NN-<slug>/README.md` before any code, in the problem / input / output / result shape, and log the organization in `clients/<org-slug>.md`.

7. **Record the build (M4).** The screen recording runs for the whole build session, however long that session is. It is not a separate 40-minute task on top of the build. They press record before opening the editor and stop when the thing works, narrating as they go, and they check the audio input before the take. Afterward they publish either the full session or the best 30 to 40 minutes of it, and the transcript of the whole thing lands at `projects/week-NN-<slug>/transcript.txt`. One file, three uses.

8. **Ship and log (M2).** Commit with a README a stranger could follow, then write `projects/week-NN-<slug>/gotchas.md` the same day. Every entry is a dated H3 with five bolded fields, newest at the top of the file:

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

   **Caught** is load-bearing and never optional. It is the record of them checking their own work, which is the thing the format exists to demonstrate. Never rewrite an old entry.

9. **Publish on both surfaces (M3).** The gotchas post goes to LinkedIn from `build-in-public/post-templates.md` with the repo linked. The code and its README go to GitHub. Same week, same work, two audiences.

10. **Answer in the rooms (M6, M7).** Time in `signals/config/subreddits.txt` matching `signals/config/keywords.txt`, on Monday, before the week's project gets picked. Answer the question in full, link only when the link is the answer. Track which posts produced a reply, a follow, or a message, and let that steer the next week's topic. Inbound is the goal, and it arrives as somebody else starting the conversation.

11. **Close the week (M1 again).** Saturday, fifteen minutes: update `me/skills.md` and `me/gaps.md` from what actually happened, and update `status.md` with the week number, what shipped, and what is next. A gap that closed moves up with the commit that closed it.

12. **Evaluate the target list out loud (M8).** When they get interest, walk `me/target-roles.md` company by company: does it solve a problem somebody pays for, and did the founders do the buyer research. Titles at that stage mean very little, and the skills stack they just built in public is the part that transfers.

13. **Hand off the clipping.** The recordings pile up. `starters/podcast-shorts/` turns them into transcript-anchored vertical clips. It ships on its own branch, so if the folder is absent, say so plainly and tell them to keep recording.

## The weekly cadence

The one table. It matches `build-in-public/weekly-loop.md` and the README, so quote it rather than inventing a schedule per student.

| Day | The work | Time | What goes public |
|-----|----------|------|------------------|
| Mon | Read the signal queue, answer one thread, pick the week's project from what you read | 30 min | One real answer in a thread |
| Tue | Confirm the client, write `projects/week-NN-<slug>/README.md` before any code | 30 min | Commit the brief |
| Wed | Build it, screen recording running the whole session | 2-5 h | Nothing yet |
| Thu | Ship it to the person who asked. Write `gotchas.md` the same day | 1 h | Repo push, README, gotchas |
| Fri | Cut clips from Wednesday, publish | 1 h | Long video, 2-3 clips, one post |
| Sat | Update `me/skills.md` and `me/gaps.md` from what actually happened | 15 min | Nothing |
| Sun | Off | | |

Total 5 to 8 hours a week. If a student is spending more, the week's project was scoped too big; cut it until it fits one sitting.

## Gotchas

- `setup.py` writes the workspace wherever it is pointed, and it does no checking of that path beyond refusing a non-empty directory without `--force`. There is no guard that keeps it inside the student's home directory, so pass the path deliberately: `--out ~/<their-repo>`. Never scaffold a student's workspace inside `gtm-coding-agent/`, and never commit their workspace back to this repo.
- Real client data (member lists, signups, contact records) stays out of the public portfolio repo. Commit the script, commit a sample row that was made up, and gitignore the rest. The generated `.gitignore` already excludes `data/`, `*.csv`, `.env*`, `recordings/`, `.gtm-setup.json`, and `*.bak`.
- No API keys anywhere in the workspace. Everything reads from `os.environ`. A leaked key in a public student repo is the kind of gotcha that does not belong in the gotchas log.
- Do not write the profile or the offer for them. Structure, tighten, and ask follow-up questions. The interview is the point of M1, and an agent-authored profile fails the first phone screen.
- `gotchas.md` gets written the day it happens, newest entry on top, with the **Caught** field filled in. A student who waits until the post is polished ends the week with an empty file and nothing to publish.
- A silent recording costs the video, the clips, and the transcript at once. Verify the audio device before the take, every take.
- One delivered project with a named organization outranks a stack of personal repos, so bias every scheduling decision toward the week that produces a real user, and log that user in `clients/`.
- The weekly loop only compounds if it repeats. Three shipped weeks in a row beats one polished month, and the repo history is what proves the cadence.
