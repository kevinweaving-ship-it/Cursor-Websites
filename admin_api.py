"""
SailingSA admin API — run on 127.0.0.1:8002 (nginx proxies /admin/ here).

    /var/www/sailingsa/api/venv/bin/uvicorn admin_api:app --host 127.0.0.1 --port 8002

Endpoints (all under this app; main site auth is proxied where noted):
- HTML: GET /admin/dashboard, /admin/dashboard-v2, /admin/dashboard-v3
- JSON: GET /admin/dashboard-data (auth)
- Main-API proxy (Cookie forward): GET /admin/api/session → main /auth/session,
  POST /admin/api/logout → main /auth/logout
- Ops: GET /admin/api/version, GET /admin/api/scrape-status, POST /admin/api/run-scrape,
  POST /admin/api/restart, GET /admin/review/issues
- Lists & session: /admin/list/*, /admin/user-session-history/{sas_id}, /admin/api/active-sailors
"""
from __future__ import annotations

import os
import socket
import subprocess
import time
from pathlib import Path

import httpx
import psycopg2.extras
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from starlette.responses import Response
from starlette.templating import Jinja2Templates

from admin_support import (
    ADMIN_LIVE_HOSTNAME,
    DASHBOARD_DATA_HEADERS,
    MAIN_API_URL,
    _admin_active_sailors,
    _admin_list_classes,
    _admin_list_clubs,
    _admin_list_races,
    _admin_list_regattas,
    _admin_list_registered_users,
    _admin_list_sailors,
    _admin_offline_sessions,
    _admin_online_users_full,
    _admin_user_session_history,
    _batch_sailor_slugs_for_sas_ids,
    _get_session_role,
    _get_site_stats,
    _get_table_columns_schema,
    _admin_dashboard_data_base,
    _admin_readonly_pass_fail,
    _admin_scraper_cards,
    _admin_scrape_status_list,
    admin_sas_registry_card_context,
    admin_audit_fallback_text,
    admin_read_log_tail,
    admin_sas_id_personal_last_records,
    admin_trigger_scrape,
    _ordinal,
    column_exists,
    get_db_connection,
    return_db_connection,
    table_exists,
)

_ROOT = Path(__file__).resolve().parent


def _resolve_admin_templates_dir() -> Path:
    """
    Repo: admin_api.py at project root → sailingsa/frontend/templates.
    Live: admin_api.py often under /var/www/sailingsa/api/ while deploy zip
    unpacks templates to /var/www/sailingsa/templates/ (not under api/).
    """
    repo_layout = _ROOT / "sailingsa" / "frontend" / "templates"
    if repo_layout.is_dir():
        return repo_layout
    webroot_templates = _ROOT.parent / "templates"
    if webroot_templates.is_dir():
        return webroot_templates
    env = (os.getenv("SAILINGSA_TEMPLATES_DIR") or "").strip()
    if env:
        ep = Path(env)
        if ep.is_dir():
            return ep
    return repo_layout


templates = Jinja2Templates(directory=str(_resolve_admin_templates_dir()))

_ADMIN_APP_START = int(time.time())

