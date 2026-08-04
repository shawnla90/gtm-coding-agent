#!/usr/bin/env python3
"""v2 single-pass master encoder. RAW video(s) + lossless WAV(s) + alpha overlay MOV
-> one ffmpeg encode -> out/clip_NN_<slug>.mp4 (1080x1920@24, x264 CRF16 slow High10,
aac 256k mono). No intermediate encodes anywhere.

Modes: square | wide (lead speaker 1080p), guest (720p second-camera upscale-square),
duo (stacked native crops, both WAVs mixed). Speed baked in (setpts/atempo). 2-pass loudnorm measured on an
audio-only graph (fast), applied linear. Audio chain ends asetpts=N/SR/TB: the
atrim/concat/atempo graph can emit audio pts jumps that players ignore but any
downstream re-encode with timestamp-aware filters materializes as silence.

Usage: final_composite.py <pack-dir> <idx>
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

EQ = "eq=brightness=0.04:gamma=1.08:saturation=1.05"
DN_S = "hqdn3d=2:1.5:3:3"
DN_L = "hqdn3d=1.5:1:2:2"
INK = "0x14101a"
LN = "loudnorm=I=-14:TP=-1.5:LRA=11"


def seg_filters(tag_v, tag_a, vin, ain, segs, seek):
    parts, pairs = [], []
    for i, (s, e) in enumerate(segs):
        a, b = s - seek, e - seek
        parts.append(f"[{vin}]trim=start={a:.3f}:end={b:.3f},setpts=PTS-STARTPTS[{tag_v}{i}]")
        parts.append(f"[{ain}]atrim=start={a:.3f}:end={b:.3f},asetpts=PTS-STARTPTS[{tag_a}{i}]")
        pairs.append(f"[{tag_v}{i}][{tag_a}{i}]")
    parts.append(f"{''.join(pairs)}concat=n={len(segs)}:v=1:a=1[{tag_v}c][{tag_a}c]")
    return parts


def audio_measure(cmd_inputs, agraph_to_loudnorm):
    f = agraph_to_loudnorm + ",{}:print_format=json[aout]".format(LN)
    r = subprocess.run(["ffmpeg", "-y", "-v", "info", *cmd_inputs, "-filter_complex", f,
                        "-map", "[aout]", "-f", "null", "-"], capture_output=True, text=True)
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr, re.S)
    return json.loads(m.group(0)) if m else {}


def ln_applied(meas):
    if not meas:
        return LN
    return (f"{LN}:measured_I={meas['input_i']}:measured_TP={meas['input_tp']}:"
            f"measured_LRA={meas['input_lra']}:measured_thresh={meas['input_thresh']}:"
            f"offset={meas['target_offset']}:linear=true")


def main():
    pack_dir = Path(sys.argv[1]).expanduser().resolve()
    idx = int(sys.argv[2])
    pack = json.loads((pack_dir / "pack.json").read_text())
    clip = pack["clips"][idx]
    cut = json.loads((pack_dir / "transcripts" / f"clip_{idx:02d}.cut.json").read_text())
    segs = [(float(s), float(e)) for s, e in cut["segments"]]
    speed = float(cut["speed"])
    dur = float(cut["duration_sped"])
    mode = clip["mode"]
    srcs = pack["sources"]
    fr_file = pack_dir / "review" / "framing.json"
    framing = json.loads(fr_file.read_text()) if fr_file.exists() else {}
    sx = framing.get("clips", {}).get(str(idx), {}).get("face_x")
    overlay = pack_dir / "projects" / f"clip_{idx:02d}" / "renders" / "overlay.mov"
    out = pack_dir / "out" / f"clip_{idx:02d}_{clip['slug']}.mp4"
    out.parent.mkdir(exist_ok=True)

    seek = max(0.0, min(s for s, _ in segs) - 2.0)
    ss = ["-ss", f"{seek:.3f}"]

    speed_v = f"setpts=PTS/{speed},fps=24"
    tail = f"atempo={speed}"
    fst = cut.get("fade_start") or max(0.0, dur - 0.15)
    fade = f"aresample=48000,afade=t=out:st={fst:.3f}:d={max(0.10, dur - fst):.3f}"

    if mode == "duo":
        sxx = int(min(max((sx or pack["framing_defaults"]["speaker_a_face_x"]) - 540, 0), 840))
        lx = int(min(max(pack["framing_defaults"]["speaker_b_face_x"] - 540, 0), 200))
        inputs = [*ss, "-i", srcs["speaker_a_video"], "-i", str(overlay),
                  *ss, "-i", srcs["speaker_a_wav"], *ss, "-i", srcs["speaker_b_video"],
                  *ss, "-i", srcs["speaker_b_wav"]]
        parts = seg_filters("sv", "sa", "0:v", "2:a", segs, seek)
        parts += seg_filters("lv", "la", "3:v", "4:a", segs, seek)
        parts.append(f"[svc]{DN_S},format=yuv420p10le,{EQ},{speed_v},crop=1080:620:{sxx}:120[svf]")
        parts.append(f"[lvc]{DN_L},format=yuv420p10le,{speed_v},crop=1080:620:{lx}:20[lvf]")
        parts.append(f"color=c={INK}:s=1080x1920:r=24:d={dur + 0.2:.3f},format=yuv420p10le[bg]")
        parts.append("[bg][svf]overlay=0:370[t1]")
        parts.append("[t1][lvf]overlay=0:990[base]")
        agraph = "[sac][lac]amix=inputs=2:normalize=0," + tail
        measure_inputs = [*ss, "-i", srcs["speaker_a_wav"], *ss, "-i", srcs["speaker_b_wav"]]
        mparts = []
        for i, (s, e) in enumerate(segs):
            a, b = s - seek, e - seek
            mparts.append(f"[0:a]atrim=start={a:.3f}:end={b:.3f},asetpts=PTS-STARTPTS[ma{i}]")
            mparts.append(f"[1:a]atrim=start={a:.3f}:end={b:.3f},asetpts=PTS-STARTPTS[mb{i}]")
        mparts.append("".join(f"[ma{i}]" for i in range(len(segs))) + f"concat=n={len(segs)}:v=0:a=1[mac]")
        mparts.append("".join(f"[mb{i}]" for i in range(len(segs))) + f"concat=n={len(segs)}:v=0:a=1[mbc]")
        mgraph = ";".join(mparts) + f";[mac][mbc]amix=inputs=2:normalize=0,{tail}"
        meas = audio_measure(measure_inputs, mgraph)
        parts.append(f"[sac][lac]amix=inputs=2:normalize=0,{tail},{ln_applied(meas)},{fade},asetpts=N/SR/TB[aout]")
    else:
        track = clip["lead"]
        vsrc, asrc = srcs[f"{track}_video"], srcs[f"{track}_wav"]
        inputs = [*ss, "-i", vsrc, "-i", str(overlay), *ss, "-i", asrc]
        parts = seg_filters("v", "a", "0:v", "2:a", segs, seek)
        if mode == "square":
            x = int(min(max((sx or pack["framing_defaults"]["speaker_a_face_x"]) - 540, 0), 840))
            frame = f"crop=1080:1080:{x}:0"
            y = 430
            chain = f"{DN_S},format=yuv420p10le,{EQ},{speed_v},{frame}"
        elif mode == "wide":
            chain = f"{DN_S},format=yuv420p10le,{EQ},{speed_v},scale=1080:608:flags=lanczos"
            y = 676
        else:  # guest
            lx = int(min(max((sx or pack["framing_defaults"]["speaker_b_face_x"]) - 360, 0), 560))
            chain = f"{DN_L},format=yuv420p10le,{speed_v},crop=720:720:{lx}:0,scale=1080:1080:flags=lanczos"
            y = 430
        parts.append(f"[vc]{chain}[vf]")
        parts.append(f"color=c={INK}:s=1080x1920:r=24:d={dur + 0.2:.3f},format=yuv420p10le[bg]")
        parts.append(f"[bg][vf]overlay=0:{y}[base]")
        mparts = []
        for i, (s, e) in enumerate(segs):
            a, b = s - seek, e - seek
            mparts.append(f"[0:a]atrim=start={a:.3f}:end={b:.3f},asetpts=PTS-STARTPTS[m{i}]")
        mparts.append("".join(f"[m{i}]" for i in range(len(segs))) + f"concat=n={len(segs)}:v=0:a=1[mc]")
        mgraph = ";".join(mparts) + f";[mc]{tail}"
        meas = audio_measure([*ss, "-i", asrc], mgraph)
        parts.append(f"[ac]{tail},{ln_applied(meas)},{fade},asetpts=N/SR/TB[aout]")

    parts.append("[1:v]format=yuva444p10le,setparams=range=tv:colorspace=bt709[g]")
    parts.append("[base][g]overlay=0:0:format=auto:alpha=straight:eof_action=repeat[vout]")

    cmd = ["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(parts),
           "-map", "[vout]", "-map", "[aout]",
           "-c:v", "libx264", "-preset", "slow", "-crf", "16",
           "-pix_fmt", "yuv420p10le", "-g", "48", "-movflags", "+faststart",
           "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-ac", "1",
           "-t", f"{dur + 0.04:.3f}", str(out)]
    subprocess.run(cmd, check=True)
    mb = out.stat().st_size / 1048576
    print(f"clip {idx:02d} {clip['slug']}: master {dur:.1f}s {mb:.1f}MB [{mode}]")


if __name__ == "__main__":
    main()
