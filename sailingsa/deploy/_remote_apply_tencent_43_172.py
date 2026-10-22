#!/usr/bin/env python3
"""Quarantine all recent 43.172.* hitters + verify nets/nginx."""
import os, subprocess, ipaddress, psycopg2

url = os.environ.get("DB_URL")
if not url:
    pid = subprocess.check_output(
        "pgrep -f 'uvicorn api:app' | head -1", shell=True, text=True
    ).strip()
    env = open(f"/proc/{pid}/environ", "rb").read().split(b"\0")
    for e in env:
        if e.startswith(b"DB_URL="):
            url = e.split(b"=", 1)[1].decode()
            break

conn = psycopg2.connect(url)
cur = conn.cursor()
cur.execute(
    """
    INSERT INTO traffic_quarantine_ips (ip_address, reason, active, hit_count, first_seen_at, last_seen_at)
    SELECT h.ip_address,
           'tencent_43_172_swarm',
           true,
           count(*)::int,
           min(h.occurred_at),
           max(h.occurred_at)
    FROM public_page_hits h
    WHERE h.ip_address LIKE '43.172.%'
      AND h.occurred_at > NOW() - interval '14 days'
    GROUP BY h.ip_address
    ON CONFLICT (ip_address) DO UPDATE SET
      active = true,
      reason = EXCLUDED.reason,
      hit_count = GREATEST(traffic_quarantine_ips.hit_count, EXCLUDED.hit_count),
      last_seen_at = GREATEST(traffic_quarantine_ips.last_seen_at, EXCLUDED.last_seen_at)
    """
)
conn.commit()
cur.execute(
    "SELECT count(*) FROM traffic_quarantine_ips WHERE reason='tencent_43_172_swarm' AND active"
)
print("quarantined_active", cur.fetchone()[0])
cur.close()
conn.close()

# Verify API nets
import sys
sys.path.insert(0, "/var/www/sailingsa/api")
import importlib
api = importlib.import_module("api")
addr = ipaddress.ip_address("43.172.197.236")
assert any(addr in n for n in api._KNOWN_SCANNER_NETS), "not in scanner nets"
assert api._lean_is_crawler_cloud_ip("43.172.197.236"), "not crawler cloud"
assert api._lean_ip_is_cloud_datacenter("43.172.197.236"), "not cloud dc"
ngx = open("/etc/nginx/snippets/sailingsa-swarm-deny.conf").read()
assert "deny 43.172.0.0/16" in ngx
print("OK tencent 43.172 block verified")