app = FastAPI(title="SailingSA Admin API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _require_admin_role(request: Request) -> str:
    role = _get_session_role(request)
    if not role or role not in ("super_admin", "admin"):
        raise HTTPException(status_code=403, detail="Admin access required.")
    return role


def _admin_dashboard_page_impl(request: Request):
    role = _get_session_role(request)
    if not role or role not in ("super_admin", "admin"):
        raise HTTPException(status_code=403, detail="Admin access required.")

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        health_pass, health_message = _admin_readonly_pass_fail(cur)
        scraper_cards = _admin_scraper_cards(cur)
        sas_registry_card = admin_sas_registry_card_context(cur)

        resp = templates.TemplateResponse(
            "pages/admin_dashboard.html",
            {
                "request": request,
                "health_pass": health_pass,
                "health_message": health_message,
                "scraper_cards": scraper_cards,
                "sas_registry_card": sas_registry_card,
            },
        )
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        return resp
    finally:
        if cur:
            try:
                cur.close()
            except Exception:
                pass
        if conn:
            return_db_connection(conn)


@app.get("/admin/dashboard", response_class=HTMLResponse)
@app.get("/admin/dashboard-v2", response_class=HTMLResponse)
@app.get("/admin/dashboard-v3", response_class=HTMLResponse)
def admin_dashboard_page(request: Request):
    """Same template for /admin/dashboard and legacy bookmark URLs v2 / v3."""
    return _admin_dashboard_page_impl(request)


@app.get("/admin/api/session")
def admin_api_session_proxy(request: Request):
    """Expose session through admin API (proxies main sailingsa-api /auth/session with the same Cookie)."""
    q = request.url.query
    url = f"{MAIN_API_URL}/auth/session" + (f"?{q}" if q else "")
    try:
        r = httpx.get(
            url,
            headers={"Cookie": request.headers.get("cookie") or ""},
            timeout=15.0,
        )
        ct = (r.headers.get("content-type") or "application/json").split(";")[0].strip()
        return Response(content=r.content, status_code=r.status_code, media_type=ct)
    except httpx.RequestError as e:
        return JSONResponse({"valid": False, "error": str(e)}, status_code=502)


@app.post("/admin/api/logout")
async def admin_api_logout_proxy(request: Request):
    """Logout through admin API (proxies main /auth/logout)."""
    body = await request.body()
    try:
        r = httpx.post(
            f"{MAIN_API_URL}/auth/logout",
            headers={
                "Cookie": request.headers.get("cookie") or "",
                "Content-Type": request.headers.get("content-type") or "application/json",
            },
            content=body,
            timeout=15.0,
        )
        ct = (r.headers.get("content-type") or "application/json").split(";")[0].strip()
        return Response(content=r.content, status_code=r.status_code, media_type=ct)
    except httpx.RequestError as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=502)


@app.get("/admin/api/health")
def admin_api_health():
    """Liveness + optional reachability of main API (no auth)."""
    ok_main = False
    try:
        r = httpx.get(f"{MAIN_API_URL}/api/process-meta", timeout=2.0)
        ok_main = r.status_code == 200
    except Exception:
        pass
    return {"ok": True, "service": "admin_api", "main_api_reachable": ok_main}


@app.get("/admin/api/panel/log-text")
def admin_api_panel_log_text(request: Request, file: str):
    """Tail of an allowlisted deploy log (for in-card panel; no redirect)."""
    _require_admin_role(request)
    ok, text = admin_read_log_tail(file)
    if not ok:
        raise HTTPException(status_code=400, detail=text)
    return {"ok": True, "text": text}


@app.get("/admin/api/panel/audit")
def admin_api_panel_audit(request: Request, name: str):
    """Scrape audit HTML/text from main API if present, else DB summary text (in-card panel)."""
    _require_admin_role(request)
    cookie = request.headers.get("cookie") or ""
    try:
        r = httpx.get(
            f"{MAIN_API_URL}/admin/scrape-audit",
            params={"name": name},
            headers={"Cookie": cookie},
            timeout=60.0,
            follow_redirects=True,
        )
        if r.status_code == 200 and (r.text or "").strip():
            ct = (r.headers.get("content-type") or "text/plain").split(";")[0].strip()
            return {
                "ok": True,
                "source": "main_api",
                "content_type": ct,
                "body": r.text,
            }
    except httpx.RequestError:
        pass
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        body = admin_audit_fallback_text(cur, name)
        return {"ok": True, "source": "fallback", "content_type": "text/plain; charset=utf-8", "body": body}
    finally:
        if conn:
            return_db_connection(conn)


@app.get("/admin/api/panel/sas-registry-recent")
def admin_api_panel_sas_registry_recent(request: Request, limit: int = 5):
    _require_admin_role(request)
    lim = 5 if limit < 1 or limit > 50 else limit
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        rows = admin_sas_id_personal_last_records(cur, lim)
        return {"ok": True, "rows": rows}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e), "rows": []}, status_code=500)
    finally:
        if cur:
            try:
                cur.close()
            except Exception:
                pass
        if conn:
            return_db_connection(conn)


