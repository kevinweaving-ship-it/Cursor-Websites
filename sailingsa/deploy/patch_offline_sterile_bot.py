#!/usr/bin/env python3
"""Wire sterile bot into offline classifier (combined if)."""
from __future__ import annotations

import py_compile
import shutil
from datetime import datetime, timezone
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")


def main() -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    shutil.copy2(API, API.with_suffix(f".bak-sterile-off-{stamp}"))
    text = API.read_text(encoding="utf-8")
    orig = text
    old = '''                ) and (
                    _is_sailor_sas_id_path(path)
                    or _lean_behavior_confident_bot(trail, path, ip)
                    or _lean_same_page_swarm_bot(cur, ip=ip, path=path, page_trail=trail, window_minutes=30)
                ):
                    is_bot = True
                else:
                    # cloud single-page no engage → bot
                    try:
                        if (not is_staff) and len(trail) <= 2 and not _lean_trail_has_engagement(trail):
                            if _lean_ip_is_cloud_datacenter(ip):
                                is_bot = True
                    except Exception:
                        pass
'''
    new = '''                ) and (
                    _is_sailor_sas_id_path(path)
                    or _lean_behavior_confident_bot(trail, path, ip)
                    or _lean_same_page_swarm_bot(cur, ip=ip, path=path, page_trail=trail, window_minutes=30)
                    or _lean_sterile_short_trail_bot(trail, path, ip or "")
                ):
                    is_bot = True
                    if ip and _lean_sterile_short_trail_bot(trail, path, ip or ""):
                        try:
                            reason = (
                                "cloud_sterile_short"
                                if _lean_ip_is_cloud_datacenter(ip)
                                else "sterile_single_page"
                            )
                            _lean_quarantine_ip(cur, ip, reason)
                        except Exception:
                            pass
                else:
                    # cloud single-page no engage → bot
                    try:
                        if (not is_staff) and len(trail) <= 2 and not _lean_trail_has_engagement(trail):
                            if _lean_ip_is_cloud_datacenter(ip):
                                is_bot = True
                    except Exception:
                        pass
'''
    if old not in text:
        raise SystemExit("offline combined block not found")
    text = text.replace(old, new, 1)
    API.write_text(text, encoding="utf-8")
    py_compile.compile(str(API), doraise=True)
    print(f"OK offline sterile (+{len(text)-len(orig)})")


if __name__ == "__main__":
    main()
