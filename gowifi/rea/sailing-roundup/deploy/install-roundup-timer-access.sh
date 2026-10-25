#!/bin/bash
# Install the localhost forced-command path so REA can activate/status
# sailing-roundup.timer without sudo or a shell. Run as root on GoWifi.
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo "run as root on GoWifi" >&2; exit 1; }

SRC="${1:-/opt/rea/work/sailing-roundup}"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR=/opt/rea/work/sailing-roundup/backups/daily-reliability-20261025
KEY=/opt/rea/.ssh/id_sailing_roundup_timer
AUTH=/root/.ssh/authorized_keys
HELPER=/usr/local/sbin/sailing-roundup-timer
ACTIVATE=/usr/local/sbin/sailing-roundup-activate-daily-timer
LIB=/usr/local/lib/sailing-roundup
CTL=/usr/local/bin/roundup-timer-ctl
# Never exec from the REA-writable project tree.
STALE=/opt/rea/work/sailing-roundup/deploy/activate-daily-timer.sh

install -d -m 755 -o rea -g rea "$BACKUP_DIR"
install -d -m 700 /root/.ssh
install -d -m 700 -o rea -g rea /opt/rea/.ssh
install -d -m 755 -o root -g root "$LIB"
[ -f "$AUTH" ] || install -m 600 /dev/null "$AUTH"
cp -p "$AUTH" "$BACKUP_DIR/root-authorized_keys.before-$STAMP"
cp -p /etc/systemd/system/sailing-roundup.timer "$BACKUP_DIR/etc-sailing-roundup.timer.before-$STAMP" 2>/dev/null || true
if [ -e "$STALE" ]; then
  cp -p "$STALE" "$BACKUP_DIR/activate-daily-timer.sh.stale-$STAMP"
fi

# Root-controlled copies only. Helper must not follow REA-writable paths.
grep -q '^OnCalendar=\*-\*-\* 06:00:00 Africa/Johannesburg$' "$SRC/deploy/sailing-roundup.timer" || {
  echo "refusing $SRC/deploy/sailing-roundup.timer: expected daily 06:00 Africa/Johannesburg" >&2
  exit 1
}
[ "$(grep -c '^OnCalendar=' "$SRC/deploy/sailing-roundup.timer")" -eq 1 ]
install -m 644 -o root -g root "$SRC/deploy/sailing-roundup.timer" "$LIB/sailing-roundup.timer"
install -m 755 -o root -g root "$SRC/deploy/activate-daily-timer.sh" "$ACTIVATE"
install -m 755 -o root -g root "$SRC/deploy/sailing-roundup-timer-helper.sh" "$HELPER"
install -m 755 -o root -g root "$SRC/deploy/roundup-timer-ctl" "$CTL"
chown root:root "$HELPER" "$ACTIVATE" "$CTL" "$LIB/sailing-roundup.timer"
chmod 755 "$HELPER" "$ACTIVATE" "$CTL"
chmod 644 "$LIB/sailing-roundup.timer"
# Remove the old REA-tree executable so root cannot be lured back to it.
if [ -e "$STALE" ]; then
  rm -f "$STALE"
fi

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

echo "installed $HELPER $ACTIVATE $CTL $LIB/sailing-roundup.timer"
