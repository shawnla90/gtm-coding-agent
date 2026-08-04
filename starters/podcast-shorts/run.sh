#!/bin/bash
# End-to-end: transcribe -> plan -> overlay -> render -> composite -> deliver -> QA.
# Usage: ./run.sh <pack-dir>
# The render step needs node (npx hyperframes). Everything else is python + ffmpeg.
set -euo pipefail
cd "$(dirname "$0")"
PACK="${1:?usage: ./run.sh <pack-dir>}"
PACK="$(cd "$PACK" && pwd)"
N=$(python3 -c "import json; print(len(json.load(open('$PACK/pack.json'))['clips']))")

python3 transcribe.py "$PACK"

for i in $(seq 0 $((N - 1))); do
  NN=$(printf "%02d" "$i")
  python3 plan_clips.py "$PACK" "$i"
  python3 compose_overlay.py "$PACK" "$i"
  mkdir -p "$PACK/projects/clip_$NN/renders"
  npx hyperframes render "$PACK/projects/clip_$NN/public" --format mov \
    -o "$PACK/projects/clip_$NN/renders/overlay.mov" --quiet
  python3 final_composite.py "$PACK" "$i"
  rm -f "$PACK/projects/clip_$NN/renders/overlay.mov"   # ProRes alpha is 300-800MB
done

bash make_delivery.sh "$PACK"
python3 qa_delivery.py delivery _social "$PACK" || {
  echo "QA FAILED — do not host or draft these files"; exit 1
}
echo "done: masters in $PACK/out/, social encodes in $PACK/out/delivery/"
