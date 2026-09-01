#!/bin/bash
# Deploy tracking-dev2 to live: frontend (zip) + api.py + sailingsa/backend bootstrap module.
# Run from project root on Mac. Requires ~/.ssh/sailingsa_live_key.
# See docs/TRACKING_DEV2.md and sailingsa/deploy/SSH_LIVE.md
set -euo pipefail

SERVER="102.218.215.253"
WEB_ROOT="/var/www/sailingsa"
API_ROOT="/var/www/sailingsa/api"
KEY="${SAILINGSA_SSH_KEY:-$HOME/.ssh/sailingsa_live_key}"
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

if [ ! -f "$KEY" ]; then
  echo "ERROR: SSH key not found: $KEY"
  echo "See sailingsa/deploy/SSH_LIVE.md for one-time key setup."
  exit 1
fi

if [ ! -f "$PROJECT_ROOT/api.py" ]; then
  echo "ERROR: Run from repo root (api.py missing)."
  exit 1
fi

echo "=== 1) Frontend zip (tracking-dev2.html, js, css, lipton-dev replay JSON) ==="
cd "$PROJECT_ROOT/sailingsa/frontend"
rm -f ../../sailingsa-frontend.zip
zip -r ../../sailingsa-frontend.zip . \
  -x "*.DS_Store" -x "__MACOSX" -x "*.BU_*" -x "*.bu_*" -x "*.bak" -x "*.md" \
  -x "data/hub_hero.json"
cd "$PROJECT_ROOT"

echo "=== 2) Upload zip + extract ==="
scp -i "$KEY" -o StrictHostKeyChecking=no sailingsa-frontend.zip "root@${SERVER}:/tmp/"
ssh -i "$KEY" -o StrictHostKeyChecking=no "root@${SERVER}" "
  cd ${WEB_ROOT} &&
  unzip -o /tmp/sailingsa-frontend.zip &&
  rm -f /tmp/sailingsa-frontend.zip &&
  chown -R www-data:www-data ${WEB_ROOT} 2>/dev/null || true
"

echo "=== 3) Bootstrap module (sailingsa/backend) ==="
ssh -i "$KEY" -o StrictHostKeyChecking=no "root@${SERVER}" \
  "mkdir -p ${WEB_ROOT}/sailingsa/backend"
scp -i "$KEY" -o StrictHostKeyChecking=no \
  "$PROJECT_ROOT/sailingsa/__init__.py" \
  "root@${SERVER}:${WEB_ROOT}/sailingsa/__init__.py"
scp -i "$KEY" -o StrictHostKeyChecking=no \
  "$PROJECT_ROOT/sailingsa/backend/__init__.py" \
  "root@${SERVER}:${WEB_ROOT}/sailingsa/backend/__init__.py"
scp -i "$KEY" -o StrictHostKeyChecking=no \
  "$PROJECT_ROOT/sailingsa/backend/tracking_dev2_sailfish.py" \
  "root@${SERVER}:${WEB_ROOT}/sailingsa/backend/tracking_dev2_sailfish.py"

echo "=== 4) api.py (verified deploy) ==="
scp -i "$KEY" -o StrictHostKeyChecking=no \
  "$PROJECT_ROOT/api.py" "root@${SERVER}:/root/incoming/api.py"
ssh -i "$KEY" -o StrictHostKeyChecking=no "root@${SERVER}" \
  "/root/deploy_api_verified.sh"

echo "=== 5) Verify tracking-dev2 ==="
curl -sf "https://sailingsa.co.za/api/tracking-dev2/replay2/getRaceDatas?race=1" | python3 -c \
  "import json,sys; d=json.load(sys.stdin); assert d.get('success') and d.get('teamList'), d; print('getRaceDatas OK', len(d.get('teamList',[])), 'teams')"
curl -sfI "https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup-dev2?race=1" | head -3

echo ""
echo "Deploy complete. Open:"
echo "  https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup-dev2?race=1"
