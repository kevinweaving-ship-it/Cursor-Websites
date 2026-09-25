#!/usr/bin/env python3
from pathlib import Path
import ipaddress

phone = ipaddress.ip_address("165.165.113.77")
telkom = [
    ipaddress.ip_network("41.246.0.0/15"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("165.165.0.0/16"),
]
text = Path("/etc/nginx/snippets/sailingsa-swarm-deny.conf").read_text()
print("TELKOM DENY LINES")
for line in text.splitlines():
    s = line.strip()
    if not s.startswith("deny "):
        continue
    cidr = s.split()[1].rstrip(";")
    try:
        net = ipaddress.ip_network(cidr, strict=False)
    except Exception:
        continue
    if any(net.overlaps(t) or (net.num_addresses == 1 and next(iter(net.hosts()), net.network_address) in t) for t in telkom):
        print(line)
    elif net.num_addresses == 1:
        ip = ipaddress.ip_address(cidr.split("/")[0])
        if any(ip in t for t in telkom):
            print(line)

print("\nSITE INCLUDES")
site = Path("/etc/nginx/sites-enabled/sailingsa").read_text()
for i, line in enumerate(site.splitlines(), 1):
    if "deny" in line.lower() or "allow" in line.lower() or "swarm" in line.lower() or "include" in line:
        print(f"{i}:{line}")

print("\nOTHER DENY FILES")
for p in Path("/etc/nginx").rglob("*"):
    if not p.is_file():
        continue
    try:
        t = p.read_text(errors="ignore")
    except Exception:
        continue
    if "165.165.113.77" in t or "deny 165.165" in t:
        print("FILE", p)

print("\nRECENT 403 PHONE")
log = Path("/var/log/nginx/access.log")
if log.exists():
    rows = []
    for line in log.read_text(errors="ignore").splitlines()[-4000:]:
        if " 403 " in line and ("165.165.113.77" in line or "iPhone" in line):
            rows.append(line)
    for line in rows[-20:]:
        print(line)
