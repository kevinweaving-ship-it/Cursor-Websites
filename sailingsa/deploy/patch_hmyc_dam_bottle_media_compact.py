#!/usr/bin/env python3
"""Force Dam Bottle media strip to Event Reels + 5 compact reel slots. No api.py."""
from pathlib import Path
import hashlib

GOLD = "9c1eea9a2bebfd02125c8eb5c133b776fd0cf06ca67e066a09a293f77857d32b"


def write_both(name, text):
    for root in (Path("/var/www/sailingsa/js"), Path("/var/www/sailingsa/frontend/js")):
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        print("wrote", p, p.stat().st_size)


p = Path("/var/www/sailingsa/js/mm-lipton-reels-card.js")
t = p.read_text(encoding="utf-8")

old_ph = """  function placeholderCount(videos) {
    if (isMidmar()) {
      var n = 5 - Math.max((videos || []).length, 0);
      return n > 0 ? n : 0;
    }
    if (!isCapeClassic() || hasRealReels(videos)) return 0;
    if (isMobilePortrait()) return 0;
    return 4;
  }
"""
new_ph = """  function placeholderCount(videos) {
    if (isMidmar() || isDamBottle()) {
      var n = 5 - Math.max((videos || []).length, 0);
      return n > 0 ? n : 0;
    }
    if (!isCapeClassic() || hasRealReels(videos)) return 0;
    if (isMobilePortrait()) return 0;
    return 4;
  }
"""
if "isMidmar() || isDamBottle()" in t:
    print("placeholderCount already dam")
elif old_ph in t:
    t = t.replace(old_ph, new_ph, 1)
else:
    raise SystemExit("placeholderCount block not found")

old_fit = """    if (isCapeClassic() && !hasRealReels(reels) && !isMobilePortrait()) nFit = 5;
    if (isDartNats() && isMobilePortrait()) nFit = 1;
"""
new_fit = """    if ((isCapeClassic() || isDamBottle()) && !hasRealReels(reels) && !isMobilePortrait()) nFit = 5;
    if (isDamBottle()) nFit = 5;
    if (isDartNats() && isMobilePortrait()) nFit = 1;
"""
if "if (isDamBottle()) nFit = 5;" in t:
    print("nFit already forced")
elif old_fit in t:
    t = t.replace(old_fit, new_fit, 1)
else:
    raise SystemExit("nFit gate not found")

if "function isDamBottle()" not in t:
    raise SystemExit("isDamBottle missing — run media card patch first")

old_tiles = """    if (reels.length) {
      var show = reels;
      if (isDartNats() && isMobilePortrait()) show = reels.slice(0, 1);
      for (i = 0; i < show.length; i++) parts.push(compactTileHtml(show[i], videos, i === 0));
    } else {
      parts.push(emptyReelSlotHtml());
    }
"""
new_tiles = """    if (reels.length) {
      var show = reels;
      if (isDartNats() && isMobilePortrait()) show = reels.slice(0, 1);
      for (i = 0; i < show.length; i++) parts.push(compactTileHtml(show[i], videos, i === 0));
    } else if (!isDamBottle()) {
      parts.push(emptyReelSlotHtml());
    }
"""
if "else if (!isDamBottle())" in t:
    print("compactTilesHtml already dam")
elif old_tiles in t:
    t = t.replace(old_tiles, new_tiles, 1)
else:
    print("WARN compactTilesHtml block not found")

write_both("mm-lipton-reels-card.js", t)

api = Path("/var/www/sailingsa/api/api.py").read_bytes()
digest = hashlib.sha256(api).hexdigest()
if digest != GOLD or len(api) != 3953427:
    raise SystemExit(f"api.py changed unexpectedly {digest} {len(api)}")
print("gold api.py unchanged", digest, len(api))
