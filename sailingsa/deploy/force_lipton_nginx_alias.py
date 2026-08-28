#!/usr/bin/env python3
"""Force Lipton public/-dev nginx locations to alias lipton-dev.html.

Replaces a proxy_pass (old event page) block, not only missing locations.
Never writes backups into sites-enabled (nginx include * would load them).
"""
from pathlib import Path

P = Path("/etc/nginx/sites-enabled/sailingsa")
AVAILABLE = Path("/etc/nginx/sites-available/sailingsa")
GOLD = Path("/root/lipton-nginx-golden.conf")

WANT = [
    "location = /regatta/2026-08-29-lipton-challenge-cup {",
    "location = /regatta/2026-08-29-lipton-challenge-cup/ {",
    "location = /regatta/2026-08-29-lipton-challenge-cup-dev {",
]
BLOCKS = {
    WANT[0]: """    location = /regatta/2026-08-29-lipton-challenge-cup {
        default_type text/html;
        etag off;
        if_modified_since off;
        add_header Cache-Control "no-store, no-cache, must-revalidate, max-age=0" always;
        add_header Pragma "no-cache" always;
        add_header Expires "0" always;
        alias /var/www/sailingsa/lipton-dev.html;
    }
""",
    WANT[1]: """    location = /regatta/2026-08-29-lipton-challenge-cup/ {
        default_type text/html;
        etag off;
        if_modified_since off;
        add_header Cache-Control "no-store, no-cache, must-revalidate, max-age=0" always;
        add_header Pragma "no-cache" always;
        add_header Expires "0" always;
        alias /var/www/sailingsa/lipton-dev.html;
    }
""",
    WANT[2]: """    location = /regatta/2026-08-29-lipton-challenge-cup-dev {
        default_type text/html;
        etag off;
        if_modified_since off;
        add_header Cache-Control "no-store, no-cache, must-revalidate, max-age=0" always;
        add_header Pragma "no-cache" always;
        add_header Expires "0" always;
        add_header X-Robots-Tag "noindex, nofollow";
        alias /var/www/sailingsa/lipton-dev.html;
    }
""",
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


def force_alias(text: str) -> str:
    for w in WANT:
        j = text.find(w)
        if j < 0:
            continue
        line_start = text.rfind("\n", 0, j) + 1
        end = skip_block(text, j)
        text = text[:line_start] + BLOCKS[w] + text[end:]
    missing = [BLOCKS[w] for w in WANT if w not in text]
    if not missing:
        return text
    insert = "".join(missing)
    for a in ("    location = /regatta {", "    location ~ ^/regatta/", "    location /regatta/", "    location / {"):
        if a in text:
            return text.replace(a, insert + a, 1)
    return text


def block_is_alias(text: str, header: str) -> bool:
    j = text.find(header)
    if j < 0:
        return False
    end = skip_block(text, j)
    blk = text[j:end]
    return "alias /var/www/sailingsa/lipton-dev.html" in blk and "proxy_pass" not in blk


def main() -> int:
    text = P.read_text(encoding="utf-8")
    text = force_alias(text)
    P.write_text(text, encoding="utf-8")
    if AVAILABLE.is_file():
        AVAILABLE.write_text(text, encoding="utf-8")
    GOLD.write_text(text, encoding="utf-8")
    for w in WANT:
        ok = block_is_alias(text, w)
        print(w, "alias" if ok else "MISSING_OR_PROXY")
        if not ok:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
