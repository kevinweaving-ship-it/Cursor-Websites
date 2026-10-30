#!/usr/bin/env python3
"""Same-page multi-IP swarm with no scroll/click = confident bot."""
from __future__ import annotations

import py_compile
import shutil
from datetime import datetime, timezone
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")


HELPER = '''def _lean_trail_has_engagement(page_trail: list) -> bool:
    """True if any stay recorded scrolled / searched / clicked."""
    for pt in page_trail or []:
        if not isinstance(pt, dict):
            continue
        eng = pt.get("engagement") or []
        if isinstance(eng, str):
            eng = _lean_parse_engage_tokens(eng)
        if eng:
            return True
        lab = (pt.get("engagement_label") or "").strip()
        if lab:
            return True
    return False


def _lean_same_page_swarm_bot(cur, *, ip: str, path: str, page_trail: list, window_minutes: int = 30) -> bool:
    """3+ distinct IPs on the same deep URL recently, this IP has no real engage = bot swarm.

    Matches patterns like three cloud IPs all hitting one /sailor/… page with zero scroll/click.
    Home `/` is excluded (many real visitors share landing).
    """
    p = (path or "").split("?", 1)[0].strip() or "/"
    if p in ("/", "/index.html"):
        return False
    # Prefer deep entity pages; also flag any non-home single-target swarm
    trail = page_trail if isinstance(page_trail, list) else []
    paths = []
    for pt in trail:
        if isinstance(pt, dict):
            pp = (pt.get("path") or "").split("?", 1)[0].strip() or "/"
            paths.append(pp)
    if not paths:
        paths = [p]
    # Real click-through (home then elsewhere) is not this swarm shape
    if any(x in ("/", "/index.html") for x in paths) and len(set(paths)) > 1:
        return False
    if _lean_trail_has_engagement(trail):
        return False
    # Short sterile trail (1–2 stays) on one URL
    uniq = {x for x in paths if x}
    if len(uniq) > 2:
        return False
    try:
        cur.execute(
            """
            SELECT COUNT(DISTINCT ip_address)::int AS n
            FROM public.public_page_hits
            WHERE occurred_at > NOW() - make_interval(mins => %s)
              AND split_part(path, '?', 1) = %s
              AND ip_address IS NOT NULL
              AND TRIM(ip_address) <> ''
            """,
            (int(window_minutes), p),
        )
        row = cur.fetchone()
        n = 0
        if row is not None:
            n = int(row[0] if not isinstance(row, dict) else (row.get("n") or 0))
        if n >= 3:
            return True
    except Exception:
        return False
    return False


'''


def main() -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    shutil.copy2(API, API.with_suffix(f".bak-swarm-bot-{stamp}"))
    text = API.read_text(encoding="utf-8")
    orig = text

    if "def _lean_same_page_swarm_bot" not in text:
        anchor = text.find("def _lean_behavior_confident_bot")
        if anchor < 0:
            raise SystemExit("behavior fn missing")
        text = text[:anchor] + HELPER + text[anchor:]

    # Strengthen: deep-link + no engagement = bot (even without cloud)
    # Already returns True for deep 1-2 pages. Add no-engage single-page for /regatta/ /club/ /class/ too.
    old_deep = '''        deep = first.startswith("/boat/") or first.startswith("/sailor/")
        if deep:
            # 1-page (or few) deep-link with no home = confident bot, esp. cloud/datacenter
            if len(paths) <= 2:
                try:
                    if ip and _lean_ip_is_cloud_datacenter(ip):
                        return True
                except Exception:
                    pass
                # even non-cloud: bare boat/sailor entry with no home/click trail = bot smell we accept as bot
                return True
'''
    new_deep = '''        deep = (
            first.startswith("/boat/")
            or first.startswith("/sailor/")
            or first.startswith("/regatta/")
            or first.startswith("/club/")
            or first.startswith("/class/")
            or first.startswith("/sponsors/")
        )
        if deep:
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
    if old_deep not in text:
        raise SystemExit("deep-link block not found")
    text = text.replace(old_deep, new_deep, 1)

    # Wire swarm check after behavior_deep_link in live classify
    old_wire = '''                if (not is_bot) and _lean_behavior_confident_bot(_trail_pre, path, ip):
                    is_bot = True
                    if ip:
                        try:
                            _lean_quarantine_ip(cur, ip, "behavior_deep_link_swarm")
                        except Exception:
                            pass
'''
    new_wire = '''                if (not is_bot) and _lean_behavior_confident_bot(_trail_pre, path, ip):
                    is_bot = True
                    if ip:
                        try:
                            _lean_quarantine_ip(cur, ip, "behavior_deep_link_swarm")
                        except Exception:
                            pass
                if (not is_bot) and _lean_same_page_swarm_bot(
                    cur, ip=ip or "", path=path, page_trail=_trail_pre, window_minutes=30
                ):
                    is_bot = True
                    if ip:
                        try:
                            _lean_quarantine_ip(cur, ip, "same_page_swarm_no_engage")
                        except Exception:
                            pass
'''
    if old_wire not in text:
        raise SystemExit("behavior wire not found")
    text = text.replace(old_wire, new_wire, 1)

    # Also in offline classifier
    old_off = '''                if _is_sailor_sas_id_path(path) or _lean_behavior_confident_bot(trail, path, ip):
                    is_bot = True
                elif ip and _lean_ip_is_quarantined(cur, ip):
                    is_bot = True
'''
    if old_off in text:
        text = text.replace(
            old_off,
            '''                if _is_sailor_sas_id_path(path) or _lean_behavior_confident_bot(trail, path, ip):
                    is_bot = True
                elif _lean_same_page_swarm_bot(cur, ip=ip or "", path=path, page_trail=trail, window_minutes=30):
                    is_bot = True
                    if ip:
                        try:
                            _lean_quarantine_ip(cur, ip, "same_page_swarm_no_engage")
                        except Exception:
                            pass
                elif ip and _lean_ip_is_quarantined(cur, ip):
                    is_bot = True
''',
            1,
        )

    if text == orig:
        raise SystemExit("no changes")
    API.write_text(text, encoding="utf-8")
    py_compile.compile(str(API), doraise=True)
    print(f"OK same-page swarm bot (+{len(text) - len(orig)} bytes)")


if __name__ == "__main__":
    main()
