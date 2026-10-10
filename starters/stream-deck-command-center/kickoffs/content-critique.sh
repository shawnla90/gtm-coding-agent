#!/bin/bash
# KICKOFF 2 (silent): copy the current pack plus a critique prompt, open the critic app.
# Chat apps have no reliable "open with this prompt" hook, so the clipboard is the hand-off:
# press the key, then Cmd+V in the critic. A different model catches what the drafter can't.
source "$(dirname "$0")/_lib.sh"
slug="$(current_slug)"; dir="$DRAFTS_DIR/$slug"
if [ -z "$slug" ] || [ ! -d "$dir" ]; then notify "Critique" "No current pack. Press New Pack first."; exit 1; fi
{
  echo "Critique this content pack hard. For each piece: does the hook land in the first line, where does it sound generic or AI-written (em dashes, 'it's not X, it's Y', hype words, three-part lists), and what would make the target reader stop scrolling. Give specific line edits, not general advice."
  echo
  for f in "$dir"/*.md "$dir"/*.txt; do
    [ -f "$f" ] || continue
    echo "===== $(basename "$f") ====="; cat "$f"; echo
  done
} | pbcopy
/usr/bin/open -a "$CRITIC_APP" 2>/dev/null || /usr/bin/open "$CRITIC_URL"
notify "Critique ready" "Pack '$slug' is on the clipboard. Cmd+V in $CRITIC_APP."
