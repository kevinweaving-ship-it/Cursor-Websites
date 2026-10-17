#!/usr/bin/env python3
"""Remove nginx exact-match aliases that serve lipton-dev.html for the PUBLIC Lipton URL."""
from __future__ import annotations

import os
import sys
from pathlib import Path

MARKER = "LIPTON_NGINX_PUBLIC_NOT_DEV_V1"
NGINX_PATH = Path(sys.argv[1] if len(sys.argv) > 1 else "/etc/nginx/sites-enabled/sailingsa")

OLD = '''    location = /regatta/2026-08-29-lipton-challenge-cup {
        default_type text/html;
        add_header Cache-Control "no-store";
        alias /var/www/sailingsa/lipton-dev.html;
    }
    location = /regatta/2026-08-29-lipton-challenge-cup/ {
        default_type text/html;
        add_header Cache-Control "no-store";
        alias /var/www/sailingsa/lipton-dev.html;
    }
'''

NEW = '''    # LIPTON_NGINX_PUBLIC_NOT_DEV_V1 public slug uses location / → API live board.
'''


def main() -> int:
    text = NGINX_PATH.read_text(encoding="utf-8")
    if MARKER in text:
        print("already", MARKER)
        print("ok", NGINX_PATH)
        return 0
    n = text.count(OLD)
    if n != 1:
        print(f"FAIL nginx public-not-dev: found {n}", file=sys.stderr)
        return 1
    tmp = Path("/tmp") / (NGINX_PATH.name + ".liptonpub")
    tmp.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    rc = os.system(f"cp {tmp} {NGINX_PATH}")
    if rc != 0:
        print("FAIL cp", rc, file=sys.stderr)
        return 1
    print("patched", MARKER)
    print("ok", NGINX_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
