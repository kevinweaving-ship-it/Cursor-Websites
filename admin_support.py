"""
Helpers for admin_api only (port 8002). Duplicated from main API patterns — do not import api.py.
"""
from __future__ import annotations

import os
import re
import socket
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
import psycopg2.extras
import psycopg2.pool
from fastapi import Request
from zoneinfo import ZoneInfo

DB_URL = os.getenv("DB_URL", "postgresql://sailors_user:change_me_strong@localhost:5432/sailors_master")
MAIN_API_URL = (os.getenv("MAIN_API_URL") or "http://127.0.0.1:8000").rstrip("/")

SERVER_START_TS = int(time.time())

ADMIN_LIVE_HOSTNAME = "vm103zuex.yourlocaldomain.com"

DASHBOARD_DATA_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate",
    "Pragma": "no-cache",
}

DB_POOL: psycopg2.pool.ThreadedConnectionPool | None = None

_cache: dict = {}
_cache_timestamps: dict = {}
CACHE_TTL = 30


def get_cached(key: str, ttl_seconds: int = CACHE_TTL):
    if key in _cache:
        if time.time() - _cache_timestamps[key] < ttl_seconds:
            return _cache[key]
        del _cache[key]
        del _cache_timestamps[key]
    return None


def set_cached(key: str, value, ttl_seconds: int = CACHE_TTL):
    _cache[key] = value
    _cache_timestamps[key] = time.time()


def init_db_pool():
    global DB_POOL
    if DB_POOL is None:
        DB_POOL = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=12,
            dsn=DB_URL,
            cursor_factory=psycopg2.extras.RealDictCursor,
        )
    return DB_POOL


def get_db_connection(request_id: str | None = None):
    pool = init_db_pool()
    return pool.getconn()


def return_db_connection(conn):
    pool = DB_POOL
    if pool and conn:
        try:
            pool.putconn(conn)
        except Exception:
            try:
                conn.close()
            except Exception:
                pass


def table_exists(name: str) -> bool:
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name=%s LIMIT 1",
            (name,),
        )
        return cur.fetchone() is not None
    except Exception:
        return False
    finally:
        if conn:
            return_db_connection(conn)


def column_exists(table: str, col: str) -> bool:
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name=%s AND column_name=%s LIMIT 1",
            (table, col),
        )
        return cur.fetchone() is not None
    except Exception:
        return False
    finally:
        if conn:
            return_db_connection(conn)


def _derive_device_type(user_agent: str) -> str:
    if not user_agent:
        return "desktop"
    ua = user_agent.lower()
    if any(x in ua for x in ("mobile", "android", "iphone", "ipod", "webos", "blackberry", "windows phone")):
        return "mobile"
    return "desktop"


def _format_dt_sast(dt):
    if not dt:
        return "—"
    try:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(ZoneInfo("Africa/Johannesburg")).strftime("%Y-%m-%d %H:%M SAST")
    except Exception:
        return str(dt) if dt else "—"


