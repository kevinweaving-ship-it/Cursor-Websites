#!/usr/bin/env python3
"""Hard-lock Cape Classic weather card format when MM live expands.

wx1 stopped copying MM height, but the gauge still sized to clientHeight
and .card/grid stretch could still blow the compass. Freeze 122px layout.
"""
from pathlib import Path
import sys

API = Path("/var/www/sailingsa/api/api.py")
JS = Path("/var/www/sailingsa/js/regatta-slot-card.js")

API_REPLACEMENTS = [
    (
        "regatta-slot-card.js?v=20260912wx1",
        "regatta-slot-card.js?v=20260912wx2",
    ),
]

JS_REPLACEMENTS = [
    (
        '  var JS_VER = "20260912wx1";',
        '  var JS_VER = "20260912wx2";',
    ),
    (
        '''      ".ssa-regatta-slot-card{display:flex;width:100%;order:2;margin:10px 0 0;padding:0;box-sizing:border-box;height:122px!important;min-height:122px!important;max-height:122px!important;flex:0 0 122px;background:#fff;border:1.5px solid #1a2750;border-radius:8px;box-shadow:0 1px 3px rgba(0,31,63,.08);overflow:hidden;}",''',
        '''      ".ssa-regatta-slot-card{display:flex;width:100%;order:2;align-self:start;margin:10px 0 0;padding:0;box-sizing:border-box;height:122px!important;min-height:122px!important;max-height:122px!important;flex:0 0 122px!important;background:#fff;border:1.5px solid #1a2750;border-radius:8px;box-shadow:0 1px 3px rgba(0,31,63,.08);overflow:hidden;}",
      ".regatta-page:has(.mm-lipton-reels--expanded) .ssa-regatta-slot-card{height:122px!important;min-height:122px!important;max-height:122px!important;flex:0 0 122px!important;align-self:start!important;}",''',
    ),
    (
        '''      ".ssa-regatta-slot-card .wx-wp-comp{flex:0 0 auto;height:100%;aspect-ratio:1/1;overflow:visible;}",''',
        '''      ".ssa-regatta-slot-card .wx-wp-comp{flex:0 0 122px;width:122px!important;height:122px!important;max-width:122px;max-height:122px;aspect-ratio:1/1;overflow:hidden;}",''',
    ),
    (
        '''  function fitGauge(slot) {
    var comp = slot && slot.querySelector(".wx-wp-comp");
    if (!slot || !comp) return;
    var h = slot.clientHeight;
    if (h > 0) {
      comp.style.height = h + "px";
      comp.style.width = h + "px";
    }
  }''',
        '''  function fitGauge(slot) {
    var comp = slot && slot.querySelector(".wx-wp-comp");
    if (!slot || !comp) return;
    slot.style.height = "122px";
    slot.style.minHeight = "122px";
    slot.style.maxHeight = "122px";
    comp.style.height = "122px";
    comp.style.width = "122px";
    comp.style.maxHeight = "122px";
    comp.style.maxWidth = "122px";
  }''',
    ),
    (
        '''    syncToMarine(el, marine);
    window.addEventListener("resize", function () { fitGauge(el); });''',
        '''    syncToMarine(el, marine);
    window.addEventListener("resize", function () { fitGauge(el); });
    if (typeof MutationObserver === "function") {
      new MutationObserver(function () { fitGauge(el); }).observe(marine, {
        attributes: true,
        attributeFilter: ["class"]
      });
    }''',
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
