"""Pass C: landing Hero / Hero 2 upcoming-event story cards.

Selects from existing events + regattas. Same /regatta/{id} forever.
Never invents history, as_at, or event totals.
"""
from __future__ import annotations

import html as html_module
import json
import os
import re
from datetime import date, datetime
from typing import Any, Optional

from event_page_seo import compact_event_date_range, derive_event_lifecycle

_PRIVATE_RID = re.compile(r"(^live-|-dev2\b|tracking-dev|^test-)", re.I)
_SKIP_STATUS = frozenset({"event_page", "deleted", "private", "admin", "test", "dev", "superseded"})
CATALOGUE_DISK = "/var/tmp/sailingsa_catalogue_event_index.json"


def _as_date(d: Any) -> Optional[date]:
    if d is None:
        return None
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date):
        return d
    s = str(d).strip()
    if len(s) >= 10:
        try:
            return date.fromisoformat(s[:10])
        except Exception:
            return None
    return None


def countdown_label(start_date: Any, end_date: Any, *, today: Optional[date] = None, as_at_time: Any = None, result_status: str = "") -> str:
    today = today or date.today()
    st = _as_date(start_date)
    en = _as_date(end_date) or st
    status = (result_status or "").strip().lower()
    if status == "final" and en and en < today:
        return "FINAL RESULTS"
    if not st:
        return ""
    if st > today:
        days = (st - today).days
        if days == 1:
            return "TOMORROW"
        return f"{days} DAYS TO GO"
    if st == today and (not en or en >= today):
        if en and en > st:
            return f"LIVE · DAY 1 OF {(en - st).days + 1}"
        return "STARTS TODAY"
    if en and st < today <= en:
        day_n = (today - st).days + 1
        total = (en - st).days + 1
        if as_at_time is not None:
            t = _as_at_hhmm(as_at_time)
            if t:
                return f"LIVE — Results updated {t}"
        return f"LIVE · DAY {day_n} OF {total}"
    if en and today > en:
        if status == "final":
            return "FINAL RESULTS"
        if as_at_time is not None:
            t = _as_at_hhmm(as_at_time)
            if t:
                return f"Results updated {t}"
        return "RESULTS"
    return ""


def _as_at_hhmm(as_at_time: Any) -> str:
    if as_at_time is None:
        return ""
    if hasattr(as_at_time, "strftime"):
        try:
            return as_at_time.strftime("%H:%M")
        except Exception:
            return ""
    s = str(as_at_time)
    m = re.search(r"(\d{2}:\d{2})", s)
    return m.group(1) if m else ""


def _public_rid(rid: str) -> bool:
    rid = (rid or "").strip()
    if not rid or "/" in rid or " " in rid:
        return False
    return not _PRIVATE_RID.search(rid)


def _class_href(name: str) -> str:
    s = (name or "").strip().lower().replace(" ", "-")
    s = re.sub(r"[^a-z0-9.-]", "", s)
    if s and re.match(r"^\d+-", s):
        s = s.split("-", 1)[1]
    return f"/class/{s}" if s else ""


def _club_href(abbrev: str, fullname: str = "") -> str:
    raw = (abbrev or fullname or "").strip().lower()
    s = re.sub(r"[^\w\s\-]", "", raw)
    s = re.sub(r"\s+", "-", s).strip("-")
    return f"/club/{s}" if s else ""


