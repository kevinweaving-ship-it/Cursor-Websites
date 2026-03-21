#!/usr/bin/env bash
# Weekly auto-run: scrape accreditation quals, diff vs member_roles, apply on live.
# Run from project root, or from server with --on-server.
# Cron: 0 3 * * 0 /path/to/run-weekly-accreditation-sync.sh [--on-server]
# When run with --on-server, writes to scrape_runs so dashboard shows Status / Last Success.
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." 2>/dev/null && pwd || echo "$SCRIPT_DIR")"
CSV="${ACCREDITATION_CSV:-$SCRIPT_DIR/accreditation_export.csv}"
ON_SERVER=false
[ "${1:-}" = "--on-server" ] && ON_SERVER=true
if [ "$ON_SERVER" = true ]; then
  LOG_DIR="/var/www/sailingsa/deploy/logs"
else
  LOG_DIR="${SCRIPT_DIR}/logs"
fi
LOG_FILE="${LOG_DIR}/weekly-accreditation-sync.log"
LOCK_FILE="${LOG_DIR}/.lock_accreditation"

RECORDS_ADDED=0
RUN_STATUS="success"
BATCH_INSERTED=false
ACC_BATCH_ID_FILE=""
ACC_BATCH_COUNT_FILE=""

mkdir -p "$LOG_DIR"
log() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" | tee -a "$LOG_FILE"; }

log "--- Weekly accreditation qual sync ---"
if [ -n "${DB_URL:-}" ]; then
  export DB_URL
else
  if [ "$ON_SERVER" = true ]; then
    export DB_URL="postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
  fi
fi

# Run start: insert scrape_runs (running) for dashboard Status / Last Success
if [ "$ON_SERVER" = true ] && [ -n "${DB_URL:-}" ] && command -v psql >/dev/null 2>&1; then
  touch "$LOCK_FILE"
  psql "$DB_URL" -c "INSERT INTO scrape_runs (scrape_name,status) VALUES ('accreditation','running');" >> "$LOG_FILE" 2>&1 || true
  log "scrape_runs started: accreditation running"
fi

# Optional: sas_scrape_batches for legacy batch tracking
BATCH_ID="ACCREDITATION_SYNC_$(date -u +%Y%m%d%H%M)"
if [ "$ON_SERVER" = true ] && [ -n "${DB_URL:-}" ] && command -v psql >/dev/null 2>&1; then
  ACC_BATCH_ID_FILE="${LOG_DIR}/.acc_batch_id_$$"
  ACC_BATCH_COUNT_FILE="${LOG_DIR}/.acc_batch_count_$$"
  printf '%s' "$BATCH_ID" > "$ACC_BATCH_ID_FILE"
  if psql "$DB_URL" -v ON_ERROR_STOP=1 -c "INSERT INTO sas_scrape_batches (batch_id, start_id, valid_count, not_found_count, error_count, started_at) VALUES ('$BATCH_ID', 0, 0, 0, 0, NOW());" >> "$LOG_FILE" 2>&1; then
    BATCH_INSERTED=true
    log "Batch started: $BATCH_ID"
  else
    rm -f "$ACC_BATCH_ID_FILE" "$ACC_BATCH_COUNT_FILE"
  fi
fi

# EXIT trap: update scrape_runs (dashboard Status/Last Success) and optionally sas_scrape_batches
on_exit() {
  local _ec=$?
  [ $_ec -ne 0 ] && RUN_STATUS="failed"
  [ -f "${ACC_BATCH_COUNT_FILE:-}" ] && RECORDS_ADDED=$(cat "$ACC_BATCH_COUNT_FILE")
  if [ -n "${DB_URL:-}" ]; then
    psql "$DB_URL" -c "
      UPDATE scrape_runs
      SET status='$RUN_STATUS',
          completed_at=NOW(),
          records_added=${RECORDS_ADDED:-0}
      WHERE id = (SELECT id FROM scrape_runs WHERE scrape_name='accreditation' ORDER BY started_at DESC LIMIT 1);
    " >> "$LOG_FILE" 2>&1 || true
    log "scrape_runs updated: accreditation status=$RUN_STATUS completed_at=NOW() records_added=${RECORDS_ADDED:-0}"
  fi
  rm -f "$LOCK_FILE" 2>/dev/null || true
  if [ "$BATCH_INSERTED" = true ] && [ -n "${DB_URL:-}" ] && [ -f "${ACC_BATCH_ID_FILE:-}" ]; then
    local bid count ec=0
    bid=$(cat "$ACC_BATCH_ID_FILE")
    count=${RECORDS_ADDED:-0}
    [ $_ec -ne 0 ] && ec=1
    psql "$DB_URL" -c "UPDATE sas_scrape_batches SET completed_at=NOW(), valid_count=$count, error_count=$ec WHERE batch_id='$bid';" >> "$LOG_FILE" 2>&1 || true
    log "Batch updated: $bid valid_count=$count"
  fi
  rm -f "$ACC_BATCH_ID_FILE" "$ACC_BATCH_COUNT_FILE" 2>/dev/null || true
  exit "$_ec"
}
[ "$ON_SERVER" = true ] && trap on_exit EXIT

# Python: on server use venv (has psycopg2 for DB diff)
if [ "$ON_SERVER" = true ] && [ -x "/var/www/sailingsa/api/venv/bin/python3" ]; then
  PYTHON="/var/www/sailingsa/api/venv/bin/python3"
else
  PYTHON="python3"
fi

# 1) Run scraper (use CSV if present, else try without CSV so script tries fetch)
if [ -f "$CSV" ]; then
  log "Using CSV: $CSV"
  $PYTHON "$SCRIPT_DIR/scrape_accreditation_quals.py" --csv "$CSV" --output-dir "$SCRIPT_DIR" 2>&1 | tee -a "$LOG_FILE"
else
  log "No CSV at $CSV; running scraper (may try fetch)."
  $PYTHON "$SCRIPT_DIR/scrape_accreditation_quals.py" --output-dir "$SCRIPT_DIR" 2>&1 | tee -a "$LOG_FILE" || true
fi

# 2) Apply
SQL_FILE=$(ls -t "$SCRIPT_DIR"/member_roles_sync_*.sql 2>/dev/null | head -1)
if [ -z "$SQL_FILE" ]; then
  log "No member_roles_sync_*.sql generated; nothing to apply."
  exit 0
fi

if [ "$ON_SERVER" = true ]; then
  log "Applying on server: $SQL_FILE"
  APPLY_OUT=$(mktemp)
  psql "${DB_URL:-postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master}" -f "$SQL_FILE" 2>&1 | tee "$APPLY_OUT" | tee -a "$LOG_FILE"
  # Sum rows from "INSERT 0 N" lines for valid_count
  VALID_COUNT=$(grep 'INSERT 0' "$APPLY_OUT" | awk '{ sum += $3 } END { print sum + 0 }')
  rm -f "$APPLY_OUT"
  [ "$BATCH_INSERTED" = true ] && [ -n "$ACC_BATCH_COUNT_FILE" ] && printf '%s' "$VALID_COUNT" > "$ACC_BATCH_COUNT_FILE"
  log "Done (server). New quals report: $(ls -t "$SCRIPT_DIR"/new_quals_report_*.txt 2>/dev/null | head -1)"
else
  log "Applying on live via SSH..."
  bash "$SCRIPT_DIR/apply-member-roles-live.sh" 2>&1 | tee -a "$LOG_FILE"
  log "Done (live)."
fi
