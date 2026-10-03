#!/usr/bin/env python3
"""Leader Board on event pages must be that event's podium, not Midmar."""
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
JS = Path("/var/www/sailingsa/js/midmar-leaderboard.js")

OLD_RID = """  function currentRid() {
    var path = String((window.location && window.location.pathname) || '')
      .replace(/\\/+$/, '')
      .toLowerCase();
    var m = path.match(/^\\/regatta\\/([^/]+)/);
    return m ? m[1] : RID;
  }
  function onMidmar() {
    var rid = currentRid();
    return rid === RID || rid === '2026-09-24-hmyc-dart-18-nationals' || rid === '2026-09-25-tsc-420-nationals';
  }"""

NEW_RID = """  function currentRid() {
    var path = String((window.location && window.location.pathname) || '')
      .replace(/\\/+$/, '')
      .toLowerCase();
    var m = path.match(/^\\/(?:regatta|event)\\/([^/]+)/);
    if (m && m[1]) return m[1];
    var el = document.querySelector('#midmar-leaderboard[data-regatta-id], [data-mm-lb-list], .regatta-page');
    var fromDom = '';
    if (el) fromDom = String(el.getAttribute('data-regatta-id') || '').trim();
    if (!fromDom) {
      var page = document.querySelector('[data-regatta-id]');
      if (page) fromDom = String(page.getAttribute('data-regatta-id') || '').trim();
    }
    return fromDom || '';
  }
  function onMidmar() {
    return !!document.getElementById(CARD_ID);
  }"""

OLD_API = '''        elif str(regatta_id) == "2026-09-25-tsc-420-nationals":
            # TSC: Leader Board + Media placeholders. No weather station, no live cam.
            mm_card = '<div id="midmar-live-media" class="midmar-live-media club-live-media" aria-label="Event media"><section id="midmar-leaderboard" class="card midmar-lb" aria-label="Leader Board"><h2 class="section-title">Leader Board</h2><p class="midmar-lb-sheet-note">Full Results sheet below on page</p><div class="midmar-lb-list" data-mm-lb-list><p class="midmar-lb-empty">Waiting for race scores</p></div></section><div class="midmar-mm-row"><section id="mmLiptonReels" class="card mm-lipton-reels mm-lipton-reels--compact" data-regatta-id="2026-09-25-tsc-420-nationals" data-media-wait="whatsapp"><div class="mm-lipton-reels-compact mm-lipton-reels-empty"><h2 class="section-title">Media</h2><p class="midmar-lb-empty">No media yet</p></div></section></div></div>'
            mm_card_script = ('<script src="/js/midmar-live-media.js?v=midmarwx60" defer></script>''<script src="/js/midmar-leaderboard.js?v=mmlb16tsc420" defer></script>')'''

NEW_API = '''        elif str(regatta_id) in (
            "2026-09-25-tsc-420-nationals",
            "2026-09-24-ayc-505-nationals",
            "2026-09-24-ayc-dabchick-gauteng-regionals",
        ):
            # Event Leader Board = this regatta's podium. Not Midmar.
            _lb_rid = str(regatta_id)
            mm_card = (
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
            )'''


def main() -> None:
    js = JS.read_text()
    if "mmlb18event" in js or "\\/(?:regatta|event)\\/" in js or "/(?:regatta|event)/" in js:
        print("JS_ALREADY")
    elif OLD_RID not in js:
        # show nearby for debug
        i = js.find("function currentRid")
        print("JS_MARK_MISSING")
        print(repr(js[i : i + 420]) if i >= 0 else "NO_FN")
        raise SystemExit(2)
    else:
        JS.write_text(js.replace(OLD_RID, NEW_RID, 1))
        print("JS_OK")

    t = API.read_text()
    if "mmlb18event" in t and "2026-09-24-ayc-505-nationals" in t[t.find("TSC: Leader Board") : t.find("TSC: Leader Board") + 800] if "TSC: Leader Board" in t else False:
        print("API_ALREADY")
    elif OLD_API not in t:
        i = t.find('elif str(regatta_id) == "2026-09-25-tsc-420-nationals"')
        print("API_MARK_MISSING")
        print(t[i : i + 500] if i >= 0 else "NO_ELIF")
        raise SystemExit(3)
    else:
        API.write_text(t.replace(OLD_API, NEW_API, 1))
        print("API_OK")

    js2 = JS.read_text()
    t2 = API.read_text()
    print("HAS_EVENT_PATH", "/(?:regatta|event)/" in js2 or "(?:regatta|event)" in js2)
    print("HAS_NO_MIDMAR_FALLBACK", "return m ? m[1] : RID" not in js2)
    print("HAS_505_CARD", "2026-09-24-ayc-505-nationals" in t2 and "mmlb18event" in t2)
    print("HAS_DAB_CARD", "2026-09-24-ayc-dabchick-gauteng-regionals" in t2)


if __name__ == "__main__":
    main()
