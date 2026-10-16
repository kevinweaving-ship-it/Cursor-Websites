#!/bin/bash
# Install Hansekop + Voelklip keypads on the GoWifi / Aerialnet box.
# Does not change the SailingSA box. Landing index.html is copied when present.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WWW="${AERIALNET_WWW:-/home/user-data/www/aerialnet.co.za}"
API_DIR="${AERIALNET_API_DIR:-/opt/aerialnet-arial}"
DATA_DIR="${AERIALNET_DATA_DIR:-/var/www/aerialnet/data}"
NGINX_SNIP="/etc/nginx/snippets/aerialnet-arial.conf"
NGINX_MIAB="${AERIALNET_NGINX_MIAB:-/home/user-data/www/aerialnet.co.za.conf}"
MIAB_MGMT="${MAILINABOX_MGMT:-/home/vmpeppyo/mailinabox/management}"
MIAB_PY="${MAILINABOX_PY:-/usr/local/lib/mailinabox/env/bin/python}"

if [ "$(id -u)" -ne 0 ]; then
  echo "run as root on box.gowifi.co.za"
  exit 1
fi

echo "www=$WWW api=$API_DIR"

mkdir -p "$WWW/hansekop" "$WWW/voelklip" "$WWW/arial" "$API_DIR" "$DATA_DIR"
if [ -f "$ROOT/index.html" ]; then
  cp -a "$ROOT/index.html" "$WWW/index.html"
fi
cp -a "$ROOT/hansekop/index.html" "$WWW/hansekop/index.html"
cp -a "$ROOT/voelklip/index.html" "$WWW/voelklip/index.html"
cp -a "$ROOT/arial/." "$WWW/arial/"
cp -a "$ROOT/api/arial_api.py" "$ROOT/api/arial_app.py" "$ROOT/api/requirements.txt" "$API_DIR/"
if [ -f "$ROOT/api/registry.json" ]; then
  cp -a "$ROOT/api/registry.json" "$DATA_DIR/registry.json"
fi
chown -R www-data:www-data "$WWW/hansekop" "$WWW/voelklip" "$WWW/arial" "$DATA_DIR"
chmod 770 "$DATA_DIR"
# Watcher runs as wapoc and must append the keypad WhatsApp tab log.
usermod -aG www-data wapoc 2>/dev/null || true
touch "$DATA_DIR/whatsapp_log.jsonl"
chown wapoc:www-data "$DATA_DIR/whatsapp_log.jsonl" 2>/dev/null || chown www-data:www-data "$DATA_DIR/whatsapp_log.jsonl"
chmod 660 "$DATA_DIR/whatsapp_log.jsonl"

if [ ! -x "$API_DIR/venv/bin/python" ]; then
  apt-get update -qq
  apt-get install -y -qq python3-venv python3-pip >/dev/null
  python3 -m venv "$API_DIR/venv"
fi
"$API_DIR/venv/bin/pip" install -q -r "$API_DIR/requirements.txt"

install -m 644 "$ROOT/deploy/aerialnet-hansekop-api.service" /etc/systemd/system/aerialnet-hansekop-api.service
install -m 644 "$ROOT/deploy/aerialnet-voelklip-api.service" /etc/systemd/system/aerialnet-voelklip-api.service
touch /etc/aerialnet-olarm.env /etc/aerialnet-tuya.env
chmod 600 /etc/aerialnet-olarm.env /etc/aerialnet-tuya.env

# Optional: copy tokens + PIN users from the Sailing box if this host can reach it.
SAIL="${SAILING_BOX:-root@102.218.215.253}"
if [ -n "${SAILING_SSH_KEY:-}" ] && [ -f "${SAILING_SSH_KEY}" ]; then
  SSH=(ssh -i "$SAILING_SSH_KEY" -o StrictHostKeyChecking=accept-new -o ConnectTimeout=8)
  SCP=(scp -i "$SAILING_SSH_KEY" -o StrictHostKeyChecking=accept-new -o ConnectTimeout=8)
else
  SSH=(ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=8)
  SCP=(scp -o StrictHostKeyChecking=accept-new -o ConnectTimeout=8)
fi
if "${SSH[@]}" "$SAIL" "test -f /etc/sailingsa-olarm.env" 2>/dev/null; then
  echo "copying Olarm/Tuya env and keypad users from Sailing box (not printed)"
  "${SCP[@]}" "$SAIL:/etc/sailingsa-olarm.env" /etc/aerialnet-olarm.env >/dev/null
  "${SCP[@]}" "$SAIL:/etc/sailingsa-tuya.env" /etc/aerialnet-tuya.env >/dev/null || true
  "${SCP[@]}" "$SAIL:/var/www/sailingsa/api/data/arial_users.json" "$DATA_DIR/arial_users.json" >/dev/null || true
  chmod 600 /etc/aerialnet-olarm.env /etc/aerialnet-tuya.env
  chown www-data:www-data "$DATA_DIR/arial_users.json" 2>/dev/null || true
else
  echo "Sailing box not reachable from here — leave /etc/aerialnet-olarm.env for a later copy"
fi

install -m 644 "$ROOT/deploy/nginx-aerialnet-keypads.conf" "$NGINX_SNIP"
install -m 644 "$ROOT/deploy/nginx-aerialnet-keypads.conf" "$NGINX_MIAB"
chown user-data:root "$NGINX_MIAB" 2>/dev/null || true

# Let Mail-in-a-Box regenerate local.conf so it includes www/aerialnet.co.za.conf
# itself. Do not patch local.conf — MIAB owns that file.
if [ -d "$MIAB_MGMT" ] && [ -x "$MIAB_PY" ]; then
  "$MIAB_PY" - "$MIAB_MGMT" <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
from utils import load_environment
from web_update import do_web_update
print(do_web_update(load_environment()))
PY
fi

systemctl disable --now aerialnet-nginx-include.timer 2>/dev/null || true

nginx -t
systemctl daemon-reload
systemctl enable --now aerialnet-hansekop-api aerialnet-voelklip-api
systemctl reload nginx

echo "---- status ----"
systemctl is-active aerialnet-hansekop-api aerialnet-voelklip-api nginx
curl -sS -o /dev/null -w "hansekop_html %{http_code}\n" https://aerialnet.co.za/hansekop/ || true
curl -sS -o /dev/null -w "voelklip_html %{http_code}\n" https://aerialnet.co.za/voelklip/ || true
curl -sS https://aerialnet.co.za/api/arial/_health || true
echo
curl -sS https://aerialnet.co.za/api/voelklip/status | head -c 400 || true
echo
echo "URLs: https://aerialnet.co.za/hansekop/  https://aerialnet.co.za/voelklip/"
