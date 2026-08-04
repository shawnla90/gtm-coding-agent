#!/usr/bin/env python3
"""v2: generate a GRAPHICS-ONLY HyperFrames project per clip — transparent root, no
media elements. Footage never touches the browser; ffmpeg composites later.

Reads pack.json, clips/clip_NN.words.json (sped, spk-tagged), transcripts/clip_NN.cut.json,
review/framing.json (optional cameo source ranges). Writes projects/clip_NN/public/index.html.

Usage: compose_overlay.py <pack-dir> <idx>
"""
from __future__ import annotations

import html
import json
import shutil
import sys
from pathlib import Path

ASSETS = Path(__file__).resolve().parent / "assets"
GSAP_URL = "https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"


def ensure_gsap() -> Path:
    """gsap ships under the GreenSock no-charge license, so it is fetched at
    first run rather than committed to the repo."""
    dst = ASSETS / "vendor" / "gsap.min.js"
    if not dst.exists():
        import urllib.request
        dst.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(GSAP_URL, dst)
    return dst
FPS = 24

OFFWHITE = "#FFFBFF"
LIME = "#E8FFCF"
PURPLE = "#642585"
SOFTP = "#D9AFD0"
DIM = "rgba(255,251,255,0.55)"

GEOM = {
    "square": {"hook_h": 430, "vid_top": 430, "pill_top": 1530, "cta_top": 1745, "kick_mt": 96},
    "guest":  {"hook_h": 430, "vid_top": 430, "pill_top": 1530, "cta_top": 1745, "kick_mt": 96},
    "wide":   {"hook_h": 430, "vid_top": 676, "pill_top": 1530, "cta_top": 1745, "kick_mt": 96},
    "duo":    {"hook_h": 370, "vid_top": 370, "pill_top": 1640, "cta_top": 1836, "kick_mt": 64},
}


def group_pills(words):
    pills, cur = [], []

    def flush():
        if cur:
            pills.append({"words": cur[:], "start": cur[0]["start"], "end": cur[-1]["end"],
                          "spk": cur[0].get("spk", "speaker_a")})
            cur.clear()

    for w in words:
        if not w["text"].strip():
            continue
        if cur:
            gap = w["start"] - cur[-1]["end"]
            tlen = sum(len(x["text"]) + 1 for x in cur)
            if (w.get("spk") != cur[0].get("spk") or gap > 0.6 or len(cur) >= 5
                    or tlen + len(w["text"]) > 26
                    or (len(cur) >= 3 and cur[-1]["text"].rstrip()[-1:] in ".?!")):
                flush()
        cur.append(w)
    flush()
    return pills


def hook_px(lines):
    return max(44, min(84, int(1846 / max(max(len(l) for l in lines), 1))))


def remap_cameo(ranges, segments, speed):
    spans, acc = [], 0.0
    for s, e in segments:
        for r in ranges:
            lo, hi = max(s, r["start"]), min(e, r["end"])
            if hi - lo > 0.5:
                spans.append(((lo - s + acc) / speed, (hi - s + acc) / speed))
        acc += e - s
    spans.sort()
    merged = []
    for s, e in spans:
        if merged and s - merged[-1][1] < 1.0:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    return merged


