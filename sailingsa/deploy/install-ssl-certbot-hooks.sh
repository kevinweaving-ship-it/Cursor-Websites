#!/usr/bin/env bash
# Install certbot nginx Gold-lock unlock/lock hooks + SSL expiry cron on live.
# Run ON the live server as root (or via SSH from Mac):
#   bash sailingsa/deploy/install-ssl-certbot-hooks.sh
#
# Why: nginx sites-enabled/sailingsa is chattr +i. Certbot's nginx plugin must
# temporarily edit that file to renew. Without pre/post hooks, renew fails and
# Safari eventually shows "This Connection Is Not Private".
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
PRE_SRC="$ROOT/certbot-hooks/pre/unlock-nginx-for-certbot.sh"
POST_SRC="$ROOT/certbot-hooks/post/lock-nginx-after-certbot.sh"
CHECK_SRC="$ROOT/scripts/sailingsa-ssl-expiry-check"

if [[ ! -f "$PRE_SRC" || ! -f "$POST_SRC" ]]; then
  echo "Missing hook sources under $ROOT/certbot-hooks/" >&2
  exit 1
fi

install -d -m 755 /etc/letsencrypt/renewal-hooks/pre /etc/letsencrypt/renewal-hooks/post
install -m 755 "$PRE_SRC" /etc/letsencrypt/renewal-hooks/pre/unlock-nginx-for-certbot.sh
install -m 755 "$POST_SRC" /etc/letsencrypt/renewal-hooks/post/lock-nginx-after-certbot.sh

if [[ -f "$CHECK_SRC" ]]; then
  install -m 755 "$CHECK_SRC" /usr/local/sbin/sailingsa-ssl-expiry-check
fi

cat > /etc/cron.d/sailingsa_ssl_expiry <<'EOF'
# TLS cert expiry guard — WhatsApp via server monitor if WARNING (<21d) or CRITICAL (<7d).
CRON_TZ=Africa/Johannesburg
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
TZ=Africa/Johannesburg
15 9 * * * root /usr/local/sbin/sailingsa-server-monitor --check-ssl >> /var/log/sailingsa-ssl-expiry.log 2>&1
EOF
chmod 644 /etc/cron.d/sailingsa_ssl_expiry

# Re-apply Gold lock if unlocked
for f in \
  /etc/nginx/sites-enabled/sailingsa \
  /etc/nginx/sites-available/sailingsa \
  /etc/nginx/sites-enabled/00-timadvisor \
  /etc/nginx/sites-available/00-timadvisor
do
  [[ -e "$f" ]] || continue
  chattr +i "$f" 2>/dev/null || true
done

echo "Installed certbot nginx lock hooks + SSL expiry cron."
echo "Verify: certbot renew --dry-run --non-interactive --no-random-sleep-on-renew"
echo "Verify: /usr/local/sbin/sailingsa-ssl-expiry-check"
echo "Verify: lsattr /etc/nginx/sites-enabled/sailingsa   # expect immutable 'i'"
