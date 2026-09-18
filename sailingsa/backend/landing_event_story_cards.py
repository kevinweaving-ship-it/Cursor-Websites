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
            return f"DAY 1 OF {(en - st).days + 1} — LIVE"
        return "STARTS TODAY"
    if en and st < today <= en:
        day_n = (today - st).days + 1
        total = (en - st).days + 1
        if as_at_time is not None:
            t = _as_at_hhmm(as_at_time)
            if t:
                return f"LIVE — Results updated {t}"
        return f"DAY {day_n} OF {total} — LIVE"
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


def select_hero_events(rows: list[dict], *, today: Optional[date] = None) -> tuple[Optional[dict], Optional[dict]]:
    """Hero 1 = nearest live/upcoming. Hero 2 = next upcoming. Same URL forever."""
    today = today or date.today()
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
    hero2 = None
    if hero1:
        h1d = _as_date(hero1.get("start_date"))
        for r in usable[1:]:
            sd = _as_date(r.get("start_date"))
            if sd and h1d and sd >= h1d and r.get("regatta_id") != hero1.get("regatta_id"):
                hero2 = r
                break
    return hero1, hero2


def _esc(s: str) -> str:
    return html_module.escape(s or "", quote=True)


def _esc_text(s: str) -> str:
    return html_module.escape(s or "")


def build_story_html(card: dict) -> str:
    name = card.get("name") or "Event"
    dates = card.get("dates") or ""
    host = card.get("host") or ""
    host_href = card.get("host_href") or ""
    classes = card.get("classes") or []
    entries = int(card.get("entries") or 0)
    fleet_counts = card.get("fleet_counts") or []
    series = card.get("series") or {}
    history = card.get("history") or ""
    bits = []
    loc = ""
    if host and host_href:
        loc = f' at <a href="{_esc(host_href)}">{_esc_text(host)}</a>'
    elif host:
        loc = f" at {_esc_text(host)}"
    class_links = []
    for c in classes[:4]:
        href = _class_href(c)
        if href:
            class_links.append(f'<a href="{_esc(href)}">{_esc_text(c)}</a>')
        else:
            class_links.append(_esc_text(c))
    class_bit = ""
    if class_links:
        class_bit = " " + ", ".join(class_links) + " event"
    bits.append(
        f"{_esc_text(name)}{loc}{', ' + _esc_text(dates) if dates else ''}.{class_bit}."
    )
    if entries > 0:
        if fleet_counts and len(fleet_counts) > 1:
            parts = [f"{_esc_text(nm)} {ct}" for nm, ct in fleet_counts]
            bits.append(f" {entries} event entries ({', '.join(parts)}).")
        else:
            bits.append(f" {entries} entries listed.")
    if series.get("href") and series.get("label"):
        bits.append(
            f' Part of <a href="{_esc(series["href"])}">{_esc_text(series["label"])}</a>.'
        )
    if history:
        bits.append(" " + _esc_text(history))
    prevs = card.get("previous") or []
    if prevs:
        links = []
        for p in prevs[:3]:
            url = p.get("url") or ""
            year = p.get("year")
            if url.startswith("/regatta/") and year:
                links.append(f'<a href="{_esc(url)}">{_esc_text(str(year))}</a>')
        if links:
            bits.append(" Previous editions held in SailingSA: " + ", ".join(links) + ".")
    return "".join(bits).replace("..", ".").strip()


def render_card_html(card: dict, *, slot: int) -> str:
    url = card.get("url") or ""
    logo = card.get("logo") or ""
    count = card.get("countdown") or ""
    title = card.get("name") or "Event"
    dates = card.get("dates") or ""
    story = build_story_html(card)
    img = ""
    if logo:
        img = (
            f'<a class="landing-event-card-media" href="{_esc(url)}">'
            f'<img src="{_esc(logo)}" alt="" width="88" height="88" loading="lazy" decoding="async">'
            f"</a>"
        )
    else:
        img = f'<a class="landing-event-card-media landing-event-card-media--empty" href="{_esc(url)}" aria-hidden="true"></a>'
    return (
        f'<article class="landing-event-card" data-landing-event-slot="{int(slot)}">'
        f"{img}"
        f'<div class="landing-event-card-body">'
        f'<p class="landing-event-card-count">{_esc_text(count)}</p>'
        f'<p class="landing-event-card-title"><a href="{_esc(url)}">{_esc_text(title)}</a></p>'
        f'<p class="landing-event-card-meta">{_esc_text(dates)}</p>'
        f'<p class="landing-event-card-story">{story}</p>'
        f"</div></article>"
    )


LANDING_CARD_CSS = """
.temp-landing-hero-image .landing-event-card,
.temp-landing-secondary-image .landing-event-card {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    width: 100%;
    max-width: 100%;
    box-sizing: border-box;
    text-align: left;
    color: #1a2750;
}
.landing-event-card-media {
    flex: 0 0 88px;
    width: 88px;
    height: 88px;
    display: block;
    background: #f4f6f8;
    border-radius: 8px;
    overflow: hidden;
}
.landing-event-card-media img {
    width: 88px;
    height: 88px;
    object-fit: contain;
    display: block;
}
.landing-event-card-body { min-width: 0; flex: 1; }
.landing-event-card-count {
    margin: 0 0 0.2rem;
    font-size: 0.78rem;
    font-weight: 800;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}
.landing-event-card-title { margin: 0 0 0.15rem; font-size: 1rem; font-weight: 700; line-height: 1.25; }
.landing-event-card-title a { color: #1a2750; text-decoration: none; }
.landing-event-card-meta { margin: 0; font-size: 0.8rem; color: #444; }
.landing-event-card-story { margin: 0.35rem 0 0; font-size: 0.82rem; line-height: 1.35; color: #444; }
.landing-event-card-story a { color: #1a2750; }
@media (max-width: 480px) {
    .temp-landing-hero-image,
    .temp-landing-secondary-image {
        overflow: hidden;
    }
    .landing-event-card { gap: 0.6rem; }
    .landing-event-card-media,
    .landing-event-card-media img { width: 72px; height: 72px; flex-basis: 72px; }
    .landing-event-card-title { font-size: 0.95rem; }
    .landing-event-card-story { font-size: 0.78rem; }
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
