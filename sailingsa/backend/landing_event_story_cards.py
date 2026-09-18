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
    if not row.get("regattas"):
        slug_try = str(row.get("slug") or "").strip()
        if slug_try:
            for v in idx.values():
                if isinstance(v, dict) and str(v.get("slug") or "") == slug_try and v.get("regattas"):
                    row = v
                    break
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
        f'width="14" height="11" loading="lazy" decoding="async" '
        f'style="width:14px;height:11px;max-width:14px;max-height:11px;display:inline;'
        f'vertical-align:-2px;margin:0 3px 0 0">'
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


def _person_html(row: dict) -> str:
    nm = _esc_text(str(row.get("name") or "").strip())
    if not nm:
        return ""
    href = str(row.get("href") or "").strip()
    helm = f'<a href="{_esc(href)}">{nm}</a>' if href.startswith("/sailor/") else nm
    crew = str(row.get("crew_name") or "").strip()
    crew_href = str(row.get("crew_href") or "").strip()
    if crew:
        ch = (
            f'<a href="{_esc(crew_href)}">{_esc_text(crew)}</a>'
            if crew_href.startswith("/sailor/")
            else _esc_text(crew)
        )
        return f"{helm} / {ch}"
    return helm


def _fmt_nett(v: Any) -> str:
    if v is None or v == "":
        return ""
    try:
        f = float(v)
        if f == int(f):
            return str(int(f))
        return ("%s" % f).rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        return str(v).strip()


def _pts(v: Any) -> str:
    n = _fmt_nett(v)
    return f"{n} pts" if n else ""


def _n_scores(scores: Any) -> int:
    if isinstance(scores, dict):
        return len(scores)
    if isinstance(scores, list):
        return len(scores)
    return 0


def _mark(s: str) -> str:
    return f'<strong class="landing-event-story-mark">{s}</strong>'


def _story_icon(kind: str) -> str:
    svg = {"trophy": _ICO_TROPHY, "cal": _ICO_CAL, "trend": _ICO_TREND}.get(kind, _ICO_TROPHY)
    return svg.replace('width="14" height="14"', 'width="12" height="12"')


def _story_wrap(kind: str, title_html: str, body_html: str) -> str:
    head = (
        f'<span class="landing-event-story-ico">{_story_icon(kind)}</span>'
        f'<span class="landing-event-last-label">{title_html}</span>'
    )
    return (
        f'<span class="landing-event-last-head">{head}</span>'
        f'<span class="landing-event-last-podium">{body_html}</span>'
    )


def _podium_line(row: dict) -> str:
    person = _person_html(row)
    pts = _pts(row.get("nett"))
    if person and pts:
        return f"{person} — {_mark(pts)}"
    return person


def _third_verb(row: dict) -> str:
    return "were" if str(row.get("crew_name") or "").strip() else "was"


def _age_years(start: Any, ref: Any) -> float:
    s = _as_date(start)
    r = _as_date(ref)
    if not s or not r:
        return 99.0
    return max(0.0, (r - s).days / 365.25)


def _recency_weight(age_years: float) -> float:
    """Smooth exponential decay. Half-life 16 months — no anniversary cliff."""
    age = max(0.0, float(age_years))
    half_life = 16.0 / 12.0
    return 100.0 * (0.5 ** (age / half_life))


def _quality_bonus(rank: int, is_national: bool, is_regional: bool, wins: int, fleet_n: int) -> float:
    q = 0.0
    if is_national and rank == 1:
        q += 40
    elif is_national and rank <= 3:
        q += 30
    elif is_national and rank <= 8 and (fleet_n >= 8 or not fleet_n):
        q += 28
    elif is_regional and rank == 1:
        q += 22
    elif rank == 1:
        q += 20
    elif rank <= 3:
        q += 16
    q += min(max(wins, 0) * 3, 12)
    return min(q, 40.0)


def _previous_story_label(card: dict, prev: dict) -> str:
    upcoming = _as_date(card.get("start_date"))
    py = int(prev.get("year") or 0)
    cls = ""
    if card.get("classes"):
        cls = re.sub(r"\s+(fleet|class)$", "", str(card["classes"][0]), flags=re.I).strip()
    uy = upcoming.year if upcoming else None
    if uy and py and py == uy - 1:
        if cls:
            return f"Last year's {cls} Nationals"
        return "Last year's champions"
    if py and cls:
        return f"{py} {cls} Champions"
    if py:
        return f"{py} Champions"
    return "Champions"


def _sentence_count(html: str) -> int:
    text = re.sub(r"<[^>]+>", "", html or "")
    return len([p for p in re.split(r"(?<=[.!?])\s+", text.strip()) if p])


