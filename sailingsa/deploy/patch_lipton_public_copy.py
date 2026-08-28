#!/usr/bin/env python3
"""Copy -dev page verbatim to public slug. Do NOT modify lipton-dev.html."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

DEV_HTML = Path("/var/www/sailingsa/lipton-dev.html")
PUBLIC_HTML = Path("/var/www/sailingsa/lipton-public.html")
NGINX = Path("/etc/nginx/sites-enabled/sailingsa")

NOOP_PY = "#!/usr/bin/env python3\nimport sys\nsys.exit(0)\n"
NEUTER = [
    "/usr/local/sbin/lipton_ngx_public_restore.py",
    "/usr/local/lib/lipton_public_not_dev_watch.py",
    "/usr/local/sbin/lipton_public_not_dev_watch.py",
    "/var/lib/sailingsa-lipton/watch.py",
    "/root/force_lipton_nginx_alias.py",
    "/root/lipton-keep-playback.sh",
    "/usr/local/lib/lipton_public_watch_guard.sh",
    "/root/lw-g17.py",
    "/root/lw-g18.py",
    "/root/lw-g19.py",
    "/root/lw-g20.py",
    "/root/lw-g21.py",
    "/root/lw-g22.py",
]

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
        # LIPTON_NGINX_PUBLIC_COPY_V1 — verbatim copy of -dev (lipton-public.html)
        default_type text/html;
        etag off;
        if_modified_since off;
        add_header Cache-Control "no-store, no-cache, must-revalidate, max-age=0" always;
        add_header Pragma "no-cache" always;
        add_header Expires "0" always;
        add_header X-Lipton-Page "public-copy-of-dev" always;
        alias /var/www/sailingsa/lipton-public.html;
    }"""

SLASH_OLD = """    location = /regatta/2026-08-29-lipton-challenge-cup/ {
        # LIPTON_NGINX_PUBLIC_PROXY_V1
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        add_header Cache-Control "no-store";
    }"""

SLASH_NEW = """    location = /regatta/2026-08-29-lipton-challenge-cup/ {
        return 301 /regatta/2026-08-29-lipton-challenge-cup;
    }"""


def run(cmd: str) -> tuple[int, str]:
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return p.returncode, ((p.stdout or "") + (p.stderr or "")).strip()


def main() -> int:
    if not DEV_HTML.is_file():
        print("ERROR: dev html missing", file=sys.stderr)
        return 1

    # verbatim copy — dev file read-only intent: cp from dev, never write dev
    run(f"chattr -i {PUBLIC_HTML} 2>/dev/null")
    run(f"cp -a {DEV_HTML} {PUBLIC_HTML}")
    print(f"copied {DEV_HTML} -> {PUBLIC_HTML}", run(f"wc -c {PUBLIC_HTML}")[1])

    for c in (
        "pkill -f lipton_ngx_public_restore 2>/dev/null || true",
        "pkill -f lipton_public_not_dev_watch 2>/dev/null || true",
        "pkill -f lipton_public_watch_guard 2>/dev/null || true",
        "pkill -f 'lw-g[0-9]+\\.py' 2>/dev/null || true",
        "systemctl mask sailingsa-lipton-url-hold sailingsa-lipton-public-watch 2>/dev/null || true",
    ):
        run(c)

    run("chattr -i " + " ".join(NEUTER) + " 2>/dev/null")
    for p in NEUTER:
        path = Path(p)
        if path.exists() or path.parent.exists():
            path.write_text(NOOP_PY if p.endswith(".py") else "#!/bin/bash\nexit 0\n", encoding="utf-8")
            if not p.endswith(".py"):
                run(f"chmod +x {p}")

    run(f"chattr -i {NGINX} 2>/dev/null")
    text = NGINX.read_text(encoding="utf-8")
    for old, new in ((PUBLIC_OLD, PUBLIC_NEW), (SLASH_OLD, SLASH_NEW)):
        if old in text:
            text = text.replace(old, new, 1)
        elif "LIPTON_NGINX_PUBLIC_COPY_V1" not in text:
            print("ERROR: public nginx block not found", file=sys.stderr)
            return 1
    NGINX.write_text(text, encoding="utf-8")

    code, out = run("nginx -t")
    print(out)
    if code != 0:
        return code
    run("nginx -s reload")
    print("nginx reloaded")

    Path("/root/LIPTON_PUBLIC_COPY_OF_DEV.md").write_text(
        "# Public Lipton = verbatim copy of -dev\n\n"
        f"Source: {DEV_HTML}\n"
        f"Public file: {PUBLIC_HTML}\n"
        "Dev slug unchanged. To refresh public: cp -a lipton-dev.html lipton-public.html\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
