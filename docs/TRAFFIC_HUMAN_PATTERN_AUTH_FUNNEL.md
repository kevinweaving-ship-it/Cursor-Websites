# Learned human pattern — land → signup/login → browse

**Example (keep):** Robyn Patrick, SAS `#6903`, IP `165.73.122.145`, 15 Aug 2026.

## Behaviour (typical real human)

1. Lands on home (`/`) as guest — scrolls / clicks  
2. Opens **signup** (`/signup.html`)  
3. Returns to home, then **login** (`/login.html`)  
4. While **logged in**, browses real URLs: club → sailor → regatta → rankings → home  

Same IP across the whole story. Guest `public_sessions` is purged on login (by design); page hits on that IP still form one continuous trail.

## What to learn

| Signal | Meaning |
|--------|---------|
| Home + signup/login + later entity URLs | Auth funnel — real person, not a scanner |
| Scroll/click on home and later pages | Real engagement (not `searched`-only fake) |
| Same IP guest → signed-in | One human; do not quarantine or bot-classify |
| Bounce-only home with **no** engage | Still bot-shaped (unchanged) |

## Code hooks

- `_lean_is_auth_funnel_path` — `/signup.html`, `/login.html`, `/signup`, `/login`, …  
- `_lean_trail_is_auth_funnel_human` — land/home + auth step + browse (or scroll/click)  
- Wired into confident-bot / sterile classify / Done offline so this shape is never bot  

Deploy patch: `sailingsa/deploy/patch_learn_auth_funnel_human.py`

## Live signed-in list — profile under name

Every logged-in Live row must show the sailor **name** (linked) and the public profile URL **under** it, e.g. `/sailor/robyn-patrick`, so you can open their profile in one tap.

Deploy: `sailingsa/deploy/patch_signed_live_profile_link.py`
