#!/usr/bin/env python3
"""One-pass production DB ownership cleanup on live api.py.

Rule: BORROW → EXECUTE/FETCH → RETURN → CPU/HTML/JSON/logo/fs/network.
Does not change SQL text or /dev-1 HTML output. Leaves /auth/session alone.
"""
from pathlib import Path
import sys

p = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")
text = p.read_text(encoding="utf-8", errors="replace")
if "DB_OWNERSHIP_AUDIT_V1" in text:
    raise SystemExit("already patched")

n = 0

# 1) Request-path raw connects → bounded pool CM. SQL unchanged.
c1 = text.count("with psycopg2.connect(DB_URL) as conn:")
if c1:
    text = text.replace("with psycopg2.connect(DB_URL) as conn:", "with db_connection() as conn:")
    n += c1
    print(f"connect→db_connection {c1}")

# 2) Pooled connections must return to the pool, not conn.close().
repls = [
    (
        """    finally:
        cur.close()
        conn.close()

@app.get("/api/regatta/{regatta_id}/class-entries")
""",
        """    finally:
        try:
            cur.close()
        except Exception:
            pass
        return_db_connection(conn)

@app.get("/api/regatta/{regatta_id}/class-entries")
""",
    ),
    (
        """    cur.close()
    conn.close()
    return {"total": len(boats), "fleet_counts": fleet_counts, "boats": [dict(b) for b in boats]}
""",
        """    cur.close()
    return_db_connection(conn)
    return {"total": len(boats), "fleet_counts": fleet_counts, "boats": [dict(b) for b in boats]}
""",
    ),
    (
        """    cur.close()
    conn.close()
    return {"total": len(boats), "class_counts": class_counts, "boats": [dict(b) for b in boats]}
""",
        """    cur.close()
    return_db_connection(conn)
    return {"total": len(boats), "class_counts": class_counts, "boats": [dict(b) for b in boats]}
""",
    ),
    (
        """    finally:
        try:
            if conn is not None:
                conn.close()
        except Exception:
            pass


def lean_traffic_api_live(request: Request):
""",
        """    finally:
        try:
            if conn is not None:
                return_db_connection(conn)
        except Exception:
            pass


def lean_traffic_api_live(request: Request):
""",
    ),
]
for old, new in repls:
    if old not in text:
        raise SystemExit(f"close-repl missing:\n{old[:80]!r}")
    text = text.replace(old, new, 1)
    n += 1

# own=True close of a pooled checkout
old_own = """            if conn is not None:
                if own:
                    conn.close()
                else:
                    return_db_connection(conn)
"""
new_own = """            if conn is not None:
                if own:
                    return_db_connection(conn)
                else:
                    return_db_connection(conn)
"""
if old_own not in text:
    raise SystemExit("own-close missing")
text = text.replace(old_own, new_own, 1)
n += 1

# 3) Yearly helpers: reuse caller conn (the #126 nest).
old_yc = '''def _yearly_series_distinct_year_counts_map() -> dict[str, int]:
    """series_key -> number of distinct calendar years (same grouping as /yearly-events)."""
'''
new_yc = '''def _yearly_series_distinct_year_counts_map(conn=None) -> dict[str, int]:
    """series_key -> number of distinct calendar years (same grouping as /yearly-events)."""
'''
if old_yc not in text:
    raise SystemExit("yearly counts def missing")
text = text.replace(old_yc, new_yc, 1)

old_yc_get = '''        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            SELECT r.event_name, r.start_date, COALESCE(r.end_date, r.start_date) AS end_date, r.regatta_id::text AS regatta_id
            FROM regattas r
            WHERE r.event_name IS NOT NULL AND TRIM(r.event_name) <> ''
            """
        )
'''
new_yc_get = '''        with _use_db_connection(conn) as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute(
            """
            SELECT r.event_name, r.start_date, COALESCE(r.end_date, r.start_date) AS end_date, r.regatta_id::text AS regatta_id
            FROM regattas r
            WHERE r.event_name IS NOT NULL AND TRIM(r.event_name) <> ''
            """
        )
'''
# This indent will be messy. Do a cleaner full-function replace via line logic below if this fails.
if old_yc_get not in text:
    raise SystemExit("yearly counts get missing")

