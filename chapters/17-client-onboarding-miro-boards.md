# Chapter 17: Client Onboarding Boards with Miro

**This chapter is for operators, agencies, and GTM builders who want the
first client conversation to feel like the work has already started. The
play is simple: build the client a live map of their GTM engine before the
proposal becomes the center of the room. Sources, database, enrichment, CRM,
outreach, website, content, funnel, and measurement all sit on one board.
Then you share the checklist, stack doc, API access doc, and roadmap that
make the board operational.**

---

## TL;DR

- **Replace the proposal with a working map.** A proposal asks the client to
  grade a promise. A board lets them react to the actual operating system.
- **Use one canonical template.** Keep a clean pipeline layout, then have your
  coding agent duplicate and relabel it for each client.
- **Make missing information explicit.** If the client stack is unknown, mark
  the field `NEEDS INPUT`. Do not let the agent invent tools, costs, owners,
  or credentials.
- **Do visual QA.** A `200 OK` from the Miro API means the request worked. It
  does not mean the board looks good. Screenshot the board and inspect it.
- **Route connectors deliberately.** Auto-routed arrows are where clean boards
  turn into spaghetti. Treat connector routing as craft.

---

## Why this works

When a client reads a proposal, they are outside the work. They compare claims,
prices, timelines, and confidence.

When they open a board of their own GTM system, they are inside the work. They
can see the sources, CRM, enrichment, outreach, website, content, and analytics
as one machine.

That changes the conversation.

Instead of asking, "Do we trust this person to do the work?" they start asking,
"Is this how our engine should run?"

That is the handoff you want.

---

## The onboarding package

The board is the visual center, but it should not live alone. Pair it with four
documents:

1. **Week-one checklist.** What happens first, who owns each item, and what
   "done" means.
2. **Tech-stack doc.** Every tool, the cost, the owner, the signup link, and
   the reason it exists.
3. **API-access doc.** Every credential needed, where it is created, who owns
   it, and how to rotate it.
4. **Roadmap.** The current plan, what is already done, what is blocked, and
   what comes next.

The package makes the board usable. Without the docs, the board is theater.
With the docs, it becomes the client operating surface.

---

## The board model

Start with a stable pipeline layout. For a website and content engine, I like:

```yaml
columns:
  - TRAFFIC
  - HOSTING
  - CONTENT
  - DISTRIBUTION
  - FUNNEL
  - MEASUREMENT
```

For an outbound or signal engine, I usually use:

```yaml
columns:
  - SOURCES
  - DATABASE
  - ENRICHMENT
  - CRM
  - OUTREACH
```

Do not over-design the template. The value is repeatability. If every board
starts from the same coordinate system, your agent can reason about it, your
screenshots are easier to inspect, and your client portfolio does not drift
into ten different diagram styles.

---

## The data contract

Give the agent a small client JSON file instead of a long paragraph.

```json
{
  "client": "Acme CRM",
  "engine": "outbound",
  "columns": {
    "SOURCES": ["Reddit", "LinkedIn", "G2"],
    "DATABASE": ["Supabase"],
    "ENRICHMENT": ["Apollo", "Clearbit"],
    "CRM": ["HubSpot"],
    "OUTREACH": ["Smartlead"]
  },
  "unknowns": [
    "analytics owner",
    "API key rotation policy"
  ]
}
```

The rule is blunt: if the agent cannot verify a value, it writes
`NEEDS INPUT`.

That includes prices, owners, login paths, scopes, API limits, and any claim
about how the client's current stack works.

A board with honest gaps is useful. A board with confident guesses is a future
fire drill.

---

## The Miro API gotcha

Miro will happily accept a connector request that creates a bad-looking board.

If you leave out snap points, the connector may take the shortest path between
two shapes. On a dense board, that often means the arrow goes straight through
another box.

Across thirty connectors, the board becomes unreadable.

So route connectors by edge class:

- `same_column`
- `adjacent_column`
- `skip_column`
- `loop_back`
- `cross_frame`
- `measurement`

Claude or Codex can generate the structure quickly: frames, boxes, labels,
colors, and starting coordinates. Connector routing is the part to inspect
carefully.

The practical workflow:

1. Generate the board from the template.
2. Create connectors with explicit start and end sides.
3. Screenshot the board.
4. Ask the agent to describe what it sees.
5. Fix overlaps, stacked logos, clipped labels, and arrows crossing boxes.
6. Repeat until the board is something you would show a client.

---

## Suggested repo structure

```text
client-onboarding/
  client.json
  board-template.json
  pipeline-6-column.yaml
  docs/
    week-one-checklist.md
    tech-stack.md
    api-access.md
    roadmap.md
  scripts/
    create_board.py
    screenshot_board.py
```

The first version does not need to be fancy. Start with a template and a JSON
file. Once the layout holds up across three clients, then script the boring
parts.

---

## Why this belongs in a coding-agent GTM repo

This is not really about Miro.

It is about making a go-to-market system legible enough that a coding agent can
help operate it.

The board gives humans a shared picture. The JSON and docs give the agent a
shared contract. The screenshot loop keeps both honest.

That combination is the pattern across the whole GTM Coding Agent repo:

- structured context
- small scripts
- visible workflow state
- human review where judgment matters

Use the board to sell the work, then keep using it to run the work.

