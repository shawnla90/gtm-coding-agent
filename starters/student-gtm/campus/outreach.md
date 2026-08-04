# Building the Campus List

**Twenty rows, built by hand in an afternoon, from four sources where people
published their contact details on purpose. This is the list that gets you your
first three organizations, and it is the version that goes on a resume.**

Part of the [Student GTM starter](../README.md). Pair it with
[`offer.md`](offer.md), which is what you are reaching out about.

A mass scrape of the student directory is technically easy and it is the wrong
tool for this job. It gets the account cut off, it puts your name in front of the
office that handles complaints instead of the officer with the chore, and it
produces four thousand people who never asked to hear from you and will not
answer. The list that works is small and assembled from places where somebody
deliberately published a contact so that people would use it. That distinction is
the whole method, and it takes one afternoon.

---

## Source 1: student organization officers

Nearly every campus runs an involvement portal where registered organizations
list what they do, when they meet, and how to reach their officers. Engage,
Presence, CampusGroups, or something homegrown on the student-life site. Officer
contact details are on those pages because the point of the page is that people
can reach the organization.

**How to read the listings.** You are looking for organizations that have
recurring operational chores, which means:

- **They run events.** Events mean signups, reminders, rosters, and sponsors.
- **Thirty members or more.** Under thirty, one person holds it all in their head
  and there is nothing to automate yet.
- **Active in the last 60 days.** A page last updated two years ago is a dead org.
- **Categories that skew operational:** business and marketing clubs, professional
  fraternities, entrepreneurship groups, student government, club sports leagues,
  campus media, and the large service organizations that run recurring drives.

**Who to write to.** The person with the operational title, not the president.
VP of operations, communications chair, membership chair, treasurer. The
president delegates the chore. The chair does the chore at 11pm on a Sunday and
is the one who will answer a message about it.

**Do this pass by hand.** Twenty organizations is about 45 minutes of clicking,
and reading each page is how you write a first line that is actually about them.
If the urge to write a scraper is strong, point it at the sponsor research job in
[`offer.md`](offer.md) instead. That one belongs in a public repo. This one
belongs in a sheet.

---

## Source 2: the campus subreddit, the student Discords, the group Slacks

Every campus has a subreddit and a handful of student-run Discord servers. Many
individual organizations run their own server, and the `#officers` or `#general`
channel is where the chore gets complained about in real time. That complaint is
a better qualifier than anything on the portal.

**Read for a week before you post anything.** You are looking for the shape of
the question people ask: how to make a form do something, how to get a
spreadsheet to stop breaking, how to schedule a recurring message. Answer those
with the actual answer, no link, no pitch. Three good answers make the next thing
you post land differently.

**Then post once.** One post, per semester, in each place:

> I'm building one free automation a week for campus orgs this semester. Last
> week: deduping event signups for a club that was hand-cleaning a 400-row CSV
> before every event. Here's the write-up [link]. If your org has a chore like
> that, reply or DM me.

One post. Reposting it weekly is the thing that gets you muted, and the
write-ups you publish are already doing the repeating for you.

---

## Source 3: professors and career-center staff

These people field "how does a student get real experience" every single week,
which means they already keep a mental list of organizations and businesses that
need help. You are asking them to say one name out loud.

**Who is worth ten minutes:**

- The professor who teaches the operations, analytics, or marketing-technology
  course. They know which student groups run real processes.
- The career center's employer-relations person. Their entire job is knowing
  local employers.
- Whoever runs the entrepreneurship center or the student incubator.
- The staff member in the involvement or student-activities office. They talk to
  every organization on campus, every semester.

**Go to office hours in person, and bring the thing you built.** Ten minutes,
laptop open, show the working script and the write-up. Then two questions:

1. **"Is there one organization or one local business you'd point me at?"** One.
   Specific. A named thing they can say in a sentence.
2. **"What do students ask you for that you never have a good answer to?"** This
   one is research, not outreach. The answer tells you what to build next, and it
   is usually more useful than the introduction.

---

## Source 4: an opt-in page

Every video and every post creates a small amount of interest that lasts about a
day. Without somewhere to put it, that interest evaporates and you start from
zero next week. A one-page opt-in turns a clip view into a row in your sheet, and
rows accumulate while you are in class.

**What is on it:**

- One sentence on what you do: "I build one free automation a week for campus
  organizations and local businesses."
- The last three things you built, with links.
- One form: email, plus a dropdown (student org / local business / just
  following along).
- The honest availability line: "Next open week: [date]."

**Where the link lives:** LinkedIn featured section, GitHub profile README, X
bio, the last line of every build log, the description of every video, and your
email signature.

**What you do with it:** ten minutes every Friday. New rows get a reply within 24
hours, because a reply on day one converts and a reply on day nine does not.

**Do not build this as a project.** A form tool, a one-page site, a Notion page.
Twenty minutes, permanently. The temptation to make the opt-in page the week's
build is real and it is a trap, because it serves nobody but you.

---

## The list schema

