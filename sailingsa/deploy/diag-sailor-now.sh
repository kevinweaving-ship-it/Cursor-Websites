#!/bin/bash
set -euo pipefail
echo '=== api status ==='
systemctl is-active sailingsa-api nginx
echo '=== recent api log ==='
journalctl -u sailingsa-api -n 80 --no-pager || true
echo '=== listen 8000 ==='
ss -ltnp | grep 8000 || true
echo '=== local sailor ==='
curl -sS -o /tmp/loc-sean.html -w 'sean=%{http_code} t=%{time_total} b=%{size_download}\n' -m 15 http://127.0.0.1:8000/sailor/sean-kavangh || echo 'sean fail'
curl -sS -o /tmp/loc-rae.html -w 'rae=%{http_code} t=%{time_total} b=%{size_download}\n' -m 15 http://127.0.0.1:8000/sailor/david-rae || echo 'rae fail'
curl -sS -o /tmp/loc-live.json -w 'live=%{http_code} t=%{time_total} b=%{size_download}\n' -m 20 http://127.0.0.1:8000/api/lipton-dev/live || echo 'live fail'
echo '=== sailor dir ==='
ls -la /var/www/sailingsa/sailor 2>/dev/null | head || echo 'no sailor dir'
echo '=== nginx sailor locs ==='
grep -n sailor /etc/nginx/sites-enabled/sailingsa
echo '=== live.py holding ==='
grep -c holding_last /var/www/sailingsa/scripts/lipton_dev_live.py /var/www/sailingsa/sailingsa/scripts/lipton_dev_live.py || true
python3 - <<'PY'
from pathlib import Path
for p in ("/tmp/loc-sean.html","/tmp/loc-rae.html"):
    t=Path(p)
    if not t.is_file():
        print(p, "missing"); continue
    s=t.read_text(encoding="utf-8", errors="replace")
    i=s.find("<title>"); j=s.find("</title>")
    print(p, "title", s[i:j+8] if i>=0 else s[:120].replace("\n"," "))
PY
