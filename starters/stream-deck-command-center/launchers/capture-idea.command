#!/bin/bash
# Drops a timestamped note template into NOTES_DIR and opens it in TextEdit.
source "$(dirname "$0")/_common.sh"
mkdir -p "$NOTES_DIR"
file="$NOTES_DIR/$(date +%Y-%m-%d_%H-%M-%S)-idea.txt"
printf 'IDEA: \n\nPlatform: \n\nHook: \n\nNotes: \n' > "$file"
/usr/bin/open -a TextEdit "$file"
