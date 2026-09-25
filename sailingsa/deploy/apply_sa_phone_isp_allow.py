#!/usr/bin/env python3
"""Allow SA WiFi/mobile ranges so phones hopping networks are never 403'd."""
from __future__ import annotations

import ipaddress
import subprocess
from pathlib import Path

import psycopg2

MARK = "PHONE_SA_ISP_ALLOW_v1"
DENY = Path("/etc/nginx/snippets/sailingsa-swarm-deny.conf")
ALLOW = Path("/etc/nginx/snippets/sailingsa-sa-isp-allow.conf")
SITE = Path("/etc/nginx/sites-enabled/sailingsa")
API = Path("/var/www/sailingsa/api/api.py")
DSN = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
SRC = Path("/tmp/sailingsa-sa-isp-allow.conf")

NETS = tuple(
    ipaddress.ip_network(n)
    for n in (
        "100.64.0.0/10",
        "41.144.0.0/13",
        "41.246.0.0/15",
        "102.248.0.0/13",
        "105.224.0.0/12",
        "165.8.0.0/14",
        "165.144.0.0/15",
        "165.165.0.0/16",
        "168.210.0.0/16",
        "196.21.0.0/16",
        "196.25.0.0/16",
        "197.80.0.0/12",
        "41.0.0.0/12",
        "41.20.0.0/14",
        "105.232.0.0/13",
        "105.240.0.0/13",
        "152.106.0.0/15",
        "196.4.0.0/16",
        "196.207.0.0/16",
        "41.112.0.0/12",
        "105.208.0.0/13",
        "197.64.0.0/13",
        "41.48.0.0/13",
        "41.156.0.0/15",
        "105.0.0.0/12",
        "41.56.0.0/16",
        "41.208.192.0/18",
        "41.213.0.0/17",
        "197.184.0.0/15",
        "41.132.0.0/16",
        "41.134.0.0/16",
        "102.64.0.0/14",
        "102.182.0.0/16",
        "102.216.0.0/16",
        "169.0.0.0/15",
        "169.224.0.0/16",
        "196.40.0.0/15",
        "196.43.0.0/16",
    )
)

OLD = '''_LEAN_OWNER_ALLOW_IPS = frozenset({
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
)  # PHONE_403_TELKOM_NGINX_v1
'''

NEW = '''_LEAN_OWNER_ALLOW_IPS = frozenset({
    "100.72.251.223",
    "41.247.20.198",
    "165.165.113.77",
})
_LEAN_OWNER_ALLOW_NETS = tuple(
    __import__("ipaddress").ip_network(n)
    for n in (
        "100.64.0.0/10",
        "41.0.0.0/12",
        "41.20.0.0/14",
        "41.48.0.0/13",
        "41.56.0.0/16",
        "41.112.0.0/12",
        "41.132.0.0/16",
        "41.134.0.0/16",
        "41.144.0.0/13",
        "41.156.0.0/15",
        "41.208.192.0/18",
        "41.213.0.0/17",
        "41.246.0.0/15",
        "102.64.0.0/14",
        "102.182.0.0/16",
        "102.216.0.0/16",
        "102.248.0.0/13",
        "105.0.0.0/12",
        "105.208.0.0/13",
        "105.224.0.0/12",
        "105.232.0.0/13",
        "105.240.0.0/13",
        "152.106.0.0/15",
        "165.8.0.0/14",
        "165.144.0.0/15",
        "165.165.0.0/16",
        "168.210.0.0/16",
        "169.0.0.0/15",
        "169.224.0.0/16",
        "196.4.0.0/16",
        "196.21.0.0/16",
        "196.25.0.0/16",
        "196.40.0.0/15",
        "196.43.0.0/16",
        "196.207.0.0/16",
        "197.64.0.0/13",
        "197.80.0.0/12",
        "197.184.0.0/15",
    )
)  # ''' + MARK + '''
'''

SWARM_INC = "    include /etc/nginx/snippets/sailingsa-swarm-deny.conf;"
BOTH_INC = (
    "    include /etc/nginx/snippets/sailingsa-sa-isp-allow.conf;\n"
    "    include /etc/nginx/snippets/sailingsa-swarm-deny.conf;"
)


def _in_sa(cidr: str) -> bool:
    try:
        net = ipaddress.ip_network(cidr, strict=False)
    except Exception:
        return False
    if net.num_addresses == 1:
        ip = ipaddress.ip_address(cidr.split("/")[0])
        return any(ip in n for n in NETS)
    return any(net.subnet_of(n) or net == n for n in NETS)


def write_allow_snippet() -> None:
    text = SRC.read_text() if SRC.exists() else ALLOW.read_text()
    if MARK not in text:
        raise SystemExit("ALLOW_SNIPPET_MISSING_MARK")
    ALLOW.write_text(text)
    print("SNIPPET", ALLOW, ALLOW.stat().st_size)


def include_before_deny() -> None:
    site = SITE.read_text()
    if "sailingsa-sa-isp-allow.conf" in site:
        print("SITE_ALREADY")
        return
    n = site.count(SWARM_INC)
    if n != 2:
        raise SystemExit(f"SITE_INC_{n}")
    SITE.write_text(site.replace(SWARM_INC, BOTH_INC))
    print("SITE_OK", SITE.read_text().count("sailingsa-sa-isp-allow.conf"))


def strip_consumer_denies() -> None:
    text = DENY.read_text()
    kept, dropped = [], []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("deny "):
            cidr = s.split()[1].rstrip(";")
            if _in_sa(cidr):
                dropped.append(line)
                continue
        kept.append(line)
    print("DROPPED", dropped)
    body = "\n".join(kept)
    if not body.endswith("\n"):
        body += "\n"
    DENY.write_text(body)
    print("DENY_LEFT_169", any("deny 169." in l for l in DENY.read_text().splitlines()))


def patch_api() -> None:
    text = API.read_text()
    if MARK in text:
        print("API_ALREADY")
        return
    n = text.count(OLD)
    if n != 1:
        i = text.find("_LEAN_OWNER_ALLOW_IPS")
        print(text[i : i + 400] if i >= 0 else "NO_BLOCK")
        raise SystemExit(f"ANCHOR_{n}")
    API.write_text(text.replace(OLD, NEW, 1))
    print("API_OK")


def clear_quarantine() -> None:
    conn = psycopg2.connect(DSN)
    cur = conn.cursor()
    cur.execute("SELECT ip_address FROM traffic_quarantine_ips")
    drop = []
    for (ip,) in cur.fetchall():
        try:
            addr = ipaddress.ip_address(str(ip).split("%")[0])
        except Exception:
            continue
        if any(addr in n for n in NETS):
            drop.append(str(ip))
    print("Q_DROP", len(drop))
    if drop:
        cur.execute(
            "DELETE FROM traffic_quarantine_ips WHERE ip_address = ANY(%s)",
            (drop,),
        )
        print("Q_DELETED", cur.rowcount)
        conn.commit()
    cur.close()
    conn.close()


def main() -> None:
    write_allow_snippet()
    include_before_deny()
    strip_consumer_denies()
    subprocess.check_call(["nginx", "-t"])
    print("NGINX_T_OK")
    clear_quarantine()
    patch_api()
    subprocess.check_call(["python3", "-m", "py_compile", str(API)])
    print("COMPILE_OK")


if __name__ == "__main__":
    main()
