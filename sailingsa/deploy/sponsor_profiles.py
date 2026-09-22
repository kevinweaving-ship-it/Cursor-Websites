from __future__ import annotations

import html as html_module
import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote, urlparse

import psycopg2.extras

from gold_entity_layout import site_footer, site_header_nav

DEPLOY = Path(__file__).resolve().parent
DATA_PATH = DEPLOY / "sponsor_profiles.json"
YEAR_SPONSORS_PATH = DEPLOY / "event_year_sponsors.json"
REGATTA_ICONS_PATH = DEPLOY / "wc_regatta_header_icons.json"

try:
    from sponsor_catalog import alias_to_slug as _catalog_alias_to_slug
    from sponsor_catalog import catalog_by_slug as _catalog_by_slug
except ImportError:
    def _catalog_by_slug() -> dict[str, dict[str, Any]]:
        return {}

    def _catalog_alias_to_slug() -> dict[str, str]:
        return {}

_EVENT_LOGO_RULES = (
    ("cape classic", "/artwork/Event Logo/Cape-Classic-Series.png"),
    ("youth national", "/artwork/Event Logo/Youth-Nationals-Logo.png"),
    ("sonnet national", "/artwork/Event Logo/Sonnet-Nationals-2025.jpg"),
    ("overberg", "/artwork/Event Logo/Overberg-Regional-Champs.png"),
    ("29er", "/artwork/Event Logo/29er-Class-Logo.png"),
    ("dinghy", "/artwork/Event Logo/Western-Cape-Dinghy-Champs.png"),
    ("sa sailing youth", "/artwork/Event Logo/SA-Sailing-WC-Youth-Regatta.png"),
    ("national", "/artwork/Event Logo/SA-Nationals.png"),
)

_REGATTA_ICON_CACHE: dict[str, dict[str, Any]] | None = None
_INDEX_HTML_CACHE: dict[str, str] = {"fp": "", "html": ""}
_INDEX_CACHE_DIR = DEPLOY / ".cache"
_INDEX_CACHE_HTML = _INDEX_CACHE_DIR / "sponsors-index.html"
_INDEX_CACHE_FP = _INDEX_CACHE_DIR / "sponsors-index.fp"


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def _safe_slug(value: Any) -> str:
    slug = _safe_text(value).lower().strip("/")
    return slug


def _safe_url(value: Any) -> str:
    raw = _safe_text(value)
    if not raw:
        return ""
    if raw.startswith(("http://", "https://", "/", "mailto:")):
        return raw
    return "https://" + raw


def _norm_text_key(value: Any) -> str:
    return re.sub(r"\s+", " ", _safe_text(value).lower()).strip()


def _norm_sail_number(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", _safe_text(value).lower())


def _norm_sail_digits(value: Any) -> str:
    return re.sub(r"[^0-9]+", "", _safe_text(value))


def _looks_like_division(label: Any) -> bool:
    low = _norm_text_key(label)
    if not low:
        return False
    if re.fullmatch(r".+\s+[abc]\b", low):
        return True
    return low in {"youth", "junior", "senior", "women", "womens", "ladies", "gold", "silver", "bronze"}


def _looks_like_fleet(label: Any) -> bool:
    low = _norm_text_key(label)
    if not low:
        return False
    return (
        "fleet" in low
        or low in {"open", "open fleet", "overall", "spinnaker", "spin", "non spin", "non-spin", "non spinnaker", "non-spinnaker"}
    )


def _is_boat_class_label(label: Any) -> bool:
    text = _safe_text(label)
    if not text:
        return False
    return not _looks_like_fleet(text) and not _looks_like_division(text)


def _event_logo_from_name(event_name: Any) -> str:
    hay = _safe_text(event_name).lower()
    if not hay:
        return ""
    for needle, src in _EVENT_LOGO_RULES:
        if needle in hay:
            return src
    return ""


def _event_logo_for_regatta(regatta_id: Any, event_name: Any = "") -> str:
    rid = _safe_text(regatta_id)
    if rid:
        icon = _load_regatta_icons().get(rid) or {}
        left = _safe_text(icon.get("left"))
        if left:
            return left
    return _event_logo_from_name(event_name)


_SPONSOR_LOGO_STOP = {
    "the", "and", "for", "sails", "shipping", "supply", "workwear", "africa",
    "logo", "regatta", "event", "week",
}


def _sponsor_name_tokens(profile: dict[str, Any]) -> list[str]:
    tokens: list[str] = []
    for key in ("slug", "short_name", "display_name"):
        tokens.extend(re.findall(r"[a-z0-9]+", _safe_text(profile.get(key)).lower()))
    out: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        if len(token) < 3 or token in _SPONSOR_LOGO_STOP or token in seen:
            continue
        seen.add(token)
        out.append(token)
    return out


def _logo_is_sponsor_brand(logo_path: Any, profile: dict[str, Any]) -> bool:
    path = _safe_text(logo_path).lower()
    if not path:
        return False
    if "sponsor logo" in path:
        return True
    filename = path.rsplit("/", 1)[-1]
    return any(token in filename for token in _sponsor_name_tokens(profile))


def _sponsor_card_logo(event_logo: Any, fallback_logo: Any, profile: dict[str, Any]) -> str:
    event = _safe_text(event_logo)
    sponsor = _safe_text(profile.get("logo_path"))
    fallback = _safe_text(fallback_logo)
    if event and _logo_is_sponsor_brand(event, profile):
        return event
    return sponsor or event or fallback


def _iso(v: Any) -> str:
    if not v:
        return ""
    if isinstance(v, date):
        return v.isoformat()
    s = str(v).strip()
    return s[:10] if len(s) >= 10 else s


def _date_sort_int(value: Any) -> int:
    digits = re.sub(r"[^0-9]+", "", _iso(value))
    return int(digits or "0")


def _date_span(start_value: Any, end_value: Any) -> str:
    start = _iso(start_value)
    end = _iso(end_value or start_value)
    if not start and not end:
        return ""
    if start and end:
        return f"{start} -> {end}"
    return start or end


def _date_from_iso(value: Any) -> date | None:
    raw = _iso(value)
    if not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def _subtract_years(value: date, years: int) -> date:
    try:
        return value.replace(year=value.year - years)
    except ValueError:
        return value.replace(year=value.year - years, month=2, day=28)


def _fmt_as_at(value: Any) -> str:
    raw = _safe_text(value)
    if not raw:
        return ""
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        m = re.match(r"^(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2})", raw)
        if m:
            return f"{m.group(1)} {m.group(2)}"
    return raw[:16]


def _resolve_sponsor_slug(slug: str) -> str:
    s = _safe_slug(slug)
    return _catalog_alias_to_slug().get(s, s)


def _merge_profile(base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in extra.items():
        if k in ("match_terms", "aliases", "source_urls"):
            cur = list(out.get(k) or [])
            for item in v or []:
                if item not in cur:
                    cur.append(item)
            out[k] = cur
        elif v not in (None, "", [], {}) and not out.get(k):
            out[k] = v
    return out


def _load_profiles() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if DATA_PATH.is_file():
        raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        items = raw.get("profiles") or []
        for item in items:
            if not isinstance(item, dict):
                continue
            slug = _safe_slug(item.get("slug"))
            if not slug:
                continue
            out[slug] = dict(item)
    for slug, stub in _catalog_by_slug().items():
        if slug in out:
            out[slug] = _merge_profile(out[slug], stub)
            # Catalog index tier wins (Ullman model: headline brand stays one URL/list).
            if stub.get("tier") in {"headline", "tier2"}:
                out[slug]["tier"] = stub["tier"]
        else:
            out[slug] = dict(stub)
    return out


def _load_regatta_icons() -> dict[str, dict[str, Any]]:
    global _REGATTA_ICON_CACHE
    if _REGATTA_ICON_CACHE is not None:
        return _REGATTA_ICON_CACHE
    if not REGATTA_ICONS_PATH.is_file():
        _REGATTA_ICON_CACHE = {}
        return _REGATTA_ICON_CACHE
    try:
        raw = json.loads(REGATTA_ICONS_PATH.read_text(encoding="utf-8"))
    except Exception:
        _REGATTA_ICON_CACHE = {}
        return _REGATTA_ICON_CACHE
    _REGATTA_ICON_CACHE = {str(k).strip(): dict(v) for k, v in raw.items() if isinstance(k, str) and isinstance(v, dict)}
    return _REGATTA_ICON_CACHE


def _profile(slug: str) -> dict[str, Any] | None:
    return _load_profiles().get(_resolve_sponsor_slug(slug))


def _json_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _json_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _db_profile(
    slug: str,
    *,
    get_db_connection: Callable[[], Any],
    return_db_connection: Callable[[Any], None],
    table_exists: Callable[[str], bool],
) -> dict[str, Any] | None:
    if not table_exists("sponsors"):
        return None
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            SELECT
              slug,
              display_name,
              short_name,
              logo_path,
              website_url,
              email,
              phone,
              contact_name,
              contact_title,
              address,
              city,
              province,
              country,
              location_url,
              about_text,
              bio_text,
              services_json,
              team_json,
              social_json,
              source_urls_json,
              match_terms_json,
              explicit_regatta_ids_json,
              scraped_payload_json,
              scrape_status
            FROM sponsors
            WHERE lower(trim(slug)) = %s
              AND is_active = true
            LIMIT 1
            """,
            (_safe_slug(slug),),
        )
        row = cur.fetchone()
    finally:
        cur.close()
        return_db_connection(conn)
    return dict(row) if row else None


def _profile_for_page(
    slug: str,
    *,
    get_db_connection: Callable[[], Any],
    return_db_connection: Callable[[Any], None],
    table_exists: Callable[[str], bool],
) -> dict[str, Any] | None:
    file_profile = _profile(slug) or {}
    db_profile = _db_profile(
        _resolve_sponsor_slug(slug),
        get_db_connection=get_db_connection,
        return_db_connection=return_db_connection,
        table_exists=table_exists,
    ) or {}
    merged = dict(file_profile)
    merged.update({k: v for k, v in db_profile.items() if v not in (None, "")})
    if merged:
        merged["slug"] = _resolve_sponsor_slug(slug) or merged.get("slug")
    return merged or None


def _match_terms(profile: dict[str, Any]) -> list[str]:
    terms = []
    for value in profile.get("match_terms") or []:
        term = _safe_text(value).lower()
        if term and term not in terms:
            terms.append(term)
    name = _safe_text(profile.get("display_name")).lower()
    if name and name not in terms:
        terms.append(name)
    return terms


def _explicit_regatta_ids(profile: dict[str, Any]) -> list[str]:
    out = []
    for value in profile.get("explicit_regatta_ids") or []:
        rid = _safe_text(value)
        if rid and rid not in out:
            out.append(rid)
    return out


def _class_href(class_name: Any) -> str:
    """Public class URL from class name only. Never put class_id in the path."""
    try:
        int(class_name)
        return ""  # numeric id alone is not a public URL
    except (TypeError, ValueError):
        pass
    class_slug = _class_canonical_slug(class_name)
    if not class_slug:
        return ""
    return f"/class/{quote(class_slug, safe='')}"


def _class_canonical_slug(class_name: Any) -> str:
    label = _safe_text(class_name).lower().replace(" ", "-")
    label = re.sub(r"[^a-z0-9.-]", "", label)
    return label.strip("-")


def _regatta_href(regatta_id: Any) -> str:
    rid = _safe_text(regatta_id)
    if not rid:
        return ""
    return f"/regatta/{html_module.escape(rid)}"


def _boat_name_slug(boat_name: Any) -> str:
    label = _safe_text(boat_name).lower()
    label = re.sub(r"[^a-z0-9]+", "-", label)
    return label.strip("-")


def _boat_href(class_name: Any, sail_number: Any, boat_name: Any = "") -> str:
    class_slug = _class_canonical_slug(class_name)
    parts = [p for p in class_slug.split("-") if p]
    fleet = {"novice", "gold", "silver", "bronze", "open", "fleet", "junior", "youth", "master", "masters", "ladies", "women", "men"}
    while parts and parts[-1] in fleet:
        parts.pop()
    class_slug = "-".join(parts)
    sail = _safe_text(sail_number)
    if sail and re.sub(r"[^a-z0-9]+", "", sail.lower()) in fleet:
        sail = ""
    if class_slug and sail:
        return f"/boat/{quote(class_slug, safe='')}-{quote(sail, safe='')}"
    if class_slug:
        return f"/boat/{quote(class_slug, safe='')}"
    name_slug = _boat_name_slug(boat_name)
    if name_slug:
        return f"/boat-name/{quote(name_slug, safe='')}"
    return ""


def _sailor_href(sas_id: str) -> str:
    sid = _safe_text(sas_id)
    if not sid:
        return ""
    return f"/sailor/{html_module.escape(sid)}"


def _fetch_linked_regattas(
    profile: dict[str, Any],
    *,
    get_db_connection: Callable[[], Any],
    return_db_connection: Callable[[Any], None],
    table_exists: Callable[[str], bool],
) -> list[dict[str, Any]]:
    if not table_exists("regattas"):
        return []
    explicit_ids = _explicit_regatta_ids(profile)
    terms = _match_terms(profile)
    patterns = [f"%{t}%" for t in terms]
    if not explicit_ids and not patterns:
        return []
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT
                reg.regatta_id::text AS regatta_id,
                COALESCE(NULLIF(TRIM(reg.event_name), ''), reg.regatta_id::text) AS event_name,
                reg.start_date,
                reg.end_date,
                COALESCE(NULLIF(TRIM(reg.source_url), ''), '') AS source_url,
                COALESCE(NULLIF(TRIM(club.club_abbrev), ''), NULLIF(TRIM(club.club_fullname), ''), '') AS host_label
            FROM regattas reg
            LEFT JOIN clubs club ON club.club_id = reg.host_club_id
            WHERE (%s <> '{}'::text[] AND reg.regatta_id::text = ANY(%s))
               OR (%s <> '{}'::text[] AND LOWER(
                    COALESCE(reg.event_name, '') || ' ' ||
                    COALESCE(reg.regatta_id::text, '') || ' ' ||
                    COALESCE(reg.source_url, '')
               ) LIKE ANY(%s))
            ORDER BY COALESCE(reg.end_date, reg.start_date) DESC NULLS LAST, LOWER(COALESCE(reg.event_name, reg.regatta_id::text)) ASC
            """,
            (explicit_ids, explicit_ids, patterns, patterns),
        )
        rows = cur.fetchall() or []
    finally:
        cur.close()
        return_db_connection(conn)
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        data = dict(row)
        rid = _safe_text(data.get("regatta_id"))
        if not rid or rid in seen:
            continue
        seen.add(rid)
        out.append(
            {
                "regatta_id": rid,
                "event_name": _safe_text(data.get("event_name")) or rid,
                "start_date": _iso(data.get("start_date")),
                "end_date": _iso(data.get("end_date") or data.get("start_date")),
                "source_url": _safe_text(data.get("source_url")),
                "host_label": _safe_text(data.get("host_label")),
                "url": f"/regatta/{rid}",
            }
        )
    if table_exists("events") and patterns:
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                """
                SELECT
                    e.event_id::text AS event_id,
                    COALESCE(NULLIF(TRIM(e.event_name), ''), e.event_id::text) AS event_name,
                    e.start_date,
                    e.end_date,
                    COALESCE(NULLIF(TRIM(e.source_url), ''), '') AS source_url,
                    COALESCE(NULLIF(TRIM(e.series_key), ''), '') AS series_key,
                    e.edition_year,
                    COALESCE(e.regatta_id::text, '') AS linked_regatta_id
                FROM events e
                WHERE LOWER(COALESCE(e.event_name, '')) LIKE ANY(%s)
                   OR LOWER(REPLACE(COALESCE(e.event_name, ''), '&#039;', '''')) LIKE ANY(%s)
                   OR LOWER(COALESCE(e.series_key, '')) LIKE ANY(%s)
                ORDER BY COALESCE(e.start_date, e.end_date) DESC NULLS LAST
                """,
                (patterns, patterns, patterns),
            )
            event_rows = cur.fetchall() or []
        except Exception:
            event_rows = []
        finally:
            cur.close()
            return_db_connection(conn)
        seen_names = {
            (_safe_text(r.get("event_name")).lower(), _safe_text(r.get("start_date"))[:10])
            for r in out
        }
        for row in event_rows:
            data = dict(row)
            ename = _safe_text(data.get("event_name"))
            start = _iso(data.get("start_date"))
            key = (ename.lower(), start[:10])
            linked = _safe_text(data.get("linked_regatta_id"))
            if linked and linked in seen:
                continue
            if key in seen_names:
                continue
            seen_names.add(key)
            year = data.get("edition_year")
            try:
                year_i = int(year) if year else (int(start[:4]) if start[:4].isdigit() else 0)
            except (TypeError, ValueError):
                year_i = 0
            series_key = _safe_text(data.get("series_key"))
            source_url = _safe_text(data.get("source_url"))
            raw_name = ename
            if series_key:
                try:
                    from backfill_event_edition_classes import canonical_series_label, edition_title
                    label = canonical_series_label(series_key, ename)
                    pretty = edition_title(label, year_i or None)
                    if pretty:
                        ename = pretty
                except Exception:
                    if year_i and str(year_i) not in ename:
                        ename = f"{ename} {year_i}".strip()
            if linked:
                href = f"/regatta/{linked}"
                rid = linked
            elif series_key and year_i:
                series_slug = re.sub(r"[^a-z0-9]+", "-", series_key.lower()).strip("-")
                href = f"/events-logos/{series_slug}"
                rid = f"event-{_safe_text(data.get('event_id'))}"
            elif source_url:
                href = source_url
                rid = f"event-{_safe_text(data.get('event_id'))}"
            else:
                href = "/events"
                rid = f"event-{_safe_text(data.get('event_id'))}"
            if rid in seen:
                continue
            seen.add(rid)
            out.append(
                {
                    "regatta_id": rid,
                    "event_name": ename or rid,
                    "start_date": start,
                    "end_date": _iso(data.get("end_date") or data.get("start_date")),
                    "source_url": source_url,
                    "host_label": "",
                    "url": href,
                    "series_key": series_key,
                    "edition_year": year_i,
                    "raw_event_name": raw_name,
                }
            )
        out.sort(
            key=lambda r: (_safe_text(r.get("end_date") or r.get("start_date")), _safe_text(r.get("event_name")).lower()),
            reverse=True,
        )
    return out


