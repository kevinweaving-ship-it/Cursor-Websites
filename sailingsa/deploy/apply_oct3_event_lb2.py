#!/usr/bin/env python3
from pathlib import Path

JS = Path("/var/www/sailingsa/js/midmar-leaderboard.js")
OLD = """  function onMidmar() {
    return !!document.getElementById(CARD_ID);
  }"""
NEW = """  function onMidmar() {
    if (document.getElementById(CARD_ID)) return true;
    var rid = currentRid();
    return rid === RID || rid === '2026-09-24-hmyc-dart-18-nationals';
  }"""


def main() -> None:
    js = JS.read_text()
    if "rid === RID || rid === '2026-09-24-hmyc-dart-18-nationals'" in js and "getElementById(CARD_ID)" in js[js.find("function onMidmar") : js.find("function onMidmar") + 280]:
        if OLD not in js:
            print("JS_ALREADY")
            return
    if OLD not in js:
        i = js.find("function onMidmar")
        print("MARK_MISSING")
        print(js[i : i + 200] if i >= 0 else "NO")
        raise SystemExit(2)
    JS.write_text(js.replace(OLD, NEW, 1))
    print("JS_OK")


if __name__ == "__main__":
    main()
