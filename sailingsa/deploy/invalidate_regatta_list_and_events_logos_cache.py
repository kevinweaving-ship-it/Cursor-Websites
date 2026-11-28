#!/usr/bin/env python3
"""Drop stale landing-list and named-event HTML caches on this API host.

Landing /api/regattas/with-counts keeps a 7-day disk+memory cache. Named-event
detail HTML under /var/tmp/sailingsa_events_logos is served until deleted.
Call this after adding/removing result rows so fleet chips and Live Event
cards refresh. Memory cache still needs an API process restart unless the
live-list count refresh patch is in api.py.
"""
from __future__ import annotations

import os
from pathlib import Path

WITH_COUNTS = Path("/var/tmp/sailingsa_regatta_with_counts.json")
EVENTS_LOGOS_DIR = Path("/var/tmp/sailingsa_events_logos")
CATALOGUE_INDEX = Path("/var/tmp/sailingsa_catalogue_event_index.json")

CAPE_CLASSIC_DETAIL = "detail-zvyc-cape-classic.html"


def invalidate(*, named_event_slug: str = "zvyc-cape-classic") -> list[str]:
    removed: list[str] = []
    for p in (WITH_COUNTS, CATALOGUE_INDEX, WITH_COUNTS.with_suffix(".json.tmp")):
        if p.is_file():
            p.unlink()
            removed.append(str(p))
    extra = WITH_COUNTS.as_posix() + ".tmp"
    if os.path.isfile(extra):
        os.unlink(extra)
        removed.append(extra)
    if EVENTS_LOGOS_DIR.is_dir():
        safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in (named_event_slug or "").strip().lower())[:120]
        targets = [
            EVENTS_LOGOS_DIR / "gallery.html",
            EVENTS_LOGOS_DIR / f"detail-{safe}.html",
            EVENTS_LOGOS_DIR / CAPE_CLASSIC_DETAIL,
        ]
        for p in targets:
            if p.is_file():
                p.unlink()
                removed.append(str(p))
    return removed


if __name__ == "__main__":
    gone = invalidate()
    print("REMOVED", gone or ["(nothing)"])
