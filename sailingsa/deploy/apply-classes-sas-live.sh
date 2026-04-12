#!/usr/bin/env bash
# Add SAS class columns and seed data on live DB. Run from project root.
# See sailingsa/deploy/SSH_LIVE.md — scp + ssh psql + restart.
# Generate SQL first: python3 sailingsa/deploy/scrape_sas_classes.py
set -e
SERVER=102.218.215.253
KEY="${HOME}/.ssh/sailingsa_live_key"
SSH_OPTS="-o StrictHostKeyChecking=no"
[ -f "$KEY" ] && SSH_OPTS="$SSH_OPTS -i $KEY"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SQL_FILE="$SCRIPT_DIR/classes_sas_columns.sql"

if [ ! -f "$SQL_FILE" ]; then
  echo "Run first: python3 sailingsa/deploy/scrape_sas_classes.py"
  exit 1
fi

echo "--- Upload SQL ---"
scp $SSH_OPTS "$SQL_FILE" root@${SERVER}:/tmp/classes_sas_columns.sql
echo "--- Run psql on server, then restart sailingsa-api ---"
# Live DB password has no ! (see server: grep DB_URL /etc/systemd/system/sailingsa-api.service)
ssh $SSH_OPTS root@${SERVER} 'psql postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master -f /tmp/classes_sas_columns.sql && systemctl restart sailingsa-api && systemctl is-active sailingsa-api'
echo ""
echo "Classes SAS columns applied on live."
