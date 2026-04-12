#!/usr/bin/env bash
# Ensure sailingsa-api.service has Restart=always and RestartSec=1 on LIVE, then restart and report PIDs.
# Run from project root. Uses SSH key from SSH_LIVE.md.

set -e
SERVER="${SAILINGSA_SERVER:-102.218.215.253}"
KEY="${SAILINGSA_SSH_KEY:-$HOME/.ssh/sailingsa_live_key}"
SVC="/etc/systemd/system/sailingsa-api.service"

ssh -i "$KEY" -o ConnectTimeout=10 root@"$SERVER" "bash -s" -- << 'REMOTE'
set -e
SVC="/etc/systemd/system/sailingsa-api.service"

echo "=== 1. Current Restart settings ==="
grep -E "^(Restart|RestartSec)=" "$SVC" 2>/dev/null || echo "(none found)"

echo ""
echo "=== 2. Ensure Restart=always and RestartSec=1 ==="
if ! grep -q "^Restart=" "$SVC" 2>/dev/null; then
  sed -i '/\[Service\]/a Restart=always' "$SVC"
  echo "Added Restart=always"
fi
if ! grep -q "^RestartSec=" "$SVC" 2>/dev/null; then
  sed -i '/Restart=always/a RestartSec=1' "$SVC"
  echo "Added RestartSec=1"
fi
sed -i 's/^Restart=.*/Restart=always/' "$SVC"
sed -i 's/^RestartSec=.*/RestartSec=1/' "$SVC"
echo "Set Restart=always, RestartSec=1"
grep -E "^(Restart|RestartSec)=" "$SVC"

echo ""
echo "=== 3. PID before restart ==="
PID_BEFORE=$(pgrep -f "uvicorn api:app" 2>/dev/null | head -1 || true)
echo "PID before: ${PID_BEFORE:-none}"

echo ""
echo "=== 4. daemon-reload and restart ==="
systemctl daemon-reload
systemctl restart sailingsa-api
sleep 2

echo ""
echo "=== 5. systemctl status sailingsa-api ==="
systemctl status sailingsa-api --no-pager || true

echo ""
echo "=== 6. PID after restart ==="
PID_AFTER=$(pgrep -f "uvicorn api:app" 2>/dev/null | head -1 || true)
echo "PID after: ${PID_AFTER:-none}"

echo ""
echo "=== 7. ps aux | grep uvicorn ==="
ps aux | grep -E "[u]vicorn api:app" || true

echo ""
echo "=== REPORT ==="
echo "Restart setting: $(grep -E "^(Restart|RestartSec)=" "$SVC" 2>/dev/null | tr '\n' ' ')"
echo "PID before: ${PID_BEFORE:-none}"
echo "PID after:  ${PID_AFTER:-none}"
if [ -n "$PID_BEFORE" ] && [ -n "$PID_AFTER" ] && [ "$PID_BEFORE" != "$PID_AFTER" ]; then
  echo "Result: PID changed — restart works."
elif [ -n "$PID_AFTER" ]; then
  echo "Result: Service running (single PID or workers)."
else
  echo "Result: No uvicorn PID found — check journalctl -u sailingsa-api -n 50"
fi
REMOTE

echo ""
echo "Done. Check REPORT above."
