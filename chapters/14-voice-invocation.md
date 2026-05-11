# Chapter 14: Voice-Invocation

**Voice DNA tells an agent how you sound. Voice-invocation runs that profile against every meeting transcript automatically, drafts the content the conversation should produce, and routes each output to its own typed surface for review.**

---

## What Voice-Invocation Is

Chapter 09 covered Voice DNA — the static profile of how you write. A markdown file that captures your tone, vocabulary, anti-slop rules, and platform adaptation. Once it exists, agents can write content that sounds like you.

Voice-invocation is the next layer. The DNA is what the agent reads. Voice-invocation is what the agent does on every conversation that happens in your business.

A meeting ends. A transcript lands. A pipeline picks it up and produces:

- A blog draft
- A LinkedIn post
- An X thread
- Reddit drafts when the conversation maps to a sub
- The todos committed to mid-conversation
- The pain points the other side surfaced without realizing it
- The signals about where the market is actually moving
- A voice-drift report telling you whether you sounded like yourself

Six to eight outputs from one thirty-minute call. Each one a draft. Nothing publishes. Everything routes to a typed Discord channel for human review.

The DNA is the map. Voice-invocation is the system that uses the map every time you have a conversation worth turning into content.

---

## Voice DNA vs Voice-Drift

These are two different things. Most builders conflate them.

**Voice DNA** is the static profile from Chapter 09. Lives at `templates/voice/core-voice.md`, `templates/voice/anti-slop.md`, `templates/voice/platform-playbook.md`. It is the rules and the corpus. How you sound on a good day, written down.

**Voice-drift** is the per-conversation audit. The new transcript came in. Did it sound like the DNA, or did the speaker drift somewhere in the middle? The drift analyzer extracts new phrasings, compares them to the corpus, and proposes updates to the principles file when the drift is worth keeping.

Drift detection is the half nobody builds. Most "AI voice tools" stop at the profile. They reference your DNA when generating new content but never check whether you actually still sound like yourself in the original input. Voice-drift closes that loop.

The DNA is the map. Drift is the compass.

---

## The Six Stages

Voice-invocation runs as a six-stage pipeline. Each stage is idempotent. Re-running on the same transcript produces a `-v2` directory rather than overwriting prior output.

### Stage 1: Load the transcript

The pipeline accepts either a Fireflies meeting ID or a local path to a `.md` transcript. If it gets an ID, it fetches the transcript via Fireflies' GraphQL API. If it gets a path, it reads directly.

The transcript text plus a meeting slug (date + speaker names) flow into the next stage.

### Stage 2: Analyze voice drift

This is the core of the system. Five sub-steps inside one analyzer.

**Read the DNA.** Load `templates/voice/core-voice.md` and the entire `examples/voice-dna/` corpus.

**Extract phrasings.** Pull anything that recurs three or more times in the transcript. Hook patterns. Topic-specific jargon. Cadence tells, the short clauses and sentence fragments that are intentional. Three occurrences is the floor — one or two could be transcription noise.

**Compare.** Two checks against the corpus. New phrasings that recur but don't match anything in the corpus get flagged as drift candidates. Phrasings that DO match get reinforced as signature patterns. Both signals matter. New language is either growth or drift, and you can't tell from the inside of the conversation.

**Write the proposal.** Output lands at `voice/drafts/YYYY-MM-DD_<slug>_voice-update.md`. Includes the new phrasings, suggested principles diff, rationale per candidate. Each one has a reason. Add to corpus. Drop because it's a verbal tic. Drop because it contradicts an existing rule. The reasons are the value.

**Human gate.** Never auto-apply to the principles file. The drift is a draft. You read it. You merge what's yours. You drop what isn't.

The full prompt for this stage is in `prompts/voice-drift-analyzer.md`. Use it directly with `claude -p` against any transcript and you get the same drift report this pipeline generates.

### Stage 3: Generate content pack

A subprocess fires `claude -p --model opus` with a system prompt that includes the principles file, the most-recent corpus examples for cadence calibration, and the new transcript. The output format is locked to JSON with explicit anti-slop rules in the prompt.

The generated pack covers a fixed shape:
- 1 long-form blog post (800-1500 words)
- 2 X posts
- 1 LinkedIn post + 2 LinkedIn comments
- 0-3 Reddit drafts (only when the conversation maps cleanly to a sub)
- A ready-to-paste video prompt for short-form rendering

Subprocess instead of API matters. The CLI binary inherits your Claude Code Max auth, so every call bills against the subscription you already pay for instead of the API. Three to five dollars of API tokens per 30-minute call collapses to about zero marginal.

### Stage 4: Stage the drafts

The pack is written to `~/content/drafts/YYYY-MM-DD_<meeting-slug>/`. One file per draft. A `manifest.json` describes which channel each item routes to and what hook variants are available.

If the directory already exists from a prior run, the stage appends `-v2`, `-v3`, and so on. Idempotent. The cron can re-run without losing prior drafts.

### Stage 5: Notify

A macOS notification fires. A handoff file lands in `~/.claude/handoffs/` so the next agent session picks up the staged drafts as context. No Discord post yet.

### Stage 6: Dispatch to Discord

