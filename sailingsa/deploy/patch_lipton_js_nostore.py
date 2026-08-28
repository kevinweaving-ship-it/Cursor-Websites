#!/usr/bin/env python3
"""No-store Lipton playback JS so browsers cannot keep a stale cache filename."""
from pathlib import Path

CANDIDATES = [
    Path("/etc/nginx/sites-enabled/sailingsa"),
    Path("/etc/nginx/sites-available/sailingsa"),
]
FILES = (
    "lipton-dev-playback.js",
    "lipton-dev-playback-dk.js",
    "lipton-dev-playback-dl.js",
    "lipton-dev-playback-dm.js",
)
ANCHOR = "location = /regatta/2026-08-29-lipton-challenge-cup-dev {"


def loc_block(name: str) -> str:
    extra = "        etag off;\n" if name == "lipton-dev-playback.js" else ""
    return (
        f"    location = /js/{name} {{\n"
        f"        add_header Cache-Control \"no-store, must-revalidate\";\n"
        f"{extra}"
        f"        alias /var/www/sailingsa/js/{name};\n"
        f"    }}\n"
    )


def main() -> int:
    conf = next((p for p in CANDIDATES if p.is_file()), None)
    if conf is None:
        print("ERROR: nginx conf not found")
        return 1
    text = conf.read_text(encoding="utf-8")
    missing = [n for n in FILES if f"location = /js/{n} {{" not in text]
    if not missing:
        print("nginx js no-store present")
        return 0
    if ANCHOR not in text:
        print("ERROR: lock snippet missing")
        return 1
    insert = "".join(loc_block(n) for n in missing)
    text = text.replace(ANCHOR, insert + "    " + ANCHOR, 1)
    conf.write_text(text, encoding="utf-8")
    print("patched nginx js no-store", conf, "added", ",".join(missing))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
