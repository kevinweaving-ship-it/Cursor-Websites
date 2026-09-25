#!/usr/bin/env python3
"""Whitelist owner IPs 100.72.251.223 and 41.247.20.198 — never quarantine."""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

import psycopg2

API = Path("/var/www/sailingsa/api/api.py")
DSN = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
IPS = ("100.72.251.223", "41.247.20.198")
MARK = "OWNER_IP_WHITELIST_v1"

INSERT = '''_LEAN_TRAFFIC_QUARANTINE_IP_SQL = (
    "(SELECT ip_address FROM public.traffic_quarantine_ips "
    "WHERE COALESCE(active, true) = true "
    "AND ip_address IS NOT NULL AND TRIM(ip_address::text) <> '')"
)

_LEAN_CLOUD_NETS_CACHE = None
'''
INSERT_NEW = '''_LEAN_TRAFFIC_QUARANTINE_IP_SQL = (
    "(SELECT ip_address FROM public.traffic_quarantine_ips "
    "WHERE COALESCE(active, true) = true "
    "AND ip_address IS NOT NULL AND TRIM(ip_address::text) <> '')"
)

_LEAN_OWNER_ALLOW_IPS = frozenset({"100.72.251.223", "41.247.20.198"})  # ''' + MARK + '''


def _lean_ip_is_owner_allowlisted(ip_address) -> bool:
    return (ip_address or "").strip() in _LEAN_OWNER_ALLOW_IPS


_LEAN_CLOUD_NETS_CACHE = None
'''

Q_OLD = '''def _lean_quarantine_ip(cur, ip_address: Optional[str], reason: str = "bot") -> None:
    ip = (ip_address or "").strip()
    if not ip or _is_noise_public_ip(ip):
        return
'''
Q_NEW = '''def _lean_quarantine_ip(cur, ip_address: Optional[str], reason: str = "bot") -> None:
    ip = (ip_address or "").strip()
    if not ip or _is_noise_public_ip(ip) or _lean_ip_is_owner_allowlisted(ip):
        return  # ''' + MARK + '''
'''

IS_OLD = '''def _lean_ip_is_quarantined(cur, ip_address: Optional[str]) -> bool:
    ip = (ip_address or "").strip()
    if not ip:
        return False
'''
IS_NEW = '''def _lean_ip_is_quarantined(cur, ip_address: Optional[str]) -> bool:
    ip = (ip_address or "").strip()
    if not ip or _lean_ip_is_owner_allowlisted(ip):
        return False  # ''' + MARK + '''
'''


def stamp_db() -> None:
    conn = psycopg2.connect(DSN)
    cur = conn.cursor()
    for ip in IPS:
        cur.execute(
            """
            INSERT INTO public.traffic_quarantine_ips
                (ip_address, reason, active, hit_count, first_seen_at, last_seen_at)
            VALUES (%s, %s, false, 0, NOW(), NOW())
            ON CONFLICT (ip_address) DO UPDATE SET
                active = false,
                reason = %s,
                last_seen_at = NOW()
            """,
            (ip, MARK, MARK),
        )
    conn.commit()
    cur.execute(
        "SELECT ip_address, reason, active FROM traffic_quarantine_ips WHERE ip_address::text = ANY(%s)",
        (list(IPS),),
    )
    print("DB", cur.fetchall())
    cur.close()
    conn.close()


def patch_api() -> None:
    text = API.read_text()
    if MARK in text and "_LEAN_OWNER_ALLOW_IPS" in text:
        print("API_ALREADY")
        return
    for label, old, new in (
        ("INSERT", INSERT, INSERT_NEW),
        ("Q", Q_OLD, Q_NEW),
        ("IS", IS_OLD, IS_NEW),
    ):
        n = text.count(old)
        if n != 1:
            raise SystemExit(f"ANCHOR_{label}_{n}")
        text = text.replace(old, new, 1)
        print("PATCH", label)
    API.write_text(text)
    print("API_OK")


def main() -> None:
    stamp_db()
    patch_api()
    subprocess.check_call(["python3", "-m", "py_compile", str(API)])
    print("COMPILE_OK")


if __name__ == "__main__":
    main()
