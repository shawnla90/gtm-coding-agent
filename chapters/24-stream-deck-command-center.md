# Chapter 24: The Stream Deck Command Center

**One key press opens Claude Code in the right repo, on the right model, at the right effort, signed into the right GitHub account, with the first prompt already typed. The whole layout is generated from a Python file, so the deck is version-controlled like everything else in this kit. This chapter is how I built it, the content pipeline that rides on top, and the afternoon I lost two Stream Deck profiles finding out how not to deploy one.**

---

A Stream Deck looks like a streamer toy. For a GTM coding agent it's something more useful: a physical layer over the commands you type fifty times a day. `/compact`. `/effort max`. Esc to stop a run going sideways. `cd ~/code/the-client-repo && claude --model opus --effort high`. Each one is a few seconds. Across a day of four or five parallel sessions in different repos, those seconds and the context switches around them add up.

The trap is building it the way Elgato's app wants you to: dragging actions onto keys, one at a time, by hand. That works for eight keys. It falls apart at forty keys across seven pages, and it's invisible to your agent. So the rule for this chapter matches the rest of the kit: if it can be code, it's code.

---

## The Hardware, Briefly

I use the Stream Deck+: 8 LCD keys in a 4x2 grid, 4 rotary dials with a touch strip, about $200. Everything here works on other models if you change the grid size in the builder. The dials matter more than I expected. Volume and key brightness are the boring defaults; a live usage readout on a dial is the one I actually glance at.

The layout I landed on:

| Page | Keys |
|---|---|
| HOME | PROJECTS, CLAUDE, KICKOFF folders, Codex CLI, Capture Idea, Workbench, GitHub PRs, Dictate |
| CLAUDE | New Claude, `/compact`, `/effort max`, `/model`, Esc, Shift+Tab, `/clear` |
| PROJECTS | one key per repo, each opening a folder of that project's workflows |
| KICKOFF | New Pack, Critique, Render, Drafts |

Folder key 0,0 is always back. That one convention is what keeps nested pages from feeling like a maze.

---

## Generate the Profile, Don't Drag It

A `.streamDeckProfile` file is a zip. Inside: a `package.json`, and a `Profiles/<UUID>.sdProfile/` folder holding a `manifest.json` for the profile, one `manifest.json` per page, and an `Images/` folder of key art. Export any profile from the Stream Deck app, unzip it, and the format reads clearly. Each key is a JSON object keyed by its grid position:

```python
def typed(key, text, title, enter=True):
    """System > Text: types `text` into the focused window (your Claude Code terminal)."""
    return action(key, "com.elgato.streamdeck.system.text", "Text",
                  {"isSendingEnter": enter, "pastedText": text}, title)

pages["claude"] = ("CLAUDE", {
    "0,0": back("k0", "HOME"),
    "2,0": typed("k2", "/compact", "/compact"),
    "3,0": typed("k3", "/effort max", "/effort max"),
    "1,1": hotkey("k5", 53, 16777216, "Stop"),               # Esc interrupts Claude
    "2,1": hotkey("k6", 48, 16777218, "Mode", shift=True),   # Shift+Tab cycles permission mode
}, dials("k"))
```

`build_profile.py` assembles those pages, renders the art, zips it, and writes `out/Command Center.streamDeckProfile`. Double-click it and Stream Deck imports it. Three details made it reliable:

- **Deterministic UUIDs.** Every action and page id is `uuid5(namespace, key_name)`. Rebuild and you get the same ids, so a diff of the generated manifests shows exactly what changed.
- **Dead-key check.** Before writing, the builder walks every Open action and confirms the target file exists. A typo fails the build instead of producing a key that silently does nothing.
- **Device read live.** The device block in a profile embeds your hardware serial. The builder reads it from your existing profiles instead of hardcoding it, which also means the starter carries nothing machine-specific.

Now the deck is a file your agent can edit. "Add a key on the CLAUDE page that types /cost" is a one-line change Claude Code can make, preview, and deploy.

