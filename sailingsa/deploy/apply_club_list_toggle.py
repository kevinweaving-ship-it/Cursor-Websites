#!/usr/bin/env python3
"""Club Past / Sailors / Other: orange expand arrow, default hidden, search still shows."""
from pathlib import Path
import shutil
import time

API = Path("/var/www/sailingsa/api/api.py")
MARK = "CLUB_LIST_TOGGLE_v1"

HELPER = r'''def _club_list_toggle_assets() -> str:
    # CLUB_LIST_TOGGLE_v1
    return (
        '<style id="club-list-toggle-style">'
        ".club-section-title-row{display:flex;flex-wrap:wrap;align-items:center;gap:8px;}"
        ".club-list-expand-btn{display:inline-flex;align-items:center;justify-content:center;"
        "width:44px;height:44px;min-width:44px;min-height:44px;margin:0;padding:0;border:0;"
        "background:transparent;color:#FF5A00;cursor:pointer;line-height:1;}"
        ".club-list-expand-btn svg{display:block;width:18px;height:18px;fill:#FF5A00;"
        "transform:rotate(0deg);transition:transform .18s ease;}"
        '.club-list-expand-btn[aria-expanded="true"] svg{transform:rotate(180deg);}'
        ".club-list-expand-label{font-size:.85rem;font-weight:700;color:#475569;}"
        ".club-list-body[hidden]{display:none!important;}"
        "</style>"
        "<script>(function(){"
        "if(window.__clubListToggleV1)return;window.__clubListToggleV1=1;"
        "function sync(sec){"
        "var btn=sec.querySelector('.club-list-expand-btn');"
        "var body=sec.querySelector('.club-list-body');"
        "if(!btn||!body)return;"
        "var inp=sec.querySelector('.club-home-card-filter');"
        "var q=((inp&&inp.value)||'').trim();"
        "var open=btn.getAttribute('aria-expanded')==='true';"
        "if(open||q)body.removeAttribute('hidden');else body.setAttribute('hidden','');"
        "}"
        "function boot(){"
        "document.querySelectorAll('.club-list-expand-btn').forEach(function(btn){"
        "if(btn.getAttribute('data-bound')==='1')return;"
        "btn.setAttribute('data-bound','1');"
        "var sec=btn.closest('.card')||btn.closest('.stats-section')||btn.parentElement;"
        "btn.addEventListener('click',function(){"
        "var on=btn.getAttribute('aria-expanded')==='true';"
        "btn.setAttribute('aria-expanded',on?'false':'true');"
        "sync(sec);"
        "});"
        "if(sec){"
        "var inp=sec.querySelector('.club-home-card-filter');"
        "if(inp)inp.addEventListener('input',function(){sync(sec);});"
        "sync(sec);"
        "}"
        "});"
        "}"
        "if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);"
        "else boot();"
        "})();</script>"
    )


def _club_section_title_toggle_html(title_html: str, list_id: str) -> str:
    lid = html_module.escape(list_id, quote=True)
    return (
        '<h2 class="section-title club-section-title-row">%s'
        '<button type="button" class="sa-avatar-expand-btn club-list-expand-btn" aria-expanded="false" aria-controls="%s" title="Show/Hide List">'
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="18" height="18" aria-hidden="true">'
        '<path fill="#FF5A00" d="M231.39,132.94A8,8,0,0,0,224,128H184V104a8,8,0,0,0-8-8H80a8,8,0,0,0-8,8v24H32a8,8,0,0,0-5.66,13.66l96,96a8,8,0,0,0,11.32,0l96-96A8,8,0,0,0,231.39,132.94ZM72,40a8,8,0,0,1,8-8h96a8,8,0,0,1,0,16H80A8,8,0,0,1,72,40Zm0,32a8,8,0,0,1,8-8h96a8,8,0,0,1,0,16H80A8,8,0,0,1,72,72Z"/>'
        "</svg></button>"
        '<span class="club-list-expand-label">Show/Hide List</span></h2>'
    ) % (title_html, lid)


'''

SECTION_OLD = '''def _club_home_cards_section_html(title: str, cards: list, club_abbrev: str, panel: str, search_id: str) -> str:
    if not cards:
        cards_html = '<p class="club-events-intro">No %s.</p>' % html_module.escape(title.lower())
    else:
        cards_html = "".join(_club_home_regatta_card_html(c, panel, club_abbrev) for c in cards)
    return (
        '<div class="card stats-section club-%s-events-section">'
        '<h2 class="section-title">%s (%d)</h2>'
        '<input type="search" class="club-home-card-filter" data-list="%s" placeholder="Search %s…" autocomplete="off">'
        '<div class="sa-home-regatta-wrap"><div class="sa-home-regatta-list" id="%s">%s</div></div>'
        "</div>"
        % (
            panel,
            html_module.escape(title),
            len(cards or []),
            html_module.escape(search_id, quote=True),
            html_module.escape(title.lower()),
            html_module.escape(search_id, quote=True),
            cards_html,
        )
    )
'''

