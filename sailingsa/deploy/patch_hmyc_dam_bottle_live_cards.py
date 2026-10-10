#!/usr/bin/env python3
"""Patch live HMYC card JS so Dam Bottle Sprints gets Dart Wind/Media/Cam."""
from pathlib import Path
import hashlib
import re

DAM = "2026-10-10-hmyc-dam-bottle-sprints"
MARKER = "DAM_BOTTLE_HMYC_LIVE_CARDS_v1"
GOLD = "9c1eea9a2bebfd02125c8eb5c133b776fd0cf06ca67e066a09a293f77857d32b"
BOOT_VER = "dbs40"


def must_write(path, text):
    p = Path(path)
    p.write_text(text, encoding="utf-8")
    print("patched", p, "bytes", p.stat().st_size)


def require(hay, needle, label):
    if needle not in hay:
        raise SystemExit(f"{label}: missing expected text")


def write_both(web, text):
    must_write(web, text)
    fp = Path(str(web).replace("/var/www/sailingsa/js/", "/var/www/sailingsa/frontend/js/"))
    if fp.is_file():
        must_write(fp, text)


# midmar-live-media.js — same venue cards as Dart, no Dart theme song
p = Path("/var/www/sailingsa/js/midmar-live-media.js")
t = p.read_text(encoding="utf-8")
if DAM in t and f'currentRid() === "{DAM}"' in t:
    print("midmar-live-media.js already has Dam Bottle")
else:
    old = 'return rid === RID || rid === "2026-09-24-hmyc-dart-18-nationals";'
    new = (
        'return rid === RID || rid === "2026-09-24-hmyc-dart-18-nationals" '
        f'|| rid === "{DAM}";'
    )
    require(t, old, "midmar-live-media.js onMidmar/hasWxCam")
    t = t.replace(old, new)
    t = t.replace(
        "    if (isDartNats()) {\n"
        "      mm.setAttribute(\n"
        '        "data-mm-initial",\n'
        '        JSON.stringify({ enabled: true, feed_source: "hmyc", fb_page: "henleymidmaryachtclub", videos: [] })',
        f'    if (isDartNats() || currentRid() === "{DAM}") {{\n'
        "      mm.setAttribute(\n"
        '        "data-mm-initial",\n'
        '        JSON.stringify({ enabled: true, feed_source: "hmyc", fb_page: "henleymidmaryachtclub", videos: [] })',
    )
    t = t.replace(
        "    if (isDartNats()) {\n"
        "    playDartTheme();\n"
        '    loadCss("/css/mm-lipton-reels.css?v=hmycdart25");',
        f'    if (isDartNats() || currentRid() === "{DAM}") {{\n'
        "    if (isDartNats()) playDartTheme();\n"
        '    loadCss("/css/mm-lipton-reels.css?v=hmycdart25");',
    )
    require(t, DAM, "midmar-live-media.js dam slug")
    write_both(p, t)

# midmar-leaderboard.js
p = Path("/var/www/sailingsa/js/midmar-leaderboard.js")
t = p.read_text(encoding="utf-8")
if DAM in t:
    print("midmar-leaderboard.js already has Dam Bottle")
else:
    old = "    return rid === RID || rid === '2026-09-24-hmyc-dart-18-nationals';"
    new = (
        "    return rid === RID || rid === '2026-09-24-hmyc-dart-18-nationals' "
        f"|| rid === '{DAM}';"
    )
    require(t, old, "midmar-leaderboard.js onMidmar")
    t = t.replace(old, new)
    write_both(p, t)

# club-score-edit.js — Dam Bottle slug + skip auto R1 (PY×ET fills place)
p = Path("/var/www/sailingsa/js/club-score-edit.js")
t = p.read_text(encoding="utf-8")
changed = False
if DAM not in t:
    old = (
        '    path.indexOf("2026-09-13-zvyc-cape-classic") === -1 &&\n'
        '    path.indexOf("2026-09-24-hmyc-dart-18-nationals") === -1'
    )
    new = (
        '    path.indexOf("2026-09-13-zvyc-cape-classic") === -1 &&\n'
        '    path.indexOf("2026-09-24-hmyc-dart-18-nationals") === -1 &&\n'
        f'    path.indexOf("{DAM}") === -1'
    )
    require(t, old, "club-score-edit.js slug gate")
    t = t.replace(old, new)
    changed = True
