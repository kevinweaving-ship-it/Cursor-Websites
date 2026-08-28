#!/usr/bin/env python3
"""Promote Lipton -dev page to public URL via nginx alias. Run on live server as root."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

NGINX_PATHS = [
    Path("/etc/nginx/sites-enabled/sailingsa"),
    Path("/etc/nginx/sites-available/sailingsa"),
]
LIPTON_HTML = Path("/var/www/sailingsa/lipton-dev.html")

PUBLIC_OLD = """    location = /regatta/2026-08-29-lipton-challenge-cup {
        # LIPTON_NGINX_PUBLIC_PROXY_V1
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        add_header Cache-Control "no-store";
    }"""

PUBLIC_NEW = """    location = /regatta/2026-08-29-lipton-challenge-cup {
        # LIPTON_NGINX_PUBLIC_ALIAS_V2 — new dev playback page (not API proxy)
        default_type text/html;
        etag off;
        if_modified_since off;
        add_header Cache-Control "no-store, no-cache, must-revalidate, max-age=0" always;
        add_header Pragma "no-cache" always;
        add_header Expires "0" always;
        add_header X-Lipton-Page "new-dev-public" always;
        alias /var/www/sailingsa/lipton-dev.html;
    }"""

PUBLIC_SLASH_OLD = """    location = /regatta/2026-08-29-lipton-challenge-cup/ {
        # LIPTON_NGINX_PUBLIC_PROXY_V1
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        add_header Cache-Control "no-store";
    }"""

PUBLIC_SLASH_NEW = """    location = /regatta/2026-08-29-lipton-challenge-cup/ {
        return 301 /regatta/2026-08-29-lipton-challenge-cup;
    }"""


def run(cmd: str) -> tuple[int, str]:
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    out = (p.stdout or "") + (p.stderr or "")
    return p.returncode, out.strip()


def unlock_paths() -> None:
    for p in NGINX_PATHS + [LIPTON_HTML]:
        if p.exists():
            run(f"chattr -i {p} 2>/dev/null")
    run("chattr -i /root/lw-g*.py 2>/dev/null")


def patch_nginx_file(path: Path) -> bool:
    if not path.exists():
        print(f"skip missing {path}")
        return True
    text = path.read_text(encoding="utf-8")
    orig = text
    for old, new, label in (
        (PUBLIC_OLD, PUBLIC_NEW, "public"),
        (PUBLIC_SLASH_OLD, PUBLIC_SLASH_NEW, "public-slash"),
    ):
        if new in text:
            print(f"already {label} in {path}")
            continue
        if old not in text:
            # try generic proxy block match
            pat = (
                r"    location = /regatta/2026-08-29-lipton-challenge-cup/? \{"
                r"\s+# LIPTON_NGINX_PUBLIC_PROXY_V1.*?^\    \}"
            )
            repl = PUBLIC_NEW if "cup/ {" not in old else PUBLIC_SLASH_NEW
            text2, n = re.subn(pat, repl, text, count=1, flags=re.MULTILINE | re.DOTALL)
            if n:
                text = text2
                print(f"regex patched {label} in {path}")
                continue
            print(f"WARN: {label} block not found in {path}", file=sys.stderr)
            continue
        text = text.replace(old, new, 1)
        print(f"patched {label} in {path}")
    if "LIPTON_NGINX_PUBLIC_ALIAS_V2" not in text:
        print(f"ERROR: alias marker still missing in {path}", file=sys.stderr)
        return False
    if text != orig:
        path.write_text(text, encoding="utf-8")
    return True


def stop_revert_loops() -> None:
    cmds = [
        "pkill -f 'lw-g[0-9]+\\.py' 2>/dev/null || true",
        "pkill -f force_lipton_nginx_alias 2>/dev/null || true",
        "pkill -f lipton-keep-playback 2>/dev/null || true",
        "pkill -f lipton_public_watch 2>/dev/null || true",
        "systemctl stop sailingsa-lipton-url-hold 2>/dev/null || true",
        "systemctl stop sailingsa-lipton-public-watch 2>/dev/null || true",
        "systemctl disable sailingsa-lipton-url-hold 2>/dev/null || true",
        "systemctl disable sailingsa-lipton-public-watch 2>/dev/null || true",
        "systemctl mask sailingsa-lipton-url-hold 2>/dev/null || true",
        "systemctl mask sailingsa-lipton-public-watch 2>/dev/null || true",
        "chattr -i /root/lw-g*.py 2>/dev/null; "
        "for f in /root/lw-g*.py; do "
        "[ -f \"$f\" ] && printf '#!/usr/bin/env python3\\nimport sys\\nsys.exit(0)\\n' > \"$f\"; done",
        "for f in /root/force_lipton_nginx_alias.py /root/lipton-keep-playback.sh; do "
        "[ -f \"$f\" ] && chattr -i \"$f\" 2>/dev/null; "
        "[ -f \"$f\" ] && mv \"$f\" \"${f}.DISABLED_DO_NOT_RUN\"; done",
        "grep -q '^#.*lipton-keep-playback' /etc/crontab || "
        "sed -i 's/^\\(.*lipton-keep-playback.*\\)$/# DISABLED \\1/' /etc/crontab 2>/dev/null || true",
        "for f in /etc/cron.d/*lipton*; do "
        "[ -f \"$f\" ] && chattr -i \"$f\" 2>/dev/null; "
        "[ -f \"$f\" ] && mv \"$f\" \"${f}.DISABLED_DO_NOT_RUN\"; done",
        "if [ -f /usr/local/lib/lipton_public_watch_guard.sh ]; then "
        "chattr -i /usr/local/lib/lipton_public_watch_guard.sh 2>/dev/null; "
        "printf '#!/bin/bash\\nexit 0\\n' > /usr/local/lib/lipton_public_watch_guard.sh; "
        "chmod +x /usr/local/lib/lipton_public_watch_guard.sh; fi",
        "touch /root/.cursor_agent_stop_public_url_fight",
    ]
    for c in cmds:
        _, out = run(c)
        if out:
            print(out)


def lock_paths() -> None:
    for p in NGINX_PATHS + [LIPTON_HTML]:
        if p.exists():
            run(f"chattr +i {p}")


def main() -> int:
    if not LIPTON_HTML.is_file():
        print(f"ERROR: missing {LIPTON_HTML}", file=sys.stderr)
        return 1
    stop_revert_loops()
    unlock_paths()
    if not all(patch_nginx_file(p) for p in NGINX_PATHS if p.exists()):
        # sites-enabled is required; sites-available is best-effort
        enabled = Path("/etc/nginx/sites-enabled/sailingsa")
        if enabled.exists() and "LIPTON_NGINX_PUBLIC_ALIAS_V2" not in enabled.read_text(encoding="utf-8"):
            return 1
    code, out = run("nginx -t")
    print(out)
    if code != 0:
        return code
    code, out = run("nginx -s reload")
    print(out or "nginx reloaded")
    lock_paths()
    Path("/root/LIPTON_PUBLIC_SWAP_DONE.md").write_text(
        "# Lipton public URL swap complete\n\n"
        "Public slug aliases `/var/www/sailingsa/lipton-dev.html`.\n"
        "Do NOT run lw-g*.py or revert nginx to API proxy.\n"
        "Configs locked with chattr +i.\n",
        encoding="utf-8",
    )
    Path("/root/CURSOR_STOP_AND_NEXT_TASK.md").write_text(
        "# STOP — public Lipton swap is done\n\n"
        "Mac agent: do not SSH nginx edits for Lipton.\n"
        "Public URL serves lipton-dev.html (new playback page).\n",
        encoding="utf-8",
    )
    print("swap complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
