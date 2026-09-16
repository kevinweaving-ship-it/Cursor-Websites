#!/usr/bin/env python3
"""Club cards: real entry counts, compact landing look, side padding.

Also: Other events keep only items that still need an Event URL;
closed events with a valid Event URL move to Past.
"""
from pathlib import Path
import shutil
import time

API = Path("/var/www/sailingsa/api/api.py")
MARK = "CLUB_PAST_COMPACT_v1"

COUNTS_OLD = '''def _club_regatta_entry_counts(rids: list) -> dict:
    out = {}
    ids = []
    for raw in rids or []:
        rid = str(raw or "").strip()
        if rid and rid not in out:
            out[rid] = 0
            ids.append(rid)
    if not ids:
        return out
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "SELECT regatta_id::text, COUNT(*) FROM entries WHERE regatta_id::text = ANY(%s) GROUP BY 1",
                (ids,),
            )
            for rid, n in cur.fetchall() or []:
                out[str(rid)] = max(out.get(str(rid), 0), int(n or 0))
        except Exception:
            pass
        try:
            cur.execute(
                "SELECT regatta_id::text, COALESCE(SUM(entries_raced),0) FROM regatta_blocks WHERE regatta_id::text = ANY(%s) GROUP BY 1",
                (ids,),
            )
            for rid, n in cur.fetchall() or []:
                out[str(rid)] = max(out.get(str(rid), 0), int(n or 0))
        except Exception:
            pass
        try:
            cur.execute(
                "SELECT regatta_id::text, COUNT(*) FROM results WHERE regatta_id::text = ANY(%s) GROUP BY 1",
                (ids,),
            )
            for rid, n in cur.fetchall() or []:
                out[str(rid)] = max(out.get(str(rid), 0), int(n or 0))
        except Exception:
            pass
    except Exception:
        pass
    finally:
        try:
            if cur is not None:
                cur.close()
        except Exception:
            pass
        try:
            if conn is not None:
                return_db_connection(conn)
        except Exception:
            pass
    return out
'''

COUNTS_NEW = '''def _club_regatta_entry_counts(rids: list) -> dict:
    # CLUB_PAST_COMPACT_v1
    out = {}
    ids = []
    for raw in rids or []:
        rid = str(raw or "").strip()
        if rid and rid not in out:
            out[rid] = 0
            ids.append(rid)
    if not ids:
        return out

    def _row_pair(row):
        if isinstance(row, dict):
            vals = list(row.values())
            return str(vals[0]), int(vals[1] or 0)
        return str(row[0]), int(row[1] or 0)

    conn = None
    cur = None
    own = False
    try:
        try:
            conn = get_db_connection()
        except Exception:
            conn = psycopg2.connect(DB_URL)
            own = True
        cur = conn.cursor()
        for sql in (
            "SELECT regatta_id::text, COUNT(*) FROM entries WHERE regatta_id::text = ANY(%s) GROUP BY 1",
            "SELECT regatta_id::text, COALESCE(SUM(entries_raced),0) FROM regatta_blocks WHERE regatta_id::text = ANY(%s) GROUP BY 1",
            "SELECT regatta_id::text, COUNT(DISTINCT COALESCE(helm_sa_sailing_id::text, result_id::text)) FROM results WHERE regatta_id::text = ANY(%s) GROUP BY 1",
        ):
            try:
                cur.execute(sql, (ids,))
                for row in cur.fetchall() or []:
                    rid, n = _row_pair(row)
                    out[rid] = max(out.get(rid, 0), n)
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass
    except Exception:
        pass
    finally:
        try:
            if cur is not None:
                cur.close()
        except Exception:
            pass
        try:
            if conn is not None:
                if own:
                    conn.close()
                else:
                    return_db_connection(conn)
        except Exception:
            pass
    return out
'''

CHIP_OLD = '''    if logo_src and event_href:
        actions += (
            '<a class="sa-home-regatta-single-class" href="%s" title="Class">'
            '<img class="sa-home-regatta-chip-logo" src="%s" alt="" loading="lazy" decoding="async" onerror="this.style.display=\\'none\\'">'
            "</a>"
        ) % (esc(event_href, quote=True), esc(logo_src, quote=True))
'''

