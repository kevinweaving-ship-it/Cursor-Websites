#!/usr/bin/env python3
"""No-store Lipton playback JS so browsers cannot keep the RCYC/RCYCA OCS mix-up."""
from pathlib import Path

CANDIDATES = [
    Path("/etc/nginx/sites-enabled/sailingsa"),
    Path("/etc/nginx/sites-available/sailingsa"),
]
SNIPPET = """    location = /js/lipton-dev-playback.js {
        add_header Cache-Control "no-store, must-revalidate";
        etag off;
        alias /var/www/sailingsa/js/lipton-dev-playback.js;
    }
    location = /js/lipton-dev-playback-dk.js {
        add_header Cache-Control "no-store, must-revalidate";
        alias /var/www/sailingsa/js/lipton-dev-playback-dk.js;
    }
"""


def main() -> int:
    conf = next((p for p in CANDIDATES if p.is_file()), None)
    if conf is None:
        print("ERROR: nginx conf not found")
        return 1
    text = conf.read_text(encoding="utf-8")
    if "lipton-dev-playback-dk.js" in text:
        print("nginx js no-store present")
        return 0
    key = "location = /regatta/2026-08-29-lipton-challenge-cup-dev {"
    if key not in text:
        print("ERROR: lock snippet missing")
        return 1
    text = text.replace(key, SNIPPET + "    " + key, 1)
    conf.write_text(text, encoding="utf-8")
    print("patched nginx js no-store", conf)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
