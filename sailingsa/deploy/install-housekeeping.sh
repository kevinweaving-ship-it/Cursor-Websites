#!/bin/bash
# Install SailingSA housekeeping on the live server.
# Safe to re-run. Does not touch api.py, nginx, Postgres, or frontend.
set -euo pipefail

SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
if [[ ! -f "$SRC_DIR/sailingsa-housekeeping.py" ]]; then
  echo "missing $SRC_DIR/sailingsa-housekeeping.py" >&2
  exit 1
fi

install -d /usr/local/sbin /etc/sailingsa /etc/systemd/journald.conf.d /var/log
install -m 0755 "$SRC_DIR/sailingsa-housekeeping.py" /usr/local/sbin/sailingsa-housekeeping.py
install -m 0755 "$SRC_DIR/sailingsa-housekeeping.wrapper" /usr/local/sbin/sailingsa-housekeeping
if [[ ! -f /etc/sailingsa/housekeeping-keep.list ]]; then
  install -m 0644 "$SRC_DIR/housekeeping-keep.list" /etc/sailingsa/housekeeping-keep.list
else
  # Keep local additions; refresh comments/known entries by merging missing KEEP paths.
  while IFS= read -r line; do
    [[ -z "$line" || "$line" == \#* ]] && continue
    if ! grep -qxF "$line" /etc/sailingsa/housekeeping-keep.list; then
      echo "$line" >> /etc/sailingsa/housekeeping-keep.list
    fi
  done < "$SRC_DIR/housekeeping-keep.list"
fi
install -m 0644 "$SRC_DIR/cron.d-sailingsa-housekeeping" /etc/cron.d/sailingsa_housekeeping
install -m 0644 "$SRC_DIR/journald-sailingsa-retention.conf" \
  /etc/systemd/journald.conf.d/sailingsa-retention.conf
install -m 0644 "$SRC_DIR/logrotate-sailingsa-housekeeping" \
  /etc/logrotate.d/sailingsa-housekeeping

if [[ -f /etc/logrotate.d/rsyslog ]]; then
  if [[ ! -f /etc/logrotate.d/rsyslog.pre-housekeeping ]]; then
    cp -a /etc/logrotate.d/rsyslog /etc/logrotate.d/rsyslog.pre-housekeeping
  fi
fi
install -m 0644 "$SRC_DIR/logrotate-rsyslog-sailingsa" /etc/logrotate.d/rsyslog

# Apply journald cap. Do not rm active logs.
systemctl restart systemd-journald
journalctl --vacuum-size=500M >> /var/log/sailingsa-housekeeping.log 2>&1 || true

# First-time rotate of oversized syslog via logrotate (rename + rsyslog signal).
if [[ ! -f /var/lib/sailingsa-housekeeping-logrotate-seeded ]]; then
  mkdir -p /var/lib
  logrotate -f /etc/logrotate.d/rsyslog || true
  touch /var/lib/sailingsa-housekeeping-logrotate-seeded
fi

chmod 644 /etc/cron.d/sailingsa_housekeeping
echo "installed sailingsa-housekeeping"
ls -l /usr/local/sbin/sailingsa-housekeeping /usr/local/sbin/sailingsa-housekeeping.py
echo "cron:"; cat /etc/cron.d/sailingsa_housekeeping
echo "journald drop-in:"; cat /etc/systemd/journald.conf.d/sailingsa-retention.conf
