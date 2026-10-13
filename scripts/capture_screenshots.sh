#!/usr/bin/env sh
# Re-capture the live products with headless Chrome (present on ubuntu-latest runners and most dev machines).
# Usage: sh scripts/capture_screenshots.sh [out-dir]
set -e
OUT="${1:-$(dirname "$0")/../data/screenshots}"; mkdir -p "$OUT"
CHROME="${CHROME:-$(command -v google-chrome || command -v chromium-browser || command -v chromium)}"
shot() { timeout 120 "$CHROME" --headless=new --no-sandbox --disable-gpu --hide-scrollbars --window-size=1280,800 \
         --virtual-time-budget=12000 --screenshot="$OUT/$1.png" "$2" >/dev/null 2>&1 && echo "captured $1"; }
shot o-guardanapo  https://o-guardanapo.site
shot agentic-hub   https://agentichub-64abdc.gitlab.io
shot sonora        https://sonora-d09e63.gitlab.io
shot ui-components https://ui-components-5218c2.gitlab.io
