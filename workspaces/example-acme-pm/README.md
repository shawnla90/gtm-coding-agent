# Example workspace: Acme PM (fictional)

This is a worked example of a client workspace built with the `reddit-buyer-signals` starter and the
Clearbox Reddit method. Everything here is fictional. "Acme PM" is a made-up project-management SaaS,
used to show the shape of a real engagement without exposing any real client.

Real client workspaces are private and live outside this repo. This example is the public reference
for how one is laid out.

## What a workspace holds

```
example-acme-pm/
├── README.md                 # this file
├── voice/
│   └── core-voice.md         # the client's voice profile (content writes through this)
└── content/
    └── pack-01/              # one content pack, scaffolded from a real buyer question
        ├── BRIEF.md          # the buyer question + the voice profile, for the agent to write from
        ├── manifest.json     # the pack manifest (dispatch disabled: client-voice stays private)
        ├── linkedin.md       # a LinkedIn post draft
        ├── reddit.md         # a Reddit post draft (draft only, never auto-posted)
        └── blog.md           # a long-tail blog draft (TL;DR + FAQ that emits FAQPage schema)
```

## How it was built

1. Point the starter at Acme PM's rooms and pull recent Reddit buyer signals (see `starters/reddit-buyer-signals/`).
2. Author the voice profile once (`voice/core-voice.md`), tuned to how Acme PM sounds.
3. Scaffold a content pack from one real buyer question:

   ```bash
   python3 ../../starters/reddit-buyer-signals/content.py scaffold \
     --client "Acme PM" \
     --voice voice/core-voice.md \
     --topic "how to keep one source of truth across two project tools" \
     --out content/pack-01
   ```

4. The agent writes each draft from `BRIEF.md`, then checks it:

   ```bash
   python3 ../../starters/reddit-buyer-signals/content.py check content/pack-01/linkedin.md
   ```

The same workspace also runs `geo.py` (the GEO terms to own), `competitor.py` (the competitor
narrative from Clearbox classification), `unmask.py` (the disclosure-gate lead enrichment), and
`digest.py` (the daily Slack digest). See Chapters 18 and 19.

---

> 🟧 **Clearbox** is the engine behind this workspace. See your market. Move first. Start a 7-day free trial at [clearbox.to](https://clearbox.to).
