#!/usr/bin/env python3
"""Surgical patches on the LIVE-sized api.py copy. Never use the 1.4MB repo api.py."""
from pathlib import Path
import sys

REG_OLD = """        # Create email/password login method
        cur.execute(\"\"\"
            INSERT INTO public.user_accounts
            (sas_id, login_method, provider_id, email, email_verified, password_hash)
            VALUES (%s, 'email', %s, %s, FALSE, %s)
            ON CONFLICT (sas_id, login_method, provider_id) 
            DO UPDATE SET 
                email = EXCLUDED.email,
                password_hash = EXCLUDED.password_hash
            RETURNING account_id
        \"\"\", (sas_id if writes_sas and sas_id else None, email, email, password_hash))
"""

REG_NEW = """        account_sas = sas_id if writes_sas and sas_id else _ensure_public_member_sas(cur, email=email)
        # Create email/password login method
        cur.execute(\"\"\"
            INSERT INTO public.user_accounts
            (sas_id, login_method, provider_id, email, email_verified, password_hash)
            VALUES (%s, 'email', %s, %s, FALSE, %s)
            ON CONFLICT (sas_id, login_method, provider_id) 
            DO UPDATE SET 
                email = EXCLUDED.email,
                password_hash = EXCLUDED.password_hash
            RETURNING account_id
        \"\"\", (account_sas, email, email, password_hash))
"""

REG_WA_OLD = """            \"\"\", (sas_id if writes_sas and sas_id else None, whatsapp_clean, password_hash))
"""

REG_WA_NEW = """            \"\"\", (account_sas, whatsapp_clean, password_hash))
"""

SESS_OLD = """        vals = [session_token, account_id, sas_id, "email", expires_at, client_ip or None, user_agent or None]
"""

SESS_NEW = """        vals = [session_token, account_id, account_sas, "email", expires_at, client_ip or None, user_agent or None]
"""

RET_OLD = """        return {\"success\": True, \"session_token\": session_token, \"sas_id\": sas_id or None, \"ownership\": ownership}
"""

RET_NEW = """        return {\"success\": True, \"session_token\": session_token, \"session\": session_token, \"sas_id\": account_sas, \"ownership\": ownership}
"""

GG_OLD = """        google_account_id = _upsert_google_account(
            cur,
            sas_id if writes_sas else None,
            google_id,
"""

GG_NEW = """        link_sas = sas_id if writes_sas and sas_id else _ensure_public_member_sas(cur, email=email or google_email, full_name=full_name)
        google_account_id = _upsert_google_account(
            cur,
            link_sas,
            google_id,
"""

HELPER = '''
def _ensure_public_member_sas(cur, email="", full_name=""):
    if not _auth_id:
        raise ValueError("auth module missing")
    pub = _auth_id.new_public_sas_id()
    cur.execute(
        """
        INSERT INTO public.sas_id_personal (sa_sailing_id, email, full_name, account_relationship)
        VALUES (%s, %s, %s, %s)
        """,
        (pub, (email or "").strip() or None, (full_name or "").strip() or "General public", "public"),
    )
    return pub

'''

REC_START_OLD = '''        channel, dest = _auth_id.recovery_destination(dest_raw)
        cid, pin = _auth_id.issue_pin_challenge(
            store, purpose="recovery", channel=channel, destination=dest,
            worker_id=str(os.getenv("HOSTNAME") or ""),
        )
'''

REC_START_NEW = '''        channel, dest = _auth_id.recovery_destination(dest_raw)
        conn_bind = get_db_connection()
        cur_bind = conn_bind.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            account = _find_account_by_destination(cur_bind, channel, dest)
        finally:
            cur_bind.close()
            return_db_connection(conn_bind)
        if not account:
            return JSONResponse({"error": "No matching account for that email or WhatsApp number"}, status_code=400)
        cid, pin = _auth_id.issue_pin_challenge(
            store, purpose="recovery", channel=channel, destination=dest,
            account_hint=str(account["account_id"]),
            worker_id=str(os.getenv("HOSTNAME") or ""),
        )
'''

REC_DONE_OLD = '''    try:
        ch = _auth_id.verify_pin(
            store,
            str(body.get("challenge_id") or ""),
            str(body.get("pin") or body.get("code") or ""),
            worker_id=str(os.getenv("HOSTNAME") or ""),
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    new_password = str(body.get("password") or body.get("new_password") or "")
    if len(new_password) < 7:
        return JSONResponse({"error": "Password must be at least 7 characters"}, status_code=400)
    password_hash = hashlib.sha256(new_password.encode("utf-8")).hexdigest()
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        dest = ch.destination
        if ch.channel == "email":
            cur.execute(
                """
                UPDATE public.user_accounts
                SET password_hash = %s
                WHERE lower(email) = %s OR (login_method IN ('email', 'sas_id') AND lower(provider_id) = %s)
                """,
                (password_hash, dest, dest),
            )
        else:
            cur.execute(
                """
                UPDATE public.user_accounts
                SET password_hash = %s
                WHERE login_method = 'whatsapp' AND provider_id = %s
                """,
                (password_hash, dest),
            )
        if cur.rowcount < 1:
            conn.rollback()
            return JSONResponse({"error": "No matching account for that email or WhatsApp number"}, status_code=404)
        conn.commit()
    finally:
        cur.close()
        return_db_connection(conn)
'''