def _load_year_sponsors() -> list[dict[str, Any]]:
    if not YEAR_SPONSORS_PATH.is_file():
        return []
    try:
        raw = json.loads(YEAR_SPONSORS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []
    series = raw.get("series") if isinstance(raw, dict) else raw
    return [item for item in (series or []) if isinstance(item, dict)]


def _edition_year(row: dict[str, Any]) -> int:
    year = row.get("edition_year")
    try:
        if year:
            return int(year)
    except (TypeError, ValueError):
        pass
    start = _safe_text(row.get("start_date"))
    if len(start) >= 4 and start[:4].isdigit():
        return int(start[:4])
    return 0


def _brand_in_edition_title(event_name: Any, profile: dict[str, Any], raw_event_name: Any = "") -> bool:
    blob = f"{_safe_text(event_name)} {_safe_text(raw_event_name)}".lower()
    if not blob.strip():
        return False
    for term in _match_terms(profile):
        if len(term) < 3:
            continue
        if re.search(rf"\b{re.escape(term)}\b", blob):
            return True
    return False


def _row_matches_series_block(row: dict[str, Any], block: dict[str, Any]) -> bool:
    series = _safe_text(row.get("series_key")).lower()
    ename = _safe_text(row.get("event_name")).lower()
    keys = [_safe_text(block.get("series_key")).lower()]
    keys.extend(_safe_text(k).lower() for k in (block.get("match_keys") or []))
    keys = [k for k in keys if k]
    if series and series in keys:
        return True
    for needle in block.get("match_names") or []:
        n = _safe_text(needle).lower()
        if n and n in ename:
            return True
    return False


def _ssot_role_for(slug: str, row: dict[str, Any]) -> str:
    want = _safe_slug(slug)
    year = str(_edition_year(row) or "")
    if not want or not year:
        return ""
    for block in _load_year_sponsors():
        if not _row_matches_series_block(row, block):
            continue
        year_block = (block.get("years") or {}).get(year) or {}
        for role in ("headline", "tier2"):
            for item in year_block.get(role) or []:
                if isinstance(item, dict) and _safe_slug(item.get("slug")) == want:
                    return role
        return ""
    return ""




def regatta_header_sponsor_html(regatta_id: str, event_name: str = "") -> str:
    """Standalone regatta header chip for explicitly assigned sponsors."""
    rid = _safe_text(regatta_id)
    if not rid:
        return ""
    links = []
    any_headline = False
    for profile in _load_profiles().values():
        if rid not in _explicit_regatta_ids(profile):
            continue
        slug = _safe_slug(profile.get("slug"))
        name = html_module.escape(_safe_text(profile.get("display_name")) or slug.replace("-", " ").title())
        href = html_module.escape(f"/sponsors/{slug}")
        logo = html_module.escape(_safe_text(profile.get("logo_path")))
        img = ""
        if logo:
            img = (
                f'<img src="{logo}" alt="{name}" width="48" height="36" '
                'loading="lazy" decoding="async">'
            )
        role = _ssot_role_for(slug, {
            "regatta_id": rid,
            "event_name": event_name,
            "raw_event_name": event_name,
            "series_key": "",
            "start_date": rid[:10] if len(rid) >= 10 and rid[4:5] == "-" else "",
        }) or "headline"
        if role == "headline":
            any_headline = True
        title = html_module.escape(("Headline sponsor" if role == "headline" else "Sponsor") + " — " + (_safe_text(profile.get("display_name")) or slug))
        links.append(f'<a href="{href}" title="{title}">{img}<span>{name}</span></a>')
    if not links:
        return ""
    label = "Headline sponsor" if any_headline else "Sponsor"
    if len(links) > 1:
        label = "Headline sponsors" if any_headline else "Sponsors"
    return f'<div class="host-club">{html_module.escape(label)}: {"".join(links)}</div>'

def _assign_sponsor_roles(profile: dict[str, Any], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    slug = _safe_slug(profile.get("slug"))
    out: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        role = _ssot_role_for(slug, item)
        if not role:
            role = "headline" if _brand_in_edition_title(item.get("event_name"), profile, item.get("raw_event_name")) else ""
        if not role:
            continue
        item["sponsor_role"] = role
        out.append(item)
    return _apply_event_target_names(profile, out)


def _apply_event_target_names(profile: dict[str, Any], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Use the event's own name from profile targets; honor headline/tier2 there."""
    targets = [t for t in _json_list(profile.get("event_targets")) if isinstance(t, dict)]
    if not targets:
        return rows
    out: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        year = _edition_year(item)
        blob = f"{item.get('event_name')} {item.get('raw_event_name')} {item.get('series_key')}".lower()
        for tgt in targets:
            tname = _safe_text(tgt.get("event_name"))
            if not tname:
                continue
            try:
                ty = int(tgt.get("year") or 0)
            except (TypeError, ValueError):
                ty = 0
            if ty and year and ty != year:
                continue
            tlow = tname.lower().replace("j/22", "j22").replace("j-22", "j22")
            blob_n = blob.replace("j/22", "j22").replace("j-22", "j22")
            if not (
                tlow in blob_n
                or ("j22" in blob_n and "j22" in tlow)
                or (ty and ty == year and tlow.replace("the ", "")[:18] in blob_n)
            ):
                continue
            item["event_name"] = tname
            role = _safe_text(tgt.get("tier")).lower()
            if role in {"headline", "tier2"}:
                item["sponsor_role"] = role
            break
        out.append(item)
    return out


def _edition_dedupe_key(row: dict[str, Any]) -> str:
    year = str(_edition_year(row) or "")
    name = _safe_text(row.get("event_name") or row.get("raw_event_name")).lower()
    name = re.sub(r"\b(19|20)\d{2}\b", " ", name)
    name = re.sub(r"[^a-z0-9]+", " ", name).strip()
    if name and year:
        return f"name|{name}|{year}"
    series = _safe_text(row.get("series_key")).lower()
    if series and year:
        return f"series|{series}|{year}"
    rid = _safe_text(row.get("regatta_id"))
    return f"id|{rid}|{year}"


def _edition_row_rank(row: dict[str, Any]) -> tuple[int, int, int]:
    start = _safe_text(row.get("start_date"))
    end = _safe_text(row.get("end_date"))
    rid = _safe_text(row.get("regatta_id"))
    has_dates = 1 if start and start not in {"—", "-"} else 0
    is_regatta = 1 if rid and not rid.startswith("event-") else 0
    has_end = 1 if end and end not in {"—", "-"} else 0
    return (has_dates, has_end, is_regatta)


def _dedupe_edition_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for row in rows:
        item = dict(row)
        key = _edition_dedupe_key(item)
        if key not in best:
            best[key] = item
            order.append(key)
            continue
        cur = best[key]
        if _edition_row_rank(item) > _edition_row_rank(cur):
            if not _safe_text(item.get("start_date")):
                item["start_date"] = cur.get("start_date")
                item["end_date"] = item.get("end_date") or cur.get("end_date")
            if not _safe_text(item.get("url")):
                item["url"] = cur.get("url")
            best[key] = item
        else:
            if not _safe_text(cur.get("start_date")):
                cur["start_date"] = item.get("start_date")
                cur["end_date"] = cur.get("end_date") or item.get("end_date")
            if not _safe_text(cur.get("url")):
                cur["url"] = item.get("url")
    return [best[k] for k in order]


def _event_row_from_events_table(data: dict[str, Any]) -> dict[str, Any]:
    ename = _safe_text(data.get("event_name"))
    start = _iso(data.get("start_date"))
    year = data.get("edition_year")
    try:
        year_i = int(year) if year else (int(start[:4]) if start[:4].isdigit() else 0)
    except (TypeError, ValueError):
        year_i = 0
    series_key = _safe_text(data.get("series_key"))
    source_url = _safe_text(data.get("source_url"))
    linked = _safe_text(data.get("linked_regatta_id") or data.get("regatta_id"))
    raw_name = ename
    if series_key:
        try:
            from backfill_event_edition_classes import canonical_series_label, edition_title
            label = canonical_series_label(series_key, ename)
            pretty = edition_title(label, year_i or None)
            if pretty:
                ename = pretty
        except Exception:
            if year_i and str(year_i) not in ename:
                ename = f"{ename} {year_i}".strip()
    if linked:
        href = f"/regatta/{linked}"
        rid = linked
    elif series_key and year_i:
        series_slug = re.sub(r"[^a-z0-9]+", "-", series_key.lower()).strip("-")
        href = f"/events-logos/{series_slug}"
        rid = f"event-{_safe_text(data.get('event_id'))}"
    elif source_url:
        href = source_url
        rid = f"event-{_safe_text(data.get('event_id'))}"
    else:
        href = "/events"
        rid = f"event-{_safe_text(data.get('event_id'))}"
    return {
        "regatta_id": rid,
        "event_name": ename or rid,
        "start_date": start,
        "end_date": _iso(data.get("end_date") or data.get("start_date")),
        "source_url": source_url,
        "host_label": "",
        "url": href,
        "series_key": series_key,
        "edition_year": year_i,
        "raw_event_name": raw_name,
    }


def _fetch_supporting_year_events(
    profile: dict[str, Any],
    existing: list[dict[str, Any]],
    *,
    get_db_connection: Callable[[], Any],
    return_db_connection: Callable[[Any], None],
    table_exists: Callable[[str], bool],
) -> list[dict[str, Any]]:
    if not table_exists("events"):
        return []
    slug = _safe_slug(profile.get("slug"))
    seen = {_safe_text(r.get("regatta_id")) for r in existing if _safe_text(r.get("regatta_id"))}
    extra: list[dict[str, Any]] = []
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        for block in _load_year_sponsors():
            years = block.get("years") or {}
            for year_s, year_block in years.items():
                if not any(
                    isinstance(item, dict) and _safe_slug(item.get("slug")) == slug
                    for role in ("headline", "tier2")
                    for item in (year_block.get(role) or [])
                ):
                    continue
                try:
                    year_i = int(year_s)
                except (TypeError, ValueError):
                    continue
                keys = [_safe_text(block.get("series_key")).lower()]
                keys.extend(_safe_text(k).lower() for k in (block.get("match_keys") or []))
                keys = [k for k in keys if k]
                name_likes = [f"%{_safe_text(n).lower()}%" for n in (block.get("match_names") or []) if _safe_text(n)]
                cur.execute(
                    """
                    SELECT
                        e.event_id::text AS event_id,
                        COALESCE(NULLIF(TRIM(e.event_name), ''), e.event_id::text) AS event_name,
                        e.start_date,
                        e.end_date,
                        COALESCE(NULLIF(TRIM(e.source_url), ''), '') AS source_url,
                        COALESCE(NULLIF(TRIM(e.series_key), ''), '') AS series_key,
                        e.edition_year,
                        COALESCE(e.regatta_id::text, '') AS linked_regatta_id
                    FROM events e
                    WHERE (
                        COALESCE(e.edition_year, 0) = %s
                        OR EXTRACT(YEAR FROM e.start_date) = %s
                    )
                    AND (
                        LOWER(COALESCE(e.series_key, '')) = ANY(%s)
                        OR (%s <> '{}'::text[] AND LOWER(COALESCE(e.event_name, '')) LIKE ANY(%s))
                    )
                    """,
                    (year_i, year_i, keys, name_likes, name_likes),
                )
                for row in cur.fetchall() or []:
                    item = _event_row_from_events_table(dict(row))
                    rid = _safe_text(item.get("regatta_id"))
                    if not rid or rid in seen:
                        continue
                    seen.add(rid)
                    extra.append(item)
    except Exception:
        extra = []
    finally:
        cur.close()
        return_db_connection(conn)
    return extra


def _regatta_logo_map(
    regatta_ids: list[str],
    *,
    get_db_connection: Callable[[], Any],
    return_db_connection: Callable[[Any], None],
    table_exists: Callable[[str], bool],
) -> dict[str, str]:
    if not regatta_ids or not table_exists("results"):
        return {}
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            WITH ranked AS (
                SELECT
                    r.regatta_id::text AS regatta_id,
                    NULLIF(TRIM(cl.logo_path), '') AS logo_path,
                    COUNT(*)::int AS row_count,
                    ROW_NUMBER() OVER (
                        PARTITION BY r.regatta_id::text
                        ORDER BY COUNT(*) DESC, NULLIF(TRIM(cl.logo_path), '') ASC
                    ) AS rn
                FROM results r
                LEFT JOIN regatta_blocks rb ON rb.block_id = r.block_id
                LEFT JOIN classes cl ON cl.class_id = COALESCE(r.class_id, rb.class_id)
                WHERE r.regatta_id = ANY(%s)
                  AND NULLIF(TRIM(cl.logo_path), '') IS NOT NULL
                GROUP BY r.regatta_id::text, NULLIF(TRIM(cl.logo_path), '')
            )
            SELECT regatta_id, logo_path
            FROM ranked
            WHERE rn = 1
            """,
            (regatta_ids,),
        )
        rows = cur.fetchall() or []
    finally:
        cur.close()
        return_db_connection(conn)
    return {_safe_text(row.get("regatta_id")): _safe_text(row.get("logo_path")) for row in rows if _safe_text(row.get("regatta_id")) and _safe_text(row.get("logo_path"))}


def _results_regatta_ids(
    regatta_ids: list[str],
    *,
    get_db_connection: Callable[[], Any],
    return_db_connection: Callable[[Any], None],
    table_exists: Callable[[str], bool],
) -> set[str]:
    if not regatta_ids or not table_exists("results"):
        return set()
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT DISTINCT regatta_id
            FROM (
                SELECT regatta_id::text AS regatta_id
                FROM results
                WHERE regatta_id = ANY(%s)

                UNION

                SELECT reg.regatta_id::text AS regatta_id
                FROM regattas reg
                WHERE reg.regatta_id = ANY(%s)
                  AND (
                    LOWER(COALESCE(reg.event_name, '')) ~ 'result|standings'
                    OR LOWER(COALESCE(reg.source_url, '')) ~ 'race-results|/results|result'
                  )
            ) x
            """,
            (regatta_ids, regatta_ids),
        )
        rows = cur.fetchall() or []
    finally:
        cur.close()
        return_db_connection(conn)
    return {_safe_text((r.get("regatta_id") if isinstance(r, dict) else r[0])) for r in rows if _safe_text((r.get("regatta_id") if isinstance(r, dict) else r[0]))}


def _linked_sailors(
    regatta_ids: list[str],
    *,
    get_db_connection: Callable[[], Any],
    return_db_connection: Callable[[Any], None],
    table_exists: Callable[[str], bool],
) -> list[dict[str, str]]:
    if not regatta_ids or not (table_exists("results") and table_exists("sas_id_personal")):
        return []
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT DISTINCT
                s.sa_sailing_id::text AS sas_id,
                COALESCE(NULLIF(TRIM(s.full_name), ''), TRIM(COALESCE(s.first_name, '') || ' ' || COALESCE(s.last_name, ''))) AS full_name,
                COALESCE(NULLIF(TRIM(s.first_name), ''), '') AS first_name,
                COALESCE(NULLIF(TRIM(s.last_name), ''), '') AS last_name
            FROM sas_id_personal s
            JOIN results r
              ON r.helm_sa_sailing_id::text = s.sa_sailing_id::text
              OR r.crew_sa_sailing_id::text = s.sa_sailing_id::text
            WHERE r.regatta_id = ANY(%s)
            ORDER BY first_name, last_name, full_name
            """,
            (regatta_ids,),
        )
        rows = cur.fetchall() or []
    finally:
        cur.close()
        return_db_connection(conn)
    out = []
    seen = set()
    for row in rows:
        data = dict(row)
        sid = _safe_text(data.get("sas_id"))
        name = _safe_text(data.get("full_name"))
        if not sid or not name or sid in seen:
            continue
        seen.add(sid)
        out.append({"sas_id": sid, "name": name})
    return out


def _linked_classes(
    regatta_ids: list[str],
    *,
    get_db_connection: Callable[[], Any],
    return_db_connection: Callable[[Any], None],
    table_exists: Callable[[str], bool],
) -> list[dict[str, Any]]:
    if not regatta_ids or not table_exists("results"):
        return []
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT
                COALESCE(cl.class_id, r.class_id) AS class_id,
                COALESCE(NULLIF(TRIM(cl.class_name), ''), '') AS class_name,
                COALESCE(NULLIF(TRIM(cl.logo_path), ''), '') AS logo_path,
                COUNT(DISTINCT r.regatta_id::text) AS regatta_count,
                COUNT(*) AS result_count
            FROM results r
            LEFT JOIN regatta_blocks rb ON rb.block_id = r.block_id
            LEFT JOIN classes cl ON cl.class_id = COALESCE(r.class_id, rb.class_id)
            WHERE r.regatta_id = ANY(%s)
            GROUP BY 1, 2, 3
            ORDER BY COUNT(DISTINCT r.regatta_id::text) DESC, COUNT(*) DESC, LOWER(COALESCE(NULLIF(TRIM(cl.class_name), ''), '')) ASC
            """,
            (regatta_ids,),
        )
        rows = cur.fetchall() or []
    finally:
        cur.close()
        return_db_connection(conn)
    out = []
    for row in rows:
        data = dict(row)
        label = _safe_text(data.get("class_name"))
        if not _is_boat_class_label(label):
            continue
        out.append(
            {
                "class_id": data.get("class_id"),
                "class_name": label,
                "logo_path": _safe_text(data.get("logo_path")),
                "regatta_count": int(data.get("regatta_count") or 0),
                "result_count": int(data.get("result_count") or 0),
            }
        )
    return out


def _live_mentions(
    slug: str,
    *,
    get_db_connection: Callable[[], Any],
    return_db_connection: Callable[[Any], None],
    table_exists: Callable[[str], bool],
) -> list[dict[str, Any]]:
    if not table_exists("sponsor_live_mentions"):
        return []
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            SELECT
              title,
              source_url,
              source_domain,
              snippet_text,
              matched_boats_json,
              matched_classes_json,
              matched_sail_nos_json,
              resolved_sailors_json,
              source_payload_json,
              updated_at
            FROM sponsor_live_mentions
            WHERE lower(trim(sponsor_slug)) = %s
              AND is_active = true
            ORDER BY updated_at DESC, mention_id DESC
            LIMIT 12
            """,
            (_safe_slug(slug),),
        )
        rows = cur.fetchall() or []
    finally:
        cur.close()
        return_db_connection(conn)
    out: list[dict[str, Any]] = []
    for row in rows:
        data = dict(row)
        out.append(
            {
                "title": _safe_text(data.get("title")),
                "source_url": _safe_text(data.get("source_url")),
                "source_domain": _safe_text(data.get("source_domain")),
                "snippet_text": _safe_text(data.get("snippet_text")),
                "matched_boats": _json_list(data.get("matched_boats_json")),
                "matched_classes": _json_list(data.get("matched_classes_json")),
                "matched_sail_nos": _json_list(data.get("matched_sail_nos_json")),
                "resolved_sailors": _json_list(data.get("resolved_sailors_json")),
                "source_payload": _json_dict(data.get("source_payload_json")),
                "updated_at": _safe_text(data.get("updated_at"))[:19].replace("T", " "),
            }
        )
    return out


def _member_result_block_tail(block_id: Any) -> str:
    raw = _safe_text(block_id)
    if ":" not in raw:
        return ""
    return raw.split(":", 1)[1].strip()


def _is_member_youth_subfleet_block(block_id: Any) -> bool:
    tail = _member_result_block_tail(block_id).lower()
    return tail in {"u19-results", "u17-results", "420-fleet-under-19", "420-fleet-under-17"}


def _is_member_result_series_row(row: dict[str, Any]) -> bool:
    event_name = _safe_text(row.get("event_name"))
    regatta_number = _safe_text(row.get("regatta_number"))
    return bool(
        row.get("is_series") is True
        or regatta_number == "S"
        or ("Series" in event_name and "> Overall" in event_name)
    )


def _member_result_career_event_key(row: dict[str, Any]) -> str:
    rid = _safe_text(row.get("regatta_id"))
    if rid in {"381-2026-rcyc-gimco-inter-academy", "382-2026-rcyc-gimco-cape-31"}:
        return "381-2026-rcyc-gimco-inter-academy"
    return rid


def _should_include_member_result_row(row: dict[str, Any], all_rows: list[dict[str, Any]]) -> bool:
    rid = _safe_text(row.get("regatta_id"))
    if not rid:
        return False
    all_ids = {_safe_text(item.get("regatta_id")) for item in all_rows}
    if rid == "419-2025-2025-420-national-championship-results" and "366-2025-420-national-championship-results" in all_ids:
        return False
    if rid == "412-2025-2025-sa-sailing-youth-national-championship-fina" and "377-2025-hyc-sa-youth-nationals" in all_ids:
        return False
    if rid == "416-2025-2025-tsc-cape-classic" and "371-2025-tsc-cape-classic" in all_ids:
        return False
    if rid == "382-2026-rcyc-gimco-inter-academy-challenge" and "381-2026-rcyc-gimco-inter-academy" in all_ids:
        return False
    if rid == "live-2026-wc-dinghy-champs-sbyc" and "2026-04-06-western-cape-dinghy-championships" in all_ids:
        return False
    return True


def _result_rank_num(row: dict[str, Any]) -> int | None:
    for value in (row.get("rank"), row.get("rank_ordinal"), row.get("pos")):
        raw = _safe_text(value)
        if not raw:
            continue
        match = re.match(r"^\s*([0-9]+)", raw)
        if match:
            return int(match.group(1))
    return None


def _result_class_name(row: dict[str, Any]) -> str:
    return _safe_text(row.get("class_name"))


def _count_races_for_result(row: dict[str, Any]) -> int:
    races_sailed = int(row.get("races_sailed") or 0)
    if races_sailed > 0:
        return races_sailed
    race_scores = row.get("race_scores")
    if isinstance(race_scores, dict):
        count = 0
        for key, value in race_scores.items():
            if not re.match(r"^R\d+$", _safe_text(key), re.I):
                continue
            score = _safe_text(value)
            if score and not re.fullmatch(r"(DNC|DNS|DNF|DSQ|RET|OCS|BFD|UFD|SCP|RDG|DPI)", score, re.I):
                count += 1
        if count:
            return count
    return races_sailed


def _sailor_profile_stats(
    sas_ids: list[str],
    *,
    get_db_connection: Callable[[], Any],
    return_db_connection: Callable[[Any], None],
    table_exists: Callable[[str], bool],
) -> dict[str, dict[str, Any]]:
    cleaned_ids = []
    seen_ids: set[str] = set()
    for value in sas_ids:
        sid = _safe_text(value)
        if not sid or sid in seen_ids:
            continue
        seen_ids.add(sid)
        cleaned_ids.append(sid)
    if not cleaned_ids or not table_exists("sas_id_personal"):
        return {}
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            SELECT
                s.sa_sailing_id::text AS sas_id,
                COALESCE(NULLIF(TRIM(s.full_name), ''), TRIM(COALESCE(s.first_name, '') || ' ' || COALESCE(s.last_name, ''))) AS full_name,
                COALESCE(s.ssl_rank, NULL) AS ssl_rank,
                COALESCE(s.ssl_points, NULL) AS ssl_points,
                COALESCE(NULLIF(TRIM(s.ssl_profile_url), ''), '') AS ssl_profile_url,
                COALESCE(NULLIF(TRIM(s.ssl_profile_slug), ''), '') AS ssl_profile_slug
            FROM sas_id_personal s
            WHERE s.sa_sailing_id::text = ANY(%s)
            """,
            (cleaned_ids,),
        )
        profile_rows = cur.fetchall() or []
        result_rows = []
        if table_exists("results"):
            cur.execute(
                """
                WITH sailor_rows AS (
                    SELECT
                        r.helm_sa_sailing_id::text AS sas_id,
                        r.regatta_id::text AS regatta_id,
                        COALESCE(r.block_id::text, '') AS block_id,
                        COALESCE(NULLIF(TRIM(r.event_name), ''), '') AS event_name,
                        COALESCE(NULLIF(TRIM(rg.regatta_number::text), ''), '') AS regatta_number,
                        false AS is_series,
                        COALESCE(rg.start_date, r.start_date)::text AS start_date,
                        COALESCE(rg.end_date, rg.start_date, r.start_date)::text AS end_date,
                        COALESCE(r.class_canonical, r.class_original, '') AS class_name,
                        COALESCE(r.rank::text, '') AS rank,
                        COALESCE(r.rank_ordinal, '') AS rank_ordinal,
                        COALESCE(r.pos::text, '') AS pos,
                        COALESCE(r.race_scores, '{}'::jsonb) AS race_scores,
                        COALESCE(r.races_sailed, rb.races_sailed, 0)::int AS races_sailed,
                        COALESCE(NULLIF(TRIM(r.boat_name), ''), '') AS boat_name,
                        COALESCE(NULLIF(TRIM(r.sail_number), ''), '') AS sail_number
                    FROM results r
                    LEFT JOIN regatta_blocks rb ON rb.block_id = r.block_id
                    LEFT JOIN regattas rg ON rg.regatta_id = r.regatta_id
                    WHERE r.helm_sa_sailing_id::text = ANY(%s)
                    UNION ALL
                    SELECT
                        r.crew_sa_sailing_id::text AS sas_id,
                        r.regatta_id::text AS regatta_id,
                        COALESCE(r.block_id::text, '') AS block_id,
                        COALESCE(NULLIF(TRIM(r.event_name), ''), '') AS event_name,
                        COALESCE(NULLIF(TRIM(rg.regatta_number::text), ''), '') AS regatta_number,
                        false AS is_series,
                        COALESCE(rg.start_date, r.start_date)::text AS start_date,
                        COALESCE(rg.end_date, rg.start_date, r.start_date)::text AS end_date,
                        COALESCE(r.class_canonical, r.class_original, '') AS class_name,
                        COALESCE(r.rank::text, '') AS rank,
                        COALESCE(r.rank_ordinal, '') AS rank_ordinal,
                        COALESCE(r.pos::text, '') AS pos,
                        COALESCE(r.race_scores, '{}'::jsonb) AS race_scores,
                        COALESCE(r.races_sailed, rb.races_sailed, 0)::int AS races_sailed,
                        COALESCE(NULLIF(TRIM(r.boat_name), ''), '') AS boat_name,
                        COALESCE(NULLIF(TRIM(r.sail_number), ''), '') AS sail_number
                    FROM results r
                    LEFT JOIN regatta_blocks rb ON rb.block_id = r.block_id
                    LEFT JOIN regattas rg ON rg.regatta_id = r.regatta_id
                    WHERE r.crew_sa_sailing_id::text = ANY(%s)
                    UNION ALL
                    SELECT
                        COALESCE(r.crew2_sa_sailing_id::text, '') AS sas_id,
                        r.regatta_id::text AS regatta_id,
                        COALESCE(r.block_id::text, '') AS block_id,
                        COALESCE(NULLIF(TRIM(r.event_name), ''), '') AS event_name,
                        COALESCE(NULLIF(TRIM(rg.regatta_number::text), ''), '') AS regatta_number,
                        false AS is_series,
                        COALESCE(rg.start_date, r.start_date)::text AS start_date,
                        COALESCE(rg.end_date, rg.start_date, r.start_date)::text AS end_date,
                        COALESCE(r.class_canonical, r.class_original, '') AS class_name,
                        COALESCE(r.rank::text, '') AS rank,
                        COALESCE(r.rank_ordinal, '') AS rank_ordinal,
                        COALESCE(r.pos::text, '') AS pos,
                        COALESCE(r.race_scores, '{}'::jsonb) AS race_scores,
                        COALESCE(r.races_sailed, rb.races_sailed, 0)::int AS races_sailed,
                        COALESCE(NULLIF(TRIM(r.boat_name), ''), '') AS boat_name,
                        COALESCE(NULLIF(TRIM(r.sail_number), ''), '') AS sail_number
                    FROM results r
                    LEFT JOIN regatta_blocks rb ON rb.block_id = r.block_id
                    LEFT JOIN regattas rg ON rg.regatta_id = r.regatta_id
                    WHERE COALESCE(r.crew2_sa_sailing_id::text, '') = ANY(%s)
                    UNION ALL
                    SELECT
                        COALESCE(r.crew3_sa_sailing_id::text, '') AS sas_id,
                        r.regatta_id::text AS regatta_id,
                        COALESCE(r.block_id::text, '') AS block_id,
                        COALESCE(NULLIF(TRIM(r.event_name), ''), '') AS event_name,
                        COALESCE(NULLIF(TRIM(rg.regatta_number::text), ''), '') AS regatta_number,
                        false AS is_series,
                        COALESCE(rg.start_date, r.start_date)::text AS start_date,
                        COALESCE(rg.end_date, rg.start_date, r.start_date)::text AS end_date,
                        COALESCE(r.class_canonical, r.class_original, '') AS class_name,
                        COALESCE(r.rank::text, '') AS rank,
                        COALESCE(r.rank_ordinal, '') AS rank_ordinal,
                        COALESCE(r.pos::text, '') AS pos,
                        COALESCE(r.race_scores, '{}'::jsonb) AS race_scores,
                        COALESCE(r.races_sailed, rb.races_sailed, 0)::int AS races_sailed,
                        COALESCE(NULLIF(TRIM(r.boat_name), ''), '') AS boat_name,
                        COALESCE(NULLIF(TRIM(r.sail_number), ''), '') AS sail_number
                    FROM results r
                    LEFT JOIN regatta_blocks rb ON rb.block_id = r.block_id
                    LEFT JOIN regattas rg ON rg.regatta_id = r.regatta_id
                    WHERE COALESCE(r.crew3_sa_sailing_id::text, '') = ANY(%s)
                )
                SELECT *
                FROM sailor_rows
                WHERE sas_id <> ''
                """,
                (cleaned_ids, cleaned_ids, cleaned_ids, cleaned_ids),
            )
            result_rows = cur.fetchall() or []
    finally:
        cur.close()
        return_db_connection(conn)
    out: dict[str, dict[str, Any]] = {}
    for row in profile_rows:
        data = dict(row)
        sid = _safe_text(data.get("sas_id"))
        if not sid:
            continue
        out[sid] = {
            "full_name": _safe_text(data.get("full_name")),
            "ssl_rank": data.get("ssl_rank"),
            "ssl_points": float(data.get("ssl_points") or 0) if data.get("ssl_points") not in (None, "") else None,
            "ssl_profile_url": _safe_text(data.get("ssl_profile_url")),
            "ssl_profile_slug": _safe_text(data.get("ssl_profile_slug")),
            "profile_regatta_count": 0,
            "profile_races_total": 0,
            "first_event_date": "",
            "last_event_date": "",
            "profile_first_count": 0,
            "profile_second_count": 0,
            "profile_third_count": 0,
        }
    rows_by_sid: dict[str, list[dict[str, Any]]] = {sid: [] for sid in out}
    seen_rows_by_sid: dict[str, set[tuple[str, str, str, str, str]]] = {sid: set() for sid in out}
    for raw in result_rows:
        row = dict(raw)
        sid = _safe_text(row.get("sas_id"))
        if sid not in rows_by_sid:
            continue
        dedupe_key = (
            _safe_text(row.get("regatta_id")),
            _safe_text(row.get("block_id")),
            _safe_text(row.get("class_name")),
            _safe_text(row.get("boat_name")),
            _safe_text(row.get("sail_number")),
        )
        if dedupe_key in seen_rows_by_sid[sid]:
            continue
        seen_rows_by_sid[sid].add(dedupe_key)
        rows_by_sid[sid].append(row)
    for sid, rows in rows_by_sid.items():
        included_rows = [row for row in rows if not _is_member_result_series_row(row) and _should_include_member_result_row(row, rows)]
        included_rows.sort(
            key=lambda row: (
                _iso(row.get("end_date") or row.get("start_date")),
                _safe_text(row.get("regatta_id")),
                _safe_text(row.get("block_id")),
            ),
            reverse=True,
        )
        regatta_event_keys: set[str] = set()
        race_seen: set[str] = set()
        medal_seen: set[str] = set()
        first_date = ""
        last_date = ""
        first_count = 0
        second_count = 0
        third_count = 0
        race_total = 0
        for row in included_rows:
            is_youth = _is_member_youth_subfleet_block(row.get("block_id"))
            event_key = _member_result_career_event_key(row)
            row_date = _iso(row.get("end_date") or row.get("start_date"))
            if not is_youth and event_key:
                regatta_event_keys.add(event_key)
                if event_key not in race_seen:
                    race_seen.add(event_key)
                    race_total += _count_races_for_result(row)
                if row_date and (not first_date or row_date < first_date):
                    first_date = row_date
                if row_date and (not last_date or row_date > last_date):
                    last_date = row_date
            rank_num = _result_rank_num(row)
            class_name = _result_class_name(row)
            if rank_num in (1, 2, 3):
                medal_event_key = f"{_safe_text(row.get('regatta_id'))}:{_member_result_block_tail(row.get('block_id'))}" if is_youth else event_key
                medal_key = f"{medal_event_key}|{rank_num}|{_norm_text_key(class_name)}"
                if medal_event_key and medal_key not in medal_seen:
                    medal_seen.add(medal_key)
                    if rank_num == 1:
                        first_count += 1
                    elif rank_num == 2:
                        second_count += 1
                    elif rank_num == 3:
                        third_count += 1
        item = out.get(sid)
        if not item:
            continue
        item["profile_regatta_count"] = len(regatta_event_keys)
        item["profile_races_total"] = race_total
        item["first_event_date"] = first_date
        item["last_event_date"] = last_date
        item["profile_first_count"] = first_count
        item["profile_second_count"] = second_count
        item["profile_third_count"] = third_count
    return out