def build_html(clip, dur, pills, cameo_spans, g):
    kicker = html.escape(clip.get("kicker") or "THE PODCAST")
    lines = [html.escape(l) for l in clip["hook"]]
    hpx = hook_px(clip["hook"])
    cta = html.escape(clip["cta"])
    duo = clip["mode"] == "duo"
    d = f"{dur:.3f}"

    hosts, tl = [], []
    # Hook/CTA fully dressed at frame 0 — the natural first frame IS the thumbnail
    # (downloads, upload pickers, platform covers). No entrance fades up top.
    tl.append("tl.set('.card-host[data-card-id=\"hook\"]',{visibility:'visible',opacity:1,y:0},0);")
    tl.append("tl.set('.card-host[data-card-id=\"cta\"]',{visibility:'visible',opacity:1},0);")
    if duo:
        for tag in ("tag-a", "tag-b"):
            tl.append(f"tl.set('.card-host[data-card-id=\"{tag}\"]',{{visibility:'visible',opacity:1}},0);")

    for p_i, pill in enumerate(pills):
        s = max(0.02, pill["start"] - 0.05)
        e = min(dur - 0.04, pill["end"] + 0.12)
        if p_i + 1 < len(pills):
            e = min(e, max(pills[p_i + 1]["start"] - 0.06, pill["end"]))
        if e - s < 0.15:
            continue
        spans = "".join(
            f'<span class="w" id="w-{p_i}-{k}">{html.escape(w["text"])}</span> '
            for k, w in enumerate(pill["words"]))
        cls = "pill pill-b" if pill["spk"] == "speaker_b" else "pill"
        hosts.append(
            f'<div class="card-host clip pill-host" id="pill-{p_i}" data-card-id="pill-{p_i}" '
            f'data-start="{s:.3f}" data-duration="{e - s:.3f}" data-track-index="4" '
            f'style="left:40px;top:{g["pill_top"]}px;width:1000px;height:190px;visibility:hidden;opacity:0;">'
            f'<div class="card"><div class="{cls}">{spans}</div></div></div>')
        sel = f".card-host[data-card-id=\"pill-{p_i}\"]"
        active = SOFTP if pill["spk"] == "speaker_b" else OFFWHITE
        tl.append(f"tl.set('{sel}',{{visibility:'visible'}},{s:.3f});")
        tl.append(f"tl.fromTo('{sel}',{{opacity:0,y:10}},{{opacity:1,y:0,duration:0.18,ease:'power2.out'}},{s:.3f});")
        tl.append(f"tl.to('{sel}',{{opacity:0,duration:0.12,ease:'power1.in'}},{max(s, e - 0.13):.3f});")
        for k, w in enumerate(pill["words"]):
            t = max(s + 0.01, min(w["start"], e - 0.05))
            tl.append(f"tl.to('#w-{p_i}-{k}',{{color:'{active}',duration:0.13,ease:'power1.out'}},{t:.3f});")

    for b_i, (bs, be) in enumerate(cameo_spans):
        s, e = max(0.0, bs), min(dur - 0.05, be)
        if e - s < 0.5:
            continue
        show_e = min(s + 4.2, e)
        hosts.append(
            f'<div class="card-host clip" id="cameo-{b_i}" data-card-id="cameo-{b_i}" '
            f'data-start="{s:.3f}" data-duration="{show_e - s:.3f}" data-track-index="5" '
            f'style="left:0;top:{g["vid_top"] - 112}px;width:1080px;height:96px;visibility:hidden;opacity:0;">'
            f'<div class="card"><div class="cameo">{html.escape(clip.get("cameo_text") or "")}</div></div></div>')
        sel = f".card-host[data-card-id=\"cameo-{b_i}\"]"
        tl.append(f"tl.set('{sel}',{{visibility:'visible'}},{s:.3f});")
        tl.append(f"tl.fromTo('{sel}',{{opacity:0,y:-8}},{{opacity:1,y:0,duration:0.3,ease:'power2.out'}},{s + 0.05:.3f});")
        tl.append(f"tl.to('{sel}',{{opacity:0,duration:0.3,ease:'power1.in'}},{show_e - 0.32:.3f});")

    if duo:
        # composite always stacks speaker_a top / speaker_b bottom — tags follow the footage
        names = clip.get("speaker_names") or {}
        a_name = names.get("speaker_a", "speaker a")
        b_name = names.get("speaker_b", "speaker b")
        hosts.append(
            f'<div class="card-host clip" id="tag-a" data-card-id="tag-a" data-start="0" '
            f'data-duration="{dur - 0.06:.3f}" data-track-index="6" '
            f'style="left:24px;top:{370 + 620 - 66}px;width:300px;height:52px;visibility:hidden;opacity:0;">'
            f'<div class="card"><div class="ntag">{a_name}</div></div></div>')
        hosts.append(
            f'<div class="card-host clip" id="tag-b" data-card-id="tag-b" data-start="0" '
            f'data-duration="{dur - 0.06:.3f}" data-track-index="6" '
            f'style="left:24px;top:{990 + 620 - 66}px;width:300px;height:52px;visibility:hidden;opacity:0;">'
            f'<div class="card"><div class="ntag">{b_name}</div></div></div>')

    hook_lines = "".join(f'<div class="hl{" hl2" if i == 1 else ""}">{l}</div>' for i, l in enumerate(lines))
    nl = "\n      "
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <style>
      @font-face {{ font-family: "Inter"; src: url("fonts/Inter-400-latin.woff2") format("woff2"); font-weight: 400; font-display: block; }}
      @font-face {{ font-family: "Inter"; src: url("fonts/Inter-700-latin.woff2") format("woff2"); font-weight: 700; font-display: block; }}
      * {{ box-sizing: border-box; }}
      html, body {{ margin: 0; padding: 0; width: 100%; height: 100%; overflow: hidden;
        background: transparent; font-family: "Inter", ui-sans-serif, system-ui, sans-serif; }}
      #stage {{ position: relative; width: 100%; height: 100%; overflow: hidden; background: transparent; }}
      .card-host {{ position: absolute; pointer-events: none; overflow: hidden; }}
      .card-host .card {{ position: relative; width: 100%; height: 100%; overflow: hidden; }}
      .kicker {{ font: 700 30px/1 "Inter"; letter-spacing: 7px; color: {LIME};
        opacity: 0.85; text-align: center; margin-top: {g["kick_mt"]}px; }}
      .kbar {{ width: 64px; height: 5px; background: {PURPLE}; margin: 22px auto 26px; border-radius: 3px; }}
      .hl {{ font: 700 {hpx}px/1.16 "Inter"; color: {OFFWHITE}; text-align: center;
        letter-spacing: -1px; padding: 0 34px; }}
      .hl2 {{ color: {LIME}; }}
      .pill-host .card {{ display: flex; align-items: flex-start; justify-content: center; }}
      .pill {{ display: inline-block; background: rgba(10,8,14,0.82); border-radius: 22px;
        padding: 26px 38px; font: 700 46px/1.3 "Inter"; text-align: center; max-width: 1000px;
        border: 1px solid rgba(100,37,133,0.55); }}
      .pill-b {{ border: 1px solid rgba(217,175,208,0.55); }}
      .pill .w {{ color: {DIM}; }}
      .cta {{ font: 400 33px/1 "Inter"; color: rgba(232,255,207,0.78); text-align: center;
        letter-spacing: 0.5px; }}
      .cameo {{ font: 700 36px/1 "Inter"; color: {OFFWHITE}; text-align: center;
        background: rgba(100,37,133,0.82); border-radius: 16px; display: inline-block;
        white-space: nowrap; padding: 18px 34px; margin-left: 50%; transform: translateX(-50%); }}
      .ntag {{ font: 700 26px/1 "Inter"; letter-spacing: 2px; color: rgba(255,251,255,0.85);
        background: rgba(10,8,14,0.62); border-radius: 10px; display: inline-block; padding: 10px 18px; }}
    </style>
  </head>
  <body>
    <div id="stage" data-composition-id="ls-overlay" data-start="0" data-duration="{d}"
      data-fps="{FPS}" data-width="1080" data-height="1920">
      <div class="card-host clip" id="hook-card" data-card-id="hook" data-start="0"
        data-duration="{dur - 0.04:.3f}" data-track-index="2"
        style="left:0;top:0;width:1080px;height:{g["hook_h"]}px;visibility:hidden;opacity:0;">
        <div class="card">
          <div class="kicker">{kicker}</div>
          <div class="kbar"></div>
          {hook_lines}
        </div>
      </div>
      <div class="card-host clip" id="cta-card" data-card-id="cta" data-start="0"
        data-duration="{dur - 0.45:.3f}" data-track-index="3"
        style="left:0;top:{g["cta_top"]}px;width:1080px;height:80px;visibility:hidden;opacity:0;">
        <div class="card"><div class="cta">{cta}</div></div>
      </div>
      {nl.join(hosts)}
      <script src="vendor/gsap.min.js"></script>
      <script>
        (function () {{
          const tl = window.gsap.timeline({{ paused: true }});
          {nl.join(tl)}
          window.__timelines = window.__timelines || {{}};
          window.__timelines["ls-overlay"] = tl;
        }})();
      </script>
    </div>
  </body>
