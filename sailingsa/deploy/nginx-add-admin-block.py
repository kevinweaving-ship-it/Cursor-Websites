#!/usr/bin/env python3
"""Insert /admin/ location block after /regatta/ block in nginx config. Run on server as root."""
import sys
path = "/etc/nginx/sites-enabled/timadvisor"
with open(path) as f:
    s = f.read()
if "location ~ ^/admin/" in s:
    print("Admin block already present")
    sys.exit(0)
old = """    location ~ ^/regatta/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

"""
block = """    location ~ ^/admin/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

"""
if old not in s:
    print("Regatta block not found")
    sys.exit(1)
s = s.replace(old, old.rstrip() + block, 1)
with open(path, "w") as f:
    f.write(s)
print("Inserted /admin/ block")
