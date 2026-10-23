#!/usr/bin/env python3
"""Live E2E for signup/login helpers. Run ON the production host.

Creates a disposable PUB_ account (not a sailor SAS ID), issues PINs in the
shared SQL store (no email/WhatsApp to a person), then hits localhost API.

Cleans up every row it creates. Does not merge or deploy.
"""
from __future__ import annotations

import json
import os
import sys
import time
import uuid
from http.cookiejar import CookieJar
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener

sys.path.insert(0, "/var/www/sailingsa/api")
sys.path.insert(0, "/var/www/sailingsa")

from modules import auth_identity as auth  # noqa: E402

BASE = os.environ.get("SSA_E2E_BASE", "http://127.0.0.1:8000")
MARK = "E2EAUTH" + uuid.uuid4().hex[:10]
EMAIL = f"{MARK.lower()}@sailingsa.test"
PUB_SAS = f"PUB_{MARK}"


def _connect():
    import psycopg2
    import psycopg2.extras

    dsn = os.environ.get("DATABASE_URL") or os.environ.get("SSA_DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL missing")
    conn = psycopg2.connect(dsn)
    return conn, psycopg2.extras.RealDictCursor


def _http(opener, method, path, body=None, cookies=None):
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
    conn, factory = _connect()
    cur = conn.cursor(cursor_factory=factory)
    auth.bind_sql_factory(lambda: conn, lambda _c: None)
    store = auth.get_store()
    results = []

    def ok(name, cond, detail=""):
        results.append((name, bool(cond), detail))
        print(("PASS" if cond else "FAIL"), name, detail)

    try:
        cur.execute(
            """
            INSERT INTO public.user_accounts (sas_id, login_method, provider_id, email, email_verified)
            VALUES (%s, 'email', %s, %s, TRUE)
            RETURNING account_id, sas_id
            """,
            (PUB_SAS, EMAIL, EMAIL),
        )
        row = cur.fetchone()
        account_id = row["account_id"]
        conn.commit()
        ok("disposable_account", account_id, f"account_id={account_id} sas={PUB_SAS}")

        cid, pin = auth.issue_pin_challenge(
            store, purpose="login", channel="email", destination=EMAIL, worker_id="e2e"
        )
        opener = build_opener(HTTPCookieProcessor(CookieJar()))
        status, data, _hdrs = _http(
            opener,
            "POST",
            "/auth/challenge/verify",
            {"challenge_id": cid, "pin": pin, "purpose": "login", "destination": EMAIL, "returnTo": "https://evil.test/phish"},
        )
        ok("login_pin_session", status == 200 and bool(data.get("session") or data.get("session_token")), f"{status} {data}")
        ok("safe_return", data.get("return_to") in ("/", None) or str(data.get("return_to") or "").startswith("/"), data.get("return_to"))
        session = data.get("session") or data.get("session_token")
        ok("no_null_sas", data.get("sas_id") == PUB_SAS, data.get("sas_id"))

        status2, data2, _ = _http(
            opener,
            "POST",
            "/auth/challenge/verify",
            {"challenge_id": cid, "pin": pin, "purpose": "login", "destination": EMAIL},
        )
        ok("login_pin_replay_blocked", status2 == 400 and "already" in str(data2.get("error") or "").lower(), f"{status2} {data2}")

        status, data, _ = _http(opener, "POST", "/auth/logout", {"keep_remember": True, "session_token": session})
        ok("logout_yes", status == 200 and data.get("remember") == "kept", f"{status} {data}")
        status, data, _ = _http(opener, "POST", "/auth/remember/resume", {})
        ok("resume_after_yes", status == 200 and bool(data.get("session") or data.get("session_token")), f"{status} {data}")
        session2 = data.get("session") or data.get("session_token")

        status, data, _ = _http(opener, "POST", "/auth/logout", {"keep_remember": False, "session_token": session2})
        ok("logout_no", status == 200 and data.get("remember") == "cleared", f"{status} {data}")
        status, data, _ = _http(opener, "POST", "/auth/remember/resume", {})
        ok("resume_after_no_denied", status in (401, 400) and not data.get("success"), f"{status} {data}")

        cur.execute(
            """
            SELECT sas_id::text AS sas_id FROM public.user_accounts
            WHERE sas_id::text ~ '^[0-9]+$'
            ORDER BY account_id ASC
            LIMIT 1
            """
        )
        claimed = cur.fetchone()
        if not claimed:
            ok("claim_409_existing_sailor", False, "no claimed numeric sas_id")
        else:
            claimed_sas = claimed["sas_id"]
            dest = f"claim-{MARK.lower()}@sailingsa.test"
            cid, pin = auth.issue_pin_challenge(
                store, purpose="claim", channel="email", destination=dest, worker_id="e2e", pin_len=4
            )
            claim_opener = build_opener(HTTPCookieProcessor(CookieJar()))
            status, data, _ = _http(
                claim_opener,
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
            ok(
                "claim_409_existing_sailor",
                status == 409 and bool(data.get("already_claimed") or "already claimed" in str(data.get("error") or "").lower()),
                f"{status} sas={claimed_sas} {data}",
            )
            cur.execute(
                "SELECT 1 FROM public.user_accounts WHERE lower(email) = %s LIMIT 1",
                (dest,),
            )
            ok("claim_did_not_create_account", cur.fetchone() is None, dest)

        rec_cid, rec_pin = auth.issue_pin_challenge(
            store, purpose="recovery", channel="email", destination=EMAIL, worker_id="e2e"
        )
        opener3 = build_opener(HTTPCookieProcessor(CookieJar()))
        status, data, _ = _http(
            opener3,
            "POST",
            "/auth/recovery/complete",
            {"challenge_id": rec_cid, "pin": rec_pin, "password": "TmpE2e-" + MARK, "returnTo": "/blank.html"},
        )
        ok("recovery_session", status == 200 and bool(data.get("session") or data.get("ok") or data.get("success")), f"{status} {data}")
    finally:
        try:
            cur.execute("DELETE FROM public.user_sessions WHERE account_id IN (SELECT account_id FROM public.user_accounts WHERE sas_id::text = %s OR lower(email) = %s)", (PUB_SAS, EMAIL))
            cur.execute("DELETE FROM public.auth_remembered_devices WHERE account_id::text IN (SELECT account_id::text FROM public.user_accounts WHERE sas_id::text = %s OR lower(email) = %s)", (PUB_SAS, EMAIL))
            cur.execute("DELETE FROM public.auth_verified_contacts WHERE account_id::text IN (SELECT account_id::text FROM public.user_accounts WHERE sas_id::text = %s) OR account_id LIKE %s", (PUB_SAS, "dest:" + EMAIL[:20] + "%"))
            cur.execute("DELETE FROM public.auth_challenges WHERE destination IN (%s, %s) OR destination LIKE %s", (EMAIL, f"claim-{MARK.lower()}@sailingsa.test", MARK.lower() + "%"))
            cur.execute("DELETE FROM public.user_accounts WHERE sas_id::text = %s OR lower(email) = %s", (PUB_SAS, EMAIL))
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
    print("RESULT", "FAIL" if failed else "PASS", f"{len(results)-len(failed)}/{len(results)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
