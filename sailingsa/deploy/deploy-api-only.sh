#!/usr/bin/env bash
# Deploy api.py to live and verify. Run from project root (Project 6).
# Requires: SSH access as root@102.218.215.253 (see sailingsa/deploy/DEPLOY_SLUG_COMMANDS.md)

set -e
SERVER=102.218.215.253
API_DIR=/var/www/sailingsa/api
KEY="${HOME}/.ssh/sailingsa_live_key"
SSH_OPTS="-o StrictHostKeyChecking=no"
[ -f "$KEY" ] && SSH_OPTS="$SSH_OPTS -i $KEY"
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_ROOT"

echo "--- Backup api.py on server ---"
ssh $SSH_OPTS root@${SERVER} "cp ${API_DIR}/api.py ${API_DIR}/api.py.backup.\$(date +%Y%m%d_%H%M%S) && echo Backup ok"

echo "--- Upload api.py ---"
scp $SSH_OPTS api.py root@${SERVER}:${API_DIR}/

echo "--- Restart sailingsa-api ---"
ssh $SSH_OPTS root@${SERVER} "grep -q STATIC_DIR /etc/systemd/system/sailingsa-api.service || (sed -i '/WorkingDirectory=/a Environment=\"STATIC_DIR=/var/www/sailingsa\"' /etc/systemd/system/sailingsa-api.service); systemctl daemon-reload && systemctl restart sailingsa-api && sleep 2 && systemctl status sailingsa-api --no-pager | head -12"

echo ""
echo "--- Verify live regatta SEO (first 120 lines) ---"
curl -s "https://sailingsa.co.za/regatta/2025-sa-youth-nationals-dec-2025" | head -n 120

echo ""
echo "--- journalctl (last 50 lines, check for 500s) ---"
ssh $SSH_OPTS root@${SERVER} "journalctl -u sailingsa-api -n 50 --no-pager"