# Safer: rewrite the yearly-counts body get/finally using unique finally.
old_yc_body_head = '''    conn = None
    try:
        if not table_exists("regattas"):
            return {}
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
'''
new_yc_body_head = '''    owned = conn is None
    try:
        if not table_exists("regattas"):
            return {}
        if owned:
            conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
'''
if old_yc_body_head not in text:
    raise SystemExit("yearly counts body head missing")
text = text.replace(old_yc_body_head, new_yc_body_head, 1)

old_yc_fin = '''    finally:
        if conn:
            return_db_connection(conn)
'''
new_yc_fin = '''    finally:
        if owned and conn:
            return_db_connection(conn)
'''
# this finally pattern may appear twice — only replace the one after yearly counts
idx = text.find("def _yearly_series_distinct_year_counts_map")
idx2 = text.find("def _yearly_event_series_title")
chunk = text[idx:idx2]
if old_yc_fin not in chunk:
    raise SystemExit("yearly counts finally missing")
chunk = chunk.replace(old_yc_fin, new_yc_fin, 1)
text = text[:idx] + chunk + text[idx2:]
n += 1

old_ys = '''def _get_yearly_event_series() -> list[dict]:
    """Recurring event series from regattas table, ordered from current month cycle."""
    out = []
    if not table_exists("regattas") or not table_exists("results"):
        return out
    try:
        with db_connection() as conn:
'''
new_ys = '''def _get_yearly_event_series(conn=None) -> list[dict]:
    """Recurring event series from regattas table, ordered from current month cycle."""
    out = []
    if not table_exists("regattas") or not table_exists("results"):
        return out
    try:
        with _use_db_connection(conn) as conn:
'''
if old_ys not in text:
    raise SystemExit("yearly series def missing")
text = text.replace(old_ys, new_ys, 1)
n += 1

old_ym = '''def _yearly_series_max_and_history_maps() -> tuple[dict[str, int], dict[str, list]]:
    """Single pass over /yearly-events data: max entries per series_key (same as yearly row sort) + history rows."""
    max_by_sk: dict[str, int] = {}
    hist_by_sk: dict[str, list] = {}
    for r in _get_yearly_event_series():
'''
new_ym = '''def _yearly_series_max_and_history_maps(conn=None) -> tuple[dict[str, int], dict[str, list]]:
    """Single pass over /yearly-events data: max entries per series_key (same as yearly row sort) + history rows."""
    max_by_sk: dict[str, int] = {}
    hist_by_sk: dict[str, list] = {}
    for r in _get_yearly_event_series(conn=conn):
'''
if old_ym not in text:
    raise SystemExit("yearly max maps missing")
text = text.replace(old_ym, new_ym, 1)
n += 1

# 4) Upcoming events: reuse conn; drop extra nested db_connection; pass conn into cards/maps.
old_up_maps = '''        _series_max_map, _ = _yearly_series_max_and_history_maps()
        out["live"] = _apply_live_display_sort(cur, live_cards, series_max_entries_by_key=_series_max_map)
'''
new_up_maps = '''        _series_max_map, _ = _yearly_series_max_and_history_maps(conn=conn)
        out["live"] = _apply_live_display_sort(cur, live_cards, series_max_entries_by_key=_series_max_map)
'''
if old_up_maps not in text:
    raise SystemExit("upcoming maps call missing")
text = text.replace(old_up_maps, new_up_maps, 1)

old_up_card = '''            up_cards.append(_event_row_to_card(r, has_regatta_id, has_host_club_id, is_upcoming=True))
'''
new_up_card = '''            up_cards.append(_event_row_to_card(r, has_regatta_id, has_host_club_id, is_upcoming=True, conn=conn))
'''
if old_up_card not in text:
    raise SystemExit("upcoming card call missing")
