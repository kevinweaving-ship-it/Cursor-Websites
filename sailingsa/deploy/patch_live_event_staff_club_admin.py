#!/usr/bin/env python3
"""Staff Show/Hide for Club Admin (back-row + SA toolbar); Login label; hide-from-public works."""
from pathlib import Path
import sys

API = Path("/var/www/sailingsa/api/api.py")

CREW_TOGGLE_FN = r'''
def _event_crew_admin_toggle_html(regatta_id: str) -> str:
    """ON/OFF for Super Admin toolbar and Club Admin back-row. Cape Classic only."""
    rid = str(regatta_id or "").strip()
    if not rid.startswith("2026-09-13-zvyc-cape-classic"):
        return ""
    show = _cape_classic_crew_show()
    parent_js = json.dumps(_CAPE_CLASSIC_MM_REGATTA_ID)
    on_sel = " selected" if show else ""
    off_sel = "" if show else " selected"
    return (
        '<span class="regatta-sa-hub-news-wrap" id="regattaCrewShowWrap">'
        '<label for="regattaCrewShowSel" class="regatta-sa-hub-news-label">Staff</label>'
        '<select id="regattaCrewShowSel" class="regatta-sa-hub-news-select" autocomplete="off" '
        'aria-label="Show or hide the staff list on this event">'
        f'<option value="OFF"{off_sel}>Hide</option>'
        f'<option value="ON"{on_sel}>Show</option>'
        "</select></span>"
        "<script>(function(){var s=document.getElementById('regattaCrewShowSel');"
        "if(!s||s.getAttribute('data-bound')==='1')return;s.setAttribute('data-bound','1');"
        "var rid=" + parent_js + ";var prev=String(s.value||'OFF');"
        "s.addEventListener('change',function(){var v=String(s.value||'OFF');s.disabled=true;"
        "fetch('/api/super-admin/regatta/'+encodeURIComponent(rid)+'/event-crew',{"
        "method:'PATCH',credentials:'include',headers:{'Content-Type':'application/json'},"
        "body:JSON.stringify({show:v==='ON'})})"
        ".then(function(r){return r.json().then(function(j){return{ok:r.ok,j:j};}).catch(function(){return{ok:r.ok,j:null};});})"
        ".then(function(o){if(!o.ok){s.value=prev;s.disabled=false;var d=o.j&&o.j.detail;"
        "alert(typeof d==='string'?d:'Save failed');return;}try{window.location.reload();}catch(e){s.disabled=false;}})"
        ".catch(function(){s.value=prev;s.disabled=false;alert('Network error.');});});})();</script>"
    )


'''

OLD_INSERT = '''    _write_wc_regatta_header_icons(all_d)


def _cape_classic_crew_table_html(
'''

NEW_INSERT = '''    _write_wc_regatta_header_icons(all_d)


''' + CREW_TOGGLE_FN + '''def _cape_classic_crew_table_html(
'''

OLD_SA_CSS = '    ".regatta-page--super-admin-edit .cape-crew-sa,.cape-crew--admin .cape-crew-sa{display:flex}"'
NEW_SA_CSS = (
    '    ".regatta-page--super-admin-edit .cape-crew-sa,'
    '.regatta-page--club-score-edit .cape-crew-sa,'
    '.cape-crew--admin .cape-crew-sa{display:flex}"'
)

OLD_HIDDEN = '    ".cape-crew--hidden{display:block}"'
NEW_HIDDEN = '    ".cape-crew--hidden{display:none}"'

OLD_TOOLBAR_TAIL = '''        + _event_whatsapp_admin_toggle_html(regatta_id)
        + "</div>"
    )'''

NEW_TOOLBAR_TAIL = '''        + _event_whatsapp_admin_toggle_html(regatta_id)
        + _event_crew_admin_toggle_html(regatta_id)
        + "</div>"
    )'''

