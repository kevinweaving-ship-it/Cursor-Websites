#!/usr/bin/env bash
# One-time: create events table (migrations 145 + 146) and load CSV. Run on server with DB_URL set.
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." 2>/dev/null && pwd || cd "$SCRIPT_DIR/.." && pwd)"
if [ -z "${DB_URL:-}" ] && [ -z "${DATABASE_URL:-}" ]; then
  echo "ERROR: Set DB_URL or DATABASE_URL first."; exit 1
fi
DB="${DB_URL:-$DATABASE_URL}"
psql "$DB" -f "$ROOT/database/migrations/145_events_table.sql" 2>/dev/null || true
psql "$DB" -f "$ROOT/database/migrations/146_events_list_scrape_columns.sql"
CSV="$SCRIPT_DIR/sas_events_list.csv"
[ -f "$CSV" ] || CSV="$ROOT/sailingsa/deploy/sas_events_list.csv"
[ -f "$CSV" ] || { echo "WARNING: No sas_events_list.csv. Copy it to deploy/ or run scraper first."; exit 1; }
cd "$ROOT" && python3 load_events_csv_to_db.py --csv "$CSV"
echo "Done. Refresh https://sailingsa.co.za/admin/events-audit"
