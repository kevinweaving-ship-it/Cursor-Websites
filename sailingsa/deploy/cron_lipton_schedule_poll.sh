#!/bin/bash
# Poll Lipton live-race so SA schedule applies without a browser.
# Does NOT set race_key. 10:00 wake / 12:00 arm / 17:00 close come from api.py.
set -eu
RID="2026-08-29-lipton-challenge-cup"
DAY="$(TZ=Africa/Johannesburg date +%Y-%m-%d)"
case "$DAY" in
  2026-08-27|2026-08-28|2026-08-29) ;;
  *) exit 0 ;;
esac
URL="https://sailingsa.co.za/api/regatta/${RID}/live-race"
# Undo public-slug playback hijack. Prefer guard (restores 39-byte stubs).
/usr/local/lib/lipton_public_watch_guard.sh >/dev/null 2>&1 || /usr/bin/python3 /usr/local/lib/lipton_public_not_dev_watch.py >/dev/null 2>&1 || /usr/bin/python3 /usr/local/sbin/lipton_public_not_dev_watch.py >/dev/null 2>&1 || true
curl -fsS -o /dev/null --max-time 20 -H 'Cache-Control: no-store' "$URL" || true
