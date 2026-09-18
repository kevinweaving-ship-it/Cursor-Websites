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
    }


def history_sentence(series_name: str, editions: list[dict], *, current_year: Optional[int] = None) -> str:
    """Bounded archive wording. Missing years = unknown, not 'not held'."""
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
    name = series_name or "this event"
    return (
        f"According to results currently held by SailingSA, there are "
        f"{n} edition{'s' if n != 1 else ''} of {name} between {lo} and {hi}."
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


def _class_anchor(name: str) -> str:
    href = _class_href(name)
    if href:
        return f'<a href="{_esc(href)}">{_esc_text(name)}</a>'
    return _esc_text(name)


def build_facts_html(card: dict) -> str:
    """Single inline facts line — not stacked metadata rows."""
    url = card.get("url") or ""
    dates = card.get("dates") or ""
    host_short = card.get("host_short") or ""
    host_href = card.get("host_href") or ""
    classes = card.get("classes") or []
    entries = int(card.get("entries") or 0)
    fleet_counts = card.get("fleet_counts") or []
    podium = card.get("podium") or []
    state = card.get("state") or ""
    bits = []
    if dates and url:
        bits.append(f'<a href="{_esc(url)}">{_esc_text(dates)}</a>')
    elif dates:
        bits.append(_esc_text(dates))
    if host_short and host_href:
        bits.append(f'<a href="{_esc(host_href)}">{_esc_text(host_short)}</a>')
    elif host_short:
        bits.append(_esc_text(host_short))
    for c in classes[:2]:
        bits.append(_class_anchor(c))
    if state == "final" and podium:
        bits.extend(podium)
    elif entries > 0:
        if fleet_counts and len(fleet_counts) > 1:
            bits.append(f"{entries} entries")
        else:
            bits.append(f"{entries} entries")
    return " · ".join(bits)


def build_story_html(card: dict) -> str:
    """One or two preview sentences. Not a stack of SEO fields."""
    name = card.get("name") or "Event"
    dates = card.get("dates") or ""
    host_short = card.get("host_short") or ""
    host_href = card.get("host_href") or ""
    classes = card.get("classes") or []
    entries = int(card.get("entries") or 0)
    fleet_counts = card.get("fleet_counts") or []
    series = card.get("series") or {}
    history = card.get("history") or ""
    countdown = card.get("countdown") or ""
    returning = card.get("returning") or ""
    bits = []
    class_name = classes[0] if classes else ""
    host_a = (
        f'<a href="{_esc(host_href)}">{_esc_text(host_short)}</a>'
        if host_short and host_href
        else _esc_text(host_short)
    )
    class_a = _class_anchor(class_name) if class_name else ""
    if returning:
        bits.append(returning)
    elif entries > 0 and class_a:
        when = "this weekend's " if countdown in {"TOMORROW", "STARTS TODAY"} else ""
        if fleet_counts and len(fleet_counts) > 1:
            parts = [f"{_esc_text(nm)} {ct}" for nm, ct in fleet_counts]
            bits.append(
                f"{entries} boats are currently entered for {when}{_esc_text(name)}"
                f" ({', '.join(parts)})."
            )
        else:
            bits.append(
                f"{entries} {class_a}s are currently entered for {when}{_esc_text(name)}."
            )
    elif history:
        hist = _esc_text(history)
        if series.get("href"):
            hist += (
                f' <a href="{_esc(series["href"])}">'
                f'{_esc_text(series.get("label") or "Event history")}</a>.'
            )
        bits.append(hist)
    elif series.get("href") and series.get("label"):
        loc = f" at {host_a}" if host_a else ""
        bits.append(
            f'<a href="{_esc(series["href"])}">{_esc_text(series["label"])}</a>{loc}.'
        )
    elif host_a:
        bits.append(f"{_esc_text(name)} at {host_a}.")
    prevs = [
        p
        for p in (card.get("previous") or [])
        if str(p.get("url") or "").startswith("/regatta/") and p.get("year")
    ]
    prevs.sort(key=lambda p: int(p.get("year") or 0), reverse=True)
    if prevs and len(bits) < 2:
        p = prevs[0]
        bits.append(
            f' Most recent edition held by SailingSA: <a href="{_esc(p["url"])}">{_esc_text(str(p["year"]))}</a>.'
        )
    return " ".join(b.strip() for b in bits if b and b.strip()).replace("..", ".").strip()


def render_card_html(card: dict, *, slot: int) -> str:
    url = card.get("url") or ""
    logo = card.get("logo") or ""
    count = card.get("countdown") or ""
    title = card.get("name") or "Event"
    state = card.get("state") or "upcoming"
    if state == "live" and count and not count.startswith("LIVE"):
        count = f"LIVE · {count}"
    story = build_story_html(card)
    facts = build_facts_html(card)
    modifier = "upcoming"
    if state == "live" or (count or "").startswith("LIVE"):
        modifier = "live"
    elif state == "final" or count == "FINAL RESULTS":
        modifier = "final"
    img = (
        f'<a class="landing-event-card-art" href="{_esc(url)}">'
        f'<img src="{_esc(logo)}" alt="{_esc(title)}" width="112" height="112" loading="lazy" decoding="async">'
        f"</a>"
        if logo
        else f'<a class="landing-event-card-art landing-event-card-art--empty" href="{_esc(url)}" aria-label="{_esc(title)}"></a>'
    )
    return (
        f'<article class="landing-event-card landing-event-card--{modifier}" '
        f'data-landing-event-slot="{int(slot)}" data-state="{_esc(modifier)}">'
        f'<div class="landing-event-card-visual">{img}</div>'
        f'<div class="landing-event-card-body">'
        f'<p class="landing-event-card-count">{_esc_text(count)}</p>'
        f'<p class="landing-event-card-title"><a href="{_esc(url)}">{_esc_text(title)}</a></p>'
        f'<p class="landing-event-card-facts">{facts}</p>'
        f'<p class="landing-event-card-story">{story}</p>'
        f"</div></article>"
    )


LANDING_CARD_CSS = """
.temp-landing-hero-image,
.temp-landing-secondary-image {
    overflow: hidden;
}
.temp-landing-hero-image .landing-event-card img,
.temp-landing-secondary-image .landing-event-card img {
    width: 112px;
    height: 112px;
    max-width: 112px;
    object-fit: contain;
}
.temp-landing-hero-image .landing-event-card,
.temp-landing-secondary-image .landing-event-card {
    display: flex;
    align-items: stretch;
    gap: 0;
    width: 100%;
    max-width: 100%;
    box-sizing: border-box;
    margin: 0;
    text-align: left;
    color: #ffffff;
    background: #001f3f;
    border-radius: 8px;
    min-height: 124px;
    overflow: hidden;
}
.landing-event-card-visual {
    flex: 0 0 124px;
    width: 124px;
    background: #ffffff;
    display: flex;
    align-items: center;
    justify-content: center;
}
.landing-event-card-art {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 100%;
    min-height: 124px;
}
.landing-event-card-art img {
    display: block;
    width: 112px;
    height: 112px;
    object-fit: contain;
}
.landing-event-card-count {
    display: inline-block;
    margin: 0 0 0.28rem;
    padding: 3px 8px;
    font-size: 0.68rem;
    font-weight: 800;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    line-height: 1.15;
    color: #001f3f;
    background: #ffe566;
    border-radius: 4px;
}
.landing-event-card--live .landing-event-card-count {
    background: #ea580c;
}
.landing-event-card--final .landing-event-card-count {
    background: #0b2c4d;
}
.landing-event-card-body {
    min-width: 0;
    flex: 1;
    padding: 0.55rem 0.7rem 0.6rem;
    box-sizing: border-box;
}
.landing-event-card-title {
    margin: 0 0 0.2rem;
    font-size: 0.92rem;
    font-weight: 800;
    line-height: 1.2;
}
.landing-event-card-title a { color: #ffffff; text-decoration: none; }
.landing-event-card-facts {
    margin: 0;
    font-size: 0.78rem;
    line-height: 1.35;
    font-weight: 650;
    color: #dbeafe;
}
.landing-event-card-facts a { color: #ffe566; text-decoration: underline; }
.landing-event-card-story {
    margin: 0.35rem 0 0;
    font-size: 0.78rem;
    line-height: 1.35;
    color: #e2e8f0;
}
.landing-event-card-story a { color: #ffe566; }
@media (max-width: 480px) {
    .temp-landing-hero-image .landing-event-card,
    .temp-landing-secondary-image .landing-event-card {
        min-height: 118px;
    }
    .landing-event-card-visual,
    .landing-event-card-art { flex-basis: 108px; width: 108px; min-height: 118px; }
    .temp-landing-hero-image .landing-event-card img,
    .temp-landing-secondary-image .landing-event-card img,
    .landing-event-card-art img { width: 96px; height: 96px; max-width: 96px; }
    .landing-event-card-count { font-size: 0.64rem; padding: 2px 6px; }
    .landing-event-card-title { font-size: 0.88rem; }
    .landing-event-card-facts,
    .landing-event-card-story { font-size: 0.74rem; }
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
    classes = [n for n, _c in fleet_counts if n.lower() not in {"fleet", "event"}]
    series = series_for_event(name, rid, idx)
    prev = []
    if cur is not None and series.get("slug"):
        prev = _previous_editions_from_catalogue(series.get("slug") or "", rid)
    history = history_sentence(series.get("label") or name, prev, current_year=(_as_date(start) or today).year)
    logo = series.get("logo") or ""
    if not logo and host_ab:
        logo = f"/api/club-logo/{host_ab}"
    return {
        "regatta_id": rid,
        "name": name,
        "url": f"/regatta/{rid}",
        "dates": compact_event_date_range(start, end),
        "start_date": start,
        "end_date": end,
        "host": host,
        "host_short": host_short,
        "host_href": _club_href(host_ab, host_fn),
        "classes": classes,
        "entries": sum(n for _n, n in fleet_counts),
        "fleet_counts": fleet_counts,
        "series": series,
        "previous": [p for p in prev if p.get("url") and p.get("url") != f"/regatta/{rid}"],
        "history": history,
        "logo": logo,
        "countdown": countdown_label(
            start, end, today=today, as_at_time=row.get("as_at_time"), result_status=row.get("result_status") or ""
        ),
        "state": derive_event_lifecycle(
            start_date=start,
            end_date=end,
            result_status=row.get("result_status"),
            as_at_time=row.get("as_at_time"),
            raced_count=sum(n for _n, n in fleet_counts),
            today=today,
        ),
    }


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
