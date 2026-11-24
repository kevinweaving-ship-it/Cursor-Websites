#!/usr/bin/env python3
"""Cap live ThreadedConnectionPool maxconn 20 → 12. minconn unchanged."""
from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/api.py.patchwork")
text = SRC.read_text(encoding="utf-8", errors="replace")

old = """                DB_POOL = psycopg2.pool.ThreadedConnectionPool(
                    minconn=2,
                    maxconn=20,
                    dsn=DB_URL,
                    cursor_factory=psycopg2.extras.RealDictCursor
                )"""
new = """                DB_POOL = psycopg2.pool.ThreadedConnectionPool(
                    minconn=2,
                    maxconn=12,
                    dsn=DB_URL,
                    cursor_factory=psycopg2.extras.RealDictCursor
                )"""
c = text.count(old)
if c != 1:
    raise SystemExit(f"FAIL init pool block count={c}")
text = text.replace(old, new, 1)
print("OK init-pool-maxconn-12")

old = """        DB_POOL = psycopg2.pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=20,
            dsn=DB_URL,
            cursor_factory=psycopg2.extras.RealDictCursor
        )"""
new = """        DB_POOL = psycopg2.pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=12,
            dsn=DB_URL,
            cursor_factory=psycopg2.extras.RealDictCursor
        )"""
c = text.count(old)
if c != 1:
    raise SystemExit(f"FAIL reset pool block count={c}")
text = text.replace(old, new, 1)
print("OK reset-pool-maxconn-12")

if text.count("maxconn=20") != 0:
    raise SystemExit(f"FAIL leftover maxconn=20 count={text.count('maxconn=20')}")
if text.count("maxconn=12") != 2:
    raise SystemExit(f"FAIL maxconn=12 count={text.count('maxconn=12')}")
if text.count("minconn=2") < 2:
    raise SystemExit("FAIL minconn changed")

SRC.write_text(text, encoding="utf-8")
print(f"WROTE {SRC} lines={text.count(chr(10))}")
