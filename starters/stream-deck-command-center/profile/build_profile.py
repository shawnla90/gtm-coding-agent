#!/usr/bin/env python3
"""Generate a .streamDeckProfile for the Stream Deck + (4x2 keys, 4 dials) from code.

    python3 profile/build_profile.py          # writes out/<PROFILE_NAME>.streamDeckProfile
    python3 profile/build_profile.py --mcp    # also writes out/MCP Actions.streamDeckProfile

First time: `open "out/Command Center.streamDeckProfile"` and Stream Deck imports it.
After that, push changes with profile/deploy_live.sh, which swaps pages inside the live
profile instead of importing a second copy.

Layout (edit PAGES below):
  HOME      PROJECTS, CLAUDE, KICKOFF folders + Codex, Capture Idea, Workbench, GitHub, Dictate
  CLAUDE    keys that type Claude Code commands into the focused terminal
  PROJECTS  one key per [[project]] in projects.toml, each opening a folder of workflow keys
  KICKOFF   the content pipeline: New Pack -> Critique -> Render -> Drafts

The file format mirrors Stream Deck 7.x ProfilesV3 exports: a zip holding package.json and
Profiles/<PROFILE>.sdProfile/{manifest.json, Profiles/<PAGE>/manifest.json, Images/*.png}.
UUIDs are deterministic (uuid5 of a key name), so rebuilding produces the same ids.
"""
import glob
import json
import os
import platform
import re
import stat
import subprocess
import sys
import uuid
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import icons  # noqa: E402
import projects as projects_mod  # noqa: E402

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(KIT, "out")
GEN_DIR = os.path.join(KIT, "generated")
LIVE = os.path.expanduser("~/Library/Application Support/com.elgato.StreamDeck/ProfilesV3")
NS = uuid.UUID("0b6f3f0e-3c55-4b8e-9a51-6d1d2a7c9e10")  # change it if you fork the layout
SD_PLUS = "20GBD9901"  # Stream Deck + model id


def uid(name):
    return str(uuid.uuid5(NS, name))


# ---------------------------------------------------------------- config + device

def load_config():
    """Source config.sh (or the example) in bash and read the variables back."""
    path = os.path.join(KIT, "config.sh")
    if not os.path.exists(path):
        print("note: no config.sh yet, building from config.example.sh")
        path = os.path.join(KIT, "config.example.sh")
    out = subprocess.run(["bash", "-c", 'set -a; source "$1"; env -0', "_", path],
                         capture_output=True, text=True, check=True).stdout
    return dict(kv.split("=", 1) for kv in out.split("\0") if "=" in kv)


def live_device(model):
    """The device block from an existing profile for this model, newest first.

    A device UUID embeds the hardware serial, so it's read live instead of hardcoded.
    The virtual MCP Deck gets a new UUID whenever it's re-enabled or a backup is restored,
    which is the other reason never to hardcode it."""
    for m in sorted(glob.glob(LIVE + "/*.sdProfile/manifest.json"), key=os.path.getmtime, reverse=True):
        try:
            dev = json.load(open(m)).get("Device", {})
        except (OSError, ValueError):
            continue
        if dev.get("Model") == model:
            return dev
    return None


# ---------------------------------------------------------------- action builders

ART = {}  # action key -> callable returning PNG bytes; filled in as pages are defined


def state(title):
    return [{"FontFamily": "", "FontSize": 12, "FontStyle": "", "FontUnderline": False,
             "OutlineThickness": 2, "ShowTitle": True, "Title": title,
             "TitleAlignment": "bottom", "TitleColor": "#ffffff"}]


def action(key, uuid_, name, settings, title, plugin=None, art=None):
    a = {"ActionID": uid(key), "LinkedTitle": False, "Name": name, "Resources": None,
         "Settings": settings, "State": 0, "States": state(title), "UUID": uuid_}
    if plugin:
        a["Plugin"] = plugin
    if art:  # baked key art replaces the text title
        a["States"][0]["Image"] = "Images/%s.png" % key.upper()
        a["States"][0]["ShowTitle"] = False
        a["_png"] = art()
    return a


