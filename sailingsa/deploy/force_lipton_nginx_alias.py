#!/usr/bin/env python3
"""Public Lipton URL internally rewrites to lipton-dev.html. -old proxies to API."""
from pathlib import Path

P = Path("/etc/nginx/sites-enabled/sailingsa")
AVAILABLE = Path("/etc/nginx/sites-available/sailingsa")
GOLD = Path("/root/lipton-nginx-golden.conf")

PUBLIC = """    location = /regatta/2026-08-29-lipton-challenge-cup {
        default_type text/html;
        add_header Cache-Control "no-store, no-cache, must-revalidate, max-age=0" always;
        rewrite ^ /lipton-dev.html last;
    }
"""
TRAIL = """    location = /regatta/2026-08-29-lipton-challenge-cup/ {
        default_type text/html;
        add_header Cache-Control "no-store, no-cache, must-revalidate, max-age=0" always;
        rewrite ^ /lipton-dev.html last;
    }
"""
DEV = """    location = /regatta/2026-08-29-lipton-challenge-cup-dev {
        default_type text/html;
        add_header Cache-Control "no-store, no-cache, must-revalidate, max-age=0" always;
        add_header X-Robots-Tag "noindex, nofollow";
        rewrite ^ /lipton-dev.html last;
    }
"""
OLD = """    location = /regatta/2026-08-29-lipton-challenge-cup-old {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
"""

BLOCKS = {
    "location = /regatta/2026-08-29-lipton-challenge-cup {": PUBLIC,
    "location = /regatta/2026-08-29-lipton-challenge-cup/ {": TRAIL,
    "location = /regatta/2026-08-29-lipton-challenge-cup-dev {": DEV,
    "location = /regatta/2026-08-29-lipton-challenge-cup-old {": OLD,
}


def skip_block(text: str, j: int) -> int:
    brace = text.find("{", j)
    depth = 0
    k = brace
    while k < len(text):
        if text[k] == "{":
            depth += 1
        elif text[k] == "}":
            depth -= 1
            if depth == 0:
                k += 1
                if k < len(text) and text[k] == "\n":
                    k += 1
                return k
        k += 1
    return k


def replace_or_insert(text: str) -> str:
    for header, block in BLOCKS.items():
        j = text.find(header)
        if j >= 0:
            line_start = text.rfind("\n", 0, j) + 1
            end = skip_block(text, j)
            text = text[:line_start] + block + text[end:]
            continue
        insert_at = None
        for a in ("    location = /regatta {", "    location / {"):
            k = text.find(a)
            if k >= 0:
                insert_at = k
                break
        if insert_at is None:
            raise SystemExit("no insert point for " + header)
        text = text[:insert_at] + block + text[insert_at:]
    return text


def main() -> int:
    text = replace_or_insert(P.read_text(encoding="utf-8"))
    P.write_text(text, encoding="utf-8")
    if AVAILABLE.is_file():
        AVAILABLE.write_text(text, encoding="utf-8")
    GOLD.write_text(text, encoding="utf-8")
    pub = "rewrite ^ /lipton-dev.html last" in text
    old = "location = /regatta/2026-08-29-lipton-challenge-cup-old {" in text
    print("public_rewrite", pub, "old_location", old)
    return 0 if pub and old else 1


if __name__ == "__main__":
    raise SystemExit(main())
