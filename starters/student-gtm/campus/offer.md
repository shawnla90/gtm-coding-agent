# The One-Automation Offer

**One organization. One recurring chore. Gone in a week. Free the first time.
That is the entire offer, and it is the fastest way a student with no title gets
a real user, a real deadline, and something to write up that actually happened.**

Part of the [Student GTM starter](../README.md). This is Module 5. The reasoning
is [Chapter 21](../../../chapters/21-student-gtm.md), the week it fits into is
[`../build-in-public/weekly-loop.md`](../build-in-public/weekly-loop.md), and the
mode is [`modes/student.md`](../../../modes/student.md).

Before you write an offer for an organization, write one for yourself. Name,
one-liner, selling points, competitors, with you as the product. That exercise is
in Chapter 21, it takes twenty minutes, and every conversation below goes better
once you can say what you do in one sentence a stranger understands.

Ten personal projects sitting in a repo are ten things you decided to build. One
automation running inside an organization is a thing somebody else uses on a
Tuesday because it saves them 45 minutes. Those two are not close in value, and
the second one is easier to get than students think, because campus
organizations are drowning in manual chores and have nobody to hand them to.

---

## Why a campus organization is a real client

A student marketing club, a consulting group, a fraternity, an intramural
league, a maker space, a campus paper. Every one of them has:

- **A recurring operational chore** somebody hates doing.
- **A real deadline**, because the event is on the 14th whether the list is
  clean or not.
- **A person accountable** for it, usually a VP of something who is a junior
  with too much on their plate.
- **Zero budget and zero technical help**, which is why the chore is still
  manual after four years of it existing.

That is a client. The size of the organization does not change the shape of the
work. The thing you build for a 60-person club is structurally the same thing a
30-person company needs, which is why the write-up transfers.

Local businesses next to campus work the same way. A coffee shop, a gym, a
tutoring service. Same chores, same absence of anyone to fix them.

---

## What to offer

Offer to remove one recurring chore. Name it, and say you will take it off their
plate. The offer lands when the chore is specific and has a finish line, because
the officer can picture their Sunday evening without it.

Four that reliably exist, with what shipping looks like:

### 1. Event signup handling

**The chore today:** the signup form exports to CSV. Somebody opens it in
Sheets, deletes duplicates by eye, fixes the names people typed in all caps,
pastes the result into the mailing tool, then does it again for the reminder
email. About 45 minutes, twice a month.

**What you build:** a script that reads the export, normalizes and dedupes on
email, flags the rows a human needs to look at instead of silently dropping
them, and pushes the clean list to the mailing tool.

**Done looks like:** the comms lead runs one command and the list is in the
tool. Build time: 2 to 3 hours, one Wednesday.

**What makes it hard:** the messy rows. Missing last names, two people sharing
an email, someone who typed their phone number in the email field. Flag them,
never drop them.

### 2. Member roster hygiene

**The chore today:** membership lives in four places. A spreadsheet from the
involvement portal, a group chat, a dues tracker, and whatever the previous
officer left behind. Nobody knows who is actually active, so dues chasing goes
to people who graduated.

**What you build:** one script that reads all four sources, matches people
across them, and outputs a single roster with a status column and a conflicts
tab listing every person the sources disagree about.

**Done looks like:** one sheet, refreshed by running one command, with the
disagreements visible instead of hidden. Build time: 4 to 5 hours, one Wednesday.

**What makes it hard:** matching people without a shared key. Name matching is
where you will spend the time, and the conflicts tab is what makes the tool
trustworthy instead of a black box.

### 3. A weekly digest

**The chore today:** the president writes a weekly update by scrolling four
channels, a shared calendar, and their own memory, then posts it late on Sunday
or forgets.

**What you build:** a script that reads the calendar for the coming week, pulls
open items from wherever they track them, formats it as one message, and posts
it to their group chat or emails it. Scheduled, or run by hand on Sunday.

**Done looks like:** the digest arrives without anybody writing it. Build time:
2 to 4 hours, one Wednesday.

**What makes it hard:** the formatting and the tone. It has to read like a
person wrote it or people stop reading it by week three. This is a good one to
run through your `voice/core-voice.md` work.

### 4. Sponsor research

