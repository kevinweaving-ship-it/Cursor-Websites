#!/usr/bin/env python3
"""Event logo gallery + per-logo gold-std detail pages.

Routes (wired in api.py):
  GET /events-logos              — grid (tiles click → detail)
  GET /events-logos/{slug}       — gold-std page: header logo + host chips + events table
  GET /api/events-logos          — JSON gallery
  GET /api/events-logos/{slug}   — JSON detail
"""
from __future__ import annotations

import html as html_module
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Callable

import psycopg2.extras

_API_DIR = Path("/var/www/sailingsa/api")
if _API_DIR.is_dir() and str(_API_DIR) not in sys.path:
    sys.path.insert(0, str(_API_DIR))
_DEPLOY_DIR = Path("/var/www/sailingsa/deploy")
if _DEPLOY_DIR.is_dir() and str(_DEPLOY_DIR) not in sys.path:
    sys.path.insert(0, str(_DEPLOY_DIR))
_LOCAL_DIR = Path(__file__).resolve().parent
if str(_LOCAL_DIR) not in sys.path:
    sys.path.insert(0, str(_LOCAL_DIR))

from logo_grid_shared import (
    POPOVER_CSS,
    collapse_to_parent_regattas,
    event_name_with_year,
    load_closed_regatta_ids,
    load_fleet_shell_parent_index,
    load_hub_master_index,
    parent_regatta_id,
    render_logo_grid_tile,
    year_from_regatta_id,
)

_LOGO_SUFFIX_RE = re.compile(r"(?i)[\s_-]+(class[\s_-]*logo|event[\s_-]*logo|logo)$")
_YEAR_IN_NAME_RE = re.compile(r"(19|20)\d{2}")

try:
    from backfill_event_edition_classes import (
        SERIES_CANONICAL_LABEL,
        canonical_series_label,
        yearly_event_series_key,
    )
except ImportError:
    SERIES_CANONICAL_LABEL = {}

    def yearly_event_series_key(name: str) -> str:
        s = re.sub(r"\b(19|20)\d{2}\b", " ", (name or "").lower())
        s = re.sub(r"[-_/()#]", " ", s)
        return re.sub(r"\s+", " ", s).strip()

    def canonical_series_label(series_key: str, fallback_name: str = "") -> str:
        return SERIES_CANONICAL_LABEL.get(series_key) or fallback_name


def series_key_to_slug(series_key: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (series_key or "").lower()).strip("-")
    return slug or "event"


def _label_from_series_key(series_key: str) -> str:
    raw = re.sub(r"\s+", " ", (series_key or "").strip())
    if not raw:
        return ""
    parts = []
    for w in raw.split(" "):
        wu = w.upper()
        if wu in {
            "WC", "SA", "SAS", "RSA", "ILCA", "DF95", "IOM", "RS", "KZN", "EC",
            "NR", "FS", "MSC", "HMYC", "RCYC", "HYC", "FBYC", "MAC", "TSC", "PSC",
            "KYC", "MBSC", "ZYC", "KYC",
        }:
            parts.append(wu)
        elif re.match(r"^[0-9]", w):
            parts.append(w)
        else:
            parts.append(w[:1].upper() + w[1:].lower())
    return " ".join(parts)


def split_slug_year(slug: str) -> tuple[str, int | None]:
    """admirals-regatta-2025 → (admirals-regatta, 2025)."""
    s = (slug or "").strip().lower().strip("/")
    m = re.search(r"^(.*?)-((?:19|20)\d{2})$", s)
    if m:
        return m.group(1), int(m.group(2))
    return s, None


def edition_year_of(rg: dict) -> int | None:
    y = rg.get("year")
    try:
        yi = int(y)
        if 1900 <= yi <= 2100:
            return yi
    except (TypeError, ValueError):
        pass
    sd = rg.get("start_date")
    if sd is not None and hasattr(sd, "year"):
        return int(sd.year)
    blob = " ".join(
        str(x or "")
        for x in (rg.get("date_label"), rg.get("start_date"), rg.get("event_name"), rg.get("regatta_id"))
    )
    m = _YEAR_IN_NAME_RE.search(blob)
    if m:
        yi = int(m.group(0))
        if 1900 <= yi <= 2100:
            return yi
    return None


def _load_series_calendar_events(
    series_keys: list[str],
    table_exists: Callable[[str], bool],
    get_db_connection: Callable[[], Any],
    return_db_connection: Callable[[Any], None],
) -> dict[str, list[dict[str, Any]]]:
    """Events calendar rows keyed by series_key (includes years with no results yet)."""
    out: dict[str, list[dict[str, Any]]] = {}
    keys = [str(k).strip() for k in series_keys if str(k).strip()]
    if not keys or not table_exists("events"):
        return out
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            SELECT e.series_key,
                   e.event_id,
                   e.event_name,
                   e.regatta_id::text AS regatta_id,
                   COALESCE(
                       e.edition_year,
                       e.event_year,
                       EXTRACT(YEAR FROM COALESCE(e.end_date, e.start_date))::int
                   ) AS year,
                   e.start_date,
                   e.end_date,
                   e.source_url,
                   c.club_abbrev
            FROM events e
            LEFT JOIN clubs c ON c.club_id = e.host_club_id
            WHERE e.series_key = ANY(%s)
            """,
            (keys,),
        )
        for row in cur.fetchall() or []:
            key = str(row.get("series_key") or "").strip()
            if not key:
                continue
            out.setdefault(key, []).append(dict(row))
    finally:
        cur.close()
        return_db_connection(conn)
    return out


def _merge_missing_edition_years(
    regattas: list[dict[str, Any]],
    calendar: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Add calendar years that have no result row yet. Keep existing result years."""
    have = {edition_year_of(rg) for rg in regattas}
    have.discard(None)
    best: dict[int, tuple[tuple[int, int, int], dict[str, Any]]] = {}
    for ev in calendar or []:
        try:
            year = int(ev.get("year"))
        except (TypeError, ValueError):
            continue
        if year in have or not (1900 <= year <= 2100):
            continue
        score = (
            1 if ev.get("start_date") else 0,
            1 if (ev.get("club_abbrev") or ev.get("host_abbrev")) else 0,
            1 if str(ev.get("regatta_id") or "").strip() else 0,
        )
        prev = best.get(year)
        if not prev or score > prev[0]:
            best[year] = (score, ev)
    urls_by_year: dict[int, list[str]] = {}
    for ev in calendar or []:
        try:
            year = int(ev.get("year"))
        except (TypeError, ValueError):
            continue
        url = str(ev.get("source_url") or "").strip()
        if year and url:
            urls_by_year.setdefault(year, []).append(url)
    extra: list[dict[str, Any]] = []
    for year, (_score, ev) in best.items():
        rid = str(ev.get("regatta_id") or "").strip()
        urls = urls_by_year.get(year) or []
        event_url = next((u for u in urls if "sailing.org.za" in u.lower()), urls[0] if urls else "")
        extra.append(
            {
                "regatta_id": rid,
                "event_name": ev.get("event_name") or "",
                "year": year,
                "closed": bool(rid),
                "host_abbrev": str(ev.get("club_abbrev") or ev.get("host_abbrev") or "").strip().upper(),
                "date_label": _format_date_label(ev.get("start_date"), ev.get("end_date")) or str(year),
                "start_date": _iso_date(ev.get("start_date")),
                "event_url": event_url,
            }
        )
    return list(regattas) + extra


def _iso_date(value: Any) -> str:
    if value is None:
        return ""
    try:
        return value.isoformat()  # datetime.date / datetime
    except Exception:
        return str(value)[:10]


def _edition_dedupe_key(rg: dict[str, Any]) -> str:
    """Stable key for named-event editions — one row per calendar year."""
    ey = edition_year_of(rg)
    if ey:
        return f"year|{ey}"
    rid = str(rg.get("regatta_id") or "").strip()
    if rid:
        return f"rid|{rid}"
    host = str(rg.get("host_abbrev") or "").strip().upper()
    name = str(rg.get("event_name") or "").strip().lower()
    return f"id|{name}|host|{host}|{id(rg)}"


def _edition_row_score(rg: dict[str, Any]) -> tuple:
    """Prefer real result rows with host + dates over class-leg / placeholder years."""
    closed = 1 if rg.get("closed") else 0
    host = 1 if str(rg.get("host_abbrev") or "").strip() else 0
    dl = str(rg.get("date_label") or "").strip()
    real_date = 1 if dl and not re.fullmatch(r"(19|20)\d{2}", dl) else 0
    rid = 1 if str(rg.get("regatta_id") or "").strip() else 0
    name = str(rg.get("event_name") or "").lower()
    # Prefer umbrella WC Dinghy / Youth titles over single-class legs
    class_leg_penalty = 0
    for tok in (
        "ilca", "optimist", "hobie", "29er", "finn", "505", "stadt", "rs tera", "dabchick", "mirror",
    ):
        if tok in name:
            class_leg_penalty = 1
            break
    return (closed, host, real_date, rid, -class_leg_penalty, -len(name))


