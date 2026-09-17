"""Live-only central DB return-on-finish.

Source of truth: /var/www/sailingsa/api/api.py
Do NOT SCP repo api.py over live.

_ConnectionWrapper.close / __exit__ / __del__ now call return_db_connection
instead of closing the raw pooled connection (which stranded pool slots
until request-end ContextVar reclaim).

Borrowed-connection tracking uses weakrefs so __del__ can return a conn
when a helper drops its last strong reference (ContextVar no longer pins it).

return_db_connection is idempotent and removes wrappers by underlying conn.

Do not change #116/#118/#119 get_db_connection retry behaviour.
Preserve profile_requests ContextVar reclaim logging.
"""