def _published_ranking_map(
    sas_ids: list[str],
    *,
    get_db_connection: Callable[[], Any],
    return_db_connection: Callable[[Any], None],
    table_exists: Callable[[str], bool],
) -> dict[str, dict[str, Any]]:
    cleaned_ids: list[str] = []
    seen: set[str] = set()
    for value in sas_ids:
        sid = _safe_text(value)
        if not sid or sid in seen:
            continue
        seen.add(sid)
        cleaned_ids.append(sid)
    if not cleaned_ids or not table_exists("ranking_audits") or not table_exists("ranking_audit_entries"):
        return {}
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            SELECT audit_id
            FROM ranking_audits
            WHERE is_published = true
            ORDER BY calculated_at DESC NULLS LAST, audit_id DESC
            LIMIT 1
            """
        )
        head = cur.fetchone() or {}
        audit_id = head.get("audit_id")
        if not audit_id:
            return {}
        cur.execute(
            """
            SELECT
              sas_id,
              rank::int AS rank,
              sas_points::float8 AS sas_points
            FROM ranking_audit_entries
            WHERE audit_id = %s
              AND sas_id = ANY(%s)
            """,
            (audit_id, cleaned_ids),
        )
        rows = cur.fetchall() or []
    finally:
        cur.close()
        return_db_connection(conn)
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        data = dict(row)
        sid = _safe_text(data.get("sas_id"))
        if not sid:
            continue
        out[sid] = {
            "rank": int(data.get("rank") or 0) or None,
            "points": float(data.get("sas_points") or 0.0) or None,
        }
    return out


def _published_ranking_classes_map(
    sas_ids: list[str],
    *,
    get_db_connection: Callable[[], Any],
    return_db_connection: Callable[[Any], None],
    table_exists: Callable[[str], bool],
) -> dict[str, list[dict[str, Any]]]:
    cleaned_ids: list[str] = []
    seen: set[str] = set()
    for value in sas_ids:
        sid = _safe_text(value)
        if not sid or sid in seen:
            continue
        seen.add(sid)
        cleaned_ids.append(sid)
    if not cleaned_ids or not table_exists("ranking_audits") or not table_exists("ranking_audit_contribs"):
        return {}
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            SELECT audit_id
            FROM ranking_audits
            WHERE is_published = true
            ORDER BY calculated_at DESC NULLS LAST, audit_id DESC
            LIMIT 1
            """
        )
        audit = cur.fetchone() or {}
        audit_id = audit.get("audit_id")
        if not audit_id:
            return {}
        cur.execute(
            """
            SELECT
              sas_id,
              TRIM(COALESCE(meta->>'class_name', '')) AS class_name,
              COUNT(*)::int AS contrib_count,
              ROUND(COALESCE(SUM(points_awarded), 0), 3) AS total_points
            FROM ranking_audit_contribs
            WHERE audit_id = %s
              AND sas_id = ANY(%s)
              AND COALESCE(NULLIF(TRIM(sas_id), ''), '') <> ''
              AND COALESCE(NULLIF(TRIM(meta->>'class_name'), ''), '') <> ''
            GROUP BY sas_id, TRIM(COALESCE(meta->>'class_name', ''))
            ORDER BY sas_id ASC, COALESCE(SUM(points_awarded), 0) DESC, COUNT(*) DESC, LOWER(TRIM(COALESCE(meta->>'class_name', ''))) ASC
            """,
            (audit_id, cleaned_ids),
        )
        rows = cur.fetchall() or []
    finally:
        cur.close()
        return_db_connection(conn)
    out: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        data = dict(row)
        sid = _safe_text(data.get("sas_id"))
        class_name = _safe_text(data.get("class_name"))
        if not sid or not class_name:
            continue
        bucket = out.setdefault(sid, [])
        bucket.append(
            {
                "class_name": class_name,
                "contrib_count": int(data.get("contrib_count") or 0),
                "total_points": float(data.get("total_points") or 0.0),
            }
        )
    return out


def _direct_targets(profile: dict[str, Any], mentions: list[dict[str, Any]]) -> dict[str, list[str]]:
    sailor_names: list[str] = []
    sailor_ids: list[str] = []
    boat_names: list[str] = []
    sail_numbers: list[str] = []

    for row in _json_list(profile.get("mention_targets")):
        if not isinstance(row, dict):
            continue
        first = _safe_text(row.get("first_name"))
        last = _safe_text(row.get("last_name"))
        full_name = " ".join([x for x in [first, last] if x]).strip()
        if full_name:
            sailor_names.append(_norm_text_key(full_name))
        for alias in _json_list(row.get("aliases")):
            alias_name = _safe_text(alias)
            if alias_name:
                sailor_names.append(_norm_text_key(alias_name))

    for row in _json_list(profile.get("boat_targets")):
        if not isinstance(row, dict):
            continue
        boat_name = _safe_text(row.get("boat_name"))
        if boat_name:
            boat_names.append(_norm_text_key(boat_name))
        for sail_no in _json_list(row.get("sail_numbers")):
            cleaned = _norm_sail_number(sail_no)
            if cleaned:
                sail_numbers.append(cleaned)

    for item in mentions:
        for sailor in _json_list(item.get("resolved_sailors")):
            if not isinstance(sailor, dict):
                continue
            sid = _safe_text(sailor.get("sa_sailing_id"))
            if sid:
                sailor_ids.append(sid)
            for key in ("full_name", "input_name"):
                label = _norm_text_key(sailor.get(key))
                if label:
                    sailor_names.append(label)
        for boat in _json_list(item.get("matched_boats")):
            label = _norm_text_key(boat)
            if label:
                boat_names.append(label)
        for sail_no in _json_list(item.get("matched_sail_nos")):
            cleaned = _norm_sail_number(sail_no)
            if cleaned:
                sail_numbers.append(cleaned)

    def _dedupe(values: list[str]) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for value in values:
            v = _safe_text(value)
            if not v or v in seen:
                continue
            seen.add(v)
            out.append(v)
        return out

    return {
        "sailor_names": _dedupe(sailor_names),
        "sailor_ids": _dedupe(sailor_ids),
        "boat_names": _dedupe(boat_names),
        "sail_numbers": _dedupe(sail_numbers),
    }


def _proof_urls_for_row(row: dict[str, Any], mentions: list[dict[str, Any]]) -> list[str]:
    boat_name = _norm_text_key(row.get("boat_name"))
    sail_number = _norm_sail_number(row.get("sail_number"))
    scored: list[tuple[int, str]] = []
    seen_urls: set[str] = set()
    for item in mentions:
        source_url = _safe_url(item.get("source_url"))
        if not source_url or source_url in seen_urls:
            continue
        score = 0
        for boat in _json_list(item.get("matched_boats")):
            if boat_name and _norm_text_key(boat) == boat_name:
                score += 4
        for sail_no in _json_list(item.get("matched_sail_nos")):
            mention_sail_no = _norm_sail_number(sail_no)
            if sail_number and mention_sail_no == sail_number:
                score += 4
        if score > 0:
            seen_urls.add(source_url)
            scored.append((score, source_url))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [url for _, url in scored]


def _is_strict_proof_mention(item: dict[str, Any]) -> bool:
    payload = _json_dict(item.get("source_payload"))
    provider_payload = _json_dict(payload.get("source_payload"))
    provider = _safe_text(provider_payload.get("provider") or payload.get("provider")).lower()
    if provider in {"source_crawl", "serpapi", "google_cse", "google_rss", "facebook_graph"}:
        return True
    matched = [dict(x) for x in _json_list(item.get("resolved_sailors")) if isinstance(x, dict)]
    if not matched:
        return False
    source_url = _safe_url(item.get("source_url"))
    domain = urlparse(source_url).netloc.lower()
    if "ullman" not in domain:
        return False
    return False


