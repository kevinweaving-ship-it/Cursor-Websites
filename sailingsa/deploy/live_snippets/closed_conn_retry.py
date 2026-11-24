"""Live-only get_db_connection() closed-connection retry.

Source of truth: /var/www/sailingsa/api/api.py  (do NOT SCP repo api.py over live)

Change (get_db_connection only):
- Discard closed/dead pooled connections and keep calling pool.getconn()
  until a live connection is obtained OR the pool reports genuine
  exhaustion/failure (PoolError / OperationalError).
- Do not use a fixed two-attempt limit for dead connections.
- Bound dead discards at pool.maxconn to prevent an infinite loop if
  every newly created connection is immediately dead.
- Never restore ephemeral psycopg2.connect() fallback.
- Do not call _reset_db_pool() on exhaustion.
- Preserve #118 ContextVar reclaim in profile_requests / return_db_connection.
"""