def _canon_series_key(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", " ", (name or "").lower()).strip()
    s = re.sub(r"\b20\d{2}\b", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def load_catalogue_index() -> dict:
    try:
        if os.path.isfile(CATALOGUE_DISK):
            idx = json.load(open(CATALOGUE_DISK, encoding="utf-8"))
            if isinstance(idx, dict):
                return idx
    except Exception:
        pass
    return {}


def series_for_event(event_name: str, regatta_id: str, idx: Optional[dict] = None) -> dict:
    idx = idx if idx is not None else load_catalogue_index()
    key = _canon_series_key(f"{event_name} {regatta_id}")
    row = idx.get(key)
    if not row:
        # try name only
        row = idx.get(_canon_series_key(event_name or ""))
    if not row:
        for k, v in idx.items():
            if key and (key == k or key in k or k in key):
                row = v
                break
    if not isinstance(row, dict):
        return {}
    slug = str(row.get("slug") or "").strip()
    href = str(row.get("url") or "").strip()
    if slug and not href.startswith("/events-logos/"):
        href = f"/events-logos/{slug}"
    return {
        "label": str(row.get("label") or "").strip(),
        "href": href,
        "logo": str(row.get("path") or "").strip(),
        "slug": slug,
        "regattas": row.get("regattas") if isinstance(row.get("regattas"), list) else [],
    }


def history_sentence(series_name: str, editions: list[dict], *, current_year: Optional[int] = None) -> str:
    """Neutral archive count. Missing years = unknown, not 'not held' / not owned."""
    years = sorted({int(e["year"]) for e in editions if e.get("year")})
    if current_year:
        years = [y for y in years if y != int(current_year)]
    if not years:
        return ""
    n = len(years) + (1 if current_year else 0)
    lo, hi = min(years), max(years)
    if current_year:
        hi = max(hi, int(current_year))
        lo = min(lo, int(current_year))
    return f"Results on record: {n} edition{'s' if n != 1 else ''} from {lo}–{hi}"


def results_cta_label(state: str, scored_races: int = 0, result_status: str = "") -> str:
    """Entries are not results. Date alone is not final."""
    status = (result_status or "").strip().lower()
    scored = int(scored_races or 0)
    st = (state or "").strip().lower()
    if status == "final" or st == "final":
        return "FULL RESULTS"
    if st == "live":
        return "LIVE RESULTS"
    if scored > 0 and st in {"provisional", "historical"}:
        return "PARTIAL RESULTS"
    if st == "upcoming" and scored == 0:
        return ""
    if scored > 0:
        return "PARTIAL RESULTS"
    return ""


def _inline_logo(src: str, alt: str = "") -> str:
    if not src:
        return ""
    return (
        f'<img class="landing-event-inline-logo" src="{html_module.escape(src, quote=True)}" '
        f'alt="{html_module.escape(alt, quote=True)}" '
        f'width="18" height="14" loading="lazy" decoding="async">'
    )


_FEATURE_NATIONAL = re.compile(r"\b(nationals?|championships?|champs?)\b", re.I)
_FEATURE_CUP = re.compile(r"\b(cup|open|week)\b", re.I)
_RADIO_LOCAL = re.compile(r"\b(df95|dragon\s*force|iom)\b", re.I)
HERO2_WINDOW_DAYS = 14
HERO2_MIN_SCORE = 30


def feature_score(row: dict, *, series: Optional[dict] = None) -> int:
    """Named / championship events outrank local same-club radio sailing."""
    name = str(row.get("event_name") or "")
    score = 0
    if series and series.get("slug"):
        score += 100
    if _FEATURE_NATIONAL.search(name):
        score += 80
    elif _FEATURE_CUP.search(name):
        score += 35
    start = _as_date(row.get("start_date"))
    end = _as_date(row.get("end_date")) or start
    if start and end and end > start:
        score += 15
    if _RADIO_LOCAL.search(name) and not _FEATURE_NATIONAL.search(name):
        score -= 60
    return score


def select_hero_events(
    rows: list[dict],
    *,
    today: Optional[date] = None,
    catalogue: Optional[dict] = None,
) -> tuple[Optional[dict], Optional[dict]]:
    """Hero 1 = nearest Upcoming/Live. Hero 2 = next relevant event in 14 days.

    Relevance is named-series / nationals / cup — not same-club date order.
    Same /regatta/{id} forever. No hard-coded event IDs.
    """
    today = today or date.today()
    idx = catalogue if catalogue is not None else {}
    usable = []
    for r in rows:
        rid = str(r.get("regatta_id") or "").strip()
        if not _public_rid(rid):
            continue
        st = (str(r.get("result_status") or "")).strip().lower()
        if st in _SKIP_STATUS:
            continue
        start = _as_date(r.get("start_date"))
        end = _as_date(r.get("end_date")) or start
        if not start:
            continue
        if end and end < today and start < today:
            continue
        usable.append(r)
    usable.sort(key=lambda r: (_as_date(r.get("start_date")) or date.max, str(r.get("regatta_id"))))
    hero1 = usable[0] if usable else None

    def _score(r: dict) -> int:
        ser = series_for_event(str(r.get("event_name") or ""), str(r.get("regatta_id") or ""), idx)
        return feature_score(r, series=ser)

    hero2 = None
    if hero1:
        h1_id = hero1.get("regatta_id")
        rest = [r for r in usable if r.get("regatta_id") != h1_id]
        window = []
        for r in rest:
            sd = _as_date(r.get("start_date"))
            if not sd:
                continue
            if 0 <= (sd - today).days <= HERO2_WINDOW_DAYS:
                window.append(r)
        if window:
            best = max(
                window,
                key=lambda r: (_score(r), _as_date(r.get("start_date")) or date.min, str(r.get("regatta_id"))),
            )
            if _score(best) >= HERO2_MIN_SCORE:
                hero2 = best
        if hero2 is None and rest:
            ranked = sorted(
                rest,
                key=lambda r: (-_score(r), _as_date(r.get("start_date")) or date.max, str(r.get("regatta_id"))),
            )
            if _score(ranked[0]) >= HERO2_MIN_SCORE:
                hero2 = ranked[0]
            else:
                hero2 = rest[0]
    return hero1, hero2


def _esc(s: str) -> str:
    return html_module.escape(s or "", quote=True)


def _esc_text(s: str) -> str:
    return html_module.escape(s or "")


_CLASS_LOGO = {
    "420": "/artwork/Class Logo/420-Class-Logo.png",
    "29er": "/artwork/Class Logo/29er-Class-Logo.png",
    "hunter 19": "/artwork/Class Logo/Hunter-19-Class-Logo.png",
    "hobie 16": "/artwork/Class Logo/Hobie-16-Class-Logo.png",
    "hobie 14": "/artwork/Class Logo/Hobie-14-Class-Logo.png",
    "df95": "/artwork/Class Logo/DF95-Class-Logo.png",
    "j22": "/artwork/Class Logo/J22-Class-Logo.png",
    "ilca 6": "/artwork/Class Logo/ILCA-6-Class-Logo.png",
    "ilca 7": "/artwork/Class Logo/ILCA-7-Class-Logo.png",
    "ilca 4": "/artwork/Class Logo/ILCA-4.7-Class-Logo.png",
    "optimist": "/artwork/Class Logo/Optimist-Class-Logo.png",
}


def class_logo_src(name: str) -> str:
    key = re.sub(r"\s+", " ", (name or "").strip().lower())
    key = re.sub(r"\s+(fleet|class)$", "", key).strip()
    return _CLASS_LOGO.get(key, "")


def infer_classes(name: str, classes: list[str]) -> list[str]:
    if classes:
        return list(classes)
    m = re.match(r"^(\d{2,4}(?:er)?)\b", (name or "").strip(), re.I)
    return [m.group(1)] if m else []


def _class_anchor(name: str) -> str:
    href = _class_href(name)
    if href:
        return f'<a href="{_esc(href)}">{_esc_text(name)}</a>'
    return _esc_text(name)


def build_facts_html(card: dict) -> str:
    """Date · entries line used by the existing All Regattas meta pills."""
    url = card.get("url") or ""
    dates = card.get("dates") or ""
    entries = int(card.get("entries") or 0)
    bits = []
    if dates and url:
        bits.append(f'<a href="{_esc(url)}">{_esc_text(dates)}</a>')
    elif dates:
        bits.append(_esc_text(dates))
    bits.append(f"{entries} Entries")
    return " · ".join(bits)


def build_story_html(card: dict) -> str:
    """Additive history/podium only. Never repeat name/date/host/entries already on the card."""
    series = card.get("series") or {}
    history = (card.get("history") or "").strip()
    if "held by SailingSA" in history or "SailingSA holds" in history:
        history = ""
    if history.startswith("According to results"):
        history = ""
    series_label = (series.get("label") or "").strip()
    series_href = (series.get("href") or "").strip()
    logo = card.get("class_logo") or card.get("logo") or series.get("logo") or ""
    prevs = [
        p
        for p in (card.get("previous") or [])
        if str(p.get("url") or "").startswith("/regatta/") and p.get("year")
    ]
    prevs.sort(key=lambda p: int(p.get("year") or 0), reverse=True)
    bits = []
    if history or (series_href and series_label) or prevs:
        head = []
        if series_label and series_href:
            head.append(
                f'<a href="{_esc(series_href)}">{_inline_logo(logo, series_label)}'
                f"{_esc_text(series_label)}</a>"
            )
        if history:
            head.append(_esc_text(history))
        if prevs:
            p = prevs[0]
            head.append(
                f'Previous: <a href="{_esc(p["url"])}">{_esc_text(str(p["year"]))}</a>'
            )
        if head:
            bits.append(" · ".join(head))
    podium = [x for x in (card.get("podium") or []) if x.get("name") and x.get("place")]
    if podium and prevs:
        p = prevs[0]
        names = []
        for row in sorted(podium, key=lambda r: int(r.get("place") or 99))[:3]:
            place = int(row["place"])
            label = {1: "1st", 2: "2nd", 3: "3rd"}.get(place, str(place))
            nm = _esc_text(str(row["name"]))
            href = str(row.get("href") or "").strip()
            if href.startswith("/sailor/"):
                names.append(f'{label} <a href="{_esc(href)}">{nm}</a>')
            else:
                names.append(f"{label} {nm}")
        if names:
            bits.append(
                f'{_inline_logo(logo, series_label or "Results")}'
                f'<a href="{_esc(p["url"])}">{_esc_text(str(p["year"]))} Results</a>'
                f' · {" · ".join(names)}'
            )
    returning = (card.get("returning") or "").strip()
    if returning:
        bits.append(returning)
    return " ".join(b.strip() for b in bits if b and b.strip()).strip()


_ICO_CAL = (
    '<svg viewBox="0 0 16 16" aria-hidden="true" focusable="false" width="14" height="14" '
    'fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
    '<rect x="2.25" y="3.5" width="11.5" height="9.5" rx="1.4"></rect>'
    '<line x1="2.25" y1="6" x2="13.75" y2="6"></line>'
    '<line x1="5" y1="2.25" x2="5" y2="4.75"></line>'
    '<line x1="11" y1="2.25" x2="11" y2="4.75"></line></svg>'
)
_ICO_USERS = (
    '<svg viewBox="0 0 16 16" aria-hidden="true" focusable="false" width="14" height="14" '
    'fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
    '<circle cx="6" cy="5.5" r="2.1"></circle><circle cx="10.5" cy="6.2" r="1.8"></circle>'
    '<path d="M2.7 12.4c.45-1.9 2.05-3 4.2-3 2.15 0 3.75 1.1 4.2 3"></path>'
    '<path d="M9.4 11.8c.35-1.2 1.35-1.95 2.7-1.95 1.05 0 1.95.45 2.5 1.25"></path></svg>'
)
_ICO_TROPHY = (
    '<svg viewBox="0 0 16 16" aria-hidden="true" focusable="false" width="14" height="14" '
    'fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M5 2.5h6v1.8c0 2.3-1.4 4-3 4.6v2h2v1.6H6V10.9h2v-2c-1.6-.6-3-2.3-3-4.6V2.5Z"></path>'
    '<path d="M5 3.4H3.2c0 1.7.7 2.9 2.1 3.4"></path>'
    '<path d="M11 3.4h1.8c0 1.7-.7 2.9-2.1 3.4"></path></svg>'
)


def render_card_html(card: dict, *, slot: int) -> str:
    """Same All Regattas `.sa-home-regatta-card` shell, plus countdown + story."""
    url = card.get("url") or ""
    logo = card.get("logo") or ""
    count = card.get("countdown") or ""
    title = card.get("name") or "Event"
    state = card.get("state") or "upcoming"
    dates = card.get("dates") or ""
    entries = int(card.get("entries") or 0)
    host_code = (card.get("host_short") or "").strip().upper()
    host_name = (card.get("host_full") or card.get("host") or "").strip()
    if host_code and host_name.upper().startswith(host_code + " -"):
        host_name = host_name.split(" - ", 1)[-1].strip()
    host_href = card.get("host_href") or ""
    host_logo = card.get("host_logo") or (f"/api/club-logo/{host_code}" if host_code else "")
    class_name = (card.get("classes") or [""])[0] if card.get("classes") else ""
    class_logo = card.get("class_logo") or class_logo_src(class_name)
    class_href = _class_href(class_name) if class_name else url
    if state == "live" and count and not count.startswith("LIVE"):
        count = f"LIVE · {count}"
    story = build_story_html(card)
    scored = int(card.get("scored_races") or 0)
    if state == "upcoming":
        scored = 0
    cta = results_cta_label(state, scored, card.get("result_status") or "")
    modifier = "upcoming"
    if state == "live" or (count or "").startswith("LIVE"):
        modifier = "live"
    elif state == "final" or count == "FINAL RESULTS" or cta == "FULL RESULTS":
        modifier = "final"
    tint = " sa-home-regatta-card--live" if modifier == "live" else ""
    logo_href = (card.get("series") or {}).get("href") or url
    event_logo = ""
    if logo:
        event_logo = (
            f'<a class="sa-home-regatta-event-logo-link" href="{_esc(logo_href)}" '
            f'aria-label="{_esc(title)}">'
            f'<img class="sa-home-regatta-event-logo" src="{_esc(logo)}" alt="{_esc(title)}" '
            f'width="78" height="58" loading="lazy" decoding="async"></a>'
        )
    else:
        event_logo = (
            f'<a class="sa-home-regatta-event-logo-link" href="{_esc(url)}" '
            f'aria-label="{_esc(title)}"></a>'
        )
    count_html = (
        f'<p class="landing-event-card-count">{_esc_text(count)}</p>' if count else ""
    )
    date_html = _esc_text(dates)
    host_tag = "a" if host_href else "div"
    host_attrs = f' href="{_esc(host_href)}" title="Open club page"' if host_href else ""
    host_img = (
        f'<img class="sa-home-regatta-host-logo" src="{_esc(host_logo)}" alt="" '
        f'width="76" height="36" loading="lazy" decoding="async">'
        if host_logo
        else ""
    )
    class_block = ""
    if class_logo:
        class_block = (
            f'<a class="sa-home-regatta-single-class" href="{_esc(class_href)}" '
            f'title="{_esc(class_name)}" aria-label="{_esc(class_name)}">'
            f'<img class="sa-home-regatta-chip-logo" src="{_esc(class_logo)}" alt="{_esc(class_name)}" '
            f'width="46" height="24" loading="lazy" decoding="async"></a>'
        )
    elif class_name:
        class_block = (
            f'<a class="sa-home-regatta-single-class" href="{_esc(class_href)}">'
            f'<span class="sa-home-regatta-chip-text">{_esc_text(class_name)}</span></a>'
        )
    cta_html = (
        f'<a class="sa-home-regatta-btn" href="{_esc(url)}">'
        f'<span class="sa-home-regatta-btn-ico">{_ICO_TROPHY}</span>{_esc_text(cta)}</a>'
        if cta
        else ""
    )
    story_html = ""
    if story:
        story_html = (
            f'<div class="sa-home-regatta-children landing-event-card-story-wrap">'
            f'<div class="sa-home-regatta-children-head">'
            f'<p class="landing-event-card-story">{story}</p>'
            f"</div></div>"
        )
    return (
        f'<article class="sa-home-regatta-card landing-event-card landing-event-card--{modifier}{tint}" '
        f'data-landing-event-slot="{int(slot)}" data-state="{_esc(modifier)}">'
        f'<div class="sa-home-regatta-top">'
        f"{event_logo}"
        f'<div class="sa-home-regatta-top-main">'
        f"{count_html}"
        f'<div class="sa-home-regatta-title">'
        f'<a href="{_esc(url)}" style="color:inherit;text-decoration:none">{_esc_text(title)}</a>'
        f"</div>"
        f'<div class="sa-home-regatta-meta">'
        f'<div class="sa-home-regatta-meta-pill"><span class="sa-home-regatta-meta-ico">{_ICO_CAL}</span>{date_html}</div>'
        f'<div class="sa-home-regatta-meta-pill"><span class="sa-home-regatta-meta-ico">{_ICO_USERS}</span>{entries} Entries</div>'
        f"</div></div>"
        f'<{host_tag} class="sa-home-regatta-host"{host_attrs}>'
        f"{host_img}"
        f'<div class="sa-home-regatta-host-text">'
        f'<div class="sa-home-regatta-host-code">{_esc_text(host_code)}</div>'
        f'<div class="sa-home-regatta-host-name">{_esc_text(host_name)}</div>'
        f"</div></{host_tag}>"
        f'<div class="sa-home-regatta-actions">{class_block}'
        f'{cta_html}'
        f"</div></div>"
        f"{story_html}"
        f'<a class="landing-event-card-hit" href="{_esc(url)}" tabindex="-1" aria-hidden="true"></a>'
        f"</article>"
    )


LANDING_CARD_CSS = """
/* Hero slots reuse All Regattas `.sa-home-regatta-card` tokens exactly. */
.temp-landing-hero-image,
.temp-landing-secondary-image {
    width: 100%;
    max-width: 100%;
    margin-left: 0;
    margin-right: 0;
    padding-left: 0;
    padding-right: 0;
    box-sizing: border-box;
}
.temp-landing-hero-image .sa-home-regatta-card,
.temp-landing-secondary-image .sa-home-regatta-card {
    background: #fff;
    border: 2px solid #8aa2c6;
    border-radius: 6px;
    box-shadow: 0 2px 3px rgba(15,23,42,.06);
    padding: 10px 12px 10px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    overflow: hidden;
    box-sizing: border-box;
    width: 100%;
    max-width: 100%;
    margin: 0;
    color: #142c78;
    position: relative;
}
.temp-landing-hero-image .sa-home-regatta-card--live,
.temp-landing-secondary-image .sa-home-regatta-card--live {
    background: #fff1e6;
    border-color: #f5ac86;
}
.temp-landing-hero-image .sa-home-regatta-top,
.temp-landing-secondary-image .sa-home-regatta-top {
    display: grid;
    grid-template-columns: 104px minmax(0,1fr) minmax(200px,252px) auto;
    grid-template-areas: "logo main host actions";
    gap: 14px;
    align-items: center;
}
.temp-landing-hero-image .sa-home-regatta-event-logo-link,
.temp-landing-secondary-image .sa-home-regatta-event-logo-link {
    grid-area: logo;
    display: flex;
    align-items: center;
    justify-content: flex-start;
    text-decoration: none;
    line-height: 0;
    min-width: 0;
}
.temp-landing-hero-image .sa-home-regatta-event-logo,
.temp-landing-secondary-image .sa-home-regatta-event-logo {
    display: block;
    width: 96px;
    height: 68px;
    max-width: 96px;
    max-height: 68px;
    object-fit: contain;
    object-position: center;
    border: none;
    background: transparent;
    padding: 0;
}
.temp-landing-hero-image .sa-home-regatta-top-main,
.temp-landing-secondary-image .sa-home-regatta-top-main { grid-area: main; min-width: 0; }
.temp-landing-hero-image .sa-home-regatta-title,
.temp-landing-secondary-image .sa-home-regatta-title {
    font-size: 15px;
    font-weight: 900;
    color: #142c78;
    line-height: 1.15;
    margin: 0;
    letter-spacing: -.01em;
}
.temp-landing-hero-image .sa-home-regatta-meta,
.temp-landing-secondary-image .sa-home-regatta-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    color: #5b6780;
    font-size: 11.5px;
    margin-top: 6px;
}
.temp-landing-hero-image .sa-home-regatta-meta-pill,
.temp-landing-secondary-image .sa-home-regatta-meta-pill {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-weight: 700;
    white-space: nowrap;
    position: relative;
}
.temp-landing-hero-image .sa-home-regatta-meta-pill + .sa-home-regatta-meta-pill,
.temp-landing-secondary-image .sa-home-regatta-meta-pill + .sa-home-regatta-meta-pill { padding-left: 10px; }
.temp-landing-hero-image .sa-home-regatta-meta-pill + .sa-home-regatta-meta-pill:before,
.temp-landing-secondary-image .sa-home-regatta-meta-pill + .sa-home-regatta-meta-pill:before {
    content: "";
    position: absolute;
    left: 0; top: 2px; bottom: 2px;
    width: 1px;
    background: #cbd5e1;
}
.temp-landing-hero-image .sa-home-regatta-meta-ico,
.temp-landing-secondary-image .sa-home-regatta-meta-ico {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 13px;
    height: 13px;
    color: #60708b;
}
.temp-landing-hero-image .sa-home-regatta-host,
.temp-landing-secondary-image .sa-home-regatta-host {
    grid-area: host;
    display: flex;
    align-items: center;
    gap: 10px;
    min-width: 0;
    color: inherit;
    text-decoration: none;
}
.temp-landing-hero-image .sa-home-regatta-host-logo,
.temp-landing-secondary-image .sa-home-regatta-host-logo {
    display: block;
    width: 84px;
    height: 44px;
    object-fit: contain;
    background: transparent;
    flex: 0 0 auto;
    padding: 0;
}
.temp-landing-hero-image .sa-home-regatta-host-text,
.temp-landing-secondary-image .sa-home-regatta-host-text {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
}
.temp-landing-hero-image .sa-home-regatta-host-code,
.temp-landing-secondary-image .sa-home-regatta-host-code {
    font-weight: 900;
    color: #21356b;
    font-size: 14px;
    line-height: 1.05;
}
.temp-landing-hero-image .sa-home-regatta-host-name,
.temp-landing-secondary-image .sa-home-regatta-host-name {
    color: #475569;
    font-size: 11px;
    line-height: 1.15;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 260px;
}
.temp-landing-hero-image .sa-home-regatta-actions,
.temp-landing-secondary-image .sa-home-regatta-actions {
    grid-area: actions;
    display: flex;
    gap: 8px;
    align-items: center;
    justify-content: flex-end;
}
.temp-landing-hero-image .sa-home-regatta-single-class,
.temp-landing-secondary-image .sa-home-regatta-single-class {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    line-height: 0;
    text-decoration: none;
}
.temp-landing-hero-image .sa-home-regatta-chip-logo,
.temp-landing-secondary-image .sa-home-regatta-chip-logo {
    display: block;
    width: 52px;
    height: 28px;
    max-width: 52px;
    object-fit: contain;
    background: transparent;
    padding: 0;
}
.temp-landing-hero-image .sa-home-regatta-btn,
.temp-landing-secondary-image .sa-home-regatta-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 7px;
    padding: 9px 14px;
    border-radius: 6px;
    border: 1px solid #a5d7de;
    background: #f9ffff;
    color: #0f6d7a;
    font-weight: 900;
    font-size: 12px;
    text-decoration: none;
    white-space: nowrap;
    min-width: 126px;
}
.temp-landing-hero-image .sa-home-regatta-children,
.temp-landing-secondary-image .sa-home-regatta-children {
    margin: 0;
    border: 1px solid #dbe3ef;
    border-radius: 4px;
    background: #fff;
    overflow: hidden;
}
.temp-landing-hero-image .sa-home-regatta-children-head,
.temp-landing-secondary-image .sa-home-regatta-children-head {
    display: block;
    padding: 8px 12px;
    background: #eff5ff;
}
.landing-event-card-count {
    display: inline-block;
    margin: 0 0 4px;
    padding: 2px 6px;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: .04em;
    text-transform: uppercase;
    line-height: 1.2;
    color: #142c78;
    background: #e8eef8;
    border: 1px solid #8aa2c6;
    border-radius: 4px;
}
.landing-event-card--live .landing-event-card-count {
    background: #fff1e6;
    border-color: #f5ac86;
    color: #9a3412;
}
.landing-event-card-story {
    margin: 0;
    font-size: 11px;
    font-weight: 700;
    color: #334155;
    line-height: 1.35;
    white-space: normal;
}
.landing-event-card-story a { color: #0b3d91; }
.landing-event-inline-logo {
    display: inline-block;
    width: 18px;
    height: 14px;
    object-fit: contain;
    vertical-align: -2px;
    margin-right: 3px;
}
.landing-event-card-hit {
    position: absolute;
    inset: 0;
    z-index: 0;
}
.temp-landing-hero-image .landing-event-card a:not(.landing-event-card-hit),
.temp-landing-secondary-image .landing-event-card a:not(.landing-event-card-hit) {
    position: relative;
    z-index: 1;
}
@media (max-width: 480px) {
    .temp-landing-hero-image .sa-home-regatta-card,
    .temp-landing-secondary-image .sa-home-regatta-card { padding: 10px 10px 10px; border-radius: 6px; }
    .temp-landing-hero-image .sa-home-regatta-top,
    .temp-landing-secondary-image .sa-home-regatta-top {
        grid-template-columns: 82px minmax(0,1fr);
        grid-template-areas: "logo main" "logo host" "actions actions";
        gap: 8px 10px;
        align-items: start;
    }
    .temp-landing-hero-image .sa-home-regatta-event-logo,
    .temp-landing-secondary-image .sa-home-regatta-event-logo {
        width: 78px; max-width: 78px; height: 58px; max-height: 58px;
    }
    .temp-landing-hero-image .sa-home-regatta-title,
    .temp-landing-secondary-image .sa-home-regatta-title { font-size: 14px; }
    .temp-landing-hero-image .sa-home-regatta-host,
    .temp-landing-secondary-image .sa-home-regatta-host { gap: 8px; }
    .temp-landing-hero-image .sa-home-regatta-host-logo,
    .temp-landing-secondary-image .sa-home-regatta-host-logo { width: 76px; height: 36px; }
    .temp-landing-hero-image .sa-home-regatta-actions,
    .temp-landing-secondary-image .sa-home-regatta-actions { width: 100%; justify-content: flex-end; }
    .temp-landing-hero-image .sa-home-regatta-btn,
    .temp-landing-secondary-image .sa-home-regatta-btn { flex: 1; min-width: 0; padding: 9px 10px; }
    .temp-landing-hero-image .sa-home-regatta-chip-logo,
    .temp-landing-secondary-image .sa-home-regatta-chip-logo { width: 46px; height: 24px; max-width: 46px; }
}
"""


def fetch_hero_candidates(cur, *, today: Optional[date] = None) -> list[dict]:
    today = today or date.today()
    cur.execute(
        """
        SELECT r.regatta_id, r.event_name, r.start_date, r.end_date, r.result_status,
               r.as_at_time, r.host_club_id,
               TRIM(COALESCE(c.club_abbrev, '')) AS club_abbrev,
               TRIM(COALESCE(c.club_fullname, '')) AS club_fullname,
               e.event_status
        FROM regattas r
        LEFT JOIN clubs c ON c.club_id = r.host_club_id
        LEFT JOIN LATERAL (
            SELECT event_status FROM events ev
            WHERE ev.regatta_id = r.regatta_id
            ORDER BY ev.event_id DESC LIMIT 1
        ) e ON TRUE
        WHERE r.regatta_id IS NOT NULL
          AND BTRIM(r.regatta_id::text) <> ''
          AND r.event_name IS NOT NULL
          AND BTRIM(r.event_name) <> ''
          AND COALESCE(r.end_date, r.start_date) >= %s
        ORDER BY r.start_date NULLS LAST
        """,
        (today,),
    )
    return [dict(r) for r in (cur.fetchall() or [])]


def fetch_fleet_entry_counts(cur, regatta_id: str) -> list[tuple[str, int]]:
    cur.execute(
        """
        SELECT COALESCE(
                 NULLIF(BTRIM(rb.class_canonical), ''),
                 NULLIF(BTRIM(rb.class_original), ''),
                 NULLIF(BTRIM(rb.fleet_label), ''),
                 'Fleet'
               ) AS fleet,
               COUNT(res.result_id)::int AS n
        FROM regatta_blocks rb
        LEFT JOIN results res
          ON res.block_id = rb.block_id AND res.regatta_id = rb.regatta_id
        WHERE rb.regatta_id = %s
        GROUP BY 1
        ORDER BY 1
        """,
        (regatta_id,),
    )
    out = []
    for r in cur.fetchall() or []:
        n = int(r.get("n") or 0)
        if n:
            out.append((str(r.get("fleet") or "Fleet"), n))
    if out:
        return out
    cur.execute("SELECT COUNT(*)::int AS n FROM results WHERE regatta_id = %s", (regatta_id,))
    n = int((cur.fetchone() or {}).get("n") or 0)
    return [("Event", n)] if n else []


def _results_columns(cur) -> set[str]:
    try:
        cur.execute(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'results'
            """
        )
        out = set()
        for r in cur.fetchall() or []:
            out.add(str(r.get("column_name") if isinstance(r, dict) else r[0]).lower())
        return out
    except Exception:
        return set()


def fetch_overall_podium(cur, regatta_id: str) -> list[dict]:
    """Top 3 overall only when place + identity columns exist. No name guessing."""
    if cur is None or not regatta_id:
        return []
    cols = _results_columns(cur)
    place = next((c for c in ("place", "position", "rank", "overall_place") if c in cols), "")
    name = next((c for c in ("sailor_name", "helm_name", "helm", "name") if c in cols), "")
    slug = next((c for c in ("sailor_slug", "helm_slug") if c in cols), "")
    sid = next((c for c in ("sailor_id", "helm_sailor_id") if c in cols), "")
    if not place or not name:
        return []
    extra = f", {sid} AS sailor_id" if sid else ", NULL::text AS sailor_id"
    extra += f", {slug} AS sailor_slug" if slug else ", NULL::text AS sailor_slug"
    try:
        cur.execute(
            f"""
            SELECT {place}::int AS place, BTRIM({name}::text) AS name
                   {extra}
            FROM results
            WHERE regatta_id = %s
              AND {place} IS NOT NULL
              AND {place}::int BETWEEN 1 AND 3
              AND BTRIM(COALESCE({name}::text, '')) <> ''
            ORDER BY {place}::int
            LIMIT 12
            """,
            (regatta_id,),
        )
    except Exception:
        try:
            cur.connection.rollback()
        except Exception:
            pass
        return []
    seen = set()
    out = []
    for r in cur.fetchall() or []:
        pl = int(r.get("place") or 0)
        if pl not in (1, 2, 3) or pl in seen:
            continue
        seen.add(pl)
        sl = str(r.get("sailor_slug") or "").strip()
        href = f"/sailor/{sl}" if sl and "/" not in sl and " " not in sl else ""
        out.append(
            {
                "place": pl,
                "name": str(r.get("name") or "").strip(),
                "href": href,
                "sailor_id": str(r.get("sailor_id") or "").strip(),
            }
        )
    return out


def fetch_current_sailor_ids(cur, regatta_id: str) -> set[str]:
    if cur is None or not regatta_id:
        return set()
    cols = _results_columns(cur)
    sid = next((c for c in ("sailor_id", "helm_sailor_id") if c in cols), "")
    if not sid:
        return set()
    try:
        cur.execute(
            f"SELECT DISTINCT {sid}::text AS sailor_id FROM results WHERE regatta_id = %s AND {sid} IS NOT NULL",
            (regatta_id,),
        )
        return {str(r.get("sailor_id") or "").strip() for r in (cur.fetchall() or []) if str(r.get("sailor_id") or "").strip()}
    except Exception:
        try:
            cur.connection.rollback()
        except Exception:
            pass
        return set()


def returning_line(podium: list[dict], current_ids: set[str]) -> str:
    """Only when the same sailor_id appears in previous podium and current entries."""
    if not podium or not current_ids:
        return ""
    winner = next((p for p in podium if int(p.get("place") or 0) == 1), None)
    if winner:
        wid = str(winner.get("sailor_id") or "").strip()
        if wid and wid in current_ids and winner.get("name"):
            href = str(winner.get("href") or "").strip()
            nm = html_module.escape(winner["name"])
            if href.startswith("/sailor/"):
                return f'Defending winner <a href="{html_module.escape(href, quote=True)}">{nm}</a> returns'
            return f"Defending winner {nm} returns"
    names = []
    for p in podium:
        pid = str(p.get("sailor_id") or "").strip()
        if not pid or pid not in current_ids or not p.get("name"):
            continue
        href = str(p.get("href") or "").strip()
        nm = html_module.escape(p["name"])
        if href.startswith("/sailor/"):
            names.append(f'<a href="{html_module.escape(href, quote=True)}">{nm}</a> returns in 2026')
        else:
            names.append(f"{nm} returns in 2026")
    return names[0] if names else ""


def card_from_row(row: dict, *, cur=None, today: Optional[date] = None, idx: Optional[dict] = None) -> dict:
    today = today or date.today()
    rid = str(row.get("regatta_id") or "").strip()
    name = str(row.get("event_name") or "").strip() or rid
    start, end = row.get("start_date"), row.get("end_date")
    host_ab = str(row.get("club_abbrev") or "").strip()
    host_fn = str(row.get("club_fullname") or "").strip()
    host = f"{host_ab} - {host_fn}" if host_ab and host_fn else (host_fn or host_ab)
    host_short = host_ab or host_fn
    fleet_counts = fetch_fleet_entry_counts(cur, rid) if cur is not None else []
    classes = infer_classes(
        name, [n for n, _c in fleet_counts if n.lower() not in {"fleet", "event"}]
    )
    series = series_for_event(name, rid, idx)
    prev = _editions_from_series(series, rid)
    if not prev and cur is not None and series.get("slug"):
        prev = _previous_editions_from_catalogue(series.get("slug") or "", rid)
    history = history_sentence(series.get("label") or name, prev, current_year=(_as_date(start) or today).year)
    class_logo = class_logo_src(classes[0]) if classes else ""
    logo = series.get("logo") or class_logo or ""
    host_logo = f"/api/club-logo/{host_ab}" if host_ab else ""
    prev_kept = [p for p in prev if p.get("url") and p.get("url") != f"/regatta/{rid}"]
    podium = []
    returning = ""
    if cur is not None and prev_kept:
        prev_kept.sort(key=lambda p: int(p.get("year") or 0), reverse=True)
        prev_rid = str(prev_kept[0].get("url") or "").rstrip("/").split("/")[-1]
        podium = fetch_overall_podium(cur, prev_rid)
        returning = returning_line(podium, fetch_current_sailor_ids(cur, rid))
    state = derive_event_lifecycle(
        start_date=start,
        end_date=end,
        result_status=row.get("result_status"),
        as_at_time=row.get("as_at_time"),
        raced_count=sum(n for _n, n in fleet_counts),
        today=today,
    )
    scored = 0 if state == "upcoming" else sum(n for _n, n in fleet_counts)
    return {
        "regatta_id": rid,
        "name": name,
        "url": f"/regatta/{rid}",
        "dates": compact_event_date_range(start, end),
        "start_date": start,
        "end_date": end,
        "host": host,
        "host_short": host_short,
        "host_full": host_fn,
        "host_href": _club_href(host_ab, host_fn),
        "host_logo": host_logo,
        "classes": classes,
        "class_logo": class_logo,
        "entries": sum(n for _n, n in fleet_counts),
        "fleet_counts": fleet_counts,
        "series": series,
        "previous": prev_kept,
        "history": history,
        "logo": logo,
        "podium": podium,
        "returning": returning,
        "scored_races": scored,
        "result_status": row.get("result_status") or "",
        "countdown": countdown_label(
            start, end, today=today, as_at_time=row.get("as_at_time"), result_status=row.get("result_status") or ""
        ),
        "state": state,
    }


def _editions_from_series(series: dict, current_rid: str) -> list[dict]:
    """Use on-disk catalogue editions — live HTTPS to the public API often hairpins out."""
    out = []
    for r in (series or {}).get("regattas") or []:
        if not isinstance(r, dict):
            continue
        url = str(r.get("url") or "").strip()
        year = r.get("year")
        rid = str(r.get("regatta_id") or "").strip()
        if not year:
            continue
        if rid and rid == current_rid:
            continue
        if not url.startswith("/regatta/"):
            continue
        out.append({"url": url, "year": year})
    return out


def _previous_editions_from_catalogue(slug: str, current_rid: str) -> list[dict]:
    if not slug:
        return []
    try:
        import urllib.request

        req = urllib.request.Request(
            f"https://sailingsa.co.za/api/events-logos/{slug}",
            headers={"User-Agent": "SailingSA-landing-cards"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8", "replace"))
    except Exception:
        return []
    out = []
    for r in data.get("regattas") or []:
        if not isinstance(r, dict):
            continue
        url = str(r.get("url") or "").strip()
        year = r.get("year")
        rid = str(r.get("regatta_id") or "").strip()
        if not url.startswith("/regatta/") or not year:
            continue
        if rid == current_rid:
            continue
        out.append({"url": url, "year": year})
    return out


def wrap_section(slot: int, inner: str, aria: str, section_id: str, section_class: str) -> str:
    return (
        f'<section id="{section_id}" class="{section_class}" aria-label="{_esc(aria)}" data-landing-event-card="1">\n'
        f"<!-- LANDING_EVENT_CARD_BEGIN slot={slot} -->\n"
        f"{inner}\n"
        f"<!-- LANDING_EVENT_CARD_END slot={slot} -->\n"
        f"</section>"
    )
