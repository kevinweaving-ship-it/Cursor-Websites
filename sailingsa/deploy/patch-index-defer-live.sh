#!/usr/bin/env bash
# Patch live thin index.html: CSS before head JS, defer all body script src tags.
# Prefer this over a full api.py replace when live api is ahead of git.
# From Mac Mini with sailingsa_live_key (see SSH_LIVE.md):
#   bash sailingsa/deploy/patch-index-defer-live.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
KEY="${SAILINGSA_SSH_KEY:-$HOME/.ssh/sailingsa_live_key}"
HOST="${SAILINGSA_SSH_HOST:-root@102.218.215.253}"
WEB_ROOT="${SAILINGSA_WEB_ROOT:-/var/www/sailingsa}"

scp -i "$KEY" \
  "$ROOT/sailingsa/optimize_index_script_loading.py" \
  "$HOST:/tmp/optimize_index_script_loading.py"

ssh -i "$KEY" "$HOST" bash -s <<EOF
set -euo pipefail
ts=\$(date +%Y%m%d%H%M%S)
cp -a "$WEB_ROOT/index.html" "$WEB_ROOT/index.html.bak-defer-\$ts"
python3 /tmp/optimize_index_script_loading.py "$WEB_ROOT/index.html"
# Ensure optimizer is importable if api serve-path rewrite is deployed later
cp -a /tmp/optimize_index_script_loading.py "$WEB_ROOT/optimize_index_script_loading.py"
echo "Patched $WEB_ROOT/index.html (backup index.html.bak-defer-\$ts)"
grep -n 'script src' "$WEB_ROOT/index.html" | head -30
EOF
