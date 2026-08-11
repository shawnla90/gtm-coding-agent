# Chapter 21: Student GTM

**This chapter is for the college student who wants a go-to-market career and
has no budget, no title, and no portfolio. The advice you get is to apply for
an internship and wait for someone to hand you experience. The alternative is
to build a public track record in one semester, using the same coding agents a
solo operator uses to run an entire GTM stack. The example throughout is Sam,
a business student at a state university with Claude Code running and one free
evening a week. The campus network Sam already has is the first client list,
and the work Sam does for it is the portfolio.**

---

## TL;DR

- **Your knowledge base is a folder of files, not a resume.** Who you are,
  what you can do, where the gaps are, who you want to sell to. The agent
  structures it. Your own codebase becomes the knowledge base as you ship.
- **Ship the unpolished version and keep a gotchas log.** What broke and what
  you caught is the highest-trust and lowest-friction thing a beginner can
  publish honestly.
- **LinkedIn carries the person. GitHub carries the proof.** In GTM roles
  right now, the engineering is what gets you the reply.
- **One recording feeds three artifacts.** Record the whole build session,
  however long it runs. That file is the long video, the clips, and the
  transcript that becomes your voice profile.
- **Point your buyer-signal tooling at the companies you want to be hired by.**
  Same engine as Chapter 18, one config change, and your Monday reading turns
  into interview preparation. Configuring it makes you write your own offer,
  which is the first positioning rep you will get.
- **The campus network is a real client list.** One automation delivered to a
  student organization and written up beats ten personal projects.

---

## The advice you were given

Get an internship. Get the title on the resume. Do the rotation, wait for the
return offer, and in two years you will have experience.

That advice was written when the distance between a student and a working GTM
operator was a stack of seat licenses. You could not enrich a list without a
data vendor, you could not build a dashboard without an engineer, and you could
not write a script without a semester of CS. The only way in was to borrow a
company's tooling by getting hired.

The tooling gap closed. A coding agent, Python, SQLite, and a free tier will
run a real go-to-market loop from a laptop in a dorm. The chapters before this
one are that loop, built for an operator with a company behind them. Nothing in
them requires the company.

What is left is the track record, and that is the actual scarce thing. Hiring
managers are not short on students who list "proficient in Salesforce" on a
resume. They are short on people who can point at something they built, say who
used it, and explain the three decisions inside it. A semester of weekly
projects, published as you go, produces exactly that.

---

## Where this chapter starts

