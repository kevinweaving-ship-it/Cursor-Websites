#!/bin/bash
# SailingSA — Deploy frontend + restart API using SSH key (no password).
# Run from project root. Requires ~/.ssh/sailingsa_live_key.
set -e
SERVER="102.218.215.253"
WEB_ROOT="/var/www/sailingsa"
API_ROOT="/var/www/sailingsa/api"
KEY="$HOME/.ssh/sailingsa_live_key"
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

if [ ! -f "$KEY" ]; then
  echo "ERROR: SSH key not found: $KEY"
  echo "Run the SSH key setup first (see SSH_LIVE.md)."
  exit 1
fi

echo "Build frontend zip..."
cd "$PROJECT_ROOT/sailingsa/frontend"
zip -r ../../sailingsa-frontend.zip . -x "*.DS_Store" -x "__MACOSX" -x "*.BU_*" -x "*.bu_*" -x "*.bak" -x "*.md"
cd "$PROJECT_ROOT"

echo "Upload zip..."
scp -i "$KEY" -o StrictHostKeyChecking=no sailingsa-frontend.zip root@${SERVER}:/tmp/

echo "Upload API modules (sailingsa/api/modules)..."
scp -r -i "$KEY" -o StrictHostKeyChecking=no sailingsa/api/modules root@${SERVER}:$API_ROOT/

echo "Extract, chown, restart API..."
ssh -i "$KEY" -o StrictHostKeyChecking=no root@${SERVER} "
  cd $WEB_ROOT &&
  unzip -o /tmp/sailingsa-frontend.zip &&
  rm -f /tmp/sailingsa-frontend.zip &&
  (chown -R www-data:www-data $WEB_ROOT || true) &&
  systemctl restart sailingsa-api &&
  sleep 2 &&
  systemctl is-active sailingsa-api
"

echo "Deploy complete. Verify: https://sailingsa.co.za/"
