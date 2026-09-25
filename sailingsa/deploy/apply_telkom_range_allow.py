#!/usr/bin/env python3
"""Allow full OpenServe/Telkom ranges — not just two host IPs."""
from __future__ import annotations

import ipaddress
import subprocess
from pathlib import Path

import psycopg2

API = Path("/var/www/sailingsa/api/api.py")
DSN = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
MARK = "OWNER_IP_RANGE_ALLOW_v1"
NETS = (
    ipaddress.ip_network("41.246.0.0/15"),  # Telkom SA OpenServe IPNET-BROADBAND
    ipaddress.ip_network("100.64.0.0/10"),  # RFC 6598 CGNAT used by OpenServe/Telkom
)

OLD = '''_LEAN_OWNER_ALLOW_IPS = frozenset({"100.72.251.223", "41.247.20.198"})  # OWNER_IP_WHITELIST_v1


def _lean_ip_is_owner_allowlisted(ip_address) -> bool:
    return (ip_address or "").strip() in _LEAN_OWNER_ALLOW_IPS
'''
NEW = '''_LEAN_OWNER_ALLOW_IPS = frozenset({"100.72.251.223", "41.247.20.198"})
_LEAN_OWNER_ALLOW_NETS = tuple(
    __import__("ipaddress").ip_network(n)
    for n in (
        "41.246.0.0/15",  # Telkom SA OpenServe IPNET-BROADBAND (covers 41.247.x)
        "100.64.0.0/10",  # RFC 6598 CGNAT — OpenServe / Telkom phones & fibre
    )
)  # ''' + MARK + '''


def _lean_ip_is_owner_allowlisted(ip_address) -> bool:
    ip = (ip_address or "").strip()
    if not ip:
        return False
    if ip in _LEAN_OWNER_ALLOW_IPS:
        return True
    try:
        addr = __import__("ipaddress").ip_address(ip.split("%")[0])
        return any(addr in net for net in _LEAN_OWNER_ALLOW_NETS)
    except Exception:
        return False
'''

BAN_OLD = '''def _ip_is_probe_banned(ip: str) -> bool:
    ip = (ip or "").strip()
    if not ip:
        return False
'''
BAN_NEW = '''def _ip_is_probe_banned(ip: str) -> bool:
    ip = (ip or "").strip()
    if not ip or _lean_ip_is_owner_allowlisted(ip):
        return False  # ''' + MARK + '''
'''

BAN2_OLD = '''def _ban_probe_ip(ip: str) -> None:
    ip = (ip or "").strip()
    if not ip or _is_noise_public_ip(ip):
        return
'''
BAN2_NEW = '''def _ban_probe_ip(ip: str) -> None:
    ip = (ip or "").strip()
    if not ip or _is_noise_public_ip(ip) or _lean_ip_is_owner_allowlisted(ip):
        return  # ''' + MARK + '''
'''

CLOUD_OLD = '''def _lean_ip_is_cloud_datacenter(ip_address: Optional[str]) -> bool:
    ip = (ip_address or "").strip()
    if not ip:
        return False
'''
CLOUD_NEW = '''def _lean_ip_is_cloud_datacenter(ip_address: Optional[str]) -> bool:
    ip = (ip_address or "").strip()
    if not ip or _lean_ip_is_owner_allowlisted(ip):
        return False  # ''' + MARK + '''
'''


def patch_api() -> None:
    text = API.read_text()
    if MARK in text and "_LEAN_OWNER_ALLOW_NETS" in text:
        print("API_ALREADY")
        return
    for label, old, new in (
        ("ALLOW", OLD, NEW),
        ("BAN", BAN_OLD, BAN_NEW),
        ("BAN2", BAN2_OLD, BAN2_NEW),
        ("CLOUD", CLOUD_OLD, CLOUD_NEW),
    ):
        n = text.count(old)
        if n != 1:
            raise SystemExit(f"ANCHOR_{label}_{n}")
        text = text.replace(old, new, 1)
        print("PATCH", label)
    API.write_text(text)
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
    cur.execute(
        "SELECT COUNT(*) FROM traffic_quarantine_ips WHERE ip_address::text IN %s",
        (("100.72.251.223", "41.247.20.198"),),
    )
    print("HOST_LEFT", cur.fetchone())
    cur.close()
    conn.close()


def main() -> None:
    clear_range_quarantine()
    patch_api()
    subprocess.check_call(["python3", "-m", "py_compile", str(API)])
    print("COMPILE_OK")


if __name__ == "__main__":
    main()
