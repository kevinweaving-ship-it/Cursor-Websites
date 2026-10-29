#!/usr/bin/env bash
# Surgical live apply: robots Allow for OG/logo + official Googlebot IP allow/rate-limit skip.
# Does NOT overwrite /var/www/sailingsa/api/api.py. Traffic-card patch is a separate script.
set -euo pipefail

SITE="${SITE:-/etc/nginx/sites-enabled/sailingsa}"
ABUSE_DST="/etc/nginx/conf.d/sailingsa-abuse.conf"
CIDR_DST="/etc/nginx/conf.d/googlebot-cidrs.inc"
ALLOW_DST="/etc/nginx/snippets/sailingsa-googlebot-allow.conf"
ROBOTS_DST="/var/www/sailingsa/robots.txt"
TS="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="${BACKUP_DIR:-/root/backups}"

mkdir -p "$BACKUP_DIR"
cp -a "$SITE" "$BACKUP_DIR/nginx-sailingsa.${TS}"
cp -a "$ABUSE_DST" "$BACKUP_DIR/sailingsa-abuse.${TS}" 2>/dev/null || true
cp -a "$ROBOTS_DST" "$BACKUP_DIR/robots.${TS}"

if [[ -z "${ABUSE_SRC:-}" || -z "${CIDR_SRC:-}" || -z "${ALLOW_SRC:-}" || -z "${ROBOTS_SRC:-}" ]]; then
  echo "Set ABUSE_SRC CIDR_SRC ALLOW_SRC ROBOTS_SRC" >&2
  exit 1
fi

cp "$ABUSE_SRC" "$ABUSE_DST"
cp "$CIDR_SRC" "$CIDR_DST"
cp "$ALLOW_SRC" "$ALLOW_DST"
cp "$ROBOTS_SRC" "$ROBOTS_DST"
chown www-data:www-data "$ROBOTS_DST" || true

chattr -i "$SITE" || true
if ! grep -q 'sailingsa-googlebot-allow.conf' "$SITE"; then
  sed -i 's|include /etc/nginx/snippets/sailingsa-swarm-deny.conf;|include /etc/nginx/snippets/sailingsa-googlebot-allow.conf;\n    include /etc/nginx/snippets/sailingsa-swarm-deny.conf;|g' "$SITE"
fi
chattr +i "$SITE" || true

nginx -t
systemctl reload nginx
echo "GOOGLEBOT_ALLOW_NGINX_OK backup=$BACKUP_DIR robots=$(wc -c < "$ROBOTS_DST")"
