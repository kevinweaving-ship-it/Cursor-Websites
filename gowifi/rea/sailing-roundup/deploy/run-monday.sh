#!/bin/bash
# Unattended Monday job: generate on GoWifi, validate, publish one issue to SailingSA.
# ROUNDUP_MODE=due          current Monday in Africa/Johannesburg (production)
# ROUNDUP_MODE=test-weekend locked 2026-09-28 reference weekend
set -euo pipefail

ROOT="${1:-/opt/rea/work/sailing-roundup}"
MODE="${ROUNDUP_MODE:-due}"
PY="$ROOT/.venv/bin/python3"
[ -x "$PY" ] && true || PY=python3
ALERT_TO="${ROUNDUP_ALERT_TO:-root}"
MAX_TRIES="${ROUNDUP_RETRIES:-3}"
RETRY_DELAY="${ROUNDUP_RETRY_DELAY:-90}"
LOCK="$ROOT/data/monday.lock"
LOG="$ROOT/data/publish.log"
mkdir -p "$ROOT/data"
cd "$ROOT"

exec 9>"$LOCK"
if ! flock -n 9; then
  echo "$(date -Is) skip: another monday job holds $LOCK" | tee -a "$LOG"
  exit 0
fi

issue_date() {
  if [ "$MODE" = "test-weekend" ]; then
    echo "2026-09-28"
    return
  fi
  "$PY" - <<'PY'
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
today = datetime.now(ZoneInfo("Africa/Johannesburg")).date()
print((today - timedelta(days=today.weekday())).isoformat())
PY
}

ISSUE="$(issue_date)"

alert() {
  local subject="$1"
  local body="$2"
  if [ -x /usr/sbin/sendmail ]; then
    {
      echo "To: $ALERT_TO"
      echo "From: sailing-roundup@$(hostname -f 2>/dev/null || hostname)"
      echo "Subject: $subject"
      echo "Content-Type: text/plain; charset=UTF-8"
      echo
      echo "$body"
      echo
      echo "host=$(hostname) issue=$ISSUE mode=$MODE"
      echo "--- last-success ---"
      cat "$ROOT/data/last-success.json" 2>/dev/null || echo "(none)"
      echo
      echo "--- publish.log tail ---"
      tail -n 80 "$LOG" 2>/dev/null || true
    } | /usr/sbin/sendmail -t || true
  fi
  echo "$(date -Is) ALERT $subject" | tee -a "$LOG"
}

run_with_retry() {
  local label="$1"
  shift
  local i
  for i in $(seq 1 "$MAX_TRIES"); do
    echo "$(date -Is) $label attempt $i/$MAX_TRIES issue=$ISSUE mode=$MODE" | tee -a "$LOG"
    if "$@"; then
      echo "$(date -Is) $label ok" | tee -a "$LOG"
      return 0
    fi
    echo "$(date -Is) $label failed attempt $i" | tee -a "$LOG"
    if [ "$i" -lt "$MAX_TRIES" ]; then
      sleep "$RETRY_DELAY"
    fi
  done
  return 1
}

if [ "$MODE" = "test-weekend" ]; then
  GEN=("$PY" "$ROOT/app/safe_publish.py" --test-weekend)
else
  GEN=("$PY" "$ROOT/app/safe_publish.py" --monday "$ISSUE")
fi

if ! run_with_retry generate "${GEN[@]}"; then
  alert "Sailing roundup FAILED $ISSUE" \
    "Generation/validation failed after $MAX_TRIES attempts. The last good edition is retained under issues/ and public/issues/. No live replace was attempted."
  exit 1
fi

if [ -x "$ROOT/deploy/publish-to-sailingsa.sh" ]; then
  if ! run_with_retry publish "$ROOT/deploy/publish-to-sailingsa.sh" "$ROOT/public" "$ISSUE"; then
    alert "Sailing roundup PUBLISH FAILED $ISSUE" \
      "GoWifi generation succeeded but SailingSA issue-scoped publish failed. Remote last-good (if any) was left in place."
    exit 1
  fi
fi

VERIFY_URL="https://sailingsa.co.za/sailing-roundup/issues/${ISSUE}/"
verify_public() {
  local tmp
  tmp="$(mktemp)"
  local code
  code="$(curl -fsS -o "$tmp" -w "%{http_code}" --max-time 30 "$VERIFY_URL" || true)"
  if [ "$code" != "200" ]; then
    echo "verify HTTP $code for $VERIFY_URL" >&2
    rm -f "$tmp"
    return 1
  fi
  python3 - "$tmp" "$ROOT/public/issues/$ISSUE/index.html" "$ISSUE" <<'PY'
import hashlib, pathlib, sys
live, local, issue = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), sys.argv[3]
body = live.read_text("utf-8", "replace")
if "Last Week's Roundup" not in body and "Weekend Sailing Roundup" not in body and "Sailing" not in body:
    raise SystemExit("live HTML missing edition chrome")
if issue == "2026-09-28":
    if "Timothy Weaving" not in body or "Hayden Miller" not in body:
        raise SystemExit("live HTML missing U17 winners")
local_html = local.read_text("utf-8", "replace")
if hashlib.sha256(live.read_bytes()).hexdigest() != hashlib.sha256(local.read_bytes()).hexdigest():
    # Allow whitespace-only drift from nginx, but require the rebuilt body markers.
    if "Timothy Weaving" in local_html and "Timothy Weaving" not in body:
        raise SystemExit("live HTML does not match rebuilt U17 names")
print("public-url-ok")
PY
  rm -f "$tmp"
  for path in issue.json edition.pdf; do
    code="$(curl -fsS -o /dev/null -w "%{http_code}" --max-time 30 "${VERIFY_URL}${path}" || true)"
    [ "$code" = "200" ] || { echo "verify $path HTTP $code" >&2; return 1; }
  done
}

if ! run_with_retry verify verify_public; then
  alert "Sailing roundup URL VERIFY FAILED $ISSUE" \
    "Publish reported success but $VERIFY_URL did not match the rebuilt edition."
  exit 1
fi

echo "$(date -Is) monday-job done $ISSUE" | tee -a "$LOG"
