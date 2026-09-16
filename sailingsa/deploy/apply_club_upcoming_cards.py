#!/usr/bin/env python3
"""Club Upcoming/Past: landing All Regattas cards, next-up first.

HMYC test first (CLUB_HOME_CARDS_ALL=False). Full Results → website until
results exist; Name → Event URL when a regatta_id exists.
Mobile portrait: stacked card, 44px targets, wrapping title, box borders kept.
"""
from pathlib import Path
import shutil
import time

API = Path("/var/www/sailingsa/api/api.py")
MARK = "CLUB_HOME_REGATTA_CARDS_v2"

# False = HMYC only (test). True = every club.
CLUB_HOME_CARDS_ALL = False

SOURCE_OLD = """        "regatta_id": (r.get("regatta_id") or "").strip() if has_regatta_id else "",
        "entries": 0,
    }
"""

SOURCE_NEW = """        "regatta_id": (r.get("regatta_id") or "").strip() if has_regatta_id else "",
        "entries": 0,
        "source_url": source_url,
    }
"""

TABLES_OLD = '''def _club_events_tables_html(
    up: list,
    lv: list,
    past_regattas: list,
    club_abbrev: str = "",
) -> str:
    """Upcoming → Past Events / Regattas Hosted. Other events render below Sailors."""
    upcoming = list(lv or []) + list(up or [])
    out = []
    head = (
        "<thead><tr>"
        + _club_sort_th("#")
        + _club_sort_th("Event")
        + _club_sort_th("Start")
        + _club_sort_th("End", "hide-mobile")
        + "</tr></thead>"
    )
    rows_up = _club_event_table_rows(upcoming, include_result=False, club_abbrev=club_abbrev, allow_regatta_links=False) or '<tr><td colspan="4">No upcoming events.</td></tr>'
    out.append(
        '<div class="card stats-section club-upcoming-events-section">'
        '<h2 class="section-title">Upcoming events (%d)</h2>'
        '<input type="search" class="club-table-filter" data-table="club-upcoming-table" placeholder="Search upcoming events…" autocomplete="off">'
        '<div class="table-container club-table-scroll"><table class="table" id="club-upcoming-table">%s<tbody>%s</tbody></table></div>'
        "</div>" % (len(upcoming), head, rows_up)
    )
'''

