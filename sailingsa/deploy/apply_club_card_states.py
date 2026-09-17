#!/usr/bin/env python3
"""Club cards: lifecycle button labels + landing sailor cards.

Event button:
  Event Info → external website until entries exist
  Upcoming Event → Event URL once entries are loaded
  Results → Event URL while today is in the event date range
  Final Results → Event URL after the event is closed (Past list)

Sailors list uses landing-style cards. All cards stay in the 52rem stack
and stack on mobile portrait first (44px targets).
"""
from pathlib import Path
import shutil
import time

API = Path("/var/www/sailingsa/api/api.py")
MARK = "CLUB_HOME_CARD_STATES_v1"

BTN_OLD = """    has_results = bool(e.get("result_yes") or str(e.get("result_url") or "").startswith("/regatta/"))
    title_html = (
        '<a href="%s" class="sa-home-regatta-title">%s</a>' % (esc(event_href, quote=True), esc(title))
        if event_href
        else '<div class="sa-home-regatta-title">%s</div>' % esc(title)
    )
"""

BTN_NEW = """    title_html = (
        '<a href="%s" class="sa-home-regatta-title">%s</a>' % (esc(event_href, quote=True), esc(title))
        if event_href
        else '<div class="sa-home-regatta-title">%s</div>' % esc(title)
    )
"""

ACTIONS_OLD = """    if has_results and event_href:
        actions += '<a class="sa-home-regatta-btn" href="%s">Full Results</a>' % esc(event_href, quote=True)
    elif website.startswith("http"):
        actions += (
            '<a class="sa-home-regatta-btn" href="%s" target="_blank" rel="noopener">Full Results</a>'
            % esc(website, quote=True)
        )
"""

ACTIONS_NEW = """    btn_href, btn_label, btn_ext = _club_card_action(e, panel, event_href, website, ent)
    if btn_href and btn_label:
        if btn_ext:
            actions += (
                '<a class="sa-home-regatta-btn" href="%s" target="_blank" rel="noopener">%s</a>'
                % (esc(btn_href, quote=True), esc(btn_label))
            )
        else:
            actions += '<a class="sa-home-regatta-btn" href="%s">%s</a>' % (
                esc(btn_href, quote=True),
                esc(btn_label),
            )
"""

FILL_OLD = """        upcoming = live + _sort_upcoming_events_page_date_first(list(up or []))
        past = list(past_regattas or [])
        css = '<style id="sa-home-regatta-list-style">' + _EVENTS_PAGE_REGATTA_LIST_CSS
"""

FILL_NEW = """        upcoming = live + _sort_upcoming_events_page_date_first(list(up or []))
        past = list(past_regattas or [])
        _club_fill_card_entries(upcoming + past)
        css = '<style id="sa-home-regatta-list-style">' + _EVENTS_PAGE_REGATTA_LIST_CSS
"""

