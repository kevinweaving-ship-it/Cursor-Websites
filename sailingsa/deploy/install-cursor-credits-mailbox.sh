#!/usr/bin/env bash
# Install cursor@sailingsa.co.za on Mac Mini OR the live box, plus daily mailer.
# Live:  ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 'bash -s' < sailingsa/deploy/install-cursor-credits-mailbox.sh
# Mac:   bash sailingsa/deploy/install-cursor-credits-mailbox.sh
set -euo pipefail

FROM_ADDR="${CURSOR_MAIL_FROM:-cursor@sailingsa.co.za}"
CC_ADDR="${CURSOR_MAIL_CC:-kevinweaving@icloud.com}"
LOCAL_USER="${CURSOR_MAIL_LOCAL:-cursor}"

SCRIPT_SRC=""
if [[ -f "${1:-}" ]]; then
  SCRIPT_SRC="$1"
elif [[ -f "$(dirname "$0")/../../scripts/cursor_credits_self_check.py" ]]; then
  SCRIPT_SRC="$(cd "$(dirname "$0")/../.." && pwd)/scripts/cursor_credits_self_check.py"
elif [[ -f /var/www/sailingsa/scripts/cursor_credits_self_check.py ]]; then
  SCRIPT_SRC=/var/www/sailingsa/scripts/cursor_credits_self_check.py
fi

echo "Installing mailbox $FROM_ADDR (inbound → $CC_ADDR)"

if command -v postfix >/dev/null 2>&1 || [[ -d /etc/postfix ]]; then
  if [[ "$(uname -s)" == "Linux" ]]; then
    if ! id -u "$LOCAL_USER" >/dev/null 2>&1; then
      useradd -r -m -s /usr/sbin/nologin "$LOCAL_USER" || true
    fi
  fi
  ALIASES=/etc/aliases
  touch "$ALIASES"
  if ! grep -qE "^${LOCAL_USER}:" "$ALIASES"; then
    echo "${LOCAL_USER}: ${CC_ADDR}" >> "$ALIASES"
  fi
  if command -v newaliases >/dev/null 2>&1; then
    newaliases || true
  fi
  VIRTUAL=/etc/postfix/virtual
  touch "$VIRTUAL"
  if ! grep -qE "^${FROM_ADDR}" "$VIRTUAL"; then
    echo "${FROM_ADDR} ${LOCAL_USER}" >> "$VIRTUAL"
  fi
  if command -v postmap >/dev/null 2>&1; then
    postmap "$VIRTUAL" || true
  fi
  if [[ -f /etc/postfix/main.cf ]] && ! grep -q "virtual_alias_maps" /etc/postfix/main.cf; then
    echo "virtual_alias_maps = hash:/etc/postfix/virtual" >> /etc/postfix/main.cf
  fi
  if command -v postfix >/dev/null 2>&1; then
    postfix reload || true
  fi
  echo "postfix alias installed: $FROM_ADDR → $CC_ADDR"
else
  echo "postfix not found — outbound still works if SMTP_HOST is set."
  echo "Create the $FROM_ADDR alias on the mail host that serves sailingsa.co.za."
fi

install -d -m 0755 /var/lib/cursor-credits /usr/local/lib/cursor-credits
if [[ -n "$SCRIPT_SRC" && -f "$SCRIPT_SRC" ]]; then
  install -m 0755 "$SCRIPT_SRC" /usr/local/lib/cursor-credits/cursor_credits_self_check.py
  SNAP_DIR="$(cd "$(dirname "$SCRIPT_SRC")/.." && pwd)/docs/audits"
  if [[ -d "$SNAP_DIR" ]]; then
    mkdir -p /usr/local/lib/cursor-credits/docs/audits
    cp -f "$SNAP_DIR"/cursor_credits_audit_*.json /usr/local/lib/cursor-credits/docs/audits/ 2>/dev/null || true
  fi
fi

# Daily 06:20 — keep mailing Cursor until credits are marked resolved.
CRON_FILE=/etc/cron.d/cursor-credits-self-check
if [[ -w /etc/cron.d || "$(id -u)" -eq 0 ]]; then
  cat > "$CRON_FILE" <<'CRON'
# Cursor credits self-check — email hi@cursor.com, CC Kevin, until resolved.
MAILTO=kevinweaving@icloud.com
20 6 * * * root SMTP_HOST=localhost CURSOR_MAIL_FROM=cursor@sailingsa.co.za CURSOR_MAIL_CC=kevinweaving@icloud.com /usr/bin/python3 /usr/local/lib/cursor-credits/cursor_credits_self_check.py email --send >> /var/log/cursor-credits-mail.log 2>&1
CRON
  chmod 644 "$CRON_FILE"
  echo "cron installed: $CRON_FILE (daily 06:20, stops only after resolve)"
else
  echo "Not root — add this cron yourself:"
  echo "20 6 * * * python3 $SCRIPT_SRC email --send"
fi

echo "Done. Test: python3 /usr/local/lib/cursor-credits/cursor_credits_self_check.py audit"
echo "Send:  python3 /usr/local/lib/cursor-credits/cursor_credits_self_check.py email --send"
echo "Stop:  python3 /usr/local/lib/cursor-credits/cursor_credits_self_check.py resolve"
