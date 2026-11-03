#!/usr/bin/env python3
"""Club share URLs (/club/{slug}) = assume human; Facebook crawler UA stays bot."""
from __future__ import annotations

import py_compile
import shutil
from datetime import datetime, timezone
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")

HELPER = '''def _lean_is_club_entity_path(path: Optional[str]) -> bool:
    """Real club page e.g. /club/gbyc — shared on FB; treat visitors as human."""
    p = (path or "").split("?", 1)[0].strip().rstrip("/") or "/"
    if not p.startswith("/club/"):
        return False
    slug = p[len("/club/") :]
    if not slug or slug in ("api", "admin", "new", "edit"):
        return False
    return True


def _lean_trail_is_club_share_only(page_trail: list, current_path: str = "") -> bool:
    """True when the trail is only real /club/{slug} pages (FB share click pattern)."""
    trail = page_trail if isinstance(page_trail, list) else []
    paths = []
    for pt in trail:
        if isinstance(pt, dict):
            paths.append((pt.get("path") or "").split("?", 1)[0].strip() or "/")
    if not paths:
        p0 = (current_path or "").split("?", 1)[0].strip() or "/"
        paths = [p0]
    if not paths:
        return False
    return all(_lean_is_club_entity_path(p) for p in paths)


def _lean_is_facebook_crawler_ua(user_agent: str) -> bool:
    ua = (user_agent or "").lower()
    if not ua:
        return False
    return any(
        x in ua
        for x in (
            "facebookexternalhit",
            "facebot",
            "facebookcatalog",
            "meta-externalagent",
            "meta-externalfetcher",
        )
    )


def _lean_is_facebook_crawler_ip(ip: str) -> bool:
    """Common Meta/Facebook crawler egress prefixes (link preview bots)."""
    ip = (ip or "").strip()
    if not ip:
        return False
    return any(
        ip.startswith(p)
        for p in (
            "173.252.",
            "69.63.",
            "69.171.",
            "31.13.",
            "66.220.",
            "157.240.",
            "185.60.",
        )
    )


'''


