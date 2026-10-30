#!/bin/bash
# Apply patch: Lipton Challenge Cup 2026 sailed line fix
# Changes: Sailed: 3, Discards: 0, To count: 3
# Run from project root

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SQL_FILE="$SCRIPT_DIR/patch_lipton_2026_sailed_line.sql"
SERVER="102.218.215.253"
SSH_KEY="$HOME/.ssh/sailingsa_live_key"

if [ ! -f "$SQL_FILE" ]; then
    echo "ERROR: patch_lipton_2026_sailed_line.sql not found at $SQL_FILE"
    exit 1
fi

echo "=== Uploading SQL to live server ==="
scp -i "$SSH_KEY" "$SQL_FILE" root@${SERVER}:/tmp/

echo "=== Applying patch on live DB ==="
ssh -i "$SSH_KEY" root@${SERVER} "psql postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master -f /tmp/patch_lipton_2026_sailed_line.sql"

echo "=== Restarting API ==="
ssh -i "$SSH_KEY" root@${SERVER} "systemctl restart sailingsa-api && sleep 2 && systemctl is-active sailingsa-api"

echo ""
echo "Done. Lipton 2026 should now show: Sailed: 3, Discards: 0, To count: 3"
echo "Verify: https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup"
