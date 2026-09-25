#!/usr/bin/env python3
from pathlib import Path
import ipaddress

phone = ipaddress.ip_address("165.165.113.77")
also = [ipaddress.ip_address(x) for x in ("100.72.251.223", "41.247.20.198")]
text = Path("/etc/nginx/snippets/sailingsa-swarm-deny.conf").read_text()
print("PHONE MATCHES")
for line in text.splitlines():
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
    for ip in also:
        if ip in net:
            print("ALSO", ip, line)

print("\n165. DENY LINES")
for line in text.splitlines():
    if line.strip().startswith("deny 165."):
        print(line)

print("\nHEAD")
print("\n".join(text.splitlines()[:15]))
print("... TAIL ...")
print("\n".join(text.splitlines()[-8:]))