def main() -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    shutil.copy2(API, API.with_suffix(f".bak-club-share-{stamp}"))
    text = API.read_text(encoding="utf-8")
    orig = text

    if "def _lean_is_club_entity_path" not in text:
        anchor = text.find("def _lean_bounce_home_bot")
        if anchor < 0:
            anchor = text.find("def _lean_is_junk_false_path")
        if anchor < 0:
            raise SystemExit("no anchor")
        text = text[:anchor] + HELPER + text[anchor:]

    # Remove /club/ from deep-link bot lists (behavior + overview scan)
    text = text.replace(
        '''            or first.startswith("/regatta/")
            or first.startswith("/club/")
            or first.startswith("/class/")
''',
        '''            or first.startswith("/regatta/")
            or first.startswith("/class/")
''',
    )
    # also the earlier deep = ( block in behavior
    text = text.replace(
        '''            or first.startswith("/regatta/")
            or first.startswith("/club/")
            or first.startswith("/class/")
            or first.startswith("/sponsors/")
''',
        '''            or first.startswith("/regatta/")
            or first.startswith("/class/")
            or first.startswith("/sponsors/")
''',
    )

    # same_page_swarm: skip club entity pages (FB share previews swarm the URL)
    old_swarm = '''    p = (path or "").split("?", 1)[0].strip() or "/"
    if p in ("/", "/index.html"):
        return False
'''
    new_swarm = '''    p = (path or "").split("?", 1)[0].strip() or "/"
    if p in ("/", "/index.html"):
        return False
    if _lean_is_club_entity_path(p):
        return False
'''
    # only in same_page_swarm_bot
    si = text.find("def _lean_same_page_swarm_bot")
    if si < 0:
        raise SystemExit("swarm missing")
    sj = text.find("\ndef ", si + 10)
    swarm = text[si:sj]
    if "_lean_is_club_entity_path(p)" not in swarm:
        if old_swarm not in swarm:
            raise SystemExit("swarm start not found")
        swarm2 = swarm.replace(old_swarm, new_swarm, 1)
        text = text[:si] + swarm2 + text[sj:]
        print("swarm skips club")
    else:
        print("swarm club skip already")

    # behavior: club share only → never bot (unless we only have agent junk)
    old_beh = '''    try:
        if _lean_trail_has_engagement(trail):
            return False
    except Exception:
        pass
    paths = []
'''
    # find in behavior fn
    bi = text.find("def _lean_behavior_confident_bot")
    bj = text.find("\ndef ", bi + 10)
    beh = text[bi:bj]
    if "_lean_trail_is_club_share_only" not in beh:
        needle = '''    try:
        if _lean_trail_has_engagement(trail):
            return False
    except Exception:
        pass
'''
        if needle not in beh:
            # insert after trail =
            needle2 = "    trail = page_trail if isinstance(page_trail, list) else []\n"
            if needle2 not in beh:
                raise SystemExit("beh trail assign missing")
            beh = beh.replace(
                needle2,
                needle2
                + '''    try:
        if _lean_trail_has_engagement(trail):
            return False
        if _lean_trail_is_club_share_only(trail, current_path):
            return False
    except Exception:
        pass
''',
                1,
            )
        else:
            beh = beh.replace(
                needle,
                needle
                + '''    try:
        if _lean_trail_is_club_share_only(trail, current_path):
            return False
    except Exception:
        pass
''',
                1,
            )
        text = text[:bi] + beh + text[bj:]
        print("behavior club share pass")
    else:
        print("behavior club already")

    # maybe_quarantine: skip club-share-only trails
    old_mq = '''    try:
        if _lean_trail_has_engagement(trail):
            return
    except Exception:
        pass
    # Real entity page still open — wait for scroll/click or leave
'''
    new_mq = '''    try:
        if _lean_trail_has_engagement(trail):
            return
        if _lean_trail_is_club_share_only(trail, path):
            return
    except Exception:
        pass
    # Real entity page still open — wait for scroll/click or leave
'''
    if old_mq in text:
        text = text.replace(old_mq, new_mq, 1)
        print("maybe_q club skip")
    else:
        print("WARN maybe_q block")

    # overview scanner: skip club share only
    old_ov = '''            if _lean_trail_has_engagement(trail):
                continue
            path = ""
'''
    new_ov = '''            if _lean_trail_has_engagement(trail):
                continue
            path = ""
            if trail:
                path = (trail[-1].get("path") or "") if isinstance(trail[-1], dict) else ""
            if _lean_trail_is_club_share_only(trail, path):
                continue
'''
    # careful - path = "" then if trail path assign exists twice
    oi = text.find("def _lean_quarantine_bot_shaped_ips_in_range")
    if oi >= 0:
        oj = text.find("\ndef ", oi + 10)
        ov = text[oi:oj]
        if "_lean_trail_is_club_share_only" not in ov:
            if "if _lean_trail_has_engagement(trail):\n                continue\n            path = \"\"" in ov:
                ov2 = ov.replace(
                    '''            if _lean_trail_has_engagement(trail):
                continue
            path = ""
            if trail:
                path = (trail[-1].get("path") or "") if isinstance(trail[-1], dict) else ""
''',
                    '''            if _lean_trail_has_engagement(trail):
                continue
            path = ""
            if trail:
                path = (trail[-1].get("path") or "") if isinstance(trail[-1], dict) else ""
            if _lean_trail_is_club_share_only(trail, path):
                continue
''',
                    1,
                )
                if ov2 == ov:
                    # simpler insert after engagement continue
                    ov2 = ov.replace(
                        '''            if _lean_trail_has_engagement(trail):
                continue
''',
                        '''            if _lean_trail_has_engagement(trail):
                continue
            _club_path = ""
            if trail:
                _club_path = (trail[-1].get("path") or "") if isinstance(trail[-1], dict) else ""
            if _lean_trail_is_club_share_only(trail, _club_path):
                continue
''',
                        1,
                    )
                text = text[:oi] + ov2 + text[oj:]
                print("overview club skip")
            else:
                print("WARN overview engage block", repr(ov[ov.find("engagement") : ov.find("engagement") + 200]))
        else:
            print("overview club already")

    # Live: club share trail → force guest (after bot checks, with engage override)
    if "club share wins" not in text:
        eng = '''                # Scroll/click wins — always Guest
                try:
                    if _lean_trail_has_engagement(_trail_pre):
                        is_bot = False
                except Exception:
                    pass
'''
        if eng in text:
            text = text.replace(
                eng,
                eng
                + '''                # Club page shares (e.g. FB → /club/gbyc) — assume human
                try:
                    if _lean_trail_is_club_share_only(_trail_pre, path):
                        if _lean_is_facebook_crawler_ua(ua_live or "") or _lean_is_facebook_crawler_ip(ip or ""):
                            is_bot = True
                            if ip:
                                try:
                                    _lean_quarantine_ip(cur, ip, "facebook_crawler")
                                except Exception:
                                    pass
                        else:
                            is_bot = False
                except Exception:
                    pass
''',
                1,
            )
            print("live club share")
        else:
            print("WARN live engage override missing")

    # Offline: club share → not bot
    old_off = '''                    try:
                        if _lean_trail_has_engagement(trail):
                            is_bot = False
                    except Exception:
                        pass
'''
    if old_off in text and "club_share_only(trail" not in text[text.find(old_off) : text.find(old_off) + 400]:
        text = text.replace(
            old_off,
            old_off
            + '''                    try:
                        if _lean_trail_is_club_share_only(trail, path):
                            is_bot = False
                    except Exception:
                        pass
''',
            1,
        )
        print("offline club share")

    if text == orig:
        raise SystemExit("no changes")
    API.write_text(text, encoding="utf-8")
    py_compile.compile(str(API), doraise=True)
    print(f"OK club share human (+{len(text)-len(orig)} bytes)")


if __name__ == "__main__":
    main()