</html>
"""


def main():
    pack_dir = Path(sys.argv[1]).expanduser().resolve()
    idx = int(sys.argv[2])
    pack = json.loads((pack_dir / "pack.json").read_text())
    clip = pack["clips"][idx]
    cut = json.loads((pack_dir / "transcripts" / f"clip_{idx:02d}.cut.json").read_text())
    words = json.loads((pack_dir / "clips" / f"clip_{idx:02d}.words.json").read_text())
    dur = float(cut["duration_sped"])
    g = GEOM[clip["mode"]]

    cameo_spans = []
    if clip["mode"] == "wide":
        fr = pack_dir / "review" / "framing.json"
        if fr.exists():
            ranges = json.loads(fr.read_text()).get("cameo", [])
            cameo_spans = remap_cameo(ranges, cut["segments"], float(cut["speed"]))

    proj = pack_dir / "projects" / f"clip_{idx:02d}" / "public"
    if proj.parent.exists():
        shutil.rmtree(proj.parent)
    (proj / "fonts").mkdir(parents=True)
    (proj / "vendor").mkdir()
    for f in (ASSETS / "fonts").glob("Inter-*.woff2"):
        shutil.copy(f, proj / "fonts" / f.name)
    shutil.copy(ensure_gsap(), proj / "vendor" / "gsap.min.js")

    pills = group_pills(words)
    (proj / "index.html").write_text(build_html(clip, dur, pills, cameo_spans, g))
    print(f"clip {idx:02d} {clip['slug']}: overlay {dur:.1f}s, {len(pills)} pills, mode={clip['mode']}"
          + (f", cameo={[(round(a,1),round(b,1)) for a,b in cameo_spans]}" if cameo_spans else ""))


if __name__ == "__main__":
    main()
