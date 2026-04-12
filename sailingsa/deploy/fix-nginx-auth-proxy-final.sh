#!/usr/bin/env bash
# FIX NGINX AUTH PROXY (FINAL VERSION) — run ON server (SSH)
# Target: /etc/nginx/sites-enabled/timadvisor (sailingsa.co.za server block)
set -e

NGCFG=$(grep -l "sailingsa.co.za" /etc/nginx/sites-enabled/* 2>/dev/null | head -1)
[ -z "$NGCFG" ] && NGCFG=/etc/nginx/sites-enabled/timadvisor
[ ! -f "$NGCFG" ] && NGCFG=$(ls /etc/nginx/sites-enabled/* 2>/dev/null | head -1)
echo "Config: $NGCFG"
cp "$NGCFG" "/tmp/timadvisor.bak.$(date +%Y%m%d%H%M)"

python3 - "$NGCFG" << 'PYEOF'
import re, sys
path = sys.argv[1]
with open(path) as f:
    content = f.read()

# 1. REMOVE any existing /auth/ block (location /auth/, location /auth, location ^~ /auth/)
content = re.sub(r'\n\s*location\s+(?:\^~)?\s*/auth/?\s*\{[^}]*\}\n', '\n', content, flags=re.DOTALL)

# 2. Build the new blocks to insert BEFORE location /
auth_block = """
    location ^~ /auth/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

"""
api_block = """
    location ^~ /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

"""

# 3. Ensure /api/ uses ^~ format: remove old /api/ block and re-add
content = re.sub(r'\n\s*location\s+(?:\^~)?\s*/api/\s*\{[^}]*\}\n', '\n', content, flags=re.DOTALL)

# 4. Insert auth + api BEFORE first "location /" so they take precedence
if 'location ^~ /auth/' in content:
    print("Auth/api blocks already present")
else:
    # Insert before first "location / {"
    pattern = r'(\n\s*)(location\s+/\s*\{)'
    new_content = re.sub(pattern, r'\1' + auth_block.strip() + '\n\n    ' + api_block.strip() + '\n\n    \2', content, count=1)
    if new_content != content:
        content = new_content
    else:
        # Fallback: find "location /" after sailingsa.co.za and insert before it
        idx = content.find("sailingsa.co.za")
        if idx != -1:
            loc = content.find("location /", idx)
            if loc != -1:
                content = content[:loc] + auth_block.strip() + "\n\n    " + api_block.strip() + "\n\n    " + content[loc:]
    print("Updated nginx config")

with open(path, 'w') as f:
    f.write(content)
PYEOF

nginx -t && systemctl reload nginx
echo "nginx reloaded"
echo ""
echo "=== Verify (MUST NOT RETURN 405) ==="
curl -s -o /dev/null -w "POST https://sailingsa.co.za/auth/login: %{http_code}\n" -X POST https://sailingsa.co.za/auth/login \
  -H "Content-Type: application/json" \
  -d '{"provider":"username","username":"21172","password":"test"}'
