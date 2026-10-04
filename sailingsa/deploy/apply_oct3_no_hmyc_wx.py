#!/usr/bin/env python3
"""Strip HMYC Midmar wind/cam/media off TSC 420, 505, Dabchick event pages."""
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
JS = Path("/var/www/sailingsa/js/midmar-live-media.js")

OLD_API = """            mm_card = (
                '<div id="midmar-live-media" class="midmar-live-media club-live-media" aria-label="Event media">'
                '<section id="midmar-leaderboard" class="card midmar-lb" aria-label="Leader Board" data-regatta-id="'
                + _lb_rid
                + '"><h2 class="section-title">Leader Board</h2>'
                '<p class="midmar-lb-sheet-note">Full Results sheet below on page</p>'
                '<div class="midmar-lb-list" data-mm-lb-list><p class="midmar-lb-empty">Waiting for race scores</p></div></section>'
                '<div class="midmar-mm-row"><section id="mmLiptonReels" class="card mm-lipton-reels mm-lipton-reels--compact" data-regatta-id="'
                + _lb_rid
                + '" data-media-wait="whatsapp"><div class="mm-lipton-reels-compact mm-lipton-reels-empty">'
                '<h2 class="section-title">Media</h2><p class="midmar-lb-empty">No media yet</p></div></section></div></div>'
            )
            mm_card_script = (
                '<script src="/js/midmar-live-media.js?v=midmarwx60" defer></script>'
                '<script src="/js/midmar-leaderboard.js?v=mmlb18event" defer></script>'
            )"""

NEW_API = """            mm_card = (
                '<section id="midmar-leaderboard" class="card midmar-lb" aria-label="Leader Board" data-regatta-id="'
                + _lb_rid
                + '"><h2 class="section-title">Leader Board</h2>'
                '<p class="midmar-lb-sheet-note">Full Results sheet below on page</p>'
                '<div class="midmar-lb-list" data-mm-lb-list><p class="midmar-lb-empty">Waiting for race scores</p></div></section>'
            )
            mm_card_script = (
                '<script src="/js/midmar-leaderboard.js?v=mmlb18event" defer></script>'
            )"""

OLD_JS = """  function currentRid() {
    var path = String((window.location && window.location.pathname) || "")
      .replace(/\\/+$/, "")
      .toLowerCase();
    var m = path.match(/^\\/regatta\\/([^/]+)/);
    return m ? m[1] : RID;
  }
  function onMidmar() {
    var rid = currentRid();
    return rid === RID || rid === "2026-09-24-hmyc-dart-18-nationals" || rid === "2026-09-25-tsc-420-nationals";
  }"""

NEW_JS = """  function currentRid() {
    var path = String((window.location && window.location.pathname) || "")
      .replace(/\\/+$/, "")
      .toLowerCase();
    var m = path.match(/^\\/(?:regatta|event)\\/([^/]+)/);
    if (m && m[1]) return m[1];
    return "";
  }
  function onMidmar() {
    var rid = currentRid();
    return rid === RID || rid === "2026-09-24-hmyc-dart-18-nationals";
  }"""


def main() -> None:
    t = API.read_text()
    if "midmar-live-media.js?v=midmarwx60" not in t[t.find("Event Leader Board") : t.find("Event Leader Board") + 1800] if "Event Leader Board" in t else True:
        if OLD_API not in t:
            print("API_ALREADY_OR_MISSING")
        else:
            pass
    if OLD_API in t:
        API.write_text(t.replace(OLD_API, NEW_API, 1))
        print("API_OK")
    else:
        i = t.find("Event Leader Board = this regatta")
        print("API_MARK")
        print(t[i : i + 900] if i >= 0 else "NO")
        if "midmar-live-media.js?v=midmarwx60" in t[i : i + 1600] if i >= 0 else False:
            raise SystemExit(2)

    js = JS.read_text()
    if OLD_JS in js:
        JS.write_text(js.replace(OLD_JS, NEW_JS, 1))
        print("JS_OK")
    else:
        i = js.find("function currentRid")
        print("JS_MARK")
        print(repr(js[i : i + 420]) if i >= 0 else "NO")
        if "2026-09-25-tsc-420-nationals" in js[i : i + 500] if i >= 0 else False:
            raise SystemExit(3)
        print("JS_SKIP")

    t2 = API.read_text()
    start = t2.find("Event Leader Board")
    chunk = t2[start : start + 1200]
    print("HAS_WX_SCRIPT", "midmar-live-media.js" in chunk)
    print("HAS_HMYC_MEDIA", "mmLiptonReels" in chunk)
    print("HAS_LB_ONLY", "midmar-leaderboard" in chunk and "midmar-leaderboard.js" in chunk)
    js2 = JS.read_text()
    print("JS_NO_420", "2026-09-25-tsc-420-nationals" not in js2[js2.find("function onMidmar") : js2.find("function onMidmar") + 280])
    print("JS_EVENT_PATH", "(?:regatta|event)" in js2)


if __name__ == "__main__":
    main()