CHIP_OLD2 = """    if logo_src and event_href:
        actions += (
            '<a class="sa-home-regatta-single-class" href="%s" title="Class">'
            '<img class="sa-home-regatta-chip-logo" src="%s" alt="" loading="lazy" decoding="async" onerror="this.style.display=\\'none\\'">'
            "</a>"
        ) % (esc(event_href, quote=True), esc(logo_src, quote=True))
"""

# live file has the chip as dumped earlier with escaped none
CHIP_LIVE = r"""    if logo_src and event_href:
        actions += (
            '<a class="sa-home-regatta-single-class" href="%s" title="Class">'
            '<img class="sa-home-regatta-chip-logo" src="%s" alt="" loading="lazy" decoding="async" onerror="this.style.display=\'none\'">'
            "</a>"
        ) % (esc(event_href, quote=True), esc(logo_src, quote=True))
"""

HOST_LOGO_OLD = r"""    host_inner = ""
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
"""

HOST_LOGO_NEW = r"""    host_inner = '<div class="sa-home-regatta-host-text">'
    if host_code and host_code not in ("—", "-"):
        host_inner += '<div class="sa-home-regatta-host-code">%s</div>' % esc(host_code)
"""

CSS_OLD = (
    '            ".club-home-cards-stack{width:100%;max-width:52rem;margin:0 auto 1.5rem;box-sizing:border-box;}"\n'
    '            ".club-home-cards-stack .card.stats-section{width:100%;max-width:100%;box-sizing:border-box;}"\n'
    '            ".club-home-cards-stack .sa-home-regatta-card{width:100%;max-width:100%;box-sizing:border-box;}"\n'
    '            "@media (max-width:768px){.club-home-cards-stack{max-width:100%;padding:0;}}"\n'
)

CSS_NEW = (
    '            ".club-home-cards-stack{width:100%;max-width:52rem;margin:0 auto 1.5rem;box-sizing:border-box;padding-left:10px;padding-right:10px;}"\n'
    '            ".club-home-cards-stack .card.stats-section{width:100%;max-width:100%;box-sizing:border-box;}"\n'
    '            ".club-home-cards-stack .sa-home-regatta-card{width:100%;max-width:100%;box-sizing:border-box;padding:8px 10px;}"\n'
    '            ".club-home-cards-stack .sa-home-regatta-event-logo{width:72px;height:48px;max-width:72px;}"\n'
    '            ".club-home-cards-stack .sa-home-regatta-host-logo{display:none;}"\n'
    '            "@media (max-width:768px){.club-home-cards-stack{max-width:100%;padding-left:10px;padding-right:10px;}.sa-home-regatta-card{padding:8px 10px;}}"\n'
)

SAILOR_CSS_OLD = (
    '".club-home-cards-stack{width:100%;max-width:52rem;margin:0 auto 1.5rem;box-sizing:border-box;}"'
)
SAILOR_CSS_NEW = (
    '".club-home-cards-stack{width:100%;max-width:52rem;margin:0 auto 1.5rem;box-sizing:border-box;padding-left:10px;padding-right:10px;}"'
)
SAILOR_MP_OLD = (
    '"@media (max-width:768px){.club-home-cards-stack{max-width:100%;padding:0;}.club-home-sailor-first{font-size:1rem;}}"'
)
SAILOR_MP_NEW = (
    '"@media (max-width:768px){.club-home-cards-stack{max-width:100%;padding-left:10px;padding-right:10px;}.club-home-sailor-first{font-size:1rem;}}"'
)

PAST_SPLIT_OLD = '''                if in_results:
                    c["result_url"] = ("/regatta/" + rid) if rid else rurl
                    c["result_yes"] = True
                    if str(c.get("details_url") or "").startswith("/regatta/"):
                        c["details_url"] = ""
                    _add_past(c)
                else:
                    c["result_url"] = ""
                    c["result_yes"] = False
                    if str(c.get("details_url") or "").startswith("/regatta/"):
                        c["details_url"] = ""
                    _add_other(c)
'''

PAST_SPLIT_NEW = '''                if rid and not str(rid).lower().startswith("live-"):
                    c["result_url"] = ("/regatta/" + rid)
                    c["result_yes"] = bool(in_results)
                    if str(c.get("details_url") or "").startswith("/regatta/"):
                        c["details_url"] = ""
                    _add_past(c)
                else:
                    c["result_url"] = ""
                    c["result_yes"] = False
                    if str(c.get("details_url") or "").startswith("/regatta/"):
                        c["details_url"] = ""
                    _add_other(c)
'''

