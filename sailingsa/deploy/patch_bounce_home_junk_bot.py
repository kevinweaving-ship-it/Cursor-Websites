#!/usr/bin/env python3
"""Bounce-home / junk-path → bot; never probe-quarantine real signup; release false-positive humans."""
from __future__ import annotations

import py_compile
import shutil
from datetime import datetime, timezone
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")

HELPER = '''def _lean_is_junk_false_path(path: Optional[str]) -> bool:
    """Made-up / scanner paths that are not real site pages."""
    p = (path or "").split("?", 1)[0].strip().rstrip("/") or "/"
    if p in ("/wk", "/wp", "/test", "/tmp", "/old", "/new", "/api", "/null", "/undefined"):
        return True
    # /classes/{digits} is not a real class slug page on this site (/class/... is)
    if p.startswith("/classes/"):
        rest = p[len("/classes/") :]
        if rest.isdigit():
            return True
    return False


def _lean_bounce_home_bot(page_trail: list, current_path: str = "") -> bool:
    """Home-only, no scroll/click, tiny or zero dwell → not a real guest for Done/offline.

    Real sailors leave a trail (class/club/regatta/sailor) or at least engage.
    """
    trail = page_trail if isinstance(page_trail, list) else []
    paths = []
    dwells = []
    for pt in trail:
        if not isinstance(pt, dict):
            continue
        pp = (pt.get("path") or "").split("?", 1)[0].strip() or "/"
        paths.append(pp)
        if pt.get("open"):
            continue
        try:
            dwells.append(int(pt.get("dwell_seconds") if pt.get("dwell_seconds") is not None else 0))
        except Exception:
            dwells.append(0)
    if not paths:
        p0 = (current_path or "").split("?", 1)[0].strip() or "/"
        paths = [p0]
    uniq = {p for p in paths if p}
    if not uniq or any(p not in ("/", "/index.html") for p in uniq):
        return False
    try:
        if _lean_trail_has_engagement(trail):
            return False
    except Exception:
        pass
    # single landing stay, no engage
    if len(paths) > 2:
        return False
    max_d = max(dwells) if dwells else 0
    # 0s instant, or very short peek with no click-through
    if max_d <= 8:
        return True
    return False


'''


