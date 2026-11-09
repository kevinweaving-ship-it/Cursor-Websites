#!/usr/bin/env python3
"""Make Dam Bottle use the Dart event-URL stack. Does not touch api.py."""
from pathlib import Path
import hashlib

DAM = "2026-10-10-hmyc-dam-bottle-sprints"
DART = "2026-09-24-hmyc-dart-18-nationals"
GOLD = "9c1eea9a2bebfd02125c8eb5c133b776fd0cf06ca67e066a09a293f77857d32b"


def write_both(name, text):
    for root in (Path("/var/www/sailingsa/js"), Path("/var/www/sailingsa/frontend/js")):
        p = root / name
        if p.is_file() or root == Path("/var/www/sailingsa/js"):
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")
            print("wrote", p, p.stat().st_size)


p = Path("/var/www/sailingsa/js/midmar-live-media.js")
t = p.read_text(encoding="utf-8")

old_brand = (
    ".mm-lipton-reels[data-regatta-id^='2026-09-24-hmyc-dart-18-nationals'] "
    ".mm-lipton-reels-brand{display:block!important;cursor:pointer;}"
)
new_brand = (
    ".mm-lipton-reels[data-regatta-id^='2026-09-24-hmyc-dart-18-nationals'] "
    ".mm-lipton-reels-brand,"
    ".mm-lipton-reels[data-regatta-id^='2026-10-10-hmyc-dam-bottle-sprints'] "
    ".mm-lipton-reels-brand{display:block!important;cursor:pointer;}"
)
# File stores this inside a JS string with escaped quotes.
old_brand_esc = old_brand.replace("'", "\\'")
new_brand_esc = new_brand.replace("'", "\\'")
if old_brand_esc in t:
    t = t.replace(old_brand_esc, new_brand_esc, 1)
elif old_brand in t:
    t = t.replace(old_brand, new_brand, 1)
elif DAM in t and "mm-lipton-reels-brand{display:block" in t:
    print("brand css already updated")
else:
    raise SystemExit("brand css gate not found")

old_img = '<img src="/img/dart-event-reels.jpg?v=dartreel3" alt="Event Reels" width="320" height="213" decoding="async">'
new_img = (
    '<img src="'
    + '" + (currentRid() === "'
    + DAM
    + '" ? "/img/hmyc-event-reels.png?v=dbsreel1" : "/img/dart-event-reels.jpg?v=dartreel3") + '
    + '" alt="Event Reels" width="320" height="213" decoding="async">'
)
if "hmyc-event-reels.png" not in t:
    if old_img not in t:
        raise SystemExit("event reels img not found")
    t = t.replace(old_img, new_img, 1)

write_both("midmar-live-media.js", t)

# Keep Dart expanded-hero logic off Dam Bottle (compact Event Reels + WhatsApp clips).
p = Path("/var/www/sailingsa/js/mm-lipton-reels-card.js")
t = p.read_text(encoding="utf-8")
old = (
    "    return id.indexOf('2026-09-24-hmyc-dart-18-nationals') === 0 "
    "|| id.indexOf('2026-10-10-hmyc-dam-bottle-sprints') === 0;"
)
new = "    return id.indexOf('2026-09-24-hmyc-dart-18-nationals') === 0;"
if old in t:
    t = t.replace(old, new, 1)
    write_both("mm-lipton-reels-card.js", t)
    print("reverted dam from isDartNats in reels card")
else:
    print("reels isDartNats already dart-only")

api = Path("/var/www/sailingsa/api/api.py").read_bytes()
digest = hashlib.sha256(api).hexdigest()
if digest != GOLD or len(api) != 3953427:
    raise SystemExit(f"api.py changed unexpectedly {digest} {len(api)}")
print("gold api.py unchanged", digest, len(api))
