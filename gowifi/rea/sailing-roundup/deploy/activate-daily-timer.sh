#!/bin/bash
# Root-only. Install the prepared daily timer and enable it.
# Edition dates stay the Monday after the event (run-monday.sh issue_date).
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Run as root on GoWifi" >&2; exit 1; }
ROOT=/opt/rea/work/sailing-roundup
UNIT=/etc/systemd/system/sailing-roundup.timer
SRC="$ROOT/deploy/sailing-roundup.timer"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="$ROOT/backups/daily-reliability-20261025"
install -d -m 755 -o rea -g rea "$BACKUP_DIR"
if [ -e "$UNIT" ] && [ ! -e "$BACKUP_DIR/installed-monday.timer" ]; then
  cp -p "$UNIT" "$BACKUP_DIR/installed-monday.timer"
fi
cp -p "$UNIT" "$BACKUP_DIR/sailing-roundup.timer.before-$STAMP" 2>/dev/null || true
[ -f "$SRC" ] || { echo "missing $SRC" >&2; exit 1; }
grep -q '^OnCalendar=\*-\*-\* 06:00:00 Africa/Johannesburg$' "$SRC" || {
  echo "refusing $SRC: expected daily 06:00 Africa/Johannesburg" >&2
  exit 1
}
systemd-analyze calendar '*-*-* 06:00:00 Africa/Johannesburg' >/dev/null
# Stop the already-active timer before daemon-reload. Reloading a daily
# calendar onto a live Monday timer with Persistent=true would immediately
# catch up every missed 06:00 since the last Monday run.
systemctl stop sailing-roundup.timer
systemctl reset-failed sailing-roundup.service 2>/dev/null || true
install -d /var/lib/systemd/timers
touch /var/lib/systemd/timers/stamp-sailing-roundup.timer
install -m 644 "$SRC" "$UNIT"
systemctl daemon-reload
# Stamp "now" so Persistent=true only applies to future daily 06:00 slots.
# Do not start the oneshot service; do not restart the timer after enable.
systemctl enable --now sailing-roundup.timer
systemctl show sailing-roundup.timer -p ActiveState -p UnitFileState -p TimersCalendar -p NextElapseUSecRealtime
