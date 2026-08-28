#!/usr/bin/env python3
"""Start-line catchup only. Writes /js/lipton-dev-live-history.json. Does not serve live GPS."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lipton_dev_live import HISTORY_PATHS, live_snapshot  # noqa: E402

OUT = Path("/var/www/sailingsa/js/lipton-dev-live-history.json")


def main() -> int:
    data = live_snapshot(history=True)
    text = json.dumps(data, separators=(",", ":"), default=str)
    for p in (OUT,) + HISTORY_PATHS:
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            tmp = p.with_name(p.name + ".tmp")
            tmp.write_text(text, encoding="utf-8")
            tmp.replace(p)
        except OSError:
            continue
    boats = data.get("boats") or {}
    gun = data.get("gun_ts_ms")
    from_gun = 0
    span = 0
    if gun:
        for b in boats.values():
            t = (b or {}).get("trail") or []
            if t and int(t[0].get("ts_ms") or 0) <= int(gun) + 15_000:
                from_gun += 1
            if len(t) >= 2:
                span = max(span, int(t[-1].get("ts_ms") or 0) - int(t[0].get("ts_ms") or 0))
    print(
        f"catchup ok boats={len(boats)} from_gun={from_gun} "
        f"span_s={span/1000:.0f} gun={gun} ocs={data.get('ocs')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
