#!/usr/bin/env python3
"""Scroll/click = human. Don't bot deep sailor landings until leave with no engage."""
from __future__ import annotations

import py_compile
import shutil
from datetime import datetime, timezone
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")


def main() -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    shutil.copy2(API, API.with_suffix(f".bak-engage-human-{stamp}"))
    text = API.read_text(encoding="utf-8")
    orig = text

    # 1) Any scroll/click = human browse (even single sailor page)
    old_hb = '''        if any_eng and npaths >= 2:
            return True
        if npaths >= 4:
            return True
    except Exception:
        return False
    return False
'''
    new_hb = '''        # Scroll or click on even one real page = human (e.g. sailor profile)
        if any_eng:
            return True
        if npaths >= 4:
            return True
    except Exception:
        return False
    return False
'''
    if old_hb not in text:
        raise SystemExit("human_browse end not found")
    text = text.replace(old_hb, new_hb, 1)

    # 2) Soften deep-link bot: never if engagement; wait while stay still open
    old_deep = '''        if deep:
            # 1-page (or few) deep-link with no home = confident bot, esp. cloud/datacenter
            if len(paths) <= 2:
                if not _lean_trail_has_engagement(trail):
                    try:
                        if ip and _lean_ip_is_cloud_datacenter(ip):
                            return True
                    except Exception:
                        pass
                    # bare entity entry, no home, no scroll/click = bot
                    return True
'''
    new_deep = '''        if deep:
            # Scroll/click on sailor/boat/etc = human — never bot
            if _lean_trail_has_engagement(trail):
                return False
            # Still on the page (open) — give them time to scroll/click
            if any(isinstance(pt, dict) and pt.get("open") for pt in trail):
                return False
            # Closed deep-link stay(s), no engage = bot (esp. cloud)
            if len(paths) <= 2:
                try:
                    if ip and _lean_ip_is_cloud_datacenter(ip):
                        return True
                except Exception:
                    pass
                # bare entity entry, left with no scroll/click = bot
                return True
'''
    if old_deep not in text:
        raise SystemExit("deep-link block not found")
    text = text.replace(old_deep, new_deep, 1)

    # Early exit at top of behavior if engagement
    old_beh_start = '''    trail = page_trail if isinstance(page_trail, list) else []
    paths = []
    dwells = []
    for pt in trail:
'''
    new_beh_start = '''    trail = page_trail if isinstance(page_trail, list) else []
    try:
        if _lean_trail_has_engagement(trail):
            return False
    except Exception:
        pass
    paths = []
    dwells = []
    for pt in trail:
'''
    # only first occurrence in behavior fn
    bi = text.find("def _lean_behavior_confident_bot")
    if bi < 0:
        raise SystemExit("behavior fn missing")
    bj = text.find("def ", bi + 10)
    beh = text[bi:bj]
    if "_lean_trail_has_engagement(trail):\n            return False" not in beh.split("paths = []")[0]:
        if old_beh_start not in beh:
            raise SystemExit("beh start missing")
        beh2 = beh.replace(old_beh_start, new_beh_start, 1)
        text = text[:bi] + beh2 + text[bj:]
        print("behavior early engage exit")
    else:
        print("behavior engage exit already")

    # 3) Live: if trail has engagement, force guest (after bot checks)
    wire = '''                if (not is_bot) and _lean_bounce_home_bot(_trail_pre, path):
                    is_bot = True
                    if ip:
                        try:
                            _lean_quarantine_ip(cur, ip, "bounce_home_no_engage")
                        except Exception:
                            pass
                likely = {"name": "", "slug": "", "hits": 0, "sas_id": ""}
'''
    wire_new = '''                if (not is_bot) and _lean_bounce_home_bot(_trail_pre, path):
                    is_bot = True
                    if ip:
                        try:
                            _lean_quarantine_ip(cur, ip, "bounce_home_no_engage")
                        except Exception:
                            pass
                # Scroll/click wins — always Guest
                try:
                    if _lean_trail_has_engagement(_trail_pre):
                        is_bot = False
                except Exception:
                    pass
                likely = {"name": "", "slug": "", "hits": 0, "sas_id": ""}
'''
    if wire in text:
        text = text.replace(wire, wire_new, 1)
        print("live engage override")
    else:
        # try without bounce block
        alt = '''                likely = {"name": "", "slug": "", "hits": 0, "sas_id": ""}
                if not is_bot:
                    try:
                        likely = _public_likely_sailor_for_ip(cur, ip, path) or likely
'''
        if "Scroll/click wins" not in text and alt in text:
            text = text.replace(
                alt,
                '''                try:
                    if _lean_trail_has_engagement(_trail_pre):
                        is_bot = False
                except Exception:
                    pass
'''
                + alt,
                1,
            )
            print("live engage override alt")
        else:
            print("WARN live wire", "Scroll/click wins" in text)

    # 4) maybe_quarantine: skip if trail has engagement; don't sterile/bounce while open deep sailor
    old_q = '''    try:
        if _lean_ip_has_human_browse(cur, ip):
            return
    except Exception:
        pass
    path = (current_path or "").split("?", 1)[0].strip() or ""
'''
    new_q = '''    try:
        if _lean_ip_has_human_browse(cur, ip):
            return
    except Exception:
        pass
    path = (current_path or "").split("?", 1)[0].strip() or ""
'''
    # After building trail in maybe_quarantine, skip if engage or open entity page
    old_after_trail = '''    if not path and trail:
        path = (trail[-1].get("path") or "") if isinstance(trail[-1], dict) else ""
    try:
        if any(
            _lean_is_junk_false_path((t or {}).get("path") if isinstance(t, dict) else "")
            for t in trail
        ):
'''
    new_after_trail = '''    if not path and trail:
        path = (trail[-1].get("path") or "") if isinstance(trail[-1], dict) else ""
    try:
        if _lean_trail_has_engagement(trail):
            return
    except Exception:
        pass
    # Real entity page still open — wait for scroll/click or leave
    try:
        _p0 = (path or "").split("?", 1)[0]
        if any(isinstance(pt, dict) and pt.get("open") for pt in trail) and (
            _p0.startswith("/sailor/")
            or _p0.startswith("/boat/")
            or _p0.startswith("/regatta/")
            or _p0.startswith("/club/")
            or _p0.startswith("/class/")
        ):
            return
    except Exception:
        pass
    try:
        if any(
            _lean_is_junk_false_path((t or {}).get("path") if isinstance(t, dict) else "")
            for t in trail
        ):
'''
    if old_after_trail not in text:
        raise SystemExit("maybe_q after trail not found")
    text = text.replace(old_after_trail, new_after_trail, 1)

    # 5) Offline: engagement forces human
    old_off = '''                ):
                    is_bot = True
                    if ip:
                        try:
                            _lean_maybe_quarantine_missed_bot(cur, ip, path)
                        except Exception:
                            pass
                else:
                    # cloud single-page no engage → bot
'''
    new_off = '''                ):
                    is_bot = True
                    try:
                        if _lean_trail_has_engagement(trail):
                            is_bot = False
                    except Exception:
                        pass
                    if is_bot and ip:
                        try:
                            _lean_maybe_quarantine_missed_bot(cur, ip, path)
                        except Exception:
                            pass
                else:
                    # cloud single-page no engage → bot
'''
    if old_off in text:
        text = text.replace(old_off, new_off, 1)
        print("offline engage override")
    else:
        print("WARN offline block")

    if text == orig:
        raise SystemExit("no changes")
    API.write_text(text, encoding="utf-8")
    py_compile.compile(str(API), doraise=True)
    print(f"OK engage=human (+{len(text)-len(orig)} bytes)")


if __name__ == "__main__":
    main()
