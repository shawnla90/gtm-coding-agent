# Chapter 16: The Clipping Content Engine

**Every video you record is already a content library. yt-dlp pulls the source, OpenShorts finds the moments, and Claude Code orchestrates the cut-down into clips, captions, and platform posts — fanned out for review, never auto-published.**

---

## What The Clipping Engine Is

You record a call. A demo. A walkthrough. A podcast. That recording is thirty to sixty minutes of you saying things worth saying — and it dies as one unwatched YouTube link.

The clipping engine is the system that turns one long video into the week of content it already contains. Not "AI makes you a video." A pipeline you own: download, transcribe, detect the moments worth clipping, cut them, write the copy each clip needs, and route every output to a place you review before anything ships.

Chapter 14 did this for meeting transcripts — text in, content pack out. This chapter does it for video. Same philosophy: the agent runs the steps, you keep the decision.

The stack is three pieces:

- **yt-dlp** — downloads the source video, audio, and subtitles from YouTube (or a local file). Battle-tested, scriptable, free.
- **OpenShorts** — an open-source clip detector. Takes a long video plus its transcript, scores segments for standalone watchability, and proposes cut points with start/end timestamps.
- **Claude Code** — the orchestrator. It doesn't replace either tool. It chains them, reads the transcript, picks which proposed clips are actually good, generates the title/caption/hook for each, and writes everything to a typed review surface.

The tools do the mechanical work. Claude does the judgment work. You do the publish decision.

---

## Why This Belongs In A GTM Repo

Because the content is the GTM motion. Every chapter in this kit produces something — a dashboard, an intel engine, a CRM script, a voice pipeline. The build *is* the content. The clipping engine is how the build becomes distribution without a separate content team.

You are already recording yourself working. This turns that recording into the top of the funnel.

---

## The Five Stages

The engine runs as five stages. Each is idempotent — re-running on the same video produces a versioned directory (`-v2`) rather than overwriting. Each stage writes to disk so you can inspect the handoff between them.

### Stage 1: Pull the source

`yt-dlp` takes a URL or a local path. It downloads the video, extracts the audio, and grabs auto-generated subtitles if they exist.

```bash
yt-dlp \
  --write-auto-subs --sub-lang en --convert-subs srt \
  -f "bestvideo[height<=1080]+bestaudio/best" \
  -o "engine/clips/source/%(id)s/%(id)s.%(ext)s" \
  "<youtube-url-or-local-path>"
```

Output lands at `engine/clips/source/<video-id>/`. Video, audio, and an `.srt`. If subtitles don't exist, Stage 2 generates them.

The video ID is the slug for everything downstream. One video, one directory, every artifact namespaced under it.

### Stage 2: Transcribe and time-align

If yt-dlp got subtitles, you have a timed transcript already. If not, run the audio through a local Whisper model and produce a word-timestamped transcript.

The output is one file: `transcript.json` — text plus per-segment start/end times. This file is the contract every later stage reads. Nothing downstream touches the video directly until the final cut. They reason over the timed text.

### Stage 3: Detect candidate clips

OpenShorts takes the video and the transcript and scores windows for clip-worthiness — completeness of thought, hook strength, whether the segment stands alone without the surrounding context.

```bash
openshorts detect \
  --video engine/clips/source/<id>/<id>.mp4 \
  --transcript engine/clips/source/<id>/transcript.json \
  --min 20 --max 90 \
  --out engine/clips/candidates/<id>/candidates.json
```

`candidates.json` is a ranked list: start, end, score, and the transcript text of each proposed clip. This is a proposal, not a decision. OpenShorts is good at "this 40-second window is a complete thought." It has no idea which thoughts are *yours to amplify*. That's the next stage.

### Stage 4: Curate and write copy (the Claude stage)

This is where the agent earns its place. A single `claude -p` call — subprocess, not API, subscription not per-token, the Chapter 14 pattern — gets:

- `candidates.json` (the proposed cuts)
- The full `transcript.json` (the context each clip came from)
- Your `templates/voice/core-voice.md` and `templates/voice/anti-slop.md`

And produces, per surviving clip:

- **Keep / drop, with a reason.** Drop the ones that need context to land. Drop the ones that restate something a stronger clip already says. The reasons are the value — they teach you what makes a clip standalone.
- **A title** — what this clip is, not clickbait.
- **A hook** — the first line of the post, in your voice, scanned against anti-slop.
- **A platform map** — this one is a 60s YouTube Short, this one is a 30s LinkedIn native video, this one is a quote-card not a clip at all.