def _get_site_stats():
    cached = get_cached("site_stats", ttl_seconds=300)
    if cached is not None:
        return cached
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT COUNT(DISTINCT sailor_id) AS active_sailors
            FROM (
                SELECT r.helm_sa_sailing_id AS sailor_id FROM results r
                JOIN regattas reg ON reg.regatta_id = r.regatta_id
                WHERE r.raced = TRUE AND r.helm_sa_sailing_id IS NOT NULL AND r.helm_sa_sailing_id::text != ''
                  AND (reg.end_date IS NOT NULL OR reg.start_date IS NOT NULL)
                UNION ALL
                SELECT r.crew_sa_sailing_id AS sailor_id FROM results r
                JOIN regattas reg ON reg.regatta_id = r.regatta_id
                WHERE r.raced = TRUE AND r.crew_sa_sailing_id IS NOT NULL AND r.crew_sa_sailing_id::text != ''
                  AND (reg.end_date IS NOT NULL OR reg.start_date IS NOT NULL)
            ) u
        """)
        row = cur.fetchone()
        val = row.get("active_sailors") if row else None
        active_sailors = int(val) if val is not None else 0
        cur.execute("""
            SELECT COUNT(DISTINCT r.class_id) AS classes_sailed
            FROM results r
            WHERE r.raced = TRUE AND r.class_id IS NOT NULL
        """)
        row2 = cur.fetchone()
        val2 = row2.get("classes_sailed") if row2 else None
        classes_sailed = int(val2) if val2 is not None else 0
        cur.execute("""
            SELECT COUNT(DISTINCT r.regatta_id) AS regattas_sailed
            FROM regattas r
            JOIN results res ON res.regatta_id = r.regatta_id
            WHERE res.raced = TRUE
        """)
        row3 = cur.fetchone()
        val3 = row3.get("regattas_sailed") if row3 else None
        regattas_sailed = int(val3) if val3 is not None else 0
        cur.execute("SELECT COUNT(*) AS races_raced FROM results r WHERE r.raced = TRUE")
        row4 = cur.fetchone()
        val4 = row4.get("races_raced") if row4 else None
        races_raced = int(val4) if val4 is not None else 0
        cur.close()
        result = {
            "active_sailors": active_sailors,
            "classes_sailed": classes_sailed,
            "regattas_sailed": regattas_sailed,
            "races_raced": races_raced,
        }
        set_cached("site_stats", result, ttl_seconds=300)
        return result
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        return {
            "active_sailors": None,
            "classes_sailed": None,
            "regattas_sailed": None,
            "races_raced": None,
            "error": str(e),
        }
    finally:
        if conn:
            return_db_connection(conn)


def _admin_dashboard_data_base() -> dict:
    """Prefer main API process meta so restart poll matches sailingsa-api restarts."""
    now = int(time.time())
    try:
        r = httpx.get(f"{MAIN_API_URL}/api/process-meta", timeout=3.0)
        if r.status_code == 200:
            j = r.json()
            start = int(j["server_start_timestamp"])
            return {
                "server_start_timestamp": start,
                "uptime_seconds": int(j.get("uptime_seconds", now - start)),
                "now_timestamp": int(j.get("now_timestamp", now)),
            }
    except Exception:
        pass
    return {
        "server_start_timestamp": SERVER_START_TS,
        "uptime_seconds": now - SERVER_START_TS,
        "now_timestamp": now,
    }


def _admin_online_users_full(cur) -> list:
    if not table_exists("user_sessions"):
        return []
    try:
        has_path = column_exists("user_sessions", "last_path")
        has_activity = column_exists("user_sessions", "last_activity")
        has_logout = column_exists("user_sessions", "logout_time")
        has_ip = column_exists("user_sessions", "ip_address")
        has_ua = column_exists("user_sessions", "user_agent")
        has_dt = column_exists("user_sessions", "device_type")
        if has_logout and has_activity:
            where_clause = "s.logout_time IS NULL AND s.last_activity >= NOW() - INTERVAL '30 minutes'"
        elif has_logout:
            where_clause = "s.logout_time IS NULL AND s.created_at >= NOW() - INTERVAL '30 minutes'"
        else:
            where_30min = (
                "s.last_activity >= NOW() - INTERVAL '30 minutes' OR (s.last_activity IS NULL AND s.created_at >= NOW() - INTERVAL '30 minutes')"
                if has_activity
                else "s.created_at >= NOW() - INTERVAL '30 minutes'"
            )
            where_clause = "s.expires_at > NOW() AND (" + where_30min + ")"
        order_col = "COALESCE(s.last_activity, s.created_at)" if has_activity else "s.created_at"
        path_col = "s.last_path" if has_path else "''"
        cols = ["s.session_id", "s.sas_id", "s.created_at AS login_at", path_col + " AS last_path"]
        if has_ip:
            cols.append("s.ip_address")
        if has_ua:
            cols.append("s.user_agent")
        if has_dt:
            cols.append("s.device_type")
        cur.execute("""
            SELECT """ + ", ".join(cols) + """,
                COALESCE(TRIM(p.full_name), TRIM(p.first_name || ' ' || COALESCE(p.last_name, ''))) AS name
            FROM public.user_sessions s
            LEFT JOIN public.sas_id_personal p ON p.sa_sailing_id::text = s.sas_id
            WHERE """ + where_clause + """
            ORDER BY """ + order_col + """ DESC NULLS LAST
        """)
        rows = cur.fetchall() or []
        out = []
        for r in rows:
            login_at = r.get("login_at")
            session_start_unix = int(login_at.timestamp()) if login_at and getattr(login_at, "timestamp", None) else None
            device = (r.get("device_type") or "").strip() if r.get("device_type") else ""
            if not device and r.get("user_agent"):
                device = _derive_device_type(r.get("user_agent") or "")
            out.append({
                "session_id": str(r.get("session_id") or ""),
                "sas_id": str(r.get("sas_id") or ""),
                "name": (r.get("name") or "—") if r else "—",
                "login_time_iso": login_at.isoformat() if login_at and getattr(login_at, "isoformat", None) else "",
                "session_start_unix": session_start_unix,
                "current_page": (r.get("last_path") or "—") if r else "—",
                "device": device or "—",
                "ip_address": (r.get("ip_address") or "—") if r else "—",
            })
        return out
    except Exception:
        return []


def _admin_offline_sessions(cur, limit: int = 50) -> list:
    if not table_exists("user_sessions"):
        return []
    try:
        has_logout = column_exists("user_sessions", "logout_time")
        has_activity = column_exists("user_sessions", "last_activity")
        has_dt = column_exists("user_sessions", "device_type")
        has_ip = column_exists("user_sessions", "ip_address")
        has_ua = column_exists("user_sessions", "user_agent")
        cols = ["s.session_id", "s.sas_id", "s.created_at AS login_at"]
        if has_logout:
            cols.append("s.logout_time AS logout_at")
        if has_activity:
            cols.append("s.last_activity AS last_activity_at")
        if has_ip:
            cols.append("s.ip_address")
        if has_ua:
            cols.append("s.user_agent")
        if has_dt:
            cols.append("s.device_type")
        if has_logout and has_activity:
            where = "(s.logout_time IS NOT NULL) OR (s.last_activity < NOW() - INTERVAL '30 minutes') OR (s.last_activity IS NULL AND s.created_at < NOW() - INTERVAL '30 minutes')"
            order = "COALESCE(s.logout_time, s.last_activity, s.created_at) DESC"
        elif has_logout:
            where = "s.logout_time IS NOT NULL"
            order = "s.logout_time DESC"
        else:
            return []
        cur.execute("""
            SELECT """ + ", ".join(cols) + """,
                COALESCE(TRIM(p.full_name), TRIM(p.first_name || ' ' || COALESCE(p.last_name, ''))) AS name
            FROM public.user_sessions s
            LEFT JOIN public.sas_id_personal p ON p.sa_sailing_id::text = s.sas_id
            WHERE """ + where + """
            ORDER BY """ + order + """
            LIMIT %s
        """, (limit,))
        rows = cur.fetchall() or []
        out = []
        for r in rows:
            login_at = r.get("login_at")
            logout_at = r.get("logout_at") if has_logout else None
            last_act = r.get("last_activity_at")
            end_at = logout_at or last_act or login_at
            duration_seconds = None
            if login_at and end_at and getattr(login_at, "timestamp", None) and getattr(end_at, "timestamp", None):
                duration_seconds = int(end_at.timestamp() - login_at.timestamp())
            device = (r.get("device_type") or "").strip() if r.get("device_type") else ""
            if not device and r.get("user_agent"):
                device = _derive_device_type(r.get("user_agent") or "")
            out.append({
                "session_id": str(r.get("session_id") or ""),
                "sas_id": str(r.get("sas_id") or ""),
                "name": (r.get("name") or "—") if r else "—",
                "login_time_iso": login_at.isoformat() if login_at and getattr(login_at, "isoformat", None) else "",
                "logout_time_iso": (
                    logout_at.isoformat()
                    if logout_at and getattr(logout_at, "isoformat", None)
                    else (end_at.isoformat() if end_at and getattr(end_at, "isoformat", None) else "")
                ),
                "duration_seconds": duration_seconds,
                "device": device or "—",
                "ip_address": (r.get("ip_address") or "—") if r else "—",
            })
        return out
    except Exception:
        return []


def _admin_user_session_history(cur, sas_id: str) -> dict:
    out = {
        "ok": True,
        "sessions": [],
        "active_session": None,
        "total_sessions_count": 0,
        "total_duration_seconds": 0,
        "last_login_iso": "",
        "device": "",
        "ip_address": "",
        "user_agent": "",
    }
    if not table_exists("user_sessions"):
        return out
    has_logout = column_exists("user_sessions", "logout_time")
    has_activity = column_exists("user_sessions", "last_activity")
    has_ip = column_exists("user_sessions", "ip_address")
    has_ua = column_exists("user_sessions", "user_agent")
    has_dt = column_exists("user_sessions", "device_type")
    cols = ["session_id", "created_at", "expires_at"]
    if has_logout:
        cols.append("logout_time")
    if has_activity:
        cols.append("last_activity")
    if has_ip:
        cols.append("ip_address")
    if has_ua:
        cols.append("user_agent")
    if has_dt:
        cols.append("device_type")
    try:
        cur.execute(
            "SELECT " + ", ".join(cols) + " FROM public.user_sessions WHERE sas_id = %s ORDER BY created_at DESC",
            (sas_id,),
        )
        rows = cur.fetchall() or []
    except Exception:
        return out
    now_ts = time.time()
    sessions = []
    total_sec = 0
    active_session = None
    has_analytics = table_exists("analytics_events")
    for r in rows:
        sid = r.get("session_id")
        created = r.get("created_at")
        logout_time = r.get("logout_time") if has_logout else None
        last_activity = r.get("last_activity") if has_activity else None
        created_ts = created.timestamp() if created and getattr(created, "timestamp", None) else None
        login_iso = created.isoformat() if created and getattr(created, "isoformat", None) else ""
        logout_iso = logout_time.isoformat() if logout_time and getattr(logout_time, "isoformat", None) else None
        if logout_time and getattr(logout_time, "timestamp", None) and created_ts is not None:
            duration_sec = int(logout_time.timestamp() - created_ts)
        elif created_ts is not None:
            duration_sec = int(now_ts - created_ts)
        else:
            duration_sec = 0
        duration_sec = max(0, duration_sec)
        total_sec += duration_sec
        device = (r.get("device_type") or "").strip() if has_dt and r.get("device_type") else ""
        if not device and r.get("user_agent"):
            device = _derive_device_type(r.get("user_agent") or "")
        pages = []
        if has_analytics and sid:
            try:
                cur.execute(
                    "SELECT metadata->>'path' AS path, created_at FROM public.analytics_events WHERE session_id = %s AND event_type = 'page_view' ORDER BY created_at",
                    (str(sid),),
                )
                pv_rows = cur.fetchall() or []
                for i, pv in enumerate(pv_rows):
                    path = (pv.get("path") or "").strip() or "—"
                    ct = pv.get("created_at")
                    ct_ts = ct.timestamp() if ct and getattr(ct, "timestamp", None) else None
                    if i + 1 < len(pv_rows):
                        next_ct = pv_rows[i + 1].get("created_at")
                        next_ts = next_ct.timestamp() if next_ct and getattr(next_ct, "timestamp", None) else None
                        time_seconds = int(next_ts - ct_ts) if ct_ts is not None and next_ts is not None else None
                    else:
                        end_ts = (
                            logout_time.timestamp()
                            if logout_time and getattr(logout_time, "timestamp", None)
                            else last_activity.timestamp()
                            if last_activity and getattr(last_activity, "timestamp", None)
                            else now_ts
                        )
                        time_seconds = int(end_ts - ct_ts) if ct_ts is not None else None
                    pages.append({"path": path, "time_seconds": max(0, time_seconds) if time_seconds is not None else None})
            except Exception:
                pass
        sess_obj = {
            "session_id": sid,
            "login_time_iso": login_iso,
            "logout_time_iso": logout_iso,
            "duration_seconds": duration_sec,
            "device": device or "—",
            "ip_address": (r.get("ip_address") or "—") if has_ip else "—",
            "user_agent": (r.get("user_agent") or "—") if has_ua else "—",
            "pages": pages,
        }
        sessions.append(sess_obj)
        last_act_ts = last_activity.timestamp() if last_activity and getattr(last_activity, "timestamp", None) else None
        is_active = logout_time is None and (last_act_ts is None or (now_ts - last_act_ts < 1800))
        if is_active and active_session is None:
            active_session = sess_obj
    out["sessions"] = sessions
    out["total_sessions_count"] = len(sessions)
    out["total_duration_seconds"] = total_sec
    out["last_login_iso"] = sessions[0]["login_time_iso"] if sessions else ""
    ref = active_session or (sessions[0] if sessions else None)
    if ref:
        out["device"] = ref.get("device") or ""
        out["ip_address"] = ref.get("ip_address") or ""
        out["user_agent"] = ref.get("user_agent") or ""
    return out


def _admin_list_sailors(cur) -> list:
    cur.execute("""
        SELECT COALESCE(TRIM(s.full_name), TRIM(s.first_name || ' ' || COALESCE(s.last_name, ''))) AS name,
               s.sa_sailing_id::text AS sas_id
        FROM public.sas_id_personal s
        ORDER BY name NULLS LAST, s.sa_sailing_id
    """)
    rows = cur.fetchall()
    return [dict(r) for r in (rows or [])]


def _admin_list_clubs(cur) -> list:
    cur.execute("""
        SELECT club_id, COALESCE(TRIM(club_abbrev), '') AS club_abbrev,
               COALESCE(TRIM(club_fullname), TRIM(club_abbrev), '') AS name
        FROM public.clubs
        ORDER BY name NULLS LAST, club_id
    """)
    rows = cur.fetchall()
    return [dict(r) for r in (rows or [])]


def _admin_list_classes(cur) -> list:
    cur.execute("""
        SELECT c.class_id, c.class_name, COUNT(DISTINCT sailor_id) AS sailor_count
        FROM (
            SELECT r.class_id, r.helm_sa_sailing_id AS sailor_id FROM results r WHERE r.class_id IS NOT NULL AND r.helm_sa_sailing_id IS NOT NULL
            UNION
            SELECT r.class_id, r.crew_sa_sailing_id AS sailor_id FROM results r WHERE r.class_id IS NOT NULL AND r.crew_sa_sailing_id IS NOT NULL
        ) t
        JOIN classes c ON c.class_id = t.class_id
        GROUP BY c.class_id, c.class_name
        ORDER BY sailor_count DESC
    """)
    rows = cur.fetchall()
    return [dict(r) for r in (rows or [])]


def _admin_list_regattas(cur) -> list:
    cur.execute("""
        SELECT regatta_id, event_name, COALESCE(end_date, start_date)::text AS date
        FROM regattas
        ORDER BY COALESCE(end_date, start_date) DESC NULLS LAST
    """)
    rows = cur.fetchall()
    return [dict(r) for r in (rows or [])]


def _admin_list_races(cur) -> list:
    cur.execute("""
        SELECT rb.regatta_id, rb.block_id AS race_no, COALESCE(TRIM(rb.fleet_label), TRIM(rb.class_canonical), '') AS fleet,
               COALESCE(r.end_date, r.start_date)::text AS regatta_date
        FROM regatta_blocks rb
        LEFT JOIN regattas r ON r.regatta_id = rb.regatta_id
        ORDER BY COALESCE(r.end_date, r.start_date) DESC NULLS LAST, rb.block_id
    """)
    rows = cur.fetchall()
    return [dict(r) for r in (rows or [])]


def _get_table_columns_schema(cur, table: str) -> str:
    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position
    """, (table,))
    rows = cur.fetchall() or []
    cols = [r["column_name"] for r in rows]
    return ", ".join(cols) if cols else "(none)"


