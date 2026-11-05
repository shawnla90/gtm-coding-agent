#!/bin/zsh -l
# Plain Claude Code in PROJECT_DIR. Project keys use claude-project.command instead.
source "$(dirname "$0")/../config.sh"
cd "$PROJECT_DIR" || { echo "PROJECT_DIR not found: $PROJECT_DIR (edit config.sh)"; exec zsh -l; }
command -v claude >/dev/null || { echo "claude is not on PATH"; exec zsh -l; }
exec claude
