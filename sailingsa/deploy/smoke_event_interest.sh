#!/bin/bash
# Live smoke after controlled deploy. Read-only GETs + optional write on disposable event.
# Usage: bash sailingsa/deploy/smoke_event_interest.sh https://sailingsa.co.za
set -euo pipefail
BASE="${1:-https://sailingsa.co.za}"
BASE="${BASE%/}"
FAIL=0

pass() { echo "PASS $1"; }
fail() { echo "FAIL $1"; FAIL=$((FAIL + 1)); }

code=$(curl -sS -o /tmp/eci_batch.json -w '%{http_code}' \
  "$BASE/api/events/interest?ids=168679,246456" || true)
if [ "$code" = "200" ]; then pass "GET /api/events/interest → 200"; else fail "GET /api/events/interest → $code"; fi

code=$(curl -sS -o /tmp/eci_classes.json -w '%{http_code}' \
  "$BASE/api/events/168679/interest/classes" || true)
if [ "$code" = "200" ]; then
  pass "GET interest/classes → 200"
  python3 - <<'PY' || fail "classes payload shape"
import json
d=json.load(open("/tmp/eci_classes.json"))
assert "classes" in d
print("classes", len(d.get("classes") or []))
if not d.get("classes"):
    raise SystemExit("empty edition classes — blocker")
PY
else
  fail "GET interest/classes → $code"
fi

html=$(curl -sS "$BASE/blank.html" || true)
echo "$html" | grep -q 'data-event-id=' && pass "blank.html has data-event-id" || fail "blank.html missing data-event-id"
echo "$html" | grep -q 'event-interest.js' && pass "blank.html loads event-interest.js" || fail "blank.html missing event-interest.js"
echo "$html" | grep -q 'event-interest.css' && pass "blank.html loads event-interest.css" || fail "blank.html missing event-interest.css"

code=$(curl -sS -o /dev/null -w '%{http_code}' "$BASE/js/event-interest.js" || true)
[ "$code" = "200" ] && pass "js/event-interest.js served" || fail "js/event-interest.js → $code"
code=$(curl -sS -o /dev/null -w '%{http_code}' "$BASE/css/event-interest.css" || true)
[ "$code" = "200" ] && pass "css/event-interest.css served" || fail "css/event-interest.css → $code"

if [ "$FAIL" -gt 0 ]; then
  echo "Smoke: $FAIL failed"
  exit 1
fi
echo "Smoke: OK"
exit 0
