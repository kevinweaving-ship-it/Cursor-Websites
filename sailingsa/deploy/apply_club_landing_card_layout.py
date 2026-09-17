#!/usr/bin/env python3
"""Club event cards: landing All Regattas layout — no date/host overlap."""
from pathlib import Path
import shutil
import time

API = Path("/var/www/sailingsa/api/api.py")
MARK = "CLUB_LANDING_CARD_LAYOUT_v1"

DATE_OLD = '''def _club_card_date_label(c: dict) -> str:
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
'''

DATE_NEW = '''def _club_card_date_label(c: dict) -> str:
    # CLUB_LANDING_CARD_LAYOUT_v1 — landing short dates, no weekday/time
    months = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

    def _short(raw):
        s = str(raw or "").strip()[:10]
        if len(s) >= 10 and s[4] == "-" and s[7] == "-":
            try:
                y = int(s[0:4])
                m = int(s[5:7])
                d = int(s[8:10])
                if 1 <= m <= 12 and 1 <= d <= 31:
                    return "%d %s %d" % (d, months[m - 1], y)
            except Exception:
                return ""
        return ""

    sd = _short(c.get("start_date_iso") or "")
    ed = _short(c.get("end_date_iso") or "")
    if sd and ed and sd != ed:
        return sd + " → " + ed
    if sd or ed:
        return sd or ed
    return ""
'''

CARD_OLD = '''def _club_home_regatta_card_html(c: dict, panel: str, club_abbrev: str) -> str:
    """Landing All Regattas card. Name → Event URL. Button follows Event Info / Upcoming Event / Results / Final Results."""
    e = _club_enrich_home_card(c, club_abbrev)
    esc = html_module.escape
    title = e.get("display_title") or e.get("event_name") or "—"
    rid = str(e.get("regatta_id") or "").strip()
    event_href = ("/regatta/" + rid) if rid else ""
    website = str(e.get("source_url") or "").strip()
    title_html = (
        '<a href="%s" class="sa-home-regatta-title">%s</a>' % (esc(event_href, quote=True), esc(title))
        if event_href
        else '<div class="sa-home-regatta-title">%s</div>' % esc(title)
    )
    logo_src = str(e.get("event_logo_url") or "").strip()
    if not logo_src and event_href:
        logo_src = str(e.get("club_logo_url") or "").strip()
    logo_html = (
        '<img class="sa-home-regatta-event-logo" src="%s" alt="" loading="lazy" decoding="async" onerror="this.style.display=\\'none\\'">'
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
    host_inner = '<div class="sa-home-regatta-host-text">'
    if host_code and host_code not in ("—", "-"):
        host_inner += '<div class="sa-home-regatta-host-code">%s</div>' % esc(host_code)
    host_inner += "</div>"
    if slug:
        host_html = '<a class="sa-home-regatta-host" href="/club/%s">%s</a>' % (esc(slug, quote=True), host_inner)
    else:
        host_html = '<div class="sa-home-regatta-host">%s</div>' % host_inner
    actions = '<div class="sa-home-regatta-actions">'
    btn_href, btn_label, btn_ext = _club_card_action(e, panel, event_href, website, ent)
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
    actions += "</div>"
    bg = " ec-upcoming" if panel == "upcoming" else (" ec-live" if panel == "live" else " ec-past-results")
    hay = esc((title + " " + date_l + " " + host_code).lower(), quote=True)
    return (
        '<article class="sa-home-regatta-card%s" data-search="%s">'
        '<div class="sa-home-regatta-top">%s<div class="sa-home-regatta-top-main">%s%s</div>%s%s</div></article>'
    ) % (bg, hay, logo_html, title_html, meta, host_html, actions)
'''

