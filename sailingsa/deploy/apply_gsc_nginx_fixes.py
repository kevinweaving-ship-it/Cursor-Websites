#!/usr/bin/env python3
"""Idempotent nginx patch for Search Console crawl errors.

Reads a sailingsa site file on stdin, writes the patched file to stdout.

Live nginx serves `/etc/nginx/sites-enabled/sailingsa` (not a symlink). That
file is `chattr +i` — clear the immutable bit before replacing it.

Apply with: python3 apply_gsc_nginx_fixes.py < site.conf > site.conf.new

- Split https://www.sailingsa.co.za onto its own 443 server (301 to apex).
- Apex 443 server_name is sailingsa.co.za only (port 80 left as-is if it already 301s).
- /home and /home/ 301 to https://sailingsa.co.za/
- Empty /regatta/class/podium/podium.html?regatta_id= 301 to /events
"""
from __future__ import annotations

import re
import sys

WWW_MARKER = "# GSC: www → apex (single 301). Applied by apply_gsc_nginx_fixes.py"
WWW_SERVER = f"""
{WWW_MARKER}
server {{
    listen 443 ssl;
    server_name www.sailingsa.co.za;
    ssl_certificate /etc/letsencrypt/live/sailingsa.co.za/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/sailingsa.co.za/privkey.pem;
    return 301 https://sailingsa.co.za$request_uri;
}}

"""

SERVER_443_BOTH = re.compile(
    r"server \{\n"
    r"(?:    listen \[::\]:443 ssl;\n)?"
    r"    listen 443 ssl;"
    r"(?:\n    listen \[::\]:443 ssl;)?"
    r"\n    server_name sailingsa\.co\.za www\.sailingsa\.co\.za;"
)

HOME_TRY = re.compile(
    r"    location = /home \{\n"
    r"(?:        [^\n]+\n)*?"
    r"        try_files /home\.html =404;\n"
    r"    \}\n"
)

HOME_301 = """    location = /home {
        return 301 https://sailingsa.co.za/$is_args$args;
    }
    location = /home/ {
        return 301 https://sailingsa.co.za/$is_args$args;
    }
"""

PODIUM = """    location = /regatta/class/podium/podium.html {
        if ($arg_regatta_id = "") {
            return 301 https://sailingsa.co.za/events;
        }
        try_files $uri @api;
    }
"""


def _has_www_redirect_server(text: str) -> bool:
    return WWW_MARKER in text or bool(
        re.search(
            r"server_name\s+www\.sailingsa\.co\.za\s*;\s*\n(?:[^\n]*\n){0,12}\s*return 301 https://sailingsa\.co\.za\$request_uri;",
            text,
        )
    )


def ensure_www_443(text: str) -> str:
    match = SERVER_443_BOTH.search(text)
    if match and not _has_www_redirect_server(text):
        text = text[: match.start()] + WWW_SERVER + text[match.start() :]
        match = SERVER_443_BOTH.search(text)
    if match:
        replaced = match.group(0).replace(
            "server_name sailingsa.co.za www.sailingsa.co.za;",
            "server_name sailingsa.co.za;",
            1,
        )
        text = text[: match.start()] + replaced + text[match.end() :]
    return text


def ensure_home_301(text: str) -> str:
    if re.search(r"location = /home \{\n\s+return 301", text):
        if "location = /home/" not in text:
            text = re.sub(
                r"(    location = /home \{\n        return 301[^\n]+\n    \}\n)",
                r"\1    location = /home/ {\n        return 301 https://sailingsa.co.za/$is_args$args;\n    }\n",
                text,
                count=1,
            )
        return text
    if HOME_TRY.search(text):
        return HOME_TRY.sub(HOME_301 + "\n", text, count=1)
    if "location = /home" in text:
        return text
    anchor = re.search(r"\n    location ~ \^/sailor/", text) or re.search(
        r"\n    location ~ \^/regatta/", text
    ) or re.search(r"\nlocation / \{", text) or re.search(r"\n    location / \{", text)
    if not anchor:
        raise SystemExit("could not find insertion point for /home")
    return text[: anchor.start()] + "\n" + HOME_301 + text[anchor.start() :]


def ensure_empty_podium(text: str) -> str:
    if "location = /regatta/class/podium/podium.html" in text:
        return text
    after = re.search(r"    location = /regatta/class/class-results.html \{[^}]+\}\n", text)
    if after:
        return text[: after.end()] + "\n" + PODIUM + text[after.end() :]
    before = re.search(r"\nlocation / \{", text) or re.search(r"\n    location / \{", text)
    if not before:
        raise SystemExit("could not find insertion point for empty podium")
    return text[: before.start()] + "\n" + PODIUM + text[before.start() :]


def patch(text: str) -> str:
    if "sailingsa.co.za" not in text:
        raise SystemExit("input is not a sailingsa nginx site file")
    text = ensure_www_443(text)
    text = ensure_home_301(text)
    text = ensure_empty_podium(text)
    return text


def main() -> None:
    sys.stdout.write(patch(sys.stdin.read()))


if __name__ == "__main__":
    main()
