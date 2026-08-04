# podcast-shorts

Turn one podcast recording into a batch of captioned vertical clips, quality-gated
and staged as Buffer drafts for TikTok, Instagram Reels, and YouTube Shorts.

This starter doubles as an installable Claude Code skill: `SKILL.md` is the
operating manual an agent follows, and the Python scripts are the pipeline it runs.

## Quickstart

```bash
# 1. system deps: ffmpeg + node (for the overlay renderer)
brew install ffmpeg        # or apt install ffmpeg

# 2. python deps
pip install -r requirements.txt

# 3. get source material
#    best: per-speaker video + lossless WAV exports from your recording platform
#    fallback: yt-dlp <video-url> pulls any published episode
mkdir -p mypack/source && cp your-exports/* mypack/source/

# 4. describe the clips you want
cp pack.example.json mypack/pack.json   # edit: sources, clip windows, hooks

# 5. run it
./run.sh mypack
```

`run.sh` walks every clip through transcribe → plan → overlay → render → composite,
then encodes social deliveries and runs the QA gate. Output masters land in
`mypack/out/`, social encodes in `mypack/out/delivery/`.

## Install as a Claude Code skill

```bash
mkdir -p ~/.claude/skills/podcast-shorts
cp -r . ~/.claude/skills/podcast-shorts/
```

Then in Claude Code, describe the moment you want in plain words ("cut the story
about the pricing call as a vertical clip that ends on the punchline") — the agent
reads SKILL.md, searches the word-timestamped transcript, and drives the scripts.
Pair it with a voice keyboard (Wispr Flow, superwhisper) and you edit by talking.

## Buffer staging (optional)

```bash
export BUFFER_ACCESS_TOKEN=...   # from any api.buffer.com request in browser devtools
export BUFFER_ORG_ID=...         # your Buffer organization id
python3 buffer_schedule.py mypack all go
```

Creates DRAFTS (never live posts) for every clip on every connected channel.
Captions come from `clips/captions.json`, video URLs from `clips/buffer_urls.json`.

## Why the QA gate exists

The audio pipeline can carry a hidden timestamp gap that no player shows but a
careless re-encode turns into seconds of silence. `qa_delivery.py` compares every
delivery against its master (silence regions, cross-correlation, packet timing)
so nothing broken ever gets hosted. The full story is in SKILL.md.