HELPERS = r'''
def _club_home_cards_enabled(club_abbrev: str = "") -> bool:
    # CLUB_HOME_REGATTA_CARDS_v2
    if ''' + ("True" if CLUB_HOME_CARDS_ALL else "False") + r''':
        return True
    return (club_abbrev or "").strip().upper() == "HMYC"


def _club_unescape_text(s) -> str:
    return html_module.unescape(str(s or "")).strip()


def _club_card_date_label(c: dict) -> str:
    dd = _club_unescape_text(c.get("date_display") or "")
    if dd:
        return dd
    sd = str(c.get("start_date_iso") or "")[:10]
    ed = str(c.get("end_date_iso") or "")[:10]
    try:
        return _format_event_date_range(sd or None, ed or None) or sd or ed or ""
    except Exception:
        if sd and ed and sd != ed:
            return sd + " → " + ed
        return sd or ed or ""


def _club_enrich_home_card(c: dict, club_abbrev: str) -> dict:
    out = dict(c or {})
    out["event_name"] = _club_unescape_text(out.get("event_name") or "")
    out["display_title"] = _club_unescape_text(out.get("display_title") or out.get("event_name") or "")
    rid = str(out.get("regatta_id") or "").strip()
    if rid and not (out.get("event_logo_url") or "").strip():
        try:
            out["event_logo_url"] = _regatta_card_event_logo_url(rid, out.get("event_name")) or ""
        except Exception:
            out["event_logo_url"] = ""
    if club_abbrev and not (out.get("host_code") or "").strip():
        out["host_code"] = club_abbrev
        out["club_slug"] = (out.get("club_slug") or club_abbrev.lower()).strip()
    if club_abbrev and not (out.get("club_logo_url") or "").strip():
        try:
            out["club_logo_url"] = _club_logo_public_url(club_abbrev) or ""
        except Exception:
            out["club_logo_url"] = ""
    if not (out.get("date_display") or "").strip():
        out["date_display"] = _club_card_date_label(out)
    return out


def _club_home_regatta_card_html(c: dict, panel: str, club_abbrev: str) -> str:
    """Landing All Regattas card. Name → Event URL. Full Results → website until results exist."""
    e = _club_enrich_home_card(c, club_abbrev)
    esc = html_module.escape
    title = e.get("display_title") or e.get("event_name") or "—"
    rid = str(e.get("regatta_id") or "").strip()
    event_href = ("/regatta/" + rid) if rid else ""
    website = str(e.get("source_url") or "").strip()
    has_results = bool(e.get("result_yes") or str(e.get("result_url") or "").startswith("/regatta/"))
    title_html = (
        '<a href="%s" class="sa-home-regatta-title">%s</a>' % (esc(event_href, quote=True), esc(title))
        if event_href
        else '<div class="sa-home-regatta-title">%s</div>' % esc(title)
    )
    logo_src = str(e.get("event_logo_url") or "").strip()
    if not logo_src and event_href:
        logo_src = str(e.get("club_logo_url") or "").strip()
    logo_html = (
        '<img class="sa-home-regatta-event-logo" src="%s" alt="" loading="lazy" decoding="async" onerror="this.style.display=\'none\'">'
        % esc(logo_src, quote=True)
        if logo_src
        else ""
    )
    date_l = _club_card_date_label(e)
    try:
        ent = int(e.get("entries") or 0)
    except Exception:
        ent = 0
    meta = '<div class="sa-home-regatta-meta">'
    if date_l:
        meta += '<span class="sa-home-regatta-meta-pill"><span>%s</span></span>' % esc(date_l)
    meta += '<span class="sa-home-regatta-meta-pill"><span>%s Entries</span></span>' % esc(str(ent))
    meta += "</div>"
    host_code = str(e.get("host_code") or club_abbrev or "").strip()
    host_name = str(e.get("host_club_fullname") or "").strip()
    club_logo = str(e.get("club_logo_url") or "").strip()
    slug = str(e.get("club_slug") or (club_abbrev or "").lower()).strip()
    host_inner = ""
    if club_logo:
        host_inner += (
            '<img class="sa-home-regatta-host-logo" src="%s" alt="" loading="lazy" decoding="async" onerror="this.style.display=\'none\'">'
            % esc(club_logo, quote=True)
        )
    host_inner += '<div class="sa-home-regatta-host-text">'
    if host_code and host_code not in ("—", "-"):
        host_inner += '<div class="sa-home-regatta-host-code">%s</div>' % esc(host_code)
        if host_name and host_name.lower() != host_code.lower():
            host_inner += '<div class="sa-home-regatta-host-name">%s</div>' % esc(host_name)
    host_inner += "</div>"
    if slug:
        host_html = '<a class="sa-home-regatta-host" href="/club/%s">%s</a>' % (esc(slug, quote=True), host_inner)
    else:
        host_html = '<div class="sa-home-regatta-host">%s</div>' % host_inner
    actions = '<div class="sa-home-regatta-actions">'
    if logo_src and event_href:
        actions += (
            '<a class="sa-home-regatta-single-class" href="%s" title="Class">'
            '<img class="sa-home-regatta-chip-logo" src="%s" alt="" loading="lazy" decoding="async" onerror="this.style.display=\'none\'">'
            "</a>"
        ) % (esc(event_href, quote=True), esc(logo_src, quote=True))
    if has_results and event_href:
        actions += '<a class="sa-home-regatta-btn" href="%s">Full Results</a>' % esc(event_href, quote=True)
    elif website.startswith("http"):
        actions += (
            '<a class="sa-home-regatta-btn" href="%s" target="_blank" rel="noopener">Full Results</a>'
            % esc(website, quote=True)
        )
    actions += "</div>"
    bg = " ec-upcoming" if panel == "upcoming" else (" ec-live" if panel == "live" else " ec-past-results")
    hay = esc((title + " " + date_l + " " + host_code).lower(), quote=True)
    return (
        '<article class="sa-home-regatta-card%s" data-search="%s">'
        '<div class="sa-home-regatta-top">%s<div class="sa-home-regatta-top-main">%s%s</div>%s%s</div></article>'
    ) % (bg, hay, logo_html, title_html, meta, host_html, actions)


def _club_home_cards_section_html(title: str, cards: list, club_abbrev: str, panel: str, search_id: str) -> str:
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

TABLES_NEW = '''def _club_events_tables_html(
    up: list,
    lv: list,
    past_regattas: list,
    club_abbrev: str = "",
) -> str:
    """Upcoming → Past Events / Regattas Hosted. Other events render below Sailors."""
    if _club_home_cards_enabled(club_abbrev):
        live = _sort_upcoming_events_page_date_first(list(lv or []))
        upcoming = live + _sort_upcoming_events_page_date_first(list(up or []))
        past = list(past_regattas or [])
        css = '<style id="sa-home-regatta-list-style">' + _EVENTS_PAGE_REGATTA_LIST_CSS
        css += (
            ".sa-home-regatta-list{display:flex;flex-direction:column;gap:10px;}"
            ".sa-home-regatta-single-class{display:inline-flex;align-items:center;justify-content:center;min-width:44px;min-height:44px;line-height:0;}"
            ".sa-home-regatta-chip-logo{display:block;width:52px;height:28px;object-fit:contain;}"
            ".club-home-card-filter{min-height:44px;width:100%;max-width:100%;box-sizing:border-box;font-size:16px;padding:8px 12px;margin:0 0 0.75rem 0;}"
            ".sa-home-regatta-title{white-space:normal;overflow-wrap:anywhere;}"
            ".sa-home-regatta-card{box-sizing:border-box;}"
            "@media (max-width:768px){"
            ".sa-home-regatta-card{padding:10px;}"
            ".sa-home-regatta-top{grid-template-columns:72px minmax(0,1fr);grid-template-areas:\"logo main\" \"host host\" \"actions actions\";gap:8px 10px;align-items:start;}"
            ".sa-home-regatta-event-logo{width:68px;height:52px;max-width:68px;}"
            ".sa-home-regatta-title{font-size:14px;line-height:1.25;}"
            ".sa-home-regatta-meta{flex-wrap:wrap;gap:6px;}"
            ".sa-home-regatta-host{min-height:44px;}"
            ".sa-home-regatta-host-name{white-space:normal;max-width:none;}"
            ".sa-home-regatta-actions{width:100%;justify-content:stretch;gap:8px;}"
            ".sa-home-regatta-btn{flex:1;min-height:44px;min-width:44px;padding:10px 12px;}"
            "}"
            "</style>"
        )
        js = (
            "<script>(function(){document.querySelectorAll('.club-home-card-filter').forEach(function(inp){"
            "inp.addEventListener('input',function(){var q=(inp.value||'').toLowerCase();"
            "var list=document.getElementById(inp.getAttribute('data-list'));if(!list)return;"
            "list.querySelectorAll('.sa-home-regatta-card').forEach(function(c){"
            "c.style.display=((c.getAttribute('data-search')||'').indexOf(q)>=0)?'':'none';});});});})();</script>"
        )
        return (
            css
            + _club_home_cards_section_html("Upcoming events", upcoming, club_abbrev, "upcoming", "club-upcoming-cards")
            + _club_home_cards_section_html(
                "Past Events / Regattas Hosted", past, club_abbrev, "past", "club-past-cards"
            )
            + js
        )
    upcoming = list(lv or []) + list(up or [])
    out = []
    head = (
        "<thead><tr>"
        + _club_sort_th("#")
        + _club_sort_th("Event")
        + _club_sort_th("Start")
        + _club_sort_th("End", "hide-mobile")
        + "</tr></thead>"
    )
    rows_up = _club_event_table_rows(upcoming, include_result=False, club_abbrev=club_abbrev, allow_regatta_links=False) or '<tr><td colspan="4">No upcoming events.</td></tr>'
    out.append(
        '<div class="card stats-section club-upcoming-events-section">'
        '<h2 class="section-title">Upcoming events (%d)</h2>'
        '<input type="search" class="club-table-filter" data-table="club-upcoming-table" placeholder="Search upcoming events…" autocomplete="off">'
        '<div class="table-container club-table-scroll"><table class="table" id="club-upcoming-table">%s<tbody>%s</tbody></table></div>'
        "</div>" % (len(upcoming), head, rows_up)
    )
'''


def main() -> None:
    api = API.read_text()
    if MARK in api and SOURCE_NEW in api and "_club_home_cards_enabled" in api:
        print("ALREADY")
        return
    ts = time.strftime("%Y%m%d_%H%M%S")
    shutil.copy2(API, API.with_name(f"api.py.bak.club_home_cards.{ts}"))
    missing = []
    if SOURCE_OLD not in api:
        missing.append("SOURCE")
    if TABLES_OLD not in api:
        missing.append("TABLES")
    if missing:
        raise SystemExit("MISSING:" + ",".join(missing))
    api = api.replace(SOURCE_OLD, SOURCE_NEW, 1)
    api = api.replace(TABLES_OLD, HELPERS + TABLES_NEW, 1)
    API.write_text(api)
    print("API_OK", MARK, "ALL" if CLUB_HOME_CARDS_ALL else "HMYC")


if __name__ == "__main__":
    main()
