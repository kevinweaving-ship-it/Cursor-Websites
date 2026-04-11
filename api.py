from fastapi import FastAPI, HTTPException, Body, Query, Request, File, UploadFile
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse, Response, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Union, Optional, List, Dict, Set, Tuple, FrozenSet
import os, shutil, sys, subprocess, socket, psycopg2, psycopg2.extras, psycopg2.pool, re
from pathlib import Path
from unidecode import unidecode
import time
from functools import lru_cache, wraps, cmp_to_key
from datetime import datetime, timedelta, timezone, date
from zoneinfo import ZoneInfo
import uuid
from collections import Counter, defaultdict
import logging
import feedparser
import httpx
import traceback
import hashlib
import html as html_module
import json
import difflib
from urllib.parse import urlparse, unquote, quote
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Sailor bio: build_sailor_bio_from_db(sas_id) from modules/sailor_bio.py — do not reintroduce _get_sailor_bio_data for bio generation.
_api_modules_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sailingsa", "api")
if _api_modules_dir not in sys.path:
    sys.path.insert(0, _api_modules_dir)
try:
    from modules.sailor_bio import build_sailor_bio_from_db
except ImportError:
    build_sailor_bio_from_db = None  # module not deployed (e.g. missing sailingsa/api/modules/)

NAME_SIM_THRESHOLD = 0.75

# Align default with config.postgres.env (sailors_user)
DB_URL = os.getenv("DB_URL", "postgresql://sailors_user:change_me_strong@localhost:5432/sailors_master")

# API process start time for admin dashboard uptime (since last restart)
_api_start_time = time.time()
SERVER_START_TS = int(time.time())

# ============================================================================
# STAGE 11: DIAGNOSTIC INSTRUMENTATION
# ============================================================================

# Configure slow query logging
SLOW_QUERY_THRESHOLD = 0.1  # Log queries slower than 100ms
SLOW_ENDPOINT_THRESHOLD = 0.5  # Log endpoints slower than 500ms
SLOW_QUERY_LOG_FILE = "slow_queries.log"

# Setup logging for slow queries
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(SLOW_QUERY_LOG_FILE),
        logging.StreamHandler()
    ]
)
slow_query_logger = logging.getLogger('slow_queries')

# Request ID tracking for parallel requests
_request_ids = {}
_request_counter = 0

def get_request_id():
    """Generate a unique request ID for tracking parallel requests"""
    global _request_counter
    _request_counter += 1
    return f"REQ-{_request_counter:06d}"

def log_slow_query(request_id: str, query: str, duration: float, params=None):
    """Log slow SQL queries to file and console"""
    if duration >= SLOW_QUERY_THRESHOLD:
        query_preview = query[:200] + "..." if len(query) > 200 else query
        params_str = f" | Params: {params}" if params else ""
        message = f"[{request_id}] SQL ({duration:.3f}s): {query_preview}{params_str}"
        slow_query_logger.warning(message)
        print(f"[DB] ⚠️  SLOW QUERY [{request_id}]: {duration:.3f}s - {query_preview}")

def log_endpoint_timing(request_id: str, endpoint: str, duration: float, status_code: int = 200):
    """Log endpoint timing"""
    if duration >= SLOW_ENDPOINT_THRESHOLD:
        slow_query_logger.warning(f"[{request_id}] ENDPOINT ({duration:.3f}s): {endpoint} [Status: {status_code}]")
        print(f"[TRACE] ⚠️  SLOW ENDPOINT [{request_id}]: {endpoint} took {duration:.3f}s")
    else:
        print(f"[TRACE] [{request_id}]: {endpoint} took {duration:.3f}s")

def trace_endpoint(endpoint_name: str = None):
    """Decorator to trace endpoint execution time"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            request_id = get_request_id()
            endpoint = endpoint_name or f"{func.__module__}.{func.__name__}"
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                log_endpoint_timing(request_id, endpoint, duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                log_endpoint_timing(request_id, f"{endpoint} [ERROR]", duration, status_code=500)
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            request_id = get_request_id()
            endpoint = endpoint_name or f"{func.__module__}.{func.__name__}"
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                log_endpoint_timing(request_id, endpoint, duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                log_endpoint_timing(request_id, f"{endpoint} [ERROR]", duration, status_code=500)
                raise
        
        # Return appropriate wrapper based on whether function is async
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    return decorator

def trace_query(cur, request_id: str = None):
    """Wrap cursor.execute to trace SQL queries"""
    if request_id is None:
        request_id = get_request_id()
    
    original_execute = cur.execute
    
    def traced_execute(query, params=None):
        start_time = time.time()
        try:
            result = original_execute(query, params)
            duration = time.time() - start_time
            log_slow_query(request_id, query, duration, params)
            return result
        except Exception as e:
            duration = time.time() - start_time
            slow_query_logger.error(f"[{request_id}] SQL ERROR ({duration:.3f}s): {str(e)} - {query[:200]}")
            raise
    
    cur.execute = traced_execute
    return cur

# ============================================================================
# CONNECTION POOLING
# ============================================================================

# Global connection pool for better performance
DB_POOL = None

# Per-request DB query count (Step 2) and connection timing (Step 1)
_db_tls = threading.local()

class _CursorWrapper:
    """Wraps cursor to time execute() and fetchall() for pool/query diagnostics."""
    def __init__(self, real_cursor):
        self._cur = real_cursor
    def execute(self, query, *args, **kwargs):
        t0 = time.time()
        out = self._cur.execute(query, *args, **kwargs)
        exec_time = time.time() - t0
        print(f"DB: exec={exec_time:.3f}", flush=True)
        if exec_time > 1.0:
            q = (query.decode("utf-8", errors="replace") if isinstance(query, bytes) else query) or ""
            print(f"DB SQL: {q[:300]}", flush=True)
            print(f"DB exec time: {exec_time:.3f}", flush=True)
        return out
    def fetchall(self):
        t0 = time.time()
        out = self._cur.fetchall()
        print(f"DB: fetch={time.time() - t0:.3f}", flush=True)
        return out
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        self._cur.close()
        return False
    def __getattr__(self, name):
        return getattr(self._cur, name)

class _ConnectionWrapper:
    """Wraps connection so cursor() returns timed cursor; unwrap for putconn."""
    def __init__(self, real_conn):
        self._conn = real_conn
    def cursor(self, *args, **kwargs):
        return _CursorWrapper(self._conn.cursor(*args, **kwargs))
    def __getattr__(self, name):
        return getattr(self._conn, name)

def init_db_pool():
    """Initialize database connection pool"""
    global DB_POOL
    if DB_POOL is None:
        DB_POOL = psycopg2.pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=20,
            dsn=DB_URL,
            cursor_factory=psycopg2.extras.RealDictCursor
        )
        print(f"[DB] Connection pool initialized: {DB_POOL.minconn}-{DB_POOL.maxconn} connections")
    return DB_POOL

def get_db_connection(request_id: str = None):
    """Get a connection from the pool with optional request ID for tracing"""
    pool = init_db_pool()
    t0 = time.time()
    try:
        conn = pool.getconn()
        wait = time.time() - t0
        print(f"DB: getconn_wait={wait:.3f}", flush=True)
        _db_tls.db_query_count = getattr(_db_tls, "db_query_count", 0) + 1
        return _ConnectionWrapper(conn)
    except Exception as e:
        print(f"[DB] Error getting connection from pool: {e}")
        # Fallback to direct connection
        return psycopg2.connect(DB_URL, cursor_factory=psycopg2.extras.RealDictCursor)

def return_db_connection(conn):
    """Return a connection to the pool"""
    real = getattr(conn, "_conn", conn)
    from_pool = hasattr(conn, "_conn")
    if from_pool and DB_POOL:
        try:
            DB_POOL.putconn(real)
            print("DB: putconn=OK", flush=True)
        except Exception as e:
            print(f"[DB] Error returning connection to pool: {e}")
            try:
                real.close()
            except:
                pass
    else:
        try:
            real.close()
        except:
            pass

# ============================================================================
# QUERY PROFILING
# ============================================================================

def profile_query(query_name, table_name=None):
    """Decorator to profile database queries"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            duration = (time.time() - start) * 1000  # Convert to ms
            
            if duration > 200:  # Log queries slower than 200ms
                table_info = f" on {table_name}" if table_name else ""
                print(f"[DB] ⚠️  SLOW QUERY: {query_name}{table_info} took {duration:.2f}ms")
            
            return result
        return wrapper
    return decorator

# ============================================================================
# RESPONSE CACHING
# ============================================================================

_cache = {}
_cache_timestamps = {}
CACHE_TTL = 30  # 30 seconds default

def get_cached(key: str, ttl_seconds: int = CACHE_TTL):
    """Get cached value if not expired"""
    if key in _cache:
        if time.time() - _cache_timestamps[key] < ttl_seconds:
            return _cache[key]
        else:
            # Expired, remove it
            del _cache[key]
            del _cache_timestamps[key]
    return None

def set_cached(key: str, value, ttl_seconds: int = CACHE_TTL):
    """Set cached value with TTL"""
    _cache[key] = value
    _cache_timestamps[key] = time.time()

