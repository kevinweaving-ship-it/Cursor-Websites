#!/usr/bin/env bash
# Daily SAS ID registry scrape: runs sas_member_scrape.py, logs to scrape_runs for dashboard.
# Cron: 0 2 * * * /var/www/sailingsa/deploy/run-sas-id-registry-scrape.sh --on-server
# Requires: scrape_runs table (migration 171), DB_URL on server. Python: sailingsa/scripts/sas_member_scrape.py
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." 2>/dev/null && pwd || true)"
ON_SERVER=false
START_ID=""
[ "${1:-}" = "--on-server" ] && ON_SERVER=true
if [ "${2:-}" = "--start-id" ] && [ -n "${3:-}" ]; then START_ID="${3}"; fi
if [ "${1:-}" = "--start-id" ] && [ -n "${2:-}" ]; then START_ID="${2}"; fi
for arg in "$@"; do case "$arg" in --start-id=*) START_ID="${arg#--start-id=}" ;; esac; done

# Dashboard popup reads from /var/www/sailingsa/deploy/logs — use that path on server.
# Cron should not append its own logfile redirection because this script already writes to LOG_FILE.
if [ "$ON_SERVER" = true ]; then
  LOG_DIR="/var/www/sailingsa/deploy/logs"
else
  LOG_DIR="${SCRIPT_DIR}/logs"
fi
LOG_FILE="${LOG_DIR}/sas-id-registry-scrape.log"

mkdir -p "$LOG_DIR"
touch "$LOG_FILE"
log() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" | tee -a "$LOG_FILE"; }

# Resolve Python scraper (same pattern as run-daily-events-scrape.sh)
if [ -n "$PROJECT_ROOT" ] && [ -f "$PROJECT_ROOT/sailingsa/scripts/sas_member_scrape.py" ]; then
  SCRAPER="$PROJECT_ROOT/sailingsa/scripts/sas_member_scrape.py"
else
  SCRAPER="$SCRIPT_DIR/../scripts/sas_member_scrape.py"
fi
if [ ! -f "$SCRAPER" ]; then
  log "Scraper not found: $SCRAPER"
  exit 1
fi

PYTHON="python3"
if [ "$ON_SERVER" = true ] && [ -x "/var/www/sailingsa/api/venv/bin/python3" ]; then
  PYTHON="/var/www/sailingsa/api/venv/bin/python3"
fi

if [ "$ON_SERVER" = true ]; then
  export DB_URL="${DB_URL:-postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master}"
fi

BATCH_ID="REGISTRY_$(date -u +%Y%m%d%H%M)"
RUN_ID=""
RECORDS_ADDED=0
RUN_STATUS="success"

log "--- SAS ID Registry scrape ---"

# Insert scrape_runs (running); capture RUN_ID so trap always updates on exit
if [ -n "${DB_URL:-}" ] && command -v psql >/dev/null 2>&1; then
  run_id_out=$(psql "$DB_URL" -v ON_ERROR_STOP=1 -t -A -c "INSERT INTO scrape_runs (scrape_name, status, batch_id) VALUES ('sas_registry', 'running', '$BATCH_ID') RETURNING id;" 2>>"$LOG_FILE" | head -1) || true
  run_id_out=$(printf '%s' "$run_id_out" | tr -d ' \n\r')
  if [ -n "$run_id_out" ] && [[ "$run_id_out" =~ ^[0-9]+$ ]]; then
    RUN_ID="$run_id_out"
    log "scrape_runs started: batch_id=$BATCH_ID run_id=$RUN_ID"
  else
    log "scrape_runs insert failed (table may not exist); continuing without."
  fi
fi

# EXIT trap: always update scrape_runs (running -> success/failed). set -e triggers trap on any error.
if [ "$ON_SERVER" = true ]; then
  trap '{
    _ec=$?
    [ $_ec -ne 0 ] && RUN_STATUS="failed"
    if [ -n "$RUN_ID" ]; then
      psql "$DB_URL" -c "
        UPDATE scrape_runs
        SET status='"'"'"$RUN_STATUS"'"'"',
            completed_at=NOW(),
            records_added=${RECORDS_ADDED:-0}
        WHERE id=$RUN_ID;
      " >> "$LOG_FILE" 2>&1 || true
      log "scrape_runs updated: id=$RUN_ID status=$RUN_STATUS completed_at=NOW() records_added=${RECORDS_ADDED:-0}"
    fi
    exit $_ec
  }' EXIT
fi

# Run scraper (stderr has "done: start=... end=... added=N"); unbuffered so dashboard popup sees lines live
export PYTHONUNBUFFERED=1
[ -n "$RUN_ID" ] && export SCRAPE_RUN_ID="$RUN_ID"
[ -n "$START_ID" ] && export START_ID="$START_ID"
$PYTHON "$SCRAPER" 2>&1 | tee -a "$LOG_FILE"
SCRAPE_EXIT=$?
ADDED_LINE=$(grep -E "added=[0-9]+" "$LOG_FILE" 2>/dev/null | tail -1)
if [ -n "$ADDED_LINE" ]; then
  RECORDS_ADDED=$(echo "$ADDED_LINE" | sed -n 's/.*added=\([0-9]*\).*/\1/p')
  [ -z "$RECORDS_ADDED" ] && RECORDS_ADDED=0
fi
log "Done. records_added=$RECORDS_ADDED"
exit "$SCRAPE_EXIT"
