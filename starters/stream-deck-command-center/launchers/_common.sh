#!/bin/bash
# Shared helpers. Every launcher sources this, which sources config.sh.
set -u
LAUNCHER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KIT_DIR="$(cd "$LAUNCHER_DIR/.." && pwd)"
if [ ! -f "$KIT_DIR/config.sh" ]; then
  /usr/bin/osascript -e 'display notification "Copy config.example.sh to config.sh first." with title "Stream Deck kit"'
  exit 1
fi
# shellcheck source=../config.example.sh
source "$KIT_DIR/config.sh"
open_url() { [ -n "${1:-}" ] && /usr/bin/open "$1"; }
open_app() { /usr/bin/open -a "$1" >/dev/null 2>&1; }
open_app_or_url() { open_app "$1" || open_url "$2"; }
notify() { /usr/bin/osascript -e "display notification \"$2\" with title \"$1\""; }
