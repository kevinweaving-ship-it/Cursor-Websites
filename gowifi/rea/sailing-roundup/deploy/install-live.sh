#!/bin/bash
# Install the Monday weekend-roundup publisher on the SailingSA live box.
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo "run as root on sailingsa live" >&2; exit 1; }
[ -d /var/www/sailingsa ] || { echo "this is not the SailingSA web box" >&2; exit 1; }

SRC_DIR="${1:-}"
[ -n "$SRC_DIR" ] && [ -f "$SRC_DIR/app/publish_weekend.py" ] || {
  echo "usage: $0 /path/to/gowifi/rea/sailing-roundup" >&2
  exit 1
}

DEST=/opt/sailing-roundup
install -d -m 755 "$DEST" "$DEST/app" "$DEST/data" "$DEST/issues" "$DEST/public" "$DEST/public/issues" "$DEST/deploy"
install -m 644 "$SRC_DIR"/app/*.py "$DEST/app/"
install -m 644 "$SRC_DIR/app/club_sources.json" "$DEST/app/club_sources.json"
install -m 644 "$SRC_DIR/app/class_sources.json" "$DEST/app/class_sources.json"
install -m 644 "$SRC_DIR/requirements.txt" "$DEST/requirements.txt"
install -m 644 "$SRC_DIR/README.md" "$DEST/README.md"
install -m 644 "$SRC_DIR/CONTENT_CONTRACT.md" "$DEST/CONTENT_CONTRACT.md"
install -m 755 "$SRC_DIR/deploy/run-monday.sh" "$DEST/deploy/run-monday.sh"
install -m 755 "$SRC_DIR/deploy/publish-to-sailingsa.sh" "$DEST/deploy/publish-to-sailingsa.sh"

if [ ! -x "$DEST/.venv/bin/python3" ]; then
  python3 -m venv "$DEST/.venv"
fi
"$DEST/.venv/bin/pip" install -q -r "$DEST/requirements.txt"
"$DEST/.venv/bin/pip" install -q gallery-dl yt-dlp || true

install -m 644 "$SRC_DIR/deploy/sailing-roundup-live.service" /etc/systemd/system/sailing-roundup.service
install -m 644 "$SRC_DIR/deploy/sailing-roundup.timer" /etc/systemd/system/sailing-roundup.timer
systemctl daemon-reload
systemctl enable --now sailing-roundup.timer

echo "installed $DEST"
systemctl list-timers sailing-roundup.timer --no-pager
