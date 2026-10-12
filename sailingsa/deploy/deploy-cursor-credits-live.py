#!/usr/bin/env python3
"""Install credits monitor on live (SSH_LIVE.md) and send the first mail. No Mac."""

from __future__ import annotations

import pathlib
import re
import sys

import pexpect

ROOT = pathlib.Path(__file__).resolve().parents[2]
SERVER = "102.218.215.253"
KEY = pathlib.Path.home() / ".ssh/sailingsa_live_key"
REMOTE = "/usr/local/lib/cursor-credits"


def _password() -> str:
    text = (ROOT / "sailingsa/deploy/diagnose-server.exp").read_text()
    m = re.search(r'set password "([^"]+)"', text)
    if not m:
        sys.exit("SSH_LIVE fallback password not found in diagnose-server.exp")
    return m.group(1)


def _ssh(args: list[str], timeout: int) -> pexpect.spawn:
    child = pexpect.spawn("/usr/bin/ssh", args, encoding="utf-8", timeout=timeout)
    i = child.expect(["password:", "Password:", pexpect.EOF, pexpect.TIMEOUT])
    if i in (0, 1):
        child.sendline(_password())
    return child


def run(cmd: str, timeout: int = 180) -> str:
    args = ["-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=20"]
    if KEY.is_file():
        args = ["-i", str(KEY), *args]
    args += [f"root@{SERVER}", cmd]
    child = _ssh(args, timeout)
    if "password:" not in str(child.after).lower() and child.after is not pexpect.TIMEOUT:
        pass
    child.expect(pexpect.EOF)
    return child.before or ""


def upload(local: pathlib.Path, remote: str) -> None:
    src = str(local)
    if KEY.is_file():
        child = pexpect.spawn(
            f"scp -i {KEY} -o StrictHostKeyChecking=no {src} root@{SERVER}:{remote}",
            encoding="utf-8",
            timeout=120,
        )
        child.expect(pexpect.EOF)
        return
    child = pexpect.spawn(
        f"scp -o StrictHostKeyChecking=no {src} root@{SERVER}:{remote}",
        encoding="utf-8",
        timeout=120,
    )
    i = child.expect(["password:", "Password:", pexpect.EOF, pexpect.TIMEOUT])
    if i in (0, 1):
        child.sendline(_password())
        child.expect(pexpect.EOF)


def main() -> int:
    print(f"SSH_LIVE deploy credits monitor → root@{SERVER}")
    files = [
        (ROOT / "sailingsa/scripts/cursor_credits_self_check.py", f"{REMOTE}/cursor_credits_self_check.py"),
        (ROOT / "sailingsa/deploy/cursor-credits-dispute-inbound.sh", f"{REMOTE}/dispute-inbound.sh"),
        (ROOT / "docs/audits/cursor_credits_audit_2026-10-12.json", f"{REMOTE}/docs/audits/cursor_credits_audit_2026-10-12.json"),
        (ROOT / "sailingsa/deploy/install-cursor-credits-mailbox.sh", "/tmp/install-cursor-credits-mailbox.sh"),
    ]
    print(run(f"mkdir -p {REMOTE}/docs/audits /var/www/sailingsa/scripts /var/www/sailingsa/docs/audits /var/lib/cursor-credits"))
    for src, dest in files:
        print(f"upload {src.name}")
        upload(src, dest)
    out = run(
        "chmod +x /usr/local/lib/cursor-credits/cursor_credits_self_check.py "
        "/usr/local/lib/cursor-credits/dispute-inbound.sh "
        "/tmp/install-cursor-credits-mailbox.sh && "
        "bash /tmp/install-cursor-credits-mailbox.sh",
        timeout=420,
    )
    print(out)
    print("done: live install + first send")
    return 0


if __name__ == "__main__":
    sys.exit(main())
