#!/usr/bin/env python3
"""Load rendered clips into Buffer as DRAFTS across TikTok / Instagram Reels / YouTube Shorts
(stage and queue; a human reviews and schedules). createPost + video-by-URL (Supabase). Captions
come from clips/captions.json (built from captions.md). Per-platform treatment:
  - TikTok:    caption + in-caption hashtags.
  - Instagram: caption + hashtags appended (IG first-comment needs a paid plan), type=reel.
  - YouTube:   strong title + #Shorts, hashtags/link in the description.

Usage:
  python3 buffer_schedule.py <pack> channels             # list connected channels
  python3 buffer_schedule.py <pack> tiktok test          # ONE draft (verify the API)
  python3 buffer_schedule.py <pack> tiktok go            # all TikTok drafts
  python3 buffer_schedule.py <pack> all go               # all drafts, all 3 platforms
"""
import json
import sys
import time
import urllib.request
import urllib.error
import os
from pathlib import Path

# Day-order posting list. Set "series" in pack.json (list of slugs, day 1 first)
# to control order and exclusions; without it every clip drafts in pack order.
# Drafts are created in series order so a later scheduling pass
# (start + interval x slot) maps day-perfect.

API = "https://api.buffer.com"
ORG = os.environ.get("BUFFER_ORG_ID", "")
IG_DISCOVERY = "#reels #reelsinstagram #explorepage #foundersofinstagram"


def token():
    tok = os.environ.get("BUFFER_ACCESS_TOKEN")
    if not tok:
        sys.exit("set BUFFER_ACCESS_TOKEN (grab it from an api.buffer.com request in devtools)")
    return tok


def gql(query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(API, data=body, method="POST", headers={
        "Authorization": f"Bearer {token()}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return {"errors": [{"message": f"HTTP {e.code}: {e.read().decode()[:300]}"}]}


def channels():
    q = "query($i:ChannelsInput!){ channels(input:$i){ id service name } }"
    out = {}
    for ch in gql(q, {"i": {"organizationId": ORG}}).get("data", {}).get("channels", []):
        out[ch["service"]] = ch["id"]
    return out


def load_captions(pack_dir):
    return json.load(open(pack_dir / "clips" / "captions.json"))


def build_post(caps, clip, service):
    c = caps.get(clip["slug"], {})
    hook = " ".join(str(x) for x in (clip.get("hook") or []) if x).strip().rstrip(".")
    if service == "instagram":
        text = "\n\n".join(x for x in [c.get("instagram", ""),
                                       (c.get("instagram_tags", "") + " " + IG_DISCOVERY).strip()] if x)
        meta = {"instagram": {"type": "reel", "shouldShareToFeed": True}}
    elif service == "youtube":
        text = c.get("yt_desc", "")
        title = (c.get("yt_title") or f"{hook} #Shorts")[:99]
        meta = {"youtube": {"title": title, "privacy": "public", "categoryId": "22"}}
    else:  # tiktok
        text = c.get("tiktok", "")
        meta = {"tiktok": {"title": hook[:90]}}
    return text, meta


CREATE = """mutation($i:CreatePostInput!){ createPost(input:$i){
  __typename
  ... on PostActionSuccess { post { id status } }
  ... on MutationError { message }
} }"""


def create_draft(channel, text, video_url, meta):
    inp = {"channelId": channel, "text": text, "schedulingType": "automatic",
           "assets": [{"video": {"url": video_url}}], "metadata": meta,
           "mode": "addToQueue", "saveToDraft": True}
    return gql(CREATE, {"i": inp})


def main():
    pack_dir = Path(sys.argv[1]).resolve()
    arg = sys.argv[2] if len(sys.argv) > 2 else "channels"
    if arg == "channels":
        print(json.dumps(channels(), indent=2))
        return
    mode = sys.argv[3] if len(sys.argv) > 3 else "go"
    pack = json.load(open(pack_dir / "pack.json"))
    urls = json.load(open(pack_dir / "clips" / "buffer_urls.json"))
    caps = load_captions(pack_dir)
    chmap = channels()
    services = ["tiktok", "instagram", "youtube"] if arg == "all" else [arg]
    summary = {}
    for service in services:
        ch = chmap.get(service)
        if not ch:
            print(f"no {service} channel (have: {list(chmap)})")
            continue
        # Idempotent: never re-draft a slug already successfully drafted for this service, so the
        # conductor can run `all go` after every new clip renders without creating duplicates.
        drafts_path = pack_dir / "clips" / f"buffer_drafts_{service}.json"
        existing = json.load(open(drafts_path)) if drafts_path.exists() else []
        done = {r["slug"] for r in existing if r.get("ok")}
        series = pack.get("series") or [c["slug"] for c in pack["clips"]]
        rank = {s: n for n, s in enumerate(series)}
        series_clips = sorted((c for c in pack["clips"] if c["slug"] in rank),
                              key=lambda c: rank[c["slug"]])
        clips = series_clips[:1] if mode == "test" else series_clips
        results = list(existing)
        made = 0
        for i, c in enumerate(clips):
            if c["slug"] in done:
                print(f"  {service:10s} clip {i:2d} {c['slug']:24s} -> already drafted, skip")
                continue
            if c["slug"] not in urls:
                print(f"  {service:10s} clip {i:2d} {c['slug']:24s} -> NO URL, skip")
                continue
            text, meta = build_post(caps, c, service)
            time.sleep(1.0)  # pace mutations — rapid churn trips Buffer's rate windows
            r = create_draft(ch, text, urls[c["slug"]], meta)
            node = r.get("data", {}).get("createPost", {})
            ok = node.get("__typename") == "PostActionSuccess"
            info = node.get("post", {}).get("id") if ok else (node.get("message") or r.get("errors"))
            print(f"  {service:10s} clip {i:2d} {c['slug']:24s} -> {'DRAFT '+str(info) if ok else 'ERR '+str(info)}")
            results.append({"clip": i, "slug": c["slug"], "service": service, "ok": ok,
                            "id": info if ok else None, "error": None if ok else str(info)})
            if ok:
                made += 1
        drafts_path.write_text(json.dumps(results, indent=2) + "\n")
        total_ok = sum(1 for r in results if r.get("ok"))
        summary[service] = f"+{made} new / {total_ok} total"
        print(f"{service}: {summary[service]} drafts -> clips/buffer_drafts_{service}.json\n")
    print("SUMMARY (drafts created):", json.dumps(summary))


if __name__ == "__main__":
    main()