CARD_OLD_LIVE = r'''def _club_home_regatta_card_html(c: dict, panel: str, club_abbrev: str) -> str:
    """Landing All Regattas card. Name → Event URL. Button follows Event Info / Upcoming Event / Results / Final Results."""
    e = _club_enrich_home_card(c, club_abbrev)
    esc = html_module.escape
    title = e.get("display_title") or e.get("event_name") or "—"
    rid = str(e.get("regatta_id") or "").strip()
    event_href = ("/regatta/" + rid) if rid else ""
    website = str(e.get("source_url") or "").strip()
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
    host_inner = '<div class="sa-home-regatta-host-text">'
    if host_code and host_code not in ("—", "-"):
        host_inner += '<div class="sa-home-regatta-host-code">%s</div>' % esc(host_code)
    host_inner += "</div>"
    if slug:
        host_html = '<a class="sa-home-regatta-host" href="/club/%s">%s</a>' % (esc(slug, quote=True), host_inner)
    else:
        host_html = '<div class="sa-home-regatta-host">%s</div>' % host_inner
    actions = '<div class="sa-home-regatta-actions">'
    btn_href, btn_label, btn_ext = _club_card_action(e, panel, event_href, website, ent)
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
    actions += "</div>"
    bg = " ec-upcoming" if panel == "upcoming" else (" ec-live" if panel == "live" else " ec-past-results")
    hay = esc((title + " " + date_l + " " + host_code).lower(), quote=True)
    return (
        '<article class="sa-home-regatta-card%s" data-search="%s">'
        '<div class="sa-home-regatta-top">%s<div class="sa-home-regatta-top-main">%s%s</div>%s%s</div></article>'
    ) % (bg, hay, logo_html, title_html, meta, host_html, actions)
'''

CARD_NEW = r'''def _club_home_regatta_card_html(c: dict, panel: str, club_abbrev: str) -> str:
    """Landing All Regattas card. Name → Event URL. Button follows Event Info / Upcoming Event / Results / Final Results."""
    e = _club_enrich_home_card(c, club_abbrev)
    esc = html_module.escape
    title = e.get("display_title") or e.get("event_name") or "—"
    rid = str(e.get("regatta_id") or "").strip()
    event_href = ("/regatta/" + rid) if rid else ""
    website = str(e.get("source_url") or "").strip()
    title_html = (
        '<a href="%s" class="sa-home-regatta-title">%s</a>' % (esc(event_href, quote=True), esc(title))
        if event_href
        else '<div class="sa-home-regatta-title">%s</div>' % esc(title)
    )
    logo_src = str(e.get("event_logo_url") or "").strip()
    if not logo_src and event_href:
        logo_src = str(e.get("club_logo_url") or "").strip()
    img = (
        '<img class="sa-home-regatta-event-logo" src="%s" alt="" loading="lazy" decoding="async" onerror="this.style.display=\'none\'">'
        % esc(logo_src, quote=True)
        if logo_src
        else ""
    )
    if img and event_href:
        logo_html = '<a class="sa-home-regatta-event-logo-link" href="%s">%s</a>' % (
            esc(event_href, quote=True),
            img,
        )
    elif img:
        logo_html = '<span class="sa-home-regatta-event-logo-link">%s</span>' % img
    else:
        logo_html = '<span class="sa-home-regatta-event-logo-link"></span>'
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
    class_logo = str(e.get("class_logo_url") or "").strip()
    if class_logo and class_logo != logo_src and event_href:
        actions += (
            '<a class="sa-home-regatta-single-class" href="%s" title="Class">'
            '<img class="sa-home-regatta-chip-logo" src="%s" alt="" loading="lazy" decoding="async" onerror="this.style.display=\'none\'">'
            "</a>"
        ) % (esc(event_href, quote=True), esc(class_logo, quote=True))
    btn_href, btn_label, btn_ext = _club_card_action(e, panel, event_href, website, ent)
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
    actions += "</div>"
    bg = " ec-upcoming" if panel == "upcoming" else (" ec-live" if panel == "live" else " ec-past-results")
    hay = esc((title + " " + date_l + " " + host_code).lower(), quote=True)
    return (
        '<article class="sa-home-regatta-card%s" data-search="%s">'
        '<div class="sa-home-regatta-top">%s<div class="sa-home-regatta-top-main">%s%s</div>%s%s</div></article>'
    ) % (bg, hay, logo_html, title_html, meta, host_html, actions)
'''

