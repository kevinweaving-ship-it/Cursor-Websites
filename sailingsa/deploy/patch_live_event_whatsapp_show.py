#!/usr/bin/env python3
"""Surgical live api.py patch: Super Admin + Club Admin WhatsApp show/hide toggle."""
from pathlib import Path
import sys

API = Path("/var/www/sailingsa/api/api.py")

FUNCS = r'''
def _session_can_toggle_event_whatsapp(request: Request, regatta_id: str) -> bool:
    """Super admin, generic admin, or club admin of the event host club."""
    if _session_role_is_super_admin(request) or _session_role_is_admin(request):
        return True
    return _session_can_edit_regatta_scores(request, regatta_id)


def _event_whatsapp_has_group(regatta_id: str) -> bool:
    rid = str(regatta_id or "").strip()
    if not rid:
        return False
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                """
                SELECT 1 FROM public.event_whatsapp_groups
                WHERE is_current AND regatta_id = %s
                LIMIT 1
                """,
                (rid,),
            )
            return bool(cur.fetchone())
        finally:
            cur.close()
            return_db_connection(conn)
    except Exception:
        return False


def _event_whatsapp_show_on_event(regatta_id: str) -> bool:
    rid = str(regatta_id or "").strip()
    if not rid:
        return False
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                """
                SELECT COALESCE(show_on_event, false) AS show_on_event
                FROM public.event_whatsapp_groups
                WHERE is_current AND regatta_id = %s
                LIMIT 1
                """,
                (rid,),
            )
            row = cur.fetchone()
            if not row:
                return False
            if isinstance(row, dict):
                return bool(row.get("show_on_event"))
            return bool(row[0])
        finally:
            cur.close()
            return_db_connection(conn)
    except Exception:
        return False


def _event_whatsapp_dump_public_json() -> None:
    try:
        import subprocess as _sp
        _sp.run(
            ["python3", "/opt/arial-whatsapp-poc/event_whatsapp_ingest.py", "--dump"],
            check=False,
            timeout=30,
            capture_output=True,
            text=True,
        )
    except Exception:
        pass


def _event_whatsapp_set_show(regatta_id: str, show: bool) -> bool:
    rid = str(regatta_id or "").strip()
    flag = bool(show)
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            UPDATE public.event_whatsapp_groups
            SET show_on_event = %s
            WHERE is_current AND regatta_id = %s
            """,
            (flag, rid),
        )
        cur.execute(
            """
            UPDATE public.events e
            SET extras = COALESCE(e.extras, '{}'::jsonb) || jsonb_build_object(
              'whatsapp',
              COALESCE(e.extras->'whatsapp', '{}'::jsonb)
                || jsonb_build_object('show_on_event', to_jsonb(%s::boolean))
            )
            FROM public.event_whatsapp_groups g
            WHERE g.event_id = e.event_id
              AND g.is_current
              AND g.regatta_id = %s
            """,
            (flag, rid),
        )
        conn.commit()
    finally:
        cur.close()
        return_db_connection(conn)
    _event_whatsapp_dump_public_json()
    return _event_whatsapp_show_on_event(rid)


def _event_whatsapp_admin_toggle_html(regatta_id: str) -> str:
    """ON/OFF for Super Admin toolbar and Club Admin back-row. Empty if no group."""
    rid = str(regatta_id or "").strip()
    if not rid or not _event_whatsapp_has_group(rid):
        return ""
    show = _event_whatsapp_show_on_event(rid)
    rid_js = json.dumps(rid)
    on_sel = " selected" if show else ""
    off_sel = "" if show else " selected"
    return (
        '<span class="regatta-sa-hub-news-wrap" id="regattaWaShowWrap">'
        '<label for="regattaWaShowSel" class="regatta-sa-hub-news-label">WhatsApp</label>'
        '<select id="regattaWaShowSel" class="regatta-sa-hub-news-select" autocomplete="off" '
        'aria-label="Show or hide WhatsApp messages on this event">'
        f'<option value="OFF"{off_sel}>Hide</option>'
        f'<option value="ON"{on_sel}>Show</option>'
        "</select></span>"
        "<script>(function(){var s=document.getElementById('regattaWaShowSel');"
        "if(!s||s.getAttribute('data-bound')==='1')return;s.setAttribute('data-bound','1');"
        "var rid=" + rid_js + ";var prev=String(s.value||'OFF');"
        "s.addEventListener('change',function(){var v=String(s.value||'OFF');s.disabled=true;"
        "fetch('/api/super-admin/regatta/'+encodeURIComponent(rid)+'/event-whatsapp',{"
        "method:'PATCH',credentials:'include',headers:{'Content-Type':'application/json'},"
        "body:JSON.stringify({show:v==='ON'})})"
        ".then(function(r){return r.json().then(function(j){return{ok:r.ok,j:j};}).catch(function(){return{ok:r.ok,j:null};});})"
        ".then(function(o){if(!o.ok){s.value=prev;s.disabled=false;var d=o.j&&o.j.detail;"
        "alert(typeof d==='string'?d:'Save failed');return;}try{window.location.reload();}catch(e){s.disabled=false;}})"
        ".catch(function(){s.value=prev;s.disabled=false;alert('Network error.');});});})();</script>"
    )


'''

