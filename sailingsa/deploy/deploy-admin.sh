#!/bin/bash
# One shot: frontend zip (templates/js/css) + main API restart + admin_api files + admin API restart.
# Run from project root:  bash sailingsa/deploy/deploy-admin.sh
set -e
SERVER="102.218.215.253"
API_ROOT="/var/www/sailingsa/api"
KEY="$HOME/.ssh/sailingsa_live_key"
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

if [ ! -f "$KEY" ]; then
  echo "ERROR: SSH key not found: $KEY"
  exit 1
fi
if [ ! -f "$PROJECT_ROOT/admin_api.py" ] || [ ! -f "$PROJECT_ROOT/admin_support.py" ]; then
  echo "ERROR: admin_api.py / admin_support.py must live at project root."
  exit 1
fi

bash "$PROJECT_ROOT/sailingsa/deploy/deploy-with-key.sh"

echo ""
echo "=== Admin API (port 8002): copy + restart ==="
scp -i "$KEY" -o StrictHostKeyChecking=no \
  "$PROJECT_ROOT/admin_api.py" \
  "$PROJECT_ROOT/admin_support.py" \
  "root@${SERVER}:${API_ROOT}/"

ssh -i "$KEY" -o StrictHostKeyChecking=no "root@${SERVER}" \
  "systemctl restart sailingsa-admin-api && sleep 2 && systemctl is-active sailingsa-admin-api"

echo ""
echo "Done. Open: https://sailingsa.co.za/admin/dashboard"