def _norm(s: str) -> str:
    if not s: return ''
    s = unidecode(s).lower()
    s = re.sub(r'[^a-z ]+', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()

def _ensure_temp_person(cur, full_name: str) -> str:
    norm = _norm(full_name)
    cur.execute("""
        INSERT INTO temp_people (full_name, normalized_name, notes)
        VALUES (%s, %s, 'Auto-created: no SAS match >=75%')
        ON CONFLICT (normalized_name) DO UPDATE SET full_name = EXCLUDED.full_name
        RETURNING temp_id
    """, (full_name, norm))
    return f"TMP:{cur.fetchone()[0]}"

def _resolve_club(cur, club_raw: str):
    if not club_raw: return (None, None)
    cur.execute("""
        WITH q AS (SELECT lower(%s) k)
        SELECT c.club_id, c.club_abbrev
          FROM q
          JOIN clubs c
            ON lower(c.club_abbrev)=q.k OR lower(c.club_fullname)=q.k
        UNION
        SELECT a.club_id, c2.club_abbrev
          FROM q
          JOIN club_aliases a ON lower(a.alias)=q.k
          JOIN clubs c2 ON c2.club_id=a.club_id
        LIMIT 1
    """, (club_raw,))
    row = cur.fetchone()
    return (row[0], row[1]) if row else (None, None)

def _find_sas_id(cur, full_name: str):
    if not full_name: return (None, 0.0)
    n = _norm(full_name)
    
    # Try exact (normalized) match first
    cur.execute("""
        SELECT sa_sailing_id
        FROM sailing_id
        WHERE lower(trim(concat_ws(' ', first_name, last_name))) = %s
        LIMIT 1
    """, (n,))
    r = cur.fetchone()
    if r: return (r[0], 1.0)
    
    # Try common name variations (Rob -> Robert, etc.)
    name_parts = n.split()
    if len(name_parts) >= 2:
        first_name = name_parts[0]
        last_name = ' '.join(name_parts[1:])
        
        # Common abbreviations
        name_variations = [first_name]
        if first_name == 'rob': name_variations.extend(['robert', 'robbie'])
        elif first_name == 'bob': name_variations.extend(['robert', 'bobby'])
        elif first_name == 'bill': name_variations.extend(['william', 'billy'])
        elif first_name == 'dick': name_variations.extend(['richard', 'rick'])
        elif first_name == 'mike': name_variations.extend(['michael', 'mickey'])
        elif first_name == 'jim': name_variations.extend(['james', 'jimmy'])
        elif first_name == 'tom': name_variations.extend(['thomas', 'tommy'])
        elif first_name == 'dan': name_variations.extend(['daniel', 'danny'])
        elif first_name == 'chris': name_variations.extend(['christopher', 'christian'])
        elif first_name == 'steve': name_variations.extend(['steven', 'stephen'])
        
        for variation in name_variations:
            test_name = f"{variation} {last_name}"
            cur.execute("""
                SELECT sa_sailing_id
                FROM sailing_id
                WHERE lower(trim(concat_ws(' ', first_name, last_name))) = %s
                LIMIT 1
            """, (test_name,))
            r = cur.fetchone()
            if r: return (r[0], 0.9)  # High confidence for name variation match
    
    # Fuzzy via pg_trgm as fallback
    cur.execute("""
        SELECT sa_sailing_id,
               similarity(lower(trim(concat_ws(' ', first_name, last_name))), %s) AS sim
        FROM sailing_id
        WHERE lower(trim(concat_ws(' ', first_name, last_name))) % %s
        ORDER BY sim DESC
        LIMIT 1
    """, (n, n))
    r = cur.fetchone()
    return (r[0], float(r[1])) if r else (None, 0.0)

def update_sailor_club_affiliations():
    """Update home_club_code for all sailors based on most common club in results"""
    with psycopg2.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            # Update SAS ID sailors with their most common club
            cur.execute("""
                WITH club_counts AS (
                    SELECT 
                        helm_sa_sailing_id as sa_id,
                        c.club_abbrev,
                        COUNT(*) as appearances
                    FROM results r
                    JOIN clubs c ON c.club_id = r.club_id
                    WHERE r.helm_sa_sailing_id IS NOT NULL
                      AND r.club_id IS NOT NULL
                    GROUP BY helm_sa_sailing_id, c.club_abbrev
                    
                    UNION ALL
                    
                    SELECT 
                        crew_sa_sailing_id as sa_id,
                        c.club_abbrev,
                        COUNT(*) as appearances
                    FROM results r
                    JOIN clubs c ON c.club_id = r.club_id
                    WHERE r.crew_sa_sailing_id IS NOT NULL
                      AND r.club_id IS NOT NULL
                    GROUP BY crew_sa_sailing_id, c.club_abbrev
                ),
                most_common_club AS (
                    SELECT DISTINCT ON (sa_id)
                        sa_id,
                        club_abbrev,
                        SUM(appearances) as total_appearances
                    FROM club_counts
                    GROUP BY sa_id, club_abbrev
                    ORDER BY sa_id, total_appearances DESC, club_abbrev
                )
                UPDATE sailing_id s
                SET home_club_code = m.club_abbrev
                FROM most_common_club m
                WHERE s.sa_sailing_id = m.sa_id
                  AND (s.home_club_code IS NULL OR s.home_club_code != m.club_abbrev)
            """)
            return cur.rowcount

def _ensure_snapshot_integrity(conn, regatta_id, result_ids=None):
    """Enforce: result rows with NULL as_at_time get NOW(). Regattas.as_at_time is NOT auto-set (leave NULL or use real snapshot time)."""
    with conn.cursor() as cur:
        if result_ids:
            cur.execute(
                "UPDATE results SET as_at_time = NOW() WHERE result_id = ANY(%s) AND as_at_time IS NULL",
                (result_ids,),
            )
        else:
            cur.execute(
                "UPDATE results SET as_at_time = NOW() WHERE regatta_id = %s AND as_at_time IS NULL",
                (regatta_id,),
            )
        # Do NOT overwrite regattas.as_at_time with NOW() — use NULL or set explicitly to real snapshot time (e.g. UPDATE regattas SET as_at_time='...' WHERE regatta_id=...).

def bulk_auto_match_regatta(regatta_id: str) -> dict:
    stats = dict(checked=0, helm_sas=0, helm_tmp=0, crew_sas=0, crew_tmp=0, clubs_mapped=0)
    with psycopg2.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT result_id, helm_name, crew_name, club_raw,
                       helm_sa_sailing_id, crew_sa_sailing_id
                FROM results
                WHERE regatta_id = %s
            """, (regatta_id,))
            rows = cur.fetchall()
            for (result_id, helm_name, crew_name, club_raw, helm_sid, crew_sid) in rows:
                stats['checked'] += 1

                # club map (once per row)
                club_id, club_code = _resolve_club(cur, club_raw)
                if club_id:
                    cur.execute("""
                        UPDATE results SET club_id=%s
                        WHERE result_id=%s AND (club_id IS NULL OR club_id<>%s)
                    """, (club_id, result_id, club_id))
                    if cur.rowcount: stats['clubs_mapped'] += 1

                # HELM
                if helm_name and not helm_sid:
                    sid, score = _find_sas_id(cur, helm_name)
                    if sid and score >= NAME_SIM_THRESHOLD:
                        cur.execute("""
                            UPDATE results
                               SET helm_sa_sailing_id=%s, helm_temp_id=NULL, match_status_helm='auto_sas'
                             WHERE result_id=%s
                        """, (sid, result_id))
                        stats['helm_sas'] += 1
                        if club_code:
                            cur.execute("""
                                UPDATE sailing_id
                                   SET home_club_code=%s
                                 WHERE sa_sailing_id=%s
                                   AND (home_club_code IS NULL OR trim(home_club_code)='')
                            """, (club_code, sid))
                    else:
                        tmp = _ensure_temp_person(cur, helm_name)
                        cur.execute("""
                            UPDATE results
                               SET helm_sa_sailing_id=NULL, helm_temp_id=%s, match_status_helm='auto_tmp'
                             WHERE result_id=%s
                        """, (tmp, result_id))
                        stats['helm_tmp'] += 1

                # CREW
                if crew_name and not crew_sid:
                    sid, score = _find_sas_id(cur, crew_name)
                    if sid and score >= NAME_SIM_THRESHOLD:
                        cur.execute("""
                            UPDATE results
                               SET crew_sa_sailing_id=%s, crew_temp_id=NULL, match_status_crew='auto_sas'
                             WHERE result_id=%s
                        """, (sid, result_id))
                        stats['crew_sas'] += 1
                        if club_code:
                            cur.execute("""
                                UPDATE sailing_id
                                   SET home_club_code=%s
                                 WHERE sa_sailing_id=%s
                                   AND (home_club_code IS NULL OR trim(home_club_code)='')
                            """, (club_code, sid))
                    else:
                        tmp = _ensure_temp_person(cur, crew_name)
                        cur.execute("""
                            UPDATE results
                               SET crew_sa_sailing_id=NULL, crew_temp_id=%s, match_status_crew='auto_tmp'
                             WHERE result_id=%s
                        """, (tmp, result_id))
                        stats['crew_tmp'] += 1
            _ensure_snapshot_integrity(conn, regatta_id)
        conn.commit()
    return stats

app = FastAPI(title="Regatta API")

# Canonical base for sitemap and canonical tags: always https://sailingsa.co.za (no www, no http)
CANONICAL_BASE = "https://sailingsa.co.za"


def _canonical_base_url() -> str:
    """Return canonical base URL for sitemap and canonical tags: https://sailingsa.co.za, no www, no trailing slash."""
    b = (os.getenv("BASE_URL") or CANONICAL_BASE).rstrip("/")
    b = b.replace("http://", "https://")
    if "www." in b:
        b = "https://" + b.split("//", 1)[-1].replace("www.", "", 1)
    return b


@app.middleware("http")
async def _canonical_redirect_middleware(request: Request, call_next):
    """Force canonical URL: http→https, www→non-www. Do not redirect /index.html, /index, /login.html, /signup, /admin (SPA/static)."""
    path = (request.url.path or "").strip() or "/"
    query = request.url.query
    qs = ("?" + query) if query else ""

    # Use X-Forwarded-Proto / Host when behind nginx so we still redirect wrong URLs
    netloc = (request.headers.get("host") or request.url.netloc or "").lower().split(":")[0]
    scheme = (request.headers.get("x-forwarded-proto") or request.url.scheme or "http").lower()
    # Legacy / alternate host: always use canonical sailingsa.co.za (SSR + API match production deploy)
    if netloc in ("sailingsa.org.za", "www.sailingsa.org.za") or netloc == "www.sailingsa.co.za" or scheme != "https":
        target = CANONICAL_BASE + path + qs
        return RedirectResponse(url=target, status_code=301)

    return await call_next(request)


def _get_client_ip(request: Request) -> str:
    """Client IP: X-Forwarded-For first (when behind proxy), then request.client.host."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return str(request.client.host) if getattr(request.client, "host", None) else ""
    return ""


def _derive_device_type(user_agent: str) -> str:
    """Derive device_type from User-Agent: mobile or desktop."""
    if not user_agent:
        return "desktop"
    ua = user_agent.lower()
    if any(x in ua for x in ("mobile", "android", "iphone", "ipod", "webos", "blackberry", "windows phone")):
        return "mobile"
    return "desktop"


def _sanitize_session_path(p: Optional[str], max_len: int = 500) -> str:
    """Store client path for last_path; must start with /, no NUL."""
    if not p or not str(p).strip():
        return "/"
    s = str(p).strip()[:max_len].replace("\x00", "")
    if not s.startswith("/"):
        s = "/" + s
    return s or "/"


def _client_path_for_session_touch(request: Request) -> str:
    """Path to record for SPA users: explicit ?path= from client, else Referer path (same host), else request path."""
    raw = (request.query_params.get("path") or request.query_params.get("current_path") or "").strip()
    if raw:
        try:
            raw = unquote(raw)
        except Exception:
            pass
        return _sanitize_session_path(raw)
    ref = (request.headers.get("referer") or request.headers.get("referrer") or "").strip()
    if ref:
        try:
            pu = urlparse(ref)
            host_req = (request.url.hostname or "").lower()
            host_ref = (pu.hostname or "").lower()
            if host_ref and host_req and host_ref.split(":")[0] == host_req.split(":")[0]:
                combined = pu.path or "/"
                if pu.query:
                    combined = combined + "?" + pu.query[:200]
                return _sanitize_session_path(combined)
        except Exception:
            pass
    return _sanitize_session_path(request.url.path or "/")


def _session_touch_user_activity(cur, session_token: str, path: str) -> None:
    """Set last_activity = now and last_path for this session (DB-backed). No-op if no table/token."""
    if not session_token or not table_exists("user_sessions"):
        return
    p = _sanitize_session_path(path)
    try:
        if column_exists("user_sessions", "last_path"):
            cur.execute(
                """
                UPDATE public.user_sessions
                SET last_activity = NOW(), last_path = %s
                WHERE session_id = %s AND expires_at > NOW()
                """,
                (p, session_token),
            )
        else:
            cur.execute(
                """
                UPDATE public.user_sessions
                SET last_activity = NOW()
                WHERE session_id = %s AND expires_at > NOW()
                """,
                (session_token,),
            )
    except Exception:
        pass


@app.middleware("http")
async def _redirect_sas_id_before_routing(request: Request, call_next):
    """Run before route matching. Fix wrong /sailor/regatta/... (old frontend bug) -> /regatta/... then sas_id redirect."""
    path = request.url.path or ""
    if path.startswith("/sailor/regatta/"):
        # Old frontend requested e.g. /sailor/regatta/class/class-results.html -> serve /regatta/class/class-results.html
        fix = "/regatta/" + path[len("/sailor/regatta/"):]
        query = str(request.url.query)
        new_url = fix + ("?" + query if query else "")
        return RedirectResponse(url=new_url, status_code=301)
    # Update session last_activity and last_path for logged-in users (every API request)
    session_token = request.cookies.get("session")
    if session_token and table_exists("user_sessions"):
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            req_path = _client_path_for_session_touch(request)
            _session_touch_user_activity(cur, session_token, req_path)
            conn.commit()
        except Exception:
            pass
        finally:
            if conn:
                return_db_connection(conn)
    if path not in ("/", "/index.html"):
        return await call_next(request)
    sas_id = request.query_params.get("sas_id") or request.query_params.get("sas-id")
    if not (sas_id and str(sas_id).strip().isdigit()):
        return await call_next(request)
    full_name, canonical_slug = _get_sailor_by_sas_id_for_redirect(str(sas_id).strip())
    if canonical_slug:
        return RedirectResponse(url=f"/sailor/{canonical_slug}", status_code=301)
    return RedirectResponse(url="/", status_code=302)


# Redirect/SPA routes (also needed for requests without sas_id)
@app.get("/")
def _root_redirect(request: Request):
    sas_id = request.query_params.get("sas_id") or request.query_params.get("sas-id")
    return root_maybe_redirect_sas_id(request, sas_id=sas_id, sas_id_alt=None)
@app.get("/index.html")
def _index_redirect(request: Request):
    sas_id = request.query_params.get("sas_id") or request.query_params.get("sas-id")
    return index_html_maybe_redirect_sas_id(request, sas_id=sas_id, sas_id_alt=None)


@app.get("/api/stats")
async def api_stats():
    """Public stats for /stats page. Registered before /sailor/{slug} so /stats is not caught as slug."""
    return _get_public_stats()


@app.get("/stats", response_class=HTMLResponse)
async def stats_page():
    """Public statistics dashboard. Calls API data and passes to stats template (not directory template)."""
    data = _get_public_stats()
    return HTMLResponse(_stats_page_html(data))


@app.get("/events", response_class=HTMLResponse)
def events_page(request: Request):
    """Upcoming events only. Sortable table: DATE, EVENT, HOST CLUB, CLASSES, LOCATION."""
    return HTMLResponse(_events_page_html())


@app.head("/events")
def events_page_head():
    """HEAD for crawlers / health checks (GET-only routes return 405 without this)."""
    return Response(status_code=200)


def _yearly_canonical_display_for_key(series_key: str) -> str | None:
    """Stable card title for a normalized series key (overrides noisy regatta names)."""
    if series_key == "dabchick wc regionals":
        return "Dabchick WC Regionals"
    if series_key == "w cape championships dinghy classes":
        return "W. Cape Championships - Dinghy Classes"
    if series_key == "wc regionals":
        return "WC Regionals"
    if series_key == "df95 wc regionals":
        return "DF95 WC Regional Championships"
    return None


def _yearly_initial_display_for_key(series_key: str, fallback_name: str) -> tuple:
    """(display_name, display_name_score) for a new series group."""
    canon = _yearly_canonical_display_for_key(series_key)
    if canon:
        return canon, (-1, 0)
    t = _yearly_event_series_title(fallback_name)
    return t, _yearly_event_title_score(t)


def _yearly_event_series_key(name: str) -> str:
    s = (name or "").strip().lower()
    if not s:
        return ""
    # Merge naming drift for the same Western Cape dinghy championship event family.
    if (
        ("wc" in s or "western cape" in s or "w. cape" in s or "w cape" in s)
        and "dinghy" in s
        and ("champ" in s or "regional championship" in s or "championship" in s)
    ):
        return "w cape championships dinghy classes"
    # Own event: Dabchick WC Regionals (multi-class); not WC Regionals umbrella, not Dabchick WC Champs.
    if (
        "dabchick" in s
        and "regional" in s
        and (
            " wc " in f" {s} "
            or "western cape" in s
            or "w. cape" in s
            or "w cape" in s
        )
    ):
        return "dabchick wc regionals"
    # DF95 / Dragonflite WC regional (single fleet). Not W. Cape multi-class champs, not generic WC Regionals.
    wc_geo = (
        " wc " in f" {s} "
        or "western cape" in s
        or "w. cape" in s
        or "w cape" in s
    )
    if (
        wc_geo
        and "regional" in s
        and (
            re.search(r"\bdf\s*95\b", s)
            or "df95" in s.replace(" ", "")
            or "dragonflite" in s
        )
    ):
        return "df95 wc regionals"
    # Other WC regional events (no Dabchick / not DF95 single-fleet carve-out above).
    if "regional" in s and wc_geo:
        return "wc regionals"
    # Dabchick WC Championship — not Regionals (handled above).
    if "dabchick" in s and (" wc " in f" {s} " or "western cape" in s):
        return "dabchick wc championship"
    # Collapse class-split sheets for same event family.
    if "cape classic" in s:
        if "hermanus" in s:
            return "hermanus cape classic"
        if "hyc" in s:
            return "hyc cape classic"
        if "tsc" in s:
            return "tsc cape classic"
        return "cape classic"
    if "youth nationals" in s:
        return "sa sailing youth nationals"
    if "29er" in s and ("national" in s or "yn" in s):
        return "29er nationals"
    # MACS @ ZVYC club champs — calendar titles often drop "Shipping" / wording differs.
    if "macs" in s and "zvyc" in s and ("champ" in s or "club" in s):
        return "macs zvyc club champs"
    s = re.sub(r"\b(19|20)\d{2}\b", " ", s)
    s = re.sub(r"\b(results|result|#live|live|rsa|sa|championship|championships|regionals|provincials|final)\b", " ", s)
    s = re.sub(r"[-_/()#]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _yearly_series_distinct_year_counts_map() -> dict[str, int]:
    """series_key -> number of distinct calendar years (same grouping as /yearly-events)."""
    year_sets: dict[str, set] = {}

    def _add(name: str, sd, ed, rid) -> None:
        name = (name or "").strip()
        key = _yearly_event_series_key(name)
        if not key:
            return
        d = ed or sd
        year = int(getattr(d, "year", 0) or 0) if d else 0
        rid_raw = str(rid or "").strip().lower()
        if year <= 0 and rid_raw:
            m = re.search(r"-(19|20)\d{2}-", f"-{rid_raw}-")
            if m:
                year = int(m.group(0).strip("-").split("-")[0])
        if year <= 0:
            m2 = re.search(r"\b(19|20)\d{2}\b", name)
            if m2:
                year = int(m2.group(0))
        if year <= 0:
            return
        year_sets.setdefault(key, set()).add(year)

    conn = None
    try:
        if not table_exists("regattas"):
            return {}
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            SELECT r.event_name, r.start_date, COALESCE(r.end_date, r.start_date) AS end_date, r.regatta_id::text AS regatta_id
            FROM regattas r
            WHERE r.event_name IS NOT NULL AND TRIM(r.event_name) <> ''
            """
        )
        for row in cur.fetchall() or []:
            _add(row.get("event_name"), row.get("start_date"), row.get("end_date"), row.get("regatta_id"))
        if table_exists("events"):
            has_events_regatta_id = column_exists("events", "regatta_id")
            reg_sql = "e.regatta_id::text" if has_events_regatta_id else "NULL::text"
            cur.execute(
                f"""
                SELECT e.event_name, e.start_date, COALESCE(e.end_date, e.start_date) AS end_date, {reg_sql} AS regatta_id
                FROM events e
                WHERE e.event_name IS NOT NULL AND TRIM(e.event_name) <> ''
                  AND (
                    (e.end_date IS NOT NULL AND e.end_date >= CURRENT_DATE)
                    OR (e.end_date IS NULL AND e.start_date >= CURRENT_DATE)
                  )
                """
            )
            for row in cur.fetchall() or []:
                _add(row.get("event_name"), row.get("start_date"), row.get("end_date"), row.get("regatta_id"))
        cur.close()
        return {k: len(v) for k, v in year_sets.items()}
    except Exception as e:
        print(f"[yearly_series_distinct_year_counts_map] {e}")
        traceback.print_exc()
        return {}
    finally:
        if conn:
            return_db_connection(conn)


