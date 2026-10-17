#!/usr/bin/env python3
"""Remove public Lipton nginx aliases (keep -dev). Handles PLAYBACK_LOCK re-inserts."""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

MARKER = "LIPTON_NGINX_PUBLIC_NOT_DEV_V2"
NGINX_PATH = Path(sys.argv[1] if len(sys.argv) > 1 else "/etc/nginx/sites-enabled/sailingsa")

PUB_ALIAS = re.compile(
    r"\n    location = /regatta/2026-08-29-lipton-challenge-cup(?:/)? \{\n"
    r"        default_type text/html;\n"
    r"        add_header Cache-Control \"no-store\";\n"
    r"        alias /var/www/sailingsa/lipton-dev.html;\n"
    r"    \}",
)

PLAYBACK_LOCK = "# LIPTON_NGINX_PLAYBACK_LOCK public + -dev slugs serve lipton-dev.html (not API event page)."
PUBLIC_KEEP = "# LIPTON_NGINX_PUBLIC_NOT_DEV_V2 public slug MUST proxy to the API live board.\n    # Only -dev may alias lipton-dev.html. Do not add a public-slug alias."


def main() -> int:
    text = NGINX_PATH.read_text(encoding="utf-8")
    new, n = PUB_ALIAS.subn("", text)
    if PLAYBACK_LOCK in new:
        new = new.replace(PLAYBACK_LOCK, PUBLIC_KEEP)
    elif MARKER not in new:
        new = new.replace(
            "# LIPTON_NGINX_PUBLIC_NOT_DEV_V1 public slug uses location / → API live board.",
            PUBLIC_KEEP,
        )
        if MARKER not in new:
            # insert before -dev location
            needle = "    location = /regatta/2026-08-29-lipton-challenge-cup-dev {"
            if needle in new:
                new = new.replace(needle, "    " + PUBLIC_KEEP.split("\n", 1)[0] + "\n" + needle, 1)
    if n == 0 and MARKER in text and "location = /regatta/2026-08-29-lipton-challenge-cup {" not in text:
        print("already", MARKER)
        print("ok", NGINX_PATH)
        return 0
    if n == 0 and "location = /regatta/2026-08-29-lipton-challenge-cup {" in text:
        print("FAIL public alias present but regex missed", file=sys.stderr)
        return 1
    tmp = Path("/tmp") / (NGINX_PATH.name + ".liptonpubv2")
    tmp.write_text(new, encoding="utf-8")
    rc = os.system(f"cp {tmp} {NGINX_PATH}")
    if rc != 0:
        print("FAIL cp", rc, file=sys.stderr)
        return 1
    print("patched", MARKER, "removed", n)
    print("ok", NGINX_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
