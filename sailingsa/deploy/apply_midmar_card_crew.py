#!/usr/bin/env python3
"""Midmar: orange Youth Helm card below sheet / above print; SA Crew (public) toggle."""
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
MARK = "MIDMAR_CARD_CREW_v1"

HELPERS = '''
def _midmar_cup_rid() -> str:
    return "2026-09-19-hmyc-midmar-cup"


def _midmar_crew_public_on() -> bool:
    return bool(_merge_wc_column_prefs_for_regatta(_midmar_cup_rid()).get("crew", True))


def _midmar_hide_crew_attr(regatta_id: str) -> str:
    if str(regatta_id or "").strip() != _midmar_cup_rid():
        return ""
    if _midmar_crew_public_on():
        return ""
    return ' data-midmar-hide-crew="1"'


def _midmar_yh_card_html(regatta_id: str) -> str:
    if str(regatta_id or "").strip() != _midmar_cup_rid():
        return ""
    return (
        '<div class="card" id="midmar-youth-helm-note">'
        '<h2 class="section-title">🔵 Youth Helm Races</h2>'
        "<p>Blue scores = declared youth-helm races and cannot be discarded.</p>"
        "</div>"
    )  # MIDMAR_CARD_CREW_v1


def _midmar_public_crew_toggle_html(regatta_id: str) -> str:
    if str(regatta_id or "").strip() != _midmar_cup_rid():
        return ""
    ck = " checked" if _midmar_crew_public_on() else ""
    rid_js = json.dumps(str(regatta_id))
    return (
        '<span class="regatta-sa-hub-news-wrap" id="midmarCrewPublicWrap">'
        '<label class="regatta-sa-hub-news-label" for="midmarCrewPublic">Crew (public)</label>'
        f'<input type="checkbox" id="midmarCrewPublic"{ck} autocomplete="off">'
        "</span>"
        "<script>(function(){var rid=" + rid_js + ";"
        "var cb=document.getElementById('midmarCrewPublic');if(!cb)return;"
        "cb.addEventListener('change',function(){"
        "fetch('/api/super-admin/regatta/'+encodeURIComponent(rid)+'/column-prefs',"
        "{method:'PATCH',credentials:'include',headers:{'Content-Type':'application/json'},"
        "body:JSON.stringify({crew:!!cb.checked})})"
        ".then(function(r){if(r.ok)location.reload();});});})();</script>"
    )


'''


