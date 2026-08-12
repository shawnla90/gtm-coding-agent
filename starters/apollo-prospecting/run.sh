#!/usr/bin/env bash
# run.sh -- the whole pipeline: load -> expand -> score -> reveal -> build sheet.
# Run setup_oauth.py once first so the builder can reach your Google Sheets.
#
#   bash run.sh                    # use sample_contacts.csv (reveal all ranked)
#   bash run.sh my_list.csv        # use your own CSV (same columns)
#   bash run.sh --no-reveal        # skip the reveal step (free search data only)
set -e
cd "$(dirname "$0")"
PY="${PYTHON:-python3}"

CSV="${1:-sample_contacts.csv}"
NO_REVEAL=false
for arg in "$@"; do
  case "$arg" in
    --no-reveal) NO_REVEAL=true ;;
    *) CSV="$arg" ;;
  esac
done

echo "1/5  loading source contacts into SQLite..."
"$PY" init_db.py "$CSV"

echo "2/5  expanding buying committees (Apollo API -- FREE, 0 credits)..."
"$PY" expand.py --all

echo "3/5  scoring and ranking contacts..."
"$PY" score.py

if [ "$NO_REVEAL" = true ]; then
  echo "4/5  skipping reveal (--no-reveal)"
else
  echo "4/5  revealing contact data (Apollo API -- 1 credit per person)..."
  "$PY" reveal.py
fi

echo "5/5  building the color-coded Google Sheet..."
"$PY" build_sheet.py

echo "done."
