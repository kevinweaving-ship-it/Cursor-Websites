#!/bin/bash
# Install SailingSA WhatsApp server monitor. Does not touch api.py / housekeeping.py / nginx / PG.
# Usage:
#   bash install-server-monitor.sh            # files only (no cron)
#   bash install-server-monitor.sh --enable   # files + daily/5-min cron
set -euo pipefail
SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
ENABLE=0
if [[ "${1:-}" == "--enable" ]]; then
  ENABLE=1
fi

install -d /usr/local/sbin /etc/sailingsa /var/lib/sailingsa /var/log
install -m 0755 "$SRC_DIR/sailingsa-server-monitor.py" /usr/local/sbin/sailingsa-server-monitor.py
install -m 0755 "$SRC_DIR/sailingsa-server-monitor.wrapper" /usr/local/sbin/sailingsa-server-monitor
if [[ ! -f /etc/sailingsa/server-monitor.conf ]]; then
  install -m 0600 "$SRC_DIR/server-monitor.conf" /etc/sailingsa/server-monitor.conf
fi
chmod 0600 /etc/sailingsa/server-monitor.conf
install -m 0644 "$SRC_DIR/logrotate-sailingsa-server-monitor" /etc/logrotate.d/sailingsa-server-monitor
touch /var/log/sailingsa-server-monitor.log
chmod 0640 /var/log/sailingsa-server-monitor.log || true

if [[ "$ENABLE" -eq 1 ]]; then
  install -m 0644 "$SRC_DIR/cron.d-sailingsa-server-monitor" /etc/cron.d/sailingsa_server_monitor
  echo "enabled cron /etc/cron.d/sailingsa_server_monitor"
else
  echo "installed files only (cron not enabled)"
fi
echo "ok"
ls -l /usr/local/sbin/sailingsa-server-monitor /usr/local/sbin/sailingsa-server-monitor.py /etc/sailingsa/server-monitor.conf