def main() -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    shutil.copy2(API, API.with_suffix(f".bak-bounce-bot-{stamp}"))
    text = API.read_text(encoding="utf-8")
    orig = text

    # 1) Remove real account pages from probe blocklist
    for bad in (
        '        "/signup",\n',
        '        "/register",\n',
        '        "/login",\n',
        '        "/login.html",\n',
        '        "/signin",\n',
        '        "/account",\n',
        '        "/profile",\n',
        '        "/settings",\n',
        '        "/my",\n',
        '        "/portal",\n',
        '        "/manage",\n',
        '        "/dashboard",\n',
        '        "/app",\n',
        '        "/console",\n',
        '        "/user",\n',
        '        "/user/login",\n',
        '        "/users",\n',
    ):
        if bad in text:
            text = text.replace(bad, "", 1)

    # Ensure signup.html never treated as probe via exact set leftover
    if '"/signup.html"' in text[text.find("blocked_exact") : text.find("blocked_exact") + 2000]:
        text = text.replace('        "/signup.html",\n', "", 1)

    # 2) Insert helpers before sterile or swarm
    if "def _lean_bounce_home_bot" not in text:
        anchor = text.find("def _lean_sterile_short_trail_bot")
        if anchor < 0:
            anchor = text.find("def _lean_same_page_swarm_bot")
        if anchor < 0:
            raise SystemExit("no helper anchor")
        text = text[:anchor] + HELPER + text[anchor:]

    # Extend sterile list helper if present
    old_sterile = '''    if p in ("/events", "/classes", "/clubs", "/vendor", "/class", "/club"):
        return True
'''
    new_sterile = '''    if p in ("/events", "/classes", "/clubs", "/vendor", "/class", "/club"):
        return True
    if _lean_is_junk_false_path(p):
        return True
'''
    if old_sterile in text:
        text = text.replace(old_sterile, new_sterile, 1)

    # 3) Wire live classify after sterile check
    old_wire = '''                if (not is_bot) and _lean_sterile_short_trail_bot(_trail_pre, path, ip or ""):
                    is_bot = True
                    if ip:
                        try:
                            reason = (
                                "cloud_sterile_short"
                                if _lean_ip_is_cloud_datacenter(ip)
                                else "sterile_single_page"
                            )
                            _lean_quarantine_ip(cur, ip, reason)
                        except Exception:
                            pass
                likely = {"name": "", "slug": "", "hits": 0, "sas_id": ""}
'''
    new_wire = '''                if (not is_bot) and _lean_sterile_short_trail_bot(_trail_pre, path, ip or ""):
                    is_bot = True
                    if ip:
                        try:
                            reason = (
                                "cloud_sterile_short"
                                if _lean_ip_is_cloud_datacenter(ip)
                                else "sterile_single_page"
                            )
                            _lean_quarantine_ip(cur, ip, reason)
                        except Exception:
                            pass
                if (not is_bot) and _lean_is_junk_false_path(path):
                    is_bot = True
                    if ip:
                        try:
                            _lean_quarantine_ip(cur, ip, "junk_false_path")
                        except Exception:
                            pass
                if (not is_bot) and _lean_bounce_home_bot(_trail_pre, path):
                    is_bot = True
                    if ip:
                        try:
                            _lean_quarantine_ip(cur, ip, "bounce_home_no_engage")
                        except Exception:
                            pass
                likely = {"name": "", "slug": "", "hits": 0, "sas_id": ""}
'''
    if old_wire not in text:
        # maybe sterile wire missing — try after swarm only
        old_wire2 = '''                if (not is_bot) and _lean_same_page_swarm_bot(
                    cur, ip=ip or "", path=path, page_trail=_trail_pre, window_minutes=30
                ):
                    is_bot = True
                    if ip:
                        try:
                            _lean_quarantine_ip(cur, ip, "same_page_swarm_no_engage")
                        except Exception:
                            pass
                likely = {"name": "", "slug": "", "hits": 0, "sas_id": ""}
'''
        if old_wire2 not in text:
            raise SystemExit("live wire not found")
        text = text.replace(
            old_wire2,
            old_wire2.replace(
                '                likely = {"name": "", "slug": "", "hits": 0, "sas_id": ""}\n',
                '''                if (not is_bot) and _lean_sterile_short_trail_bot(_trail_pre, path, ip or ""):
                    is_bot = True
                    if ip:
                        try:
                            reason = (
                                "cloud_sterile_short"
                                if _lean_ip_is_cloud_datacenter(ip)
                                else "sterile_single_page"
                            )
                            _lean_quarantine_ip(cur, ip, reason)
                        except Exception:
                            pass
                if (not is_bot) and _lean_is_junk_false_path(path):
                    is_bot = True
                    if ip:
                        try:
                            _lean_quarantine_ip(cur, ip, "junk_false_path")
                        except Exception:
                            pass
                if (not is_bot) and _lean_bounce_home_bot(_trail_pre, path):
                    is_bot = True
                    if ip:
                        try:
                            _lean_quarantine_ip(cur, ip, "bounce_home_no_engage")
                        except Exception:
                            pass
                likely = {"name": "", "slug": "", "hits": 0, "sas_id": ""}
''',
            ),
            1,
        )
    else:
        text = text.replace(old_wire, new_wire, 1)

    # 4) Offline: add bounce + junk into combined bot if
    old_off = '''                    or _lean_same_page_swarm_bot(cur, ip=ip, path=path, page_trail=trail, window_minutes=30)
                ):
                    is_bot = True
'''
    # try with sterile already
    if "or _lean_sterile_short_trail_bot(trail, path, ip or \"\")" in text:
        old_off = '''                    or _lean_same_page_swarm_bot(cur, ip=ip, path=path, page_trail=trail, window_minutes=30)
                    or _lean_sterile_short_trail_bot(trail, path, ip or "")
                ):
                    is_bot = True
'''
        new_off = '''                    or _lean_same_page_swarm_bot(cur, ip=ip, path=path, page_trail=trail, window_minutes=30)
                    or _lean_sterile_short_trail_bot(trail, path, ip or "")
                    or _lean_is_junk_false_path(path)
                    or _lean_bounce_home_bot(trail, path)
                    or any(_lean_is_junk_false_path((t or {}).get("path") if isinstance(t, dict) else "") for t in (trail or []))
                ):
                    is_bot = True
'''
    else:
        new_off = '''                    or _lean_same_page_swarm_bot(cur, ip=ip, path=path, page_trail=trail, window_minutes=30)
                    or _lean_sterile_short_trail_bot(trail, path, ip or "")
                    or _lean_is_junk_false_path(path)
                    or _lean_bounce_home_bot(trail, path)
                    or any(_lean_is_junk_false_path((t or {}).get("path") if isinstance(t, dict) else "") for t in (trail or []))
                ):
                    is_bot = True
'''
    if old_off not in text:
        print("WARN offline combined if not exact; trying alternate")
        # find snippet
        i = text.find("or _lean_same_page_swarm_bot(cur, ip=ip, path=path, page_trail=trail")
        print(repr(text[i : i + 350]))
    else:
        text = text.replace(old_off, new_off, 1)

    # After offline is_bot True for bounce, quarantine
    # Expand hard reasons for bounce/junk
    for marker in (
        '"sterile_",\n',
        '"cloud_sterile",\n',
    ):
        pass
    old_hard_tail = '''                                "sterile_",
                                "cloud_sterile",
                                "live_bot",
                            )
'''
    new_hard_tail = '''                                "sterile_",
                                "cloud_sterile",
                                "live_bot",
                                "bounce_home",
                                "junk_false",
                            )
'''
    if old_hard_tail in text:
        text = text.replace(old_hard_tail, new_hard_tail)

    # Release SQL never release bounce/junk
    old_rel = '''                                            " AND COALESCE(reason,'') NOT LIKE '%%live_bot%%'",
'''
    if old_rel in text:
        text = text.replace(
            old_rel,
            '''                                            " AND COALESCE(reason,'') NOT LIKE '%%live_bot%%'"
                                            " AND COALESCE(reason,'') NOT LIKE '%%bounce_home%%'"
                                            " AND COALESCE(reason,'') NOT LIKE '%%junk_false%%'",
''',
            1,
        )

    # Guard: never quarantine probe_path if IP already has human browse evidence
    old_probe_q = None
    # Find upsert quarantine probe
    needle = '_lean_quarantine_ip(cur, ip_address, "probe_path")'
    if needle not in text:
        needle = "_lean_quarantine_ip(cur, ip_address, 'probe_path')"
    # Also live: if probe path but human trail, don't bot — add near probe checks
    # Safer: wrap _lean_quarantine_ip probe calls... too many. Instead add helper used before quarantine.

    if "def _lean_ip_has_human_browse" not in text:
        hb = '''def _lean_ip_has_human_browse(cur, ip: str, window_hours: int = 24) -> bool:
    """True if IP already showed a real multi-page / engaged browse (do not probe-quarantine)."""
    if not ip:
        return False
    try:
        cur.execute(
            """
            SELECT COUNT(DISTINCT split_part(path,'?',1))::int AS npaths,
                   BOOL_OR(
                     COALESCE(engagement::text,'') NOT IN ('','[]','null','None')
                   ) AS any_eng
            FROM public.public_page_hits
            WHERE ip_address = %s
              AND occurred_at > NOW() - make_interval(hours => %s)
              AND split_part(path,'?',1) NOT LIKE '/api/%%'
            """,
            (ip[:80], int(window_hours)),
        )
        row = cur.fetchone()
        if not row:
            return False
        if isinstance(row, dict):
            npaths = int(row.get("npaths") or 0)
            any_eng = bool(row.get("any_eng"))
        else:
            npaths = int(row[0] or 0)
            any_eng = bool(row[1])
        if any_eng and npaths >= 2:
            return True
        if npaths >= 4:
            return True
    except Exception:
        return False
    return False


'''
        anchor = text.find("def _lean_bounce_home_bot")
        if anchor < 0:
            anchor = text.find("def _lean_is_junk_false_path")
        text = text[:anchor] + hb + text[anchor:]

    # Patch common probe quarantine lines to skip humans
    for old_p, new_p in [
        (
            '_lean_quarantine_ip(cur, ip, "probe_path")',
            '(_lean_quarantine_ip(cur, ip, "probe_path") if not _lean_ip_has_human_browse(cur, ip) else None)',
        ),
        (
            "_lean_quarantine_ip(cur, ip, 'probe_path')",
            "(_lean_quarantine_ip(cur, ip, 'probe_path') if not _lean_ip_has_human_browse(cur, ip) else None)",
        ),
        (
            '_lean_quarantine_ip(cur, ip_address, "probe_path")',
            '(_lean_quarantine_ip(cur, ip_address, "probe_path") if not _lean_ip_has_human_browse(cur, ip_address) else None)',
        ),
    ]:
        if old_p in text:
            text = text.replace(old_p, new_p)

    if text == orig:
        raise SystemExit("no changes")
    API.write_text(text, encoding="utf-8")
    py_compile.compile(str(API), doraise=True)
    print(f"OK bounce/junk bot cleanup (+{len(text)-len(orig)} bytes)")


if __name__ == "__main__":
    main()