CSS_OLD = (
    '            ".sa-home-regatta-list{display:flex;flex-direction:column;gap:10px;}"\n'
    '            ".sa-home-regatta-single-class{display:inline-flex;align-items:center;justify-content:center;min-width:44px;min-height:44px;line-height:0;}"\n'
    '            ".sa-home-regatta-chip-logo{display:block;width:52px;height:28px;object-fit:contain;}"\n'
    '            ".club-home-card-filter{min-height:44px;width:100%;max-width:100%;box-sizing:border-box;font-size:16px;padding:8px 12px;margin:0 0 0.75rem 0;}"\n'
    '            ".sa-home-regatta-title{white-space:normal;overflow-wrap:anywhere;}"\n'
    '            ".sa-home-regatta-card{box-sizing:border-box;}"\n'
    '            "@media (max-width:768px){"\n'
    '            ".sa-home-regatta-card{padding:10px;}"\n'
    "            '.sa-home-regatta-top{grid-template-columns:72px minmax(0,1fr);grid-template-areas:\"logo main\" \"host host\" \"actions actions\";gap:8px 10px;align-items:start;}'\n"
    '            ".sa-home-regatta-event-logo{width:68px;height:52px;max-width:68px;}"\n'
    '            ".sa-home-regatta-title{font-size:14px;line-height:1.25;}"\n'
    '            ".sa-home-regatta-meta{flex-wrap:wrap;gap:6px;}"\n'
    '            ".sa-home-regatta-host{min-height:44px;}"\n'
    '            ".sa-home-regatta-host-name{white-space:normal;max-width:none;}"\n'
    '            ".sa-home-regatta-actions{width:100%;justify-content:stretch;gap:8px;}"\n'
    '            ".sa-home-regatta-btn{flex:1;min-height:44px;min-width:44px;padding:10px 12px;}"\n'
    '            "}"\n'
    '            ".club-home-cards-stack{width:100%;max-width:52rem;margin:0 auto 1.5rem;box-sizing:border-box;padding-left:10px;padding-right:10px;}"\n'
    '            ".club-home-cards-stack .card.stats-section{width:100%;max-width:100%;box-sizing:border-box;}"\n'
    '            ".club-home-cards-stack .sa-home-regatta-card{width:100%;max-width:100%;box-sizing:border-box;padding:8px 10px;}"\n'
    '            ".club-home-cards-stack .sa-home-regatta-event-logo{width:72px;height:48px;max-width:72px;}"\n'
    '            ".club-home-cards-stack .sa-home-regatta-host-logo{display:none;}"\n'
    '            "@media (max-width:768px){.club-home-cards-stack{max-width:100%;padding-left:10px;padding-right:10px;}.sa-home-regatta-card{padding:8px 10px;}}"\n'
)

