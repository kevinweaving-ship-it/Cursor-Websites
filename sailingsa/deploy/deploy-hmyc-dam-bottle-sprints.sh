#!/usr/bin/env bash
# Create live Club event Dam Bottle Sprints.
# URL: https://sailingsa.co.za/regatta/2026-10-10-hmyc-dam-bottle-sprints
# Does NOT upload or replace live api.py (Master/Gold lock).
set -euo pipefail

SERVER="102.218.215.253"
WEB_ROOT="/var/www/sailingsa"
RID="2026-10-10-hmyc-dam-bottle-sprints"
LOGO_NAME="Dam-Bottle-Sprints.png"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOGO_SRC="$SCRIPT_DIR/hmyc-dam-bottle-sprints-logo.png"
KEY="${SAILINGSA_SSH_KEY:-$HOME/.ssh/sailingsa_live_key}"
SSH_OPTS=(-o StrictHostKeyChecking=no)
if [ -f "$KEY" ]; then
  SSH_OPTS+=(-i "$KEY")
fi

if [ ! -f "$LOGO_SRC" ]; then
  echo "ERROR: missing event logo: $LOGO_SRC"
  exit 1
fi

echo "=== 1) Event logo ==="
ssh "${SSH_OPTS[@]}" "root@${SERVER}" "mkdir -p '${WEB_ROOT}/artwork/Event Logo'"
scp "${SSH_OPTS[@]}" "$LOGO_SRC" "root@${SERVER}:${WEB_ROOT}/artwork/Event Logo/${LOGO_NAME}"
ssh "${SSH_OPTS[@]}" "root@${SERVER}" "chown www-data:www-data '${WEB_ROOT}/artwork/Event Logo/${LOGO_NAME}'"

echo "=== 2) SQL (regatta + events, Club / Non SAS) ==="
ssh "${SSH_OPTS[@]}" "root@${SERVER}" 'bash -s' <<'REMOTE'
set -euo pipefail
DB_URL=$(grep -E 'Environment="DB_URL=' /etc/systemd/system/sailingsa-api.service | head -1 | sed -E 's/Environment="DB_URL=//; s/"$//')
psql "$DB_URL" -v ON_ERROR_STOP=1 <<'SQL'
BEGIN;
INSERT INTO public.regattas (
  regatta_id, regatta_number, event_name, year, regatta_type,
  host_club_id, host_club_code, host_club_name, province_name,
  start_date, end_date, result_status, import_status, result_type, class_layout,
  event_rating_level, event_rating_type, event_scope, event_rating_status,
  event_rating_locked, event_rating_locked_at, event_rating_locked_by,
  ranking_eligible, governing_authority, provenance_status
) VALUES (
  '2026-10-10-hmyc-dam-bottle-sprints', 999011, 'Dam Bottle Sprints', 2026, 'CLUB',
  98, 'HMYC', 'Henley Midmar Yacht Club', 'KZN',
  DATE '2026-10-10', DATE '2026-10-11', NULL, 'manual', 'UNKNOWN', 'single_class',
  50, 'Ordinary Club Race', 'CLUB', 'MANUAL_CONFIRMED',
  TRUE, NOW(), 'club-admin',
  FALSE, 'HMYC', 'manual_club'
)
ON CONFLICT (regatta_id) DO UPDATE SET
  event_name = EXCLUDED.event_name, start_date = EXCLUDED.start_date,
  end_date = EXCLUDED.end_date, event_scope = EXCLUDED.event_scope,
  event_rating_type = EXCLUDED.event_rating_type, ranking_eligible = EXCLUDED.ranking_eligible,
  updated_at = NOW();
INSERT INTO public.events (
  source, source_event_id, event_name, start_date, end_date, event_year,
  venue_raw, host_club_id, host_club_name_raw, event_status, regatta_id,
  match_method, category, organiser, image_url, activity_kind, extras, result_expectation
) VALUES (
  'club', 'club-2026-10-10-hmyc-dam-bottle-sprints', 'Dam Bottle Sprints',
  DATE '2026-10-10', DATE '2026-10-11', 2026, 'Henley Midmar Yacht Club', 98,
  'Henley Midmar Yacht Club', 'scheduled', '2026-10-10-hmyc-dam-bottle-sprints',
  'manual_club', 'Club', 'HMYC', '/artwork/Event Logo/Dam-Bottle-Sprints.png',
  'regatta', '{"sanction":"Non SAS","event_source":"club"}'::jsonb, 'unknown'
)
ON CONFLICT (source, source_event_id) DO UPDATE SET
  event_name = EXCLUDED.event_name, category = EXCLUDED.category,
  image_url = EXCLUDED.image_url, last_seen_at = NOW();
COMMIT;
SQL
REMOTE

echo "=== 3) Header icons (left event logo, right HMYC) ==="
ssh "${SSH_OPTS[@]}" "root@${SERVER}" 'python3 - <<'"'"'PY'"'"'
import json
from pathlib import Path
rid = "2026-10-10-hmyc-dam-bottle-sprints"
entry = {
    "left": "/artwork/Event Logo/Dam-Bottle-Sprints.png",
    "right": "/artwork/Club Logo/HMYC.png",
}
paths = [
    Path("/var/www/sailingsa/data/wc_regatta_header_icons.json"),
    Path("/var/www/sailingsa/static/data/wc_regatta_header_icons.json"),
    Path("/var/www/sailingsa/wc_regatta_header_icons.json"),
    Path("/var/www/sailingsa/deploy/wc_regatta_header_icons.json"),
]
# Prefer the largest existing SSOT so we do not shrink gold.
best = None
best_n = -1
for p in paths:
    if p.is_file():
        try:
            o = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(o, dict) and len(o) > best_n:
            best, best_n = o, len(o)
if not isinstance(best, dict):
    raise SystemExit("no header icons SSOT")
best[rid] = entry
payload = json.dumps(best, ensure_ascii=False, indent=2) + "\n"
for p in paths:
    p.write_text(payload, encoding="utf-8")
    print("wrote", p, "keys", len(best))
# Drop gallery cache so the new event logo is picked up
for cache in (
    Path("/var/tmp/sailingsa_catalogue_event_index.json"),
):
    if cache.exists():
        cache.unlink()
        print("cleared", cache)
PY'

echo "=== 4) Verify (no api.py deploy) ==="
curl -sS -o /tmp/dam-bottle.html -w "HTTP %{http_code} bytes %{size_download}\n" \
  "https://sailingsa.co.za/regatta/${RID}"
python3 - <<'PY'
from pathlib import Path
h = Path("/tmp/dam-bottle.html").read_text(encoding="utf-8", errors="replace")
need = (
    "Dam Bottle Sprints",
    "HMYC",
    "Henley Midmar Yacht Club",
    "Dam-Bottle-Sprints.png",
    "HMYC.png",
)
missing = [n for n in need if n not in h]
print("missing", missing or "none")
if missing:
    raise SystemExit(1)
print("live page OK")
PY

echo ""
echo "Audit: https://sailingsa.co.za/regatta/${RID}"