def _admin_list_registered_users(cur, include_whatsapp: bool = True) -> list:
    has_sessions = table_exists("user_sessions")
    if not has_sessions:
        online_expr = "FALSE AS online"
        order_online = "1"
        login_count_expr = "0 AS login_count"
    else:
        has_logout = column_exists("user_sessions", "logout_time")
        has_activity = column_exists("user_sessions", "last_activity")
        if has_logout and has_activity:
            online_expr = "EXISTS (SELECT 1 FROM public.user_sessions s WHERE s.sas_id = u.sas_id AND s.logout_time IS NULL AND s.last_activity >= NOW() - INTERVAL '30 minutes') AS online"
            order_online = "EXISTS (SELECT 1 FROM public.user_sessions s WHERE s.sas_id = u.sas_id AND s.logout_time IS NULL AND s.last_activity >= NOW() - INTERVAL '30 minutes')"
        elif has_logout:
            online_expr = "EXISTS (SELECT 1 FROM public.user_sessions s WHERE s.sas_id = u.sas_id AND s.logout_time IS NULL AND s.created_at >= NOW() - INTERVAL '30 minutes') AS online"
            order_online = "EXISTS (SELECT 1 FROM public.user_sessions s WHERE s.sas_id = u.sas_id AND s.logout_time IS NULL AND s.created_at >= NOW() - INTERVAL '30 minutes')"
        else:
            online_expr = "EXISTS (SELECT 1 FROM public.user_sessions s WHERE s.sas_id = u.sas_id AND s.expires_at > NOW() AND (s.last_activity >= NOW() - INTERVAL '30 minutes' OR (s.last_activity IS NULL AND s.created_at >= NOW() - INTERVAL '30 minutes'))) AS online"
            order_online = "EXISTS (SELECT 1 FROM public.user_sessions s WHERE s.sas_id = u.sas_id AND s.expires_at > NOW())"
        login_count_expr = "(SELECT COUNT(*) FROM public.user_sessions us WHERE us.sas_id = u.sas_id) AS login_count"
    whatsapp_expr = (
        "MAX(u.provider_id) FILTER (WHERE u.login_method = 'whatsapp') AS whatsapp_provider_id"
        if include_whatsapp
        else "NULL::text AS whatsapp_provider_id"
    )
    cur.execute("""
        SELECT
            COALESCE(TRIM(MAX(p.full_name)), TRIM(MAX(p.first_name) || ' ' || COALESCE(MAX(p.last_name), ''))) AS name,
            u.sas_id,
            MAX(u.email) AS email,
            """ + whatsapp_expr + """,
            MIN(u.created_at) AS date_registered,
            MAX(u.last_login) AS last_login,
            """ + login_count_expr + """,
            CASE WHEN BOOL_OR(u.is_active) = TRUE THEN 'active' ELSE 'inactive' END AS status,
            """ + online_expr + """
        FROM public.user_accounts u
        LEFT JOIN public.sas_id_personal p ON p.sa_sailing_id::text = u.sas_id
        GROUP BY u.sas_id
        ORDER BY """ + order_online + """ DESC NULLS LAST, MAX(u.last_login) DESC NULLS LAST
    """)
    rows = cur.fetchall()
    out = []
    for r in (rows or []):
        d = dict(r)
        dr = d.get("date_registered")
        ll = d.get("last_login")
        d["date_registered"] = _format_dt_sast(dr) if dr is not None else "—"
        d["last_login"] = _format_dt_sast(ll) if ll is not None else "—"
        d["login_count"] = str(d.get("login_count") or 0)
        d["active"] = bool(d.pop("online", False))
        out.append(d)
    return out


