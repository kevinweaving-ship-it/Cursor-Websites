#!/usr/bin/env python3
"""Swarm vs normal. Range-block only hosting/scanner nets with zero normal IPs."""
from __future__ import annotations

import collections
import gzip
import ipaddress
import re
from pathlib import Path

LOGS = [Path("/var/log/nginx/access.log"), Path("/var/log/nginx/access.log.1")]
for i in range(2, 8):
    p = Path(f"/var/log/nginx/access.log.{i}.gz")
    if p.exists():
        LOGS.append(p)

ASSET = re.compile(r"\.(css|js|png|jpe?g|gif|ico|svg|woff2?|map|webp|mp4|m3u8)(\?|$)", re.I)
API_POLL = re.compile(r"^/api/(arial|voelklip|bing|stanford|traffic|club-cam)/")
SKIP_UA = ("Googlebot", "bingbot", "Google-Inspection", "AdsBot-Google", "SailingSA-")
SKIP_IP = {"102.218.215.253", "127.0.0.1", "::1"}
KEEP_IP = {
    "41.247.20.198",  # HYC live / Midmar user
}

# Never range-block these: ZA/Africa access + Cloudflare edge
NEVER_RANGE = [
    ipaddress.ip_network("41.0.0.0/8"),
    ipaddress.ip_network("102.0.0.0/8"),
    ipaddress.ip_network("105.0.0.0/8"),
    ipaddress.ip_network("196.0.0.0/8"),
    ipaddress.ip_network("197.0.0.0/8"),
    ipaddress.ip_network("156.0.0.0/8"),  # often ZA/Africa
    ipaddress.ip_network("165.0.0.0/8"),
    ipaddress.ip_network("168.80.0.0/16"),  # some ZA
    ipaddress.ip_network("172.64.0.0/13"),  # Cloudflare
    ipaddress.ip_network("173.245.48.0/20"),
    ipaddress.ip_network("103.21.244.0/22"),
    ipaddress.ip_network("103.22.200.0/22"),
    ipaddress.ip_network("103.31.4.0/22"),
    ipaddress.ip_network("104.16.0.0/13"),
    ipaddress.ip_network("104.24.0.0/14"),
    ipaddress.ip_network("108.162.192.0/18"),
    ipaddress.ip_network("131.0.72.0/22"),
    ipaddress.ip_network("141.101.64.0/18"),
    ipaddress.ip_network("162.158.0.0/15"),
    ipaddress.ip_network("188.114.96.0/20"),
    ipaddress.ip_network("190.93.240.0/20"),
    ipaddress.ip_network("197.234.240.0/22"),
    ipaddress.ip_network("198.41.128.0/17"),
    ipaddress.ip_network("2400:cb00::/32"),
    ipaddress.ip_network("2606:4700::/32"),
    ipaddress.ip_network("2803:f800::/32"),
    ipaddress.ip_network("2405:b500::/32"),
    ipaddress.ip_network("2405:8100::/32"),
    ipaddress.ip_network("2a06:98c0::/29"),
    ipaddress.ip_network("2c0f:f248::/32"),
]

