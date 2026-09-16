#!/usr/bin/env python3
"""GOLD leftovers v2: child Event URLs render; Lipton two-line status; 2024 slug."""
from pathlib import Path
import shutil
import time

API = Path("/var/www/sailingsa/api/api.py")
MARK = "GOLD_LEFTOVERS_v2"

OWN_OLD = """    only_block_id: Optional[str] = None
    reg = None
    shell = _resolve_fleet_shell_public_slug(requested_slug)
    if shell:
"""

OWN_NEW = """    only_block_id: Optional[str] = None
    reg = _get_regatta_by_regatta_id(requested_slug)
    shell = None if reg else _resolve_fleet_shell_public_slug(requested_slug)
    if shell:
"""

CLASS_OLD = """    try:
        event_name = ev_name or reg[1]
        base_url = _canonical_base_url()
        canonical_url = f"{base_url}/regatta/{regatta_id}/class-{_class_canonical_slug(class_name)}"
"""

CLASS_NEW = """    try:
        from sailingsa.backend.cape_classic_fleet_sheet import (
            cape_classic_event_header_title,
            cape_classic_event_header_status_html,
        )
        event_name = cape_classic_event_header_title(ev_name or reg[1], str(regatta_id), start_d)
        base_url = _canonical_base_url()
        canonical_url = f"{base_url}/regatta/{regatta_id}/class-{_class_canonical_slug(class_name)}"
"""

LIPTON_OLD = """                + _regatta_lipton_venue_host_block_html(str(regatta_id))
                + f'<div class="status-line">{status_line_text}</div>'
                + _regatta_live_board_badge_html(
"""

LIPTON_NEW = """                + _regatta_lipton_venue_host_block_html(str(regatta_id))
                + '<div class="regatta-header-status-stack">'
                + cape_classic_event_header_status_html(status_line_text, str(regatta_id))
                + _cape_classic_total_entries_line_html(str(regatta_id), fleets)
                + "</div>"
                + _regatta_live_board_badge_html(
"""

REDIR_OLD = '        "2024-08-31-lipton-cup": "/regatta/2026-08-29-lipton-challenge-cup",\n'
REDIR_NEW = '        "2024-08-31-lipton-cup": "/regatta/2024-08-31-lipton-challenge-cup",\n'

CLASS_FAIL_OLD = """    except Exception as e:
        print(f"[serve_regatta_class_standalone] {e}", flush=True)
        return HTMLResponse(content=_HTML_SOFT_FAIL_200, status_code=200, media_type="text/html")
"""

CLASS_FAIL_NEW = """    except Exception as e:
        print(f"[serve_regatta_class_standalone] {e}", flush=True)
        try:
            return RedirectResponse(url=f"/regatta/{rid_q}", status_code=302)
        except Exception:
            return HTMLResponse(content=_HTML_SOFT_FAIL_200, status_code=200, media_type="text/html")
"""

MARKER = '''
def _gold_leftovers_v2_marker():
    return "GOLD_LEFTOVERS_v2"

'''


def main() -> None:
    api = API.read_text()
    if MARK in api and OWN_NEW in api and CLASS_NEW in api and LIPTON_NEW in api:
        print("ALREADY")
        return
    ts = time.strftime("%Y%m%d_%H%M%S")
    shutil.copy2(API, API.with_name(f"api.py.bak.gold_left_v2.{ts}"))
    if MARK not in api:
        needle = "def serve_regatta_standalone(slug: str, request: Request):"
        if needle not in api:
            raise SystemExit("SERVE_FN_MISSING")
        api = api.replace(needle, MARKER + needle, 1)
    if OWN_OLD not in api:
        raise SystemExit("OWN_BLOCK_MISSING")
    api = api.replace(OWN_OLD, OWN_NEW, 1)
    if CLASS_OLD not in api:
        raise SystemExit("CLASS_IMPORT_MISSING")
    api = api.replace(CLASS_OLD, CLASS_NEW, 1)
    n_lipton = api.count(LIPTON_OLD)
    if n_lipton < 1:
        raise SystemExit("LIPTON_STATUS_MISSING")
    api = api.replace(LIPTON_OLD, LIPTON_NEW)
    print("LIPTON_REPLACED", n_lipton)
    if REDIR_OLD in api:
        api = api.replace(REDIR_OLD, REDIR_NEW, 1)
        print("REDIR_2024_OK")
    else:
        print("REDIR_2024_SKIP")
    if CLASS_FAIL_OLD in api:
        api = api.replace(CLASS_FAIL_OLD, CLASS_FAIL_NEW, 1)
        print("CLASS_FAIL_OK")
    else:
        print("CLASS_FAIL_SKIP")
    API.write_text(api)
    print("API_OK", MARK)


if __name__ == "__main__":
    main()
