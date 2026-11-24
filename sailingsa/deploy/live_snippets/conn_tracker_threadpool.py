"""Live-only request-owned DB tracker (#122).

Source of truth: /var/www/sailingsa/api/api.py
Do NOT SCP repo api.py over live.

#121 proved ContextVar-held mutable lists are not the same object
across async middleware and FastAPI threadpool helpers:
  reclaim 41→35, PG 98/100, 12 unkeyed, from= path mismatch.

Replace the list with one _RequestConnTracker per request.
Middleware creates it, ContextVar stores that object, threadpool
copies share it. get_db registers; return_db unregisters after
successful putconn; reclaim uses the middleware's local tracker.

Thread-safe. No weakrefs. No cursor-close auto-return.
Keep #118 reclaim, #119 retry, #120 close/idempotent, #121 db_connection().
"""
