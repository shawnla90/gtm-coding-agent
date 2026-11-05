#!/bin/bash
# Copy to config.sh and edit. Plain paths and URLs only: never put tokens or passwords here.
# Every launcher and kickoff sources this file.

# Fallback repo for keys that aren't tied to a project in projects.toml.
PROJECT_DIR="$HOME/code/acme-gtm"

# Where the Capture Idea key drops notes. Keep it OUT of ~/Documents, ~/Desktop and
# ~/Downloads: macOS privacy-protects those, and a launcher started by Stream Deck
# fails silently there.
NOTES_DIR="$HOME/notes/ideas"

# Content kickoffs: one folder per pack lives here.
DRAFTS_DIR="$HOME/content/drafts"

# Your voice rules. The drafting agent reads this before it writes anything.
VOICE_FILE="$HOME/voice/principles.md"

# The app that gives the second opinion. It gets the pack via the clipboard,
# so any chat app works (ChatGPT, Claude, a Cursor agent window, ...).
CRITIC_APP="ChatGPT"
CRITIC_URL="https://chatgpt.com/"          # opened if the app isn't installed

# A local video toolkit (Remotion, HyperFrames, ffmpeg scripts) that the render step points Codex at.
RENDER_KIT_DIR="$HOME/code/video-kit"

# Name of the generated Stream Deck profile. deploy_live.sh looks for exactly one profile with this name.
PROFILE_NAME="Command Center"

# Set to 1 if you installed the Elgato "ChatGPT & Codex" plugin and want its usage/power dials.
CODEX_PLUGIN=0
