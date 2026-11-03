#!/usr/bin/env python3
"""Early bot classify: no engage within ~12s + short trail → quarantine; Live = engaged only."""
from pathlib import Path
import sys

API = Path("/var/www/sailingsa/api/api.py")
text = API.read_text(encoding="utf-8")
orig = text

HELPER = '''
# Seconds to wait for scroll/click before sterile short trails are bots (backend, not live poll).
_LEAN_ENGAGE_GRACE_SECONDS = 12
_LEAN_STERILE_MAX_PAGES = 5


def _lean_schedule_early_no_engage_check(ip: str, visitor_id: str = "") -> None:
    """One-shot: after grace, if still no scroll/click and short trail → quarantine (bots list).

    Does not hold a DB connection while sleeping. Skip if already quarantined / crawler-cloud.
    """
    ip = (ip or "").strip()
    if not ip:
        return
    try:
        if _lean_is_crawler_cloud_ip(ip):
            return
    except Exception:
        pass

    def _run() -> None:
        import time as _time
        try:
            _time.sleep(int(_LEAN_ENGAGE_GRACE_SECONDS))
        except Exception:
            return
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            try:
                if _lean_ip_is_quarantined(cur, ip):
                    conn.commit()
                    return
            except Exception:
                pass
            try:
                _lean_classify_sterile_no_engage(cur, ip=ip, visitor_id=visitor_id or "")
                conn.commit()
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass
        except Exception:
            try:
                if conn:
                    conn.rollback()
            except Exception:
                pass
        finally:
            if conn:
                try:
                    return_db_connection(conn)
                except Exception:
                    pass

    try:
        threading.Thread(target=_run, name="lean-early-bot", daemon=True).start()
    except Exception:
        pass


def _lean_classify_sterile_no_engage(cur, *, ip: str, visitor_id: str = "") -> bool:
    """Mark bot when short trail (<=5 pages) and still no scroll/click after grace.

    Returns True when quarantined / classified bot.
    """
    ip = (ip or "").strip()
    if not ip:
        return False
    try:
        if _lean_is_crawler_cloud_ip(ip):
            _lean_quarantine_ip(cur, ip, "crawler_cloud_ip")
            return True
    except Exception:
        pass
    try:
        if _lean_ip_is_quarantined(cur, ip):
            return True
    except Exception:
        pass
    # Any engagement on this IP recently → real enough, leave alone
    try:
        _lean_ensure_page_hit_engagement_column(cur)
        cur.execute(
            """
            SELECT engagement, path, occurred_at
            FROM public.public_page_hits
            WHERE ip_address = %s
              AND occurred_at > NOW() - interval '30 minutes'
            ORDER BY occurred_at ASC
            LIMIT 20
            """,
            (ip[:80],),
        )
        rows = cur.fetchall() or []
    except Exception:
        return False
    if not rows:
        return False
    trail = []
    first_at = None
    for row in rows:
        if isinstance(row, dict):
            eng = row.get("engagement")
            path = row.get("path") or "/"
            occurred = row.get("occurred_at")
        else:
            eng, path, occurred = row[0], row[1] or "/", row[2]
        if first_at is None:
            first_at = occurred
        trail.append({"path": path, "engagement": eng, "occurred_at": occurred})
    try:
        if _lean_trail_has_engagement(trail):
            return False
    except Exception:
        pass
    # Age since first hit in window
    try:
        cur.execute(
            "SELECT (%s::timestamptz <= NOW() - make_interval(secs => %s))",
            (first_at, int(_LEAN_ENGAGE_GRACE_SECONDS)),
        )
        rr = cur.fetchone()
        aged = bool(rr[0] if rr and not isinstance(rr, dict) else (next(iter(rr.values())) if rr else False))
    except Exception:
        aged = True
    if not aged:
        return False
    n_pages = len({(t.get("path") or "/").split("?", 1)[0] for t in trail})
    if n_pages > int(_LEAN_STERILE_MAX_PAGES):
        # Long trail without engage is rare; still treat as bot for Guest purposes via display rules
        try:
            _lean_quarantine_ip(cur, ip, "no_engage_long_trail")
            return True
        except Exception:
            return False
    try:
        _lean_quarantine_ip(cur, ip, "no_engage_sterile")
        return True
    except Exception:
        return False

'''

# Insert helpers before _lean_schedule_public_presence or after _lean_is_crawler_cloud_ip block
# Place after _lean_is_crawler_cloud_ip function ends (before bounce_home was where we inserted google helpers)
anchor = "def _lean_bounce_home_bot(page_trail: list, current_path: str = \"\") -> bool:"
if "_lean_classify_sterile_no_engage" in text:
    print("SKIP helpers")
else:
    if anchor not in text:
        print("FAIL helper anchor", file=sys.stderr)
        sys.exit(1)
    text = text.replace(anchor, HELPER + "\n" + anchor, 1)
    print("OK helpers")

# --- Live: engaged only (no multi-minute grace) ---
old_live = """                # No scroll/click → not Guest (3 min grace while still on first page)
                if not is_bot:
                    try:
                        has_eng = _lean_trail_has_engagement(_trail_pre)
                    except Exception:
                        has_eng = False
                    if not has_eng:
                        fresh = False
                        try:
                            cur.execute(
                                "SELECT (%s::timestamptz > NOW() - interval '3 minutes')",
                                (d.get("last_activity"),),
                            )
                            rr = cur.fetchone()
                            if rr:
                                fresh = bool(rr[0] if not isinstance(rr, dict) else next(iter(rr.values())))
                        except Exception:
                            fresh = False
                        if not fresh:
                            is_bot = True"""