def _one_row_per_edition_year(regattas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One row per calendar year for a named-event series (parent edition only)."""
    best: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for rg in regattas:
        key = _edition_dedupe_key(rg)
        if key not in best:
            best[key] = dict(rg)
            order.append(key)
            continue
        cur = best[key]
        if _edition_row_score(rg) > _edition_row_score(cur):
            best[key] = dict(rg)
    return [best[k] for k in order]


def _clean_aka_names(names: list[str], series_label: str, allowed_years: set[int] | None = None) -> list[str]:
    """One original title per result year, newest first. Skip years with no result row."""
    canon = re.sub(r"[^a-z0-9]+", " ", (series_label or "").lower()).strip()
    by_year: dict[int, str] = {}
    for raw in names or []:
        s = html_module.unescape(str(raw or "")).replace("&amp;", "&").strip()
        if not s:
            continue
        s = re.sub(r"^\d{4}-\d{2}-\d{2}\s+", "", s)
        years = [int(x) for x in re.findall(r"\b((?:19|20)\d{2})\b", s)]
        year = years[0] if years else 0
        if not year:
            continue
        if allowed_years is not None and year not in allowed_years:
            continue
        core = re.sub(r"\b((?:19|20)\d{2})\b", " ", s.lower())
        core = re.sub(r"[^a-z0-9]+", " ", core).strip()
        if core == canon:
            continue
        prev = by_year.get(year)
        if not prev or len(s) < len(prev):
            by_year[year] = s
    return [by_year[y] for y in sorted(by_year, reverse=True)]


def edition_display_name(series_label: str, year: int | None, sponsor: str = "") -> str:
    try:
        from backfill_event_edition_classes import edition_title
        return edition_title(series_label, year, sponsor)
    except Exception:
        label = (series_label or "").strip() or "Event"
        if sponsor and sponsor.lower() not in label.lower():
            label = f"{sponsor} {label}"
        if year and not re.search(rf"\b{year}\b", label):
            return f"{label} {year}"
        return label


def edition_url(series_slug: str, year: int | None = None) -> str:
    slug = (series_slug or "").strip("/")
    return f"/events-logos/{slug}"


def _norm_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


def _year_sponsor_rows(series_key: str, series_slug: str, year: int) -> list[dict[str, str]]:
    paths = [
        _DEPLOY_DIR / "event_year_sponsors.json",
        _LOCAL_DIR / "event_year_sponsors.json",
    ]
    data = None
    for path in paths:
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                break
            except Exception:
                continue
    if not isinstance(data, dict):
        return []
    want = {_norm_key(series_key), _norm_key(series_slug.replace("-", " "))}
    want.discard("")
    year_s = str(int(year))
    year_block = None
    for block in data.get("series") or []:
        if not isinstance(block, dict):
            continue
        keys = [_norm_key(block.get("series_key") or "")]
        keys.extend(_norm_key(k) for k in (block.get("match_keys") or []))
        if want & {k for k in keys if k}:
            year_block = (block.get("years") or {}).get(year_s) or {}
            break
    if not year_block:
        return []
    try:
        from sponsor_catalog import catalog_by_slug
        catalog = catalog_by_slug()
    except Exception:
        catalog = {}
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for role in ("headline", "tier2"):
        for item in year_block.get(role) or []:
            if not isinstance(item, dict):
                continue
            slug = (item.get("slug") or "").strip().lower()
            if not slug or slug in seen:
                continue
            seen.add(slug)
            prof = catalog.get(slug) or {}
            out.append(
                {
                    "slug": slug,
                    "role": role,
                    "name": (prof.get("display_name") or prof.get("short_name") or slug).strip(),
                    "logo": (prof.get("logo_path") or "").strip(),
                }
            )
    return out


def _sponsors_row_html(series_key: str, series_slug: str, year: int | None) -> str:
    if not year:
        return ""
    rows = _year_sponsor_rows(series_key, series_slug, int(year))
    if not rows:
        return ""
    chips = []
    for item in rows:
        href = html_module.escape(f"/sponsors/{item['slug']}")
        name = html_module.escape(item["name"])
        logo = html_module.escape(item["logo"])
        role = "2nd tier" if item["role"] == "tier2" else "Headline"
        img = (
            f'<img src="{logo}" alt="" loading="lazy" decoding="async" onerror="this.style.display=\'none\'">'
            if logo else ""
        )
        chips.append(
            f'<a class="club-story-chip" href="{href}" title="{name} · {role}">'
            f"{img}<span class=\"club-story-chip-label\">{name}</span></a>"
        )
    n_head = sum(1 for r in rows if r["role"] == "headline")
    n_t2 = sum(1 for r in rows if r["role"] == "tier2")
    bits = []
    if n_head:
        bits.append(f"{n_head} headline")
    if n_t2:
        bits.append(f"{n_t2} 2nd-tier")
    label = f"{year} sponsors"
    if bits:
        label += " · " + " · ".join(bits)
    return (
        '<div class="club-story-logo-row">'
        f'<div class="club-story-logo-row-label">{html_module.escape(label)}</div>'
        f'<div class="club-story-logo-chips">{"".join(chips)}</div></div>'
    )


def _year_in_filename(filename: str) -> int:
    m = _YEAR_IN_NAME_RE.search(filename or "")
    return int(m.group(0)) if m else 0


def _web_root_from_api_file(api_file: str) -> Path:
    return Path(os.path.dirname(os.path.abspath(api_file))).parent


def _public_artwork_exists(api_file: str, public_path: str) -> bool:
    p = (public_path or "").strip()
    if not p.startswith("/artwork/"):
        return False
    return (_web_root_from_api_file(api_file) / p.lstrip("/")).is_file()


def _series_class_logo_path(
    series_key: str,
    class_logo_path_for_name: Callable[[str], str | None] | None = None,
) -> str | None:
    """When a named event is really a single-class series, use the class master logo."""
    k = re.sub(r"\s+", " ", (series_key or "").strip().lower())
    if re.search(r"\bdf\s*95\b|\bdf95\b|dragonflite\s*95", k):
        if class_logo_path_for_name:
            lp = class_logo_path_for_name("DF95")
            if lp:
                return lp.strip()
        return "/artwork/Class Logo/DF95-Class-Logo.png"
    _class_by_series = {
        "ilca nationals": "ILCA",
        "optimist nationals": "Optimist",
        "420 nationals": "420",
        "29er nationals": "29er",
        "finn nationals": "Finn",
        "505 nationals": "505",
        "mirror nationals": "Mirror",
        "dabchick nationals": "Dabchick",
        "hobie 16 nationals": "Hobie 16",
        "hobie tiger nationals": "Hobie Tiger",
        "dart 18 nationals": "Dart 18",
        "windsurfer lt nationals": "Windsurfer LT",
    }
    class_name = _class_by_series.get(k)
    if class_name:
        if class_logo_path_for_name:
            lp = class_logo_path_for_name(class_name)
            if lp:
                return lp.strip()
        _hardcoded = {
            "ILCA": "/artwork/Class Logo/ILCA-Class-Logo.png",
            "Optimist": "/artwork/Class Logo/Optimist-Class-Logo.png",
            "420": "/artwork/Class Logo/420-Class-Logo.png",
            "29er": "/artwork/Class Logo/29er-Class-Logo.png",
            "Finn": "/artwork/Class Logo/Finn-Class-Logo.png",
            "Mirror": "/artwork/Class Logo/Mirror-Class-Logo.png",
            "Dabchick": "/artwork/Class Logo/Dabchick-Class-Logo.png",
        }
        return _hardcoded.get(class_name)
    return None


def pick_series_logo_path(paths: list[str], prefer_key: str = "") -> str:
    """One artwork per series: prefer master file (no year), else newest year.

    When merging aliases, prefer a filename whose tokens match the series key
    (e.g. Brass-Monkey-Regatta over Brass-Monkey-Sailing).
    """
    if not paths:
        return ""
    key_toks = set(re.findall(r"[a-z0-9]+", (prefer_key or "").lower()))
    key_toks -= {"the", "a", "of", "and", "sa", "sas"}

    def score(p: str) -> tuple:
        fname = p.rsplit("/", 1)[-1]
        year = _year_in_filename(fname)
        stem = clean_event_logo_label(fname).lower()
        stem_toks = set(re.findall(r"[a-z0-9]+", stem))
        overlap = len(key_toks & stem_toks) if key_toks else 0
        return (overlap, 0 if year == 0 else 1, -year, p)

    return sorted(paths, key=score, reverse=True)[0]


# Class / fleet / junk artwork must not appear on Named Events (those belong on /classes).
_CLASS_FLEET_KEY_RE = re.compile(
    r"^(?:"
    r"29er|49er|topaz|farr\s*40|hobie\s*cat|dinghy|dinghy\s*fleet|junior\s*dinghy|"
    r"senior\s*dinghy|keelboat|keelboat\s*fleet|multihull|multihull\s*fleet|"
    r"monohull\s*dinghy|monohull\s*dinghy\s*open\s*fleet|monohull\s*keelboats|"
    r"primary\s*school|primary\s*school\s*fleet|club|offshore|national|"
    r"interclub|original\s*illegible|partially\s*illegible"
    r")$",
    re.I,
)
_CLASS_FLEET_FILE_RE = re.compile(
    r"(class[\s_-]*logo|fleet|\billegible\b)",
    re.I,
)
_SPONSOR_ONLY_KEYS = {
    "intasure",
    "macs shipping",
    "msc",
    "zhik",
    "north sails",
    "ullman",
    "ullman sails",
    "jonsson",
    "genmac",
}
# Ambiguous umbrella / junk keys — never show as a named-event tile
_HIDE_SERIES_KEYS = {
    "dinghy provincial",
    "dinghy champs",
    "dinghy provincials championship",
    "wc regionals",  # class WC regionals keep their own tiles
    "national",
    "offshore",
    "interclub",
    "club",
}
# Collapse filename drift into one named-event series tile.
_SERIES_KEY_ALIASES: dict[str, str] = {
    "brass monkey sailing": "brass monkey regatta",
    "brass monkey": "brass monkey regatta",
    "formula one national": "formula 1 nationals",
    "formula one nationals": "formula 1 nationals",
    "vasco": "vasco da gama ocean race",
    "west coast offshore": "seaport supply west coast offshore",
    "seajet west coast offshore": "seaport supply west coast offshore",
    "knysna yacht club interclub": "kyc interclub",
    "10 20 canyon cup": "canyon cup offshore",
    "wc dinghy champs": "w cape championships dinghy classes",
    "western cape dinghy championships": "w cape championships dinghy classes",
    "hmyc 9hr": "hmyc 6hr 9hr race",
    "tsc 9hr": "hmyc 6hr 9hr race",
    "overberg sailing": "overberg regional champs",
    "overberg sailing champs": "overberg regional champs",
    "overberg sailing championships": "overberg regional champs",
    "overberg champs": "overberg regional champs",
    "overberg championships": "overberg regional champs",
    "mbsc interclub": "interclub",
    "mbsc interclubs": "interclub",
    "eden district inter schools": "schools dinghy sailing",
    "eden district inter schools regatta": "schools dinghy sailing",
    "eden inter schools": "schools dinghy sailing",
    "eden inter schools primary": "schools dinghy sailing",
    "eden inter schools primary school": "schools dinghy sailing",
    # Do NOT merge generic dinghy provincials — province keys stay separate
    # (gauteng dinghy provincials, ec dinghy regionals, w cape championships…).
    "cape classic": "zvyc cape classic",
    "zvyc southern charter cape classic": "zvyc cape classic",
    "southern charter cape classic": "zvyc cape classic",
    "hermanus cape classic": "hyc cape classic",
    "hobie wc regionals": "hobie wc regionals",
    "wc regionals": "wc regionals",  # umbrella only; class WC regionals keep own keys
    "08 30 triple crown 1": "triple crown",
    "11 17 triple crown": "triple crown",
    "08 17 triple crown": "triple crown",
    "10 26 triple crown": "triple crown",
    "12 31 triple crown": "triple crown",
    "09 07 triple crown 2 24 25": "triple crown",
    "mac 24 hour challenge": "mac hour challenge",
    "mac 24 hr": "mac hour challenge",
    "mac 24hr": "mac hour challenge",
    "mac 12 24hr": "mac hour challenge",
    "mac 12hr": "mac hour challenge",
    "mac 12 hour challenge": "mac hour challenge",
}

MAC_HOUR_CHALLENGE_LOGO = "/artwork/Event Logo/MAC-Hour-Challenge.png"
_MAC_HOUR_SERIES_KEY = "mac hour challenge"

# Shared artwork when a series has regattas but no dedicated logo file yet.
CAPE_CLASSIC_SERIES_LOGO = "/artwork/Event Logo/Cape-Classic-Series.png"
_CAPE_CLASSIC_SERIES_KEYS = {
    "zvyc cape classic",
    "hyc cape classic",
    "tsc cape classic",
}
_SERIES_FALLBACK_LOGO: dict[str, str] = {
    k: CAPE_CLASSIC_SERIES_LOGO for k in _CAPE_CLASSIC_SERIES_KEYS
}
_SERIES_FALLBACK_LOGO[_MAC_HOUR_SERIES_KEY] = MAC_HOUR_CHALLENGE_LOGO

_MAC_HOUR_ARTWORK_RE = re.compile(r"mac[-_\s].*(?:hour|12|24).*challenge|mac-12-hour|mac-24-hour", re.I)
_MAC_HOUR_DURATION_RE = re.compile(
    r"(?:\b|[-_/])(9|12|24)\s*(?:hr|hour)|mac[-_\s](9|12|24)",
    re.I,
)


def _mac_hour_duration_hours(regatta_id: str, event_name: str) -> str:
    """9 / 12 / 24 from regatta slug or title (MAC Hour family)."""
    blob = f"{regatta_id} {event_name}".lower().replace("_", "-")
    if re.search(r"mac-12|12[-_/]24hr|\b12\s*(?:hr|hour)", blob):
        return "12"
    m = _MAC_HOUR_DURATION_RE.search(blob)
    if m:
        return next(g for g in m.groups() if g)
    if re.search(r"\b24\b|24hr|24-hour", blob):
        return "24"
    if re.search(r"\b9\b|9hr|9-hour", blob):
        return "9"
    return ""


def _mac_hour_regatta_display_name(event_name: str, regatta_id: str = "") -> str:
    """Real edition title — never generic 'Mac Hour Challenge {year}'."""
    name = _strip_leading_iso_date((event_name or regatta_id or "").strip())
    return re.sub(r"\s+", " ", name).strip() or "MAC Hour Challenge"


def _mac_hour_regatta_logo_path(
    regatta_id: str,
    event_name: str,
    year: int | None = None,
) -> str:
    """Per-edition MAC logo (9 / 12 / 24). Catalogue header stays generic."""
    dur = _mac_hour_duration_hours(regatta_id, event_name)
    if dur == "12":
        return "/artwork/Event Logo/MAC-12-Hour-Challenge.png"
    if dur == "24":
        if year == 2024:
            return "/artwork/Event Logo/MAC-24-Hour-Challenge-2024.png"
        return "/artwork/Event Logo/MAC-24-Hour-Challenge.png"
    if dur == "9":
        return "/artwork/Event Logo/MAC-9-Hour-Challenge.png"
    return MAC_HOUR_CHALLENGE_LOGO


def _canon_series_key(key: str) -> str:
    k = re.sub(r"\s+", " ", (key or "").strip().lower())
    if re.search(r"\btripp?le\s+crown\b", k):
        return "triple crown"
    if re.search(r"\btwilight\s+series\b", k) or k == "twilight":
        return "twilight series"
    if re.search(r"\bmac\b", k) and re.search(
        r"\b(12|24)\s*(hr|hour)|hour\s+challenge|12.?24\s*hr|\bchallenge\b", k
    ):
        return _MAC_HOUR_SERIES_KEY
    return _SERIES_KEY_ALIASES.get(k, k)


def _is_named_event_tile(series_key: str, filename: str = "") -> bool:
    """False for class logos, fleet shells, sponsor-only marks, and junk sheets."""
    key = _canon_series_key(series_key)
    fname = (filename or "").rsplit("/", 1)[-1]
    if _CLASS_FLEET_FILE_RE.search(fname):
        # Keep real named events that happen to say Regionals in the file name.
        if not re.search(
            r"\b(national|championship|champs|cup|regatta|series|week|race|"
            r"classic|slam|challenge|offshore|interschool|regionals?)\b",
            key,
            re.I,
        ):
            return False
    if _CLASS_FLEET_KEY_RE.match(key):
        return False
    if key in _SPONSOR_ONLY_KEYS:
        return False
    if key in _HIDE_SERIES_KEYS:
        return False
    if key.endswith(" masters") and key != "masters nationals":
        return False
    if "illegible" in key:
        return False
    return True


def event_logo_artwork_dir(api_file: str) -> Path:
    return Path(os.path.dirname(os.path.abspath(api_file))) / "artwork" / "Event Logo"


def is_event_logo_path(path: str) -> bool:
    """True only for /artwork/Event Logo/ — class logos belong on /classes."""
    p = str(path or "").strip()
    if not p or "/artwork/Class Logo/" in p:
        return False
    return p.startswith("/artwork/Event Logo/")


def filename_to_slug(filename: str) -> str:
    stem = Path(str(filename or "")).stem
    stem = _LOGO_SUFFIX_RE.sub("", stem)
    slug = re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-")
    return slug or "event"


def path_to_slug(path: str) -> str:
    return filename_to_slug(str(path or "").rsplit("/", 1)[-1])


def clean_event_logo_label(filename_or_label: str) -> str:
    """Human label from filename/stem — never trailing 'Logo' / 'Class Logo'."""
    raw = str(filename_or_label or "").strip()
    if "/" in raw:
        raw = raw.rsplit("/", 1)[-1]
    if "." in raw and not raw.lower().endswith((" logo",)):
        raw = Path(raw).stem
    raw = raw.replace("-", " ").replace("_", " ")
    raw = _LOGO_SUFFIX_RE.sub("", raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    parts = []
    for w in raw.split():
        wu = w.upper()
        if wu in {
            "WC", "SA", "SAS", "RSA", "ILCA", "DF95", "IOM", "RS", "KZN", "EC",
            "NR", "FS", "MSC", "HMYC", "RCYC", "HYC", "FBYC", "MAC", "TSC", "PSC",
            "KYC", "MBSC", "ZYC",
        }:
            parts.append(wu)
        elif re.match(r"^[0-9]", w):
            parts.append(w)
        else:
            parts.append(w[:1].upper() + w[1:].lower())
    return " ".join(parts) or "Event"


def _series_key_from_artwork_path(path: str) -> str:
    """Map artwork filename → series_key (logo file must not define regatta membership)."""
    fname = str(path or "").rsplit("/", 1)[-1]
    stem_label = clean_event_logo_label(fname)
    fn = fname.lower()
    blob = f"{fn} {stem_label.lower()}"
    if "knysna-yacht-club-interclub" in fn or re.search(r"\bkyc[-_]interclub", fn):
        return "kyc interclub"
    if "wc-dinghy" in fn or "western-cape-dinghy" in fn:
        return "w cape championships dinghy classes"
    if re.search(r"\bhyc\b", blob) and "cape" in blob and "classic" in blob:
        return "hyc cape classic"
    if re.search(r"\bhermanus\b", blob) and "cape" in blob and "classic" in blob:
        return "hyc cape classic"
    if re.search(r"\btsc\b", blob) and "cape" in blob and "classic" in blob:
        return "tsc cape classic"
    if ("zvyc" in blob or "southern-charter" in fn or "cape-classic-series" in fn) and "cape" in blob:
        return "zvyc cape classic"
    if "triple-crown" in fn or re.search(r"\btriple\s+crown\b", stem_label, re.I):
        return "triple crown"
    if "j22-nationals" in fn or (
        re.search(r"\bj\s*-?\s*22\b|\bj22\b", blob) and re.search(r"\bnational", blob)
    ):
        return "j22 nationals"
    if "twilight-series" in fn or re.search(r"\btwilight\s+series\b", stem_label, re.I):
        return "twilight series"
    if re.search(r"\bmac\b", blob) and re.search(r"hour|12|24|challenge", blob):
        return _MAC_HOUR_SERIES_KEY
    if re.search(r"\bbrass\s+monkey\b", blob):
        return "brass monkey regatta"
    key = yearly_event_series_key(stem_label) or yearly_event_series_key(fname.replace("-", " "))
    if not key:
        key = filename_to_slug(fname).replace("-", " ")
    return _canon_series_key(key)


def _strip_leading_iso_date(blob: str) -> str:
    """Remove YYYY-MM-DD prefix from regatta slugs / dated titles before series_key."""
    s = (blob or "").strip()
    s = re.sub(r"^\d{4}-\d{2}-\d{2}[-\s]+", "", s)
    s = re.sub(r"^\d{4}-\d{2}-\d{2}\s+", "", s)
    return s.strip()


def _series_key_from_regatta_name(name: str, regatta_id: str = "") -> str:
    blob = _strip_leading_iso_date((name or "").strip())
    rid = (regatta_id or "").strip()
    if not blob:
        blob = _strip_leading_iso_date(rid)
    if not blob:
        return ""
    # Prefer host hint from slug when title is bare (e.g. "Easter Regatta" + fbyc-… id).
    hay = f"{blob} {rid}".replace("-", " ").lower()
    key = _canon_series_key(yearly_event_series_key(blob))
    if (not key or key == "easter regatta") and "easter" in hay and "fbyc" in hay:
        return "fbyc easter regatta"
    if key and "overberg" in key and ("sailing" in key or "champ" in key or "regional" in key):
        return _canon_series_key("overberg regional champs")
    if key and "mbsc" in hay and "interclub" in key.replace(" ", ""):
        return _canon_series_key("interclub")
    return key


# Umbrella series beat class/fleet spin-offs when the same parent regatta was
# proposed under multiple keys (child fleet shells must never own a tile).
_SERIES_ASSIGNMENT_PRIORITY: dict[str, int] = {
    "sa sailing youth nationals": 100,
    "w cape championships dinghy classes": 95,
    "eastern cape championships": 90,
    "gauteng dinghy provincials": 90,
    "ec dinghy regionals": 85,
    "wc regionals": 50,
    "optimist wc championships": 35,
    "optimist regionals": 30,
    "optimist nationals": 25,
    "ilca nationals": 25,
}


def _series_assignment_rank(key: str) -> tuple[int, int, str]:
    k = _canon_series_key(key)
    pri = _SERIES_ASSIGNMENT_PRIORITY.get(k, 0)
    if pri == 0 and k in SERIES_CANONICAL_LABEL:
        pri = 60
    if pri == 0 and k.endswith(" wc regionals"):
        pri = 55
    if pri == 0 and k.endswith(" nationals"):
        pri = 25
    if pri == 0:
        pri = 10
    return (pri, len(k), k)


def _resolve_parent_series_key(
    parent_rid: str,
    parent_name: str,
    candidate_keys: set[str],
) -> str:
    """One parent regatta → exactly one named-event series."""
    auth = _series_key_from_regatta_name(parent_name, parent_rid)
    if auth and _is_named_event_tile(auth):
        return auth
    if not candidate_keys:
        return auth or ""
    return max(candidate_keys, key=_series_assignment_rank)


def _structural_parent_hub(hub_index: dict[str, str]) -> dict[str, str]:
    """Keep only slug-extension fleet shells — not loose event_regatta_links hub merges."""
    out: dict[str, str] = {}
    for child, parent in (hub_index or {}).items():
        c = str(child or "").strip()
        p = str(parent or "").strip()
        if c and p and c != p and c.startswith(p + "-"):
            out[c] = p
    return out


def _is_fleet_child_rid(rid: str, hub_index: dict[str, str]) -> bool:
    rid_s = str(rid or "").strip()
    if not rid_s:
        return False
    parent = parent_regatta_id(rid_s, hub_index)
    if not parent or parent == rid_s:
        return False
    # Only structural fleet shells (slug extends parent). Hub DB links alone must not
    # hide separate parent regattas (e.g. Triple Crown legs in the same season).
    return rid_s.startswith(parent + "-")


def _header_icon_matches_series(icon_path: str, series_key: str) -> bool:
    left = (icon_path or "").strip()
    if not left or not is_event_logo_path(left):
        return False
    return _series_key_from_artwork_path(left) == _canon_series_key(series_key)


def _load_series_regatta_refs(
    *,
    read_header_icons: Callable[[], dict],
    hub_index: dict[str, str],
    closed_ids: set[str],
    table_exists: Callable[[str], bool],
    get_db_connection: Callable[[], Any],
    return_db_connection: Callable[[Any], None],
) -> dict[str, list[dict[str, Any]]]:
    """series_key → parent regatta refs (one parent → one series; no fleet children)."""
    proposals: dict[str, set[str]] = {}
    parent_names: dict[str, str] = {}

    def _note_parent(rid: str, event_name: str = "") -> str:
        rid_s = str(rid or "").strip()
        if not rid_s:
            return ""
        parent = parent_regatta_id(rid_s, hub_index)
        if event_name:
            prev = parent_names.get(parent, "")
            if not prev or len(event_name) > len(prev):
                parent_names[parent] = event_name.strip()
        return parent

    def _propose(key: str, rid: str, event_name: str = "") -> None:
        key = _canon_series_key(key)
        if not key or not _is_named_event_tile(key):
            return
        parent = _note_parent(rid, event_name)
        if not parent:
            return
        proposals.setdefault(parent, set()).add(key)

    if table_exists("regattas"):
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            if table_exists("events"):
                cur.execute(
                    """
                    SELECT e.series_key, e.regatta_id::text AS regatta_id, e.event_name
                    FROM events e
                    WHERE COALESCE(NULLIF(btrim(e.series_key), ''), '') <> ''
                       OR COALESCE(NULLIF(btrim(e.event_name), ''), '') <> ''
                    """
                )
                for row in cur.fetchall() or []:
                    rid = str(row.get("regatta_id") or "").strip()
                    if not rid:
                        continue
                    parent = _note_parent(rid, str(row.get("event_name") or ""))
                    en = str(row.get("event_name") or "").strip()
                    # Calendar series_key is a hint only — parent regatta name is authoritative.
                    if en:
                        sk2 = _series_key_from_regatta_name(en, parent)
                        if sk2:
                            _propose(sk2, parent, en)
                    else:
                        sk = _canon_series_key(str(row.get("series_key") or ""))
                        if sk:
                            _propose(sk, parent)

            cur.execute(
                """
                SELECT DISTINCT r.regatta_id::text AS regatta_id, r.event_name
                FROM regattas r
                WHERE COALESCE(NULLIF(btrim(r.event_name), ''), '') <> ''
                  AND EXISTS (
                      SELECT 1 FROM results res
                      WHERE res.regatta_id = r.regatta_id
                  )
                """
            )
            for row in cur.fetchall() or []:
                rid = str(row.get("regatta_id") or "").strip()
                en = str(row.get("event_name") or "").strip()
                if _is_fleet_child_rid(rid, hub_index):
                    continue
                sk = _series_key_from_regatta_name(en, rid)
                if sk:
                    _propose(sk, rid, en)
        finally:
            cur.close()
            return_db_connection(conn)

    icons = read_header_icons() or {}
    icon_rids: list[str] = []
    for rid, cfg in icons.items():
        if not isinstance(cfg, dict):
            continue
        left = cfg.get("left")
        if isinstance(left, str) and is_event_logo_path(left.strip()):
            icon_rids.append(str(rid).strip())
    if icon_rids and table_exists("regattas"):
        meta = _regatta_meta(icon_rids, table_exists, get_db_connection, return_db_connection)
        for rid in icon_rids:
            display_rid = parent_regatta_id(rid, hub_index)
            m = meta.get(display_rid) or meta.get(rid) or {}
            en = str(m.get("event_name") or display_rid or rid).strip()
            parent_names.setdefault(display_rid, en)
            sk = _series_key_from_regatta_name(en, display_rid)
            if sk:
                _propose(sk, display_rid, en)

    # Fill missing parent names for exclusive resolution.
    missing = [p for p in proposals if p not in parent_names]
    if missing and table_exists("regattas"):
        meta = _regatta_meta(missing, table_exists, get_db_connection, return_db_connection)
        for pid, m in meta.items():
            parent_names.setdefault(pid, str(m.get("event_name") or pid))

    out: dict[str, list[dict[str, Any]]] = {}
    seen_by_key: dict[str, set[str]] = {}
    for parent_rid, keys in proposals.items():
        pname = parent_names.get(parent_rid) or parent_rid
        best = _resolve_parent_series_key(parent_rid, pname, keys)
        if not best or not _is_named_event_tile(best):
            continue
        seen = seen_by_key.setdefault(best, set())
        if parent_rid in seen:
            continue
        seen.add(parent_rid)
        out.setdefault(best, []).append(
            {
                "regatta_id": parent_rid,
                "closed": parent_rid in closed_ids,
            }
        )
    return out


def _qualifies_as_named_event_series(
    key: str,
    refs: list[dict[str, Any]],
    artwork_paths: list[str],
) -> bool:
    """Tile when canonical label + artwork, or artwork + refs, or ≥2 editions."""
    key = _canon_series_key(key)
    if not key or not _is_named_event_tile(key):
        return False
    n = len(refs or [])
    art = list(artwork_paths or [])
    if not art and key in _SERIES_FALLBACK_LOGO:
        art = [_SERIES_FALLBACK_LOGO[key]]
    try:
        if key in SERIES_CANONICAL_LABEL and art:
            return True
    except NameError:
        pass
    if n <= 0:
        return bool(art)
    if art:
        return True
    return n >= 2


def _artwork_paths_by_series_key(
    all_paths: list[str],
) -> dict[str, list[str]]:
    artwork: dict[str, list[str]] = {}
    for path in all_paths:
        fname = path.rsplit("/", 1)[-1]
        key = _series_key_from_artwork_path(path)
        if not key or not _is_named_event_tile(key, fname):
            continue
        artwork.setdefault(key, []).append(path)
    return artwork


def gallery_rows(
    *,
    read_header_icons: Callable[[], dict],
    table_exists: Callable[[str], bool],
    get_db_connection: Callable[[], Any],
    return_db_connection: Callable[[Any], None],
    api_file: str,
    class_logo_path_for_name: Callable[[str], str | None] | None = None,
) -> list[dict[str, Any]]:
    icons = read_header_icons() or {}
    icon_rids = [str(k).strip() for k in icons.keys() if str(k).strip()]
    hub = load_hub_master_index(table_exists, get_db_connection, return_db_connection)
    # Fleet shells (…-open, …-ilca-6, …) → parent: host/date live on parent only
    fleet = load_fleet_shell_parent_index(
        icon_rids, table_exists, get_db_connection, return_db_connection
    )
    hub = {**hub, **fleet}
    hub_series = _structural_parent_hub(hub)
    closed_ids = load_closed_regatta_ids(table_exists, get_db_connection, return_db_connection)
    usage = _usage_index(lambda: icons, hub, closed_ids)
    dir_path = event_logo_artwork_dir(api_file)
    on_disk: dict[str, Path] = {}
    if dir_path.is_dir():
        for p in sorted(dir_path.iterdir()):
            if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}:
                on_disk[f"/artwork/Event Logo/{p.name}"] = p
    all_paths = sorted(set(on_disk) | set(usage))
    try:
        from backfill_event_edition_classes import load_series_aliases, load_series_sponsors
        aka_by_key = load_series_aliases() or {}
        sponsors_by_key = load_series_sponsors() or {}
    except Exception:
        aka_by_key = {}
        sponsors_by_key = {}

    # Regatta membership = series_key from event names (not logo file path).
    refs_by_key = _load_series_regatta_refs(
        read_header_icons=read_header_icons,
        hub_index=hub_series,
        closed_ids=closed_ids,
        table_exists=table_exists,
        get_db_connection=get_db_connection,
        return_db_connection=return_db_connection,
    )
    artwork_by_key = _artwork_paths_by_series_key(all_paths)
    # MAC Hour files must always resolve to one named-event tile (12hr + 24hr editions).
    _mac_paths = [
        p for p in all_paths
        if _MAC_HOUR_ARTWORK_RE.search(p.rsplit("/", 1)[-1])
    ]
    if _mac_paths:
        artwork_by_key.setdefault(_MAC_HOUR_SERIES_KEY, [])
        for p in sorted(set(_mac_paths)):
            if p not in artwork_by_key[_MAC_HOUR_SERIES_KEY]:
                artwork_by_key[_MAC_HOUR_SERIES_KEY].append(p)
    # Brass Monkey: merge Regatta + Sailing artwork under one series.
    _brass_paths = [p for p in all_paths if "brass-monkey" in p.lower()]
    if _brass_paths:
        artwork_by_key.setdefault("brass monkey regatta", [])
        for p in sorted(set(_brass_paths)):
            if p not in artwork_by_key["brass monkey regatta"]:
                artwork_by_key["brass monkey regatta"].append(p)
    all_keys = sorted(set(refs_by_key) | set(artwork_by_key))
    all_keys = [
        k
        for k in all_keys
        if _qualifies_as_named_event_series(k, refs_by_key.get(k) or [], artwork_by_key.get(k) or [])
    ]

    calendar_by_key = _load_series_calendar_events(
        all_keys, table_exists, get_db_connection, return_db_connection
    )

    # Collect all regatta ids for meta lookup.
    all_rids = []
    for refs in refs_by_key.values():
        for u in refs:
            all_rids.append(u["regatta_id"])
    meta_by_rid = _regatta_meta(all_rids, table_exists, get_db_connection, return_db_connection)

    rows: list[dict[str, Any]] = []
    seen_slugs: set[str] = set()
    for key in all_keys:
        g_paths = artwork_by_key.get(key) or []
        if not g_paths and key in _SERIES_FALLBACK_LOGO:
            g_paths = [_SERIES_FALLBACK_LOGO[key]]
        path = pick_series_logo_path(g_paths, prefer_key=key) if g_paths else ""
        if key in _CAPE_CLASSIC_SERIES_KEYS:
            path = CAPE_CLASSIC_SERIES_LOGO
            g_paths = [CAPE_CLASSIC_SERIES_LOGO]
        if key == _MAC_HOUR_SERIES_KEY:
            path = MAC_HOUR_CHALLENGE_LOGO
            g_paths = sorted(
                {
                    MAC_HOUR_CHALLENGE_LOGO,
                    "/artwork/Event Logo/MAC-12-Hour-Challenge.png",
                    "/artwork/Event Logo/MAC-24-Hour-Challenge.png",
                    "/artwork/Event Logo/MAC-24-Hour-Challenge-2024.png",
                    *g_paths,
                }
            )
        class_lp = _series_class_logo_path(key, class_logo_path_for_name)
        if class_lp:
            path = class_lp
        if not path:
            for u in refs_by_key.get(key) or []:
                rid = str(u.get("regatta_id") or "").strip()
                for try_rid in (rid,):
                    cfg = icons.get(try_rid)
                    if not isinstance(cfg, dict):
                        continue
                    left = (cfg.get("left") or "").strip()
                    if left and _header_icon_matches_series(left, key):
                        path = left if left.startswith("/") else f"/{left.lstrip('/')}"
                        g_paths = [path]
                        break
                if path:
                    break
        if not path:
            continue
        fname = path.rsplit("/", 1)[-1]
        label = canonical_series_label(key, "") or _label_from_series_key(key) or clean_event_logo_label(fname)
        slug = series_key_to_slug(key)
        if slug in seen_slugs:
            slug = f"{slug}-{len(seen_slugs)}"
        seen_slugs.add(slug)
        raw_entries = []
        seen_rids: set[str] = set()
        for u in refs_by_key.get(key) or []:
            rid = str(u.get("regatta_id") or "").strip()
            if not rid or rid in seen_rids:
                continue
            seen_rids.add(rid)
            meta = meta_by_rid.get(rid, {})
            raw_entries.append(
                {
                    "regatta_id": rid,
                    "event_name": meta.get("event_name") or rid,
                    "year": meta.get("year"),
                    "closed": u.get("closed") or rid in closed_ids,
                    "host_abbrev": meta.get("host_abbrev") or "",
                    "date_label": meta.get("date_label") or "",
                    "start_date": meta.get("start_date"),
                }
            )
        regattas = collapse_to_parent_regattas(raw_entries, hub_series, closed_ids)
        for rg in regattas:
            meta = meta_by_rid.get(rg["regatta_id"], {})
            rg["host_abbrev"] = meta.get("host_abbrev") or ""
            rg["date_label"] = meta.get("date_label") or ""
            rg["start_date"] = meta.get("start_date")
            if not rg.get("closed"):
                rg["closed"] = rg["regatta_id"] in closed_ids
        regattas = _merge_missing_edition_years(regattas, calendar_by_key.get(key) or [])
        regattas = _one_row_per_edition_year(regattas)
        regattas.sort(key=lambda rg: edition_year_of(rg) or 0, reverse=True)
        filename_slugs = sorted(
            {filename_to_slug(p.rsplit("/", 1)[-1]) for p in g_paths if p}
        )
        aliases = sorted({s for s in filename_slugs if s and s != slug})
        artwork_years = sorted(
            {
                _year_in_filename(p.rsplit("/", 1)[-1])
                for p in g_paths
                if _year_in_filename(p.rsplit("/", 1)[-1])
            }
        )
        db_aka = aka_by_key.get(key) or []
        aka = []
        seen_aka = set()
        for n in list(db_aka):
            low = n.strip().lower()
            if not low or low == label.lower() or low in seen_aka:
                continue
            seen_aka.add(low)
            aka.append(n.strip())
        rows.append(
            {
                "path": path,
                "filename": fname,
                "slug": slug,
                "url": f"/events-logos/{slug}",
                "label": label,
                "on_disk": path in on_disk or _public_artwork_exists(api_file, path),
                "regattas": regattas,
                "event_count": len(regattas),
                "series_key": key,
                "logo_paths": g_paths,
                "aliases": aliases,
                "artwork_years": artwork_years,
                "aka_names": aka,
                "sponsors_by_year": sponsors_by_key.get(key) or {},
            }
        )
    def _keep_gallery_row(r: dict) -> bool:
        if int(r.get("event_count") or 0) > 0:
            return True
        sk = _canon_series_key(str(r.get("series_key") or ""))
        if sk == _MAC_HOUR_SERIES_KEY:
            return True
        path = str(r.get("path") or "")
        if path.startswith("/artwork/Event Logo/") and r.get("on_disk"):
            return True
        return False

    rows = [r for r in rows if _keep_gallery_row(r)]
    # One tile per series_key (filename drift must not duplicate tiles).
    by_series: dict[str, dict[str, Any]] = {}
    for r in rows:
        sk = _canon_series_key(str(r.get("series_key") or ""))
        prev = by_series.get(sk)
        if not prev or int(r.get("event_count") or 0) > int(prev.get("event_count") or 0):
            by_series[sk] = r
    rows = list(by_series.values())
    rows.sort(key=lambda r: (-r["event_count"], r["label"].lower()))
    return rows


def row_by_slug(slug: str, **deps: Any) -> dict[str, Any] | None:
    want = (slug or "").strip().lower().strip("/")
    if not want:
        return None
    base, _year = split_slug_year(want)
    for row in gallery_rows(**deps):
        row_slug = (row.get("slug") or "").lower()
        aliases = {str(a).lower() for a in (row.get("aliases") or [])}
        if want == row_slug or base == row_slug or want in aliases or base in aliases:
            return row
    return None


def gallery_about(rows: list[dict[str, Any]] | None = None) -> str:
    if rows is None:
        rows = []
    used = sum(1 for r in rows if r.get("event_count"))
    return (
        f"{len(rows)} named event(s) · {used} with linked result years. "
        f"Click a logo for all years / hosts of that master event. "
        f"Calendar & general listings stay on /events. "
        f"Class logos are on /classes."
    )


def gallery_extra_css() -> str:
    return POPOVER_CSS


def gallery_grid_html(rows: list[dict[str, Any]]) -> str:
    tiles: list[str] = []
    for row in rows:
        path = html_module.escape(row["path"])
        label = html_module.escape(row["label"])
        if row["on_disk"]:
            logo_html = f'<img src="{path}" alt="{label}" class="dlg-logo" loading="lazy">'
        else:
            logo_html = '<span class="dlg-missing" style="font-size:0.75rem;color:#b45309;">missing file</span>'
        tiles.append(
            render_logo_grid_tile(
                href=row.get("url") or f"/events-logos/{row.get('slug')}",
                label=row["label"],
                logo_html=logo_html,
                regattas=row["regattas"],
            )
        )
    body = "\n".join(tiles) if tiles else "<p>No event logos found.</p>"
    return f'<div class="dlg-grid">{body}</div>'


def page_html(rows: list[dict[str, Any]] | None = None, **deps: Any) -> str:
    if rows is None:
        rows = gallery_rows(**deps)
    about = gallery_about(rows)
    grid = gallery_grid_html(rows)
    return (
        "<!DOCTYPE html><html lang=\"en-US\"><head><meta charset=\"UTF-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1.0\">"
        "<title>Named Events – SailingSA</title>"
        "<link rel=\"canonical\" href=\"https://sailingsa.co.za/events-logos\">"
        "<link rel=\"icon\" href=\"/favicon.ico\" sizes=\"any\">"
        "<link rel=\"apple-touch-icon\" href=\"/apple-touch-icon.png\">"
        "<link rel=\"stylesheet\" href=\"/css/main.css\">"
        "<style>"
        ".elg-page{max-width:1100px;margin:0 auto;padding:2rem 1.25rem;}"
        ".elg-page h1{font-size:1.6rem;color:#001f3f;margin:0 0 0.5rem;}"
        ".elg-intro{color:#334155;line-height:1.5;margin:0 0 1.5rem;}"
        ".return-home-btn{display:inline-flex;align-items:center;justify-content:center;padding:0.65rem 1rem;margin:0 0 1rem 0;border-radius:10px;border:1px solid #1a365d;background:#1a365d;color:#fff !important;font-weight:800;text-decoration:none !important;}"
        ".return-home-btn:hover{background:#24466b;border-color:#24466b;}"
        f"{gallery_extra_css()}"
        "</style></head><body>"
        f"{_site_header_nav()}"
        "<main class=\"main-content\"><div class=\"container\"><div class=\"card elg-page\">"
        "<a class=\"return-home-btn\" href=\"/\">Return Home</a>"
        "<h1>Named Events</h1>"
        f"<p class=\"elg-intro\">{html_module.escape(about)}</p>"
        f"{grid}"
        "</div></div></main>"
        f"{_site_footer()}"
        "</body></html>"
    )


def _detail_page_build(slug: str, year: int | None = None, **deps: Any) -> tuple[str, str, str] | None:
    """Gold-std event-logo page: header + host logos + events table (club-page pattern).

    Per-year child URLs are not used: results go to /regatta/{id}, sponsors expand on this parent.
    """
    year = None
    base_slug, slug_year = split_slug_year(slug)
    row = row_by_slug(slug, **deps)
    if not row:
        return None
    series_slug = row["slug"]
    series_label = row["label"]
    path = row["path"]
    all_regattas = row.get("regattas") or []
    sponsors = row.get("sponsors_by_year") or {}
    if year:
        sp = sponsors.get(int(year)) or sponsors.get(str(year)) or ""
        regattas = [rg for rg in all_regattas if edition_year_of(rg) == int(year)]
        if not regattas and not slug_year:
            art = row.get("artwork_years") or []
            if int(year) not in art:
                return None
        label = edition_display_name(series_label, int(year), sp)
        canonical_path = edition_url(series_slug, int(year))
    else:
        regattas = all_regattas
        label = series_label
        canonical_path = f"/events-logos/{series_slug}"
    regattas = _one_row_per_edition_year(regattas)
    regattas.sort(key=lambda rg: edition_year_of(rg) or 0, reverse=True)
    path_esc = html_module.escape(path)
    label_esc = html_module.escape(label)
    n = len(regattas)
    aka_names = row.get("aka_names") or []

    # Host club chips: most recent host first, oldest last
    host_latest: dict[str, int] = {}
    for rg in regattas:
        ab = (rg.get("host_abbrev") or "").strip().upper()
        if not ab:
            continue
        ey = edition_year_of(rg) or 0
        if ey >= host_latest.get(ab, -1):
            host_latest[ab] = ey
    host_chips = []
    for ab in sorted(host_latest, key=lambda a: (-host_latest[a], a)):
        host_chips.append(
            f'<a class="club-story-chip" href="/club/{html_module.escape(ab)}" title="{html_module.escape(ab)}">'
            f'<img src="/api/club-logo/{html_module.escape(ab)}" alt="{html_module.escape(ab)}" '
            f'loading="lazy" decoding="async" onerror="this.style.display=\'none\'" />'
            f'<span class="club-story-chip-label">{html_module.escape(ab)}</span></a>'
        )
    hosts_row = ""
    if host_chips:
        hosts_row = (
            '<div class="club-story-logo-row">'
            '<div class="club-story-logo-row-label">Host clubs</div>'
            f'<div class="club-story-logo-chips">{"".join(host_chips)}</div></div>'
        )
    sponsors_row = _sponsors_row_html(row.get("series_key") or "", series_slug, year)

    # Events table (gold std club table)
    tbody = []
    for i, rg in enumerate(regattas, start=1):
        rid = str(rg.get("regatta_id") or "").strip()
        rid_esc = html_module.escape(rid)
        ey = edition_year_of(rg)
        sp = (row.get("sponsors_by_year") or {}).get(ey) or (row.get("sponsors_by_year") or {}).get(str(ey) or "") or ""
        series_key = _canon_series_key(str(row.get("series_key") or ""))
        if series_key == _MAC_HOUR_SERIES_KEY:
            row_label = _mac_hour_regatta_display_name(str(rg.get("event_name") or ""), rid)
            row_logo = _mac_hour_regatta_logo_path(rid, str(rg.get("event_name") or ""), ey)
        else:
            row_label = edition_display_name(series_label, ey, sp)
            row_logo = path
        ename = html_module.escape(row_label)
        row_logo_esc = html_module.escape(row_logo)
        date_l = html_module.escape(str(rg.get("date_label") or ey or "—"))
        host = (rg.get("host_abbrev") or "").strip().upper()
        host_html = "—"
        if host:
            host_esc = html_module.escape(host)
            host_html = (
                f'<img src="/api/club-logo/{host_esc}" alt="" class="row-logo" '
                f'onerror="this.style.display=\'none\'">'
                f'<a href="/club/{host_esc}">{host_esc}</a>'
            )
        tag = ""
        results_href = f"/regatta/{rid_esc}" if rid else ""
        if rid:
            if rg.get("closed"):
                tag = f' <a href="{results_href}" class="dlg-tag">results</a>'
            else:
                tag = f' <a href="{results_href}" class="elg-regatta-link">open</a>'
        if results_href:
            name_html = f'<a href="{results_href}">{ename}</a>{tag}'
        else:
            name_html = f'<span class="elg-year-plain">{ename}</span>'
        toggle_html = ""
        panel_html = ""
        if not year and ey:
            sp_rows = _year_sponsor_rows(row.get("series_key") or "", series_slug, int(ey))
            if sp_rows:
                chips = []
                for item in sp_rows:
                    sh = html_module.escape(f"/sponsors/{item['slug']}")
                    sn = html_module.escape(item["name"])
                    sl = html_module.escape(item["logo"])
                    img = (
                        f'<img src="{sl}" alt="" loading="lazy" decoding="async" onerror="this.style.display=\'none\'">'
                        if sl else ""
                    )
                    chips.append(
                        f'<a class="club-story-chip" href="{sh}" title="{sn}">'
                        f"{img}<span class=\"club-story-chip-label\">{sn}</span></a>"
                    )
                toggle_html = (
                    '<button type="button" class="elg-sp-toggle" aria-expanded="false" aria-label="Show sponsors">'
                    '<span class="elg-sp-arrow" aria-hidden="true"></span>'
                    '<span class="elg-sp-label">Sponsors</span></button>'
                )
                panel_html = (
                    f'<tr class="elg-sp-panel" hidden><td colspan="4">'
                    f'<div class="club-story-logo-chips elg-year-sponsors">{"".join(chips)}</div>'
                    f"</td></tr>"
                )
        search = html_module.escape(
            f"{ename} {host} {rg.get('date_label') or ''} {ey or ''} {' '.join(aka_names)}".lower()
        )
        tbody.append(
            f'<tr class="elg-year-row" data-search="{search}">'
            f"<td>{i}</td>"
            f'<td class="cell-left">'
            f'<img src="{row_logo_esc}" alt="" class="row-logo" onerror="this.style.display=\'none\'">'
            f'{name_html}{toggle_html}'
            f"</td>"
            f'<td class="cell-left">{host_html}</td>'
            f"<td>{date_l}</td>"
            f"</tr>{panel_html}"
        )
    if tbody:
        table_html = (
            '<div class="section-heading-row">'
            f'<h2 class="section-title">Result years ({n})</h2>'
            '<input type="search" class="club-table-filter" data-table="elg-events-table" '
            'placeholder="Search result years…" autocomplete="off"></div>'
            '<div class="table-container club-table-scroll">'
            '<table class="table" id="elg-events-table">'
            "<thead><tr>"
            "<th>#</th><th>Result year</th><th>Host</th><th>Date</th>"
            "</tr></thead>"
            f"<tbody>{''.join(tbody)}</tbody></table></div>"
        )
    else:
        table_html = (
            '<div class="section-heading-row"><h2 class="section-title">Result years (0)</h2></div>'
            "<p>No linked result pages yet for this named event.</p>"
        )

    meta_bits = [f"{n} result year{'s' if n != 1 else ''}"]
    if host_latest:
        meta_bits.append(f"{len(host_latest)} host club{'s' if len(host_latest) != 1 else ''}")
    result_years = {edition_year_of(rg) for rg in regattas}
    result_years.discard(None)
    aka_source = row.get("aka_names") or []
    if year:
        aka_clean = _clean_aka_names(aka_source, series_label, {int(year)})
    else:
        aka_clean = _clean_aka_names(aka_source, series_label, {int(y) for y in result_years if y})
    meta_line = " · ".join(meta_bits)
    aka_html = ""
    if aka_clean:
        meta_line = meta_line + " · also known as:"
        bits = []
        for i, name in enumerate(aka_clean, 1):
            label_n = name if name.endswith(".") else f"{name}."
            bits.append(f'<span class="elg-aka-item">{i}. {html_module.escape(label_n)}</span>')
        aka_html = f'<p class="elg-aka">{"".join(bits)}</p>'

    crumb = (
        f'<p class="elg-crumb"><a href="/events-logos">Named Events</a> / '
        f'<a href="/events-logos/{html_module.escape(series_slug)}">{html_module.escape(series_label)}</a>'
        + (f" / {html_module.escape(str(year))}" if year else "")
        + "</p>"
    )
    if not year:
        crumb = f'<p class="elg-crumb"><a href="/events-logos">Named Events</a> / {label_esc}</p>'

    inner = (
        f'<div class="container"><div class="card club-page elg-detail-page">'
        f"  {crumb}"
        f'  <div class="header club-page-header club-story-header">'
        f'    <div class="club-story-inner">'
        f'      <div class="club-story-title-row">'
        f"        <h1>{label_esc}</h1>"
        f'        <div class="club-page-logo-wrap">'
        f'          <img src="{path_esc}" alt="{label_esc}" class="club-page-logo-img" loading="lazy">'
        f"        </div>"
        f"      </div>"
        f'      <p class="club-story-meta">{html_module.escape(meta_line)}</p>'
        f"      {aka_html}"
        f"      {hosts_row}"
        f"      {sponsors_row}"
        f"    </div>"
        f"  </div>"
        f"  {table_html}"
        f"</div></div>"
        f"{detail_page_script()}"
    )
    title = f"{label} | Named Events | SailingSA"
    return title, canonical_path, inner


def detail_page_script() -> str:
    return """
<script>
(function(){
  var inp=document.querySelector('.club-table-filter[data-table="elg-events-table"]');
  var table=document.getElementById('elg-events-table');
  if(inp&&table){
    inp.addEventListener('input', function(){
      var q=(inp.value||'').toLowerCase().trim();
      table.querySelectorAll('tbody tr.elg-year-row').forEach(function(tr){
        var hay=tr.getAttribute('data-search')||tr.textContent.toLowerCase();
        var show=!q||hay.indexOf(q)!==-1;
        tr.style.display=show?'':'none';
        var panel=tr.nextElementSibling;
        if(panel&&panel.classList.contains('elg-sp-panel')&&!show){
          panel.hidden=true;
          var btn=tr.querySelector('.elg-sp-toggle');
          if(btn){
            btn.classList.remove('is-open');
            btn.setAttribute('aria-expanded','false');
            var lab=btn.querySelector('.elg-sp-label');
            if(lab) lab.textContent='Sponsors';
          }
        }
      });
    });
  }
  document.querySelectorAll('.elg-sp-toggle').forEach(function(btn){
    btn.addEventListener('click', function(ev){
      ev.preventDefault();
      ev.stopPropagation();
      var tr=btn.closest('tr');
      var panel=tr&&tr.nextElementSibling;
      if(!panel||!panel.classList.contains('elg-sp-panel')) return;
      var open=panel.hidden;
      panel.hidden=!open;
      btn.classList.toggle('is-open', open);
      btn.setAttribute('aria-expanded', open?'true':'false');
      var lab=btn.querySelector('.elg-sp-label');
      if(lab) lab.textContent=open?'Hide':'Sponsors';
    });
  });
})();
</script>"""


def detail_page_parts(slug: str, year: int | None = None, **deps: Any) -> tuple[str, str, str] | None:
    return _detail_page_build(slug, year=year, **deps)


def detail_page_html(slug: str, year: int | None = None, **deps: Any) -> str | None:
    built = _detail_page_build(slug, year=year, **deps)
    if not built:
        return None
    title, canonical_path, inner = built
    label_esc = html_module.escape(title.split(" | ")[0])
    return f"""<!DOCTYPE html>
<html lang="en-US">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{html_module.escape(title)}</title>
<link rel="canonical" href="https://sailingsa.co.za{html_module.escape(canonical_path)}">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="stylesheet" href="/css/main.css">
<style>
{_DETAIL_CSS}
</style>
</head>
<body>
{_site_header_nav()}
<main class="main-content">{inner}</main>
{_site_footer()}
</body></html>"""


def detail_extra_css() -> str:
    return _DETAIL_CSS


_DETAIL_CSS = """
.elg-detail-page{max-width:1100px;margin:0 auto;padding:2rem 1.25rem;}
.elg-crumb{margin:0 0 1rem;font-size:0.9rem;color:#64748b;}
.elg-crumb a{color:#001f3f;text-decoration:none;font-weight:600;}
.elg-crumb a:hover{text-decoration:underline;color:#e65100;}
.club-page .club-story-header{display:flex;flex-direction:column;align-items:center;gap:0;margin:0 0 1.5rem 0;padding:0 0 1.35rem 0;border-bottom:2px solid #e2e8f0;text-align:center;}
.club-page .club-story-inner{width:100%;max-width:42rem;margin:0 auto;display:flex;flex-direction:column;align-items:center;gap:0.85rem;}
.club-page .club-story-title-row{display:flex;flex-direction:column;align-items:center;gap:0.75rem;width:100%;}
.club-page .club-story-header h1{text-align:center;width:100%;font-size:1.75rem;font-weight:700;margin:0;color:#001f3f;line-height:1.25;}
.club-page .club-page-logo-wrap{display:flex;justify-content:center;}
.club-page .club-page-logo-img{display:block;width:auto;max-width:min(220px,100%);height:auto;max-height:120px;object-fit:contain;}
.club-page .club-story-meta{margin:0;color:#475569;font-size:0.95rem;font-weight:600;text-align:center;}
.elg-aka{margin:0.15rem 0 0;max-width:42rem;color:#475569;font-size:0.8rem;line-height:1.4;font-weight:600;text-align:center;}
.elg-aka-item{display:inline;margin:0 0.7em 0 0;}
.club-page .club-story-logo-row{width:100%;}
.club-page .club-story-logo-row-label{font-size:0.72rem;font-weight:700;text-transform:uppercase;letter-spacing:0.04em;color:#64748b;margin:0 0 0.45rem 0;text-align:center;}
.club-page .club-story-logo-chips{display:flex;flex-wrap:wrap;gap:0.65rem 0.7rem;align-items:stretch;justify-content:center;}
.club-page .club-story-chip{display:inline-flex;flex-direction:column;align-items:center;justify-content:flex-start;gap:0.35rem;width:6.1rem;max-width:6.1rem;min-height:5.6rem;padding:0.55rem 0.4rem 0.5rem;border:1px solid #dbe5ef;border-radius:10px;background:#fff;text-decoration:none;color:#001f3f;box-sizing:border-box;}
.club-page .club-story-chip img{display:block;width:auto;height:48px;max-width:76px;object-fit:contain;}
.club-page .club-story-chip-label{font-size:0.65rem;line-height:1.15;text-align:center;color:#475569;}
.club-page a.club-story-chip:hover{border-color:#1a2750;box-shadow:0 2px 8px rgba(26,39,80,.12);color:#e65100;}.club-page a.club-story-chip:hover img{opacity:0.9;}
.club-page a.club-story-chip:hover .club-story-chip-label{text-decoration:underline;color:#001f3f;}
.club-page .section-heading-row{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:0.75rem;margin:1.25rem 0 0.65rem;}
.club-page .section-title{margin:0;font-size:1.15rem;color:#001f3f;}
.club-page .club-table-filter{min-width:12rem;padding:0.4rem 0.65rem;border:1px solid #cbd5e1;border-radius:6px;}
.club-page .table-container{overflow-x:auto;}
.club-page table.table{width:100%;border-collapse:collapse;}
.club-page table.table th,.club-page table.table td{padding:0.55rem 0.65rem;border-bottom:1px solid #e2e8f0;vertical-align:middle;}
.club-page table.table th{text-align:left;font-size:0.8rem;text-transform:uppercase;letter-spacing:.03em;color:#64748b;}
.club-page .cell-left{text-align:left;}
.club-page .row-logo{display:inline-block;width:auto;height:28px;max-width:40px;object-fit:contain;vertical-align:middle;margin-right:0.45rem;}
.elg-year-plain{color:inherit;font:inherit;font-weight:inherit;text-decoration:none;cursor:default;}
.elg-sp-toggle{display:inline-flex;align-items:center;gap:5px;margin-left:8px;border:0;background:transparent;padding:2px 0;cursor:pointer;color:#e65100;font-weight:800;font-size:0.78rem;vertical-align:middle;line-height:1;}
.elg-sp-arrow{width:0;height:0;border-left:6px solid transparent;border-right:6px solid transparent;border-top:8px solid #e65100;}
.elg-sp-toggle.is-open .elg-sp-arrow{border-top:0;border-bottom:8px solid #e65100;}
.elg-sp-panel td{background:#f8fafc;padding:0.65rem 0.65rem 0.85rem;}
.elg-year-sponsors{justify-content:flex-start;}
.dlg-tag{font-size:0.65rem;background:#166534;color:#dcfce7;border-radius:3px;padding:0 0.25rem;margin-left:0.2rem;text-decoration:none;}
.elg-regatta-link{font-size:0.75rem;margin-left:0.35rem;color:#64748b;}
"""


def _site_header_nav() -> str:
    return (
        '<header class="site-header"><div class="container" style="display:flex;align-items:center;flex-wrap:wrap;gap:0.75rem;">'
        '<a href="/" class="logo js-go-home" title="Home"><img src="/assets/logos/sailingsa-logo.png" alt="SailingSA Logo"></a>'
        '<nav class="nav-inline" aria-label="Main" style="display:flex;align-items:center;gap:0.75rem;flex-wrap:wrap;margin-right:auto;">'
        '<a href="/">Home</a><a href="/sailors">Sailors</a><a href="/regattas">Regattas</a>'
        '<a href="/classes">Classes</a><a href="/clubs">Clubs</a><a href="/events">Events</a>'
        '<a href="/events-logos">Named Events</a><a href="/stats">Statistics</a><a href="/about">About</a>'
        '</nav><div class="header-auth" style="margin-left:auto;"></div></div></header>'
    )


def _site_footer() -> str:
    return (
        '<footer class="site-footer-about" style="text-align:center;padding:2rem 1rem;font-size:0.9rem;color:#666;'
        'border-top:1px solid #e0e0e0;margin-top:2rem;">'
        'SailingSA – South African Sailing Results Database © <span id="year"></span></footer>'
        '<script>document.getElementById("year").textContent=new Date().getFullYear();</script>'
    )


def _usage_index(
    read_header_icons: Callable[[], dict],
    hub_index: dict[str, str],
    closed_ids: set[str],
) -> dict[str, list[dict]]:
    icons = read_header_icons()
    usage: dict[str, list[dict]] = {}
    for rid, cfg in icons.items():
        if not isinstance(cfg, dict):
            continue
        rid_s = str(rid).strip()
        if not rid_s:
            continue
        left = cfg.get("left")
        if isinstance(left, str) and is_event_logo_path(left):
            display_rid = parent_regatta_id(rid_s, hub_index)
            usage.setdefault(left.strip(), []).append(
                {
                    "regatta_id": display_rid,
                    "role": "main header (left)",
                    "closed": rid_s in closed_ids or display_rid in closed_ids,
                }
            )
    return usage


def _format_date_label(start_date, end_date) -> str:
    def _fmt(d):
        if d is None:
            return ""
        try:
            return d.strftime("%d %b %Y")
        except Exception:
            return str(d)[:10]

    s = _fmt(start_date)
    e = _fmt(end_date)
    if s and e and s != e:
        return f"{s} – {e}"
    return s or e or ""


def _regatta_meta(
    regatta_ids: list[str],
    table_exists: Callable[[str], bool],
    get_db_connection: Callable[[], Any],
    return_db_connection: Callable[[Any], None],
) -> dict[str, dict[str, Any]]:
    meta: dict[str, dict[str, Any]] = {}
    ids = [str(x).strip() for x in regatta_ids if str(x).strip()]
    if not ids or not table_exists("regattas"):
        return meta
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            SELECT r.regatta_id::text,
                   r.event_name,
                   r.start_date,
                   r.end_date,
                   EXTRACT(YEAR FROM COALESCE(r.end_date, r.start_date))::int AS cal_year,
                   c.club_abbrev
            FROM regattas r
            LEFT JOIN clubs c ON c.club_id = r.host_club_id
            WHERE r.regatta_id = ANY(%s)
            """,
            (ids,),
        )
        for row in cur.fetchall() or []:
            rid = str(row.get("regatta_id") or "").strip()
            if not rid:
                continue
            name = (row.get("event_name") or "").strip() or rid
            meta[rid] = {
                "event_name": event_name_with_year(name, rid, row.get("cal_year")),
                "year": row.get("cal_year") or year_from_regatta_id(rid),
                "host_abbrev": (row.get("club_abbrev") or "").strip().upper(),
                "date_label": _format_date_label(row.get("start_date"), row.get("end_date")),
                "start_date": _iso_date(row.get("start_date")),
            }
    finally:
        cur.close()
        return_db_connection(conn)
    return meta
