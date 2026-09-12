#!/usr/bin/env python3
"""Fast Cape Classic LIVE poll. Uses MM Page token when present, else a cheap scrape.

Live clips are committed with an empty play_url so the card embeds Facebook,
never a saved /assets/adverts/ mp4. When scrape returns no live, existing
lives are marked as reels (was live).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path("/var/www/sailingsa/deploy")))
from mm_fb_fetch_cape import commit_videos, graph_fetch, page_token, probe_live  # noqa: E402


def main() -> int:
    token = page_token()
    if token:
        graphed = graph_fetch(token)
        row = commit_videos(graphed)
        print(
            json.dumps(
                {
                    "ok": True,
                    "source": "graph",
                    "live": [v.get("id") for v in (row.get("videos") or []) if v.get("is_live")],
                }
            )
        )
        return 0
    probed = probe_live()
    if probed is None:
        print(json.dumps({"ok": True, "source": "scrape", "skipped": True}))
        return 0
    row = commit_videos(probed)
    print(
        json.dumps(
            {
                "ok": True,
                "source": "scrape",
                "live": [v.get("id") for v in (row.get("videos") or []) if v.get("is_live")],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