REC_DONE_NEW = '''    new_password = str(body.get("password") or body.get("new_password") or "")
    ok_pw, pw_err = _auth_id.valid_new_password(new_password)
    if not ok_pw:
        return JSONResponse({"error": pw_err}, status_code=400)
    try:
        ch = _auth_id.match_pin(
            store,
            str(body.get("challenge_id") or ""),
            str(body.get("pin") or body.get("code") or ""),
            worker_id=str(os.getenv("HOSTNAME") or ""),
            expected_purpose="recovery",
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    password_hash = hashlib.sha256(new_password.encode("utf-8")).hexdigest()
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        dest = ch.destination
        account = _find_account_by_destination(cur, ch.channel, dest)
        if not account:
            conn.rollback()
            return JSONResponse({"error": "No matching account for that email or WhatsApp number"}, status_code=400)
        _auth_id.bind_recovery_account(ch, account["account_id"], dest)
        cur.execute(
            "UPDATE public.user_accounts SET password_hash = %s WHERE account_id = %s",
            (password_hash, account["account_id"]),
        )
        conn.commit()
        try:
            _auth_id.consume_matched(store, ch.id)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)
    except ValueError as e:
        conn.rollback()
        return JSONResponse({"error": str(e)}, status_code=400)
    finally:
        cur.close()
        return_db_connection(conn)
'''

FULFILL_OLD = '''        else:
            if not account:
                account_id = None
                sas_out = None
            else:
                account_id = account["account_id"]
                sas_out = account.get("sas_id")
'''

FULFILL_NEW = '''        else:
            if not account and intent.create_public_account:
                pub = _ensure_public_member_sas(
                    cur,
                    email=intent.destination if intent.channel == "email" else "",
                )
                cur.execute(
                    """
                    INSERT INTO public.user_accounts (sas_id, login_method, provider_id, email, email_verified)
                    VALUES (%s, %s, %s, %s, TRUE)
                    RETURNING account_id
                    """,
                    (
                        pub,
                        intent.login_method,
                        intent.destination,
                        intent.destination if intent.channel == "email" else None,
                    ),
                )
                account_id = cur.fetchone()["account_id"]
                sas_out = pub
            elif not account:
                account_id = None
                sas_out = None
            else:
                account_id = account["account_id"]
                sas_out = account.get("sas_id")
'''


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/live-sailingsa/api.py")
    text = path.read_text(encoding="utf-8")
    if "def _ensure_public_member_sas" not in text:
        text = text.replace("def _find_account_by_destination", HELPER + "def _find_account_by_destination", 1)
    replacements = [
        (REG_OLD, REG_NEW, 1),
        (REG_WA_OLD, REG_WA_NEW, 1),
        (SESS_OLD, SESS_NEW, 1),
        (RET_OLD, RET_NEW, 1),
        (GG_OLD, GG_NEW, 1),
        (REC_START_OLD, REC_START_NEW, 1),
        (REC_DONE_OLD, REC_DONE_NEW, 1),
        (FULFILL_OLD, FULFILL_NEW, 1),
        (
            "        writes_sas = (not _auth_id) or _auth_id.account_writes_sas(ownership)\n        \n        conn = get_db_connection()\n        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)\n        \n        # Check if account already exists\n",
            "        writes_sas = (not _auth_id) or _auth_id.account_writes_sas(ownership)\n        \n        conn = get_db_connection()\n        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)\n        link_sas = sas_id if writes_sas and sas_id else _ensure_public_member_sas(cur, email=email or \"\")\n        \n        # Check if account already exists\n",
            1,
        ),
        (
            """, (sas_id if writes_sas and sas_id else None, str(facebook_id), first_name, last_name, facebook_name, profile_pic_path))""",
            """, (link_sas, str(facebook_id), first_name, last_name, facebook_name, profile_pic_path))""",
            1,
        ),
        (
            "        vals = [session_token, account_id, sas_id, \"facebook\", expires_at, client_ip or None, user_agent or None]",
            "        vals = [session_token, account_id, link_sas or sas_id, \"facebook\", expires_at, client_ip or None, user_agent or None]",
            1,
        ),
    ]
    missing = []
    for old, new, n in replacements:
        if old not in text:
            missing.append(old[:90].replace("\n", " "))
        else:
            text = text.replace(old, new, n)
    if "account_sas = sas_id if writes_sas" not in text:
        missing.append("register account_sas")
    if missing:
        print("MISSING blocks:")
        for m in missing:
            print(" -", m)
        return 1
    path.write_text(text, encoding="utf-8")
    print("patched", path, "bytes", path.stat().st_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
