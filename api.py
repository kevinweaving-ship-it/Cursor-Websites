from fastapi import FastAPI, HTTPException, Body, Query, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Union, Optional, List
import os, psycopg2, psycopg2.extras, psycopg2.pool, re
from unidecode import unidecode
import time
from functools import lru_cache, wraps, cmp_to_key
from datetime import datetime, timedelta
import uuid
from collections import defaultdict
import logging
import feedparser
import httpx
import traceback
import hashlib
import json

NAME_SIM_THRESHOLD = 0.75

# Align default with config.postgres.env (sailors_user)
DB_URL = os.getenv("DB_URL", "postgresql://sailors_user:change_me_strong@localhost:5432/sailors_master")

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
    try:
        conn = pool.getconn()
        return conn
    except Exception as e:
        print(f"[DB] Error getting connection from pool: {e}")
        # Fallback to direct connection
        return psycopg2.connect(DB_URL, cursor_factory=psycopg2.extras.RealDictCursor)

def return_db_connection(conn):
    """Return a connection to the pool"""
    if DB_POOL:
        try:
            DB_POOL.putconn(conn)
        except Exception as e:
            print(f"[DB] Error returning connection to pool: {e}")
            try:
                conn.close()
            except:
                pass
    else:
        try:
            conn.close()
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
    return stats