WITHOUT_OLD = '''            for row in regattas_without_results:
                card = _club_hosted_tuple_to_event_card(row, with_results=False)
                rid = str(card.get("regatta_id") or "").strip()
                resolved = _resolve_list_rid(rid)
                if resolved and resolved in results_set:
                    continue  # superseded empty shell
                if resolved and resolved != rid:
                    card["regatta_id"] = resolved
                _add_other(card)
'''

WITHOUT_NEW = '''            for row in regattas_without_results:
                card = _club_hosted_tuple_to_event_card(row, with_results=False)
                rid = str(card.get("regatta_id") or "").strip()
                resolved = _resolve_list_rid(rid)
                if resolved and resolved in results_set:
                    continue  # superseded empty shell
                if resolved and resolved != rid:
                    card["regatta_id"] = resolved
                    rid = resolved
                if rid and not rid.lower().startswith("live-"):
                    today = _club_today_iso()
                    ed = str(card.get("end_date_iso") or card.get("start_date_iso") or "")[:10]
                    sd = str(card.get("start_date_iso") or "")[:10]
                    if (ed and today and ed >= today) or (sd and today and sd >= today):
                        continue
                    card["result_url"] = "/regatta/" + rid
                    card["result_yes"] = False
                    _add_past(card)
                else:
                    _add_other(card)
'''

FILTER_OLD = '''            other_events = _club_collapse_same_event_cards(other_events)
            past_regattas.sort(
'''

FILTER_NEW = '''            other_events = _club_collapse_same_event_cards(other_events)
            keep_other = []
            for c in other_events:
                rid = str((c or {}).get("regatta_id") or "").strip()
                rurl = str((c or {}).get("result_url") or "").strip()
                if rid or rurl.startswith("/regatta/"):
                    continue
                keep_other.append(c)
            other_events = keep_other
            past_regattas.sort(
'''

OTHER_OLD = '''def _club_other_events_table_html(other_events: list, club_abbrev: str = "") -> str:
    """Other events (no results) — rendered below Sailors on the club page."""
    head = (
        "<thead><tr>"
        + _club_sort_th("#")
        + _club_sort_th("Event")
        + _club_sort_th("Start")
        + _club_sort_th("End", "hide-mobile")
        + "</tr></thead>"
    )
    rows_ot = _club_event_table_rows(
        other_events or [],
        include_result=False,
        club_abbrev=club_abbrev,
        allow_regatta_links=False,
    ) or '<tr><td colspan="4">No other hosted events.</td></tr>'
    return (
        '<div class="card stats-section club-other-events-section">'
        '<h2 class="section-title">Other events (%d)</h2>'
        '<p class="club-events-intro" style="margin:0 0 0.65rem 0;font-size:0.9rem;color:#475569;">'
        "Hosted events that are not a regatta, or do not have results yet — no result-page link."
        "</p>"
        '<input type="search" class="club-table-filter" data-table="club-other-events-table" placeholder="Search other events…" autocomplete="off">'
        '<div class="table-container club-table-scroll"><table class="table" id="club-other-events-table">%s<tbody>%s</tbody></table></div>'
        "</div>" % (len(other_events or []), head, rows_ot)
    )
'''

