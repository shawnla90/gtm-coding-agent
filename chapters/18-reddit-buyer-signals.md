# Chapter 18: Reddit Buyer Signals

**This chapter is for founders, GTM engineers, and operators who want to
show up when their buyers ask AI which tool to pick. The play is simple:
pull the recent Reddit conversations where buyers compare the tools you
compete with, score them into a content plan, and publish the pages the
models will cite. You connect Google over the CLI, pull only live threads,
build a color-coded scored sheet, and hand a deck to whoever needs to see
the gap. The example throughout is a project-management SaaS for small
teams. Point it at your own market by editing two config files.**

---

## TL;DR

- **AI reads Reddit, so your buyers' questions live there.** When someone
  asks an assistant "Asana or Monday for a small team," the model answers
  from threads it has read. Be in those threads or be invisible.
- **Recency is the whole guardrail.** Pull only the last 30 days. Fresh
  threads are what models weight, and engaging live conversations is the
  sincere way to earn a mention. Dredging up old threads gets you banned.
- **Score the plan, do not guess it.** Rank every topic 1 to 5 on intent,
  demand, competitive fit, and how widely the threads are read. Publish the
  A-tier first.
- **Two data sources, honestly.** A keyword pull via RapidAPI is a free
  baseline. Clearbox classifies by real buying intent instead of keywords.
  Same pipeline, better input.
- **It is an engine, not a one-off.** Re-run weekly. New threads flow in,
  topics re-score, the plan stays current.

---

## Why this works

Your buyers have changed how they shop. Before they open your site, before
they ask a peer, a lot of them ask an AI assistant. "Best project management
tool for a small team." "ClickUp or Notion." "What are people switching to
from Trello."

The model does not make those answers up. It answers from what it has read,
and it has read Reddit. The buyer talk on r/projectmanagement,
r/smallbusiness, and r/startups is training and retrieval fuel. The tool that
answers the question in public becomes the default recommendation.

Right now, for many categories, nobody has claimed that spot. The comparison
threads are full of buyers weighing your competitors, and your product is not
in the conversation, so the model has nothing of yours to cite.

Two things make a thread worth engaging: it is recent, and it is relevant.
Recent, because a live thread with a few hundred interactions is already
high-read and is the one that surfaces in an answer. Relevant, because a
keyword search drags in careers, gaming, and politics threads that share a
word but not a buyer.

And the move is not to spam. It is to comment sincerely, add real value, and
publish the pages that answer the question better than anyone else. You earn
the citation. You do not automate your way to it.

---

## The loop

The whole thing is five steps, plus an optional deck.

1. **Connect Google Workspace.** One-time OAuth so the builder can write
   Sheets and Slides as you. This is the step copy-paste prompt guides skip,
   and the reason a borrowed script fails on the first run.
2. **Pull recent threads.** Only the last 30 days, filtered for relevance on
   the way into a local SQLite database. Two sources to choose from.
3. **Mine the buyer language.** Pull the real questions, comparisons, and
   pains out of titles, bodies, and comments, then cluster them into topics.
4. **Score and build the sheet.** Rank every topic 1 to 5, then render it as
   a color-coded Google Sheet: score gradient, tier colors, a dashboard, all
   shared and rebuildable in place.
5. **Build the deck.** An editable Google Slides deck, built from the same
   scored data, for the meeting where you show the gap.

The runnable version of this loop is the `reddit-buyer-signals` starter in
this repo. Clone it, run `bash run.sh --offline` to see the whole thing work
on bundled sample data with no key, then run it live with your own.

---

## The data contract

Point the engine at your market by editing configuration, not code. Two text
files and two Python maps.

The subreddits and keywords are plain lists:

```text
# config/subreddits.txt
projectmanagement
smallbusiness
startups
Notion
clickup

# config/keywords.txt
asana vs monday
clickup vs notion
best project management tool for small team
trello alternative
```

The vocabulary that decides what counts as a buyer signal lives in one file:

```python
# lib/relevance.py
BRANDS = ["asana", "monday.com", "trello", "clickup", "notion", "jira", ...]

TOPIC_KEYWORDS = {
    "kanban-boards": ["kanban", "board view", "swimlane"],
    "free-vs-paid": ["free plan", "pricing", "per seat", "too expensive"],
    "switching-tools": ["switching from", "migrate", "alternative to"],
}

CATEGORY = ["project management", "kanban", "gantt", "sprint", "backlog", ...]
```

And the scoring is four transparent dimensions summed to a number:

```python
# score.py
# search intent (0-35) + buyer-talk volume (0-25)
# + brand fit (0-18) + citation potential (0-15) = 0-100
# 85+ = 5 (A tier, publish first) ... <40 = 1 (D tier)
CARRIED = ("asana", "monday.com", "trello", "clickup", "notion", "jira", ...)
```

The rule is the same one from every other chapter in this repo: if the value
lives in a small structured file, a coding agent can read it, reason about
it, and help you edit it. A paragraph of instructions cannot be scored.
Everything flows through SQLite, so each stage is idempotent. Re-score
without re-pulling, rebuild the sheet without re-mining.

