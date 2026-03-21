#!/usr/bin/env bash
# Deploy api.py (Dash 2) to live. Run from project root.
# Usage: bash sailingsa/deploy/deploy-dash2-live.sh

set -e
HOST="102.218.215.253"
KEY="${HOME}/.ssh/sailingsa_live_key"
API_PATH="/var/www/sailingsa/api/api.py"

# Must run from project root; api.py must be the full Dash 2 (no "Blank page")
if [ ! -f "api.py" ]; then
  echo "ERROR: Run from project root (where api.py is). cd to 'Project 6' then run this script."
  exit 1
fi
if grep -q "Blank page. Build here" api.py 2>/dev/null; then
  echo "ERROR: Your api.py still has the old blank page. Get the full Dash 2 version from the repo."
  exit 1
fi

echo "Deploying api.py to $HOST ..."

# 1. Backup + unlock on server
ssh -i "$KEY" root@$HOST "cp $API_PATH ${API_PATH}.$(date +%Y%m%d_%H%M%S).bak && chattr -i $API_PATH"

# 2. Upload api.py
scp -i "$KEY" api.py root@$HOST:$API_PATH

# 3. Lock, chown, restart
ssh -i "$KEY" root@$HOST "chown www-data:www-data $API_PATH && chattr +i $API_PATH && systemctl restart sailingsa-api && sleep 2 && systemctl is-active sailingsa-api"

# 4. Verify: new page has "Data Review", not "Blank page"
BODY=$(ssh -i "$KEY" root@$HOST "curl -sS http://127.0.0.1:8000/admin/dashboard-v2 2>/dev/null | head -c 12000")
if echo "$BODY" | grep -q "Data Review"; then
  echo "OK: Full Dash 2 is live."
elif echo "$BODY" | grep -q "Blank page"; then
  echo "WARN: Server still returning old page. Run: ssh -i $KEY root@$HOST 'systemctl restart sailingsa-api' then hard-refresh."
else
  echo "Note: Curl may get 403 (auth). Open URL and hard-refresh."
fi
echo "URL: https://sailingsa.co.za/admin/dashboard-v2"
