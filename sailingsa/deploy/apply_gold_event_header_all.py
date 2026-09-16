#!/usr/bin/env python3
"""GOLD Event URL headers for every event (title, host, Final, host-logo fallback, child render)."""
from pathlib import Path
import shutil
import time

SHEET = Path("/var/www/sailingsa/sailingsa/backend/cape_classic_fleet_sheet.py")
API = Path("/var/www/sailingsa/api/api.py")
MARK = "GOLD_EVENT_HEADER_ALL_v1"

TITLE_OLD = '''def cape_classic_event_header_title(raw: str, regatta_id: Optional[str] = None) -> str:
    """Event-card title: year + Zeekoe Vlei Cape Classic (not the date-slug)."""
    if not is_cape_classic_2026_zvy_event(regatta_id):
        return str(raw or "").strip()
    return CAPE_CLASSIC_HEADER_TITLE
'''

TITLE_NEW = '''def cape_classic_event_header_title(raw: str, regatta_id: Optional[str] = None, start_date=None) -> str:
    """Event URL title: year + name. Strip YYYY-MM-DD. Cape Classic 2026 ZVY keeps its gold string."""
    if is_cape_classic_2026_zvy_event(regatta_id):
        return CAPE_CLASSIC_HEADER_TITLE
    name = str(raw or "").strip()
    year = None
    m = re.match(r"^(\\d{4})-(\\d{2})-(\\d{2})\\s+", name)
    if m:
        year = m.group(1)
        name = name[m.end():].strip()
    if re.match(r"^\\d{4}\\b", name):
        return name
    if start_date is not None:
        try:
            year = str(getattr(start_date, "year", None) or str(start_date)[:4])
        except Exception:
            year = year
    if not year and regatta_id:
        ym = re.match(r"^(\\d{4})", str(regatta_id))
        if ym:
            year = ym.group(1)
    if year and name:
        return f"{year} {name}"
    return name
'''

HELPERS = r'''
def _gold_event_header_all_v1_marker():
    return "GOLD_EVENT_HEADER_ALL_v1"


def _gold_title_year_name(raw, regatta_id=None, start_date=None):
    try:
        from sailingsa.backend.cape_classic_fleet_sheet import cape_classic_event_header_title
        return cape_classic_event_header_title(raw, str(regatta_id or ""), start_date)
    except Exception:
        return str(raw or "").strip()


def _gold_status_word_if_results(status_word, fleets):
    word = (status_word or "Final").strip() or "Final"
    if word.casefold() in ("unknown", "unk", "") and fleets:
        return "Final"
    return word


def _gold_infer_event_host(regatta_id: str, event_name: str = ""):
    """Host from club code in name/slug, else majority club on result rows."""
    rid = str(regatta_id or "").strip()
    blob = f"{rid} {event_name or ''}"
    try:
        _fn = globals().get("_resolve_club_from_event_name")
        got = _fn(blob) if callable(_fn) else None
        if got:
            cid, abbrev, full = got[0], got[1], got[2]
            slug = _get_club_slug_by_id(cid) if cid else (str(abbrev or "").lower() or None)
            text = _format_regatta_host_display(abbrev or "", full or "", "")
            if text:
                return {
                    "abbrev": (abbrev or "").strip(),
                    "fullname": (full or "").strip(),
                    "club_id": cid,
                    "slug": slug,
                    "text": text,
                }
    except Exception:
        pass
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cur.execute(
                """
                SELECT COALESCE(NULLIF(btrim(r.club_raw), ''), NULLIF(btrim(c.club_abbrev), ''), '(blank)') AS club,
                       MAX(c.club_id) AS club_id,
                       MAX(NULLIF(btrim(c.club_abbrev), '')) AS abbrev,
                       MAX(NULLIF(btrim(c.club_fullname), '')) AS fullname,
                       COUNT(*) AS n
                FROM results r
                LEFT JOIN clubs c ON c.club_id = r.club_id
                WHERE r.regatta_id = %s
                GROUP BY 1
                ORDER BY n DESC
                """,
                (rid,),
            )
            rows = [x for x in (cur.fetchall() or []) if str(x.get("club") or "") not in ("(blank)", "")]
            if not rows:
                return None
            top = rows[0]
            if len(rows) > 1 and int(top.get("n") or 0) == int(rows[1].get("n") or 0):
                return None
            abbrev = (top.get("abbrev") or top.get("club") or "").strip()
            full = (top.get("fullname") or "").strip()
            cid = top.get("club_id")
            if not cid and abbrev:
                try:
                    cur.execute(
                        """
                        SELECT club_id, club_abbrev, club_fullname
                        FROM clubs
                        WHERE upper(club_abbrev)=upper(%s)
                           OR upper(club_fullname)=upper(%s)
                           OR club_fullname ILIKE %s
                        LIMIT 1
                        """,
                        (abbrev, abbrev, abbrev + "%"),
                    )
                    c = cur.fetchone()
                    if c:
                        cid = c.get("club_id")
                        abbrev = (c.get("club_abbrev") or abbrev).strip()
                        full = (c.get("club_fullname") or full).strip()
                except Exception:
                    pass
            slug = _get_club_slug_by_id(cid) if cid else (abbrev.lower() if abbrev else None)
            text = _format_regatta_host_display(abbrev, full, abbrev)
            if not text:
                return None
            return {
                "abbrev": abbrev,
                "fullname": full,
                "club_id": cid,
                "slug": slug,
                "text": text,
            }
        finally:
            cur.close()
            return_db_connection(conn)
    except Exception as e:
        print(f"[gold_header] infer host {rid}: {e}", flush=True)
        return None


def _gold_parent_fleet_for_empty_child(slug: str):
    """Child Event URL with no rows: render the matching parent fleet."""
    s = str(slug or "").strip()
    if not s:
        return None
    shell = None
    try:
        shell = _resolve_fleet_shell_public_slug(s)
    except Exception:
        shell = None
    if not shell:
        parts = s.split("-")
        for i in range(len(parts) - 1, 2, -1):
            parent = "-".join(parts[:i])
            try:
                preg = _get_regatta_by_regatta_id(parent) or _get_regatta_by_slug(parent)
            except Exception:
                preg = None
            if not preg:
                continue
            tail = "-".join(parts[i:])
            try:
                probe = _resolve_fleet_shell_public_slug(f"{preg[0]}-{tail}")
            except Exception:
                probe = None
            if probe:
                shell = probe
                break
    if not shell:
        return None
    rid, bid = shell
    reg = _get_regatta_by_regatta_id(rid)
    if not reg:
        return None
    data = _get_regatta_full_page_data(rid, only_block_id=bid)
    if not data or not data[4]:
        data = _get_regatta_full_page_data(rid)
    if not data or not data[4]:
        return None
    return reg, data, bid


'''

