#!/bin/zsh -l
# KICKOFF 3 (Terminal): Codex builds a vertical MP4 and a looping GIF from the current pack.
source "$(dirname "$0")/_lib.sh"
slug="$(current_slug)"; dir="$DRAFTS_DIR/$slug"
if [ -z "$slug" ] || [ ! -d "$dir" ]; then echo "No current pack. Press New Pack first."; exec zsh -l; fi
command -v codex >/dev/null || { echo "codex is not on PATH"; exec zsh -l; }
cd "$dir"
exec codex "Make short-form video assets for the content pack in this folder ($dir).
Read video.md and the other drafts, pick the strongest hook, and build a 1080x1920 MP4 (15-30s, burned-in captions, clean motion) plus a looping GIF of the key visual.
Use the toolkit in $RENDER_KIT_DIR (read its README first). Write outputs to $dir/renders/.
Don't upload, post or send anything."
