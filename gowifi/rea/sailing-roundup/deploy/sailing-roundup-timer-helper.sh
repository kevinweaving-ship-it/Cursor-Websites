#!/bin/bash
# Root-owned forced-command helper. Accepts only activate|status.
# Invoked by sshd via authorized_keys command= ; never a shell.
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
# Exact tokens only; no extra words, paths, or shell metacharacters.
case "$op" in
  activate)
    exec /opt/rea/work/sailing-roundup/deploy/activate-daily-timer.sh
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
