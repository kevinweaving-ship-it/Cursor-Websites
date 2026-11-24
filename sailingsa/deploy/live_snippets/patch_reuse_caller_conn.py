#!/usr/bin/env python3
"""Helpers reuse the caller connection when supplied (no extra nested borrow)."""
from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/api.py.patchwork")
text = SRC.read_text(encoding="utf-8", errors="replace")


def once(old: str, new: str, label: str) -> None:
    global text
    c = text.count(old)
    if c != 1:
        raise SystemExit(f"FAIL {label}: count={c}")
    text = text.replace(old, new, 1)
    print(f"OK {label}")


def many(old: str, new: str, label: str, expect: int) -> None:
    global text
    c = text.count(old)
    if c != expect:
        raise SystemExit(f"FAIL {label}: count={c} expect={expect}")
    text = text.replace(old, new)
    print(f"OK {label} x{expect}")


once(
    '''@contextmanager
def db_connection(request_id: str = None):
    """Borrow a pooled connection and always return it."""
    conn = get_db_connection(request_id)
    try:
        yield conn
    finally:
        return_db_connection(conn)
''',
    '''@contextmanager
def db_connection(request_id: str = None):
    """Borrow a pooled connection and always return it."""
    conn = get_db_connection(request_id)
    try:
        yield conn
    finally:
        return_db_connection(conn)


@contextmanager
def _use_db_connection(conn=None):
    """Reuse a caller-owned connection, or borrow one when called standalone."""
    if conn is not None:
        yield conn
        return
    with db_connection() as owned:
        yield owned
''',
    "add-use-db-connection",
)

once(
    '''def qf(sql, *args):
    """Execute query with connection pooling"""
    start = time.time()
    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, args)
            result = cur.fetchall()
            duration = time.time() - start  # Keep in seconds for logging
''',
    '''def qf(sql, *args, conn=None):
    """Execute query with connection pooling"""
    start = time.time()
    with _use_db_connection(conn) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, args)
            result = cur.fetchall()
            duration = time.time() - start  # Keep in seconds for logging
''',
    "qf-reuse",
)

once(
    '''def table_exists(name: str) -> bool:
    """Cached: avoid hammering information_schema under traffic."""
    key = ("t", str(name))
    hit = _SCHEMA_EXISTS_CACHE.get(key)
    if hit is not None:
        return hit
    try:
        res = qf("SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name=%s LIMIT 1", name)
''',
    '''def table_exists(name: str, conn=None) -> bool:
    """Cached: avoid hammering information_schema under traffic."""
    key = ("t", str(name))
    hit = _SCHEMA_EXISTS_CACHE.get(key)
    if hit is not None:
        return hit
    try:
        res = qf("SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name=%s LIMIT 1", name, conn=conn)
''',
    "table-exists-reuse",
)

once(
    '''def column_exists(table: str, col: str) -> bool:
    """Cached: avoid hammering information_schema under traffic."""
    key = ("c", str(table), str(col))
    hit = _SCHEMA_EXISTS_CACHE.get(key)
    if hit is not None:
        return hit
    try:
        res = qf("SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name=%s AND column_name=%s LIMIT 1", table, col)
''',
    '''def column_exists(table: str, col: str, conn=None) -> bool:
    """Cached: avoid hammering information_schema under traffic."""
    key = ("c", str(table), str(col))
    hit = _SCHEMA_EXISTS_CACHE.get(key)
    if hit is not None:
        return hit
    try:
        res = qf("SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name=%s AND column_name=%s LIMIT 1", table, col, conn=conn)
''',
    "column-exists-reuse",
)