CSS_NEW = (
    '            ".sa-home-regatta-list{display:flex;flex-direction:column;gap:10px;}"\n'
    '            ".club-home-card-filter{min-height:44px;width:100%;max-width:100%;box-sizing:border-box;font-size:16px;padding:8px 12px;margin:0 0 0.75rem 0;}"\n'
    '            ".club-home-cards-stack{width:100%;max-width:52rem;margin:0 auto 1.5rem;box-sizing:border-box;padding-left:10px;padding-right:10px;}"\n'
    '            ".club-home-cards-stack .card.stats-section,.club-home-cards-stack .sa-home-regatta-card{width:100%;max-width:100%;box-sizing:border-box;}"\n'
    '            ".club-home-cards-stack .sa-home-regatta-card{overflow:hidden;}"\n'
    '            ".club-home-cards-stack .sa-home-regatta-top{display:grid;grid-template-columns:96px minmax(0,1fr) minmax(96px,140px) auto;grid-template-areas:\\"logo main host actions\\";gap:10px 12px;align-items:center;}"\n'
    '            ".club-home-cards-stack .sa-home-regatta-event-logo-link{grid-area:logo;display:flex;align-items:center;justify-content:flex-start;min-width:0;line-height:0;}"\n'
    '            ".club-home-cards-stack .sa-home-regatta-event-logo{grid-area:auto;width:96px;height:68px;max-width:96px;object-fit:contain;}"\n'
    '            ".club-home-cards-stack .sa-home-regatta-top-main{grid-area:main;min-width:0;overflow:hidden;}"\n'
    '            ".club-home-cards-stack .sa-home-regatta-title{white-space:normal;overflow-wrap:anywhere;}"\n'
    '            ".club-home-cards-stack .sa-home-regatta-meta{flex-wrap:wrap;gap:6px;}"\n'
    '            ".club-home-cards-stack .sa-home-regatta-meta-pill{white-space:normal;overflow-wrap:anywhere;max-width:100%;}"\n'
    '            ".club-home-cards-stack .sa-home-regatta-host{grid-area:host;min-width:0;align-items:center;}"\n'
    '            ".club-home-cards-stack .sa-home-regatta-host-logo{display:block;width:72px;height:40px;object-fit:contain;flex:0 0 auto;}"\n'
    '            ".club-home-cards-stack .sa-home-regatta-actions{grid-area:actions;flex-wrap:nowrap;}"\n'
    '            ".club-home-cards-stack .sa-home-regatta-single-class{display:inline-flex;align-items:center;justify-content:center;min-width:44px;min-height:44px;}"\n'
    '            "@media (max-width:768px){"\n'
    '            ".club-home-cards-stack{max-width:100%;padding-left:10px;padding-right:10px;}"\n'
    '            ".club-home-cards-stack .sa-home-regatta-top{grid-template-columns:78px minmax(0,1fr);grid-template-areas:\\"logo main\\" \\"logo host\\" \\"actions actions\\";gap:8px 10px;align-items:start;}"\n'
    '            ".club-home-cards-stack .sa-home-regatta-event-logo{width:78px;height:58px;max-width:78px;}"\n'
    '            ".club-home-cards-stack .sa-home-regatta-actions{width:100%;justify-content:flex-end;gap:8px;}"\n'
    '            ".club-home-cards-stack .sa-home-regatta-btn{flex:1;min-height:44px;min-width:44px;}"\n'
    '            "}"\n'
)

OTHER_HIDE = '".club-home-cards-stack .sa-home-regatta-host-logo{display:none;}"'
OTHER_SHOW = '".club-home-cards-stack .sa-home-regatta-host-logo{display:block;width:72px;height:40px;object-fit:contain;}"'


def main() -> None:
    api = API.read_text()
    if MARK in api:
        print("ALREADY")
        return
    missing = []
    if DATE_OLD not in api:
        missing.append("DATE")
    if CARD_OLD_LIVE not in api:
        missing.append("CARD")
    if CSS_OLD not in api:
        missing.append("CSS")
    if missing:
        raise SystemExit("MISSING:" + ",".join(missing))
    ts = time.strftime("%Y%m%d_%H%M%S")
    bak = API.with_name("api.py.bak.club_landing_layout." + ts)
    shutil.copy2(API, bak)
    api = api.replace(DATE_OLD, DATE_NEW, 1)
    api = api.replace(CARD_OLD_LIVE, CARD_NEW, 1)
    api = api.replace(CSS_OLD, CSS_NEW, 1)
    if OTHER_HIDE in api:
        api = api.replace(OTHER_HIDE, OTHER_SHOW)
    if MARK not in api:
        raise SystemExit("MARK_MISSING")
    API.write_text(api)
    print("API_OK", MARK, "BAK", str(bak))


if __name__ == "__main__":
    main()
