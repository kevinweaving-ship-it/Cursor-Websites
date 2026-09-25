#!/usr/bin/env python3
"""Add Telkom SAIX 165.165.0.0/16 + current phone host to API owner allow."""
from __future__ import annotations

import ipaddress
import subprocess
from pathlib import Path

import psycopg2

API = Path("/var/www/sailingsa/api/api.py")
DSN = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
MARK = "PHONE_403_TELKOM_NGINX_v1"
NETS = (
    ipaddress.ip_network("41.246.0.0/15"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("165.165.0.0/16"),
)

OLD = '''_LEAN_OWNER_ALLOW_IPS = frozenset({"100.72.251.223", "41.247.20.198"})
_LEAN_OWNER_ALLOW_NETS = tuple(
    __import__("ipaddress").ip_network(n)
    for n in (
        "41.246.0.0/15",  # Telkom SA OpenServe IPNET-BROADBAND (covers 41.247.x)
        "100.64.0.0/10",  # RFC 6598 CGNAT — OpenServe / Telkom phones & fibre
    )
)  # OWNER_IP_RANGE_ALLOW_v1
'''
NEW = '''_LEAN_OWNER_ALLOW_IPS = frozenset({
    "100.72.251.223",
    "41.247.20.198",
    "165.165.113.77",
})
_LEAN_OWNER_ALLOW_NETS = tuple(
    __import__("ipaddress").ip_network(n)
    for n in (
        "41.246.0.0/15",  # Telkom SA OpenServe IPNET-BROADBAND (covers 41.247.x)
        "100.64.0.0/10",  # RFC 6598 CGNAT — OpenServe / Telkom phones & fibre
        "165.165.0.0/16",  # Telkom SAIX / OpenServe CGNAT (current phone)
    )
)  # ''' + MARK + '''
'''


def patch_api() -> None:
    text = API.read_text()
    if MARK in text and "165.165.0.0/16" in text and "165.165.113.77" in text:
        print("API_ALREADY")
        return
    n = text.count(OLD)
    if n != 1:
        idx = text.find("_LEAN_OWNER_ALLOW_IPS")
        print(text[idx : idx + 700] if idx >= 0 else "NO_ALLOW_BLOCK")
        raise SystemExit(f"ANCHOR_ALLOW_{n}")
    API.write_text(text.replace(OLD, NEW, 1))
    print("API_OK")


def clear_range_quarantine() -> None:
    conn = psycopg2.connect(DSN)
    cur = conn.cursor()
    cur.execute("SELECT ip_address, reason, active FROM traffic_quarantine_ips")
    rows = cur.fetchall()
    drop = []
    for ip, reason, active in rows:
        try:
            addr = ipaddress.ip_address(str(ip).split("%")[0])
        except Exception:
            continue
        if any(addr in net for net in NETS):
            drop.append((str(ip), reason, active))
    print("RANGE_HITS", drop)
    if drop:
        cur.execute(
            "DELETE FROM traffic_quarantine_ips WHERE ip_address = ANY(%s)",
            ([d[0] for d in drop],),
        )
        print("DELETED", cur.rowcount)
        conn.commit()
    cur.close()
    conn.close()


def main() -> None:
    clear_range_quarantine()
    patch_api()
    subprocess.check_call(["python3", "-m", "py_compile", str(API)])
    print("COMPILE_OK")


if __name__ == "__main__":
    main()
