#!/bin/bash
# Install the localhost forced-command path so REA can activate/status
# sailing-roundup.timer without sudo or a shell. Run as root on GoWifi.
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo "run as root on GoWifi" >&2; exit 1; }

SRC="${1:-/opt/rea/work/sailing-roundup}"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="$SRC/backups/daily-reliability-20261025"
KEY=/opt/rea/.ssh/id_sailing_roundup_timer
AUTH=/root/.ssh/authorized_keys
HELPER=/usr/local/sbin/sailing-roundup-timer
CTL=/usr/local/bin/roundup-timer-ctl

install -d -m 755 -o rea -g rea "$BACKUP_DIR"
install -d -m 700 /root/.ssh
install -d -m 700 -o rea -g rea /opt/rea/.ssh
[ -f "$AUTH" ] || install -m 600 /dev/null "$AUTH"
cp -p "$AUTH" "$BACKUP_DIR/root-authorized_keys.before-$STAMP"
cp -p /etc/systemd/system/sailing-roundup.timer "$BACKUP_DIR/etc-sailing-roundup.timer.before-$STAMP" 2>/dev/null || true

# Activate script stays in the project deploy dir; helper/ctl are root-owned.
chown root:root "$SRC/deploy/activate-daily-timer.sh"
chmod 755 "$SRC/deploy/activate-daily-timer.sh"
install -m 755 "$SRC/deploy/sailing-roundup-timer-helper.sh" "$HELPER"
install -m 755 "$SRC/deploy/roundup-timer-ctl" "$CTL"
chown root:root "$HELPER" "$CTL"
# Helper must not be writable by rea.
chmod 755 "$HELPER" "$CTL"

if [ ! -f "$KEY" ]; then
  sudo -u rea -H ssh-keygen -t ed25519 -f "$KEY" -N "" -C "roundup-timer-localhost" -q
fi
chmod 600 "$KEY"
chown rea:rea "$KEY" "$KEY.pub"

PUB="$(tr -d '\n' < "$KEY.pub")"
MARKER="roundup-timer-localhost"
TMP="$(mktemp)"
if [ -s "$AUTH" ]; then
  grep -v "$MARKER" "$AUTH" > "$TMP" || true
else
  : > "$TMP"
fi
printf 'command="%s",restrict,from="127.0.0.1,::1" %s\n' "$HELPER" "$PUB" >> "$TMP"
install -m 600 "$TMP" "$AUTH"
rm -f "$TMP"

# Host key for 127.0.0.1 only; do not print keys.
sudo -u rea -H ssh-keyscan -t ed25519,rsa,ecdsa 127.0.0.1 2>/dev/null \
  | sudo -u rea -H tee -a /opt/rea/.ssh/known_hosts >/dev/null
sudo -u rea -H sort -u /opt/rea/.ssh/known_hosts -o /opt/rea/.ssh/known_hosts
chown rea:rea /opt/rea/.ssh/known_hosts
chmod 600 /opt/rea/.ssh/known_hosts

# Confirm tunnel NoNewPrivileges was not touched.
systemctl show openai-rea-tunnel.service -p NoNewPrivileges --value | grep -qx yes

echo "installed $HELPER and $CTL"
