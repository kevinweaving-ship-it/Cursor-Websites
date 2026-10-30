#!/bin/bash
# Upload the ILCA 4 deploy guard, patch, and alias module.
# Does not copy api.py and does not restart the API.
# Usage: bash sailingsa/deploy/stage_ilca4_incoming.sh [ssh-key] [user@host]
set -euo pipefail

KEY="${1:-$HOME/.ssh/sailingsa_live_key}"
HOST="${2:-root@102.218.215.253}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

if [ -f "$KEY" ]; then
  SCP=(scp -i "$KEY" -o StrictHostKeyChecking=no)
  SSH=(ssh -i "$KEY" -o StrictHostKeyChecking=no)
elif [ -n "${SSHPASS:-}" ]; then
  SCP=(sshpass -e scp -o StrictHostKeyChecking=no)
  SSH=(sshpass -e ssh -o StrictHostKeyChecking=no)
else
  echo "ERROR: SSH key not found: $KEY"
  exit 1
fi

echo "Staging ILCA 4 guard on $HOST"
"${SSH[@]}" "$HOST" "mkdir -p /root/incoming"
"${SCP[@]}" "$ROOT/sailingsa/deploy/deploy_api_verified.sh" "$HOST:/root/deploy_api_verified.sh"
"${SCP[@]}" "$ROOT/sailingsa/deploy/deploy_api.sh" "$HOST:/root/deploy_api.sh"
"${SCP[@]}" "$ROOT/sailingsa/deploy/ilca4_keep_live_api.sh" "$HOST:/root/ilca4_keep_live_api.sh"
"${SCP[@]}" "$ROOT/sailingsa/deploy/patches/20261004_ilca4_live_api.patch" "$HOST:/root/incoming/20261004_ilca4_live_api.patch"
"${SCP[@]}" "$ROOT/sailingsa/api/class_name_aliases.py" "$HOST:/root/incoming/class_name_aliases.py"
if [ -f "$ROOT/ilca4_canonical.py" ]; then
  "${SCP[@]}" "$ROOT/ilca4_canonical.py" "$HOST:/root/incoming/ilca4_canonical.py"
fi
"${SSH[@]}" "$HOST" "chmod +x /root/deploy_api_verified.sh /root/deploy_api.sh /root/ilca4_keep_live_api.sh"
echo "ILCA 4 guard staged. Live api.py was not replaced and the API was not restarted."