OLD_BACK = '''        can_wa = _session_can_toggle_event_whatsapp(request, str(regatta_id))
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

NEW_BACK = '''        can_wa = _session_can_toggle_event_whatsapp(request, str(regatta_id))
        can_crew_toggle = (
            str(regatta_id).startswith("2026-09-13-zvyc-cape-classic")
            and _session_can_toggle_event_crew(request)
        )
        if is_sa:
            back_block = (
                '<div class="regatta-back-row">'
                + back_link
                + _wc_super_admin_regatta_toolbar_html(str(regatta_id), hub_badge)
                + "</div>"
            )
        elif can_wa or can_crew_toggle:
            back_block = (
                '<div class="regatta-back-row">'
                + back_link
                + '<div class="regatta-sa-mode-wrap" id="regattaWaAdminWrap">'
                + _event_whatsapp_admin_toggle_html(str(regatta_id))
                + _event_crew_admin_toggle_html(str(regatta_id))
                + "</div></div>"
            )
        else:
            back_block = back_link
'''

OLD_CREW_CHILD = '''    is_sa = _session_role_is_super_admin(request)
    back_link = f'<a href="/regatta/{html_module.escape(rid)}" class="back-to-home">← Back to full regatta</a>'
    if is_sa:
        back_block = (
            '<div class="regatta-back-row">'
            + back_link
            + _regatta_sa_toolbar_html(rid)
            + "</div>"
        )
    else:
        back_block = back_link
'''

NEW_CREW_CHILD = '''    is_sa = _session_role_is_super_admin(request)
    hub_badge = _effective_regatta_hub_toolbar_badge_label(rid) if is_sa else None
    can_wa = _session_can_toggle_event_whatsapp(request, rid)
    back_link = f'<a href="/regatta/{html_module.escape(rid)}" class="back-to-home">← Back to full regatta</a>'
    if is_sa:
        back_block = (
            '<div class="regatta-back-row">'
            + back_link
            + _wc_super_admin_regatta_toolbar_html(rid, hub_badge)
            + "</div>"
        )
    elif can_wa or can_crew:
        back_block = (
            '<div class="regatta-back-row">'
            + back_link
            + '<div class="regatta-sa-mode-wrap" id="regattaWaAdminWrap">'
            + _event_whatsapp_admin_toggle_html(rid)
            + _event_crew_admin_toggle_html(rid)
            + "</div></div>"
        )
    else:
        back_block = back_link
'''

OLD_JS = "regatta-slot-card.js?v=20260912wa7"
NEW_JS = "regatta-slot-card.js?v=20260912wa8"

OLD_SIGNIN = '''    "<div class=\\"ssa-wa-gate-actions\\"><a class=\\"ssa-wa-gate-in\\" href=\\"/login.html?returnTo='+ret+'\\">Sign In</a>"'''
NEW_SIGNIN = '''    "<div class=\\"ssa-wa-gate-actions\\"><a class=\\"ssa-wa-gate-in\\" href=\\"/login.html?returnTo='+ret+'\\">Login</a>"'''


def apply(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "_event_crew_admin_toggle_html" in text:
        raise SystemExit(f"{path}: already patched")
    checks = [
        ("insert", OLD_INSERT, 1),
        ("sa css", OLD_SA_CSS, 1),
        ("hidden css", OLD_HIDDEN, 1),
        ("toolbar tail", OLD_TOOLBAR_TAIL, 1),
        ("back", OLD_BACK, 2),
        ("crew child", OLD_CREW_CHILD, 1),
        ("js ver", OLD_JS, 1),
        ("signin", OLD_SIGNIN, 1),
    ]
    for label, old, want in checks:
        got = text.count(old)
        if got != want:
            raise SystemExit(f"{path}: {label} count {got} want {want}")
    text = text.replace(OLD_INSERT, NEW_INSERT, 1)
    text = text.replace(OLD_SA_CSS, NEW_SA_CSS, 1)
    text = text.replace(OLD_HIDDEN, NEW_HIDDEN, 1)
    text = text.replace(OLD_TOOLBAR_TAIL, NEW_TOOLBAR_TAIL, 1)
    text = text.replace(OLD_BACK, NEW_BACK)
    text = text.replace(OLD_CREW_CHILD, NEW_CREW_CHILD, 1)
    text = text.replace(OLD_JS, NEW_JS, 1)
    text = text.replace(OLD_SIGNIN, NEW_SIGNIN, 1)
    path.write_text(text, encoding="utf-8")
    print("patched", path)


def main() -> int:
    apply(Path(sys.argv[1]) if len(sys.argv) > 1 else API)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
