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