---

## The Reddit gotcha

Recency is not a setting. It is the guardrail that keeps the whole play
honest, and it works in two directions at once.

The pull only keeps threads from the last 30 days. Nothing older enters the
database. On the retrieval side, that is what AI models want: current, active
conversations, not a forum post from three years ago that no longer reflects
how the tools compare. On the behavior side, it is what keeps you from
getting banned. The way to grow on Reddit is to show up in discussions that
are actually happening and add something real. If your engagement strategy is
digging up old threads to drop a link, moderators catch it, and the community
catches it, and you are done. Recent-only forces you into live conversations,
which is the only place a sincere mention is even possible.

The other gotcha is the source. There are two, and the difference is honest:

- **RapidAPI** runs keyword searches and subreddit pulls. It is a free
  baseline, good enough to see the gap and build the first version. It
  matches on keywords, so it finds the conversations a keyword can find:
  some noise gets through, and some real intent gets missed because the buyer
  did not phrase it the way you searched.
- **Clearbox** classifies Reddit by real buying intent instead of keywords,
  off real content consumption, and adds sentiment and competitor context.
  You export the filtered opportunity inbox and the pipeline reads it through
  the same recency and relevance gates. Higher signal in, higher signal out.

Both feed the identical pipeline, so the sheet and deck look the same either
way. Start on RapidAPI. Move to the intent-classified source when a keyword's
best guess is not good enough.

---

## Suggested repo structure

```text
reddit-buyer-signals/
  config/
    subreddits.txt        # communities your buyers post in
    keywords.txt          # the "X vs Y" searches they run
  lib/
    reddit_client.py      # the Reddit source (swappable)
    relevance.py          # brands, category nouns, topic tags, classifier
    sheet_engine.py       # the color-coded Google Sheet builder
  data/
    signals.db            # local SQLite, four tables, idempotent
    clearbox_export.sample.json   # bundled offline sample
  init_db.py              # create the database
  pull.py                 # recent-only pull, two sources
  mine.py                 # extract + cluster buyer language
  score.py                # 1-5 scoring, transparent rules
  build_sheet.py          # render the color-coded sheet
  build_deck.py           # render the editable Slides deck
  setup_oauth.py          # one-time Google Workspace connection
  run.sh                  # the whole loop
```

Start by running the offline sample so the shape is real before you touch it.
Then edit the two config files and the two maps in `relevance.py` and
`score.py` for your own market. Once the plan holds up across a couple of
weekly runs, wrap `run.sh` in a cron job and let it re-score itself.

---

## The content and intelligence layer

The pull, the score, and the sheet find the gap. Four more scripts help you
close it. They ship in the same `reddit-buyer-signals/` starter, they read the
same classified opportunities, and each one does a single job you can run on
its own.

### What are the GEO terms (geo.py)

A GEO term is a buyer question you want an answer engine to cite you for. "How
do you keep one source of truth across HubSpot and Salesforce." "What is the
fastest way to dedupe accounts before a migration." The sort of thing a RevOps
lead asks an assistant, and something your product can answer with authority.

`geo.py` starts from the real buyer language the account already surfaced, the
same mined topics the sheet is built on, and shapes each into a clean query.
Then it runs a hard-capped pass through Exa on the top few terms and asks one
thing of each. When a buyer asks this today, does your brand show up in what
the model reads. The cap lives in `lib/exa_client.py` as `MAX_QUERIES`
(default 8), and a caller cannot exceed it even by passing more queries, so a
visibility check never burns the balance. With no Exa key set, the terms still
come out, just without a live score.

The output carries two things on every row, the term to own and whether AI
cites you for it right now. That is the plan and the gap in one file.

```bash
python3 geo.py --brand "Acme PM" --db data/signals.db --out data/geo_terms.json
# GEO terms: 22 · visibility-checked 8 · already cited 1 · score 12 -> data/geo_terms.json
```

A score of 12 means that across the eight buyer questions checked, your brand
surfaced in one. That number is the reason to publish the pages, stated plainly.

### Competitor analysis (competitor.py)

This read does not count brand strings, and it does not have to. Clearbox has
already classified every opportunity as engage, lead, or competitor, tagged
against your own brands and your competitors' brands. The classification is the
relevant-mention signal by construction. `competitor.py` reads it straight and
rolls it into a share-of-voice view, how many live conversations a competitor
is already the answer in, versus how many are an open opening where your
category is live and no one owns it yet.

It adds two things the Reddit data itself has no field for. A sentiment read,
generated upstream over the opportunity summaries and labeled as generated so
no one mistakes an LLM read for a stored field. And a plain narrative of where
you stand.

```bash
python3 competitor.py --own "Acme PM" --competitor "Rival PM" \
    --ops data/ops_classified.json --out data/competitor_analysis.json
# competitor analysis: 9/40 competitor ops · 26 openings · sentiment {'neutral': 5} -> ...
```

