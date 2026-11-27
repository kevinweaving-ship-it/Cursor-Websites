#!/usr/bin/env python3
"""Block Tencent 43.172/16 in api.py via write-to-tmp + cp (handles immutable)."""
from pathlib import Path
import os, subprocess, shutil

API = Path("/var/www/sailingsa/api/api.py")
subprocess.run(["chattr", "-i", str(API)], check=False)

text = API.read_text(encoding="utf-8")
orig = text

old_scan = """_KNOWN_SCANNER_NETS = (
    ipaddress.ip_network(\"47.79.0.0/16\"),   # Alibaba Cloud
    ipaddress.ip_network(\"43.128.0.0/14\"),  # Tencent Cloud
    ipaddress.ip_network(\"43.132.0.0/16\"),
)"""
new_scan = """_KNOWN_SCANNER_NETS = (
    ipaddress.ip_network(\"47.79.0.0/16\"),   # Alibaba Cloud
    ipaddress.ip_network(\"43.128.0.0/14\"),  # Tencent Cloud
    ipaddress.ip_network(\"43.132.0.0/16\"),
    ipaddress.ip_network(\"43.172.0.0/16\"),  # Tencent AS132203 SG swarm 2026-10-22
)"""

if 'ip_network("43.172.0.0/16")' in text.split("_KNOWN_SCANNER_NETS", 1)[-1][:600]:
    print("SKIP scanner")
elif old_scan not in text:
    raise SystemExit("FAIL scanner block")
else:
    text = text.replace(old_scan, new_scan, 1)
    print("OK scanner")

cloud_needle = '"47.96.0.0/11",'
cloud_add = (
    '"47.96.0.0/11",\n'
    '                "43.128.0.0/14",  # Tencent Cloud\n'
    '                "43.132.0.0/16",\n'
    '                "43.172.0.0/16",  # Tencent AS132203 SG — regatta/sailor swarm'
)
idx = text.find("def _lean_cloud_nets")
if idx < 0:
    raise SystemExit("FAIL no cloud nets")
chunk = text[idx : idx + 2000]
if '"43.172.0.0/16"' in chunk:
    print("SKIP cloud")
elif cloud_needle not in chunk:
    raise SystemExit("FAIL cloud needle")
else:
    text = text[:idx] + chunk.replace(cloud_needle, cloud_add, 1) + text[idx + 2000 :]
    print("OK cloud")

if text == orig:
    print("NOCHANGE")
else:
    compile(text, str(API), "exec")
    tmp = Path("/tmp/api_tencent_patched.py")
    tmp.write_text(text, encoding="utf-8")
    subprocess.check_call(["cp", "-f", str(tmp), str(API)])
    print("WROTE via cp -f delta", len(text) - len(orig))

# confirm
src = API.read_text(encoding="utf-8")
assert "43.172.0.0/16" in src
print("OK api contains 43.172.0.0/16")