else:
    print("club-score-edit.js slug already has Dam Bottle")
if 'data-auto-from-et' not in t:
    needle = "    if (!/^R\\d+$/.test(race)) return;\n"
    insert = needle + '    if (td.getAttribute("data-auto-from-et") === "1") return;\n'
    require(t, needle, "club-score-edit.js wireCell race gate")
    t = t.replace(needle, insert, 1)
    changed = True
else:
    print("club-score-edit.js already skips auto-from-et R1")
if changed:
    write_both(p, t)

# mm-lipton-reels-card.js — HMYC Facebook media feed
p = Path("/var/www/sailingsa/js/mm-lipton-reels-card.js")
t = p.read_text(encoding="utf-8")
if DAM in t:
    print("mm-lipton-reels-card.js already has Dam Bottle")
    t2 = t.replace(
        "if (isCapeClassic() || isDartNats()) pollMs = 2000;",
        "if (isCapeClassic() || isDartNats() || isDamBottle()) pollMs = 2000;",
    )
    if t2 != t:
        write_both(p, t2)
        t = t2
else:
    old = "    return id.indexOf('2026-09-24-hmyc-dart-18-nationals') === 0;"
    new = (
        "    return id.indexOf('2026-09-24-hmyc-dart-18-nationals') === 0 "
        f"|| id.indexOf('{DAM}') === 0;"
    )
    require(t, old, "mm-lipton-reels-card.js isDartNats")
    t = t.replace(old, new, 1)
    write_both(p, t)

loader = f"""
/* {MARKER} */
(function () {{
  var path = String((window.location && window.location.pathname) || "")
    .replace(/\\/+$/, "")
    .toLowerCase();
  if (
    path !== "/regatta/{DAM}" &&
    path.indexOf("/regatta/{DAM}/") !== 0
  )
    return;
  if (!document.getElementById("dam-bottle-pre-css")) {{
    var hide = document.createElement("style");
    hide.id = "dam-bottle-pre-css";
    hide.textContent =
      '.fleet-section[data-block-id="{DAM}:open"]{{visibility:hidden!important}}' +
      'html[data-dbs-ready="1"] .fleet-section[data-block-id="{DAM}:open"]{{visibility:visible!important}}';
    (document.head || document.documentElement).appendChild(hide);
  }}
  if (document.querySelector('script[src*="hmyc-dam-bottle-live-boot.js"]')) return;
  var s = document.createElement("script");
  s.src = "/js/hmyc-dam-bottle-live-boot.js?v={BOOT_VER}";
  s.defer = true;
  document.head.appendChild(s);
}})();
"""


def replace_loader(text):
    start = text.find(f"/* {MARKER} */")
    if start < 0:
        return text.rstrip() + "\n" + loader
    end = text.find("})();", start)
    if end < 0:
        return text.rstrip() + "\n" + loader
    return text[:start] + loader.strip() + text[end + 5 :]


for dest in (
    Path("/var/www/sailingsa/js/regatta-pdf-share.js"),
    Path("/var/www/sailingsa/frontend/js/regatta-pdf-share.js"),
):
    if not dest.is_file():
        continue
    t = dest.read_text(encoding="utf-8")
    nxt = replace_loader(t)
    if nxt != t:
        must_write(dest, nxt)
    else:
        print("loader already", BOOT_VER, dest)

api = Path("/var/www/sailingsa/api/api.py").read_bytes()
digest = hashlib.sha256(api).hexdigest()
if digest != GOLD or len(api) != 3953427:
    raise SystemExit(f"api.py changed unexpectedly {digest} {len(api)}")
print("gold api.py unchanged", digest, len(api))
