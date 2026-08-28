#!/bin/bash
# Kill the 1s watch that restores the old weather page on the public Lipton URL.
set -euo pipefail

STUB_PY='#!/usr/bin/python3
raise SystemExit(0)
'
STUB_SH='#!/bin/bash
exit 0
'

echo '=== stop loops and units ==='
systemctl stop sailingsa-lipton-public-watch.service 2>/dev/null || true
systemctl disable sailingsa-lipton-public-watch.service 2>/dev/null || true
systemctl mask sailingsa-lipton-public-watch.service 2>/dev/null || true
systemctl stop sailingsa-lipton-public-watch.timer 2>/dev/null || true
systemctl disable sailingsa-lipton-public-watch.timer 2>/dev/null || true
systemctl mask sailingsa-lipton-public-watch.timer 2>/dev/null || true
pkill -f lipton_public_watch_guard 2>/dev/null || true
pkill -f lipton_public_not_dev 2>/dev/null || true
pkill -f lipton_apply_nginx_public_proxy 2>/dev/null || true
pkill -f 'while true; do /usr/local/lib/lipton_public_watch_guard' 2>/dev/null || true
sleep 1
pkill -9 -f lipton_public_watch_guard 2>/dev/null || true
pkill -9 -f lipton_public_not_dev 2>/dev/null || true

mkdir -p /root/disabled-lipton-not-dev

stub() {
  local f="$1"
  local kind="$2"
  [ -e "$f" ] || return 0
  chattr -i "$f" 2>/dev/null || true
  cp -a "$f" "/root/disabled-lipton-not-dev/$(basename "$f").$(date +%s)" 2>/dev/null || true
  if [ "$kind" = py ]; then
    printf '%s' "$STUB_PY" > "$f"
  else
    printf '%s' "$STUB_SH" > "$f"
  fi
  chmod 755 "$f"
  chattr +i "$f" 2>/dev/null || true
  echo "stubbed $f"
}

# Any path that restores old public page
while IFS= read -r f; do
  case "$f" in
    *.py) stub "$f" py ;;
    *) stub "$f" sh ;;
  esac
done <<'LIST'
/usr/local/lib/lipton_public_watch_guard.sh
/usr/local/sbin/lipton_public_not_dev_watch.py
/usr/local/sbin/lipton_apply_nginx_public_proxy_once.py
/tmp/lipton_public_not_dev_watch.py
/tmp/lipton_hold_check.py
LIST

find /usr/local/sbin /usr/local/lib /tmp /root -maxdepth 2 -type f \( \
  -name '*lipton*public*watch*' -o -name '*lipton*public*proxy*' -o -name '*public_not_dev*' \
  \) 2>/dev/null | while read -r f; do
  case "$f" in
    /root/disabled-lipton-not-dev/*) continue ;;
    *.py) stub "$f" py ;;
    *.sh) stub "$f" sh ;;
  esac
done

# systemd unit files: make them no-ops then mask
for u in /etc/systemd/system/sailingsa-lipton-public-watch.service \
         /etc/systemd/system/sailingsa-lipton-public-watch.timer \
         /lib/systemd/system/sailingsa-lipton-public-watch.service; do
  if [ -f "$u" ]; then
    chattr -i "$u" 2>/dev/null || true
    cp -a "$u" /root/disabled-lipton-not-dev/ 2>/dev/null || true
    cat > "$u" <<'UNIT'
[Unit]
Description=disabled — must not restore old Lipton event page
[Service]
Type=oneshot
ExecStart=/bin/true
[Install]
WantedBy=multi-user.target
UNIT
    chattr +i "$u" 2>/dev/null || true
  fi
done
systemctl daemon-reload 2>/dev/null || true
systemctl mask sailingsa-lipton-public-watch.service 2>/dev/null || true

echo '=== remaining processes ==='
ps aux | grep -Ei 'lipton_public|public_not_dev|public_watch' | grep -v grep || echo none
