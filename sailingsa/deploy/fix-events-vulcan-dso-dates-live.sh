#!/usr/bin/env bash
# One-shot live fixes for known bad event end_dates (run on server with DB_URL).
# Vulcan 370405: same-day 12 Sep 2026 (not through 18 Sep).
# DSO 361162: end 31 May 2026 (not 2029).
set -euo pipefail
DB="${DB_URL:-${DATABASE_URL:-}}"
if [ -z "$DB" ]; then
  echo "Set DB_URL or DATABASE_URL" >&2
  exit 1
fi
psql "$DB" -v ON_ERROR_STOP=1 <<'SQL'
UPDATE events
SET end_date = start_date, last_seen_at = now()
WHERE source = 'sas' AND source_event_id = '370405'
  AND end_date IS DISTINCT FROM start_date;

UPDATE events
SET end_date = DATE '2026-05-31', last_seen_at = now()
WHERE source = 'sas' AND source_event_id = '361162'
  AND end_date IS DISTINCT FROM DATE '2026-05-31';

SELECT source_event_id, event_name, start_date, end_date
FROM events
WHERE source = 'sas' AND source_event_id IN ('370405', '361162')
ORDER BY source_event_id;
SQL
