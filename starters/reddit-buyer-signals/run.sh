#!/usr/bin/env bash
# run.sh - the whole loop: init -> pull -> mine -> score -> build the color-coded sheet.
# Run setup_oauth.py once first so the builder can reach your Google Sheets, and export your
# reddit34 RapidAPI key so the pull can reach Reddit.
#
#   export RAPIDAPI_KEY=...       # your reddit34.p.rapidapi.com key
#   bash run.sh                   # full pull + Claude-polished content angles
#   bash run.sh --sample          # quick capped pull (proves the pipeline fast)
#   bash run.sh --no-cli          # skip the Claude polish, heuristic angles only
#   bash run.sh --offline         # no key needed: run the bundled sample export end to end
#
# Optional 6th step (needs the Google token from setup_oauth.py):
#   python3 build_deck.py         # build a short editable Google Slides deck from the same data
set -e
cd "$(dirname "$0")"
PY="${PYTHON:-python3}"

PULL_ARGS=""
MINE_ARGS="--cli"
OFFLINE=0
for arg in "$@"; do
  case "$arg" in
    --sample)   PULL_ARGS="--max 6" ;;
    --no-cli)   MINE_ARGS="" ;;
    --offline)  OFFLINE=1; MINE_ARGS="" ;;
  esac
done

if [ "$OFFLINE" = "1" ]; then
  echo "offline mode: seeding data/clearbox_export.json from the bundled sample"
  cp data/clearbox_export.sample.json data/clearbox_export.json
  export REDDIT_SOURCE=clearbox
elif [ -z "$RAPIDAPI_KEY" ]; then
  echo "RAPIDAPI_KEY is not set. Run: export RAPIDAPI_KEY=your_reddit34_key" >&2
  echo "(or run: bash run.sh --offline  to try the bundled sample with no key)" >&2
  exit 1
fi

echo "1/5  creating the local database..."
"$PY" init_db.py

echo "2/5  pulling recent buyer threads from Reddit..."
"$PY" pull.py $PULL_ARGS

echo "3/5  mining buyer language + content topics..."
"$PY" mine.py $MINE_ARGS

echo "4/5  scoring every content topic 1 to 5..."
"$PY" score.py

echo "5/5  building the color-coded Google Sheet..."
"$PY" build_sheet.py

echo "done. optional next step: python3 build_deck.py"
