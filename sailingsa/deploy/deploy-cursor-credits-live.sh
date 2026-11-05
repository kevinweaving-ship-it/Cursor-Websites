#!/usr/bin/env bash
# Deploy credits monitor to live and SEND. No Mac. Uses SSH_LIVE.md host.
# Auth: ~/.ssh/sailingsa_live_key, else the same expect-script password fallback.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SERVER="${SAILINGSA_SERVER:-102.218.215.253}"
KEY="${SAILINGSA_SSH_KEY:-$HOME/.ssh/sailingsa_live_key}"
REMOTE_DIR=/usr/local/lib/cursor-credits

ssh_do() {
  if [[ -f "$KEY" ]]; then
    ssh -i "$KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=20 "root@${SERVER}" "$@"
    return
  fi
  python3 - "$SERVER" "$@" <<'PY'
import pexpect, sys
host, *remote = sys.argv[1:]
cmd = " ".join(remote)
child = pexpect.spawn(
    f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=20 root@{host} {cmd}",
    encoding="utf-8", timeout=180)
i = child.expect(["password:", "Password:", pexpect.EOF, pexpect.TIMEOUT])
if i in (0, 1):
    import pathlib, re
    exp = pathlib.Path(__file__).resolve().parents[0]  # unused
    pw = None
    for p in pathlib.Path("sailingsa/deploy").glob("diagnose-server.exp"):
        m = re.search(r'set password "([^"]+)"', p.read_text())
        if m:
            pw = m.group(1)
            break
    if not pw:
        sys.exit("no SSH key and no expect-script password")
    child.sendline(pw)
    child.expect(pexpect.EOF)
print(child.before or "")
if child.exitstatus not in (0, None):
    sys.exit(child.exitstatus or 1)
PY
}

scp_do() {
  local src="$1" dest="$2"
  if [[ -f "$KEY" ]]; then
    scp -i "$KEY" -o StrictHostKeyChecking=no "$src" "root@${SERVER}:$dest"
    return
  fi
  python3 - "$SERVER" "$src" "$dest" <<'PY'
import pexpect, pathlib, re, sys
host, src, dest = sys.argv[1], sys.argv[2], sys.argv[3]
pw = None
for p in pathlib.Path("sailingsa/deploy").glob("diagnose-server.exp"):
    m = re.search(r'set password "([^"]+)"', p.read_text())
    if m:
        pw = m.group(1)
child = pexpect.spawn(
    f"scp -o StrictHostKeyChecking=no {src} root@{host}:{dest}",
    encoding="utf-8", timeout=120)
i = child.expect(["password:", "Password:", pexpect.EOF, pexpect.TIMEOUT])
if i in (0, 1):
    child.sendline(pw)
    child.expect(pexpect.EOF)
print(child.before or "")
PY
}

cd "$ROOT"
echo "Uploading credits monitor to ${SERVER} (SSH_LIVE)"
ssh_do "mkdir -p ${REMOTE_DIR}/docs/audits /var/www/sailingsa/scripts /var/www/sailingsa/docs/audits /var/lib/cursor-credits"
scp_do "$ROOT/sailingsa/scripts/cursor_credits_self_check.py" "${REMOTE_DIR}/cursor_credits_self_check.py"
scp_do "$ROOT/sailingsa/deploy/cursor-credits-dispute-inbound.sh" "${REMOTE_DIR}/dispute-inbound.sh"
scp_do "$ROOT/docs/audits/cursor_credits_audit_2026-10-12.json" "${REMOTE_DIR}/docs/audits/cursor_credits_audit_2026-10-12.json"
scp_do "$ROOT/sailingsa/deploy/install-cursor-credits-mailbox.sh" "/tmp/install-cursor-credits-mailbox.sh"
ssh_do "chmod +x ${REMOTE_DIR}/cursor_credits_self_check.py ${REMOTE_DIR}/dispute-inbound.sh /tmp/install-cursor-credits-mailbox.sh && bash /tmp/install-cursor-credits-mailbox.sh && python3 ${REMOTE_DIR}/cursor_credits_self_check.py email --send"
echo "Live credits monitor installed and first mail sent."