HELPERS = r'''
def _club_today_iso() -> str:
    try:
        return datetime.date.today().isoformat()
    except Exception:
        return ""


def _club_regatta_entry_counts(rids: list) -> dict:
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


def _club_fill_card_entries(cards: list) -> None:
    rids = [str((c or {}).get("regatta_id") or "").strip() for c in (cards or [])]
    counts = _club_regatta_entry_counts(rids)
    for c in cards or []:
        rid = str((c or {}).get("regatta_id") or "").strip()
        n = int(counts.get(rid, 0) or 0)
        try:
            already = int((c or {}).get("entries") or 0)
        except Exception:
            already = 0
        c["entries"] = max(already, n)


def _club_card_action(e: dict, panel: str, event_href: str, website: str, entries: int):
    """Lifecycle button: Event Info → Upcoming Event → Results → Final Results."""
    today = _club_today_iso()
    sd = str((e or {}).get("start_date_iso") or "")[:10]
    ed = str((e or {}).get("end_date_iso") or sd)[:10]
    state = str((e or {}).get("event_state") or "").upper()
    closed = (panel == "past") or (state == "PAST") or (bool(ed) and bool(today) and ed < today)
    in_range = (
        (panel == "live")
        or (state == "ACTIVE")
        or (bool(sd) and bool(ed) and bool(today) and sd <= today <= ed)
    )
    if closed:
        if event_href:
            return event_href, "Final Results", False
        if website.startswith("http"):
            return website, "Final Results", True
        return "", "", False
    if in_range:
        if event_href:
            return event_href, "Results", False
        if website.startswith("http"):
            return website, "Results", True
        return "", "", False
    if entries > 0 and event_href:
        return event_href, "Upcoming Event", False
    if website.startswith("http"):
        return website, "Event Info", True
    return "", "", False


def _club_province_short(raw: str) -> str:
    u = (raw or "").strip().upper()
    if not u:
        return ""
    if "KWAZULU" in u or u in ("KZN", "KN", "KP"):
        return "KP"
    if "WESTERN CAPE" in u or u == "WC":
        return "WC"
    if "EASTERN CAPE" in u or u == "EC":
        return "EC"
    if "NORTHERN CAPE" in u or u == "NC":
        return "NC"
    if "FREE STATE" in u or u == "FS":
        return "FS"
    if "GAUTENG" in u or u == "GP":
        return "GP"
    if "MPUMALANGA" in u or u == "MP":
        return "MP"
    if "LIMPOPO" in u or u == "LP":
        return "LP"
    if "NORTH WEST" in u or u == "NW":
        return "NW"
    return u[:2]


def _club_sailor_province_map(sids: list) -> dict:
    out = {}
    ids = [str(s or "").strip() for s in (sids or []) if str(s or "").strip()]
    if not ids:
        return out
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT sa_sailing_id::text, COALESCE(province,'') FROM sas_id_personal WHERE sa_sailing_id::text = ANY(%s)",
            (ids,),
        )
        for sid, prov in cur.fetchall() or []:
            out[str(sid)] = str(prov or "").strip()
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

SAILORS_OLD = '''def _club_sailors_table_section_html(sailors: list, club_abbrev: str = "") -> str:
    n = len(sailors or [])
    head = "<thead><tr>" + _club_sort_th("#") + _club_sort_th("Sailor") + "</tr></thead>"
    trs = []
    for i, row in enumerate(sailors or [], 1):
        name = row[0] if row else ""
        sslug = row[1] if len(row) > 1 else ""
        sas = str(row[2] or "").strip() if len(row) > 2 else ""
        fn = str(row[3] or "").strip() if len(row) > 3 else ""
        ln = str(row[4] or "").strip() if len(row) > 4 else ""
        full = str(row[5] or "").strip() if len(row) > 5 else name
        dn = html_module.escape(name)
        ds = html_module.escape(name.lower(), quote=True)
        av_src = html_module.escape(_users_avatar_url(sas, fn, ln, full), quote=True)
        av = f'<img src="{av_src}" alt="" class="row-av" width="28" height="28" loading="lazy" decoding="async">'
        trs.append(
            '<tr data-search="%s"><td>%d</td><td class="cell-left">%s'
            '<a href="/sailor/%s">%s</a></td></tr>' % (ds, i, av, html_module.escape(sslug), dn)
        )
    body_rows = "".join(trs) or '<tr><td colspan="2">No sailors found.</td></tr>'
    return (
        '<div class="card stats-section club-sailors-section">'
        '<h2 class="section-title">Sailors (%d)</h2>'
        '<input type="search" class="club-table-filter" data-table="club-sailors-table" placeholder="Search sailors name…" autocomplete="off">'
        '<div class="table-container club-table-scroll"><table class="table" id="club-sailors-table">%s<tbody>%s</tbody></table></div>'
        "</div>" % (n, head, body_rows)
    )
