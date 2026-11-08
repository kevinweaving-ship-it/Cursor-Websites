# Traffic UI — sticky show/hide toggles

**Live applied:** `patch_traffic_toggle_sticky.py` on `/var/www/sailingsa/api/api.py`.

## Problem

Every 3s poll re-rendered Live / Offline and reset open trails and FB/bots sections. Brief empty `page_trail` (timeout) also deleted sticky open state.

## Fix

1. Keep `LIVE_TRAIL_OPEN` sticky across polls — do not delete when trail is briefly empty.
2. FB / bots sections — persist `window.__offlineFbOpen` / `__offlineBotsOpen`; re-apply after each render (including empty lists).
3. `loadAll` — do not wipe Live/Top to Loading if a table is already shown.
4. Poll — prefer `human_live` for the LIVE NOW card.

Hard-refresh `/traffic` after deploy. Open a trail or FB/bots section; it should stay open across updates.
