#!/usr/bin/env python3
"""Leader Board Day = day inside the event, not days since start until today."""
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
JS = Path("/var/www/sailingsa/js/midmar-leaderboard.js")

OLD = """  function eventDay(rows) {
    var start = '';
    (rows || []).some(function (r) {
      start = ymdSlice(r.start_date || r.startDate);
      return !!start;
    });
    if (!start) return 0;
    var d0 = new Date(start + 'T12:00:00');
    var d1 = new Date(todayYmdSast() + 'T12:00:00');
    if (isNaN(d0.getTime()) || isNaN(d1.getTime())) return 0;
    var diff = Math.round((d1.getTime() - d0.getTime()) / 86400000);
    if (diff < 0) return 0;
    return diff + 1;
  }"""

NEW = """  function eventDay(rows) {
    var start = '';
    var end = '';
    (rows || []).some(function (r) {
      if (!start) start = ymdSlice(r.start_date || r.startDate);
      if (!end) end = ymdSlice(r.end_date || r.endDate);
      return !!start && !!end;
    });
    if (!start) return 0;
    var cap = todayYmdSast();
    if (end && end < cap) cap = end;
    var d0 = new Date(start + 'T12:00:00');
    var d1 = new Date(cap + 'T12:00:00');
    if (isNaN(d0.getTime()) || isNaN(d1.getTime())) return 0;
    var diff = Math.round((d1.getTime() - d0.getTime()) / 86400000);
    if (diff < 0) return 0;
    return diff + 1;
  }"""

OLD_VER = '<script src="/js/midmar-leaderboard.js?v=mmlb19card" defer></script>'
NEW_VER = '<script src="/js/midmar-leaderboard.js?v=mmlb20day" defer></script>'


def main() -> None:
    js = JS.read_text()
    if OLD not in js:
        i = js.find("function eventDay")
        print("JS_MARK")
        print(js[i : i + 520] if i >= 0 else "NO")
        if "end && end < cap" in js:
            print("JS_ALREADY")
        else:
            raise SystemExit(2)
    else:
        js = js.replace(OLD, NEW, 1)
        JS.write_text(js)
        print("JS_OK")

    t = API.read_text()
    if OLD_VER in t:
        API.write_text(t.replace(OLD_VER, NEW_VER, 1))
        print("API_VER_OK")
    elif NEW_VER in t:
        print("API_VER_ALREADY")
    else:
        i = t.find("mmlb19card")
        print("API_VER_MARK", i)
        print(t[i - 60 : i + 80] if i >= 0 else "NO")
        raise SystemExit(3)

    js2 = JS.read_text()
    print("CLAMP", "end && end < cap" in js2)
    print("TODAY_ONLY", "todayYmdSast() + 'T12:00:00'" in js2[js2.find("function eventDay") : js2.find("function eventDay") + 700])
    print("API_V20", "mmlb20day" in API.read_text())


if __name__ == "__main__":
    main()
