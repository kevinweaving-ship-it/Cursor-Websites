#!/usr/bin/env bash
# Backup local sailors_master DB and write proof (result 4563, regatta 385 count).
# Run from project root. Requires: pg_dump, psql (or set DATABASE_URL).
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BACKUPS="$PROJECT_ROOT/backups"
STAMP=$(date +%Y%m%d_%H%M%S)
DB_URL="${DATABASE_URL:-${DB_URL:-postgresql://sailors_user:change_me_strong@localhost:5432/sailors_master}}"

mkdir -p "$BACKUPS"

DUMP="$BACKUPS/local_sailors_master_${STAMP}.sql"
PROOF="$BACKUPS/PROOF_local_${STAMP}.txt"

echo "=== Local backup ==="
pg_dump "$DB_URL" --no-owner --no-acl -f "$DUMP"
echo "Dump: $DUMP"

echo "=== Proof (local) ==="
{
  echo "Backup: local_sailors_master_${STAMP}.sql"
  echo "At: $(date +%Y-%m-%dT%H:%M:%S%z)"
  echo "--- result_id 4563 ---"
  psql "$DB_URL" -t -A -c "SELECT result_id, helm_name, helm_sa_sailing_id, fleet_label, class_canonical FROM results WHERE result_id = 4563;" || true
  echo ""
  echo "--- regatta 385 result count ---"
  psql "$DB_URL" -t -A -c "SELECT COUNT(*) FROM results WHERE regatta_id = '385-2026-hyc-cape-classic';" || true
} > "$PROOF"
echo "Proof: $PROOF"
cat "$PROOF"
