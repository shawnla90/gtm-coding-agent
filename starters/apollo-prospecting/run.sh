#!/usr/bin/env bash
# run.sh -- the whole pipeline: load -> expand -> score -> build the color-coded sheet.
# Run setup_oauth.py once first so the builder can reach your Google Sheets.
#
#   bash run.sh                    # use sample_contacts.csv
#   bash run.sh my_list.csv        # use your own CSV (same columns)
set -e
cd "$(dirname "$0")"
PY="${PYTHON:-python3}"

echo "1/4  loading source contacts into SQLite..."
"$PY" init_db.py "${1:-sample_contacts.csv}"

echo "2/4  expanding buying committees (Apollo API -- FREE, 0 credits)..."
"$PY" expand.py --all

echo "3/4  scoring and ranking contacts..."
"$PY" score.py

echo "4/4  building the color-coded Google Sheet..."
"$PY" build_sheet.py

echo "done."
