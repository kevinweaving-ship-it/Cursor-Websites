#!/usr/bin/env python3
"""Live E2E for signup/login. Run ON the production host.

Does not insert user_accounts (sas_id FK to sas_id_personal) and does not
create sessions for real sailors. Issues PINs in the shared SQL store only.
Cleans up challenges it creates.
"""
from __future__ import annotations

import json
import os
import sys
import uuid
from http.cookiejar import CookieJar
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener

sys.path.insert(0, "/var/www/sailingsa/api")
sys.path.insert(0, "/var/www/sailingsa")

from modules import auth_identity as auth  # noqa: E402

BASE = os.environ.get("SSA_E2E_BASE", "https://sailingsa.co.za")
MARK = "E2EAUTH" + uuid.uuid4().hex[:10]
UNKNOWN = f"{MARK.lower()}@sailingsa.test"
UNKNOWN2 = f"{MARK.lower()}-b@sailingsa.test"


def _dsn() -> str:
    dsn = (
        os.environ.get("DATABASE_URL")
        or os.environ.get("DB_URL")
        or os.environ.get("SSA_DATABASE_URL")
    )
    if not dsn:
        raise SystemExit("DATABASE_URL/DB_URL missing")
    return dsn


def _connect():
    import psycopg2
    import psycopg2.extras

    conn = psycopg2.connect(_dsn())
    return conn, psycopg2.extras.RealDictCursor


def _http(opener, method, path, body=None):
    data = None
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with opener.open(req, timeout=30) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw.decode() or "{}"), dict(resp.headers)
    except HTTPError as e:
        raw = e.read()
        try:
            parsed = json.loads(raw.decode() or "{}")
        except Exception:
            parsed = {"error": raw.decode()[:300]}
        return e.code, parsed, dict(e.headers)


