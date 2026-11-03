#!/bin/bash
# Surgical homepage deploy: index.html, blank.html, roundup JS, and the four
# display-sized card images. Does not unzip the repo and does not touch api.py.
set -euo pipefail
SERVER="102.218.215.253"
USER="root"
WEB_ROOT="/var/www/sailingsa"
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
KEY="${SAILINGSA_SSH_KEY:-$HOME/.ssh/sailingsa_live_key}"

SSH_OPTS=(-o StrictHostKeyChecking=no)
SCP=(scp "${SSH_OPTS[@]}")
SSH=(ssh "${SSH_OPTS[@]}")

if [ -f "$KEY" ]; then
  SCP+=(-i "$KEY")
  SSH+=(-i "$KEY")
elif [ -n "${SSHPASS:-}" ]; then
  SCP=(sshpass -e scp "${SSH_OPTS[@]}")
  SSH=(sshpass -e ssh "${SSH_OPTS[@]}")
else
  echo "ERROR: Need ~/.ssh/sailingsa_live_key or SSHPASS env"
  exit 1
fi

echo "=== Homepage LCP/a11y deploy ==="
"${SSH[@]}" "${USER}@${SERVER}" "bash -s" <<'REMOTE'
set -euo pipefail
WEB_ROOT="/var/www/sailingsa"
TS=$(date +%Y%m%d_%H%M%S)
mkdir -p "/root/homepage-lcp-backup-${TS}"
cp -a "${WEB_ROOT}/index.html" "/root/homepage-lcp-backup-${TS}/index.html"
cp -a "${WEB_ROOT}/blank.html" "/root/homepage-lcp-backup-${TS}/blank.html" 2>/dev/null || true
cp -a "${WEB_ROOT}/js/landing-roundup-cards.js" "/root/homepage-lcp-backup-${TS}/landing-roundup-cards.js"
if [ ! -d "${WEB_ROOT}/artwork" ]; then
  echo "ERROR: ${WEB_ROOT}/artwork is missing"
  exit 1
fi
mkdir -p "${WEB_ROOT}/artwork/home-cards"
echo "BACKUP /root/homepage-lcp-backup-${TS}"
REMOTE

"${SCP[@]}" "$PROJECT_ROOT/sailingsa/frontend/home-cards/ullman-sails-womens-series.png" \
  "$PROJECT_ROOT/sailingsa/frontend/home-cards/tour-de-vlei.jpg" \
  "$PROJECT_ROOT/sailingsa/frontend/home-cards/ec-dinghy-regionals.png" \
  "$PROJECT_ROOT/sailingsa/frontend/home-cards/rcyc-host.png" \
  "${USER}@${SERVER}:${WEB_ROOT}/artwork/home-cards/"
"${SCP[@]}" "$PROJECT_ROOT/sailingsa/frontend/js/landing-roundup-cards.js" \
  "${USER}@${SERVER}:${WEB_ROOT}/js/landing-roundup-cards.js"
"${SCP[@]}" "$PROJECT_ROOT/sailingsa/frontend/index.html" \
  "${USER}@${SERVER}:${WEB_ROOT}/index.html"

"${SSH[@]}" "${USER}@${SERVER}" "bash -s" <<'REMOTE'
set -euo pipefail
WEB_ROOT="/var/www/sailingsa"
cp "${WEB_ROOT}/index.html" "${WEB_ROOT}/blank.html"
chown www-data:www-data \
  "${WEB_ROOT}/index.html" \
  "${WEB_ROOT}/blank.html" \
  "${WEB_ROOT}/js/landing-roundup-cards.js" \
  "${WEB_ROOT}/artwork/home-cards/"*
grep -q "homepage-lcp-20261024" "${WEB_ROOT}/index.html"
grep -q "homepage-lcp-20261024" "${WEB_ROOT}/blank.html"
grep -q "loadDeferredHero" "${WEB_ROOT}/js/landing-roundup-cards.js"
echo "SERVER_FILES_OK"
REMOTE

echo "Done. Verify https://sailingsa.co.za/?v=homepage-lcp-20261024"
