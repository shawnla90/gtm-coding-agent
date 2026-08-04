#!/usr/bin/env python3
"""QA gate for delivery encodes vs masters. Checks the full spectrum the v3e-v6
generations each missed one dimension of: audio content (silence regions must
match the master, cross-correlation lag <=25ms at 5 windows), container timing
(IDR at pts 0, uniform 24fps packet deltas), and duration drift <=0.1s.

Usage: qa_delivery.py <delivery-dir-name> <suffix> [pack-dir]   e.g. qa_delivery.py delivery _social mypack
Exit 1 if any clip fails.
"""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path

import numpy as np

HERE = Path(sys.argv[3]).resolve() if len(sys.argv) > 3 else Path.cwd()
SR = 48000


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def silences(f):
    r = run(["ffmpeg", "-v", "info", "-i", str(f), "-af", "silencedetect=n=-45dB:d=0.4",
             "-f", "null", "-"])
    return r.stderr.count("silence_start")


def duration(f):
    r = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(f)])
    return float(r.stdout.strip())


def pcm(f, secs):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(f), "-map", "0:a:0",
                        "-t", str(secs), "-f", "s16le", "-ar", str(SR), "-ac", "1", "-"],
                       capture_output=True)
    return np.frombuffer(r.stdout, dtype=np.int16).astype(np.float64)


def max_lag_ms(m, d, windows=(0.2, 1.0, 2.0, 5.0, 10.0), win_s=1.0, max_lag_s=0.5):
    worst = 0.0
    L, ML = int(win_s * SR), int(max_lag_s * SR)
    for t in windows:
        a = int(t * SR)
        if a + L + ML >= min(len(m), len(d)):
            continue
        w = m[a:a + L]
        if np.sqrt(np.mean(w * w)) < 100:      # silent window: correlation meaningless
            continue
        ml = min(ML, a)
        seg = d[a - ml:a + L + ML]
        c = np.correlate(seg, w, mode="valid")
        lag = (np.argmax(c) - ml) / SR * 1000
        worst = max(worst, abs(lag))
    return worst


def video_packets(f, secs=1.0):
    r = run(["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-read_intervals", f"%+{secs}", "-show_entries",
             "packet=pts_time,duration_time,flags", "-of", "csv=p=0", str(f)])
    rows = [l.split(",") for l in r.stdout.strip().splitlines()]
    first_key = rows[0][2].startswith("K") and float(rows[0][0]) == 0.0
    uniform = all(abs(float(x[1]) - 1 / 24) < 1e-4 for x in rows if x[1])
    return first_key, uniform


def main():
    ddir = sys.argv[1] if len(sys.argv) > 1 else "delivery"
    suf = sys.argv[2] if len(sys.argv) > 2 else "_social"
    pack = json.loads((HERE / "pack.json").read_text())
    fails = 0
    print(f"{'clip':34s} {'sil m/d':>8s} {'lag ms':>7s} {'dur d':>7s} {'K@0':>4s} {'cfr':>4s}")
    for i, c in enumerate(pack["clips"]):
        m = HERE / "out" / f"clip_{i:02d}_{c['slug']}.mp4"
        d = HERE / "out" / ddir / f"clip_{i:02d}_{c['slug']}{suf}.mp4"
        if not d.exists():
            print(f"clip_{i:02d}_{c['slug']}: MISSING"); fails += 1; continue
        sm, sd = silences(m), silences(d)
        lag = max_lag_ms(pcm(m, 12.5), pcm(d, 12.5))
        dd = abs(duration(m) - duration(d))
        k0, cfr = video_packets(d)
        ok = sm == sd and lag <= 25 and dd <= 0.1 and k0 and cfr
        fails += 0 if ok else 1
        print(f"clip_{i:02d}_{c['slug']:24s} {sm:>3d}/{sd:<3d} {lag:7.1f} {dd:7.3f} "
              f"{'ok' if k0 else 'BAD':>4s} {'ok' if cfr else 'BAD':>4s}  {'PASS' if ok else 'FAIL'}")
    print("ALL PASS" if fails == 0 else f"{fails} FAILURES")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
