#!/usr/bin/env sh
# Redraw every artwork and stamp the colophon. Locally: REPOS=a,b,c sh scripts/draw_all.sh
set -e
cd "$(dirname "$0")/.."
export ART_WORK="${ART_WORK:-/tmp/data-art-work}" ART_CACHE="${ART_CACHE:-0}"
rm -f "$ART_WORK/contributions.json" "$ART_WORK/repos.json"   # fresh data each run; clones are reused
export ART_CACHE=1                                            # ...then shared by the three drawings
python3 -I scripts/draw_skyline.py
python3 -I scripts/draw_constellation.py
python3 -I scripts/update_colophon.py