def build_previous_overall_story_html(card: dict) -> str:
    """Previous-edition overall championship. Every displayed score uses pts."""
    prevs = [
        p
        for p in (card.get("previous") or [])
        if str(p.get("url") or "").startswith("/regatta/") and p.get("year")
    ]
    prevs.sort(key=lambda p: int(p.get("year") or 0), reverse=True)
    podium = [x for x in (card.get("podium") or []) if x.get("name") and x.get("place")]
    podium = sorted(podium, key=lambda r: int(r.get("place") or 99))[:3]
    if not podium or not prevs:
        return ""
    prev = prevs[0]
    url = str(prev.get("url") or "").strip()
    first = podium[0]
    second = podium[1] if len(podium) > 1 else None
    third = podium[2] if len(podium) > 2 else None
    if int(first.get("place") or 0) != 1:
        return ""
    a = _person_html(first)
    b = _person_html(second) if second else ""
    c = _person_html(third) if third else ""
    p1 = _pts(first.get("nett"))
    p2 = _pts((second or {}).get("nett")) if second else ""
    p3 = _pts((third or {}).get("nett")) if third else ""
    label = _previous_story_label(card, prev)
    title = f'<a href="{_esc(url)}">{_esc_text(label)}</a>' if url else _esc_text(label)
    gap = None
    if first.get("nett") is not None and second is not None and second.get("nett") is not None:
        try:
            gap = abs(float(first.get("nett")) - float(second.get("nett")))
        except (TypeError, ValueError):
            gap = None
    wins, _s, _t = _score_places(first.get("race_scores"))
    races = int(first.get("races_sailed") or 0) or _n_scores(first.get("race_scores"))
    dominant = bool(races and wins >= max(3, (races + 1) // 2))
    body = ""
    if p1 and p2 and gap == 1:
        body = f"{a} won by a single point over {b} ({_mark(f'{p1} to {p2}')})."
        if c and p3:
            body += f" {c} finished 3rd on {_mark(p3)}."
    elif p1 and p2 and gap is not None and 0 < gap <= 2:
        pts_word = "point" if gap == 1 else "points"
        body = f"{a} won by {_fmt_nett(gap)} {pts_word} over {b} ({_mark(f'{p1} to {p2}')})."
        if c and p3:
            body += f" {c} finished 3rd on {_mark(p3)}."
    elif dominant and p1:
        body = f"{a} won on {_mark(p1)}, taking {wins} of {races} races."
        if b and p2:
            body += f" {b} {_third_verb(second)} 2nd on {_mark(p2)}."
        if c and p3:
            body += f" {c} {_third_verb(third)} 3rd on {_mark(p3)}."
    else:
        lines = [_podium_line(row) for row in podium if _podium_line(row)]
        if not lines:
            return ""
        body = " ".join(lines)
    returning = (card.get("returning") or "").strip()
    if returning and _sentence_count(body) < 2:
        body = f"{body} {returning}".strip()
    return _story_wrap("trophy", title, body)


def build_story_html(card: dict) -> str:
    """Editorial history only. Never dump current entries. Never mix category fleets."""
    overall = build_previous_overall_story_html(card)
    if overall:
        return overall
    form = (card.get("class_form_html") or "").strip()
    if form:
        return form
    return ""


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
_ICO_TREND = (
    '<svg viewBox="0 0 16 16" aria-hidden="true" focusable="false" width="14" height="14" '
    'fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
    '<polyline points="2.5,12 6,8.2 8.6,10 13.5,4"></polyline>'
    '<polyline points="9.8,4 13.5,4 13.5,7.6"></polyline></svg>'
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
            f'width="78" height="58" loading="lazy" decoding="async" '
            f'style="width:78px;height:58px;max-width:78px;max-height:58px;object-fit:contain"></a>'
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
        f'width="76" height="36" loading="lazy" decoding="async" '
        f'style="width:76px;height:36px;max-width:76px;max-height:36px;object-fit:contain">'
        if host_logo
        else ""
    )
    class_block = ""
    if class_logo:
        class_block = (
            f'<a class="sa-home-regatta-single-class" href="{_esc(class_href)}" '
            f'title="{_esc(class_name)}" aria-label="{_esc(class_name)}">'
            f'<img class="sa-home-regatta-chip-logo" src="{_esc(class_logo)}" alt="{_esc(class_name)}" '
            f'width="46" height="24" loading="lazy" decoding="async" '
            f'style="width:46px;height:24px;max-width:46px;max-height:24px;object-fit:contain"></a>'
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
        f'<span class="landing-event-card-open" aria-hidden="true">'
        f'<svg viewBox="0 0 16 16" width="12" height="12" fill="none" stroke="currentColor" '
        f'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        f'<path d="M6 3.5 11 8 6 12.5"></path></svg></span>'
        f'<a class="landing-event-card-hit" href="{_esc(url)}" tabindex="-1" aria-hidden="true"></a>'
        f"</article>"
    )


LANDING_CARD_CSS = """
/* Hero slots reuse All Regattas `.sa-home-regatta-card` tokens exactly. */
.temp-landing-hero-image,
.temp-landing-secondary-image,
#landing-event-hero-2 {
    width: 100%;
    max-width: 100%;
    margin-left: 0;
    margin-right: 0;
    padding-left: 0;
    padding-right: 0;
    box-sizing: border-box;
}
/* Hero 2 must stay visible even if a prior .temp-landing-secondary-image exists. */
#landing-event-hero-2 {
    display: block !important;
}
/* Banner-era `.temp-landing-*-image img { width:100%; display:block }` must not size the card. */
.temp-landing-hero-image .landing-event-card img:not(.landing-event-inline-logo),
.temp-landing-secondary-image .landing-event-card img:not(.landing-event-inline-logo),
#landing-event-hero-2 .landing-event-card img:not(.landing-event-inline-logo) {
    width: auto;
    height: auto;
    max-width: 78px;
}
.temp-landing-hero-image .sa-home-regatta-card,
.temp-landing-secondary-image .sa-home-regatta-card,
#landing-event-hero-2 .sa-home-regatta-card {
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
.temp-landing-secondary-image .sa-home-regatta-top,
#landing-event-hero-2 .sa-home-regatta-top {
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
.temp-landing-secondary-image .sa-home-regatta-event-logo,
#landing-event-hero-2 .sa-home-regatta-event-logo {
    display: block !important;
    width: 78px !important;
    height: 58px !important;
    max-width: 78px !important;
    max-height: 58px !important;
    object-fit: contain !important;
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
.temp-landing-secondary-image .sa-home-regatta-host-logo,
#landing-event-hero-2 .sa-home-regatta-host-logo {
    display: block !important;
    width: 76px !important;
    height: 36px !important;
    max-width: 76px !important;
    max-height: 36px !important;
    object-fit: contain !important;
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
.temp-landing-secondary-image .sa-home-regatta-chip-logo,
#landing-event-hero-2 .sa-home-regatta-chip-logo {
    display: block !important;
    width: 46px !important;
    height: 24px !important;
    max-width: 46px !important;
    max-height: 24px !important;
    object-fit: contain !important;
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
    font-weight: 600;
    color: #334155;
    line-height: 1.4;
    white-space: normal;
}
.landing-event-card-story a {
    color: #1e3a6e;
    font-weight: 800;
    text-decoration: underline;
    text-decoration-color: #94a3b8;
    text-underline-offset: 2px;
}
.landing-event-story-ico {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 12px;
    height: 12px;
    color: #64748b;
    flex: 0 0 12px;
}
.landing-event-story-ico svg {
    display: block;
    width: 12px;
    height: 12px;
}
.landing-event-last-label {
    color: #64748b;
}
.landing-event-story-mark {
    font-weight: 800;
    color: #142c78;
}
.temp-landing-hero-image .landing-event-inline-logo,
.temp-landing-secondary-image .landing-event-inline-logo,
#landing-event-hero-2 .landing-event-inline-logo,
.temp-landing-hero-image .landing-event-card-story img,
.temp-landing-secondary-image .landing-event-card-story img,
#landing-event-hero-2 .landing-event-card-story img,
.landing-event-inline-logo {
    display: inline !important;
    width: 14px !important;
    height: 11px !important;
    max-width: 14px !important;
    max-height: 11px !important;
    object-fit: contain !important;
    vertical-align: -2px;
    margin: 0 3px 0 0 !important;
    float: none !important;
}
.temp-landing-hero-image .landing-event-card-story-wrap,
.temp-landing-secondary-image .landing-event-card-story-wrap,
#landing-event-hero-2 .landing-event-card-story-wrap {
    flex: 0 0 auto;
}
.temp-landing-hero-image .landing-event-card-story-wrap .sa-home-regatta-children-head,
.temp-landing-secondary-image .landing-event-card-story-wrap .sa-home-regatta-children-head,
#landing-event-hero-2 .landing-event-card-story-wrap .sa-home-regatta-children-head {
    padding: 4px 22px 4px 8px;
    line-height: 1.2;
}
.landing-event-card-hit {
    position: absolute;
    inset: 0;
    z-index: 0;
}
.landing-event-card-open {
    position: absolute;
    right: 8px;
    bottom: 6px;
    z-index: 2;
    pointer-events: none;
    color: #3d5a8a;
    line-height: 0;
}
.landing-event-last-head,
.landing-event-last-podium,
.landing-event-return {
    display: block;
    margin: 0;
}
.landing-event-last-head {
    display: flex;
    align-items: center;
    gap: 5px;
    font-size: 9px;
    font-weight: 800;
    letter-spacing: .06em;
    text-transform: uppercase;
    color: #64748b;
}
.landing-event-last-podium,
.landing-event-return {
    margin-top: 2px;
}
.temp-landing-hero-image .landing-event-card a:not(.landing-event-card-hit),
.temp-landing-secondary-image .landing-event-card a:not(.landing-event-card-hit),
#landing-event-hero-2 .landing-event-card a:not(.landing-event-card-hit) {
    position: relative;
    z-index: 1;
}
@media (max-width: 480px) {
    .temp-landing-hero-image .sa-home-regatta-card,
    .temp-landing-secondary-image .sa-home-regatta-card,
    #landing-event-hero-2 .sa-home-regatta-card { padding: 10px 10px 10px; border-radius: 6px; }
    .temp-landing-hero-image .sa-home-regatta-top,
    .temp-landing-secondary-image .sa-home-regatta-top,
    #landing-event-hero-2 .sa-home-regatta-top {
        grid-template-columns: 82px minmax(0,1fr);
        grid-template-areas: "logo main" "logo host" "actions actions";
        gap: 8px 10px;
        align-items: start;
    }
    .temp-landing-hero-image .sa-home-regatta-event-logo-link,
    .temp-landing-secondary-image .sa-home-regatta-event-logo-link,
    #landing-event-hero-2 .sa-home-regatta-event-logo-link {
        width: 78px; max-width: 78px;
    }
    .temp-landing-hero-image .sa-home-regatta-event-logo,
    .temp-landing-secondary-image .sa-home-regatta-event-logo,
    #landing-event-hero-2 .sa-home-regatta-event-logo {
        width: 78px !important; max-width: 78px !important; height: 58px !important; max-height: 58px !important;
    }
    .temp-landing-hero-image .sa-home-regatta-title,
    .temp-landing-secondary-image .sa-home-regatta-title,
    #landing-event-hero-2 .sa-home-regatta-title { font-size: 14px; }
    .temp-landing-hero-image .sa-home-regatta-host,
    .temp-landing-secondary-image .sa-home-regatta-host,
    #landing-event-hero-2 .sa-home-regatta-host { gap: 8px; }
    .temp-landing-hero-image .sa-home-regatta-host-logo,
    .temp-landing-secondary-image .sa-home-regatta-host-logo,
    #landing-event-hero-2 .sa-home-regatta-host-logo { width: 76px !important; height: 36px !important; }
    .temp-landing-hero-image .sa-home-regatta-actions,
    .temp-landing-secondary-image .sa-home-regatta-actions,
    #landing-event-hero-2 .sa-home-regatta-actions { width: 100%; justify-content: flex-end; }
    .temp-landing-hero-image .sa-home-regatta-btn,
    .temp-landing-secondary-image .sa-home-regatta-btn,
    #landing-event-hero-2 .sa-home-regatta-btn { flex: 1; min-width: 0; padding: 9px 10px; }
    .temp-landing-hero-image .sa-home-regatta-chip-logo,
    .temp-landing-secondary-image .sa-home-regatta-chip-logo,
    #landing-event-hero-2 .sa-home-regatta-chip-logo { width: 46px !important; height: 24px !important; max-width: 46px !important; }
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


_OVERALL_BLOCK_RE = re.compile(r":overall(?:-results)?$", re.I)
_CATEGORY_BLOCK_RE = re.compile(
    r":(?:u\d+|u19|u17|u15|youth|masters|ladies|women|junior)(?:-results)?$",
    re.I,
)


def _primary_overall_block_ids(rows: list[dict]) -> set[str]:
    """Genuine overall table only. Never union U19/U17/Youth category blocks."""
    bids: list[str] = []
    seen: set[str] = set()
    for r in rows:
        b = str(r.get("block_id") or "")
        if not b or b in seen:
            continue
        seen.add(b)
        bids.append(b)
    overall = [b for b in bids if _OVERALL_BLOCK_RE.search(b) and not _CATEGORY_BLOCK_RE.search(b)]
    if overall:
        return set(overall)
    non_cat = [b for b in bids if not _CATEGORY_BLOCK_RE.search(b)]
    if len(non_cat) == 1:
        return set(non_cat)
    if len(bids) == 1:
        return set(bids)
    return set()


def fetch_overall_podium(cur, regatta_id: str) -> list[dict]:
    """Top 3 of the primary overall fleet only. Helm + crew. No category mix."""
    if cur is None or not regatta_id:
        return []
    cols = _results_columns(cur)
    place = next((c for c in ("place", "position", "overall_place", "rank", "pos") if c in cols), "")
    name = next((c for c in ("sailor_name", "helm_name", "helm", "name") if c in cols), "")
    slug = next((c for c in ("sailor_slug", "helm_slug") if c in cols), "")
    sid = next((c for c in ("sailor_id", "helm_sailor_id", "helm_sa_sailing_id") if c in cols), "")
    if not place or not name:
        return []
    extra = f", {sid} AS sailor_id" if sid else ", NULL::text AS sailor_id"
    extra += f", {slug} AS sailor_slug" if slug else ", NULL::text AS sailor_slug"
    extra += ", block_id" if "block_id" in cols else ", NULL::text AS block_id"
    extra += ", BTRIM(fleet_label::text) AS fleet_label" if "fleet_label" in cols else ", NULL::text AS fleet_label"
    extra += ", BTRIM(crew_name::text) AS crew_name" if "crew_name" in cols else ", NULL::text AS crew_name"
    extra += ", crew_sa_sailing_id::text AS crew_id" if "crew_sa_sailing_id" in cols else ", NULL::text AS crew_id"
    extra += ", nett_points_raw AS nett" if "nett_points_raw" in cols else ", NULL::numeric AS nett"
    extra += ", result_id" if "result_id" in cols else ", NULL::bigint AS result_id"
    extra += ", race_scores" if "race_scores" in cols else ", NULL::jsonb AS race_scores"
    extra += ", races_sailed" if "races_sailed" in cols else ", NULL::int AS races_sailed"
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
            ORDER BY {place}::int, result_id
            """,
            (regatta_id,),
        )
    except Exception:
        try:
            cur.connection.rollback()
        except Exception:
            pass
        return []
    raw = list(cur.fetchall() or [])
    keep_blocks = _primary_overall_block_ids(raw)
    if not keep_blocks:
        return []
    rows = [r for r in raw if str(r.get("block_id") or "") in keep_blocks]
    seen = set()
    out = []
    for r in rows:
        pl = int(r.get("place") or 0)
        if pl not in (1, 2, 3) or pl in seen:
            continue
        seen.add(pl)
        sl = str(r.get("sailor_slug") or "").strip()
        href = f"/sailor/{sl}" if sl and "/" not in sl and " " not in sl else ""
        crew = str(r.get("crew_name") or "").strip()
        if "," in crew:
            crew = crew.split(",")[0].strip()
        out.append(
            {
                "place": pl,
                "name": str(r.get("name") or "").strip(),
                "href": href,
                "sailor_id": str(r.get("sailor_id") or "").strip(),
                "crew_name": crew,
                "crew_id": str(r.get("crew_id") or "").strip(),
                "crew_href": "",
                "nett": r.get("nett"),
                "block_id": str(r.get("block_id") or ""),
                "result_id": r.get("result_id"),
                "race_scores": r.get("race_scores"),
                "races_sailed": r.get("races_sailed"),
            }
        )
    resolve_podium_hrefs(cur, out)
    crews = [
        {"name": p["crew_name"], "sailor_id": p.get("crew_id") or "", "href": ""}
        for p in out
        if p.get("crew_name")
    ]
    if crews:
        resolve_podium_hrefs(cur, crews)
        by = {str(c.get("name") or "").lower(): str(c.get("href") or "") for c in crews}
        for p in out:
            if p.get("crew_name"):
                p["crew_href"] = by.get(p["crew_name"].lower()) or ""
    return out


def _slug_from_name(name: str) -> str:
    s = re.sub(r"[^a-z0-9\s-]", "", (name or "").strip().lower())
    s = re.sub(r"\s+", "-", s)
    return re.sub(r"-+", "-", s).strip("-")


def resolve_podium_hrefs(cur, podium: list[dict]) -> list[dict]:
    """Attach /sailor/{slug} only when sas_id_personal uniquely identifies the helm."""
    if cur is None or not podium:
        return podium
    need = [p for p in podium if not str(p.get("href") or "").startswith("/sailor/")]
    if not need:
        return podium
    ids = [str(p.get("sailor_id") or "").strip() for p in need if str(p.get("sailor_id") or "").strip().isdigit()]
    names = [str(p.get("name") or "").strip() for p in need if str(p.get("name") or "").strip()]
    rows: list[dict] = []
    try:
        if ids:
            cur.execute(
                """
                SELECT sa_sailing_id::text AS sas_id,
                    COALESCE(TRIM(full_name), TRIM(first_name || ' ' || COALESCE(last_name, ''))) AS full_name
                FROM public.sas_id_personal
                WHERE sa_sailing_id::text = ANY(%s)
                """,
                (ids,),
            )
            rows.extend(cur.fetchall() or [])
        if names:
            cur.execute(
                """
                SELECT sa_sailing_id::text AS sas_id,
                    COALESCE(TRIM(full_name), TRIM(first_name || ' ' || COALESCE(last_name, ''))) AS full_name
                FROM public.sas_id_personal
                WHERE LOWER(TRIM(COALESCE(full_name, first_name || ' ' || COALESCE(last_name, '')))) = ANY(%s)
                """,
                ([n.lower() for n in names],),
            )
            rows.extend(cur.fetchall() or [])
    except Exception:
        try:
            cur.connection.rollback()
        except Exception:
            pass
        return podium
    by_id: dict[str, tuple[str, str]] = {}
    by_name: dict[str, list[tuple[str, str]]] = {}
    seen = set()
    for r in rows:
        sid = str(r.get("sas_id") or "").strip()
        full = str(r.get("full_name") or "").strip()
        if not full or (sid, full.lower()) in seen:
            continue
        seen.add((sid, full.lower()))
        by_id[sid] = (full, sid)
        by_name.setdefault(full.lower(), []).append((full, sid))
    name_count: dict[str, int] = {}
    try:
        keys = list(by_name)
        if keys:
            cur.execute(
                """
                SELECT LOWER(TRIM(COALESCE(full_name, first_name || ' ' || COALESCE(last_name, '')))) AS n,
                       COUNT(*)::int AS c
                FROM public.sas_id_personal
                WHERE LOWER(TRIM(COALESCE(full_name, first_name || ' ' || COALESCE(last_name, '')))) = ANY(%s)
                GROUP BY 1
                """,
                (keys,),
            )
            name_count = {str(r.get("n") or ""): int(r.get("c") or 0) for r in (cur.fetchall() or [])}
    except Exception:
        try:
            cur.connection.rollback()
        except Exception:
            pass
    for p in podium:
        if str(p.get("href") or "").startswith("/sailor/"):
            continue
        sid = str(p.get("sailor_id") or "").strip()
        nm = str(p.get("name") or "").strip()
        picked = None
        if sid and sid in by_id:
            picked = by_id[sid]
        elif nm and len(by_name.get(nm.lower()) or []) == 1 and (name_count.get(nm.lower()) or 0) == 1:
            picked = by_name[nm.lower()][0]
        if not picked:
            continue
        full, sas = picked
        has_dup = (name_count.get(full.lower()) or 0) > 1
        slug = _slug_from_name(full)
        if not slug:
            continue
        if has_dup and sas:
            slug = f"{slug}-{sas}"
        p["href"] = f"/sailor/{slug}"
        if not p.get("sailor_id") and sas:
            p["sailor_id"] = sas
    return podium


_EVENT_MARK = re.compile(r"\b(cup|nationals?|championships?|champs?|open|week)\b", re.I)


def _event_identity_key(name: str) -> str:
    """Year-stripped event identity. Dates/years never participate in the match."""
    s = re.sub(r"^\d{4}-\d{2}-\d{2}\s+", "", (name or "").strip())
    return _canon_series_key(s)


def find_same_event_editions(cur, name: str, rid: str) -> list[dict]:
    """Previous editions of the same named event. Exact identity key only — no fuzzy titles."""
    key = _event_identity_key(name)
    tokens = key.split()
    generic = {
        "cup",
        "national",
        "nationals",
        "championship",
        "championships",
        "champs",
        "open",
        "week",
        "sailing",
        "regatta",
        "event",
    }
    distinctive = [t for t in tokens if t not in generic]
    if cur is None or not key or len(tokens) < 2 or not _EVENT_MARK.search(key) or not distinctive:
        return []
    try:
        cur.execute(
            """
            SELECT regatta_id, event_name, start_date,
                   (SELECT COUNT(*) FROM results res WHERE res.regatta_id = r.regatta_id) AS n
            FROM regattas r
            WHERE r.regatta_id <> %s
              AND r.event_name IS NOT NULL
              AND BTRIM(r.event_name) <> ''
            ORDER BY r.start_date DESC NULLS LAST
            """,
            (rid,),
        )
    except Exception:
        try:
            cur.connection.rollback()
        except Exception:
            pass
        return []
    out = []
    for r in cur.fetchall() or []:
        prid = str(r.get("regatta_id") or "").strip()
        en = str(r.get("event_name") or "")
        if not prid or _event_identity_key(en) != key:
            continue
        if int(r.get("n") or 0) <= 0:
            continue
        sd = _as_date(r.get("start_date"))
        if not sd:
            continue
        out.append({"url": f"/regatta/{prid}", "year": sd.year})
    return out


def fetch_current_entry_people(cur, regatta_id: str) -> list[dict]:
    if cur is None or not regatta_id:
        return []
    cols = _results_columns(cur)
    if "helm_name" not in cols:
        return []
    extra = ", helm_sa_sailing_id::text AS sailor_id" if "helm_sa_sailing_id" in cols else ", NULL::text AS sailor_id"
    extra += ", BTRIM(crew_name::text) AS crew_name" if "crew_name" in cols else ", NULL::text AS crew_name"
    extra += ", crew_sa_sailing_id::text AS crew_id" if "crew_sa_sailing_id" in cols else ", NULL::text AS crew_id"
    try:
        cur.execute(
            f"""
            SELECT BTRIM(helm_name::text) AS name {extra}
            FROM results
            WHERE regatta_id = %s
              AND BTRIM(COALESCE(helm_name::text, '')) <> ''
            ORDER BY result_id
            """,
            (regatta_id,),
        )
    except Exception:
        try:
            cur.connection.rollback()
        except Exception:
            pass
        return []
    out = []
    seen = set()
    for r in cur.fetchall() or []:
        nm = str(r.get("name") or "").strip()
        if not nm or nm.lower() in seen:
            continue
        seen.add(nm.lower())
        crew_raw = str(r.get("crew_name") or "").strip()
        crew = crew_raw.split(",")[0].strip() if crew_raw else ""
        out.append(
            {
                "name": nm,
                "sailor_id": str(r.get("sailor_id") or "").strip(),
                "href": "",
                "crew_name": crew,
                "crew_id": str(r.get("crew_id") or "").strip(),
                "crew_href": "",
            }
        )
    resolve_podium_hrefs(cur, out)
    crews = [
        {"name": e["crew_name"], "sailor_id": e.get("crew_id") or "", "href": ""}
        for e in out
        if e.get("crew_name")
    ]
    if crews:
        resolve_podium_hrefs(cur, crews)
        by = {str(c.get("name") or "").lower(): str(c.get("href") or "") for c in crews}
        for e in out:
            if e.get("crew_name"):
                e["crew_href"] = by.get(e["crew_name"].lower()) or ""
    return out


def fetch_current_sailor_ids(cur, regatta_id: str) -> set[str]:
    if cur is None or not regatta_id:
        return set()
    cols = _results_columns(cur)
    sid = next((c for c in ("sailor_id", "helm_sailor_id", "helm_sa_sailing_id") if c in cols), "")
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
            names.append(f'<a href="{html_module.escape(href, quote=True)}">{nm}</a> returns')
        else:
            names.append(f"{nm} returns")
    return names[0] if names else ""


def _score_places(scores: Any) -> tuple[int, int, int]:
    if isinstance(scores, dict):
        vals = scores.values()
    elif isinstance(scores, list):
        vals = scores
    else:
        return 0, 0, 0
    wins = seconds = thirds = 0
    for v in vals:
        s = str(v or "").strip().upper().replace("(", "").replace(")", "")
        tok = s.split()[0] if s else ""
        try:
            n = int(float(tok))
        except (TypeError, ValueError):
            continue
        if n == 1:
            wins += 1
        elif n == 2:
            seconds += 1
        elif n == 3:
            thirds += 1
    return wins, seconds, thirds


def _class_key(name: str) -> str:
    s = re.sub(r"\s+", " ", (name or "").strip().lower())
    s = re.sub(r"\s+(fleet|class)$", "", s).strip()
    return s


def _class_keys(classes: list[str]) -> list[str]:
    keys = []
    for c in classes or []:
        k = _class_key(c)
        if k and k not in {"fleet", "event", "open"} and k not in keys:
            keys.append(k)
    return keys


def _same_class(fields: list[Any], keys: list[str]) -> bool:
    blobs = [_class_key(str(f or "")) for f in fields if f]
    for key in keys:
        if not key:
            continue
        for blob in blobs:
            if not blob:
                continue
            if key == blob or key in blob or blob in key:
                return True
    return False


def _is_title_event(event_name: str) -> bool:
    en = (event_name or "").lower()
    if re.search(
        r"\b(6hr|9hr|endurance|grand\s*slam|triple\s*crown|azalea|memorial|vulcan|leopard|challenge)\b",
        en,
    ):
        return False
    return bool(re.search(r"national|regional", en))


def _class_event_label(event_name: str, start: Any, class_name: str = "", fleet_label: str = "") -> str:
    sd = _as_date(start)
    year = sd.year if sd else None
    en = (event_name or "").strip()
    low = en.lower()
    cls = (class_name or fleet_label or "").strip()
    cls = re.sub(r"\s+(fleet|class)$", "", cls, flags=re.I).strip()
    if year and re.search(r"regional", low):
        region = "KZN " if re.search(r"\bkzn\b", low) else ""
        if cls:
            return f"{year} {region}{cls} Regionals".replace("  ", " ").strip()
    if year and re.search(r"national", low) and cls:
        return f"{year} {cls} Nationals"
    cleaned = re.sub(r"^\d{4}-\d{2}-\d{2}\s+", "", en)
    if year and cleaned and not cleaned.startswith(str(year)):
        return f"{year} {cleaned}"
    return cleaned or en or cls


def _place_phrase(wins: int, seconds: int, thirds: int) -> str:
    bits = []
    if wins:
        bits.append("a race win" if wins == 1 else f"{wins} race wins")
    if seconds:
        bits.append("a 2nd" if seconds == 1 else f"{seconds} 2nds")
    if thirds:
        bits.append("a 3rd" if thirds == 1 else f"{thirds} 3rds")
    if not bits:
        return ""
    if len(bits) == 1:
        return bits[0]
    if len(bits) == 2:
        return f"{bits[0]} plus {bits[1]}"
    return f"{bits[0]} plus {bits[1]} and {bits[2]}"


def _ordinal(rk: int) -> str:
    if rk % 10 == 1 and rk % 100 != 11:
        return f"{rk}st"
    if rk % 10 == 2 and rk % 100 != 12:
        return f"{rk}nd"
    if rk % 10 == 3 and rk % 100 != 13:
        return f"{rk}rd"
    return f"{rk}th"


def _title_kind(label: str) -> str:
    low = (label or "").lower()
    if "regional" in low:
        return "KZN Regional" if "kzn" in low else "Regional"
    if "national" in low:
        return "National"
    return ""


def _summarize_title_kinds(labels: list[str]) -> str:
    kinds: list[str] = []
    for lab in labels:
        k = _title_kind(lab)
        if k and k not in kinds:
            kinds.append(k)
    if not kinds:
        return ""
    if len(kinds) == 1:
        n = sum(1 for lab in labels if _title_kind(lab) == kinds[0])
        if n >= 2:
            return f"multiple {kinds[0]} titles"
        return f"a {kinds[0]} title"
    if len(kinds) == 2:
        return f"{kinds[0]} and {kinds[1]} titles"
    return f"{', '.join(kinds[:-1])} and {kinds[-1]} titles"


def _is_national_event(event_name: str) -> bool:
    en = event_name or ""
    if re.search(r"regional|6hr|9hr|endurance|challenge", en, re.I):
        return False
    return bool(re.search(r"national", en, re.I))


def _is_regional_event(event_name: str) -> bool:
    return bool(re.search(r"regional", event_name or "", re.I))


def fetch_same_class_form_html(
    cur,
    *,
    classes: list[str],
    entered: list[dict],
    current_rid: str,
    upcoming_start: Any = None,
    logo: str = "",
) -> tuple[str, list[int]]:
    """Same-class history of current entrants. Recency-weighted. Never dumps entries."""
    del logo
    if cur is None or not entered:
        return "", []
    keys = _class_keys(classes)
    if not keys:
        return "", []
    class_name = classes[0]
    ref = _as_date(upcoming_start) or date.today()
    people: list[dict] = []
    ids: list[int] = []
    for e in entered:
        hid = str(e.get("sailor_id") or "").strip()
        if e.get("name"):
            people.append({"name": e["name"], "sailor_id": hid, "href": e.get("href") or ""})
        if hid.isdigit():
            ids.append(int(hid))
        cid = str(e.get("crew_id") or "").strip()
        cnm = str(e.get("crew_name") or "").strip()
        if cnm:
            people.append({"name": cnm, "sailor_id": cid, "href": e.get("crew_href") or ""})
        if cid.isdigit():
            ids.append(int(cid))
    if not ids:
        return "", []
    like_clauses = []
    like_args: list[Any] = []
    for k in keys:
        like_clauses.append(
            "(res.class_canonical ILIKE %s OR res.class_original ILIKE %s OR res.fleet_label ILIKE %s)"
        )
        like_args.extend([f"%{k}%", f"%{k}%", f"%{k}%"])
    try:
        cur.execute(
            f"""
            SELECT res.result_id, res.regatta_id, r.event_name, r.start_date, res.block_id,
                   res.fleet_label, res.class_canonical, res.class_original, res.rank,
                   res.helm_name, res.helm_sa_sailing_id::text AS helm_id,
                   res.crew_name, res.crew_sa_sailing_id::text AS crew_id,
                   res.boat_name, res.race_scores
            FROM results res
            JOIN regattas r ON r.regatta_id = res.regatta_id
            WHERE res.regatta_id <> %s
              AND (res.helm_sa_sailing_id = ANY(%s) OR res.crew_sa_sailing_id = ANY(%s))
              AND ({" OR ".join(like_clauses)})
            ORDER BY r.start_date DESC NULLS LAST, res.result_id
            """,
            [current_rid, ids, ids, *like_args],
        )
        rows = list(cur.fetchall() or [])
    except Exception:
        try:
            cur.connection.rollback()
        except Exception:
            pass
        return "", []
    rows = [
        r
        for r in rows
        if _same_class(
            [r.get("class_canonical"), r.get("class_original"), r.get("fleet_label")],
            keys,
        )
        and not _CATEGORY_BLOCK_RE.search(str(r.get("block_id") or ""))
    ]
    current_ids = {str(i) for i in ids}
    by_person = {str(p.get("sailor_id") or ""): p for p in people if p.get("sailor_id")}

    pairs = []
    seen_pair = set()
    for r in rows:
        pair = (str(r.get("regatta_id") or ""), str(r.get("block_id") or ""))
        if pair[0] and pair not in seen_pair:
            seen_pair.add(pair)
            pairs.append(pair)
    fleet_map: dict[tuple[str, str], int] = {}
    if pairs:
        try:
            cur.execute(
                """
                SELECT regatta_id::text AS regatta_id,
                       COALESCE(block_id::text, '') AS block_id,
                       COUNT(*)::int AS n
                FROM results
                WHERE rank IS NOT NULL
                  AND regatta_id = ANY(%s)
                GROUP BY 1, 2
                """,
                ([p[0] for p in pairs],),
            )
            for fr in cur.fetchall() or []:
                fleet_map[(str(fr.get("regatta_id") or ""), str(fr.get("block_id") or ""))] = int(fr.get("n") or 0)
        except Exception:
            try:
                cur.connection.rollback()
            except Exception:
                pass

    facts: list[dict] = []
    titles: dict[str, list[dict]] = {}
    for r in rows:
        en = str(r.get("event_name") or "")
        rk = int(r.get("rank") or 0)
        if rk <= 0:
            continue
        is_nat = _is_national_event(en)
        is_reg = _is_regional_event(en)
        if rk == 1 and _is_title_event(en):
            for sid in (r.get("helm_id"), r.get("crew_id")):
                sid = str(sid or "").strip()
                if sid not in current_ids:
                    continue
                titles.setdefault(sid, []).append(
                    {
                        "url": f"/regatta/{r['regatta_id']}",
                        "label": _class_event_label(en, r.get("start_date"), class_name, str(r.get("fleet_label") or "")),
                        "year": (_as_date(r.get("start_date")) or date.min).year,
                        "regatta_id": r["regatta_id"],
                        "result_id": r.get("result_id"),
                    }
                )
        fleet_n = fleet_map.get((str(r.get("regatta_id") or ""), str(r.get("block_id") or "")), 0)
        worthwhile = False
        if is_nat and rk <= 3:
            worthwhile = True
        elif is_nat and rk <= 8 and (fleet_n >= 8 or not fleet_n):
            worthwhile = True
        elif is_reg and rk == 1:
            worthwhile = True
        elif _is_title_event(en) and rk == 1:
            worthwhile = True
        if not worthwhile:
            continue
        wins, seconds, thirds = _score_places(r.get("race_scores"))
        age = _age_years(r.get("start_date"), ref)
        rec = _recency_weight(age)
        q = _quality_bonus(rk, is_nat, is_reg, wins, fleet_n)
        facts.append(
            {
                "score": rec + q,
                "age": age,
                "recency": rec,
                "row": r,
                "fleet_n": fleet_n,
                "wins": wins,
                "seconds": seconds,
                "thirds": thirds,
                "rank": rk,
            }
        )

    for sid, lst in list(titles.items()):
        seen_rid = set()
        seen_lab = set()
        uniq = []
        for t in sorted(lst, key=lambda x: x["year"]):
            lab = (t["year"], t["label"])
            if t["regatta_id"] in seen_rid or lab in seen_lab:
                continue
            seen_rid.add(t["regatta_id"])
            seen_lab.add(lab)
            uniq.append(t)
        titles[sid] = uniq

    lead = None
    if facts:
        lead = max(facts, key=lambda f: (f["score"], -f["age"], -f["rank"]))

    bits: list[str] = []
    evidence: list[int] = []
    lead_ids: set[str] = set()
    lead_rid = ""
    if lead:
        r = lead["row"]
        helm_id = str(r.get("helm_id") or "").strip()
        crew_id = str(r.get("crew_id") or "").strip()
        helm_nm = str(r.get("helm_name") or "").strip()
        crew_nm = str(r.get("crew_name") or "").strip()
        if "," in crew_nm:
            crew_nm = crew_nm.split(",")[0].strip()
        helm_p = by_person.get(helm_id) or {"name": helm_nm, "href": ""}
        crew_p = by_person.get(crew_id) if crew_id in current_ids else None
        team = _person_html(
            {
                "name": helm_p.get("name") or helm_nm,
                "href": helm_p.get("href") or "",
                "crew_name": (crew_p or {}).get("name") or (crew_nm if crew_id in current_ids else ""),
                "crew_href": (crew_p or {}).get("href") or "",
            }
        )
        ev_label = _class_event_label(
            str(r.get("event_name") or ""),
            r.get("start_date"),
            class_name,
            str(r.get("fleet_label") or ""),
        )
        url = f"/regatta/{r['regatta_id']}"
        rk = lead["rank"]
        fleet_n = lead["fleet_n"]
        place = _place_phrase(lead["wins"], lead["seconds"], lead["thirds"])
        finish = f"{_ordinal(rk)} of {fleet_n}" if fleet_n else _ordinal(rk)
        extra = f", taking {place}" if place else ""
        if team and rk:
            bits.append(
                f"{team} finished {_mark(finish)} at the "
                f'<a href="{_esc(url)}">{_esc_text(ev_label)}</a>{extra}.'
            )
            if r.get("result_id"):
                evidence.append(int(r["result_id"]))
            lead_ids = {x for x in (helm_id, crew_id) if x}
            lead_rid = str(r.get("regatta_id") or "")

    pedigree_sid = ""
    pedigree_titles: list[dict] = []
    best_pedigree = None
    for sid, lst in titles.items():
        kept = [t for t in lst if t["regatta_id"] != lead_rid]
        if not kept:
            continue
        if sid in lead_ids and lead:
            continue
        newest = min(_age_years(date(t["year"], 7, 1), ref) for t in kept)
        score = (len(kept), -newest)
        if best_pedigree is None or score > best_pedigree:
            best_pedigree = score
            pedigree_sid = sid
            pedigree_titles = kept
    if pedigree_sid and pedigree_titles and len(bits) < 2:
        person = by_person.get(pedigree_sid) or {"name": "", "href": ""}
        who = _person_html({"name": person.get("name"), "href": person.get("href")})
        summary = _summarize_title_kinds([t["label"] for t in pedigree_titles])
        cls = class_name or "class"
        if who and summary:
            bits.append(f"{who} brings proven {_esc_text(cls)} pedigree, with {summary} on record.")
            for t in pedigree_titles:
                if t.get("result_id"):
                    evidence.append(int(t["result_id"]))

    if not bits and titles:
        sid = sorted(titles.keys(), key=lambda s: (-len(titles[s]), s))[0]
        person = by_person.get(sid) or {"name": "", "href": ""}
        who = _person_html({"name": person.get("name"), "href": person.get("href")})
        summary = _summarize_title_kinds([t["label"] for t in titles[sid]])
        if who and summary:
            bits.append(f"{who} brings proven {_esc_text(class_name or 'class')} pedigree, with {summary} on record.")
            for t in titles[sid]:
                if t.get("result_id"):
                    evidence.append(int(t["result_id"]))

    if not bits:
        return "", []
    body = " ".join(bits[:2])
    recent = bool(lead and lead["recency"] >= 40)
    head = f"Recent {class_name} form" if recent and class_name else (f"{class_name} record" if class_name else "Class record")
    kind = "trend" if recent else "cal"
    return _story_wrap(kind, _esc_text(head), body), evidence


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
    if not prev_kept and cur is not None:
        prev_kept = find_same_event_editions(cur, name, rid)
    podium = []
    returning = ""
    entered = fetch_current_entry_people(cur, rid) if cur is not None else []
    if cur is not None and prev_kept:
        prev_kept.sort(key=lambda p: int(p.get("year") or 0), reverse=True)
        prev_rid = str(prev_kept[0].get("url") or "").rstrip("/").split("/")[-1]
        podium = fetch_overall_podium(cur, prev_rid)
        returning = returning_line(podium, fetch_current_sailor_ids(cur, rid))
    class_form_html = ""
    class_form_ids: list[int] = []
    if cur is not None and not podium:
        class_form_html, class_form_ids = fetch_same_class_form_html(
            cur,
            classes=classes,
            entered=entered,
            current_rid=rid,
            upcoming_start=start,
            logo=class_logo or logo,
        )
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
        "entered": entered,
        "class_form_html": class_form_html,
        "source_result_ids": [int(p["result_id"]) for p in podium if p.get("result_id")] + class_form_ids,
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


def fetch_regatta_row(cur, regatta_id: str) -> Optional[dict]:
    if cur is None or not regatta_id:
        return None
    cur.execute(
        """
        SELECT r.regatta_id, r.event_name, r.start_date, r.end_date, r.result_status,
               r.as_at_time, r.host_club_id,
               TRIM(COALESCE(c.club_abbrev, '')) AS club_abbrev,
               TRIM(COALESCE(c.club_fullname, '')) AS club_fullname
        FROM regattas r
        LEFT JOIN clubs c ON c.club_id = r.host_club_id
        WHERE r.regatta_id = %s
        """,
        (regatta_id,),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def generate_story_for_regatta(cur, regatta_id: str, *, today: Optional[date] = None, idx: Optional[dict] = None) -> dict:
    """Reusable packet: story HTML + source result IDs. No event-specific branches."""
    row = fetch_regatta_row(cur, regatta_id)
    if not row:
        return {"regatta_id": regatta_id, "story_html": "", "story_text": "", "source_result_ids": [], "path": "none"}
    card = card_from_row(row, cur=cur, today=today or date.today(), idx=idx if idx is not None else load_catalogue_index())
    html = build_story_html(card)
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    path = "none"
    if card.get("podium"):
        path = "previous_overall"
    elif card.get("class_form_html"):
        path = "same_class"
    return {
        "regatta_id": regatta_id,
        "event_name": card.get("name"),
        "classes": card.get("classes") or [],
        "story_html": html,
        "story_text": text,
        "source_result_ids": card.get("source_result_ids") or [],
        "path": path,
        "previous": card.get("previous") or [],
    }


def wrap_section(slot: int, inner: str, aria: str, section_id: str, section_class: str) -> str:
    return (
        f'<section id="{section_id}" class="{section_class}" aria-label="{_esc(aria)}" data-landing-event-card="1">\n'
        f"<!-- LANDING_EVENT_CARD_BEGIN slot={slot} -->\n"
        f"{inner}\n"
        f"<!-- LANDING_EVENT_CARD_END slot={slot} -->\n"
        f"</section>"
    )