@app.get("/admin/dashboard-data")
def admin_dashboard_data(request: Request):
    _require_admin_role(request)
    base = _admin_dashboard_data_base()
    site_stats = _get_site_stats()
    if not table_exists("user_sessions"):
        return JSONResponse(
            content={**base, **site_stats, "online_users": [], "offline_sessions": []},
            headers=DASHBOARD_DATA_HEADERS,
        )
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        online_data = _admin_online_users_full(cur)
        offline_data = _admin_offline_sessions(cur)
        return JSONResponse(
            content={**base, **site_stats, "online_users": online_data, "offline_sessions": offline_data},
            headers=DASHBOARD_DATA_HEADERS,
        )
    except Exception as e:
        return JSONResponse(
            content={
                **base,
                **site_stats,
                "online_users": [],
                "offline_sessions": [],
                "error": str(e),
            },
            headers=DASHBOARD_DATA_HEADERS,
        )
    finally:
        if conn:
            return_db_connection(conn)


class RunScrapeBody(BaseModel):
    scrape: str


@app.get("/admin/api/version")
def admin_api_version(request: Request):
    _require_admin_role(request)
    marker = os.environ.get("DEPLOY_MARKER", "")
    return {
        "ok": True,
        "deploy_marker": marker,
        "api_start_time": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(_ADMIN_APP_START)),
        "pid": os.getpid(),
    }


@app.get("/admin/api/scrape-status")
def admin_api_scrape_status(request: Request):
    _require_admin_role(request)
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        rows = _admin_scrape_status_list(cur)
        return {"ok": True, "scrapes": rows}
    except Exception as e:
        return {"ok": False, "error": str(e), "scrapes": []}
    finally:
        if conn:
            return_db_connection(conn)


@app.post("/admin/api/run-scrape")
def admin_api_run_scrape(request: Request, body: RunScrapeBody):
    if socket.gethostname() != ADMIN_LIVE_HOSTNAME:
        raise HTTPException(status_code=403, detail="Admin dashboard disabled on local environment.")
    _require_admin_role(request)
    key = (body.scrape or "").strip()
    out = admin_trigger_scrape(key)
    if not out.get("ok"):
        raise HTTPException(status_code=400, detail=out.get("error", "Run failed"))
    return {"ok": True}


@app.get("/admin/review/issues")
def admin_review_issues(request: Request):
    _require_admin_role(request)
    return {"sailors": [], "classes": [], "unknown_clubs_distinct": 0}


@app.get("/admin/api/active-sailors")
def admin_api_active_sailors(request: Request):
    if socket.gethostname() != ADMIN_LIVE_HOSTNAME:
        raise HTTPException(status_code=403, detail="Admin dashboard disabled on local environment.")
    _require_admin_role(request)
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        rows = _admin_active_sailors(cur)
        sas_ids = [r.get("sas_id") for r in rows if r.get("sas_id")]
        slug_map = _batch_sailor_slugs_for_sas_ids(sas_ids) if sas_ids else {}
        for r in rows:
            r["slug"] = slug_map.get(r.get("sas_id")) or r.get("sas_id") or ""
            rank_val = r.get("last_regatta_rank")
            fleet_val = r.get("fleet_size")
            if rank_val is not None and fleet_val is not None:
                r["last_result_display"] = _ordinal(rank_val) + "/" + str(fleet_val)
            elif rank_val is not None:
                r["last_result_display"] = _ordinal(rank_val)
            else:
                r["last_result_display"] = ""
        return {"ok": True, "sailors": rows}
    except Exception as e:
        return {"ok": False, "error": str(e), "sailors": []}
    finally:
        if conn:
            return_db_connection(conn)


@app.get("/admin/user-session-history/{sas_id}")
def admin_user_session_history(request: Request, sas_id: str):
    _require_admin_role(request)
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        return _admin_user_session_history(cur, sas_id)
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        if conn:
            return_db_connection(conn)


@app.get("/admin/list/sailors")
def admin_list_sailors(request: Request):
    _require_admin_role(request)
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        data = _admin_list_sailors(cur)
        return {"ok": True, "rows": data}
    except Exception as e:
        return {"ok": False, "error": str(e), "rows": []}
    finally:
        if conn:
            return_db_connection(conn)


@app.get("/admin/list/clubs")
def admin_list_clubs(request: Request):
    _require_admin_role(request)
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        data = _admin_list_clubs(cur)
        return {"ok": True, "rows": data}
    except Exception as e:
        return {"ok": False, "error": str(e), "rows": []}
    finally:
        if conn:
            return_db_connection(conn)