If you have never opened a terminal, this is the wrong chapter to start in.
Go do [first-boot](https://github.com/shawnla90/first-boot) first. It covers
the terminal, git, getting Claude Code running, context engineering, and
shipping something small. It takes a weekend.

This chapter assumes you finished that. You have Claude Code running, you can
make a commit and push it, and you know what a `CLAUDE.md` file is for. From
here the subject is the track record, and none of the terminal basics get
repeated.

Two runnable things sit behind this chapter. `starters/student-gtm/` is the
pack: `python3 setup.py` interviews you, writes the workspace described below to
a path you pick, runs `git init`, and makes the first commit, so the tree exists
before you have to remember what goes in it. `modes/student.md` is the operating
configuration: the stack, the same folder structure, and the first week laid out
day by day. Read this chapter for the reasoning, run the starter, keep the mode
file open while you work.

---

## Your knowledge base is a folder of files

The first build is a folder about you.

It is a set of small markdown files that an agent reads before it helps you
with anything, closer to a config file than to a resume. Chapter 02 makes this
argument for a company's context. It applies harder to a person, because the
person is the thing being sold.

Four files:

```text
me/
  profile.md        # who you are, what you're studying, what you've done
  skills.md         # what you can do today, rated 1-4 on evidence
  gaps.md           # what you can't do yet. The important one.
  target-roles.md   # the roles and companies you want, and why
```

`setup.py` creates the four files and fills what the interview covers. You and
the agent finish them.

You do not write these from scratch. You talk and let the agent structure it.
Open Claude Code in the folder and give it this:

```
I'm a business student building a GTM track record. Interview me, one question
at a time, until you can write four files:

1. profile.md      : who I am, what I'm studying, what I've actually done
2. skills.md       : what I can do today, rated 1-4 (1 = read about it,
                     4 = shipped it for someone else)
3. gaps.md         : what I can't do yet, ordered by what blocks me soonest
4. target-roles.md : the companies and roles I want, and why

Rules: don't inflate anything. If I say I "know Python" ask me what I've
actually built with it and rate it on the evidence, not the claim. Ask about
gaps last and don't let me be vague about them.
```

Twenty minutes of questions produces a better picture of you than a resume you
would have spent a week on, because the agent keeps asking for evidence.

The gaps file is the one students skip, and it is the one that does the work.
An agent that knows you cannot write SQL yet will teach in that gap instead of
handing you a query you cannot defend in an interview. An agent that thinks you
are fluent will skip the explanation, you will ship code you do not understand,
and the first technical question will end the conversation.

The folder is a starting point, and then it stops being a description of you.
Week three, `projects/` has three subfolders with READMEs and commit history.
Week eight, `clients/` has notes on two campus organizations that use something
you wrote. At that point the agent is reading your actual work when it helps
you write a cover letter, prepare for an interview, or decide what to build
next. Your codebase became your knowledge base, which is the same thing that
happens to a company that runs a GTM-OS properly.

---

## Ship the unpolished version, and keep a gotchas log

The instinct is to wait until the thing is good. Every week the project gets
one more refactor and one more feature, and it never goes out.

Ship it Thursday. Whatever state it is in.

Then write the gotchas entry, which is the format that makes this work. One file
per project at `projects/week-NN-<slug>/gotchas.md`, newest entry at the top,
and every entry is a dated heading with the same five fields:

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

Five fields, every time, in that order. The same format is in the mode file and
in the starter, so an agent reading your repo knows the shape without being told.

Three reasons this format is the right one for a beginner.

It is true, so it costs nothing to write and nothing to defend. You are
reporting, and reporting is easy when it happened to you an hour ago.

It requires no authority. A student writing "5 lessons on modern GTM strategy"
is claiming standing they have not earned, and every reader can tell. A student
writing "here is the bug that almost double-emailed 40 people" is claiming
nothing except that it happened. Being new is the qualification for that post
rather than a problem to hide.

And it demonstrates the thing hiring managers actually screen for. The Caught
section is a record of you checking your own work before it hit a real person.
Anybody can write a script. The person who dry-runs it and counts the
recipients first is the person you can put near production.

Which is why the Caught field is never optional. An entry without it is a bug
report. An entry with it is the evidence.

Keep `gotchas.md` in every project folder. At the end of the semester you have
twelve of them, which reads as a log of someone getting better in public.

---

## Two profiles, two jobs

LinkedIn and GitHub do different work, and running them as one thing wastes
both.

**LinkedIn carries the person.** The weekly post, the story of what you built
and who used it, the gotchas entry rewritten for people who do not read code.
This is where a founder or a GTM lead in your target market runs into you.
Chapter 09 covers voice, and the platform section there applies without
modification: short paragraphs, a real hook, personal experience over abstract
advice.

**GitHub carries the proof.** A resume line is a claim. A repo is a dated
record. Commits on Tuesday nights across fourteen weeks say something a bullet
point cannot, and no one has to take your word for any of it.

Make the repos readable, because a hiring manager gives you ninety seconds. A
README that opens with the problem, the input, the output, and the result:

```markdown
# rsvp-reminders

A campus organization tracked event RSVPs in a Google Sheet and sent reminders
by hand. 340 rows, three events a semester, and the reminders went out late.

**Input:** the RSVP sheet (Sheets API, read-only)
**Output:** deduped list, segmented into confirmed / no-show-last-time / new,
plus a drafted reminder email per segment
**Result:** reminders went out 4 days ahead instead of the morning of.
See `gotchas.md` for what broke.

Run it: `python3 remind.py --sheet-id $RSVP_SHEET_ID --dry-run`
```

Name repos after the problem they solve rather than after the technology. A
recruiter scanning your profile understands `rsvp-reminders`. Nobody
understands `python-project-3`.

In GTM roles right now, the engineering is the part that gets a reply. The
market is full of candidates who can describe a campaign. The candidate who
shows up with a repo that pulls a list, scores it, and writes the drafts is
answering a question the team is currently paying someone to solve.

---

## One recording, three artifacts

This is the highest-return habit in the whole chapter, and it costs one click.

Before you start the week's project, hit record. Screen and microphone. Talk
while you work: what you are trying to do, why you picked this approach, what
just broke, what you are about to try. Stop when the project is done. The
recording runs for the whole build session, however long the session takes. It
is not a forty-minute task sitting on top of the build, it is the build with the
recorder on.

That one file becomes three things.

**The long video.** Upload it. Unedited, with the dead ends and the moment you
misread the error message. Publish the full session, or the best thirty to forty
minutes of it when the build ran long. The genre already exists and it works,
because watching somebody solve a problem in real time is more useful than
watching somebody perform a solution they rehearsed.

**The clips.** Two or three vertical cuts, taken from the moments where
something broke or something clicked. Chapter 20 and the
`starters/podcast-shorts/` starter handle this end of it, transcript-anchored
cuts and captions. You feed it the same recording and it gives you the week's
distribution.

**The voice profile.** This is the part people miss, and it solves a problem
students have with Chapter 09. Voice DNA is extracted from your best writing
samples, and a nineteen-year-old does not have five years of LinkedIn posts to
mine. But an hour of talking through a build under real conditions is around
seven thousand words of your actual voice, including how you explain things,
what you say when you are stuck, and the phrases you reach for without thinking.
That is a better sample than anything you would have written on purpose.

Transcribe locally, no key and no upload:

```bash
# whisper runs on your laptop; the audio never leaves it
whisper recordings/week-03/raw.mp4 \
  --model base \
  --output_format txt \
  --output_dir projects/week-03-rsvp-reminders/
```

Two paths, two rules. The raw video stays in `recordings/week-NN/`, which is
gitignored, because a repo is the wrong place for a two-gigabyte file. The
transcript is written next to the project as
`projects/week-NN-<slug>/transcript.txt` and it gets committed, because it is a
few kilobytes and it is your voice sample.

Then hand the transcript to the agent with the extraction prompt from
Chapter 09 and save the result to `voice/core-voice.md`. Re-run it every four
weeks with the new transcripts and the profile sharpens as you do.

One recording. Long-form, short-form, and voice, from a single take. The
economics of that are why the weekly cadence holds up when you have four
classes and a job.

| Day | The work | Time | What goes public |
|-----|----------|------|------------------|
| Mon | Read the signal queue, answer one thread, pick the week's project from what you read | 30 min | One real answer in a thread |
| Tue | Confirm the client, write `projects/week-NN-<slug>/README.md` before any code | 30 min | Commit the brief |
| Wed | Build it, screen recording running the whole session | 2-5 h | Nothing yet |
| Thu | Ship it to the person who asked. Write `gotchas.md` the same day | 1 h | Repo push, README, gotchas |
| Fri | Cut clips from Wednesday, publish | 1 h | Long video, 2-3 clips, one post |
| Sat | Update `me/skills.md` and `me/gaps.md` from what actually happened | 15 min | Nothing |
| Sun | Off | | |

Five to eight hours a week, and the range is Wednesday. Twelve weeks in a
semester. The output is twelve repos, twelve write-ups, twelve videos, and
around thirty clips, all dated, all yours.

---

## Configure the signal engine on the people who hire you

Chapter 18 builds a Reddit buyer-signal engine from a complete Clearbox
opportunity export. It preserves the source disposition and permalink, scores
the buyer language, and shows you the gap. It is written for a company pointed
at its buyers.

Point it at the market you want to be hired into instead, and the same pipeline
becomes a standing brief on your future employer's problems.

Configure a Clearbox offer around the market you want to enter. Give the offer
the communities, buyer language, competitors, pains, and outcomes that define
the people who could hire you. Clearbox returns the classified source records;
the local starter turns them into the working brief.

Use the offer-context interview in ClearboxGTM to research those fields instead
of typing a keyword list from memory.

Run the offline sample first so you can see the shape with no key and no cost:

```bash
cd starters/reddit-buyer-signals
bash run.sh --offline
```

Then export the complete classified inbox and run it locally:

```bash
CLEARBOX_EXPORT=/absolute/path/to/clearbox-opportunities.json bash run.sh
```

### Write your own offer while you are in there

The offer context aims the engine at a market. The downstream competitor and
visibility work takes a brand and the names it is up against. Configuring the
engine makes you write an offer: a name, a one-liner, the selling points, and
the competitors.

Do that exercise with yourself as the product. It is the highest-value first rep
in this whole chapter, because saying what a thing does, for whom, in one
sentence a stranger understands is the skill the job is made of. Every campaign,
landing page, and cold email is downstream of that one sentence.

Read two real ones before you write yours. Both are public, so you can check
them.

**ChatGPT.** One-liner: an AI assistant you type at in plain language. Selling
points: answers questions, drafts and edits writing, writes code, reads files you
hand it. Competitors: Claude, Gemini, Perplexity. Nothing there is clever, and a
stranger knows from one line what they would use it for.

**Cal AI.** Built and shipped in public by a high school student who posted the
revenue as it moved. One-liner: point your phone at a plate and it logs the
calories. Selling points: a photo instead of a search box, macros per meal, works
on food you cooked yourself. Competitors: MyFitnessPal, Lose It. A student wrote
that positioning, and it is the same exercise you are about to do.

Then yours:

```text
Name:           what you call the thing you ship every week
One-liner:      I build ______ for ______ so they can ______.
Selling points: three, each with a number or an artifact behind it
Competitors:    who else is applying for the job you want, and what you have
                that they do not
```

Two rules, and they do the work.

**Say it out loud first, then type what you said.** The spoken version is always
clearer, because a vague sentence has nowhere to hide when somebody is listening
to it.

**No adjective you cannot prove.** "Detail-oriented" means nothing and every
applicant writes it. "I hand it back inside a week, working, with a README a
non-technical person can follow" means something, and the repo is right there to
check.

Then have the agent take it apart:

```
Interview me on this offer, one question at a time. For every selling point, ask
me what I actually did that proves it and who saw it. Cut anything I cannot point
at. If a line would be equally true of any other student in my major, say so and
make me replace it.
```

Redo it at week six. By then the selling points have numbers in them, and the
one-liner gets shorter, because you finally know which part people care about.

### What the Monday read buys you

Thirty minutes on Monday reading that output does two jobs at once.

The first is the obvious one. You learn the actual problem list of the teams
you want to join, in the words the people with the problem use, updated weekly.
When an interviewer asks what you think their biggest go-to-market problem is,
you have thirty days of their buyers answering that question, and you can name
the phrasing those buyers use. That answer separates you from every candidate
who read the company's homepage the night before.

The second job is that it tells you what to build. A student picking projects
from a tutorial list builds things nobody needs. A student picking projects
from a live feed of operator complaints builds things that map to a job
description. Your Wednesday project comes off Monday's read.

And then answer the questions. Chapter 18's guardrails hold here exactly as
written: recent threads only, sincere replies, and value in the comment itself.
A student has nothing to pitch, which turns out to be an advantage. You are
free to just answer, and answering well in public where operators are reading
is how a nineteen-year-old ends up in a DM with a founder.

---

## The campus network is a client list

Every campus organization is a small business with an operations problem and
zero budget for software.

A student club with a 400-person mailing list maintained by hand. A fraternity
tracking a recruitment funnel in a group chat. A student-run consulting group
with a sponsorship pipeline living in one senior's inbox. A campus radio
station whose scheduling spreadsheet breaks every time someone drops a shift.
The coffee shop two blocks off campus with three hundred unanswered Google
reviews.

These are real users with real problems and real deadlines, and they will say
yes immediately, because the alternative is doing it by hand again.

Sam's week three: the events chair of a student organization keeps RSVPs in a
Google Sheet and sends reminder emails manually the morning of each event. Sam
writes about sixty lines of Python that read the sheet, normalize and dedupe
the emails, split the list into confirmed, no-show-last-time, and first-timer,
and draft a different reminder for each segment. It runs Wednesday night. The
events chair sends the drafts Thursday.

Write down the number before and the number after. If attendance moved, that is
a case study with a client, a mechanism, and a result. If it did not move, the
gotchas log is still the artifact, and "it did not move attendance, here is what
I would test next" is a more credible post than anything that worked on the
first try.

One automation delivered to somebody who actually needed it beats ten personal
projects, and the reason is narrow. A personal project proves you can write
code. A delivered automation proves your code survived contact with a person
who did not care how it worked, who used it wrong, whose data was messy, and
who came back with a change request. That is the entire job.

Asking is one paragraph, sent in the group chat you are already in:

> You track RSVPs in a sheet, right? I'll write something that dedupes the list
> and drafts the reminders by segment. Free, takes me an evening, and I want to
> write up what I learn from it. If it works you keep it. If it breaks I fix it.

No proposal, no deck, no invoice. You are buying a case study with an evening
of your time, and both sides know it, which is why it is an easy yes.

---

## Publishing is how you stop applying

The outbound available to a student is weak. A cold email from a .edu address
with no track record behind it competes with every other cold email that lands
in a founder's inbox, and it has less to say than any of them.

Publishing reverses the direction. Every gotchas post, every repo, every clip
is a piece of surface area sitting in the places your future employer already
reads. Inbound for a student looks specific: a founder replying to a comment
you left, a GTM lead asking who wrote the script in the video, a DM about a
small paid project, a hiring manager who read three of your posts before the
interview and opens with a question about week seven.

The arithmetic is not complicated. Twelve weeks, twelve write-ups, twelve
videos, around thirty clips, and a repo trail with dates on it. Somebody in your
target market reads one of them. That is the whole mechanism, and it beats any
sequence you could run, because you cannot run a sequence that makes a stranger
trust you and publishing twelve honest build logs does.

The order matters. Build for a real user, write what broke, publish it, then
repeat. Publishing without the build is a countdown post. The build without the
publishing is a private hobby.

---

## Reading the market you are entering

Two things to keep straight while you do this.

**Titles do not define you, skills do.** GTM titles are unstable and mean
different things at different companies. Growth, RevOps, GTM engineer, demand
gen, marketing ops, and biz ops can all describe the same daily work. Chasing a
title means optimizing for a label that changes when you switch companies.
Track skills instead, in `me/skills.md`, rated on evidence: can you pull a list,
enrich it, score it, write to it, measure it, and explain every step. Those
transfer to every title in the category.

**Evaluate the company on two questions.** Does it solve a real problem, and
did the founders do the buyer research. The first one you assess by whether
anybody is paying and whether they would be upset if it disappeared. The second
one you can check yourself, for free, with the engine you already configured.

Read the company's site, then read the threads where its buyers talk. Compare
the language. If the site says "unified workflow orchestration for revenue
teams" and the buyers in those threads are saying "our reps forget to log
calls", the founders wrote positioning from a whiteboard. If the site's headline
uses the same phrase the buyers use, somebody did the work.

That comparison tells you something about the company you would be joining, and
it is also the best question you can bring to an interview. "I read thirty days
of threads in your category and the phrase that comes up over and over is X.
How do you think about that?" No student asks that question. Ask it.

---

## The line on schoolwork

Worth stating plainly, because the boundary is easy to get wrong in either
direction.

Use the agent for the work around the coursework. Research, summarizing
material you already read, building study tools, scheduling, cleaning up your
own notes, learning to code, and everything you build for clubs, clients, and
your own repos. That is the entire subject of this chapter and there is nothing
questionable about any of it.

Keep it out of graded work. Two reasons, and the second is the one that
actually matters.

The first is that it violates the academic integrity policy at your school, and
getting caught takes the transcript and the track record down together. A year
of weekly projects is worth a lot, and it is worth less than nothing attached to
an academic integrity finding.

The second is that it makes you worse at the thing you are claiming to be good
at. The entire value of the portfolio is that you can defend every line of it in
a room. Somebody who let an agent write their marketing analytics assignment
skipped the reps that would have made them fast at the actual job. The interview
finds that out in about four minutes.

One test: is this output being graded? If yes, keep the agent out of it. If the
work is for a club, a client, a repo, or your own learning, use everything.

---

## Anti-patterns

- **Polishing week one for three weeks.** The unpolished shipped thing beats
  the perfect unshipped one, every time, and the gotchas log turns rough edges
  into content.
- **Building for an imaginary user.** A project with no user is a coding
  exercise. Find one person who will use it before you start.
- **Posting about learning instead of shipping.** "Day 14 of learning Python"
  is a countdown. A gotchas entry from a real build is evidence.
- **Shipping a repo you cannot explain.** If you cannot walk an interviewer
  through why a function exists, it is not portfolio, it is a liability.
- **Pitching in threads.** Answer the question and stop. The Chapter 18
  guardrails apply: recent threads only, real value in the comment.
- **Hoarding the recording.** The unedited session with the dead ends in it is
  the content. Publish it, or the best forty minutes of it.
- **Chasing the title.** Take the role where you touch the whole loop over the
  role with the better label and a narrow scope.
- **Committing secrets.** Every credential from the environment. `data/`,
  `*.csv`, `recordings/`, and `.env*` belong in `.gitignore` before the first
  commit, not after. `setup.py` writes that file for you on the way in.
- **Rebuilding the repo instead of using it.** The starters in this kit already
  run. Configure them and spend the evening on the client's problem.

---

## Exercise: your first week

Do this over the next seven days. It fits around a full course load.

1. **Run the starter, then fill in `me/`.** `cd starters/student-gtm` and
   `python3 setup.py`. It interviews you, writes the workspace to a path you
   pick, runs `git init`, and makes the first commit. Then use the interview
   prompt above to finish `me/profile.md`, `me/skills.md`, `me/gaps.md`, and
   `me/target-roles.md`. Be honest in `gaps.md` or the rest of it stops working.
2. **Configure the signal engine and write your own offer.** Use
   `signals/config/subreddits.txt` and `signals/config/keywords.txt` as human
   reading and offer-research notes, configure the matching Clearbox offer,
   then run `starters/reddit-buyer-signals/run.sh --offline` to inspect the
   source contract. Write the four-line offer with yourself as the product.
3. **Ask one campus organization for one problem.** Send the paragraph. Take
   whatever they say yes to, even if it sounds too small.
4. **Build it on Wednesday with the recording running.** Screen and mic, the
   whole session, talking the whole time.
5. **Ship it Thursday and write the gotchas entry.** All five fields. Caught is
   the one that matters.
6. **Transcribe the recording and extract your voice profile.** Local whisper,
   transcript committed at `projects/week-01-<slug>/transcript.txt`, the
   Chapter 09 prompt, result saved to `voice/core-voice.md`.
7. **Publish on Friday.** The repo with a real README, the long video, and one
   LinkedIn post that tells what broke.

At the end of the week you have one client, one repo, one video, one voice
profile, and one honest post. Repeat it eleven more times and you have a
semester nobody can argue with.

---

## Key Takeaways

- A student's constraint is a track record, not tooling. The tooling is
  already free and already in this repo.
- Structure yourself as files first. `profile.md`, `skills.md`, `gaps.md`, and
  `target-roles.md` make every later agent session better, and the gaps file
  matters more than the skills file.
- The gotchas log is the format built for a beginner. It is true, it is short,
  it needs no authority, and the Caught section is the thing hiring managers
  are screening for.
- One recording per week is the long video, the clips, and the voice profile.
  Press record before you build, and leave it running for the whole session.
- Point the buyer-signal engine at the companies you want to work for. Your
  Monday reading becomes both your project queue and your interview prep, and
  configuring it makes you write your own offer in four lines.
- The campus network is a client list. One delivered automation with a real
  user beats ten personal projects.
- Publishing is the mechanism that makes people come to you, and it is the only
  distribution a student has that actually works.
- Keep the agent out of graded work. Everything around the coursework is fair
  game and that is where the portfolio comes from anyway.

---

**Starter:** [`starters/student-gtm/`](../starters/student-gtm/) is the runnable
pack. `python3 setup.py` interviews you and builds the workspace this chapter
describes, as your own repo with the first commit already made.

**Mode:** [`modes/student.md`](../modes/student.md) has the stack, the same
folder structure, and the first week day by day.
