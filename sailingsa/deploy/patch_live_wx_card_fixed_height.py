#!/usr/bin/env python3
"""Weather card must not grow when MM live/reels expand.

regatta-slot-card.js copied the MM card height via ResizeObserver.
Lock the Zeekoevlei wind card at 122px always.
"""
from pathlib import Path
import sys

API = Path("/var/www/sailingsa/api/api.py")
JS = Path("/var/www/sailingsa/js/regatta-slot-card.js")

API_REPLACEMENTS = [
    (
        'regatta-slot-card.js?v=20260911w2s11',
        'regatta-slot-card.js?v=20260912wx1',
    ),
]

JS_REPLACEMENTS = [
    (
        '  var JS_VER = "20260911w2s11";',
        '  var JS_VER = "20260912wx1";',
    ),
    (
        '''      ".ssa-regatta-slot-card{display:flex;width:100%;order:2;margin:10px 0 0;padding:0;box-sizing:border-box;height:122px;min-height:122px;background:#fff;border:1.5px solid #1a2750;border-radius:8px;box-shadow:0 1px 3px rgba(0,31,63,.08);overflow:hidden;}",''',
        '''      ".ssa-regatta-slot-card{display:flex;width:100%;order:2;margin:10px 0 0;padding:0;box-sizing:border-box;height:122px!important;min-height:122px!important;max-height:122px!important;flex:0 0 122px;background:#fff;border:1.5px solid #1a2750;border-radius:8px;box-shadow:0 1px 3px rgba(0,31,63,.08);overflow:hidden;}",''',
    ),
    (
        '''  function syncToMarine(slot, marine) {
    if (!slot || !marine) return;
    var h = Math.round(marine.getBoundingClientRect().height);
    if (h > 0) {
      slot.style.height = h + "px";
      slot.style.minHeight = h + "px";
    }
    var mt = getComputedStyle(marine).marginTop;
    if (mt) slot.style.marginTop = mt;
    fitGauge(slot);
  }''',
        '''  function syncToMarine(slot, marine) {
    if (!slot || !marine) return;
    slot.style.height = "122px";
    slot.style.minHeight = "122px";
    slot.style.maxHeight = "122px";
    var mt = getComputedStyle(marine).marginTop;
    if (mt) slot.style.marginTop = mt;
    fitGauge(slot);
  }''',
    ),
    (
        '''    syncToMarine(el, marine);
    if (typeof ResizeObserver === "function") {
      var ro = new ResizeObserver(function () { syncToMarine(el, marine); });
      ro.observe(marine);
    }
    window.addEventListener("resize", function () { syncToMarine(el, marine); });''',
        '''    syncToMarine(el, marine);
    window.addEventListener("resize", function () { fitGauge(el); });''',
    ),
]


def apply(path: Path, reps: list) -> None:
    text = path.read_text(encoding="utf-8")
    for i, (old, new) in enumerate(reps, start=1):
        n = text.count(old)
        if n != 1:
            raise SystemExit(f"{path}: replacement {i}: expected 1 match, found {n}")
        text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")
    print("patched", path)


def main() -> int:
    api = Path(sys.argv[1]) if len(sys.argv) > 1 else API
    js = Path(sys.argv[2]) if len(sys.argv) > 2 else JS
    apply(js, JS_REPLACEMENTS)
    apply(api, API_REPLACEMENTS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
