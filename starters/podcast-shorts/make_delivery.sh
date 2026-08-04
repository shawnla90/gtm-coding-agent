#!/bin/bash
# Social delivery encode: vanilla 8-bit H.264 both-streams-fresh, phone-safe.
# The masters carry a hidden audio-timestamp gap at the first cut seam (the
# concat/atempo/loudnorm graph emits a pts jump the fps=24 video chain never
# gets); an earlier delivery generation used aresample=async=1, trusted those timestamps, and materialized the
# gap as sped-up audio + 2.25s of real silence. asetpts=N/SR/TB rewrites each
# audio frame's pts from its sample position — continuous by construction,
# zero content change. No -r: masters are already CFR 24.
set -u
cd "${1:-.}"   # pack dir (contains out/)
mkdir -p out/delivery
for f in out/clip_*[0-9a-z].mp4; do
  base=$(basename "$f" .mp4)
  [[ "$base" == *_review ]] && continue
  dst="out/delivery/${base}_social.mp4"
  [[ -f "$dst" ]] && { echo "skip $base"; continue; }
  echo "[$(date +%H:%M:%S)] $base"
  ffmpeg -y -v error -i "$f" \
    -c:v libx264 -preset medium -crf 17 -pix_fmt yuv420p -profile:v high -level 4.0 \
    -af "asetpts=N/SR/TB" -c:a aac -b:a 192k -ar 48000 -ac 1 \
    -movflags +faststart "$dst" || echo "FAIL $base"
done
echo "[$(date +%H:%M:%S)] DELIVERY DONE"
