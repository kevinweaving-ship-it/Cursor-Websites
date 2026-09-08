#!/usr/bin/env python3
"""Remove ← Back to Search from all event /regatta pages. Club pages unchanged."""

from pathlib import Path

LIVE_API = Path("/var/www/sailingsa/api/api.py")
OLD = (
    "        back_link = '' if _is_lipton else "
    "'<a href=\"/\" class=\"back-to-home\">← Back to Search</a>'\n"
)
NEW = "        back_link = ''\n"


def main() -> None:
    text = LIVE_API.read_text(encoding="utf-8")
    if OLD not in text:
        if "back_link = ''\n        is_sa = _session_role_is_super_admin(request)" in text:
            print("already removed")
            return
        raise SystemExit("event back_link assignment not found")
    LIVE_API.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    print("removed Back to Search from event pages")


if __name__ == "__main__":
    main()
