#!/bin/bash
# Wraps the silent launchers as tiny .app bundles, so a key press runs them without
# leaving a Terminal window behind. Terminal-based ones (.command that start claude or
# codex) stay as .command on purpose: you want that window.
set -euo pipefail
KIT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUT="$KIT_DIR/apps"
mkdir -p "$OUT"
wrap() {  # wrap <name> <script>
  rm -rf "$OUT/$1.app"
  /usr/bin/osacompile -o "$OUT/$1.app" \
    -e "do shell script \"/bin/bash \" & quoted form of \"$2\" & \" >/dev/null 2>&1 &\""
  echo "built apps/$1.app"
}
wrap capture-idea      "$KIT_DIR/launchers/capture-idea.command"
wrap ai-workbench      "$KIT_DIR/launchers/ai-workbench.command"
wrap content-critique  "$KIT_DIR/kickoffs/content-critique.sh"
wrap content-open      "$KIT_DIR/kickoffs/content-open.sh"