def _admin_active_sailors(cur) -> list:
    cur.execute("""
        WITH block_counts AS (
            SELECT block_id, COUNT(*)::int AS count FROM results WHERE block_id IS NOT NULL GROUP BY block_id
        ),
        sailor_results AS (
            SELECT r.helm_sa_sailing_id AS sailor_id, r.result_id, r.regatta_id, r.block_id, r.rank,
                   reg.event_name, COALESCE(reg.end_date, reg.start_date) AS regatta_date,
                   reg.regatta_id AS regatta_slug,
                   c.class_id,
                   COALESCE(NULLIF(TRIM(r.fleet_label), ''), NULLIF(TRIM(c.class_name), ''), '') AS class_name,
                   COALESCE(rb.entries_raced, bc.count)::int AS entries,
                   COALESCE(NULLIF(r.races_sailed, 0), (SELECT COUNT(*) FROM jsonb_object_keys(COALESCE(r.race_scores, '{}'::jsonb)) k WHERE k ~ '^R[0-9]'))::int AS race_entries
            FROM results r
            JOIN regattas reg ON reg.regatta_id = r.regatta_id
            LEFT JOIN classes c ON c.class_id = r.class_id
            LEFT JOIN regatta_blocks rb ON rb.block_id = r.block_id
            LEFT JOIN block_counts bc ON bc.block_id = r.block_id
            WHERE r.raced = TRUE AND r.helm_sa_sailing_id IS NOT NULL AND r.helm_sa_sailing_id::text != ''
              AND (reg.end_date IS NOT NULL OR reg.start_date IS NOT NULL)
            UNION ALL
            SELECT r.crew_sa_sailing_id AS sailor_id, r.result_id, r.regatta_id, r.block_id, r.rank,
                   reg.event_name, COALESCE(reg.end_date, reg.start_date) AS regatta_date,
                   reg.regatta_id AS regatta_slug,
                   c.class_id,
                   COALESCE(NULLIF(TRIM(r.fleet_label), ''), NULLIF(TRIM(c.class_name), ''), '') AS class_name,
                   COALESCE(rb.entries_raced, bc.count)::int AS entries,
                   COALESCE(NULLIF(r.races_sailed, 0), (SELECT COUNT(*) FROM jsonb_object_keys(COALESCE(r.race_scores, '{}'::jsonb)) k WHERE k ~ '^R[0-9]'))::int AS race_entries
            FROM results r
            JOIN regattas reg ON reg.regatta_id = r.regatta_id
            LEFT JOIN classes c ON c.class_id = r.class_id
            LEFT JOIN regatta_blocks rb ON rb.block_id = r.block_id
            LEFT JOIN block_counts bc ON bc.block_id = r.block_id
            WHERE r.raced = TRUE AND r.crew_sa_sailing_id IS NOT NULL AND r.crew_sa_sailing_id::text != ''
              AND (reg.end_date IS NOT NULL OR reg.start_date IS NOT NULL)
        ),
        agg AS (
            SELECT sailor_id,
                   SUM(race_entries)::int AS races_count,
                   COUNT(DISTINCT regatta_id)::int AS regattas_count,
                   MAX(regatta_date) AS last_active_date
            FROM sailor_results
            GROUP BY sailor_id
        ),
        last_row AS (
            SELECT DISTINCT ON (sr.sailor_id) sr.sailor_id, sr.event_name AS last_regatta_name, sr.regatta_date,
                   sr.regatta_slug, sr.class_id AS last_class_id, sr.class_name AS last_class_sailed, sr.rank::int AS last_regatta_rank, sr.entries AS fleet_size
            FROM sailor_results sr
            JOIN agg a ON a.sailor_id = sr.sailor_id AND sr.regatta_date = a.last_active_date
            ORDER BY sr.sailor_id, sr.result_id
        )
        SELECT a.sailor_id::text AS sas_id,
               COALESCE(NULLIF(TRIM(s.full_name), ''), NULLIF(TRIM(s.first_name || ' ' || COALESCE(s.last_name, '')), ''), '') AS full_name,
               a.races_count,
               a.regattas_count,
               a.last_active_date::text AS last_active_date,
               lr.last_regatta_name,
               lr.regatta_slug,
               lr.last_class_id,
               lr.last_class_sailed,
               lr.last_regatta_rank,
               lr.fleet_size
        FROM agg a
        LEFT JOIN sas_id_personal s ON s.sa_sailing_id::text = a.sailor_id::text
        JOIN last_row lr ON lr.sailor_id = a.sailor_id
        ORDER BY a.races_count DESC
    """)
    rows = cur.fetchall() or []
    out = []
    for rank, row in enumerate(rows, start=1):
        d = dict(row)
        d["rank"] = rank
        out.append(d)
    return out


def _ordinal(n):
    if n is None:
        return ""
    try:
        n = int(n)
    except (TypeError, ValueError):
        return ""
    s = str(n)
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return s + suffix


def _slug_from_name(full_name: str) -> str:
    if not full_name or not isinstance(full_name, str):
        return ""
    s = full_name.strip().lower().replace("&", " and ")
    s = re.sub(r"[^\w\s\-]", "", s)
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def _sailor_canonical_slug(full_name: str, sas_id: str, has_duplicate: bool) -> str:
    base = _slug_from_name(full_name)
    if not base:
        return f"sailor-{sas_id}" if sas_id else "sailor"
    if has_duplicate and sas_id:
        return f"{base}-{sas_id}"
    return base


def _batch_sailor_slugs_for_sas_ids(sas_ids: list):
    if not sas_ids:
        return {}
    ids = list({str(i).strip() for i in sas_ids if i is not None and str(i).strip().isdigit()})
    if not ids:
        return {}
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cur.execute("""
                SELECT sa_sailing_id::text AS sas_id,
                    COALESCE(TRIM(full_name), TRIM(first_name || ' ' || COALESCE(last_name, ''))) AS full_name
                FROM public.sas_id_personal
                WHERE sa_sailing_id::text = ANY(%s)
            """, (ids,))
            rows = cur.fetchall()
            if not rows:
                return {}
            names_lower = list({(r.get("full_name") or "").strip().lower() for r in rows if (r.get("full_name") or "").strip()})
            name_count = {}
            if names_lower:
                cur.execute("""
                    SELECT LOWER(TRIM(COALESCE(full_name, first_name || ' ' || COALESCE(last_name, '')))) AS n, COUNT(*) AS c
                    FROM public.sas_id_personal
                    WHERE LOWER(TRIM(COALESCE(full_name, first_name || ' ' || COALESCE(last_name, '')))) = ANY(%s)
                    GROUP BY 1
                """, (names_lower,))
                name_count = {r["n"]: r["c"] for r in cur.fetchall()}
            out = {}
            for r in rows:
                sid = str(r.get("sas_id") or "")
                full_name = (r.get("full_name") or "").strip()
                if not full_name:
                    continue
                has_dup = (name_count.get(full_name.lower()) or 0) > 1
                out[sid] = _sailor_canonical_slug(full_name, sid, has_dup)
            return out
        finally:
            cur.close()
            return_db_connection(conn)
    except Exception as e:
        print(f"[admin_api] _batch_sailor_slugs_for_sas_ids: {e}")
        return {}


