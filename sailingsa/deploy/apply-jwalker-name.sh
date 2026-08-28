#!/bin/bash
set -euo pipefail
API=/var/www/sailingsa/api/api.py
chattr -i "$API" 2>/dev/null || true
python3 /tmp/patch_jwalker_name.py
python3 -m py_compile "$API"
chattr +i "$API" 2>/dev/null || true

python3 - <<'PY'
import os
from pathlib import Path
import psycopg2
url = None
for line in Path("/var/www/sailingsa/.env").read_text().splitlines():
    if line.startswith("DB_URL="):
        url = line.split("=", 1)[1].strip().strip('"').strip("'")
conn = psycopg2.connect(url)
cur = conn.cursor()
cur.execute(
    """
    UPDATE results
    SET boat_name = 'J-Walker'
    WHERE boat_name ILIKE '%j-walker%powered by%north%'
       OR boat_name ILIKE '%j-walker powered by north sails%'
    """
)
print("results_updated", cur.rowcount)
cur.execute(
    """
    UPDATE boat_names
    SET boat_name = 'J-Walker',
        notes = COALESCE(notes,'') || ' [jwalker_north_logo_lock]'
    WHERE boat_name ILIKE '%j-walker%powered by%north%'
    """
)
print("boat_names_updated", cur.rowcount)
conn.commit()
cur.execute(
    """
    SELECT regatta_id, sail_number, bow_no, boat_name
    FROM results
    WHERE sail_number::text IN ('173')
      AND (regatta_id ILIKE '%lipton%' OR boat_name ILIKE '%walker%')
    """
)
print("lipton_173", cur.fetchall())
PY

# replay JSON on live
python3 - <<'PY'
from pathlib import Path
old_t = '"title": "J-Walker powered by North Sails"'
new_t = '"title": "J-Walker"'
old_h = '"nameHref": "/boat-name/j-walker-powered-by-north-sails"'
new_h = '"nameHref": "/boat-name/j-walker"'
n = 0
for root in (Path("/var/www/sailingsa/js"), Path("/var/www/sailingsa/frontend/js"), Path("/tmp")):
    if not root.is_dir():
        continue
    for p in root.glob("lipton-dev-replay*.json"):
        t = p.read_text(encoding="utf-8")
        nt = t.replace(old_t, new_t).replace(old_h, new_h)
        if nt != t:
            p.write_text(nt, encoding="utf-8")
            n += 1
            print("json", p)
print("json_files", n)
PY

# live race state overlay files (narrow)
python3 - <<'PY'
from pathlib import Path
n=0
roots = [
    Path("/var/www/sailingsa/js"),
    Path("/var/www/sailingsa/frontend"),
    Path("/var/www/sailingsa/data"),
    Path("/var/lib/sailingsa"),
    Path("/tmp"),
]
for root in roots:
    if not root.exists():
        continue
    for p in root.rglob("*.json"):
        try:
            t = p.read_text(encoding="utf-8")
        except Exception:
            continue
        if "J-Walker powered by North Sails" not in t:
            continue
        p.write_text(t.replace("J-Walker powered by North Sails", "J-Walker"), encoding="utf-8")
        n += 1
        print("state", p)
print("state_files", n)
PY

systemctl restart sailingsa-api
sleep 5
systemctl is-active sailingsa-api
python3 - <<'PY'
import re, subprocess
from pathlib import Path
api = Path("/var/www/sailingsa/api/api.py").read_text(encoding="utf-8")
assert "J-Walker powered by North Sails" not in api
assert '"8": ("J-Walker", "RCYCA")' in api
html = subprocess.check_output(
    ["curl","-sS","-A","SailingSA-devcheck",
     "https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup/class-j22"],
    text=True, errors="replace",
)
if "powered by" in html.lower() and "j-walker" in html.lower():
    # leftover text next to the name
    i = html.lower().find("j-walker")
    print("context", html[i:i+180])
    raise SystemExit("FAIL powered-by still in class-j22")
print("class-j22 has J-Walker", "J-Walker" in html)
print("class-j22 has North-Sails.png", "North-Sails.png" in html)
pub = subprocess.check_output(
    ["curl","-sS","-A","SailingSA-devcheck",
     "https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup"],
    text=True, errors="replace",
)
print("public_playback", 'data-lipton-dev="1"' in pub, "len", len(pub))
if 'data-lipton-dev="1"' not in pub:
    raise SystemExit("FAIL public")
print("OK J-Walker + logo")
PY