ROUTES = r'''
@app.patch("/api/super-admin/regatta/{regatta_id}/event-whatsapp")
async def api_super_admin_regatta_event_whatsapp_patch(request: Request, regatta_id: str, body: dict = Body(...)):
    rid = str(regatta_id or "").strip()
    if not _session_can_toggle_event_whatsapp(request, rid):
        raise HTTPException(status_code=403, detail="super_admin or club_admin only")
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="JSON object expected")
    raw = body.get("show")
    if raw is None:
        raw = body.get("enabled")
    if isinstance(raw, str):
        flag = raw.strip().lower() in ("1", "true", "on", "yes")
    else:
        flag = bool(raw)
    show = _event_whatsapp_set_show(rid, flag)
    return {"ok": True, "show": show}


@app.get("/api/regatta/{regatta_id}/event-whatsapp")
async def api_regatta_event_whatsapp(request: Request, regatta_id: str):
    rid = str(regatta_id or "").strip()
    return {
        "ok": True,
        "show": _event_whatsapp_show_on_event(rid),
        "can_toggle": _session_can_toggle_event_whatsapp(request, rid),
    }


'''

MARKER_FUNCS = '@app.patch("/api/super-admin/regatta/{regatta_id}/event-crew")'

OLD_TOOLBAR_TAIL = '''        '<textarea id="regattaMmClipUrls" class="regatta-mm-clip-urls" name="mm_clip_urls" rows="3" placeholder="One Facebook URL per line"></textarea>'
        "</span>"
        "</div>"
    )'''

NEW_TOOLBAR_TAIL = '''        '<textarea id="regattaMmClipUrls" class="regatta-mm-clip-urls" name="mm_clip_urls" rows="3" placeholder="One Facebook URL per line"></textarea>'
        "</span>"
        + _event_whatsapp_admin_toggle_html(regatta_id)
        + "</div>"
    )'''

OLD_BACK = '''        if is_sa:
            back_block = (
                '<div class="regatta-back-row">'
                + back_link
                + _wc_super_admin_regatta_toolbar_html(str(regatta_id), hub_badge)
                + "</div>"
            )
        else:
            back_block = back_link
'''

NEW_BACK = '''        can_wa = _session_can_toggle_event_whatsapp(request, str(regatta_id))
        if is_sa:
            back_block = (
                '<div class="regatta-back-row">'
                + back_link
                + _wc_super_admin_regatta_toolbar_html(str(regatta_id), hub_badge)
                + "</div>"
            )
        elif can_wa:
            back_block = (
                '<div class="regatta-back-row">'
                + back_link
                + '<div class="regatta-sa-mode-wrap" id="regattaWaAdminWrap">'
                + _event_whatsapp_admin_toggle_html(str(regatta_id))
                + "</div></div>"
            )
        else:
            back_block = back_link
'''

OLD_JS = "regatta-slot-card.js?v=20260912wa1"
NEW_JS = "regatta-slot-card.js?v=20260912wa2"


def apply(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "_session_can_toggle_event_whatsapp" in text:
        raise SystemExit(f"{path}: already patched")
    if text.count(MARKER_FUNCS) != 1:
        raise SystemExit(f"{path}: event-crew marker count {text.count(MARKER_FUNCS)}")
    if text.count(OLD_TOOLBAR_TAIL) != 1:
        raise SystemExit(f"{path}: toolbar tail count {text.count(OLD_TOOLBAR_TAIL)}")
    if text.count(OLD_BACK) != 2:
        raise SystemExit(f"{path}: back_block count {text.count(OLD_BACK)}")
    if text.count(OLD_JS) != 1:
        raise SystemExit(f"{path}: slot-card ver count {text.count(OLD_JS)}")
    text = text.replace(MARKER_FUNCS, FUNCS + ROUTES + MARKER_FUNCS, 1)
    text = text.replace(OLD_TOOLBAR_TAIL, NEW_TOOLBAR_TAIL, 1)
    text = text.replace(OLD_BACK, NEW_BACK)
    text = text.replace(OLD_JS, NEW_JS, 1)
    path.write_text(text, encoding="utf-8")
    print("patched", path)


def main() -> int:
    apply(Path(sys.argv[1]) if len(sys.argv) > 1 else API)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