once(
    '''        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        has_regatta_id = column_exists("events", "regatta_id")
        has_host_club_id = column_exists("events", "host_club_id")
        has_map_url = column_exists("events", "map_url")
        has_image_url = column_exists("events", "image_url")
        has_address = column_exists("events", "address")
        has_start_time = column_exists("events", "start_time")
        has_end_time = column_exists("events", "end_time")
        has_source = column_exists("events", "source")
''',
    '''        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        has_regatta_id = column_exists("events", "regatta_id", conn=conn)
        has_host_club_id = column_exists("events", "host_club_id", conn=conn)
        has_map_url = column_exists("events", "map_url", conn=conn)
        has_image_url = column_exists("events", "image_url", conn=conn)
        has_address = column_exists("events", "address", conn=conn)
        has_start_time = column_exists("events", "start_time", conn=conn)
        has_end_time = column_exists("events", "end_time", conn=conn)
        has_source = column_exists("events", "source", conn=conn)
''',
    "upcoming-column-exists-reuse",
)

once(
    '''        print("EVENTS: past query", round(t2 - t1, 3))
        # Resolve host_display to club when host_club_id is NULL. Use venue_raw when host_club_name_raw is association-only.
        if table_exists("clubs"):
''',
    '''        print("EVENTS: past query", round(t2 - t1, 3))
        # Resolve host_display to club when host_club_id is NULL. Use venue_raw when host_club_name_raw is association-only.
        if table_exists("clubs", conn=conn):
''',
    "upcoming-table-exists-clubs",
)

once(
    '''def _load_boat_norm_slug_map() -> dict:
    """Cached boat norm -> slug map for profile links (5 min TTL)."""
    global _boat_norm_slug_map_cache, _boat_norm_slug_map_cache_at
    now = time.time()
    if _boat_norm_slug_map_cache and (now - _boat_norm_slug_map_cache_at) < _BOAT_NORM_SLUG_CACHE_TTL_SEC:
        return _boat_norm_slug_map_cache
    if _boat_names_directory is None or not table_exists("results"):
''',
    '''def _load_boat_norm_slug_map(conn=None) -> dict:
    """Cached boat norm -> slug map for profile links (5 min TTL)."""
    global _boat_norm_slug_map_cache, _boat_norm_slug_map_cache_at
    now = time.time()
    if _boat_norm_slug_map_cache and (now - _boat_norm_slug_map_cache_at) < _BOAT_NORM_SLUG_CACHE_TTL_SEC:
        return _boat_norm_slug_map_cache
    if _boat_names_directory is None or not table_exists("results", conn=conn):
''',
    "boat-map-table-exists",
)

once(
    '''def _batch_sailor_slugs_for_sas_ids(sas_ids: list):
    """Return dict sas_id -> canonical_slug for regatta rows. Enables real /sailor/<slug> links."""
    if not sas_ids:
        return {}
    ids = list({str(i).strip() for i in sas_ids if i is not None and str(i).strip().isdigit()})
    if not ids:
        return {}
    try:
        with db_connection() as conn:
''',
    '''def _batch_sailor_slugs_for_sas_ids(sas_ids: list, conn=None):
    """Return dict sas_id -> canonical_slug for regatta rows. Enables real /sailor/<slug> links."""
    if not sas_ids:
        return {}
    ids = list({str(i).strip() for i in sas_ids if i is not None and str(i).strip().isdigit()})
    if not ids:
        return {}
    try:
        with _use_db_connection(conn) as conn:
''',
    "batch-slugs-reuse",
)

once(
    '''def _get_sailor_name_from_results(sas_id: str):
    """Fallback: get sailor name from results (helm/crew) when not in sas_id_personal. Returns (name, slug) or (None, None).
    Prefers name from sas_id_personal when available so slug matches official name."""
    if not sas_id or not str(sas_id).strip().isdigit():
        return None, None
    sid = str(sas_id).strip()
    name = _get_name_from_sas_id_personal(sid)
    if name:
        return name, _sailor_canonical_slug(name, sid, True)
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
''',
    '''def _get_sailor_name_from_results(sas_id: str, conn=None):
    """Fallback: get sailor name from results (helm/crew) when not in sas_id_personal. Returns (name, slug) or (None, None).
    Prefers name from sas_id_personal when available so slug matches official name."""
    if not sas_id or not str(sas_id).strip().isdigit():
        return None, None
    sid = str(sas_id).strip()
    name = _get_name_from_sas_id_personal(sid)
    if name:
        return name, _sailor_canonical_slug(name, sid, True)
    owned = conn is None
    try:
        if owned:
            conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
''',
    "sailor-name-from-results-reuse-open",
)