**The chore today:** an event needs sponsors. Somebody spends an evening
searching local businesses, copying names into a doc, hunting for a contact
form, and re-contacting three places that already said no last year.

**What you build:** a list-building script. Pull businesses by category near
campus, dedupe against last year's list, find the contact page or email, and
output a sheet with a suggested first line for each one based on what the
business actually does.

**Done looks like:** a 60-row sheet with contacts and a first line, built in
four minutes instead of four hours. Build time: 4 to 5 hours, one Wednesday. If
your scope needs more than five, cut it until it fits the session.

**What makes it hard:** nothing technical. This is straight go-to-market work,
which is exactly why it is the best one on this list to have on your record.

---

## How to scope it so it ships in a week

Scope is the whole game. A student who scopes correctly ships every week. A
student who scopes ambitiously ships in March.

The week it has to fit is the one in
[`../build-in-public/weekly-loop.md`](../build-in-public/weekly-loop.md):
scoped on Tuesday, built on Wednesday in one recorded session of two to five
hours, delivered on Thursday. Anything that does not fit that shape is either a
smaller v1 or somebody else's project.

### The scoping conversation, 20 minutes on Tuesday

Do this before you write anything. Four questions, in order:

1. **"Walk me through the last time you did this."** Ask them to share their
   screen and actually do it. Do not accept a description. The description is
   always cleaner than the chore.
2. **"How long did it take, and how often does it happen?"** You want two
   numbers. They become the headline of the write-up.
3. **"What happens when it goes wrong?"** This is where the real requirement
   lives. Duplicate emails, wrong person charged dues, a sponsor contacted
   twice.
4. **"Who else touches this?"** If the answer is three people, you have a
   handoff problem, not a script problem, and v1 gets smaller.

### The scope contract

Write this down and send it to them before you start. One page.

```
CHORE: [the specific thing, in their words]
HAPPENS: [how often] · TAKES: [how long] · OWNER: [name of the role, not a person]

INPUT:   [exactly one file or one source]
OUTPUT:  [exactly one artifact]
TRIGGER: [one person runs one command]

DONE WHEN:
  [the owner runs it themselves, once, without me in the room]

NOT IN V1:
  [list 4 things you are deliberately leaving out]

DATE: [seven days from today]
```

**One input, one output, one owner, one week.** Every one of those is a hard
constraint, and every one of them is what somebody will try to talk you out of
in the second meeting.

### What v1 leaves out, every time

- **Hosting or scheduling.** It runs on your machine or theirs, by hand. A
  scheduled version needs somewhere to live and that is v2.
- **A user interface.** The terminal is the interface. If they cannot run a
  command, you record a 90-second video showing them.
- **A second integration.** One source in, one destination out. The second
  destination doubles the surface area and triples the debugging.
- **Historical backfill.** Fix it going forward. The archive is a separate
  project.
- **Permissions and roles.** One person runs it. When two people need it, that
  is a good problem and it is v2.

Say these out loud when you agree the scope. Naming the exclusions is what makes
the one-week deadline believable, and it is the thing that makes an officer
trust you more, not less.

---

## How to price it

**The first one is free. Say the word "first" when you offer it.**

> "I'll build it for free. It's the first one I'm doing for an organization on
> campus, and I want a real one on my record."

That sentence does four things at once, and it is honest, which is why it works.

### Why free is the right call as a student

- **You have no track record, so the price is the risk discount.** Nobody is
  weighing your $200 against your portfolio, because there is no portfolio yet.
  Free removes the entire evaluation.
- **It collapses the sales cycle to one conversation.** A student organization
  with a budget has a treasurer, a vote, and a semester calendar. Two hundred
  dollars costs three weeks of waiting. Zero dollars costs one yes from the
  person who has the chore.
- **You are buying something more valuable than the money.** A real user, a real
  deadline, a written case with two real numbers in it, and a reference who will
  answer their phone. At this stage those are worth multiples of what you could
  charge.
- **It gives both sides an exit.** If it goes badly, they lost nothing and you
  owe nothing. That freedom is what lets you scope aggressively and ship fast.

### Free once, run like work

