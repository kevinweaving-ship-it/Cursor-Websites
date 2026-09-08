#!/bin/bash
# Fallback only. go2rtc yaml uses this same RTP | hikpoc ffmpeg hevc | 640p line.
set -euo pipefail
SERIAL="${1:-}"
if [ -z "$SERIAL" ]; then
  echo "usage: $0 SERIAL" >&2
  exit 1
fi
export PATH="/opt/hikpoc/bin:/usr/bin:$PATH"
exec bash -c "trap 'kill 0' EXIT TERM INT; /opt/hikpoc/venv/bin/python /opt/ezvizpoc/bridge_ezviz_rtp.py \"$SERIAL\" | /opt/hikpoc/bin/ffmpeg -hide_banner -loglevel error -fflags nobuffer+genpts -flags low_delay -err_detect ignore_err -probesize 32 -analyzeduration 0 -f hevc -i pipe:0 -an -vf scale=640:-2 -r 12 -vsync cfr -c:v libx264 -preset ultrafast -tune zerolatency -profile:v baseline -pix_fmt yuv420p -g 12 -muxdelay 0 -muxpreload 0 -f mpegts -"