# Hosting / scanner space we WILL range-block if swarm-only
HOSTING = [
    ipaddress.ip_network("68.183.0.0/16"),  # DigitalOcean
    ipaddress.ip_network("104.131.0.0/16"),
    ipaddress.ip_network("104.236.0.0/16"),
    ipaddress.ip_network("104.248.0.0/16"),
    ipaddress.ip_network("138.197.0.0/16"),
    ipaddress.ip_network("139.59.0.0/16"),
    ipaddress.ip_network("142.93.0.0/16"),
    ipaddress.ip_network("157.230.0.0/16"),
    ipaddress.ip_network("159.65.0.0/16"),
    ipaddress.ip_network("159.89.0.0/16"),
    ipaddress.ip_network("161.35.0.0/16"),
    ipaddress.ip_network("164.90.0.0/16"),
    ipaddress.ip_network("165.227.0.0/16"),
    ipaddress.ip_network("167.71.0.0/16"),
    ipaddress.ip_network("167.99.0.0/16"),
    ipaddress.ip_network("174.138.0.0/16"),
    ipaddress.ip_network("188.166.0.0/16"),
    ipaddress.ip_network("198.211.96.0/19"),
    ipaddress.ip_network("206.189.0.0/16"),
    ipaddress.ip_network("104.207.32.0/19"),  # DO / Choopa
    ipaddress.ip_network("104.167.0.0/16"),
    ipaddress.ip_network("135.181.0.0/16"),  # Hetzner
    ipaddress.ip_network("95.216.0.0/16"),
    ipaddress.ip_network("168.119.0.0/16"),
    ipaddress.ip_network("49.12.0.0/16"),
    ipaddress.ip_network("116.203.0.0/16"),
    ipaddress.ip_network("128.140.0.0/16"),
    ipaddress.ip_network("159.69.0.0/16"),
    ipaddress.ip_network("78.46.0.0/15"),
    ipaddress.ip_network("3.0.0.0/8"),  # AWS
    ipaddress.ip_network("13.32.0.0/12"),
    ipaddress.ip_network("18.0.0.0/8"),
    ipaddress.ip_network("34.0.0.0/8"),
    ipaddress.ip_network("35.0.0.0/8"),
    ipaddress.ip_network("44.0.0.0/8"),
    ipaddress.ip_network("52.0.0.0/8"),
    ipaddress.ip_network("54.0.0.0/8"),
    ipaddress.ip_network("51.75.0.0/16"),  # OVH
    ipaddress.ip_network("51.83.0.0/16"),
    ipaddress.ip_network("54.37.0.0/16"),
    ipaddress.ip_network("145.239.0.0/16"),
    ipaddress.ip_network("147.135.0.0/16"),
    ipaddress.ip_network("213.209.128.0/17"),  # scanner/proxy
    ipaddress.ip_network("45.128.0.0/11"),  # many bulletproof/scan
    ipaddress.ip_network("45.80.0.0/12"),
    ipaddress.ip_network("45.144.0.0/14"),
    ipaddress.ip_network("91.92.0.0/16"),
    ipaddress.ip_network("94.154.0.0/16"),
    ipaddress.ip_network("195.178.0.0/16"),
    ipaddress.ip_network("193.8.0.0/16"),
    ipaddress.ip_network("193.32.0.0/16"),
    ipaddress.ip_network("146.70.0.0/16"),  # M247
    ipaddress.ip_network("185.220.0.0/16"),  # tor
    ipaddress.ip_network("8.208.0.0/12"),  # Alibaba
    ipaddress.ip_network("8.210.0.0/16"),
    ipaddress.ip_network("47.74.0.0/15"),
    ipaddress.ip_network("47.88.0.0/16"),
    ipaddress.ip_network("216.73.192.0/19"),  # Censys-ish
    ipaddress.ip_network("167.94.138.0/24"),
    ipaddress.ip_network("162.142.125.0/24"),
    ipaddress.ip_network("66.132.0.0/16"),
    ipaddress.ip_network("13.37.0.0/16"),
    ipaddress.ip_network("4.0.0.0/8"),  # Azure
    ipaddress.ip_network("20.0.0.0/8"),
    ipaddress.ip_network("40.0.0.0/8"),
    ipaddress.ip_network("104.40.0.0/13"),
]

ENTITY = re.compile(r"^/(sailor|club|class|regatta|boat|boat-name)/")
SCAN = re.compile(
    r"^/(\.git|wp-|wordpress|xmlrpc|phpmyadmin|pma/|adminer|\.env|wp-config|\.aws|"
    r"backend/|public/|cgi-bin|vendor/|\.well-known/security)"
)


def in_nets(ip, nets) -> bool:
    a = ipaddress.ip_address(ip)
    return any(a in n for n in nets)


def net24(ip: str) -> str:
    a = ipaddress.ip_address(ip)
    if a.version == 6:
        return str(ipaddress.ip_network(f"{ip}/64", strict=False))
    return str(ipaddress.ip_network(f"{ip}/24", strict=False))


def open_log(p: Path):
    if str(p).endswith(".gz"):
        return gzip.open(p, "rt", encoding="utf-8", errors="replace")
    return open(p, "rt", encoding="utf-8", errors="replace")


ip_stats = collections.defaultdict(
    lambda: {
        "html": 0,
        "entity": 0,
        "scan": 0,
        "mins": collections.Counter(),
        "days": set(),
        "ua_bot": 0,
        "ua_browser": 0,
    }
)

