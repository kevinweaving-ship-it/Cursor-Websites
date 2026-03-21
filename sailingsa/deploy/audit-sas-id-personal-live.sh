#!/bin/bash
# READ-ONLY audit: sas_id_personal on LIVE. Run from your machine (has SSH access).
# Usage: bash sailingsa/deploy/audit-sas-id-personal-live.sh
# Paste output to compare with LOCAL.

set -e
SERVER="102.218.215.253"
USER="root"
DBURL="postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"

echo "========== LIVE Step 1 — \\d+ public.sas_id_personal =========="
ssh -o StrictHostKeyChecking=no "${USER}@${SERVER}" "psql $DBURL -c \"\\d+ public.sas_id_personal\""

echo ""
echo "========== LIVE — Row count, min/max id =========="
ssh -o StrictHostKeyChecking=no "${USER}@${SERVER}" "psql $DBURL -c \"SELECT COUNT(*) AS total_rows, MIN(id) AS min_id, MAX(id) AS max_id FROM public.sas_id_personal;\""

echo ""
echo "========== LIVE — id != sa_sailing_id mismatches =========="
ssh -o StrictHostKeyChecking=no "${USER}@${SERVER}" "psql $DBURL -c \"SELECT COUNT(*) AS mismatches FROM public.sas_id_personal WHERE id::text != sa_sailing_id AND sa_sailing_id IS NOT NULL;\""

echo ""
echo "=== LIVE audit done. Compare with LOCAL. ==="