---

## Real Key Art

Text-only keys are hard to read at arm's length. Real icons fix that, and you already have them on disk.

App icons come out of the `.app` bundle. `Info.plist` names the icon file, and `sips` converts the `.icns`:

```bash
icon="$(defaults read "$app/Contents/Info" CFBundleIconFile)"
sips -s format png --resampleHeightWidthMax 256 "$app/Contents/Resources/${icon%.icns}.icns" --out app-claude.png
```

Some newer apps ship only an asset catalog with no `.icns`; `qlmanage -t` renders the bundle icon anyway. Site icons come from the site itself: `/apple-touch-icon.png` first (180px and usually clean), `/favicon.ico` as a last resort.

`icons.py` turns those sources into 144x144 keys with Pillow, with the label baked into the image so it stays crisp. Four styles cover everything: `single` (one icon over a label, with an optional white plate for dark favicons), `grid` (2x2 mini icons for folders, tinted with the folder's accent), `glyph` (a big monospace `/c` or `esc` for command keys) and `back`. Missing source? You get a colored letter tile instead of a crash, so a fresh clone renders on day one.

Then `preview.py` lays every page out as one contact sheet PNG. Look at it before Stream Deck ever sees the file. It's much faster than squinting at the hardware.

---

## The Deploy-in-Place Rule

Here's the expensive lesson. To push an update, I deleted the old profile folder from `~/Library/Application Support/com.elgato.StreamDeck/ProfilesV3/` and imported the new build. Stream Deck noticed the active profile had vanished, flagged it as data loss, restored its daily backup, and every profile newer than that backup was gone. Two profiles, gone.

The rule since then: **never move or delete a live profile folder, and never re-import a second copy over the first.** Import once. After that, `deploy_live.sh` updates the profile in place:

1. Rebuild the profile.
2. Find exactly one live profile with the right name on the right device. Zero or two matches: stop.
3. Back up all of `ProfilesV3` and the app prefs to a timestamped folder.
4. Quit Stream Deck and wait until the process is really gone. Still running: stop, nothing changed.
5. Swap the page folders inside the same profile folder, so the profile UUID never changes.
6. Relaunch and grep the Stream Deck log for `data loss` or `RestoreBackup`.

Same profile UUID, new pages. Stream Deck sees a profile whose contents changed while it was closed, which is a normal event, instead of a profile that disappeared.

---

## Claude Code Command Keys

The CLAUDE page is the one I use most. System > Text types a string into the focused window and can press Enter after it; System > Hotkey sends a key combo. Click into your Claude Code terminal and press:

- **/compact** when a long session starts to drift.
- **/effort max** before the hard part of a task, without retyping it.
- **/model** to open the picker.
- **Esc** to interrupt a run you can see going wrong. Having a physical stop button changes how comfortably you let an agent run.
- **Shift+Tab** to cycle permission modes.

One caveat: Text types into whatever has focus. Press `/clear` while your cursor sits in a Slack message box and Slack gets it.

---

## Project Launcher Keys

This is the part that turned the deck from shortcuts into a command center. Each repo you work in gets an entry in `projects.toml`:

```toml
[[project]]
id = "acme"
name = "Acme GTM"
path = "~/code/acme-gtm"
gh_user = "example-user"
model = "opus"
effort = "high"
github = "https://github.com/example-org/acme-gtm/pulls"

  [[project.workflow]]
  label = "Status"
  prompt = "Read the repo's CLAUDE.md and recent git log. Tell me what's in flight, what's blocked, and the next three steps. Don't change anything."
```

Each project becomes a key on the PROJECTS page that opens a folder: a plain Claude key, one key per workflow, Open Repo, and PRs. One press runs `launchers/claude-project.command`:

```zsh
cd "$P_PATH"
if [ -n "$P_GH_USER" ]; then
  export GH_TOKEN="$(gh auth token --user "$P_GH_USER")"
fi
exec claude -n "$P_SESSION" --model "$P_MODEL" --effort "$P_EFFORT" "$P_PROMPT"
```

Four things happen in that one press. The terminal lands in the right repo, so Claude loads that repo's `CLAUDE.md`. The model and effort match the work: a client site tweak doesn't need max effort, a pipeline rebuild does. `-n` names the session, so `/resume` and the terminal tab tell you which project is which when five are open. And the workflow prompt goes in as the first message, so a "Status" press is a status report thirty seconds later.

The `GH_TOKEN` line deserves its own paragraph. If you work across GitHub accounts (yours, a client's org, a bot), the obvious move is `gh auth switch`. Don't put that on a key. It changes the active account for the whole machine, so every other terminal and every other agent session flips accounts mid-task, and the next push from another window goes out as the wrong user. `gh auth token --user` prints the token for one logged-in account, and exporting it as `GH_TOKEN` scopes that account to this one shell. Log into each account once with `gh auth login`, and each project key picks its own.

Stream Deck's Open action can't pass arguments to a script, so the builder writes one three-line wrapper per key into `generated/` that calls the launcher with the project id and workflow label. Every key can be tested from a terminal before it's ever on the deck: `./launchers/claude-project.command acme Status`.

---

## Agentic Content Kickoffs

The KICKOFF page runs a content pipeline across three different agents, with a human at the end:

1. **New Pack** asks for a topic in a Terminal window, creates `~/content/drafts/<date>-<slug>/` with a `brief.md`, and starts Claude Code drafting it against your voice file. The prompt ends with "do not publish, post, schedule or send anything."
2. **Critique** concatenates every draft plus a critique prompt, puts it on the clipboard, and opens a second app (ChatGPT by default, any chat app works). Press Cmd+V. A different model reading the drafter's output catches the patterns the drafter can't see in itself: the em dashes, the "it's not X, it's Y", the three-part lists.
3. **Render** starts Codex in the pack folder to build a 1080x1920 MP4 with captions and a looping GIF from your local video toolkit, writing to `renders/`.
4. **Drafts** opens the folder in Finder. That's the human gate. You read, you edit, you decide what ships.

Why the clipboard? Desktop chat apps don't offer a reliable "open with this prompt" hook, and only an API can sit inside an unattended chain. The clipboard hand-off is one Cmd+V, works with any app, and keeps a human looking at the critique before it feeds back into the draft. The state between keys is one file, `~/content/kickoffs/current`, holding the active slug, so each key knows which folder to act on without asking.

The point of the gate: nothing in this pipeline can post. Agents draft, critique and render. Publishing stays a deliberate human action, and every prompt says so.

---

## Elgato MCP: Let the Agent Press Keys

Elgato ships an MCP server, `@elgato/mcp-server`. Turn on Preferences > General > Enable MCP Deck and Stream Deck creates a virtual deck. Register the server with Claude Code (`claude mcp add elgato -- npx --yes @elgato/mcp-server@latest`) and the agent can list and trigger the actions on that deck. I asked Claude to press Capture Idea through it and a fresh note template opened in TextEdit.

The agent sees only the MCP Deck, not your other profiles. That boundary is the feature. The builder's `--mcp` flag generates that page with open-only actions: Capture Idea, the workbench, the drafts folder, each project's repo in Finder. Nothing that publishes, sends, deletes or spends goes on it. An agent that can press a key is an agent that can press it at 3am in a loop; keep the keys boring.

---

## A Usage Dial

A dial with a live readout of today's token usage and cost is the most-glanced-at thing on my deck. The pattern is general: some local tool already writes a usage snapshot to disk (a menu-bar tracker, a cron job over your provider's usage API, your own logging), and a small Stream Deck plugin reads that file every 30 seconds and draws it on the dial.

Plugins use Elgato's Node SDK (`@elgato/streamdeck`, SDK v2) and run on the Node runtime Stream Deck bundles. In `manifest.json`, give the action `"Controllers": ["Encoder"]` and `"Encoder": { "layout": "$A1" }` (a title plus a value) so `setFeedback` has somewhere to draw. The core is short. This is a sketch, not a drop-in: the snapshot path and its fields depend on whatever writes your file.

```js
import streamDeck, { action, SingletonAction } from "@elgato/streamdeck";
import { readFile } from "node:fs/promises";

const SNAPSHOT = `${process.env.HOME}/.local/share/usage/last-snapshot.json`;

@action({ UUID: "com.example.usage.dial" })
class UsageDial extends SingletonAction {
  onWillAppear(ev) {
    const tick = async () => {
      try {
        const s = JSON.parse(await readFile(SNAPSHOT, "utf8"));
        await ev.action.setFeedback({ title: "Today", value: `${s.tokens} · $${s.cost}` });
      } catch {
        await ev.action.setFeedback({ title: "Today", value: "no data" });
      }
    };
    tick();
    this.timer = setInterval(tick, 30_000);
  }
  onWillDisappear() { clearInterval(this.timer); }
}

streamDeck.actions.registerAction(new UsageDial());
streamDeck.connect();
```

Scaffold the plugin with Elgato's CLI (`npm i -g @elgato/cli && streamdeck create`), symlink the `.sdPlugin` folder into `~/Library/Application Support/com.elgato.StreamDeck/Plugins/`, and add its action UUID to a dial in `build_profile.py`. Reading a local file means no API key lives in the plugin.

---

## Gotchas

- **macOS privacy blocks launchers under `~/Documents`.** Also `~/Desktop` and `~/Downloads`. A script started by Stream Deck can't read there, and it fails without an error dialog. Keep the kit, notes and drafts elsewhere.
- **The MCP Deck UUID changes.** Re-enabling MCP Deck or a backup restore gives the virtual deck a new id, and a profile bound to the old one goes nowhere. Read it live every build.
- **Synthetic GUI clicks on Stream Deck are unreliable.** I tried letting an agent drive the Stream Deck app with scripted clicks. Menus ignored them, and one run created a stray virtual device I had to remove by hand. Edit the files with the app quit; that's the whole reason the deploy script exists.
- **npm 11 skips install scripts by default.** Building a plugin with a native dependency that installs but silently does nothing? `npm install-scripts approve <pkg>`.
- **Text keys type into whatever has focus.** Click the terminal first.
- **Fn shortcuts can't be sent.** Stream Deck's Hotkey action can't send Fn combos. If your dictation app defaults to one, change it to something like Ctrl+Option+Space and point a key at that.

---

## Closing Exercise

1. Copy `starters/stream-deck-command-center/` outside `~/Documents`, fill in `config.sh` and `projects.toml` with two of your real repos, run `./build_apps.sh` and `python3 profile/build_profile.py`, and open `preview.png`. You don't need a Stream Deck for this part.
2. Run one workflow key from the terminal: `./launchers/claude-project.command <id> Status`. Check `gh auth status` in that window versus another one. Only the new window should show the project's account.
3. If you own a deck: import once, then change one key in the builder and push it with `deploy_live.sh`. Open the backup folder it made and confirm you could roll back by hand.

---

## Key Takeaways

- Generate the profile from code. A `.streamDeckProfile` is a zip of JSON and PNGs, and a Python builder makes the deck diffable, reviewable and editable by your agent.
- Deploy in place. Never move or delete a live profile folder; swap pages inside the same profile UUID with the app quit, after a backup.
- Project keys carry the whole setup: repo, model, effort, session name, first prompt, and a GitHub account scoped to that one terminal with `GH_TOKEN` instead of a global `gh auth switch`.
- Multi-agent pipelines can live on keys: Claude drafts, a second model critiques via the clipboard, Codex renders, and a human gate decides what ships.
- Give an agent hardware access through Elgato's MCP Deck only, and only for open-only actions.

---

Runnable version of everything above: `starters/stream-deck-command-center/`.
