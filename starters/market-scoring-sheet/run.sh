#!/usr/bin/env bash
# run.sh — the whole pipeline: load -> (enrich) -> score -> build the color-coded sheet.
# Run setup_oauth.py once first so the builder can reach your Google Sheets.
#
#   bash run.sh                 # use sample_market.csv
#   bash run.sh my_list.csv     # use your own CSV (same columns)
set -e
cd "$(dirname "$0")"
PY="${PYTHON:-python3}"

echo "1/4  loading the market into SQLite..."
"$PY" init_db.py "${1:-sample_market.csv}"

echo "2/4  enriching missing emails (skips if APOLLO_API_KEY is not set)..."
"$PY" enrich.py || true

echo "3/4  scoring every account 1 to 5..."
"$PY" score.py

echo "4/4  building the color-coded Google Sheet..."
"$PY" build_sheet.py

echo "done."
