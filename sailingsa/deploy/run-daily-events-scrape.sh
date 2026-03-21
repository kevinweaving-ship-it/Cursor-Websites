#!/usr/bin/env bash
# Daily auto: scrape SAS events list (sailing.org.za/events/).
# Writes sas_events_list.csv and optionally sas_events_list_YYYYMMDD.csv.
# Cron: 0 4 * * * /path/to/run-daily-events-scrape.sh [--on-server]
# Dashboard: creates .lock_events while running; updates scrape_runs at end so status switches Running → Success.
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." 2>/dev/null && pwd || true)"
ON_SERVER=false
[ "${1:-}" = "--on-server" ] && ON_SERVER=true

# Dashboard popup reads from /var/www/sailingsa/deploy/logs — use that path on server
if [ "$ON_SERVER" = true ]; then
  LOG_DIR="/var/www/sailingsa/deploy/logs"
else
  LOG_DIR="${SCRIPT_DIR}/logs"
fi
LOG_FILE="${LOG_DIR}/daily-events-scrape.log"
LOCK_FILE="${LOG_DIR}/.lock_events"

mkdir -p "$LOG_DIR"
touch "$LOG_FILE"
log() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" | tee -a "$LOG_FILE"; }

# DB_URL for loader when run by cron (same pattern as run-weekly-accreditation-sync.sh)
if [ -n "${DB_URL:-}" ]; then
  export DB_URL
elif [ "$ON_SERVER" = true ]; then
  export DB_URL="postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
fi

# When run by cron: create lock so dashboard shows "Running"; when run by API, lock is already created.
# Cron should not append its own logfile redirection because this script already writes to LOG_FILE.
if [ "$ON_SERVER" = true ]; then
  touch "$LOCK_FILE"
fi

BATCH_ID="EVENTS_$(date -u +%Y%m%d%H%M)"
RUN_ID=""
RECORDS_ADDED=0
RUN_STATUS="success"

# Insert scrape_runs (running) when DB available; set RUN_ID so trap can always update on exit
if [ -n "${DB_URL:-}" ] && command -v psql >/dev/null 2>&1; then
  run_id_out=$(psql "$DB_URL" -v ON_ERROR_STOP=1 -t -A -c "INSERT INTO scrape_runs (scrape_name, status, batch_id) VALUES ('events', 'running', '$BATCH_ID') RETURNING id;" 2>>"$LOG_FILE" | head -1) || true
  run_id_out=$(printf '%s' "$run_id_out" | tr -d ' \n\r')
  if [ -n "$run_id_out" ] && [[ "$run_id_out" =~ ^[0-9]+$ ]]; then
    RUN_ID="$run_id_out"
    log "scrape_runs started: batch_id=$BATCH_ID run_id=$RUN_ID"
  else
    log "scrape_runs insert failed (table may not exist); continuing without."
  fi
fi

# EXIT trap: always update scrape_runs (running -> success/failed). With set -e, any command error triggers exit and trap runs with non-zero $?
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
      log "scrape_runs updated: id=$RUN_ID status=$RUN_STATUS completed_at=NOW() records_added=$RECORDS_ADDED"
    fi
    rm -f "$LOCK_FILE" 2>/dev/null || true
    exit $_ec
  }' EXIT
fi

log "--- Daily SAS events list scrape ---"

# On server use fixed path so dashboard and cron find the scraper
if [ "$ON_SERVER" = true ] && [ -f "/var/www/sailingsa/scripts/scrape_sas_events_list.py" ]; then
  SCRAPER="/var/www/sailingsa/scripts/scrape_sas_events_list.py"
  OUTPUT_DIR="$SCRIPT_DIR"
elif [ -n "$PROJECT_ROOT" ] && [ -f "$PROJECT_ROOT/scrape_sas_events_list.py" ]; then
  SCRAPER="$PROJECT_ROOT/scrape_sas_events_list.py"
  OUTPUT_DIR="$SCRIPT_DIR"
else
  SCRAPER="$SCRIPT_DIR/scrape_sas_events_list.py"
  OUTPUT_DIR="$SCRIPT_DIR"
fi

if [ ! -f "$SCRAPER" ]; then
  log "Scraper not found: $SCRAPER"
  exit 1
fi

PYTHON="python3"
if [ "$ON_SERVER" = true ] && [ -x "/var/www/sailingsa/api/venv/bin/python3" ]; then
  PYTHON="/var/www/sailingsa/api/venv/bin/python3"
fi

export PYTHONUNBUFFERED=1
$PYTHON "$SCRAPER" --output-dir "$OUTPUT_DIR" --date-stamp --no-detail 2>&1 | tee -a "$LOG_FILE"
log "Scrape done. Latest: $OUTPUT_DIR/sas_events_list.csv"

# Load into DB when DATABASE_URL or DB_URL is set (e.g. on server)
if [ "$ON_SERVER" = true ] && [ -f "/var/www/sailingsa/scripts/load_events_csv_to_db.py" ]; then
  LOADER="/var/www/sailingsa/scripts/load_events_csv_to_db.py"
elif [ -n "$PROJECT_ROOT" ] && [ -f "$PROJECT_ROOT/load_events_csv_to_db.py" ]; then
  LOADER="$PROJECT_ROOT/load_events_csv_to_db.py"
else
  LOADER=""
fi
if [ -n "${LOADER:-}" ] && ( [ -n "${DATABASE_URL:-}" ] || [ -n "${DB_URL:-}" ] ); then
  if [ -f "$OUTPUT_DIR/sas_events_list.csv" ]; then
    log "Loading events into DB..."
    $PYTHON "$LOADER" --csv "$OUTPUT_DIR/sas_events_list.csv" 2>&1 | tee -a "$LOG_FILE"
    log "Load done."
    ADDED_LINE=$(grep -E "Upserted [0-9]+ events|Loaded [0-9]+ rows" "$LOG_FILE" 2>/dev/null | tail -1)
    if [ -n "$ADDED_LINE" ]; then
      RECORDS_ADDED=$(echo "$ADDED_LINE" | sed -n 's/.*Upserted \([0-9]*\) events.*/\1/p')
      [ -z "$RECORDS_ADDED" ] && RECORDS_ADDED=$(echo "$ADDED_LINE" | sed -n 's/.*Loaded \([0-9]*\) rows.*/\1/p')
      [ -z "$RECORDS_ADDED" ] && RECORDS_ADDED=0
    fi
  fi
fi
log "Done. records_added=$RECORDS_ADDED"
