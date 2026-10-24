#!/usr/bin/env python3
"""Idempotent nginx patch for Search Console crawl errors.

Reads a sailingsa site file on stdin, writes the patched file to stdout.

Apply with: python3 apply_gsc_nginx_fixes.py < site.conf > site.conf.new

- Split https://www.sailingsa.co.za onto its own 443 server (301 to apex).
- Apex 443 server_name is sailingsa.co.za only.
- /home and /home/ 301 to https://sailingsa.co.za/
- Empty /regatta/class/podium/podium.html?regatta_id= 301 to /events
"""
from __future__ import annotations

import re
import sys

WWW_SERVER = """
# GSC: www → apex (single 301). Applied by apply-gsc-nginx-fixes.py
server {
    listen [::]:443 ssl;
    listen 443 ssl;
    server_name www.sailingsa.co.za;
    ssl_certificate /etc/letsencrypt/live/sailingsa.co.za/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/sailingsa.co.za/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
    return 301 https://sailingsa.co.za$request_uri;
}

"""

HOME_PODIUM = """
    # GSC: /home is a duplicate of /
    location = /home {
        return 301 https://sailingsa.co.za/$is_args$args;
    }
    location = /home/ {
        return 301 https://sailingsa.co.za/$is_args$args;
    }
    # GSC: empty podium query is a soft-404
    location = /regatta/class/podium/podium.html {
        if ($arg_regatta_id = "") {
            return 301 https://sailingsa.co.za/events;
        }
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
"""


def _has_www_redirect_server(text: str) -> bool:
    return bool(
        re.search(
            r"server_name\s+www\.sailingsa\.co\.za\s*;\s*\n(?:[^\n]*\n){0,12}\s*return 301 https://sailingsa\.co\.za\$request_uri;",
            text,
        )
    )


def _strip_www_from_apex_server_name(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        names = match.group(2).split()
        if names == ["www.sailingsa.co.za"]:
            return match.group(0)
        if "www.sailingsa.co.za" not in names:
            return match.group(0)
        parts = [p for p in names if p != "www.sailingsa.co.za"]
        if "sailingsa.co.za" not in parts:
            parts.insert(0, "sailingsa.co.za")
        return f"{match.group(1)}{' '.join(parts)};"

    return re.sub(
        r"(server_name\s+)([^;]*sailingsa\.co\.za[^;]*);",
        repl,
        text,
    )


def _insert_www_server(text: str) -> str:
    if _has_www_redirect_server(text):
        return text
    # Prefer immediately before the first 443 sailingsa server.
    match = re.search(
        r"(# SailingSA[^\n]*\n)?server \{[^{}]*server_name\s+(?:sailingsa\.co\.za|www\.sailingsa\.co\.za)",
        text,
    )
    if match:
        return text[: match.start()] + WWW_SERVER + text[match.start() :]
    # Fallback: prepend.
    return WWW_SERVER + text


def _insert_home_podium(text: str) -> str:
    if "location = /home" in text and "location = /regatta/class/podium/podium.html" in text:
        # Refresh the empty-podium block if an older /home-only snippet is present.
        if "$arg_regatta_id" in text:
            return text
    if "location = /home {" not in text:
        anchor = re.search(r"\n    location ~ \^/sailor/", text)
        if not anchor:
            anchor = re.search(r"\n    location ~ \^/regatta/", text)
        if not anchor:
            anchor = re.search(r"\n    location / \{", text)
        if anchor:
            text = text[: anchor.start()] + "\n" + HOME_PODIUM + text[anchor.start() :]
        else:
            text = text.replace("\n}", "\n" + HOME_PODIUM + "\n}", 1)
    elif "location = /regatta/class/podium/podium.html" not in text:
        home_end = re.search(r"location = /home/ \{[^}]+\}", text)
        insert_at = home_end.end() if home_end else text.find("location = /home {")
        if insert_at == -1:
            text += HOME_PODIUM
        else:
            podium_only = "\n".join(HOME_PODIUM.splitlines()[7:]) + "\n"
            text = text[:insert_at] + "\n" + podium_only + text[insert_at:]
    return text


def patch(text: str) -> str:
    if "sailingsa.co.za" not in text:
        raise SystemExit("input is not a sailingsa nginx site file")
    text = _insert_www_server(text)
    text = _strip_www_from_apex_server_name(text)
    text = _insert_home_podium(text)
    return text


def main() -> None:
    sys.stdout.write(patch(sys.stdin.read()))


if __name__ == "__main__":
    main()
