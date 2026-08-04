#!/usr/bin/env python3
"""Word-level transcription from the lossless per-speaker WAVs, per clip and per track.

solo clips -> lead speaker's WAV over the clip window; duo clips -> BOTH WAVs.
`tx_windows` (optional list of [start, end]) overrides the window for sparse
block clips. Output: transcripts/clip_NN.words.<track>.source.json.

Usage: transcribe.py <pack-dir> [idx]
Requires: pip install openai-whisper, plus ffmpeg on PATH. First run downloads
the model (~1.5GB for medium.en); pass WHISPER_MODEL=small.en for a faster one.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

PAD = 2.0

# text-level fixes for names whisper reliably mangles. add your product and
# brand names here — proper nouns are where ASR fails hardest.
ASR_FIXES = [
    ("Cloud Code", "Claude Code"), ("cloud code", "Claude Code"), ("Cloud code", "Claude Code"),
    ("Clod Code", "Claude Code"), ("clod code", "Claude Code"),
    ("Open AI", "OpenAI"), ("open AI", "OpenAI"),
    ("youtube", "YouTube"), ("Youtube", "YouTube"),
    ("Tiktoks", "TikToks"), ("Tiktok", "TikTok"), ("tick tock", "TikTok"), ("Tick Tock", "TikTok"),
]

_model = None


def get_model():
    global _model
    if _model is None:
        import whisper
        _model = whisper.load_model(os.environ.get("WHISPER_MODEL", "medium.en"))
    return _model


def asr_fix(text: str) -> str:
    for a, b in ASR_FIXES:
        text = text.replace(a, b)
    return text


def transcribe_window(wav: Path, ws: float, we: float, tmp: Path) -> list[dict]:
    s = max(0.0, ws - PAD)
    seg = tmp / "seg.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{s:.3f}", "-to", f"{we + PAD:.3f}",
                    "-i", str(wav), "-ar", "16000", "-ac", "1", str(seg)], check=True)
    result = get_model().transcribe(str(seg), word_timestamps=True, language="en")
    words = []
    for segment in result["segments"]:
        for w in segment.get("words", []):
            words.append({"text": asr_fix(w["word"].strip()),
                          "start": round(w["start"] + s, 3),
                          "end": round(w["end"] + s, 3)})
    return words


def main():
    pack_dir = Path(sys.argv[1]).expanduser().resolve()
    pack = json.loads((pack_dir / "pack.json").read_text())
    only = int(sys.argv[2]) if len(sys.argv) > 2 else None
    srcs = pack["sources"]
    tdir = pack_dir / "transcripts"
    tdir.mkdir(exist_ok=True)
    for i, clip in enumerate(pack["clips"]):
        if only is not None and i != only:
            continue
        tracks = ["speaker_a", "speaker_b"] if clip["mode"] == "duo" else [clip["lead"]]
        windows = clip.get("tx_windows") or [[clip["start"], clip["end"]]]
        for track in tracks:
            dest = tdir / f"clip_{i:02d}.words.{track}.source.json"
            if dest.exists():
                print(f"clip {i:02d} {clip['slug']} [{track}]: exists, skip")
                continue
            wav = Path(srcs[f"{track}_wav"])
            words = []
            with tempfile.TemporaryDirectory() as td:
                for ws, we in windows:
                    words.extend(transcribe_window(wav, float(ws), float(we), Path(td)))
            words.sort(key=lambda w: w["start"])
            dest.write_text(json.dumps(
                {"slug": clip["slug"], "track": track, "windows": windows, "words": words},
                indent=1))
            span = f"{words[0]['start']:.0f}-{words[-1]['end']:.0f}" if words else "EMPTY"
            print(f"clip {i:02d} {clip['slug']} [{track}]: {len(words)} words [{span}]")


if __name__ == "__main__":
    main()
