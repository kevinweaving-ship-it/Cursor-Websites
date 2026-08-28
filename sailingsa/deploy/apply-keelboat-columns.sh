#!/bin/bash
set -euo pipefail
cp -a /var/www/sailingsa/api/api.py "/root/api.py.bak_keelboat_$(date +%Y%m%d_%H%M%S)"
python3 /tmp/patch_keelboat_columns.py
systemctl restart sailingsa-api
sleep 4
systemctl is-active sailingsa-api
python3 - <<'PY'
import re, subprocess
html = subprocess.check_output(
    ["curl","-sS","-A","SailingSA-devcheck",
     "https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup/class-j22"],
    text=True, errors="replace",
)
ths = re.findall(r"<th[^>]*>([^<]*)</th>", html)
print("ths", ths[:20])
pub = subprocess.check_output(
    ["curl","-sS","-A","SailingSA-devcheck",
     "https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup"],
    text=True, errors="replace",
)
print("public_playback", 'data-lipton-dev="1"' in pub, "weather", "WEATHER" in pub)
if ths[:5] != ["Rank", "Bow", "Boat Name", "Club", "Nett"]:
    raise SystemExit("FAIL column order " + str(ths[:10]))
if "R7" in ths and "R1" in ths and ths.index("R7") > ths.index("R1"):
    raise SystemExit("FAIL races not newest-first")
if 'data-lipton-dev="1"' not in pub or "WEATHER" in pub:
    raise SystemExit("FAIL public URL")
print("OK keelboat columns + public still playback")
PY
