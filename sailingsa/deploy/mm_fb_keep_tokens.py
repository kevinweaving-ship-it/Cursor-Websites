#!/usr/bin/env python3
"""systemd entry: keep Marine Megastore Facebook Page token without Graph Explorer."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mm_fb_graph_live import keep_tokens  # noqa: E402


def main() -> int:
    force = "--force" in sys.argv
    status = keep_tokens(force=force)
    print(
        json.dumps(
            {
                "ok": status.get("ok"),
                "needs_login": status.get("needs_login"),
                "action": status.get("action"),
                "connect": status.get("connect"),
                "page_never_expires": (status.get("page") or {}).get("never_expires"),
                "user_valid": (status.get("user") or {}).get("is_valid"),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
