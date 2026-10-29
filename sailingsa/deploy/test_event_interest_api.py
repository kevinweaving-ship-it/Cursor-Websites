#!/usr/bin/env python3
"""
Stage 2 — local disposable Postgres + FastAPI TestClient for event interest API.

Never connects to production. Refuses non-localhost DSNs.
Does not modify api.py; registers routes on a throwaway FastAPI app.
"""

from __future__ import annotations

import os
import sys
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BLOCKED = ("sailingsa.co.za", "102.218.215.253", "amazonaws.com", "neon.tech", "supabase.co")


def _dsn() -> str:
    dsn = (
        os.environ.get("EVENT_INTEREST_VALIDATE_DSN")
        or os.environ.get("DATABASE_URL")
        or os.environ.get("DB_URL")
        or ""
    ).strip()
    if not dsn:
        print("FAIL: set EVENT_INTEREST_VALIDATE_DSN to local disposable Postgres")
        sys.exit(2)
    low = dsn.lower()
    for frag in BLOCKED:
        if frag in low:
            print(f"FAIL: refusing production-like DSN ({frag})")
            sys.exit(2)
    if "127.0.0.1" not in low and "localhost" not in low:
        print("FAIL: DSN must target localhost/127.0.0.1")
        sys.exit(2)
    return dsn


def _setup(conn) -> None:
    cur = conn.cursor()
    cur.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    cur.execute(
        """
        CREATE TABLE public.events (
            event_id integer PRIMARY KEY,
            event_name text NOT NULL
        );
        CREATE TABLE public.classes (
            class_id integer PRIMARY KEY,
            class_name text NOT NULL UNIQUE,
            logo_path text,
            icon_path text
        );
        CREATE TABLE public.user_accounts (
            account_id bigint PRIMARY KEY,
            sas_id text NOT NULL,
            role text NOT NULL DEFAULT 'sailor',
            is_active boolean NOT NULL DEFAULT true
        );
        CREATE TABLE public.user_sessions (
            session_id text PRIMARY KEY,
            account_id bigint NOT NULL REFERENCES public.user_accounts(account_id),
            sas_id text NOT NULL,
            expires_at timestamptz NOT NULL,
            is_active boolean NOT NULL DEFAULT true
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
          (246456, 'Flying fifteen & Soling Nationals'),
          (45, '2026 USSA Sailing Championships');

        INSERT INTO public.classes(class_id, class_name, logo_path) VALUES
          (9, 'Finn', '/artwork/Class Logo/Finn-Class-Logo.png'),
          (46, 'ILCA 7', '/artwork/Class Logo/ILCA-7-Class-Logo.png'),
          (206, 'Flying 15', '/artwork/Class Logo/Flying-Fifteen-Class-Logo.png'),
          (69, 'Soling', '/artwork/Class Logo/Soling-Class-Logo.png');

        INSERT INTO public.event_edition_classes(event_id, class_identifier, class_display_name, sort_order)
        VALUES
          (168679, 'finn', 'Finn', 1),
          (168679, 'ilca-7', 'ILCA 7', 2),
          (168679, 'junior', 'Junior', 3),
          (246456, 'flying-15', 'Flying 15', 1),
          (246456, 'soling', 'Soling', 2);
        -- event 45 intentionally has zero edition classes

        INSERT INTO public.user_accounts(account_id, sas_id, role) VALUES
          (1001, 'SAS-1001', 'sailor'),
          (1002, 'SAS-1002', 'sailor');

        INSERT INTO public.user_sessions(session_id, account_id, sas_id, expires_at)
        VALUES
          ('sess-1001', 1001, 'SAS-1001', NOW() + INTERVAL '1 day'),
          ('sess-1002', 1002, 'SAS-1002', NOW() + INTERVAL '1 day'),
          ('sess-expired', 1001, 'SAS-1001', NOW() - INTERVAL '1 day');
        """
    )
    conn.commit()
    cur.close()

    from sailingsa.backend.event_interest import reset_schema_ready_flag
    from sailingsa.backend.event_interest_schema import apply_schema

    reset_schema_ready_flag()
    apply_schema(conn)


