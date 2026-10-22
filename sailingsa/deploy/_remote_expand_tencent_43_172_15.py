#!/usr/bin/env python3
"""Expand Tencent block 43.172/16 → 43.172.0.0/15 (covers 43.173 spillover)."""
from pathlib import Path
import subprocess
import sys

# --- nginx ---
ngx = Path("/etc/nginx/snippets/sailingsa-swarm-deny.conf")
subprocess.check_call(
    ["cp", "-a", str(ngx), f"/root/sailingsa-swarm-deny.conf.bak.expand15"]
)
t = ngx.read_text(encoding="utf-8")
if "deny 43.172.0.0/15" in t:
    print("SKIP nginx /15")
elif "deny 43.172.0.0/16" in t:
    t = t.replace("deny 43.172.0.0/16;", "deny 43.172.0.0/15;", 1)
    t = t.replace(
        "swarm 2026-10-22 on 43.172.194–198.x",
        "swarm 2026-10-22 — /15 covers 43.172+43.173",
        1,
    )
    ngx.write_text(t, encoding="utf-8")
    print("OK nginx /16→/15")
else:
    needle = "deny 4.224.45.0/24;"
    block = (
        "# Tencent Cloud AS132203 (SG) — 43.172.0.0/15 covers 43.172+43.173\n"
        "deny 43.172.0.0/15;\n" + needle
    )
    if needle not in t:
        raise SystemExit("FAIL nginx needle")
    ngx.write_text(t.replace(needle, block, 1), encoding="utf-8")
    print("OK nginx insert /15")

r = subprocess.run(["nginx", "-t"], capture_output=True, text=True)
print(r.stderr or r.stdout)
if r.returncode != 0:
    raise SystemExit("nginx -t failed")
subprocess.check_call(["systemctl", "reload", "nginx"])
print("NGINX_OK")

# --- iptables ---
subprocess.run(
    ["iptables", "-D", "INPUT", "-s", "43.172.0.0/16", "-j", "DROP"],
    check=False,
    capture_output=True,
)
# wipe leftover /16
for _ in range(5):
    r = subprocess.run(
        ["iptables", "-C", "INPUT", "-s", "43.172.0.0/16", "-j", "DROP"],
        capture_output=True,
    )
    if r.returncode != 0:
        break
    subprocess.run(
        ["iptables", "-D", "INPUT", "-s", "43.172.0.0/16", "-j", "DROP"], check=False
    )

r = subprocess.run(
    ["iptables", "-C", "INPUT", "-s", "43.172.0.0/15", "-j", "DROP"],
    capture_output=True,
)
if r.returncode == 0:
    print("SKIP iptables /15")
else:
    subprocess.check_call(
        [
            "iptables",
            "-I",
            "INPUT",
            "1",
            "-s",
            "43.172.0.0/15",
            "-j",
            "DROP",
            "-m",
            "comment",
            "--comment",
            "Tencent AS132203 swarm 43.172/15",
        ]
    )
    print("OK iptables /15")

Path("/etc/iptables").mkdir(parents=True, exist_ok=True)
with open("/etc/iptables/rules.v4", "w") as f:
    subprocess.check_call(["iptables-save"], stdout=f)
print("SAVED iptables")

# --- api.py ---
api = Path("/var/www/sailingsa/api/api.py")
subprocess.run(["chattr", "-i", str(api)], check=False)
src = api.read_text(encoding="utf-8")
if "43.172.0.0/15" in src and "43.172.0.0/16" not in src:
    print("SKIP api already /15")
else:
    src2 = src.replace("43.172.0.0/16", "43.172.0.0/15")
    if src2 == src:
        raise SystemExit("FAIL api replace")
    compile(src2, str(api), "exec")
    Path("/tmp/api_tencent15.py").write_text(src2, encoding="utf-8")
    subprocess.check_call(["cp", "-f", "/tmp/api_tencent15.py", str(api)])
    print("OK api /15")

subprocess.check_call(["systemctl", "restart", "sailingsa-api"])
subprocess.run(["sleep", "4"])
print("api", subprocess.check_output(["systemctl", "is-active", "sailingsa-api"], text=True).strip())

# --- quarantine + purge live guest sessions ---
import os
import psycopg2

pid = subprocess.check_output(
    "pgrep -f 'uvicorn api:app' | head -1", shell=True, text=True
).strip()
env = open(f"/proc/{pid}/environ", "rb").read().split(b"\0")
url = None
for e in env:
    if e.startswith(b"DB_URL="):
        url = e.split(b"=", 1)[1].decode()
        break
conn = psycopg2.connect(url)
cur = conn.cursor()
cur.execute(
    """
    INSERT INTO traffic_quarantine_ips (ip_address, reason, active, hit_count, first_seen_at, last_seen_at)
    SELECT h.ip_address, 'tencent_43_172_15_swarm', true, count(*)::int,
           min(h.occurred_at), max(h.occurred_at)
    FROM public_page_hits h
    WHERE (h.ip_address LIKE '43.172.%' OR h.ip_address LIKE '43.173.%')
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
    """
    SELECT count(*) FROM traffic_quarantine_ips
    WHERE (ip_address LIKE '43.172.%' OR ip_address LIKE '43.173.%') AND active
    """
)
print("quarantine", cur.fetchone()[0])
cur.execute(
    "DELETE FROM public_sessions WHERE ip_address LIKE '43.172.%' OR ip_address LIKE '43.173.%'"
)
print("purged_sessions", cur.rowcount)
conn.commit()
cur.close()
conn.close()

sys.path.insert(0, "/var/www/sailingsa/api")
import importlib

api_mod = importlib.import_module("api")
for ip in ("43.173.177.15", "43.173.179.48", "43.172.197.236"):
    assert api_mod._lean_is_crawler_cloud_ip(ip), ip
    assert api_mod._lean_ip_is_cloud_datacenter(ip), ip
print("OK 43.172+43.173 classified crawler/cloud")
print("DONE expand /15")
