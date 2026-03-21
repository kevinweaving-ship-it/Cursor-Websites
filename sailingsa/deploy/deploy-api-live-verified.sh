#!/bin/bash
# Run FROM PROJECT ROOT (where api.py lives). Deploys api.py to live with verification.
# Requires: api.py in current directory, SSH key at ~/.ssh/sailingsa_live_key.
#
# 1) scp api.py to /root/incoming/
# 2) Verify file exists on server
# 3) Run deploy_api_verified.sh on server (chattr -i, cp, hash check, restart)
# 4) Verify version endpoint (new pid / api_start_time)
# 5) Verify dashboard HTML contains "Next Run" (proves new code is served)

set -e

KEY="${1:-$HOME/.ssh/sailingsa_live_key}"
HOST="root@102.218.215.253"
API_PY="api.py"

if [ ! -f "$API_PY" ]; then
  echo "ERROR: $API_PY not found. Run from project root."
  exit 1
fi

if [ ! -f "$KEY" ]; then
  echo "ERROR: SSH key not found: $KEY"
  exit 1
fi

echo "=== 1) Copy api.py to server ==="
scp -i "$KEY" "$API_PY" "$HOST:/root/incoming/api.py"
if [ -f regatta_host_code.py ]; then
  scp -i "$KEY" regatta_host_code.py "$HOST:/root/incoming/regatta_host_code.py"
fi

echo "=== 2) Verify file on server ==="
ssh -i "$KEY" "$HOST" "ls -lh /root/incoming/api.py" || { echo "ERROR: /root/incoming/api.py missing after scp."; exit 1; }

echo "=== 3) Run deploy on server ==="
ssh -i "$KEY" "$HOST" "test -x /root/deploy_api_verified.sh && /root/deploy_api_verified.sh" || { echo "ERROR: deploy failed or /root/deploy_api_verified.sh missing. See SSH_LIVE.md one-time setup."; exit 1; }

echo "=== 4) Verify version endpoint ==="
curl -s "https://sailingsa.co.za/admin/api/version" | head -c 300
echo ""

echo "=== 5) Required: dashboard must contain 'Next Run' ==="
if ! curl -s "https://sailingsa.co.za/admin/dashboard-v3" | grep -q "Next Run"; then
  echo "ERROR: Dashboard HTML does not contain 'Next Run'. Deploy failed or old code still served."
  echo "Check https://sailingsa.co.za/admin/dashboard-v3 and /var/www/sailingsa/api/api.py timestamp."
  exit 1
fi
echo "OK - dashboard contains 'Next Run' (new code is live)."

echo "=== Deploy and verification done ==="
