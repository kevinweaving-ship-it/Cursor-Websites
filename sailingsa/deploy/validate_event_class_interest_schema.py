#!/usr/bin/env python3
"""
Stage 1 local validation for event_class_interest migration.

Creates stub parent tables matching production types, applies the migration,
exercises constraints / identity / class mapping / transaction safety / rollback.

NEVER connects to production. Requires a disposable local DATABASE_URL.
"""

from __future__ import annotations

import os
import sys
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import psycopg2
import psycopg2.extras

ROOT = Path(__file__).resolve().parents[2]
MIG = Path(__file__).resolve().parent / "event_class_interest.sql"
RB = Path(__file__).resolve().parent / "event_class_interest_rollback.sql"

# Explicit block: refuse known production hosts
BLOCKED_HOST_FRAGMENTS = (
    "sailingsa.co.za",
    "102.218.215.253",
    "amazonaws.com",
    "neon.tech",
    "supabase.co",
)


def _dsn() -> str:
    dsn = (os.environ.get("EVENT_INTEREST_VALIDATE_DSN")
           or os.environ.get("DATABASE_URL")
           or os.environ.get("DB_URL")
           or "").strip()
    if not dsn:
        print("FAIL: set EVENT_INTEREST_VALIDATE_DSN to a local disposable Postgres DSN")
        sys.exit(2)
    low = dsn.lower()
    for frag in BLOCKED_HOST_FRAGMENTS:
        if frag in low:
            print(f"FAIL: refusing DSN that looks like production ({frag})")
            sys.exit(2)
    if "127.0.0.1" not in low and "localhost" not in low:
        print("FAIL: Stage 1 validation DSN must target localhost/127.0.0.1")
        sys.exit(2)
    return dsn


def _exec_file(cur, path: Path) -> None:
    sql = path.read_text()
    cur.execute(sql)


def _setup_stubs(cur) -> None:
    cur.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    # Minimal parents matching live PK / unique shapes used by interest FKs.
    cur.execute(
        """
        CREATE TABLE public.events (
            event_id integer PRIMARY KEY,
            event_name text NOT NULL DEFAULT 'stub'
        );
        CREATE TABLE public.classes (
            class_id integer PRIMARY KEY,
            class_name text NOT NULL UNIQUE
        );
        CREATE TABLE public.user_accounts (
            account_id bigint PRIMARY KEY,
            sas_id text NOT NULL
        );
        CREATE TABLE public.event_edition_classes (
            id bigserial PRIMARY KEY,
            event_id integer NOT NULL REFERENCES public.events(event_id),
            class_identifier text NOT NULL,
            class_display_name text,
            sort_order smallint NOT NULL DEFAULT 0,
            extras jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (event_id, class_identifier)
        );

        INSERT INTO public.events(event_id, event_name) VALUES
            (168679, '2026 EC Dinghy Regionals'),
            (246456, 'Flying fifteen & Soling Nationals');

        INSERT INTO public.classes(class_id, class_name) VALUES
            (9, 'Finn'),
            (46, 'ILCA 7'),
            (206, 'Flying 15'),
            (69, 'Soling');

        INSERT INTO public.event_edition_classes(event_id, class_identifier, class_display_name, sort_order)
        VALUES
            (168679, 'finn', 'Finn', 1),
            (168679, 'ilca-7', 'ILCA 7', 2),
            (168679, 'junior', 'Junior', 3),
            (246456, 'flying-15', 'Flying 15', 1),
            (246456, 'soling', 'Soling', 2);

        INSERT INTO public.user_accounts(account_id, sas_id) VALUES
            (1001, 'SAS-1001'),
            (1002, 'SAS-1002');
        """
    )


def _expect_fail(cur, sql: str, params=None, label: str = "") -> None:
    """Assert SQL fails without aborting the surrounding test transaction."""
    cur.execute("SAVEPOINT eci_expect_fail")
    try:
        cur.execute(sql, params or ())
        cur.execute("ROLLBACK TO SAVEPOINT eci_expect_fail")
        raise AssertionError(f"expected failure: {label or sql}")
    except psycopg2.Error:
        cur.execute("ROLLBACK TO SAVEPOINT eci_expect_fail")
    finally:
        try:
            cur.execute("RELEASE SAVEPOINT eci_expect_fail")
        except psycopg2.Error:
            cur.connection.rollback()
            raise

def _count_active(cur, event_id: int) -> int:
    cur.execute(
        "SELECT COUNT(*) FROM public.event_class_interest WHERE event_id=%s AND status='active'",
        (event_id,),
    )
    return int(cur.fetchone()[0])


