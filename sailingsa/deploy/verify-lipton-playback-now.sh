#!/bin/bash
set -euo pipefail
echo waiting for :8000
for i in $(seq 1 25); do
  if ss -ltn | grep -q ':8000'; then echo listen ok; break; fi
  sleep 1
done
systemctl is-active sailingsa-api
sleep 2
curl -sS -m 20 -H 'Host: sailingsa.co.za' -A SailingSA-devcheck -o /tmp/fa.html -w 'fastapi %{http_code} %{size_download}\n' http://127.0.0.1:8000/regatta/2026-08-29-lipton-challenge-cup || true
curl -sS -m 20 -H 'Host: sailingsa.co.za' -A SailingSA-devcheck -o /tmp/fa-old.html -w 'fastapi-old %{http_code} %{size_download}\n' http://127.0.0.1:8000/regatta/2026-08-29-lipton-challenge-cup-old || true
sleep 3
curl -sk --resolve sailingsa.co.za:443:127.0.0.1 -A SailingSA-devcheck -o /tmp/p.html -D /tmp/p.hdr -w 'pub %{http_code} %{size_download}\n' https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup
curl -sk --resolve sailingsa.co.za:443:127.0.0.1 -A SailingSA-devcheck -o /tmp/o.html -w 'old %{http_code} %{size_download}\n' https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup-old
python3 - <<'PY'
from pathlib import Path
def chk(label, path):
    p = Path(path)
    if not p.is_file():
        print(label, 'MISSING')
        return
    t = p.read_text(encoding='utf-8', errors='replace')
    weather = ('WEATHER' in t) or ('Live cam' in t)
    play = 'data-lipton-dev="1"' in t
    print(label, 'bytes', len(t), 'playback', play, 'weather', weather)
chk('fastapi','/tmp/fa.html')
chk('fastapi-old','/tmp/fa-old.html')
chk('nginx-pub','/tmp/p.html')
chk('nginx-old','/tmp/o.html')
print('hdr', Path('/tmp/p.hdr').read_text(encoding='utf-8', errors='replace')[:500])
js=Path('/var/www/sailingsa/js/lipton-event-sheet.js').read_text(encoding='utf-8')
print('wrap gone', 'white-space:normal!important' not in js)
print('nowrap', 'white-space:nowrap!important' in js)
print('v ee', '20260828ee' in Path('/var/www/sailingsa/lipton-dev.html').read_text(encoding='utf-8'))
print('snip', Path('/etc/nginx/snippets/lipton-public-proxy.conf').read_text())
PY
STUB=$'#!/usr/bin/python3\nraise SystemExit(0)\n'
for f in /root/lw-g13b.py /root/lw-g14b.py /root/lw-g14.py /root/fix_api_once.py /root/hijack_shape.py /root/lipton_hold_check.py /root/strip_now.py; do
  [ -e "$f" ] || continue
  chattr -i "$f" 2>/dev/null || true
  printf '%s' "$STUB" > "$f"
  chmod 755 "$f"
  echo stubbed "$f"
done
echo remaining gold
ls /root/lw-* 2>/dev/null || true