def main() -> None:
    text = API.read_text()
    if MARK in text and 'data-midmar-hide-crew' in text and "background:#ffd4a8!important" in text:
        print("ALREADY", MARK)
        return

    write_gate = (
        "    if not _regatta_slug_is_sa_pilot_standalone(rid):\n"
        '        raise ValueError("column prefs only for SA pilot regattas")\n'
    )
    write_gate_new = (
        "    if not _regatta_slug_is_sa_pilot_standalone(rid) and rid != _midmar_cup_rid():\n"
        '        raise ValueError("column prefs only for SA pilot regattas")\n'
    )
    if text.count(write_gate) != 1:
        raise SystemExit("ANCHOR_WRITE_" + str(text.count(write_gate)))

    insert_at = "\n\nDF95_CLASS_LOGO_SSOT"
    if text.count(insert_at) != 1:
        raise SystemExit("ANCHOR_INSERT_" + str(text.count(insert_at)))

    get_old = (
        "    if not _regatta_slug_is_sa_pilot_standalone(rid):\n"
        '        raise HTTPException(status_code=403, detail="not editable for this regatta yet")\n'
        '    return {"ok": True, "prefs": _merge_wc_column_prefs_for_regatta(rid)}\n'
    )
    get_new = (
        "    if not _regatta_slug_is_sa_pilot_standalone(rid) and rid != _midmar_cup_rid():\n"
        '        raise HTTPException(status_code=403, detail="not editable for this regatta yet")\n'
        '    return {"ok": True, "prefs": _merge_wc_column_prefs_for_regatta(rid)}\n'
    )
    if text.count(get_old) != 1:
        raise SystemExit("ANCHOR_GET_" + str(text.count(get_old)))

    patch_old = (
        "    if not _regatta_slug_is_sa_pilot_standalone(rid):\n"
        '        raise HTTPException(status_code=403, detail="not editable for this regatta yet")\n'
        "    if not isinstance(body, dict):\n"
        '        raise HTTPException(status_code=400, detail="JSON object expected")\n'
        "    patch = {}\n"
        "    for k in _WC_COLUMN_PREF_KEYS:\n"
    )
    patch_new = (
        "    if not _regatta_slug_is_sa_pilot_standalone(rid) and rid != _midmar_cup_rid():\n"
        '        raise HTTPException(status_code=403, detail="not editable for this regatta yet")\n'
        "    if not isinstance(body, dict):\n"
        '        raise HTTPException(status_code=400, detail="JSON object expected")\n'
        "    patch = {}\n"
        "    for k in _WC_COLUMN_PREF_KEYS:\n"
    )
    if text.count(patch_old) != 1:
        raise SystemExit("ANCHOR_PATCH_" + str(text.count(patch_old)))

    css_old = (
        '    ".regatta-page>#midmar-youth-helm-note.card{order:4;width:100%!important;max-width:100%!important;'
        "box-sizing:border-box!important;margin:12px 0 0!important;padding:10px 16px;background:#fff;"
        "border:2px solid #001f3f!important;border-radius:8px!important;"
        'box-shadow:0 1px 3px rgba(0,31,63,0.08)!important;overflow:hidden}"  # YOUTH_HELM_CARD_v2\n'
    )
    css_new = (
        '    ".regatta-page>#midmar-youth-helm-note.card{order:9;width:100%!important;max-width:100%!important;'
        "box-sizing:border-box!important;margin:12px 0 0!important;padding:10px 16px;"
        "background:#ffd4a8!important;"
        "border:2px solid #001f3f!important;border-radius:8px!important;"
        'box-shadow:0 1px 3px rgba(0,31,63,0.08)!important;overflow:hidden}"  # MIDMAR_CARD_CREW_v1\n'
        '    ".regatta-page[data-midmar-hide-crew=\\"1\\"]:not(.regatta-page--super-admin-edit) '
        ".fleet-section .table-wrapper table.fleet-results-table th.crew-col,"
        '.regatta-page[data-midmar-hide-crew=\\"1\\"]:not(.regatta-page--super-admin-edit) '
        ".fleet-section .table-wrapper table.fleet-results-table td.crew-col"
        '{display:none!important}"\n'
    )
    if text.count(css_old) != 1:
        raise SystemExit("ANCHOR_CSS_" + str(text.count(css_old)))

    html_old = (
        "        f'<div class=\"table-wrapper\">{table_html}{course_footer_html}</div></div>'\n"
        '        f"{_yh_card}"\n'
        "    )\n"
    )
    html_new = (
        "        f'<div class=\"table-wrapper\">{table_html}{course_footer_html}</div></div>'\n"
        "    )\n"
    )
    if text.count(html_old) != 1:
        raise SystemExit("ANCHOR_HTML_" + str(text.count(html_old)))

    body_old = (
        '            + fleet_joined + crew_frag + "\\n" + banner_bottom + print_btn\n'
    )
    body_new = (
        '            + fleet_joined + crew_frag + "\\n" + _midmar_yh_card_html(str(regatta_id))'
        " + banner_bottom + print_btn\n"
    )
    if text.count(body_old) != 1:
        raise SystemExit("ANCHOR_BODY_" + str(text.count(body_old)))

    page_old = (
        'f"<div class=\\"regatta-page\\"{_regatta_page_live_board_attrs(str(regatta_id), start_d, end_d)}>{body_html}'
    )
    page_new = (
        'f"<div class=\\"regatta-page\\"{_regatta_page_live_board_attrs(str(regatta_id), start_d, end_d)}'
        "{_midmar_hide_crew_attr(str(regatta_id))}>{body_html}"
    )
    if text.count(page_old) != 2:
        raise SystemExit("ANCHOR_PAGE_" + str(text.count(page_old)))

    tb_old = (
        "        + _event_whatsapp_admin_toggle_html(regatta_id)\n"
        "        + _event_crew_admin_toggle_html(regatta_id)\n"
        '        + "</div>"\n'
        "    )\n"
    )
    tb_new = (
        "        + _event_whatsapp_admin_toggle_html(regatta_id)\n"
        "        + _event_crew_admin_toggle_html(regatta_id)\n"
        "        + _midmar_public_crew_toggle_html(regatta_id)\n"
        '        + "</div>"\n'
        "    )\n"
    )
    if text.count(tb_old) != 1:
        raise SystemExit("ANCHOR_TB_" + str(text.count(tb_old)))

    text = text.replace(insert_at, "\n" + HELPERS + "DF95_CLASS_LOGO_SSOT", 1)
    text = text.replace(write_gate, write_gate_new, 1)
    text = text.replace(get_old, get_new, 1)
    text = text.replace(patch_old, patch_new, 1)
    text = text.replace(css_old, css_new, 1)
    text = text.replace(html_old, html_new, 1)
    text = text.replace(body_old, body_new, 1)
    text = text.replace(page_old, page_new)
    text = text.replace(tb_old, tb_new, 1)
    API.write_text(text)
    print("OK", MARK)


if __name__ == "__main__":
    main()
