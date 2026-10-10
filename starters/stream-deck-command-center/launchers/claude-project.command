#!/bin/zsh -l
# Usage: claude-project.command <project-id> [workflow-label]
# One key press: cd into the right repo, scope GitHub to the right account for THIS
# terminal only, and start Claude Code with the project's model, effort and session name.
# Stream Deck can't pass arguments to a file, so build_profile.py writes one tiny wrapper
# per key into generated/ that calls this script.
KIT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
eval "$(python3 "$KIT_DIR/profile/projects.py" env "$@")" || { echo "Check projects.toml."; exec zsh -l; }

cd "$P_PATH" 2>/dev/null || { echo "Repo not found: $P_PATH (edit projects.toml)"; exec zsh -l; }
command -v claude >/dev/null || { echo "claude is not on PATH"; exec zsh -l; }

# Per-terminal GitHub identity. `gh auth switch` is global: it flips the account for every
# other terminal and agent on the machine mid-session. GH_TOKEN only lives in this shell.
if [ -n "$P_GH_USER" ]; then
  if token="$(gh auth token --user "$P_GH_USER" 2>/dev/null)"; then
    export GH_TOKEN="$token"
  else
    echo "gh has no login for $P_GH_USER (run: gh auth login). Continuing with the active account."
  fi
fi

args=(-n "$P_SESSION")
[ -n "$P_MODEL" ] && args+=(--model "$P_MODEL")
[ -n "$P_EFFORT" ] && args+=(--effort "$P_EFFORT")
[ -n "$P_PROMPT" ] && args+=("$P_PROMPT")
printf '\e]0;%s\a' "$P_SESSION"   # Terminal tab title
exec claude "${args[@]}"