'''

SAILORS_NEW = r'''def _club_sailors_table_section_html(sailors: list, club_abbrev: str = "") -> str:
    # CLUB_HOME_CARD_STATES_v1
    n = len(sailors or [])
    if n == 0:
        return (
            '<div class="club-home-cards-stack"><div class="card stats-section club-sailors-section">'
            '<h2 class="section-title">Sailors (0)</h2><p>No sailors found.</p></div></div>'
        )
    esc = html_module.escape
    club_code = (club_abbrev or "").strip()
    club_slug = club_code.lower()
    try:
        club_logo = _club_logo_public_url(club_code) if club_code else ""
    except Exception:
        club_logo = ""
    sids = [str(row[2] or "").strip() for row in sailors if row and len(row) > 2]
    provinces = _club_sailor_province_map(sids)
    cards = []
    for row in sailors or []:
        name = row[0] if row else ""
        sslug = row[1] if len(row) > 1 else ""
        sas = str(row[2] or "").strip() if len(row) > 2 else ""
        fn = str(row[3] or "").strip() if len(row) > 3 else ""
        ln = str(row[4] or "").strip() if len(row) > 4 else ""
        full = str(row[5] or "").strip() if len(row) > 5 else name
        if not fn and "," in str(name):
            fn = str(name).split(",", 1)[0].strip()
            ln = str(name).split(",", 1)[1].strip()
        first = fn or (full.split(" ", 1)[0] if full else name) or "Sailor"
        last = ln or (" ".join(full.split(" ")[1:]) if full and " " in full else "")
        href = ("/sailor/" + sslug) if sslug else ""
        hay = esc(" ".join([name, first, last, sas]).lower(), quote=True)
        try:
            av_src = _users_avatar_url(sas, fn, ln, full)
        except Exception:
            av_src = "/assets/avatars/default-youth.png"
        initials = ((first[:1] + last[:1]) if first and last else (first[:2] or "?")).upper()
        profile = (
            '<a class="club-home-sailor-profile" href="%s">' % esc(href, quote=True)
            if href
            else '<div class="club-home-sailor-profile">'
        )
        profile_end = "</a>" if href else "</div>"
        club_html = '<div class="club-home-sailor-club">'
        if club_logo:
            club_html += (
                '<img class="club-home-sailor-club-logo" src="%s" alt="" loading="lazy" decoding="async" onerror="this.style.display=\'none\'">'
                % esc(club_logo, quote=True)
            )
        if club_code:
            club_html += '<span class="club-home-sailor-club-code">%s</span>' % esc(club_code)
        club_html += "</div>"
        claim = ""
        if sas:
            qname = (first + " " + last).strip().replace(" ", "+")
            claim_href = "/signup.html?signup=1&sas_id=%s&name=%s" % (
                esc(sas, quote=True),
                esc(qname, quote=True),
            )
            claim = (
                '<a class="sa-claim-banner club-home-sailor-claim" href="%s">'
                '<span class="club-home-sailor-claim-copy">'
                '<strong>Is this your sailing profile?</strong>'
                "<span>Unlock your full results and stats</span></span>"
                '<span class="club-home-sailor-claim-cta">CLAIM MY PROFILE</span></a>'
            ) % claim_href
        prov_raw = provinces.get(sas, "")
        prov_short = _club_province_short(prov_raw)
        prov = ""
        if prov_short:
            prov = (
                '<div class="club-home-sailor-prov">'
                '<span class="club-home-sailor-prov-box">%s</span>'
                '<span class="club-home-sailor-prov-name">%s</span></div>'
            ) % (esc(prov_short), esc(prov_raw or prov_short))
        cards.append(
            '<article class="sa-approved-sailor-card club-home-sailor-card" data-search="%s" data-sas-id="%s">'
            '%s<div class="club-home-sailor-avatar"><img src="%s" alt="" loading="lazy" decoding="async" onerror="this.style.display=\'none\'">'
            '<span class="club-home-sailor-initials">%s</span></div>'
            '<div class="club-home-sailor-main"><div class="club-home-sailor-name">'
            '<span class="club-home-sailor-first">%s</span>'
            '<span class="club-home-sailor-last">%s</span></div>%s</div>%s'
            "%s%s</article>"
            % (
                hay,
                esc(sas, quote=True),
                profile,
                esc(av_src, quote=True),
                esc(initials),
                esc(first),
                esc(last),
                club_html,
                profile_end,
                claim,
                prov,
            )
        )
    css = (
        '<style id="club-home-sailor-cards-style">'
        ".club-home-cards-stack{width:100%;max-width:52rem;margin:0 auto 1.5rem;box-sizing:border-box;}"
        ".club-home-cards-stack .card.stats-section,.club-home-sailor-card{width:100%;max-width:100%;box-sizing:border-box;}"
        ".club-home-sailor-list{display:flex;flex-direction:column;gap:10px;width:100%;}"
        ".club-home-card-filter{min-height:44px;width:100%;max-width:100%;box-sizing:border-box;font-size:16px;padding:8px 12px;margin:0 0 0.75rem 0;}"
        ".club-home-sailor-card{display:flex;flex-direction:column;gap:10px;padding:10px;border:3px solid #6c8ebd;border-radius:22px;background:#fff;}"
        ".club-home-sailor-profile{display:grid;grid-template-columns:76px minmax(0,1fr);gap:10px;align-items:start;text-decoration:none;color:inherit;min-height:44px;}"
        ".club-home-sailor-avatar{width:76px;height:76px;border-radius:999px;overflow:hidden;background:#eef4fb;border:1px solid #dbe4ee;position:relative;}"
        ".club-home-sailor-avatar img{width:100%;height:100%;object-fit:cover;display:block;}"
        ".club-home-sailor-initials{display:none;width:100%;height:100%;align-items:center;justify-content:center;font-weight:800;color:#142b5f;}"
        ".club-home-sailor-name{min-width:0;overflow-wrap:anywhere;}"
        ".club-home-sailor-first{display:block;font-size:1.05rem;font-weight:800;color:#142b5f;line-height:1.15;}"
        ".club-home-sailor-last{display:block;font-size:0.95rem;font-weight:500;margin-top:0.12rem;}"
        ".club-home-sailor-club{margin-top:0.35rem;display:inline-flex;flex-direction:column;align-items:center;gap:3px;min-height:44px;}"
        ".club-home-sailor-club-logo{width:auto;max-width:56px;height:34px;object-fit:contain;display:block;}"
        ".club-home-sailor-club-code{font-size:0.95rem;font-weight:900;color:#142b5f;}"
        ".club-home-sailor-claim{display:flex;flex-direction:column;width:100%;min-height:44px;border:1px solid #e5e7eb;border-radius:12px;overflow:hidden;text-decoration:none;background:#fff;}"
        ".club-home-sailor-claim-copy{display:flex;flex-direction:column;gap:2px;padding:8px 10px;color:#111827;font-size:0.82rem;line-height:1.25;}"
        ".club-home-sailor-claim-cta{display:flex;align-items:center;justify-content:center;min-height:44px;background:#001f3f;color:#fff;font-size:0.78rem;font-weight:800;letter-spacing:0.04em;}"
        ".club-home-sailor-prov{display:flex;flex-direction:column;align-items:center;gap:4px;min-width:44px;}"
        ".club-home-sailor-prov-box{width:54px;height:54px;border-radius:999px;background:#001f3f;color:#fff;display:flex;align-items:center;justify-content:center;font-weight:800;}"
        ".club-home-sailor-prov-name{font-size:0.7rem;line-height:1.15;text-align:center;color:#475569;max-width:7rem;overflow-wrap:anywhere;}"
        "@media (min-width:769px){"
        ".club-home-sailor-card{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(0,1fr) 76px;align-items:center;gap:12px;padding:12px 10px;}"
        ".club-home-sailor-profile{grid-column:1;}"
        ".club-home-sailor-claim{grid-column:2;max-width:22rem;margin:0 auto;}"
        ".club-home-sailor-prov{grid-column:3;}"
        "}"
        "@media (max-width:768px){.club-home-cards-stack{max-width:100%;padding:0;}.club-home-sailor-first{font-size:1rem;}}"
        "</style>"
    )
    js = (
        "<script>(function(){var inp=document.getElementById('club-sailors-home-filter');"
        "var list=document.getElementById('club-home-sailors-list');"
        "if(!inp||!list)return;"
        "inp.addEventListener('input',function(){var q=(inp.value||'').toLowerCase();var n=0;"
        "list.querySelectorAll('.club-home-sailor-card').forEach(function(c){"
        "var ok=((c.getAttribute('data-search')||'').indexOf(q)>=0);c.style.display=ok?'':'none';if(ok)n++;});"
        "var empty=document.getElementById('club-home-sailors-empty');"
        "if(empty)empty.style.display=n?'none':'block';});})();</script>"
    )
    return (
        '<div class="club-home-cards-stack">'
        + css
        + '<div class="card stats-section club-sailors-section">'
        '<h2 class="section-title">Sailors (%d)</h2>'
        '<input type="search" id="club-sailors-home-filter" class="club-home-card-filter" placeholder="Search sailors name…" autocomplete="off">'
        '<div class="club-home-sailor-list" id="club-home-sailors-list">%s</div>'
        '<p id="club-home-sailors-empty" role="status" style="display:none">No sailors match your search.</p>'
        "</div></div>"
        % (n, "".join(cards))
        + js
    )


