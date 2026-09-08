#!/usr/bin/env python3
"""Remove the invented 2026-only handler so /regatta/{slug} serves it like every other event."""

from pathlib import Path

LIVE_API = Path("/var/www/sailingsa/api/api.py")
START = '@app.get("/regatta/2026-09-13-zvyc-cape-classic")'
END = '@app.get("/regatta/{slug}")'


def main() -> None:
    text = LIVE_API.read_text(encoding="utf-8")
    start = text.find(START)
    end = text.find(END)
    if start < 0:
        print("no special route; already standard")
        return
    if end < 0 or end <= start:
        raise SystemExit("generic /regatta/{slug} not found")
    LIVE_API.write_text(text[:start] + text[end:], encoding="utf-8")
    print("removed special route")


if __name__ == "__main__":
    main()
