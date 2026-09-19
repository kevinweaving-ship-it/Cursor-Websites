#!/usr/bin/env python3
"""List Midmar public media in display order (newest first after pin)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, "/var/www/sailingsa")
from sailingsa.backend import mm_event_clips as mm

RID = "2026-09-19-hmyc-midmar-cup"
STATIC = Path("/var/www/sailingsa")
payload = mm.public_payload(RID, STATIC)
videos = payload.get("videos") or []
print("PUBLIC_N", len(videos))
for i, v in enumerate(videos[:8]):
    print(
        f"{i:02d} id={v.get('id')} kind={v.get('kind')} pin={v.get('pinned')} "
        f"at={v.get('started_at')} title={v.get('title')!r} "
        f"w={v.get('width')} h={v.get('height')} play={v.get('play_url')}"
    )
