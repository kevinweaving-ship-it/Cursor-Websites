#!/bin/bash
# Unused by go2rtc once yaml uses Bing exec directly.
# Kept as the same Bing gold pipeline (bridge_ezviz.sh | hikpoc ffmpeg mpeg).
# Usage: start_stanford_live.sh SERIAL
set -euo pipefail
SERIAL="${1:-}"
if [ -z "$SERIAL" ]; then
  echo "usage: $0 SERIAL" >&2
  exit 1
fi
export PATH="/opt/hikpoc/bin:/usr/bin:$PATH"
exec bash -c "trap 'kill 0' EXIT TERM INT; /opt/ezvizpoc/bridge_ezviz.sh \"$SERIAL\" | /opt/hikpoc/bin/ffmpeg -hide_banner -loglevel error -fflags nobuffer+genpts -flags low_delay -err_detect ignore_err -probesize 500000 -analyzeduration 500000 -f mpeg -i pipe:0 -an -vf scale=640:-2 -r 12 -vsync cfr -c:v libx264 -preset ultrafast -tune zerolatency -profile:v baseline -pix_fmt yuv420p -g 12 -muxdelay 0 -muxpreload 0 -f mpegts -"
