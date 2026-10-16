#!/bin/bash
# Mail-in-a-Box rewrites /etc/nginx/conf.d/local.conf and drops custom includes.
# Re-inject the Aerialnet keypad API snippet when it is missing. Idempotent.
set -euo pipefail
SNIP="${SNIP:-/etc/nginx/snippets/aerialnet-arial.conf}"
CONF="${CONF:-/etc/nginx/conf.d/local.conf}"
if [ ! -f "$SNIP" ] || [ ! -f "$CONF" ]; then
  exit 0
fi
if grep -qF "$SNIP" "$CONF"; then
  exit 0
fi
python3 - "$SNIP" "$CONF" <<'PY'
import pathlib, sys
snip, confp = sys.argv[1], sys.argv[2]
include = f"    include {snip};\n"
path = pathlib.Path(confp)
text = path.read_text(encoding="utf-8")
if snip in text:
    raise SystemExit(0)
lines = text.splitlines(True)
out = []
injected = False
in_ssl_server = False
in_server = False
for line in lines:
    out.append(line)
    if line.lstrip().startswith("server {") or line.strip() == "server {":
        in_server = True
        in_ssl_server = False
    if in_server and "listen" in line and "443" in line:
        in_ssl_server = True
    if in_ssl_server and "server_name" in line and "aerialnet.co.za" in line and not injected:
        out.append(include)
        injected = True
    if in_server and line.strip() == "}":
        in_server = False
        in_ssl_server = False
if not injected:
    raise SystemExit("aerialnet TLS server_name not found")
path.write_text("".join(out), encoding="utf-8")
print("re-injected", snip)
PY
nginx -t
systemctl reload nginx
echo "nginx reloaded after Aerialnet API include restore"
