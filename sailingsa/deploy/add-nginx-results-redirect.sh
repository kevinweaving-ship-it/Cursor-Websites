#!/bin/bash
# Add nginx 301: /results/{slug} -> /regatta/{slug}; leave /results/full.html and /results/lite.html unchanged.
# Run ON server (or via apply-results-redirect.exp).

set -e

NGCFG=$(grep -l "sailingsa.co.za" /etc/nginx/sites-enabled/* 2>/dev/null | head -1)
[ -z "$NGCFG" ] && NGCFG=$(ls /etc/nginx/sites-enabled/* 2>/dev/null | head -1)
[ ! -f "$NGCFG" ] && { echo "ERROR: No nginx config"; exit 1; }

echo "Config: $NGCFG"
cp "$NGCFG" "/tmp/nginx-sailingsa.bak.results-redirect.$(date +%Y%m%d%H%M%S)"

python3 - "$NGCFG" << 'PYEOF'
import sys
path = sys.argv[1]
with open(path) as f:
    content = f.read()

block = """
    location = /results/full.html {
        try_files $uri =404;
    }
    location = /results/lite.html {
        try_files $uri =404;
    }
    location ~ ^/results/([^/]+)$ {
        return 301 https://sailingsa.co.za/regatta/$1;
    }
"""

idx = content.find("server_name sailingsa.co.za")
if idx == -1:
    idx = content.find("server_name")
if idx == -1:
    print("ERROR: Could not find sailingsa server block")
    sys.exit(1)

loc = content.find("location / {", idx)
if loc == -1:
    loc = content.find("location /{", idx)
if loc == -1:
    print("ERROR: Could not find location / block")
    sys.exit(1)

if "location ~ ^/results/" in content[idx:loc+200]:
    print("results redirect already present")
else:
    content = content[:loc] + block + "\n" + content[loc:]
    print("Added /results/{slug} -> /regatta/{slug} redirect")

with open(path, "w") as f:
    f.write(content)
PYEOF

echo ""
echo "Testing nginx..."
nginx -t
echo ""
echo "Reloading nginx..."
systemctl reload nginx
echo "NGINX_RELOADED"
