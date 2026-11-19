#!/usr/bin/env python3
"""Patch live api.py: real Chrome/Safari phone/PC/tablet on valid URLs pass as traffic.

- Do not quarantine / label bot when UA is a real browser on a trackable page path.
- Cloud IP alone is not enough to mark bot if human-browser signals are present.
- Safe to re-run (idempotent markers).
"""
from __future__ import annotations

import pathlib
import re
import sys

API = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")
text = API.read_text(encoding="utf-8")
orig = text

HELPER = '''
def _is_human_browser_ua(user_agent: str) -> bool:
    """True for Chrome/Safari/Firefox/Edge on phone / tablet / laptop / PC.

    Used to let likely-real visitors pass even when IP is in a cloud range.
    """
    ua = user_agent or ""
    low = ua.lower().strip()
    if not low or low == "mozilla/5.0":
        return False
    if _is_bot_user_agent(ua):
        return False
    if "mozilla/" not in low:
        return False
    has_browser = any(
        tok in low
        for tok in (
            "chrome/",
            "crios/",
            "firefox/",
            "fxios/",
            "safari/",
            "edg/",
            "edgios/",
            "edga/",
        )
    )
    if not has_browser:
        return False
    # Safari desktop has Version/ + Safari/ without Chrome; mobile has iPhone/iPad/Android.
    is_phone_or_tablet = any(
        tok in low for tok in ("iphone", "ipad", "ipod", "android", "mobile", "tablet")
    )
    is_laptop_or_pc = any(
        tok in low
        for tok in ("windows nt", "macintosh", "mac os x", "cros", "linux x86_64", "x11")
    )
    return bool(is_phone_or_tablet or is_laptop_or_pc)


def _lean_human_traffic_pass(user_agent: str, path: Optional[str] = None) -> bool:
    """Valid clickable page + real browser UA => treat as real traffic (not bot)."""
    if not _is_human_browser_ua(user_agent):
        return False
    if path is None or path == "":
        return True
    try:
        return bool(_is_trackable_page_path(path))
    except Exception:
        p = (path or "").split("?", 1)[0]
        return p.startswith("/") and not p.startswith("/api/") and not p.startswith("/wp-")

'''

MARKER = "def _is_human_browser_ua(user_agent: str) -> bool:"
if MARKER not in text:
    # Insert after _is_bot_user_agent block
    m = re.search(
        r"(def _is_bot_user_agent\(user_agent: str\) -> bool:.*?return any\(.*?\)\n\s*\)\n)",
        text,
        flags=re.S,
    )
    if not m:
        print("ERROR: could not find _is_bot_user_agent block", file=sys.stderr)
        sys.exit(1)
    text = text[: m.end()] + "\n" + HELPER + text[m.end() :]
    print("inserted human-browser helpers")
else:
    print("helpers already present")

OLD_UPSERT = """    # Cloud / datacenter probes: keep session for Live (labelled bot) but quarantine so stats ignore them.
    try:
        if _lean_ip_is_cloud_datacenter(ip_address):
            _lean_quarantine_ip(cur, ip_address, "cloud_datacenter")
    except Exception:
        pass
"""

NEW_UPSERT = """    # Cloud probes only quarantine when UA is NOT a real phone/PC/tablet browser on a valid page.
    try:
        if _lean_ip_is_cloud_datacenter(ip_address) and not _lean_human_traffic_pass(user_agent, path):
            _lean_quarantine_ip(cur, ip_address, "cloud_datacenter")
    except Exception:
        pass
"""

if OLD_UPSERT in text:
    text = text.replace(OLD_UPSERT, NEW_UPSERT, 1)
    print("patched upsert quarantine gate")
elif NEW_UPSERT in text:
    print("upsert gate already patched")
else:
    print("WARN: upsert quarantine block not found exact match", file=sys.stderr)

OLD_LIVE = """                is_bot = False
                try:
                    if ip and (_lean_ip_is_quarantined(cur, ip) or _lean_ip_is_cloud_datacenter(ip)):
                        is_bot = True
                        _lean_quarantine_ip(cur, ip, "cloud_datacenter" if _lean_ip_is_cloud_datacenter(ip) else "quarantine")
                except Exception:
                    is_bot = bool(ip and _lean_ip_is_cloud_datacenter(ip))
"""

NEW_LIVE = """                is_bot = False
                ua_live = d.get("device") or ""
                try:
                    # Real Chrome/Safari/etc on a valid page path => pass as guest (not bot).
                    if _lean_human_traffic_pass(ua_live, path):
                        is_bot = False
                        if ip and _lean_ip_is_quarantined(cur, ip):
                            try:
                                cur.execute(
                                    "UPDATE public.traffic_quarantine_ips SET active = false, "
                                    "reason = LEFT(COALESCE(reason,'') || '|released_human_browser', 80), "
                                    "last_seen_at = NOW() WHERE ip_address = %s AND COALESCE(active, true) = true",
                                    (ip[:80],),
                                )
                            except Exception:
                                pass
                    elif ip and (_lean_ip_is_quarantined(cur, ip) or _lean_ip_is_cloud_datacenter(ip)):
                        is_bot = True
                        if not _is_human_browser_ua(ua_live):
                            _lean_quarantine_ip(
                                cur,
                                ip,
                                "cloud_datacenter" if _lean_ip_is_cloud_datacenter(ip) else "quarantine",
                            )
                except Exception:
                    if _lean_human_traffic_pass(ua_live, path):
                        is_bot = False
                    else:
                        is_bot = bool(ip and _lean_ip_is_cloud_datacenter(ip))
"""

if OLD_LIVE in text:
    text = text.replace(OLD_LIVE, NEW_LIVE, 1)
    print("patched live visitor bot labelling")
elif "released_human_browser" in text and "_lean_human_traffic_pass(ua_live, path)" in text:
    print("live visitor labelling already patched")
else:
    print("WARN: live is_bot block not found exact match", file=sys.stderr)

if text == orig:
    print("no changes written")
    sys.exit(0)

API.write_text(text, encoding="utf-8")
print("wrote", API, "bytes", len(text))
