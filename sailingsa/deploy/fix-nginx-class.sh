#!/bin/bash
# Add nginx location ~ ^/class/ proxy to FastAPI — run ON server. Proxies /class/* before try_files/SPA fallback.
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

class_block = """
    location ~ ^/class/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
"""

idx = content.find("server_name sailingsa.co.za")
if idx == -1:
    idx = content.find("server_name")
if idx == -1:
    print("ERROR: Could not find sailingsa server block"); sys.exit(1)

# Insert before first "location /" or "location / {" or "try_files"
loc = content.find("location / {", idx)
if loc == -1:
    loc = content.find("location /{", idx)
if loc == -1:
    loc = content.find("location / ", idx)
if loc == -1:
    loc = content.find("try_files", idx)
if loc == -1:
    print("ERROR: Could not find location / or try_files"); sys.exit(1)

if "location ~ ^/class/" in content[idx:idx+2000]:
    print("location ~ ^/class/ already present")
else:
    content = content[:loc] + class_block + "\n" + content[loc:]
    print("Added location ~ ^/class/")

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
