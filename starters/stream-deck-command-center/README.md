# Stream Deck Command Center Starter

The runnable kit behind [Chapter 25](../../chapters/25-stream-deck-command-center.md): a Stream Deck + layout generated from Python, with project keys that drop you into Claude Code in the right repo, Claude Code command keys, a content kickoff pipeline, and an open-only page for Elgato's MCP server.

macOS only. Built for the Stream Deck + (8 keys, 4 dials). Other models work if you change `SD_PLUS` and the slot grid in `profile/build_profile.py`.

## What's in the box

| Path | What it does |
|---|---|
| `config.example.sh` | paths and app names the launchers read. Copy to `config.sh` (gitignored) |
| `projects.example.toml` | your repos: model, effort, GitHub account, workflow keys. Copy to `projects.toml` (gitignored) |
| `build_apps.sh` | wraps the silent launchers as tiny `.app` bundles so a press doesn't leave a Terminal window open |
| `profile/build_profile.py` | writes `out/<PROFILE_NAME>.streamDeckProfile` (and `--mcp` for the MCP Deck) |
| `profile/icons.py` | renders 144px key art from real app icons and favicons, with a letter-tile fallback |
| `profile/preview.py` | contact sheet of every page, so you check the art before Stream Deck sees it |
| `profile/deploy_live.sh` | pushes a rebuild into the live profile without re-importing (read the rule below) |
| `profile/projects.py` | reads `projects.toml` for the builder and the launchers |
| `icons/fetch_icons.sh` | pulls icons out of installed `.app` bundles and site favicons into `icons/src/` |
| `launchers/` | `claude-project.command` (the project launcher), `claude`, `codex`, `capture-idea`, `ai-workbench` |
| `kickoffs/` | `content-new` (Claude drafts), `content-critique` (second opinion via clipboard), `content-render` (Codex renders), `content-open` (the human gate) |
| `mcp/claude-mcp-config.example.json` | the Elgato MCP server entry for Claude Desktop or Claude Code |

## Setup

Needs Stream Deck 7.x, Python 3.11+ with Pillow (`pip3 install pillow`), and the `claude`, `codex` and `gh` CLIs on your PATH.

```bash
# Put the kit OUTSIDE ~/Documents, ~/Desktop and ~/Downloads (see Gotchas)
cp -R starters/stream-deck-command-center ~/stream-deck-kit && cd ~/stream-deck-kit
cp config.example.sh config.sh           # edit: PROJECT_DIR, NOTES_DIR, CRITIC_APP, ...
cp projects.example.toml projects.toml   # edit: one [[project]] per repo
./icons/fetch_icons.sh                   # optional: real key art (edit the lists first)
./build_apps.sh
python3 profile/build_profile.py
python3 profile/preview.py && open profile/preview.png
open "out/Command Center.streamDeckProfile"   # first time only: imports the profile
```

After the first import, every change is: edit, rebuild, `./profile/deploy_live.sh`.

## The one rule: deploy in place

Never move or delete a live profile folder in `~/Library/Application Support/com.elgato.StreamDeck/ProfilesV3/`, and don't re-import a second copy over the first. If the active profile disappears, Stream Deck reports data loss, restores its daily backup, and any profile newer than that backup is gone.

`deploy_live.sh` does it the safe way: backs up `ProfilesV3` and the prefs to `~/.streamdeck-backups/<timestamp>/`, quits Stream Deck cleanly, swaps the page folders inside the same profile folder (same profile UUID), relaunches, and greps the Stream Deck log for a restore. Quit means quit: it refuses to touch files while the app is running.

## Project keys

Each `[[project]]` becomes a key on the PROJECTS page. That key opens a folder:

- **Claude**: Terminal opens in the repo and runs `claude --model <model> --effort <effort> -n "<name>"`.
- **One key per workflow**: same, plus the workflow's prompt as the first message, and its own model/effort if set.
- **Open Repo** in Finder, and **PRs** if you set `github`.

The launcher scopes GitHub per terminal. If `gh_user` is set it runs `export GH_TOKEN=$(gh auth token --user <gh_user>)` before starting Claude. Use `gh auth login` once per account; never `gh auth switch` from a key, because it changes the account for every other terminal and agent on the machine.

Stream Deck's Open action can't pass arguments, so the builder writes one 3-line wrapper per key into `generated/` that calls `launchers/claude-project.command <id> [workflow]`. Test any key from a terminal first: `./launchers/claude-project.command acme Status`.

## Claude Code command keys

The CLAUDE page types into whatever window has focus: `/compact`, `/effort max`, `/model`, `/clear`, plus Esc (interrupt) and Shift+Tab (cycle permission mode). Click into the Claude Code terminal, then press.

## Content kickoffs

KICKOFF page, in order:

1. **New Pack**: asks for a topic, makes `DRAFTS_DIR/<date>-<slug>/`, starts Claude Code drafting it against your `VOICE_FILE`.
2. **Critique**: copies every draft plus a critique prompt to the clipboard and opens `CRITIC_APP`. Press Cmd+V there. A different model catches what the drafter can't see.
3. **Render**: starts Codex in the pack folder to build a 1080x1920 MP4 and a GIF with the toolkit in `RENDER_KIT_DIR`.
4. **Drafts**: opens the folder. You read it and decide what ships.

Every prompt in this kit tells the agent not to post, send or schedule. Keep it that way. Publishing is a human step.

## Elgato MCP (optional)

1. Stream Deck Preferences > General > Enable MCP Deck. That creates a virtual deck.
2. `python3 profile/build_profile.py --mcp`, then `open "out/MCP Actions.streamDeckProfile"` and assign it to the MCP Deck.
3. Merge `mcp/claude-mcp-config.example.json` into your Claude config (Claude Desktop: Settings > Developer > Edit Config; Claude Code: `claude mcp add elgato -- npx --yes @elgato/mcp-server@latest`). Restart.
4. Ask the agent which Stream Deck actions it can see, then have it press Capture Idea.

The agent sees only the MCP Deck. The builder puts open-only actions there on purpose. Don't add anything that publishes, sends, deletes or spends.

## Gotchas

- **`~/Documents` blocks launchers.** macOS privacy protection stops Stream Deck-launched scripts from reading there, and they fail without an error. Keep the kit, notes and drafts elsewhere.
- **The MCP Deck UUID changes** when you re-enable it or Stream Deck restores a backup. The builder reads it live from your profiles each run.
- **Don't drive the Stream Deck app with synthetic clicks** (AppleScript, computer-use agents). Its menus ignore them or misfire. Edit files with the app quit instead.
- **npm 11 skips install scripts by default.** If you build a plugin with a native dependency and it silently does nothing, run `npm install-scripts approve <pkg>`.
- **Dictation key**: the HOME page sends Ctrl+Option+Space. Set your dictation app's shortcut to that; Fn-based shortcuts can't be sent by Stream Deck.
- **Codex dials**: set `CODEX_PLUGIN=1` only after installing Elgato's ChatGPT & Codex plugin from the Marketplace, or those dials import blank.
