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
