#!/usr/bin/env bash
# Deploy HMYC club-admin PY event page to live.
# Audit URL (working title until the event is named):
#   https://sailingsa.co.za/dev-1/club/hmyc/event
# Run from project root. See sailingsa/deploy/SSH_LIVE.md
set -euo pipefail

SERVER="102.218.215.253"
WEB_ROOT="/var/www/sailingsa"
KEY="${SAILINGSA_SSH_KEY:-$HOME/.ssh/sailingsa_live_key}"
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SSH_OPTS=(-o StrictHostKeyChecking=no)
[ -f "$KEY" ] && SSH_OPTS+=(-i "$KEY")

if [ ! -f "$PROJECT_ROOT/api.py" ]; then
  echo "ERROR: api.py missing. Run from repo root."
  exit 1
fi

echo "=== 1) Backend module ==="
ssh "${SSH_OPTS[@]}" "root@${SERVER}" "mkdir -p ${WEB_ROOT}/sailingsa/backend"
scp "${SSH_OPTS[@]}" \
  "$PROJECT_ROOT/sailingsa/__init__.py" \
  "root@${SERVER}:${WEB_ROOT}/sailingsa/__init__.py"
scp "${SSH_OPTS[@]}" \
  "$PROJECT_ROOT/sailingsa/backend/__init__.py" \
  "root@${SERVER}:${WEB_ROOT}/sailingsa/backend/__init__.py"
scp "${SSH_OPTS[@]}" \
  "$PROJECT_ROOT/sailingsa/backend/hmyc_club_py_event_dev.py" \
  "root@${SERVER}:${WEB_ROOT}/sailingsa/backend/hmyc_club_py_event_dev.py"

echo "=== 2) api.py (verified deploy) ==="
ssh "${SSH_OPTS[@]}" "root@${SERVER}" "mkdir -p /root/incoming"
scp "${SSH_OPTS[@]}" \
  "$PROJECT_ROOT/api.py" "root@${SERVER}:/root/incoming/api.py"
ssh "${SSH_OPTS[@]}" "root@${SERVER}" "/root/deploy_api_verified.sh"

echo "=== 3) Verify audit URL ==="
curl -sS -o /tmp/hmyc-club-event-live.html -w "HTTP %{http_code}\n" \
  "https://sailingsa.co.za/dev-1/club/hmyc/event"
python3 - <<'PY'
from pathlib import Path
h = Path("/tmp/hmyc-club-event-live.html").read_text(encoding="utf-8", errors="replace")
need = ("HMYC Club Event", "id=\"fleet\"", ">Time<", ">PY<", "Lorrian Wells")
missing = [n for n in need if n not in h]
if missing:
    raise SystemExit(f"live page missing {missing}")
print("live page OK")
PY

echo ""
echo "Audit: https://sailingsa.co.za/dev-1/club/hmyc/event"