text = text.replace(old_up_card, new_up_card, 1)

old_past_card = '''            out["past"].append(_event_row_to_card(r, has_regatta_id, has_host_club_id, is_upcoming=False, regattas_with_results=regattas_with_results))
'''
new_past_card = '''            out["past"].append(_event_row_to_card(r, has_regatta_id, has_host_club_id, is_upcoming=False, regattas_with_results=regattas_with_results, conn=conn))
'''
c_past = text.count(old_past_card)
if c_past < 1:
    raise SystemExit("past card call missing")
text = text.replace(old_past_card, new_past_card)
print(f"past card conn= {c_past}")

old_extra = '''            if past_need:
                # Fresh connection — long past-match can leave the primary cursor SSL-dead
                with db_connection() as _econn:
                    _ecur = _econn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                    try:
                        _attach_event_card_display_sort_fields(
                            _ecur, past_need, series_max_entries_by_key=_series_max_map
                        )
                    finally:
                        _ecur.close()
'''
new_extra = '''            if past_need:
                _attach_event_card_display_sort_fields(
                    cur, past_need, series_max_entries_by_key=_series_max_map
                )
'''
if old_extra not in text:
    raise SystemExit("upcoming extra db_connection missing")
text = text.replace(old_extra, new_extra, 1)
n += 1

# 5) Attach sort fields: reuse cur.connection for year-count map.
old_att = '''    ent_map = _batch_entries_by_regatta_ids(cur, rids)
    series_map = _yearly_series_distinct_year_counts_map()
'''
new_att = '''    ent_map = _batch_entries_by_regatta_ids(cur, rids)
    _att_conn = getattr(cur, "connection", None)
    series_map = _yearly_series_distinct_year_counts_map(conn=_att_conn)
'''
if old_att not in text:
    raise SystemExit("attach series_map missing")
text = text.replace(old_att, new_att, 1)
n += 1

# 6) Logo/hub chain: pass conn so event-card construction does not nest.
old_hub_icon = '''def _regatta_header_icon_source_regatta_id(regatta_id: Optional[str], conn=None) -> str:
    """Main header JSON lookup id: umbrella master when this slug is a linked child."""
    rid = str(regatta_id or "").strip()
    # Canonicalize known slug aliases (e.g. long 2023 MSC WC Dinghy → short results id)
    try:
        rid = REGATTA_ID_ALIASES.get(rid, rid)
    except Exception:
        pass
    return _regatta_header_hub_master_regatta_id(rid, conn=conn) or rid
'''
if old_hub_icon not in text:
    raise SystemExit("hub icon missing")

old_uses = '''def _regatta_slug_uses_header_icon_json(regatta_id: Optional[str]) -> bool:
    """True when wc_regatta_header_icons.json may supply left/right logo URLs."""
    rid = str(regatta_id or "").strip()
    src = _regatta_header_icon_source_regatta_id(rid)
'''
new_uses = '''def _regatta_slug_uses_header_icon_json(regatta_id: Optional[str], conn=None) -> bool:
    """True when wc_regatta_header_icons.json may supply left/right logo URLs."""
    rid = str(regatta_id or "").strip()
    src = _regatta_header_icon_source_regatta_id(rid, conn=conn)
'''
if old_uses not in text:
    raise SystemExit("uses header json missing")
text = text.replace(old_uses, new_uses, 1)

