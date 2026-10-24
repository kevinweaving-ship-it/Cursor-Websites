#!/bin/bash
# Issue-scoped publish to SailingSA: stage, validate, atomic replace, keep last-good.
# Generation stays on GoWifi. Never rsync --delete the public tree. Never touch
# SailingSA SPA, API, nginx, database, or files outside /var/www/sailingsa/sailing-roundup.
set -euo pipefail

usage() {
  echo "usage: $0 /path/to/sailing-roundup/public [YYYY-MM-DD]" >&2
  exit 1
}

SRC="${1:-}"
ISSUE="${2:-}"
[ -n "$SRC" ] && [ -d "$SRC" ] || usage
SRC="$(cd "$SRC" && pwd)"
HERE="$(cd "$(dirname "$0")" && pwd)"
SITEMAP_WRITER="$HERE/../app/write_google_sitemaps.py"
# seo_head.py + news_schema.py must sit next to the writer so live PYTHONPATH works.

if [ -z "$ISSUE" ]; then
  ISSUE="$(ls -1 "$SRC/issues" 2>/dev/null | grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' | sort | tail -1 || true)"
fi
[ -n "$ISSUE" ] || { echo "no issue date to publish" >&2; exit 1; }
[ -f "$SRC/issues/$ISSUE/index.html" ] || { echo "missing $SRC/issues/$ISSUE/index.html" >&2; exit 1; }
[ -f "$SRC/issues/$ISSUE/issue.json" ] || { echo "missing $SRC/issues/$ISSUE/issue.json" >&2; exit 1; }
[ -f "$SRC/issues/$ISSUE/edition.pdf" ] || { echo "missing $SRC/issues/$ISSUE/edition.pdf" >&2; exit 1; }

python3 - "$SRC/issues/$ISSUE" <<'PY'
import sys
from pathlib import Path
stage = Path(sys.argv[1])
if not (stage / "edition.pdf").read_bytes().startswith(b"%PDF-"):
    raise SystemExit("local edition.pdf is not a PDF")
print("local-issue-valid")
PY

DEST_DIR=/var/www/sailingsa/sailing-roundup
LANDING_FILES=(index.html latest.json feed.json cards.json)

promote_issue() {
  local live_root="$1"
  local incoming="$2"
  local issue="$3"
  local stage="$live_root/.stage/issues/$issue"
  local good="$live_root/.last-good/issues/$issue"
  local live="$live_root/issues/$issue"
  mkdir -p "$live_root/.stage/issues" "$live_root/.last-good/issues" "$live_root/issues"
  rm -rf "$stage"
  cp -a "$incoming" "$stage"
  python3 - "$stage" <<'PY'
import sys
from pathlib import Path
stage = Path(sys.argv[1])
for name in ("index.html", "issue.json", "edition.pdf"):
    if not (stage / name).is_file():
        raise SystemExit("missing " + name)
if not (stage / "edition.pdf").read_bytes().startswith(b"%PDF-"):
    raise SystemExit("invalid pdf")
print("stage-valid")
PY
  if [ -d "$live" ]; then
    rm -rf "$good"
    cp -a "$live" "$good"
  fi
  local new="$live.new"
  rm -rf "$new"
  cp -a "$stage" "$new"
  if [ -d "$live" ]; then
    rm -rf "$live.old"
    mv "$live" "$live.old"
  fi
  if ! mv "$new" "$live"; then
    echo "atomic replace failed; restoring last-good" >&2
    rm -rf "$live"
    if [ -d "$live.old" ]; then
      mv "$live.old" "$live"
    elif [ -d "$good" ]; then
      cp -a "$good" "$live"
    fi
    exit 1
  fi
  rm -rf "$live.old"
}

publish_landing() {
  local live_root="$1"
  local src_root="$2"
  mkdir -p "$live_root/.last-good"
  for f in "${LANDING_FILES[@]}"; do
    if [ -f "$src_root/$f" ]; then
      [ -f "$live_root/$f" ] && cp -a "$live_root/$f" "$live_root/.last-good/$f" || true
      cp -a "$src_root/$f" "$live_root/$f"
    fi
  done
  if [ -d "$src_root/latest" ]; then
    mkdir -p "$live_root/latest"
    rsync -a "$src_root/latest/" "$live_root/latest/"
  fi
}

refresh_google_sitemaps() {
  # Exception: Google needs hub + issue URLs at the web-root sitemap, not only
  # under /sailing-roundup/. Failure here must never undo a published issue.
  local web_root="$1"
  if [ ! -f "$SITEMAP_WRITER" ]; then
    echo "google sitemap writer missing: $SITEMAP_WRITER" >&2
    return 0
  fi
  python3 "$SITEMAP_WRITER" --web-root "$web_root" || echo "google sitemap refresh failed (issue still published)" >&2
  return 0
}

fix_perms() {
  local live_root="$1"
  local issue="$2"
  if id www-data >/dev/null 2>&1; then
    chown -R www-data:www-data "$live_root/issues/$issue" || true
    for f in "${LANDING_FILES[@]}" latest; do
      [ -e "$live_root/$f" ] && chown -R www-data:www-data "$live_root/$f" || true
    done
  fi
  find "$live_root/issues/$issue" -type d -exec chmod 755 {} \;
  find "$live_root/issues/$issue" -type f -exec chmod 644 {} \;
}

if [ -d /var/www/sailingsa ]; then
  promote_issue "$DEST_DIR" "$SRC/issues/$ISSUE" "$ISSUE"
  publish_landing "$DEST_DIR" "$SRC"
  fix_perms "$DEST_DIR" "$ISSUE"
  refresh_google_sitemaps /var/www/sailingsa
  echo "published local issue $ISSUE -> $DEST_DIR/issues/$ISSUE"
  exit 0
