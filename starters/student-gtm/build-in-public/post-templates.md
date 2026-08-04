# Post Templates

**Three shapes that work when you have no title, no track record, and no
portfolio. Every one of them runs on the same fuel: a specific thing that
happened to you this week, written down with the details left in. Pick a
template, fill it from your transcript, edit it yourself, publish it.**

Part of the [Student GTM starter](../README.md). These are the written half of
the [weekly loop](weekly-loop.md).

---

## Which one, and how often

| Template | Cadence | Effort | What it earns you |
|----------|---------|--------|-------------------|
| Gotcha post | Weekly, the default | 30 min | Trust. People believe someone who shows the break. |
| Build log | Every finished project | 45 min | Evidence you ship, with a link |
| Teardown | Every 3 to 4 weeks | 3 hours | Attention from the teams you want to work for |

Run gotchas as the baseline. They are the lowest-friction honest thing a
beginner can publish, because you already have the material and it requires zero
claims about your expertise. Add a build log when a project finishes. Save the
teardown for when you have something real to say about a buyer room you have
actually been reading.

**Rules that apply to all three:**

- Specific numbers, always. "400 rows" beats "a lot of rows."
- Paste the real error text. The exact string is what makes it credible.
- Link the repo or the video. A post with no artifact is an opinion.
- Write from the transcript, then edit it in your own hands. The draft is raw
  material, you are the editor.
- One idea per post. If you have two, that is next week's post.

---

## Template 1: The gotcha post

The default weekly post. Something broke, you figured out why, here is the fix.
That is the whole thing.

This works for a beginner better than any other format because it makes no claim
about your seniority. You are reporting an event, and events are checkable.
Somebody with fifteen years of experience reading it either learns something or
recognizes the bug, and both reactions are good for you.

**Platform fit:** LinkedIn primary. The entry itself already lives in
`projects/week-NN-<slug>/gotchas.md`, written the day it broke, so the post is a
rewrite of something you have rather than a thing you sit down to invent. Across a
semester those per-project logs are the page to send someone who asks what you have
been doing.

**Length:** 120 to 200 words on LinkedIn. Two to five sentences in the repo file.

### The shape

```
[What broke, in one line, with the specific thing that broke]

[What I expected to happen]

[What actually happened, with the real error or the real symptom]

[Why it happened. The actual root cause, not the symptom.]

[The fix, specific enough to be useful]

[One line of what I will check for next time]
```

### Filled example

```
Spent 40 minutes on a dedupe that "worked" and still left 38 duplicate rows in a
400-row event signup sheet.

I was matching signups on email. Clean, unique key, done in one line.

Except the count kept coming back wrong. Same person, three rows, three
different events, all still there after the dedupe.

The emails were not identical. Some had a trailing space from the form export,
some were capitalized differently because people type their own address
differently every time. "Sam.Rivera@example.edu " and "sam.rivera@example.edu"
are two different strings to Python and one person to a human being.

Fix was one line:

    df["email"] = df["email"].str.strip().str.lower()

38 duplicates collapsed. The club's mailing list dropped from 412 to 374, which
means they had been paying for 38 phantom contacts and emailing at least a few
people three times per campaign.

Now I normalize every join key before I join on it. Strip, lowercase, then
compare. Every time, even when I am sure the data is clean.

Repo: github.com/[you]/campus-signups
```

### What makes it fail

- **Vagueness.** "Had some issues with data quality" is a post nobody finishes.
  The trailing space is the post.
- **Making yourself the hero.** The bug is the subject. You are the person who
  reported it.
- **Padding it with a lesson.** One line at the end is enough. Three paragraphs
  about how this taught you the importance of attention to detail turns a good
  post into a bad one.
- **Posting a gotcha that is not yours.** If you read it somewhere, it is not a
  gotcha, it is a link.
- **Hiding that it took you 40 minutes.** The time cost is the part that makes
  other people feel seen.

---

## Template 2: The build log

What you set out to do, what you actually shipped, and what you would do
differently. Written when a project is finished, or finished enough to be used
by someone.

The build log is where you get to show scope judgment, which is the thing that
separates a student who can code from a student who can be handed work. Anybody
can list what they built. The "what I would do differently" section is the part
a hiring manager reads twice.

**Platform fit:** the project repo README first, because that is the permanent
copy. Then a condensed version on LinkedIn linking back to it. A blog if you
keep one.

**Length:** 300 to 500 words in the README. 150 on LinkedIn with the link.

### The shape

```
[The one-sentence goal I started with, quoted from when I started]

WHAT I SET OUT TO DO
[The problem, whose problem it was, and what it cost them before]

WHAT I SHIPPED
[The actual thing. What it does, what it runs on, how it gets triggered,
who uses it. Link it.]

WHAT IT TOOK
[Honest time. Honest count of things that broke.]

WHAT I WOULD DO DIFFERENTLY
[Two or three real ones. Scope, tool choice, sequencing.]

WHAT IS STILL BROKEN
[The known limitations. Say them before someone finds them.]
```

### Filled example

