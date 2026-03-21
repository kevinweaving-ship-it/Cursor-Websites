#!/bin/bash
# Audit deploy system: D/R host, SSH key, paths, test connections.
# Run from project root.

set -e

KEY="${HOME}/.ssh/sailingsa_live_key"
PROD_HOST="root@102.218.215.253"
DR_HOST=""
if [ -n "$SAILINGSA_DR_HOST" ]; then
  DR_HOST="$SAILINGSA_DR_HOST"
elif [ -f "sailingsa/deploy/DR_HOST" ]; then
  DR_HOST=$(grep -v '^#' sailingsa/deploy/DR_HOST | grep -v '^[[:space:]]*$' | head -1 | tr -d '\r\n')
fi

echo "=== Deploy system audit ==="
echo ""
echo "| Item                  | Value |"
echo "|-----------------------|-------|"
echo "| D/R host IP           | ${DR_HOST:-*(not configured)*} |"
echo "| SSH key used          | $KEY |"
echo "| Deploy path (PROD)    | /var/www/sailingsa (API: /var/www/sailingsa/api/api.py) |"
echo "| Deploy path (D/R)     | Same layout on D/R host |"
echo ""

echo "=== Test connections ==="
echo -n "PROD ($PROD_HOST): "
if ssh -i "$KEY" -o ConnectTimeout=5 -o BatchMode=yes "$PROD_HOST" "echo OK" 2>/dev/null; then
  echo "OK"
else
  echo "FAILED"
fi

if [ -n "$DR_HOST" ]; then
  echo -n "D/R ($DR_HOST): "
  if ssh -i "$KEY" -o ConnectTimeout=5 -o BatchMode=yes $DR_HOST "echo OK" 2>/dev/null; then
    echo "OK"
  else
    echo "FAILED"
  fi
else
  echo "D/R: (skip - not configured. Set SAILINGSA_DR_HOST or sailingsa/deploy/DR_HOST)"
fi
echo ""
echo "See sailingsa/deploy/DEPLOY_AUDIT.md for full audit notes."