The dispatcher reads `manifest.json` and posts each item to its assigned channel via webhook. Each post carries the body as an attachment, the three hook variants in the embed, and a footer with anti-slop scan results.

After dispatch, the queue lives in SQLite. Terminal verbs (`status`, `approve`, `edit <channel>`, `final`, `clip next`) advance items through the state machine.

---

## What Lands in Discord

Six channels for one call. Each one a typed mailbox holding one shape of context.

| Channel | Content |
|---|---|
| `blog-newsletters` | Long-form blog + LinkedIn newsletter mirror |
| `linkedin-content` | Standalone LinkedIn feed posts |
| `x-posts` | Single X posts and threads |
| `reddit-posts` | 0-3 subreddit-matched drafts |
| `voice-drift` | The drift report with proposed principles updates |
| `productivity-to-dos` | Action items committed to during the call |

Open Discord and the right shape is already waiting. Blog channel for writing mode. Drift channel for voice-review mode. Todos channel when you want to know what you committed to. Each channel is a webhook. Each webhook is a one-line config change. Modular.

---

## Setup: Wire It Up Locally

This takes about an hour the first time. Most of it is one-time wiring.

### Step 1: Install the skill

The voice-invocation skill is a single SKILL.md file plus three Python scripts. Place them at `~/.claude/skills/voice-invocation/`. The skill description triggers on phrases like "run voice invocation on", "/voice-invocation", or when the cron passes the right env var.

### Step 2: Wire your transcript source

The reference implementation uses Fireflies. Any source that produces a markdown transcript works — Otter, Granola, Krisp, Whisper-on-Zoom-recordings.

For Fireflies specifically: get an API key from `app.fireflies.ai → Settings → Developer Settings`. Save it to a chmod-600 dotfile. The `fireflies_pull.py` companion script polls for new transcripts on a schedule and downloads any it hasn't seen.

### Step 3: Set up the cron

On macOS, launchd. On Linux, systemd or cron. The job runs the puller every five minutes during your active hours (the reference plist guards 07:00-22:00 local).

When the puller finds a new transcript, it spawns:

```bash
VOICE_INVOCATION_FROM_CRON=1 claude -p --model opus \
  "Use the voice-invocation skill on ~/data/fireflies/<new-transcript>.md"
```

The env var lets the skill detect cron context and adjust logging accordingly.

### Step 4: Wire Discord webhooks

Create a Discord server with one channel per output type. Generate a webhook for each channel. Store the webhook URLs in your secrets store — a SQLite `secrets` table works well (key/value pairs, easy to query, easy to rotate). Never hardcode webhooks in scripts. Always resolve at runtime.

Default Python `urllib` UA returns 403 from Discord. Always set an explicit `User-Agent` header.

### Step 5: Dry-run

Before the cron runs live, point the dispatcher at an existing transcript with `--dry-run`. It prints the channel routing without posting. Verify each item lands in the right channel. Verify slop flags are clean. Then drop the flag and let it run for real.

---

## Anti-Patterns

Five things kill the pipeline if you build it wrong.

**Auto-applying drift to principles.md.** The drift report is a draft. Auto-applying erodes the corpus toward whatever phrasings are loudest in recent calls. The human gate is the entire point.

**Mocking the transcript source.** Tests that mock Fireflies or the LLM hide real failures. The pipeline's hard cases are real-world ones — partial transcripts, missing speakers, weird unicode. Run against a real transcript.

**Silently retrying failed JSON parsing.** When the LLM produces malformed JSON, log the raw output and surface the error. Silent retries waste API budget and hide drift in the prompt.

**Skipping anti-slop scan on public channels.** Three flags or more should fail the dispatch, not warn. The whole point is the voice gate. Letting slop through defeats the system.

**Hardcoding webhooks or API keys.** Webhooks rotate. Keys leak. Always resolve from a secrets store at runtime. One line of grep finds every script that hardcoded a token six months ago.

---

## Closing Exercise

Run the drift analyzer manually on one transcript. Twenty minutes. No code yet.

1. Find or download one meeting transcript as markdown. Anything 15-60 minutes long.
2. Open the analyzer prompt: `prompts/voice-drift-analyzer.md`.
3. Paste the prompt into Claude Code along with your principles file and the transcript.
4. Read the output. The drift candidates the analyzer flags will tell you whether your principles file is too narrow or too broad.
5. Decide one merge and one drop. Write down why.

That decision pattern is the entire system. The script automates the steps before the decision. The decision still belongs to you.

---

## Key Takeaways

- Voice DNA is the profile. Voice-invocation is the system that uses it on every conversation.
- Voice-drift is the per-conversation audit. New phrasings get flagged. The corpus grows over time. The principles file stays small.
- Six stages, idempotent, re-runnable. The cron writes drafts; humans review them.
- Subprocess against `claude -p` instead of the API. Subscriptions over per-token billing.
- Discord is the typed staging surface. Each channel a mailbox for one shape of output.
- The system catches what you missed in the moment. That's what the audit gives you.

---

**Next:** [README.md](../README.md) — return to the index for chapter selection, or revisit [Chapter 09 - Voice DNA & Content](./09-voice-dna-content.md) for the static profile this chapter builds on.
