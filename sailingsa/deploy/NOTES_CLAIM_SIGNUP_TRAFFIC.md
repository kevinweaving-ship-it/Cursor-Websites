# Claim / sign-up on /traffic

## Why near-zero successful claims (found 2026-08-25)
1. `/api/funnel-event` was **404** — `traffic_funnel_events` stopped receiving steps after ~6 Aug.
2. `/api/register-account` session INSERT omitted `login_method` value while listing the column → SQL error recorded as `verification_failed` (`INSERT has more target columns than expressions`).

## Live fixes
- Restored `POST /api/funnel-event` → `traffic_funnel_events`
- Fixed register-account session vals to include `"email"` login_method
- `/traffic` KPI **Claim / sign-up** + panel: attempts, succeeded/failed, failure reasons, step counts, accounts created

## KPI maths identities (enforced live)
- Direct + Google + Facebook + Other = Visitors (same real-visitor set)
- Signed-in + guests = Visitors
- Claim: ok + fail + open = attempts (distinct people; accounts lift ok when funnel gaps)

## Super-admin excluded from /traffic
Kevin/Tim/agent (role=super_admin) IPs and sessions are omitted from Visitors, hits, sources, Live, and Real visitors. Public traffic only.

## Claim card popup
Claim/sign-up KPI is clickable → modal via `GET /traffic/api/claim-attempts`.

Shows **one row per attempt** (not every micro-step):
- **How they started** — Claim on sailor profile vs Sign-up banner vs direct
- **Sailor** they tried to claim (+ link)
- **Searched for** — text they typed when finding a sailor from banner/signup
- **Got as far as** / **Result** / **Why** (plain English)
- **On /users?** — successful accounts must appear on https://sailingsa.co.za/users

Beacons (signup.html + sailor Claim CTA): `claim_page_loaded` always (with `entry`), `sailor_search`, `sailor_selected`, plus existing submit/fail/success steps. Meta carries `sailor_name`, `search_query`, `entry`.

`/users` = Registered Users from `user_accounts` (not the traffic Visitors card).

## Popup layman model (live)

- **Blocked** = submitted / form error (real problem). Example: Waydon Goliath — old register SQL bug (fixed).
- **Left** = opened claim, never submitted (not a bug). Example: John Lindemann.
- **Became a member** = funnel success **or** `user_accounts.created_at` in the selected range (catches Google sign-ups like Robyn Patrick).
- **Who tried** = email/name if they typed one; else “Didn’t leave email” (no visitor hex).
- **Already on /users?** = that sailor profile already has a member (they should Sign in).
- Claim **card number** is driven from the same `/traffic/api/claim-attempts` digest as the popup (same range).

Historical: Alex Schon / Andrew Scott can log in because accounts exist from Feb 2026 — they will not appear as “new members” in a last-30-days filter.


## Sign-up made easier (live 2026-08-25)

Why ~94 “left”: multi-step form + **required WhatsApp/DOB** + sailor Claim path **skipped Google splash**.

Fixes on live:
- WhatsApp + DOB **optional** (email path)
- **Continue with Google — easiest** on Confirm Profile + registration form
- Plain-English API/client errors (no raw SQL)
- Google complete signup records `claim_completed` funnel
- Register no longer requires WhatsApp

Patches: `patch_claim_signup_easy.py`, `patch_claim_signup_easy_html.py`


## INCIDENT 2026-08-25 — site search broken

`patch_lean_traffic_claim_entry_search.py` wrote an **unescaped** `onclick` string into `index.html` `claimCtaHtml`, which terminated a JS string and broke sailor + regatta search on the main SPA.

**Fix:** restore escaped `\'claim_cta_click\'` quotes in `/var/www/sailingsa/index.html`. Also coerce `hub=Query()` when `/api/search` is called from Python (`/api/people/search`).