def _direct_result_rows(
    targets: dict[str, list[str]],
    *,
    get_db_connection: Callable[[], Any],
    return_db_connection: Callable[[Any], None],
    table_exists: Callable[[str], bool],
) -> list[dict[str, Any]]:
    if not table_exists("results"):
        return []
    sailor_names = targets.get("sailor_names") or []
    sailor_ids = targets.get("sailor_ids") or []
    boat_names = targets.get("boat_names") or []
    sail_numbers = targets.get("sail_numbers") or []
    if not any([sailor_names, sailor_ids, boat_names, sail_numbers]):
        return []
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            WITH matched AS (
                SELECT
                    r.regatta_id::text AS regatta_id,
                    COALESCE(rg.event_name, r.event_name, r.regatta_id::text) AS event_name,
                    rg.start_date AS start_date,
                    rg.end_date AS end_date,
                    COALESCE(cl.class_id, rb.class_id, r.class_id) AS class_id,
                    COALESCE(
                        NULLIF(r.rank, 0),
                        NULLIF(CASE WHEN r.rank_ordinal ~ '^[0-9]+$' THEN r.rank_ordinal::int ELSE NULL END, 0),
                        NULLIF(CASE WHEN r.pos::text ~ '^[0-9]+$' THEN r.pos::int ELSE NULL END, 0)
                    ) AS place_raw,
                    COALESCE(NULLIF(TRIM(r.helm_name), ''), NULLIF(TRIM(r.crew_name), ''), 'Unknown') AS sailor_name,
                    COALESCE(NULLIF(TRIM(r.helm_name), ''), '') AS helm_name,
                    COALESCE(NULLIF(TRIM(r.crew_name), ''), '') AS crew_name,
                    COALESCE(NULLIF(TRIM(r.crew2_name), ''), '') AS crew2_name,
                    COALESCE(NULLIF(TRIM(r.crew3_name), ''), '') AS crew3_name,
                    COALESCE(r.helm_sa_sailing_id::text, '') AS helm_sas_id,
                    COALESCE(r.crew_sa_sailing_id::text, '') AS crew_sas_id,
                    COALESCE(r.crew2_sa_sailing_id::text, '') AS crew2_sas_id,
                    COALESCE(r.crew3_sa_sailing_id::text, '') AS crew3_sas_id,
                    COALESCE(NULLIF(TRIM(r.class_canonical), ''), NULLIF(TRIM(r.class_original), ''), '') AS class_name,
                    COALESCE(NULLIF(TRIM(r.fleet_label), ''), NULLIF(TRIM(r.class_canonical), ''), NULLIF(TRIM(r.class_original), ''), '') AS fleet_name,
                    COALESCE(rg.end_date, rg.start_date, r.start_date)::text AS event_date,
                    NULLIF(TRIM(cl.logo_path), '') AS class_logo_path,
                    COALESCE(NULLIF(TRIM(r.boat_name), ''), '') AS boat_name,
                    COALESCE(NULLIF(TRIM(r.sail_number), ''), '') AS sail_number,
                    COALESCE(r.races_sailed, rb.races_sailed, 0) AS races_sailed,
                    r.as_at_time::text AS as_at_time
                FROM results r
                LEFT JOIN regattas rg ON rg.regatta_id = r.regatta_id
                LEFT JOIN regatta_blocks rb ON rb.block_id = r.block_id
                LEFT JOIN classes cl ON cl.class_id = COALESCE(r.class_id, rb.class_id)
                WHERE (
                    (%s <> '{}'::text[] AND r.helm_sa_sailing_id::text = ANY(%s))
                    OR (%s <> '{}'::text[] AND r.crew_sa_sailing_id::text = ANY(%s))
                    OR (%s <> '{}'::text[] AND COALESCE(r.crew2_sa_sailing_id::text, '') = ANY(%s))
                    OR (%s <> '{}'::text[] AND COALESCE(r.crew3_sa_sailing_id::text, '') = ANY(%s))
                    OR (%s <> '{}'::text[] AND LOWER(TRIM(COALESCE(r.helm_name, ''))) = ANY(%s))
                    OR (%s <> '{}'::text[] AND LOWER(TRIM(COALESCE(r.crew_name, ''))) = ANY(%s))
                    OR (%s <> '{}'::text[] AND LOWER(TRIM(COALESCE(r.crew2_name, ''))) = ANY(%s))
                    OR (%s <> '{}'::text[] AND LOWER(TRIM(COALESCE(r.crew3_name, ''))) = ANY(%s))
                    OR (%s <> '{}'::text[] AND LOWER(TRIM(COALESCE(r.boat_name, ''))) = ANY(%s))
                    OR (%s <> '{}'::text[] AND regexp_replace(LOWER(COALESCE(r.sail_number, '')), '[^a-z0-9]+', '', 'g') = ANY(%s))
                )
                  AND COALESCE(
                        NULLIF(r.rank, 0),
                        NULLIF(CASE WHEN r.rank_ordinal ~ '^[0-9]+$' THEN r.rank_ordinal::int ELSE NULL END, 0),
                        NULLIF(CASE WHEN r.pos::text ~ '^[0-9]+$' THEN r.pos::int ELSE NULL END, 0)
                  ) IS NOT NULL
            )
            SELECT *
            FROM matched
            ORDER BY COALESCE(end_date, start_date) DESC NULLS LAST,
                     regatta_id ASC,
                     place_raw ASC,
                     LOWER(fleet_name) ASC,
                     LOWER(sailor_name) ASC
            LIMIT 250
            """,
            (
                sailor_ids, sailor_ids,
                sailor_ids, sailor_ids,
                sailor_ids, sailor_ids,
                sailor_ids, sailor_ids,
                sailor_names, sailor_names,
                sailor_names, sailor_names,
                sailor_names, sailor_names,
                sailor_names, sailor_names,
                boat_names, boat_names,
                sail_numbers, sail_numbers,
            ),
        )
        rows = cur.fetchall() or []
    finally:
        cur.close()
        return_db_connection(conn)
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str, str, str]] = set()
    for row in rows:
        data = dict(row)
        rid = _safe_text(data.get("regatta_id"))
        sailor_name = _safe_text(data.get("sailor_name")) or "Unknown"
        event_name = _safe_text(data.get("event_name")) or rid
        place_raw = data.get("place_raw")
        class_name = _safe_text(data.get("class_name"))
        fleet_name = _safe_text(data.get("fleet_name")) or class_name
        boat_name = _safe_text(data.get("boat_name"))
        sail_number = _safe_text(data.get("sail_number"))
        boat_name_key = boat_name.lower()
        sail_number_key = _norm_sail_number(sail_number)
        key = (rid, sailor_name.lower(), str(place_raw), class_name.lower(), boat_name.lower(), sail_number.lower())
        if key in seen:
            continue
        seen.add(key)
        people: list[dict[str, str]] = []
        seen_people: set[tuple[str, str]] = set()
        for name_key, id_key in (
            ("helm_name", "helm_sas_id"),
            ("crew_name", "crew_sas_id"),
            ("crew2_name", "crew2_sas_id"),
            ("crew3_name", "crew3_sas_id"),
        ):
            person_name = _safe_text(data.get(name_key))
            person_id = _safe_text(data.get(id_key))
            if not person_name:
                continue
            person_key = (person_id or "", person_name.lower())
            if person_key in seen_people:
                continue
            seen_people.add(person_key)
            people.append({"name": person_name, "sas_id": person_id})
        matched_by_sailor = False
        for person in people:
            person_name_key = _norm_text_key(person.get("name"))
            person_id_key = _safe_text(person.get("sas_id"))
            if (person_id_key and person_id_key in sailor_ids) or (person_name_key and person_name_key in sailor_names):
                matched_by_sailor = True
                break
        matched_by_boat = bool(boat_name_key and boat_name_key in boat_names)
        matched_by_sail_number = bool(sail_number_key and sail_number_key in sail_numbers)
        out.append(
            {
                "regatta_id": rid,
                "event_name": event_name,
                "start_date": _iso(data.get("start_date")),
                "end_date": _iso(data.get("end_date") or data.get("start_date")),
                "class_id": data.get("class_id"),
                "sailor_name": sailor_name,
                "place_raw": int(place_raw) if place_raw not in (None, "") else None,
                "class_name": class_name,
                "fleet_name": fleet_name,
                "event_date": _safe_text(data.get("event_date")),
                "class_logo_path": _safe_text(data.get("class_logo_path")),
                "boat_name": boat_name,
                "sail_number": sail_number,
                "races_sailed": int(data.get("races_sailed") or 0),
                "as_at_time": _safe_text(data.get("as_at_time")),
                "people": people,
                "matched_by_sailor": matched_by_sailor,
                "matched_by_boat": matched_by_boat,
                "matched_by_sail_number": matched_by_sail_number,
                "url": f"/regatta/{rid}",
            }
        )
    return out


def _direct_linked_sailors(
    rows: list[dict[str, Any]],
    mentions: list[dict[str, Any]],
    *,
    get_db_connection: Callable[[], Any],
    return_db_connection: Callable[[Any], None],
    table_exists: Callable[[str], bool],
) -> list[dict[str, Any]]:
    agg: dict[str, dict[str, Any]] = {}
    for row in rows:
        row_proof_urls = _proof_urls_for_row(row, mentions)
        row_proof_domains = {
            urlparse(url).netloc.replace("www.", "")
            for url in row_proof_urls
            if _safe_url(url)
        }
        boat_match = bool(row.get("matched_by_boat")) or bool(row.get("matched_by_sail_number"))
        boat_proof_applies = boat_match and bool(row_proof_urls)
        regatta_id = _safe_text(row.get("regatta_id"))
        place_raw = int(row.get("place_raw") or 0)
        races_sailed = int(row.get("races_sailed") or 0)
        year_value = ""
        for value in (row.get("start_date"), row.get("end_date"), row.get("event_date")):
            match = re.match(r"^(\d{4})", _safe_text(value))
            if match:
                year_value = match.group(1)
                break
        row_key = (
            regatta_id,
            _norm_text_key(row.get("class_name")),
            _norm_text_key(row.get("fleet_name")),
            _norm_text_key(row.get("boat_name")),
            _norm_sail_number(row.get("sail_number")),
            str(place_raw),
        )
        for person in _json_list(row.get("people")):
            if not isinstance(person, dict):
                continue
            name = _safe_text(person.get("name"))
            sas_id = _safe_text(person.get("sas_id"))
            if not name:
                continue
            key = _norm_text_key(name)
            if not key:
                continue
            item = agg.setdefault(
                key,
                {
                    "sas_id": "",
                    "name": name,
                    "regatta_ids": set(),
                    "row_keys": set(),
                    "mention_urls": set(),
                    "mention_domains": set(),
                    "has_boat_target_match": False,
                    "regatta_count": 0,
                    "races_total": 0,
                    "first_count": 0,
                    "second_count": 0,
                    "third_count": 0,
                    "since_year": "",
                    "last_active_date": "",
                    "sort_score": 0.0,
                },
            )
            if sas_id and not _safe_text(item.get("sas_id")):
                item["sas_id"] = sas_id
            current_name = _safe_text(item.get("name"))
            if not current_name or (len(name) > len(current_name) and key == _norm_text_key(current_name)):
                item["name"] = name
            if regatta_id:
                regatta_ids = item["regatta_ids"]
                regatta_ids.add(regatta_id)
                item["regatta_count"] = len(regatta_ids)
            row_keys = item["row_keys"]
            if row_key not in row_keys:
                row_keys.add(row_key)
                item["races_total"] += races_sailed
                if place_raw == 1:
                    item["first_count"] += 1
                elif place_raw == 2:
                    item["second_count"] += 1
                elif place_raw == 3:
                    item["third_count"] += 1
            if year_value and (not _safe_text(item.get("since_year")) or year_value < _safe_text(item.get("since_year"))):
                item["since_year"] = year_value
            row_date = ""
            for value in (row.get("end_date"), row.get("start_date"), row.get("event_date")):
                iso_value = _iso(value)
                if iso_value:
                    row_date = iso_value
                    break
            if row_date and (not _safe_text(item.get("last_active_date")) or row_date > _safe_text(item.get("last_active_date"))):
                item["last_active_date"] = row_date
            if boat_match:
                item["has_boat_target_match"] = True
            if boat_proof_applies:
                mention_urls = item.setdefault("mention_urls", set())
                mention_domains = item.setdefault("mention_domains", set())
                mention_urls.update(row_proof_urls)
                mention_domains.update(domain for domain in row_proof_domains if domain)
    profile_stats = _sailor_profile_stats(
        [_safe_text(item.get("sas_id")) for item in agg.values() if _safe_text(item.get("sas_id"))],
        get_db_connection=get_db_connection,
        return_db_connection=return_db_connection,
        table_exists=table_exists,
    )
    published_ranks = _published_ranking_map(
        [_safe_text(item.get("sas_id")) for item in agg.values() if _safe_text(item.get("sas_id"))],
        get_db_connection=get_db_connection,
        return_db_connection=return_db_connection,
        table_exists=table_exists,
    )
    published_classes = _published_ranking_classes_map(
        [_safe_text(item.get("sas_id")) for item in agg.values() if _safe_text(item.get("sas_id"))],
        get_db_connection=get_db_connection,
        return_db_connection=return_db_connection,
        table_exists=table_exists,
    )
    sid_lookup = {_safe_text(item.get("sas_id")): key for key, item in agg.items() if _safe_text(item.get("sas_id"))}
    for mention in mentions:
        mention_url = _safe_url(mention.get("source_url"))
        mention_domain = _safe_text(mention.get("source_domain"))
        if not mention_url:
            continue
        matched_keys: set[str] = set()
        for sailor in _json_list(mention.get("resolved_sailors")):
            if not isinstance(sailor, dict):
                continue
            status = _safe_text(sailor.get("status"))
            if not status:
                continue
            sid = _safe_text(sailor.get("sa_sailing_id"))
            full_name = _norm_text_key(sailor.get("full_name"))
            input_name = _norm_text_key(sailor.get("input_name"))
            if sid and sid in sid_lookup:
                matched_keys.add(sid_lookup[sid])
            elif full_name and full_name in agg:
                matched_keys.add(full_name)
            elif input_name and input_name in agg:
                matched_keys.add(input_name)
        for key in matched_keys:
            item = agg.get(key)
            if not item:
                continue
            mention_urls = item.setdefault("mention_urls", set())
            mention_urls.add(mention_url)
            if mention_domain:
                mention_domains = item.setdefault("mention_domains", set())
                mention_domains.add(mention_domain)
    out = []
    for item in agg.values():
        mention_urls = sorted(_safe_url(url) for url in (item.get("mention_urls") or set()) if _safe_url(url))
        if not mention_urls and not bool(item.get("has_boat_target_match")):
            continue
        regatta_count = int(item.get("regatta_count") or 0)
        sponsor_first_count = int(item.get("first_count") or 0)
        sponsor_second_count = int(item.get("second_count") or 0)
        sponsor_third_count = int(item.get("third_count") or 0)
        first_count = sponsor_first_count
        second_count = sponsor_second_count
        third_count = sponsor_third_count
        podium_count = first_count + second_count + third_count
        win_rate = (first_count / regatta_count) if regatta_count else 0.0
        podium_rate = (podium_count / regatta_count) if regatta_count else 0.0
        sid = _safe_text(item.get("sas_id"))
        profile = profile_stats.get(sid) or {}
        has_profile = bool(profile)
        profile_regatta_count = int(profile.get("profile_regatta_count") or 0)
        profile_races_total = int(profile.get("profile_races_total") or 0)
        profile_first_count = int(profile.get("profile_first_count") or 0)
        profile_second_count = int(profile.get("profile_second_count") or 0)
        profile_third_count = int(profile.get("profile_third_count") or 0)
        profile_since = _safe_text(profile.get("first_event_date"))[:4]
        profile_last_active = _safe_text(profile.get("last_event_date"))
        published = published_ranks.get(sid) or {}
        ranking_classes = published_classes.get(sid) or []
        ranking_rank = published.get("rank")
        ranking_points = published.get("points")
        ssl_rank = profile.get("ssl_rank")
        ssl_points = float(profile.get("ssl_points") or 0.0)
        mention_count = len(mention_urls)
        media_domain_count = len(item.get("mention_domains") or set())
        display_regatta_count = profile_regatta_count if has_profile else regatta_count
        display_races_total = profile_races_total if has_profile else int(item.get("races_total") or 0)
        display_since_year = profile_since if has_profile else _safe_text(item.get("since_year"))
        display_last_active = profile_last_active if has_profile else _safe_text(item.get("last_active_date"))
        display_first_count = profile_first_count if has_profile else sponsor_first_count
        display_second_count = profile_second_count if has_profile else sponsor_second_count
        display_third_count = profile_third_count if has_profile else sponsor_third_count
        rank_bonus = 0.0
        if ssl_rank not in (None, "", 0):
            rank_bonus = max(0.0, 2500.0 - float(ssl_rank)) * 0.015
        points_bonus = min(ssl_points, 5000.0) * 0.02
        experience_bonus = min(display_regatta_count, 400) * 0.18
        media_bonus = (mention_count * 18.0) + (media_domain_count * 8.0)
        item["profile_regatta_count"] = display_regatta_count
        item["profile_races_total"] = display_races_total
        item["since_year"] = display_since_year
        item["last_active_date"] = display_last_active
        item["first_count"] = display_first_count
        item["second_count"] = display_second_count
        item["third_count"] = display_third_count
        item["sponsor_first_count"] = sponsor_first_count
        item["sponsor_second_count"] = sponsor_second_count
        item["sponsor_third_count"] = sponsor_third_count
        item["ssl_rank"] = ssl_rank
        item["ssl_points"] = ssl_points if ssl_points else None
        item["ranking_rank"] = ranking_rank
        item["ranking_points"] = ranking_points
        item["ranking_classes"] = ranking_classes[:12]
        item["media_mentions"] = mention_count
        item["media_domains"] = media_domain_count
        item["proof_urls"] = mention_urls
        item["proof_url"] = mention_urls[0] if mention_urls else ""
        item["sort_score"] = (
            (display_first_count * 100000.0)
            + (display_regatta_count * 1000.0)
            + (display_second_count * 100.0)
            + (display_third_count * 10.0)
            + (display_races_total * 0.01)
        )
        item["is_ranked"] = 1 if ranking_rank not in (None, "", 0) else 0
        item.pop("mention_urls", None)
        item.pop("mention_domains", None)
        item.pop("has_boat_target_match", None)
        item.pop("regatta_ids", None)
        item.pop("row_keys", None)
        out.append(item)
    out.sort(
        key=lambda item: (
            -int(item.get("is_ranked") or 0),
            int(item.get("ranking_rank") or 999999),
            -int(item.get("first_count") or 0),
            -int(item.get("profile_regatta_count") or item.get("regatta_count") or 0),
            -int(item.get("second_count") or 0),
            -int(item.get("third_count") or 0),
            -float(item.get("sort_score") or 0.0),
            -_date_sort_int(item.get("last_active_date")),
            float(item.get("ssl_rank") or 999999),
            -int(item.get("profile_races_total") or item.get("races_total") or 0),
            _safe_text(item.get("name")).lower(),
        )
    )
    return out


def _class_match_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", _safe_text(value).lower())


def _direct_linked_classes(
    mentions: list[dict[str, Any]],
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    agg: dict[str, dict[str, Any]] = {}
    for mention in mentions:
        classes = [_safe_text(x) for x in _json_list(mention.get("matched_classes")) if _safe_text(x)]
        if not classes:
            continue
        sponsored_sailors = []
        for sailor in _json_list(mention.get("resolved_sailors")):
            if not isinstance(sailor, dict):
                continue
            status = _safe_text(sailor.get("status"))
            if not status:
                continue
            sponsored_sailors.append(
                {
                    "name": _safe_text(sailor.get("full_name")) or _safe_text(sailor.get("input_name")),
                    "class_keys": {_class_match_key(x) for x in _json_list(sailor.get("primary_classes")) if _safe_text(x)},
                }
            )
        if not sponsored_sailors:
            continue
        mention_url = _safe_url(mention.get("source_url"))
        for label in classes:
            if not _is_boat_class_label(label):
                continue
            class_key = _class_match_key(label)
            matched_names = sorted(
                {
                    _safe_text(sailor.get("name"))
                    for sailor in sponsored_sailors
                    if _safe_text(sailor.get("name")) and class_key and class_key in (sailor.get("class_keys") or set())
                }
            )
            if not matched_names:
                continue
            key = _norm_text_key(label)
            item = agg.setdefault(
                key,
                {
                    "class_id": "",
                    "class_name": label,
                    "logo_path": "",
                    "mention_count": 0,
                    "boat_proof_count": 0,
                    "sailor_count": 0,
                    "_mention_urls": set(),
                    "_boat_row_keys": set(),
                    "_sailor_names": set(),
                },
            )
            if mention_url and mention_url not in item["_mention_urls"]:
                item["_mention_urls"].add(mention_url)
                item["mention_count"] += 1
            for name in matched_names:
                if name not in item["_sailor_names"]:
                    item["_sailor_names"].add(name)
            item["sailor_count"] = len(item["_sailor_names"])
    for row in rows:
        if not (bool(row.get("matched_by_boat")) or bool(row.get("matched_by_sail_number"))):
            continue
        label = _safe_text(row.get("class_name"))
        if not _is_boat_class_label(label):
            continue
        key = _norm_text_key(label)
        if not key:
            continue
        item = agg.setdefault(
            key,
            {
                "class_id": row.get("class_id") or "",
                "class_name": label,
                "logo_path": _safe_text(row.get("class_logo_path")),
                "mention_count": 0,
                "boat_proof_count": 0,
                "sailor_count": 0,
                "_mention_urls": set(),
                "_boat_row_keys": set(),
                "_sailor_names": set(),
            },
        )
        if not item.get("class_id") and row.get("class_id") not in (None, ""):
            item["class_id"] = row.get("class_id")
        if not item.get("logo_path"):
            item["logo_path"] = _safe_text(row.get("class_logo_path"))
        row_key = (
            _safe_text(row.get("regatta_id")),
            _norm_text_key(row.get("boat_name")),
            _norm_sail_number(row.get("sail_number")),
            _norm_text_key(label),
        )
        if row_key not in item["_boat_row_keys"]:
            item["_boat_row_keys"].add(row_key)
            item["boat_proof_count"] += 1
        for person in _json_list(row.get("people")):
            if not isinstance(person, dict):
                continue
            name = _safe_text(person.get("name"))
            if not name:
                continue
            item["_sailor_names"].add(name)
        item["sailor_count"] = len(item["_sailor_names"])
    out: list[dict[str, Any]] = []
    for item in agg.values():
        item.pop("_mention_urls", None)
        item.pop("_boat_row_keys", None)
        item.pop("_sailor_names", None)
        out.append(item)
    out.sort(
        key=lambda x: (
            -int(x.get("sailor_count") or 0),
            -(int(x.get("mention_count") or 0) + int(x.get("boat_proof_count") or 0)),
            _safe_text(x.get("class_name")).lower(),
        )
    )
    return out


def _direct_latest_results(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        return []
    preferred_rows = [
        row for row in rows
        if _json_list(row.get("proof_urls"))
        and (bool(row.get("matched_by_boat")) or bool(row.get("matched_by_sail_number")))
    ]
    if not preferred_rows:
        return []
    sorted_rows = sorted(
        preferred_rows,
        key=lambda row: (
            _safe_text(row.get("end_date") or row.get("start_date")),
            _safe_text(row.get("regatta_id")),
        ),
        reverse=True,
    )
    latest_regatta_id = _safe_text(sorted_rows[0].get("regatta_id"))
    latest_rows = [row for row in sorted_rows if _safe_text(row.get("regatta_id")) == latest_regatta_id]
    latest_rows.sort(
        key=lambda row: (
            int(row.get("place_raw") or 999999),
            _safe_text(row.get("fleet_name")).lower(),
            _safe_text(row.get("boat_name")).lower(),
        )
    )
    return latest_rows[:40]


def _boat_target_rows(profile: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in _json_list(profile.get("boat_targets")):
        if not isinstance(row, dict):
            continue
        boat_name = _safe_text(row.get("boat_name"))
        if not boat_name:
            continue
        sail_numbers = [_safe_text(x) for x in _json_list(row.get("sail_numbers")) if _safe_text(x)]
        out.append(
            {
                "boat_name": boat_name,
                "boat_key": _norm_text_key(boat_name),
                "class_category": _safe_text(row.get("class_category")),
                "sail_numbers": sail_numbers,
                "sail_keys": {_norm_sail_number(x) for x in sail_numbers if _norm_sail_number(x)},
                "sail_digit_keys": {_norm_sail_digits(x) for x in sail_numbers if _norm_sail_digits(x)},
            }
        )
    return out


def _canonical_boat_meta(row: dict[str, Any], target_rows: list[dict[str, Any]]) -> dict[str, str]:
    boat_name = _safe_text(row.get("boat_name"))
    sail_number = _safe_text(row.get("sail_number"))
    boat_key = _norm_text_key(boat_name)
    sail_key = _norm_sail_number(sail_number)
    sail_digits = _norm_sail_digits(sail_number)
    class_name = _safe_text(row.get("class_name"))
    for target in target_rows:
        if sail_key and sail_key in target["sail_keys"]:
            return {
                "boat_name": _safe_text(target.get("boat_name")) or boat_name,
                "sail_number": sail_number,
                "class_name": _safe_text(target.get("class_category")) or class_name,
            }
        if sail_digits and sail_digits in target["sail_digit_keys"]:
            return {
                "boat_name": _safe_text(target.get("boat_name")) or boat_name,
                "sail_number": sail_number,
                "class_name": _safe_text(target.get("class_category")) or class_name,
            }
        target_name = _safe_text(target.get("boat_name"))
        target_key = _safe_text(target.get("boat_key"))
        if boat_key and target_key and (boat_key == target_key or boat_key.endswith(target_key) or target_key.endswith(boat_key)):
            inferred_class = class_name
            if not inferred_class and len(_json_list(target.get("sail_numbers"))) == 1:
                inferred_class = _safe_text(target.get("class_category"))
            return {
                "boat_name": target_name or boat_name,
                "sail_number": sail_number,
                "class_name": inferred_class,
            }
    return {
        "boat_name": boat_name or "Unnamed boat",
        "sail_number": sail_number,
        "class_name": class_name,
    }


def _direct_boats(rows: list[dict[str, Any]], profile: dict[str, Any]) -> list[dict[str, Any]]:
    target_rows = _boat_target_rows(profile)
    agg: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not (bool(row.get("matched_by_boat")) or bool(row.get("matched_by_sail_number"))):
            continue
        meta = _canonical_boat_meta(row, target_rows)
        boat_name = _safe_text(meta.get("boat_name"))
        sail_number = _safe_text(meta.get("sail_number"))
        if not boat_name and not sail_number:
            continue
        sail_key = _norm_sail_digits(sail_number) or _norm_sail_number(sail_number)
        key = (_norm_text_key(boat_name) or "unknown", sail_key)
        item = agg.setdefault(
            "|".join(key),
            {
                "boat_name": boat_name or "Unnamed boat",
                "sail_number": sail_number,
                "class_name": _safe_text(meta.get("class_name")),
                "class_id": row.get("class_id"),
                "event_count": 0,
                "latest_event_name": "",
                "latest_event_date": "",
                "latest_regatta_id": "",
                "_regattas": set(),
                "sailors": [],
                "_seen_sailors": set(),
            },
        )
        rid = _safe_text(row.get("regatta_id"))
        if rid and rid not in item["_regattas"]:
            item["_regattas"].add(rid)
            item["event_count"] += 1
        event_date = _safe_text(row.get("end_date") or row.get("start_date") or row.get("event_date"))
        if event_date >= _safe_text(item.get("latest_event_date")):
            item["latest_event_date"] = event_date
            item["latest_event_name"] = _safe_text(row.get("event_name"))
            item["latest_regatta_id"] = rid
        if len(sail_number) > len(_safe_text(item.get("sail_number"))):
            item["sail_number"] = sail_number
        if not _safe_text(item.get("class_name")):
            item["class_name"] = _safe_text(meta.get("class_name"))
        if not item.get("class_id") and row.get("class_id") not in (None, ""):
            item["class_id"] = row.get("class_id")
        for person in _json_list(row.get("people")):
            if not isinstance(person, dict):
                continue
            label = _safe_text(person.get("name"))
            sas_id = _safe_text(person.get("sas_id"))
            if not label:
                continue
            label_key = f"{sas_id}|{label.lower()}"
            if label_key in item["_seen_sailors"]:
                continue
            item["_seen_sailors"].add(label_key)
            item["sailors"].append({"name": label, "sas_id": sas_id})
    out: list[dict[str, Any]] = []
    for item in agg.values():
        item.pop("_regattas", None)
        item.pop("_seen_sailors", None)
        out.append(item)
    out.sort(
        key=lambda row: (
            -int(row.get("event_count") or 0),
            -_date_sort_int(row.get("latest_event_date")),
            _safe_text(row.get("boat_name")).lower(),
        ),
        reverse=False,
    )
    return out


def _split_regattas(regattas: list[dict[str, Any]], with_results: set[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    today = date.today().isoformat()
    upcoming = []
    results = []
    other = []
    for row in regattas:
        rid = _safe_text(row.get("regatta_id"))
        end_date = _safe_text(row.get("end_date") or row.get("start_date"))
        if end_date and end_date >= today:
            upcoming.append(row)
        if rid in with_results:
            results.append(row)
        elif not end_date or end_date < today:
            other.append(row)
    upcoming.sort(key=lambda row: (_safe_text(row.get("start_date") or row.get("end_date")), _safe_text(row.get("event_name")).lower()))
    results.sort(key=lambda row: (_safe_text(row.get("end_date") or row.get("start_date")), _safe_text(row.get("event_name")).lower()), reverse=True)
    other.sort(key=lambda row: (_safe_text(row.get("end_date") or row.get("start_date")), _safe_text(row.get("event_name")).lower()), reverse=True)
    return upcoming, results, other


def _latest_results(
    regatta_ids: list[str],
    *,
    get_db_connection: Callable[[], Any],
    return_db_connection: Callable[[Any], None],
    table_exists: Callable[[str], bool],
) -> list[dict[str, Any]]:
    if not regatta_ids or not table_exists("results"):
        return []
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            WITH latest_event AS (
                SELECT r.regatta_id::text AS regatta_id
                FROM results r
                LEFT JOIN regattas rg ON rg.regatta_id = r.regatta_id
                WHERE r.regatta_id = ANY(%s)
                  AND COALESCE(
                        NULLIF(r.rank, 0),
                        NULLIF(CASE WHEN r.rank_ordinal ~ '^[0-9]+$' THEN r.rank_ordinal::int ELSE NULL END, 0),
                        NULLIF(CASE WHEN r.pos::text ~ '^[0-9]+$' THEN r.pos::int ELSE NULL END, 0)
                  ) IS NOT NULL
                ORDER BY COALESCE(rg.end_date, rg.start_date, r.start_date) DESC NULLS LAST,
                         r.regatta_id::text ASC
                LIMIT 1
            )
            SELECT
                r.regatta_id::text AS regatta_id,
                COALESCE(rg.event_name, r.event_name, r.regatta_id::text) AS event_name,
                rg.start_date AS start_date,
                rg.end_date AS end_date,
                COALESCE(
                    NULLIF(r.rank, 0),
                    NULLIF(CASE WHEN r.rank_ordinal ~ '^[0-9]+$' THEN r.rank_ordinal::int ELSE NULL END, 0),
                    NULLIF(CASE WHEN r.pos::text ~ '^[0-9]+$' THEN r.pos::int ELSE NULL END, 0)
                ) AS place_raw,
                COALESCE(NULLIF(TRIM(r.helm_name), ''), NULLIF(TRIM(r.crew_name), ''), 'Unknown') AS sailor_name,
                COALESCE(NULLIF(TRIM(r.class_canonical), ''), NULLIF(TRIM(r.class_original), ''), '') AS class_name,
                COALESCE(NULLIF(TRIM(r.fleet_label), ''), NULLIF(TRIM(r.class_canonical), ''), NULLIF(TRIM(r.class_original), ''), '') AS fleet_name,
                COALESCE(rg.end_date, rg.start_date, r.start_date)::text AS event_date,
                NULLIF(TRIM(cl.logo_path), '') AS class_logo_path,
                COALESCE(NULLIF(TRIM(r.boat_name), ''), '') AS boat_name,
                COALESCE(NULLIF(TRIM(r.sail_number), ''), '') AS sail_number,
                COALESCE(r.races_sailed, rb.races_sailed, 0) AS races_sailed,
                r.as_at_time::text AS as_at_time
            FROM results r
            JOIN latest_event le ON le.regatta_id = r.regatta_id::text
            LEFT JOIN regattas rg ON rg.regatta_id = r.regatta_id
            LEFT JOIN regatta_blocks rb ON rb.block_id = r.block_id
            LEFT JOIN classes cl ON cl.class_id = COALESCE(r.class_id, rb.class_id)
            WHERE COALESCE(
                    NULLIF(r.rank, 0),
                    NULLIF(CASE WHEN r.rank_ordinal ~ '^[0-9]+$' THEN r.rank_ordinal::int ELSE NULL END, 0),
                    NULLIF(CASE WHEN r.pos::text ~ '^[0-9]+$' THEN r.pos::int ELSE NULL END, 0)
              ) IS NOT NULL
            ORDER BY COALESCE(rg.end_date, rg.start_date, r.start_date) DESC NULLS LAST,
                     COALESCE(
                        NULLIF(r.rank, 0),
                        NULLIF(CASE WHEN r.rank_ordinal ~ '^[0-9]+$' THEN r.rank_ordinal::int ELSE NULL END, 0),
                        NULLIF(CASE WHEN r.pos::text ~ '^[0-9]+$' THEN r.pos::int ELSE NULL END, 0)
                     ) ASC,
                     LOWER(COALESCE(NULLIF(TRIM(r.fleet_label), ''), NULLIF(TRIM(r.class_canonical), ''), NULLIF(TRIM(r.class_original), ''), 'Open')) ASC,
                     LOWER(COALESCE(NULLIF(TRIM(r.helm_name), ''), NULLIF(TRIM(r.crew_name), ''), 'Unknown')) ASC
            LIMIT 40
            """,
            (regatta_ids,),
        )
        rows = cur.fetchall() or []
    finally:
        cur.close()
        return_db_connection(conn)
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str, str, str]] = set()
    for row in rows:
        data = dict(row)
        rid = _safe_text(data.get("regatta_id"))
        sailor_name = _safe_text(data.get("sailor_name")) or "Unknown"
        event_name = _safe_text(data.get("event_name")) or rid
        place_raw = data.get("place_raw")
        class_name = _safe_text(data.get("class_name"))
        fleet_name = _safe_text(data.get("fleet_name")) or class_name
        event_date = _safe_text(data.get("event_date"))
        boat_name = _safe_text(data.get("boat_name"))
        sail_number = _safe_text(data.get("sail_number"))
        key = (rid, _norm_text_key(sailor_name), str(place_raw), _norm_text_key(class_name), _norm_text_key(boat_name), _norm_sail_number(sail_number))
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "regatta_id": rid,
                "event_name": event_name,
                "start_date": _iso(data.get("start_date")),
                "end_date": _iso(data.get("end_date") or data.get("start_date")),
                "sailor_name": sailor_name,
                "place_raw": int(place_raw) if place_raw not in (None, "") else None,
                "class_name": class_name,
                "fleet_name": fleet_name,
                "event_date": event_date,
                "class_logo_path": _safe_text(data.get("class_logo_path")),
                "boat_name": boat_name,
                "sail_number": sail_number,
                "races_sailed": int(data.get("races_sailed") or 0),
                "as_at_time": _safe_text(data.get("as_at_time")),
                "url": f"/regatta/{rid}",
            }
        )
    return out


