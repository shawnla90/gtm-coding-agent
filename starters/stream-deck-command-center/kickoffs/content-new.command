#!/bin/zsh -l
# KICKOFF 1 (Terminal): ask for a topic, make the pack folder, start Claude Code drafting it.
source "$(dirname "$0")/_lib.sh"
print -n "Content pack topic: "; read topic
[ -z "$topic" ] && { echo "No topic, nothing started."; exit 0; }
slug="$(date +%Y-%m-%d)-$(echo "$topic" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-|-$//g' | cut -c1-48)"
dir="$DRAFTS_DIR/$slug"
mkdir -p "$dir" && echo "$slug" > "$STATE_DIR/current"
printf '# Brief\n\nTopic: %s\nStarted: %s (Stream Deck kickoff)\n' "$topic" "$(date)" > "$dir/brief.md"
cd "$dir"
exec claude -n "Pack: $topic" "Draft a content pack on: $topic.
Work in $dir (brief.md is there). Read $VOICE_FILE before writing anything.
Write one LinkedIn post (linkedin.md), one X post (x.md) and a 20-second video script (video.md).
Do NOT publish, post, schedule or send anything. Stop when the drafts are written and tell me what's there.
Next I'll run the critique key, then the render key."