def _get_session_role(request: Request) -> Optional[str]:
    try:
        if not table_exists("user_accounts") or not column_exists("user_accounts", "role"):
            return None
        token = request.cookies.get("session") or (request.query_params.get("session") if request.query_params else None)
        if not token:
            return None
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            where_extra = " AND s.logout_time IS NULL" if column_exists("user_sessions", "logout_time") else ""
            cur.execute("""
                SELECT ua.role FROM public.user_sessions s
                JOIN public.user_accounts ua ON ua.account_id = s.account_id
                WHERE s.session_id = %s AND s.expires_at > NOW()
            """ + where_extra, (token,))
            row = cur.fetchone()
            return str(row["role"]).strip() if row and row.get("role") else None
        finally:
            cur.close()
            return_db_connection(conn)
    except Exception:
        return None

# --- Admin dashboard Jinja (scrape health): aligned with main api.py ---
def _admin_scrape_status_list(cur) -> list:
    """Build list of scrape status dicts for /admin/api/scrape-status. Prefers scrape_runs when present; else events, sas_scrape_batches."""
    out = []
    has_scrape_runs = table_exists("scrape_runs")

    def _last_run_from_scrape_runs(scrape_name: str):
        """Return latest row from scrape_runs for scrape_name, or None."""
        if not has_scrape_runs:
            return None
        cur.execute(
            "SELECT started_at, completed_at, records_added, errors, status, batch_id FROM scrape_runs WHERE scrape_name = %s ORDER BY started_at DESC LIMIT 1",
            (scrape_name,),
        )
        return cur.fetchone()

    # ---- Events scraper (prefer scrape_runs; else events table) ----
    # new_records = count of rows in latest scrape batch where is_new = 1 (not in previous run)
    def _events_new_records_count(c):
        c.execute("""
            WITH run_ids AS (
              SELECT (SELECT MAX(scrape_run_id) FROM events) AS latest_run,
                     (SELECT scrape_run_id FROM events WHERE scrape_run_id IS NOT NULL ORDER BY scrape_run_id DESC LIMIT 1 OFFSET 1) AS previous_run
            )
            SELECT COUNT(*) AS cnt FROM events e
            WHERE e.scrape_run_id = (SELECT latest_run FROM run_ids)
              AND (SELECT previous_run FROM run_ids) IS NOT NULL
              AND (e.source, e.source_event_id) NOT IN (
                SELECT source, source_event_id FROM events WHERE scrape_run_id = (SELECT previous_run FROM run_ids)
              )
        """)
        return (c.fetchone() or {}).get("cnt")

    if table_exists("events"):
        sr = _last_run_from_scrape_runs("events")
        if sr:
            sr = dict(sr)
            completed = sr.get("completed_at")
            last_run = completed or sr.get("started_at")
            last_successful_run = completed.isoformat() if completed and hasattr(completed, "isoformat") else (str(completed) if completed else None)
            if not last_successful_run and last_run:
                last_successful_run = last_run.isoformat() if hasattr(last_run, "isoformat") else str(last_run)
            out.append({
                "scrape_name": "SAS Events List Scrape",
                "run_key": "events",
                "run_implemented": "events" in _RUN_SCRAPE_MAP,
                "last_run": last_run.isoformat() if last_run and hasattr(last_run, "isoformat") else (str(last_run) if last_run else None),
                "last_successful_run": last_successful_run,
                "status": "Running" if sr.get("status") == "running" and not completed else ("Failed" if (sr.get("errors") or 0) > 0 else "Success"),
                "error_count": sr.get("errors") or 0,
                "new_records": _events_new_records_count(cur),
                "target_table": "events",
                "last_batch_id": sr.get("batch_id"),
                "validation_ok": True,
                "audit_url": "/admin/scrape-audit?name=events",
                "log_url": "/admin/log-view?file=daily-events-scrape.log",
            })
        else:
            cur.execute("""
                SELECT MAX(last_seen_at) AS last_run, MAX(scrape_run_id) AS last_batch_id
                FROM events
            """)
            row = cur.fetchone()
            last_run = (row or {}).get("last_run")
            last_batch_id = (row or {}).get("last_batch_id")
            new_records = _events_new_records_count(cur) if last_batch_id else None
            last_successful_run = last_run.isoformat() if last_run and hasattr(last_run, "isoformat") else (str(last_run) if last_run else None)
            out.append({
                "scrape_name": "SAS Events List Scrape",
                "run_key": "events",
                "run_implemented": "events" in _RUN_SCRAPE_MAP,
                "last_run": last_successful_run,
                "last_successful_run": last_successful_run,
                "status": "Success",
                "error_count": 0,
                "new_records": new_records,
                "target_table": "events",
                "last_batch_id": last_batch_id,
                "validation_ok": True,
                "audit_url": "/admin/scrape-audit?name=events",
                "log_url": "/admin/log-view?file=daily-events-scrape.log",
            })
    else:
        out.append({
            "scrape_name": "SAS Events List Scrape",
            "run_key": "events",
            "run_implemented": "events" in _RUN_SCRAPE_MAP,
            "last_run": None,
            "last_successful_run": None,
            "status": "Never Run",
            "error_count": 0,
            "new_records": None,
            "target_table": "events",
            "last_batch_id": None,
            "validation_ok": True,
            "audit_url": "/admin/scrape-audit?name=events",
            "log_url": "/admin/log-view?file=daily-events-scrape.log",
        })
    # ---- Accreditation (prefer scrape_runs; else sas_scrape_batches ACCREDITATION_SYNC%) ----
    if table_exists("member_roles"):
        sr = _last_run_from_scrape_runs("accreditation")
        if sr:
            sr = dict(sr)
            completed = sr.get("completed_at")
            last_run = completed or sr.get("started_at")
            last_successful_run_iso = completed.isoformat() if completed and hasattr(completed, "isoformat") else (str(completed) if completed else None)
            out.append({
                "scrape_name": "SAS Accreditation Sync",
                "run_key": "accreditation",
                "run_implemented": "accreditation" in _RUN_SCRAPE_MAP,
                "last_run": last_run.isoformat() if last_run and hasattr(last_run, "isoformat") else (str(last_run) if last_run else None),
                "last_successful_run": last_successful_run_iso,
                "status": "Running" if sr.get("status") == "running" and not completed else ("Failed" if (sr.get("errors") or 0) > 0 else "Success"),
                "error_count": sr.get("errors") or 0,
                "new_records": sr.get("records_added"),
                "target_table": "member_roles",
                "last_batch_id": sr.get("batch_id"),
                "validation_ok": True,
                "audit_url": "/admin/scrape-audit?name=accreditation",
                "log_url": "/admin/log-view?file=weekly-accreditation-sync.log",
            })
        else:
            last_run = None
            new_records = None
            last_batch_id = None
            status = "Success"
            error_count_acc = 0
            last_successful_run_acc = None
            if table_exists("sas_scrape_batches"):
                cur.execute("""
                    SELECT batch_id, started_at, completed_at, error_count, valid_count
                    FROM sas_scrape_batches
                    WHERE batch_id LIKE 'ACCREDITATION_SYNC%%'
                    ORDER BY started_at DESC NULLS LAST
                    LIMIT 1
                """)
                row = cur.fetchone()
                if row:
                    row = dict(row)
                    completed_at = row.get("completed_at")
                    error_count_acc = row.get("error_count") or 0
                    if completed_at is None:
                        status = "Running"
                    elif error_count_acc > 0:
                        status = "Failed"
                    else:
                        status = "Success"
                    last_run = completed_at or row.get("started_at")
                    new_records = row.get("valid_count")
                    last_batch_id = row.get("batch_id")
                    if completed_at is not None:
                        last_successful_run_acc = completed_at
            last_successful_run_iso = last_successful_run_acc.isoformat() if last_successful_run_acc and hasattr(last_successful_run_acc, "isoformat") else (str(last_successful_run_acc) if last_successful_run_acc else None)
            out.append({
                "scrape_name": "SAS Accreditation Sync",
                "run_key": "accreditation",
                "run_implemented": "accreditation" in _RUN_SCRAPE_MAP,
                "last_run": last_run.isoformat() if last_run and hasattr(last_run, "isoformat") else (str(last_run) if last_run else None),
                "last_successful_run": last_successful_run_iso,
                "status": status,
                "error_count": error_count_acc,
                "new_records": new_records,
                "target_table": "member_roles",
                "last_batch_id": last_batch_id,
                "validation_ok": True,
                "audit_url": "/admin/scrape-audit?name=accreditation",
                "log_url": "/admin/log-view?file=weekly-accreditation-sync.log",
            })
    # ---- SAS ID Registry (prefer scrape_runs; else sas_scrape_batches non-accreditation) ----
    sr_reg = _last_run_from_scrape_runs("sas_registry")
    if sr_reg:
        sr_reg = dict(sr_reg)
        completed = sr_reg.get("completed_at")
        last_run = completed or sr_reg.get("started_at")
        last_successful_run_reg_iso = completed.isoformat() if completed and hasattr(completed, "isoformat") else (str(completed) if completed else None)
        out.append({
            "scrape_name": "SAS ID Registry Scrape",
            "run_key": "sas_registry",
            "run_implemented": "sas_registry" in _RUN_SCRAPE_MAP,
            "last_run": last_run.isoformat() if last_run and hasattr(last_run, "isoformat") else (str(last_run) if last_run else None),
            "last_successful_run": last_successful_run_reg_iso,
            "status": "Running" if sr_reg.get("status") == "running" and not completed else ("Failed" if (sr_reg.get("errors") or 0) > 0 else "Success"),
            "error_count": sr_reg.get("errors") or 0,
            "new_records": sr_reg.get("records_added"),
            "target_table": "sas_id_personal",
            "last_batch_id": sr_reg.get("batch_id"),
            "validation_ok": True,
            "audit_url": "/admin/scrape-audit?name=registry",
            "log_url": "/admin/log-view?file=sas-id-registry-scrape.log",
        })
    elif table_exists("sas_scrape_batches"):
        cur.execute("""
            SELECT batch_id, started_at, completed_at, error_count, valid_count
            FROM sas_scrape_batches
            WHERE batch_id NOT LIKE 'ACCREDITATION_SYNC%%'
            ORDER BY started_at DESC NULLS LAST
            LIMIT 1
        """)
        row = cur.fetchone()
        last_run = None
        status = "Success"
        new_records = None
        last_batch_id = None
        error_count_reg = 0
        if row:
            row = dict(row)
            completed_at = row.get("completed_at")
            error_count_reg = row.get("error_count") or 0
            if completed_at is None:
                status = "Running"
            elif error_count_reg > 0:
                status = "Failed"
            else:
                status = "Success"
            last_run = completed_at or row.get("started_at")
            new_records = row.get("valid_count")
            last_batch_id = row.get("batch_id")
        last_successful_run_reg = None
        cur.execute("""
            SELECT MAX(completed_at) AS last_successful
            FROM sas_scrape_batches
            WHERE batch_id NOT LIKE 'ACCREDITATION_SYNC%%' AND completed_at IS NOT NULL
        """)
        r = cur.fetchone()
        if r and r.get("last_successful"):
            last_successful_run_reg = r["last_successful"]
        last_successful_run_reg_iso = last_successful_run_reg.isoformat() if last_successful_run_reg and hasattr(last_successful_run_reg, "isoformat") else (str(last_successful_run_reg) if last_successful_run_reg else None)
        out.append({
            "scrape_name": "SAS ID Registry Scrape",
            "run_key": "sas_registry",
            "run_implemented": "sas_registry" in _RUN_SCRAPE_MAP,
            "last_run": last_run.isoformat() if last_run and hasattr(last_run, "isoformat") else (str(last_run) if last_run else None),
            "last_successful_run": last_successful_run_reg_iso,
            "status": status,
            "error_count": error_count_reg,
            "new_records": new_records,
            "target_table": "sas_id_personal",
            "last_batch_id": last_batch_id,
            "validation_ok": True,
            "audit_url": "/admin/scrape-audit?name=registry",
            "log_url": "/admin/log-view?file=sas-id-registry-scrape.log",
        })
    else:
        out.append({
            "scrape_name": "SAS ID Registry Scrape",
            "run_key": "sas_registry",
            "run_implemented": "sas_registry" in _RUN_SCRAPE_MAP,
            "last_run": None,
            "last_successful_run": None,
            "status": "Never Run",
            "error_count": 0,
            "new_records": None,
            "target_table": "sas_id_personal",
            "last_batch_id": None,
            "validation_ok": True,
            "audit_url": "/admin/scrape-audit?name=registry",
            "log_url": "/admin/log-view?file=sas-id-registry-scrape.log",
        })
    # ---- Historical Results (future; table race_results) ----
    out.append({
        "scrape_name": "Historical Results Scrape",
        "run_key": "historical_results",
        "run_implemented": "historical_results" in _RUN_SCRAPE_MAP,
        "last_run": None,
        "last_successful_run": None,
        "status": "Never Run",
        "error_count": 0,
        "new_records": None,
        "target_table": "race_results",
        "last_batch_id": None,
        "validation_ok": True,
        "audit_url": None,
        "log_url": None,
    })
    # Status is from scrape_runs only (running -> Running, success -> Success, failed -> Failed). No lock-file override.
    # Unified status rule: Never Run when no last_successful_run; else Running / Failed / Success from DB
    for s in out:
        if s.get("status") == "Running":
            continue
        if not s.get("last_successful_run"):
            s["status"] = "Never Run"
        elif (s.get("error_count") or 0) > 0:
            s["status"] = "Failed"
        else:
            s["status"] = "Success"
    # Add next_scheduled_run and countdown_seconds (UTC server time)
    now_utc = datetime.now(timezone.utc)
    for s in out:
        run_key = s.get("run_key")
        next_iso, countdown = _next_scheduled_run(run_key, now_utc)
        s["next_scheduled_run"] = next_iso
        if s.get("status") == "Running":
            s["countdown_seconds"] = None
        else:
            s["countdown_seconds"] = countdown
    # Dashboard v10: total_records from latest scrape_runs.records_added; explicit timestamps
    latest_scrape_ra: dict = {}
    if has_scrape_runs:
        try:
            cur.execute(
                """
                SELECT DISTINCT ON (scrape_name) scrape_name, records_added
                FROM scrape_runs
                ORDER BY scrape_name, COALESCE(completed_at, started_at) DESC NULLS LAST
                """
            )
            for row in cur.fetchall() or []:
                drow = row if isinstance(row, dict) else dict(row)
                sn = str(drow.get("scrape_name") or "").strip()
                if sn:
                    latest_scrape_ra[sn] = drow.get("records_added")
        except Exception:
            pass
    _rk_scrape_db = {"events": "events", "accreditation": "accreditation", "sas_registry": "sas_registry"}
    for s in out:
        rk = s.get("run_key")
        dbn = _rk_scrape_db.get(rk) if rk else None
        if dbn and dbn in latest_scrape_ra:
            val = latest_scrape_ra[dbn]
            if val is not None:
                try:
                    s["total_records"] = int(val)
                except (TypeError, ValueError):
                    s["total_records"] = None
            else:
                s["total_records"] = None
        else:
            if "total_records" not in s:
                s["total_records"] = None
        s["last_run_at"] = s.get("last_successful_run") or s.get("last_run")
        s["next_run_at"] = s.get("next_scheduled_run")
    # Sort by last_run DESC (most recent first); nulls last
    out.sort(key=lambda s: (s.get("last_run") is None, s.get("last_run") or ""), reverse=True)
    return out