Nine of forty live conversations already point at the competitor. Twenty-six
are wide open. That is the argument for showing up, in two numbers.

### Create content (content.py)

`content.py scaffold` takes one real buyer question and builds a three-draft
pack, a LinkedIn post, a Reddit post kept as a draft, and a long-tail blog, all
in the client's voice, with anti-slop enforced. The coding agent writes the
words. The script gives it the skeleton, a generation brief with the voice
profile inlined, and a manifest that keeps the pack client-scoped so it never
dispatches to a public content channel.

```bash
python3 content.py scaffold --client "Acme PM" --voice ../voice/core-voice.md \
    --topic "keeping one source of truth across HubSpot and Salesforce" \
    --out content/pack-01
```

The blog has a defined shape so it earns citations. A buyer-query H1, a TL;DR
answer block up top, and a `## Frequently Asked Questions` section with
`### question` headings that emit FAQPage schema. HowTo-shaped steps go in where
the answer is a procedure. When a draft is done, the second subcommand scans it
before it ships.

```bash
python3 content.py check content/pack-01/blog.md
# content/pack-01/blog.md: ok
# PASS: 0 flag(s) across 1 file(s)
```

The checker merges the house structural scanner with an explicit banned-word
list and an em-dash catch. No em-dashes, no define-by-negation, no CTA-slop,
no banned words. It is the same check that gates this chapter.

### Access everything through the API

The classified opportunity inbox is a live HTTP API, pull-only. Three routes,
no writes to your data.

- `GET /inbox` lists every open opportunity. Each row carries `kind`, one of
  `lead`, `competitor`, or `engage`. That field is the routing switch the rest
  of the pipeline reads.
- `GET /op/{id}` returns one opportunity in full.
- `GET /op/{id}/done` marks an opportunity worked, so it leaves the inbox on
  the next pull.

Two things about the transport that a copy-pasted snippet gets wrong. The token
is a path segment in the URL, not a header. And Cloudflare fronts the host, so a
request sent with the default urllib User-Agent comes back 403. Send a browser
User-Agent on every call and it goes through.

```python
import os, json, urllib.request

BASE = "https://api.clearbox.to"
TOKEN = os.environ["CLEARBOX_INBOX_TOKEN"]          # a path segment, not a header
UA = {"User-Agent": "Mozilla/5.0 (clearbox-inbox-poller)"}  # default urllib UA gets a 403

def get(path):
    req = urllib.request.Request(f"{BASE}/{TOKEN}{path}", headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)

inbox = get("/inbox")                       # rows tagged lead | competitor | engage
for row in inbox["opportunities"]:
    op = get(f"/op/{row['id']}")            # the full opportunity
    # classify, gate, enrich, digest ...
    get(f"/op/{row['id']}/done")            # done, drop it from the inbox
```

There are no POST routes. You do not push state back beyond marking an
opportunity done. The pattern is a cron that polls `/inbox`, works each row by
its `kind`, and marks it done. Everything else in this chapter reads the JSON
that comes out of these three routes.

---

## The Reddit skills that do not get you banned

This is the hook, so it is worth saying flat. The reason these skills are safe
to run is that the risky part, the posting, stays human, and the parts that
scale, the reading and the routing, are the only parts automated.

Three guardrails hold that line.

- **Recency, enforced at the pull.** Only the last 30 to 60 days enters the
  database. Nothing older, ever. Fresh threads are what answer engines weight,
  and a live conversation is the only place a sincere mention is even possible.
- **Relevance, on every pull.** A thread is kept only when it names a real
  brand or a category noun. A keyword search drags in careers, gaming, and
  politics threads that share a word but not a buyer. The relevance gate drops
  them on the way into SQLite, so the plan is built on real buyers.
- **Karma first, always.** Be a genuine human on Reddit. Comment because you
  have something to add, build standing in the communities you sell into, and
  let the reading and routing run off to the side. The automation reads the
  room. You still speak in it.

Automate the inbox, the classification, the gate, the enrichment, and the
digest. Post in your own voice, on threads you would have answered anyway. That
split is the whole method, and it is why the account stays in good standing
while the pipeline runs every day.

---

## Why this belongs in a coding-agent GTM repo

This is not really about Reddit.

It is about making a demand signal legible enough that a coding agent can help
you act on it. The buyer talk is unstructured and scattered across a hundred
communities. The pipeline turns it into a scored table with a reason on every
row, which is something an agent can read, rank, and help you write against.

The pattern is the same one that runs through the whole GTM Coding Agent repo:

- structured context in small files
- small scripts that each do one job
- visible workflow state you can inspect
- human review where judgment matters, because you still decide what to
  publish and you still comment in your own voice

Use the sheet to find the questions your buyers are asking right now, use the
deck to show anyone the gap, then go be the answer. On a channel and a
schedule you control, not one you rent.

---

> 🟧 **Clearbox** is the engine behind this chapter. See your market. Move first. Start a 7-day free trial at [clearbox.to](https://clearbox.to).
