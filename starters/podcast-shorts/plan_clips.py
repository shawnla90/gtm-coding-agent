#!/usr/bin/env python3
"""v2 cut planner — pure computation, no encoding.

Per clip: anchors/blocks/drops -> ordered source segments (silence jump-cuts computed
on the MERGED word stream for duo clips, so neither speaker's lines get cut) ->
transcripts/clip_NN.cut.json  {segments:[[s,e],...], duration_src, duration_sped, warnings}
clips/clip_NN.words.json      sped-timeline words [{text,start,end,spk}]

Usage: plan_clips.py <pack-dir> [idx]
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

LEAD, TAIL, HEAD = 0.20, 0.50, 0.15
# whisper word-end timestamps run ~0.1s early; END_COMP keeps the final word's
# decay, BLEED lets the cut ride into the next word's attack (the end fade masks it)
END_COMP, BLEED = 0.12, 0.15
GAP_CUT = 1.40
MIN_CUT = 0.40

# word-SEQUENCE fixes whisper's text-level pass can't express (merges span two word slots)
WORD_FIXES = [
    # add your product/brand names here — whisper mangles proper nouns.
    # each entry: (tuple of consecutive misheard words, replacement string)
    (("Cloud", "Code"), "Claude Code"),
    (("open", "AI"), "OpenAI"),
    (("sass",), "SaaS"), (("sass,",), "SaaS,"), (("Sass",), "SaaS"),
    (("cool", "email"), "cold email"),
]


def apply_word_fixes(words):
    out, i = [], 0
    while i < len(words):
        matched = False
        for seq, rep in WORD_FIXES:
            if len(seq) <= len(words) - i and all(
                    words[i + k]["text"].strip().strip(".,?!").lower() == seq[k].strip(".,?!").lower()
                    for k in range(len(seq))):
                tail_punct = ""
                last_raw = words[i + len(seq) - 1]["text"].strip()
                if last_raw and last_raw[-1] in ".,?!" and not rep[-1] in ".,?!":
                    tail_punct = last_raw[-1]
                out.append({"text": rep + tail_punct, "start": words[i]["start"],
                            "end": words[i + len(seq) - 1]["end"]})
                i += len(seq)
                matched = True
                break
        if not matched:
            out.append(words[i])
            i += 1
    return out


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()


def find_anchor(words, text, from_end=False):
    target = norm(text).split()
    if not target:
        return None
    toks = [norm(w["text"]) for w in words]
    n, m = len(toks), len(target)
    cands = []
    for i in range(0, n - 1):
        if not toks[i] or (toks[i] != target[0] and not (len(toks[i]) >= 3 and target[0].startswith(toks[i]))):
            continue
        j, k, hits, first, last = i, 0, 0, None, None
        while j < n and k < m and (j - i) < m * 2 + 4:
            if toks[j] and (toks[j] == target[k] or (len(toks[j]) >= 3 and target[k].startswith(toks[j]))):
                hits += 1
                if first is None:
                    first = j
                last = j
                k += 1
            j += 1
        if hits >= max(2, int(m * 0.6)) and first is not None:
            cands.append((first, last, hits))
    if not cands:
        return None
    best = max(c[2] for c in cands)
    good = [c for c in cands if c[2] >= best - 1]
    pick = min(good, key=lambda c: (c[1] - c[0], -c[0] if from_end else c[0]))
    return (pick[0], pick[1])


def span_from_anchors(words, start_text, end_text, w_in, w_out, warn):
    """Returns (t_in, t_out, legit_end) — legit_end is the anchor word's end so
    callers can suppress ghost captions for bled-into next words."""
    t_in, t_out, legit_end = float(w_in), float(w_out), None
    a = find_anchor(words, start_text)
    if a:
        t_in = max(0.0, words[a[0]]["start"] - LEAD)
        if a[0] > 0:
            t_in = max(t_in, words[a[0] - 1]["end"] + 0.03)
    else:
        warn.append(f"start anchor missing: {start_text[:40]}")
    b = find_anchor(words, end_text, from_end=True)
    if b:
        legit_end = words[b[1]]["end"]
        t_out = legit_end + END_COMP + TAIL
        if b[1] + 1 < len(words):
            t_out = min(t_out, words[b[1] + 1]["start"] + BLEED)
        t_out = max(t_out, legit_end + END_COMP + 0.05)
    else:
        warn.append(f"end anchor missing: {end_text[:40]}")
    return t_in, t_out, legit_end


def jumpcut(words, t_in, t_out):
    """Silence jump-cuts within [t_in,t_out] using the given (merged) word stream."""
    inside = [w for w in words if w["start"] >= t_in - 0.01 and w["end"] <= t_out + 0.01]
    if not inside:
        return [(t_in, t_out)]
    segs = []
    seg_start = max(0.0, inside[0]["start"] - LEAD, t_in)
    prev_end = inside[0]["end"]
    for w in inside[1:]:
        if w["start"] - prev_end > GAP_CUT:
            kept = prev_end + TAIL
            nxt = w["start"] - HEAD
            if nxt - kept >= MIN_CUT:
                segs.append((seg_start, kept))
                seg_start = nxt
        prev_end = max(prev_end, w["end"])
    segs.append((seg_start, min(prev_end + TAIL, t_out)))
    return segs


def apply_drops(segs, words, drops, warn):
    spans = []
    for dr in drops:
        da = find_anchor(words, dr["from"])
        db = find_anchor(words, dr["to"])
        if da and db and words[db[1]]["end"] > words[da[0]]["start"]:
            ds = words[da[0]]["start"] + 0.08
            if da[0] > 0:
                ds = min(ds, words[da[0] - 1]["end"] + TAIL)
                ds = max(ds, words[da[0] - 1]["end"] + 0.02)
            de = words[db[1]]["end"] + 0.10
            if db[1] + 1 < len(words):
                de = min(de, words[db[1] + 1]["start"] - 0.02)
            spans.append((ds, max(de, ds + 0.2)))
        else:
            warn.append(f"drop missing: {dr['from'][:34]}")
    for ds, de in sorted(spans):
        nxt = []
        for s, e in segs:
            if de <= s or ds >= e:
                nxt.append((s, e))
            else:
                if ds - s > 0.3:
                    nxt.append((s, ds))
                if e - de > 0.3:
                    nxt.append((de, e))
        segs = nxt
    return segs


def process(pack_dir, pack, i, clip):
    speed = float(pack.get("speed", 1.0))
    warn = []
    tracks = ["speaker_a", "speaker_b"] if clip["mode"] == "duo" else [clip["lead"]]
    tw = {}
    for t in tracks:
        f = pack_dir / "transcripts" / f"clip_{i:02d}.words.{t}.source.json"
        tw[t] = apply_word_fixes(json.loads(f.read_text())["words"])
    lead_words = tw[clip["lead"]]
    merged = sorted(
        [dict(w, spk=t) for t in tracks for w in tw[t]], key=lambda w: w["start"])

    segs, ghost_zones = [], []
    if "blocks" in clip:
        for blk in clip["blocks"]:
            t_in, t_out, legit_end = span_from_anchors(lead_words, blk["from"], blk["to"],
                                                       clip["start"], clip["end"], warn)
            if legit_end is not None:
                ghost_zones.append((legit_end, t_out))
            segs.extend(jumpcut(merged, t_in, t_out))
    else:
        t_in, t_out, legit_end = span_from_anchors(lead_words, clip["start_text"], clip["end_text"],
                                                   clip["start"], clip["end"], warn)
        if legit_end is not None:
            ghost_zones.append((legit_end, t_out))
        segs = jumpcut(merged, t_in, t_out)
        segs = apply_drops(segs, lead_words, clip.get("drops", []), warn)

    dur_src = sum(e - s for s, e in segs)
    dur_sped = dur_src / speed
    if dur_sped > 90.5:
        warn.append(f"SPED DURATION {dur_sped:.1f}s > 90s")

    offsets, acc = [], 0.0
    for s, e in segs:
        offsets.append((s, e, acc))
        acc += e - s
    out_words = []
    for w in merged:
        if any(le - 0.02 <= w["start"] < be for le, be in ghost_zones):
            continue
        for s, e, off in offsets:
            if s - 0.02 <= w["start"] and w["end"] <= e + 0.05:
                out_words.append({
                    "text": w["text"], "spk": w["spk"],
                    "start": round((w["start"] - s + off) / speed, 3),
                    "end": round(min(w["end"] - s + off, acc) / speed, 3)})
                break
    out_words.sort(key=lambda w: w["start"])
    fade_start = None
    if out_words:
        last_end = max(w["end"] for w in out_words)
        fade_start = round(max(0.0, min(max(last_end + 0.12, dur_sped - 0.40),
                                        dur_sped - 0.12)), 3)
    (pack_dir / "clips").mkdir(exist_ok=True)
    (pack_dir / "clips" / f"clip_{i:02d}.words.json").write_text(json.dumps(out_words, indent=0))
    plan = {"slug": clip["slug"], "mode": clip["mode"], "segments": [[round(s, 3), round(e, 3)] for s, e in segs],
            "duration_src": round(dur_src, 2), "duration_sped": round(dur_sped, 3),
            "speed": speed, "n_words": len(out_words), "fade_start": fade_start, "warnings": warn}
    (pack_dir / "transcripts" / f"clip_{i:02d}.cut.json").write_text(json.dumps(plan, indent=1))
    return plan


def main():
    pack_dir = Path(sys.argv[1]).expanduser().resolve()
    pack = json.loads((pack_dir / "pack.json").read_text())
    only = int(sys.argv[2]) if len(sys.argv) > 2 else None
    for i, clip in enumerate(pack["clips"]):
        if only is not None and i != only:
            continue
        p = process(pack_dir, pack, i, clip)
        flag = ("  ⚠ " + "; ".join(p["warnings"])) if p["warnings"] else ""
        print(f"clip {i:02d} {p['slug']}: {p['duration_sped']:.1f}s sped "
              f"({p['duration_src']}s src, {len(p['segments'])} segs, {p['n_words']} words){flag}")


if __name__ == "__main__":
    main()