def _recent_activity_items(
    regattas: list[dict[str, Any]],
    results: list[dict[str, Any]],
    latest_results: list[dict[str, Any]],
) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    result_regatta_ids = {
        _safe_text(row.get("regatta_id"))
        for row in (results or [])
        if _safe_text(row.get("regatta_id"))
    }
    latest_by_regatta: dict[str, list[dict[str, Any]]] = {}
    for row in latest_results or []:
        rid = _safe_text(row.get("regatta_id"))
        if not rid:
            continue
        latest_by_regatta.setdefault(rid, []).append(row)

    seen_regatta_ids: set[str] = set()
    for rid, rows in latest_by_regatta.items():
        if rid in result_regatta_ids:
            continue
        first = rows[0]
        detail_href = _safe_url((first.get("proof_urls") or [""])[0])
        if not detail_href:
            continue
        date_label = _date_span(first.get("start_date"), first.get("end_date")) or _safe_text(first.get("event_date"))
        class_names = []
        for row in rows:
            class_name = _safe_text(row.get("class_name"))
            if class_name and class_name not in class_names:
                class_names.append(class_name)
        class_label = ", ".join(class_names[:3])
        if len(class_names) > 3:
            class_label += f" +{len(class_names) - 3} more"
        detail_bits = [f"Direct sponsor-linked results · {len(rows)} entries"]
        boat_names = []
        for row in rows:
            boat_name = _safe_text(row.get("boat_name"))
            if boat_name and boat_name not in boat_names:
                boat_names.append(boat_name)
        if boat_names:
            detail_bits.append("Boats: " + ", ".join(boat_names[:2]) + (f" +{len(boat_names) - 2} more" if len(boat_names) > 2 else ""))
        if class_label:
            detail_bits.append(f"Classes: {class_label}")
        races_sailed = max(int(row.get("races_sailed") or 0) for row in rows)
        if races_sailed > 0:
            detail_bits.append(f"{races_sailed} races")
        items.append(
            {
                "date": date_label,
                "title": _safe_text(first.get("event_name")),
                "detail": " · ".join(detail_bits),
                "detail_href": detail_href,
                "regatta_id": rid,
            }
        )
        seen_regatta_ids.add(rid)
    # Do not copy history events into activity — that duplicates the same year.
    dedup: list[dict[str, str]] = []
    seen = set()
    for item in items:
        key = (item.get("regatta_id", ""), item.get("date", ""), item.get("title", ""), item.get("detail", ""))
        if key in seen:
            continue
        seen.add(key)
        dedup.append(item)
    dedup.sort(key=lambda x: (_safe_text(x.get("date")), _safe_text(x.get("title"))), reverse=True)
    return dedup[:8]


def _count_list(value: Any) -> int:
    return len(_json_list(value))


