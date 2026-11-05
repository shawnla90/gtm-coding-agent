#!/bin/bash
# Push a rebuilt profile into Stream Deck WITHOUT re-importing it.
#
# The rule this script exists for: never move or delete a live profile folder. Stream Deck
# treats a vanished active profile as data loss, restores its daily backup, and any profile
# newer than that backup is gone. So: back up, quit Stream Deck cleanly, swap the PAGES inside
# the SAME profile folder (same profile UUID), relaunch, and check the log for a restore.
#
# First install is different: open "out/<name>.streamDeckProfile" once to import it.
set -euo pipefail
KIT="$(cd "$(dirname "$0")/.." && pwd)"
source "$KIT/config.sh"
NAME="${PROFILE_NAME:-Command Center}"
SD="$HOME/Library/Application Support/com.elgato.StreamDeck"
PROC="Elgato Stream Deck.app/Contents/MacOS/Stream Deck"
LOG="$HOME/Library/Logs/ElgatoStreamDeck/StreamDeck.log"
BK="$HOME/.streamdeck-backups/$(date +%Y%m%d-%H%M%S)"

python3 "$KIT/profile/build_profile.py"
BUILT="$KIT/out/$NAME.streamDeckProfile"

LIVE="$(python3 - "$SD/ProfilesV3" "$NAME" <<'PY'
import glob, json, sys
hits = []
for m in glob.glob(sys.argv[1] + "/*.sdProfile/manifest.json"):
    j = json.load(open(m))
    if j.get("Name") == sys.argv[2] and j.get("Device", {}).get("Model") == "20GBD9901":
        hits.append(m.rsplit("/", 1)[0])
print(hits[0] if len(hits) == 1 else "")
PY
)"
if [ -z "$LIVE" ]; then
  echo "Need exactly one live '$NAME' profile on a Stream Deck +."
  echo "First time? Import it: open \"$BUILT\". Two copies? Delete one in Stream Deck Preferences > Profiles."
  exit 1
fi

mkdir -p "$BK" && cp -R "$SD/ProfilesV3" "$BK/" && defaults export com.elgato.StreamDeck "$BK/prefs.plist"
echo "backup: $BK"
NEW="$(mktemp -d)"; unzip -q "$BUILT" -d "$NEW"
SRC="$(ls -d "$NEW"/Profiles/*.sdProfile)"

osascript -e 'tell application "Elgato Stream Deck" to quit' >/dev/null 2>&1 || true
for _ in $(seq 1 30); do pgrep -f "$PROC" >/dev/null || break; sleep 0.5; done
if pgrep -f "$PROC" >/dev/null; then echo "Stream Deck didn't quit. Nothing changed."; exit 1; fi

# Keep the live manifest's Device block (the import may have bound it to your hardware).
python3 - "$SRC/manifest.json" "$LIVE/manifest.json" <<'PY'
import json, sys
new, live = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
new["Device"] = live.get("Device", new.get("Device"))
json.dump(new, open(sys.argv[1], "w"), indent=2)
PY
rm -rf "$LIVE/Profiles" && cp -R "$SRC/Profiles" "$LIVE/Profiles" && cp "$SRC/manifest.json" "$LIVE/manifest.json"

START="$(date +%Y-%m-%dT%H:%M:%S)"
open -a "Elgato Stream Deck"; sleep 8
if [ -f "$LOG" ] && awk -v t="$START" '$0 >= t' "$LOG" | grep -qiE 'data loss|RestoreBackup'; then
  echo "WARNING: Stream Deck reported data loss or a restore. Your backup is at $BK"; exit 1
fi
echo "deployed: $(ls "$LIVE/Profiles" | wc -l | tr -d ' ') pages into $(basename "$LIVE")"
