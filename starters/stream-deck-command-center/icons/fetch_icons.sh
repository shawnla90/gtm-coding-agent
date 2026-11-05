#!/bin/bash
# Pull real key art into icons/src.
#   App icons come straight out of the installed .app bundle (the .icns the Dock uses).
#   Site icons come from the site itself: apple-touch-icon first (180px, usually clean),
#   then /favicon.ico as a last resort.
# Edit the two lists, run it, then rebuild the profile.
set -u
cd "$(dirname "$0")/src"

APPS=(  # "<file name>|<app path>"
  "app-claude|/Applications/Claude.app"
  "app-chatgpt|/Applications/ChatGPT.app"
  "app-codex|/Applications/Codex.app"
  "app-terminal|/System/Applications/Utilities/Terminal.app"
  "app-finder|/System/Library/CoreServices/Finder.app"
  "app-textedit|/System/Applications/TextEdit.app"
)
SITES=(  # "<file name>|<site root>"
  "web-github|https://github.com"
  "web-acme|https://example.com"
)

for entry in "${APPS[@]}"; do
  name="${entry%%|*}"; app="${entry#*|}"
  [ -d "$app" ] || { echo "skip $name: $app not installed"; continue; }
  icon="$(/usr/bin/defaults read "$app/Contents/Info" CFBundleIconFile 2>/dev/null)"
  icns="$app/Contents/Resources/${icon%.icns}.icns"
  if [ -n "$icon" ] && [ -f "$icns" ]; then
    /usr/bin/sips -s format png --resampleHeightWidthMax 256 "$icns" --out "$name.png" >/dev/null && echo "ok   $name"
  else
    # Some newer apps ship only an asset catalog. Quick Look can still render the bundle icon.
    /usr/bin/qlmanage -t -s 256 -o . "$app" >/dev/null 2>&1 && mv "$(basename "$app").png" "$name.png" && echo "ok   $name (quicklook)" \
      || echo "miss $name: no .icns and Quick Look failed"
  fi
done

tmp="$(mktemp)"
for entry in "${SITES[@]}"; do
  name="${entry%%|*}"; site="${entry#*|}"
  for path in /apple-touch-icon.png /apple-touch-icon-precomposed.png /favicon.ico; do
    if curl -fsSL --max-time 10 "$site$path" -o "$tmp" 2>/dev/null && [ -s "$tmp" ]; then
      /usr/bin/sips -s format png "$tmp" --out "$name.png" >/dev/null 2>&1 && { echo "ok   $name ($path)"; break; }
    fi
  done
  [ -f "$name.png" ] || echo "miss $name: drop a PNG in icons/src/$name.png by hand"
done
rm -f "$tmp"
