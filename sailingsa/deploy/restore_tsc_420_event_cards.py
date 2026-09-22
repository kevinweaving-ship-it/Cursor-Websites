#!/usr/bin/env python3
"""Restore TSC 420 Nationals Leader Board + Media placeholders on live.

Surgical only. Never replace live api.py with the repo snapshot.

TSC has no weather station and no live cam — those cards stay off.
Leader Board is the Midmar empty shell (Waiting for race scores).
Media is the Dart empty shell (No media yet) until a WhatsApp /mm-clips feed exists.

Run on the live box as root:

  python3 /root/restore_tsc_420_event_cards.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from datetime import datetime

API = "/var/www/sailingsa/api/api.py"
LB_JS = "/var/www/sailingsa/js/midmar-leaderboard.js"
MEDIA_JS = "/var/www/sailingsa/js/midmar-live-media.js"
SLUG = "2026-09-25-tsc-420-nationals"
DART = "2026-09-24-hmyc-dart-18-nationals"

API_ELIF = (
    f'        elif str(regatta_id) == "{SLUG}":\n'
    "            # TSC: Leader Board + Media placeholders. No weather station, no live cam.\n"
    "            mm_card = "
    "'<div id=\"midmar-live-media\" class=\"midmar-live-media club-live-media\" "
    "aria-label=\"Event media\">"
    '<section id="midmar-leaderboard" class="card midmar-lb" aria-label="Leader Board">'
    '<h2 class="section-title">Leader Board</h2>'
    '<p class="midmar-lb-sheet-note">Full Results sheet below on page</p>'
    '<div class="midmar-lb-list" data-mm-lb-list>'
    '<p class="midmar-lb-empty">Waiting for race scores</p></div></section>'
    '<div class="midmar-mm-row">'
    f'<section id="mmLiptonReels" class="card mm-lipton-reels mm-lipton-reels--compact" '
    f'data-regatta-id="{SLUG}" data-media-wait="whatsapp">'
    '<div class="mm-lipton-reels-compact mm-lipton-reels-empty">'
    '<h2 class="section-title">Media</h2>'
    '<p class="midmar-lb-empty">No media yet</p></div></section></div></div>\'\n'
    "            mm_card_script = ("
    '\'<script src="/js/midmar-live-media.js?v=midmarwx55tsc420" defer></script>\''
    '\'<script src="/js/midmar-leaderboard.js?v=mmlb16tsc420" defer></script>\')\n'
)


def backup(path: str, dest_dir: str) -> str:
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, os.path.basename(path) + "." + datetime.now().strftime("%Y%m%d_%H%M%S"))
    shutil.copy2(path, dest)
    return dest


def must_contain(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"ERROR: {label} missing expected marker:\n{needle[:120]}")


def patch_leaderboard(text: str) -> str:
    old = (
        "    return rid === RID || rid === '2026-09-24-hmyc-dart-18-nationals';"
    )
    new = (
        "    return rid === RID || rid === '2026-09-24-hmyc-dart-18-nationals' "
        f"|| rid === '{SLUG}';"
    )
    if f"|| rid === '{SLUG}'" in text:
        return text
    must_contain(text, old, "midmar-leaderboard.js onMidmar")
    return text.replace(old, new, 1)


def patch_live_media(text: str) -> str:
    old_on = (
        '    return rid === RID || rid === "2026-09-24-hmyc-dart-18-nationals";'
    )
    new_on = (
        '    return rid === RID || rid === "2026-09-24-hmyc-dart-18-nationals" '
        f'|| rid === "{SLUG}";'
    )
    if f'|| rid === "{SLUG}"' not in text:
        must_contain(text, old_on, "midmar-live-media.js onMidmar")
        text = text.replace(old_on, new_on, 1)

    has_fn = (
        "  function hasWxCam() {\n"
        "    var rid = currentRid();\n"
        '    return rid === RID || rid === "2026-09-24-hmyc-dart-18-nationals";\n'
        "  }\n"
    )
    if "function hasWxCam()" not in text:
        empty = "  function emptyMedia() {\n    return currentRid() !== RID;\n  }\n"
        must_contain(text, empty, "midmar-live-media.js emptyMedia")
        text = text.replace(empty, empty + "\n" + has_fn, 1)

    old_place = """    var wx = makeWx();
    var row = makeMmRow();
    var mm = makeMmCard();
    var sa = makeSaCard();
    var cam = makeCam();
    if (wx.parentNode !== host) host.appendChild(wx);
    if (row.parentNode !== host) host.appendChild(row);
    if (mm.parentNode !== row) row.appendChild(mm);
    if (sa.parentNode !== row) row.appendChild(sa);
    if (cam.parentNode !== host) host.appendChild(cam);
    if (wx.nextSibling !== row) host.insertBefore(row, wx.nextSibling);
    if (row.nextSibling !== cam) host.insertBefore(cam, row.nextSibling);
    bindCam(cam);
    mountSa(host, sa);
    return host;"""
    new_place = """    var row = makeMmRow();
    var mm = makeMmCard();
    var sa = makeSaCard();
    if (hasWxCam()) {
      var wx = makeWx();
      var cam = makeCam();
      if (wx.parentNode !== host) host.appendChild(wx);
      if (row.parentNode !== host) host.appendChild(row);
      if (mm.parentNode !== row) row.appendChild(mm);
      if (sa.parentNode !== row) row.appendChild(sa);
      if (cam.parentNode !== host) host.appendChild(cam);
      if (wx.nextSibling !== row) host.insertBefore(row, wx.nextSibling);
      if (row.nextSibling !== cam) host.insertBefore(cam, row.nextSibling);
      bindCam(cam);
    } else {
      host.setAttribute("aria-label", "Event media");
      if (row.parentNode !== host) host.appendChild(row);
      if (mm.parentNode !== row) row.appendChild(mm);
      if (sa.parentNode !== row) row.appendChild(sa);
    }
    mountSa(host, sa);
    return host;"""
    if "if (hasWxCam()) {" not in text:
        must_contain(text, old_place, "midmar-live-media.js placeHost")
        text = text.replace(old_place, new_place, 1)

    old_boot = """    loadScript("/js/midmar-leaderboard.js?v=mmlb16");
    loadScript("/js/midmar-media-rotate.js?v=mmrot4");
    loadScript("/js/regatta-slot-card.js?v=" + JS_VER).then(function () {
      var wx = document.getElementById(WX_ID);
      if (wx && typeof window.ssaMountWeatherCard === "function") {
        window.ssaMountWeatherCard(wx, { club: "HMYC", slug: "agromet-midmar", role: "venue" });
      }
    });"""
    new_boot = """    loadScript("/js/midmar-leaderboard.js?v=mmlb16");
    if (hasWxCam()) {
    loadScript("/js/midmar-media-rotate.js?v=mmrot4");
    loadScript("/js/regatta-slot-card.js?v=" + JS_VER).then(function () {
      var wx = document.getElementById(WX_ID);
      if (wx && typeof window.ssaMountWeatherCard === "function") {
        window.ssaMountWeatherCard(wx, { club: "HMYC", slug: "agromet-midmar", role: "venue" });
      }
    });
    }"""
    if "if (hasWxCam()) {\n    loadScript(\"/js/midmar-media-rotate.js" not in text:
        must_contain(text, old_boot, "midmar-live-media.js boot weather")
        text = text.replace(old_boot, new_boot, 1)
    return text


def patch_api(text: str) -> str:
    if f'str(regatta_id) == "{SLUG}"' in text:
        return text
    dart = (
        f'        elif str(regatta_id).startswith("{DART}"):\n'
        "            # Same HMYC cards + Cape Classic club-score-edit (DH/SH).\n"
    )
    must_contain(text, dart, "api.py Dart card branch")
    # Insert 420 branch immediately after the Dart mm_card_script line.
    marker = (
        "            mm_card_script = '<script src=\"/js/midmar-live-media.js?v=midmarwx55dart2\" defer></script>"
        "<script src=\"/js/midmar-leaderboard.js?v=mmlb16dart1\" defer></script>"
        "<script src=\"/js/midmar-media-rotate.js?v=mmrot4\" defer></script>"
        "<script src=\"/js/club-score-edit.js?v=ccr24\" defer></script>'\n"
    )
    must_contain(text, marker, "api.py Dart mm_card_script")
    return text.replace(marker, marker + API_ELIF, 1)


def write_if_changed(path: str, new: str) -> bool:
    with open(path, "r", encoding="utf-8") as f:
        old = f.read()
    if old == new:
        print(f"unchanged {path}")
        return False
    with open(path, "w", encoding="utf-8") as f:
        f.write(new)
    print(f"patched  {path}")
    return True


def main() -> int:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = f"/root/prechange/tsc420_cards_{ts}"
    for path in (API, LB_JS, MEDIA_JS):
        print("backup", backup(path, dest))

    lb = patch_leaderboard(open(LB_JS, encoding="utf-8").read())
    media = patch_live_media(open(MEDIA_JS, encoding="utf-8").read())
    api = patch_api(open(API, encoding="utf-8").read())

    write_if_changed(LB_JS, lb)
    write_if_changed(MEDIA_JS, media)

    subprocess.check_call(["chattr", "-i", API])
    try:
        write_if_changed(API, api)
    finally:
        subprocess.check_call(["chattr", "+i", API])

    if SLUG not in open(API, encoding="utf-8").read():
        raise SystemExit("ERROR: 420 elif missing from api.py after patch")
    if f"|| rid === '{SLUG}'" not in open(LB_JS, encoding="utf-8").read():
        raise SystemExit("ERROR: 420 missing from leaderboard onMidmar")
    if "function hasWxCam()" not in open(MEDIA_JS, encoding="utf-8").read():
        raise SystemExit("ERROR: hasWxCam missing from live-media.js")
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
