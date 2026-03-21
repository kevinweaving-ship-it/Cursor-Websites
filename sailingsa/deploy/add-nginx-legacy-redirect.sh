#!/usr/bin/env bash
# Add nginx redirect: /sailingsa/frontend/* -> /* (so mobile/old links get correct login page)
# Run ON server (SSH) or via: ssh root@server 'bash -s' < add-nginx-legacy-redirect.sh
set -e

NGCFG="${NGINX_SITES_ENABLED:-/etc/nginx/sites-enabled/timadvisor}"
echo "Config: $NGCFG"
cp "$NGCFG" "/tmp/timadvisor.bak.$(date +%Y%m%d%H%M)"

# Insert legacy redirect BEFORE "location /" in sailingsa server block (so /sailingsa/frontend/login.html -> /login.html)
python3 - "$NGCFG" << 'PYEOF'
import re, sys
path = sys.argv[1]
with open(path) as f:
    content = f.read()

legacy_block = """
    # Redirect old path to root (mobile/cloud parity: /login.html not /sailingsa/frontend/login.html)
    location ^~ /sailingsa/frontend/ {
        rewrite ^/sailingsa/frontend/(.*)$ $scheme://$host/$1 permanent;
    }

"""

# Remove if already present
content = re.sub(r'\n\s*# Redirect old path to root.*?location \^~ /sailingsa/frontend/ \{[^}]*\}\n', '\n', content, flags=re.DOTALL)

# Insert before "location /" in sailingsa server block
pattern = r'(server\s*\{[^}]*?server_name[^;]*sailingsa\.co\.za[^}]*?)(\s*location\s+/\s*\{)'
def repl(m):
    if 'location ^~ /sailingsa/frontend/' in m.group(1):
        return m.group(0)
    return m.group(1) + legacy_block + m.group(2)

content = re.sub(pattern, repl, content, count=1, flags=re.DOTALL)

with open(path, 'w') as f:
    f.write(content)
print("Added legacy redirect")
PYEOF

nginx -t && systemctl reload nginx
echo "nginx reloaded"
echo "Verify: curl -sI https://sailingsa.co.za/sailingsa/frontend/login.html | head -5"
curl -sI "https://sailingsa.co.za/sailingsa/frontend/login.html" 2>/dev/null | head -5
