#!/usr/bin/env python3
"""Shorten the two EXH1-proven long-held pool occupants.

EXH1 (44 exhaust events, all requester req_n=0):
  holders: 191x _get_sailor_name_by_slug, 128x q < _wc_helm_cell_html
  requesters: 27x q < _wc_helm_cell_html during regatta HTML

Dominant cause is long-held checkouts, not requester-side nesting.

1) _get_sailor_name_by_slug held its pooled connection across
   _get_sailor_by_name_slug_from_results (own get_db + multi-second
   REGEXP scans on results). Return the lookup conn first.
2) _wc_helm_cell_html re-queried sas_id_personal via q() per row
   during HTML render. helm_name is already SAS-truthed in
   _get_regatta_full_page_data after that function returned its conn.
"""
from pathlib import Path
import sys

p = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")
text = p.read_text(encoding="utf-8", errors="replace")

if "_slug_need_results_fb" in text and "POOL_EXHAUST_HOLDERS" in text:
    raise SystemExit("already patched")

old_helm = '''    helm_raw = str(r.get("helm_name") or "").strip()
    sid = str(r.get("helm_sa_sailing_id") or "").strip()
    if sid:
        try:
            _sn = q(
                """
                SELECT COALESCE(NULLIF(TRIM(full_name), ''), TRIM(COALESCE(first_name,'') || ' ' || COALESCE(last_name,''))) AS n
                FROM sas_id_personal
                WHERE sa_sailing_id::text = %s
                LIMIT 1
                """,
                (sid,),
            )
            if _sn and _sn[0].get("n"):
                helm_raw = str(_sn[0].get("n") or "").strip() or helm_raw
        except Exception:
            pass
    parts = _wc_co_skipper_name_parts(helm_raw)
'''
new_helm = '''    helm_raw = str(r.get("helm_name") or "").strip()
    parts = _wc_co_skipper_name_parts(helm_raw)
'''
if old_helm not in text:
    raise SystemExit("helm q() block missing")
text = text.replace(old_helm, new_helm, 1)

old_slug_init = '''def _get_sailor_name_by_slug(slug: str):
    """Return (full_name, canonical_slug) for sailor or (None, None). Used for server-side SEO HTML."""
    if not slug or not slug.strip():
        return None, None
    slug = slug.strip()
    try:
        conn = get_db_connection()
'''
new_slug_init = '''def _get_sailor_name_by_slug(slug: str):
    """Return (full_name, canonical_slug) for sailor or (None, None). Used for server-side SEO HTML."""
    if not slug or not slug.strip():
        return None, None
    slug = slug.strip()
    _slug_need_results_fb = None
    try:
        conn = get_db_connection()
'''
if old_slug_init not in text:
    raise SystemExit("slug init missing")
text = text.replace(old_slug_init, new_slug_init, 1)

old_fb = '''            if not rows:
                # Fallback: name-only slug from results (regatta page links)
                name_from_res, sid_from_res = _get_sailor_by_name_slug_from_results(slug)
                if name_from_res and sid_from_res:
                    return name_from_res, _slug_from_name(name_from_res)
                cur.execute(
                    """
                    SELECT sailor_name, sailor_slug
                    FROM ranking_audit_entries
                    WHERE lower(sailor_slug) = lower(%s)
                    ORDER BY audit_id DESC
                    LIMIT 1
                    """,
                    (slug,),
                )
                rank_row = cur.fetchone()
                if rank_row and (rank_row.get("sailor_slug") or rank_row.get("sailor_name")):
                    rname = (rank_row.get("sailor_name") or "").strip()
                    rslug = (rank_row.get("sailor_slug") or slug).strip()
                    return rname or None, rslug
                return None, None
            r = rows[0]
'''
new_fb = '''            if not rows:
                # Return this checkout before the results-table fallback.
                # That helper borrows its own connection and can run for seconds.
                _slug_need_results_fb = slug
            else:
                r = rows[0]
'''
if old_fb not in text:
    raise SystemExit("slug fallback block missing")
text = text.replace(old_fb, new_fb, 1)

