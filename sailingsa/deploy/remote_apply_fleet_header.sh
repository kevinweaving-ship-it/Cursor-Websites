#!/bin/bash
set -euo pipefail
TS=$(date +%Y%m%d_%H%M%S)
API=/var/www/sailingsa/api/api.py
cp -a "$API" "${API}.bak.fleet_title_pre.${TS}"
echo "PRE_BACKUP ${API}.bak.fleet_title_pre.${TS}"
chattr -i "$API" || true
python3 /tmp/apply_fleet_header_title_standard.py
chattr +i "$API" || true
sudo -u postgres psql -d sailors_master -v ON_ERROR_STOP=1 -f /tmp/fix_vulcan_fleet_labels.sql
echo "SQL_OK"
systemctl restart sailingsa-api
sleep 2
systemctl is-active sailingsa-api
python3 - <<'PY'
import psycopg2
conn = psycopg2.connect("postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master")
cur = conn.cursor()
cur.execute("""
    SELECT block_id, fleet_label, block_label_raw
    FROM public.regatta_blocks
    WHERE regatta_id='2026-09-13-vulcan-challenge'
    ORDER BY block_id
""")
print("BLOCKS:")
for row in cur.fetchall():
    print(" ", row)
cur.close()
conn.close()
PY
