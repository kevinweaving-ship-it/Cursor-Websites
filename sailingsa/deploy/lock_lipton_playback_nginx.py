#!/usr/bin/env python3
"""Lock Lipton public/-dev URLs to lipton-dev.html in nginx. Does not replace api.py."""
from __future__ import annotations

import re
import sys
from pathlib import Path

MARKER = "location = /regatta/2026-08-29-lipton-challenge-cup"
SNIPPET = """    location = /regatta/2026-08-29-lipton-challenge-cup {
        default_type text/html;
        add_header Cache-Control "no-store";
        alias /var/www/sailingsa/lipton-dev.html;
    }
    location = /regatta/2026-08-29-lipton-challenge-cup/ {
        default_type text/html;
        add_header Cache-Control "no-store";
        alias /var/www/sailingsa/lipton-dev.html;
    }
    location = /regatta/2026-08-29-lipton-challenge-cup-dev {
        default_type text/html;
        add_header Cache-Control "no-store";
        add_header X-Robots-Tag "noindex, nofollow";
        alias /var/www/sailingsa/lipton-dev.html;
    }

"""

CANDIDATES = [
    Path("/etc/nginx/sites-enabled/sailingsa"),
    Path("/etc/nginx/sites-available/sailingsa"),
    Path("/etc/nginx/sites-enabled/sailingsa.co.za"),
    Path("/etc/nginx/sites-available/sailingsa.co.za"),
    Path("/etc/nginx/conf.d/sailingsa.conf"),
]


def _find_conf() -> Path:
    for p in CANDIDATES:
        if p.is_file() and "server_name" in p.read_text(encoding="utf-8", errors="ignore"):
            txt = p.read_text(encoding="utf-8", errors="ignore")
            if "sailingsa" in txt and ("regatta" in txt or "proxy_pass" in txt):
                return p
    enabled = Path("/etc/nginx/sites-enabled")
    if enabled.is_dir():
        for p in sorted(enabled.iterdir()):
            if not p.is_file():
                continue
            txt = p.read_text(encoding="utf-8", errors="ignore")
            if "sailingsa.co.za" in txt:
                return p
    raise SystemExit("ERROR: nginx sailingsa site conf not found")


def main() -> int:
    conf = _find_conf()
    text = conf.read_text(encoding="utf-8")
    if MARKER in text:
        print("nginx lock already present", conf)
        return 0
    m = re.search(r"\n    location = /regatta \{", text)
    if not m:
        m = re.search(r"\n    location ~ \^/regatta/", text)
    if not m:
        m = re.search(r"\n    location /regatta/", text)
    if not m:
        m = re.search(r"\nlocation / \{", text)
    if not m:
        print("ERROR: no /regatta/ location to insert before", file=sys.stderr)
        return 1
    text = text[: m.start() + 1] + SNIPPET + text[m.start() + 1 :]
    bak = conf.with_suffix(conf.suffix + ".bak_lipton_lock")
    bak.write_text(conf.read_text(encoding="utf-8"), encoding="utf-8")
    conf.write_text(text, encoding="utf-8")
    print("patched nginx", conf)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