SECTION_NEW = '''def _club_home_cards_section_html(title: str, cards: list, club_abbrev: str, panel: str, search_id: str) -> str:
    if not cards:
        cards_html = '<p class="club-events-intro">No %s.</p>' % html_module.escape(title.lower())
    else:
        cards_html = "".join(_club_home_regatta_card_html(c, panel, club_abbrev) for c in cards)
    heading = "%s (%d)" % (html_module.escape(title), len(cards or []))
    sid = html_module.escape(search_id, quote=True)
    title_html = (
        _club_section_title_toggle_html(heading, search_id)
        if panel == "past"
        else '<h2 class="section-title">%s</h2>' % heading
    )
    body_open = '<div class="club-list-body" hidden>' if panel == "past" else ""
    body_close = "</div>" if panel == "past" else ""
    return (
        '<div class="card stats-section club-%s-events-section">'
        "%s"
        '<input type="search" class="club-home-card-filter" data-list="%s" placeholder="Search %s…" autocomplete="off">'
        '%s<div class="sa-home-regatta-wrap"><div class="sa-home-regatta-list" id="%s">%s</div></div>%s'
        "</div>"
        % (
            panel,
            title_html,
            sid,
            html_module.escape(title.lower()),
            body_open,
            sid,
            cards_html,
            body_close,
        )
    )
'''

SAILORS_OLD = '''        + '<div class="card stats-section club-sailors-section">'
        '<h2 class="section-title">Sailors (%d)</h2>'
        '<input type="search" id="club-sailors-home-filter" class="club-home-card-filter" placeholder="Search sailors name…" autocomplete="off">'
        '<div class="club-home-sailor-list" id="club-home-sailors-list">%s</div>'
        '<p id="club-home-sailors-empty" role="status" style="display:none">No sailors match your search.</p>'
        "</div></div>"
'''

SAILORS_NEW = '''        + '<div class="card stats-section club-sailors-section">'
        + _club_section_title_toggle_html("Sailors (%d)" % n, "club-home-sailors-list")
        + '<input type="search" id="club-sailors-home-filter" class="club-home-card-filter" placeholder="Search sailors name…" autocomplete="off">'
        '<div class="club-list-body" hidden>'
        '<div class="club-home-sailor-list" id="club-home-sailors-list">%s</div>'
        '<p id="club-home-sailors-empty" role="status" style="display:none">No sailors match your search.</p>'
        "</div></div></div>"
'''

# sailors return currently % (n, "".join(slots)) — after change title already has n, only slots remain
SAILORS_PCT_OLD = "        % (n, \"\".join(slots))\n"
SAILORS_PCT_NEW = "        % (\"\".join(slots),)\n"

OTHER_OLD = '''            + '<div class="card stats-section club-other-events-section">'
            + '<h2 class="section-title">Other events (%d)</h2>' % len(cards)
            + intro
            + '<input type="search" class="club-home-card-filter" data-list="club-other-cards" placeholder="Search other events…" autocomplete="off">'
            + '<div class="sa-home-regatta-wrap"><div class="sa-home-regatta-list" id="club-other-cards">'
'''

OTHER_NEW = '''            + '<div class="card stats-section club-other-events-section">'
            + _club_section_title_toggle_html("Other events (%d)" % len(cards), "club-other-cards")
            + intro
            + '<input type="search" class="club-home-card-filter" data-list="club-other-cards" placeholder="Search other events…" autocomplete="off">'
            + '<div class="club-list-body" hidden><div class="sa-home-regatta-wrap"><div class="sa-home-regatta-list" id="club-other-cards">'
'''

OTHER_CLOSE_OLD = '            + "</div></div></div></div>"\n'
OTHER_CLOSE_NEW = '            + "</div></div></div></div></div>"\n'

ASSETS_INJECT_OLD = '''            + _club_home_cards_section_html("Upcoming events", upcoming, club_abbrev, "upcoming", "club-upcoming-cards")
'''
ASSETS_INJECT_NEW = '''            + _club_list_toggle_assets()
            + _club_home_cards_section_html("Upcoming events", upcoming, club_abbrev, "upcoming", "club-upcoming-cards")
'''


def main() -> None:
    api = API.read_text()
    if MARK in api:
        print("ALREADY")
        return
    missing = []
    if SECTION_OLD not in api:
        missing.append("SECTION")
    if SAILORS_OLD not in api:
        missing.append("SAILORS")
    if SAILORS_PCT_OLD not in api:
        missing.append("SAILORS_PCT")
    if OTHER_OLD not in api:
        missing.append("OTHER")
    if OTHER_CLOSE_OLD not in api:
        missing.append("OTHER_CLOSE")
    if ASSETS_INJECT_OLD not in api:
        missing.append("ASSETS")
    if "def _club_home_cards_section_html" not in api:
        missing.append("FN")
    if missing:
        raise SystemExit("MISSING:" + ",".join(missing))
    ts = time.strftime("%Y%m%d_%H%M%S")
    bak = API.with_name("api.py.bak.club_list_toggle." + ts)
    shutil.copy2(API, bak)
    api = api.replace("def _club_home_cards_section_html", HELPER + "def _club_home_cards_section_html", 1)
    api = api.replace(SECTION_OLD, SECTION_NEW, 1)
    api = api.replace(SAILORS_OLD, SAILORS_NEW, 1)
    api = api.replace(SAILORS_PCT_OLD, SAILORS_PCT_NEW, 1)
    api = api.replace(OTHER_OLD, OTHER_NEW, 1)
    api = api.replace(OTHER_CLOSE_OLD, OTHER_CLOSE_NEW, 1)
    api = api.replace(ASSETS_INJECT_OLD, ASSETS_INJECT_NEW, 1)
    if MARK not in api:
        raise SystemExit("MARK_MISSING")
    API.write_text(api)
    print("API_OK", MARK, "BAK", str(bak))


if __name__ == "__main__":
    main()