def open_path(key, path, title, art=None):
    """System > Open: runs a .command (in Terminal), an .app, or opens a folder."""
    return action(key, "com.elgato.streamdeck.system.open", "Open", {"path": '"%s"' % path}, title, art=art)


def kit(key, rel, title, art=None):
    return open_path(key, os.path.join(KIT, rel), title, art)


def web(key, url, title, art=None):
    return action(key, "com.elgato.streamdeck.system.website", "Website",
                  {"openInBrowser": True, "path": url}, title, art=art)


def folder(key, page, title, art=None):
    return action(key, "com.elgato.streamdeck.profile.openchild", "Create Folder",
                  {"ProfileUUID": uid(page)}, title,
                  {"Name": "Create Folder", "UUID": "com.elgato.streamdeck.profile.openchild", "Version": "1.0"},
                  art=art)


def back(key, label="BACK"):
    return action(key, "com.elgato.streamdeck.profile.backtoparent", "Parent Folder", {}, label,
                  art=lambda: icons.back(label))


def typed(key, text, title, enter=True, art=None):
    """System > Text: types `text` into the focused window (your Claude Code terminal)."""
    return action(key, "com.elgato.streamdeck.system.text", "Text",
                  {"isSendingEnter": enter, "pastedText": text}, title, art=art)


_EMPTY_HK = {"KeyCmd": False, "KeyCtrl": False, "KeyModifiers": 0, "KeyOption": False, "KeyShift": False,
             "NativeCode": -1, "QTKeyCode": 33554431, "VKeyCode": -1}


def hotkey(key, native, qt, title, shift=False, ctrl=False, option=False, art=None):
    """System > Hotkey: one key combo. native = macOS virtual key code, qt = Qt key code."""
    mods = (1 if shift else 0) | (2 if ctrl else 0) | (8 if option else 0)
    hk = {"KeyCmd": False, "KeyCtrl": ctrl, "KeyModifiers": mods, "KeyOption": option, "KeyShift": shift,
          "NativeCode": native, "QTKeyCode": qt, "VKeyCode": native}
    return action(key, "com.elgato.streamdeck.system.hotkey", "Hotkey",
                  {"Coalesce": True, "Hotkeys": [hk, _EMPTY_HK, _EMPTY_HK, _EMPTY_HK]}, title,
                  {"Name": "Activate a Key Command", "UUID": "com.elgato.streamdeck.system.hotkey", "Version": "1.0"},
                  art=art)


def dial_volume(key):
    return action(key, "com.elgato.streamdeck.system.multimedia", "Multimedia", {"actionIdx": 18}, "Volume",
                  {"Name": "Multimedia", "UUID": "com.elgato.streamdeck.system.multimedia", "Version": "1.0"})


def dial_brightness(key):
    return action(key, "com.elgato.streamdeck.system.keybrightness", "Brightness", {"actionIdx": 0}, "Brightness",
                  {"Name": "Brightness", "UUID": "com.elgato.streamdeck.system.keybrightness", "Version": "1.0"})


CODEX = {"Name": "Codex", "UUID": "com.elgato.openai-codex", "Version": "1.0.0.8"}


def dial_codex(key, act, title, settings=None):
    """Dials from Elgato's ChatGPT & Codex plugin (install it from the Marketplace first)."""
    return action(key, "com.elgato.openai-codex." + act, title, settings or {}, title, CODEX)


# ---------------------------------------------------------------- generated wrappers

