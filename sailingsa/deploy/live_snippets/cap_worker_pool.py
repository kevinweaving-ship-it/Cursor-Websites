"""Live capacity cap (#124). Configuration only.

ThreadedConnectionPool maxconn 20 → 12 at BOTH construction sites
(init_db_pool and _reset_db_pool). minconn stays 2.

4 workers × 12 = 48 API pooled connections.
Do not change PostgreSQL max_connections or uvicorn --workers.
Do not SCP repo api.py over live.
"""