new_live = """                # Live = real only: must have scrolled/clicked (bots never do).
                # No grace flash on Live — early backend timer moves sterile to bots.
                if not is_bot:
                    try:
                        if not _lean_trail_has_engagement(_trail_pre):
                            is_bot = True
                    except Exception:
                        is_bot = True"""

if "Live = real only: must have scrolled/clicked" in text:
    print("SKIP live engaged-only")
elif old_live not in text:
    print("FAIL live grace block", file=sys.stderr)
    k = text.find("No scroll/click → not Guest")
    print(repr(text[k:k+600]))
    sys.exit(2)
else:
    text = text.replace(old_live, new_live, 1)
    print("OK live engaged-only")

# --- _touch_public_presence: crawler-cloud skip + schedule early check ---
old_touch = """    ip = _get_client_ip(request)
    if _is_noise_public_ip(ip):
        return None
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        _ensure_public_sessions_table(cur)
        # Signed-in sailor on this IP → not Public
        if _ip_has_active_logged_in_session(cur, ip):
            vid_cookie = _public_visitor_id_from_request(request)
            _purge_public_sessions_known_user(cur, ip_address=ip, visitor_id=vid_cookie)
            conn.commit()
            return None
        visitor_id = _resolve_public_visitor_id(cur, request, ip)
        _upsert_public_session(cur, visitor_id, p, ua, ip)
        try:
            _lean_ensure_page_hit_engagement_column(cur)
            eng = str(request.query_params.get("engage") or "")
            if eng:
                _lean_merge_open_hit_engagement(cur, ip=ip, visitor_id=visitor_id or "", engage_raw=eng)
        except Exception:
            pass
        conn.commit()
        return visitor_id"""

new_touch = """    ip = _get_client_ip(request)
    if _is_noise_public_ip(ip):
        return None
    # Meta/AWS/Alibaba/Google: never Guest — quarantine and skip (no live monitoring cost)
    try:
        if _lean_is_crawler_cloud_ip(ip):
            conn_q = None
            try:
                conn_q = get_db_connection()
                cur_q = conn_q.cursor()
                _lean_quarantine_ip(cur_q, ip, "crawler_cloud_ip")
                conn_q.commit()
            except Exception:
                try:
                    if conn_q:
                        conn_q.rollback()
                except Exception:
                    pass
            finally:
                if conn_q:
                    try:
                        return_db_connection(conn_q)
                    except Exception:
                        pass
            return None
    except Exception:
        pass
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        _ensure_public_sessions_table(cur)
        # Signed-in sailor on this IP → not Public
        if _ip_has_active_logged_in_session(cur, ip):
            vid_cookie = _public_visitor_id_from_request(request)
            _purge_public_sessions_known_user(cur, ip_address=ip, visitor_id=vid_cookie)
            conn.commit()
            return None
        # Already quarantined sterile bot → do not refresh live trail
        try:
            if _lean_ip_is_quarantined(cur, ip):
                conn.commit()
                return None
        except Exception:
            pass
        visitor_id = _resolve_public_visitor_id(cur, request, ip)
        _upsert_public_session(cur, visitor_id, p, ua, ip)
        try:
            _lean_ensure_page_hit_engagement_column(cur)
            eng = str(request.query_params.get("engage") or "")
            if eng:
                _lean_merge_open_hit_engagement(cur, ip=ip, visitor_id=visitor_id or "", engage_raw=eng)
        except Exception:
            pass
        conn.commit()
        # No engage yet → one-shot classify after grace (bots: ≤5 pages, no scroll/click)
        try:
            eng_now = str(request.query_params.get("engage") or "").strip()
            if not eng_now:
                _lean_schedule_early_no_engage_check(ip, visitor_id or "")
        except Exception:
            pass
        return visitor_id"""

if "Already quarantined sterile bot → do not refresh live trail" in text:
    print("SKIP touch")
elif old_touch not in text:
    print("FAIL touch block", file=sys.stderr)
    sys.exit(3)
else:
    text = text.replace(old_touch, new_touch, 1)
    print("OK touch early classify")

# --- leave path: classify if no engage ---
old_leave = """            try:
                _lean_ensure_page_hit_engagement_column(cur)
                eng = str(request.query_params.get("engage") or "")
                if eng:
                    _lean_merge_open_hit_engagement(cur, ip=ip, visitor_id=vid_leave, engage_raw=eng)
            except Exception:
                pass
            _close_open_public_page_hit(cur, ip_address=ip, visitor_id=vid_leave)
            conn.commit()
            return vid_leave or None"""

new_leave = """            try:
                _lean_ensure_page_hit_engagement_column(cur)
                eng = str(request.query_params.get("engage") or "")
                if eng:
                    _lean_merge_open_hit_engagement(cur, ip=ip, visitor_id=vid_leave, engage_raw=eng)
            except Exception:
                eng = ""
            _close_open_public_page_hit(cur, ip_address=ip, visitor_id=vid_leave)
            # Left without scroll/click → sterile bot bucket (backend, not live)
            try:
                if not str(eng or "").strip():
                    _lean_classify_sterile_no_engage(cur, ip=ip, visitor_id=vid_leave or "")
            except Exception:
                pass
            conn.commit()
            return vid_leave or None"""

if "Left without scroll/click → sterile bot bucket" in text:
    print("SKIP leave")
elif old_leave not in text:
    print("FAIL leave block", file=sys.stderr)
    sys.exit(4)
else:
    text = text.replace(old_leave, new_leave, 1)
    print("OK leave classify")

if text == orig:
    print("NO CHANGE", file=sys.stderr)
    sys.exit(5)

compile(text, str(API), "exec")
API.write_text(text, encoding="utf-8")
print("WROTE", len(text) - len(orig))