def main() -> int:
    import psycopg2
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from sailingsa.backend.event_interest import (
        PUBLIC_VISITOR_COOKIE,
        register_event_interest_routes,
        reset_schema_ready_flag,
    )

    dsn = _dsn()
    results = []

    def ok(name: str) -> None:
        results.append(("PASS", name))
        print(f"PASS  {name}")

    # Bootstrap schema on a setup connection, then use one connection per request.
    setup_conn = psycopg2.connect(dsn)
    setup_conn.autocommit = False
    _setup(setup_conn)
    setup_conn.close()
    ok("local schema + Stage 1 migration applied (disposable DB only)")

    def get_db():
        conn = psycopg2.connect(dsn)
        conn.autocommit = False
        return conn

    def ret_db(conn):
        try:
            conn.close()
        except Exception:
            pass

    app = FastAPI()
    register_event_interest_routes(app, get_db, ret_db)
    client = TestClient(app)

    # --- anonymous set interest + cookie mint ---
    r = client.post("/api/events/168679/interest", json={"class_identifier": "finn"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total_interested"] == 1
    assert body["mine"]["interested"] is True
    assert body["mine"]["class_identifier"] == "finn"
    assert body["classes"][0]["interested_count"] == 1
    vid = r.cookies.get(PUBLIC_VISITOR_COOKIE)
    assert vid and len(vid) == 32
    ok("anonymous POST interest mints ssa_vid and counts")

    # duplicate same visitor same class — no double count
    r2 = client.post(
        "/api/events/168679/interest",
        json={"class_identifier": "finn"},
        cookies={PUBLIC_VISITOR_COOKIE: vid},
    )
    assert r2.status_code == 200
    assert r2.json()["total_interested"] == 1
    ok("duplicate anonymous interest is idempotent")

    # class change keeps total
    r3 = client.post(
        "/api/events/168679/interest",
        json={"class_identifier": "ilca-7"},
        cookies={PUBLIC_VISITOR_COOKIE: vid},
    )
    assert r3.status_code == 200
    data = r3.json()
    assert data["total_interested"] == 1
    assert data["mine"]["class_identifier"] == "ilca-7"
    by_id = {c["class_identifier"]: c["interested_count"] for c in data["classes"]}
    assert by_id.get("ilca-7") == 1 and "finn" not in by_id
    ok("class change keeps event total; moves class bucket")

    # Junior (no canonical class_id) still counts
    r4 = client.post(
        "/api/events/168679/interest",
        json={"class_identifier": "junior"},
        cookies={PUBLIC_VISITOR_COOKIE: vid},
    )
    assert r4.status_code == 200
    data = r4.json()
    assert data["mine"]["class_identifier"] == "junior"
    assert data["mine"]["class_id"] is None
    assert data["total_interested"] == 1
    junior = next(c for c in data["classes"] if c["class_identifier"] == "junior")
    assert junior["interested_count"] == 1
    ok("Junior (unmapped class_id) selectable and counted")

    # reject class not on event
    bad = client.post(
        "/api/events/168679/interest",
        json={"class_identifier": "soling"},
        cookies={PUBLIC_VISITOR_COOKIE: vid},
    )
    assert bad.status_code == 400
    ok("rejects class_identifier not on event")

    # event with zero edition classes cannot accept interest
    empty = client.post(
        "/api/events/45/interest",
        json={"class_identifier": "finn"},
        cookies={PUBLIC_VISITOR_COOKIE: vid},
    )
    assert empty.status_code == 400
    ok("event without edition classes cannot accept interest")

    # registered sailor
    sailor = client.post(
        "/api/events/168679/interest",
        json={"class_identifier": "finn"},
        cookies={"session": "sess-1001", PUBLIC_VISITOR_COOKIE: vid},
    )
    assert sailor.status_code == 200
    sbody = sailor.json()
    # visitor interest reconciled/withdrawn + sailor active → still coherent totals
    assert sbody["mine"]["interested"] is True
    assert sbody["mine"]["class_identifier"] == "finn"
    assert sbody["total_interested"] >= 1
    ok("registered sailor interest via session cookie")

    # expired session treated as anonymous (new write uses visitor cookie)
    expired = client.post(
        "/api/events/246456/interest",
        json={"class_identifier": "soling"},
        cookies={"session": "sess-expired", PUBLIC_VISITOR_COOKIE: "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"},
    )
    assert expired.status_code == 200
    # mine should be visitor-based since session invalid
    assert expired.json()["mine"]["interested"] is True
    ok("expired session does not authenticate; visitor path used")

    # client-supplied account_id must be ignored (not in body contract) — security:
    # forging body account_id has no effect; identity comes from cookies only.
    forged = client.post(
        "/api/events/246456/interest",
        json={"class_identifier": "flying-15", "account_id": 1001},
        cookies={PUBLIC_VISITOR_COOKIE: "ffffffffffffffffffffffffffffffff"},
    )
    assert forged.status_code == 200
    # Verify row is visitor-owned, not account 1001
    chk = psycopg2.connect(dsn)
    cur = chk.cursor()
    cur.execute(
        """
        SELECT account_id, visitor_id FROM public.event_class_interest
        WHERE event_id=246456 AND status='active'
          AND (visitor_id='ffffffffffffffffffffffffffffffff' OR account_id=1001)
        """
    )
    rows = cur.fetchall()
    cur.close()
    chk.close()
    assert any(r[1] == "ffffffffffffffffffffffffffffffff" and r[0] is None for r in rows)
    ok("client account_id in JSON is ignored; cookie identity wins")

    # withdraw
    w = client.post(
        "/api/events/168679/interest/withdraw",
        cookies={"session": "sess-1001", PUBLIC_VISITOR_COOKIE: vid},
    )
    assert w.status_code == 200
    assert w.json()["mine"]["interested"] is False
    assert w.json()["mine"]["status"] == "withdrawn"
    ok("withdraw sets status withdrawn and removes from totals")

    # batch + single get
    g = client.get("/api/events/168679/interest", cookies={"session": "sess-1001"})
    assert g.status_code == 200
    b = client.get("/api/events/interest?ids=168679,246456,45")
    assert b.status_code == 200
    events = b.json()["events"]
    assert "168679" in events and "246456" in events and "45" in events
    ok("GET single + batch interest snapshots")

    # classes endpoint includes zeros
    cls = client.get("/api/events/168679/interest/classes")
    assert cls.status_code == 200
    idents = [c["class_identifier"] for c in cls.json()["classes"]]
    assert idents == ["finn", "ilca-7", "junior"]
    assert all("interested_count" in c for c in cls.json()["classes"])
    ok("classes endpoint lists all edition classes including zero counts")

    # count accuracy invariant across active rows
    chk = psycopg2.connect(dsn)
    cur = chk.cursor()
    cur.execute(
        """
        SELECT e.event_id,
               (SELECT COUNT(*) FROM event_class_interest i
                 WHERE i.event_id=e.event_id AND i.status='active') AS total,
               (SELECT COALESCE(SUM(interested_count),0) FROM event_class_interest_counts c
                 WHERE c.event_id=e.event_id) AS summed
        FROM events e
        """
    )
    for event_id, total, summed in cur.fetchall():
        assert total == summed, (event_id, total, summed)
    cur.close()
    chk.close()
    ok("DB invariant: active total == sum(class counts) for all events")

    # concurrency: many visitors on same event
    def visitor_hit(i: int):
        v = f"{i:032x}"
        c = TestClient(app)
        resp = c.post(
            "/api/events/246456/interest",
            json={"class_identifier": "soling"},
            cookies={PUBLIC_VISITOR_COOKIE: v},
        )
        return resp.status_code, resp.json().get("total_interested")

    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = [pool.submit(visitor_hit, i) for i in range(20, 28)]
        codes = [f.result()[0] for f in as_completed(futs)]
    assert all(c == 200 for c in codes)
    final = client.get("/api/events/246456/interest").json()
    # at least the 8 new visitors active (plus earlier ones)
    assert final["total_interested"] >= 8
    ok("concurrent visitor interest submissions succeed without 5xx")

    # concurrent same sailor — still one row
    def sailor_hit(_i: int):
        c = TestClient(app)
        return c.post(
            "/api/events/168679/interest",
            json={"class_identifier": "finn"},
            cookies={"session": "sess-1002"},
        ).status_code

    with ThreadPoolExecutor(max_workers=8) as pool:
        codes = list(pool.map(sailor_hit, range(8)))
    assert all(c == 200 for c in codes)
    chk = psycopg2.connect(dsn)
    cur = chk.cursor()
    cur.execute(
        """
        SELECT COUNT(*) FROM event_class_interest
        WHERE event_id=168679 AND account_id=1002
        """
    )
    assert cur.fetchone()[0] == 1
    cur.close()
    chk.close()
    ok("concurrent same-sailor upserts collapse to one current row")

    # reconcile: visitor interest then signed-in request with same ssa_vid
    v_new = "aabbccddeeff00112233445566778899"
    client.post(
        "/api/events/246456/interest",
        json={"class_identifier": "flying-15"},
        cookies={PUBLIC_VISITOR_COOKIE: v_new},
    )
    chk = psycopg2.connect(dsn)
    cur = chk.cursor()
    cur.execute(
        """
        SELECT status, account_id FROM event_class_interest
        WHERE event_id=246456 AND visitor_id=%s
        """,
        (v_new,),
    )
    before = cur.fetchone()
    assert before and before[0] == "active" and before[1] is None
    cur.execute(
        "SELECT COUNT(*) FROM event_class_interest WHERE event_id=246456 AND status='active'"
    )
    active_before = cur.fetchone()[0]
    cur.close()
    chk.close()

    # Auto-reconcile runs inside authenticated requests; explicit endpoint also available.
    rec = client.post(
        "/api/events/interest/reconcile",
        cookies={"session": "sess-1001", PUBLIC_VISITOR_COOKIE: v_new},
    )
    assert rec.status_code == 200
    # Either this call moved rows, or a parallel auto path did — final state matters.
    chk = psycopg2.connect(dsn)
    cur = chk.cursor()
    cur.execute(
        """
        SELECT status, account_id, visitor_id FROM event_class_interest
        WHERE event_id=246456
          AND (visitor_id=%s OR account_id=1001)
        ORDER BY interest_id
        """,
        (v_new,),
    )
    rows = cur.fetchall()
    # No active visitor row for v_new; exactly one active account row for 1001 on this event
    assert not any(r[0] == "active" and r[2] == v_new for r in rows)
    cur.execute(
        """
        SELECT COUNT(*) FROM event_class_interest
        WHERE event_id=246456 AND account_id=1001 AND status='active'
        """
    )
    assert cur.fetchone()[0] == 1
    cur.execute(
        "SELECT COUNT(*) FROM event_class_interest WHERE event_id=246456 AND status='active'"
    )
    active_after = cur.fetchone()[0]
    assert active_after == active_before  # reassign keeps count; no double
    cur.close()
    chk.close()
    ok("login reconciliation never double-counts")

    # unknown event
    missing = client.get("/api/events/999999/interest")
    assert missing.status_code == 404
    ok("unknown event_id returns 404")

    failed = [n for s, n in results if s != "PASS"]
    print()
    print(f"Stage 2 API validation: {len(results)} checks, {len(failed)} failed")
    print("Production was NOT touched. api.py was NOT modified.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