Output: `engine/clips/curated/<id>/clip-plan.md` plus a `cuts.json` with the final approved timestamps.

The human gate lives here. The plan is a draft. You read it before a single frame is cut.

### Stage 5: Cut and fan out

Read `cuts.json`. For each approved clip, `ffmpeg` cuts the segment from the source video — clean keyframe cuts, no re-encode where possible. Burn captions if the platform needs them. Write each rendered clip plus its copy to a typed review surface — the Chapter 14 Discord pattern works here unchanged: one channel per platform, each clip a draft sitting in its mailbox.

Nothing publishes. The pipeline produced six clips and the copy for each. You open the channel, watch them, ship the three that are right.

---

## The Orchestration

The point isn't the five stages. It's that one command runs all five, and Claude Code is what makes that one command exist.

You don't write a brittle bash script that hardcodes the chain. You describe the pipeline to the agent — the stages, the file contracts between them, the idempotency rule — and it builds the runner, wires the tools it finds installed, and handles the failures each tool throws. When OpenShorts ships a new flag, you tell the agent; it doesn't mean rewriting the orchestrator by hand.

That is the difference between *using* clipping tools and *owning* a clipping engine. The tools are commodities. The orchestration — the file contracts, the voice gate, the human review surface, the idempotency — is yours, and it's the part that compounds.

This is also the chapter to build live. If you're walking someone through this kit, don't show them a finished script. Open Claude Code, point it at a recording, and build Stages 1 through 4 in front of them. The build *is* the demo. They watch the engine assemble itself, which teaches the actual lesson: the agent is the thing that turns three CLI tools into a system.

---

## Anti-Patterns

Five ways to build this wrong.

**Auto-publishing the clips.** The whole system is a draft generator. The moment a clip ships without a human watching it end to end, you've built a slop cannon pointed at your own audience. The review surface is not optional.

**Skipping the transcript contract.** If later stages re-read the video instead of the timed transcript, every stage gets slow and non-deterministic. The `transcript.json` is the spine. Everything reasons over text until the final cut.

**Letting OpenShorts pick the final clips.** It scores standalone-ness, not strategy. A 92-scored clip of you saying something off-message is still off-message. Stage 4 exists because the detector has no taste. Don't skip it.

**No anti-slop scan on the generated copy.** The captions and hooks are generated text. Run them through the same kill list as every other piece of content in this kit. Three flags should drop the copy, not warn.

**Re-encoding every cut.** Cutting on non-keyframe boundaries with a full re-encode turns a 30-second job into a 30-minute one and degrades quality. Cut on keyframes, copy the stream, only re-encode when you must burn captions.

---

## Closing Exercise

One video. Thirty minutes. No orchestrator yet — run the stages by hand.

1. Pick one recording of yourself — a call, a demo, a walkthrough. Get the URL or the file.
2. Run Stage 1 (`yt-dlp`) and Stage 2 (subtitles or Whisper). Look at the `transcript.json`. That's your raw material.
3. Run Stage 3 (OpenShorts) or, if it's not installed yet, read the transcript yourself and mark three windows you'd clip.
4. Run Stage 4 by hand: paste the transcript and your voice files into Claude Code, ask for the keep/drop plan and the copy.
5. Read the plan. Pick one clip to drop and write down why it needed context to land.

That decision — "this thought doesn't survive on its own" — is the entire engine. The tools automate everything before it. The taste is still yours.

---

## Key Takeaways

- One long video already contains a week of content. The engine extracts it; it doesn't manufacture it.
- yt-dlp pulls, OpenShorts detects, Claude curates and writes copy, ffmpeg cuts, Discord stages. Five stages, idempotent, file contracts between them.
- The tools are commodities. The orchestration, the voice gate, and the review surface are what you own and what compounds.
- The detector has no taste. Stage 4 is the agent applying your strategy to its proposals. Never skip it.
- Nothing auto-publishes. The pipeline produces drafts; you ship the ones that are right.
- This is the chapter to build live. The assembly of the engine is itself the best demonstration of why coding agents matter.

---

**Next:** [README.md](../README.md) — return to the index, or revisit [Chapter 14 - Voice-Invocation](./14-voice-invocation.md) for the transcript-side pipeline this chapter mirrors.