OTHER_NEW = r'''def _club_other_events_table_html(other_events: list, club_abbrev: str = "") -> str:
    """Attention-only other events — no Event URL yet."""
    cards = list(other_events or [])
    intro = (
        '<p class="club-events-intro">Events that still need an Event URL — website or calendar only.</p>'
    )
    if _club_home_cards_enabled(club_abbrev):
        css = (
            '<style id="club-other-cards-style">'
            ".club-home-cards-stack{width:100%;max-width:52rem;margin:0 auto 1.5rem;box-sizing:border-box;padding-left:10px;padding-right:10px;}"
            ".club-home-cards-stack .card.stats-section,.club-home-cards-stack .sa-home-regatta-card{width:100%;max-width:100%;box-sizing:border-box;}"
            ".club-home-cards-stack .sa-home-regatta-card{padding:8px 10px;}"
            ".club-home-cards-stack .sa-home-regatta-event-logo{width:72px;height:48px;max-width:72px;}"
            ".club-home-cards-stack .sa-home-regatta-host-logo{display:none;}"
            ".club-events-intro{margin:0 0 0.65rem 0;font-size:0.9rem;color:#475569;}"
            "@media (max-width:768px){.club-home-cards-stack{max-width:100%;padding-left:10px;padding-right:10px;}}"
            "</style>"
        )
        js = (
            "<script>(function(){var inp=document.querySelector('.club-other-events-section .club-home-card-filter');"
            "var list=document.getElementById('club-other-cards');if(!inp||!list)return;"
            "inp.addEventListener('input',function(){var q=(inp.value||'').toLowerCase();"
            "list.querySelectorAll('.sa-home-regatta-card').forEach(function(c){"
            "c.style.display=((c.getAttribute('data-search')||'').indexOf(q)>=0)?'':'none';});});})();</script>"
        )
        return (
            '<div class="club-home-cards-stack">'
            + css
            + '<div class="card stats-section club-other-events-section">'
            + '<h2 class="section-title">Other events (%d)</h2>' % len(cards)
            + intro
            + '<input type="search" class="club-home-card-filter" data-list="club-other-cards" placeholder="Search other events…" autocomplete="off">'
            + '<div class="sa-home-regatta-wrap"><div class="sa-home-regatta-list" id="club-other-cards">'
            + (
                "".join(_club_home_regatta_card_html(c, "upcoming", club_abbrev) for c in cards)
                if cards
                else '<p class="club-events-intro">No events need attention.</p>'
            )
            + "</div></div></div></div>"
            + js
        )
    head = (
        "<thead><tr>"
        + _club_sort_th("#")
        + _club_sort_th("Event")
        + _club_sort_th("Start")
        + _club_sort_th("End", "hide-mobile")
        + "</tr></thead>"
    )
    rows_ot = _club_event_table_rows(
        cards,
        include_result=False,
        club_abbrev=club_abbrev,
        allow_regatta_links=False,
    ) or '<tr><td colspan="4">No other hosted events.</td></tr>'
    return (
        '<div class="card stats-section club-other-events-section">'
        '<h2 class="section-title">Other events (%d)</h2>'
        '%s'
        '<input type="search" class="club-table-filter" data-table="club-other-events-table" placeholder="Search other events…" autocomplete="off">'
        '<div class="table-container club-table-scroll"><table class="table" id="club-other-events-table">%s<tbody>%s</tbody></table></div>'
        "</div>" % (len(cards), intro, head, rows_ot)
    )
'''


def main() -> None:
    api = API.read_text()
    if MARK in api:
        print("ALREADY")
        return
    missing = []
    if COUNTS_OLD not in api:
        missing.append("COUNTS")
    if CHIP_LIVE not in api:
        missing.append("CHIP")
    if HOST_LOGO_OLD not in api:
        missing.append("HOST")
    if CSS_OLD not in api:
        missing.append("CSS")
    if PAST_SPLIT_OLD not in api:
        missing.append("SPLIT")
    if WITHOUT_OLD not in api:
        missing.append("WITHOUT")
    if FILTER_OLD not in api:
        missing.append("FILTER")
    if OTHER_OLD not in api:
        missing.append("OTHER")
    if missing:
        raise SystemExit("MISSING:" + ",".join(missing))
    ts = time.strftime("%Y%m%d_%H%M%S")
    bak = API.with_name("api.py.bak.club_past_compact." + ts)
    shutil.copy2(API, bak)
    api = api.replace(COUNTS_OLD, COUNTS_NEW, 1)
    api = api.replace(CHIP_LIVE, "", 1)
    api = api.replace(HOST_LOGO_OLD, HOST_LOGO_NEW, 1)
    api = api.replace(CSS_OLD, CSS_NEW, 1)
    if SAILOR_CSS_OLD in api:
        api = api.replace(SAILOR_CSS_OLD, SAILOR_CSS_NEW, 1)
    if SAILOR_MP_OLD in api:
        api = api.replace(SAILOR_MP_OLD, SAILOR_MP_NEW, 1)
    api = api.replace(PAST_SPLIT_OLD, PAST_SPLIT_NEW, 1)
    api = api.replace(WITHOUT_OLD, WITHOUT_NEW, 1)
    api = api.replace(FILTER_OLD, FILTER_NEW, 1)
    api = api.replace(OTHER_OLD, OTHER_NEW, 1)
    API.write_text(api)
    print("API_OK", MARK, "BAK", str(bak))


if __name__ == "__main__":
    main()
