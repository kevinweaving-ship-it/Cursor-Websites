#!/usr/bin/env bash
# Apply clean URL-trail traffic model on live api.py (run on server or via ssh).
# Order matters. Backup first.
set -euo pipefail
API="${1:-/var/www/sailingsa/api/api.py}"
DIR="$(cd "$(dirname "$0")" && pwd)"
cp -a "$API" "${API}.bak-clean-trail-$(date +%Y%m%d_%H%M%S)"
python3 "$DIR/patch_clean_url_trail.py" "$API"
python3 "$DIR/patch_clean_url_trail_v2.py" "$API"
python3 "$DIR/patch_clean_url_trail_v3.py" "$API"
python3 "$DIR/patch_clean_url_trail_v4.py" "$API"
python3 -m py_compile "$API"
echo "OK patched $API — restart: systemctl restart sailingsa-api"
