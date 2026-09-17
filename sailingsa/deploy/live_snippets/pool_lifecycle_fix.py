"""Live-only shared DB lifecycle fix. Source of truth:
/var/www/sailingsa/api/api.py get_db_connection / return_db_connection / profile_requests.

Do not SCP repo api.py over live.

1. Never call _reset_db_pool() from get_db_connection. closeall() was
   invalidating in-use connections (cursor already closed) and opening
   another 20-conn pool per exhausted worker.
2. Track borrowed connections on a ContextVar so async middleware
   finally can return leaks from sync threadpool endpoints.
"""