'''

DOC_OLD = '    """Landing All Regattas card. Name → Event URL. Full Results → website until results exist."""\n'
DOC_NEW = '    """Landing All Regattas card. Name → Event URL. Button follows Event Info / Upcoming Event / Results / Final Results."""\n'

INSERT_NEEDLE = "def _club_home_regatta_card_html(c: dict, panel: str, club_abbrev: str) -> str:\n"


def main() -> None:
    api = API.read_text()
    if MARK in api:
        print("ALREADY")
        return
    missing = []
    if BTN_OLD not in api:
        missing.append("BTN")
    if ACTIONS_OLD not in api:
        missing.append("ACTIONS")
    if FILL_OLD not in api:
        missing.append("FILL")
    if SAILORS_OLD not in api:
        missing.append("SAILORS")
    if INSERT_NEEDLE not in api:
        missing.append("INSERT")
    if missing:
        raise SystemExit("MISSING:" + ",".join(missing))
    ts = time.strftime("%Y%m%d_%H%M%S")
    bak = API.with_name("api.py.bak.club_card_states." + ts)
    shutil.copy2(API, bak)
    api = api.replace(BTN_OLD, BTN_NEW, 1)
    api = api.replace(ACTIONS_OLD, ACTIONS_NEW, 1)
    api = api.replace(FILL_OLD, FILL_NEW, 1)
    api = api.replace(SAILORS_OLD, SAILORS_NEW, 1)
    api = api.replace(DOC_OLD, DOC_NEW, 1)
    api = api.replace(INSERT_NEEDLE, HELPERS + INSERT_NEEDLE, 1)
    API.write_text(api)
    print("API_OK", MARK, "BAK", str(bak))


if __name__ == "__main__":
    main()
