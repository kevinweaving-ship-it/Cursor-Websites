# Sponsors SailingSA — Dedicated agent scope

When the user says **"Sponsors SailingSA"**, **"Sponsors"**, or **"SailingSA sponsors"**, limit changes to this scope only.

## Behaviour

- Public **Sponsors** page at `/sponsors` (same header/nav as `/about`; do not change header layout).
- Sponsor profile pages clone live `/sponsors/ullman` architecture (`sp-hero`, stats, services, team, contact, location, media). First profile: `/sponsors/miller-gold`.
- Home landing section `#landing-sponsors-embed` (visible on home only).
- List **confirmed** commercial partners only. Do not invent sponsor names, logos, or SailingSA event/sailor/boat/class relationships.
- Miller Gold social URLs must be extracted from mgandco.co.za (Instagram `millergoldandco`, Facebook page `Miller-Gold-Co-103655218496198`).
- Current confirmed partner in product: **Marine Megastore** (`https://www.marinemegastore.co.za/`), already used on the hub advert (enquiry: `warren@marineconnect.co.za`, WhatsApp `https://wa.me/27783816564`).
- Partner names, websites, and enquiry contacts must be clickable.

## Frontend

- `sponsors.html` (and `public/sponsors.html`)
- Landing: `index.html` / `sailingsa/frontend/index.html` — `#landing-sponsors-embed`
- Optional About content link to `/sponsors` (page body only — not header/nav)
- Reuse existing classes: `.container`, `.about-page`, `.home-intro-box`, `.table`, `.table-container`, `.news-feed-section-header`

## Backend / API

- `api.py`: `GET /sponsors` serves `sponsors.html` (same pattern as `GET /about`)

## Out of scope

- Header / navigation layout
- Inventing logos or unconfirmed partners
- Live SSH deploy unless the user asks in the same message
- News Feed, sailor Media tab, regatta sheets

Do not change those unless the user explicitly asks.
