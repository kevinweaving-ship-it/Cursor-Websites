#!/usr/bin/env python3
"""Public Lipton URL = playback file. -old = API event page.

The live fight is /etc/nginx/snippets/lipton-public-proxy.conf which
proxies the public slug to FastAPI's old weather page.
"""
from pathlib import Path

ENABLED = Path("/etc/nginx/sites-enabled/sailingsa")
AVAILABLE = Path("/etc/nginx/sites-available/sailingsa")
SNIP = Path("/etc/nginx/snippets/lipton-public-proxy.conf")
GOLD = Path("/root/lipton-nginx-golden.conf")

SNIP_TEXT = """    location = /regatta/2026-08-29-lipton-challenge-cup {
        default_type text/html;
        add_header Cache-Control "no-store, no-cache, must-revalidate, max-age=0" always;
        rewrite ^ /lipton-dev.html last;
    }
    location = /regatta/2026-08-29-lipton-challenge-cup/ {
        default_type text/html;
        add_header Cache-Control "no-store, no-cache, must-revalidate, max-age=0" always;
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

INCLUDE = "    include /etc/nginx/snippets/lipton-public-proxy.conf;"


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


def strip_headers(text: str, headers: list[str]) -> str:
    for header in headers:
        while True:
            j = text.find(header)
            if j < 0:
                break
            line_start = text.rfind("\n", 0, j) + 1
            end = skip_block(text, j)
            text = text[:line_start] + text[end:]
    return text


def main() -> int:
    SNIP.parent.mkdir(parents=True, exist_ok=True)
    SNIP.write_text(SNIP_TEXT, encoding="utf-8")

    text = ENABLED.read_text(encoding="utf-8")
    # Public slug must live in the snippet only — strip duplicates from the site conf.
    text = strip_headers(
        text,
        [
            "location = /regatta/2026-08-29-lipton-challenge-cup {",
            "location = /regatta/2026-08-29-lipton-challenge-cup/ {",
        ],
    )
    if INCLUDE not in text:
        for a in ("    location = /regatta {", "    location / {"):
            if a in text:
                text = text.replace(a, INCLUDE + "\n" + a, 1)
                break
    if "location = /regatta/2026-08-29-lipton-challenge-cup-old {" not in text:
        text = text.replace(INCLUDE, INCLUDE + "\n" + OLD, 1)
        if "location = /regatta/2026-08-29-lipton-challenge-cup-old {" not in text:
            for a in ("    location = /regatta {", "    location / {"):
                if a in text:
                    text = text.replace(a, OLD + a, 1)
                    break

    ENABLED.write_text(text, encoding="utf-8")
    if AVAILABLE.is_file():
        AVAILABLE.write_text(text, encoding="utf-8")
    GOLD.write_text(text, encoding="utf-8")
    print("snippet_playback", "rewrite ^ /lipton-dev.html last" in SNIP.read_text())
    print("snippet_no_proxy", "proxy_pass" not in SNIP.read_text())
    print("old_in_site", "lipton-challenge-cup-old" in text)
    print("include", INCLUDE.strip() in text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
