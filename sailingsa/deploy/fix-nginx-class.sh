#!/bin/bash
# Ensure /class/* is served by nginx as SPA (try_files → index.html), not proxied to FastAPI.
# Run ON server as root after backing up nginx config.
set -e

NGCFG=$(grep -l "sailingsa.co.za" /etc/nginx/sites-enabled/* 2>/dev/null | head -1)
[ -z "$NGCFG" ] && NGCFG=$(ls /etc/nginx/sites-enabled/* 2>/dev/null | head -1)
[ ! -f "$NGCFG" ] && { echo "ERROR: No nginx config"; exit 1; }

echo "Config: $NGCFG"
cp "$NGCFG" "/tmp/nginx-sailingsa.bak.$(date +%Y%m%d_%H%M%S)"

python3 - "$NGCFG" << 'PYEOF'
import sys
path = sys.argv[1]
with open(path) as f:
    content = f.read()

# Remove old proxy-to-API class block if present
import re
content = re.sub(
    r"\n\s*location ~ \^/class/ \{[^}]*proxy_pass[^}]*\}\s*",
    "\n",
    content,
    flags=re.DOTALL,
)

class_block = """
    location ~ ^/class/ {
        try_files $uri $uri/ /index.html;
    }
"""

idx = content.find("server_name sailingsa.co.za")
if idx == -1:
    idx = content.find("server_name")
if idx == -1:
    print("ERROR: Could not find sailingsa server block"); sys.exit(1)

loc = content.find("location / {", idx)
if loc == -1:
    loc = content.find("location /{", idx)
if loc == -1:
    loc = content.find("location / ", idx)
if loc == -1:
    loc = content.find("try_files", idx)
if loc == -1:
    print("ERROR: Could not find location / or try_files"); sys.exit(1)

snippet = "location ~ ^/class/"
if snippet in content[idx:idx + 8000]:
    # Already have a /class/ block — replace try_files block only
    if "try_files $uri $uri/ /index.html" in content and snippet in content:
        print("location ~ ^/class/ with SPA try_files already present")
    else:
        print("WARN: /class/ block exists but not SPA try_files; edit manually")
else:
    content = content[:loc] + class_block + "\n" + content[loc:]
    print("Added location ~ ^/class/ { try_files ... /index.html; }")

with open(path, 'w') as f:
    f.write(content)
PYEOF

echo ""
echo "Testing nginx..."
nginx -t
echo ""
echo "Reloading nginx..."
systemctl reload nginx
echo "NGINX_RELOADED"