# The success-path body after `r = rows[0]` must stay inside the new else.
# After replace, those lines are still at the old indent (siblings of else).
# Re-indent the four statements that belong to the else.
old_else_body = '''            else:
                r = rows[0]
            name = _sas_personal_display_name(
                r.get("first_name") or "",
                r.get("last_name") or "",
                r.get("full_name_raw") or "",
            )
            sid = str(r.get("sas_id") or "")
            slugs = _batch_sailor_slugs_for_sas_ids([sid], conn=conn) if sid and sid.isdigit() else {}
            return name, slugs.get(sid) or _slug_from_name(name)
'''
new_else_body = '''            else:
                r = rows[0]
                name = _sas_personal_display_name(
                    r.get("first_name") or "",
                    r.get("last_name") or "",
                    r.get("full_name_raw") or "",
                )
                sid = str(r.get("sas_id") or "")
                slugs = _batch_sailor_slugs_for_sas_ids([sid], conn=conn) if sid and sid.isdigit() else {}
                return name, slugs.get(sid) or _slug_from_name(name)
'''
if old_else_body not in text:
    raise SystemExit("slug else-body missing")
text = text.replace(old_else_body, new_else_body, 1)

old_tail = '''    except Exception as e:
        print(f"[SEO] _get_sailor_name_by_slug: {e}")
        return None, None


# 1x1 transparent PNG so club-logo returns 200 when no file exists (no 404 in console)
'''
new_tail = '''    except Exception as e:
        print(f"[SEO] _get_sailor_name_by_slug: {e}")
        return None, None
    if _slug_need_results_fb:
        name_from_res, sid_from_res = _get_sailor_by_name_slug_from_results(_slug_need_results_fb)
        if name_from_res and sid_from_res:
            return name_from_res, _slug_from_name(name_from_res)
        try:
            with db_connection() as conn:
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                try:
                    cur.execute(
                        """
                        SELECT sailor_name, sailor_slug
                        FROM ranking_audit_entries
                        WHERE lower(sailor_slug) = lower(%s)
                        ORDER BY audit_id DESC
                        LIMIT 1
                        """,
                        (_slug_need_results_fb,),
                    )
                    rank_row = cur.fetchone()
                    if rank_row and (rank_row.get("sailor_slug") or rank_row.get("sailor_name")):
                        rname = (rank_row.get("sailor_name") or "").strip()
                        rslug = (rank_row.get("sailor_slug") or _slug_need_results_fb).strip()
                        return rname or None, rslug
                finally:
                    cur.close()
        except Exception as e:
            print(f"[SEO] _get_sailor_name_by_slug audit: {e}")
        return None, None
    return None, None


# POOL_EXHAUST_HOLDERS
# 1x1 transparent PNG so club-logo returns 200 when no file exists (no 404 in console)
'''
if old_tail not in text:
    raise SystemExit("slug tail missing")
text = text.replace(old_tail, new_tail, 1)

old_add = '''    with _exhaust_lock:
        _exhaust_holds[id(wrapped)] = rec
'''
new_add = '''    with _exhaust_lock:
        _exhaust_holds[id(wrapped)] = rec
        n = len(_exhaust_holds)
    try:
        with open("/tmp/ssa_hold_peaks.json", "a", encoding="utf-8") as fh:
            if n >= 8:
                fh.write(f"{n}\\t{rec.get('pid')}\\t{rec.get('site')}\\t{rec.get('path')}\\n")
    except Exception:
        pass
'''
if old_add not in text:
    raise SystemExit("exhaust add missing")
text = text.replace(old_add, new_add, 1)

old_drop = '''    with _exhaust_lock:
        _exhaust_holds.pop(id(conn), None)
'''
new_drop = '''    rec = None
    with _exhaust_lock:
        rec = _exhaust_holds.pop(id(conn), None)
    try:
        if rec and rec.get("t0"):
            age_ms = round((time.time() - float(rec["t0"])) * 1000.0, 1)
            if age_ms >= 200:
                print(
                    f"[DB] HOLD_MS={age_ms} site={rec.get('site')} path={rec.get('path')}",
                    flush=True,
                )
    except Exception:
        pass
'''
if old_drop not in text:
    raise SystemExit("exhaust drop missing")
text = text.replace(old_drop, new_drop, 1)

p.write_text(text, encoding="utf-8")
print(f"patched pool-exhaust holders {p}")
