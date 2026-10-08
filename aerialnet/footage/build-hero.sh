#!/bin/bash
# Build the Aerial Networks hero loop from the three Pexels downloads.
# Does not publish the site.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
SRC=${1:-/tmp/aerial-footage}
WORK=${SRC}/build
mkdir -p "$WORK" "$ROOT/media"

LAND="$SRC/12915608-landscape.mp4"
MAST="$SRC/4916490-mast.mp4"
RACK="$SRC/5028622-racks.mp4"
for f in "$LAND" "$MAST" "$RACK"; do
  if [ ! -f "$f" ]; then
    echo "Missing $f" >&2
    echo "Download with the official Pexels redirect, for example:" >&2
    echo "  curl -L -o $LAND https://www.pexels.com/download/video/12915608/" >&2
    exit 1
  fi
done

GRADE="eq=contrast=1.04:brightness=0.01:saturation=0.75,colorbalance=rh=-0.03:bh=0.04:rm=-0.02:bm=0.03"
COVER="fps=30,scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,${GRADE},format=yuv420p"

ffmpeg -y -ss 0 -t 10.8 -i "$LAND" -an -vf "$COVER" -c:v libx264 -pix_fmt yuv420p -preset veryfast "$WORK/land.mp4"
ffmpeg -y -ss 0.4 -t 8.4 -i "$MAST" -an -vf "$COVER" -c:v libx264 -pix_fmt yuv420p -preset veryfast "$WORK/mast.mp4"
ffmpeg -y -ss 20.0 -t 8.4 -i "$RACK" -an -vf "$COVER" -c:v libx264 -pix_fmt yuv420p -preset veryfast "$WORK/rack.mp4"
ffmpeg -y -t 1.2 -i "$WORK/land.mp4" -an -c copy "$WORK/return.mp4"

ffmpeg -y -i "$WORK/land.mp4" -i "$WORK/mast.mp4" -i "$WORK/rack.mp4" -i "$WORK/return.mp4" \
  -filter_complex "[0:v][1:v]xfade=transition=fade:duration=1.2:offset=9.6[a];[a][2:v]xfade=transition=fade:duration=1.2:offset=16.8[b];[b][3:v]xfade=transition=fade:duration=1.2:offset=24[c];[c]trim=start=1.2:duration=24,setpts=PTS-STARTPTS[v]" \
  -map "[v]" -an -c:v libx264 -pix_fmt yuv420p -preset slow -b:v 2300k -maxrate 2600k -bufsize 4800k \
  -movflags +faststart "$ROOT/media/hero-1080.mp4"

ffmpeg -y -i "$ROOT/media/hero-1080.mp4" -an -vf scale=1280:720 -c:v libx264 -pix_fmt yuv420p -preset slow \
  -b:v 800k -maxrate 1000k -bufsize 2000k -movflags +faststart "$ROOT/media/hero-720.mp4"

ffmpeg -y -i "$ROOT/media/hero-1080.mp4" -frames:v 1 -vf scale=1600:-1 -q:v 3 "$ROOT/media/hero-poster.jpg"

ffprobe -v error -show_entries format=duration,size -show_entries stream=codec_name,width,height -of default=nw=1 "$ROOT/media/hero-1080.mp4"
ffprobe -v error -show_entries format=duration,size -show_entries stream=codec_name,width,height -of default=nw=1 "$ROOT/media/hero-720.mp4"
ls -lh "$ROOT/media/hero-1080.mp4" "$ROOT/media/hero-720.mp4" "$ROOT/media/hero-poster.jpg"
