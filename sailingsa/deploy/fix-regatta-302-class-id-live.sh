#!/usr/bin/env bash
# Fix NULL class_id in results for regatta 302 on production DB. Run from project root.
# See sailingsa/deploy/SSH_LIVE.md (manual pattern: scp + ssh with -i key, psql then restart).
set -e
SERVER=102.218.215.253
KEY="${HOME}/.ssh/sailingsa_live_key"
SSH_OPTS="-o StrictHostKeyChecking=no"
[ -f "$KEY" ] && SSH_OPTS="$SSH_OPTS -i $KEY"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SQL_FILE="$SCRIPT_DIR/fix-regatta-302-class-id.sql"

echo "--- Upload SQL ---"
scp $SSH_OPTS "$SQL_FILE" root@${SERVER}:/tmp/fix-regatta-302-class-id.sql
echo "--- Run psql on server, then restart sailingsa-api ---"
ssh $SSH_OPTS root@${SERVER} 'psql postgresql://sailors_user:SailSA_Pg_Beta2026!@localhost:5432/sailors_master -f /tmp/fix-regatta-302-class-id.sql && systemctl restart sailingsa-api'
echo ""
echo "302 CLASS IDS FIXED"
