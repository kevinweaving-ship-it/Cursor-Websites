#!/usr/bin/env bash
# Postfix pipe: every inbound mail to cursor@ is saved and auto-disputed
# if it came from Cursor support. Kevin still gets a copy via the alias CC.
set -euo pipefail
DIR="${CURSOR_CREDITS_INBOUND:-/var/lib/cursor-credits/inbound}"
LOG="${CURSOR_CREDITS_LOG:-/var/log/cursor-credits-mail.log}"
PY="${CURSOR_CREDITS_PY:-/usr/local/lib/cursor-credits/cursor_credits_self_check.py}"
mkdir -p "$DIR"
f="$DIR/$(date -u +%Y%m%dT%H%M%SZ).$$.eml"
cat > "$f"
if [[ -f "$PY" ]]; then
  /usr/bin/python3 "$PY" dispute --inbound "$f" --send >> "$LOG" 2>&1 || true
fi