def _class_counts(cur, event_id: int) -> dict:
    cur.execute(
        """
        SELECT class_identifier, COUNT(*)::int
        FROM public.event_class_interest
        WHERE event_id=%s AND status='active'
        GROUP BY class_identifier
        """,
        (event_id,),
    )
    return {r[0]: r[1] for r in cur.fetchall()}


def _assert_total_equals_sum(cur, event_id: int) -> None:
    total = _count_active(cur, event_id)
    sums = sum(_class_counts(cur, event_id).values())
    assert total == sums, f"invariant broken: total={total} sum_classes={sums}"


def main() -> int:
    dsn = _dsn()
    conn = psycopg2.connect(dsn)
    conn.autocommit = False
    cur = conn.cursor()
    results = []

    def ok(name: str) -> None:
        results.append(("PASS", name))
        print(f"PASS  {name}")

    try:
        _setup_stubs(cur)
        conn.commit()
        ok("stub parents created (local only)")

        _exec_file(cur, MIG)
        conn.commit()
        ok("migration applied")

        # --- identity constraints ---
        _expect_fail(
            cur,
            """
            INSERT INTO public.event_class_interest
              (event_id, class_identifier, account_id, visitor_id, status)
            VALUES (168679, 'finn', NULL, NULL, 'active')
            """,
            label="reject neither identity",
        )
        ok("reject row with neither account nor visitor")

        _expect_fail(
            cur,
            """
            INSERT INTO public.event_class_interest
              (event_id, class_identifier, account_id, visitor_id, status)
            VALUES (168679, 'finn', 1001, 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', 'active')
            """,
            label="reject both identities",
        )
        ok("reject row with both account and visitor")

        _expect_fail(
            cur,
            """
            INSERT INTO public.event_class_interest
              (event_id, class_identifier, visitor_id, status)
            VALUES (168679, 'finn', 'NOT-A-VALID-VID', 'active')
            """,
            label="reject bad visitor_id",
        )
        ok("reject non-hex / non-32 visitor_id (ssa_vid shape)")

        # --- class mapping: must belong to event_edition_classes ---
        _expect_fail(
            cur,
            """
            INSERT INTO public.event_class_interest
              (event_id, class_identifier, account_id, status)
            VALUES (168679, 'soling', 1001, 'active')
            """,
            label="reject class not on event",
        )
        ok("reject class_identifier not configured for event")

        _expect_fail(
            cur,
            """
            INSERT INTO public.event_class_interest
              (event_id, class_identifier, account_id, status)
            VALUES (999999, 'finn', 1001, 'active')
            """,
            label="reject unknown event",
        )
        ok("reject unknown event_id")

        # --- happy path upserts ---
        cur.execute(
            "SELECT interest_id FROM public.eci_upsert_interest(%s,%s,%s,NULL,%s)",
            (168679, "finn", 1001, 9),
        )
        a1 = cur.fetchone()[0]
        cur.execute(
            "SELECT interest_id FROM public.eci_upsert_interest(%s,%s,NULL,%s,%s)",
            (168679, "ilca-7", "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", 46),
        )
        v1 = cur.fetchone()[0]
        conn.commit()
        assert _count_active(cur, 168679) == 2
        _assert_total_equals_sum(cur, 168679)
        ok("create sailor + visitor interests; total==sum(class counts)")

        # Idempotent repeat must not double-count
        cur.execute(
            "SELECT interest_id FROM public.eci_upsert_interest(%s,%s,%s,NULL,%s)",
            (168679, "finn", 1001, 9),
        )
        assert cur.fetchone()[0] == a1
        assert _count_active(cur, 168679) == 2
        cur.execute(
            """
            SELECT COUNT(*) FROM public.event_class_interest_history
            WHERE interest_id=%s AND action='created'
            """,
            (a1,),
        )
        assert cur.fetchone()[0] == 1
        ok("repeat upsert is idempotent (no double-count, no extra created history)")

        # Class change keeps event total
        before = _count_active(cur, 168679)
        cur.execute(
            "SELECT class_identifier FROM public.eci_upsert_interest(%s,%s,%s,NULL,%s)",
            (168679, "ilca-7", 1001, 46),
        )
        assert cur.fetchone()[0] == "ilca-7"
        assert _count_active(cur, 168679) == before
        _assert_total_equals_sum(cur, 168679)
        counts = _class_counts(cur, 168679)
        assert counts.get("ilca-7") == 2
        assert "finn" not in counts
        cur.execute(
            """
            SELECT action, from_class_identifier, to_class_identifier
            FROM public.event_class_interest_history
            WHERE interest_id=%s AND action='class_changed'
            ORDER BY history_id DESC LIMIT 1
            """,
            (a1,),
        )
        row = cur.fetchone()
        assert row == ("class_changed", "finn", "ilca-7")
        ok("class change: total unchanged; class buckets move; history logged")

        # Unique regardless of status: cannot insert second current row
        _expect_fail(
            cur,
            """
            INSERT INTO public.event_class_interest
              (event_id, class_identifier, account_id, status)
            VALUES (168679, 'finn', 1001, 'withdrawn')
            """,
            label="unique current row",
        )
        ok("unique (event, account) regardless of status")

        # Withdraw decreases totals
        cur.execute(
            "SELECT status FROM public.eci_withdraw_interest(%s,%s,NULL)",
            (168679, 1001),
        )
        assert cur.fetchone()[0] == "withdrawn"
        assert _count_active(cur, 168679) == 1
        _assert_total_equals_sum(cur, 168679)
        # idempotent withdraw
        cur.execute(
            "SELECT status FROM public.eci_withdraw_interest(%s,%s,NULL)",
            (168679, 1001),
        )
        assert cur.fetchone()[0] == "withdrawn"
        assert _count_active(cur, 168679) == 1
        ok("withdraw decreases totals; withdraw is idempotent")

        # Reactivate
        cur.execute(
            "SELECT status FROM public.eci_upsert_interest(%s,%s,%s,NULL,%s)",
            (168679, "finn", 1001, 9),
        )
        assert cur.fetchone()[0] == "active"
        assert _count_active(cur, 168679) == 2
        ok("reactivate withdrawn interest")

        # --- reconciliation: visitor only → reassigned to account ---
        cur.execute(
            "SELECT public.eci_reconcile_visitor_to_account(%s,%s)",
            ("bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", 1002),
        )
        moved = cur.fetchone()[0]
        assert moved == 1
        cur.execute(
            """
            SELECT account_id, visitor_id, status
            FROM public.event_class_interest WHERE interest_id=%s
            """,
            (v1,),
        )
        assert cur.fetchone() == (1002, None, "active")
        assert _count_active(cur, 168679) == 2
        _assert_total_equals_sum(cur, 168679)
        ok("reconcile visitor→account (no prior sailor row): reassign, no double-count")

        # --- reconciliation: both active → keep sailor, withdraw visitor ---
        cur.execute(
            "SELECT interest_id FROM public.eci_upsert_interest(%s,%s,NULL,%s,%s)",
            (168679, "finn", "cccccccccccccccccccccccccccccccc", 9),
        )
        v2 = cur.fetchone()[0]
        # sailor 1001 already active on 168679
        before = _count_active(cur, 168679)
        assert before == 3
        cur.execute(
            "SELECT public.eci_reconcile_visitor_to_account(%s,%s)",
            ("cccccccccccccccccccccccccccccccc", 1001),
        )
        assert cur.fetchone()[0] == 1
        cur.execute(
            "SELECT status, visitor_id FROM public.event_class_interest WHERE interest_id=%s",
            (v2,),
        )
        st, vid = cur.fetchone()
        assert st == "withdrawn" and vid == "cccccccccccccccccccccccccccccccc"
        assert _count_active(cur, 168679) == before - 1
        _assert_total_equals_sum(cur, 168679)
        ok("reconcile when sailor already active: visitor withdrawn, sailor kept")

        # History immutability
        cur.execute("SELECT history_id FROM public.event_class_interest_history LIMIT 1")
        hid = cur.fetchone()[0]
        _expect_fail(
            cur,
            "UPDATE public.event_class_interest_history SET action='created' WHERE history_id=%s",
            (hid,),
            label="history update blocked",
        )
        _expect_fail(
            cur,
            "DELETE FROM public.event_class_interest_history WHERE history_id=%s",
            (hid,),
            label="history delete blocked",
        )
        ok("history UPDATE/DELETE blocked by immutability trigger")

        # Views
        cur.execute(
            """
            SELECT t.total_interested, COALESCE(SUM(c.interested_count),0)
            FROM public.event_interest_totals t
            LEFT JOIN public.event_class_interest_counts c ON c.event_id = t.event_id
            WHERE t.event_id = 168679
            GROUP BY t.total_interested
            """
        )
        tot, sm = cur.fetchone()
        assert tot == sm
        ok("views: event_interest_totals == sum(event_class_interest_counts)")

        # Transaction safety: failed class map rolls back write
        conn.commit()
        try:
            cur.execute(
                "SELECT public.eci_upsert_interest(%s,%s,%s,NULL,%s)",
                (168679, "not-a-real-class", 1001, 9),
            )
            raise AssertionError("expected class rejection")
        except psycopg2.Error:
            conn.rollback()
        assert _count_active(cur, 168679) == 2
        ok("failed upsert aborts transaction; prior counts intact")

        # --- Unmapped class (Junior): class_id NULL must still count ---
        cur.execute(
            """
            SELECT class_id, class_identifier, status
            FROM public.eci_upsert_interest(%s,%s,%s,NULL,NULL)
            """,
            (168679, "junior", 1001),
        )
        j_class_id, j_ident, j_status = cur.fetchone()
        assert j_class_id is None and j_ident == "junior" and j_status == "active"
        cur.execute(
            """
            SELECT interested_count, class_id
            FROM public.event_class_interest_counts
            WHERE event_id=168679 AND class_identifier='junior'
            """
        )
        j_count, j_view_class_id = cur.fetchone()
        assert j_count == 1 and j_view_class_id is None
        _assert_total_equals_sum(cur, 168679)
        cur.execute(
            "SELECT total_interested FROM public.event_interest_totals WHERE event_id=168679"
        )
        total_now = cur.fetchone()[0]
        cur.execute(
            """
            SELECT COALESCE(SUM(interested_count),0)
            FROM public.event_class_interest_counts WHERE event_id=168679
            """
        )
        assert total_now == cur.fetchone()[0]
        ok("Junior (NULL class_id) stays in counts; total still equals sum")

        # History TRUNCATE blocked
        _expect_fail(
            cur,
            "TRUNCATE public.event_class_interest_history",
            label="history truncate blocked",
        )
        ok("history TRUNCATE blocked by statement trigger")

        # Composite FK matches production UNIQUE(event_id, class_identifier)
        cur.execute(
            """
            SELECT pg_get_constraintdef(oid)
            FROM pg_constraint
            WHERE conrelid = 'public.event_edition_classes'::regclass
              AND conname = 'event_edition_classes_event_id_class_identifier_key'
            """
        )
        assert cur.fetchone()[0] == "UNIQUE (event_id, class_identifier)"
        cur.execute(
            """
            SELECT pg_get_constraintdef(oid)
            FROM pg_constraint
            WHERE conrelid = 'public.event_class_interest'::regclass
              AND conname = 'eci_event_class_fkey'
            """
        )
        fkdef = cur.fetchone()[0]
        compact = fkdef.replace(" ", "").replace("public.", "")
        assert compact.startswith("FOREIGNKEY(event_id,class_identifier)REFERENCESevent_edition_classes(event_id,class_identifier)")
        ok("composite FK definition matches edition-classes unique key")

        conn.commit()

        # --- Concurrency: simultaneous upserts same identity ---
        barrier = threading.Barrier(8)
        errors = []

        def _upsert_same(n: int) -> None:
            c = psycopg2.connect(dsn)
            try:
                barrier.wait(timeout=10)
                with c.cursor() as cu:
                    cu.execute(
                        "SELECT interest_id, class_identifier FROM public.eci_upsert_interest(%s,%s,%s,NULL,%s)",
                        (168679, "finn", 1002, 9),
                    )
                    cu.fetchone()
                c.commit()
            except Exception as ex:  # noqa: BLE001
                errors.append(ex)
                c.rollback()
            finally:
                c.close()

        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(_upsert_same, range(8)))
        assert not errors, errors
        cur.execute(
            """
            SELECT COUNT(*), COUNT(*) FILTER (WHERE status='active')
            FROM public.event_class_interest
            WHERE event_id=168679 AND account_id=1002
            """
        )
        rows, active = cur.fetchone()
        assert rows == 1 and active == 1
        _assert_total_equals_sum(cur, 168679)
        ok("8 concurrent upserts same sailor/event → one row, no double-count")

        # Concurrent distinct visitors
        def _upsert_visitor(i: int) -> None:
            vid = f"{i:032x}"
            c = psycopg2.connect(dsn)
            try:
                with c.cursor() as cu:
                    cu.execute(
                        "SELECT public.eci_upsert_interest(%s,%s,NULL,%s,%s)",
                        (246456, "soling", vid, 69),
                    )
                c.commit()
            finally:
                c.close()

        with ThreadPoolExecutor(max_workers=10) as pool:
            list(pool.map(_upsert_visitor, range(10)))
        cur.execute(
            """
            SELECT COUNT(*) FROM public.event_class_interest
            WHERE event_id=246456 AND status='active'
            """
        )
        assert cur.fetchone()[0] == 10
        _assert_total_equals_sum(cur, 246456)
        ok("10 concurrent distinct visitor upserts → 10 active rows")

        # Concurrent reconcile vs upsert: sailor wins, no double-count
        cur.execute(
            "SELECT public.eci_upsert_interest(%s,%s,NULL,%s,%s)",
            (246456, "flying-15", "dddddddddddddddddddddddddddddddd", 206),
        )
        conn.commit()

        def _reconcile() -> None:
            c = psycopg2.connect(dsn)
            try:
                with c.cursor() as cu:
                    cu.execute(
                        "SELECT public.eci_reconcile_visitor_to_account(%s,%s)",
                        ("dddddddddddddddddddddddddddddddd", 1001),
                    )
                c.commit()
            finally:
                c.close()

        def _upsert_account() -> None:
            c = psycopg2.connect(dsn)
            try:
                with c.cursor() as cu:
                    cu.execute(
                        "SELECT public.eci_upsert_interest(%s,%s,%s,NULL,%s)",
                        (246456, "soling", 1001, 69),
                    )
                c.commit()
            finally:
                c.close()

        with ThreadPoolExecutor(max_workers=6) as pool:
            futs = [pool.submit(_reconcile) for _ in range(3)] + [
                pool.submit(_upsert_account) for _ in range(3)
            ]
            for f in as_completed(futs):
                f.result()

        cur.execute(
            """
            SELECT COUNT(*) FILTER (WHERE status='active' AND account_id=1001),
                   COUNT(*) FILTER (WHERE visitor_id='dddddddddddddddddddddddddddddddd' AND status='active')
            FROM public.event_class_interest
            WHERE event_id=246456
            """
        )
        acc_active, vis_active = cur.fetchone()
        assert acc_active == 1 and vis_active == 0
        _assert_total_equals_sum(cur, 246456)
        ok("concurrent reconcile + account upsert: one active sailor, visitor not active")

        # Rollback removes ONLY interest objects — preserve unrelated table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS public._eci_validation_canary (
                id int PRIMARY KEY,
                note text NOT NULL
            );
            INSERT INTO public._eci_validation_canary(id, note)
            VALUES (1, 'must-survive-rollback')
            ON CONFLICT (id) DO UPDATE SET note=EXCLUDED.note;
            """
        )
        conn.commit()
        _exec_file(cur, RB)
        conn.commit()
        cur.execute(
            """
            SELECT to_regclass('public.event_class_interest'),
                   to_regclass('public.event_class_interest_history'),
                   to_regclass('public.event_interest_totals')
            """
        )
        assert cur.fetchone() == (None, None, None)
        cur.execute(
            """
            SELECT COUNT(*) FROM pg_proc p
            JOIN pg_namespace n ON n.oid = p.pronamespace
            WHERE n.nspname='public'
              AND p.proname IN (
                'eci_upsert_interest','eci_withdraw_interest',
                'eci_reconcile_visitor_to_account','eci_identity_lock',
                'eci_history_immutable'
              )
            """
        )
        assert cur.fetchone()[0] == 0
        cur.execute("SELECT note FROM public._eci_validation_canary WHERE id=1")
        assert cur.fetchone()[0] == "must-survive-rollback"
        cur.execute("SELECT to_regclass('public.events'), to_regclass('public.event_edition_classes')")
        assert cur.fetchone() == ("events", "event_edition_classes")
        ok("rollback drops only interest objects; parents + canary survive")

        # Re-apply after rollback
        _exec_file(cur, MIG)
        conn.commit()
        cur.execute("SELECT to_regclass('public.event_class_interest')")
        assert cur.fetchone()[0] is not None
        ok("migration re-applies cleanly after rollback")

    except Exception as e:
        conn.rollback()
        print("FAIL ", e)
        traceback.print_exc()
        return 1
    finally:
        cur.close()
        conn.close()

    fails = [n for s, n in results if s != "PASS"]
    print()
    print(f"Stage 1 validation: {len(results)} checks, {len(fails)} failed")
    print("Production was NOT touched.")
    return 0 if not fails else 1


if __name__ == "__main__":
    raise SystemExit(main())
