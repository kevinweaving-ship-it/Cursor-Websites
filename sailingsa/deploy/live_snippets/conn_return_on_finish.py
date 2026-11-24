"""Live-only central DB return-on-finish.

Source of truth: /var/www/sailingsa/api/api.py
Do NOT SCP repo api.py over live.

_ConnectionWrapper.close / __exit__ / __del__ now call return_db_connection
instead of closing the raw pooled connection (which stranded pool slots
until request-end ContextVar reclaim).

return_db_connection is idempotent and removes wrappers by underlying conn.

Weakref borrowed-list tracking was tried and reverted: it allowed
__del__ to putconn while a cursor on the same wrapper was still live.

Do not change #116/#118/#119 get_db_connection retry behaviour.
Preserve profile_requests ContextVar reclaim logging.
"""
