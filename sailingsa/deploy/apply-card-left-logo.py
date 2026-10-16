#!/usr/bin/env python3
"""Live hook: prior-year Event Logos on empty landing / club card left slots.

Does not edit gold api.py. Copies the card filler JS, restores HMYC Grand Slam
artwork into Event Logo/, hooks club-page-std.js, and lets landing bake use
card_left_logo.resolve_card_left_logo when the slot is empty.
"""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path("/var/www/sailingsa")
JS_NAME = "card-left-logo.js"
JS_VER = "cll1"
HOOK = f'loadScript("/js/{JS_NAME}?v={JS_VER}")'
BAKE_APPLY = (
    "    if not logo:\n"
    "        try:\n"
    "            from sailingsa.backend.card_left_logo import resolve_card_left_logo as _card_left_logo\n"
    "            logo = _card_left_logo(name, rid) or \"\"\n"
    "        except Exception:\n"
    "            logo = logo or \"\"\n"
)


def _copy_js(src: Path) -> None:
    dests = [ROOT / "js" / JS_NAME, ROOT / "frontend" / "js" / JS_NAME]
    for dest in dests:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        print("js", dest)


def _hook_club_std() -> None:
    p = ROOT / "js" / "club-page-std.js"
    if not p.is_file():
        print("skip club-page-std.js missing")
        return
    t = p.read_text(encoding="utf-8")
    if JS_NAME in t:
        print("club-page-std already hooked")
        return
    needle = "function boot() {"
    if needle not in t:
        t = t.rstrip() + "\n  try { " + HOOK + "; } catch (e) {}\n"
    else:
        t = t.replace(needle, needle + "\n    try { " + HOOK + "; } catch (e) {}", 1)
    p.write_text(t, encoding="utf-8")
    print("hooked", p)


def _hook_html(path: Path) -> None:
    if not path.is_file():
        return
    t = path.read_text(encoding="utf-8", errors="replace")
    if JS_NAME in t:
        print("html already", path)
        return
    tag = f'<script src="/js/{JS_NAME}?v={JS_VER}"></script>\n'
    old = '<script src="/js/session.js?v=20260813_SILENT_LOGIN"></script>'
    if old in t:
        t = t.replace(old, old + "\n    " + tag, 1)
    else:
        t = t.replace("</body>", "    " + tag + "</body>", 1)
    path.write_text(t, encoding="utf-8")
    print("html", path)


def _copy_grand_slam() -> None:
    dest = ROOT / "artwork" / "Event Logo" / "HMYC-Grand-Slam.png"
    if dest.is_file() and dest.stat().st_size > 1000:
        print("grand slam already", dest.stat().st_size)
        return
    src = ROOT / "deploy" / "HMYC-Grand-Slam.png"
    if not src.is_file():
        print("skip grand slam source missing")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    print("copied", dest, dest.stat().st_size)


def _hook_landing_bake(src_helper: Path) -> None:
    helper_dest = ROOT / "sailingsa" / "backend" / "card_left_logo.py"
    helper_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_helper, helper_dest)
    print("helper", helper_dest)
    bake = ROOT / "sailingsa" / "backend" / "landing_event_story_cards.py"
    if not bake.is_file():
        print("skip bake missing")
        return
    t = bake.read_text(encoding="utf-8")
    if "resolve_card_left_logo" in t:
        print("bake already hooked")
        return
    old = "        logo = series.get(\"logo\") or class_logo or \"\"\n"
    new = old + BAKE_APPLY
    if old in t:
        t = t.replace(old, new, 1)
        bake.write_text(t, encoding="utf-8")
        print("bake hooked", bake)
    else:
        print("bake hook point missing")


def main() -> None:
    here = Path(__file__).resolve()
    repo = here.parents[2]
    js_src = repo / "sailingsa" / "frontend" / "js" / JS_NAME
    if not js_src.is_file():
        js_src = here.parent / JS_NAME
    if not js_src.is_file():
        raise SystemExit("card-left-logo.js not found")
    helper_src = repo / "sailingsa" / "backend" / "card_left_logo.py"
    _copy_js(js_src)
    _hook_club_std()
    for name in ("index.html", "blank.html", "frontend/index.html"):
        _hook_html(ROOT / name)
    _copy_grand_slam()
    if helper_src.is_file():
        _hook_landing_bake(helper_src)
    print("OK card left logo")


if __name__ == "__main__":
    main()
