#!/bin/bash
# Unlock Gold-locked nginx site files so certbot nginx authenticator can patch/revert.
# Install to: /etc/letsencrypt/renewal-hooks/pre/
set -u
LOG=/var/log/letsencrypt/nginx-lock-hooks.log
mkdir -p /var/log/letsencrypt
echo "$(date -Is) pre unlock start" >>"$LOG"
for f in \
  /etc/nginx/sites-enabled/sailingsa \
  /etc/nginx/sites-available/sailingsa \
  /etc/nginx/sites-enabled/00-timadvisor \
  /etc/nginx/sites-available/00-timadvisor
do
  [ -e "$f" ] || continue
  if lsattr "$f" 2>/dev/null | awk '{print $1}' | grep -q i; then
    chattr -i "$f" && echo "$(date -Is) unlocked $f" >>"$LOG" || echo "$(date -Is) FAIL unlock $f" >>"$LOG"
  else
    echo "$(date -Is) already mutable $f" >>"$LOG"
  fi
done
rm -rf /var/lib/letsencrypt/temp_checkpoint 2>/dev/null || true
echo "$(date -Is) cleared temp_checkpoint" >>"$LOG"