_RUN_SCRAPE_MAP = {
    "events": ("run-daily-events-scrape.sh", ["--on-server"], "daily-events-scrape.log", ".lock_events"),
    "accreditation": ("run-weekly-accreditation-sync.sh", ["--on-server"], "weekly-accreditation-sync.log", ".lock_accreditation"),
    "sas_registry": ("run-sas-id-registry-scrape.sh", ["--on-server"], "sas-id-registry-scrape.log", ".lock_registry"),
}
# Scrape schedules (UTC): run_key -> (hour, minute, "daily"|"weekly", weekday or None). weekday: Monday=0, Sunday=6.
_SCRAPE_SCHEDULES = {
    "events": (4, 0, "daily", None),
    "accreditation": (1, 0, "weekly", 6),   # Sunday 01:00
    "sas_registry": (2, 0, "daily", None),
    "associations": (2, 0, "weekly", 5),    # Saturday 02:00
    "clubs": (3, 0, "weekly", 5),           # Saturday 03:00 (future)
}

# Fixed order for dashboard: always show these three first, then Historical.
_CONFIGURED_SCRAPE_ORDER = ("sas_registry", "events", "accreditation")
_WEEKDAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def _schedule_label(run_key: str) -> str:
    """Human-readable schedule e.g. 'Daily 02:00 UTC' or 'Weekly Sun 01:00 UTC'."""
    if run_key not in _SCRAPE_SCHEDULES:
        return "—"
    hour, minute, mode, weekday = _SCRAPE_SCHEDULES[run_key]
    time_str = f"{hour:02d}:{minute:02d} UTC"
    if mode == "daily":
        return f"Daily {time_str}"
    if weekday is not None and 0 <= weekday <= 6:
        return f"Weekly {_WEEKDAY_NAMES[weekday]} {time_str}"
    return time_str