def _hero_links(profile: dict[str, Any]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    website = _safe_url(profile.get("website_url"))
    email = _safe_text(profile.get("email"))
    phone = _safe_text(profile.get("phone"))
    location = _safe_url(profile.get("location_url"))
    social = _json_dict(profile.get("social_json"))

    if website:
        out.append({"href": website, "label": "Website", "kind": "link"})
    if email:
        out.append({"href": f"mailto:{email}", "label": email, "kind": "email"})
    if phone:
        tel = "tel:" + re.sub(r"[^\d+]+", "", phone)
        out.append({"href": tel, "label": phone, "kind": "phone"})
    if location:
        out.append({"href": location, "label": "Map", "kind": "map"})

    for key in ("facebook", "instagram", "youtube", "x", "twitter", "linkedin"):
        href = _safe_url(social.get(key))
        if href:
            label = key.title() if key != "x" else "X"
            out.append({"href": href, "label": label, "kind": "social"})

    dedup = []
    seen = set()
    for item in out:
        href = _safe_text(item.get("href"))
        if not href or href in seen:
            continue
        seen.add(href)
        dedup.append(item)
    return dedup


def _hero(profile: dict[str, Any], *, meta_line: str) -> str:
    title = _safe_text(profile.get("display_name")) or _safe_text(profile.get("short_name")) or "Sponsor"
    about = _safe_text(profile.get("about_text"))
    logo = _safe_text(profile.get("logo_path"))
    links = _hero_links(profile)

    link_html = ""
    if links:
        link_html = '<div class="sp-links">' + "".join(
            f'<a class="sp-link" href="{html_module.escape(item["href"])}" target="_blank" rel="noopener noreferrer">{html_module.escape(item["label"])}</a>'
            if item["href"].startswith(("http://", "https://"))
            else f'<a class="sp-link" href="{html_module.escape(item["href"])}">{html_module.escape(item["label"])}</a>'
            for item in links
        ) + "</div>"

    about_html = f'<p class="sp-hero-blurb">{html_module.escape(about)}</p>' if about else ""
    logo_html = ""
    if logo:
        src = html_module.escape(logo if logo.startswith("/") else "/" + logo.lstrip("/"))
        logo_html = f'<img class="sp-logo" src="{src}" alt="{html_module.escape(title)}" loading="lazy" decoding="async" onerror="this.style.display=\'none\'">'
    else:
        logo_html = '<span class="sp-logo sp-logo--empty" aria-hidden="true"></span>'
    return (
        '<header class="sp-hero">'
        '<div class="sp-hero-inner">'
        '<div class="sp-brand-row">'
        f"{logo_html}"
        '<div class="sp-brand-text">'
        '<span class="sp-kicker sp-kicker-light">Sponsor Profile</span>'
        f'<h1 class="sp-title">{html_module.escape(title)}</h1>'
        f'<p class="sp-meta">{html_module.escape(meta_line)}</p>'
        "</div>"
        "</div>"
        f"{about_html}"
        f"{link_html}"
        "</div>"
        "</header>"
    )


def _contact_section(profile: dict[str, Any]) -> str:
    contact_name = _safe_text(profile.get("contact_name"))
    contact_title = _safe_text(profile.get("contact_title"))
    address = _safe_text(profile.get("address"))
    city = _safe_text(profile.get("city"))
    province = _safe_text(profile.get("province"))
    country = _safe_text(profile.get("country"))
    phone = _safe_text(profile.get("phone"))
    email = _safe_text(profile.get("email"))
    website = _safe_url(profile.get("website_url"))
    if not any([contact_name, phone, email, address, city, province, country, website]):
        return ""
    location_bits = [x for x in [address, city, province, country] if x]
    primary = contact_name + (f" — {contact_title}" if contact_title else "") if contact_name else ""
    primary_html = (
        f'<div class="sp-kv"><div class="sp-k">Primary</div><div class="sp-v">{html_module.escape(primary)}</div></div>'
        if primary
        else ""
    )
    tel = "tel:" + re.sub(r"[^\d+]+", "", phone) if phone else ""
    phone_html = (
        f'<div class="sp-kv"><div class="sp-k">Phone</div><div class="sp-v"><a href="{html_module.escape(tel)}">{html_module.escape(phone)}</a></div></div>'
        if phone
        else ""
    )
    email_html = f'<div class="sp-kv"><div class="sp-k">Email</div><div class="sp-v"><a href="mailto:{html_module.escape(email)}">{html_module.escape(email)}</a></div></div>' if email else ""
    loc_html = f'<div class="sp-kv"><div class="sp-k">Location</div><div class="sp-v">{html_module.escape(", ".join(location_bits))}</div></div>' if location_bits else ""
    web_html = f'<div class="sp-kv"><div class="sp-k">Website</div><div class="sp-v"><a href="{html_module.escape(website)}" target="_blank" rel="noopener noreferrer">{html_module.escape(website)}</a></div></div>' if website else ""
    return _section(
        "Contact",
        '<div class="sp-kv-grid">' + primary_html + phone_html + email_html + loc_html + web_html + "</div>",
        section_id="contact",
    )


def _services_section(profile: dict[str, Any]) -> str:
    items = [str(x).strip() for x in _json_list(profile.get("services_json")) if str(x).strip()]
    if not items:
        return ""
    chips = "".join(f'<span class="sp-chip">{html_module.escape(item)}</span>' for item in items)
    return _section("Services", f'<div class="sp-chip-wrap">{chips}</div>', section_id="services")


def _team_section(profile: dict[str, Any]) -> str:
    members = [dict(x) for x in _json_list(profile.get("team_json")) if isinstance(x, dict)]
    if not members:
        return ""
    cards = []
    for member in members:
        name = _safe_text(member.get("name")) or "Team Member"
        title = _safe_text(member.get("title"))
        bio = _safe_text(member.get("bio"))
        email = _safe_text(member.get("email"))
        phone = _safe_text(member.get("phone"))
        contact_bits = []
        if email:
            contact_bits.append(f'<a href="mailto:{html_module.escape(email)}">{html_module.escape(email)}</a>')
        if phone:
            tel = "tel:" + re.sub(r"[^\d+]+", "", phone)
            contact_bits.append(f'<a href="{html_module.escape(tel)}">{html_module.escape(phone)}</a>')
        parts = [
            '<article class="sp-card">',
            f'<h3 class="sp-card-title">{html_module.escape(name)}</h3>',
            f'<p class="sp-card-sub">{html_module.escape(title)}</p>' if title else "",
            f'<p class="sp-card-body">{html_module.escape(bio)}</p>' if bio else "",
            f'<p class="sp-card-links">{" · ".join(contact_bits)}</p>' if contact_bits else "",
            "</article>",
        ]
        cards.append("".join([p for p in parts if p]))
    return _section("Team", f'<div class="sp-grid">{"".join(cards)}</div>', section_id="team")


def _source_links_section(profile: dict[str, Any]) -> str:
    items = [str(x).strip() for x in _json_list(profile.get("source_urls_json")) if str(x).strip()]
    if not items:
        return ""
    links = "".join(
        '<article class="sp-card">'
        f'<p class="sp-card-body"><a href="{html_module.escape(item)}" target="_blank" rel="noopener noreferrer">{html_module.escape(item)}</a></p>'
        "</article>"
        for item in items
    )
    return _section("Media & Sources", f'<div class="sp-grid">{links}</div>', section_id="media")


def _mentions_section(mentions: list[dict[str, Any]]) -> str:
    if not mentions:
        return ""
    cards = []
    for item in mentions:
        source_url = _safe_text(item.get("source_url"))
        title = _safe_text(item.get("title")) or source_url or "External mention"
        source_domain = _safe_text(item.get("source_domain"))
        updated_at = _safe_text(item.get("updated_at"))
        snippet = _safe_text(item.get("snippet_text"))
        resolved = [dict(x) for x in _json_list(item.get("resolved_sailors")) if isinstance(x, dict)]
        boats = [str(x).strip() for x in _json_list(item.get("matched_boats")) if str(x).strip()]
        classes = [str(x).strip() for x in _json_list(item.get("matched_classes")) if str(x).strip()]
        sail_nos = [str(x).strip() for x in _json_list(item.get("matched_sail_nos")) if str(x).strip()]
        sailor_bits = []
        for row in resolved:
            label = _safe_text(row.get("full_name")) or _safe_text(row.get("input_name"))
            href = _sailor_href(_safe_text(row.get("sa_sailing_id")))
            status = _safe_text(row.get("status"))
            if href:
                sailor_bits.append(f'<a href="{html_module.escape(href)}">{html_module.escape(label)}</a>' + (f" ({html_module.escape(status)})" if status else ""))
            elif label:
                sailor_bits.append(html_module.escape(label) + (f" ({html_module.escape(status)})" if status else ""))
        meta_bits = [html_module.escape(x) for x in [source_domain, updated_at] if x]
        chips = "".join(f'<span class="sp-chip">{html_module.escape(x)}</span>' for x in boats + classes + sail_nos)
        cards.append(
            '<article class="sp-card">'
            + (f'<p class="sp-card-sub">{" · ".join(meta_bits)}</p>' if meta_bits else "")
            + (f'<h3 class="sp-card-title"><a href="{html_module.escape(source_url)}" target="_blank" rel="noopener noreferrer">{html_module.escape(title)}</a></h3>' if source_url else f'<h3 class="sp-card-title">{html_module.escape(title)}</h3>')
            + (f'<p class="sp-card-body">{html_module.escape(snippet)}</p>' if snippet else "")
            + (f'<p class="sp-card-links">{" · ".join(sailor_bits)}</p>' if sailor_bits else "")
            + (f'<div class="sp-chip-wrap">{chips}</div>' if chips else "")
            + "</article>"
        )
    inner = (
        '<details class="sp-audit-toggle">'
        '<summary class="sp-audit-summary">Show live mentions audit</summary>'
        f'<div class="sp-audit-body"><div class="sp-grid">{"".join(cards)}</div></div>'
        '</details>'
    )
    return _section("Live mentions", inner, section_id="mentions")


def _admin_controls(profile: dict[str, Any], regattas: list[dict[str, Any]]) -> str:
    terms = ", ".join(_match_terms(profile)) or "none"
    explicit = ", ".join(_explicit_regatta_ids(profile)) or "none"
    scrape_status = _safe_text(profile.get("scrape_status")) or "fallback"
    return (
        _section(
            "Admin",
            "<div class=\"sp-kv-grid\">"
            f'<div class="sp-kv"><div class="sp-k">Slug</div><div class="sp-v">{html_module.escape(_safe_slug(profile.get("slug")))}</div></div>'
            f'<div class="sp-kv"><div class="sp-k">Match terms</div><div class="sp-v">{html_module.escape(terms)}</div></div>'
            f'<div class="sp-kv"><div class="sp-k">Explicit regatta IDs</div><div class="sp-v">{html_module.escape(explicit)}</div></div>'
            f'<div class="sp-kv"><div class="sp-k">Matched regattas</div><div class="sp-v">{len(regattas)}</div></div>'
            f'<div class="sp-kv"><div class="sp-k">Scrape status</div><div class="sp-v">{html_module.escape(scrape_status)}</div></div>'
            f'<div class="sp-kv"><div class="sp-k">Fallback file</div><div class="sp-v">{html_module.escape(str(DATA_PATH.name))}</div></div>'
            "</div>",
            section_id="admin",
        )
    )


def _section(title: str, inner_html: str, *, section_id: str) -> str:
    if not inner_html:
        return ""
    return (
        f'<section class="sp-section" id="{html_module.escape(section_id)}">'
        f'<div class="sp-section-head"><div><span class="sp-kicker">{html_module.escape(section_id.replace("-", " "))}</span><h2 class="sp-section-title">{html_module.escape(title)}</h2></div></div>'
        f"{inner_html}"
        "</section>"
    )


def _stat_help(label: str, value: int) -> str:
    low = label.lower()
    if low == "history events":
        return f"{value} verified regattas are linked to this sponsor profile for sponsorship history."
    if low == "direct events":
        return f"{value} regattas contain direct sponsor-linked boats or sailors."
    if low == "result pages":
        return f"{value} sponsorship-history regattas currently have published result pages in SailingSA."
    if low == "direct sailors":
        return f"{value} distinct sailors were found on directly linked sponsor boats or entries."
    if low == "direct boats":
        return f"{value} directly linked boats or sail numbers were found in verified results."
    if low == "classes":
        return f"{value} distinct classes or fleets were found across the direct sponsor-linked entries."
    if low == "services":
        return f"{value} sponsor service items are stored on this profile from verified source data."
    if low == "team":
        return f"{value} sponsor team/contact records are stored on this profile from verified source data."
    return f"{value} verified items are currently linked to this sponsor profile."


def _stats_strip(
    *,
    regattas: list[dict[str, Any]],
    results: list[dict[str, Any]],
    sailors: list[dict[str, Any]],
    boats: list[dict[str, Any]],
    classes: list[dict[str, Any]],
    direct_event_count: int,
    profile: dict[str, Any],
) -> str:
    items = [
        ("History events", len(regattas)),
        ("Direct events", direct_event_count),
        ("Result pages", len(results)),
        ("Direct sailors", len(sailors)),
        ("Direct boats", len(boats)),
        ("Classes", len(classes)),
    ]
    if _count_list(profile.get("services_json")):
        items.append(("Services", _count_list(profile.get("services_json"))))
    if _count_list(profile.get("team_json")):
        items.append(("Team", _count_list(profile.get("team_json"))))
    html = "".join(
        '<button type="button" class="sp-stat" aria-expanded="false">'
        f'<div class="sp-stat-k">{html_module.escape(k)}</div>'
        f'<div class="sp-stat-v">{html_module.escape(str(v))}</div>'
        '<span class="sp-stat-info" aria-hidden="true">?</span>'
        f'<span class="sp-stat-pop" role="tooltip">{html_module.escape(_stat_help(k, v))}</span>'
        "</button>"
        for k, v in items
    )
    return f'<section class="sp-stats" aria-label="Sponsor statistics">{html}</section>'


def _event_card(row: dict[str, Any], *, badge: str = "") -> str:
    name = _safe_text(row.get("event_name")) or "Untitled"
    rid = _safe_text(row.get("regatta_id"))
    start = _safe_text(row.get("start_date")) or "—"
    end = _safe_text(row.get("end_date") or row.get("start_date")) or "—"
    host = _safe_text(row.get("host_label"))
    logo = _safe_text(row.get("event_logo_path") or row.get("fallback_logo_path"))
    badge_class = f" sp-badge-{_safe_text(badge).lower().replace(' ', '-')}" if badge else ""
    badge_html = f'<span class="sp-badge{html_module.escape(badge_class)}">{html_module.escape(badge)}</span>' if badge else ""
    meta_bits = []
    if badge_html:
        meta_bits.append(badge_html)
    if host:
        meta_bits.append(f'<span>{html_module.escape(host)}</span>')
    if f"{start} → {end}" != "— → —":
        meta_bits.append(f'<span>{html_module.escape(f"{start} → {end}")}</span>')
    meta_html = '<div class="sp-card-meta">' + "".join(meta_bits) + "</div>" if meta_bits else ""
    href = _safe_text(row.get("url")) or (f"/regatta/{rid}" if rid and not rid.startswith("event-") else "")
    logo_html = ""
    if logo:
        logo_html = f'<img class="sp-event-logo" src="{html_module.escape(logo)}" alt="" loading="lazy" decoding="async" onerror="this.style.display=\'none\'">'
    parts = [
        f'<a class="sp-card sp-card-link" href="{html_module.escape(href)}">',
        f'<div class="sp-event-row">{logo_html}<div class="sp-event-copy"><h3 class="sp-card-title">{html_module.escape(name)}</h3>',
        meta_html,
        "</div></div>",
        "</a>",
    ]
    return "".join([p for p in parts if p])


def _activity_section(items: list[dict[str, str]]) -> str:
    if not items:
        return ""
    cards = []
    for item in items:
        date_label = _safe_text(item.get("date"))
        title = _safe_text(item.get("title"))
        detail = _safe_text(item.get("detail"))
        detail_href = _safe_url(item.get("detail_href"))
        parts = [
            '<article class="sp-card">',
            f'<p class="sp-card-date">{html_module.escape(date_label)}</p>' if date_label else "",
            f'<h3 class="sp-card-title">{html_module.escape(title)}</h3>',
            (
                f'<p class="sp-card-sub"><a class="sp-proof-link" href="{html_module.escape(detail_href)}" target="_blank" rel="noopener noreferrer">{html_module.escape(detail)}</a></p>'
                if detail and detail_href else
                (f'<p class="sp-card-sub">{html_module.escape(detail)}</p>' if detail else "")
            ),
            "</article>",
        ]
        cards.append("".join([p for p in parts if p]))
    return _section("Recent activity", f'<div class="sp-grid">{ "".join(cards) }</div>', section_id="overview")


def _role_badge(row: dict[str, Any], *, fallback: str = "") -> str:
    role = _safe_text(row.get("sponsor_role")).lower()
    if role == "tier2":
        return "2nd tier"
    if role == "headline":
        return "Headline"
    return fallback


def _upcoming_section(regattas: list[dict[str, Any]], *, with_results: set[str]) -> str:
    if not regattas:
        return ""
    upcoming, results, other = _split_regattas(regattas, with_results)
    if not upcoming:
        return ""
    upcoming_cards = "".join(
        _event_card(row, badge=_role_badge(row, fallback="Upcoming"))
        for row in _dedupe_edition_rows(upcoming)[:12]
    )
    return _section("Upcoming", f'<div class="sp-grid">{upcoming_cards}</div>', section_id="upcoming")


def _history_cards(regattas: list[dict[str, Any]], *, with_results: set[str], limit: int = 12) -> str:
    upcoming, results, other = _split_regattas(regattas, with_results)
    past_rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in _dedupe_edition_rows(list(results) + list(other)):
        key = _edition_dedupe_key(row)
        if key in seen:
            continue
        seen.add(key)
        past_rows.append(row)
    if not past_rows:
        return ""
    past_cards = []
    for row in past_rows[:limit]:
        past_cards.append(_event_card(row, badge=_role_badge(row, fallback="Past")))
    return f'<div class="sp-grid">{"".join(past_cards)}</div>'


def _history_section(regattas: list[dict[str, Any]], *, with_results: set[str]) -> str:
    headline = [row for row in regattas if _safe_text(row.get("sponsor_role")) != "tier2"]
    tier2 = [row for row in regattas if _safe_text(row.get("sponsor_role")) == "tier2"]
    parts = []
    h_cards = _history_cards(headline, with_results=with_results)
    if h_cards:
        parts.append(_section("Headline events", h_cards, section_id="history"))
    t_cards = _history_cards(tier2, with_results=with_results)
    if t_cards:
        parts.append(
            _section(
                "2nd-tier events",
                '<p class="sp-section-blurb">Sponsored that year only. Name is not in the title. Not copied from other years.</p>' + t_cards,
                section_id="tier2-history",
            )
        )
    return "".join(parts)


def _sailors_section(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    cutoff = _subtract_years(date.today(), 3)
    active_rows: list[dict[str, Any]] = []
    inactive_rows: list[dict[str, Any]] = []
    for row in rows:
        last_active = _date_from_iso(row.get("last_active_date"))
        if last_active and last_active >= cutoff:
            active_rows.append(row)
        else:
            inactive_rows.append(row)

    def _pill_html(row: dict[str, Any]) -> str:
        name = _safe_text(row.get("name")) or "Unknown"
        sid = _safe_text(row.get("sas_id"))
        href = _sailor_href(sid)
        proof_href = _safe_url(row.get("proof_url"))
        ranking_classes = [dict(x) for x in _json_list(row.get("ranking_classes")) if isinstance(x, dict)]
        ranking_rank = row.get("ranking_rank")
        regatta_count = int(row.get("profile_regatta_count") or row.get("regatta_count") or 0)
        races_total = int(row.get("profile_races_total") or row.get("races_total") or 0)
        first_count = int(row.get("first_count") or 0)
        second_count = int(row.get("second_count") or 0)
        third_count = int(row.get("third_count") or 0)
        meta_bits = []
        if regatta_count > 0:
            meta_bits.append(f"{regatta_count} regatta" + ("" if regatta_count == 1 else "s"))
        if races_total > 0:
            meta_bits.append(f"{races_total} race" + ("" if races_total == 1 else "s"))
        meta_html = ' <span class="sp-sailor-sep">•</span> '.join(html_module.escape(bit) for bit in meta_bits)
        podium_html = (
            f'<span>🥇 {first_count}</span>'
            f'<span class="sp-sailor-sep">•</span>'
            f'<span>🥈 {second_count}</span>'
            f'<span class="sp-sailor-sep">•</span>'
            f'<span>🥉 {third_count}</span>'
        )
        name_html = html_module.escape(name)
        if href:
            name_html = f'<a class="sp-sailor-pill-name sp-sailor-name-link" href="{html_module.escape(href)}">{name_html}</a>'
        rank_html = ""
        try:
            rank_num = int(ranking_rank or 0)
        except (TypeError, ValueError):
            rank_num = 0
        if rank_num > 0:
            rank_html = f'<span class="sp-sailor-rank">{html_module.escape(str(rank_num))}</span>'
        classes_html = ""
        if ranking_classes:
            class_bits = []
            for class_row in ranking_classes:
                class_name = _safe_text(class_row.get("class_name"))
                if not class_name:
                    continue
                class_href = _class_href(class_name)
                class_text = html_module.escape(class_name)
                if class_href:
                    class_text = f'<a class="sp-sailor-name-link" href="{html_module.escape(class_href)}">{class_text}</a>'
                class_bits.append(class_text)
            if class_bits:
                classes_joined = ' <span class="sp-sailor-sep">•</span> '.join(class_bits)
                classes_html = f'<span class="sp-sailor-proof-link">Class: {classes_joined}</span>'
        body = (
            f'<span class="sp-sailor-pill-top"><span class="sp-sailor-pill-name">{name_html}</span>{rank_html}</span>'
            + (f'<span class="sp-sailor-pill-meta">{meta_html}</span>' if meta_html else "")
            + f'<span class="sp-sailor-pill-podium">{podium_html}</span>'
            + classes_html
        )
        return f'<span class="sp-sailor-pill">{body}</span>'

    blocks = []
    if active_rows:
        blocks.append(
            f'<div class="sp-subgroup"><div class="sp-subgroup-title">Active (last 3 years) · {len(active_rows)}</div><div class="sp-divider" aria-hidden="true"></div><div class="sp-chip-wrap sp-sailor-grid">{"".join(_pill_html(row) for row in active_rows[:40])}</div></div>'
        )
    if inactive_rows:
        blocks.append(
            f'<div class="sp-subgroup"><div class="sp-subgroup-title">Less active last sailed 3 or more years ago · {len(inactive_rows)}</div><div class="sp-divider" aria-hidden="true"></div><div class="sp-chip-wrap sp-sailor-grid">{"".join(_pill_html(row) for row in inactive_rows[:40])}</div></div>'
        )
    return _section("Direct sailors", "".join(blocks), section_id="sailors")


def _classes_section(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    cards = []
    for row in rows[:18]:
        label = _safe_text(row.get("class_name")) or "Unknown"
        href = _class_href(row.get("class_name"))
        logo = _safe_text(row.get("logo_path"))
        mention_count = int(row.get("mention_count") or 0)
        boat_proof_count = int(row.get("boat_proof_count") or 0)
        sailor_count = int(row.get("sailor_count") or 0)
        if mention_count or boat_proof_count or sailor_count:
            proof_total = mention_count + boat_proof_count
            proof_label = "proofs"
            if mention_count and not boat_proof_count:
                proof_label = "mentions"
            elif boat_proof_count and not mention_count:
                proof_label = "boat proofs"
            meta = f"{sailor_count} sailors · {proof_total} {proof_label}"
        else:
            meta = f'{int(row.get("regatta_count") or 0)} events · {int(row.get("result_count") or 0)} results'
        logo_html = ""
        if logo:
            logo_html = f'<img class="sp-class-logo" src="{html_module.escape(logo)}" alt="" loading="lazy" decoding="async" onerror="this.style.display=\'none\'">'
        if href:
            cards.append(
                f'<a class="sp-card sp-card-link" href="{html_module.escape(href)}">'
                f'<div class="sp-class-row">{logo_html}<div class="sp-class-text"><h3 class="sp-card-title">{html_module.escape(label)}</h3><p class="sp-card-sub">{html_module.escape(meta)}</p></div></div>'
                "</a>"
            )
        else:
            cards.append(
                '<div class="sp-card">'
                f'<div class="sp-class-row">{logo_html}<div class="sp-class-text"><h3 class="sp-card-title">{html_module.escape(label)}</h3><p class="sp-card-sub">{html_module.escape(meta)}</p></div></div>'
                "</div>"
            )
    return _section("Sponsor-proved classes", f'<div class="sp-grid">{ "".join(cards) }</div>', section_id="classes")


def _boats_section(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    name_counts: dict[str, int] = {}
    for row in rows:
        key = _norm_text_key(row.get("boat_name"))
        if not key:
            continue
        name_counts[key] = name_counts.get(key, 0) + 1
    cards = []
    for row in rows[:24]:
        boat_name = _safe_text(row.get("boat_name")) or "Unnamed boat"
        sail_number = _safe_text(row.get("sail_number"))
        class_name = _safe_text(row.get("class_name"))
        class_href = _class_href(row.get("class_name"))
        boat_href = _boat_href(class_name, sail_number, boat_name)
        event_count = int(row.get("event_count") or 0)
        latest_event_name = _safe_text(row.get("latest_event_name"))
        latest_regatta_href = _regatta_href(row.get("latest_regatta_id"))
        sailors = [dict(x) for x in _json_list(row.get("sailors")) if isinstance(x, dict)]
        duplicate_name = name_counts.get(_norm_text_key(boat_name), 0) > 1
        title = boat_name
        if duplicate_name and sail_number:
            title = f"{boat_name} · {sail_number}"
        elif duplicate_name and class_name:
            title = f"{boat_name} · {class_name}"
        title_html = html_module.escape(title)
        if boat_href:
            title_html = f'<a class="sp-sailor-name-link" href="{html_module.escape(boat_href)}">{title_html}</a>'
        sub_bits = []
        if sail_number and title == boat_name:
            sub_bits.append(html_module.escape(sail_number))
        if class_name:
            class_html = html_module.escape(class_name)
            if class_href:
                class_html = f'<a class="sp-sailor-name-link" href="{html_module.escape(class_href)}">{class_html}</a>'
            sub_bits.append(class_html)
        if event_count:
            sub_bits.append(html_module.escape(f"{event_count} events"))
        body_bits = []
        if latest_event_name:
            latest_event_html = html_module.escape(latest_event_name)
            if latest_regatta_href:
                latest_event_html = f'<a class="sp-sailor-name-link" href="{html_module.escape(latest_regatta_href)}">{latest_event_html}</a>'
            body_bits.append(f'Latest event: {latest_event_html}')
        if sailors:
            crew_parts = []
            for sailor in sailors[:3]:
                sailor_name = _safe_text(sailor.get("name"))
                if not sailor_name:
                    continue
                sailor_href = _sailor_href(_safe_text(sailor.get("sas_id")))
                sailor_html = html_module.escape(sailor_name)
                if sailor_href:
                    sailor_html = f'<a class="sp-sailor-name-link" href="{html_module.escape(sailor_href)}">{sailor_html}</a>'
                crew_parts.append(sailor_html)
            crew_label = ", ".join(crew_parts)
            if len(sailors) > 3:
                crew_label += f' +{len(sailors) - 3} more'
            body_bits.append(f'Sailors: {crew_label}')
        cards.append(
            '<article class="sp-card">'
            f'<h3 class="sp-card-title">{title_html}</h3>'
            + (f'<p class="sp-card-sub">{" · ".join(sub_bits)}</p>' if sub_bits else "")
            + (f'<p class="sp-card-body">{" · ".join(body_bits)}</p>' if body_bits else "")
            + "</article>"
        )
    return _section("Direct boats", f'<div class="sp-grid">{ "".join(cards) }</div>', section_id="boats")


def _results_section(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    first = rows[0]
    event_name = _safe_text(first.get("event_name"))
    event_range = _date_span(first.get("start_date"), first.get("end_date")) or _safe_text(first.get("event_date"))
    races_sailed = max(int(row.get("races_sailed") or 0) for row in rows)
    as_at = _fmt_as_at(first.get("as_at_time"))
    href = _safe_text(first.get("url"))
    logo = _safe_text(first.get("event_logo_path") or first.get("class_logo_path"))
    proof_urls = [_safe_url(x) for x in _json_list(first.get("proof_urls")) if _safe_url(x)]
    proof_href = proof_urls[0] if proof_urls else ""
    if not proof_href:
        return ""
    proof_label = urlparse(proof_href).netloc.replace("www.", "") if proof_href else ""
    meta_bits = []
    if event_range:
        meta_bits.append(event_range)
    if races_sailed > 0:
        meta_bits.append(f"{races_sailed} races")
    if as_at:
        meta_bits.append(f"Results at {as_at}")
    row_html = []
    for row in rows[:16]:
        place_raw = row.get("place_raw")
        if place_raw in (None, ""):
            continue
        people = [dict(x) for x in _json_list(row.get("people")) if isinstance(x, dict)]
        people_label = ", ".join(_safe_text(person.get("name")) for person in people if _safe_text(person.get("name")))
        sailor_name = people_label or _safe_text(row.get("sailor_name")) or "Unknown"
        boat_name = _safe_text(row.get("boat_name")) or "—"
        sail_number = _safe_text(row.get("sail_number")) or "—"
        class_name = _safe_text(row.get("class_name"))
        row_html.append(
            '<div class="sp-result-table-row">'
            f'<div class="sp-result-table-rank">{html_module.escape(str(place_raw))}</div>'
            f'<div class="sp-result-table-sailor">{html_module.escape(sailor_name)}</div>'
            f'<div class="sp-result-table-boat">{html_module.escape(boat_name)}</div>'
            f'<div class="sp-result-table-sailno">{html_module.escape(sail_number)}</div>'
            f'<div class="sp-result-table-fleet">{html_module.escape(class_name)}</div>'
            '</div>'
        )
    if not row_html:
        return ""
    title_html = html_module.escape(event_name or "Latest event")
    if href:
        title_html = f'<a class="sp-title-link" href="{html_module.escape(href)}">{title_html}</a>'
    head = (
        '<div class="sp-result-head">'
        + (
            f'<img class="sp-event-logo" src="{html_module.escape(logo)}" alt="" loading="lazy" decoding="async" onerror="this.style.display=\'none\'">'
            if logo else ""
        )
        + '<div class="sp-event-copy">'
        + f'<h3 class="sp-card-title">{title_html}</h3>'
        + (f'<p class="sp-card-date">{html_module.escape(event_range)}</p>' if event_range else "")
        + (f'<p class="sp-card-sub">{html_module.escape(" · ".join(meta_bits[1:]))}</p>' if len(meta_bits) > 1 else "")
        + (
            f'<p class="sp-card-sub"><a class="sp-proof-link" href="{html_module.escape(proof_href)}" target="_blank" rel="noopener noreferrer">Proof: {html_module.escape(proof_label)}</a></p>'
            if proof_href else ""
        )
        + "</div></div>"
    )
    table = (
        '<div class="sp-result-table">'
        '<div class="sp-result-table-row sp-result-table-head">'
        '<div>Rank</div><div>Sailors</div><div>Boat</div><div>Sail No</div><div>Class</div>'
        '</div>'
        + "".join(row_html)
        + '</div>'
    )
    body = head + table
    card_html = f'<article class="sp-card">{body}</article>'
    return _section("Latest direct results", card_html, section_id="results")


def _page_css() -> str:
    return """
:root{
  --sp-navy:#001f3f;
  --sp-ink:#1a2750;
  --sp-muted:#5b6b86;
  --sp-line:#94a3b8;
  --sp-soft:#e9eefb;
  --sp-bg:#f7f8fb;
  --sp-white:#ffffff;
  --sp-accent:#c45c26;
  --sp-touch:44px;
}
*,
*::before,
*::after{box-sizing:border-box;}
html{-webkit-text-size-adjust:100%;text-size-adjust:100%;}
body.sp-body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;background:var(--sp-bg);color:var(--sp-ink);line-height:1.35;overflow-x:hidden;}
body.sp-body a{color:var(--sp-navy);}
body.sp-body a:hover{color:var(--sp-accent);}
.sp-wrap{max-width:920px;margin:0 auto;padding:14px 12px 52px;min-width:0;}
.sp-back{display:inline-flex;align-items:center;gap:8px;text-decoration:none;font-weight:700;color:var(--sp-navy);min-height:var(--sp-touch);padding:8px 2px;}
.sp-logo{width:var(--sp-logo-box,72px);height:var(--sp-logo-box,72px);object-fit:contain;background:rgba(255,255,255,.92);border-radius:14px;padding:8px;flex:0 0 auto;box-sizing:border-box;}
.sp-logo--empty{display:inline-block;}
.sp-partner-box{display:inline-flex;align-items:center;justify-content:center;width:var(--sp-logo-box,72px);height:var(--sp-logo-box,72px);flex:0 0 auto;box-sizing:border-box;padding:0;overflow:hidden;border-radius:14px;background:rgba(255,255,255,.92);}
.sp-partner-badge{display:block;width:100%;height:100%;object-fit:cover;object-position:center;transform:scale(1.12);}
.sp-partner-badge--1,.sp-partner-badge--2,.sp-partner-badge--3{transform:scale(1.12);}
.sp-hero{--sp-logo-box:88px;border:1px solid var(--sp-line);background:linear-gradient(135deg,#0a2b55 0%, #0a2b55 45%, #173f74 100%);color:#fff;border-radius:16px;overflow:hidden;position:relative;}
.sp-hero::before{content:"";position:absolute;inset:0;background:radial-gradient(circle at 15% 20%, rgba(255,255,255,.18), rgba(255,255,255,0) 55%);pointer-events:none;border-radius:inherit;}
.sp-hero-inner{position:relative;padding:16px 14px 14px;border-radius:inherit;}
.sp-brand-row{display:flex;gap:12px;align-items:center;}
.sp-brand-text{min-width:0;flex:1 1 auto;}
@media (min-width:768px){
  .sp-hero{--sp-logo-box:104px;}
}
@media (min-width:1024px){
  .sp-hero{--sp-logo-box:116px;}
}
.sp-kicker{display:block;font-size:0.7rem;line-height:1;text-transform:uppercase;letter-spacing:.12em;font-weight:900;color:var(--sp-accent);margin:0 0 6px;}
.sp-kicker-light{color:rgba(255,255,255,.78);margin-bottom:8px;}
.sp-title{margin:0;font-size:1.45rem;line-height:1.2;font-weight:800;}
.sp-meta{margin:4px 0 0;color:rgba(255,255,255,.85);font-weight:650;font-size:0.92rem;}
.sp-hero-blurb{margin:12px 0 0;color:rgba(255,255,255,.9);font-size:0.95rem;line-height:1.45;}
.sp-links{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px;}
.sp-link{display:inline-flex;align-items:center;justify-content:center;min-height:var(--sp-touch);padding:0 12px;border-radius:999px;border:1px solid rgba(255,255,255,.28);background:rgba(255,255,255,.10);color:#fff !important;text-decoration:none;font-weight:700;font-size:0.9rem;max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.sp-link:hover,.sp-link:focus-visible{background:rgba(255,255,255,.18);border-color:rgba(255,255,255,.5);text-decoration:underline;}
.sp-stats{display:flex;gap:8px;overflow-x:auto;padding:12px 2px 18px;margin:12px 0 8px;-webkit-overflow-scrolling:touch;position:relative;z-index:24;transition:padding-bottom .15s ease;}
.sp-stats:has(.sp-stat:hover),.sp-stats:has(.sp-stat:focus-visible),.sp-stats:has(.sp-stat.is-open){padding-bottom:88px;}
.sp-stat{position:relative;flex:0 0 auto;min-width:138px;border:1px solid var(--sp-line);border-radius:14px;background:var(--sp-white);padding:10px 34px 10px 12px;text-align:left;appearance:none;-webkit-appearance:none;cursor:pointer;}
.sp-stat:hover,.sp-stat:focus-visible,.sp-stat.is-open{border-color:var(--sp-navy);background:#fbfcff;}
.sp-stat-k{font-size:0.72rem;text-transform:uppercase;letter-spacing:.04em;color:var(--sp-muted);font-weight:800;margin-bottom:4px;}
.sp-stat-v{font-size:1.15rem;font-weight:900;color:var(--sp-navy);}
.sp-stat-info{position:absolute;top:10px;right:10px;display:grid;place-items:center;width:18px;height:18px;border-radius:999px;background:var(--sp-soft);border:1px solid rgba(0,31,63,.18);color:var(--sp-navy);font-size:0.72rem;font-weight:900;line-height:1;}
.sp-stat-pop{position:absolute;left:8px;right:8px;top:calc(100% + 8px);z-index:30;padding:9px 10px;border-radius:12px;background:var(--sp-navy);color:#fff;font-size:0.82rem;line-height:1.35;font-weight:650;box-shadow:0 10px 24px rgba(2,6,23,.22);opacity:0;pointer-events:none;transform:translateY(-4px);transition:opacity .15s ease, transform .15s ease;}
.sp-stat-pop::before{content:"";position:absolute;top:-6px;right:18px;width:12px;height:12px;background:var(--sp-navy);transform:rotate(45deg);}
.sp-stat:hover .sp-stat-pop,.sp-stat:focus-visible .sp-stat-pop,.sp-stat.is-open .sp-stat-pop{opacity:1;pointer-events:auto;transform:translateY(0);}
.sp-section{margin:14px 0 0;}
.sp-section-head{display:flex;align-items:center;justify-content:space-between;gap:10px;margin:0 0 10px;}
.sp-section-title{margin:0;font-size:1.15rem;color:var(--sp-navy);}
.sp-grid{display:grid;grid-template-columns:1fr;gap:10px;}
.sp-audit-toggle{display:block;border:1px solid var(--sp-line);border-radius:14px;background:var(--sp-white);overflow:hidden;}
.sp-audit-summary{cursor:pointer;list-style:none;padding:12px 14px;font-weight:850;color:var(--sp-navy);outline:none;}
.sp-audit-summary::-webkit-details-marker{display:none;}
.sp-audit-summary::after{content:'+';float:right;color:var(--sp-accent);font-size:1.05rem;}
.sp-audit-toggle[open] .sp-audit-summary::after{content:'-';}
.sp-audit-body{padding:0 10px 10px;}
.sp-card{display:block;background:var(--sp-white);border:1px solid var(--sp-line);border-radius:14px;padding:10px;text-decoration:none;color:inherit;min-height:var(--sp-touch);min-width:0;max-width:100%;}
.sp-card:hover,.sp-card:focus-visible{border-color:var(--sp-navy);background:#fbfcff;}
.sp-card-row{display:flex;align-items:flex-start;gap:8px;}
.sp-card-title{margin:0;font-size:0.98rem;font-weight:850;color:var(--sp-navy);line-height:1.18;}
.sp-card-sub{margin:6px 0 0;color:var(--sp-muted);font-weight:650;font-size:0.9rem;}
.sp-card-date{margin:0 0 6px;color:var(--sp-muted);font-weight:800;font-size:0.75rem;letter-spacing:.03em;text-transform:uppercase;}
.sp-card-body{margin:8px 0 0;color:var(--sp-ink);font-size:0.92rem;line-height:1.45;overflow-wrap:anywhere;word-break:break-word;min-width:0;}
.sp-card-body a{overflow-wrap:anywhere;word-break:break-word;}
.sp-title-link{color:inherit;text-decoration:none;}
.sp-title-link:hover,.sp-title-link:focus-visible{text-decoration:underline;text-underline-offset:2px;}
.sp-proof-link{color:inherit;text-decoration:underline;text-underline-offset:2px;}
.sp-proof-link:hover,.sp-proof-link:focus-visible{color:var(--sp-navy);}
.sp-card-links{margin:10px 0 0;font-size:0.9rem;color:var(--sp-muted);font-weight:650;word-break:break-word;}
.sp-badge{display:inline-flex;align-items:center;justify-content:center;padding:2px 8px;border-radius:999px;background:var(--sp-soft);border:1px solid rgba(0,31,63,.25);color:var(--sp-navy);font-weight:850;font-size:0.72rem;letter-spacing:.02em;flex:0 0 auto;margin-top:2px;}
.sp-badge-upcoming{background:#fff3e6;border-color:#f59e0b;color:#b45309;}
.sp-badge-headline{background:#e8eef7;border-color:#001f3f;color:#001f3f;}
.sp-badge-2nd-tier{background:#f3e8ff;border-color:#7c3aed;color:#5b21b6;}
.sp-badge-result{background:#e8f7ea;border-color:#22c55e;color:#166534;}
.sp-badge-past{background:#eef2f7;border-color:#94a3b8;color:#475569;}
.sp-history-block + .sp-history-block{margin-top:14px;}
.sp-subsection-title{margin:0 0 8px;font-size:0.95rem;font-weight:850;color:var(--sp-navy);}
.sp-chip-wrap{display:flex;flex-wrap:wrap;gap:8px;}
.sp-chip{display:inline-flex;align-items:center;justify-content:center;min-height:34px;padding:0 12px;border-radius:999px;border:1px solid var(--sp-line);background:var(--sp-white);font-weight:750;font-size:0.9rem;color:var(--sp-navy);max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.sp-chip-link{text-decoration:none;}
.sp-chip:hover,.sp-chip:focus-visible{border-color:var(--sp-navy);background:var(--sp-soft);}
.sp-sailor-pill{display:flex;flex-direction:column;align-items:flex-start;gap:4px;min-width:0;max-width:100%;padding:10px 12px;border-radius:18px;border:1px solid var(--sp-line);background:var(--sp-white);color:var(--sp-navy);}
.sp-sailor-pill:hover,.sp-sailor-pill:focus-visible{border-color:var(--sp-navy);background:var(--sp-soft);}
.sp-sailor-pill-top{display:flex;align-items:baseline;justify-content:space-between;gap:10px;width:100%;min-width:0;}
.sp-sailor-pill-name{font-size:0.95rem;font-weight:850;line-height:1.1;}
.sp-sailor-rank{flex:0 0 auto;font-size:0.85rem;font-weight:900;color:var(--sp-muted);font-variant-numeric:tabular-nums;}
.sp-sailor-name-link{color:inherit;text-decoration:underline;text-underline-offset:2px;}
.sp-sailor-name-link:hover,.sp-sailor-name-link:focus-visible{color:var(--sp-navy);}
.sp-sailor-pill-meta,.sp-sailor-pill-podium{display:flex;flex-wrap:wrap;align-items:center;gap:4px;font-size:0.77rem;line-height:1.15;font-weight:700;color:var(--sp-muted);}
.sp-sailor-pill-podium{color:var(--sp-navy);}
.sp-sailor-proof-link{font-size:0.74rem;line-height:1.1;font-weight:700;color:var(--sp-muted);text-decoration:underline;text-underline-offset:2px;}
.sp-sailor-proof-link:hover,.sp-sailor-proof-link:focus-visible{color:var(--sp-navy);}
.sp-sailor-sep{color:var(--sp-muted);}
.sp-sailor-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;}
.sp-subgroup{display:grid;gap:8px;margin-bottom:12px;}
.sp-subgroup:last-child{margin-bottom:0;}
.sp-subgroup-title{font-size:0.82rem;font-weight:850;letter-spacing:.08em;text-transform:uppercase;color:var(--sp-accent);}
.sp-divider{height:1px;background:var(--sp-line);}
@media (min-width:720px){.sp-sailor-grid{grid-template-columns:repeat(3,minmax(0,1fr));}}
.sp-card-meta{display:flex;flex-wrap:wrap;align-items:center;gap:6px;margin-top:6px;color:var(--sp-muted);font-weight:700;font-size:0.84rem;line-height:1.25;}
.sp-card-meta span{display:inline-flex;align-items:center;}
.sp-event-row{display:grid;grid-template-columns:44px minmax(0,1fr);align-items:start;gap:8px;}
.sp-event-logo{width:44px;height:44px;border-radius:10px;border:1px solid rgba(148,163,184,.6);background:var(--sp-white);object-fit:contain;padding:4px;}
.sp-event-copy{min-width:0;}
.sp-sponsor-index-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;width:100%;max-width:var(--sp-index-grid-max,40rem);margin:0 auto;}
.sp-sponsor-index-card{--sp-logo-box:44px;position:relative;overflow:hidden;display:grid;grid-template-rows:var(--sp-logo-box) minmax(84px,1fr);align-items:stretch;gap:6px;width:100%;min-height:160px;padding:8px;box-sizing:border-box;border:1px solid var(--sp-line);border-radius:16px;background:var(--sp-white);text-decoration:none;color:inherit;}
.sp-sponsor-index-card:hover,.sp-sponsor-index-card:focus-visible{border-color:var(--sp-navy);background:#fbfcff;}
.sp-sponsor-index-top{display:flex;align-items:center;justify-content:center;width:100%;height:var(--sp-logo-box);min-height:var(--sp-logo-box);}
.sp-sponsor-index-name{display:flex;align-items:center;justify-content:center;margin:0;padding:0 2px 0 0;box-sizing:border-box;height:var(--sp-logo-box);text-align:center;font-size:0.8rem;font-weight:850;line-height:1.12;color:var(--sp-navy);overflow:hidden;}
.sp-sponsor-index-logo-wrap{display:flex;align-items:center;justify-content:center;width:100%;min-height:0;height:100%;}
.sp-sponsor-index-logo{display:block;width:auto;height:auto;max-width:100%;max-height:100%;object-fit:contain;object-position:center;}
.sp-sponsor-index-card .sp-partner-box{position:static;justify-self:end;width:var(--sp-logo-box);height:var(--sp-logo-box);padding:0;overflow:hidden;background:#fff;border:1px solid var(--sp-line);}
.sp-sponsor-index-card .sp-partner-badge{object-fit:cover;object-position:center;transform:scale(1.18);}
@media (min-width:700px){
  .sp-sponsor-index-grid{grid-template-columns:repeat(3,minmax(0,1fr));max-width:var(--sp-index-grid-max,52rem);gap:14px;}
  .sp-sponsor-index-card{--sp-logo-box:48px;grid-template-rows:var(--sp-logo-box) minmax(100px,1fr);min-height:184px;}
  .sp-sponsor-index-name{font-size:0.84rem;}
}
@media (min-width:1024px){
  .sp-sponsor-index-grid{max-width:var(--sp-index-grid-max,56rem);}
  .sp-sponsor-index-card{--sp-logo-box:52px;grid-template-rows:var(--sp-logo-box) minmax(108px,1fr);min-height:196px;}
}
.sp-section-blurb{margin:0 0 10px;color:var(--sp-muted);font-size:0.88rem;line-height:1.35;}
.sp-empty{margin:0;color:var(--sp-muted);font-size:0.9rem;}
.sp-result-row{display:grid;grid-template-columns:46px 44px minmax(0,1fr);align-items:start;gap:10px;}
.sp-result-rank{width:36px;height:36px;border-radius:10px;display:grid;place-items:center;background:var(--sp-navy);color:#fff;font-size:0.95rem;font-weight:900;}
.sp-result-logo{width:44px;height:44px;border-radius:12px;border:1px solid rgba(148,163,184,.6);background:var(--sp-white);object-fit:contain;padding:6px;}
.sp-result-copy{min-width:0;}
.sp-result-summary{margin-top:10px;display:grid;gap:6px;}
.sp-result-line{display:grid;grid-template-columns:24px minmax(0,1fr);gap:8px;align-items:start;}
.sp-result-pos{display:inline-grid;place-items:center;width:24px;height:24px;border-radius:999px;background:var(--sp-navy);color:#fff;font-size:0.8rem;font-weight:900;}
.sp-result-name{font-weight:750;color:var(--sp-ink);line-height:1.3;}
.sp-result-head{display:grid;grid-template-columns:52px minmax(0,1fr);gap:10px;align-items:center;margin-bottom:12px;}
.sp-result-table{display:grid;gap:8px;}
.sp-result-table-row{display:grid;grid-template-columns:42px minmax(0,1.3fr) minmax(0,1fr) 78px minmax(0,.9fr);gap:8px;align-items:start;border-top:1px solid rgba(148,163,184,.35);padding-top:8px;}
.sp-result-table-head{border-top:none;padding-top:0;font-size:0.72rem;text-transform:uppercase;letter-spacing:.04em;color:var(--sp-muted);font-weight:800;}
.sp-result-table-rank{display:inline-grid;place-items:center;width:32px;height:32px;border-radius:10px;background:var(--sp-navy);color:#fff;font-size:0.9rem;font-weight:900;}
.sp-result-table-sailor,.sp-result-table-boat,.sp-result-table-sailno,.sp-result-table-fleet{min-width:0;overflow-wrap:anywhere;word-break:break-word;line-height:1.3;}
.sp-result-table-sailor{font-weight:800;color:var(--sp-ink);}
.sp-result-table-boat,.sp-result-table-sailno,.sp-result-table-fleet{color:var(--sp-muted);font-weight:650;}
.sp-class-row{display:flex;gap:10px;align-items:center;}
.sp-class-logo{width:44px;height:44px;border-radius:12px;border:1px solid rgba(148,163,184,.6);background:var(--sp-white);object-fit:contain;padding:6px;flex:0 0 auto;}
.sp-class-text{min-width:0;}
.sp-kv-grid{display:grid;grid-template-columns:1fr;gap:10px;}
.sp-kv{border:1px solid rgba(148,163,184,.55);border-radius:14px;background:var(--sp-white);padding:10px 12px;}
.sp-k{font-size:0.72rem;text-transform:uppercase;letter-spacing:.04em;color:var(--sp-muted);font-weight:800;margin-bottom:4px;}
.sp-v{font-weight:750;color:var(--sp-ink);word-break:break-word;}
.sp-v a{text-decoration:underline;text-underline-offset:2px;font-weight:800;}
@media (min-width: 720px){
  .sp-wrap{padding:18px 18px 64px;}
  .sp-hero-inner{padding:22px 20px 18px;}
  .sp-grid{grid-template-columns:repeat(2,minmax(0,1fr));}
  .sp-kv-grid{grid-template-columns:repeat(2,minmax(0,1fr));}
}
@media (max-width: 520px){
  .sp-result-table-row{grid-template-columns:34px minmax(0,1fr);gap:6px;}
  .sp-result-table-head{display:none;}
  .sp-result-table-rank{width:28px;height:28px;font-size:0.8rem;}
  .sp-result-table-sailor{grid-column:2;}
  .sp-result-table-boat,.sp-result-table-sailno,.sp-result-table-fleet{grid-column:2;font-size:0.86rem;}
  .sp-stat-pop{left:0;right:auto;width:min(220px, calc(100vw - 40px));}
  .sp-sponsor-index-grid{gap:10px;}
  .sp-sponsor-index-card{min-height:152px;padding:8px;border-radius:14px;grid-template-rows:var(--sp-logo-box) minmax(78px,1fr);}
}
"""


def _render_404(slug: str, canonical_base_url: str) -> str:
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<meta name='theme-color' content='#001f3f'>"
        "<title>Sponsor Not Found | SailingSA</title>"
        f"<style>{_page_css()}</style></head><body class='sp-body'>"
        f"{site_header_nav()}"
        '<main class="sp-wrap">'
        '<a href="/" class="sp-back">Back to Home</a>'
        f'<div class="sp-hero"><div class="sp-hero-inner"><h1 class="sp-title">Sponsor Not Found</h1><p class="sp-meta">{html_module.escape("/sponsors/" + _safe_slug(slug))}</p></div></div>'
        '<section class="sp-section"><div class="sp-section-head"><h2 class="sp-section-title">Details</h2></div><div class="sp-card"><p class="sp-card-body">No sponsor profile exists for this slug yet.</p></div></section>'
        "</main>"
        f"{site_footer()}</body></html>"
    )


def _sponsor_index_items(
    *,
    get_db_connection: Callable[[], Any] | None = None,
    return_db_connection: Callable[[Any], None] | None = None,
    table_exists: Callable[[str], bool] | None = None,
) -> list[dict[str, str]]:
    """Index cards from catalog/JSON only (no per-sponsor DB). Fast + cacheable."""
    items: list[dict[str, str]] = []
    profiles = _load_profiles()
    for slug in sorted(profiles.keys(), key=lambda x: (_safe_text(profiles[x].get("display_name") or profiles[x].get("short_name") or x).lower(), x)):
        profile = profiles.get(slug) or {}
        title = _safe_text(profile.get("display_name")) or _safe_text(profile.get("short_name")) or slug.replace("-", " ").title()
        logo = _safe_text(profile.get("logo_path"))
        href = f"/sponsors/{_safe_slug(slug)}"
        tier = _safe_text(profile.get("tier")).lower()
        if tier not in {"headline", "tier2"}:
            tier = "headline"
        items.append(
            {
                "slug": _safe_slug(slug),
                "title": title,
                "logo_path": logo,
                "href": href,
                "tier": tier,
                "partner_tier": str(profile.get("partner_tier") or "").strip(),
            }
        )
    by_slug: dict[str, dict[str, str]] = {}
    for item in items:
        canon = _resolve_sponsor_slug(item.get("slug"))
        prev = by_slug.get(canon)
        if not prev:
            item["slug"] = canon
            item["href"] = f"/sponsors/{canon}"
            by_slug[canon] = item
            continue
        if item.get("tier") == "headline":
            prev["tier"] = "headline"
        if not prev.get("logo_path") and item.get("logo_path"):
            prev["logo_path"] = item["logo_path"]
        if not prev.get("title") and item.get("title"):
            prev["title"] = item["title"]
        if item.get("partner_tier") and not prev.get("partner_tier"):
            prev["partner_tier"] = item["partner_tier"]
    return sorted(by_slug.values(), key=lambda x: (_safe_text(x.get("title")).lower(), x.get("slug") or ""))


def _index_source_fingerprint() -> str:
    """Rebuild index only when catalog / profiles / badge art / this module change."""
    paths = [
        DATA_PATH,
        DEPLOY / "sponsor_catalog.py",
        DEPLOY / "sponsor_profiles.py",
        DEPLOY / "artwork" / "Partner-Badge" / "SailingSA-Partner-Tier-1-Gold.png",
        DEPLOY / "artwork" / "Partner-Badge" / "SailingSA-Partner-Tier-2-Silver.png",
        DEPLOY / "artwork" / "Partner-Badge" / "SailingSA-Partner-Tier-3-Bronze.png",
        Path("/var/www/sailingsa/api/sponsor_catalog.py"),
        Path("/var/www/sailingsa/api/sponsor_profiles.py"),
        Path("/var/www/sailingsa/api/sponsor_profiles.json"),
    ]
    api_art = Path("/var/www/sailingsa/api/artwork/Partner-Badge")
    if api_art.is_dir():
        paths.extend(sorted(api_art.glob("*.png")))
    bits = []
    for path in paths:
        try:
            st = path.stat()
            bits.append(f"{path}:{st.st_mtime_ns}:{st.st_size}")
        except OSError:
            continue
    return "|".join(bits) or "empty"


def _read_cached_index_html(fp: str) -> str:
    if _INDEX_HTML_CACHE.get("fp") == fp and _INDEX_HTML_CACHE.get("html"):
        return _INDEX_HTML_CACHE["html"]
    try:
        if _INDEX_CACHE_FP.is_file() and _INDEX_CACHE_HTML.is_file():
            if _INDEX_CACHE_FP.read_text(encoding="utf-8").strip() == fp:
                html = _INDEX_CACHE_HTML.read_text(encoding="utf-8")
                if html:
                    _INDEX_HTML_CACHE["fp"] = fp
                    _INDEX_HTML_CACHE["html"] = html
                    return html
    except OSError:
        pass
    return ""


def _write_cached_index_html(fp: str, html: str) -> None:
    _INDEX_HTML_CACHE["fp"] = fp
    _INDEX_HTML_CACHE["html"] = html
    try:
        _INDEX_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _INDEX_CACHE_HTML.write_text(html, encoding="utf-8")
        _INDEX_CACHE_FP.write_text(fp, encoding="utf-8")
    except OSError:
        pass


def _index_card_width_css(items: list[dict[str, str]]) -> str:
    """Equal cards; 2-col mobile / 3-col desktop. Width tracks longest label."""
    longest = 0
    for item in items:
        longest = max(longest, len(_safe_text(item.get("title"))))
    # Rem units keep equal boxes readable without crushing logos into the badge.
    grid_max = max(34, min(56, 18 + longest * 0.7))
    return f"--sp-index-grid-max:{grid_max:.0f}rem;"


def _partner_badge_box_html(partner_tier: Any = None, *, always: bool = True) -> str:
    """Partner stamps were a test — never render them."""
    return ""


def _partner_badge_html(partner_tier: Any) -> str:
    """Back-compat: always render the uniform partner box."""
    return _partner_badge_box_html(partner_tier, always=True)


def sponsors_index_html(
    *,
    get_db_connection: Callable[[], Any],
    return_db_connection: Callable[[Any], None],
    table_exists: Callable[[str], bool],
    canonical_base_url: str,
) -> tuple[int, str]:
    fp = _index_source_fingerprint()
    cached = _read_cached_index_html(fp)
    if cached:
        return 200, cached

    items = _sponsor_index_items()
    card_w = _index_card_width_css(items)

    def _cards_for(rows: list[dict[str, str]]) -> str:
        if not rows:
            return '<p class="sp-empty">None listed yet.</p>'
        cards = []
        for item in rows:
            logo = _safe_text(item.get("logo_path"))
            logo_html = ""
            if logo:
                logo_html = (
                    f'<img class="sp-sponsor-index-logo" src="{html_module.escape(logo)}" '
                    'alt="" loading="lazy" decoding="async">'
                )
            cards.append(
                '<a class="sp-sponsor-index-card" href="'
                + html_module.escape(_safe_text(item.get("href")))
                + '">'
                + '<div class="sp-sponsor-index-top">'
                + '<span class="sp-sponsor-index-name">'
                + html_module.escape(_safe_text(item.get("title")))
                + "</span>"
                + "</div>"
                + '<div class="sp-sponsor-index-logo-wrap">'
                + logo_html
                + "</div></a>"
            )
        return (
            f'<div class="sp-sponsor-index-grid" style="{html_module.escape(card_w)}">'
            + "".join(cards)
            + "</div>"
        )

    headline = [i for i in items if i.get("tier") != "tier2"]
    tier2 = [i for i in items if i.get("tier") == "tier2"]
    extra_nav = '<a href="/directory">Directory</a>'
    html = (
        "<!DOCTYPE html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<meta name='theme-color' content='#001f3f'>"
        "<title>Sponsors | SailingSA</title>"
        f"<link rel='canonical' href='{html_module.escape(canonical_base_url.rstrip('/') + '/sponsors')}'>"
        f"<link rel='stylesheet' href='/css/main.css?v=13'>"
        f"<style>{_page_css()}</style></head><body class='sp-body'>"
        f"{site_header_nav(extra_nav=extra_nav)}"
        '<main class="sp-wrap">'
        '<a href="/" class="sp-back">Back to Home</a>'
        '<section class="sp-hero"><div class="sp-hero-inner"><h1 class="sp-title">Sponsors</h1>'
        f'<p class="sp-meta">{len(headline)} headline · {len(tier2)} 2nd tier</p></div></section>'
        '<section class="sp-section" id="headline">'
        '<div class="sp-section-head"><h2 class="sp-section-title">Headline Sponsors</h2></div>'
        '<p class="sp-section-blurb">Name appears in that year\'s event title. Same yearly event can have different headline sponsors in other years.</p>'
        + _cards_for(headline)
        + "</section>"
        '<section class="sp-section" id="tier-2">'
        '<div class="sp-section-head"><h2 class="sp-section-title">2nd Tier Sponsors</h2></div>'
        '<p class="sp-section-blurb">Proof for that event that year, name not in the title. Not copied from other years.</p>'
        + _cards_for(tier2)
        + "</section></main>"
        + site_footer()
        + "</body></html>"
    )
    _write_cached_index_html(fp, html)
    return 200, html


def page_html(
    *,
    slug: str,
    get_db_connection: Callable[[], Any],
    return_db_connection: Callable[[Any], None],
    table_exists: Callable[[str], bool],
    canonical_base_url: str,
    is_super_admin: bool = False,
) -> tuple[int, str]:
    profile = _profile_for_page(
        slug,
        get_db_connection=get_db_connection,
        return_db_connection=return_db_connection,
        table_exists=table_exists,
    )
    if not profile:
        return 404, _render_404(slug, canonical_base_url)

    regattas = _fetch_linked_regattas(
        profile,
        get_db_connection=get_db_connection,
        return_db_connection=return_db_connection,
        table_exists=table_exists,
    )
    regattas.extend(
        _fetch_supporting_year_events(
            profile,
            regattas,
            get_db_connection=get_db_connection,
            return_db_connection=return_db_connection,
            table_exists=table_exists,
        )
    )
    regattas = _assign_sponsor_roles(profile, regattas)
    regattas = _dedupe_edition_rows(regattas)
    regatta_ids = [row["regatta_id"] for row in regattas]
    logo_map = _regatta_logo_map(
        regatta_ids,
        get_db_connection=get_db_connection,
        return_db_connection=return_db_connection,
        table_exists=table_exists,
    )
    with_results = _results_regatta_ids(
        regatta_ids,
        get_db_connection=get_db_connection,
        return_db_connection=return_db_connection,
        table_exists=table_exists,
    )
    mentions = _live_mentions(
        _safe_slug(profile.get("slug") or slug),
        get_db_connection=get_db_connection,
        return_db_connection=return_db_connection,
        table_exists=table_exists,
    )
    mentions = [item for item in mentions if _is_strict_proof_mention(item)]
    direct_targets = _direct_targets(profile, mentions)
    direct_rows = _direct_result_rows(
        direct_targets,
        get_db_connection=get_db_connection,
        return_db_connection=return_db_connection,
        table_exists=table_exists,
    )
    for row in direct_rows:
        row["proof_urls"] = _proof_urls_for_row(row, mentions)
    latest_results = _direct_latest_results(direct_rows)
    sailors = _direct_linked_sailors(
        direct_rows,
        mentions,
        get_db_connection=get_db_connection,
        return_db_connection=return_db_connection,
        table_exists=table_exists,
    )
    classes = _direct_linked_classes(mentions, direct_rows)
    boats = _direct_boats(direct_rows, profile)
    for row in regattas:
        rid = _safe_text(row.get("regatta_id"))
        event_logo = _event_logo_for_regatta(rid, row.get("event_name"))
        fallback_logo = _safe_text(logo_map.get(rid))
        row["event_logo_path"] = _sponsor_card_logo(event_logo, fallback_logo, profile)
        row["fallback_logo_path"] = _safe_text(profile.get("logo_path")) or fallback_logo
    for row in latest_results:
        rid = _safe_text(row.get("regatta_id"))
        event_logo = _event_logo_for_regatta(rid, row.get("event_name"))
        row["event_logo_path"] = _sponsor_card_logo(event_logo, "", profile)
    _, results, _ = _split_regattas(regattas, with_results)
    activity_items = _recent_activity_items(regattas, results, direct_rows)

    title = _safe_text(profile.get("display_name")) or _safe_text(profile.get("short_name")) or "Sponsor"
    meta_line = "Sponsor profile"
    direct_event_count = len({_safe_text(row.get("regatta_id")) for row in direct_rows if _safe_text(row.get("regatta_id"))})
    if regattas or direct_event_count:
        meta_bits = []
        if regattas:
            meta_bits.append(f"{len(regattas)} history events")
        if direct_event_count:
            meta_bits.append(f"{direct_event_count} direct events")
        if results:
            meta_bits.append(f"{len(results)} result pages")
        meta_line = "Sponsor profile" + (" · " + " · ".join(meta_bits) if meta_bits else "")

    upcoming_html = _upcoming_section(regattas, with_results=with_results)
    history_html = _history_section(regattas, with_results=with_results)

    sections_by_id: list[tuple[str, str, str]] = []
    sections_by_id.append(("history", "History", history_html))
    sections_by_id.append(("mentions", "Mentions", _mentions_section(mentions)))
    sections_by_id.append(("overview", "Overview", _activity_section(activity_items)))
    sections_by_id.append(("results", "Results", _results_section(latest_results)))
    sections_by_id.append(("sailors", "Sailors", _sailors_section(sailors)))
    sections_by_id.append(("boats", "Boats", _boats_section(boats)))
    sections_by_id.append(("classes", "Classes", _classes_section(classes)))
    sections_by_id.append(("services", "Services", _services_section(profile)))
    sections_by_id.append(("team", "Team", _team_section(profile)))
    sections_by_id.append(("contact", "Contact", _contact_section(profile)))
    sections_by_id.append(("media", "Media", _source_links_section(profile)))
    rendered_sections = [html for sid, _, html in sections_by_id if html and sid != "history"]
    extra_nav = '<a href="/directory">Directory</a>'
    html = (
        "<!DOCTYPE html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<meta name='theme-color' content='#001f3f'>"
        f"<title>{html_module.escape(title)} | SailingSA Sponsors</title>"
        f"<link rel='canonical' href='{html_module.escape(canonical_base_url.rstrip('/') + '/sponsors/' + _safe_slug(profile.get('slug')))}'>"
        f"<link rel='stylesheet' href='/css/main.css?v=13'>"
        f"<style>{_page_css()}</style></head><body class='sp-body'>"
        f"{site_header_nav(extra_nav=extra_nav)}"
        '<main class="sp-wrap">'
        '<a href="/" class="sp-back">Back to Home</a>'
        + _hero(profile, meta_line=meta_line)
        + upcoming_html
        + history_html
        + _stats_strip(regattas=regattas, results=results, sailors=sailors, boats=boats, classes=classes, direct_event_count=direct_event_count, profile=profile)
        + "".join(rendered_sections)
        + "</main>"
        + _page_script()
        + site_footer()
        + "</body></html>"
    )
    return 200, html


def _page_script() -> str:
    return """
<script>
(function(){
  var statCards = Array.prototype.slice.call(document.querySelectorAll('.sp-stat'));
  function closeStats(exceptEl){
    statCards.forEach(function(card){
      var open = exceptEl && card === exceptEl;
      card.classList.toggle('is-open', !!open);
      card.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  }
  statCards.forEach(function(card){
    card.addEventListener('click', function(ev){
      ev.preventDefault();
      var isOpen = card.classList.contains('is-open');
      closeStats(isOpen ? null : card);
    });
  });
  document.addEventListener('click', function(ev){
    var inside = ev.target && ev.target.closest ? ev.target.closest('.sp-stat') : null;
    if (!inside) closeStats(null);
  });
  document.addEventListener('keydown', function(ev){
    if (ev.key === 'Escape') closeStats(null);
  });
})();
</script>
"""
