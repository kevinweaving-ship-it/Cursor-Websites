#!/bin/bash
# LIVE only: two read-only queries for sas_id_personal parity.
# Run from your machine (you have SSH access). Paste output to compare with LOCAL.
# Credentials from sailingsa/deploy/SSH_LIVE.md and *.exp

SERVER="102.218.215.253"
# DB password from backup-live-with-proof.exp / apply-patch-4563-live.exp
export PGPASSWORD="SailSA_Pg_Beta2026"

echo "=== LIVE 1: total_rows, min_id, max_id ==="
ssh -o StrictHostKeyChecking=no root@102.218.215.253 "export PGPASSWORD=\"$PGPASSWORD\"; psql -U sailors_user -d sailors_master -h localhost -c \"
  SELECT
    COUNT(*) AS total_rows,
    MIN(id) AS min_id,
    MAX(id) AS max_id
  FROM public.sas_id_personal;
\""

echo ""
echo "=== LIVE 2: mismatches (id != sa_sailing_id) ==="
ssh -o StrictHostKeyChecking=no root@102.218.215.253 "export PGPASSWORD=\"$PGPASSWORD\"; psql -U sailors_user -d sailors_master -h localhost -c \"
  SELECT COUNT(*) AS mismatches
  FROM public.sas_id_personal
  WHERE id::text != sa_sailing_id
    AND sa_sailing_id IS NOT NULL;
\""

unset PGPASSWORD
echo ""
echo "=== Compare to LOCAL: total_rows=28217, min_id=1, max_id=28217, mismatches=0 ==="