```
Goal I wrote on Monday: "The campus marketing club's event signup CSV gets
deduped and pushed into their mailing list automatically, so nobody hand-cleans
it before an event."

WHAT I SET OUT TO DO
The club runs about two events a month. Every time, whoever is on comms exports
the signup form to CSV, opens it in Sheets, hand-deletes duplicates, and pastes
the result into the mailing tool. It takes roughly 45 minutes and it happened 20
times last year. Two people told me they had emailed the same person three times
in one week and did not know why.

WHAT I SHIPPED
A 90-line Python script that reads the form export, normalizes and dedupes on
email, flags rows with missing names for a human to look at instead of silently
dropping them, and pushes the clean list to their mailing tool over its API. It
runs from the terminal with one command. The club's comms lead runs it herself.

WHAT IT TOOK
About 3 hours across two sittings. Four things broke. The dedupe that did not
dedupe (trailing whitespace), an API key I put in the wrong environment
variable, a rate limit I did not read about until I hit it, and a first version
that dropped 11 rows silently because they had no last name.

WHAT I WOULD DO DIFFERENTLY
1. I built the mailing-tool push before I had the dedupe right, so I was
   debugging two systems at once. Get one clean output to a CSV first, then wire
   the destination.
2. I asked for the CSV instead of asking to watch someone do the chore. Watching
   would have surfaced the missing-name case in the first five minutes.
3. I scoped it as "automate the list" when the real scope was "stop emailing
   people three times." The second framing would have gotten me to the flag
   behavior faster.

WHAT IS STILL BROKEN
It runs on my machine, on purpose, because a scheduled version needs somewhere
to live and the club has nowhere to put it yet. If I leave, someone has to run
it. That is the next version.

Repo: github.com/[you]/campus-signups
Walkthrough video: [link]
```

### What makes it fail

- **Listing features.** Nobody cares what it does. They care what it removed
  from someone's week.
- **A "what I would do differently" that is fake modesty.** "I would have added
  more tests" is not a real one. Scope and sequencing mistakes are real ones.
- **Hiding the limitations.** Saying what is still broken is what makes the rest
  of the post believable.
- **No link.** A build log without a repo is a claim.
- **Inflating the time.** If it took 3 hours, say 3 hours. The people you want
  reading this can estimate, and being right about small numbers is how they
  decide to trust your big ones.

---

## Template 3: The teardown

You read a large number of threads in one room where your future employer
complains, and you name the pattern running underneath them.

This is the post that gets a student read by the teams they want to join. A
gotcha post proves you are honest. A build log proves you ship. A teardown proves
you understand a market well enough to say something about it that the people
inside it have not put into words. That last one is the actual job in go-to-market,
and it is the only one of the three where a student can compete on equal footing
with someone who has a title, because reading carefully is available to anybody
willing to spend three hours.

**Platform fit:** LinkedIn primary, as a standalone post with the data at the
top. An X thread as the secondary cut, one finding per post. Do not post it in
the community you sourced it from unless you can contribute it as a genuine
answer to something being asked, and even then, link nothing.

**Length:** 400 to 600 words. The numbers go in the first two lines.

### How to do the reading

1. **Pick one room, not five.** One subreddit, one Slack, one forum. A pattern
   across five rooms is a survey. A pattern inside one room is a finding.
2. **Read 50 to 100 threads.** Fewer than 50 and you are pattern-matching on
   noise. Set a timer, three hours.
3. **Log every thread in a sheet as you go:** link, the stated problem, the
   problem underneath it, what they tried, what they blamed. Five columns.
4. **Ask your agent to cluster the sheet.** It will find the frequency counts.
   You decide which cluster matters, because the interesting one is usually the
   third biggest, not the biggest.
5. **Write the finding people are not saying out loud,** and show the count that
   supports it.

### The shape

```
[The number, the room, and the timeframe, in one line]

[The thing everybody in the room says the problem is]

[The thing the threads actually describe, with the count]

[Two or three quotes or paraphrases that show it]

[Why the gap exists. This is the paragraph that gets you read.]

[What that means for anyone selling into this room]

[What I am doing with this]
```

### Filled example

```
I read 63 threads in one revenue-operations community over the last four months
and logged what each one was actually about.

Everybody in that room describes their problem as CRM data quality. That phrase
or a close version of it shows up in 41 of the 63.

But when you read what happened rather than what they called it, 38 of those 41
describe a breakage at a handoff. The record was fine when the first person
owned it. It broke when it moved to the second person, because the second
person needed a field the first person was never asked to fill in.

The pattern in the threads:

- "The account was clean until it got routed" (some version of this, 22 threads)
- Fields that exist for one team and are dead weight for the other (17)
- A rule that fires on stage change and overwrites what the previous owner typed
  (9)

The gap is in the naming. Data quality sounds like a hygiene problem, so it gets
solved with hygiene tools: validation rules, required fields, a quarterly
cleanup, an enrichment vendor. Those tools all operate on the record. But the
threads describe an ownership problem, where the record is a symptom and the
handoff is the event. Nobody buys "handoff software" because that category does
not exist, so they buy the hygiene tool, it does not fix the handoff, and six
months later the same person posts the same thread with a different vendor name
in it.

If you sell into this room, the demo that lands is not the one that shows a
clean record. It is the one that shows what happens at the moment the record
changes hands, and who is accountable for the fields that appear at that moment.

I am building a small script that logs every ownership change on a record and
diffs the fields before and after. It is week one and it barely works. The sheet
with all 63 threads is public, take it: [link]

Method: [link to how I logged them]
```

### What makes it fail

- **A number you did not actually count.** If you read 12 threads, the post says
  12. Somebody will ask for the sheet, and the sheet is the whole asset.
- **No sheet.** Publish the raw log. It is more valuable than the post and it is
  the thing that gets shared onward.
- **Naming a company or a person from the threads.** Quote the pattern,
  paraphrase the language, credit nobody by name. You are describing a room, not
  reporting on individuals.
- **A finding that is already the consensus.** If the room already says it, you
  summarized, you did not find anything. Go back to the third-biggest cluster.
- **Turning it into a pitch.** The moment there is a call to action for your own
  thing, the credibility drains out. The last line is what you are building
  because you found this, and it is fine for that thing to barely work.
- **Doing it in a room you do not read.** A teardown of a community you visited
  once reads exactly like what it is.
