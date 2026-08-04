# Chapter 20: Podcast to Shorts

**One recording session becomes seventeen captioned vertical clips, a blog post, a newsletter, and a month of daily posting — because the transcript, not the video, is the asset you work with. A coding agent that can read word-level timestamps can cut clips by being told what the moment was, not where it is.**

---

## The Origin

I recorded a podcast with the LeanScale team. The episode would not hit YouTube for two weeks. Waiting two weeks means posting nothing while the content is freshest, so the distribution machine started the day the recording landed.

The raw session became a word-timestamped transcript. The transcript became 17 vertical clips, each cut where a story peaks. The clips became drafts on TikTok, Instagram Reels, and YouTube Shorts, staged through the Buffer API, plus one LinkedIn clip a day. The same transcript then got mined again for the long-form layer: a blog post shaped like buyer questions, a newsletter issue, a Reddit post.

The episode is one asset. The transcript is thirty. This chapter is the pipeline that does the conversion, and it ships as a runnable starter you can point at your own recording.

---

## Why the Transcript Is the Interface

Video editing software makes you find moments by scrubbing a timeline with your eyes. A transcript with word-level timestamps inverts that: every word knows its exact second, so "the story about the $10,000 API bill" is a text search, not a hunt.

That inversion is what makes a coding agent a video editor. You say the moment, the agent greps the transcript, and the timestamps fall out. Pair it with a voice keyboard (Wispr Flow, superwhisper) and the workflow is literally speaking: "cut the pricing story as a vertical clip, end it on the punchline." No timeline was scrubbed in the making of those 17 clips.

The stack, all free or already on your machine:

| Stage | Tool | What it does |
|---|---|---|
| Fetch | yt-dlp | pulls any published episode; or get per-speaker exports from your recorder |
| Transcribe | Whisper | word-level timestamps, runs locally |
| Plan | `plan_clips.py` | anchors each cut on the words it must open and close with |
| Overlay | `compose_overlay.py` | hook text, karaoke caption pills, CTA — rendered as transparent graphics |
| Composite | `final_composite.py` | one ffmpeg pass: footage + overlay + loudness + speed |
| Verify | `qa_delivery.py` | the gate that catches what your eyes cannot |
| Stage | `buffer_schedule.py` | drafts on every platform through one API |

---

## Cut Where Stories Peak, Not Where Topics Change

"Here is our take on automation" is a topic. "The AI told me API access takes 24 hours and forgot to mention the $10,000" is a story. Stories get watched to the end; topics get swiped past. The clip spec in `pack.json` forces this discipline: every clip declares `start_text` and `end_text` — the exact words it opens and closes on. The planner anchors to those words in the transcript and refuses to guess.

Two timing rules the pipeline encodes because whisper will betray you otherwise:

- Whisper's word-END timestamps run about 0.1s early. If you clamp a cut to the next word's start, continuous speech collapses the tail and chops the final word. The planner compensates (`END_COMP`) and rides slightly into the next word's attack (`BLEED`), letting the audio fade mask it.
- The end fade must anchor to the last word, never to "clip duration minus 0.15s" — that eats the punchline exactly when the speaker lands it.

---

## The Audio Lesson That Cost Three Rebuilds

This one is the reason the starter has a QA gate, and it is invisible to every visual check you will ever run.

A filter-graph master (trim → concat → tempo → loudnorm) can emit an audio **timestamp** jump at a cut seam while the audio **content** stays perfectly continuous. Every player and every platform ingest reads audio sample-by-sample and never notices — the master sounds flawless. Then a delivery re-encode adds `aresample=async=1`, a flag that trusts timestamps, and the hidden gap becomes real: the first second of audio time-compresses, then two seconds of literal silence, then normal. Published, it reads as "the clip glitches, then recovers." Fifteen of seventeen clips shipped broken while every frame-level check passed.

The fix is one filter: end the audio chain with `asetpts=N/SR/TB`, which rebuilds every timestamp from the sample position — continuous by construction. And never use `aresample=async=1` on filter-graph masters.

The durable lesson: **QA every dimension, not just the one that failed last time.** Frames, audio content, and container timing are three separate failure surfaces.

| QA check | bar |
|---|---|
| silence regions (silencedetect) | count equals the master's |
| audio cross-correlation vs master | lag ≤ 25ms at five windows |
| first packet | keyframe at pts 0 |
| packet cadence | uniform CFR |
| duration | within 0.1s of master |

`qa_delivery.py` runs all five on every clip. Nothing gets hosted until the table is all PASS.

---

## Stage as Drafts, Not Posts

`buffer_schedule.py` creates drafts on TikTok, Instagram Reels, and YouTube Shorts through Buffer's API — per-platform captions, one video URL each. Drafts on purpose: a human approves before anything goes live. Three operational rules from production scar tissue:

- Pace every mutation about a second apart. Buffer rate-limits bursts on a 15-minute window and heavy create/delete churn on a 24-hour one.
- `editPost` is a full replace. Send only a new time and the API wipes the media and rejects the post; always resend text, assets, and metadata.
- Never overwrite a hosted video under the same filename. CDNs serve stale bytes for an hour or more, and the platform ingests whatever the edge hands it. Version filenames, then verify the served bytes (sha256) match your local file.

---

## Anti-Patterns

- **Editing by timeline.** If you are scrubbing, you have not given the agent the transcript.
- **Cutting on topics.** Topic boundaries produce clips that start slow and end nowhere.
- **Trusting your eyes for QA.** The worst defect this pipeline ever shipped was inaudible in frames and invisible in waveform thumbnails.
- **Re-uploading over a published filename.** The CDN will make a liar out of you.
- **Auto-publishing.** Drafts exist so a human sees every post once before the world does.

---

## Closing Exercise

Take any recording you have — a podcast, a sales call you are allowed to use, a loom you rambled into. Run the starter:

1. `cp pack.example.json mypack/pack.json`, point `sources` at your files, describe two clips by their opening and closing words.
2. `./run.sh mypack`
3. Watch the QA table. If a clip fails the silence check, you just caught the bug this chapter is about — on your own footage, before your audience did.

Then post one clip manually and watch what a story-peak cut does against your usual topic-cut clips.

---

## Key Takeaways

- The transcript is the interface. Word timestamps turn "that moment when" into an exact cut.
- Anchor cuts on words (`start_text` / `end_text`), compensate whisper's early word-ends.
- Audio timestamps and audio content are different things; `asetpts=N/SR/TB` keeps re-encodes honest, and the QA gate proves it clip by clip.
- Stage drafts through one API, pace the calls, version the filenames, verify the served bytes.
- One recording, mined twice (clips + long-form), fills a month of distribution.

---

Runnable version of everything above: `starters/podcast-shorts/` — install it as a Claude Code skill and cut your next episode by talking.
