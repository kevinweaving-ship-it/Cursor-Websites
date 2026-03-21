#!/usr/bin/env bash
# Add /club/ and /sitemap.xml proxy to nginx — run ON server (SSH)
set -e

NGCFG=$(grep -l "sailingsa.co.za" /etc/nginx/sites-enabled/* 2>/dev/null | head -1)
[ -z "$NGCFG" ] && NGCFG=$(ls /etc/nginx/sites-enabled/* 2>/dev/null | head -1)
[ ! -f "$NGCFG" ] && { echo "ERROR: No nginx config"; exit 1; }

echo "Config: $NGCFG"
cp "$NGCFG" "/tmp/nginx-sailingsa.bak.$(date +%Y%m%d_%H%M%S)"

python3 - "$NGCFG" << 'PYEOF'
import re, sys
path = sys.argv[1]
with open(path) as f:
    content = f.read()

club_block = """
    location ~ ^/club/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
"""

sitemap_block = """
    location = /sitemap.xml {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
"""

need_club = "sailingsa.co.za" in content and "location ~ ^/club/" not in content
need_sitemap = "sailingsa.co.za" in content and "location = /sitemap.xml" not in content

if need_club or need_sitemap:
    idx = content.find("server_name sailingsa.co.za")
    if idx != -1:
        loc = content.find("location / {", idx)
        if loc != -1:
            insert = ""
            if need_club:
                insert += club_block + "\n"
                print("Added /club/ route")
            if need_sitemap:
                insert += sitemap_block + "\n"
                print("Added /sitemap.xml route")
            content = content[:loc] + insert + content[loc:]
else:
    print("Routes already present")

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