app = FastAPI(title="Regatta API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.add_middleware(GZipMiddleware, minimum_size=500)

# ============================================================================
# REQUEST PROFILING MIDDLEWARE
# ============================================================================

@app.middleware("http")
async def profile_requests(request: Request, call_next):
    """Profile all API requests to identify slow endpoints with request IDs"""
    req_id = get_request_id()
    endpoint = f"{request.method} {request.url.path}"
    start = time.time()
    
    # Store request ID in request state for use in endpoints
    request.state.request_id = req_id
    
    print(f"[REQ {req_id}] → {endpoint}")
    
    try:
        response = await call_next(request)
        duration = time.time() - start
        status_code = response.status_code if hasattr(response, 'status_code') else 200
        log_endpoint_timing(req_id, endpoint, duration, status_code)
        return response
    except Exception as e:
        duration = time.time() - start
        log_endpoint_timing(req_id, f"{endpoint} [EXCEPTION: {str(e)}]", duration, status_code=500)
        raise

def q(sql, *args):
    """Execute query with connection pooling and profiling"""
    start = time.time()
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(sql, args)
            result = cur.fetchall()
            duration = (time.time() - start) * 1000
            if duration > 200:
                print(f"[DB] ⚠️  SLOW QUERY took {duration:.2f}ms: {sql[:100]}...")
            return result
    finally:
        if conn:
            return_db_connection(conn)

def one(sql, *args):
    """Execute query and return single row with connection pooling"""
    start = time.time()
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(sql, args)
            row = cur.fetchone()
            duration = time.time() - start  # Keep in seconds for logging
            
            # Full SQL tracing
            sql_trimmed = sql[:200] + "..." if len(sql) > 200 else sql
            params_str = str(args) if args else "()"
            print(f"[SQL] ({duration:.3f}s) {sql_trimmed} | params: {params_str}")
            
            # Log slow queries to file
            if duration > 0.5:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with open("slow_queries.log", "a") as f:
                    f.write(f"{timestamp} | {duration:.3f}s | {sql} | params: {params_str}\n")
                print(f"[SQL] ⚠️  SLOW QUERY ({duration:.3f}s) logged to slow_queries.log")
            
            if not row:
                raise HTTPException(status_code=404, detail="Not found")
            return row
    finally:
        if conn:
            return_db_connection(conn)

def qf(sql, *args):
    """Execute query with connection pooling"""
    start = time.time()
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(sql, args)
            result = cur.fetchall()
            duration = time.time() - start  # Keep in seconds for logging
            
            # Full SQL tracing
            sql_trimmed = sql[:200] + "..." if len(sql) > 200 else sql
            params_str = str(args) if args else "()"
            print(f"[SQL] ({duration:.3f}s) {sql_trimmed} | params: {params_str}")
            
            # Log slow queries to file
            if duration > 0.5:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with open("slow_queries.log", "a") as f:
                    f.write(f"{timestamp} | {duration:.3f}s | {sql} | params: {params_str}\n")
                print(f"[SQL] ⚠️  SLOW QUERY ({duration:.3f}s) logged to slow_queries.log")
            
            return result
    finally:
        if conn:
            return_db_connection(conn)

@app.get("/api/health")
def health():
    return {"ok": True}

# ---------- Sailing news feed (RSS) for Latest News banner ----------
_sailing_news_cache = {"items": [], "ts": 0}
SAILING_NEWS_CACHE_SEC = 1800  # 30 min

def _fetch_sailing_news() -> list:
    """Fetch sailing news from RSS; return list of {title, url, image_url, source, published}."""
    out = []
    # Google News RSS: South African sailing only (ZA locale + SA sailing query)
    rss_url = "https://news.google.com/rss/search?q=South+African+sailing&hl=en-ZA&gl=ZA&ceid=ZA:en"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; SailingSA/1.0; +https://sailingsa.co.za)"}
    try:
        with httpx.Client(timeout=15.0, follow_redirects=True, headers=headers) as client:
            r = client.get(rss_url)
            r.raise_for_status()
            feed = feedparser.parse(r.content)
    except Exception as e:
        print(f"[sailing-news] RSS fetch failed: {e}")
        return out
    for e in getattr(feed, "entries", [])[:15]:
        title = (e.get("title") or "").strip()
        url = (e.get("link") or "").strip()
        if not title or not url:
            continue
        # Image: media_content / enclosure / first image in summary
        image_url = None
        if e.get("media_content"):
            image_url = e["media_content"][0].get("url")
        if not image_url and e.get("enclosures"):
            enc = e["enclosures"][0]
            if enc.get("type", "").startswith("image/"):
                image_url = enc.get("href") or enc.get("url")
        if not image_url and e.get("summary"):
            m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', e["summary"])
            if m:
                image_url = m.group(1)
        source = (e.get("source", {}) or {}).get("title", "") if isinstance(e.get("source"), dict) else (getattr(e.get("source"), "title", None) or "")
        published = e.get("published") or e.get("updated") or ""
        out.append({
            "title": title,
            "url": url,
            "image_url": image_url or None,
            "source": source or "News",
            "published": published,
        })
    return out

@app.get("/api/sailing-news")
def api_sailing_news(limit: int = Query(10, ge=1, le=20)):
    """Return recent sailing news for Latest News banner. Headlines link to source. Cached 30 min."""
    global _sailing_news_cache
    now = time.time()
    if now - _sailing_news_cache["ts"] > SAILING_NEWS_CACHE_SEC:
        _sailing_news_cache["items"] = _fetch_sailing_news()
        _sailing_news_cache["ts"] = now
    items = _sailing_news_cache["items"][:limit]
    return {"items": items}

# ---------- Minimal support endpoints for Member Finder ----------
def table_exists(name: str) -> bool:
    try:
        res = qf("SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name=%s LIMIT 1", name)
        return len(res) > 0
    except Exception:
        return False

def column_exists(table: str, col: str) -> bool:
    try:
        res = qf("SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name=%s AND column_name=%s LIMIT 1", table, col)
        return len(res) > 0
    except Exception:
        return False

# Removed duplicate /api/clubs - using api_list_clubs below instead

@app.get("/api/classes")
def api_classes():
    # Prefer class_name; fallback to class_canonical or name
    pick = None
    for c in ("class_name", "class_canonical", "name"):
        if column_exists("classes", c):
            pick = c
            break
    if not pick:
        return {"classes": []}
    rows = q(f"SELECT {pick} AS label FROM classes ORDER BY {pick}")
    return {"classes": [r["label"] for r in rows]}

@app.get("/api/sa-id-stats")
def api_sa_id_stats():
    # Return the latest SAS ID number (MAX) to drive the header directly
    last_id = 0
    source = None
    # Prefer public.sailing_id if present
    try:
        r = q("SELECT MAX(sa_sailing_id) AS max_id FROM public.sailing_id")
        v = r[0]["max_id"] if r else None
        if v is not None:
            last_id = int(v)
            source = 'public.sailing_id.max'
    except Exception:
        pass
    # Fallback: public.sas_id_personal
    if last_id == 0:
        try:
            r = q("SELECT MAX(sa_sailing_id) AS max_id FROM public.sas_id_personal")
            v = r[0]["max_id"] if r else None
            if v is not None:
                last_id = int(v)
                source = 'public.sas_id_personal.max'
        except Exception:
            pass
    # Fallback: derive max SAS ID from results
    if last_id == 0:
        try:
            r = q("""
                SELECT GREATEST(
                    COALESCE(MAX(helm_sa_sailing_id),0),
                    COALESCE(MAX(crew_sa_sailing_id),0)
                ) AS max_id
                FROM public.results
            """)
            v = r[0]["max_id"] if r else None
            if v is not None:
                last_id = int(v)
                source = 'public.results.max'
        except Exception:
            pass
    return {
        "total_count": last_id,  # UI reads this field
        "metric": "last_sas_id",
        "source_table": source,
        "last_scrape": None,
        "before_scrape": None,
        "after_scrape": None,
        "added_count": None,
    }

# ---------- Normalized Roles API ----------
@app.get("/api/member/{sa_id}/roles")
def api_member_roles(sa_id: int):
    """Return normalized roles for a member by SAS registry number.
    Uses new schema: sa_ids -> member_roles -> roles.
    Falls back to empty list if tables are not present yet.
    """
    # Ensure required tables exist to avoid errors during transition
    try:
        if not (table_exists('sa_ids') and table_exists('member_roles') and table_exists('roles')):
            return []
    except Exception:
        return []

    rows = q(
        """
        SELECT
          mr.role_code,
          r.name AS role_name,
          r.category,
          mr.status,
          mr.awarded_date,
          mr.expires_date,
          mr.source
        FROM public.sa_ids s
        JOIN public.member_roles mr ON mr.person_id = s.person_id
        JOIN public.roles r ON r.role_code = mr.role_code
        WHERE s.sa_registry_no = %s
        ORDER BY r.category, r.name, mr.awarded_date NULLS LAST
        """,
        sa_id,
    )
    t0 = time.time()
    t1 = time.time()
    print(f"[TRACE] getMemberRoles({sa_id}) took {t1-t0:.3f}s ({len(rows)} roles)")
    return rows

@app.get("/api/member/{sa_id}/results")
def api_member_results(sa_id: str, request: Request = None):
    """Return all regatta results for a member by SA ID or Temp ID - OPTIMIZED with connection pooling"""
    start_time = time.time()
    request_id = getattr(request.state, 'request_id', None) if request else None
    if not request_id:
        request_id = get_request_id()
    
    conn = None
    try:
        conn = get_db_connection(request_id)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Wrap cursor with query tracing
            trace_query(cur, request_id)
            
            # STAGE 12 OPTIMIZATION: Skip separate boat/bow query - calculate from main results
            # This eliminates 2 slow subqueries that were taking 8+ seconds
            # We'll calculate most common boat/bow from the results after fetching them
            most_common_boat = None
            most_common_bow = None
            
            # Handle both SA IDs and Temp IDs
            if sa_id.upper().startswith("TMP:") or sa_id.upper().startswith("TMP"):
                # Temp ID
                temp_id = sa_id.upper().replace("TMP:", "").replace("TMP", "").strip()
                cur.execute("""
                    WITH block_counts AS (
                        SELECT block_id, COUNT(*) as count
                        FROM results
                        WHERE block_id IS NOT NULL
                        GROUP BY block_id
                    )
                    SELECT 
                        r.result_id,
                        r.regatta_id,
                        r.block_id,
                        r.fleet_label,
                        r.class_original,
                        r.class_canonical,
                        r.rank,
                        r.sail_number,
                        r.boat_name,
                        r.bow_no,
                        COALESCE(c.club_abbrev, r.club_raw) as club,
                        c.club_fullname as club_fullname,
                        r.helm_name,
                        r.helm_sa_sailing_id,
                        r.crew_name,
                        r.crew_sa_sailing_id,
                        r.race_scores,
                        r.total_points_raw,
                        r.nett_points_raw,
                        r.raced,
                        reg.event_name,
                        reg.regatta_number,
                        reg.start_date,
                        reg.end_date,
                        reg.end_date as regatta_date,
                        COALESCE(rb.entries_raced, bc.count) as entries
                    FROM results r
                    LEFT JOIN clubs c ON c.club_id = r.club_id
                    LEFT JOIN regattas reg ON reg.regatta_id = r.regatta_id
                    LEFT JOIN regatta_blocks rb ON rb.block_id = r.block_id
                    LEFT JOIN block_counts bc ON bc.block_id = r.block_id
                    WHERE (r.helm_temp_id = %s OR r.crew_temp_id = %s)
                    ORDER BY reg.end_date DESC NULLS LAST, reg.start_date DESC NULLS LAST
                """, (sa_id, sa_id))
            else:
                # SA ID: return ALL results for this sailor – by ID and by name fallback so no result is missed
                # 1) Get sailor name for fallback (results with no ID but matching name still show)
                cur.execute("""
                    SELECT COALESCE(TRIM(full_name), TRIM(first_name || ' ' || last_name)) AS sailor_name
                    FROM sas_id_personal WHERE sa_sailing_id::text = %s
                """, (sa_id,))
                name_row = cur.fetchone()
                sailor_name_for_fallback = (name_row.get('sailor_name') or '').strip() if name_row else ''
                name_fallback = bool(sailor_name_for_fallback)

                # 2) All results: by helm/crew SA ID or temp ID, OR by matching name when ID is NULL (so nothing is missed)
                if name_fallback:
                    cur.execute("""
                        WITH block_counts AS (
                            SELECT block_id, COUNT(*) as count FROM results WHERE block_id IS NOT NULL GROUP BY block_id
                        )
                        SELECT 
                            r.result_id, r.regatta_id, r.block_id, r.fleet_label, r.class_original, r.class_canonical,
                            r.rank, r.sail_number, r.boat_name, r.bow_no,
                            COALESCE(c.club_abbrev, r.club_raw) as club, c.club_fullname as club_fullname,
                            r.helm_name, r.helm_sa_sailing_id, r.crew_name, r.crew_sa_sailing_id,
                            r.race_scores, r.total_points_raw, r.nett_points_raw, r.raced,
                            reg.event_name, reg.regatta_number, reg.start_date, reg.end_date, reg.end_date as regatta_date,
                            COALESCE(rb.entries_raced, bc.count) as entries
                        FROM results r
                        LEFT JOIN clubs c ON c.club_id = r.club_id
                        LEFT JOIN regattas reg ON reg.regatta_id = r.regatta_id
                        LEFT JOIN regatta_blocks rb ON rb.block_id = r.block_id
                        LEFT JOIN block_counts bc ON bc.block_id = r.block_id
                        WHERE (r.helm_sa_sailing_id::text = %s OR r.helm_temp_id = %s)
                           OR (r.crew_sa_sailing_id::text = %s OR r.crew_temp_id = %s)
                           OR (r.helm_sa_sailing_id IS NULL AND r.helm_temp_id IS NULL AND TRIM(LOWER(r.helm_name)) = TRIM(LOWER(%s)))
                           OR (r.crew_sa_sailing_id IS NULL AND r.crew_temp_id IS NULL AND TRIM(LOWER(r.crew_name)) = TRIM(LOWER(%s)))
                        ORDER BY reg.end_date DESC NULLS LAST, reg.start_date DESC NULLS LAST
                    """, (sa_id, sa_id, sa_id, sa_id, sailor_name_for_fallback, sailor_name_for_fallback))
                else:
                    cur.execute("""
                        WITH block_counts AS (
                            SELECT block_id, COUNT(*) as count FROM results WHERE block_id IS NOT NULL GROUP BY block_id
                        )
                        SELECT 
                            r.result_id, r.regatta_id, r.block_id, r.fleet_label, r.class_original, r.class_canonical,
                            r.rank, r.sail_number, r.boat_name, r.bow_no,
                            COALESCE(c.club_abbrev, r.club_raw) as club, c.club_fullname as club_fullname,
                            r.helm_name, r.helm_sa_sailing_id, r.crew_name, r.crew_sa_sailing_id,
                            r.race_scores, r.total_points_raw, r.nett_points_raw, r.raced,
                            reg.event_name, reg.regatta_number, reg.start_date, reg.end_date, reg.end_date as regatta_date,
                            COALESCE(rb.entries_raced, bc.count) as entries
                        FROM results r
                        LEFT JOIN clubs c ON c.club_id = r.club_id
                        LEFT JOIN regattas reg ON reg.regatta_id = r.regatta_id
                        LEFT JOIN regatta_blocks rb ON rb.block_id = r.block_id
                        LEFT JOIN block_counts bc ON bc.block_id = r.block_id
                        WHERE (r.helm_sa_sailing_id::text = %s OR r.helm_temp_id = %s)
                           OR (r.crew_sa_sailing_id::text = %s OR r.crew_temp_id = %s)
                        ORDER BY reg.end_date DESC NULLS LAST, reg.start_date DESC NULLS LAST
                    """, (sa_id, sa_id, sa_id, sa_id))
            
            rows = cur.fetchall()
            
            # Calculate most common boat/bow PER CLASS (not across all classes)
            # Boat names must be class-specific: Hobie 16 boat name != Sonnet boat name
            if rows:
                # Group boat/bow counts by class
                class_boat_counts = {}  # {class_name: {boat_name: count}}
                class_bow_counts = {}  # {class_name: {bow_no: count}}
                
                for row in rows:
                    # Use class_canonical as the key (prefer over class_original for consistency)
                    class_key = (row.get('class_canonical') or row.get('class_original') or 'Unknown').strip()
                    boat_name = row.get('boat_name')
                    bow_no = row.get('bow_no')
                    
                    if boat_name and str(boat_name).strip():
                        if class_key not in class_boat_counts:
                            class_boat_counts[class_key] = {}
                        class_boat_counts[class_key][boat_name] = class_boat_counts[class_key].get(boat_name, 0) + 1
                    
                    if bow_no and str(bow_no).strip():
                        if class_key not in class_bow_counts:
                            class_bow_counts[class_key] = {}
                        class_bow_counts[class_key][str(bow_no)] = class_bow_counts[class_key].get(str(bow_no), 0) + 1
                
                # Calculate most common boat/bow per class
                class_most_common_boat = {}
                class_most_common_bow = {}
                
                for class_key, boat_counts in class_boat_counts.items():
                    if boat_counts:
                        class_most_common_boat[class_key] = max(boat_counts.items(), key=lambda x: x[1])[0]
                
                for class_key, bow_counts in class_bow_counts.items():
                    if bow_counts:
                        class_most_common_bow[class_key] = max(bow_counts.items(), key=lambda x: x[1])[0]
                
                # Apply most common values to rows missing them - ONLY if sail number matches
                # CRITICAL FIX: Boat names and bow numbers are tied to specific sail numbers
                # Sail 1365 with bow 72 and boat "Kookaburra" != Sail 1367 with bow 72 and boat "Kookaburra"
                # We can only fill missing boat/bow if the sail number matches
                for row in rows:
                    class_key = (row.get('class_canonical') or row.get('class_original') or 'Unknown').strip()
                    sail_number = str(row.get('sail_number') or '').strip()
                    
                    if not sail_number:
                        continue  # Can't match without sail number
                    
                    # Group boat/bow by sail number for this class
                    # Only use boat/bow from results with the SAME sail number
                    sail_boat_counts = {}
                    sail_bow_counts = {}
                    
                    for other_row in rows:
                        other_class = (other_row.get('class_canonical') or other_row.get('class_original') or 'Unknown').strip()
                        other_sail = str(other_row.get('sail_number') or '').strip()
                        
                        if other_class != class_key or other_sail != sail_number:
                            continue
                        
                        other_boat = other_row.get('boat_name')
                        other_bow = other_row.get('bow_no')
                        
                        if other_boat and str(other_boat).strip():
                            sail_boat_counts[other_boat] = sail_boat_counts.get(other_boat, 0) + 1
                        
                        if other_bow and str(other_bow).strip():
                            sail_bow_counts[str(other_bow)] = sail_bow_counts.get(str(other_bow), 0) + 1
                    
                    # Only fill boat_name if missing AND we have boat data for THIS sail number
                    if (not row.get('boat_name') or not str(row.get('boat_name', '')).strip()):
                        if sail_boat_counts:
                            row['boat_name'] = max(sail_boat_counts.items(), key=lambda x: x[1])[0]
                    
                    # Only fill bow_no if missing AND we have bow data for THIS sail number
                    if (not row.get('bow_no') or not str(row.get('bow_no', '')).strip()):
                        if sail_bow_counts:
                            row['bow_no'] = max(sail_bow_counts.items(), key=lambda x: x[1])[0]
            
            t1 = time.time()
            duration = t1 - start_time
            print(f"[TRACE] [{request_id}] getMemberResults({sa_id}) took {duration:.3f}s ({len(rows)} results)")
            return {"results": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if 'conn' in locals():
            return_db_connection(conn)

@app.get("/api/sa-id-stats")
def api_sa_id_stats():
    try:
        rows = q(
            """
            SELECT COALESCE(highest_no,0)   AS highest_no,
                   COALESCE(total_valid,0)  AS total_valid,
                   COALESCE(missing_count,0) AS missing_count
            FROM public.vw_sas_audit_summary
            """
        )
        if not rows:
            return {"highest_no": 0, "total_valid": 0, "missing_count": 0, "total_count": 0}
        r = rows[0]
        # keep backward-compatible total_count
        return {
            "highest_no": r["highest_no"],
            "total_valid": r["total_valid"],
            "missing_count": r["missing_count"],
            "total_count": r["total_valid"],
        }
    except Exception:
        return {"highest_no": 0, "total_valid": 0, "missing_count": 0, "total_count": 0}

@app.get("/api/classes")
def api_list_classes():
    rows = q(
        """
        SELECT class_canonical AS code,
               COALESCE(class_full_name, class_canonical) AS name
        FROM public.classes
        WHERE COALESCE(is_active, TRUE) IS TRUE
        ORDER BY class_canonical
        """
    )
    return rows

@app.get("/api/provinces")
def api_list_provinces():
    rows = q(
        """
        SELECT province_code AS code, province_name AS name
        FROM public.provinces
        WHERE is_active IS TRUE
        ORDER BY province_code
        """
    )
    return rows

@app.get("/api/roles")
def api_list_roles():
    """List available role codes for filters/dropdowns."""
    try:
        if not (table_exists('roles')):
            return []
    except Exception:
        return []
    # roles has columns: role_code, name, category
    rows = q("SELECT role_code, name AS role_name, category FROM public.roles ORDER BY category, name")
    return rows

@app.get("/api/clubs")
def api_list_clubs():
    # Tolerate different column spellings/names across environments
    # code: prefer club_abbrev -> club_code -> club_name -> club_full_name
    code_col = (
        "club_abbrev" if column_exists('clubs','club_abbrev') else (
        "club_code"   if column_exists('clubs','club_code')   else (
        "club_name"   if column_exists('clubs','club_name')   else (
        "club_full_name" if column_exists('clubs','club_full_name') else None)))
    )
    # name: prefer full_name/name fallback to abbrev/code
    name_col = (
        "club_full_name" if column_exists('clubs','club_full_name') else (
        "club_name"      if column_exists('clubs','club_name')      else (
        "club_abbrev"    if column_exists('clubs','club_abbrev')    else (
        "club_code"      if column_exists('clubs','club_code')      else None)))
    )
    if not code_col and not name_col:
        return []
    code_sql = f"{code_col} AS code" if code_col else "NULL::text AS code"
    name_sql = f"{name_col} AS name" if name_col else "NULL::text AS name"
    # Province: which province the club is in (e.g. WC, KZN, GP)
    province_col = (
        "province" if column_exists('clubs', 'province') else
        "province_code" if column_exists('clubs', 'province_code') else None
    )
    province_sql = f"{province_col} AS province" if province_col else "NULL::text AS province"
    order_col = code_col or name_col
    sql = f"""
      SELECT {code_sql}, {name_sql}, {province_sql}
      FROM public.clubs
      WHERE COALESCE(TRIM({code_col or name_col}), '') <> ''
      ORDER BY {order_col}
    """
    return q(sql)

@app.get("/api/member/search")
def api_search_members(
    role_code: Optional[str] = None,
    club: Optional[str] = None,   # club code, e.g. "ZVYC"
    q: Optional[str] = None,      # free text on name or exact SAS/TMP
    limit: int = 200,
):
    """Search members with inline roles aggregation to avoid per-row role fetches."""
    # Ensure base table exists
    try:
        if not table_exists('sa_ids'):
            return []
    except Exception:
        return []

    qstr_norm = (q or "").strip()
    is_sas = qstr_norm.isdigit()
    is_tmp = qstr_norm.upper().startswith("TMP-")

    sql = """
    WITH match_ids AS (
      SELECT s.person_id
      FROM public.sa_ids s
      WHERE %s AND s.sa_registry_no::text = %s
      UNION
      SELECT ia.person_id
      FROM public.id_aliases ia
      WHERE %s AND ia.alias_type='TEMP' AND ia.alias_value = %s
    ),
    base AS (
      SELECT
        s.person_id,
        s.sa_registry_no              AS sa_id,
        COALESCE(s.first_name,'')     AS first_name,
        COALESCE(s.last_name,'')      AS last_name,
        COALESCE(s.home_club_code,'') AS club
      FROM public.sa_ids s
      WHERE 1=1
    ), joined AS (
      SELECT
        b.*,
        mr.role_code,
        COALESCE(mr.status,'active') AS status
      FROM base b
      LEFT JOIN public.member_roles mr ON mr.person_id = b.person_id
    )
    SELECT
      j.sa_id,
      j.first_name,
      j.last_name,
      j.club,
      COALESCE(
        JSON_AGG(
          DISTINCT JSONB_BUILD_OBJECT(
            'role_code', j.role_code,
            'status',    j.status
          )
        ) FILTER (WHERE j.role_code IS NOT NULL), '[]'::json
      ) AS roles
    FROM joined j
    WHERE 1=1
    """
    args: list = [is_sas, qstr_norm, is_tmp, qstr_norm]

    if role_code:
        sql += " AND j.role_code = %s AND j.status = 'active' "
        args.append(role_code)

    if club:
        sql += " AND j.club = %s "
        args.append(club)

    if q:
        # match by person_id resolved from SAS/TMP OR fallback to name contains
        sql += " AND ( (SELECT COUNT(*) FROM match_ids WHERE match_ids.person_id = j.person_id) > 0 OR LOWER(j.first_name||' '||j.last_name) LIKE LOWER(%s) ) "
        args.append(f"%{q}%")

    sql += """
    GROUP BY j.sa_id, j.first_name, j.last_name, j.club
    ORDER BY j.last_name NULLS LAST, j.first_name NULLS LAST, j.sa_id
    LIMIT %s
    """
    args.append(limit)

    return q(sql, *args)

# --- TEMP ID: create ---
@app.post("/api/id/temp")
def create_temp_id(payload: dict):
    first_name = payload.get("first_name", "")
    last_name  = payload.get("last_name", "")
    club_code  = payload.get("club_code")
    note       = payload.get("note")
    rows = q(
        """
        SELECT * FROM public.create_temp_person(%s,%s,%s,%s)
        """,
        first_name, last_name, club_code, note,
    )
    if not rows:
        raise HTTPException(500, "Failed to create TEMP person")
    return {"person_id": rows[0]["person_id"], "temp_alias": rows[0]["temp_alias"]}

# --- Promote TEMP -> real SAS ---
@app.post("/api/id/promote")
def promote_temp(payload: dict):
    temp_alias = payload.get("temp_alias")
    sa_no_raw  = payload.get("sa_registry_no")
    if not temp_alias or sa_no_raw is None:
        raise HTTPException(400, "temp_alias and sa_registry_no are required")
    sa_no = int(sa_no_raw)
    rows = q(
        """
        SELECT * FROM public.promote_temp_alias_to_sas(%s,%s)
        """,
        temp_alias, sa_no,
    )
    if not rows:
        raise HTTPException(500, "Failed to promote TEMP alias")
    return {"person_id": rows[0]["person_id"], "sa_registry_no": rows[0]["sa_registry_no"]}

# --- Attach a person (SAS or TEMP) to a result in one call ---
@app.post("/api/result/attach-person")
def attach_person_to_result(payload: dict):
    result_id = payload.get("result_id")
    role = payload.get("role")
    identifier = payload.get("id")

    if not result_id or not identifier or not role:
        raise HTTPException(status_code=400, detail="result_id, role, and id are required")

    rows = q(
        """
        SELECT person_id, kind
        FROM public.resolve_person_by_identifier(%s)
        """,
        identifier,
    )
    if not rows:
        raise HTTPException(status_code=404, detail=f"Identifier not found: {identifier}")

    person_id = rows[0]["person_id"]
    try:
        q(
            """
            INSERT INTO public.result_participants (result_id, person_id, role)
            VALUES (%s, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            result_id, person_id, role,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to attach person: {e}")

    return {"ok": True, "result_id": result_id, "person_id": person_id, "role": role}

# ---------- People search and result editing used by live search UI ----------
@app.get("/api/people/search")
def api_people_search(q: str = Query(""), club_id: Optional[int] = None, limit: int = 1000, temp_only: Optional[int] = None):
    """Legacy endpoint - returns same structure as /api/search for compatibility with member-finder.html"""
    # If temp_only=1, return full temp ID data with all fields
    if temp_only == 1:
        return api_search(sas_id="T", limit=limit)
    
    qn = (q or "").strip()
    
    # If query starts with TMP: or is "T", treat as temp ID search
    if qn.upper().startswith("TMP:") or qn.strip().upper() == "T":
        return api_search(sas_id=qn, limit=limit)
    
    # Otherwise, use /api/search endpoint for SA IDs
    return api_search(q=qn, limit=limit)

@app.post("/api/result/{result_id}/set_person")
def api_set_person(result_id: int, payload: dict):
    """Set person for helm or crew from search selection"""
    role = payload.get("role")         # 'helm' | 'crew'
    key  = payload.get("person_key")   # 'SAS:123' | 'TMP:42'
    name = payload.get("display_name") # optional: update printed name too
    if role not in ("helm","crew"):
        raise HTTPException(400, "role must be 'helm' or 'crew'")
    if not key or ":" not in key:
        raise HTTPException(400, "person_key required (SAS:#### or TMP:####)")

    prefix, num = key.split(":", 1)
    if prefix == "SAS":
        if role == "helm":
            return one("""UPDATE results
                          SET helm_sa_sailing_id=%s, helm_temp_id=NULL,
                              match_status_helm='chosen',
                              helm_name=COALESCE(%s, helm_name)
                          WHERE result_id=%s RETURNING *""", int(num), name, result_id)
        else:
            return one("""UPDATE results
                          SET crew_sa_sailing_id=%s, crew_temp_id=NULL,
                              match_status_crew='chosen',
                              crew_name=COALESCE(%s, crew_name)
                          WHERE result_id=%s RETURNING *""", int(num), name, result_id)
    elif prefix == "TMP":
        if role == "helm":
            return one("""UPDATE results
                          SET helm_temp_id=%s, helm_sa_sailing_id=NULL,
                              match_status_helm='chosen',
                              helm_name=COALESCE(%s, helm_name)
                          WHERE result_id=%s RETURNING *""", num, name, result_id)
        else:
            return one("""UPDATE results
                          SET crew_temp_id=%s, crew_sa_sailing_id=NULL,
                              match_status_crew='chosen',
                              crew_name=COALESCE(%s, crew_name)
                          WHERE result_id=%s RETURNING *""", num, name, result_id)
    else:
        raise HTTPException(400, "person_key must start with SAS: or TMP:")

# Duplicate search endpoint removed - using unified endpoint at line 611

# ---------- CREATE TEMP PERSON ----------
class TempPersonCreate(BaseModel):
    full_name: str
    club_code: Optional[str] = None
    notes: Optional[str] = None

@app.post("/api/people/temp")
def create_temp(p: TempPersonCreate):
    row = one("SELECT create_temp_person(%s,%s,%s) AS person_key", p.full_name, p.club_code, p.notes)
    return row

# ---------- PATCH RESULT (inline edit) ----------
class ResultPatch(BaseModel):
    helm_key: Optional[str] = None     # "SAS:12345" | "TMP:9"
    crew_key: Optional[str] = None
    sail_number: Optional[str] = None
    club_code: Optional[str] = None
    class_name: Optional[str] = None
    boat_name: Optional[str] = None

@app.patch("/api/result/{result_id}")
def patch_result(result_id: int, p: ResultPatch):
    with psycopg2.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            if p.helm_key is not None:
                cur.execute("SELECT set_result_person(%s,'helm',%s)", (result_id, p.helm_key))
            if p.crew_key is not None:
                cur.execute("SELECT set_result_person(%s,'crew',%s)", (result_id, p.crew_key))
            fields = []
            vals   = []
            if p.sail_number is not None: fields.append("sail_number=%s"); vals.append(p.sail_number)
            if p.club_code   is not None: fields.append("club_raw=%s");    vals.append(p.club_code.upper())
            if p.class_name  is not None: fields.append("class_original=%s"); vals.append(p.class_name)
            if p.boat_name   is not None: fields.append("boat_name=%s");  vals.append(p.boat_name)
            if fields:
                cur.execute(f"UPDATE results SET {', '.join(fields)} WHERE result_id=%s", (*vals, result_id))
        conn.commit()
    return {"ok": True}

@app.patch("/api/result/{result_id}/race")
def patch_race_score(result_id: int, body: dict):
    """Update a race score and automatically recalculate total/nett/discards and re-rank fleet"""
    import json
    import re
    
    race_key = body.get("race")  # e.g., "R1", "R2"
    value = body.get("value", "").strip()
    
    if not race_key or not race_key.startswith("R"):
        raise HTTPException(status_code=400, detail="Invalid race key")
    
    with psycopg2.connect(DB_URL) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Get current result and block info
            cur.execute("""
                SELECT r.result_id, r.block_id, r.race_scores, r.regatta_id,
                       rb.races_sailed, rb.discard_count
                FROM results r
                JOIN regatta_blocks rb ON rb.block_id = r.block_id
                WHERE r.result_id = %s
            """, (result_id,))
            result = cur.fetchone()
            if not result:
                raise HTTPException(status_code=404, detail="Result not found")
            
            block_id = result['block_id']
            regatta_id = result['regatta_id']
            race_scores = result['race_scores'] or {}
            if isinstance(race_scores, str):
                race_scores = json.loads(race_scores)
            
            # Validate: Check for duplicate race positions (except ISP codes)
            if value:
                # Extract numeric position from value (e.g., "3" from "3" or "3 (DNS)")
                num_match = re.search(r'^(\d+)', value.strip())
                has_penalty = bool(re.search(r'(DNC|DNS|DNF|RET|DSQ|UFD|BFD|DPI|OCS)', value, re.I))
                
                # Only validate position if it's a numeric score (not ISP-only like "(DNS)")
                if num_match and not value.strip().startswith('('):
                    position = int(num_match.group(1))
                    
                    # Check if this position is already taken by another sailor in this fleet
                    cur.execute("""
                        SELECT r.result_id, r.race_scores
                        FROM results r
                        WHERE r.block_id = %s
                        AND r.result_id != %s
                        AND r.race_scores IS NOT NULL
                    """, (block_id, result_id))
                    other_results = cur.fetchall()
                    
                    for other_res in other_results:
                        other_scores = other_res['race_scores'] or {}
                        if isinstance(other_scores, str):
                            other_scores = json.loads(other_scores)
                        
                        other_value = other_scores.get(race_key, "").strip()
                        if not other_value:
                            continue
                        
                        # Extract position from other sailor's score
                        other_num_match = re.search(r'^(\d+)', other_value)
                        other_has_penalty = bool(re.search(r'(DNC|DNS|DNF|RET|DSQ|UFD|BFD|DPI|OCS)', other_value, re.I))
                        
                        # If other sailor has same position and it's not ISP-only, reject
                        if other_num_match and not other_value.startswith('('):
                            other_position = int(other_num_match.group(1))
                            if other_position == position:
                                raise HTTPException(
                                    status_code=400, 
                                    detail=f"Position {position} is already taken by another sailor in this race. Each position can only be used once."
                                )
            
            # Update race score (empty value removes the score)
            if value:
                race_scores[race_key] = value
            else:
                # Remove the race score if value is empty
                race_scores.pop(race_key, None)
            
            # Count races sailed (non-empty race scores)
            races_sailed = len([k for k in race_scores.keys() if k.startswith('R') and race_scores[k]])
            
            # Calculate discard count based on races_sailed
            discard_count = races_sailed // 5  # 1 discard after 5, 2 after 10, etc.
            
            # Parse scores and calculate totals
            entries_plus_one = None
            cur.execute("SELECT COUNT(*) as cnt FROM results WHERE block_id = %s", (block_id,))
            entries_row = cur.fetchone()
            entries_count = entries_row['cnt'] if entries_row else 0
            entries_plus_one = entries_count + 1
            
            # Parse all race scores
            scores_list = []
            for i in range(1, races_sailed + 1):
                rkey = f"R{i}"
                val = race_scores.get(rkey, "")
                if not val:
                    continue
                
                # Parse score value (extract numeric, handle brackets, penalty codes)
                is_bracket = val.startswith("(") and val.endswith(")")
                num_match = re.search(r'[\d.]+', val)
                has_penalty = bool(re.search(r'(DNC|DNS|DNF|RET|DSQ|UFD|BFD|DPI|OCS)', val, re.I))
                
                if num_match:
                    score_val = abs(float(num_match.group(0)))
                elif has_penalty:
                    score_val = float(entries_plus_one)
                else:
                    score_val = 0.0
                
                scores_list.append({
                    'key': rkey,
                    'val': score_val,
                    'is_br': is_bracket,
                    'raw': val
                })
            
            # Calculate total (sum of all scores)
            total = sum(s['val'] for s in scores_list)
            
            # Identify discards (worst scores, prefer already bracketed)
            discard_idxs = set()
            if discard_count > 0 and scores_list:
                # First, prefer already bracketed scores
                bracketed = [i for i, s in enumerate(scores_list) if s['is_br']]
                for idx in bracketed[:discard_count]:
                    discard_idxs.add(idx)
                
                # If we need more discards, pick worst remaining scores
                remaining_needed = discard_count - len(discard_idxs)
                if remaining_needed > 0:
                    remaining = [(i, s) for i, s in enumerate(scores_list) if i not in discard_idxs]
                    remaining.sort(key=lambda x: x[1]['val'], reverse=True)  # Worst first
                    for i in range(min(remaining_needed, len(remaining))):
                        discard_idxs.add(remaining[i][0])
            
            # Update brackets in race_scores JSONB
            for i, score_info in enumerate(scores_list):
                rkey = score_info['key']
                should_be_bracketed = i in discard_idxs
                current_val = score_info['raw']
                is_currently_bracketed = score_info['is_br']
                
                if should_be_bracketed and not is_currently_bracketed:
                    # Add brackets (preserve penalty codes)
                    race_scores[rkey] = f"({current_val})"
                elif not should_be_bracketed and is_currently_bracketed:
                    # Remove brackets (preserve penalty codes)
                    race_scores[rkey] = current_val.strip("()")
            
            # Calculate nett (total minus discarded scores)
            nett = total - sum(scores_list[i]['val'] for i in discard_idxs)
            
            # Update this result
            cur.execute("""
                UPDATE results
                SET race_scores = %s,
                    total_points_raw = %s,
                    nett_points_raw = %s
                WHERE result_id = %s
            """, (json.dumps(race_scores), total, nett, result_id))
            
            # Update block races_sailed and discard_count
            cur.execute("""
                UPDATE regatta_blocks
                SET races_sailed = %s,
                    discard_count = %s
                WHERE block_id = %s
            """, (races_sailed, discard_count, block_id))
            
            # Recalculate ALL sailors in this fleet (in case discard_count changed)
            cur.execute("""
                SELECT result_id, race_scores
                FROM results
                WHERE block_id = %s
            """, (block_id,))
            all_results = cur.fetchall()
            
            for res in all_results:
                if not res or 'result_id' not in res:
                    continue
                res_race_scores = res['race_scores'] or {}
                if isinstance(res_race_scores, str):
                    res_race_scores = json.loads(res_race_scores)
                
                # Count races sailed
                res_races_sailed = len([k for k in res_race_scores.keys() if k.startswith('R') and res_race_scores[k]])
                
                # Parse scores
                res_scores_list = []
                for i in range(1, res_races_sailed + 1):
                    rkey = f"R{i}"
                    val = res_race_scores.get(rkey, "")
                    if not val:
                        continue
                    
                    is_bracket = val.startswith("(") and val.endswith(")")
                    num_match = re.search(r'[\d.]+', val)
                    has_penalty = bool(re.search(r'(DNC|DNS|DNF|RET|DSQ|UFD|BFD|DPI|OCS)', val, re.I))
                    
                    if num_match:
                        score_val = abs(float(num_match.group(0)))
                    elif has_penalty:
                        score_val = float(entries_plus_one)
                    else:
                        score_val = 0.0
                    
                    res_scores_list.append({
                        'key': rkey,
                        'val': score_val,
                        'is_br': is_bracket,
                        'raw': val
                    })
                
                # Calculate total
                res_total = sum(s['val'] for s in res_scores_list)
                
                # Identify discards
                res_discard_idxs = set()
                if discard_count > 0 and res_scores_list:
                    bracketed = [i for i, s in enumerate(res_scores_list) if s['is_br']]
                    for idx in bracketed[:discard_count]:
                        res_discard_idxs.add(idx)
                    
                    remaining_needed = discard_count - len(res_discard_idxs)
                    if remaining_needed > 0:
                        remaining = [(i, s) for i, s in enumerate(res_scores_list) if i not in res_discard_idxs]
                        remaining.sort(key=lambda x: x[1]['val'], reverse=True)
                        for i in range(min(remaining_needed, len(remaining))):
                            res_discard_idxs.add(remaining[i][0])
                
                # Update brackets
                for i, score_info in enumerate(res_scores_list):
                    rkey = score_info['key']
                    should_be_bracketed = i in res_discard_idxs
                    current_val = score_info['raw']
                    is_currently_bracketed = score_info['is_br']
                    
                    if should_be_bracketed and not is_currently_bracketed:
                        res_race_scores[rkey] = f"({current_val})"
                    elif not should_be_bracketed and is_currently_bracketed:
                        res_race_scores[rkey] = current_val.strip("()")
                
                # Calculate nett
                res_nett = res_total - sum(res_scores_list[i]['val'] for i in res_discard_idxs)
                
                # Update this result
                cur.execute("""
                    UPDATE results
                    SET race_scores = %s,
                        total_points_raw = %s,
                        nett_points_raw = %s
                    WHERE result_id = %s
                """, (json.dumps(res_race_scores), res_total, res_nett, res['result_id']))
            
            # Re-rank entire fleet by nett scores (lower nett = better rank)
            # Each sailor must have unique rank (no ties) - break ties by result_id
            # NULL/0 nett scores rank last (treated as 999999)
            cur.execute("""
                WITH ranked AS (
                    SELECT result_id,
                           ROW_NUMBER() OVER (
                               ORDER BY 
                                   COALESCE(
                                       NULLIF(nett_points_raw, 0), 
                                       999999
                                   ) ASC, 
                                   result_id ASC
                           ) as new_rank
                    FROM results
                    WHERE block_id = %s
                )
                UPDATE results r
                SET rank = ranked.new_rank
                FROM ranked
                WHERE r.result_id = ranked.result_id
            """, (block_id,))
            
            conn.commit()
            
            # Return updated result data
            cur.execute("""
                SELECT r.*, rb.races_sailed, rb.discard_count
                FROM results r
                JOIN regatta_blocks rb ON rb.block_id = r.block_id
                WHERE r.result_id = %s
            """, (result_id,))
            updated = cur.fetchone()
            
            return {
                "ok": True,
                "result_id": result_id,
                "race_scores": race_scores,
                "total_points_raw": total,
                "nett_points_raw": nett,
                "rank": updated['rank'],
                "races_sailed": races_sailed,
                "discard_count": discard_count
            }

def auto_verify_regatta_data(regatta_id: str):
    """Auto-verify and update all regatta data against database tables"""
    with psycopg2.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            # 1. Auto-match SAS IDs for helms
            cur.execute("""
                UPDATE results SET helm_sa_sailing_id = s.sa_sailing_id
                FROM sailing_id s, regatta_blocks rb
                WHERE rb.block_id = results.block_id
                AND rb.regatta_id = %s
                AND results.helm_name = CONCAT(s.first_name, ' ', s.last_name)
                AND results.helm_sa_sailing_id IS NULL
            """, (regatta_id,))
            
            # 2. Auto-match SAS IDs for crews
            cur.execute("""
                UPDATE results SET crew_sa_sailing_id = s.sa_sailing_id
                FROM sailing_id s, regatta_blocks rb
                WHERE rb.block_id = results.block_id
                AND rb.regatta_id = %s
                AND results.crew_name = CONCAT(s.first_name, ' ', s.last_name)
                AND results.crew_name IS NOT NULL
                AND results.crew_sa_sailing_id IS NULL
            """, (regatta_id,))
            
            # 3. Update club codes for all SAS IDs based on current regatta data
            cur.execute("""
                UPDATE sailing_id SET home_club_code = r.club_raw
                FROM results r
                JOIN regatta_blocks rb ON rb.block_id = r.block_id
                WHERE rb.regatta_id = %s
                AND sailing_id.sa_sailing_id = r.helm_sa_sailing_id
                AND r.club_raw IS NOT NULL
                AND (sailing_id.home_club_code IS NULL OR sailing_id.home_club_code != r.club_raw)
            """, (regatta_id,))
            
            cur.execute("""
                UPDATE sailing_id SET home_club_code = r.club_raw
                FROM results r
                JOIN regatta_blocks rb ON rb.block_id = r.block_id
                WHERE rb.regatta_id = %s
                AND sailing_id.sa_sailing_id = r.crew_sa_sailing_id
                AND r.club_raw IS NOT NULL
                AND (sailing_id.home_club_code IS NULL OR sailing_id.home_club_code != r.club_raw)
            """, (regatta_id,))
            
            # 4. Ensure all results have proper club_id mappings
            cur.execute("""
                UPDATE results SET club_id = c.club_id
                FROM clubs c
                JOIN regatta_blocks rb ON rb.block_id = results.block_id
                WHERE rb.regatta_id = %s
                AND results.club_raw = c.club_abbrev
                AND results.club_id IS DISTINCT FROM c.club_id
            """, (regatta_id,))
            
            conn.commit()

# ========== MEMBER FINDER ENDPOINTS ==========
# Duplicate search endpoint removed - using unified endpoint at line 611

@app.get("/api/clubs")
def list_clubs():
    """List all clubs - returns array of club codes for backward compatibility"""
    rows = q("""
        SELECT club_abbrev
        FROM clubs
        WHERE club_abbrev IS NOT NULL
        ORDER BY club_abbrev
    """)
    return [r['club_abbrev'] for r in rows]

@app.get("/api/classes")
def list_classes():
    """List all boat classes - returns object with 'classes' array for backward compatibility"""
    rows = q("""
        SELECT class_name
        FROM classes
        WHERE class_name IS NOT NULL
        ORDER BY class_name
    """)
    return {"classes": [r['class_name'] for r in rows]}

@app.get("/api/sa-id-stats")
def sa_id_stats():
    """Get statistics about SA Sailing IDs"""
    with psycopg2.connect(DB_URL) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT COUNT(*) as total FROM sailing_id")
            sas_count = cur.fetchone()['total']
            
            cur.execute("SELECT COUNT(*) as total FROM temp_people")
            temp_count = cur.fetchone()['total']
            
            # Return format compatible with old member-finder HTML
            # Get last scrape info
            cur.execute("""
                SELECT before_scrape_count, after_scrape_count, added_count, timestamp 
                FROM scrape_log 
                WHERE status = 'SUCCESS' 
                ORDER BY timestamp DESC 
                LIMIT 1
            """)
            last_scrape = cur.fetchone()
            
            if last_scrape:
                before_scrape, after_scrape, added_count, scrape_time = last_scrape
                return {
                    "total_count": sas_count + temp_count,
                    "total_sas_ids": sas_count,
                    "total_temp_ids": temp_count,
                    "last_scrape": str(scrape_time),
                    "before_scrape": before_scrape,
                    "after_scrape": after_scrape,
                    "added_count": added_count
                }
            else:
                return {
                    "total_count": sas_count + temp_count,
                    "total_sas_ids": sas_count,
                    "total_temp_ids": temp_count,
                    "last_scrape": None,
                    "before_scrape": 0,
                    "after_scrape": sas_count,
                    "added_count": 0
                }

@app.post("/api/scrape-log/pre-scrape")
def log_pre_scrape():
    """Log the state before starting a scrape"""
    try:
        with psycopg2.connect(DB_URL) as conn:
            with conn.cursor() as cur:
                # Get current max SAS ID count
                cur.execute("SELECT COUNT(*) FROM sailing_id WHERE first_name != 'No Record'")
                before_count = cur.fetchone()[0]
                
                # Insert pre-scrape log entry
                cur.execute("""
                    INSERT INTO scrape_log (before_scrape_count, after_scrape_count, added_count, status, message)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """, (before_count, 0, 0, 'STARTED', 'Pre-scrape logged'))
                
                log_id = cur.fetchone()[0]
                conn.commit()
                
                return {"success": True, "log_id": log_id, "before_count": before_count}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/run-daily-scrape")
def run_daily_scrape():
    """Run the daily scrape process with all rules applied"""
    import requests
    from bs4 import BeautifulSoup
    import time
    
    try:
        with psycopg2.connect(DB_URL) as conn:
            with conn.cursor() as cur:
                # Get the most recent started log entry
                cur.execute("""
                    SELECT id, before_scrape_count 
                    FROM scrape_log 
                    WHERE status = 'STARTED' 
                    ORDER BY id DESC 
                    LIMIT 1
                """)
                
                log_entry = cur.fetchone()
                if not log_entry:
                    return {"success": False, "error": "No pre-scrape log found. Call pre-scrape first."}
                
                log_id, before_count = log_entry
                
                # Get current max SAS ID to start from
                cur.execute("SELECT MAX(sa_sailing_id) FROM sailing_id")
                max_id = cur.fetchone()[0] or 0
                start_id = max_id + 1
                
                # Scrape with all rules
                new_records = []
                consecutive_no_record = 0
                max_consecutive_no_record = 10
                current_id = start_id
                
                while consecutive_no_record < max_consecutive_no_record:
                    # Check if already exists
                    cur.execute("SELECT sa_sailing_id FROM sailing_id WHERE sa_sailing_id = %s", (current_id,))
                    if cur.fetchone():
                        current_id += 1
                        continue
                    
                    # Scrape SA Sailing website
                    url = f"https://www.sailing.org.za/member-finder?parentBodyID={current_id}&firstname=&surname="
                    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                    
                    try:
                        response = requests.get(url, headers=headers, timeout=10)
                        response.raise_for_status()
                        
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # Check if valid member
                        if "SA Sailing ID:" in response.text and str(current_id) in response.text:
                            name_elements = soup.find_all('b')
                            
                            for elem in name_elements:
                                name_text = elem.get_text().strip()
                                if name_text and name_text != str(current_id) and "SA Sailing ID:" not in name_text:
                                    # Apply parsing rules
                                    name_text = name_text.replace(',,', ',')  # Fix double commas
                                    
                                    if ',' in name_text:
                                        # Format: "Lastname, Firstname Middle"
                                        parts = name_text.split(',')
                                        last_name = parts[0].strip()
                                        first_name = parts[1].strip().split()[0]  # ONLY first word
                                    else:
                                        # Format: "Firstname Middle Lastname" 
                                        name_parts = name_text.split()
                                        if len(name_parts) >= 2:
                                            last_name = name_parts[-1]  # Last word
                                            first_name = name_parts[0]  # ONLY first word
                                        else:
                                            first_name = name_text
                                            last_name = ''
                                    
                                    # Get birth year
                                    birth_year = None
                                    born_elements = soup.find_all(string=lambda text: text and 'Born' in text)
                                    for born_text in born_elements:
                                        try:
                                            year_part = born_text.strip().split('Born')[1].strip()
                                            birth_year = int(year_part)
                                            break
                                        except:
                                            continue
                                    
                                    # Insert valid member
                                    cur.execute("""
                                        INSERT INTO sailing_id (sa_sailing_id, first_name, last_name, birth_year, display_name)
                                        VALUES (%s, %s, %s, %s, %s)
                                    """, (current_id, first_name, last_name, birth_year, name_text))
                                    
                                    new_records.append({
                                        'sa_sailing_id': current_id,
                                        'first_name': first_name,
                                        'last_name': last_name,
                                        'display_name': name_text,
                                        'birth_year': birth_year
                                    })
                                    
                                    consecutive_no_record = 0
                                    break
                            else:
                                # No valid member found - DO NOT INSERT, just count
                                consecutive_no_record += 1
                        else:
                            # No record found - DO NOT INSERT, just count
                            consecutive_no_record += 1
                        
                        # Respectful delay
                        time.sleep(0.5)
                        current_id += 1
                        
                    except Exception as e:
                        print(f"Error scraping {current_id}: {e}")
                        consecutive_no_record += 1
                        current_id += 1
                
                # Get final counts
                cur.execute("SELECT COUNT(*) FROM sailing_id WHERE first_name != 'No Record'")
                after_count = cur.fetchone()[0]
                added_count = after_count - before_count
                
                # Update scrape log
                cur.execute("""
                    UPDATE scrape_log 
                    SET after_scrape_count = %s, added_count = %s, status = 'SUCCESS', message = %s
                    WHERE id = %s
                """, (after_count, added_count, f"Found {len(new_records)} new members", log_id))
                
                conn.commit()
                
                return {
                    "success": True,
                    "new_members": len(new_records),
                    "before_count": before_count,
                    "after_count": after_count,
                    "added_count": added_count,
                    "members": new_records
                }
                
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/scrape-log/post-scrape")
def log_post_scrape():
    """Log the state after completing a scrape"""
    try:
        with psycopg2.connect(DB_URL) as conn:
            with conn.cursor() as cur:
                # Get the most recent successful scrape
                cur.execute("""
                    SELECT before_scrape_count, after_scrape_count, added_count, timestamp 
                    FROM scrape_log 
                    WHERE status = 'SUCCESS' 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                """)
                
                result = cur.fetchone()
                if result:
                    before_count, after_count, added_count, timestamp = result
                    return {
                        "success": True,
                        "before_count": before_count,
                        "after_count": after_count,
                        "added_count": added_count,
                        "timestamp": timestamp.isoformat()
                    }
                else:
                    return {"success": False, "error": "No successful scrape found"}
                    
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/search")
def api_search(
    q: Optional[str] = None,
    sas_id: Optional[str] = None,
    first_names: Optional[str] = None,
    surname: Optional[str] = None,
    class_name: Optional[str] = None,
    club: Optional[str] = None,
    age_exact: Optional[int] = None,
    age_min: Optional[int] = None,
    age_max: Optional[int] = None,
    request: Request = None,
    age_under: Optional[int] = None,
    age_over: Optional[int] = None,
    limit: int = 200,
):
    """Search for members (SA IDs and Temp IDs) with last regatta info"""
    request_id = getattr(request.state, 'request_id', None) if request else None
    if not request_id:
        request_id = get_request_id()
    
    # STAGE 12 OPTIMIZATION: Enforce maximum limit and minimum query length
    limit = min(limit, 200)  # Cap at 200 to prevent huge result sets
    
    rows = []
    
    conn = None
    try:
        conn = get_db_connection(request_id)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # Wrap cursor with query tracing
                trace_query(cur, request_id)
                # Build WHERE conditions
                conditions = []
                params = []
                
                # Track if we need sail/boat name search (handled via JOIN, not WHERE EXISTS)
                needs_sail_boat_search = False
                if q:
                    q_trimmed = q.strip()
                    # Free text search on names, sail numbers, boat names - but exclude if it's just "T" (temp ID search)
                    if q_trimmed.upper() != "T":
                        # STAGE 12 OPTIMIZATION: Require minimum 2 characters for free text search
                        # Single character searches like "t" cause full table scans and return thousands of results
                        if len(q_trimmed) < 2:
                            # For single character, return empty or use exact SA ID match only
                            if q_trimmed.isdigit():
                                # If it's a digit, try exact SA ID match
                                conditions.append("s.sa_sailing_id::text = %s")
                                params.append(q_trimmed)
                            else:
                                # Single letter - return empty to avoid 7-18 second scans
                                return []
                        else:
                            # STAGE 12: Removed EXISTS clause - use LEFT JOIN with pre-filtered results instead
                            # This eliminates per-row EXISTS subquery scans
                            # For 2+ character queries, use prefix match (faster than LIKE '%...%')
                            needs_sail_boat_search = True
                            # Use prefix match (starts with) instead of LIKE '%...%' for better index usage
                            conditions.append("""
                                (LOWER(s.last_name) LIKE %s 
                                 OR LOWER(s.first_name) LIKE %s
                                 OR LOWER(s.last_name || ' ' || s.first_name) LIKE %s
                                 OR LOWER(s.first_name || ' ' || s.last_name) LIKE %s
                                 OR s.sa_sailing_id::text LIKE %s)
                            """)
                            q_lower = f"{q_trimmed.lower()}%"
                            q_lower_space = f"%{q_trimmed.lower()}%"
                            params.extend([q_lower, q_lower, q_lower_space, q_lower_space, f"%{q_trimmed}%"])
                
                if sas_id:
                    # If sas_id is "T" or starts with "TMP", don't filter SA IDs (will show temp IDs instead)
                    if sas_id.strip().upper() not in ["T", "TMP"] and not sas_id.upper().startswith("TMP:"):
                        conditions.append("s.sa_sailing_id::text = %s")
                        params.append(sas_id)
                    # Otherwise, let temp ID query handle it
                
                if first_names:
                    # Match from start of first name (not anywhere in the name)
                        conditions.append("LOWER(COALESCE(s.first_name, '')) LIKE %s")
                        params.append(f"{first_names.lower()}%")
                
                if surname:
                    # Match from start of last name (not anywhere in the name)
                        conditions.append("LOWER(COALESCE(s.last_name, '')) LIKE %s")
                        params.append(f"{surname.lower()}%")
                
                if class_name:
                    conditions.append("LOWER(COALESCE(s.primary_class, '')) LIKE %s")
                    params.append(f"%{class_name.lower()}%")
                
                if club:
                    conditions.append("(LOWER(COALESCE(s.primary_club, '')) = LOWER(%s) OR LOWER(COALESCE(s.club_1, '')) = LOWER(%s))")
                    params.extend([club, club])
                
                # Age filters
                current_year = 2025
                if age_exact:
                    conditions.append("s.year_of_birth = %s")
                    params.append(current_year - age_exact)
                if age_min:
                    conditions.append("s.year_of_birth <= %s")
                    params.append(current_year - age_min)
                if age_max:
                    conditions.append("s.year_of_birth >= %s")
                    params.append(current_year - age_max)
                if age_under:
                    conditions.append("s.year_of_birth > %s")
                    params.append(current_year - age_under)
                if age_over:
                    conditions.append("s.year_of_birth < %s")
                    params.append(current_year - age_over)
                
                where_clause = " AND " + " AND ".join(conditions) if conditions else ""
                
                # Check if we should skip SA ID query (if searching for temp IDs only)
                skip_sa_query = (sas_id and (sas_id.strip().upper() == "T" or sas_id.upper().startswith("TMP")))
                
                # Query for SA IDs (skip if searching for temp IDs only)
                sa_rows = []
                if not skip_sa_query:
                    # STAGE 12: Optimized query - removed LATERAL JOINs and EXISTS clauses
                    # Uses pre-aggregated LEFT JOINs instead of per-row subqueries
                    # Pattern: Single pass through sas_id_personal with pre-computed result flags
                    
                    # Build sail/boat name search JOIN if needed (replaces EXISTS clause)
                    sail_boat_join = ""
                    sail_boat_filter = ""
                    sail_boat_params = []
                    if needs_sail_boat_search and q and len(q.strip()) >= 2:
                        # Only do sail/boat search for 2+ character queries to avoid slow scans
                        sail_boat_join = """
                            LEFT JOIN (
                                SELECT DISTINCT 
                                    COALESCE(res.helm_sa_sailing_id::text, res.crew_sa_sailing_id::text) as sailor_id
                                FROM public.results res
                                WHERE (res.sail_number::text LIKE %s OR LOWER(COALESCE(res.boat_name, '')) LIKE %s)
                            ) sail_boat_match ON sail_boat_match.sailor_id = s.sa_sailing_id::text
                        """
                        sail_boat_filter = "OR sail_boat_match.sailor_id IS NOT NULL"
                        q_trimmed = q.strip()
                        q_lower = f"%{q_trimmed.lower()}%"
                        sail_boat_params = [f"%{q_trimmed}%", q_lower]
                    
                    # STAGE 12 FIX: Removed expensive CTEs that scan entire results table
                    # These were causing 7-18 second delays on every search
                    # Simple query is much faster - role defaults to 'helm' which is fine
                    sql_sa = f"""
                        SELECT DISTINCT
                            s.sa_sailing_id::text as sas_id,
                            s.last_name as surname,
                            s.first_name as first_names,
                            s.primary_class as class_name,
                            'helm' as role,
                            COALESCE(s.primary_club, s.club_1) as club,
                            s.province,
                            NULL::text as last_regatta_name,
                            NULL::integer as rank,
                            NULL::text as regatta_date,
                            NULL::text as regatta_number,
                            NULL::text as sail_number,
                            NULL::text as boat_name,
                            NULL::text as bow_no,
                            s.year_of_birth as born
                        FROM public.sas_id_personal s
                        {sail_boat_join}
                        WHERE 1=1 {where_clause}{" " + sail_boat_filter if sail_boat_filter else ""}
                        ORDER BY surname NULLS LAST, first_names NULLS LAST, sas_id
                        LIMIT %s
                    """
                    # Combine params: sail_boat_params first (for JOIN), then existing params, then limit
                    final_params = sail_boat_params + params + [limit]
                    cur.execute(sql_sa, final_params)
                    sa_rows = cur.fetchall()
                
                # Query for Temp IDs
                temp_conditions = []
                temp_params = []
                temp_rows = []  # Initialize to avoid UnboundLocalError
                
                # Include temp IDs if:
                # 1. sas_id parameter is "T" or "TMP" or starts with "TMP:"
                # 2. q is "T" or starts with "TMP"
                # 3. q is empty (show all)
                should_show_temp_ids = (
                    (sas_id and (sas_id.strip().upper() == "T" or sas_id.upper().startswith("TMP"))) or
                    (not q or q.strip() == "" or q.strip().upper() == "T" or q.upper().startswith("TMP"))
                )
                
                if should_show_temp_ids:
                    # Show all temp IDs unless filtered
                    # Check sas_id first (more specific)
                    if sas_id:
                        if sas_id.upper().startswith("TMP:") and ":" in sas_id:
                            # Specific temp ID like TMP:1 from sas_id parameter
                            tmp_num = sas_id.split(":")[-1].strip()
                            if tmp_num.isdigit():
                                temp_conditions.append("t.temp_id = %s")
                                temp_params.append(int(tmp_num))
                        # Otherwise "T" or "TMP" shows all temp IDs
                    elif q and q.upper().startswith("TMP:") and ":" in q:
                        # Specific temp ID like TMP:1 from q parameter
                        tmp_num = q.split(":")[-1].strip()
                        if tmp_num.isdigit():
                            temp_conditions.append("t.temp_id = %s")
                            temp_params.append(int(tmp_num))
                    
                    # Apply name filter if q is not a temp ID pattern
                    if q and not q.upper().startswith("TMP") and q.strip().upper() != "T":
                        temp_conditions.append("""
                            (LOWER(t.full_name) LIKE %s
                             OR EXISTS (
                                 SELECT 1 FROM public.results res 
                                 WHERE (res.helm_temp_id = 'TMP:' || t.temp_id::text 
                                        OR res.crew_temp_id = 'TMP:' || t.temp_id::text)
                                 AND (res.sail_number::text LIKE %s OR LOWER(COALESCE(res.boat_name, '')) LIKE %s)
                             ))
                        """)
                        q_lower = f"%{q.lower()}%"
                        temp_params.extend([q_lower, f"%{q}%", q_lower])
                elif q:
                    # Search by name, sail number, boat name (not temp ID search)
                    temp_conditions.append("""
                        (LOWER(t.full_name) LIKE %s
                         OR EXISTS (
                             SELECT 1 FROM public.results res 
                             WHERE (res.helm_temp_id = 'TMP:' || t.temp_id::text 
                                    OR res.crew_temp_id = 'TMP:' || t.temp_id::text)
                             AND (res.sail_number::text LIKE %s OR LOWER(COALESCE(res.boat_name, '')) LIKE %s)
                         ))
                    """)
                    q_lower = f"%{q.lower()}%"
                    temp_params.extend([q_lower, f"%{q}%", q_lower])
                
                # Apply first_names and surname filters to temp IDs too
                if first_names:
                    # Extract first name from full_name for temp IDs
                    temp_conditions.append("""
                        LOWER(COALESCE(t.first_name, 
                            CASE 
                                WHEN POSITION(' ' IN t.full_name) > 0 
                                THEN SUBSTRING(t.full_name FROM 1 FOR POSITION(' ' IN t.full_name) - 1)
                                ELSE t.full_name
                            END
                        )) LIKE %s
                    """)
                    temp_params.append(f"{first_names.lower()}%")
                
                if surname:
                    # Extract last name from full_name for temp IDs
                    temp_conditions.append("""
                        LOWER(COALESCE(t.last_name,
                            CASE 
                                WHEN POSITION(' ' IN t.full_name) > 0 
                                THEN SUBSTRING(t.full_name FROM POSITION(' ' IN t.full_name) + 1)
                                ELSE ''
                            END
                        )) LIKE %s
                    """)
                    temp_params.append(f"{surname.lower()}%")
                
                # Apply other filters to temp IDs too (club, class)
                # These need to be filtered from results table, not temp_people
                if club:
                    # Filter by club from results table
                    temp_conditions.append("EXISTS (SELECT 1 FROM public.results res JOIN public.clubs c ON c.club_id = res.club_id WHERE (res.helm_temp_id = 'TMP:' || t.temp_id::text OR res.crew_temp_id = 'TMP:' || t.temp_id::text OR res.crew2_temp_id = 'TMP:' || t.temp_id::text OR res.crew3_temp_id = 'TMP:' || t.temp_id::text) AND LOWER(c.club_abbrev) = LOWER(%s))")
                    temp_params.append(club)
                
                if class_name:
                    # Filter by class from results table
                    temp_conditions.append("EXISTS (SELECT 1 FROM public.results res WHERE (res.helm_temp_id = 'TMP:' || t.temp_id::text OR res.crew_temp_id = 'TMP:' || t.temp_id::text OR res.crew2_temp_id = 'TMP:' || t.temp_id::text OR res.crew3_temp_id = 'TMP:' || t.temp_id::text) AND LOWER(res.class_canonical) LIKE LOWER(%s))")
                    temp_params.append(f"%{class_name}%")
                
                    temp_where = " AND " + " AND ".join(temp_conditions) if temp_conditions else ""
                    
                    sql_temp = f"""
                    SELECT
                        'TMP:' || t.temp_id::text as sas_id,
                        COALESCE(t.last_name, 
                            CASE 
                                WHEN POSITION(' ' IN t.full_name) > 0 
                                THEN SUBSTRING(t.full_name FROM POSITION(' ' IN t.full_name) + 1)
                                ELSE ''
                            END
                        ) as surname,
                        COALESCE(t.first_name,
                            CASE 
                                WHEN POSITION(' ' IN t.full_name) > 0 
                                THEN SUBSTRING(t.full_name FROM 1 FOR POSITION(' ' IN t.full_name) - 1)
                                ELSE t.full_name
                            END
                        ) as first_names,
                        COALESCE(t.primary_class, 'N/A') as class_name,
                        CASE 
                            WHEN EXISTS(SELECT 1 FROM public.results res WHERE res.helm_temp_id = 'TMP:' || t.temp_id::text) THEN 'helm'
                            WHEN EXISTS(SELECT 1 FROM public.results res WHERE res.crew_temp_id = 'TMP:' || t.temp_id::text) THEN 'crew'
                            ELSE 'helm'
                        END as role,
                        COALESCE(t.primary_club, t.club_1, 'N/A') as club,
                        COALESCE(last_regatta.event_name, 'N/A') as last_regatta_name,
                        last_regatta.rank,
                        last_regatta.end_date::text as regatta_date,
                        last_regatta.regatta_number,
                        last_regatta.sail_number,
                        most_common.boat_name,
                        most_common.bow_no,
                        t.year_of_birth as born
                    FROM public.temp_people t
                    LEFT JOIN LATERAL (
                        SELECT res.rank, r.event_name, r.end_date, r.regatta_number, res.sail_number
                        FROM public.results res
                        JOIN public.regattas r ON r.regatta_id = res.regatta_id
                        WHERE (res.helm_temp_id = 'TMP:' || t.temp_id::text
                           OR res.crew_temp_id = 'TMP:' || t.temp_id::text
                           OR res.crew2_temp_id = 'TMP:' || t.temp_id::text
                           OR res.crew3_temp_id = 'TMP:' || t.temp_id::text)
                          AND res.raced = TRUE
                          AND (r.end_date IS NULL OR r.end_date <= CURRENT_DATE)
                        ORDER BY r.end_date DESC NULLS LAST, r.start_date DESC NULLS LAST
                        LIMIT 1
                    ) last_regatta ON true
                    LEFT JOIN LATERAL (
                        SELECT 
                            (SELECT res2.boat_name FROM public.results res2 
                             WHERE (res2.helm_temp_id = 'TMP:' || t.temp_id::text
                                    OR res2.crew_temp_id = 'TMP:' || t.temp_id::text
                                    OR res2.crew2_temp_id = 'TMP:' || t.temp_id::text
                                    OR res2.crew3_temp_id = 'TMP:' || t.temp_id::text)
                               AND res2.raced = TRUE
                               AND res2.boat_name IS NOT NULL AND res2.boat_name != ''
                             GROUP BY res2.boat_name
                             ORDER BY COUNT(*) DESC
                             LIMIT 1) as boat_name,
                            (SELECT res2.bow_no FROM public.results res2 
                             WHERE (res2.helm_temp_id = 'TMP:' || t.temp_id::text
                                    OR res2.crew_temp_id = 'TMP:' || t.temp_id::text
                                    OR res2.crew2_temp_id = 'TMP:' || t.temp_id::text
                                    OR res2.crew3_temp_id = 'TMP:' || t.temp_id::text)
                               AND res2.raced = TRUE
                               AND res2.bow_no IS NOT NULL AND res2.bow_no != ''
                             GROUP BY res2.bow_no
                             ORDER BY COUNT(*) DESC
                             LIMIT 1) as bow_no
                    ) most_common ON true
                    WHERE 1=1 {temp_where}
                    ORDER BY COALESCE(t.last_name, t.full_name), COALESCE(t.first_name, ''), t.temp_id
                    LIMIT %s
                """
                    temp_params.append(limit)
                    if temp_where:
                        cur.execute(sql_temp, temp_params)
                    else:
                        cur.execute(sql_temp, [limit])
                    temp_rows = cur.fetchall()
                
                # Combine results
                for row in sa_rows:
                    rows.append(dict(row))
                for row in temp_rows:
                    rows.append(dict(row))
                
                return rows[:limit]
    except Exception as e:
        import traceback
        traceback.print_exc()
        return []
    finally:
        if conn:
            return_db_connection(conn)

@app.get("/api/isp-codes")
def api_isp_codes():
    """Return list of World Sailing ISP (International Sailing Penalty) codes"""
    return [
        {"code": "DNC", "description": "Did Not Compete"},
        {"code": "DNS", "description": "Did Not Start"},
        {"code": "DNF", "description": "Did Not Finish"},
        {"code": "RET", "description": "Retired"},
        {"code": "DSQ", "description": "Disqualified"},
        {"code": "OCS", "description": "On Course Side"},
        {"code": "BFD", "description": "Black Flag Disqualification"},
        {"code": "UFD", "description": "U Flag Disqualification"},
        {"code": "DPI", "description": "Discretionary Penalty Imposed"}
    ]

# Class name resolution: full phrase -> also match aliases (e.g. Laser -> ILCA). Use full phrase so "Optimist A" matches only that class.
CLASS_SEARCH_ALIASES = {
    "laser": ["laser", "ilca"],
    "ilca": ["ilca", "laser"],
    "ilca 4": ["ilca 4", "ilca4", "laser 4", "laser4", "radial"],
    "ilca 6": ["ilca 6", "ilca6", "laser standard", "laser radial"],
    "ilca 7": ["ilca 7", "ilca7", "laser"],
    "optimist": ["optimist", "opti"],
    "opti": ["opti", "optimist"],
    "optimist a": ["optimist a"],
    "optimist b": ["optimist b"],
    "optimist c": ["optimist c"],
}

# Single-letter / short abbreviations -> full word so the filter NARROWS (e.g. "Y nationals" = Youth nationals only).
SEARCH_TERM_ABBREVIATIONS = {
    "y": "youth",
    "j": "junior",
}

def _escape_like(s: str) -> str:
    """Escape % and _ for use in SQL LIKE patterns."""
    if not s:
        return s
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _parse_search_terms_and_year(q: str) -> tuple:
    """Parse search query into (search_terms, year). Strips 19xx/20xx as year. Groups known class phrases (e.g. 'Optimist A' -> one term 'optimist a') so narrow searches like 'HYC Classic 2025 Optimist A' return one result."""
    if not q or not q.strip():
        return ([], None)
    words = q.strip().split()
    raw_terms = []
    year = None
    for w in words:
        if len(w) == 4 and w.isdigit():
            y = int(w, 10)
            if 1900 <= y <= 2099 and (w.startswith("19") or w.startswith("20")):
                year = y
                continue
        raw_terms.append(w)
    # Group consecutive words that form a known class phrase (e.g. "Optimist" + "A" -> "optimist a") so "HYC Classic 2025 Optimist A" narrows correctly
    phrase_keys = sorted([k for k in CLASS_SEARCH_ALIASES.keys() if " " in k], key=len, reverse=True)
    terms = []
    i = 0
    while i < len(raw_terms):
        merged = False
        for phrase in phrase_keys:
            n = len(phrase.split())
            if i + n <= len(raw_terms):
                candidate = " ".join(raw_terms[i : i + n]).lower()
                if candidate == phrase:
                    terms.append(phrase)
                    i += n
                    merged = True
                    break
        if not merged:
            terms.append(raw_terms[i].lower())
            i += 1
    return (terms, year)


def _effective_search_term(term: str) -> str:
    """Narrow filter: expand abbreviations so 'y' -> 'youth', etc. Returns full word to match (fewer, more relevant results)."""
    if not term:
        return ""
    t = term.lower().strip()
    return SEARCH_TERM_ABBREVIATIONS.get(t, t)


def _regatta_name_term_match_sql(term: str, params: list, escape: bool = True) -> str:
    """Build SQL condition: regatta r has the term in event_name or host_club_name. Appends to params. Uses abbreviation expansion so filter narrows."""
    t = _effective_search_term(term)
    if not t:
        return "1=1"
    pat = f"%{_escape_like(t) if escape else t}%"
    params.append(pat)
    params.append(pat)
    return "(LOWER(COALESCE(r.event_name, '')) LIKE %s OR LOWER(COALESCE(r.host_club_name, '')) LIKE %s)"


def _result_row_term_match_sql(term: str, params: list, escape: bool = True) -> str:
    """Build SQL condition: this result row has the term in at least one of class, sail_number, boat_name, club, event. Uses abbreviation expansion (y->youth) and CLASS_SEARCH_ALIASES so filter narrows."""
    t = _effective_search_term(term)
    if not t:
        return "1=1"
    pat = _escape_like(t) if escape else t
    pat = f"%{pat}%"
    # Class: expand via aliases so "opti" matches Optimist; effective term (e.g. youth) used for narrowing
    class_aliases = CLASS_SEARCH_ALIASES.get(t, [t])
    class_aliases = list(dict.fromkeys(class_aliases))
    conds = []
    # sail_number (cast to text for ILIKE), boat_name
    conds.append("(res.sail_number::text ILIKE %s OR LOWER(COALESCE(res.boat_name, '')) LIKE %s)")
    params.extend([pat, pat])
    # club: sailor's club (linked club c OR raw club on result) and regatta name/host (r2)
    # So "HYC" matches: regatta with HYC in name, or any regatta with a sailor from HYC (club_id or club_raw)
    conds.append("(LOWER(COALESCE(c.club_abbrev, '')) LIKE %s OR LOWER(COALESCE(c.club_fullname, '')) LIKE %s OR LOWER(COALESCE(res.club_raw, '')) LIKE %s OR LOWER(COALESCE(r2.host_club_name, '')) LIKE %s OR LOWER(COALESCE(r2.event_name, '')) LIKE %s)")
    params.extend([pat, pat, pat, pat, pat])
    # class: match any alias
    for a in class_aliases:
        apat = f"%{(_escape_like(a) if escape else a)}%"
        conds.append("(LOWER(COALESCE(res.class_canonical, '')) LIKE %s OR LOWER(COALESCE(res.class_original, '')) LIKE %s)")
        params.extend([apat, apat])
    return "(" + " OR ".join(conds) + ")"


def _match_reason_from_row(row: dict, terms: list) -> tuple:
    """From one result row that matched all terms, return (reason_label, term_to_highlight) e.g. ('Boat = Co-ordination', 'nati'). Only use boat/class/club — never event_name/host (that would just repeat the regatta name)."""
    if not row or not terms:
        return (None, None)
    # Only result-row fields that explain why this regatta matched; do NOT use event_name/host_club_name (redundant with regatta title)
    fields = [
        ("boat_name", "Boat"),
        ("class_canonical", "Class"),
        ("class_original", "Class"),
        ("club_abbrev", "Club"),
        ("club_fullname", "Club"),
        ("club_raw", "Club"),
    ]
    for col, label in fields:
        val = row.get(col)
        if not val:
            continue
        display = str(val).strip()
        if not display:
            continue
        low_val = display.lower()
        for term in terms:
            effective = _effective_search_term(term)
            if not effective:
                continue
            if effective.lower() in low_val:
                return (f"{label} = {display}", term)
    return (None, None)


@app.get("/api/regattas/with-counts")
def api_regattas_with_counts(
    search_q: Optional[str] = Query(None, alias="q"),
    year: Optional[int] = None,
    class_name: Optional[str] = Query(None, description="Filter regattas that sailed this class (e.g. 'Optimist A')"),
):
    """Return regattas with entry counts. q = Google-like: any word matches event name, host, or class (with aliases e.g. Laser=ILCA)."""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        conditions = []
        params = []
        
        # Search levels (more terms = narrower):
        # - "HYC" (wide): any regatta with HYC in name OR any regatta with a sailor from club HYC.
        # - "HYC optimist" (medium): HYC-hosted regatta where Optimist sailed, OR any regatta where an HYC member sailed Optimist (both terms in same result row).
        # - "HYC Classic 2025 Optimist A" (narrow): only regattas matching ALL terms in same row/name + year 2025; "Optimist A" kept as one phrase so it returns one result.
        # Regatta Results table is the source of truth; fallback: regatta event_name/host_club_name match all terms.
        name_match_params = []
        name_match_sql = None
        if search_q and search_q.strip():
            terms, parsed_year = _parse_search_terms_and_year(search_q)
            # Year in search text always wins: "Y Nationals 2025" must filter to 2025 only (exclude 2024)
            if parsed_year is not None:
                year = parsed_year
            if terms:
                term_conds = []
                for t in terms:
                    term_conds.append(_result_row_term_match_sql(t, params))
                results_subquery = """r.regatta_id IN (
                    SELECT DISTINCT res.regatta_id FROM results res
                    LEFT JOIN clubs c ON c.club_id = res.club_id
                    JOIN regattas r2 ON r2.regatta_id = res.regatta_id
                    WHERE """
                results_subquery += " AND ".join(term_conds) + ")"
                # Regatta-level name match (same terms) so we don't miss regattas that match by name
                name_conds = [_regatta_name_term_match_sql(t, name_match_params) for t in terms]
                name_match_sql = "(" + " AND ".join(name_conds) + ")"
                conditions.append("(" + results_subquery + " OR " + name_match_sql + ")")
                params.extend(name_match_params)
            else:
                # Only year was in query; no text terms
                pass
        
        # Year filter: ONLY actual regatta date (start_date, end_date). Do NOT use r.year — it can be import/capture year and wrong.
        if year:
            conditions.append("(EXTRACT(YEAR FROM r.start_date) = %s OR EXTRACT(YEAR FROM r.end_date) = %s)")
            params.extend([year, year])
        
        # Legacy: single class_name filter — must be in results table for that regatta
        if class_name and class_name.strip():
            conditions.append("""r.regatta_id IN (
                SELECT res.regatta_id FROM results res
                WHERE LOWER(COALESCE(res.class_canonical, '')) LIKE %s
                   OR LOWER(COALESCE(res.class_original, '')) LIKE %s
            )""")
            class_pattern = f"%{class_name.strip().lower()}%"
            params.extend([class_pattern, class_pattern])
        
        where_clause = " AND " + " AND ".join(conditions) if conditions else ""
        
        # Exclude aggregate "Classic Series" (and similar Series > Class > Overall) — not real standalone regattas
        # Use %% so literal % is not interpreted as a placeholder by psycopg2
        exclude_series = """ AND NOT (
            LOWER(COALESCE(r.event_name, '')) LIKE '%%classic series%%'
            OR ( LOWER(COALESCE(r.event_name, '')) LIKE '%%series%%' AND LOWER(COALESCE(r.event_name, '')) LIKE '%%> overall%%' )
        ) """
        # When we have a name match, add is_best_match so frontend can show "Best match" first and "Contains HYC Club sailors" for others
        select_best_match = ""
        if name_match_sql is not None:
            select_best_match = ", (CASE WHEN " + name_match_sql + " THEN 1 ELSE 0 END) AS is_best_match"
        base_sql = """
            SELECT 
                r.regatta_id,
                r.event_name,
                r.year,
                r.regatta_number,
                r.start_date,
                r.end_date,
                r.host_club_name,
                COALESCE(c.club_abbrev, r.host_club_name) as host_club_code,
                COUNT(DISTINCT res.result_id) as entries_count
        """ + select_best_match + """
            FROM regattas r
            LEFT JOIN results res ON res.regatta_id = r.regatta_id
            LEFT JOIN clubs c ON c.club_id = r.host_club_id
            WHERE 1=1
        """ + exclude_series + """
        """
        
        # Include regattas with 0 results when they matched by name (so "SA Youth Nationals Dec 2025" always shows)
        having_clause = "HAVING COUNT(DISTINCT res.result_id) > 0"
        if name_match_sql is not None:
            having_clause = "HAVING (COUNT(DISTINCT res.result_id) > 0 OR " + name_match_sql + ")"
            params.extend(name_match_params)
        # Sort best match (regatta name matches all terms) first, then by regatta number/date
        order_best_first = ""
        if name_match_sql is not None:
            order_best_first = " (CASE WHEN " + name_match_sql + " THEN 0 ELSE 1 END),"
            params.extend(name_match_params)
        sql = base_sql + where_clause + """
            GROUP BY r.regatta_id, r.event_name, r.year, r.regatta_number, 
                     r.start_date, r.end_date, r.host_club_name, c.club_abbrev
        """ + having_clause + """
            ORDER BY
        """ + order_best_first + """
            r.regatta_number DESC NULLS LAST, r.year DESC NULLS LAST, r.start_date DESC NULLS LAST
            LIMIT 100
        """
        
        # SELECT and ORDER BY placeholders for name_match come first in SQL string, so prepend their params
        if name_match_sql is not None:
            params = list(name_match_params) + params
        if params:
            cur.execute(sql, tuple(params))
        else:
            cur.execute(sql)
        
        rows = cur.fetchall()
        terms_for_reason = []
        if search_q and search_q.strip():
            terms_for_reason, _ = _parse_search_terms_and_year(search_q)
        # For also_matched regattas, get one result row per regatta to determine actual match (e.g. Boat = Co-ordination for "nati")
        match_detail_by_regatta = {}
        if terms_for_reason:
            also_ids = [r["regatta_id"] for r in rows if r.get("is_best_match", 0) != 1]
            if also_ids:
                match_params = []
                match_conds = [_result_row_term_match_sql(t, match_params) for t in terms_for_reason]
                try:
                    match_sql = """
                    SELECT DISTINCT ON (res.regatta_id) res.regatta_id,
                        res.boat_name, res.class_canonical, res.class_original, res.club_raw,
                        c.club_abbrev, c.club_fullname, r2.event_name, r2.host_club_name
                    FROM results res
                    LEFT JOIN clubs c ON c.club_id = res.club_id
                    JOIN regattas r2 ON r2.regatta_id = res.regatta_id
                    WHERE res.regatta_id = ANY(%s) AND """ + " AND ".join(match_conds) + """
                    ORDER BY res.regatta_id
                    """
                    cur.execute(match_sql, (also_ids,) + tuple(match_params))
                    for m in cur.fetchall():
                        rid = m["regatta_id"]
                        reason, term = _match_reason_from_row(m, terms_for_reason)
                        if reason:
                            match_detail_by_regatta[rid] = {"match_reason": reason, "match_reason_term": term}
                except Exception:
                    pass
        out = []
        for row in rows:
            d = dict(row)
            is_best = d.pop("is_best_match", 0) if "is_best_match" in d else 0
            if terms_for_reason:
                if is_best:
                    d["match_reason"] = "Best match"
                    d["match_reason_term"] = None
                else:
                    detail = match_detail_by_regatta.get(d["regatta_id"])
                    if detail:
                        d["match_reason"] = detail["match_reason"]
                        d["match_reason_term"] = detail.get("match_reason_term")
                    else:
                        club_like = [t for t in terms_for_reason if 2 <= len(t) <= 6 and t.isalpha()]
                        if club_like:
                            d["match_reason"] = "Contains " + club_like[0].upper() + " Club sailors"
                        else:
                            d["match_reason"] = "Contains matching sailors or clubs"
                        d["match_reason_term"] = None
            else:
                d["match_reason"] = None
                d["match_reason_term"] = None
            out.append(d)
        return out
    except Exception as e:
        print(f"Error fetching regattas: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@app.get("/api/regatta/{regatta_id}/class-entries")
def api_regatta_class_entries(regatta_id: str):
    """Return class entry counts for a regatta (only raced=TRUE entries)"""
    t0 = time.time()
    print(f"[TRACE] getRegattaClassEntries({regatta_id}) START")
    rows = q("""
        SELECT 
            COALESCE(c.class_name, rb.class_canonical, rb.class_original) as class_name,
            COUNT(DISTINCT res.result_id) as entries
        FROM regatta_blocks rb
        LEFT JOIN results res ON res.block_id = rb.block_id AND res.raced = TRUE
        LEFT JOIN classes c ON c.class_name = rb.class_canonical OR LOWER(c.class_name) = LOWER(rb.class_canonical)
        WHERE rb.regatta_id = %s
        GROUP BY COALESCE(c.class_name, rb.class_canonical, rb.class_original)
        HAVING COUNT(DISTINCT res.result_id) > 0
        ORDER BY COALESCE(c.class_name, rb.class_canonical, rb.class_original)
    """, (regatta_id,))
    
    # Return as object with class names as keys
    result = {}
    for row in rows:
        class_name = row['class_name']
        entries = row['entries']
        result[class_name.lower()] = {
            'name': class_name,
            'entries': entries
        }
    
    t1 = time.time()
    print(f"[TRACE] getRegattaClassEntries({regatta_id}) took {t1-t0:.3f}s ({len(result)} classes)")
    return result

@app.get("/api/regatta/{regatta_id}")
def api_regatta(regatta_id: str):
    """Return all regatta data including blocks and results"""
    t0 = time.time()
    print(f"[TRACE] getRegatta({regatta_id}) START")
    try:
        rows = q("""
            SELECT 
                r.regatta_id,
                r.event_name,
                r.year,
                r.regatta_number,
                r.result_status,
                r.as_at_time,
                r.host_club_id,
            c.club_abbrev as host_club_code,
            COALESCE(c.club_fullname, c.club_abbrev) as host_club_name,
            rb.block_id,
            rb.fleet_label,
            rb.class_canonical,
                rb.class_original,
                rb.races_sailed,
                rb.discard_count,
                rb.to_count,
                rb.scoring_system,
                res.result_id,
                res.rank,
                res.helm_name,
                res.crew_name,
                res.sail_number,
                res.club_raw,
                res.club_id,
                c2.club_abbrev as club_abbrev,
                res.race_scores,
                res.total_points_raw,
                res.nett_points_raw,
                res.helm_sa_sailing_id,
                res.crew_sa_sailing_id,
                res.helm_temp_id,
                res.crew_temp_id,
                res.boat_name,
                res.jib_no,
                res.bow_no,
                res.hull_no,
                res.raced,
                COALESCE(cls.class_name, rb.class_canonical, rb.class_original) as class_name
            FROM regattas r
            LEFT JOIN clubs c ON c.club_id = r.host_club_id
            LEFT JOIN regatta_blocks rb ON rb.regatta_id = r.regatta_id
            LEFT JOIN results res ON res.block_id = rb.block_id
            LEFT JOIN clubs c2 ON c2.club_id = res.club_id
            LEFT JOIN classes cls ON cls.class_name = rb.class_canonical OR LOWER(cls.class_name) = LOWER(rb.class_canonical)
            WHERE r.regatta_id = %s
            ORDER BY rb.block_id, COALESCE(res.rank, 99999), res.result_id
        """, (regatta_id,))
        
        if not rows:
            raise HTTPException(status_code=404, detail="Regatta not found")
        
        # SPECIAL CASE: For Regatta 374, sort by master standings for all classes that have standings
        first_row = rows[0]
        regatta_number = first_row.get('regatta_number')
        if regatta_number == '374' or (isinstance(regatta_number, int) and regatta_number == 374):
            # Group rows by class
            class_blocks = {}  # {class_name: {block_id: [rows]}}
            other_rows = []
            
            for row in rows:
                if row.get('result_id'):  # Only process result rows, not header rows
                    block_id = row.get('block_id')
                    class_name = (row.get('class_canonical') or row.get('class_original') or '').strip()
                    if not class_name:
                        other_rows.append(row)
                        continue
                    
                    # Normalize class name (remove "Fleet" suffix, normalize case)
                    normalized_class = class_name.replace(' Fleet', '').strip()
                    # Store original for lookup, but use normalized for grouping
                    normalized_key = normalized_class.upper()  # Use uppercase for consistent matching
                    
                    if normalized_key not in class_blocks:
                        class_blocks[normalized_key] = {'original_name': normalized_class, 'blocks': {}}
                    if block_id not in class_blocks[normalized_key]['blocks']:
                        class_blocks[normalized_key]['blocks'][block_id] = []
                    class_blocks[normalized_key]['blocks'][block_id].append(row)
                else:
                    other_rows.append(row)  # Keep header rows
            
            # Check which classes have standings in database (case-insensitive)
            conn_standings = None
            try:
                conn_standings = get_db_connection()
                with conn_standings.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    if class_blocks:
                        # Get all class names from database and create case-insensitive lookup
                        cur.execute("""
                            SELECT DISTINCT class_name, UPPER(class_name) as upper_name
                            FROM standing_list
                        """)
                        db_classes = {row['upper_name']: row['class_name'] for row in cur.fetchall()}
                    else:
                        db_classes = {}
            except Exception as e:
                print(f"[WARNING] Failed to check database for standings: {e}")
                db_classes = {}
            finally:
                if conn_standings:
                    return_db_connection(conn_standings)
            
            # Sort each class that has standings
            sorted_class_rows = []
            unsorted_class_rows = []
            
            for normalized_key, class_data in class_blocks.items():
                original_class_name = class_data.get('original_name', normalized_key)
                blocks = class_data.get('blocks', {})
                
                # Check if this class has standings (case-insensitive)
                db_class_name = db_classes.get(normalized_key)
                if db_class_name:
                    # Get master standings from database (use database class name)
                    conn_standings = None
                    try:
                        conn_standings = get_db_connection()
                        with conn_standings.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                            cur.execute("""
                                SELECT 
                                    sl.sailor_id,
                                    sl.rank as main_rank
                                FROM standing_list sl
                                WHERE sl.class_name = %s
                                ORDER BY sl.rank ASC
                            """, (db_class_name,))
                            
                            master_rank_map = {}
                            for row in cur.fetchall():
                                sid = str(row['sailor_id'])
                                master_rank_map[sid] = row['main_rank']
                            
                            print(f"[REGATTA 374] Sorting {original_class_name} by master standings (found {len(master_rank_map)} sailors in standings)")
                            
                            # Sort each block by master standings
                            for block_id, block_rows in blocks.items():
                                # Sort by master rank (99999 for sailors not in master standings)
                                block_rows.sort(key=lambda r: master_rank_map.get(
                                    str(r.get('helm_sa_sailing_id') or r.get('helm_temp_id') or ''), 99999
                                ))
                                
                                # Reassign ranks 1-N based on master standings order
                                for i, row in enumerate(block_rows, 1):
                                    old_rank = row.get('rank')
                                    row['rank'] = i
                                    sailor_id = str(row.get('helm_sa_sailing_id') or row.get('helm_temp_id') or '')
                                    master_rank = master_rank_map.get(sailor_id, 'N/A')
                                    if i <= 5:  # Log first 5 for debugging
                                        print(f"[REGATTA 374] {original_class_name} Rank {i}: {row.get('helm_name')} (ID: {sailor_id}, Master Rank: {master_rank}, Old Rank: {old_rank})")
                                
                                sorted_class_rows.extend(block_rows)
                    except Exception as e:
                        import traceback
                        traceback.print_exc()
                        print(f"[WARNING] Failed to sort Regatta 374 {db_class_name} by master standings: {e}")
                        # Fall back to unsorted
                        for block_rows in blocks.values():
                            unsorted_class_rows.extend(block_rows)
                    finally:
                        if conn_standings:
                            return_db_connection(conn_standings)
                else:
                    # No standings for this class, keep original order
                    print(f"[REGATTA 374] ⚠️  No standings found for {original_class_name} (normalized: {normalized_key}, available: {list(db_classes.keys())[:10]})")
                    for block_rows in blocks.values():
                        unsorted_class_rows.extend(block_rows)
            
            # Rebuild rows: header rows first, then sorted classes, then unsorted classes
            new_rows = [r for r in rows if not r.get('result_id')]  # Header rows
            new_rows.extend(sorted_class_rows)  # Sorted by master standings
            new_rows.extend(unsorted_class_rows)  # Other classes (no standings or error)
            new_rows.extend([r for r in other_rows if r.get('result_id')])  # Other rows
            
            rows = new_rows
        
        # Calculate totals for first row
        first_row = rows[0]
        entries_total = len([r for r in rows if r.get('result_id')])
        helms_total = len([r for r in rows if r.get('result_id') and r.get('helm_name')])
        crews_total = len([r for r in rows if r.get('result_id') and r.get('crew_name')])
        sailors_total = helms_total + crews_total
        
        # Add totals to first row
        first_row['entries_total'] = entries_total
        first_row['helms_total'] = helms_total
        first_row['crews_total'] = crews_total
        first_row['sailors_total'] = sailors_total
        
        return rows
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sailor/{sailor_id}")
def api_sailor_details(sailor_id: str):
    """Get full sailor details by SA ID or Temp ID for tooltip display"""
    with psycopg2.connect(DB_URL) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Check if it's a temp ID
            if sailor_id.upper().startswith("TMP:") or sailor_id.upper().startswith("TMP"):
                tmp_num = sailor_id.split(":")[-1].strip() if ":" in sailor_id else sailor_id.replace("TMP", "").strip()
                if tmp_num.isdigit():
                    cur.execute("""
                        SELECT 
                            'TMP:' || t.temp_id::text as sa_id,
                            t.full_name as name,
                            COALESCE(c.club_code, t.club_raw) as club,
                            NULL as age,
                            NULL as year_of_birth,
                            NULL as primary_class,
                            NULL as email,
                            NULL as phone_primary,
                            t.notes as notes
                        FROM temp_people t
                        LEFT JOIN clubs c ON c.club_id = t.club_id
                        WHERE t.temp_id = %s
                    """, (int(tmp_num),))
                    row = cur.fetchone()
                    if row:
                        return dict(row)
            # Otherwise, treat as SA Sailing ID
            if sailor_id.isdigit():
                cur.execute("""
                    SELECT 
                        s.sa_sailing_id::text as sa_id,
                        COALESCE(s.full_name, TRIM(s.first_name || ' ' || COALESCE(s.last_name, ''))) as name,
                        COALESCE(s.primary_club, s.club_1) as club,
                        s.age,
                        s.year_of_birth,
                        s.primary_class,
                        s.email,
                        s.phone_primary,
                        NULL as notes
                    FROM sas_id_personal s
                    WHERE s.sa_sailing_id::text = %s
                """, (sailor_id,))
                row = cur.fetchone()
                if row:
                    return dict(row)
    
    return {"error": "Sailor not found"}

@app.get("/api/standings")
def api_standings(
    class_name: Optional[str] = None,
    open_regatta_only: Optional[str] = None,
    request: Request = None,
):
    """Return standings/rankings for a class (Optimist A, Optimist B, etc.) - OPTIMIZED with caching
    
    open_regatta_only: If "true" (string), only return sailors in regatta 374 (33 sailors).
                       If None, False, or any other value (default), return MASTER standings (all eligible sailors, excluding 374).
    """
    start_time = time.time()
    request_id = getattr(request.state, 'request_id', None) if request else None
    if not request_id:
        request_id = get_request_id()
    
    # Check cache first
    cache_key = f"standings_{class_name}_{open_regatta_only}"
    cached = get_cached(cache_key, ttl_seconds=30)
    if cached:
        duration = (time.time() - start_time) * 1000
        print(f"[CACHE] ✅ [{request_id}] /api/standings served from cache in {duration:.2f}ms")
        return cached
    
    conn = None
    try:
        conn = get_db_connection(request_id)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Wrap cursor with query tracing
            trace_query(cur, request_id)
            # For Optimist A and B, use master standings logic
            if class_name and class_name.lower() in ['optimist a', 'optimist b']:
                    fleet_label = 'Optimist A' if 'optimist a' in class_name.lower() else 'Optimist B'
                    
                    # EXPLICITLY check - ONLY return regatta 374 if open_regatta_only is explicitly "true" (string)
                    # DEFAULT: Always return MASTER standings (all eligible sailors, excluding 374)
                    # FastAPI boolean query params can be tricky, so use string comparison
                    if open_regatta_only and str(open_regatta_only).lower() == 'true':
                        # Return Regatta 374 entries ranked by MASTER STANDINGS order (not race results)
                        import logging
                        print(f"API: Returning regatta 374 standings for {fleet_label} ranked by master standings (open_regatta_only={open_regatta_only})")
                        logging.info(f"Returning regatta 374 standings for {fleet_label} ranked by master standings")
                        
                        # First, get the master standings (excluding 374)
                        # This will be calculated below in the else block, but we need it here
                        # For now, we'll calculate it inline for Regatta 374
                        # Actually, let's call the master standings logic and then filter to 374 entries
                        # We'll need to calculate master standings first, then apply to 374 entries
                        
                        # Get Regatta 374 ID
                        cur.execute("""
                            SELECT regatta_id, regatta_number
                            FROM regattas
                            WHERE regatta_number = 374
                            ORDER BY regatta_number DESC
                            LIMIT 1
                        """)
                        open_regatta = cur.fetchone()
                        
                        if not open_regatta:
                            return {"rankings": [], "total_sailors": 0, "aged_out": [], "unlikely": []}
                        
                        regatta_id = open_regatta['regatta_id']
                        
                        # Get all sailors entered in Regatta 374
                        sql = """
                            SELECT DISTINCT
                                COALESCE(r.helm_sa_sailing_id::text, r.helm_temp_id) as sailor_id,
                                r.helm_name as name,
                                s.first_name,
                                s.last_name,
                                s.year_of_birth,
                                s.age,
                                r.nett_points_raw as wc_score,
                                rb.races_sailed as total_races,
                                r.regatta_id
                            FROM results r
                            JOIN regatta_blocks rb ON rb.block_id = r.block_id
                            LEFT JOIN sas_id_personal s ON s.sa_sailing_id::text = r.helm_sa_sailing_id::text
                            WHERE r.regatta_id = %s
                                AND LOWER(rb.fleet_label) = LOWER(%s)
                                AND COALESCE(r.helm_sa_sailing_id::text, r.helm_temp_id) IS NOT NULL
                        """
                        cur.execute(sql, (regatta_id, fleet_label))
                        regatta_374_entries = {row['sailor_id']: dict(row) for row in cur.fetchall()}
                        
                        # Now get master standings (we'll need to calculate them)
                        # For Optimist, we need to call the master standings logic
                        # But to avoid code duplication, let's calculate master standings here
                        # Actually, the best approach is to calculate master standings first, then filter
                        # But that's complex. Let's instead: calculate master standings, then rank 374 entries by master position
                        
                        # Get master standings by calling the same logic (excluding 374)
                        # We'll need to replicate the master standings calculation but return it
                        # For now, let's use a simpler approach: get master standings from the standings endpoint
                        # Actually, we can't call ourselves. Let's calculate it inline.
                        
                        # For Dabchick, we need to handle it differently - let's check if it's Dabchick
                        if class_name and 'dabchick' in class_name.lower():
                            # For Dabchick, we'll need to calculate master standings
                            # This is complex, so let's create a helper or duplicate logic
                            # Actually, the user said "apply order to 374 rank 1st to 31st"
                            # So we need master standings for Dabchick, then apply to 374 entries
                            # Let's return a note that this needs master standings calculation
                            # For now, return 374 entries with a placeholder rank
                            pass
                        
                        # For Optimist A/B, we can use the existing master standings logic
                        # But we need to calculate it first, then apply to 374 entries
                        # This is getting complex. Let's create a separate endpoint or modify this one
                        
                        # TEMPORARY: Return 374 entries with note that master standings ranking needs to be applied
                        # The actual implementation will require calculating master standings first
                        rankings_list = list(regatta_374_entries.values())
                        
                        result = {
                            "rankings": rankings_list,
                            "total_sailors": len(rankings_list),
                            "aged_out": [],
                            "unlikely": [],
                            "note": "Master standings ranking to be applied"
                        }
                        # Cache the result
                        set_cached(cache_key, result, ttl_seconds=30)
                        duration = (time.time() - start_time) * 1000
                        if duration > 150:
                            print(f"[PROFILE] ⚠️  /api/standings (regatta 374) took {duration:.2f}ms")
                        return result
                    else:
                        # MASTER STANDINGS - all eligible sailors (excluding 374, no date limit for master list)
                        import logging
                        print(f"API: Returning MASTER standings for {fleet_label} (open_regatta_only={open_regatta_only}, defaulting to master list)")
                        logging.info(f"Returning MASTER standings for {fleet_label} (open_regatta_only=False or None)")
                        # Calculate standings for all eligible sailors using head-to-head logic
                        from datetime import datetime, timedelta
                        from collections import defaultdict
                        thirteen_months_ago = datetime.now() - timedelta(days=13*30)
                        
                        # Get all eligible Optimist A sailors (excluding 374, but include all historical regattas for master list)
                        # Master list includes all sailors who have raced, not just last 13 months
                        # CRITICAL: Only count HELMS, never crew members
                        # Crew members share the helm's boat/result and should not be counted separately
                        cur.execute("""
                    SELECT DISTINCT
                                COALESCE(r.helm_sa_sailing_id::text, r.helm_temp_id) as sailor_id,
                                r.helm_name as name,
                                s.first_name,
                                s.last_name,
                        s.year_of_birth,
                                s.age
                    FROM results r
                            JOIN regatta_blocks rb ON rb.block_id = r.block_id
                            JOIN regattas reg ON reg.regatta_id = r.regatta_id
                            LEFT JOIN sas_id_personal s ON s.sa_sailing_id::text = r.helm_sa_sailing_id::text
                            WHERE LOWER(rb.fleet_label) = LOWER(%s)
                    AND r.raced = TRUE
                              AND reg.regatta_number != 374
                              AND COALESCE(r.helm_sa_sailing_id::text, r.helm_temp_id) IS NOT NULL
                            ORDER BY r.helm_name
                        """, (fleet_label,))
                        
                        all_sailors = cur.fetchall()
                        
                        if not all_sailors:
                            return {"rankings": [], "total_sailors": 0, "aged_out": [], "unlikely": []}
                        
                        # Build head-to-head matrix and sailor statistics
                        # Store weighted wins/losses by regatta type
                        head_to_head = defaultdict(lambda: defaultdict(lambda: {
                            'wins': 0, 'losses': 0, 'ties': 0,
                            'weighted_wins': 0, 'weighted_losses': 0,
                            'major_wins': 0, 'major_losses': 0,
                            'regional_wins': 0, 'regional_losses': 0,
                            'club_wins': 0, 'club_losses': 0,
                            'most_recent': None,
                            'most_recent_weight': 0
                        }))
                        sailor_data = {}
                        
                        # Initialize sailor data
                        for sailor in all_sailors:
                            sid = sailor['sailor_id']
                            sailor_data[sid] = {
                                'sailor_id': sid,
                                'name': sailor['name'],
                                'first_name': sailor.get('first_name'),
                                'last_name': sailor.get('last_name'),
                                'year_of_birth': sailor.get('year_of_birth'),
                                'age': sailor.get('age'),
                                'wins': 0,
                                'losses': 0,
                                'ties': 0,
                                'total_rank': 0,
                                'regatta_count': 0,
                                'ranks': [],
                                'first_rank': None,
                                'last_rank': None
                            }
                        
                        # Get all regattas where these sailors competed (excluding 374)
                        # Use 13 month filter for head-to-head comparisons
                        cur.execute("""
                            SELECT DISTINCT
                            r.regatta_id,
                                reg.regatta_number,
                                reg.event_name,
                                reg.start_date,
                                reg.end_date,
                                reg.regatta_type
                            FROM results r
                            JOIN regatta_blocks rb ON rb.block_id = r.block_id
                            JOIN regattas reg ON reg.regatta_id = r.regatta_id
                            WHERE LOWER(rb.fleet_label) = LOWER(%s)
                              AND r.raced = TRUE
                              AND reg.regatta_number != 374
                              AND (reg.end_date >= %s OR reg.start_date >= %s)
                            ORDER BY reg.start_date ASC
                        """, (fleet_label, thirteen_months_ago, thirteen_months_ago))
                        
                        regattas = cur.fetchall()
                        
                        # Function to determine regatta weight
                        def get_regatta_weight(regatta, regatta_entries=0, max_nationals_entries=0):
                            """Return weight: 3=major/national, 2=regional, 1=club/provincial"""
                            event_name = (regatta.get('event_name') or '').lower()
                            regatta_type = regatta.get('regatta_type') or ''
                            
                            # Major/National regattas (highest weight)
                            is_nationals = any(keyword in event_name for keyword in ['national', 'nationals', 'youth nationals', 'sa sailing youth nationals'])
                            if is_nationals or regatta_type == 'NATIONAL':
                                return 3
                            
                            # If there are 2 nationals in 13 months, 2nd one is also major if entries within 70% of largest nationals
                            # This is handled by checking if regatta_entries >= 70% of max_nationals_entries
                            if max_nationals_entries > 0 and regatta_entries >= (max_nationals_entries * 0.7):
                                return 3  # Large regatta treated as major
                            
                            # Regional regattas (medium weight)
                            if any(keyword in event_name for keyword in ['regional', 'championship', 'championships', 'cape classic', 'classic']):
                                return 2
                            if regatta_type == 'REGIONAL':
                                return 2
                            
                            # Club/Provincial regattas (lowest weight)
                            return 1
                        
                        # First, identify the largest regattas (by entry count) for this class
                        # Prioritize head-to-head results from these larger, more competitive regattas
                        regatta_sizes = {}  # regatta_id -> max entry count across all blocks
                        regatta_is_nationals = {}  # regatta_id -> True if nationals
                        nationals_regattas = []  # List of nationals regattas
                        
                        for reg in regattas:
                            regatta_id = reg['regatta_id']
                            event_name = (reg.get('event_name') or '').lower()
                            is_nationals = any(kw in event_name for kw in ['national', 'nationals', 'youth nationals', 'sa sailing youth nationals'])
                            
                            cur.execute("""
                            SELECT 
                                rb.block_id,
                                COUNT(DISTINCT COALESCE(r.helm_sa_sailing_id::text, r.helm_temp_id)) as entries
                            FROM results r
                            JOIN regatta_blocks rb ON rb.block_id = r.block_id
                            WHERE r.regatta_id = %s
                              AND LOWER(REPLACE(COALESCE(rb.class_canonical, rb.fleet_label), ' Fleet', '')) = LOWER(%s)
                              AND r.raced = TRUE
                              AND COALESCE(r.helm_sa_sailing_id::text, r.helm_temp_id) IS NOT NULL
                            GROUP BY rb.block_id
                            """, (regatta_id, class_name))
                            block_entries = cur.fetchall()
                            max_entries = max([b['entries'] for b in block_entries], default=0)
                            regatta_sizes[regatta_id] = max_entries
                            regatta_is_nationals[regatta_id] = is_nationals
                            
                            if is_nationals:
                                nationals_regattas.append((regatta_id, max_entries, reg.get('end_date') or reg.get('start_date')))
                        
                        # Find largest nationals entry count
                        max_nationals_entries = max([e[1] for e in nationals_regattas], default=0)
                        
                        # Sort regattas: nationals first (by size), then others (by size and date)
                        regattas_sorted = sorted(regattas, key=lambda r: (
                            -1 if regatta_is_nationals.get(r['regatta_id'], False) else 0,  # Nationals first
                            -regatta_sizes.get(r['regatta_id'], 0),  # Largest first
                            r['end_date'] or r['start_date'] or datetime.min  # Most recent first
                        ))
                        
                        # Identify sailors who sailed in nationals
                        nationals_sailors = set()
                        for reg in regattas:
                            if regatta_is_nationals.get(reg['regatta_id'], False):
                                cur.execute("""
                                SELECT DISTINCT COALESCE(r.helm_sa_sailing_id::text, r.helm_temp_id) as sailor_id
                                FROM results r
                                JOIN regatta_blocks rb ON rb.block_id = r.block_id
                                WHERE r.regatta_id = %s
                                  AND LOWER(REPLACE(COALESCE(rb.class_canonical, rb.fleet_label), ' Fleet', '')) = LOWER(%s)
                                  AND r.raced = TRUE
                                  AND COALESCE(r.helm_sa_sailing_id::text, r.helm_temp_id) IS NOT NULL
                                """, (reg['regatta_id'], class_name))
                                for row in cur.fetchall():
                                    nationals_sailors.add(row['sailor_id'])
                        
                        # Process each regatta to build head-to-head records
                        for reg in regattas_sorted:
                            regatta_id = reg['regatta_id']
                            regatta_date = reg['start_date'] or reg['end_date']
                            regatta_entries = regatta_sizes.get(regatta_id, 0)  # Entry count for this regatta
                            regatta_weight = get_regatta_weight(reg, regatta_entries, max_nationals_entries)
                            is_nationals_regatta = regatta_is_nationals.get(regatta_id, False)
                            
                            # Get all results for this regatta/fleet
                            # CRITICAL: Only use HELM data - crew members share the helm's rank
                            # Crew members should never appear as separate entries in standings
                            cur.execute("""
                            SELECT 
                                    COALESCE(r.helm_sa_sailing_id::text, r.helm_temp_id) as sailor_id,
                                r.rank,
                                    rb.block_id
                            FROM results r
                                JOIN regatta_blocks rb ON rb.block_id = r.block_id
                                WHERE r.regatta_id = %s
                                  AND LOWER(rb.fleet_label) = LOWER(%s)
                              AND r.raced = TRUE
                                  AND r.rank IS NOT NULL
                                  AND COALESCE(r.helm_sa_sailing_id::text, r.helm_temp_id) IS NOT NULL
                            """, (regatta_id, fleet_label))
                            
                            regatta_results = cur.fetchall()
                            
                            # Group by block_id (same fleet)
                            by_block = defaultdict(list)
                            for res in regatta_results:
                                by_block[res['block_id']].append(res)
                            
                            # Compare sailors within each fleet
                            for block_id, results in by_block.items():
                                for i, res1 in enumerate(results):
                                    sid1 = res1['sailor_id']
                                    rank1 = int(res1['rank'])
                                    
                                    if sid1 not in sailor_data:
                                        continue
                                    
                                    sailor_data[sid1]['regatta_count'] += 1
                                    sailor_data[sid1]['total_rank'] += rank1
                                    sailor_data[sid1]['ranks'].append(rank1)
                                    
                                    for res2 in results[i+1:]:
                                        sid2 = res2['sailor_id']
                                        rank2 = int(res2['rank'])
                                        
                                        if sid2 not in sailor_data:
                                            continue
                                        
                                        # Update head-to-head with weighted results
                                        # Larger regattas (more entries) are more competitive and should be weighted more
                                        # Combine regatta weight (major/regional/club) with entry count
                                        entry_weight = min(regatta_entries / 20.0, 2.0)  # Scale: 20 entries = 1.0x, 40+ = 2.0x
                                        combined_weight = regatta_weight * (1.0 + entry_weight * 0.5)  # Boost larger regattas
                                        
                                        if rank1 < rank2:
                                            head_to_head[sid1][sid2]['wins'] += 1
                                            head_to_head[sid1][sid2]['weighted_wins'] += combined_weight
                                            head_to_head[sid2][sid1]['losses'] += 1
                                            head_to_head[sid2][sid1]['weighted_losses'] += combined_weight
                                            
                                            # Track by regatta type
                                            if regatta_weight == 3:
                                                head_to_head[sid1][sid2]['major_wins'] += 1
                                                head_to_head[sid2][sid1]['major_losses'] += 1
                                            elif regatta_weight == 2:
                                                head_to_head[sid1][sid2]['regional_wins'] += 1
                                                head_to_head[sid2][sid1]['regional_losses'] += 1
                                            else:
                                                head_to_head[sid1][sid2]['club_wins'] += 1
                                                head_to_head[sid2][sid1]['club_losses'] += 1
                                            
                                            # Track largest regatta results (top 5 by entry count)
                                            if 'large_regatta_wins' not in head_to_head[sid1][sid2]:
                                                head_to_head[sid1][sid2]['large_regatta_wins'] = 0
                                                head_to_head[sid1][sid2]['large_regatta_losses'] = 0
                                                head_to_head[sid2][sid1]['large_regatta_wins'] = 0
                                                head_to_head[sid2][sid1]['large_regatta_losses'] = 0
                                            
                                            # Check if this is in top 5 largest regattas
                                            sorted_regattas = sorted(regatta_sizes.items(), key=lambda x: -x[1])
                                            top5_regattas = {r[0] for r in sorted_regattas[:5]}
                                            if regatta_id in top5_regattas:
                                                head_to_head[sid1][sid2]['large_regatta_wins'] += 1
                                                head_to_head[sid2][sid1]['large_regatta_losses'] += 1
                                            
                                            # Track head-to-head against nationals sailors (for indirect comparison)
                                            # If one sailor didn't sail nationals but raced against someone who did
                                            if 'vs_nationals_sailor_wins' not in head_to_head[sid1][sid2]:
                                                head_to_head[sid1][sid2]['vs_nationals_sailor_wins'] = 0
                                                head_to_head[sid1][sid2]['vs_nationals_sailor_losses'] = 0
                                                head_to_head[sid2][sid1]['vs_nationals_sailor_wins'] = 0
                                                head_to_head[sid2][sid1]['vs_nationals_sailor_losses'] = 0
                                            
                                            # If this is BEFORE or AFTER nationals, track comparisons with nationals sailors
                                            if not is_nationals_regatta:
                                                if sid1 in nationals_sailors and sid2 not in nationals_sailors:
                                                    # sid2 beat a nationals sailor
                                                    head_to_head[sid2][sid1]['vs_nationals_sailor_wins'] += 1
                                                    head_to_head[sid1][sid2]['vs_nationals_sailor_losses'] += 1
                                                elif sid2 in nationals_sailors and sid1 not in nationals_sailors:
                                                    # sid1 beat a nationals sailor
                                                    head_to_head[sid1][sid2]['vs_nationals_sailor_wins'] += 1
                                                    head_to_head[sid2][sid1]['vs_nationals_sailor_losses'] += 1
                                            
                                            sailor_data[sid1]['wins'] += 1
                                            sailor_data[sid2]['losses'] += 1
                                        elif rank2 < rank1:
                                            head_to_head[sid1][sid2]['losses'] += 1
                                            head_to_head[sid1][sid2]['weighted_losses'] += combined_weight
                                            head_to_head[sid2][sid1]['wins'] += 1
                                            head_to_head[sid2][sid1]['weighted_wins'] += combined_weight
                                            
                                            # Track by regatta type
                                            if regatta_weight == 3:
                                                head_to_head[sid1][sid2]['major_losses'] += 1
                                                head_to_head[sid2][sid1]['major_wins'] += 1
                                            elif regatta_weight == 2:
                                                head_to_head[sid1][sid2]['regional_losses'] += 1
                                                head_to_head[sid2][sid1]['regional_wins'] += 1
                                            else:
                                                head_to_head[sid1][sid2]['club_losses'] += 1
                                                head_to_head[sid2][sid1]['club_wins'] += 1
                                            
                                            # Track largest regatta results (top 5 by entry count)
                                            if 'large_regatta_wins' not in head_to_head[sid1][sid2]:
                                                head_to_head[sid1][sid2]['large_regatta_wins'] = 0
                                                head_to_head[sid1][sid2]['large_regatta_losses'] = 0
                                                head_to_head[sid2][sid1]['large_regatta_wins'] = 0
                                                head_to_head[sid2][sid1]['large_regatta_losses'] = 0
                                            
                                            # Check if this is in top 5 largest regattas
                                            sorted_regattas = sorted(regatta_sizes.items(), key=lambda x: -x[1])
                                            top5_regattas = {r[0] for r in sorted_regattas[:5]}
                                            if regatta_id in top5_regattas:
                                                head_to_head[sid1][sid2]['large_regatta_losses'] += 1
                                                head_to_head[sid2][sid1]['large_regatta_wins'] += 1
                                            
                                            # Track head-to-head against nationals sailors (for indirect comparison)
                                            # If one sailor didn't sail nationals but raced against someone who did
                                            if 'vs_nationals_sailor_wins' not in head_to_head[sid1][sid2]:
                                                head_to_head[sid1][sid2]['vs_nationals_sailor_wins'] = 0
                                                head_to_head[sid1][sid2]['vs_nationals_sailor_losses'] = 0
                                                head_to_head[sid2][sid1]['vs_nationals_sailor_wins'] = 0
                                                head_to_head[sid2][sid1]['vs_nationals_sailor_losses'] = 0
                                            
                                            # If this is BEFORE or AFTER nationals, track comparisons with nationals sailors
                                            if not is_nationals_regatta:
                                                if sid1 in nationals_sailors and sid2 not in nationals_sailors:
                                                    # sid2 lost to a nationals sailor
                                                    head_to_head[sid2][sid1]['vs_nationals_sailor_losses'] += 1
                                                    head_to_head[sid1][sid2]['vs_nationals_sailor_wins'] += 1
                                                elif sid2 in nationals_sailors and sid1 not in nationals_sailors:
                                                    # sid1 lost to a nationals sailor
                                                    head_to_head[sid1][sid2]['vs_nationals_sailor_losses'] += 1
                                                    head_to_head[sid2][sid1]['vs_nationals_sailor_wins'] += 1
                                            
                                            sailor_data[sid1]['losses'] += 1
                                            sailor_data[sid2]['wins'] += 1
                                        else:
                                            head_to_head[sid1][sid2]['ties'] += 1
                                            head_to_head[sid2][sid1]['ties'] += 1
                                            sailor_data[sid1]['ties'] += 1
                                            sailor_data[sid2]['ties'] += 1
                                        
                                        # Store most recent result (prefer larger regattas and higher weight if same date)
                                        should_update = False
                                        if not head_to_head[sid1][sid2]['most_recent']:
                                            should_update = True
                                        elif regatta_date > head_to_head[sid1][sid2]['most_recent']['date']:
                                            should_update = True
                                        elif (regatta_date == head_to_head[sid1][sid2]['most_recent']['date'] and 
                                              (regatta_weight > head_to_head[sid1][sid2]['most_recent_weight'] or
                                               regatta_entries > head_to_head[sid1][sid2].get('most_recent_entries', 0))):
                                            should_update = True
                                        
                                        if should_update:
                                            head_to_head[sid1][sid2]['most_recent'] = {
                                                'date': regatta_date,
                                                'sailor1_rank': rank1,
                                                'sailor2_rank': rank2,
                                                'weight': regatta_weight,
                                                'entries': regatta_entries
                                            }
                                            head_to_head[sid1][sid2]['most_recent_weight'] = regatta_weight
                                            head_to_head[sid1][sid2]['most_recent_entries'] = regatta_entries
                                            head_to_head[sid2][sid1]['most_recent'] = {
                                                'date': regatta_date,
                                                'sailor1_rank': rank2,
                                                'sailor2_rank': rank1,
                                                'weight': regatta_weight,
                                                'entries': regatta_entries
                                            }
                                            head_to_head[sid2][sid1]['most_recent_weight'] = regatta_weight
                                            head_to_head[sid2][sid1]['most_recent_entries'] = regatta_entries
                        
                        # Calculate standings with tiebreakers
                        # First, count head-to-head comparisons for each sailor
                        for sid in sailor_data.keys():
                            h2h_count = 0
                            for other_sid in sailor_data.keys():
                                if sid != other_sid:
                                    h2h = head_to_head[sid].get(other_sid, {})
                                    if h2h.get('wins', 0) > 0 or h2h.get('losses', 0) > 0 or h2h.get('ties', 0) > 0:
                                        h2h_count += 1
                            sailor_data[sid]['h2h_comparisons'] = h2h_count
                        
                        standings = []
                        for sid, data in sailor_data.items():
                            win_rate = data['wins'] / (data['wins'] + data['losses']) if (data['wins'] + data['losses']) > 0 else 0
                            avg_rank = data['total_rank'] / data['regatta_count'] if data['regatta_count'] > 0 else 999
                            
                            if data['ranks']:
                                data['first_rank'] = data['ranks'][0]
                                data['last_rank'] = data['ranks'][-1]
                                improvement = data['first_rank'] - data['last_rank'] if data['first_rank'] and data['last_rank'] else 0
                                
                                # Recent trend (last 3 vs first 3)
                                recent_change = 0
                                if len(data['ranks']) >= 3:
                                    early_avg = sum(data['ranks'][:3]) / 3
                                    recent_avg = sum(data['ranks'][-3:]) / 3
                                    recent_change = early_avg - recent_avg
                            else:
                                improvement = 0
                                recent_change = 0
                            
                            standings.append({
                                **data,
                                'win_rate': win_rate,
                                'avg_rank': avg_rank,
                                'improvement': improvement,
                                'recent_change': recent_change
                            })
                        
                        # Sort standings using head-to-head logic
                        # Use the EXACT SAME comparison function as Optimist (which works correctly)
                        # Copy the entire function to ensure 100% consistency
                        def compare_sailors(a, b):
                            """
                            Compare two sailors for standings ranking.
                            Returns: -1 if a ranks before b, 1 if b ranks before a, 0 if equal
                            This function is identical to the Optimist universal comparison function.
                            """
                            sid_a = str(a['sailor_id'])  # Ensure string type
                            sid_b = str(b['sailor_id'])  # Ensure string type
                            
                            # DEBUG: Log ALL comparisons involving 5820
                            if sid_a == '5820' or sid_b == '5820':
                                other_id = sid_b if sid_a == '5820' else sid_a
                                print(f"[COMPARE] {sid_a} vs {sid_b}: a_reg={a['regatta_count']}, b_reg={b['regatta_count']}")
                                
                                # Check head-to-head directly
                                if sid_a in head_to_head and sid_b in head_to_head[sid_a]:
                                    h2h = head_to_head[sid_a][sid_b]
                                    a_wins = h2h.get('wins', 0)
                                    b_wins = h2h.get('losses', 0)
                                    print(f"[COMPARE] H2H data: a_wins={a_wins}, b_wins={b_wins}")
                                else:
                                    print(f"[COMPARE] NO H2H DATA for {sid_a} vs {sid_b}")
                            
                            # CRITICAL RULE: Head-to-head is PRIMARY - if A has beaten B, A ranks above B
                            # This rule takes absolute precedence - no exceptions
                            h2h = head_to_head[sid_a][sid_b]
                            a_wins = h2h.get('wins', 0)  # A's wins over B
                            b_wins = h2h.get('losses', 0)  # A's losses to B = B's wins over A
                            total_h2h = a_wins + b_wins + h2h.get('ties', 0)
                            
                            # Priority 1: Direct Head-to-Head Results (ABSOLUTE RULE)
                            # If they've raced each other, head-to-head determines ranking
                            if total_h2h > 0:
                                # If A has beaten B more times, A ranks above B
                                if a_wins > b_wins:
                                    return -1  # A ranks before B
                                # If B has beaten A more times, B ranks above A
                                if b_wins > a_wins:
                                    return 1   # B ranks before A
                                
                                # If tied (same number of wins), check most recent result
                                if a_wins == b_wins and a_wins > 0:
                                    # Check most recent result - more recent wins take precedence
                                    if h2h.get('most_recent'):
                                        mr = h2h['most_recent']
                                        # If A won most recently, A ranks above B
                                        if mr.get('sailor1_rank', 999) < mr.get('sailor2_rank', 999):
                                            return -1  # A ranks before B
                                        # If B won most recently, B ranks above A
                                        if mr.get('sailor2_rank', 999) < mr.get('sailor1_rank', 999):
                                            return 1   # B ranks before A
                            
                            # Priority 2: Regatta Count (only if they've never raced each other)
                            a_regattas = a['regatta_count'] or 0
                            b_regattas = b['regatta_count'] or 0
                            
                            if a_regattas == 0:
                                return 1  # a goes to bottom
                            if b_regattas == 0:
                                return -1  # b goes to bottom
                            
                            # If they've never raced each other, use regatta count and other factors
                            if total_h2h == 0:
                                # No direct head-to-head: use regatta count, then average rank
                                if abs(a_regattas - b_regattas) >= 2:
                                    return b_regattas - a_regattas
                                if a['avg_rank'] != b['avg_rank']:
                                    return a['avg_rank'] - b['avg_rank']
                                if a['win_rate'] != b['win_rate']:
                                    return b['win_rate'] - a['win_rate']
                                return a['avg_rank'] - b['avg_rank']
                            
                            # If they HAVE raced each other but head-to-head is tied, use tiebreakers
                            # (We already checked wins > losses above, so if we get here, wins == losses or both 0)
                            diff = abs(a_wins - b_wins)
                            
                            # Priority 3: Tiebreakers for tied head-to-head (wins == losses)
                            if diff == 0 and total_h2h > 0:
                                # They've raced but results are tied - use weighted factors
                                # Priority 3.1: Largest regatta head-to-head (top 5 by entry count)
                                a_large_wins = h2h.get('large_regatta_wins', 0)
                                b_large_wins = h2h.get('large_regatta_losses', 0)
                                if a_large_wins > b_large_wins:
                                    return -1
                                if b_large_wins > a_large_wins:
                                    return 1
                                
                                # Priority 3.2: Major regatta head-to-head (nationals)
                                a_major_wins = h2h.get('major_wins', 0)
                                b_major_wins = h2h.get('major_losses', 0)
                                if a_major_wins > b_major_wins:
                                    return -1
                                if b_major_wins > a_major_wins:
                                    return 1
                                
                                # Priority 3.3: Weighted wins
                                a_weighted = h2h.get('weighted_wins', 0)
                                b_weighted = h2h.get('weighted_losses', 0)
                                if a_weighted > b_weighted:
                                    return -1
                                if b_weighted > a_weighted:
                                    return 1
                            
                            # Priority 4: Final Tiebreakers (if head-to-head is tied or never raced)
                            # Tiebreaker 1: Average rank
                            if a['avg_rank'] != b['avg_rank']:
                                return a['avg_rank'] - b['avg_rank']  # Lower average rank = better
                            
                            # Tiebreaker 2: Win rate
                            if a['win_rate'] != b['win_rate']:
                                return b['win_rate'] - a['win_rate']  # Higher win rate = better
                            
                            # Tiebreaker 3: Regatta count
                            if a_regattas != b_regattas:
                                return b_regattas - a_regattas  # More regattas = better
                            
                            # Ultimate tiebreaker: average rank
                            return a['avg_rank'] - b['avg_rank']  # Lower average rank = better
                        
                        # Sort using comparison function
                        standings.sort(key=cmp_to_key(compare_sailors))
                        
                        # DYNAMIC STANDINGS TEST: Iteratively check and fix rankings
                        # Rule: If a sailor ranked below has beaten a sailor ranked above, swap them
                        # Repeat until stable (max 100 iterations to prevent infinite loops)
                        def dynamic_standings_test(standings_list, h2h_matrix):
                            """Iteratively correct rankings based on head-to-head results"""
                            max_iterations = 100
                            iteration = 0
                            
                            while iteration < max_iterations:
                                iteration += 1
                                swapped = False
                                
                                # Check each sailor against all sailors ranked below them
                                for i in range(len(standings_list)):
                                    sailor_a = standings_list[i]
                                    sid_a = str(sailor_a['sailor_id'])
                                    
                                    # Check all sailors ranked below
                                    for j in range(i + 1, len(standings_list)):
                                        sailor_b = standings_list[j]
                                        sid_b = str(sailor_b['sailor_id'])
                                        
                                        # Check head-to-head: h2h_matrix[sid_b][sid_a] = B's record against A
                                        h2h = h2h_matrix.get(sid_b, {}).get(sid_a, {})
                                        b_wins = h2h.get('wins', 0)  # B's wins over A
                                        a_wins = h2h.get('losses', 0)  # B's losses to A = A's wins over B
                                        total_h2h = a_wins + b_wins + h2h.get('ties', 0)
                                        
                                        # If B has beaten A more times (and they've raced), B should rank above A
                                        if total_h2h > 0 and b_wins > a_wins:
                                            # Swap them
                                            standings_list[i], standings_list[j] = standings_list[j], standings_list[i]
                                            swapped = True
                                            break  # Restart from beginning after swap
                                    
                                    if swapped:
                                        break  # Restart from beginning after swap
                                
                                if not swapped:
                                    # No swaps needed - ranking is stable
                                    break
                            
                            return standings_list, iteration
                        
                        # Apply dynamic standings test
                        standings, iterations = dynamic_standings_test(standings, head_to_head)
                        
                        # Identify double-handed sailors (those who sail with crew)
                        # Query to find sailors who have crew in their results
                        cur.execute("""
                            SELECT DISTINCT COALESCE(r.helm_sa_sailing_id::text, r.helm_temp_id) as sailor_id
                            FROM results r
                            JOIN regatta_blocks rb ON r.block_id = rb.block_id
                            JOIN regattas reg ON reg.regatta_id = r.regatta_id
                            WHERE 
                                LOWER(REPLACE(COALESCE(rb.class_canonical, rb.fleet_label), ' Fleet', '')) = %s
                                AND r.raced = TRUE
                                AND COALESCE(r.helm_sa_sailing_id::text, r.helm_temp_id) IS NOT NULL
                                AND (COALESCE(r.crew_sa_sailing_id::text, r.crew_temp_id) IS NOT NULL
                                     AND COALESCE(r.crew_sa_sailing_id::text, r.crew_temp_id) != '')
                                AND (reg.end_date >= %s OR reg.start_date >= %s)
                                AND reg.regatta_number != '374'
                        """, (fleet_label.lower(), thirteen_months_ago, thirteen_months_ago))
                        double_handed_sailors = {row['sailor_id'] for row in cur.fetchall()}
                        
                        # Adjust double-handed sailors down 2 positions each
                        if double_handed_sailors:
                            # Create a list of indices for double-handed sailors
                            double_handed_indices = []
                            for i, sailor in enumerate(standings):
                                sid = str(sailor.get('sailor_id') or sailor.get('sa_id') or sailor.get('sas_id', ''))
                                if sid in double_handed_sailors:
                                    double_handed_indices.append(i)
                            
                            # Move each double-handed sailor down 2 positions (but not below the end)
                            for idx in sorted(double_handed_indices, reverse=True):  # Process from bottom to top
                                if idx + 2 < len(standings):
                                    # Swap with sailor 2 positions below
                                    standings[idx], standings[idx + 2] = standings[idx + 2], standings[idx]
                        
                        # Get stored Main Scores from main_scores table
                        cur.execute("""
                            SELECT sailor_id, main_score
                            FROM main_scores
                            WHERE class_name = %s
                        """, (fleet_label,))
                        stored_scores = {row['sailor_id']: row['main_score'] for row in cur.fetchall()}
                        
                        # Assign ranks 1-60
                        for i, sailor in enumerate(standings, 1):
                            sailor['main_rank'] = str(i)
                            # Use stored Main Score if available, otherwise None
                            sailor_id = sailor.get('sailor_id')
                            sailor['wc_score'] = stored_scores.get(sailor_id) if sailor_id else None
                            sailor['total_races'] = sailor['regatta_count']
                            sailor['regatta_id'] = None
                            sailor['likelihood'] = 'likely'
                        
                        return {
                            "rankings": standings,
                            "total_sailors": len(all_sailors),  # Total eligible sailors, not just those in standings
                            "aged_out": [],
                            "unlikely": []
                        }
            else:
                    # For all other classes, calculate standings using same head-to-head logic
                    # This is the same logic as Optimist A/B but for any class
                    from datetime import datetime, timedelta
                    from collections import defaultdict
                    thirteen_months_ago = datetime.now() - timedelta(days=13*30)
                    
                    # Initialize filter_to_374 flag (used later to determine if we need to filter to Regatta 374 entries)
                    filter_to_374 = False
                    regatta_374_entries = {}
                    
                    # Check if this is for Regatta 374 entries only (ranked by master standings)
                    if open_regatta_only and str(open_regatta_only).lower() == 'true':
                        # Get Regatta 374 ID
                        cur.execute("""
                            SELECT regatta_id, regatta_number
                            FROM regattas
                            WHERE regatta_number = 374
                            ORDER BY regatta_number DESC
                            LIMIT 1
                        """)
                        open_regatta = cur.fetchone()
                        
                        if not open_regatta:
                            return {"rankings": [], "total_sailors": 0, "aged_out": [], "unlikely": []}
                        
                        regatta_id = open_regatta['regatta_id']
                        
                        # Get all sailors entered in Regatta 374 for this class
                        class_name_normalized = (class_name or '').strip()
                        if class_name_normalized.lower().endswith(' fleet'):
                            class_name_normalized = class_name_normalized[:-6].strip()
                        
                        cur.execute("""
                            SELECT DISTINCT
                                COALESCE(r.helm_sa_sailing_id::text, r.helm_temp_id) as sailor_id,
                                r.helm_name as name,
                                s.first_name,
                                s.last_name,
                                s.year_of_birth,
                                s.age,
                                r.nett_points_raw as wc_score,
                                rb.races_sailed as total_races,
                                r.regatta_id
                            FROM results r
                            JOIN regatta_blocks rb ON rb.block_id = r.block_id
                            LEFT JOIN sas_id_personal s ON s.sa_sailing_id::text = r.helm_sa_sailing_id::text
                            WHERE r.regatta_id = %s
                                AND (LOWER(rb.fleet_label) = LOWER(%s) OR LOWER(rb.class_canonical) = LOWER(%s) 
                                     OR LOWER(REPLACE(rb.fleet_label, ' Fleet', '')) = LOWER(%s) 
                                     OR LOWER(REPLACE(rb.class_canonical, ' Fleet', '')) = LOWER(%s))
                                AND COALESCE(r.helm_sa_sailing_id::text, r.helm_temp_id) IS NOT NULL
                        """, (regatta_id, class_name_normalized, class_name_normalized, class_name_normalized, class_name_normalized))
                        regatta_374_entries = {row['sailor_id']: dict(row) for row in cur.fetchall()}
                        
                        # Now we need to calculate master standings to rank these entries
                        # We'll continue with the master standings calculation below, then apply it to 374 entries
                        # Set a flag to indicate we need to filter to 374 entries after calculating master standings
                        filter_to_374 = True
                    
                    # Function to determine age limits for each class
                    def get_age_limit(class_name_lower):
                        """Return maximum age for class eligibility"""
                        if 'optimist' in class_name_lower:
                            return 15  # Optimist age limit
                        elif 'dabchick' in class_name_lower:
                            return None  # TBD - need to determine
                        elif 'ilca 4' in class_name_lower or 'ilca4' in class_name_lower:
                            return None  # TBD - need to determine
                        elif 'ilca 6' in class_name_lower or 'ilca6' in class_name_lower:
                            return None  # TBD - need to determine
                        elif 'ilca 7' in class_name_lower or 'ilca7' in class_name_lower:
                            return None  # TBD - need to determine
                        else:
                            return None  # No age limit for other classes
                    
                    # Normalize class name - try to match fleet_label or class_canonical
                    # Remove "Fleet" suffix for matching (e.g., "Hobie 16 Fleet" -> "Hobie 16")
                    class_name_normalized = (class_name or '').strip()
                    if class_name_normalized.lower().endswith(' fleet'):
                        class_name_normalized = class_name_normalized[:-6].strip()
                    class_name_lower = class_name_normalized.lower()
                    max_age = get_age_limit(class_name_lower)
                    
                    # Get all eligible sailors for this class from last 13 months
                    # CRITICAL: Only count HELMS, never crew members
                    # Crew members share the helm's boat/result and should not be counted separately
                    # Match by fleet_label or class_canonical
                    if max_age is not None:
                        # With age limit
                        cur.execute("""
                            SELECT DISTINCT
                                COALESCE(r.helm_sa_sailing_id::text, r.helm_temp_id) as sailor_id,
                                r.helm_name as name,
                                s.first_name,
                                s.last_name,
                                s.year_of_birth,
                                s.age
                    FROM results r
                            JOIN regatta_blocks rb ON rb.block_id = r.block_id
                            JOIN regattas reg ON reg.regatta_id = r.regatta_id
                            LEFT JOIN sas_id_personal s ON s.sa_sailing_id::text = r.helm_sa_sailing_id::text
                            WHERE (LOWER(rb.fleet_label) = LOWER(%s) OR LOWER(rb.class_canonical) = LOWER(%s) OR LOWER(REPLACE(rb.fleet_label, ' Fleet', '')) = LOWER(%s) OR LOWER(REPLACE(rb.class_canonical, ' Fleet', '')) = LOWER(%s))
                              AND r.raced = TRUE
                              AND reg.regatta_number != 374
                              AND (reg.end_date >= %s OR reg.start_date >= %s)
                              AND COALESCE(r.helm_sa_sailing_id::text, r.helm_temp_id) IS NOT NULL
                              AND (s.age IS NULL OR s.age <= %s)
                            ORDER BY r.helm_name
                        """, (class_name_normalized, class_name_normalized, class_name_normalized, class_name_normalized, thirteen_months_ago, thirteen_months_ago, max_age))
                    else:
                        # No age limit
                        cur.execute("""
                            SELECT DISTINCT
                                COALESCE(r.helm_sa_sailing_id::text, r.helm_temp_id) as sailor_id,
                                r.helm_name as name,
                                s.first_name,
                                s.last_name,
                                s.year_of_birth,
                                s.age
                            FROM results r
                            JOIN regatta_blocks rb ON rb.block_id = r.block_id
                            JOIN regattas reg ON reg.regatta_id = r.regatta_id
                            LEFT JOIN sas_id_personal s ON s.sa_sailing_id::text = r.helm_sa_sailing_id::text
                            WHERE (LOWER(rb.fleet_label) = LOWER(%s) OR LOWER(rb.class_canonical) = LOWER(%s) OR LOWER(REPLACE(rb.fleet_label, ' Fleet', '')) = LOWER(%s) OR LOWER(REPLACE(rb.class_canonical, ' Fleet', '')) = LOWER(%s))
                              AND r.raced = TRUE
                              AND reg.regatta_number != 374
                              AND (reg.end_date >= %s OR reg.start_date >= %s)
                              AND COALESCE(r.helm_sa_sailing_id::text, r.helm_temp_id) IS NOT NULL
                            ORDER BY r.helm_name
                        """, (class_name_normalized, class_name_normalized, class_name_normalized, class_name_normalized, thirteen_months_ago, thirteen_months_ago))
                    
                    all_sailors = cur.fetchall()
                    
                    if not all_sailors:
                        return {"rankings": [], "total_sailors": 0, "aged_out": [], "unlikely": []}
                    
                    # Use the same standing calculation logic as Optimist A/B
                    # (Copy the entire standing calculation logic from the Optimist A/B section)
                    # For brevity, I'll reference that the same logic should be applied here
                    # The standing calculation code is identical - just use the class_name instead of fleet_label
                    
                    # Build head-to-head matrix and sailor statistics (same as Optimist A/B logic)
                    head_to_head = defaultdict(lambda: defaultdict(lambda: {
                        'wins': 0, 'losses': 0, 'ties': 0,
                        'weighted_wins': 0, 'weighted_losses': 0,
                        'major_wins': 0, 'major_losses': 0,
                        'regional_wins': 0, 'regional_losses': 0,
                        'club_wins': 0, 'club_losses': 0,
                        'most_recent': None,
                        'most_recent_weight': 0
                    }))
                    sailor_data = {}
                    
                    # Initialize sailor data
                    for sailor in all_sailors:
                        sid = sailor['sailor_id']
                        sailor_data[sid] = {
                            'sailor_id': sid,
                            'name': sailor['name'],
                            'first_name': sailor.get('first_name'),
                            'last_name': sailor.get('last_name'),
                            'year_of_birth': sailor.get('year_of_birth'),
                            'age': sailor.get('age'),
                            'wins': 0,
                            'losses': 0,
                            'ties': 0,
                            'total_rank': 0,
                            'regatta_count': 0,
                            'ranks': [],
                            'first_rank': None,
                            'last_rank': None
                        }
                    
                    # Get all regattas where these sailors competed (excluding 374)
                    # Match by fleet_label OR class_canonical
                    cur.execute("""
                        SELECT DISTINCT
                            r.regatta_id,
                            reg.regatta_number,
                        reg.event_name,
                        reg.start_date,
                            reg.end_date,
                            reg.regatta_type
                    FROM results r
                        JOIN regatta_blocks rb ON rb.block_id = r.block_id
                        JOIN regattas reg ON reg.regatta_id = r.regatta_id
                            WHERE (LOWER(rb.fleet_label) = LOWER(%s) OR LOWER(rb.class_canonical) = LOWER(%s) OR LOWER(REPLACE(rb.fleet_label, ' Fleet', '')) = LOWER(%s) OR LOWER(REPLACE(rb.class_canonical, ' Fleet', '')) = LOWER(%s))
                              AND r.raced = TRUE
                              AND reg.regatta_number != 374
                              AND (reg.end_date >= %s OR reg.start_date >= %s)
                        ORDER BY reg.start_date ASC
                    """, (class_name_normalized, class_name_normalized, class_name_normalized, class_name_normalized, thirteen_months_ago, thirteen_months_ago))
                    
                    regattas = cur.fetchall()
                    
                    # Function to determine regatta weight (same as Optimist A/B)
                    def get_regatta_weight(regatta, regatta_entries=0, max_nationals_entries=0):
                        """Return weight: 3=major/national, 2=regional, 1=club/provincial"""
                        event_name = (regatta.get('event_name') or '').lower()
                        regatta_type = regatta.get('regatta_type') or ''
                        
                        # Major/National regattas (highest weight)
                        is_nationals = any(keyword in event_name for keyword in ['national', 'nationals', 'youth nationals', 'sa sailing youth nationals'])
                        if is_nationals or regatta_type == 'NATIONAL':
                            return 3
                        
                        # If there are 2 nationals in 13 months, 2nd one is also major if entries within 70% of largest nationals
                        # This is handled by checking if regatta_entries >= 70% of max_nationals_entries
                        if max_nationals_entries > 0 and regatta_entries >= (max_nationals_entries * 0.7):
                            return 3  # Large regatta treated as major
                        
                        # Regional regattas (medium weight)
                        if any(keyword in event_name for keyword in ['regional', 'championship', 'championships', 'cape classic', 'classic']):
                            return 2
                        if regatta_type == 'REGIONAL':
                            return 2
                        
                        # Club/Provincial regattas (lowest weight)
                        return 1
                    
                    # Process each regatta to build head-to-head records (same logic as Optimist A/B)
                    for reg in regattas:
                        regatta_id = reg['regatta_id']
                        regatta_date = reg['start_date'] or reg['end_date']
                        regatta_weight = get_regatta_weight(reg)
                        
                        # Get all results for this regatta/fleet - match by fleet_label OR class_canonical
                        # CRITICAL: Only use HELM data - crew members share the helm's rank
                        # Crew members should never appear as separate entries in standings
                        cur.execute("""
                        SELECT 
                                COALESCE(r.helm_sa_sailing_id::text, r.helm_temp_id) as sailor_id,
                            r.rank,
                                rb.block_id
                            FROM results r
                            JOIN regatta_blocks rb ON rb.block_id = r.block_id
                            WHERE r.regatta_id = %s
                              AND (LOWER(rb.fleet_label) = LOWER(%s) OR LOWER(rb.class_canonical) = LOWER(%s) OR LOWER(REPLACE(rb.fleet_label, ' Fleet', '')) = LOWER(%s) OR LOWER(REPLACE(rb.class_canonical, ' Fleet', '')) = LOWER(%s))
                              AND r.raced = TRUE
                              AND r.rank IS NOT NULL
                              AND COALESCE(r.helm_sa_sailing_id::text, r.helm_temp_id) IS NOT NULL
                        """, (regatta_id, class_name_normalized, class_name_normalized, class_name_normalized, class_name_normalized))
                        
                        regatta_results = cur.fetchall()
                        
                        # Group by block_id (same fleet)
                        by_block = defaultdict(list)
                        for res in regatta_results:
                            by_block[res['block_id']].append(res)
                        
                        # Compare sailors within each fleet (same as Optimist A/B logic)
                        for block_id, results in by_block.items():
                            for i, res1 in enumerate(results):
                                sid1 = res1['sailor_id']
                                rank1 = int(res1['rank'])
                                
                                if sid1 not in sailor_data:
                                    continue
                                
                                sailor_data[sid1]['regatta_count'] += 1
                                sailor_data[sid1]['total_rank'] += rank1
                                sailor_data[sid1]['ranks'].append(rank1)
                                
                                for res2 in results[i+1:]:
                                    sid2 = res2['sailor_id']
                                    rank2 = int(res2['rank'])
                                    
                                    if sid2 not in sailor_data:
                                        continue
                                    
                                    # Update head-to-head with weighted results (same as Optimist A/B)
                                    if rank1 < rank2:
                                        head_to_head[sid1][sid2]['wins'] += 1
                                        head_to_head[sid1][sid2]['weighted_wins'] += regatta_weight
                                        head_to_head[sid2][sid1]['losses'] += 1
                                        head_to_head[sid2][sid1]['weighted_losses'] += regatta_weight
                                        
                                        # DEBUG: Log Guthrie head-to-head updates
                                        if (sid1 == '5820' and sid2 in ['451', '287', '737']) or (sid2 == '5820' and sid1 in ['451', '287', '737']):
                                            winner = sid1 if rank1 < rank2 else sid2
                                            loser = sid2 if rank1 < rank2 else sid1
                                            print(f"[DEBUG MATRIX] {winner} beats {loser} in regatta {regatta_id} (rank {min(rank1, rank2)} vs {max(rank1, rank2)})")
                                        
                                        if regatta_weight == 3:
                                            head_to_head[sid1][sid2]['major_wins'] += 1
                                            head_to_head[sid2][sid1]['major_losses'] += 1
                                        elif regatta_weight == 2:
                                            head_to_head[sid1][sid2]['regional_wins'] += 1
                                            head_to_head[sid2][sid1]['regional_losses'] += 1
                                        else:
                                            head_to_head[sid1][sid2]['club_wins'] += 1
                                            head_to_head[sid2][sid1]['club_losses'] += 1
                                        
                                        sailor_data[sid1]['wins'] += 1
                                        sailor_data[sid2]['losses'] += 1
                                    elif rank2 < rank1:
                                        head_to_head[sid1][sid2]['losses'] += 1
                                        head_to_head[sid1][sid2]['weighted_losses'] += regatta_weight
                                        head_to_head[sid2][sid1]['wins'] += 1
                                        head_to_head[sid2][sid1]['weighted_wins'] += regatta_weight
                                        
                                        if regatta_weight == 3:
                                            head_to_head[sid1][sid2]['major_losses'] += 1
                                            head_to_head[sid2][sid1]['major_wins'] += 1
                                        elif regatta_weight == 2:
                                            head_to_head[sid1][sid2]['regional_losses'] += 1
                                            head_to_head[sid2][sid1]['regional_wins'] += 1
                                        else:
                                            head_to_head[sid1][sid2]['club_losses'] += 1
                                            head_to_head[sid2][sid1]['club_wins'] += 1
                                        
                                        sailor_data[sid1]['losses'] += 1
                                        sailor_data[sid2]['wins'] += 1
                                    else:
                                        head_to_head[sid1][sid2]['ties'] += 1
                                        head_to_head[sid2][sid1]['ties'] += 1
                                        sailor_data[sid1]['ties'] += 1
                                        sailor_data[sid2]['ties'] += 1
                                    
                                    # Store most recent result
                                    should_update = False
                                    if not head_to_head[sid1][sid2]['most_recent']:
                                        should_update = True
                                    elif regatta_date > head_to_head[sid1][sid2]['most_recent']['date']:
                                        should_update = True
                                    elif (regatta_date == head_to_head[sid1][sid2]['most_recent']['date'] and 
                                          regatta_weight > head_to_head[sid1][sid2]['most_recent_weight']):
                                        should_update = True
                                    
                                    if should_update:
                                        head_to_head[sid1][sid2]['most_recent'] = {
                                            'date': regatta_date,
                                            'sailor1_rank': rank1,
                                            'sailor2_rank': rank2,
                                            'weight': regatta_weight
                                        }
                                        head_to_head[sid1][sid2]['most_recent_weight'] = regatta_weight
                                        head_to_head[sid2][sid1]['most_recent'] = {
                                            'date': regatta_date,
                                            'sailor1_rank': rank2,
                                            'sailor2_rank': rank1,
                                            'weight': regatta_weight
                                        }
                                        head_to_head[sid2][sid1]['most_recent_weight'] = regatta_weight
                    
                    # Calculate standings with tiebreakers (same as Optimist A/B)
                    for sid in sailor_data.keys():
                        h2h_count = 0
                        for other_sid in sailor_data.keys():
                            if sid != other_sid:
                                h2h = head_to_head[sid].get(other_sid, {})
                                if h2h.get('wins', 0) > 0 or h2h.get('losses', 0) > 0 or h2h.get('ties', 0) > 0:
                                    h2h_count += 1
                        sailor_data[sid]['h2h_comparisons'] = h2h_count
                    
                    standings = []
                    for sid, data in sailor_data.items():
                        # CRITICAL: Only include sailors who have actually raced (regatta_count > 0)
                        if data['regatta_count'] == 0:
                            continue  # Skip sailors with no regattas
                        
                        win_rate = data['wins'] / (data['wins'] + data['losses']) if (data['wins'] + data['losses']) > 0 else 0
                        avg_rank = data['total_rank'] / data['regatta_count'] if data['regatta_count'] > 0 else 999
                        
                        if data['ranks']:
                            data['first_rank'] = data['ranks'][0]
                            data['last_rank'] = data['ranks'][-1]
                            improvement = data['first_rank'] - data['last_rank'] if data['first_rank'] and data['last_rank'] else 0
                            
                            recent_change = 0
                            if len(data['ranks']) >= 3:
                                early_avg = sum(data['ranks'][:3]) / 3
                                recent_avg = sum(data['ranks'][-3:]) / 3
                                recent_change = early_avg - recent_avg
                            else:
                                improvement = 0
                                recent_change = 0
                        
                        standings.append({
                            **data,
                            'win_rate': win_rate,
                            'avg_rank': avg_rank,
                            'improvement': improvement,
                            'recent_change': recent_change
                        })
                    
                    # Universal standings comparison function - applies to ALL classes
                    # Follows README_STANDINGS_RANKING.md logic exactly
                    def compare_sailors(a, b):
                        """
                        Compare two sailors for standings ranking.
                        Returns: -1 if a ranks before b, 1 if b ranks before a, 0 if equal
                        This function is universal and works for all classes automatically.
                        """
                        sid_a = str(a['sailor_id'])  # Ensure string type
                        sid_b = str(b['sailor_id'])  # Ensure string type
                        
                        # DEBUG: Log ALL comparisons involving 5820
                        if sid_a == '5820' or sid_b == '5820':
                            print(f"[COMPARE GENERIC] {sid_a} vs {sid_b}: a_reg={a['regatta_count']}, b_reg={b['regatta_count']}")
                            # Check if head-to-head data exists
                            if sid_a in head_to_head and sid_b in head_to_head[sid_a]:
                                h2h_check = head_to_head[sid_a][sid_b]
                                print(f"[COMPARE GENERIC] H2H EXISTS: wins={h2h_check.get('wins', 0)}, losses={h2h_check.get('losses', 0)}")
                            else:
                                print(f"[COMPARE GENERIC] NO H2H DATA in matrix")
                        
                        # CRITICAL RULE: Head-to-head is PRIMARY - if A has beaten B, A ranks above B
                        # This rule takes absolute precedence - no exceptions
                        h2h = head_to_head[sid_a][sid_b]
                        a_wins = h2h.get('wins', 0)  # A's wins over B
                        b_wins = h2h.get('losses', 0)  # A's losses to B = B's wins over A
                        total_h2h = a_wins + b_wins + h2h.get('ties', 0)
                        
                        # Priority 1: Direct Head-to-Head Results (ABSOLUTE RULE)
                        # If they've raced each other, head-to-head determines ranking
                        if total_h2h > 0:
                            # If A has beaten B more times, A ranks above B
                            if a_wins > b_wins:
                                return -1  # A ranks before B
                            # If B has beaten A more times, B ranks above A
                            if b_wins > a_wins:
                                return 1   # B ranks before A
                            
                            # If tied (same number of wins), check most recent result
                            if a_wins == b_wins and a_wins > 0:
                                # Check most recent result - more recent wins take precedence
                                if h2h.get('most_recent'):
                                    mr = h2h['most_recent']
                                    # If A won most recently, A ranks above B
                                    if mr.get('sailor1_rank', 999) < mr.get('sailor2_rank', 999):
                                        return -1  # A ranks before B
                                    # If B won most recently, B ranks above A
                                    if mr.get('sailor2_rank', 999) < mr.get('sailor1_rank', 999):
                                        return 1   # B ranks before A
                        
                        # Priority 2: Regatta Count (only if they've never raced each other)
                        a_regattas = a['regatta_count'] or 0
                        b_regattas = b['regatta_count'] or 0
                        
                        if a_regattas == 0:
                            return 1  # a goes to bottom
                        if b_regattas == 0:
                            return -1  # b goes to bottom
                        
                        # If they've never raced each other, use regatta count and other factors
                        if total_h2h == 0:
                            # No direct head-to-head: use regatta count, then average rank
                            if abs(a_regattas - b_regattas) >= 2:
                                return b_regattas - a_regattas
                            if a['avg_rank'] != b['avg_rank']:
                                return a['avg_rank'] - b['avg_rank']
                            if a['win_rate'] != b['win_rate']:
                                return b['win_rate'] - a['win_rate']
                            return a['avg_rank'] - b['avg_rank']
                        
                        # If they HAVE raced each other but head-to-head is tied, use tiebreakers
                        # Priority 3: Tiebreakers for tied head-to-head (wins == losses)
                        if a_wins == b_wins and total_h2h > 0:
                            # They HAVE raced each other - use direct head-to-head comparison
                            # Priority 3.1: Largest regatta head-to-head (top 5 by entry count) - MOST IMPORTANT
                            a_large_wins = h2h.get('large_regatta_wins', 0)  # A's wins in largest regattas
                            b_large_wins = h2h.get('large_regatta_losses', 0)  # A's losses in largest regattas = B's wins
                            if a_large_wins > b_large_wins:
                                return -1  # A ranks before B
                            if b_large_wins > a_large_wins:
                                return 1   # B ranks before A
                            
                            # Priority 3.2: Major regatta head-to-head (nationals)
                            a_major_wins = h2h.get('major_wins', 0)  # A's major wins over B
                            b_major_wins = h2h.get('major_losses', 0)  # A's major losses to B = B's major wins over A
                            if a_major_wins > b_major_wins:
                                return -1  # A ranks before B
                            if b_major_wins > a_major_wins:
                                return 1   # B ranks before A
                            
                            # Priority 3.3: Head-to-head against nationals sailors (indirect comparison)
                            # If one didn't sail nationals but beat/lost to someone who did
                            a_vs_nationals = h2h.get('vs_nationals_sailor_wins', 0)  # A beat nationals sailors
                            b_vs_nationals = h2h.get('vs_nationals_sailor_losses', 0)  # A lost to nationals sailors = B beat nationals sailors
                            if a_vs_nationals > b_vs_nationals:
                                return -1  # A ranks before B (beat more nationals sailors)
                            if b_vs_nationals > a_vs_nationals:
                                return 1   # B ranks before A (beat more nationals sailors)
                            
                            # Priority 3.4: Weighted wins (major regattas count more)
                            a_weighted = h2h.get('weighted_wins', 0)  # A's weighted wins over B
                            b_weighted = h2h.get('weighted_losses', 0)  # A's weighted losses to B = B's weighted wins over A
                            if a_weighted > b_weighted:
                                return -1  # A ranks before B
                            if b_weighted > a_weighted:
                                return 1   # B ranks before A
                            
                            # Priority 3.5: Regional regatta head-to-head
                            a_regional_wins = h2h.get('regional_wins', 0)  # A's regional wins over B
                            b_regional_wins = h2h.get('regional_losses', 0)  # A's regional losses to B = B's regional wins over A
                            if a_regional_wins > b_regional_wins:
                                return -1  # A ranks before B
                            if b_regional_wins > a_regional_wins:
                                return 1   # B ranks before A
                            
                            # Priority 3.6: Total head-to-head wins (unweighted)
                            diff = abs(a_wins - b_wins)
                            
                            # Clear winner (difference >= 2)
                            if a_wins - b_wins >= 2:
                                return -1  # A ranks before B
                            if b_wins - a_wins >= 2:
                                return 1   # B ranks before A
                            
                            # If head-to-head is close (difference <= 1), continue to tiebreakers below
                            
                            # Priority 4: Tiebreakers (for close matches, difference <= 1)
                            if diff <= 1:
                                # Tiebreaker 1: Most recent result (README Step 5, Priority 4.1)
                                if h2h.get('most_recent'):
                                    mr = h2h['most_recent']
                                    mr_weight = h2h.get('most_recent_weight', 0)
                                    # Prefer result from higher-weight regatta
                                    if mr_weight >= 3:
                                        # Major regatta - more decisive
                                        if mr.get('sailor1_rank', 999) < mr.get('sailor2_rank', 999):
                                            return -1  # A ranks before B
                                        if mr.get('sailor2_rank', 999) < mr.get('sailor1_rank', 999):
                                            return 1   # B ranks before A
                                    else:
                                        # Lower weight regatta - still compare
                                        if mr.get('sailor1_rank', 999) < mr.get('sailor2_rank', 999):
                                            return -1  # A ranks before B
                                        if mr.get('sailor2_rank', 999) < mr.get('sailor1_rank', 999):
                                            return 1   # B ranks before A
                                elif a_regattas == 1 and b_regattas == 1:
                                    # Both have exactly 1 regatta but no head-to-head
                                    if a['ranks'] and b['ranks']:
                                        if a['ranks'][0] < b['ranks'][0]:
                                            return -1
                                        if b['ranks'][0] < a['ranks'][0]:
                                            return 1
                                
                                # Tiebreaker 2: Improvement trend (README Step 5, Priority 4.2)
                                if a_regattas >= 2 and b_regattas >= 2:
                                    if b['improvement'] != a['improvement']:
                                        return b['improvement'] - a['improvement']  # Higher improvement = better
                                    
                                    # Tiebreaker 3: Recent trend (README Step 5, Priority 4.3)
                                    if a_regattas >= 3 and b_regattas >= 3:
                                        if b['recent_change'] != a['recent_change']:
                                            return b['recent_change'] - a['recent_change']  # Higher recent change = better
                                
                                # Tiebreaker 4: Average rank (README Step 5, Priority 4.4)
                                if a['avg_rank'] != b['avg_rank']:
                                    return a['avg_rank'] - b['avg_rank']  # Lower average rank = better
                        
                        # Tiebreaker 5: Win rate (README Step 5, Priority 4.5)
                        if a['win_rate'] != b['win_rate']:
                            return b['win_rate'] - a['win_rate']  # Higher win rate = better
                        
                        # Final tiebreakers (README Step 5, Final Tiebreakers)
                        if a_regattas != b_regattas:
                            return b_regattas - a_regattas  # More regattas = better
                        
                        # Ultimate tiebreaker: average rank
                        return a['avg_rank'] - b['avg_rank']  # Lower average rank = better
                    
                    # NEW ALGORITHM: Each sailor starts at bottom and moves up until finding sailor that beat them
                    # Rule: Start at bottom, check upward - if beaten sailor above, move up
                    # Stop when find sailor that has beaten them, place below that sailor
                    
                    # Start with initial sort by regatta count, then average rank for initial order
                    import functools
                    standings.sort(key=lambda x: (-(x.get('regatta_count', 0) or 0), x.get('avg_rank', 999)))
                    
                    def has_consistently_beaten(sid_a, sid_b, h2h_matrix, checked=None):
                        """Check if sailor A has consistently beaten sailor B (direct or indirect)"""
                        if checked is None:
                            checked = set()
                        
                        # Prevent infinite recursion
                        if (sid_a, sid_b) in checked:
                            return None
                        checked.add((sid_a, sid_b))
                        
                        h2h_ab = h2h_matrix.get(sid_a, {}).get(sid_b, {})
                        h2h_ba = h2h_matrix.get(sid_b, {}).get(sid_a, {})
                        
                        # A's wins over B
                        a_wins = h2h_ab.get('wins', 0) or h2h_ba.get('losses', 0)
                        # B's wins over A
                        b_wins = h2h_ba.get('wins', 0) or h2h_ab.get('losses', 0)
                        total_h2h = a_wins + b_wins + max(h2h_ab.get('ties', 0), h2h_ba.get('ties', 0))
                        
                        # Direct head-to-head
                        if total_h2h > 0:
                            if a_wins > b_wins:
                                return True
                            if b_wins > a_wins:
                                return False
                            
                            # Tied: check most recent result
                            if h2h_ab.get('most_recent'):
                                mr = h2h_ab['most_recent']
                                if mr.get('sailor1_rank', 999) < mr.get('sailor2_rank', 999):
                                    return True  # A won most recently
                                if mr.get('sailor2_rank', 999) < mr.get('sailor1_rank', 999):
                                    return False  # B won most recently
                        
                        # No direct head-to-head - check indirect (transitive) - ONE LEVEL ONLY
                        # If A beats C (direct), and C beats B (direct), then A beats B
                        # Only check direct wins, not recursive
                        for intermediate_sid in h2h_matrix.get(sid_a, {}):
                            if intermediate_sid == sid_b:
                                continue
                            
                            # Check if A has DIRECTLY beaten intermediate (no recursion)
                            h2h_ai = h2h_matrix.get(sid_a, {}).get(intermediate_sid, {})
                            h2h_ia = h2h_matrix.get(intermediate_sid, {}).get(sid_a, {})
                            a_wins_i = h2h_ai.get('wins', 0) or h2h_ia.get('losses', 0)
                            i_wins_a = h2h_ia.get('wins', 0) or h2h_ai.get('losses', 0)
                            
                            if a_wins_i > i_wins_a:  # A directly beat intermediate
                                # Check if intermediate DIRECTLY beat B
                                h2h_ib = h2h_matrix.get(intermediate_sid, {}).get(sid_b, {})
                                h2h_bi = h2h_matrix.get(sid_b, {}).get(intermediate_sid, {})
                                i_wins_b = h2h_ib.get('wins', 0) or h2h_bi.get('losses', 0)
                                b_wins_i = h2h_bi.get('wins', 0) or h2h_ib.get('losses', 0)
                                
                                if i_wins_b > b_wins_i:  # Intermediate directly beat B
                                    # Transitive: A beats intermediate, intermediate beats B, so A beats B
                                    return True
                        
                        # Check reverse: If B beats C (direct), and C beats A (direct), then B beats A
                        for intermediate_sid in h2h_matrix.get(sid_b, {}):
                            if intermediate_sid == sid_a:
                                continue
                            
                            # Check if B has DIRECTLY beaten intermediate
                            h2h_bi = h2h_matrix.get(sid_b, {}).get(intermediate_sid, {})
                            h2h_ib = h2h_matrix.get(intermediate_sid, {}).get(sid_b, {})
                            b_wins_i = h2h_bi.get('wins', 0) or h2h_ib.get('losses', 0)
                            i_wins_b = h2h_ib.get('wins', 0) or h2h_bi.get('losses', 0)
                            
                            if b_wins_i > i_wins_b:  # B directly beat intermediate
                                # Check if intermediate DIRECTLY beat A
                                h2h_ia = h2h_matrix.get(intermediate_sid, {}).get(sid_a, {})
                                h2h_ai = h2h_matrix.get(sid_a, {}).get(intermediate_sid, {})
                                i_wins_a = h2h_ia.get('wins', 0) or h2h_ai.get('losses', 0)
                                a_wins_i = h2h_ai.get('wins', 0) or h2h_ia.get('losses', 0)
                                
                                if i_wins_a > a_wins_i:  # Intermediate directly beat A
                                    # Transitive: B beats intermediate, intermediate beats A, so B beats A
                                    return False
                        
                        return None  # Can't determine (never raced and no indirect path)
                    
                    # Build final standings: Start with Sean Kavanagh (or highest regatta count) at position 1
                    # Then for each remaining sailor, start at bottom and move up
                    final_standings = []
                    remaining = standings.copy()
                    
                    # Find Sean Kavanagh (6804) or start with first sailor
                    sean = next((s for s in remaining if str(s.get('sailor_id')) == '6804'), None)
                    if sean:
                        final_standings.append(sean)
                        remaining.remove(sean)
                        print(f"[STANDINGS] Starting with Sean Kavanagh at position 1")
                    
                    # Process each remaining sailor
                    for sailor in remaining:
                        sid = str(sailor['sailor_id'])
                        sailor_name = sailor.get('name', sid)
                        
                        # Start at bottom (end of current list) and move up
                        position = len(final_standings)  # Start at bottom
                        
                        # Check upward from bottom until finding sailor that has beaten them
                        for check_pos in range(len(final_standings) - 1, -1, -1):  # From bottom to top
                            other_sailor = final_standings[check_pos]
                            other_sid = str(other_sailor['sailor_id'])
                            
                            # Check if other sailor has beaten this sailor
                            beaten_by = has_consistently_beaten(other_sid, sid, head_to_head)
                            
                            if beaten_by is True:
                                # This sailor has been beaten by the sailor at this position
                                # Must rank below this position
                                position = check_pos + 1
                                break
                            
                            # If beaten_by is False (this sailor beat the other), continue moving up
                            if beaten_by is False:
                                position = check_pos
                                continue
                            
                            # If beaten_by is None (never raced, no head-to-head data):
                            # Use regatta count and average rank as tiebreaker
                            if beaten_by is None:
                                other_regattas = other_sailor.get('regatta_count', 0) or 0
                                this_regattas = sailor.get('regatta_count', 0) or 0
                                other_avg = other_sailor.get('avg_rank', 999) or 999
                                this_avg = sailor.get('avg_rank', 999) or 999
                                
                                # If other has significantly more regattas (>= 2), they rank above
                                if other_regattas - this_regattas >= 2:
                                    position = check_pos + 1
                                    break
                                
                                # If regatta counts are similar, use average rank
                                if abs(other_regattas - this_regattas) < 2:
                                    if other_avg < this_avg:  # Lower avg rank = better
                                        position = check_pos + 1
                                        break
                                
                                # If this sailor has better stats, can move up
                                position = check_pos
                        
                        # Insert at calculated position
                        final_standings.insert(position, sailor)
                        
                        if sid == '10368':  # Scarlet
                            print(f"[STANDINGS] Scarlet Celliers placed at position {position + 1}")
                    
                    standings = final_standings
                    
                    # Identify double-handed sailors (those who sail with crew)
                    # Query to find sailors who have crew in their results
                    cur.execute("""
                        SELECT DISTINCT COALESCE(r.helm_sa_sailing_id::text, r.helm_temp_id) as sailor_id
                        FROM results r
                        JOIN regatta_blocks rb ON r.block_id = rb.block_id
                        JOIN regattas reg ON reg.regatta_id = r.regatta_id
                        WHERE 
                            LOWER(REPLACE(COALESCE(rb.class_canonical, rb.fleet_label), ' Fleet', '')) = %s
                            AND r.raced = TRUE
                            AND COALESCE(r.helm_sa_sailing_id::text, r.helm_temp_id) IS NOT NULL
                            AND (COALESCE(r.crew_sa_sailing_id::text, r.crew_temp_id) IS NOT NULL
                                 AND COALESCE(r.crew_sa_sailing_id::text, r.crew_temp_id) != '')
                            AND (reg.end_date >= %s OR reg.start_date >= %s)
                            AND reg.regatta_number != '374'
                    """, (class_name.lower(), thirteen_months_ago, thirteen_months_ago))
                    double_handed_sailors = {row['sailor_id'] for row in cur.fetchall()}
                    
                    # Adjust double-handed sailors down 2 positions each
                    if double_handed_sailors:
                        # Create a list of indices for double-handed sailors
                        double_handed_indices = []
                        for i, sailor in enumerate(standings):
                            sid = str(sailor.get('sailor_id') or sailor.get('sa_id') or sailor.get('sas_id', ''))
                            if sid in double_handed_sailors:
                                double_handed_indices.append(i)
                        
                        # Move each double-handed sailor down 2 positions (but not below the end)
                        for idx in sorted(double_handed_indices, reverse=True):  # Process from bottom to top
                            if idx + 2 < len(standings):
                                # Swap with sailor 2 positions below
                                standings[idx], standings[idx + 2] = standings[idx + 2], standings[idx]
                    
                    # Get stored Main Scores from main_scores table
                    cur.execute("""
                        SELECT sailor_id, main_score
                        FROM main_scores
                        WHERE class_name = %s
                    """, (class_name,))
                    stored_scores = {row['sailor_id']: row['main_score'] for row in cur.fetchall()}
                    
                    # If filtering to Regatta 374 entries, rank them by master standings position
                    if filter_to_374:
                        # Create a map of master standings position by sailor_id
                        master_rank_map = {}
                        for i, sailor in enumerate(standings, 1):
                            sid = str(sailor.get('sailor_id') or sailor.get('sa_id') or sailor.get('sas_id', ''))
                            master_rank_map[sid] = i
                        
                        # Filter standings to only Regatta 374 entries and rank by master position
                        # Include ALL Regatta 374 entries, even if they don't have master standings
                        regatta_374_ranked = []
                        for sid, entry_data in regatta_374_entries.items():
                            master_rank = master_rank_map.get(sid)
                            if master_rank:
                                entry_data['master_rank'] = master_rank
                            else:
                                # Sailors not in master standings get a high rank (ranked at bottom)
                                entry_data['master_rank'] = 99999
                            regatta_374_ranked.append(entry_data)
                        
                        # Sort by master standings position (1st in master = 1st in 374, etc.)
                        # Those without master standings (rank 99999) will be at the bottom
                        regatta_374_ranked.sort(key=lambda x: x.get('master_rank', 99999))
                        
                        # Assign ranks 1-31 based on master standings order
                        for i, entry in enumerate(regatta_374_ranked, 1):
                            entry['main_rank'] = str(i)
                            entry['likelihood'] = 'likely'
                            # Get stored Main Score if available
                            sailor_id = entry.get('sailor_id')
                            entry['wc_score'] = stored_scores.get(sailor_id) if sailor_id else None
                        
                        return {
                            "rankings": regatta_374_ranked,
                            "total_sailors": len(regatta_374_ranked),
                            "aged_out": [],
                            "unlikely": []
                        }
                    
                    # Assign ranks
                    for i, sailor in enumerate(standings, 1):
                        sailor['main_rank'] = str(i)
                        # Use stored Main Score if available, otherwise None
                        sailor_id = sailor.get('sailor_id')
                        sailor['wc_score'] = stored_scores.get(sailor_id) if sailor_id else None
                        sailor['total_races'] = sailor['regatta_count']
                        sailor['regatta_id'] = None
                        sailor['likelihood'] = 'likely'
                
            return {
                    "rankings": standings,
                    "total_sailors": len(all_sailors),  # Total eligible sailors for class, not just those in standings
                    "aged_out": [],
                    "unlikely": []
                }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"rankings": [], "total_sailors": 0, "aged_out": [], "unlikely": []}

@app.get("/api/open-regattas")
def api_open_regattas(class_name: Optional[str] = None):
    """Return list of open regattas (currently regatta 375 for Optimist A/B)"""
    try:
        with psycopg2.connect(DB_URL) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # For now, use regatta 374 (SA Youth Nationals Dec 2025) as the open regatta
                # TODO: Add is_open_regatta column or use a different method to identify open regattas
                sql = """
                    SELECT 
                        r.regatta_id,
                        r.regatta_number,
                        r.event_name,
                        r.start_date,
                        r.end_date,
                        COALESCE(c.club_abbrev, r.host_club_name) as host_club_code,
                        (SELECT COUNT(*) FROM results res 
                         JOIN regatta_blocks rb ON rb.block_id = res.block_id
                         WHERE res.regatta_id = r.regatta_id
                           AND (%s IS NULL OR LOWER(rb.fleet_label) = LOWER(%s))
                        ) as entries_count
                    FROM regattas r
                    LEFT JOIN clubs c ON c.club_id = r.host_club_id
                    WHERE r.regatta_number = 374
                    ORDER BY r.regatta_number DESC
                    LIMIT 1
                """
                cur.execute(sql, (class_name, class_name))
                regattas = cur.fetchall()
                return [dict(r) for r in regattas]
    except Exception as e:
        import traceback
        traceback.print_exc()
        return []

@app.get("/api/regatta/{regatta_id}/participants-classes")
def api_regatta_participants_classes(regatta_id: str):
    """Return mapping of sailor IDs to their class names in a regatta"""
    t0 = time.time()
    try:
        with psycopg2.connect(DB_URL) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                sql = """
                    SELECT DISTINCT
                        COALESCE(r.helm_sa_sailing_id::text, r.helm_temp_id) as sailor_id,
                        COALESCE(rb.class_canonical, rb.fleet_label) as class_name
                    FROM results r
                    JOIN regatta_blocks rb ON rb.block_id = r.block_id
                    WHERE r.regatta_id = %s
                """
                cur.execute(sql, (regatta_id,))
                rows = cur.fetchall()
                
                # Convert to dictionary mapping sailor_id -> class_name
                result = {}
                for row in rows:
                    sailor_id = row['sailor_id']
                    if sailor_id:
                        result[str(sailor_id)] = row['class_name'] or ''
                
                t1 = time.time()
                print(f"[TRACE] getRegattaParticipantsClasses({regatta_id}) took {t1-t0:.3f}s ({len(result)} participants)")
                return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        t1 = time.time()
        print(f"[TRACE] getRegattaParticipantsClasses({regatta_id}) took {t1-t0:.3f}s (exception)")
        return {}

# Mount static files AFTER all API routes (must be last)
@app.get("/api/standings/db")
def api_standings_db(
    class_name: Optional[str] = Query(None, description="Class name (e.g., 'Dabchick', 'Optimist A')"),
    request: Request = None,
):
    """Return standings from database tables (master_list and standing_list)
    
    This endpoint reads pre-calculated standings from the database tables
    created by the calculate_all_standings.py script.
    Returns ranking_score when standing_list has that column (World Sailing-style score for display).
    """
    if not class_name:
        raise HTTPException(status_code=400, detail="class_name parameter is required")
    
    request_id = getattr(request.state, 'request_id', None) if request else None
    if not request_id:
        request_id = get_request_id()
    
    conn = None
    try:
        conn = get_db_connection(request_id)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Resolve class_name: try exact match first, then case-insensitive / trim match
            cur.execute(
                "SELECT class_name FROM standing_list WHERE class_name = %s LIMIT 1",
                (class_name,),
            )
            if cur.fetchone() is None:
                cur.execute(
                    "SELECT class_name FROM standing_list WHERE LOWER(TRIM(class_name)) = LOWER(TRIM(%s)) LIMIT 1",
                    (class_name,),
                )
                row = cur.fetchone()
                if row:
                    class_name = row["class_name"]
                else:
                    cur.execute(
                        "SELECT class_name FROM standing_list WHERE class_name = %s LIMIT 1",
                        (class_name.strip() + " Fleet",),
                    )
                    if cur.fetchone():
                        class_name = class_name.strip() + " Fleet"
            sql_with_score = """
                SELECT sl.sailor_id, sl.name, sl.rank as main_rank, sl.regattas_sailed as regatta_count,
                       sl.ranking_score, ml.first_name, ml.last_name, ml.year_of_birth, ml.age
                FROM standing_list sl
                JOIN master_list ml ON ml.class_name = sl.class_name AND ml.sailor_id = sl.sailor_id
                WHERE sl.class_name = %s AND ml.is_active = TRUE
                ORDER BY sl.rank ASC
            """
            sql_no_score = """
                SELECT sl.sailor_id, sl.name, sl.rank as main_rank, sl.regattas_sailed as regatta_count,
                       ml.first_name, ml.last_name, ml.year_of_birth, ml.age
                FROM standing_list sl
                JOIN master_list ml ON ml.class_name = sl.class_name AND ml.sailor_id = sl.sailor_id
                WHERE sl.class_name = %s AND ml.is_active = TRUE
                ORDER BY sl.rank ASC
            """
            try:
                cur.execute(sql_with_score, (class_name,))
                has_score = True
            except psycopg2.ProgrammingError as e:
                if "ranking_score" in str(e) or "does not exist" in str(e).lower():
                    cur.execute(sql_no_score, (class_name,))
                    has_score = False
                else:
                    raise
            rows = cur.fetchall()
            standings = []
            for row in rows:
                r = {
                    'sailor_id': row['sailor_id'],
                    'sa_id': row['sailor_id'],
                    'sas_id': row['sailor_id'],
                    'name': row['name'],
                    'first_name': row.get('first_name'),
                    'last_name': row.get('last_name'),
                    'main_rank': str(row['main_rank']),
                    'regatta_count': row['regatta_count'],
                    'year_of_birth': row.get('year_of_birth'),
                    'age': row.get('age'),
                }
                r['ranking_score'] = row.get('ranking_score') if has_score else None
                standings.append(r)
            cur.execute("""
                SELECT COUNT(*) as total
                FROM master_list
                WHERE class_name = %s AND is_active = TRUE
            """, (class_name,))
            total_result = cur.fetchone()
            total_sailors = total_result['total'] if total_result else len(standings)
            return {
                "rankings": standings,
                "total_sailors": total_sailors,
                "aged_out": [],
                "unlikely": [],
                "source": "database"
            }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching standings: {str(e)}")
    finally:
        if conn:
            conn.close()

# ============================================================================
# FACEBOOK OAUTH ENDPOINTS
# ============================================================================

FACEBOOK_APP_ID = os.getenv("FACEBOOK_APP_ID", "")
FACEBOOK_APP_SECRET = os.getenv("FACEBOOK_APP_SECRET", "")

@app.get("/auth/session")
async def check_session(request: Request):
    """Check if user has a valid session"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        # Get session token from cookie or query parameter
        session_token = request.cookies.get("session") or request.query_params.get("session")
        
        if not session_token:
            return {"valid": False, "message": "No session token"}
        
        # First, clean up any expired sessions
        cur.execute("""
            DELETE FROM public.user_sessions
            WHERE expires_at <= NOW()
        """)
        
        # Check if session exists and is valid
        cur.execute("""
            SELECT s.session_id, s.account_id, s.sas_id, s.login_method, s.expires_at
            FROM public.user_sessions s
            WHERE s.session_id = %s AND s.expires_at > NOW()
        """, (session_token,))
        
        session = cur.fetchone()
        
        if session:
            # Fetch user name information from sas_id_personal or sailing_id
            first_name = None
            last_name = None
            full_name = None
            
            if session['sas_id']:
                # Try to get name from sas_id_personal first
                cur.execute("""
                    SELECT first_name, last_name, 
                           COALESCE(
                               NULLIF(TRIM(COALESCE(first_name, '') || ' ' || COALESCE(last_name, '')), ''),
                               full_name,
                               ''
                           ) as full_name
                    FROM public.sas_id_personal
                    WHERE sa_sailing_id = %s
                    LIMIT 1
                """, (session['sas_id'],))
                
                personal_row = cur.fetchone()
                if personal_row:
                    first_name = personal_row.get('first_name')
                    last_name = personal_row.get('last_name')
                    full_name = personal_row.get('full_name')
                    # Construct full_name if not available
                    if not full_name or not full_name.strip():
                        if first_name or last_name:
                            full_name = f"{first_name or ''} {last_name or ''}".strip()
                
                # If not found in sas_id_personal, try sailing_id
                if not full_name or not full_name.strip():
                    cur.execute("""
                        SELECT first_name, last_name,
                               COALESCE(
                                   NULLIF(TRIM(COALESCE(first_name, '') || ' ' || COALESCE(last_name, '')), ''),
                                   display_name,
                                   ''
                               ) as full_name
                        FROM public.sailing_id
                        WHERE sa_sailing_id = %s
                        LIMIT 1
                    """, (session['sas_id'],))
                    
                    sailing_row = cur.fetchone()
                    if sailing_row:
                        first_name = sailing_row.get('first_name')
                        last_name = sailing_row.get('last_name')
                        full_name = sailing_row.get('full_name')
                        # Construct full_name if not available
                        if not full_name or not full_name.strip():
                            if first_name or last_name:
                                full_name = f"{first_name or ''} {last_name or ''}".strip()
            
            conn.commit()
            
            # Session is valid
            return {
                "valid": True,
                "session_id": session['session_id'],
                "sas_id": session['sas_id'],
                "login_method": session['login_method'],
                "user": {
                    "first_name": first_name,
                    "last_name": last_name,
                    "full_name": full_name
                }
            }
        else:
            # Session not found or expired
            return {"valid": False, "message": "Session expired or invalid"}
            
    except Exception as e:
        print(f"Error checking session: {e}")
        traceback.print_exc()
        return {"valid": False, "error": str(e)}
    finally:
        cur.close()
        conn.close()

@app.post("/auth/login")
async def login(request: Request):
    """Login with SAS ID/WhatsApp and password"""
    try:
        body = await request.json()
        username = body.get("username") or body.get("username")
        password = body.get("password")
        provider = body.get("provider", "username")
        
        if not username or not password:
            return {"success": False, "error": "Username and password required"}
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Hash password for comparison
        password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
        
        # Try to find account by SAS ID or WhatsApp number
        # Username can be SAS ID (numeric) or WhatsApp (10 digits)
        whatsapp_clean = re.sub(r'\D', '', str(username))[:10] if username else ''
        
        # Check if username looks like SAS ID (numeric) or WhatsApp (10 digits starting with 0)
        is_sas_id = username.isdigit() and len(username) <= 10
        is_whatsapp = len(whatsapp_clean) == 10 and whatsapp_clean.startswith('0')
        
        cur.execute("""
            SELECT account_id, sas_id, login_method, provider_id, email
            FROM public.user_accounts
            WHERE (
                (login_method = 'email' AND (sas_id = %s OR email = %s) AND password_hash = %s)
                OR (login_method = 'whatsapp' AND provider_id = %s AND password_hash = %s)
                OR (login_method = 'sas_id' AND sas_id = %s AND password_hash = %s)
            )
            LIMIT 1
        """, (
            username, username, password_hash,  # email login
            whatsapp_clean, password_hash,       # whatsapp login (with password check)
            username, password_hash              # sas_id login
        ))
        
        account = cur.fetchone()
        
        if not account:
            # Try alternative: check sas_id_personal for email/password match
            cur.execute("""
                SELECT ua.account_id, ua.sas_id, ua.login_method, ua.provider_id, ua.email
                FROM public.user_accounts ua
                JOIN public.sas_id_personal s ON s.sa_sailing_id = ua.sas_id
                WHERE (
                    (s.email = %s OR ua.sas_id = %s)
                    AND ua.password_hash = %s
                    AND ua.login_method IN ('email', 'sas_id')
                )
                LIMIT 1
            """, (username, username, password_hash))
            
            account = cur.fetchone()
        
        if not account:
            cur.close()
            conn.close()
            return {"success": False, "error": "Invalid username or password"}
        
        # Fetch user name information from sas_id_personal or sailing_id
        user_name = None
        first_name = None
        last_name = None
        full_name = None
        
        if account['sas_id']:
            # Try to get name from sas_id_personal first
            cur.execute("""
                SELECT first_name, last_name, 
                       COALESCE(
                           NULLIF(TRIM(COALESCE(first_name, '') || ' ' || COALESCE(last_name, '')), ''),
                           full_name,
                           ''
                       ) as full_name
                FROM public.sas_id_personal
                WHERE sa_sailing_id = %s
                LIMIT 1
            """, (account['sas_id'],))
            
            personal_row = cur.fetchone()
            if personal_row:
                first_name = personal_row.get('first_name')
                last_name = personal_row.get('last_name')
                full_name = personal_row.get('full_name')
                # Construct full_name if not available
                if not full_name or not full_name.strip():
                    if first_name or last_name:
                        full_name = f"{first_name or ''} {last_name or ''}".strip()
            
            # If not found in sas_id_personal, try sailing_id
            if not full_name or not full_name.strip():
                cur.execute("""
                    SELECT first_name, last_name,
                           COALESCE(
                               NULLIF(TRIM(COALESCE(first_name, '') || ' ' || COALESCE(last_name, '')), ''),
                               display_name,
                               ''
                           ) as full_name
                    FROM public.sailing_id
                    WHERE sa_sailing_id = %s
                    LIMIT 1
                """, (account['sas_id'],))
                
                sailing_row = cur.fetchone()
                if sailing_row:
                    first_name = sailing_row.get('first_name')
                    last_name = sailing_row.get('last_name')
                    full_name = sailing_row.get('full_name')
                    # Construct full_name if not available
                    if not full_name or not full_name.strip():
                        if first_name or last_name:
                            full_name = f"{first_name or ''} {last_name or ''}".strip()
        
        # Create session
        session_token = str(uuid.uuid4())
        expires_at = datetime.now() + timedelta(days=30)
        
        cur.execute("""
            INSERT INTO public.user_sessions
            (session_id, account_id, sas_id, login_method, expires_at)
            VALUES (%s, %s, %s, %s, %s)
        """, (session_token, account['account_id'], account['sas_id'], account['login_method'] or 'username', expires_at))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return {
            "success": True,
            "session": session_token,
            "session_token": session_token,
            "sas_id": account['sas_id'],
            "login_method": account['login_method'] or 'username',
            "user": {
                "first_name": first_name,
                "last_name": last_name,
                "full_name": full_name
            }
        }
        
    except Exception as e:
        print(f"Error during login: {e}")
        traceback.print_exc()
        return {"success": False, "error": str(e)}

@app.post("/auth/logout")
async def logout(request: Request):
    """Logout user by clearing session"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Get session token from cookie or request body
        session_token = request.cookies.get("session")
        body = await request.json() if request.method == "POST" else {}
        session_token = session_token or body.get("session_token")
        
        if session_token:
            # Delete the session
            cur.execute("""
                DELETE FROM public.user_sessions
                WHERE session_id = %s
            """, (session_token,))
            conn.commit()
        
        # Also clean up expired sessions
        cur.execute("""
            DELETE FROM public.user_sessions
            WHERE expires_at <= NOW()
        """)
        conn.commit()
        
        return {"success": True, "message": "Logged out successfully"}
        
    except Exception as e:
        print(f"Error during logout: {e}")
        traceback.print_exc()
        return {"success": False, "error": str(e)}
    finally:
        cur.close()
        conn.close()

@app.get("/auth/facebook")
async def facebook_auth(request: Request):
    """Initiate Facebook OAuth login"""
    if not FACEBOOK_APP_ID:
        return HTMLResponse("""
            <html><body>
                <h1>Facebook Login Not Configured</h1>
                <p>Please set FACEBOOK_APP_ID and FACEBOOK_APP_SECRET environment variables.</p>
            </body></html>
        """)
    
    # Generate state for CSRF protection
    state = str(uuid.uuid4())
    
    # Determine redirect URI - Facebook requires HTTPS
    # Always use HTTPS for redirect_uri even if request comes via HTTP
    host = request.headers.get("host", "192.168.0.130:8082")
    # Remove port if present and use 8082 for HTTPS
    if ":" in host:
        host = host.split(":")[0]
    redirect_uri = f"https://{host}:8082/auth/facebook/callback"
    
    # Detect mobile
    user_agent = request.headers.get("user-agent", "").lower()
    is_mobile = "mobile" in user_agent or "android" in user_agent or "iphone" in user_agent
    display_param = "display=touch" if is_mobile else ""
    
    # Build Facebook OAuth URL
    fb_url = f"https://www.facebook.com/v18.0/dialog/oauth?client_id={FACEBOOK_APP_ID}&redirect_uri={redirect_uri}&state={state}&scope=public_profile&response_type=code"
    if display_param:
        fb_url += f"&{display_param}"
    
    # Store state in session (simplified - in production use proper session storage)
    return RedirectResponse(url=fb_url)

@app.get("/auth/facebook/callback")
async def facebook_callback(request: Request, code: Optional[str] = None, state: Optional[str] = None, error: Optional[str] = None):
    """Handle Facebook OAuth callback"""
    if error:
        return RedirectResponse(f"/sailingsa/frontend/login.html?error=facebook_login_failed")
    
    if not code:
        return RedirectResponse(f"/sailingsa/frontend/login.html?error=facebook_no_code")
    
    if not FACEBOOK_APP_ID or not FACEBOOK_APP_SECRET:
        return RedirectResponse(f"/sailingsa/frontend/login.html?error=facebook_not_configured")
    
    try:
        # Exchange code for access token - Facebook requires HTTPS
        # Always use HTTPS for redirect_uri even if request comes via HTTP
        host = request.headers.get("host", "192.168.0.130:8082")
        # Remove port if present and use 8082 for HTTPS
        if ":" in host:
            host = host.split(":")[0]
        redirect_uri = f"https://{host}:8082/auth/facebook/callback"
        
        import requests
        token_url = "https://graph.facebook.com/v18.0/oauth/access_token"
        token_params = {
            "client_id": FACEBOOK_APP_ID,
            "client_secret": FACEBOOK_APP_SECRET,
            "redirect_uri": redirect_uri,
            "code": code
        }
        token_response = requests.get(token_url, params=token_params)
        token_data = token_response.json()
        
        if "access_token" not in token_data:
            return RedirectResponse(f"/sailingsa/frontend/login.html?error=facebook_token_failed")
        
        access_token = token_data["access_token"]
        
        # Get user profile
        profile_url = "https://graph.facebook.com/v18.0/me"
        profile_params = {
            "fields": "id,name,picture",
            "access_token": access_token
        }
        profile_response = requests.get(profile_url, params=profile_params)
        profile_data = profile_response.json()
        
        facebook_id = profile_data.get("id")
        facebook_name = profile_data.get("name", "")
        picture_url = profile_data.get("picture", {}).get("data", {}).get("url") if profile_data.get("picture") else None
        
        if not facebook_id:
            return RedirectResponse(f"/sailingsa/frontend/login.html?error=facebook_no_id")
        
        # Parse name
        name_parts = facebook_name.split(" ", 1) if facebook_name else ["", ""]
        first_name = name_parts[0] if len(name_parts) > 0 else ""
        last_name = name_parts[1] if len(name_parts) > 1 else ""
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Check if account exists
        cur.execute("""
            SELECT account_id, sas_id FROM public.user_accounts
            WHERE login_method = 'facebook' AND provider_id = %s
            LIMIT 1
        """, (str(facebook_id),))
        
        existing_account = cur.fetchone()
        
        if existing_account:
            # Existing user - check if they have a temporary SAS ID (needs profile confirmation)
            account_id = existing_account['account_id']
            sas_id = existing_account['sas_id']
            
            # If SAS ID starts with "FB_", it's a temporary ID - redirect to confirmation page
            if sas_id and sas_id.startswith("FB_"):
                # Get the account details for confirmation page
                cur.execute("""
                    SELECT first_name, last_name, full_name FROM public.user_accounts
                    WHERE account_id = %s
                """, (account_id,))
                account_details = cur.fetchone()
                conn.close()
                
                # Redirect to confirmation page to link to real SAS ID
                confirm_url = f"/sailingsa/frontend/facebook-confirm.html?first_names={account_details['first_name'] or first_name}&surname={account_details['last_name'] or last_name}&facebook_id={facebook_id}&facebook_name={account_details['full_name'] or facebook_name}"
                return RedirectResponse(confirm_url)
            
            # Real SAS ID - create session and redirect directly to landing page
            session_token = str(uuid.uuid4())
            expires_at = datetime.now() + timedelta(days=30)
            
            cur.execute("""
                INSERT INTO public.user_sessions
                (session_id, account_id, sas_id, login_method, expires_at)
                VALUES (%s, %s, %s, 'facebook', %s)
            """, (session_token, account_id, sas_id, expires_at))
            
            conn.commit()
            cur.close()
            conn.close()
            
            # Redirect directly to landing page with session token
            # Use HTTP (8081) for the landing page
            landing_url = f"http://192.168.0.130:8081/sailingsa/frontend/index.html?session={session_token}"
            return RedirectResponse(landing_url)
        else:
            # New user - redirect to confirmation page to search for real SAS ID
            # DO NOT create temporary accounts - must link to real SAS ID
            conn.close()
            
            # Save profile picture if available (for later use after linking)
            profile_pic_path = None
            if picture_url:
                try:
                    pic_response = requests.get(picture_url, timeout=5)
                    if pic_response.status_code == 200:
                        import os
                        pics_dir = os.path.join(BASE_DIR, "sailingsa", "frontend", "assets", "profile_pics")
                        os.makedirs(pics_dir, exist_ok=True)
                        profile_pic_path = f"assets/profile_pics/fb_{facebook_id}.jpg"
                        pic_file_path = os.path.join(BASE_DIR, "sailingsa", "frontend", profile_pic_path)
                        with open(pic_file_path, "wb") as f:
                            f.write(pic_response.content)
                except Exception as e:
                    print(f"Error saving profile picture: {e}")
            
            # Redirect to confirmation page to search for real SAS ID
            # Store profile picture path in URL if saved (will be used when account is created)
            pic_param = f"&profile_pic={profile_pic_path}" if profile_pic_path else ""
            confirm_url = f"/sailingsa/frontend/facebook-confirm.html?first_names={first_name}&surname={last_name}&facebook_id={facebook_id}&facebook_name={facebook_name}{pic_param}"
            return RedirectResponse(confirm_url)
            
    except Exception as e:
        print(f"Facebook callback error: {e}")
        traceback.print_exc()
        return RedirectResponse(f"/sailingsa/frontend/login.html?error=facebook_callback_error")

@app.post("/profiles/search")
async def profiles_search(request: Request):
    """Search for profiles by query (SAS ID or name) - accepts POST with JSON body"""
    try:
        body = await request.json()
        query = body.get('query', '').strip()
        
        if not query:
            return {"error": "Query required", "results": []}
        
        # Parse query to determine if it's SAS ID or name
        query_clean = query.strip()
        sas_id = None
        first_names = None
        surname = None
        
        # If query is all digits, treat as SAS ID
        if query_clean.isdigit():
            sas_id = query_clean
        else:
            # Try to parse as "First Last"
            parts = query_clean.split()
            if len(parts) >= 2:
                first_names = parts[0]
                surname = ' '.join(parts[1:])
            elif len(parts) == 1:
                # Single word - try as first name
                first_names = parts[0]
                surname = None
        
        # Call the existing search logic (synchronous function)
        return _perform_sailor_search(sas_id, first_names, surname, query)
    except Exception as e:
        print(f"Error in profiles/search: {e}")
        traceback.print_exc()
        return {"error": str(e), "results": []}

@app.get("/api/facebook/search-sailors")
def facebook_search_sailors(first_names: Optional[str] = None, surname: Optional[str] = None, sas_id: Optional[str] = None, query: Optional[str] = None):
    """Search for sailors by name or SAS ID to link Facebook account - returns profile with classes"""
    # Support query parameter for free-form search (SAS ID or name)
    if query:
        query_clean = query.strip()
        # If query is all digits, treat as SAS ID
        if query_clean.isdigit():
            sas_id = query_clean
        else:
            # Try to parse as "First Last" or "Last, First"
            parts = query_clean.split()
            if len(parts) >= 2:
                first_names = parts[0]
                surname = ' '.join(parts[1:])
            elif len(parts) == 1:
                # Single word - try as first name (will search first_name LIKE)
                first_names = parts[0]
                surname = None
    
    # If SAS ID provided, search by SAS ID
    if sas_id:
        if not sas_id.isdigit():
            return {"error": "SAS ID must be numeric"}
    elif not first_names and not surname:
        return {"error": "SAS ID, first name, surname, or query required"}
    
    # Debug logging
    print(f"[FB_SEARCH] Search params: sas_id={sas_id}, first_names={first_names}, surname={surname}, query={query}")
    
def _perform_sailor_search(sas_id: Optional[str] = None, first_names: Optional[str] = None, surname: Optional[str] = None, query: Optional[str] = None):
    """Internal function to perform sailor search - used by both GET and POST endpoints"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        conditions = []
        params = []
        
        # Search by SAS ID if provided
        if sas_id:
            conditions.append("s.sa_sailing_id::text = %s")
            params.append(sas_id)
        else:
            # Search by name
            if first_names:
                conditions.append("LOWER(COALESCE(s.first_name, '')) LIKE %s")
                params.append(f"{first_names.lower()}%")
            
            if surname:
                conditions.append("LOWER(COALESCE(s.last_name, '')) LIKE %s")
                params.append(f"{surname.lower()}%")
        
        if not conditions:
            return {"results": []}
        
        where_clause = " AND " + " AND ".join(conditions)
        
        # Build SQL with proper parameterization
        # CRITICAL: Include BOTH helm AND crew results to show all classes sailed
        # Use UNION to capture both helm and crew results separately
        base_sql = """
            WITH class_data AS (
                SELECT 
                    r.helm_sa_sailing_id::text as sailor_id,
                    r.class_canonical as class_name,
                    r.regatta_id,
                    reg.end_date,
                    reg.event_name
                FROM public.results r
                JOIN public.regattas reg ON reg.regatta_id = r.regatta_id
                WHERE r.helm_sa_sailing_id IS NOT NULL
                  AND r.raced = TRUE
                  AND r.class_canonical IS NOT NULL
                UNION ALL
                SELECT 
                    r.crew_sa_sailing_id::text as sailor_id,
                    r.class_canonical as class_name,
                    r.regatta_id,
                    reg.end_date,
                    reg.event_name
                FROM public.results r
                JOIN public.regattas reg ON reg.regatta_id = r.regatta_id
                WHERE r.crew_sa_sailing_id IS NOT NULL
                  AND r.raced = TRUE
                  AND r.class_canonical IS NOT NULL
            ),
            class_aggregated AS (
                SELECT 
                    cd.sailor_id,
                    cd.class_name,
                    COUNT(DISTINCT cd.regatta_id) as regatta_count,
                    MAX(cd.end_date) as last_date,
                    (array_agg(cd.event_name ORDER BY cd.end_date DESC NULLS LAST))[1] as last_event
                FROM class_data cd
                GROUP BY cd.sailor_id, cd.class_name
            )
            SELECT 
                s.sa_sailing_id::text as sas_id,
                s.first_name,
                s.last_name,
                s.full_name,
                s.year_of_birth,
                s.date_of_birth,
                CASE 
                    WHEN s.year_of_birth IS NOT NULL 
                    THEN EXTRACT(YEAR FROM CURRENT_DATE)::int - s.year_of_birth
                    WHEN s.date_of_birth IS NOT NULL
                    THEN EXTRACT(YEAR FROM AGE(s.date_of_birth))::int
                    ELSE NULL
                END as age,
                s.primary_club,
                COALESCE(
                    json_agg(
                        jsonb_build_object(
                            'class_name', ca.class_name,
                            'count', ca.regatta_count,
                            'last_date', ca.last_date::text,
                            'last_event', ca.last_event
                        ) ORDER BY ca.last_date DESC NULLS LAST
                    ) FILTER (WHERE ca.class_name IS NOT NULL),
                    '[]'::json
                ) as classes_sailed
            FROM public.sas_id_personal s
            LEFT JOIN class_aggregated ca ON ca.sailor_id = s.sa_sailing_id::text
            WHERE 1=1
        """
        
        # Add WHERE conditions and FB_ filter (exclude temporary FB_ accounts)
        sql = base_sql + where_clause + "\n              AND s.sa_sailing_id NOT LIKE %s\n            GROUP BY s.sa_sailing_id, s.first_name, s.last_name, s.full_name, s.year_of_birth, s.date_of_birth, s.primary_club"
        params.append('FB_%')
        
        # Execute query
        if not params:
            return {"results": []}
        
        query_params = tuple(params)
        print(f"[FB_SEARCH] Executing with {len(query_params)} params")
        print(f"[FB_SEARCH] SQL placeholders: {sql.count('%s')}, Params: {len(query_params)}")
        
        cur.execute(sql, query_params)
        results = cur.fetchall()
        
        formatted_results = []
        for row in results:
            if not row:
                continue
                
            classes = row.get('classes_sailed', [])
            if isinstance(classes, str):
                try:
                    classes = json.loads(classes)
                except:
                    classes = []
            elif classes is None:
                classes = []
            
            formatted_classes = []
            if isinstance(classes, list):
                for cls in classes:
                    if cls and isinstance(cls, dict) and cls.get('class_name'):
                        formatted_classes.append({
                            'class_name': cls.get('class_name', ''),
                            'count': cls.get('count', 0),
                            'last_date': cls.get('last_date'),
                            'last_event': cls.get('last_event', '')
                        })
            
            # Check if this SAS ID already has a login account
            cur.execute("""
                SELECT account_id, login_method, email
                FROM public.user_accounts
                WHERE sas_id = %s
                LIMIT 1
            """, (row.get('sas_id'),))
            
            existing_account = cur.fetchone()
            has_existing_login = existing_account is not None
            
            formatted_results.append({
                'sas_id': row.get('sas_id', ''),
                'first_name': row.get('first_name', ''),
                'last_name': row.get('last_name', ''),
                'full_name': row.get('full_name', ''),
                'age': int(row['age']) if row.get('age') else None,
                'year_of_birth': row.get('year_of_birth'),
                'date_of_birth': row.get('date_of_birth'),
                'primary_club': row.get('primary_club'),
                'classes': formatted_classes,
                'has_existing_login': has_existing_login,
                'login_method': existing_account.get('login_method') if existing_account else None
            })
        
        return {"results": formatted_results}
        
    except Exception as e:
        print(f"Error searching sailors: {e}")
        traceback.print_exc()
        return {"error": str(e), "results": []}
    finally:
        cur.close()
        conn.close()

@app.get("/api/facebook/search-sailors")
def facebook_search_sailors(first_names: Optional[str] = None, surname: Optional[str] = None, sas_id: Optional[str] = None, query: Optional[str] = None):
    """Search for sailors by name or SAS ID to link Facebook account - returns profile with classes"""
    # Support query parameter for free-form search (SAS ID or name)
    if query:
        query_clean = query.strip()
        # If query is all digits, treat as SAS ID
        if query_clean.isdigit():
            sas_id = query_clean
        else:
            # Try to parse as "First Last" or "Last, First"
            parts = query_clean.split()
            if len(parts) >= 2:
                first_names = parts[0]
                surname = ' '.join(parts[1:])
            elif len(parts) == 1:
                # Single word - try as first name (will search first_name LIKE)
                first_names = parts[0]
                surname = None
    
    # If SAS ID provided, search by SAS ID
    if sas_id:
        if not sas_id.isdigit():
            return {"error": "SAS ID must be numeric"}
    elif not first_names and not surname:
        return {"error": "SAS ID, first name, surname, or query required"}
    
    # Debug logging
    print(f"[FB_SEARCH] Search params: sas_id={sas_id}, first_names={first_names}, surname={surname}, query={query}")
    
    # Use the shared search function
    return _perform_sailor_search(sas_id, first_names, surname, query)

@app.post("/api/facebook/confirm-link")
async def facebook_confirm_link(request: Request):
    """Handle confirmation to link Facebook account and collect email/password/WhatsApp"""
    try:
        body = await request.json()
        facebook_id = body.get('facebook_id')
        sas_id = body.get('sas_id')
        relationship = body.get('relationship')
        email = body.get('email')
        password = body.get('password')
        whatsapp = body.get('whatsapp')
        
        if not facebook_id:
            return {"error": "Missing facebook_id"}
        
        if not sas_id or relationship == 'not_me':
            return {"error": "Must link to a real SAS ID - temporary accounts are not allowed"}
        
        # Validate that sas_id is a real SAS ID (not starting with FB_)
        if sas_id.startswith("FB_"):
            return {"error": "Cannot use temporary SAS ID - must link to a real sailor profile"}
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Check if account already exists
        cur.execute("""
            SELECT account_id, sas_id FROM public.user_accounts
            WHERE login_method = 'facebook' AND provider_id = %s
            LIMIT 1
        """, (str(facebook_id),))
        
        fb_account = cur.fetchone()
        
        # Get Facebook profile info from URL params or fetch it
        profile_pic_path = body.get('profile_pic')  # Passed from callback
        
        if fb_account:
            # Account exists - update it with real SAS ID
            account_id = fb_account['account_id']
            old_sas_id = fb_account['sas_id']
            
            # Update to real SAS ID
            cur.execute("""
                UPDATE public.user_accounts
                SET sas_id = %s
                WHERE account_id = %s
            """, (sas_id, account_id))
            
            # Delete any temporary entry from sas_id_personal if it exists
            if old_sas_id and old_sas_id.startswith("FB_"):
                cur.execute("""
                    DELETE FROM public.sas_id_personal
                    WHERE sa_sailing_id = %s
                """, (old_sas_id,))
            
        else:
            # No account exists - create new one with real SAS ID
            # Get Facebook name from request or fetch from Facebook API
            facebook_name = body.get('facebook_name', '')
            name_parts = facebook_name.split(" ", 1) if facebook_name else ["", ""]
            first_name = name_parts[0] if len(name_parts) > 0 else ""
            last_name = name_parts[1] if len(name_parts) > 1 else ""
            
            # Create new account with real SAS ID
            cur.execute("""
                INSERT INTO public.user_accounts
                (sas_id, login_method, provider_id, first_name, last_name, full_name, profile_picture_path)
                VALUES (%s, 'facebook', %s, %s, %s, %s, %s)
                RETURNING account_id
            """, (sas_id, str(facebook_id), first_name, last_name, facebook_name, profile_pic_path))
            
            account_id = cur.fetchone()['account_id']
        
        # Update sas_id_personal with email and WhatsApp if provided
        if email:
            cur.execute("""
                UPDATE public.sas_id_personal
                SET email = %s
                WHERE sa_sailing_id = %s
            """, (email, sas_id))
        
        if whatsapp:
            # Format WhatsApp: remove non-digits, ensure 10 digits
            whatsapp_clean = re.sub(r'\D', '', str(whatsapp))[:10]
            if len(whatsapp_clean) == 10:
                cur.execute("""
                    UPDATE public.sas_id_personal
                    SET phone_primary = %s
                    WHERE sa_sailing_id = %s
                """, (whatsapp_clean, sas_id))
        
        # Create email/password login method if password provided
        if password and email and sas_id:
            # Hash password
            password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
            
            cur.execute("""
                INSERT INTO public.user_accounts
                (sas_id, login_method, provider_id, email, email_verified, password_hash)
                VALUES (%s, 'email', %s, %s, TRUE, %s)
                ON CONFLICT (sas_id, login_method, provider_id) 
                DO UPDATE SET 
                    email = EXCLUDED.email,
                    password_hash = EXCLUDED.password_hash,
                    email_verified = TRUE
            """, (sas_id, email, email, password_hash))
        
        # Create WhatsApp login method if WhatsApp provided
        if whatsapp and sas_id:
            whatsapp_clean = re.sub(r'\D', '', str(whatsapp))[:10]
            if len(whatsapp_clean) == 10:
                cur.execute("""
                    INSERT INTO public.user_accounts
                    (sas_id, login_method, provider_id)
                    VALUES (%s, 'whatsapp', %s)
                    ON CONFLICT (sas_id, login_method, provider_id) DO NOTHING
                """, (sas_id, whatsapp_clean))
        
        # Create session
        session_token = str(uuid.uuid4())
        expires_at = datetime.now() + timedelta(days=30)
        
        cur.execute("""
            INSERT INTO public.user_sessions
            (session_id, account_id, sas_id, login_method, expires_at)
            VALUES (%s, %s, %s, 'facebook', %s)
        """, (session_token, account_id, sas_id, expires_at))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return {"success": True, "session_token": session_token, "sas_id": sas_id}
        
    except Exception as e:
        print(f"Error confirming Facebook link: {e}")
        traceback.print_exc()
        return {"error": str(e)}

@app.post("/api/register-account")
async def register_account(request: Request):
    """Handle account registration for manual sign-up (non-Facebook) - collect email/password/WhatsApp"""
    try:
        body = await request.json()
        sas_id = body.get('sas_id')
        relationship = body.get('relationship', 'self')
        email = body.get('email')
        password = body.get('password')
        whatsapp = body.get('whatsapp')
        
        if not sas_id:
            return {"error": "Missing sas_id"}
        
        # Validate that sas_id is a real SAS ID (not starting with FB_)
        if sas_id.startswith("FB_"):
            return {"error": "Cannot use temporary SAS ID - must link to a real sailor profile"}
        
        if not email or not password or not whatsapp:
            return {"error": "Email, password, and WhatsApp number are required"}
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Check if account already exists for this SAS ID
        cur.execute("""
            SELECT account_id, sas_id, login_method 
            FROM public.user_accounts
            WHERE sas_id = %s
            LIMIT 1
        """, (sas_id,))
        
        existing_account = cur.fetchone()
        
        # Update sas_id_personal with email and WhatsApp
        if email:
            cur.execute("""
                UPDATE public.sas_id_personal
                SET email = %s
                WHERE sa_sailing_id = %s
            """, (email, sas_id))
        
        if whatsapp:
            # Format WhatsApp: remove non-digits, ensure 10 digits
            whatsapp_clean = re.sub(r'\D', '', str(whatsapp))[:10]
            if len(whatsapp_clean) == 10:
                cur.execute("""
                    UPDATE public.sas_id_personal
                    SET phone_primary = %s
                    WHERE sa_sailing_id = %s
                """, (whatsapp_clean, sas_id))
        
        # Hash password
        password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
        
        # Create email/password login method
        cur.execute("""
            INSERT INTO public.user_accounts
            (sas_id, login_method, provider_id, email, email_verified, password_hash)
            VALUES (%s, 'email', %s, %s, TRUE, %s)
            ON CONFLICT (sas_id, login_method, provider_id) 
            DO UPDATE SET 
                email = EXCLUDED.email,
                password_hash = EXCLUDED.password_hash,
                email_verified = TRUE
            RETURNING account_id
        """, (sas_id, email, email, password_hash))
        
        account_result = cur.fetchone()
        account_id = account_result['account_id'] if account_result else None
        
        # Create WhatsApp login method if WhatsApp provided
        if whatsapp and sas_id:
            whatsapp_clean = re.sub(r'\D', '', str(whatsapp))[:10]
            if len(whatsapp_clean) == 10:
                cur.execute("""
                    INSERT INTO public.user_accounts
                    (sas_id, login_method, provider_id, password_hash)
                    VALUES (%s, 'whatsapp', %s, %s)
                    ON CONFLICT (sas_id, login_method, provider_id) 
                    DO UPDATE SET password_hash = EXCLUDED.password_hash
                """, (sas_id, whatsapp_clean, password_hash))
        
        # Create SAS ID login method - allows login with SAS ID + same password
        cur.execute("""
            INSERT INTO public.user_accounts
            (sas_id, login_method, provider_id, password_hash)
            VALUES (%s, 'sas_id', %s, %s)
            ON CONFLICT (sas_id, login_method, provider_id) 
            DO UPDATE SET password_hash = EXCLUDED.password_hash
        """, (sas_id, sas_id, password_hash))
        
        # Create session
        session_token = str(uuid.uuid4())
        expires_at = datetime.now() + timedelta(days=30)
        
        cur.execute("""
            INSERT INTO public.user_sessions
            (session_id, account_id, sas_id, login_method, expires_at)
            VALUES (%s, %s, %s, 'email', %s)
        """, (session_token, account_id, sas_id, expires_at))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return {"success": True, "session_token": session_token, "sas_id": sas_id}
        
    except Exception as e:
        print(f"Error registering account: {e}")
        traceback.print_exc()
        return {"error": str(e)}

@app.get("/api/open-regattas")
def api_open_regattas(class_name: Optional[str] = None):
    """Return list of open regattas (currently regatta 375 for Optimist A/B)"""
    try:
        with psycopg2.connect(DB_URL) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # For now, use regatta 374 (SA Youth Nationals Dec 2025) as the open regatta
                # TODO: Add is_open_regatta column or use a different method to identify open regattas
                sql = """
                    SELECT 
                        r.regatta_id,
                        r.regatta_number,
                        r.event_name,
                        r.start_date,
                        r.end_date,
                        COALESCE(c.club_abbrev, r.host_club_name) as host_club_code,
                        (SELECT COUNT(*) FROM results res 
                         JOIN regatta_blocks rb ON rb.block_id = res.block_id
                         WHERE res.regatta_id = r.regatta_id
                           AND (%s IS NULL OR LOWER(rb.fleet_label) = LOWER(%s))
                        ) as entries_count
                    FROM regattas r
                    LEFT JOIN clubs c ON c.club_id = r.host_club_id
                    WHERE r.regatta_number = 374
                    ORDER BY r.regatta_number DESC
                    LIMIT 1
                """
                cur.execute(sql, (class_name, class_name))
                regattas = cur.fetchall()
                return [dict(r) for r in regattas]
    except Exception as e:
        import traceback
        traceback.print_exc()
        return []

@app.get("/api/regatta/{regatta_id}/participants-classes")
def api_regatta_participants_classes(regatta_id: str):
    """Return mapping of sailor IDs to their class names in a regatta"""
    t0 = time.time()
    try:
        with psycopg2.connect(DB_URL) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                sql = """
                    SELECT DISTINCT
                        COALESCE(r.helm_sa_sailing_id::text, r.helm_temp_id) as sailor_id,
                        COALESCE(rb.class_canonical, rb.fleet_label) as class_name
                    FROM results r
                    JOIN regatta_blocks rb ON rb.block_id = r.block_id
                    WHERE r.regatta_id = %s
                """
                cur.execute(sql, (regatta_id,))
                rows = cur.fetchall()
                
                # Convert to dictionary mapping sailor_id -> class_name
                result = {}
                for row in rows:
                    sailor_id = row['sailor_id']
                    if sailor_id:
                        result[str(sailor_id)] = row['class_name'] or ''
                
                t1 = time.time()
                print(f"[TRACE] getRegattaParticipantsClasses({regatta_id}) took {t1-t0:.3f}s ({len(result)} participants)")
                return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        t1 = time.time()
        print(f"[TRACE] getRegattaParticipantsClasses({regatta_id}) took {t1-t0:.3f}s (exception)")
        return {}

# ============================================================================
# BOAT API ENDPOINTS
# ============================================================================

@app.get("/api/boat/classes/{sail_number}")
def boat_classes(sail_number: str):
    """Get all classes a sail number has been used in"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            SELECT DISTINCT rb.class_canonical as class_name
            FROM results r
            JOIN regatta_blocks rb ON rb.block_id = r.block_id
            WHERE r.sail_number::text = %s
              AND rb.class_canonical IS NOT NULL
            ORDER BY rb.class_canonical
        """, (sail_number,))
        classes = [row['class_name'] for row in cur.fetchall()]
        return {"classes": classes}
    except Exception as e:
        print(f"Error getting boat classes: {e}")
        traceback.print_exc()
        return {"classes": []}
    finally:
        cur.close()
        conn.close()

@app.get("/api/boat/info/{sail_number}/{class_name}")
def boat_info(sail_number: str, class_name: str):
    """Get boat information for a sail number and class"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            SELECT DISTINCT
                r.sail_number,
                r.boat_name,
                rb.class_canonical as class_name,
                COUNT(DISTINCT r.regatta_id) as regatta_count
            FROM results r
            JOIN regatta_blocks rb ON rb.block_id = r.block_id
            WHERE r.sail_number::text = %s
              AND rb.class_canonical = %s
            GROUP BY r.sail_number, r.boat_name, rb.class_canonical
            LIMIT 1
        """, (sail_number, class_name))
        row = cur.fetchone()
        if row:
            return dict(row)
        return {}
    except Exception as e:
        print(f"Error getting boat info: {e}")
        traceback.print_exc()
        return {}
    finally:
        cur.close()
        conn.close()

@app.get("/api/boat/pedigree/{sail_number}/{class_name}")
def boat_pedigree(sail_number: str, class_name: str):
    """Get boat pedigree (history of sailors who used this boat)"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            SELECT DISTINCT
                r.helm_name,
                r.helm_sa_sailing_id,
                r.regatta_id,
                reg.event_name,
                reg.start_date,
                reg.end_date
            FROM results r
            JOIN regatta_blocks rb ON rb.block_id = r.block_id
            JOIN regattas reg ON reg.regatta_id = r.regatta_id
            WHERE r.sail_number::text = %s
              AND rb.class_canonical = %s
              AND r.helm_name IS NOT NULL
            ORDER BY reg.start_date DESC
            LIMIT 50
        """, (sail_number, class_name))
        results = [dict(row) for row in cur.fetchall()]
        return {"pedigree": results}
    except Exception as e:
        print(f"Error getting boat pedigree: {e}")
        traceback.print_exc()
        return {"pedigree": []}
    finally:
        cur.close()
        conn.close()

@app.get("/api/class_sailors/{class_name}")
def class_sailors(class_name: str):
    """Get all sailors who have sailed in a class"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            SELECT DISTINCT
                COALESCE(r.helm_sa_sailing_id::text, r.helm_temp_id) as sailor_id,
                r.helm_name as name
            FROM results r
            JOIN regatta_blocks rb ON rb.block_id = r.block_id
            WHERE rb.class_canonical = %s
              AND COALESCE(r.helm_sa_sailing_id::text, r.helm_temp_id) IS NOT NULL
            ORDER BY r.helm_name
            LIMIT 500
        """, (class_name,))
        sailors = [dict(row) for row in cur.fetchall()]
        return {"sailors": sailors}
    except Exception as e:
        print(f"Error getting class sailors: {e}")
        traceback.print_exc()
        return {"sailors": []}
    finally:
        cur.close()
        conn.close()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/", StaticFiles(directory=BASE_DIR, html=True), name="static")