def wrapper(name, args):
    """Stream Deck's Open action can't pass arguments, so each project key gets a 3-line
    .command in generated/ that calls launchers/claude-project.command with its args."""
    os.makedirs(GEN_DIR, exist_ok=True)
    path = os.path.join(GEN_DIR, name + ".command")
    quoted = " ".join("'%s'" % a.replace("'", "'\\''") for a in args)
    with open(path, "w") as f:
        f.write("#!/bin/zsh -l\n# generated by build_profile.py, do not edit\n"
                'exec "%s" %s\n' % (os.path.join(KIT, "launchers", "claude-project.command"), quoted))
    os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


# ---------------------------------------------------------------- pages

SLOTS = ["1,0", "2,0", "3,0", "0,1", "1,1", "2,1", "3,1"]  # every key except 0,0 (back)
_s, _g, _gl = icons.single, icons.grid, icons.glyph
ORANGE, PURPLE = (255, 159, 10), (124, 92, 255)


def build_pages(cfg, projects):
    pages = {}

    def dials(prefix):
        d = {"0,0": dial_volume(prefix + "d1"), "3,0": dial_brightness(prefix + "d4")}
        if cfg.get("CODEX_PLUGIN") == "1":
            d["1,0"] = dial_codex(prefix + "d2", "power", "Codex Power", {"actionContractVersion": 1})
            d["2,0"] = dial_codex(prefix + "d3", "usage", "Codex Usage")
        return d

    proj_icons = [p.get("icon", "x-" + p["id"]) for p in projects]

    pages["home"] = ("HOME", {
        "0,0": folder("h1", "projects", "PROJECTS", lambda: _g(proj_icons, "PROJECTS", PURPLE)),
        "1,0": folder("h2", "claude", "CLAUDE",
                      lambda: _g(["app-claude", "app-terminal"], "CLAUDE", icons.CLAUDE_ORANGE)),
        "2,0": folder("h3", "kickoff", "KICKOFF",
                      lambda: _g(["app-claude", "app-chatgpt", "app-codex", "app-finder"], "KICKOFF", ORANGE)),
        "3,0": kit("h4", "launchers/codex.command", "Codex", lambda: _s("app-codex", "Codex CLI")),
        "0,1": kit("h5", "apps/capture-idea.app", "Capture\nIdea", lambda: _s("app-textedit", "Capture Idea")),
        "1,1": kit("h6", "apps/ai-workbench.app", "Workbench",
                   lambda: _g(["app-chatgpt", "app-claude", "app-terminal", "web-github"], "Workbench")),
        "2,1": web("h7", "https://github.com/pulls", "GitHub", lambda: _s("web-github", "GitHub PRs", plate=True)),
        # Dictation: set your dictation app's hands-free shortcut to Ctrl+Option+Space.
        # Fn-based shortcuts can't be sent by Stream Deck.
        "3,1": hotkey("h8", 49, 32, "Dictate", ctrl=True, option=True, art=lambda: _gl("mic", "Dictate", PURPLE)),
    }, dials("h"))

    # Claude Code commands, typed into whatever window has focus.
    pages["claude"] = ("CLAUDE", {
        "0,0": back("k0", "HOME"),
        "1,0": kit("k1", "launchers/claude.command", "New\nClaude", lambda: _s("app-claude", "New Claude")),
        "2,0": typed("k2", "/compact", "/compact", art=lambda: _gl("/c", "/compact")),
        "3,0": typed("k3", "/effort max", "/effort max", art=lambda: _gl("max", "/effort max")),
        "0,1": typed("k4", "/model", "/model", art=lambda: _gl("/m", "/model")),
        "1,1": hotkey("k5", 53, 16777216, "Stop", art=lambda: _gl("esc", "Stop")),             # Esc interrupts
        "2,1": hotkey("k6", 48, 16777218, "Mode", shift=True, art=lambda: _gl("⇧tab", "Mode")),  # Shift+Tab
        "3,1": typed("k7", "/clear", "/clear", art=lambda: _gl("clr", "/clear")),
    }, dials("k"))

    # PROJECTS: one folder key per project.
    if len(projects) > len(SLOTS):
        print("note: only the first %d projects fit on the PROJECTS page" % len(SLOTS))
    proj_keys = {"0,0": back("p0", "HOME")}
    for slot, p in zip(SLOTS, projects):
        pid, color = p["id"], tuple(p.get("color", PURPLE))
        icon = p.get("icon", "x-" + p["name"])
        proj_keys[slot] = folder("p-" + pid, "proj-" + pid, p["name"],
                                 lambda icon=icon, p=p, color=color: _g([icon, "app-claude"], p["name"], color))

        keys = {"0,0": back("pb-" + pid)}
        extras = [open_path("pf-" + pid, p["path"], "Finder", lambda: _s("app-finder", "Open Repo"))]
        if p.get("github"):
            extras.append(web("pg-" + pid, p["github"], "PRs", lambda: _s("web-github", "PRs", plate=True)))
        room = len(SLOTS) - 1 - len(extras)
        flows = p["workflow"][:room]
        if len(p["workflow"]) > room:
            print("note: %s has %d workflows, %d fit" % (pid, len(p["workflow"]), room))
        launch = [open_path("pc-" + pid, wrapper(pid, [pid]), "Claude",
                            lambda icon=icon, p=p: _s(icon, p["name"][:12]))]
        for w in flows:
            label = w["label"]
            launch.append(open_path("pw-%s-%s" % (pid, slug(label)),
                                    wrapper("%s--%s" % (pid, slug(label)), [pid, label]), label,
                                    lambda label=label, color=color: _gl(label[:4].lower(), label, color)))
        for slot2, a in zip(SLOTS, launch + extras):
            keys[slot2] = a
        pages["proj-" + pid] = (p["name"][:20].upper(), keys, dials("p" + pid))
    pages["projects"] = ("PROJECTS", proj_keys, dials("pp"))

    pages["kickoff"] = ("KICKOFF", {
        "0,0": back("q0", "HOME"),
        "1,0": kit("q1", "kickoffs/content-new.command", "New\nPack", lambda: _gl("+", "New Pack", ORANGE)),
        "2,0": kit("q2", "apps/content-critique.app", "Critique", lambda: _s("app-chatgpt", "Critique")),
        "3,0": kit("q3", "kickoffs/content-render.command", "Render", lambda: _s("app-codex", "Render")),
        "0,1": kit("q4", "apps/content-open.app", "Drafts", lambda: _s("app-finder", "Drafts")),
    }, dials("q"))
    return pages


