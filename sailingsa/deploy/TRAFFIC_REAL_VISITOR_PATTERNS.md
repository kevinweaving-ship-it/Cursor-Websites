# Real visitor patterns (learned 2026-08-15)

From `public_page_hits` engagement + admin/phone samples vs Meta/AWS fakes.

## Real (keep / Live)

- **Tokens:** `scrolled` and/or `clicked` (required for Guest/Live)
- **Admin phone (`165.165.*`):** scrolled+clicked across clubs/class/sailor
- **ZA samples:** `102.*` / `105.*` / `41.*` with scroll|click; Android phone common
- **Dwell:** often 3–60s+ when engaged (not instant bounce)
- **Phone UA** (iPhone/Android/mobile) + scroll|click = strong real tell vs desktop broadcast scrapers

## Fake / bot (quarantine → ignore)

- **No scroll/click within ~12s**, ≤5 pages → `no_engage_sterile`
- **`searched` without scroll/click** → `fake_search_engage` (Meta/AWS samples had this)
- **Crawler-cloud IP ranges** (Meta, Googlebot, AWS, Alibaba, Azure 20.x, AWS 16.x) → never Guest
- Sterile trails: 1–4 pages, club/sailor/boat deep links, no engage

## Resource rule

Identify → quarantine → **ignore** (no further public trail / live cost).
Only engaged humans appear on Live.

## Facebook in-app vs link-preview (2026-08-15)

- **Real:** person opens a SailingSA link *inside* Facebook/Instagram browser (Meta IP OK). Scroll/click counts like any human.
- **Not real:** `facebookexternalhit` / meta-external* link-preview crawler (UA). Often fakes `searched`+`clicked` without `scrolled`.
- Meta IP alone is **not** a ban. UA crawler ⇒ quarantine. Scroll ⇒ always real.
