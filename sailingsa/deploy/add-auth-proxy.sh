#!/usr/bin/env bash
# Add /auth/ proxy to nginx - run ON server
set -e

NGCFG=/etc/nginx/sites-enabled/timadvisor
echo "Config: $NGCFG"
cp "$NGCFG" "/tmp/timadvisor.bak.$(date +%Y%m%d%H%M)"
rm -f /etc/nginx/sites-enabled/*.bak* 2>/dev/null || true

python3 - "$NGCFG" << 'PYEOF'
import re, sys
path = sys.argv[1]
with open(path) as f:
    content = f.read()
content = re.sub(r'\n\s*location /auth/ \{[^}]*\}\n', '\n', content, flags=re.DOTALL)
auth_block = """
    location /auth/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
"""
content = re.sub(r'(location /api/ \{[^}]*\})', r'\1' + auth_block, content, count=1, flags=re.DOTALL)
with open(path, 'w') as f:
    f.write(content)
print("Updated nginx config")
PYEOF
nginx -t && systemctl reload nginx
echo "nginx reloaded"
echo ""
echo "=== Verify ==="
curl -s -o /dev/null -w "POST https://sailingsa.co.za/auth/login: %{http_code}\n" -X POST https://sailingsa.co.za/auth/login \
  -H "Content-Type: application/json" \
  -d '{"provider":"username","username":"21172","password":"test"}'