def _next_scheduled_run(run_key: str, now_utc: datetime):
    """Return (next_run_iso, countdown_seconds) for run_key. countdown_seconds None if no schedule."""
    if run_key not in _SCRAPE_SCHEDULES:
        return None, None
    hour, minute, mode, weekday = _SCRAPE_SCHEDULES[run_key]
    today = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
    if mode == "daily":
        target_today = today.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if now_utc < target_today:
            next_run = target_today
        else:
            next_run = target_today + timedelta(days=1)
    else:
        # weekly: weekday 0=Monday, 6=Sunday
        days_ahead = (weekday - now_utc.weekday()) % 7
        next_date = today + timedelta(days=days_ahead)
        next_run = next_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if now_utc >= next_run:
            next_run = next_run + timedelta(days=7)
    countdown = int((next_run - now_utc).total_seconds())
    return next_run.isoformat(), countdown

def _admin_readonly_pass_fail(cur) -> tuple[bool, str]:
    """SHOW transaction_read_only — PASS when session is read-only (same intent as main api)."""
    try:
        cur.execute("SHOW transaction_read_only")
        r = cur.fetchone()
        v = ""
        if r:
            d = dict(r) if hasattr(r, "keys") else {"v": r[0]}
            v = str(next(iter(d.values()))).strip().lower()
        ok = v in ("on", "true", "1", "yes")
        if ok:
            return True, "Session is read-only ({0}).".format(v or "on")
        return False, "Session is not read-only (got {0!r}); expected read-only for scrape safety.".format(v)
    except Exception as e:
        return False, str(e)


def _admin_scraper_cards(cur) -> list:
    """Map _admin_scrape_status_list() rows to Jinja admin_dashboard.html card dicts."""
    rows = _admin_scrape_status_list(cur)
    cards = []
    for s in rows:
        name = s.get("scrape_name") or "Scrape"
        cards.append({
            "name": name,
            "last_run": s.get("last_run") or s.get("last_successful_run") or "—",
            "status": s.get("status") or "—",
            "records_added": s.get("new_records") if s.get("new_records") is not None else "—",
            "batch_id": str(s.get("last_batch_id") or "—"),
        })
    return cards


