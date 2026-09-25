#!/usr/bin/env python3
from pathlib import Path
import ipaddress

phone = ipaddress.ip_address("165.165.113.77")
deny = Path("/etc/nginx/snippets/sailingsa-swarm-deny.conf").read_text()
api = Path("/var/www/sailingsa/api/api.py").read_text()
print("MARK_NGINX", "PHONE_403_TELKOM_NGINX_v1" in deny)
print("HAS_PHONE_DENY", "deny 165.165.113.77" in deny)
print("ALLOW_HEAD")
print("\n".join(deny.splitlines()[:8]))
print("PHONE_STILL_DENIED")
for line in deny.splitlines():
    s = line.strip()
    if not s.startswith("deny "):
        continue
    cidr = s.split()[1].rstrip(";")
    try:
        net = ipaddress.ip_network(cidr, strict=False)
    except Exception:
        continue
    if phone in net:
        print("HIT", line)
print("API_MARK", "PHONE_403_TELKOM_NGINX_v1" in api)
print("API_HAS_165", "165.165.0.0/16" in api, "165.165.113.77" in api)