def mcp_keys(projects):
    """Keys for the virtual MCP Deck (Preferences > General > Enable MCP Deck).
    An agent connected to Elgato's MCP server can see and press ONLY these. Keep them
    open-only: never put publish, send, delete or pay actions here."""
    keys = {
        "0,0": kit("m1", "apps/capture-idea.app", "Capture Idea", lambda: _s("app-textedit", "Capture Idea")),
        "1,0": kit("m2", "apps/ai-workbench.app", "Open AI Workbench",
                   lambda: _g(["app-chatgpt", "app-claude", "app-terminal", "web-github"], "Workbench")),
        "2,0": kit("m3", "apps/content-open.app", "Open Content Drafts", lambda: _s("app-finder", "Drafts")),
    }
    for i, p in enumerate(projects[:5]):
        keys["%d,0" % (i + 3)] = open_path("mp-" + p["id"], p["path"], "Open %s repo" % p["name"],
                                           lambda p=p: _s(p.get("icon", "x-" + p["name"]), p["name"][:12]))
    return keys


# ---------------------------------------------------------------- write

def page_manifest(name, keys, dials=None):
    ctrls = [{"Actions": keys, "Type": "Keypad"}]
    if dials is not None:
        ctrls.append({"Actions": dials, "Type": "Encoder"})
    return {"Controllers": ctrls, "Icon": "", "Name": name}


def images(page, keys):
    """Move each action's rendered art into {page}/Images/<KEY>.png."""
    out = {}
    for a in keys.values():
        png = a.pop("_png", None)
        if png:
            out["%s/%s" % (page, a["States"][0]["Image"])] = png
    return out