def _parse_last_run_datetime(value) -> datetime | None:
    """Parse scrape last-run from DB (datetime or ISO string)."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    s = str(value).strip()
    if not s or s == "—":
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        pass
    try:
        if len(s) >= 19 and s[10] in " T":
            return datetime.fromisoformat(s[:19].replace(" ", "T"))
    except ValueError:
        pass
    try:
        if len(s) >= 10 and s[4] == "-" and s[7] == "-":
            return datetime.fromisoformat(s[:10] + "T00:00:00")
    except ValueError:
        pass
    return None


def format_last_run_pill_label(value) -> str:
    """Pill text: Last run: 2026-04-11 2h30m29s (clock time as h/m/s, no duplicate ISO noise)."""
    dt = _parse_last_run_datetime(value)
    if dt is None:
        return "Last run: —"
    dpart = dt.strftime("%Y-%m-%d")
    tpart = f"{dt.hour}h{dt.minute}m{dt.second}s"
    return f"Last run: {dpart} {tpart}"


def _format_iso_line(value) -> str:
    if value is None or value == "":
        return "—"
    return str(value).strip()


def _pill_next_scheduled_utc(iso_s) -> str:
    if not iso_s:
        return "Next (UTC): —"
    s = str(iso_s).strip()
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s.replace(" ", "T")[:32])
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return "Next (UTC): " + dt.strftime("%a %d %b %H:%M UTC")
    except Exception:
        return "Next (UTC): " + (s[:28] + "…" if len(s) > 28 else s)


def _human_countdown(seconds) -> str:
    if seconds is None:
        return "—"
    try:
        sec = int(seconds)
    except (TypeError, ValueError):
        return "—"
    if sec < 60:
        return f"{sec}s"
    h, r = divmod(sec, 3600)
    m, s2 = divmod(r, 60)
    if h:
        return f"{h}h {m}m"
    return f"{m}m"


def admin_sas_id_personal_last_records(cur, limit: int = 5) -> list[dict]:
    """Latest rows by numeric SAS ID (newest IDs first). Each dict: first_name, last_name, sas_id, year_born."""
    if limit < 1 or limit > 50:
        limit = 5
    if not table_exists("sas_id_personal") or not column_exists("sas_id_personal", "sa_sailing_id"):
        return []
    has_fn = column_exists("sas_id_personal", "first_name")
    has_ln = column_exists("sas_id_personal", "last_name")
    has_yob = column_exists("sas_id_personal", "year_of_birth")
    fn_expr = "COALESCE(TRIM(first_name), '')" if has_fn else "''::text"
    ln_expr = "COALESCE(TRIM(last_name), '')" if has_ln else "''::text"
    yob_sel = "year_of_birth AS year_born" if has_yob else "NULL::integer AS year_born"
    try:
        cur.execute(
            f"""
            SELECT TRIM(sa_sailing_id::text) AS sas_id,
                   {fn_expr} AS first_name,
                   {ln_expr} AS last_name,
                   {yob_sel}
            FROM public.sas_id_personal
            WHERE TRIM(COALESCE(sa_sailing_id::text, '')) ~ '^[0-9]+$'
            ORDER BY TRIM(sa_sailing_id::text)::bigint DESC NULLS LAST
            LIMIT %s
            """,
            (limit,),
        )
        out: list[dict] = []
        for r in cur.fetchall() or []:
            d = dict(r) if hasattr(r, "keys") else {}
            yr = d.get("year_born")
            if yr is not None:
                try:
                    yr = int(yr)
                except (TypeError, ValueError):
                    yr = None
            out.append(
                {
                    "first_name": d.get("first_name") or "",
                    "last_name": d.get("last_name") or "",
                    "sas_id": d.get("sas_id") or "",
                    "year_born": yr,
                }
            )
        return out
    except Exception:
        return []


def admin_sas_registry_card_context(cur) -> dict:
    """Template context for /admin/dashboard SAS registry card."""
    rows = _admin_scrape_status_list(cur)
    reg: dict = {}
    for s in rows:
        if s.get("run_key") == "sas_registry":
            reg = dict(s)
            break
    if not reg:
        reg = {
            "scrape_name": "SAS ID Registry Scrape",
            "run_key": "sas_registry",
            "target_table": "sas_id_personal",
            "status": "Never Run",
            "last_run": None,
            "last_successful_run": None,
            "last_run_at": None,
            "new_records": None,
            "last_batch_id": None,
            "error_count": 0,
            "run_implemented": "sas_registry" in _RUN_SCRAPE_MAP,
            "audit_url": "/admin/scrape-audit?name=registry",
            "log_url": "/admin/log-view?file=sas-id-registry-scrape.log",
        }

    def dash(v) -> str:
        if v is None or v == "":
            return "—"
        return str(v)

    row_count_val = None
    if table_exists("sas_id_personal"):
        try:
            cur.execute("SELECT COUNT(*) AS c FROM public.sas_id_personal")
            rr = cur.fetchone()
            if rr:
                d = dict(rr) if hasattr(rr, "keys") else {"c": rr[0]}
                row_count_val = d.get("c")
        except Exception:
            pass

    nr = reg.get("new_records")
    if nr is None:
        nr_display = "—"
    else:
        try:
            nr_display = str(int(nr))
        except (TypeError, ValueError):
            nr_display = str(nr)

    st = (reg.get("status") or "—").strip()
    if st == "Success":
        status_class = "admin-pill--status-ok"
    elif st == "Failed":
        status_class = "admin-pill--status-fail"
    elif st == "Running":
        status_class = "admin-pill--status-run"
    else:
        status_class = "admin-pill--status-muted"

    last_iso = reg.get("last_run_at") or reg.get("last_successful_run") or reg.get("last_run")

    bid = reg.get("last_batch_id")
    batch_disp = dash(bid)
    batch_short = batch_disp
    if batch_disp != "—" and len(batch_disp) > 28:
        batch_short = batch_disp[:26] + "…"

    rows_display = "—"
    if isinstance(row_count_val, int):
        rows_display = f"{row_count_val:,}"

    tbl = reg.get("target_table") or "sas_id_personal"
    table_pill = f"Table: {tbl}"
    rows_pill = f"Rows: {rows_display}"
    last_run_pill = format_last_run_pill_label(last_iso)

    audit_url = reg.get("audit_url") or "/admin/scrape-audit?name=registry"
    log_url = reg.get("log_url") or "/admin/log-view?file=sas-id-registry-scrape.log"
    ec = int(reg.get("error_count") or 0)
    pill_errors = f"Errors: {ec}"
    pill_next = _pill_next_scheduled_utc(reg.get("next_scheduled_run"))
    cd = reg.get("countdown_seconds")
    pill_countdown = "Next in: " + _human_countdown(cd) if cd is not None else "Next in: —"
    tr = reg.get("total_records")
    pill_total_added = (
        f"scrape_runs records_added: {tr:,}" if isinstance(tr, int) else "scrape_runs records_added: —"
    )
    pill_last_batch_records = f"Records added (last batch): {nr_display}"
    run_ok = bool(reg.get("run_implemented"))
    pill_trigger = "Server trigger: on" if run_ok else "Server trigger: off"
    return {
        "scrape_name": reg.get("scrape_name") or "SAS ID Registry Scrape",
        "table_pill": table_pill,
        "rows_pill": rows_pill,
        "last_run_pill": last_run_pill,
        "status": st,
        "status_pill_class": status_class,
        "batch_id_display": batch_disp,
        "batch_id_pill": batch_short,
        "audit_url": audit_url,
        "log_url": log_url,
        "panel_log_file": "sas-id-registry-scrape.log",
        "run_scrape_key": "sas_registry",
        "pill_errors": pill_errors,
        "pill_next_scheduled": pill_next,
        "pill_countdown": pill_countdown,
        "pill_total_added": pill_total_added,
        "pill_trigger": pill_trigger,
        "pill_last_batch_records": pill_last_batch_records,
    }


# Log filenames allowed for GET /admin/api/panel/log-text (server paths).
_PANEL_LOG_ALLOWLIST = {
    "sas-id-registry-scrape.log": "/var/www/sailingsa/deploy/logs/sas-id-registry-scrape.log",
    "daily-events-scrape.log": "/var/www/sailingsa/deploy/logs/daily-events-scrape.log",
    "weekly-accreditation-sync.log": "/var/www/sailingsa/deploy/logs/weekly-accreditation-sync.log",
}

_AUDIT_NAME_TO_RUN_KEY = {
    "registry": "sas_registry",
    "events": "events",
    "accreditation": "accreditation",
}


def admin_read_log_tail(filename: str, max_bytes: int = 131072) -> tuple[bool, str]:
    """Read tail of an allowlisted deploy log. Returns (ok, text_or_error)."""
    fn = (filename or "").strip()
    if fn not in _PANEL_LOG_ALLOWLIST:
        return False, "Unknown or disallowed log file."
    path = _PANEL_LOG_ALLOWLIST[fn]
    if not os.path.isfile(path):
        return True, f"(No file yet: {path})"
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            if size <= max_bytes:
                f.seek(0)
                raw = f.read()
            else:
                f.seek(size - max_bytes)
                raw = f.read()
        text = raw.decode("utf-8", errors="replace")
        if size > max_bytes:
            text = f"(Showing last {max_bytes:,} bytes)\n\n" + text
        return True, text
    except Exception as e:
        return False, str(e)


def admin_audit_fallback_text(cur, audit_name: str) -> str:
    """Plain-text summary when main API has no scrape-audit HTML."""
    key = _AUDIT_NAME_TO_RUN_KEY.get((audit_name or "").strip().lower())
    if not key:
        return f"Unknown audit name: {audit_name!r}"
    rows = _admin_scrape_status_list(cur)
    for row in rows:
        if row.get("run_key") != key:
            continue
        lines = [
            row.get("scrape_name") or "—",
            f"Status: {row.get('status') or '—'}",
            f"Target table: {row.get('target_table') or '—'}",
            f"Last run: {row.get('last_run_at') or row.get('last_successful_run') or row.get('last_run') or '—'}",
            f"Batch ID: {row.get('last_batch_id') or '—'}",
            f"New records (last batch): {row.get('new_records') if row.get('new_records') is not None else '—'}",
        ]
        return "\n".join(lines)
    return f"No scrape row found for {audit_name!r}."


def admin_trigger_scrape(run_key: str) -> dict:
    """Start a deploy/ scrape script on the live host only. Returns {ok, error?}."""
    import subprocess
    from pathlib import Path

    rk = (run_key or "").strip()
    if socket.gethostname() != ADMIN_LIVE_HOSTNAME:
        return {"ok": False, "error": "Scrape trigger only on configured live host."}
    if rk not in _RUN_SCRAPE_MAP:
        return {"ok": False, "error": "Unknown scrape key"}
    script, extra_args, _log, _lock = _RUN_SCRAPE_MAP[rk]
    deploy = Path("/var/www/sailingsa/deploy")
    sh = deploy / script
    if not sh.is_file():
        return {"ok": False, "error": f"Missing script: {sh}"}
    try:
        subprocess.Popen(
            ["/bin/bash", str(sh)] + list(extra_args),
            cwd=str(deploy),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True}
