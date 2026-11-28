#!/usr/bin/env python3
"""Surgical live api.py patch: keep landing fleet counts fresh while live,
and let named-event HTML flip Live Event → Full Results after end_date.

Never overwrite live api.py with the repo copy. This edits in place.
Marker: LIVE_LIST_COUNTS_v1
"""
from __future__ import annotations

from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
MARKER = "LIVE_LIST_COUNTS_v1"

HELPER = r'''
def _events_logos_html_cache_ttl(html: str) -> float:
    """Live Event cards must rebuild after end_date; long TTL would freeze the button."""
    if "sa-home-regatta-btn--live" in (html or ""):
        return 120.0
    return _EVENTS_LOGOS_HTML_TTL_SEC


def _refresh_live_regatta_list_entry_counts(rows) -> None:
    """Re-count live parents from results/blocks so 7-day with-counts cache cannot freeze fleet chips."""
    if not rows:
        return
    live_ids = []
    by_id = {}
    for d in rows:
        if not isinstance(d, dict):
            continue
        rid = str(d.get("regatta_id") or "").strip()
        if not rid:
            continue
        by_id[rid] = d
        if d.get("is_live"):
            live_ids.append(rid)
    live_ids = list(dict.fromkeys(live_ids))
    if not live_ids:
        return
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT rb.regatta_id::text AS rid,
                   rb.block_id::text AS block_id,
                   COUNT(r.result_id)::int AS entries
            FROM regatta_blocks rb
            LEFT JOIN results r ON r.block_id = rb.block_id
            WHERE rb.regatta_id::text = ANY(%s)
            GROUP BY rb.regatta_id, rb.block_id
            """,
            (live_ids,),
        )
        by_parent: dict = {}
        for rid, block_id, entries in cur.fetchall() or []:
            rid_s = str(rid or "").strip()
            bid = str(block_id or "").strip()
            if not rid_s or not bid:
                continue
            child_id = bid.replace(":", "-", 1) if ":" in bid else f"{rid_s}-{bid}"
            by_parent.setdefault(rid_s, {})[child_id] = int(entries or 0)
        cur.execute(
            """
            SELECT regatta_id::text, COUNT(*)::int
            FROM results
            WHERE regatta_id::text = ANY(%s)
            GROUP BY regatta_id
            """,
            (live_ids,),
        )
        parent_totals = {str(r or "").strip(): int(n or 0) for r, n in (cur.fetchall() or [])}
        for rid in live_ids:
            d = by_id.get(rid)
            if not d:
                continue
            kids = d.get("children") or []
            counts = by_parent.get(rid) or {}
            if kids:
                for ch in kids:
                    cid = str(ch.get("regatta_id") or "").strip()
                    if cid in counts:
                        ch["entries_count"] = counts[cid]
                try:
                    d["entries_count"] = sum(int(c.get("entries_count") or 0) for c in kids)
                except Exception:
                    d["entries_count"] = parent_totals.get(rid, d.get("entries_count") or 0)
            else:
                d["entries_count"] = parent_totals.get(rid, d.get("entries_count") or 0)
    finally:
        cur.close()
        conn.close()


'''

CACHE_HIT_OLD = '''                    try:
                        _attach_regatta_live_board_fields(_cached)
                    except Exception:
                        pass
                    return _cached[:_lim]'''

CACHE_HIT_NEW = '''                    try:
                        _attach_regatta_live_board_fields(_cached)
                        _refresh_live_regatta_list_entry_counts(_cached)
                    except Exception:
                        pass
                    return _cached[:_lim]'''

DISK_HIT_OLD = '''                        try:
                            _attach_regatta_live_board_fields(disk_data)
                        except Exception:
                            pass
                        _REGATTA_WITH_COUNTS_CACHE["data"] = disk_data
                        _REGATTA_WITH_COUNTS_CACHE["ts"] = now
                        _REGATTA_WITH_COUNTS_CACHE["limit"] = max(_lim, len(disk_data))
                        return disk_data[:_lim]'''

DISK_HIT_NEW = '''                        try:
                            _attach_regatta_live_board_fields(disk_data)
                            _refresh_live_regatta_list_entry_counts(disk_data)
                        except Exception:
                            pass
                        _REGATTA_WITH_COUNTS_CACHE["data"] = disk_data
                        _REGATTA_WITH_COUNTS_CACHE["ts"] = now
                        _REGATTA_WITH_COUNTS_CACHE["limit"] = max(_lim, len(disk_data))
                        return disk_data[:_lim]'''

GET_DETAIL_OLD = '''def _events_logos_cache_get_detail(slug: str) -> str | None:
    import os, time as _t, re as _re
    key = (slug or "").strip().lower()
    now = _t.time()
    details = _EVENTS_LOGOS_HTML_CACHE.setdefault("details", {})
    ent = details.get(key)
    if ent and (now - float(ent[0])) < _EVENTS_LOGOS_HTML_TTL_SEC:
        if _EVENTS_LOGOS_OG_CACHE_MARKER in (ent[1] or ""):
            return ent[1]
    safe = _re.sub(r"[^a-z0-9_-]+", "_", key)[:120]
    disk = os.path.join(_EVENTS_LOGOS_DISK, f"detail-{safe}.html")
    try:
        if os.path.isfile(disk) and os.path.getsize(disk) > 400:
            html = open(disk, encoding="utf-8", errors="replace").read()
            if html and _EVENTS_LOGOS_OG_CACHE_MARKER in html:
                details[key] = (now, html)
                return html
    except Exception:
        pass
    return None'''

