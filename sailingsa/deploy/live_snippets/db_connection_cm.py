"""Live-only shared DB borrow/return context manager (#121).

Source of truth: /var/www/sailingsa/api/api.py
Do NOT SCP repo api.py over live.

#120 FINAL matrix leftover: 41 request-end reclaims, PG peak 98/100.
Helpers call get_db_connection() then finish without a covering
return_db_connection() (or they call another get_db helper while still
holding the first conn). ContextVar keeps those wrappers until reclaim.

One helper: db_connection()
    borrow → use → finally return_db_connection()

Adopted only in shared helpers proven by the #120 reclaim routes:
q/qf/one, directory fetchers, SEO discovery, gold host infer,
yearly series, events-by-type, upcoming second-conn, sailor bio,
site stats, batch sailor slugs, club slug, analytics/session touch.

Also:
- move nested get_db calls out of an open borrow (table_exists /
  column_exists / _batch_sailor_slugs / _get_club_slug_by_id /
  _load_boat_norm_slug_map)
- tag wrapper._borrowed_from so reclaim logs the acquisition site

Keep #118 ContextVar reclaim as the emergency safety net.
Keep #119 closed-connection retry untouched.
Keep #120 wrapper close()/idempotent return.
No weakrefs. No cursor-close auto-return. No /auth/session patch.
No pool/max_connections change.
"""
