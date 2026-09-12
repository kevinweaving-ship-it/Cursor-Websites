#!/bin/bash
set -euo pipefail
TOK="$1"
OUT="${2:-/var/www/sailingsa/assets/adverts/mm-cape-classic/zvyc-live-cam.jpg}"
TMP="${OUT}.tmp"
URL="https://hd-auth.skylinewebcams.com/live.m3u8?a=${TOK}"
mkdir -p "$(dirname "$OUT")"
/usr/bin/ffmpeg -hide_banner -loglevel error \
  -headers $'Referer: https://www.skylinewebcams.com/en/webcam/south-africa/western-cape/cape-town/zeekoevlei.html\r\nUser-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36\r\n' \
  -rw_timeout 5000000 \
  -i "$URL" -ss 1 -frames:v 1 -q:v 5 -f image2 "$TMP"
ls -la "$TMP"
file "$TMP"
python3 - <<PY
from pathlib import Path
p = Path("$TMP")
b = p.read_bytes()
print("magic", b[:3], "size", len(b))
if b[:2] != b"\xff\xd8" or len(b) < 800:
    raise SystemExit("not a jpeg")
PY
mv -f "$TMP" "$OUT"
chown www-data:www-data "$OUT"
ls -la "$OUT"
