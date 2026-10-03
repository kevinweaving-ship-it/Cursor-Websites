#!/usr/bin/env python3
"""Restore Leader Board .card box on 420 / 505 / Dabchick (no Midmar media wrap)."""
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
JS = Path("/var/www/sailingsa/js/midmar-leaderboard.js")

OLD_CSS = """      '.regatta-page > .midmar-live-media > #midmar-leaderboard.card,' +
      '.regatta-page > .midmar-live-media > #ssa-regatta-slot-card,' +
      '.regatta-page > .midmar-live-media > .mm-lipton-reels,' +
      '.regatta-page > .midmar-live-media .midmar-mm-row > .mm-lipton-reels{' +
      'border:2px solid #001f3f!important;border-radius:8px!important;' +
      'box-shadow:0 1px 3px rgba(0,31,63,0.08)!important;' +
      'width:100%!important;max-width:100%!important;box-sizing:border-box!important;' +
      'margin-left:0!important;margin-right:0!important;}' +
      '.regatta-page > .midmar-live-media > #midmar-leaderboard.card{' +
      'order:0;margin:10px 0 0;padding:6px 10px;background:#fff;overflow:hidden;}' +"""

NEW_CSS = """      '.regatta-page > #midmar-leaderboard.card,' +
      '.regatta-page > .midmar-live-media > #midmar-leaderboard.card,' +
      '.regatta-page > .midmar-live-media > #ssa-regatta-slot-card,' +
      '.regatta-page > .midmar-live-media > .mm-lipton-reels,' +
      '.regatta-page > .midmar-live-media .midmar-mm-row > .mm-lipton-reels{' +
      'border:2px solid #001f3f!important;border-radius:8px!important;' +
      'box-shadow:0 1px 3px rgba(0,31,63,0.08)!important;' +
      'width:100%!important;max-width:100%!important;box-sizing:border-box!important;' +
      'margin-left:0!important;margin-right:0!important;}' +
      '.regatta-page > #midmar-leaderboard.card,' +
      '.regatta-page > .midmar-live-media > #midmar-leaderboard.card{' +
      'order:0;margin:10px 0 0;padding:6px 10px;background:#fff;overflow:hidden;}' +"""

OLD_CSS_ID = "  var CSS_ID = 'midmar-leaderboard-css-v11';"
NEW_CSS_ID = "  var CSS_ID = 'midmar-leaderboard-css-v12';"
OLD_CLEAN = "['midmar-leaderboard-css', 'midmar-leaderboard-css-v4', 'midmar-leaderboard-css-v5', 'midmar-leaderboard-css-v6', 'midmar-leaderboard-css-v7', 'midmar-leaderboard-css-v8', 'midmar-leaderboard-css-v9', 'midmar-leaderboard-css-v10']"
NEW_CLEAN = "['midmar-leaderboard-css', 'midmar-leaderboard-css-v4', 'midmar-leaderboard-css-v5', 'midmar-leaderboard-css-v6', 'midmar-leaderboard-css-v7', 'midmar-leaderboard-css-v8', 'midmar-leaderboard-css-v9', 'midmar-leaderboard-css-v10', 'midmar-leaderboard-css-v11']"

OLD_VER = '<script src="/js/midmar-leaderboard.js?v=mmlb18event" defer></script>'
NEW_VER = '<script src="/js/midmar-leaderboard.js?v=mmlb19card" defer></script>'


def main() -> None:
    js = JS.read_text()
    if OLD_CSS not in js:
        i = js.find(".regatta-page > .midmar-live-media > #midmar-leaderboard.card")
        print("JS_CSS_MARK")
        print(repr(js[i : i + 400]) if i >= 0 else "NO")
        if ".regatta-page > #midmar-leaderboard.card" in js:
            print("JS_CSS_ALREADY")
        else:
            raise SystemExit(2)
    else:
        js = js.replace(OLD_CSS, NEW_CSS, 1)
        print("JS_CSS_OK")
    if OLD_CSS_ID in js:
        js = js.replace(OLD_CSS_ID, NEW_CSS_ID, 1)
        print("JS_CSSID_OK")
    elif NEW_CSS_ID in js:
        print("JS_CSSID_ALREADY")
    else:
        print("JS_CSSID_SKIP")
    if OLD_CLEAN in js:
        js = js.replace(OLD_CLEAN, NEW_CLEAN, 1)
        print("JS_CLEAN_OK")
    JS.write_text(js)

    t = API.read_text()
    if OLD_VER in t:
        API.write_text(t.replace(OLD_VER, NEW_VER, 1))
        print("API_VER_OK")
    elif NEW_VER in t:
        print("API_VER_ALREADY")
    else:
        i = t.find("mmlb18event")
        print("API_VER_MARK", i)
        print(t[i - 80 : i + 80] if i >= 0 else "NO")
        raise SystemExit(3)

    js2 = JS.read_text()
    print("HAS_DIRECT", ".regatta-page > #midmar-leaderboard.card" in js2)
    print("HAS_WRAP", ".regatta-page > .midmar-live-media > #midmar-leaderboard.card" in js2)
    print("CSS_V12", "midmar-leaderboard-css-v12" in js2)
    print("API_V19", "mmlb19card" in API.read_text())


if __name__ == "__main__":
    main()
