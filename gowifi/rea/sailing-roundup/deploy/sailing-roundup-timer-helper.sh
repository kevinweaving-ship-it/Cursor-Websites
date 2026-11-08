#!/bin/bash
# Root-owned forced-command helper. Accepts only activate|status.
# Invoked by sshd via authorized_keys command= ; never a shell.
# Executes only root-controlled paths under /usr/local.
set -euo pipefail
if [ "$(id -u)" -ne 0 ]; then
  echo "denied" >&2
  exit 2
fi
if [ -n "${SSH_ORIGINAL_COMMAND+x}" ]; then
  op="$SSH_ORIGINAL_COMMAND"
elif [ "$#" -eq 1 ]; then
  op="$1"
else
  echo "denied: only activate|status" >&2
  exit 2
fi

ACTIVATE=/usr/local/sbin/sailing-roundup-activate-daily-timer
# Exact tokens only; no extra words, paths, or shell metacharacters.
case "$op" in
  activate)
    [ -x "$ACTIVATE" ] || { echo "denied: helper not installed" >&2; exit 2; }
    [ "$(stat -c '%u:%g' "$ACTIVATE")" = "0:0" ] || { echo "denied: activate not root-owned" >&2; exit 2; }
    exec "$ACTIVATE"
    ;;
  status)
    systemctl is-enabled sailing-roundup.timer
    systemctl is-active sailing-roundup.timer
    systemctl show sailing-roundup.timer -p ActiveState -p UnitFileState -p TimersCalendar -p NextElapseUSecRealtime -p LastTriggerUSec
    systemctl list-timers sailing-roundup.timer --all --no-pager
    systemd-analyze calendar --iterations=3 '*-*-* 06:00:00 Africa/Johannesburg'
    ;;
  *)
    echo "denied: only activate|status" >&2
    exit 2
    ;;
esac
