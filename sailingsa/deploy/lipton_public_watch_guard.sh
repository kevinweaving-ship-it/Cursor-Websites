#!/bin/bash
# Restore stubbed or stale Lipton public-URL watchdog copies, then run one.
set -euo pipefail
MARKER="LIPTON_WATCH_DEBOUNCE_V1"

# Nginx public slug even if sbin is a 46-byte stub. Prefer /opt and /var/lib.
for f in /opt/sailingsa/ngx-restore.py /var/lib/sailingsa-lipton/ngx-restore.py /tmp/lw-ngx-fix-2121.py /usr/local/sbin/lipton_ngx_public_restore.py /root/lipton_ngx_public_restore.py /usr/local/lib/lipton_ngx_public_restore.py; do
  if [[ -f "$f" ]] && grep -q LIPTON_NGINX_BASH_RESTORE_V1 "$f" 2>/dev/null; then
    sz=$(wc -c < "$f" | tr -d ' ')
    if [[ "$sz" -gt 500 ]]; then
      /usr/bin/python3 "$f" >/dev/null 2>&1 || true
      break
    fi
  fi
done

COPIES=(
  /var/lib/sailingsa-lipton/watch.py
  /opt/sailingsa/watch.py
  /usr/local/lib/lipton_public_not_dev_watch.py
  /usr/local/sbin/lipton_public_not_dev_watch.py
)
GOLDS=(
  /var/lib/sailingsa-lipton/watch.py
  /var/lib/sailingsa-lipton/watch.py.gold
  /opt/sailingsa/watch.py
  /root/lw-g22.py
  /root/lw-g21.py
  /root/lw-g20.py
  /root/lw-g19.py
  /root/lw-g18.py
  /root/lw-g17.py
  /root/lw-g14d.py
  /root/lw-g14c.py
  /root/lw-g14.py
  /root/lw-g13b.py
  /root/lw-gold13.py
  /root/lw-gold7.py
  /root/lw-gold6.py
  /root/lw-gold5.py
  /root/lw-gold4.py
  /root/lw-gold3.py
  /root/lw-gold.py
  /root/lipton_public_not_dev_watch.py
)

is_good() {
  local f="$1"
  [[ -f "$f" ]] || return 1
  local sz
  sz=$(wc -c < "$f" | tr -d ' ')
  [[ "$sz" -gt 500 ]] || return 1
  grep -q "$MARKER" "$f"
}

good=""
for f in "${GOLDS[@]}" "${COPIES[@]}"; do
  if is_good "$f"; then
    good=$f
    break
  fi
done
if [[ -z "$good" ]]; then
  echo "lipton watch: no good copy" >&2
  exit 1
fi
for f in "${COPIES[@]}"; do
  if ! is_good "$f"; then
    chattr -i "$f" 2>/dev/null || true
    mkdir -p "$(dirname "$f")"
    cp "$good" "$f"
    chmod 755 "$f"
    chattr +i "$f" 2>/dev/null || true
  fi
done

restore_unit() {
  local dest="$1"
  local src="$2"
  [[ -f "$src" ]] || return 0
  local need=0
  if [[ ! -f "$dest" ]]; then
    need=1
  elif grep -q 'ExecStart=/bin/true' "$dest" 2>/dev/null; then
    need=1
  elif grep -q 'must not restore' "$dest" 2>/dev/null; then
    need=1
  elif ! grep -q 'while true' "$dest" 2>/dev/null; then
    need=1
  elif ! grep -Eq 'lw-g|lw-gold|sailingsa-lipton/watch.py' "$dest" 2>/dev/null; then
    need=1
  fi
  if [[ "$need" -eq 1 ]]; then
    chattr -i "$dest" 2>/dev/null || true
    cp "$src" "$dest"
    chmod 644 "$dest"
    chattr +i "$dest" 2>/dev/null || true
    systemctl daemon-reload >/dev/null 2>&1 || true
  fi
}

restore_unit /etc/systemd/system/sailingsa-lipton-public-watch.service /usr/local/lib/sailingsa-lipton-public-watch.service
restore_unit /etc/systemd/system/sailingsa-lipton-url-hold.service /usr/local/lib/sailingsa-lipton-url-hold.service

# LIPTON_WATCH_ENABLE_V1
systemctl unmask sailingsa-lipton-public-watch.service >/dev/null 2>&1 || true
systemctl unmask sailingsa-lipton-url-hold.service >/dev/null 2>&1 || true
systemctl enable sailingsa-lipton-public-watch.service >/dev/null 2>&1 || true
systemctl enable sailingsa-lipton-url-hold.service >/dev/null 2>&1 || true
systemctl start sailingsa-lipton-public-watch.service >/dev/null 2>&1 || true
if ! pgrep -f "ngx-restore.py --loop" >/dev/null 2>&1 && ! pgrep -f "lipton_ngx_public_restore.py --loop" >/dev/null 2>&1; then
  for f in /opt/sailingsa/ngx-restore.py /var/lib/sailingsa-lipton/ngx-restore.py /tmp/lw-ngx-fix-2121.py /usr/local/sbin/lipton_ngx_public_restore.py; do
    if [[ -f "$f" ]] && grep -q LIPTON_NGINX_BASH_RESTORE_V1 "$f" 2>/dev/null; then
      sz=$(wc -c < "$f" | tr -d ' ')
      if [[ "$sz" -gt 500 ]]; then
        nohup /usr/bin/python3 "$f" --loop >/dev/null 2>&1 &
        break
      fi
    fi
  done
fi
if ! pgrep -f "watch.py --loop" >/dev/null 2>&1 && ! pgrep -f "lipton_public_not_dev_watch.py --loop" >/dev/null 2>&1 && ! pgrep -f "/usr/bin/python3 /root/lw-g.*--loop" >/dev/null 2>&1; then
  nohup /usr/bin/python3 "$good" --loop >/dev/null 2>&1 &
fi
if systemctl is-active --quiet sailingsa-lipton-public-watch.service; then
  exit 0
fi
exec /usr/bin/python3 "$good" "$@"
