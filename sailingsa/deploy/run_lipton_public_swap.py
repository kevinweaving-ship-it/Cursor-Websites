#!/usr/bin/env python3
"""Upload Lipton dev assets + run public swap on live server via SSH."""
from __future__ import annotations

import sys
from pathlib import Path

import paramiko

SERVER = "102.218.215.253"
USER = "root"
PASSWORD = "TimAdd#072082"
REPO = Path(__file__).resolve().parents[2]

UPLOADS = [
    (REPO / "sailingsa/frontend/lipton-dev.html", "/var/www/sailingsa/lipton-dev.html"),
    (REPO / "sailingsa/frontend/js/lipton-dev-playback.js", "/var/www/sailingsa/js/lipton-dev-playback.js"),
    (REPO / "sailingsa/frontend/css/lipton-dev.css", "/var/www/sailingsa/css/lipton-dev.css"),
]
for p in (REPO / "sailingsa/frontend/js").glob("lipton-dev-*.json"):
    UPLOADS.append((p, f"/var/www/sailingsa/js/{p.name}"))

REMOTE_SCRIPT = REPO / "sailingsa/deploy/patch_lipton_public_swap.py"


def run_remote(client: paramiko.SSHClient, cmd: str) -> tuple[int, str]:
    _, stdout, stderr = client.exec_command(cmd, timeout=120)
    out = (stdout.read().decode() + stderr.read().decode()).strip()
    code = stdout.channel.recv_exit_status()
    return code, out


def main() -> int:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(SERVER, username=USER, password=PASSWORD, timeout=30)
    sftp = client.open_sftp()

    for local, remote in UPLOADS:
        if not local.is_file():
            print(f"skip missing {local}")
            continue
        tmp = f"/tmp/{local.name}"
        sftp.put(str(local), tmp)
        code, out = run_remote(client, f"chattr -i {remote} 2>/dev/null; cp {tmp} {remote} && wc -c {remote}")
        print(f"upload {local.name} -> {remote}: {out}")

    sftp.put(str(REMOTE_SCRIPT), "/tmp/patch_lipton_public_swap.py")
    code, out = run_remote(client, "python3 /tmp/patch_lipton_public_swap.py")
    print(out)
    if code != 0:
        client.close()
        return code

    verify = r"""
sleep 2
echo '=== VERIFY PUBLIC ==='
curl -sS -D - -o /tmp/vpub.html https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup | head -20
wc -c /tmp/vpub.html
grep -o 'lipton-dev-races\|regatta-page' /tmp/vpub.html | head -3
echo '=== VERIFY DEV ==='
curl -sS -D - -o /tmp/vdev.html https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup-dev | head -15
wc -c /tmp/vdev.html
sleep 5
echo '=== STABILITY CHECK (5s later) ==='
curl -sS -o /tmp/vpub2.html -w 'public_size=%{size_download}\n' https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup
grep -o 'lipton-dev-races\|regatta-page' /tmp/vpub2.html | head -3
pgrep -af 'lw-g' || echo 'no lw-g processes'
"""
    code, out = run_remote(client, verify)
    print(out)
    client.close()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
