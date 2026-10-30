#!/usr/bin/env python3
"""Force Dam Bottle media card to the Dart compact Event Reels strip. No api.py."""
from pathlib import Path
import hashlib

DAM = "2026-10-10-hmyc-dam-bottle-sprints"
DART = "2026-09-24-hmyc-dart-18-nationals"
GOLD = "9c1eea9a2bebfd02125c8eb5c133b776fd0cf06ca67e066a09a293f77857d32b"


def write_both(name, text):
    for root in (Path("/var/www/sailingsa/js"), Path("/var/www/sailingsa/frontend/js")):
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        print("wrote", p, p.stat().st_size)


# 1) Show compact Event Reels brand on Dam Bottle (same CSS as Dart).
live = Path("/var/www/sailingsa/js/midmar-live-media.js")
t = live.read_text(encoding="utf-8")
old = (
    ".mm-lipton-reels[data-regatta-id^='2026-09-24-hmyc-dart-18-nationals'] "
    ".mm-lipton-reels-brand{display:block!important;cursor:pointer;}"
)
new = (
    ".mm-lipton-reels[data-regatta-id^='2026-09-24-hmyc-dart-18-nationals'] "
    ".mm-lipton-reels-brand,"
    ".regatta-page > .midmar-live-media .mm-lipton-reels[data-regatta-id^='2026-10-10-hmyc-dam-bottle-sprints'] "
    ".mm-lipton-reels-brand{display:block!important;cursor:pointer;}"
)
old_esc = old.replace("'", "\\'")
new_esc = new.replace("'", "\\'")
if DAM + "'] .mm-lipton-reels-brand{display:block" in t.replace("\\'", "'"):
    print("brand css already has dam")
elif old_esc in t:
    t = t.replace(old_esc, new_esc, 1)
elif old in t:
    t = t.replace(old, new, 1)
else:
    raise SystemExit("brand css not found")

# Keep Dam Bottle out of Dart expanded-hero; compact HTML already cloned.
write_both("midmar-live-media.js", t)

# 2) Reels card: Dam Bottle is compact Event Reels + WhatsApp clips, not Dart expanded live.
reels = Path("/var/www/sailingsa/js/mm-lipton-reels-card.js")
r = reels.read_text(encoding="utf-8")
old_fn = (
    "  function isDartNats() {\n"
    "    var root = cardEl();\n"
    "    var id = (root && root.getAttribute('data-regatta-id')) || '';\n"
    "    return id.indexOf('2026-09-24-hmyc-dart-18-nationals') === 0 "
    "|| id.indexOf('2026-10-10-hmyc-dam-bottle-sprints') === 0;\n"
    "  }\n"
)
new_fn = (
    "  function isDartNats() {\n"
    "    var root = cardEl();\n"
    "    var id = (root && root.getAttribute('data-regatta-id')) || '';\n"
    "    return id.indexOf('2026-09-24-hmyc-dart-18-nationals') === 0;\n"
    "  }\n"
    "  function isDamBottle() {\n"
    "    var root = cardEl();\n"
    "    var id = (root && root.getAttribute('data-regatta-id')) || '';\n"
    "    return id.indexOf('2026-10-10-hmyc-dam-bottle-sprints') === 0;\n"
    "  }\n"
    "  function isHmycCompact() {\n"
    "    return isDartNats() || isDamBottle();\n"
    "  }\n"
)
if "function isDamBottle()" in r:
    print("isDamBottle already present")
elif old_fn in r:
    r = r.replace(old_fn, new_fn, 1)
else:
    # dart-only already
    old_fn2 = (
        "  function isDartNats() {\n"
        "    var root = cardEl();\n"
        "    var id = (root && root.getAttribute('data-regatta-id')) || '';\n"
        "    return id.indexOf('2026-09-24-hmyc-dart-18-nationals') === 0;\n"
        "  }\n"
    )
    if old_fn2 in r and "function isDamBottle()" not in r:
        r = r.replace(old_fn2, new_fn, 1)
    else:
        raise SystemExit("isDartNats block not found")

# Pull WhatsApp/mm-clips into the compact rail (same extra fetch Dart uses).
r = r.replace(
    "      if (isDartNats()) {\n        jobs.push(",
    "      if (isDartNats() || isDamBottle()) {\n        jobs.push(",
    1,
)
# Same compact thumb chrome as Dart.
r = r.replace(
    "    if (isDartNats()) {\n      root.style.height = '';",
    "    if (isHmycCompact()) {\n      root.style.height = '';",
    1,
)
write_both("mm-lipton-reels-card.js", r)

api = Path("/var/www/sailingsa/api/api.py").read_bytes()
digest = hashlib.sha256(api).hexdigest()
if digest != GOLD or len(api) != 3953427:
    raise SystemExit(f"api.py changed unexpectedly {digest} {len(api)}")
print("gold api.py unchanged", digest, len(api))
