#!/usr/bin/env python3
"""Live-only: ThreadedConnectionPool maxconn 12 → 15. No helper/SQL changes."""
from pathlib import Path
import sys

p = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")
text = p.read_text(encoding="utf-8")
old = """                DB_POOL = psycopg2.pool.ThreadedConnectionPool(
                    minconn=2,
                    maxconn=12,"""
new = """                DB_POOL = psycopg2.pool.ThreadedConnectionPool(
                    minconn=2,
                    maxconn=15,"""
old2 = """        DB_POOL = psycopg2.pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=12,"""
new2 = """        DB_POOL = psycopg2.pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=15,"""
if text.count(old) != 1 or text.count(old2) != 1:
    raise SystemExit("expected two maxconn=12 pool constructors")
text = text.replace(old, new, 1).replace(old2, new2, 1)
p.write_text(text, encoding="utf-8")
print(f"patched {p} maxconn 12->15")