GET_DETAIL_NEW = '''def _events_logos_cache_get_detail(slug: str) -> str | None:
    import os, time as _t, re as _re
    key = (slug or "").strip().lower()
    now = _t.time()
    details = _EVENTS_LOGOS_HTML_CACHE.setdefault("details", {})
    ent = details.get(key)
    if ent and (now - float(ent[0])) < _events_logos_html_cache_ttl(ent[1] if len(ent) > 1 else ""):
        if _EVENTS_LOGOS_OG_CACHE_MARKER in (ent[1] or ""):
            return ent[1]
    safe = _re.sub(r"[^a-z0-9_-]+", "_", key)[:120]
    disk = os.path.join(_EVENTS_LOGOS_DISK, f"detail-{safe}.html")
    try:
        if os.path.isfile(disk) and os.path.getsize(disk) > 400:
            html = open(disk, encoding="utf-8", errors="replace").read()
            ttl = _events_logos_html_cache_ttl(html)
            if html and _EVENTS_LOGOS_OG_CACHE_MARKER in html and (now - os.path.getmtime(disk)) < ttl:
                details[key] = (now, html)
                return html
    except Exception:
        pass
    return None'''

GET_GALLERY_OLD = '''def _events_logos_cache_get_gallery() -> str | None:
    import os, time as _t
    now = _t.time()
    ent = _EVENTS_LOGOS_HTML_CACHE
    if ent.get("gallery") and (now - float(ent.get("gallery_ts") or 0)) < _EVENTS_LOGOS_HTML_TTL_SEC:
        if _EVENTS_LOGOS_OG_CACHE_MARKER in (ent.get("gallery") or ""):
            return ent["gallery"]
    disk = os.path.join(_EVENTS_LOGOS_DISK, "gallery.html")
    try:
        if os.path.isfile(disk) and os.path.getsize(disk) > 500:
            html = open(disk, encoding="utf-8", errors="replace").read()
            if html and _EVENTS_LOGOS_OG_CACHE_MARKER in html:
                ent["gallery"] = html
                ent["gallery_ts"] = now
                return html
    except Exception:
        pass
    return None'''

GET_GALLERY_NEW = '''def _events_logos_cache_get_gallery() -> str | None:
    import os, time as _t
    now = _t.time()
    ent = _EVENTS_LOGOS_HTML_CACHE
    gallery_html = ent.get("gallery") or ""
    if gallery_html and (now - float(ent.get("gallery_ts") or 0)) < _events_logos_html_cache_ttl(gallery_html):
        if _EVENTS_LOGOS_OG_CACHE_MARKER in gallery_html:
            return ent["gallery"]
    disk = os.path.join(_EVENTS_LOGOS_DISK, "gallery.html")
    try:
        if os.path.isfile(disk) and os.path.getsize(disk) > 500:
            html = open(disk, encoding="utf-8", errors="replace").read()
            ttl = _events_logos_html_cache_ttl(html)
            if html and _EVENTS_LOGOS_OG_CACHE_MARKER in html and (now - os.path.getmtime(disk)) < ttl:
                ent["gallery"] = html
                ent["gallery_ts"] = now
                return html
    except Exception:
        pass
    return None'''

ANCHOR = '_REGATTA_WITH_COUNTS_DISK = "/var/tmp/sailingsa_regatta_with_counts.json"\n'


def main() -> int:
    text = API.read_text(encoding="utf-8")
    if MARKER in text:
        print("ALREADY_PATCHED")
        return 0
    if ANCHOR not in text:
        raise SystemExit("anchor missing")
    if CACHE_HIT_OLD not in text or DISK_HIT_OLD not in text:
        raise SystemExit("with-counts cache-hit block missing")
    if GET_DETAIL_OLD not in text or GET_GALLERY_OLD not in text:
        raise SystemExit("events-logos cache getters missing")
    helper = f"# {MARKER}\n" + HELPER
    text = text.replace(ANCHOR, ANCHOR + "\n" + helper, 1)
    text = text.replace(CACHE_HIT_OLD, CACHE_HIT_NEW, 1)
    text = text.replace(DISK_HIT_OLD, DISK_HIT_NEW, 1)
    text = text.replace(GET_DETAIL_OLD, GET_DETAIL_NEW, 1)
    text = text.replace(GET_GALLERY_OLD, GET_GALLERY_NEW, 1)
    if MARKER not in text:
        raise SystemExit("marker failed to insert")
    API.write_text(text, encoding="utf-8")
    print("PATCHED", API, "bytes", API.stat().st_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
