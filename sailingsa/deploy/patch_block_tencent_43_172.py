#!/usr/bin/env python3
"""Block Tencent Cloud 43.172.0.0/16 swarm (AS132203) — nginx deny + API cloud nets + quarantine.

Confirmed 2026-10-22: dozens of 43.172.194–198.x IPs deep-linking /regatta + /sailor
with fake Chrome UAs and sparse/fake clicked tokens. ipinfo: Tencent Building, Singapore.
Existing Tencent net 43.128.0.0/14 does NOT cover 43.172.
"""
from pathlib import Path
import sys

API = Path("/var/www/sailingsa/api/api.py")
NGINX = Path("/etc/nginx/snippets/sailingsa-swarm-deny.conf")

DENY_BLOCK = """
# Tencent Cloud AS132203 (SG) — swarm 2026-10-22 on 43.172.194–198.x
# Existing 43.128.0.0/14 does not cover 43.172.
deny 43.172.0.0/16;
"""

# --- nginx ---
if NGINX.exists():
    ngx = NGINX.read_text(encoding="utf-8")
    if "deny 43.172.0.0/16" in ngx:
        print("SKIP nginx already has 43.172.0.0/16")
    else:
        # Insert after the header comment block, before first deny (or append before end)
        # Prefer after Telkom allow lines if present
        marker = "deny 4.224.45.0/24;"
        if marker in ngx:
            ngx = ngx.replace(marker, DENY_BLOCK.strip() + "\n" + marker, 1)
        else:
            ngx = ngx.rstrip() + "\n" + DENY_BLOCK
        NGINX.write_text(ngx, encoding="utf-8")
        print("OK nginx deny 43.172.0.0/16")
else:
    print("WARN no nginx swarm deny file", file=sys.stderr)

# --- api.py ---
text = API.read_text(encoding="utf-8")
orig = text

# 1) Known scanner nets (probe ban path)
old_scan = '''_KNOWN_SCANNER_NETS = (
    ipaddress.ip_network("47.79.0.0/16"),   # Alibaba Cloud
    ipaddress.ip_network("43.128.0.0/14"),  # Tencent Cloud
    ipaddress.ip_network("43.132.0.0/16"),
)'''
new_scan = '''_KNOWN_SCANNER_NETS = (
    ipaddress.ip_network("47.79.0.0/16"),   # Alibaba Cloud
    ipaddress.ip_network("43.128.0.0/14"),  # Tencent Cloud
    ipaddress.ip_network("43.132.0.0/16"),
    ipaddress.ip_network("43.172.0.0/16"),  # Tencent AS132203 SG swarm 2026-10-22
)'''
if 'ipaddress.ip_network("43.172.0.0/16")' in text.split("_KNOWN_SCANNER_NETS", 1)[-1][:500]:
    print("SKIP scanner nets")
elif old_scan in text:
    text = text.replace(old_scan, new_scan, 1)
    print("OK _KNOWN_SCANNER_NETS +43.172/16")
else:
    print("WARN scanner nets block mismatch", file=sys.stderr)

# 2) Cloud nets used by _lean_ip_is_cloud_datacenter / crawler_cloud_ip
# Insert after Alibaba 47.x block or at end of tuple before closing
cloud_needle = '"47.96.0.0/11",'
cloud_add = '''"47.96.0.0/11",
                "43.128.0.0/14",  # Tencent Cloud
                "43.132.0.0/16",
                "43.172.0.0/16",  # Tencent AS132203 SG — regatta/sailor swarm'''
if '"43.172.0.0/16"' in text.split("def _lean_cloud_nets", 1)[-1][:1200]:
    print("SKIP cloud nets")
elif cloud_needle in text:
    # only first occurrence in cloud nets list
    idx = text.find("def _lean_cloud_nets")
    if idx < 0:
        print("WARN no _lean_cloud_nets", file=sys.stderr)
    else:
        chunk = text[idx : idx + 2000]
        if cloud_needle in chunk and '"43.172.0.0/16"' not in chunk:
            chunk2 = chunk.replace(cloud_needle, cloud_add, 1)
            text = text[:idx] + chunk2 + text[idx + 2000 :]
            print("OK _lean_cloud_nets +43.172/16")
        else:
            print("WARN cloud nets insert skipped", file=sys.stderr)
else:
    print("WARN cloud needle missing", file=sys.stderr)

if text != orig:
    try:
        compile(text, str(API), "exec")
    except SyntaxError as e:
        print("SYNTAX", e, file=sys.stderr)
        sys.exit(1)
    import subprocess
    subprocess.run(["chattr", "-i", str(API)], check=False)
    tmp = Path("/tmp/api_tencent_patched.py")
    tmp.write_text(text, encoding="utf-8")
    subprocess.check_call(["cp", "-f", str(tmp), str(API)])
    print("WROTE api.py via cp -f delta", len(text) - len(orig))
else:
    print("api.py unchanged")

print("DONE patch file")
