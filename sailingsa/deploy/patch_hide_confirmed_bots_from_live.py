#!/usr/bin/env python3
"""Once bot confirmed on Live: quarantine and hide from Live list (offline audit only)."""
from __future__ import annotations

import py_compile
import shutil
from datetime import datetime, timezone
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")


def main() -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    shutil.copy2(API, API.with_suffix(f".bak-hide-live-bots-{stamp}"))
    text = API.read_text(encoding="utf-8")
    orig = text

    old = '''                if r.get("kind") == "bot" and ip_r:
                    try:
                        _lean_quarantine_ip(cur, ip_r, "live_bot")
                    except Exception:
                        pass
                filtered.append(r)
'''
    new = '''                # Confirmed bot → quarantine and remove from Live (audit via Done/offline)
                if r.get("kind") == "bot":
                    if ip_r:
                        try:
                            _lean_quarantine_ip(cur, ip_r, "live_bot")
                        except Exception:
                            pass
                    continue
                if ip_r:
                    try:
                        if _lean_ip_is_quarantined(cur, ip_r):
                            continue
                    except Exception:
                        pass
                filtered.append(r)
'''
    if old not in text:
        raise SystemExit("live bot append block not found")
    text = text.replace(old, new, 1)

    # UI note on Live section if present
    old_note = "▶ shows URL trail + dwell."
    if old_note in text and "Confirmed bots are hidden" not in text:
        text = text.replace(
            old_note,
            "▶ shows URL trail + dwell. Confirmed bots are hidden from Live (see Done/offline).",
            1,
        )

    if text == orig:
        raise SystemExit("no changes")
    API.write_text(text, encoding="utf-8")
    py_compile.compile(str(API), doraise=True)
    print(f"OK hide live bots (+{len(text) - len(orig)} bytes)")


if __name__ == "__main__":
    main()
