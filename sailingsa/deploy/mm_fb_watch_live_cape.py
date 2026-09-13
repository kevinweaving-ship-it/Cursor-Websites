#!/usr/bin/env python3
"""Fast Cape Classic LIVE poll.

Graph first. If no LIVE, Chrome-dump /live. A new /videos/{id}/ that is not
already a stored reel is either LIVE (own card) or the broadcast that just
ended (newest reel). Never promote an old reel id.
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
    graph_ok = bool(token)
    try:
        from mm_fb_graph_live import read_status

        st = read_status() or {}
        if st.get("needs_login") or (st.get("page") or {}).get("error_code") == 190:
            graph_ok = False
    except Exception:
        pass
    if graph_ok:
        try:
            fetched = graph_fetch(token) or []
            source = "graph"
        except Exception as e:
            print(f"[mm_fb] graph failed: {e}", flush=True)
            fetched = []
    if graph_ok and not live_ids(fetched):
        try:
            from mm_fb_graph_live import keep_tokens, page_token as live_page_token

            st = keep_tokens(force=False)
            if st.get("action") == "minted":
                token = live_page_token() or token
                fetched = graph_fetch(token) or []
                source = "graph"
        except Exception as e:
            print(f"[mm_fb] keep_tokens: {e}", flush=True)
    if not live_ids(fetched):
        probed = probe_live() or []
        if probed:
            fetched = probed + [v for v in fetched if str(v.get("id") or "") not in {str(x.get("id") or "") for x in probed}]
            source = "chrome" if token else "scrape"
    row = commit_videos(fetched)
    print(
        json.dumps(
            {
                "ok": True,
                "source": source,
                "live": [v.get("id") for v in (row.get("videos") or []) if v.get("is_live")],
                "new_reels": [
                    v.get("id")
                    for v in (row.get("videos") or [])
                    if not v.get("is_live") and str(v.get("id") or "").isdigit()
                ][:3],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
