"""
Stage 1 — Event class interest schema only.

No API routes. No production apply from this module without explicit approval.
SQL sources of truth also live beside the deploy scripts:
  sailingsa/deploy/event_class_interest.sql
  sailingsa/deploy/event_class_interest_rollback.sql
"""

from __future__ import annotations

from pathlib import Path

_DEPLOY = Path(__file__).resolve().parents[1] / "deploy"
MIGRATION_SQL_PATH = _DEPLOY / "event_class_interest.sql"
ROLLBACK_SQL_PATH = _DEPLOY / "event_class_interest_rollback.sql"


def migration_sql() -> str:
    return MIGRATION_SQL_PATH.read_text()


def rollback_sql() -> str:
    return ROLLBACK_SQL_PATH.read_text()


def apply_schema(conn) -> None:
    """Apply interest + history DDL. Caller owns the connection / transaction policy."""
    with conn.cursor() as cur:
        cur.execute(migration_sql())
    conn.commit()


def rollback_schema(conn) -> None:
    """Drop interest objects. Only for disposable / approved rollback."""
    with conn.cursor() as cur:
        cur.execute(rollback_sql())
    conn.commit()