fi

SSH_IDENTITY="${SAILINGSA_SSH_IDENTITY:-}"
if [ -z "$SSH_IDENTITY" ]; then
  if [ -f "${HOME:-/opt/rea}/.ssh/id_rea_publish" ]; then
    SSH_IDENTITY="${HOME:-/opt/rea}/.ssh/id_rea_publish"
  elif [ -f /opt/rea/.ssh/id_rea_publish ]; then
    SSH_IDENTITY=/opt/rea/.ssh/id_rea_publish
  fi
fi
DEST_HOST="${SAILINGSA_SSH_HOST:-root@102.218.215.253}"
SSH_OPTS="-o StrictHostKeyChecking=accept-new -o BatchMode=yes -o IdentitiesOnly=yes -o ConnectTimeout=20"
if [ -n "${SSH_IDENTITY:-}" ] && [ -f "$SSH_IDENTITY" ]; then
  SSH=(ssh -i "$SSH_IDENTITY" $SSH_OPTS)
  RSYNC_RSH="ssh -i $SSH_IDENTITY $SSH_OPTS"
else
  echo "missing publish key; set SAILINGSA_SSH_IDENTITY" >&2
  exit 1
fi

"${SSH[@]}" "$DEST_HOST" "mkdir -p '$DEST_DIR/.stage/issues' '$DEST_DIR/.last-good/issues' '$DEST_DIR/issues'"
rsync -az --delete -e "$RSYNC_RSH" "$SRC/issues/$ISSUE/" "$DEST_HOST:$DEST_DIR/.stage/issues/$ISSUE/"
for f in "${LANDING_FILES[@]}"; do
  if [ -f "$SRC/$f" ]; then
    rsync -az -e "$RSYNC_RSH" "$SRC/$f" "$DEST_HOST:$DEST_DIR/.stage/$f"
  fi
done
if [ -d "$SRC/latest" ]; then
  rsync -az -e "$RSYNC_RSH" "$SRC/latest/" "$DEST_HOST:$DEST_DIR/.stage/latest/"
fi

"${SSH[@]}" "$DEST_HOST" "ISSUE='$ISSUE' DEST_DIR='$DEST_DIR' bash -s" <<'REMOTE'
set -euo pipefail
STAGE="$DEST_DIR/.stage/issues/$ISSUE"
LIVE="$DEST_DIR/issues/$ISSUE"
GOOD="$DEST_DIR/.last-good/issues/$ISSUE"
python3 - "$STAGE" <<'PY'
import sys
from pathlib import Path
stage = Path(sys.argv[1])
for name in ("index.html", "issue.json", "edition.pdf"):
    if not (stage / name).is_file():
        raise SystemExit("missing " + name)
if not (stage / "edition.pdf").read_bytes().startswith(b"%PDF-"):
    raise SystemExit("invalid pdf")
print("stage-valid")
PY
if [ -d "$LIVE" ]; then
  rm -rf "$GOOD"
  mkdir -p "$(dirname "$GOOD")"
  cp -a "$LIVE" "$GOOD"
fi
NEW="$LIVE.new"
rm -rf "$NEW"
cp -a "$STAGE" "$NEW"
if [ -d "$LIVE" ]; then
  rm -rf "$LIVE.old"
  mv "$LIVE" "$LIVE.old"
fi
if ! mv "$NEW" "$LIVE"; then
  echo "atomic replace failed; restoring last-good" >&2
  rm -rf "$LIVE"
  if [ -d "$LIVE.old" ]; then
    mv "$LIVE.old" "$LIVE"
  elif [ -d "$GOOD" ]; then
    cp -a "$GOOD" "$LIVE"
  fi
  exit 1
fi
rm -rf "$LIVE.old"
mkdir -p "$DEST_DIR/.last-good"
for f in index.html latest.json feed.json cards.json; do
  if [ -f "$DEST_DIR/.stage/$f" ]; then
    [ -f "$DEST_DIR/$f" ] && cp -a "$DEST_DIR/$f" "$DEST_DIR/.last-good/$f" || true
    cp -a "$DEST_DIR/.stage/$f" "$DEST_DIR/$f"
  fi
done
if [ -d "$DEST_DIR/.stage/latest" ]; then
  mkdir -p "$DEST_DIR/latest"
  cp -a "$DEST_DIR/.stage/latest/." "$DEST_DIR/latest/"
fi
if id www-data >/dev/null 2>&1; then
  chown -R www-data:www-data "$LIVE" || true
  for f in index.html latest.json feed.json cards.json latest; do
    [ -e "$DEST_DIR/$f" ] && chown -R www-data:www-data "$DEST_DIR/$f" || true
  done
fi
find "$LIVE" -type d -exec chmod 755 {} \;
find "$LIVE" -type f -exec chmod 644 {} \;
echo "published remote issue $ISSUE"
REMOTE

if [ -f "$SITEMAP_WRITER" ]; then
  "${SSH[@]}" "$DEST_HOST" "mkdir -p /tmp/roundup-gsc" || true
  rsync -az -e "$RSYNC_RSH" \
    "$SITEMAP_WRITER" \
    "$HERE/../app/seo_head.py" \
    "$HERE/../app/news_schema.py" \
    "$DEST_HOST:/tmp/roundup-gsc/" || true
  "${SSH[@]}" "$DEST_HOST" "python3 /tmp/roundup-gsc/write_google_sitemaps.py --web-root /var/www/sailingsa" \
    || echo "google sitemap refresh failed (issue still published)" >&2
fi

echo "published $DEST_HOST:$DEST_DIR/issues/$ISSUE"
