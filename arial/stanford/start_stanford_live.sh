#!/bin/bash
# Fast Stanford LIVE: last 640p JPEG immediately, refresh snap in background.
# Usage: start_stanford_live.sh SERIAL NAME rtsp://...
set -u
SERIAL=$1
NAME=$2
RTSP=$3
JPG="/opt/ezvizpoc/out/${NAME}_640.jpg"
WEB="/var/www/sailingsa/stanford/thumbs/${NAME}.jpg"
LOG="/opt/ezvizpoc/out/bridge_${NAME}.log"
SNAP=/opt/hikpoc/venv/bin/python
PY=/opt/ezvizpoc/bridge_ezviz_snap.py
FF=/opt/hikpoc/bin/ffmpeg
mkdir -p /var/www/sailingsa/stanford/thumbs
publish() {
  if [ -s "$JPG" ]; then
    cp -f "$JPG" "$WEB"
    chmod 644 "$WEB"
  fi
}
publish
if [ ! -s "$JPG" ]; then
  "$SNAP" "$PY" "$SERIAL" "$JPG" >>"$LOG" 2>&1 || true
  publish
fi
"$SNAP" "$PY" "$SERIAL" "$JPG" >>"$LOG" 2>&1 && publish &
exec "$FF" -hide_banner -loglevel error -loop 1 -i "$JPG" -an \
  -c:v libx264 -preset ultrafast -tune zerolatency -profile:v baseline -pix_fmt yuv420p \
  -r 12 -g 12 -muxdelay 0 -muxpreload 0 -rtsp_transport tcp -f rtsp "$RTSP"
