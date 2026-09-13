#!/usr/bin/env python3
"""Fast Cape Classic LIVE poll.

Graph first when a Page token exists. If Graph returns no LIVE, Chrome-dump
facebook.com/marin.megastoresa/live in the same tick. Never promote an old
reel: live rows must come from Graph/Chrome as is_live, with empty play_url.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path("/var/www/sailingsa/deploy")))
from mm_fb_fetch_cape import commit_videos, graph_fetch, page_token, probe_live  # noqa: E402


def live_ids(rows: list) -> list:
    return [str(v.get("id") or "") for v in (rows or []) if v.get("is_live") and str(v.get("id") or "").isdigit()]


def main() -> int:
    token = page_token()
    source = "none"
    fetched: list = []
    if token:
        try:
            fetched = graph_fetch(token) or []
            source = "graph"
        except Exception as e:
            print(f"[mm_fb] graph failed: {e}", flush=True)
            fetched = []
    if not live_ids(fetched):
        probed = probe_live()
        if probed:
            live = [v for v in probed if v.get("is_live")]
            rest = [v for v in fetched if not v.get("is_live")]
            fetched = live + rest
            source = "chrome" if token else "scrape"
    row = commit_videos(fetched)
    print(
        json.dumps(
            {
                "ok": True,
                "source": source,
                "live": [v.get("id") for v in (row.get("videos") or []) if v.get("is_live")],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
