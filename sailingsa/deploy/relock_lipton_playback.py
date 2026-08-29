#!/usr/bin/env python3
"""Force Lipton public slug onto lipton-dev.html in EVERY sailingsa nginx server."""
from __future__ import annotations

from pathlib import Path

SLUG = "2026-08-29-lipton-challenge-cup"
BLOCK = f"""    location = /regatta/{SLUG} {{
        default_type text/html;
        add_header Cache-Control "no-store";
        alias /var/www/sailingsa/lipton-dev.html;
    }}
    location = /regatta/{SLUG}/ {{
        default_type text/html;
        add_header Cache-Control "no-store";
        alias /var/www/sailingsa/lipton-dev.html;
    }}
    location = /regatta/{SLUG}-dev {{
        default_type text/html;
        add_header Cache-Control "no-store";
        add_header X-Robots-Tag "noindex, nofollow";
        alias /var/www/sailingsa/lipton-dev.html;
    }}
"""
NEEDLE = f"location = /regatta/{SLUG} {{"
ROOTS = [
    Path("/etc/nginx/sites-enabled"),
    Path("/etc/nginx/sites-available"),
    Path("/etc/nginx/conf.d"),
]


def _files() -> list[Path]:
    out: list[Path] = []
    for root in ROOTS:
        if not root.is_dir():
            continue
        for p in sorted(root.iterdir()):
            if p.is_file():
                out.append(p)
    return out


def _inject(text: str) -> tuple[str, bool]:
    if NEEDLE in text:
        return text, False
    keys = [
        "    location ~ ^/regatta/",
        "    location /regatta/",
        "    location = /regatta {",
        "    location / {",
    ]
    for key in keys:
        if key in text:
            return text.replace(key, BLOCK + key, 1), True
    return text, False


def main() -> int:
    changed = []
    scanned = []
    for p in _files():
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if "sailingsa" not in text.lower() and "regatta" not in text:
            continue
        scanned.append(str(p))
        new, did = _inject(text)
        if did:
            p.write_text(new, encoding="utf-8")
            changed.append(str(p))
    print("scanned", len(scanned), "changed", changed or "none")
    if not changed and not any(NEEDLE in Path(s).read_text(encoding="utf-8", errors="ignore") for s in scanned):
        print("ERROR: lock not present and not inserted")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
