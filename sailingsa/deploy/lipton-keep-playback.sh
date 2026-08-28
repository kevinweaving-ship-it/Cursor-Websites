#!/bin/bash
# Public Lipton URL must stay playback. Old weather page is -old only.
set -euo pipefail
pkill -f lipton_public_watch_guard 2>/dev/null || true
pkill -f lipton_public_not_dev_watch.py 2>/dev/null || true
SNIP=/etc/nginx/snippets/lipton-public-proxy.conf
CONF=/etc/nginx/sites-enabled/sailingsa
if test -f "$SNIP" && grep -q proxy_pass "$SNIP"; then
  chattr -i "$CONF" "$SNIP" 2>/dev/null || true
  python3 /root/force_lipton_nginx_alias.py
  nginx -t && nginx -s reload
  chattr +i "$CONF" "$SNIP" 2>/dev/null || true
  echo "$(date -Is) snippet was proxy; restored playback rewrite" >> /root/lipton-keep-playback.log
fi
if grep -q LIPTON_PUBLIC_NOT_DEV /var/www/sailingsa/api/api.py 2>/dev/null; then
  python3 /root/patch_lipton_public_slug.py && systemctl restart sailingsa-api || true
  echo "$(date -Is) stripped PUBLIC_NOT_DEV hijack" >> /root/lipton-keep-playback.log
fi
