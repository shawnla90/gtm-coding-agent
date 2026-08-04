---
name: podcast-shorts
description: Turn a raw podcast or interview recording into captioned vertical shorts staged as Buffer drafts. Invoke on "podcast to shorts", "cut podcast shorts", "clip this episode", "/podcast-shorts", or when the user hands over a long recording and asks for social clips.
---

# podcast-shorts — transcript-anchored vertical clips

Raw recording → word-timestamped transcript → planned cuts → styled overlay render →
one-pass master composite → QA gate → social encodes → Buffer drafts.

## When to invoke

- A podcast/interview recording (ideally per-speaker video + WAV exports) needs to become vertical clips.
- The user describes moments by content ("the story about the pricing call") — the transcript layer turns that into timestamps.

Do NOT invoke for single-source talking-head recuts with no cutting plan, or for meme-style captioning.

## Pack layout

```
<pack-dir>/
  pack.json            # the spec — see pack.example.json
  source/              # per-speaker video + lossless WAV exports
  transcripts/         # written by transcribe.py + plan_clips.py
  projects/clip_NN/    # HyperFrames overlay projects (compose_overlay.py)
  out/                 # masters + delivery encodes
  clips/               # word jsons, captions, buffer_urls.json
  review/framing.json  # optional: face_x overrides + cameo source ranges
```

## pack.json schema

See `pack.example.json`. Per clip: `slug`, `mode` (square | wide | guest | duo), `lead`
(speaker_a | speaker_b), `start`/`end` (source seconds), `start_text`/`end_text` (the words
the clip must open and close on — anchors, not guesses), `hook` (two overlay lines),
`cta`, optional `kicker`, `speaker_names`, `cameo_text`, `tx_windows`, `drops`, `blocks`.
Top level: `sources`, `framing_defaults`, optional `series` (day-order slugs for Buffer).

## Workflow

1. **Transcribe** — `python3 transcribe.py <pack> [idx]`. Whisper (word timestamps) per
   speaker track. Add your product names to ASR_FIXES first; whisper mangles proper nouns.
2. **Plan cuts** — `python3 plan_clips.py <pack> <idx>`. Anchors the cut on
   `start_text`/`end_text` word matches, jump-cuts silences, compensates whisper's early
   word-end stamps (END_COMP/BLEED), writes `transcripts/clip_NN.cut.json` including
   `fade_start` anchored to the last word.
3. **Compose overlay** — `python3 compose_overlay.py <pack> <idx>`. Graphics-only
   transparent HyperFrames project (footage never touches the browser). Keep every
   text card-host at `data-start="0"` — card hosts run their own scheduler clock, and a
   nonzero data-start fights the gsap timeline and flashes on frame 0.
4. **Render** — `npx hyperframes render <pack>/projects/clip_NN/public --format mov -o
   <abs>/projects/clip_NN/renders/overlay.mov`. ProRes 4444 alpha; delete after step 5
   (300-800MB each).
5. **Composite master** — `python3 final_composite.py <pack> <idx>`. One ffmpeg pass:
   denoise, speed bake, crops, alpha overlay, loudnorm, end fade. The audio chain ends
   `asetpts=N/SR/TB` — do not remove it (see below).
6. **Social encodes** — `./make_delivery.sh`. 8-bit yuv420p re-encode, both streams
   fresh, `asetpts=N/SR/TB` on audio.
7. **QA gate** — `python3 qa_delivery.py delivery _social`. Every clip must PASS before
   anything is hosted or drafted.
8. **Stage drafts** — host the encodes anywhere with public URLs, write
   `clips/buffer_urls.json` (`{slug: url}`) and `clips/captions.json`, then
   `python3 buffer_schedule.py <pack> all go`. Needs `BUFFER_ACCESS_TOKEN` and
   `BUFFER_ORG_ID` env vars. Drafts, not scheduled posts — a human reviews.

## The hidden audio-pts gap (read this before changing any audio flag)

The master's audio filter graph (atrim → concat → atempo → loudnorm) can emit a
timestamp jump at a cut seam while the audio CONTENT stays continuous. Players and
platform ingests play sample-continuously and never show it — masters sound perfect.
But any re-encode with a timestamp-aware filter materializes the gap:
`aresample=async=1` turns it into time-squeezed audio followed by seconds of real
silence at the start of the clip.

Rules:
- The composite's audio chain ends `asetpts=N/SR/TB` (timestamps rebuilt from sample
  position — continuous by construction).
- Delivery encodes use `-af "asetpts=N/SR/TB"` and NEVER `aresample=async=1`.
- QA compares decoded audio, not just frames: a defect like this is invisible in
  every visual check.

## QA gate spec (qa_delivery.py)

| check | bar |
|---|---|
| silencedetect regions | count == the master's (a new region = injected dropout) |
| audio cross-correlation vs master | abs lag <= 25ms at 0.2/1/2/5/10s windows |
| first video packet | keyframe at pts 0 |
| packet timing | uniform CFR |
| duration | within 0.1s of master |

## Gotchas

- Whisper word-END stamps run ~0.1s early: never clamp a cut to the next word's start
  minus epsilon, or continuous speech collapses the tail and chops the final word.
- Never overwrite a published object under the same filename — CDNs serve stale bytes
  for an hour or more. Version filenames and byte-verify (sha256) what the URL serves.
- Buffer: pace mutations ~1s apart (rate windows at 15m and 24h); `editPost` is a full
  replace, resend text + assets + metadata with any change.
- gsap is fetched from jsdelivr on first run (GreenSock license — not committed).