n = 0
for log in LOGS:
    if not log.exists():
        continue
    with open_log(log) as f:
        for line in f:
            n += 1
            parts = line.split()
            if len(parts) < 9:
                continue
            ip = parts[0]
            if ip in SKIP_IP:
                continue
            try:
                ipaddress.ip_address(ip)
            except ValueError:
                continue
            method = parts[5][1:] if parts[5].startswith('"') else parts[5]
            if method not in ("GET", "HEAD"):
                continue
            req = line.split('"')[1] if '"' in line else ""
            bits = req.split()
            path = bits[1].split("?")[0] if len(bits) > 1 else ""
            if ASSET.search(path) or API_POLL.search(path):
                continue
            ua = line.split('"')[-2] if line.count('"') >= 5 else ""
            if any(s in ua for s in SKIP_UA):
                continue
            ts = parts[3]
            st = ip_stats[ip]
            st["html"] += 1
            st["mins"][ts[1:18]] += 1
            st["days"].add(ts[1:12])
            if ENTITY.search(path):
                st["entity"] += 1
            if SCAN.search(path):
                st["scan"] += 1
            if "bot" in ua.lower() or "spider" in ua.lower() or "crawler" in ua.lower():
                st["ua_bot"] += 1
            else:
                st["ua_browser"] += 1

print("lines", n, "ips", len(ip_stats))

normal, swarm = set(), set()
for ip, st in ip_stats.items():
    peak = max(st["mins"].values()) if st["mins"] else 0
    html, entity, scan, days = st["html"], st["entity"], st["scan"], len(st["days"])
    botish = st["ua_bot"] > st["ua_browser"]
    is_scan = scan >= 3 or (scan >= 1 and html <= scan + 2)
    is_flood = peak >= 20  # well above 1.5x p90(~9) / 1.5x p75(3)
    is_farm = entity >= 30 and days <= 1 and peak >= 8
    if ip in KEEP_IP:
        normal.add(ip)
    elif is_scan or is_flood or is_farm or (botish and peak >= 10):
        swarm.add(ip)
    else:
        normal.add(ip)

print("normal", len(normal), "swarm", len(swarm))

norm_nets = collections.Counter(net24(ip) for ip in normal)
swarm_nets = collections.Counter(net24(ip) for ip in swarm)

block_ranges = []
block_ips = []
for ip in sorted(swarm, key=lambda x: ipaddress.ip_address(x)):
    net = net24(ip)
    n_norm = norm_nets.get(net, 0)
    n_sw = swarm_nets.get(net, 0)
    hosting = in_nets(ip, HOSTING)
    never = in_nets(ip, NEVER_RANGE)
    if never:
        # ZA / CF: only the single swarm IP, never the range
        block_ips.append(ip)
    elif hosting and n_norm == 0:
        block_ranges.append(net)
    elif n_norm == 0 and n_sw >= 2 and hosting:
        block_ranges.append(net)
    else:
        block_ips.append(ip)

block_ranges = sorted(set(block_ranges), key=lambda n: ipaddress.ip_network(n))
range_set = set(block_ranges)
block_ips = [ip for ip in block_ips if net24(ip) not in range_set]
block_ips = sorted(set(block_ips), key=lambda x: ipaddress.ip_address(x))

print("block_ranges", len(block_ranges))
for net in block_ranges[:50]:
    print(" ", net, "swarm", swarm_nets[net], "normal", norm_nets.get(net, 0))
print("block_ips", len(block_ips))
for ip in block_ips[:25]:
    st = ip_stats[ip]
    print(" ", ip, "peak", max(st["mins"].values()), "html", st["html"], "scan", st["scan"])

lines = [
    "# SailingSA permanent swarm deny — built from nginx history.\n",
    "# Range deny ONLY for hosting/scanner nets with 0 normal visitor IPs.\n",
    "# ZA / Africa / Cloudflare ranges: individual swarm IPs only.\n",
    f"# normal_ips={len(normal)} swarm_ips={len(swarm)} ranges={len(block_ranges)} singles={len(block_ips)}\n",
]
for net in block_ranges:
    lines.append(f"deny {net};\n")
for ip in block_ips:
    lines.append(f"deny {ip};\n")
Path("/tmp/ssa_swarm_deny.conf").write_text("".join(lines))
print("wrote", len(block_ranges) + len(block_ips), "deny lines")
