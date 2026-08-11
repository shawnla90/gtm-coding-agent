#!/usr/bin/env bash
# run.sh - the whole loop: init -> pull -> mine -> score -> build the color-coded sheet.
# Run setup_oauth.py once first so the builder can reach your Google Sheets. The source is a
# complete Clearbox opportunity export; this script does not discover Reddit content itself.
#
#   bash run.sh                   # import data/clearbox_export.json + build
#   bash run.sh --no-cli          # skip the Claude polish, heuristic angles only
#   bash run.sh --offline         # run the bundled synthetic Clearbox export
#
# Optional 6th step (needs the Google token from setup_oauth.py):
#   python3 build_deck.py         # build a short editable Google Slides deck from the same data
set -e
cd "$(dirname "$0")"
PY="${PYTHON:-python3}"

MINE_ARGS="--cli"
OFFLINE=0
for arg in "$@"; do
  case "$arg" in
    --no-cli)   MINE_ARGS="" ;;
    --offline)  OFFLINE=1; MINE_ARGS="" ;;
  esac
done

if [ "$OFFLINE" = "1" ]; then
  OPS_PATH="data/clearbox_export.sample.json"
  echo "offline mode: using the bundled synthetic Clearbox export"
else
  OPS_PATH="${CLEARBOX_EXPORT:-data/clearbox_export.json}"
fi

if [ ! -f "$OPS_PATH" ]; then
  echo "Clearbox export not found at $OPS_PATH" >&2
  echo "Export the complete opportunity inbox, or run: bash run.sh --offline" >&2
  exit 1
fi

echo "1/5  creating the local database..."
"$PY" init_db.py

echo "2/5  importing classified Clearbox opportunities..."
if [ "$OFFLINE" = "1" ]; then
  "$PY" pull.py --ops "$OPS_PATH" --all-dates
else
  "$PY" pull.py --ops "$OPS_PATH"
fi

echo "3/5  mining buyer language + content topics..."
"$PY" mine.py $MINE_ARGS

echo "4/5  scoring every content topic 1 to 5..."
"$PY" score.py

echo "5/5  building the color-coded Google Sheet..."
"$PY" build_sheet.py

echo "done. optional next step: python3 build_deck.py"