old_logo = '''def _regatta_card_event_logo_url(
    rid: str,
    regatta_name: Optional[str],
    *,
    cur=None,
    class_logo_by_rid: Optional[dict] = None,
) -> Optional[str]:
    """Search-card left logo = same Event/Class artwork as /regatta main header (never host club)."""
    _rid = str(rid or "").strip()
    if not _rid:
        return None
    cls_map = class_logo_by_rid or {}
    icon_rid = _regatta_header_icon_source_regatta_id(_rid)
    ls: Optional[str] = None
    if _regatta_slug_uses_header_icon_json(_rid):
'''
new_logo = '''def _regatta_card_event_logo_url(
    rid: str,
    regatta_name: Optional[str],
    *,
    cur=None,
    conn=None,
    class_logo_by_rid: Optional[dict] = None,
) -> Optional[str]:
    """Search-card left logo = same Event/Class artwork as /regatta main header (never host club)."""
    _rid = str(rid or "").strip()
    if not _rid:
        return None
    if conn is None and cur is not None:
        conn = getattr(cur, "connection", None)
    cls_map = class_logo_by_rid or {}
    icon_rid = _regatta_header_icon_source_regatta_id(_rid, conn=conn)
    ls: Optional[str] = None
    if _regatta_slug_uses_header_icon_json(_rid, conn=conn):
'''
if old_logo not in text:
    raise SystemExit("card logo url missing")
text = text.replace(old_logo, new_logo, 1)
n += 1

old_row = '''def _event_row_to_card(r, has_regatta_id, has_host_club_id, is_upcoming, regattas_with_results=None):
'''
new_row = '''def _event_row_to_card(r, has_regatta_id, has_host_club_id, is_upcoming, regattas_with_results=None, conn=None):
'''
if old_row not in text:
    raise SystemExit("event_row_to_card def missing")
text = text.replace(old_row, new_row, 1)

old_row_logo = '''                event_logo_url = _regatta_card_event_logo_url(rid_for_logo, event_name) or ""
'''
new_row_logo = '''                event_logo_url = _regatta_card_event_logo_url(rid_for_logo, event_name, conn=conn) or ""
'''
if old_row_logo not in text:
    raise SystemExit("event_row logo call missing")
text = text.replace(old_row_logo, new_row_logo, 1)

old_left = '''            icon_rids.add(_regatta_header_icon_source_regatta_id(rid))
'''
new_left = '''            icon_rids.add(_regatta_header_icon_source_regatta_id(rid, conn=getattr(cur, "connection", None)))
'''
if old_left not in text:
    raise SystemExit("left logos hub call missing")
text = text.replace(old_left, new_left, 1)
n += 1

# apply_live / upcoming default maps reuse — they have cur
old_app_up = '''    if series_max_entries_by_key is None:
        series_max_entries_by_key, _ = _yearly_series_max_and_history_maps()
    _attach_event_card_display_sort_fields(
        cur, upcoming_only_cards, series_max_entries_by_key=series_max_entries_by_key
'''
new_app_up = '''    if series_max_entries_by_key is None:
        series_max_entries_by_key, _ = _yearly_series_max_and_history_maps(conn=getattr(cur, "connection", None))
    _attach_event_card_display_sort_fields(
        cur, upcoming_only_cards, series_max_entries_by_key=series_max_entries_by_key
'''
if old_app_up not in text:
    raise SystemExit("apply upcoming maps missing")
text = text.replace(old_app_up, new_app_up, 1)

old_app_live = '''    if series_max_entries_by_key is None:
        series_max_entries_by_key, _ = _yearly_series_max_and_history_maps()
    _attach_event_card_display_sort_fields(
        cur, live_cards, series_max_entries_by_key=series_max_entries_by_key
'''
new_app_live = '''    if series_max_entries_by_key is None:
        series_max_entries_by_key, _ = _yearly_series_max_and_history_maps(conn=getattr(cur, "connection", None))
    _attach_event_card_display_sort_fields(
        cur, live_cards, series_max_entries_by_key=series_max_entries_by_key
'''
if old_app_live not in text:
    raise SystemExit("apply live maps missing")
text = text.replace(old_app_live, new_app_live, 1)
n += 1

# Marker
text = text.replace(
    "class _RequestConnTracker:",
    "class _RequestConnTracker:\n    # DB_OWNERSHIP_AUDIT_V1\n",
    1,
)

p.write_text(text, encoding="utf-8")
print(f"patched {p} steps={n}")
