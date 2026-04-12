#!/bin/bash
# Insert exact-match location for class-results.html with Cache-Control no-store.
# Run from project root (uses SSH key). Inserts before main `location / {` in sailingsa vhost.
set -euo pipefail
KEY="${SSH_KEY:-$HOME/.ssh/sailingsa_live_key}"
SERVER="${NGINX_SSH_HOST:-root@102.218.215.253}"

ssh -i "$KEY" -o StrictHostKeyChecking=no "$SERVER" bash -s << 'REMOTE'
set -e
NGCFG=$(grep -l "sailingsa.co.za" /etc/nginx/sites-enabled/* 2>/dev/null | head -1)
[ -z "$NGCFG" ] && NGCFG=$(ls /etc/nginx/sites-enabled/* 2>/dev/null | head -1)
[ ! -f "$NGCFG" ] && { echo "ERROR: No nginx config"; exit 1; }
echo "Config: $NGCFG"
cp "$NGCFG" "/tmp/nginx-sailingsa.bak.class-results.$(date +%Y%m%d_%H%M%S)"

python3 - "$NGCFG" << 'PYEOF'
import sys
path = sys.argv[1]
mark = "location = /regatta/class/class-results.html"
with open(path) as f:
    content = f.read()
if mark in content:
    print("location = /regatta/class/class-results.html already present — skip insert")
    sys.exit(0)

block = """
    location = /regatta/class/class-results.html {
        add_header Cache-Control "no-store, no-cache, must-revalidate, max-age=0";
        try_files $uri =404;
    }
"""

idx = content.find("server_name sailingsa.co.za")
if idx == -1:
    idx = content.find("server_name")
if idx == -1:
    print("ERROR: Could not find server_name"); sys.exit(1)

loc = content.find("location / {", idx)
if loc == -1:
    loc = content.find("location /{", idx)
if loc == -1:
    print("ERROR: Could not find location /"); sys.exit(1)

content = content[:loc] + block + "\n" + content[loc:]
with open(path, "w") as f:
    f.write(content)
print("Inserted class-results no-cache location")
PYEOF

nginx -t
systemctl reload nginx
echo "nginx reloaded (config test OK)"
REMOTE
