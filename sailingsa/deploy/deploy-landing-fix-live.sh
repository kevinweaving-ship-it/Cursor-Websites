#!/bin/bash
# Deploy landing + regatta search fixes to live (index.html, js/api.js, api.py).
# Run from project root. Uses SSHPASS env or ~/.ssh/sailingsa_live_key.
set -euo pipefail

SERVER="102.218.215.253"
USER="root"
WEB_ROOT="/var/www/sailingsa"
API_ROOT="/var/www/sailingsa/api"
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

echo "=== 1) Frontend zip (includes index.html + js/api.js) ==="
cd "$PROJECT_ROOT/sailingsa/frontend"
rm -f ../../sailingsa-frontend.zip
zip -r ../../sailingsa-frontend.zip . \
  -x "*.DS_Store" -x "__MACOSX" -x "*.BU_*" -x "*.bu_*" -x "*.bak" -x "*.md" \
  -x "data/hub_hero.json"
cd "$PROJECT_ROOT"

echo "=== 2) Upload + extract frontend ==="
"${SCP[@]}" sailingsa-frontend.zip "${USER}@${SERVER}:/tmp/"
"${SSH[@]}" "${USER}@${SERVER}" "
  cd ${WEB_ROOT} &&
  unzip -o /tmp/sailingsa-frontend.zip &&
  rm -f /tmp/sailingsa-frontend.zip &&
  chown -R www-data:www-data ${WEB_ROOT} 2>/dev/null || true &&
  ls -la ${WEB_ROOT}/index.html ${WEB_ROOT}/js/api.js
"

echo "=== 3) Deploy api.py ==="
"${SCP[@]}" "$PROJECT_ROOT/api.py" "${USER}@${SERVER}:/root/incoming/api.py"
"${SSH[@]}" "${USER}@${SERVER}" "/root/deploy_api_verified.sh"

echo "=== 4) Verify live ==="
curl -sfI "https://sailingsa.co.za/api/regattas/with-counts?limit=500" | head -1
curl -sfI "https://sailingsa.co.za/dev-1?embed=1&sas_id=15737" | head -1
curl -sf "https://sailingsa.co.za/js/api.js" | rg -n "limit=400|Math.min\(400" | head -3 || true
curl -sf "https://sailingsa.co.za/" | rg -n "20260901landingfix|limit: 400" | head -3 || true
curl -sf "https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup" | rg -o 'lipton-dev-event|J22-Class|club-logo/HYC' | head -5 || true

echo "Deploy complete."
