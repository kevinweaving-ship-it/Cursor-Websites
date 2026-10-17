# Nav engage tracking (scroll/click between pages)

## Problem
Trails showed page A → page B with no `clicked` / `scrolled` even when a human
navigated. Client leave/engage often loses the race on full document navigation.
Scroll only fired at ≥35% page height (missed short scrolls).

## Fix (live + repo)
1. **Server** (`_lean_stamp_nav_click_on_prev_hit`): when a new path opens for the
   same IP/visitor, stamp `clicked` on the previous hit. If dwell ≥3s, also stamp
   `scrolled`.
2. **Leave merge by path** (`_lean_merge_hit_engagement_for_path`): engage from
   leave beacon attaches to the leaving URL, not the next open page.
3. **Read-time backfill** on Live trails: consecutive different paths ⇒ prior row
   gets `clicked` (and `scrolled` if dwell ≥3s) for display if missing.
4. **Client** (`js/session.js` LITE_PAGE_ENGAGE): scroll at ~40px / 10%;
   `pointerdown` + sync Image beacon on nav links so click is less likely to drop.

## Apply
`python3 sailingsa/deploy/patch_nav_engage_track.py` on live (paths hardcoded to
`/var/www/sailingsa/...`).
