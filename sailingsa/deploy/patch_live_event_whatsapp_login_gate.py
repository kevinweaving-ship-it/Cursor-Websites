#!/usr/bin/env python3
"""Surgical live api.py patch: WhatsApp messages only for logged-in registered users."""
from pathlib import Path
import sys

API = Path("/var/www/sailingsa/api/api.py")

HELPERS = r'''
def _session_is_registered_user(request: Request) -> bool:
    """Logged-in sailor or user account (not a public guest)."""
    try:
        if _session_role_is_super_admin(request) or _session_role_is_admin(request):
            return True
        if _session_role_is_club_admin(request):
            return True
        if str(_get_session_sas_id(request) or "").strip():
            return True
        if _get_session_role(request):
            return True
    except Exception:
        return False
    return False


def _event_whatsapp_messages(regatta_id: str) -> list:
    rid = str(regatta_id or "").strip()
    if not rid:
        return []
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cur.execute(
                """
                SELECT from_me, sender_name, kind,
                       left(coalesce(body, ''), 500) AS body,
                       left(coalesce(caption, ''), 200) AS caption,
                       duration_sec,
                       to_char(occurred_at AT TIME ZONE 'Africa/Johannesburg', 'YYYY-MM-DD"T"HH24:MI:SS') AS occurred_at
                FROM (
                  SELECT from_me, sender_name, kind, body, caption, duration_sec, occurred_at
                  FROM public.event_whatsapp_messages
                  WHERE regatta_id = %s
                    AND COALESCE(kind, '') NOT IN ('empty', 'group-list')
                  ORDER BY occurred_at DESC NULLS LAST
                  LIMIT 40
                ) newest
                ORDER BY occurred_at ASC NULLS LAST
                """,
                (rid,),
            )
            rows = cur.fetchall() or []
            out = []
            for r in rows:
                if isinstance(r, dict):
                    out.append(dict(r))
                else:
                    out.append({
                        "from_me": r[0],
                        "sender_name": r[1],
                        "kind": r[2],
                        "body": r[3],
                        "caption": r[4],
                        "duration_sec": r[5],
                        "occurred_at": r[6],
                    })
            return out
        finally:
            cur.close()
            return_db_connection(conn)
    except Exception:
        return []


'''

OLD_GET = '''@app.get("/api/regatta/{regatta_id}/event-whatsapp")
async def api_regatta_event_whatsapp(request: Request, regatta_id: str):
    rid = str(regatta_id or "").strip()
    return {
        "ok": True,
        "show": _event_whatsapp_show_on_event(rid),
        "can_toggle": _session_can_toggle_event_whatsapp(request, rid),
    }
'''

NEW_GET = '''@app.get("/api/regatta/{regatta_id}/event-whatsapp")
async def api_regatta_event_whatsapp(request: Request, regatta_id: str):
    rid = str(regatta_id or "").strip()
    logged_in = _session_is_registered_user(request)
    show = _event_whatsapp_show_on_event(rid)
    can_toggle = _session_can_toggle_event_whatsapp(request, rid)
    messages = _event_whatsapp_messages(rid) if (logged_in and (show or can_toggle)) else []
    return {
        "ok": True,
        "show": show,
        "can_toggle": can_toggle,
        "logged_in": logged_in,
        "messages": messages,
    }
'''

OLD_JS = "regatta-slot-card.js?v=20260912wa3"
NEW_JS = "regatta-slot-card.js?v=20260912wa4"


def apply(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(OLD_GET) != 1:
        raise SystemExit(f"{path}: GET count {text.count(OLD_GET)}")
    if "_session_is_registered_user" not in text:
        text = text.replace(OLD_GET, HELPERS + NEW_GET, 1)
    else:
        text = text.replace(OLD_GET, NEW_GET, 1)
    if text.count(OLD_JS) != 1:
        raise SystemExit(f"{path}: js ver count {text.count(OLD_JS)}")
    text = text.replace(OLD_JS, NEW_JS, 1)
    path.write_text(text, encoding="utf-8")
    print("patched", path)


def main() -> int:
    apply(Path(sys.argv[1]) if len(sys.argv) > 1 else API)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