One sheet, twenty rows to start. These columns and no more:

| Column | What goes in it |
|--------|-----------------|
| `org` | Organization or business name |
| `type` | student org / local business / referral |
| `size` | Members or employees, roughly |
| `likely_chore` | The specific chore you think they have, in one line |
| `role` | The operational title you are writing to |
| `source` | involvement portal / discord / professor intro / opt-in |
| `sent` | Date of first message |
| `reply` | yes / no / date |
| `status` | no reply / talking / scoped / building / shipped |
| `next` | The one next action, with a date |

`likely_chore` is the column that does the work. If you cannot fill it from
reading their page, you are not ready to write to them, and the message you would
send is the generic one that gets ignored.

**Keep this sheet local.** It has contact details in it that people published for
a purpose, and that purpose was not your repo. Add it to `.gitignore` before you
create it. If somebody asks to be removed, remove the row that day.

---

## The first message

Lead with the chore. The first line names something somebody in their
organization does by hand, specific enough that they know you read the page.
Your major and your coursework belong in the signature, if anywhere at all.

### The shape

```
Line 1  The chore, specific to them, as a question.
Line 2  What you would do about it, one sentence, with a time number.
Line 3  Proof. One link to something you already shipped.
Line 4  The ask. Small, specific, this week.
```

Four lines. On LinkedIn or Instagram DM, that is already long. In email, it looks
like a person wrote it.

### Filled example, student organization

```
Subject: your event signup list

Hi [name],

Quick question about the club's event signups. Does someone still clean that CSV
by hand before each email goes out, or did you find a way around it?

I write scripts that dedupe and push that kind of list automatically. Usually
takes me a few hours to build and saves whoever's doing it about 45 minutes an
event.

I did this for another org on campus last month, write-up and code here: [link]

I'm doing one of these free a week this semester and I have next week open. Worth
15 minutes to see if it fits?

Sam
```

### Filled example, local business

```
Subject: the Tuesday inventory sheet

Hi [name],

I've been in on Tuesdays and I've watched someone re-key the delivery sheet into
the POS by hand. Is that a weekly thing?

I build small scripts that take that kind of re-keying off a person's plate. This
one looks like about a two-hour build.

Last one I did was for a campus org: [link to the write-up]

First one I do for a business is free because I want a case study out of it. 15
minutes this week?

Sam
```

### What makes it fail

- **Opening with yourself.** "I'm a junior studying business and I'm passionate
  about go-to-market" is where they stop reading. Nobody has a problem you solve
  by being a junior.
- **Asking for time to learn about them.** "15 minutes to hear about what you do"
  is a request for a favor. "15 minutes to see if this fits" is a request about a
  chore they already hate.
- **The same message twenty times with the name swapped.** The `likely_chore`
  line has to come from their actual page or their actual Discord, and if it does
  not, it reads exactly like what it is.
- **Attaching a resume.** The link to a working thing does the job a resume is
  pretending to do.
- **No link.** Without proof you are a stranger asking for time.
- **Writing to the president.** Write to the person doing the chore.

### The follow-up

One. Seven days later. It has to carry new information, which means the thing you
shipped in the meantime:

```
Hi [name], following up on this. Shipped one for [other org] this week, it's
here: [link]. Still have the week of the [date] open if the signup thing is worth
15 minutes. If it's not a fit, all good, I'll stop here.
```

Then stop. Two messages, both useful, both easy to say no to. That is the whole
sequence.

---

## The rule of thumb

**Twenty well-chosen campus contacts beat forty thousand cold ones.**

Twenty rows where you read the page, named the chore, and wrote four specific
lines will get you two to five real conversations and one or two builds. That is
a semester of real work and two write-ups.

Forty thousand scraped addresses get you a suspended account and nothing to show
anybody.

The second thing that matters here: only one of these versions can go on a
resume, in an interview answer, or in a portfolio.

> Built and shipped free automations for 6 campus organizations over one
> semester. Sourced them by hand from the involvement portal and two referrals,
> scoped each to a one-week build, published the code and the write-up for every
> one.

That is a paragraph a hiring manager can ask five real questions about, and you
have five real answers. Nobody has ever written the other version down.

---

## The weekly cadence

This is not a separate week. It rides inside the canonical one in
[`weekly-loop.md`](../build-in-public/weekly-loop.md), in the gaps the loop already
leaves:

| When | Time | What |
|------|------|------|
| Mon, after the signal read | 20 min | Send 5 first messages, and follow up on anything sent 7 days ago. Log the dates. |
| Tue, while writing the brief | 10 min | Add 5 new rows. Fill `likely_chore` from their actual page. |
| Fri, after publishing | 10 min | Work the opt-in inbox. Reply to everything. |

About 40 minutes, folded into days that are already in your week rather than added
on top of them, and Sunday stays off. It depends on the loop running, because the
loop is producing the proof links this outreach points at. Neither one works well without the other. The
outreach gets you the projects, the projects get you the write-ups, the write-ups
are what make the next outreach get answered.
