#!/bin/bash
# Proxy singular /sailor, /regatta, /club, /class (+ trailing slash) to API so FastAPI 301s apply.
# Without this, nginx may redirect /regatta → /regatta/ and return 403 before the app.
# Run ON server: bash fix-nginx-singular-seo-routes.sh
set -e

NGCFG=$(grep -l "sailingsa.co.za" /etc/nginx/sites-enabled/* 2>/dev/null | head -1)
[ -z "$NGCFG" ] && NGCFG=$(ls /etc/nginx/sites-enabled/* 2>/dev/null | head -1)
[ ! -f "$NGCFG" ] && { echo "ERROR: No nginx config"; exit 1; }

echo "Config: $NGCFG"
cp "$NGCFG" "/tmp/nginx-singular-seo.bak.$(date +%Y%m%d_%H%M%S)"

python3 - "$NGCFG" << 'PYEOF'
import sys
path = sys.argv[1]
with open(path) as f:
    content = f.read()

if "location = /regatta {" in content and "proxy_pass http://127.0.0.1:8000/regatta" in content:
    print("Singular SEO routes already present (skip)")
    sys.exit(0)

block = """
    location = /sailor {
        proxy_pass http://127.0.0.1:8000/sailor;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    location = /sailor/ {
        proxy_pass http://127.0.0.1:8000/sailor/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    location = /regatta {
        proxy_pass http://127.0.0.1:8000/regatta;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    location = /regatta/ {
        proxy_pass http://127.0.0.1:8000/regatta/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    location = /club {
        proxy_pass http://127.0.0.1:8000/club;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    location = /club/ {
        proxy_pass http://127.0.0.1:8000/club/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    location = /class {
        proxy_pass http://127.0.0.1:8000/class;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    location = /class/ {
        proxy_pass http://127.0.0.1:8000/class/;
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
    print("ERROR: Could not find server block"); sys.exit(1)

loc = content.find("location / {", idx)
if loc == -1:
    loc = content.find("location /{", idx)
if loc == -1:
    print("ERROR: Could not find location / block"); sys.exit(1)

content = content[:loc] + block + "\n" + content[loc:]
print("Added singular SEO proxy locations")

with open(path, 'w') as f:
    f.write(content)
PYEOF

echo ""
nginx -t
systemctl reload nginx
echo "NGINX_RELOADED"