once(
    '''            if row and row.get("crew_name"):
                name = (row.get("crew_name") or "").strip()
                if name:
                    return name, _sailor_canonical_slug(name, sid, True)
        finally:
            cur.close()
            return_db_connection(conn)
    except Exception as e:
        print(f"[api] _get_sailor_name_from_results: {e}")
    return None, None
''',
    '''            if row and row.get("crew_name"):
                name = (row.get("crew_name") or "").strip()
                if name:
                    return name, _sailor_canonical_slug(name, sid, True)
        finally:
            cur.close()
            if owned:
                return_db_connection(conn)
    except Exception as e:
        print(f"[api] _get_sailor_name_from_results: {e}")
    return None, None
''',
    "sailor-name-from-results-reuse-close",
)

once(
    '''def _get_club_slug_by_id(club_id):
    """Return club slug for club_id or None."""
    if not club_id:
        return None
    try:
        with db_connection() as conn:
''',
    '''def _get_club_slug_by_id(club_id, conn=None):
    """Return club slug for club_id or None."""
    if not club_id:
        return None
    try:
        with _use_db_connection(conn) as conn:
''',
    "club-slug-reuse",
)

once(
    '''def _regatta_header_hub_master_regatta_id(regatta_id: Optional[str]) -> Optional[str]:
    """Umbrella master regatta_id for a child fleet shell (event_regatta_links), else None."""
    rid = str(regatta_id or "").strip()
    if not rid:
        return None
    if rid in _header_hub_master_cache:
        return _header_hub_master_cache[rid]
    master: Optional[str] = None
    if table_exists("event_regatta_links"):
        conn = None
        cur = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
''',
    '''def _regatta_header_hub_master_regatta_id(regatta_id: Optional[str], conn=None) -> Optional[str]:
    """Umbrella master regatta_id for a child fleet shell (event_regatta_links), else None."""
    rid = str(regatta_id or "").strip()
    if not rid:
        return None
    if rid in _header_hub_master_cache:
        return _header_hub_master_cache[rid]
    master: Optional[str] = None
    if table_exists("event_regatta_links", conn=conn):
        owned = conn is None
        work = conn
        cur = None
        try:
            if owned:
                work = get_db_connection()
            cur = work.cursor()
''',
    "header-master-reuse-open",
)

once(
    '''        except Exception as e:
            print(f"[header] hub master lookup {rid}: {e}")
        finally:
            if cur:
                cur.close()
            if conn:
                return_db_connection(conn)
    _header_hub_master_cache[rid] = master
    return master
''',
    '''        except Exception as e:
            print(f"[header] hub master lookup {rid}: {e}")
        finally:
            if cur:
                cur.close()
            if owned and work:
                return_db_connection(work)
    _header_hub_master_cache[rid] = master
    return master
''',
    "header-master-reuse-close",
)

once(
    '''def _regatta_header_icon_source_regatta_id(regatta_id: Optional[str]) -> str:
    """Main header JSON lookup id: umbrella master when this slug is a linked child."""
    rid = str(regatta_id or "").strip()
    # Canonicalize known slug aliases (e.g. long 2023 MSC WC Dinghy → short results id)
    try:
        rid = REGATTA_ID_ALIASES.get(rid, rid)
    except Exception:
        pass
    return _regatta_header_hub_master_regatta_id(rid) or rid
''',
    '''def _regatta_header_icon_source_regatta_id(regatta_id: Optional[str], conn=None) -> str:
    """Main header JSON lookup id: umbrella master when this slug is a linked child."""
    rid = str(regatta_id or "").strip()
    # Canonicalize known slug aliases (e.g. long 2023 MSC WC Dinghy → short results id)
    try:
        rid = REGATTA_ID_ALIASES.get(rid, rid)
    except Exception:
        pass
    return _regatta_header_hub_master_regatta_id(rid, conn=conn) or rid
''',
    "header-icon-source-reuse",
)