Free is a price, and it says nothing about how you run the job. Same scope contract, same deadline, same handoff, same
follow-up. The reason this works on a resume is that you ran it like work. An
unpaid thing you did sloppily is worth less than nothing, because it is the
version people remember.

### The second one

Charge. Not because the first one was worth zero, but because you now have a
case, and a case is what converts a price into a yes.

How to set the number without agonizing:

- **Hours saved per month, times a number they would pay a person, times three
  months.** Forty-five minutes twice a month at $20 an hour is $30 a month, so
  roughly $90 for the quarter. That is small, and small is correct for a campus
  org.
- **For a local business, $250 to $750 for a one-week build.** They have a bank
  account and a real cost of the chore, and that range does not require anyone
  to think hard.
- **Campus orgs can stay free or trade.** A trade is fine: a table at their
  event, a post from their account, a slot at their meeting to show what you
  built. Distribution is a currency and they have it.

Your third one has two cases and a video. That is when the number starts moving.

---

## What to ask for in return

Free is not free. You ask for two things, and you ask for them up front, at the
same time you offer the build. Asking after it works looks like a bill.

### 1. Permission to write it up publicly

Be specific about what you want to publish, because vagueness makes people say
no:

> "In return, I want to write up how I built it and post it publicly. That means
> the problem, my approach, the code, and how long the chore used to take. No
> member data, no emails, no names. I'll show you the post before it goes up."

What that permission covers:

- The problem in plain terms and the two numbers (time per run, runs per month)
- Your approach and your code, in a public repo
- Screenshots with real data replaced by sample data
- The recording of you building it, which is the weekly loop

What is off the table, permanently:

- Member names, emails, phone numbers, dues status, anything from the roster
- Anything in a screenshot you did not replace with sample data
- The organization's internal disagreements

Get the yes in writing. A text message is writing. Then honor the "I'll show you
the post" part, every time, before it goes up. That one habit is why the second
organization says yes.

### 2. One introduction to another organization

Ask for it at the moment it works, not at the end of the semester. The moment is
when they run it themselves for the first time and it does the thing.

> "This is the part where I ask for the favor. Do you know one other org or one
> business nearby with a chore like this? An intro is worth more to me than
> getting paid for this."

One introduction. Not "keep me in mind," not "let me know if anybody needs
anything." A name, and an offer for them to send the message.

Two organizations in October is four in November. That is the entire growth
mechanism and it costs one sentence.

---

## The handoff

The build is done when they can run it without you. Four things, none of them
optional:

1. **A README with the exact commands.** Copy-pasteable. Written for the person
   who has never opened a terminal, because that is who they are.
2. **Keys in environment variables, never in the file.** If the tool needs an
   API key, it reads it from the environment and the README says how to set it.
   A key committed to a public repo is a bad week for both of you.
3. **A 5-minute recorded walkthrough.** You are already recording yourself
   build. Record five more minutes at the end showing the owner running it.
   That video is the handoff, the training, and a clip.
4. **An off switch and a person.** Tell them exactly what to do if it does the
   wrong thing (stop running it, nothing is automatic, nothing is destroyed) and
   that you will fix things for 30 days.

### Their data stays out of your repo

The public repo gets the code and sample data you made up. Their actual export
goes in a `data/` folder that is in `.gitignore` before you download the first
file. Do this on the day you start, not the day you publish.

---

## What breaks

**You built what they said instead of what they do.** They described a clean
process, you automated the clean process, and the real one has three exceptions.
Watch them do it. Always watch them do it.

**Scope grew in the second meeting.** Somebody said "could it also" and you said
yes. "That's v2, and I'll build v2 after this one works" is a complete sentence
and it keeps the deadline.

**You disappeared for eight days.** A week means a week. If you are going to
miss, send a message on day five saying what is done and what is left. Missing
silently is the only unrecoverable mistake here.

**You waited to be paid and got nothing at all.** The first one is free on
purpose. Take the case study.

**You never wrote it up.** This is the common one. The automation ships, the org
is happy, and there is no public record that any of it happened, so it does not
exist to anybody who was not in the room. The write-up is the deliverable. See
[`../build-in-public/post-templates.md`](../build-in-public/post-templates.md),
build log template.

**You asked for the introduction too late.** Enthusiasm has a half-life of about
four days. Ask on the day it works.