def main() -> int:
    import psycopg2

    conn, factory = _connect()
    cur = conn.cursor(cursor_factory=factory)
    auth.bind_sql_factory(lambda: psycopg2.connect(_dsn()), lambda c: c.close())
    store = auth.get_store()
    results = []
    opener = build_opener(HTTPCookieProcessor(CookieJar()))

    def ok(name, cond, detail=""):
        results.append((name, bool(cond), detail))
        print(("PASS" if cond else "FAIL"), name, detail)

    try:
        cid, pin = auth.issue_pin_challenge(
            store, purpose="login", channel="email", destination=UNKNOWN, worker_id="e2e"
        )
        status, data, _ = _http(
            opener,
            "POST",
            "/auth/challenge/verify",
            {
                "challenge_id": cid,
                "pin": pin,
                "purpose": "login",
                "destination": UNKNOWN,
                "returnTo": "https://evil.test/phish",
            },
        )
        err = str(data.get("error") or "")
        ok(
            "login_pin_unknown_no_account",
            status == 400 and "no matching account" in err.lower(),
            f"{status} {data}",
        )
        ok("login_pin_unknown_no_session", not (data.get("session") or data.get("session_token")), data)
        cur.execute("SELECT 1 FROM public.user_accounts WHERE lower(email) = %s LIMIT 1", (UNKNOWN,))
        ok("login_did_not_insert_account", cur.fetchone() is None, UNKNOWN)

        cur.execute(
            """
            SELECT sas_id::text AS sas_id FROM public.user_accounts
            WHERE sas_id::text ~ '^[0-9]+$'
            ORDER BY account_id ASC
            LIMIT 1
            """
        )
        claimed = cur.fetchone()
        dest = f"claim-{MARK.lower()}@sailingsa.test"
        if not claimed:
            ok("claim_409_existing_sailor", False, "no claimed numeric sas_id")
        else:
            claimed_sas = claimed["sas_id"]
            cid, pin = auth.issue_pin_challenge(
                store, purpose="claim", channel="email", destination=dest, worker_id="e2e", pin_len=4
            )
            status, data, _ = _http(
                opener,
                "POST",
                "/auth/challenge/verify",
                {
                    "challenge_id": cid,
                    "pin": pin,
                    "purpose": "claim",
                    "destination": dest,
                    "relationship": "self",
                    "sas_id": claimed_sas,
                },
            )
            err = str(data.get("error") or "")
            ok(
                "claim_409_existing_sailor",
                status == 409
                and (
                    bool(data.get("already_claimed"))
                    or "already claimed" in err.lower()
                ),
                f"{status} sas={claimed_sas} {data}",
            )
            cur.execute(
                "SELECT 1 FROM public.user_accounts WHERE lower(coalesce(email,'')) = %s LIMIT 1",
                (dest,),
            )
            ok("claim_did_not_create_account", cur.fetchone() is None, dest)

        cid, pin = auth.issue_pin_challenge(
            store, purpose="login", channel="email", destination=UNKNOWN2, worker_id="e2e"
        )
        status_a, data_a, _ = _http(
            opener, "POST", "/auth/challenge/verify", {"challenge_id": cid, "pin": pin, "destination": UNKNOWN2}
        )
        status_b, data_b, _ = _http(
            opener, "POST", "/auth/challenge/verify", {"challenge_id": cid, "pin": pin, "destination": UNKNOWN2}
        )
        ok("pin_first_response", status_a in (400, 409), f"{status_a} {data_a}")
        ok(
            "pin_replay_blocked",
            status_b == 400 and "already" in str(data_b.get("error") or "").lower(),
            f"{status_b} {data_b}",
        )

        status, data, _ = _http(opener, "GET", "/auth/remember/check")
        ok("remember_check_anonymous", status == 200 and data.get("recognised") is False, f"{status} {data}")
        status, data, _ = _http(opener, "POST", "/auth/remember/resume")
        ok("remember_resume_anonymous", status == 401 and not data.get("success"), f"{status} {data}")
        status, data, _ = _http(opener, "POST", "/auth/logout", {"keep_remember": True})
        ok("logout_yes_no_session", status == 200 and data.get("remember") == "kept", f"{status} {data}")
        status, data, _ = _http(opener, "POST", "/auth/logout", {"keep_remember": False})
        ok("logout_no_no_session", status == 200 and data.get("remember") == "cleared", f"{status} {data}")

        rec_cid, rec_pin = auth.issue_pin_challenge(
            store, purpose="recovery", channel="email", destination=UNKNOWN, worker_id="e2e"
        )
        status, data, _ = _http(
            opener,
            "POST",
            "/auth/recovery/complete",
            {"challenge_id": rec_cid, "pin": rec_pin, "password": "TmpE2e-unused", "returnTo": "https://evil.test/"},
        )
        ok(
            "recovery_unknown_no_account",
            status in (400, 404) and "no matching account" in str(data.get("error") or "").lower(),
            f"{status} {data}",
        )
        ok("recovery_did_not_set_session", not (data.get("session") or data.get("session_token")), data)
    finally:
        try:
            conn.rollback()
            cur.execute(
                "DELETE FROM public.auth_challenges WHERE destination IN (%s, %s) OR destination LIKE %s",
                (UNKNOWN, UNKNOWN2, f"claim-{MARK.lower()}@sailingsa.test"),
            )
            cur.execute(
                "DELETE FROM public.auth_challenges WHERE destination LIKE %s",
                ("%" + MARK.lower() + "%",),
            )
            cur.execute(
                "DELETE FROM public.user_accounts WHERE lower(coalesce(email,'')) IN (%s, %s, %s)",
                (UNKNOWN, UNKNOWN2, f"claim-{MARK.lower()}@sailingsa.test"),
            )
            conn.commit()
            ok("cleanup", True, MARK)
        except Exception as e:
            conn.rollback()
            ok("cleanup", False, str(e))
        try:
            cur.close()
            conn.close()
        except Exception:
            pass

    failed = [r for r in results if not r[1]]
    print("RESULT", "FAIL" if failed else "PASS", f"{len(results) - len(failed)}/{len(results)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