once(
    '''    event_idx = _catalogue_event_index()
    class_map = _catalogue_class_path_map()
    icon_rids: set[str] = set()
    for d in rows:
        rid = str(d.get("regatta_id") or "").strip()
        if rid:
            icon_rids.add(_regatta_header_icon_source_regatta_id(rid))
''',
    '''    event_idx = _catalogue_event_index()
    class_map = _catalogue_class_path_map()
    icon_rids: set[str] = set()
    own_conn = None
    try:
        own_conn = getattr(cur, "connection", None)
        if own_conn is None:
            inner = getattr(cur, "_cur", None)
            own_conn = getattr(inner, "connection", None) if inner is not None else None
    except Exception:
        own_conn = None
    for d in rows:
        rid = str(d.get("regatta_id") or "").strip()
        if rid:
            icon_rids.add(_regatta_header_icon_source_regatta_id(rid, conn=own_conn))
''',
    "attach-logos-pass-conn",
)

once(
    '''                name_from_res, canon_from_res = _get_sailor_name_from_results(str(sas_id).strip())
                return (name_from_res, canon_from_res) if (name_from_res and canon_from_res) else (None, None)
            full_name = (row.get("full_name") or "").strip()
            if not full_name:
                return None, None
            slugs = _batch_sailor_slugs_for_sas_ids([str(sas_id).strip()])
''',
    '''                name_from_res, canon_from_res = _get_sailor_name_from_results(str(sas_id).strip(), conn=conn)
                return (name_from_res, canon_from_res) if (name_from_res and canon_from_res) else (None, None)
            full_name = (row.get("full_name") or "").strip()
            if not full_name:
                return None, None
            slugs = _batch_sailor_slugs_for_sas_ids([str(sas_id).strip()], conn=conn)
''',
    "redirect-pass-conn",
)

many(
    "                        slugs = _batch_sailor_slugs_for_sas_ids([sid])\n",
    "                        slugs = _batch_sailor_slugs_for_sas_ids([sid], conn=conn)\n",
    "name-by-slug-batch-sid-24",
    2,
)

many(
    "                    slugs = _batch_sailor_slugs_for_sas_ids([sid])\n",
    "                    slugs = _batch_sailor_slugs_for_sas_ids([sid], conn=conn)\n",
    "name-by-slug-batch-sid-20",
    2,
)

many(
    "                name_from_results, _ = _get_sailor_name_from_results(sid)\n",
    "                name_from_results, _ = _get_sailor_name_from_results(sid, conn=conn)\n",
    "name-by-slug-from-results",
    2,
)

once(
    '''            slugs = _batch_sailor_slugs_for_sas_ids([sid]) if sid and sid.isdigit() else {}
            return name, slugs.get(sid) or _slug_from_name(name)
        finally:
            cur.close()
            return_db_connection(conn)
    except Exception as e:
        print(f"[SEO] _get_sailor_name_by_slug: {e}")
''',
    '''            slugs = _batch_sailor_slugs_for_sas_ids([sid], conn=conn) if sid and sid.isdigit() else {}
            return name, slugs.get(sid) or _slug_from_name(name)
        finally:
            cur.close()
            return_db_connection(conn)
    except Exception as e:
        print(f"[SEO] _get_sailor_name_by_slug: {e}")
''',
    "name-by-slug-final-batch",
)

once(
    '''                    sids = [str(x.get("sas_id") or "") for x in srows if x.get("sas_id")]
                    smap = _batch_sailor_slugs_for_sas_ids(sids) if sids else {}
''',
    '''                    sids = [str(x.get("sas_id") or "") for x in srows if x.get("sas_id")]
                    smap = _batch_sailor_slugs_for_sas_ids(sids, conn=conn) if sids else {}
''',
    "seo-discovery-batch",
)

if "def _use_db_connection(" not in text:
    raise SystemExit("missing _use_db_connection")
if text.count("def qf(sql, *args, conn=None)") != 1:
    raise SystemExit("qf signature")

SRC.write_text(text, encoding="utf-8")
print(f"WROTE {SRC} lines={text.count(chr(10))}")
