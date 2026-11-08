"""Guest/Done requires scroll or click engagement.

Live 2026-08-15: /tmp/patch_engage_required2.py on api.py

- Offline: no engagement on trail → bot (not Guest), after crawler-cloud checks
- Live: engagement no longer clears crawler-cloud IPs; no engage → bot after 3 min grace
- Real people who use the site fire session.js engage=scrolled|clicked|searched

Presence recording still disabled for anonymous middleware; engage only lands when
/auth/session beacons run (session.js).
"""
