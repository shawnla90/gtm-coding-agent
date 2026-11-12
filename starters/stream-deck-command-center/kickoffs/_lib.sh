#!/bin/bash
# Shared helpers for the content kickoff keys.
# State is one file: $STATE_DIR/current holds the slug of the pack you're working on,
# so each key knows which folder to act on without asking.
KICKOFF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$KICKOFF_DIR/../config.sh"
STATE_DIR="$(dirname "$DRAFTS_DIR")/kickoffs"
mkdir -p "$DRAFTS_DIR" "$STATE_DIR"
current_slug() { [ -f "$STATE_DIR/current" ] && cat "$STATE_DIR/current"; }
notify() { /usr/bin/osascript -e "display notification \"$2\" with title \"$1\""; }
