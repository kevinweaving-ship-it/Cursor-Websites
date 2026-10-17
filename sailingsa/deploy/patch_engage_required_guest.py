#!/usr/bin/env python3
"""Guest = scroll/click engagement. No engage → not real (Done); live has 3m grace."""
from pathlib import Path
import sys

API = Path("/var/www/sailingsa/api/api.py")
text = API.read_text(encoding="utf-8")
orig = text

# --- Offline ---
old_off = """                else:
                    # cloud single-page no engage → bot
                    try:
                        if (not is_staff) and len(trail) <= 2 and not _lean_trail_has_engagement(trail):
                            if _lean_ip_is_cloud_datacenter(ip):
                                is_bot = True
                    except Exception:
                        pass
            except Exception:
                pass
            in_live_window = False"""

new_off = """                else:
                    # cloud single-page no engage → bot
                    try:
                        if (not is_staff) and len(trail) <= 2 and not _lean_trail_has_engagement(trail):
                            if _lean_ip_is_cloud_datacenter(ip):
                                is_bot = True
                    except Exception:
                        pass
                # Real people scroll or click. No engagement → not a Guest on Done.
                if (not is_bot) and (not is_staff):
                    try:
                        if not _lean_trail_has_engagement(trail):
                            is_bot = True
                    except Exception:
                        pass
            except Exception:
                pass
            in_live_window = False"""

if "Real people scroll or click. No engagement → not a Guest on Done." in text:
    print("SKIP offline")
elif old_off not in text:
    print("FAIL offline anchor", file=sys.stderr)
    sys.exit(1)
else:
    text = text.replace(old_off, new_off, 1)
    print("OK offline")

# --- Live: engagement wins must NOT clear crawler-cloud; no-engage → bot with grace ---
old_live = """                # Scroll/click wins — always Guest
                try:
                    if _lean_trail_has_engagement(_trail_pre):
                        is_bot = False
                except Exception:
                    pass
                # Club page shares (e.g. FB → /club/gbyc) — assume human
                try:
                    if _lean_trail_is_club_share_only(_trail_pre, path):
                        if _lean_is_facebook_crawler_ua(ua_live or "") or _lean_is_facebook_crawler_ip(ip or ""):
                            is_bot = True"""

new_live = """                # Scroll/click = real, but never clears Meta/AWS/Alibaba/Google IP ranges
                try:
                    if _lean_trail_has_engagement(_trail_pre):
                        if not (ip and _lean_is_crawler_cloud_ip(ip)):
                            is_bot = False
                except Exception:
                    pass
                # No scroll/click → not Guest (3 min grace while still on first page)
                if not is_bot:
                    try:
                        has_eng = _lean_trail_has_engagement(_trail_pre)
                    except Exception:
                        has_eng = False
                    if not has_eng:
                        fresh = False
                        try:
                            cur.execute(
                                "SELECT (%s::timestamptz > NOW() - interval '3 minutes')",
                                (d.get("last_activity"),),
                            )
                            rr = cur.fetchone()
                            if rr:
                                fresh = bool(rr[0] if not isinstance(rr, dict) else next(iter(rr.values())))
                        except Exception:
                            fresh = False
                        if not fresh:
                            is_bot = True
                # Club page shares (e.g. FB → /club/gbyc) — assume human
                try:
                    if _lean_trail_is_club_share_only(_trail_pre, path):
                        if _lean_is_facebook_crawler_ua(ua_live or "") or _lean_is_facebook_crawler_ip(ip or ""):
                            is_bot = True"""

if "No scroll/click → not Guest (3 min grace" in text:
    print("SKIP live")
elif old_live not in text:
    print("FAIL live anchor", file=sys.stderr)
    k = text.find("Scroll/click wins")
    print(repr(text[k:k+500]))
    sys.exit(2)
else:
    text = text.replace(old_live, new_live, 1)
    print("OK live")

if text == orig:
    print("NO CHANGE", file=sys.stderr)
    sys.exit(3)

compile(text, str(API), "exec")
API.write_text(text, encoding="utf-8")
print("WROTE delta", len(text) - len(orig))