@app.get("/admin/list/classes")
def admin_list_classes(request: Request):
    _require_admin_role(request)
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        data = _admin_list_classes(cur)
        return {"ok": True, "rows": data}
    except Exception as e:
        return {"ok": False, "error": str(e), "rows": []}
    finally:
        if conn:
            return_db_connection(conn)


@app.get("/admin/list/regattas")
def admin_list_regattas(request: Request):
    _require_admin_role(request)
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        data = _admin_list_regattas(cur)
        return {"ok": True, "rows": data}
    except Exception as e:
        return {"ok": False, "error": str(e), "rows": []}
    finally:
        if conn:
            return_db_connection(conn)


@app.get("/admin/list/races")
def admin_list_races(request: Request):
    _require_admin_role(request)
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        data = _admin_list_races(cur)
        return {"ok": True, "rows": data}
    except Exception as e:
        return {"ok": False, "error": str(e), "rows": []}
    finally:
        if conn:
            return_db_connection(conn)


@app.get("/admin/list/top-search-sailor")
def admin_list_top_search_sailor(request: Request):
    _require_admin_role(request)
    if not table_exists("analytics_events"):
        return {"ok": False, "error": "analytics_events table not found", "rows": []}
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT LOWER(TRIM(metadata->>'query')) AS query, COUNT(*) AS count
            FROM public.analytics_events
            WHERE event_type = 'search' AND metadata->>'search_type' = 'sailor'
              AND created_at >= NOW() - INTERVAL '30 days'
              AND TRIM(COALESCE(metadata->>'query', '')) != ''
            GROUP BY LOWER(TRIM(metadata->>'query'))
            ORDER BY count DESC
            LIMIT 10
        """)
        rows = [dict(r) for r in (cur.fetchall() or [])]
        return {"ok": True, "rows": rows}
    except Exception as e:
        return {"ok": False, "error": str(e), "rows": []}
    finally:
        if conn:
            return_db_connection(conn)


@app.get("/admin/list/top-search-regatta")
def admin_list_top_search_regatta(request: Request):
    _require_admin_role(request)
    if not table_exists("analytics_events"):
        return {"ok": False, "error": "analytics_events table not found", "rows": []}
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT LOWER(TRIM(metadata->>'query')) AS query, COUNT(*) AS count
            FROM public.analytics_events
            WHERE event_type = 'search' AND metadata->>'search_type' = 'regatta'
              AND created_at >= NOW() - INTERVAL '30 days'
              AND TRIM(COALESCE(metadata->>'query', '')) != ''
            GROUP BY LOWER(TRIM(metadata->>'query'))
            ORDER BY count DESC
            LIMIT 10
        """)
        rows = [dict(r) for r in (cur.fetchall() or [])]
        return {"ok": True, "rows": rows}
    except Exception as e:
        return {"ok": False, "error": str(e), "rows": []}
    finally:
        if conn:
            return_db_connection(conn)


@app.get("/admin/list/registered-users")
def admin_list_registered_users(request: Request):
    _require_admin_role(request)
    if not table_exists("user_accounts"):
        return {"ok": False, "error": "user_accounts table not found", "rows": []}
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        has_whatsapp_col = column_exists("user_accounts", "whatsapp")
        data = _admin_list_registered_users(cur, include_whatsapp=True)
        out: dict = {"ok": True, "rows": data}
        if not has_whatsapp_col:
            out["schema_report"] = "user_accounts columns (no 'whatsapp' column): " + _get_table_columns_schema(
                cur, "user_accounts"
            )
        out["column_labels"] = {"whatsapp_provider_id": "WhatsApp (provider_id)", "active": "Active"}
        return out
    except Exception as e:
        return {"ok": False, "error": str(e), "rows": []}
    finally:
        if conn:
            return_db_connection(conn)


@app.post("/admin/api/restart")
def restart_api(request: Request):
    if socket.gethostname() != ADMIN_LIVE_HOSTNAME:
        raise HTTPException(status_code=403, detail="Admin dashboard disabled on local environment.")
    role = _get_session_role(request)
    if not role or role not in ("super_admin", "admin"):
        raise HTTPException(status_code=403, detail="Admin access required.")
    subprocess.Popen(
        ["/usr/bin/sudo", "systemctl", "restart", "sailingsa-api"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return {"ok": True}