def package(model, required):
    return {"AppVersion": "7.6.0.23012", "DeviceModel": model, "DeviceSettings": None, "FormatVersion": 1,
            "OSType": "macOS", "OSVersion": platform.mac_ver()[0] or "15.0", "RequiredPlugins": required}


def write(path, files):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        os.remove(path)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data if isinstance(data, bytes) else json.dumps(data, indent=2))


def check_targets(pages):
    """Every Open target must exist or the key is dead on press."""
    missing = []
    for _, keys, _ in pages.values():
        for a in keys.values():
            p = a["Settings"].get("path", "").strip('"')
            if a["UUID"].endswith("system.open") and not os.path.exists(p):
                missing.append(p)
    return missing


def main():
    cfg = load_config()
    projects = projects_mod.load()
    name = cfg.get("PROFILE_NAME", "Command Center")

    device = live_device(SD_PLUS)
    if not device:
        print("note: no Stream Deck + profile found on this Mac; writing a device-less profile. "
              "Import still works, Stream Deck asks which device to use.")
        device = {"Model": SD_PLUS, "UUID": ""}

    pages = build_pages(cfg, projects)
    missing = check_targets(pages)
    # Repo folders that don't exist yet only warn; missing kit files are fatal.
    fatal = [m for m in missing if m.startswith(KIT)]
    for m in missing:
        if m not in fatal:
            print("warning: project path does not exist yet:", m)
    if fatal:
        raise SystemExit("Missing launcher targets (run ./build_apps.sh first?):\n  " + "\n  ".join(fatal))

    profile_id = uid("profile").upper()
    default_page = uid("default-page")
    base = "Profiles/%s.sdProfile" % profile_id
    root = {
        "package.json": package(SD_PLUS, ["com.elgato.openai-codex"] if cfg.get("CODEX_PLUGIN") == "1" else []),
        base + "/manifest.json": {
            "Device": device, "Name": name, "Version": "3.0",
            "Pages": {"Current": uid("home"), "Default": default_page, "Pages": [uid("home")]},
        },
        "%s/Profiles/%s/manifest.json" % (base, default_page.upper()): page_manifest("", None, None),
    }
    for key, (title, keys, dials) in pages.items():
        page = "%s/Profiles/%s" % (base, uid(key).upper())
        root.update(images(page, keys))
        root[page + "/manifest.json"] = page_manifest(title, keys, dials)
    out = os.path.join(OUT_DIR, name + ".streamDeckProfile")
    write(out, root)
    print("wrote %s (%d pages, %d projects)" % (out, len(pages), len(projects)))

    if "--mcp" in sys.argv:
        dev = live_device("AI Stream Deck")
        if not dev:
            raise SystemExit("No MCP Deck found: enable Stream Deck Preferences > General > Enable MCP Deck first.")
        keys = mcp_keys(projects)
        mid, mpage, mdefault = uid("mcp-profile").upper(), uid("mcp-page"), uid("mcp-default")
        mbase = "Profiles/%s.sdProfile" % mid
        files = {
            "package.json": package(dev["Model"], []),
            mbase + "/manifest.json": {"Device": dev, "Name": "MCP Actions", "Version": "3.0",
                                       "Pages": {"Current": mpage, "Default": mdefault, "Pages": [mpage]}},
            "%s/Profiles/%s/manifest.json" % (mbase, mdefault.upper()): page_manifest("", None),
        }
        files.update(images("%s/Profiles/%s" % (mbase, mpage.upper()), keys))
        files["%s/Profiles/%s/manifest.json" % (mbase, mpage.upper())] = page_manifest("MCP Actions", keys)
        mout = os.path.join(OUT_DIR, "MCP Actions.streamDeckProfile")
        write(mout, files)
        print("wrote", mout)


if __name__ == "__main__":
    main()
