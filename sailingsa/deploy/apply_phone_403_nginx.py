#!/usr/bin/env python3
"""Unblock OpenServe/Telkom phones from nginx swarm-deny 403s."""
from __future__ import annotations

import ipaddress
import subprocess
from pathlib import Path

DENY = Path("/etc/nginx/snippets/sailingsa-swarm-deny.conf")
MARK = "PHONE_403_TELKOM_NGINX_v1"
ALLOW_BLOCK = """# """ + MARK + """ — OpenServe / Telkom consumer ranges; never 403 real phones.
allow 41.246.0.0/15;   # Telkom SA OpenServe IPNET-BROADBAND
allow 100.64.0.0/10;   # RFC 6598 CGNAT (OpenServe / Telkom mobile)
allow 165.165.0.0/16;  # Telkom SAIX / OpenServe CGNAT (covers 165.165.113.77)
"""
TELKOM = (
    ipaddress.ip_network("41.246.0.0/15"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("165.165.0.0/16"),
)
DROP_HOSTS = {"165.165.113.77", "165.165.93.73"}


def _deny_target(line: str) -> str | None:
    s = line.strip()
    if not s.startswith("deny "):
        return None
    return s.split()[1].rstrip(";")


def _is_telkom_deny(cidr: str) -> bool:
    try:
        net = ipaddress.ip_network(cidr, strict=False)
    except Exception:
        return False
    if net.num_addresses == 1:
        ip = ipaddress.ip_address(cidr.split("/")[0])
        return any(ip in t for t in TELKOM) or str(ip) in DROP_HOSTS
    return any(net.subnet_of(t) or net == t for t in TELKOM)


def main() -> None:
    text = DENY.read_text()
    if MARK in text and "allow 165.165.0.0/16" in text and "deny 165.165.113.77" not in text:
        print("NGINX_ALREADY")
        return
    kept: list[str] = []
    dropped: list[str] = []
    for line in text.splitlines():
        cidr = _deny_target(line)
        if cidr and _is_telkom_deny(cidr):
            dropped.append(line)
            continue
        kept.append(line)
    print("DROPPED", dropped)
    body = "\n".join(kept).lstrip("\n")
    if MARK not in body:
        body = ALLOW_BLOCK + body
        if not body.endswith("\n"):
            body += "\n"
    DENY.write_text(body)
    print("WROTE", DENY, "bytes", DENY.stat().st_size)
    print("HAS_PHONE_DENY", "deny 165.165.113.77" in DENY.read_text())
    print("HAS_ALLOW_165", "allow 165.165.0.0/16" in DENY.read_text())
    subprocess.check_call(["nginx", "-t"])
    print("NGINX_T_OK")


if __name__ == "__main__":
    main()
