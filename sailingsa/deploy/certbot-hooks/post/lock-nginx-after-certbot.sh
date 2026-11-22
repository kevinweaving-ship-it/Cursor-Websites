#!/bin/bash
# Restore Gold-lock immutable bit after certbot finishes.
# Install to: /etc/letsencrypt/renewal-hooks/post/
set -u
LOG=/var/log/letsencrypt/nginx-lock-hooks.log
mkdir -p /var/log/letsencrypt
echo "$(date -Is) post lock start" >>"$LOG"
for f in \
  /etc/nginx/sites-enabled/sailingsa \
  /etc/nginx/sites-available/sailingsa \
  /etc/nginx/sites-enabled/00-timadvisor \
  /etc/nginx/sites-available/00-timadvisor
do
  [ -e "$f" ] || continue
  chattr +i "$f" 2>/dev/null && echo "$(date -Is) locked $f" >>"$LOG" || echo "$(date -Is) FAIL lock $f" >>"$LOG"
done
if nginx -t >>"$LOG" 2>&1; then
  systemctl reload nginx >>"$LOG" 2>&1 || true
  echo "$(date -Is) nginx reloaded" >>"$LOG"
else
  echo "$(date -Is) nginx -t FAILED — not reloading" >>"$LOG"
fi
