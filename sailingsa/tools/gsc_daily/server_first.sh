#!/bin/bash
# Ubuntu GSC daily collector. Monitoring only.
set -euo pipefail
export TZ=Africa/Johannesburg
export PYTHONPATH="${PYTHONPATH:-/opt/sailingsa-gsc}"
LOG=/var/log/sailingsa-gsc-daily.log
mkdir -p /var/lib/sailingsa/gsc-daily /var/log
{
  echo "===== $(date '+%Y-%m-%d %H:%M:%S %Z') gsc-server start ====="
  /usr/bin/python3 -m sailingsa.tools.gsc_daily.run_server_daily "$@"
  echo "===== $(date '+%Y-%m-%d %H:%M:%S %Z') gsc-server end $? ====="
} >>"$LOG" 2>&1
