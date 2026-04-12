#!/usr/bin/env bash
# Apply latest member_roles_sync_*.sql on live DB. Run from project root.
# See sailingsa/deploy/SSH_LIVE.md. No API restart needed (member_roles is data only).
# Generate SQL first: python3 sailingsa/deploy/scrape_accreditation_quals.py [--csv ...]
set -e
SERVER=102.218.215.253
KEY="${HOME}/.ssh/sailingsa_live_key"
SSH_OPTS="-o StrictHostKeyChecking=no"
[ -f "$KEY" ] && SSH_OPTS="$SSH_OPTS -i $KEY"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# Use latest member_roles_sync_*.sql
SQL_FILE=$(ls -t "$SCRIPT_DIR"/member_roles_sync_*.sql 2>/dev/null | head -1)
if [ -z "$SQL_FILE" ]; then
  echo "No member_roles_sync_*.sql found. Run: python3 sailingsa/deploy/scrape_accreditation_quals.py [--csv ...]"
  exit 1
fi
echo "--- Using $SQL_FILE ---"
echo "--- Upload SQL ---"
scp $SSH_OPTS "$SQL_FILE" root@${SERVER}:/tmp/member_roles_sync.sql
echo "--- Run psql on server ---"
ssh $SSH_OPTS root@${SERVER} 'psql postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master -f /tmp/member_roles_sync.sql'
echo ""
echo "Member roles sync applied on live."
