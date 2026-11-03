# Signed-in engage was dropped

## Bug
`/auth/session` with a `session` cookie recorded URL stays via
`_session_touch_user_activity` but **never read `engage=` / `leave=`**.
Signed-in Tim could scroll/click all day and trails stayed empty.

## Fix
- Valid session branch: merge `engage` onto the hit for that path; honour `leave`
- Client: any content click counts; scroll ≥10px; SPA flush+reset; 15s heartbeat

Apply: `python3 sailingsa/deploy/patch_signed_in_engage.py`
