#!/bin/zsh -l
# Opens a Terminal in PROJECT_DIR and starts the Codex CLI.
source "$(dirname "$0")/../config.sh"
cd "$PROJECT_DIR" || { echo "PROJECT_DIR not found: $PROJECT_DIR (edit config.sh)"; exec zsh -l; }
command -v codex >/dev/null || { echo "codex is not on PATH"; exec zsh -l; }
exec codex
