#!/usr/bin/env bash
# run.sh -- the whole pipeline: load -> grade -> score -> build sheet.
# Run setup_oauth.py once first so the builder can reach your Google Sheets.
#
#   bash run.sh                          # sample_contacts.csv, first pass only
#   bash run.sh my_list.csv              # your own CSV (short schema or a raw Apollo export)
#   bash run.sh my_list.csv --full       # Moltsets employment check + second pass
#   bash run.sh my_list.csv --full --both # also run Apollo people/match and record agreement
#   bash run.sh my_list.csv --phones 10  # also buy up to 10 mobiles for dead-email rows
#   bash run.sh my_list.csv --full --people  # second pass via search_people instead of the business-profile search
#
# If the CSV carries your verifier's verdict (a zb_status / verifier_status column), every row also gets a
# delta class and the sheet gains the Disagreements and Verifier vs Moltsets tabs. No flag needed.
# REACHABILITY_DB=data/other.db bash run.sh ...  keeps a second list in its own database.
set -e
cd "$(dirname "$0")"
PY="${PYTHON:-python3}"

CSV="sample_contacts.csv"
GRADE_ARGS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --full) GRADE_ARGS+=(--second-pass) ;;
    --both) GRADE_ARGS+=(--employment both) ;;
    --people) GRADE_ARGS+=(--second-pass-endpoint people) ;;
    --apollo|--second-pass|--redo) GRADE_ARGS+=("$1") ;;
    --phones) GRADE_ARGS+=(--phones "$2"); shift ;;
    --limit) GRADE_ARGS+=(--limit "$2"); shift ;;
    *) CSV="$1" ;;
  esac
  shift
done

echo "1/4  loading contacts into SQLite..."
"$PY" init_db.py "$CSV"

echo "2/4  grading reachability (Moltsets; 404s are free, records are metered)..."
"$PY" grade.py "${GRADE_ARGS[@]}"

echo "3/4  scoring and ranking..."
"$PY" score.py

echo "4/4  building the color-coded Google Sheet..."
"$PY" build_sheet.py

echo "done."