CALL_TITLE_OLD = "            display_name = cape_classic_event_header_title(display_name, str(regatta_id))\n"
CALL_TITLE_NEW = "            display_name = cape_classic_event_header_title(display_name, str(regatta_id), start_d)\n"

STATUS_OLD = """        status_word = (result_status or "Final").strip() or "Final"
        status_line_text = _format_regatta_status_line(
            status_word, as_at_time, str(regatta_id), end_date=end_d, start_date=start_d
        )
"""

STATUS_NEW = """        status_word = _gold_status_word_if_results((result_status or "Final").strip() or "Final", fleets)
        status_line_text = _format_regatta_status_line(
            status_word, as_at_time, str(regatta_id), end_date=end_d, start_date=start_d
        )
"""

HOST_OLD = """        host_club_text = _format_regatta_host_display(
            host_club_abbrev, host_club_fullname, (host_club_legacy or host_club_name or "")
        )
"""

HOST_NEW = """        host_club_text = _format_regatta_host_display(
            host_club_abbrev, host_club_fullname, (host_club_legacy or host_club_name or "")
        )
        if not (host_club_text or "").strip():
            _gh = _gold_infer_event_host(str(regatta_id), ev_name or event_name)
            if _gh:
                host_club_abbrev = _gh.get("abbrev") or host_club_abbrev
                host_club_fullname = _gh.get("fullname") or host_club_fullname
                if _gh.get("club_id"):
                    host_club_id = _gh["club_id"]
                    host_club_slug = _gh.get("slug") or _get_club_slug_by_id(host_club_id)
                elif _gh.get("slug"):
                    host_club_slug = _gh["slug"]
                host_club_text = _gh["text"]
"""

LOGO_OLD = """        if not lu:
            try:
                lu = _regatta_main_header_left_class_logo_url(str(regatta_id))
            except Exception:
                lu = None
        _host_code_logo = _regatta_host_club_code_resolved(
"""

LOGO_NEW = """        if not lu:
            try:
                lu = _regatta_main_header_left_class_logo_url(str(regatta_id))
            except Exception:
                lu = None
        _host_code_logo = _regatta_host_club_code_resolved(
"""

# host-logo fallback inserted after _host_code_logo assignment block
LOGO2_OLD = """        if not ru and _host_code_logo:
            _ensure_club_logo_cached(_host_code_logo, host_club_slug)
        left_logo_col = _regatta_standalone_left_logo_column_html(lu, str(regatta_id), ev_name or event_name)
"""

LOGO2_NEW = """        if not ru and _host_code_logo:
            _ensure_club_logo_cached(_host_code_logo, host_club_slug)
        if not lu and _host_code_logo:
            try:
                lu = _regatta_host_club_logo_src_for_code(_host_code_logo)
            except Exception:
                lu = None
        left_logo_col = _regatta_standalone_left_logo_column_html(lu, str(regatta_id), ev_name or event_name)
"""

