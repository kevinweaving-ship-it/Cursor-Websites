# Sponsors SailingSA — Dedicated agent scope

When the user says **"Sponsors SailingSA"**, **"Sponsors"**, or **"SailingSA sponsors"**, limit changes to this scope only.

## Behaviour

- Public **Sponsors** page at `/sponsors` uses the live Ullman-era index architecture: Headline + 2nd-tier `.sp-sponsor-index-card` grid (logo + name). Cards click through to `/sponsors/{slug}`.
- Sponsor profile pages clone live `/sponsors/ullman` architecture (`sp-hero`, stats, services, team, contact, location, media). First profile: `/sponsors/miller-gold`.
- Home landing section `#landing-sponsors-embed` (visible on home only).
- List **confirmed** commercial partners only. Do not invent sponsor names, logos, or SailingSA event/sailor/boat/class relationships.
- Miller Gold is a **Headline** sponsor. Logo: `/artwork/Sponsor Logo/Miller-Gold.png` (tracked file `landing-page-artwork/logos/miller-gold.png`). Profile: `/sponsors/miller-gold`. Confirmed event: [2026 TSC 420 Nationals](https://sailingsa.co.za/regatta/2026-09-25-tsc-420-nationals) via `sponsors/event_headline_sponsors.json`.
- Miller Gold social URLs must be extracted from mgandco.co.za (Instagram `millergoldandco`, Facebook page `Miller-Gold-Co-103655218496198`).
- Current confirmed partner in product: **Marine Megastore** (`https://www.marinemegastore.co.za/`), already used on the hub advert (enquiry: `warren@marineconnect.co.za`, WhatsApp `https://wa.me/27783816564`).
- Partner names, websites, and enquiry contacts must be clickable.

## Frontend

- `sponsors.html` (and `public/sponsors.html`) — live index architecture plus Miller Gold Headline card
- `sponsors/miller-gold.html` (and `public/sponsors/miller-gold.html`)
- `sponsors/event_headline_sponsors.json` — confirmed regatta → sponsor links
- Landing: `index.html` / `sailingsa/frontend/index.html` — `#landing-sponsors-embed`
- Optional About content link to `/sponsors` (page body only — not header/nav)
- Reuse existing classes: `.container`, `.about-page`, `.home-intro-box`, `.table`, `.table-container`, `.news-feed-section-header`, plus live `.sp-*` sponsor classes

## Backend / API

- `api.py`: `GET /sponsors` serves `sponsors.html` (same pattern as `GET /about`)
- `GET /sponsors/miller-gold` and Miller Gold logo FileResponse
- `serve_regatta_standalone` reads `event_headline_sponsors.json` and renders a Headline sponsor logo/name linking to the sponsor profile (does not replace class/club header logos)

## Out of scope

- Header / navigation layout
- Inventing logos or unconfirmed partners
- Live SSH deploy unless the user asks in the same message
- News Feed, sailor Media tab, regatta sheets

Do not change those unless the user explicitly asks.
