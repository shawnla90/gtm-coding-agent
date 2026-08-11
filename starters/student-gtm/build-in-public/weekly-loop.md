# The Weekly Loop

**One project a week, built for somebody who asked for it. Record yourself doing
it once. That single recording becomes a long video, two or three clips, a
written post, and an update to your voice profile. The work you were already
going to do is the content. You are not adding a content job on top of a build
job, you are recording the build job.**

Part of the [Student GTM starter](../README.md). This is Module 4 turned into a
schedule you can actually run with classes. The reasoning is
[Chapter 21](../../../chapters/21-student-gtm.md), and the same week in mode form
is [`modes/student.md`](../../../modes/student.md).

Prerequisite: Claude Code is installed and you can commit to a repo. If that is
not true yet, start at [first-boot](https://github.com/shawnla90/first-boot),
finish it, then come back here. This loop assumes the terminal is behind you.

---

## The loop

```
Mon   read the signal queue    ──►  answer one thread for real
      pick the week's project  ──►  from what you just read, not from a tutorial
Tue   confirm the client       ──►  one person is waiting on it
      write the brief          ──►  projects/week-NN-<slug>/README.md, before any code
Wed   record while you build   ──►  the whole session, recorder on start to finish
Thu   ship it to the client    ──►  they can run it without you
      write the gotchas entry  ──►  projects/week-NN-<slug>/gotchas.md, same day
Fri   ship the long cut        ──►  YouTube (unlisted week 1, public by week 3)
      clip the recording       ──►  starters/podcast-shorts (Ch 20)  ──►  2-3 clips
      mine the transcript      ──►  the week's written post
                               └──►  voice/core-voice.md update
Sat   update me/skills.md and me/gaps.md from what actually happened
Sun   off
```

One delivered project and one recording. The long video, the clips, the written
post, and the voice update all come out of that single file, which is why
Wednesday is the only day that cannot be rescheduled.

---

## The time budget

| Day | The work | Time | What goes public |
|-----|----------|------|------------------|
| Mon | Read the signal queue, answer one thread, pick the week's project from what you read | 30 min | One real answer in a thread |
| Tue | Confirm the client, write `projects/week-NN-<slug>/README.md` before any code | 30 min | Commit the brief |
| Wed | Build it, screen recording running the whole session | 2-5 h | Nothing yet |
| Thu | Ship it to the person who asked. Write `gotchas.md` the same day | 1 h | Repo push, README, gotchas |
| Fri | Cut clips from Wednesday, publish | 1 h | Long video, 2-3 clips, one post |
| Sat | Update `me/skills.md` and `me/gaps.md` from what actually happened | 15 min | Nothing |
| Sun | Off | | |

**Total 5 to 8 hours a week,** and the range is Wednesday. Everything outside
Wednesday is fixed and short.

The recording runs for the **whole** build session, however long that session is.
You then publish either the full session or the best 30 to 40 minutes of it. It
is not a separate 40-minute recording task sitting on top of a build. That
distinction is the reason this fits around a full course load, and it is the
reason people quit in week three when they get it wrong.

It also does not fit if you try to make the video good. Do not try to make the
video good.

---

## Step 1. Read the queue, answer one thread, pick the project (Mon, 30 min)

Use `config/subreddits.txt` and `config/keywords.txt` as human reading and
offer-research notes. Configure the matching Clearbox offer, then use
`starters/reddit-buyer-signals/` ([Chapter 18](../../../chapters/18-reddit-buyer-signals.md))
to score the complete classified export so your thirty minutes goes to threads
that are live.

Two things come out of that half hour.

**One answer, posted.** Pick the thread where you actually know something and
answer it. The whole answer goes in the comment. No link, no pitch, no "happy to
DM." You have nothing to sell, which is the advantage: you are free to just be
useful in a room full of the people who hire.

**The week's project.** Pick it from what you just read rather than from a
tutorial list. A student building off a tutorial builds things nobody needs. A
student building off a live complaint builds things that map to a job
description.

Then write one sentence with a finish line in it. Present tense, specific
object, observable outcome.

Sam, a business student at a state university, week 3:

> The campus marketing club's event signup CSV gets deduped and pushed into
> their mailing list automatically, so nobody hand-cleans it before an event.

Three rules for the sentence:

1. **Finishable in one Wednesday.** Two to five hours of real work. If it needs
   two sittings, it is two weeks.
2. **It produces an artifact.** A repo, a script that runs, a sheet that
   populates. Something with a URL at the end.
3. **It serves someone other than you.** A club, a local shop, a student org.
   See [`../campus/offer.md`](../campus/offer.md) for how to find one. A project
   with a real user survives contact with reality, and reality is what makes the
   recording worth watching.

If the sentence takes more than three lines to write, the scope is wrong. Cut it
until it fits.

---

## Step 2. Confirm the client, write the brief (Tue, 30 min)

Message the person and get the yes before you build anything. The scoping
conversation and the one-page scope contract are in
[`../campus/offer.md`](../campus/offer.md), and the whole point of doing it on
Tuesday is that their answers change what you build on Wednesday. Watch them do
the chore once if they will let you. The description is always cleaner than the
chore.

Then write the brief and commit it, before any code:

```
projects/week-03-rsvp-dedupe/README.md
```

Four things in it, in this order:

```markdown
# rsvp-dedupe

**Problem:** the marketing club's event signup CSV gets hand-cleaned before
every event. 400 rows, twice a month, about 45 minutes each time.
**Input:** the signup export (one CSV)
**Output:** a deduped list plus a flagged-rows tab for the ones a human has to
look at
**Result:** [fill this in Thursday, with the number]
```

Committing the brief before the build is not paperwork. It is the thing that
keeps Wednesday from turning into a four-hour scope negotiation with yourself,
and it is the file a hiring manager reads first when they open the repo.

---

## Step 3. Record while you build (Wed, 2-5 h)

Screen recording with your mic on. QuickTime works. OBS works and is free on
every platform. 1080p is plenty.

What you are recording is you doing the work, thinking out loud. It is not a
tutorial. Nobody is expecting production value from a student, and the version
where you try for production value takes six hours and gets fewer views than the
honest one.

How to talk for a couple of hours without a script:

- **Narrate the intent before every action.** "I am going to point this at the
  CSV and see what the column headers look like." Then do it. Then say what
  happened.
- **Say the error out loud.** When something throws, read the message. That
  sentence becomes a clip and a post, and you get it for free by reading a
  screen.
- **Keep the failures in.** The moment it breaks is the moment the recording
  earns attention. A video where everything works is a video nobody finishes.
- **One take.** Do not restart when you fumble. Restarting is how a two-hour
  build turns into a five-hour afternoon.
- **If you are stuck past ten minutes, say so and take the workaround.** Stuck,
  then unstuck, is the entire genre. Stuck for 25 silent minutes is not.

Two practical things that cost a whole week when skipped:

- Record 10 seconds, play it back, confirm you can hear yourself. Audio you
  cannot hear is a wasted week and there is no fixing it after.
- Keep a paper list of timestamps as you go. When something interesting happens,
  write the clock time on paper. Three seconds each. It saves twenty minutes of
  scrubbing on Friday.

---

## Step 4. Ship it, then write the gotchas entry (Thu, 1 h)

Two deliveries happen on Thursday, and the second one is the one students skip.

### Deliver it to the person who asked (30 min)

The build is done when they can run it without you in the room. Four things,
none optional, and all four are in
[`../campus/offer.md`](../campus/offer.md) under the handoff:

- A README with the exact commands, written for someone who has never opened a
  terminal.
- Keys from the environment, never in the file.
- A short recorded walkthrough of them running it. You already have the recorder
  set up.
- An off switch and a person, which is you, for thirty days.

Then fill in the **Result** line of `projects/week-NN-<slug>/README.md` with the
number, push the repo, and tell them it is live. If the number did not move, put
that in the Result line. An honest zero is a stronger artifact than a vague win.

### Write the gotchas entry the same day (30 min)

Same day, while it is fresh. Wednesday's failures are gone by Sunday, and the
reconstructed version reads like a summary because it is one.

One file per project at `projects/week-NN-<slug>/gotchas.md`, newest entry at the
top, five fields every time:

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

**Caught** is never optional and it is never "nothing." It is the record of you
checking your own work before it reached a real person, and it is the field a
hiring manager reads twice. If you genuinely caught nothing, the honest entry is
what you would check next time and why you did not check it this time.

---

## Step 5. Ship the long cut (Fri, 10 min)

Friday is one hour, hands-on, and it is four small things. This is the first.

Upload the raw file. The entire edit is: cut the dead air at the front, cut the
fumbling at the back where you reach for the stop button. That is it.

If the session ran long, publish the best 30 to 40 minutes instead of all of it.
Pick the stretch with the break and the fix in it. Do not re-record anything.

- **Title with the outcome and the surprise.** "Deduping a 400-row club signup
  sheet, and the trailing space that broke it." A title with a specific number
  and a specific failure gets clicked. A title that says "Building an automation
  (Week 3)" does not.
- **Description carries the goal sentence, the repo link, and the timestamp
  where it broke.** Three lines.
- **Unlisted is fine for week 1 and 2.** Public from week 3. The point of the
  first two is to get the muscle, and knowing it is unlisted is what gets a
  nervous person to press record at all.

---

## Step 6. Hand the recording to the clipper (Fri, 15 min)

The clipping pipeline is the sibling starter at `starters/podcast-shorts`
(Chapter 20). It transcribes with word-level timestamps, cuts on word
boundaries so clips never start mid-syllable, and renders vertical with burned-in
captions.

That starter ships on its own branch, so if the folder is not in your checkout
yet, keep recording anyway and clip the backlog when it lands. Read its README
for its own setup. This loop only cares about what goes in and what comes out.

**What you hand it:** the raw recording file, plus the 3 to 5 timestamps you
wrote on paper during the build.

**What you ask for:** 2 or 3 clips, 30 to 60 seconds each.

**What makes a clip work:** it stands alone. Someone who never saw the long cut
has to understand it. The reliable shape is the moment it broke, the fix, and one
sentence on why it broke. Skip installs, skip setup, skip the part where you read
documentation.

Fifteen minutes is your attention, not the runtime. The transcription and the
render take longer and they do not need you in the chair, so start it and go do
something else.

Review the output before you touch anything else. Caption timing drift is the
failure that ships if you are not watching for it.

---

## Step 7. Publish the clips (Fri, 15 min)

- Watch each clip end to end. Every one. This is the step people skip and it is
  the step that catches a clip ending mid-word.
- One clip native to LinkedIn, one to X, and the third to YouTube Shorts when
  there is a third.
- Native upload, always. A link to a video gets a fraction of the distribution
  of the same video uploaded directly.
- The caption on the post is the first line of the written post you are about to
  write in the next twenty minutes. Same idea, shorter. You are not writing it
  twice.

---

## Step 8. Mine the transcript twice (Fri, 20 min)

The clipper leaves a transcript behind. Save it next to the project as
`projects/week-NN-<slug>/transcript.txt` and commit it. The raw video stays in
`recordings/week-NN/`, which is gitignored, because the repo is the wrong home
for a multi-gigabyte file.

That transcript does two separate jobs, and running both is what makes this loop
compound instead of just repeat.

### Pass one: the week's written post (15 min)

```
Read projects/week-03-rsvp-dedupe/transcript.txt.

Pull out:
1. Every moment something broke, with what the error actually said.
2. What I tried first that did not work.
3. The fix, and why it worked.
4. Any sentence where I explained a concept in my own words.

Draft a gotcha post from #1 and #3 using the format in
build-in-public/post-templates.md. Use my words from the transcript wherever
they exist. Do not smooth them out.
```

Then edit it yourself. The draft is raw material. You are the one who decides
what shipped and what is true, and a 10-minute edit pass is the difference
between a post that reads like you and a post that reads like a machine
summarizing you.

### Pass two: update your voice profile (5 min)

One prompt, chained straight after the first one. You are reading the output, not
writing it.

```
Read projects/week-03-rsvp-dedupe/transcript.txt and voice/core-voice.md.

From the transcript, extract:
- Phrases I used more than once
- My average sentence length when I am explaining something
- How I open an explanation, and how I close one
- Words I reach for when something goes wrong
- Anything I say that a generic writing assistant would never produce

Append these to voice/core-voice.md under a dated heading. Do not delete or
rewrite anything already in the file.
```

Append, do not overwrite. Once a month, ask the agent to consolidate the dated
sections into a single profile and keep the raw appendix underneath.

---

## Step 9. Update skills and gaps (Sat, 15 min)

Fifteen minutes, nothing publishes, and it is the step that keeps the agent
useful in week nine.

Move anything you actually did this week into `me/skills.md` with the evidence
attached: the project folder, the commit, the client. Rate on evidence rather
than on exposure, 1 for read about it and 4 for shipped it for someone else.
Then rewrite `me/gaps.md` around what this week showed you cannot do yet. The
gap you hit on Wednesday is the truest thing you will write all week, and next
Monday's project should aim at it.

```
Read projects/week-03-rsvp-dedupe/README.md and gotchas.md, then update
me/skills.md and me/gaps.md. Only add a skill if this week produced evidence for
it, and name the evidence. Move anything I clearly could not do into gaps.md and
tell me which gap is blocking the next project.
```

---

## Why the transcript is the artifact that matters

The video gets views. The clips get reach. The transcript is the one that keeps
paying, and it is the one everybody throws away.

A transcript of you working through a problem out loud is the only honest record
of how you actually talk. It has your real sentence lengths. Your filler. The
order you put ideas in when you are thinking rather than performing. The words
you reach for when something breaks at 11pm. None of that survives writing,
because when you write you edit, and editing is where your voice gets sanded
into everyone else's.

This matters for one concrete reason. When you ask an agent to write a post from
a blank prompt, it produces competent, average prose, and everybody who reads it
knows exactly what produced it. When you ask an agent to write a post from a
transcript of you explaining the same thing out loud, it produces your sentences
in a cleaner order. Same tool, different input, completely different result.

Twelve weeks of this and `voice/core-voice.md` is a real asset. It is the thing you
load before writing anything: an application, a cold email, a README, a post.
You cannot buy it and you cannot fake it, because it is a record of you doing
work you actually did.

Keep every transcript. They are a few kilobytes each. Commit them.

---

## What breaks

**You try to make the video good.** The build takes an afternoon and the edit
takes four hours, so week 2 never happens. Trim two ends and upload. That is the
whole edit, permanently.

**You treat the recording as its own task.** It is not 40 minutes of filming
added to the build. It is the build with the recorder running, and the only
decision at the end is whether you publish the whole session or the best 40
minutes of it.

**The audio is unusable.** Ten seconds of test recording prevents it. There is
no recovery after the fact, and it costs the transcript too, which costs the
post and the voice update. One check, every time.

**The project is too big.** You record two hours of a thing that needed twelve,
and there is no finish line on tape. Cut the goal sentence until it fits one
Wednesday. A small finished thing beats a large unfinished one every week of the
year.

**You ship it and never write the gotchas entry.** The client is happy, the code
is pushed, and the one artifact that shows how you work is missing. Thursday is
delivery plus gotchas, in the same hour, or it does not get written.

**You skip Friday.** The clips go out, the post never does, and the written
track record stays empty. The clips get reach; the written posts are what people
read before they decide whether to talk to you. Friday is the step with the
compounding.

**You batch three weeks into one weekend.** The recording is honest because it
is same-day. Reconstructed from memory a week later, it flattens into a summary,
and summaries are the thing nobody watches.

---

## The first four weeks

| Week | Project | Video | Post |
|------|---------|-------|------|
| 1 | The smallest real chore, for an org you already belong to (see `../campus/offer.md`) | Unlisted | Publish it anyway |
| 2 | v2 of week 1, or a second small one for the same org | Unlisted | Publish it |
| 3 | First one for an org you had to ask | Public | Publish it |
| 4 | The next org, from the introduction week 3 gave you | Public | Publish it |

The video goes unlisted for two weeks, not the work. The client is real from
week 1, because the point of the first month is a person waiting on something,
and knowing the video is unlisted is what gets a nervous person to press record
at all.

By week 4 you have four recordings, eight to twelve clips, four written posts, a
repo with four working projects, two organizations that use something you built,
and a voice profile with four weeks of you in it.

That is a track record, and it cost 20 to 30 hours.