def _yearly_event_series_title(name: str) -> str:
    raw = (name or "").strip()
    if not raw:
        return "Event"
    raw = re.sub(r"\b(19|20)\d{2}\b", " ", raw)
    raw = re.sub(r"\bResults?\b", " ", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s+", " ", raw).strip(" -")
    return raw or "Event"


def _yearly_event_title_score(title: str) -> tuple:
    """Lower is better: prefer event-level names over class-split sheet titles."""
    t = (title or "").strip().lower()
    # Penalize likely class/result sheet labels.
    penalty = 0
    if re.search(r"\b(results?|final|provisional)\b", t):
        penalty += 3
    if re.search(r"\b(optimist|ilca|dabchick|mirror|hobie|sonnet|topper|finn|laser|fleet|multihull)\b", t):
        penalty += 2
    if " - " in (title or ""):
        penalty += 1
    # Prefer concise, cleaner event names once penalties are equal.
    return (penalty, len(t))


def _yearly_series_row_sort_key(r: dict) -> tuple:
    """/yearly-events: same priority as /events cards (max history entries, series depth, first-year last)."""
    cy = int(r.get("count_years") or 0)
    est = 0 if cy >= 2 else 1
    max_ent = 0
    for h in r.get("history") or []:
        max_ent = max(max_ent, int(h.get("entries_count") or 0))
    nud = r.get("next_upcoming_date")
    if nud is None:
        nud_sort = date.max
    else:
        if hasattr(nud, "date") and not isinstance(nud, date):
            try:
                nud_sort = nud.date()
            except Exception:
                nud_sort = date.max
        elif isinstance(nud, date):
            nud_sort = nud
        else:
            nud_sort = date.max
    return (est, -max_ent, -cy, nud_sort, str(r.get("display_name") or "").lower())


def _get_yearly_event_series() -> list[dict]:
    """Recurring event series from regattas table, ordered from current month cycle."""
    out = []
    if not table_exists("regattas") or not table_exists("results"):
        return out
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            SELECT
              r.regatta_id::text AS regatta_id,
              r.event_name,
              r.start_date,
              COALESCE(r.end_date, r.start_date) AS end_date,
              r.as_at_time,
              EXISTS (
                SELECT 1 FROM results rs
                WHERE rs.regatta_id = r.regatta_id
                  AND rs.raced IS TRUE
              ) AS has_results
            FROM regattas r
            WHERE r.event_name IS NOT NULL
              AND TRIM(r.event_name) <> ''
            """
        )
        rows = list(cur.fetchall() or [])
        upcoming_rows = []
        if table_exists("events"):
            has_events_regatta_id = column_exists("events", "regatta_id")
            reg_col = "e.regatta_id::text AS regatta_id," if has_events_regatta_id else "NULL::text AS regatta_id,"
            cur.execute(
                f"""
                SELECT
                  {reg_col}
                  e.event_name,
                  e.start_date,
                  COALESCE(e.end_date, e.start_date) AS end_date
                FROM events e
                WHERE e.event_name IS NOT NULL
                  AND TRIM(e.event_name) <> ''
                  AND (
                    (e.end_date IS NOT NULL AND e.end_date >= CURRENT_DATE)
                    OR (e.end_date IS NULL AND e.start_date >= CURRENT_DATE)
                  )
                """
            )
            upcoming_rows = list(cur.fetchall() or [])
        regatta_ids = [str(x.get("regatta_id") or "").strip() for x in rows if x.get("regatta_id")]
        stats_map = {}
        if regatta_ids:
            if (
                table_exists("classes")
                and column_exists("classes", "class_name")
                and column_exists("results", "class_id")
            ):
                cls_join = "LEFT JOIN classes ycls ON ycls.class_id = rr.class_id"
                cls_expr = "COALESCE(ycls.class_name::text, rr.class_original, rb.class_canonical, rb.class_original, '')"
            else:
                cls_join = ""
                cls_expr = "COALESCE(rr.class_original, rb.class_canonical, rb.class_original, '')"
            cur.execute(
                f"""
                SELECT
                  rr.regatta_id::text AS regatta_id,
                  COUNT(*)::int AS entries_count,
                  ARRAY_REMOVE(ARRAY_AGG(DISTINCT COALESCE(rr.class_id::text, rb.class_id::text)), NULL) AS class_keys,
                  ARRAY_REMOVE(ARRAY_AGG(DISTINCT NULLIF(TRIM({cls_expr}), '')), NULL) AS class_labels_raw,
                  ARRAY_REMOVE(ARRAY_AGG(DISTINCT NULLIF(TRIM(COALESCE(rr.helm_sa_sailing_id::text, rr.helm_name, '')), '')), NULL) AS helm_keys,
                  ARRAY_REMOVE(ARRAY_AGG(DISTINCT NULLIF(TRIM(COALESCE(rr.crew_sa_sailing_id::text, rr.crew_name, '')), '')), NULL) AS crew_keys
                FROM results rr
                LEFT JOIN regatta_blocks rb ON rb.block_id = rr.block_id
                {cls_join}
                WHERE rr.raced IS TRUE
                  AND rr.regatta_id::text = ANY(%s)
                GROUP BY rr.regatta_id
                """,
                (regatta_ids,),
            )
            for s in (cur.fetchall() or []):
                class_keys = set(str(x).strip() for x in (s.get("class_keys") or []) if str(x).strip())
                sailor_keys = set(str(x).strip().lower() for x in (s.get("helm_keys") or []) if str(x).strip())
                sailor_keys.update(str(x).strip().lower() for x in (s.get("crew_keys") or []) if str(x).strip())
                raw_labs = s.get("class_labels_raw") or []
                class_labels = sorted(
                    {str(x).strip() for x in raw_labs if x is not None and str(x).strip()}
                )
                stats_map[str(s.get("regatta_id") or "").strip()] = {
                    "entries_count": int(s.get("entries_count") or 0),
                    "classes_count": len(class_keys),
                    "sailors_count": len(sailor_keys),
                    "class_keys": class_keys,
                    "sailor_keys": sailor_keys,
                    "class_labels": class_labels,
                }
    except Exception as e:
        print(f"[yearly-events] query failed: {e}")
        rows = []
        upcoming_rows = []
        stats_map = {}
    finally:
        if conn:
            try:
                return_db_connection(conn)
            except Exception:
                pass

    now = datetime.now().date()
    cur_month = int(now.month)
    groups: dict[str, dict] = {}
    for r in rows:
        name = (r.get("event_name") or "").strip()
        key = _yearly_event_series_key(name)
        if not key:
            continue
        sd = r.get("start_date")
        ed = r.get("end_date")
        as_at = r.get("as_at_time")
        d = ed or sd
        rid_raw = str(r.get("regatta_id") or "").strip().lower()
        year = int(getattr(d, "year", 0) or 0)
        if year <= 0:
            m = re.search(r"-(19|20)\d{2}-", f"-{rid_raw}-")
            if m:
                year = int(m.group(0).strip("-").split("-")[0])
        if year <= 0:
            m2 = re.search(r"\b(19|20)\d{2}\b", name)
            if m2:
                year = int(m2.group(0))
        month = int(getattr(sd or d, "month", 0) or 0)
        if year <= 0:
            continue
        g = groups.get(key)
        if not g:
            dn, ds = _yearly_initial_display_for_key(key, name)
            g = {
                "series_key": key,
                "display_name": dn,
                "display_name_score": ds,
                "years": set(),
                "month": month or 1,
                "latest_date": d,
                "latest_regatta_id": (r.get("regatta_id") or "").strip(),
                "history": [],
            }
            groups[key] = g
        g["years"].add(year)
        rid = (r.get("regatta_id") or "").strip()
        st = stats_map.get(rid, {})
        canon = _yearly_canonical_display_for_key(key)
        if canon:
            g["display_name"] = canon
            g["display_name_score"] = (-1, 0)
        else:
            cand_title = _yearly_event_series_title(name)
            cand_score = _yearly_event_title_score(cand_title)
            if cand_title and cand_score < g.get("display_name_score", (999, 999)):
                g["display_name"] = cand_title
                g["display_name_score"] = cand_score
        g["history"].append(
            {
                "year": year,
                "regatta_id": rid,
                "has_results": bool(r.get("has_results")),
                "entries_count": int(st.get("entries_count") or 0),
                "classes_count": int(st.get("classes_count") or 0),
                "sailors_count": int(st.get("sailors_count") or 0),
                "class_keys": set(st.get("class_keys") or set()),
                "sailor_keys": set(st.get("sailor_keys") or set()),
                "class_labels": set(st.get("class_labels") or []),
                "result_date": as_at or ed or sd,
                "end_date": d,
            }
        )
        if d and (g["latest_date"] is None or d > g["latest_date"]):
            g["latest_date"] = d
            g["latest_regatta_id"] = rid
            if month:
                g["month"] = month

    # Pull in upcoming events so known series show future years even before results exist.
    for e in (upcoming_rows or []):
        name = (e.get("event_name") or "").strip()
        key = _yearly_event_series_key(name)
        if not key:
            continue
        sd = e.get("start_date")
        ed = e.get("end_date")
        d = ed or sd
        rid_raw = str(e.get("regatta_id") or "").strip().lower()
        year = int(getattr(d, "year", 0) or 0)
        if year <= 0:
            m = re.search(r"-(19|20)\d{2}-", f"-{rid_raw}-")
            if m:
                year = int(m.group(0).strip("-").split("-")[0])
        if year <= 0:
            m2 = re.search(r"\b(19|20)\d{2}\b", name)
            if m2:
                year = int(m2.group(0))
        if year <= 0:
            continue
        month = int(getattr(sd or d, "month", 0) or 0)
        g = groups.get(key)
        if not g:
            dn, ds = _yearly_initial_display_for_key(key, name)
            g = {
                "series_key": key,
                "display_name": dn,
                "display_name_score": ds,
                "years": set(),
                "month": month or 1,
                "latest_date": d,
                "latest_regatta_id": "",
                "history": [],
            }
            groups[key] = g
        if year in g["years"]:
            continue
        g["years"].add(year)
        ev_rid = (str(e.get("regatta_id") or "").strip() if e.get("regatta_id") is not None else "") or ""
        g["history"].append(
            {
                "year": year,
                "regatta_id": ev_rid,
                "has_results": False,
                "entries_count": 0,
                "classes_count": 0,
                "sailors_count": 0,
                "class_keys": set(),
                "sailor_keys": set(),
                "class_labels": set(),
                "result_date": None,
                "scheduled_date": d,
                "end_date": d,
            }
        )
        if d and (g["latest_date"] is None or d > g["latest_date"]):
            g["latest_date"] = d
            if month:
                g["month"] = month

    cy = int(now.year)
    for g in groups.values():
        ys = g.get("years") or set()
        # Established series (2+ years): if current calendar year has no row yet, show a placeholder
        # so readers see where the next edition should appear on the Events calendar.
        if len(ys) >= 2 and cy not in ys:
            g["years"].add(cy)
            g["history"].append(
                {
                    "year": cy,
                    "regatta_id": "",
                    "has_results": False,
                    "entries_count": 0,
                    "classes_count": 0,
                    "sailors_count": 0,
                    "class_keys": set(),
                    "sailor_keys": set(),
                    "class_labels": set(),
                    "result_date": None,
                    "scheduled_date": None,
                    "end_date": None,
                    "missing_calendar_listing": True,
                }
            )
        # Merge all sheets in the same event-year into one yearly total.
        by_year = {}
        for h in g["history"]:
            y = int(h.get("year") or 0)
            if y <= 0:
                continue
            agg = by_year.get(y)
            if not agg:
                by_year[y] = {
                    "year": y,
                    "regatta_id": h.get("regatta_id") or "",
                    "has_results": bool(h.get("has_results")),
                    "entries_count": int(h.get("entries_count") or 0),
                    "class_keys": set(h.get("class_keys") or set()),
                    "sailor_keys": set(h.get("sailor_keys") or set()),
                    "class_label_set": set(h.get("class_labels") or set()),
                    "result_date": h.get("result_date"),
                    "scheduled_date": h.get("scheduled_date"),
                    "end_date": h.get("end_date"),
                    "missing_calendar_listing": bool(h.get("missing_calendar_listing")),
                }
                continue
            agg["has_results"] = bool(agg.get("has_results")) or bool(h.get("has_results"))
            agg["entries_count"] += int(h.get("entries_count") or 0)
            agg["class_keys"].update(h.get("class_keys") or set())
            agg["sailor_keys"].update(h.get("sailor_keys") or set())
            agg["class_label_set"].update(h.get("class_labels") or set())
            if (
                (h.get("regatta_id") or "").strip()
                or h.get("scheduled_date")
                or bool(h.get("has_results"))
                or int(h.get("entries_count") or 0) > 0
            ):
                agg["missing_calendar_listing"] = False
            agg_date = agg.get("end_date")
            cur_date = h.get("end_date")
            if cur_date and (not agg_date or cur_date > agg_date):
                agg["end_date"] = cur_date
                agg["regatta_id"] = h.get("regatta_id") or agg.get("regatta_id") or ""
                agg["result_date"] = h.get("result_date") or agg.get("result_date")
                agg["scheduled_date"] = h.get("scheduled_date") or agg.get("scheduled_date")
            h_rid = (h.get("regatta_id") or "").strip()
            if h_rid and not (agg.get("regatta_id") or "").strip():
                agg["regatta_id"] = h_rid
            if h.get("scheduled_date") and not agg.get("scheduled_date"):
                agg["scheduled_date"] = h.get("scheduled_date")
        g["history"] = sorted(
            [
                {
                    "year": yy,
                    "regatta_id": v.get("regatta_id") or "",
                    "has_results": bool(v.get("has_results")),
                    "entries_count": int(v.get("entries_count") or 0),
                    "classes_count": len(v.get("class_keys") or set()),
                    "sailors_count": len(v.get("sailor_keys") or set()),
                    "class_labels": sorted(v.get("class_label_set") or set()),
                    "result_date": v.get("result_date"),
                    "scheduled_date": v.get("scheduled_date"),
                    "end_date": v.get("end_date"),
                    "missing_calendar_listing": bool(v.get("missing_calendar_listing")),
                }
                for yy, v in by_year.items()
            ],
            key=lambda x: x["year"],
            reverse=True,
        )
        # Earliest upcoming scheduled date for this series (from events feed roll-ins).
        next_upcoming_date = None
        for h in g["history"]:
            sd = h.get("scheduled_date")
            if not sd:
                continue
            if hasattr(sd, "date") and callable(getattr(sd, "date", None)):
                try:
                    sd = sd.date()
                except Exception:
                    pass
            if next_upcoming_date is None or sd < next_upcoming_date:
                next_upcoming_date = sd
        years_sorted = sorted(g["years"], reverse=True)
        month = int(g["month"] or 1)
        month_offset = (month - cur_month) % 12
        out.append(
            {
                "series_key": g.get("series_key") or "",
                "display_name": g["display_name"],
                "count_years": len(years_sorted),
                "years": years_sorted,
                "month": month,
                "month_offset": month_offset,
                "next_upcoming_date": next_upcoming_date,
                "latest_regatta_id": g["latest_regatta_id"],
                "history": g["history"],
            }
        )
    # Month cycle first; within month same rules as /events (entries + series depth + first-year last).
    out.sort(key=lambda x: (x["month_offset"],) + _yearly_series_row_sort_key(x))
    return out


def _yearly_series_max_and_history_maps() -> tuple[dict[str, int], dict[str, list]]:
    """Single pass over /yearly-events data: max entries per series_key (same as yearly row sort) + history rows."""
    max_by_sk: dict[str, int] = {}
    hist_by_sk: dict[str, list] = {}
    for r in _get_yearly_event_series():
        sk = (r.get("series_key") or "").strip() or _yearly_event_series_key(
            (r.get("display_name") or "").strip()
        )
        if not sk:
            continue
        hist = r.get("history") or []
        hist_by_sk[sk] = hist
        mx = 0
        for h in hist:
            mx = max(mx, int(h.get("entries_count") or 0))
        max_by_sk[sk] = mx
    return max_by_sk, hist_by_sk


def _event_year_from_public_event_item(item: dict) -> int:
    sd = item.get("start_date")
    if sd is None:
        return 0
    if hasattr(sd, "year"):
        try:
            return int(sd.year)
        except Exception:
            pass
    s = str(sd)[:10]
    if len(s) >= 4 and s[:4].isdigit():
        return int(s[:4])
    return 0


def _prior_year_entries_from_hist(hist: list | None, event_year: int) -> tuple[int | None, int | None]:
    """Latest calendar year strictly before event_year with positive entries (label for hub / API)."""
    if not hist or event_year <= 0:
        return None, None
    best_y: int | None = None
    best_e = 0
    for h in hist:
        y = int(h.get("year") or 0)
        if y <= 0 or y >= event_year:
            continue
        ec = int(h.get("entries_count") or 0)
        if ec <= 0:
            continue
        if best_y is None or y > best_y:
            best_y = y
            best_e = ec
    if best_y is None:
        return None, None
    return best_y, best_e


def _yearly_events_page_html() -> str:
    rows = _get_yearly_event_series()
    month_names = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December")
    by_month: dict[int, list[dict]] = {}
    for r in rows:
        m = max(1, min(12, int(r.get("month") or 1)))
        by_month.setdefault(m, []).append(r)
    body_parts = []
    if not rows:
        body_parts.append('<p class="yl-empty">No recurring yearly events found yet.</p>')
    else:
        for m in sorted(by_month.keys(), key=lambda mm: ((mm - datetime.now().month) % 12, mm)):
            body_parts.append(f'<section class="card yl-month-box"><h2 class="yl-month-title">{month_names[m-1]}</h2>')
            month_rows = sorted(by_month[m], key=_yearly_series_row_sort_key)
            for i, r in enumerate(month_rows, start=1):
                years_line = "/".join(str(y) for y in r["years"])
                count_txt = f"({r['count_years']} years)"
                hist = []
                for h in (r.get("history") or []):
                    year_txt = str(int(h.get("year") or 0))
                    h_has_results = bool(h.get("has_results"))
                    h_rid = (h.get("regatta_id") or "").strip()
                    if bool(h.get("missing_calendar_listing")):
                        stats_txt = html_module.escape(
                            "No upcoming event listed for this year yet · Not on the Events calendar — add it when dates are known"
                        )
                        card_inner = (
                            f'<span class="yl-year">{html_module.escape(year_txt)}</span>'
                            f'<span class="yl-stats">{stats_txt}</span>'
                        )
                        hist.append(
                            f'<div class="yl-year-card yl-year-card--pending">{card_inner}</div>'
                        )
                        continue
                    lbls = h.get("class_labels") or []
                    cls_names_html = ""
                    if lbls:
                        lim = 24
                        shown = lbls[:lim]
                        extra = " …" if len(lbls) > lim else ""
                        cls_names_html = " · " + html_module.escape("Class names: " + ", ".join(shown) + extra)
                    if h_has_results:
                        rd = h.get("result_date")
                        if hasattr(rd, "strftime"):
                            rd_txt = rd.strftime("%d %b %Y")
                        elif rd:
                            rd_txt = str(rd)[:10]
                        else:
                            rd_txt = ""
                        stats_txt = (
                            f'Entries: {int(h.get("entries_count") or 0)} · '
                            f'Classes: {int(h.get("classes_count") or 0)} · '
                            f'Sailors: {int(h.get("sailors_count") or 0)}'
                        )
                        if rd_txt:
                            stats_txt += f' · Result date: {html_module.escape(rd_txt)}'
                        stats_txt += cls_names_html
                    else:
                        sd = h.get("scheduled_date")
                        if hasattr(sd, "strftime"):
                            sd_txt = sd.strftime("%d %b %Y")
                        elif sd:
                            sd_txt = str(sd)[:10]
                        else:
                            sd_txt = ""
                        stats_txt = f'Results pending{(" · Scheduled: " + html_module.escape(sd_txt)) if sd_txt else ""}'
                        stats_txt += cls_names_html
                    card_inner = (
                        f'<span class="yl-year">{html_module.escape(year_txt)}</span>'
                        f'<span class="yl-stats">{stats_txt}</span>'
                    )
                    if h_has_results and h_rid:
                        hist.append(
                            f'<a class="yl-year-card yl-year-card--has-results" href="/regatta/{html_module.escape(h_rid)}">{card_inner}</a>'
                        )
                    elif h_rid:
                        hist.append(
                            f'<a class="yl-year-card yl-year-card--pending yl-year-card--linked" href="/regatta/{html_module.escape(h_rid)}">{card_inner}</a>'
                        )
                    else:
                        hist.append(
                            f'<div class="yl-year-card yl-year-card--pending">{card_inner}</div>'
                        )
                hist_html = '<div class="yl-years-list">' + "".join(hist) + "</div>" if hist else ""
                body_parts.append(
                    '<div class="yl-card">'
                    f'<div class="yl-title">{i}. {html_module.escape(r["display_name"])}</div>'
                    f'<div class="yl-meta">{count_txt} - {html_module.escape(years_line)}</div>'
                    f'{hist_html}'
                    '</div>'
                )
            body_parts.append('</section>')
    body = "\n".join(body_parts)
    return f"""<!DOCTYPE html>
<html lang="en-US">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>Yearly Events – SailingSA</title>
  <link rel="canonical" href="https://sailingsa.co.za/yearly-events">
  <link rel="icon" type="image/png" sizes="48x48" href="/favicon-48.png">
  <link rel="stylesheet" href="/css/main.css">
  <style>
    .yl-wrap{{max-width:980px;margin:0 auto;padding:1rem;}}
    .yl-month-box{{background:#f8fbff;border:1px solid #7fb3e8;border-radius:12px;padding:10px 10px 6px 10px;margin-bottom:10px;}}
    .yl-month-title{{font-size:1rem;font-weight:800;color:#001f3f;margin:0 0 8px 0;}}
    .yl-card{{background:#fff;border:1px solid #7fb3e8;border-radius:10px;padding:10px 12px;margin-bottom:8px;}}
    .yl-title{{font-weight:800;color:#001f3f;font-size:0.95rem;}}
    .yl-meta{{font-size:0.82rem;color:#334155;margin-top:2px;}}
    .yl-years-list{{margin:6px 0 0 0;padding:0;display:grid;gap:6px;}}
    .yl-year-card{{display:flex;justify-content:space-between;gap:8px;font-size:0.8rem;padding:8px 10px;border:1px solid #7fb3e8;border-radius:8px;}}
    .yl-year-card--has-results{{background:#b7ff4a;color:#0f172a;text-decoration:none;}}
    .yl-year-card--has-results:hover{{filter:brightness(0.98);}}
    .yl-year-card--pending{{background:#f9fcff;color:#334155;}}
    .yl-year-card--linked{{text-decoration:none;color:#001f3f;}}
    .yl-year-card--linked:hover{{text-decoration:underline;}}
    .yl-year-card--has-results .yl-year{{color:#0b2f07;}}
    .yl-year-card--has-results .yl-stats{{color:#1f3d1a;}}
    .yl-year{{font-weight:700;color:#001f3f;}}
    .yl-stats{{color:#475569;}}
    .yl-empty{{color:#64748b;}}
    .yl-sub{{font-size:0.82rem;color:#64748b;margin:0 0 10px 0;}}
  </style>
</head>
<body>
<header class="site-header">
  <div class="container" style="display:flex;align-items:center;flex-wrap:wrap;gap:0.75rem;">
    <a href="/" class="logo" title="Home"><img src="/assets/logos/sailingsa-logo.png" alt="SailingSA Logo"></a>
    <nav class="nav-inline" aria-label="Main" style="display:flex;align-items:center;gap:0.75rem;flex-wrap:wrap;margin-right:auto;">
      <a href="/">Home</a><a href="/sailors">Sailors</a><a href="/regattas">Regattas</a><a href="/classes">Classes</a><a href="/clubs">Clubs</a><a href="/events">Events</a><a href="/about">About</a>
    </nav>
    <div class="header-auth" style="margin-left:auto;"></div>
  </div>
</header>
<main class="main-content">
  <div class="yl-wrap">
    <div class="card">
      <h1 class="section-title">Yearly Events</h1>
      <p class="yl-sub">Ordered from current month onward. Past-in-year months roll lower as next cycle items. Each year with results lists class names from the database for quick audits (single-fleet vs multi-class).</p>
      {body}
    </div>
  </div>
</main>
<footer class="site-footer-about" style="text-align:center;padding:2rem 1rem;font-size:0.9rem;color:#666;border-top:1px solid #e0e0e0;margin-top:2rem;">SailingSA – South African Sailing Results Database © <span id="year-ye"></span></footer>
<script>document.getElementById('year-ye').textContent = new Date().getFullYear();</script>
</body>
</html>"""


@app.get("/yearly-events", response_class=HTMLResponse)
def yearly_events_page():
    return HTMLResponse(_yearly_events_page_html())


@app.get("/events/type/{slug}", response_class=HTMLResponse)
def events_type_page(request: Request, slug: str):
    """Event type page: /events/type/{slug} e.g. regional-championships, nationals. Same card layout as /events, filtered by category."""
    data = _get_events_by_type_slug(slug)
    if not data.get("display_name"):
        return RedirectResponse(url="/events", status_code=301)
    return HTMLResponse(_events_type_page_html(slug, data["display_name"], data))


@app.get("/sailor")
def _redirect_sailor_directory():
    """Singular /sailor → directory (SEO / legacy links)."""
    return RedirectResponse(url="/sailors", status_code=301)


@app.get("/sailor/")
def _redirect_sailor_directory_trailing_slash():
    return RedirectResponse(url="/sailors", status_code=301)


@app.get("/regatta")
def _redirect_regatta_directory():
    """Singular /regatta → events listing (SEO / legacy links)."""
    return RedirectResponse(url="/events", status_code=301)


@app.get("/regatta/")
def _redirect_regatta_directory_trailing_slash():
    """Nginx often 301s /regatta → /regatta/; send that to /events as well."""
    return RedirectResponse(url="/events", status_code=301)


@app.get("/club")
def _redirect_club_directory():
    """Singular /club → directory (SEO / legacy links)."""
    return RedirectResponse(url="/clubs", status_code=301)


@app.get("/club/")
def _redirect_club_directory_trailing_slash():
    return RedirectResponse(url="/clubs", status_code=301)


@app.get("/class")
def _redirect_class_directory():
    """Singular /class → directory (SEO / legacy links)."""
    return RedirectResponse(url="/classes", status_code=301)


@app.get("/class/")
def _redirect_class_directory_trailing_slash():
    return RedirectResponse(url="/classes", status_code=301)


@app.get("/sailor/{slug}")
@app.head("/sailor/{slug}")
def _sailor_spa(slug: str): return serve_sailor_spa(slug)


@app.get("/class/{class_slug}")
@app.head("/class/{class_slug}")
def _class_spa(class_slug: str): return serve_class_spa(class_slug)


def _static_dir():
    """Return absolute static dir (same as STATIC_DIR) so worker cwd does not affect paths."""
    return STATIC_DIR


@app.get("/regatta/results.html")
def _regatta_results_html():
    """Serve actual regatta results page so iframe shows results, not SPA landing page."""
    path = os.path.join(_static_dir(), "regatta", "results.html")
    if os.path.isfile(path):
        return FileResponse(path, media_type="text/html")
    raise HTTPException(status_code=404, detail="regatta/results.html not found")


@app.get("/regatta/class/class-results.html")
def _regatta_class_results_html():
    path = os.path.join(_static_dir(), "regatta", "class", "class-results.html")
    if os.path.isfile(path):
        return FileResponse(path, media_type="text/html")
    raise HTTPException(status_code=404, detail="regatta/class/class-results.html not found")


@app.get("/regatta/class/podium/podium.html")
def _regatta_podium_html():
    path = os.path.join(_static_dir(), "regatta", "class", "podium", "podium.html")
    if os.path.isfile(path):
        return FileResponse(path, media_type="text/html")
    raise HTTPException(status_code=404, detail="regatta/class/podium/podium.html not found")


@app.get("/about")
def _about_html():
    """Serve About SailingSA page at /about."""
    path = os.path.join(_static_dir(), "about.html")
    if os.path.isfile(path):
        return FileResponse(path, media_type="text/html")
    raise HTTPException(status_code=404, detail="about.html not found")


# Directory pages: /sailors, /regattas, /clubs, /classes — alphabetical lists for SEO crawl
def _directory_sailors():
    """Return [(display_name, slug), ...] for sailors with at least one result. Sorted by name."""
    out = []
    try:
        if not table_exists("results") or not table_exists("sas_id_personal"):
            return out
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cur.execute("""
                SELECT DISTINCT r.helm_sa_sailing_id::text AS sas_id,
                    COALESCE(TRIM(s.full_name), TRIM(s.first_name || ' ' || COALESCE(s.last_name, ''))) AS full_name
                FROM results r
                JOIN public.sas_id_personal s ON s.sa_sailing_id::text = r.helm_sa_sailing_id::text
                WHERE r.helm_sa_sailing_id IS NOT NULL AND (s.full_name IS NOT NULL AND TRIM(s.full_name) != '' OR s.first_name IS NOT NULL OR s.last_name IS NOT NULL)
                UNION
                SELECT DISTINCT r.crew_sa_sailing_id::text AS sas_id,
                    COALESCE(TRIM(s.full_name), TRIM(s.first_name || ' ' || COALESCE(s.last_name, ''))) AS full_name
                FROM results r
                JOIN public.sas_id_personal s ON s.sa_sailing_id::text = r.crew_sa_sailing_id::text
                WHERE r.crew_sa_sailing_id IS NOT NULL AND (s.full_name IS NOT NULL AND TRIM(s.full_name) != '' OR s.first_name IS NOT NULL OR s.last_name IS NOT NULL)
            """)
            rows = cur.fetchall()
            by_sid = {}
            for r in rows:
                sid = str(r.get("sas_id") or "")
                if not sid:
                    continue
                name = (r.get("full_name") or "").strip()
                if not name:
                    continue
                by_sid[sid] = name
            from collections import defaultdict
            by_name = defaultdict(list)
            for sid, name in by_sid.items():
                by_name[name].append(sid)
            for name, sids in sorted(by_name.items(), key=lambda x: x[0].lower()):
                has_dup = len(sids) > 1
                for sid in sids:
                    slug = _sailor_canonical_slug(name, sid, has_dup)
                    out.append((name, slug))
        finally:
            cur.close()
            return_db_connection(conn)
    except Exception as e:
        print(f"[directory] sailors: {e}")
    return out


def _directory_regattas():
    """Return [(event_name, slug), ...] for regattas. Sorted by event_name."""
    out = []
    try:
        if not table_exists("regattas"):
            return out
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cur.execute("""
                SELECT event_name FROM regattas
                WHERE event_name IS NOT NULL AND TRIM(event_name) != ''
                ORDER BY event_name
            """)
            for r in cur.fetchall() or []:
                name = (r.get("event_name") or "").strip()
                if not name:
                    continue
                slug = re.sub(r"[^\w\s\-]", "", name).strip().lower()
                slug = re.sub(r"\s+", "-", slug).strip("-")
                if slug:
                    out.append((name, slug))
        finally:
            cur.close()
            return_db_connection(conn)
    except Exception as e:
        print(f"[directory] regattas: {e}")
    return out


def _directory_clubs():
    """Return [(display_name, slug), ...] for all clubs. Links to /club/{slug}. Uses club_fullname or club_abbrev (PROD has no club_name). Slug generated from display name."""
    out = []
    try:
        if not table_exists("clubs"):
            return out
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cur.execute("""
                SELECT club_fullname, club_abbrev FROM clubs
                WHERE ((club_fullname IS NOT NULL AND TRIM(club_fullname) != '')
                   OR (club_abbrev IS NOT NULL AND TRIM(club_abbrev) != ''))
                  AND lower(trim(COALESCE(club_abbrev, ''))) != 'unassigned'
                  AND lower(trim(COALESCE(club_fullname, ''))) != 'unassigned'
                ORDER BY COALESCE(NULLIF(TRIM(club_fullname), ''), club_abbrev) ASC
            """)
            for r in cur.fetchall() or []:
                fullname = (r.get("club_fullname") or "").strip()
                abbrev = (r.get("club_abbrev") or "").strip()
                if abbrev and fullname:
                    display = abbrev + " – " + fullname
                else:
                    display = fullname or abbrev
                if not display:
                    continue
                slug = _club_slug_from_name(abbrev) if abbrev else _club_slug_from_name(fullname)
                if slug:
                    out.append((display, slug))
        finally:
            cur.close()
            return_db_connection(conn)
    except Exception as e:
        print(f"[directory] clubs: {e}")
    return out


def _directory_classes():
    """Return [(class_name, path), ...] for classes. path = /class/{id}-{slug}. Sorted by class_name."""
    out = []
    try:
        if not table_exists("classes"):
            return out
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cur.execute("SELECT class_id, class_name FROM classes WHERE class_id IS NOT NULL ORDER BY class_name")
            for r in cur.fetchall() or []:
                cid = r.get("class_id")
                name = (r.get("class_name") or "").strip()
                if cid is None or not name:
                    continue
                slug = _class_canonical_slug(name) if name else ""
                path = f"/class/{cid}-{slug}" if slug else f"/class/{cid}"
                out.append((name, path))
        finally:
            cur.close()
            return_db_connection(conn)
    except Exception as e:
        print(f"[directory] classes: {e}")
    return out


def _directory_page_html(title: str, items: list, href_key: str, page_title: str):
    """Build full HTML for a directory page. items = [(display_name, slug_or_path), ...]. href_key = 'sailor'|'regatta'|'club'|'class' (for link path)."""
    about_by_page = {
        "sailor": "Search all South African sailors with complete regatta results, rankings, and performance history. SailingSA is the most comprehensive South African sailing results database for sailors.",
        "regatta": "Explore all South African sailing regattas with full race results, rankings, and performance history. SailingSA is the most complete South African regatta results database.",
        "club": "View all South African sailing clubs and their hosted events, sailors, and regatta results. SailingSA provides a complete directory of South African sailing activity and performance.",
        "class": "Browse all South African sailing classes with regatta results, sailor rankings, and fleet performance. SailingSA tracks all major South African sailing classes and results.",
    }
    about_text = about_by_page.get(href_key, "")
    header = """<!DOCTYPE html>
<html lang="en-US">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>""" + html_module.escape(page_title) + """</title>
<link rel="canonical" href="https://sailingsa.co.za""" + html_module.escape(title) + """">
<link rel="icon" type="image/png" sizes="48x48" href="/favicon-48.png">
<link rel="stylesheet" href="/css/main.css">
<style>.dir-page{max-width:950px;margin:0 auto;padding:40px 20px;}.dir-page h1{font-size:1.5rem;color:#001f3f;margin-bottom:0.75rem;}.dir-page h2{font-size:1.1rem;color:#001f3f;margin:1rem 0 0.4rem;}.dir-page ul{list-style:none;padding:0;margin:0;}.dir-page li{margin:0.25rem 0;}.dir-page a{color:#001f3f;font-weight:600;text-decoration:underline;}.dir-page a:hover{color:#e65100;}.page-about-block{margin:0 0 1rem 0;padding:0.85rem 1rem;border:1px solid #dbe5ef;border-radius:8px;background:#f8fbff;color:#1e293b;line-height:1.45;font-size:0.95rem;}</style>
</head>
<body>
<header class="site-header"><div class="container" style="display:flex;align-items:center;flex-wrap:wrap;gap:0.75rem;">
<a href="/" class="logo js-go-home" title="Home"><img src="/assets/logos/sailingsa-logo.png" alt="SailingSA Logo"></a>
<nav class="nav-inline" aria-label="Main" style="display:flex;align-items:center;gap:0.75rem;flex-wrap:wrap;margin-right:auto;"><a href="/">Home</a><a href="/sailors">Sailors</a><a href="/regattas">Regattas</a><a href="/classes">Classes</a><a href="/clubs">Clubs</a><a href="https://sailingsa.co.za/events">Events</a><a href="/stats">Statistics</a><a href="/about">About</a></nav>
<div class="header-auth" style="margin-left:auto;"></div>
</div></header>
<main class="main-content"><div class="container"><div class="card dir-page"><h1>""" + html_module.escape(page_title) + """</h1>""" + (f'<div class="page-about-block">{html_module.escape(about_text)}</div>' if about_text else "") + """
"""
    _footer = '<footer class="site-footer-about" style="text-align:center;padding:2rem 1rem;font-size:0.9rem;color:#666;border-top:1px solid #e0e0e0;margin-top:2rem;">SailingSA – South African Sailing Results Database © <span id="year"></span></footer><script>document.getElementById("year").textContent=new Date().getFullYear();</script>'
    if not items:
        header += "<p>No entries.</p>" + _seo_discovery_block_html() + "</div></div></main>" + _footer + "</body></html>"
        return header
    # Group by first letter for sailors; for others use single list
    if href_key == "sailor":
        from collections import OrderedDict
        by_letter = OrderedDict()
        for name, slug in items:
            letter = (name[:1].upper() if name else "?")
            if letter not in by_letter:
                by_letter[letter] = []
            by_letter[letter].append((name, f"/sailor/{html_module.escape(slug)}"))
        body_parts = []
        for letter in sorted(by_letter.keys()):
            body_parts.append(f"<h2>{html_module.escape(letter)}</h2><ul>")
            for name, href in by_letter[letter]:
                body_parts.append(f'<li><a href="{href}">{html_module.escape(name)}</a></li>')
            body_parts.append("</ul>")
        header += "\n".join(body_parts)
    else:
        header += "<ul>"
        for name, slug_or_path in items:
            path = slug_or_path if slug_or_path.startswith("/") else f"/{href_key}/{slug_or_path}"
            header += f'<li><a href="{html_module.escape(path)}">{html_module.escape(name)}</a></li>'
        header += "</ul>"
    header += _seo_discovery_block_html() + "</div></div></main>" + _footer + "</body></html>"
    return header


@app.get("/sailors", response_class=HTMLResponse)
def _directory_sailors_page():
    """Directory: all sailors, alphabetical by first letter. Links to /sailor/{slug}."""
    items = _directory_sailors()
    return HTMLResponse(_directory_page_html("/sailors", items, "sailor", "Sailors"))


@app.get("/regattas", response_class=HTMLResponse)
def _directory_regattas_page():
    """Directory: all regattas. Links to /regatta/{slug}."""
    items = _directory_regattas()
    return HTMLResponse(_directory_page_html("/regattas", items, "regatta", "Regattas"))


@app.get("/clubs", response_class=HTMLResponse)
def _directory_clubs_page():
    """Directory: all clubs. Links to /club/{slug}."""
    items = _directory_clubs()
    return HTMLResponse(_directory_page_html("/clubs", items, "club", "Clubs"))


@app.get("/classes", response_class=HTMLResponse)
def _directory_classes_page(request: Request):
    """Directory: all classes rendered by API route. Links to /class/{id}-{slug}."""
    items = _directory_classes()
    return HTMLResponse(_directory_page_html("/classes", items, "class", "Classes"))


@app.head("/classes")
def _directory_classes_page_head():
    """HEAD support for crawlers / health checks."""
    return Response(status_code=200)


def _format_event_date_range(start_date, end_date, start_time=None, end_time=None):
    """Format event date range for display. If start_time exists: 'Thu 30 Apr 2026 18:00 – Sun 03 May 2026 18:00'. Else date only: 'Sat 14 Mar 2026 – Sun 15 Mar 2026'."""
    if not start_date:
        return "—"
    try:
        time_fmt = "%H:%M"
        if hasattr(start_date, "strftime"):
            start_str = start_date.strftime("%a %d %b %Y")
        else:
            start_str = str(start_date)[:10] if start_date else "—"
        if start_time and hasattr(start_time, "strftime"):
            start_str += " " + start_time.strftime(time_fmt)
        if end_date and end_date != start_date:
            if hasattr(end_date, "strftime"):
                end_str = end_date.strftime("%a %d %b %Y")
            else:
                end_str = str(end_date)[:10]
            if end_time and hasattr(end_time, "strftime"):
                end_str += " " + end_time.strftime(time_fmt)
            return f"{start_str} – {end_str}"
        return start_str
    except Exception:
        return str(start_date) if start_date else "—"


# Host separator: SAS scrape may use middle dot · (U+00B7), bullet • (U+2022), or pipe |
# Rule: If host_club_name_raw contains · OR • OR | then SPLIT, take the LAST part, TRIM. Use that for club resolution only.
# Never attempt club matching on the association part. Examples:
#   "LASA (Laser Association of South Africa) · Club Mykonos" -> host_display = "Club Mykonos"
#   "29er Class Association · Saldanha Bay Yacht Club" -> host_display = "Saldanha Bay Yacht Club"
_HOST_SEPARATORS = ("\u00b7", "\u2022", "|")  # · • |


def _parse_host_after_separator(raw: str) -> str:
    """If raw contains · or • or |: split, take LAST part, trim. Use for club resolution only; never match on association. Handles ·, •, |."""
    if not raw or not isinstance(raw, str):
        return (raw or "").strip()
    s = raw.strip().lstrip(">").strip()
    parts = re.split(r"[\u00b7\u2022|]", s)
    if len(parts) > 1:
        last = (parts[-1] or "").strip()
        if last:
            return last
    return s


def _is_association_like(s: str) -> bool:
    """True if string looks like a class/association name rather than a club (e.g. '29er Class Association', 'LASA (Laser...)'). Used to prefer venue_raw as host when host_club_name_raw is association-only."""
    if not s or not isinstance(s, str):
        return False
    h = s.strip().lower()
    return (
        "association" in h or "associat" in h or h.startswith("lasa ") or h == "lasa"
        or "29er class" in h or "laser associat" in h or "dabchick class" in h
    )


def _host_display_from_row(r) -> str:
    """Preferred host_display for a row: use venue_raw when host_club_name_raw parses to association-like; else parsed host_club_name_raw."""
    raw_host = (r.get("host_club_name_raw") or "").strip()
    venue = (r.get("venue_raw") or "").strip()
    part = _parse_host_after_separator(raw_host)
    if _is_association_like(part) and venue:
        return venue
    return part or ""


def _best_club_substring_match(event_lower: str, club_rows, unassigned_id):
    """If event_lower contains a club abbrev or fullname as substring, return (club_id, club_abbrev, club_fullname) for the longest match (same idea as load_events_csv_to_db.resolve_club_from_event_name). Excludes virtual Unassigned."""
    if not event_lower or not event_lower.strip():
        return None
    event_lower = event_lower.strip().lower()
    candidates = []
    for row in club_rows:
        cid = row.get("club_id")
        if cid is None:
            continue
        if unassigned_id is not None and int(cid) == int(unassigned_id):
            continue
        abbr_l = (row.get("abbr_l") or "").strip()
        full_l = (row.get("full_l") or "").strip()
        if abbr_l and abbr_l in event_lower:
            candidates.append((cid, len(abbr_l)))
        if full_l and full_l in event_lower:
            candidates.append((cid, len(full_l)))
    if not candidates:
        return None
    by_club = {}
    for cid, length in candidates:
        by_club[cid] = max(by_club.get(cid, 0), length)
    best_cid = max(by_club.items(), key=lambda x: x[1])[0]
    for row in club_rows:
        if row.get("club_id") == best_cid:
            abbr = (row.get("club_abbrev") or "").strip()
            full = (row.get("club_fullname") or "").strip()
            return (best_cid, abbr, full)
    return None


def _apply_event_title_club_match(cur, upcoming_rows, past_rows):
    """After host/venue equality match: if host_club_id still NULL, resolve club from club name/abbrev appearing inside event_name (then venue/location), same as CSV loader. Reduces spurious Unassigned when SAS omits host but title names the club."""
    if not table_exists("clubs"):
        return
    uid = _get_unassigned_club_id()
    cur.execute(
        """
        SELECT club_id,
               trim(lower(coalesce(club_abbrev, ''))) AS abbr_l,
               trim(lower(coalesce(club_fullname, ''))) AS full_l,
               club_abbrev, club_fullname
        FROM clubs
        WHERE ((club_abbrev IS NOT NULL AND trim(club_abbrev) != '')
            OR (club_fullname IS NOT NULL AND trim(club_fullname) != ''))
          AND lower(trim(coalesce(club_abbrev, ''))) != 'unassigned'
        """
    )
    club_rows = list(cur.fetchall() or [])
    if not club_rows:
        return
    for r in upcoming_rows + past_rows:
        if r.get("host_club_id"):
            continue
        name = (r.get("event_name") or "").strip()
        if not name:
            continue
        blob = " ".join(
            x
            for x in (
                name,
                (r.get("venue_raw") or "").strip(),
                (r.get("location_raw") or "").strip(),
            )
            if x
        ).strip()
        matched = None
        for text in (name.lower(), blob.lower()):
            if not text.strip():
                continue
            matched = _best_club_substring_match(text, club_rows, uid)
            if matched:
                break
        if matched:
            cid, abbr, full = matched
            r["host_club_id"] = cid
            r["club_abbrev"] = abbr
            r["club_fullname"] = full
            r["club_slug"] = _club_slug_from_name(full or abbr)


def _category_to_slug(category: str) -> str:
    """Slug from category: lower, replace spaces with '-', remove non-word characters. Example: Regional Championships → regional-championships."""
    if not category or not isinstance(category, str):
        return ""
    s = category.lower().strip()
    s = re.sub(r"[^a-z0-9\s\-]", "", s)
    s = re.sub(r"\s+", "-", s).strip("-")
    return s or ""


def _event_date_to_iso(d):
    if d is None:
        return ""
    if hasattr(d, "strftime"):
        try:
            return d.strftime("%Y-%m-%d")
        except Exception:
            return str(d)[:10]
    return str(d)[:10]


def _event_date_only(d):
    """Normalize DB date / datetime to date for comparisons."""
    if d is None:
        return None
    if hasattr(d, "date") and callable(d.date):
        try:
            return d.date()
        except Exception:
            pass
    if hasattr(d, "year"):
        from datetime import date as _date

        try:
            return _date(d.year, d.month, d.day)
        except Exception:
            pass
    return None


def _derive_sanction_level(r) -> str:
    """SAS = SA Sailing calendar / official source; CLUB = other. OTHER reserved for edge cases."""
    src = (r.get("source") or "").strip().lower()
    url = ((r.get("source_url") or "") + " " + (r.get("organiser") or "")).lower()
    if src == "sas":
        return "SAS"
    if "sailing.org.za" in url or "sa-sailing" in url.replace(" ", ""):
        return "SAS"
    if "worldsailing" in url or "sailing.org" in url and "sailing.org.za" not in url:
        return "OTHER"
    return "CLUB"


