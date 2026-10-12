#!/usr/bin/env bash
# Live box only. Install cursor@sailingsa.co.za, start local mail, cron, FIRST SEND.
# No Mac. Called by deploy-cursor-credits-live.py (SSH_LIVE.md).
set -euo pipefail

FROM_ADDR="${CURSOR_MAIL_FROM:-cursor@sailingsa.co.za}"
CC_ADDR="${CURSOR_MAIL_CC:-kevinweaving@icloud.com}"
LOCAL_USER="${CURSOR_MAIL_LOCAL:-cursor}"
LIB=/usr/local/lib/cursor-credits

echo "Installing $FROM_ADDR on $(hostname) (auto-send, no Mac)"

if [[ "$(id -u)" -eq 0 ]] && [[ "$(uname -s)" == "Linux" ]]; then
  if ! command -v postfix >/dev/null 2>&1; then
    echo "postfix missing — installing (box mail)"
    export DEBIAN_FRONTEND=noninteractive
    echo "postfix postfix/main_mailer_type select Internet Site" | debconf-set-selections
    echo "postfix postfix/mailname string sailingsa.co.za" | debconf-set-selections
    apt-get update -qq
    apt-get install -y -qq postfix mailutils
  fi
  systemctl enable postfix >/dev/null 2>&1 || true
  systemctl start postfix || service postfix start || true
  if ! id -u "$LOCAL_USER" >/dev/null 2>&1; then
    useradd -r -m -s /usr/sbin/nologin "$LOCAL_USER" || true
  fi
fi

install -d -m 0755 /var/lib/cursor-credits "$LIB/docs/audits"
if [[ -f "$LIB/cursor_credits_self_check.py" ]]; then
  chmod +x "$LIB/cursor_credits_self_check.py"
fi
if [[ -f "$LIB/dispute-inbound.sh" ]]; then
  chmod +x "$LIB/dispute-inbound.sh"
fi

if [[ -d /etc/postfix ]] || command -v postfix >/dev/null 2>&1; then
  touch /etc/aliases
  PIPE="$LIB/dispute-inbound.sh"
  ALIAS_LINE="${LOCAL_USER}: ${CC_ADDR}, \"|${PIPE}\""
  if grep -qE "^${LOCAL_USER}:" /etc/aliases; then
    sed -i.bak -E "s|^${LOCAL_USER}:.*|${ALIAS_LINE}|" /etc/aliases
  else
    echo "$ALIAS_LINE" >> /etc/aliases
  fi
  command -v newaliases >/dev/null 2>&1 && newaliases || true
  touch /etc/postfix/virtual
  if ! grep -qE "^${FROM_ADDR}" /etc/postfix/virtual; then
    echo "${FROM_ADDR} ${LOCAL_USER}" >> /etc/postfix/virtual
  fi
  command -v postmap >/dev/null 2>&1 && postmap /etc/postfix/virtual || true
  if [[ -f /etc/postfix/main.cf ]]; then
    postconf -e "myhostname = sailingsa.co.za" || true
    postconf -e "myorigin = sailingsa.co.za" || true
    grep -q "virtual_alias_maps" /etc/postfix/main.cf || \
      echo "virtual_alias_maps = hash:/etc/postfix/virtual" >> /etc/postfix/main.cf
  fi
  postfix reload || systemctl reload postfix || true
  echo "mailbox ready: $FROM_ADDR → $CC_ADDR + auto-dispute pipe"
fi

rm -f /etc/cron.d/cursor-credits-self-check
echo "no daily outbound cron — wait; inbound pipe replies only on rejection"

echo "install finished (no extra send)"
