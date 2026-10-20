#!/bin/bash
# Install the independent weekend-roundup publisher on GoWifi.
# Does not change SailingSA, gowifi.co.za nginx, REA package files, or the MCP tunnel.
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo "run as root on GoWifi" >&2; exit 1; }

SRC_DIR="${1:-}"
[ -n "$SRC_DIR" ] && [ -f "$SRC_DIR/app/publish_weekend.py" ] || {
  echo "usage: $0 /path/to/gowifi/rea/sailing-roundup" >&2
  exit 1
}

DEST=/opt/rea/work/sailing-roundup
install -d -m 755 -o rea -g rea "$DEST" "$DEST/app" "$DEST/data" "$DEST/issues" "$DEST/public" "$DEST/public/issues"

# App code only. Never clobber generated issues or the venv.
install -m 644 -o rea -g rea "$SRC_DIR"/app/*.py "$DEST/app/"
install -m 644 -o rea -g rea "$SRC_DIR/app/club_sources.json" "$DEST/app/club_sources.json"
install -m 644 -o rea -g rea "$SRC_DIR/app/class_sources.json" "$DEST/app/class_sources.json"
install -m 644 -o rea -g rea "$SRC_DIR/requirements.txt" "$DEST/requirements.txt"
install -m 644 -o rea -g rea "$SRC_DIR/README.md" "$DEST/README.md"
install -m 644 -o rea -g rea "$SRC_DIR/PROJECT.md" "$DEST/PROJECT.md"
install -m 644 -o rea -g rea "$SRC_DIR/CONTENT_CONTRACT.md" "$DEST/CONTENT_CONTRACT.md"

if [ ! -x "$DEST/.venv/bin/python3" ]; then
  sudo -u rea -H python3 -m venv "$DEST/.venv"
fi
sudo -u rea -H "$DEST/.venv/bin/pip" install -q -r "$DEST/requirements.txt"
sudo -u rea -H "$DEST/.venv/bin/pip" install -q gallery-dl yt-dlp || true

# Local copy on the REA box www tree (real files — nginx cannot follow /opt/rea).
# Canonical public URL is https://sailingsa.co.za/sailing-roundup/ after publish-to-sailingsa.sh
WWW=/home/user-data/www/default/sailing-roundup
rm -rf "$WWW"
mkdir -p "$WWW"
if [ -d "$DEST/public" ]; then
  tar -C "$DEST/public" -cf - . | tar -C "$WWW" -xf -
fi

install -d -m 755 -o rea -g rea "$DEST/deploy"
install -m 755 -o rea -g rea "$SRC_DIR/deploy/run-monday.sh" "$DEST/deploy/run-monday.sh"
install -m 755 -o rea -g rea "$SRC_DIR/deploy/publish-to-sailingsa.sh" "$DEST/deploy/publish-to-sailingsa.sh"
install -m 644 "$SRC_DIR/deploy/sailing-roundup.service" /etc/systemd/system/sailing-roundup.service
install -m 644 "$SRC_DIR/deploy/sailing-roundup.timer" /etc/systemd/system/sailing-roundup.timer
# Africa/Johannesburg is the box timezone; timer OnCalendar uses local time.
systemctl daemon-reload
systemctl enable --now sailing-roundup.timer

# Leftover from a previous brace-expansion mistake.
rm -rf "$DEST/{app,issues"

echo "installed $DEST"
systemctl list-timers sailing-roundup.timer --no-pager