DATA_OLD = """    if not data:
        _fleet_parent_redir = _redirect_missing_fleet_shell_to_parent(requested_slug)
        if _fleet_parent_redir is not None:
            return _fleet_parent_redir
        return _regatta_not_found_response(slug)
"""

DATA_NEW = """    if not data or (isinstance(data, (list, tuple)) and len(data) > 4 and not data[4]):
        _child = _gold_parent_fleet_for_empty_child(requested_slug)
        if _child:
            reg, data, only_block_id = _child
            regatta_id, event_name, start_date, end_date, host_club_name, host_club_id = reg
    if not data:
        _fleet_parent_redir = _redirect_missing_fleet_shell_to_parent(requested_slug)
        if _fleet_parent_redir is not None:
            return _fleet_parent_redir
        return _regatta_not_found_response(slug)
"""

REDIR_OLD = '''def _regatta_slug_redirect_target(slug: str) -> Optional[str]:
    rid = str(slug).strip()
    if not rid:
        return None
    j = _read_regatta_slug_redirects().get(rid)
    if isinstance(j, str) and j.strip():
        return j.strip()
    return _REGATTA_STANDALONE_SLUG_REDIRECTS.get(rid)
'''

REDIR_NEW = '''def _regatta_slug_redirect_target(slug: str) -> Optional[str]:
    rid = str(slug).strip()
    if not rid:
        return None
    _GOLD_SLUG_FIX = {
        "2026-09-14-hbyc-vulcan-challenge": "/regatta/2026-09-13-vulcan-challenge",
        "2024-08-31-lipton-cup": "/regatta/2026-08-29-lipton-challenge-cup",
    }
    if rid in _GOLD_SLUG_FIX:
        return _GOLD_SLUG_FIX[rid]
    j = _read_regatta_slug_redirects().get(rid)
    if isinstance(j, str) and j.strip():
        return j.strip()
    return _REGATTA_STANDALONE_SLUG_REDIRECTS.get(rid)
'''

LIPTON_OLD = """                + f'<div class="status-line">{status_line_text}</div>'
                + _regatta_live_board_badge_html(
                    str(regatta_id), start_d, end_d, sa_toggle=bool(is_sa)
                )
"""

LIPTON_NEW = """                + cape_classic_event_header_status_html(status_line_text, str(regatta_id))
                + _regatta_live_board_badge_html(
                    str(regatta_id), start_d, end_d, sa_toggle=bool(is_sa)
                )
"""


def main() -> None:
    sheet = SHEET.read_text()
    api = API.read_text()
    if MARK in api and "start_date=None" in sheet.split("def cape_classic_event_header_title", 1)[-1][:400]:
        print("ALREADY")
        return
    ts = time.strftime("%Y%m%d_%H%M%S")
    if TITLE_OLD not in sheet:
        raise SystemExit("TITLE_BLOCK_MISSING")
    shutil.copy2(SHEET, SHEET.with_name(f"cape_classic_fleet_sheet.py.bak.gold_hdr.{ts}"))
    SHEET.write_text(sheet.replace(TITLE_OLD, TITLE_NEW, 1))
    print("SHEET_OK")

    shutil.copy2(API, API.with_name(f"api.py.bak.gold_hdr.{ts}"))
    api = API.read_text()
    if MARK not in api:
        needle = "def serve_regatta_standalone(slug: str, request: Request):"
        if needle not in api:
            raise SystemExit("SERVE_FN_MISSING")
        api = api.replace(needle, HELPERS + "\n" + needle, 1)
    if CALL_TITLE_OLD not in api:
        raise SystemExit("TITLE_CALL_MISSING")
    api = api.replace(CALL_TITLE_OLD, CALL_TITLE_NEW)
    if STATUS_OLD not in api:
        raise SystemExit("STATUS_BLOCK_MISSING")
    api = api.replace(STATUS_OLD, STATUS_NEW)
    if HOST_OLD not in api:
        raise SystemExit("HOST_BLOCK_MISSING")
    api = api.replace(HOST_OLD, HOST_NEW, 1)
    if LOGO2_OLD not in api:
        raise SystemExit("LOGO_BLOCK_MISSING")
    api = api.replace(LOGO2_OLD, LOGO2_NEW, 1)
    if DATA_OLD not in api:
        raise SystemExit("DATA_BLOCK_MISSING")
    api = api.replace(DATA_OLD, DATA_NEW, 1)
    if REDIR_OLD not in api:
        raise SystemExit("REDIR_BLOCK_MISSING")
    api = api.replace(REDIR_OLD, REDIR_NEW, 1)
    if LIPTON_OLD in api:
        api = api.replace(LIPTON_OLD, LIPTON_NEW, 1)
        print("LIPTON_STATUS_OK")
    else:
        print("LIPTON_STATUS_SKIP")
    API.write_text(api)
    print("API_OK", MARK)


if __name__ == "__main__":
    main()
