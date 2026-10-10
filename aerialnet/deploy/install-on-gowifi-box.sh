#!/bin/bash
# Install Hansekop + Voelklip keypads on the GoWifi / Aerialnet box.
# Does not change the SailingSA box. Landing page at / is left as-is.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WWW="${AERIALNET_WWW:-/home/user-data/www/aerialnet.co.za}"
API_DIR="${AERIALNET_API_DIR:-/opt/aerialnet-arial}"
DATA_DIR="${AERIALNET_DATA_DIR:-/var/www/aerialnet/data}"
NGINX_SNIP="/etc/nginx/snippets/aerialnet-arial.conf"

if [ "$(id -u)" -ne 0 ]; then
  echo "run as root on box.gowifi.co.za"
  exit 1
fi

echo "www=$WWW api=$API_DIR"

mkdir -p "$WWW/hansekop" "$WWW/voelklip" "$WWW/arial" "$API_DIR" "$DATA_DIR"
cp -a "$ROOT/hansekop/index.html" "$WWW/hansekop/index.html"
cp -a "$ROOT/voelklip/index.html" "$WWW/voelklip/index.html"
cp -a "$ROOT/arial/." "$WWW/arial/"
cp -a "$ROOT/api/arial_api.py" "$ROOT/api/arial_app.py" "$ROOT/api/requirements.txt" "$API_DIR/"
if [ -f "$ROOT/api/registry.json" ]; then
  cp -a "$ROOT/api/registry.json" "$DATA_DIR/registry.json"
fi
chown -R www-data:www-data "$WWW/hansekop" "$WWW/voelklip" "$WWW/arial" "$DATA_DIR"
chmod 750 "$DATA_DIR"

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
# Inject include into the aerialnet.co.za TLS server if missing.
python3 - "$NGINX_SNIP" <<'PY'
import pathlib, sys
snip = sys.argv[1]
include = f"    include {snip};\n"
candidates = [
    pathlib.Path("/etc/nginx/conf.d/local.conf"),
    *pathlib.Path("/etc/nginx/sites-enabled").glob("*"),
    *pathlib.Path("/etc/nginx/conf.d").glob("*.conf"),
]
changed = False
for path in candidates:
    if not path.is_file():
        continue
    text = path.read_text(encoding="utf-8")
    if snip in text:
        continue
    if "server_name" not in text or "aerialnet.co.za" not in text:
        continue
    lines = text.splitlines(True)
    out = []
    injected = False
    in_ssl_server = False
    for i, line in enumerate(lines):
        out.append(line)
        if line.lstrip().startswith("server {") or line.strip() == "server {":
            in_ssl_server = False
        if "listen" in line and "443" in line:
            in_ssl_server = True
        if in_ssl_server and "server_name" in line and "aerialnet.co.za" in line and not injected:
            # insert after this server_name line
            out.append(include)
            injected = True
            changed = True
    if injected:
        path.write_text("".join(out), encoding="utf-8")
        print(f"injected include into {path}")
if not changed:
    print("nginx include already present or no aerialnet server found — check $NGINX_SNIP")
PY

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
