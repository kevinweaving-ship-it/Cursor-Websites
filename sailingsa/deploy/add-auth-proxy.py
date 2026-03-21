#!/usr/bin/env python3
"""Add /auth/ proxy block to nginx config - run ON server"""
import re, sys

NGCFG = "/etc/nginx/sites-enabled/timadvisor"

with open(NGCFG) as f:
    content = f.read()

# Remove existing /auth/ block if present
content = re.sub(r'\n\s*location /auth/ \{[^}]*\}\n', '\n', content, flags=re.DOTALL)

# Add /auth/ block after /api/ block (same structure)
auth_block = """
    location /auth/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
"""

# Insert after location /api/ { ... }
content = re.sub(
    r'(location /api/ \{[^}]*\})',
    r'\1' + auth_block,
    content,
    count=1,
    flags=re.DOTALL
)

with open(NGCFG, 'w') as f:
    f.write(content)
print("Updated nginx config")
