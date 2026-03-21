#!/bin/bash
# Deploy api.py to PROD then D/R; require D/R host; output proof (hashes, API PID) for BOTH.
# Run from project root. Requires: api.py, ~/.ssh/sailingsa_live_key.
#
# Order: PROD deploy → verify → D/R deploy → verify.
# D/R host: set SAILINGSA_DR_HOST=root@IP or create sailingsa/deploy/DR_HOST with one line "root@IP".

set -e

KEY="${1:-$HOME/.ssh/sailingsa_live_key}"
PROD_HOST="root@102.218.215.253"
API_PY="api.py"

# Resolve D/R host
DR_HOST=""
if [ -n "$SAILINGSA_DR_HOST" ]; then
  DR_HOST="$SAILINGSA_DR_HOST"
elif [ -f "sailingsa/deploy/DR_HOST" ]; then
  DR_HOST=$(grep -v '^#' sailingsa/deploy/DR_HOST | grep -v '^[[:space:]]*$' | head -1 | tr -d '\r\n')
fi

if [ -z "$DR_HOST" ]; then
  echo "ERROR: D/R host not configured. Set SAILINGSA_DR_HOST or create sailingsa/deploy/DR_HOST (e.g. echo 'root@IP' > sailingsa/deploy/DR_HOST). See DR_HOST.example."
  exit 1
fi

if [ ! -f "$API_PY" ]; then
  echo "ERROR: $API_PY not found. Run from project root."
  exit 1
fi

if [ ! -f "$KEY" ]; then
  echo "ERROR: SSH key not found: $KEY"
  exit 1
fi

do_deploy() {
  local label="$1"
  local host="$2"
  local base_url="${3:-}"  # optional; if empty, version proof from process list

  echo ""
  echo "========== $label =========="
  scp -i "$KEY" "$API_PY" "$host:/root/incoming/api.py"
  ssh -i "$KEY" "$host" "test -x /root/deploy_api_verified.sh && /root/deploy_api_verified.sh" || {
    echo "ERROR: deploy failed on $label or /root/deploy_api_verified.sh missing."
    exit 1
  }
  echo "--- Proof: hashes and API process above ---"
  if [ -n "$base_url" ]; then
    echo "Live version endpoint:"
    curl -s "${base_url}/admin/api/version" | head -c 400
    echo ""
  fi
  echo "========== End $label =========="
}

echo "=== PROD deploy ==="
do_deploy "PROD" "$PROD_HOST" "https://sailingsa.co.za"

echo "=== D/R deploy ==="
do_deploy "D/R" "$DR_HOST" ""

echo ""
echo "=== Deploy and verify done (PROD + D/R) ==="
