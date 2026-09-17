"""
Full DB-driven sitemap builder. No request context. No FastAPI dependency.

Production invoke path (Google-facing files):
  PYTHONPATH=/var/www/sailingsa
  from utils.sitemap_builder import build_sitemap
  → /var/www/sailingsa/utils/sitemap_builder.py
  writes /var/www/sailingsa/sitemap.xml + family children
  (sailingsa/deploy/refresh-sitemap-cron.sh)

Writes sitemap.xml (index) + child urlsets: core, regattas, sailors, classes, clubs.
Each URL appears in exactly one child sitemap.

Lastmod: entity dates from Postgres, never a future date.
Floor is 2000-01-01 when no past date exists. Does not hardcode "today" as lastmod.
"""
from __future__ import annotations

import glob
import os
import re
import logging
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit
from typing import Any

import psycopg2.extras  # RealDictCursor for dict-like rows

LOG = logging.getLogger(__name__)

DEFAULT_STATIC_DIR = "/var/www/sailingsa/static"
SITEMAP_INDEX_FILENAME = "sitemap.xml"
BASE_URL_DEFAULT = "https://sailingsa.co.za"
# Protocol max URLs per urlset; larger sets are split into -partNNNNN.xml files.
SITEMAP_MAX_URLS_PER_FILE = int(os.environ.get("SITEMAP_MAX_URLS_PER_FILE", "50000"))

# Proven independently indexable hub pages already served by the app.
# Do not add /events-logos, /boat-names, /boat/, or /boat-name/.
CORE_PATHS = (
    "/",
    "/about",
    "/events",
    "/regattas",
    "/sailors",
    "/clubs",
    "/classes",
    "/yearly-events",
    "/stats",
)

CHILD_STEMS = (
    "sitemap-core",
    "sitemap-regattas",
    "sitemap-sailors",
    "sitemap-classes",
    "sitemap-clubs",
)

LASTMOD_FLOOR = "2000-01-01"


def _utc_today_iso() -> str:
    """Ceiling for lastmod only — never used as a fabricated entity lastmod."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _sas_personal_display_name(first_name: str = "", last_name: str = "", full_name: str = "") -> str:
    """Same rule as live api.py: First then Surname; flip legacy 'Last, First'."""
    f = (first_name or "").strip()
    l = (last_name or "").strip()
    if f and l:
        return f"{f} {l}"
    raw = (full_name or "").strip()
    if "," in raw:
        parts = [p.strip() for p in raw.split(",", 1)]
        if len(parts) == 2 and parts[0] and parts[1]:
            return f"{parts[1]} {parts[0]}"
    if f or l:
        return " ".join(x for x in (f, l) if x)
    return raw


def _slug_from_name(full_name: str) -> str:
    """Same rule as live api.py _slug_from_name (including Last, First flip)."""
    if not full_name or not isinstance(full_name, str):
        return ""
    s = full_name.strip()
    if "," in s:
        parts = [p.strip() for p in s.split(",", 1)]
        if len(parts) == 2 and parts[0] and parts[1]:
            s = f"{parts[1]} {parts[0]}"
    s = s.lower().replace("&", " and ")
    s = re.sub(r"[^\w\s\-]", "", s)
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def _sailor_canonical_slug(full_name: str, sas_id: str = "", has_duplicate: bool = False) -> str:
    """Same rule as live api.py: public sailor slug is name-only. Never append SAS id."""
    base = _slug_from_name(full_name)
    return base or "sailor"


def _class_canonical_slug(class_name: str) -> str:
    """Same rule as live api.py: keep dots (ILCA 4.7 → ilca-4.7)."""
    if not class_name or not isinstance(class_name, str):
        return ""
    s = class_name.strip().lower().replace(" ", "-")
    s = re.sub(r"[^a-z0-9.-]", "", s)
    return s.strip("-") or ""


def _class_public_path(class_name: str) -> str:
    """Same rule as live api.py _class_public_path: /class/{slug} only, never /class/{id}-{slug}."""
    s = _class_canonical_slug(class_name)
    if s and re.match(r"^\d+-", s):
        s = s.split("-", 1)[1]
    if not s:
        return ""
    return f"/class/{s}"


def _club_slug_from_name(name: str) -> str:
    """Same rule as api.py _club_slug_from_name (canonical club_code)."""
    if not name or not isinstance(name, str):
        return ""
    s = re.sub(r"[^\w\s\-]", "", name).strip().lower()
    return re.sub(r"\s+", "-", s).strip("-")


def _escape_loc(url: str) -> str:
    if not url:
        return ""
    return (
        url.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _date_iso(d: Any, *, today: str | None = None) -> str:
    """Format a DB date. Future dates fall back to LASTMOD_FLOOR (not today's date)."""
    if d is None:
        return LASTMOD_FLOOR
    if hasattr(d, "strftime"):
        iso = d.strftime("%Y-%m-%d")
    else:
        s = str(d)
        iso = s[:10] if s else LASTMOD_FLOOR
    if not iso or iso < LASTMOD_FLOOR:
        return LASTMOD_FLOOR
    ceiling = today or _utc_today_iso()
    if iso > ceiling:
        return LASTMOD_FLOOR
    return iso


def _max_lastmod(entries: list[tuple[str, str]], *, today: str | None = None) -> str:
    m = LASTMOD_FLOOR
    ceiling = today or _utc_today_iso()
    for _p, lm in entries:
        if not lm:
            continue
        if lm > ceiling:
            continue
        if lm > m:
            m = lm
    return m


def _fetch_regattas(cur, today: str) -> list[tuple[str, str]]:
    """Real regatta_id values from regattas that already have raced results. No invented IDs."""
    cur.execute(
        """
        SELECT
            regatta_id,
            CASE
                WHEN COALESCE(end_date, start_date) IS NOT NULL
                 AND COALESCE(end_date, start_date) <= CURRENT_DATE
                THEN COALESCE(end_date, start_date)
                ELSE DATE '2000-01-01'
            END AS lastmod
        FROM regattas
        WHERE regatta_id IS NOT NULL
          AND BTRIM(regatta_id::text) <> ''
          AND EXISTS (
              SELECT 1
              FROM results r
              WHERE r.regatta_id = regattas.regatta_id
                AND r.raced IS TRUE
          )
        """
    )
    out = []
    for r in cur.fetchall() or []:
        regatta_id = (str(r.get("regatta_id") or "")).strip()
        if not regatta_id:
            continue
        out.append((regatta_id, _date_iso(r.get("lastmod"), today=today)))
    return out


def _fetch_sailors(cur, today: str) -> list[tuple[str, str]]:
    """
    One canonical /sailor/{name-slug} per unique live public slug.
    Live api.py never appends SAS id; name-{sasid} URLs 301 to the name slug.
    """
    cur.execute(
        """
        WITH raced AS (
            SELECT
                BTRIM(x.sa_id) AS sas_id,
                MAX(
                    CASE
                        WHEN x.d IS NOT NULL AND x.d <= CURRENT_DATE THEN x.d
                    END
                ) AS lastmod
            FROM (
                SELECT r.helm_sa_sailing_id::text AS sa_id,
                       COALESCE(rg.end_date, rg.start_date) AS d
                FROM results r
                JOIN regattas rg ON rg.regatta_id = r.regatta_id
                WHERE r.raced IS TRUE
                  AND r.helm_sa_sailing_id IS NOT NULL
                UNION ALL
                SELECT r.crew_sa_sailing_id::text AS sa_id,
                       COALESCE(rg.end_date, rg.start_date) AS d
                FROM results r
                JOIN regattas rg ON rg.regatta_id = r.regatta_id
                WHERE r.raced IS TRUE
                  AND r.crew_sa_sailing_id IS NOT NULL
            ) x
            WHERE x.sa_id IS NOT NULL AND BTRIM(x.sa_id) <> ''
            GROUP BY BTRIM(x.sa_id)
        )
        SELECT
            s.sa_sailing_id::text AS sas_id,
            COALESCE(NULLIF(TRIM(s.first_name), ''), '') AS first_name,
            COALESCE(NULLIF(TRIM(s.last_name), ''), '') AS last_name,
            COALESCE(NULLIF(TRIM(s.full_name), ''), '') AS full_name_raw,
            raced.lastmod
        FROM sas_id_personal s
        JOIN raced ON raced.sas_id = s.sa_sailing_id::text
        WHERE s.sa_sailing_id IS NOT NULL
        """
    )
    rows = list(cur.fetchall() or [])
    by_slug: dict[str, str] = {}
    for r in rows:
        sas_id = (r.get("sas_id") or "").strip()
        if not sas_id:
            continue
        display = _sas_personal_display_name(
            r.get("first_name") or "",
            r.get("last_name") or "",
            r.get("full_name_raw") or "",
        )
        slug = _sailor_canonical_slug(display, sas_id, False)
        if not slug:
            continue
        lastmod_iso = _date_iso(r.get("lastmod"), today=today)
        prev = by_slug.get(slug)
        if prev is None or lastmod_iso > prev:
            by_slug[slug] = lastmod_iso
    return list(by_slug.items())


def _fetch_classes(cur, today: str) -> list[tuple[int, str, str]]:
    """Current class_name so /class/{canonical-slug} matches live _class_public_path (never id-prefixed)."""
    cur.execute(
        """
        SELECT
            c.class_id,
            c.class_name,
            (
                SELECT MAX(
                    CASE
                        WHEN COALESCE(rg.end_date, rg.start_date) IS NOT NULL
                         AND COALESCE(rg.end_date, rg.start_date) <= CURRENT_DATE
                        THEN COALESCE(rg.end_date, rg.start_date)
                    END
                )
                FROM results r
                JOIN regattas rg ON rg.regatta_id = r.regatta_id
                WHERE r.class_id = c.class_id
                  AND r.raced IS TRUE
            ) AS lastmod
        FROM classes c
        WHERE c.class_id IS NOT NULL
          AND EXISTS (
              SELECT 1
              FROM results r
              WHERE r.class_id = c.class_id
                AND r.raced IS TRUE
          )
        """
    )
    out = []
    for r in cur.fetchall() or []:
        cid = r.get("class_id")
        name = (r.get("class_name") or "").strip()
        if cid is None:
            continue
        out.append((int(cid), name, _date_iso(r.get("lastmod"), today=today)))
    return out


def _fetch_clubs(cur, today: str) -> list[tuple[int, str, str, str]]:
    """
    Canonical club_code only (abbrev when present, else fullname) — same as serve_club_page.
    lastmod is the latest hosted/result date that is not in the future.
    """
    cur.execute(
        """
        SELECT
            c.club_id,
            NULLIF(TRIM(c.club_abbrev), '') AS club_abbrev,
            NULLIF(TRIM(c.club_fullname), '') AS club_fullname,
            GREATEST(
                COALESCE(
                    MAX(
                        CASE
                            WHEN COALESCE(hosted.end_date, hosted.start_date) IS NOT NULL
                             AND COALESCE(hosted.end_date, hosted.start_date) <= CURRENT_DATE
                            THEN COALESCE(hosted.end_date, hosted.start_date)
                        END
                    ),
                    DATE '2000-01-01'
                ),
                COALESCE(
                    MAX(
                        CASE
                            WHEN COALESCE(rg.end_date, rg.start_date) IS NOT NULL
                             AND COALESCE(rg.end_date, rg.start_date) <= CURRENT_DATE
                            THEN COALESCE(rg.end_date, rg.start_date)
                        END
                    ),
                    DATE '2000-01-01'
                )
            ) AS lastmod
        FROM clubs c
        LEFT JOIN regattas hosted ON hosted.host_club_id = c.club_id
        LEFT JOIN results r ON r.club_id = c.club_id AND r.raced IS TRUE
        LEFT JOIN regattas rg ON rg.regatta_id = r.regatta_id
        WHERE c.club_id IS NOT NULL
          AND LOWER(TRIM(COALESCE(c.club_abbrev, ''))) <> 'unassigned'
          AND EXISTS (
              SELECT 1
              FROM results rr
              WHERE rr.club_id = c.club_id
                AND rr.raced IS TRUE
          )
        GROUP BY c.club_id, c.club_abbrev, c.club_fullname
        """
    )
    out = []
    for r in cur.fetchall() or []:
        cid = r.get("club_id")
        if cid is None:
            continue
        abbrev = (r.get("club_abbrev") or "").strip()
        fullname = (r.get("club_fullname") or "").strip()
        out.append((int(cid), abbrev, fullname, _date_iso(r.get("lastmod"), today=today)))
    return out


def _build_urlset_xml(base_url: str, entries: list[tuple[str, str]]) -> str:
    """path_suffix '/' = homepage loc exactly base (no trailing slash)."""
    base = (base_url or BASE_URL_DEFAULT).rstrip("/")
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for path_suffix, lastmod in entries:
        if path_suffix == "/":
            loc = base
        elif path_suffix.startswith("/"):
            loc = f"{base}{path_suffix}"
        else:
            loc = f"{base}/{path_suffix}"
        esc = _escape_loc(loc)
        lines.append("  <url>")
        lines.append(f"    <loc>{esc}</loc>")
        lines.append(f"    <lastmod>{lastmod}</lastmod>")
        lines.append("    <changefreq>weekly</changefreq>")
        lines.append("  </url>")
    lines.append("</urlset>")
    return "\n".join(lines)


def _build_sitemap_index_xml(base_url: str, child_locs_lastmod: list[tuple[str, str]]) -> str:
    """child_locs_lastmod: (full https URL to child sitemap, lastmod YYYY-MM-DD)."""
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for loc, lastmod in child_locs_lastmod:
        lines.append("  <sitemap>")
        lines.append(f"    <loc>{_escape_loc(loc)}</loc>")
        lines.append(f"    <lastmod>{lastmod}</lastmod>")
        lines.append("  </sitemap>")
    lines.append("</sitemapindex>")
    return "\n".join(lines)


def _atomic_write(path: str, content: str) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(content)
    os.replace(tmp, path)


def _chunk_filenames(stem: str, n: int, max_per: int) -> list[str]:
    if n == 0:
        return []
    if n <= max_per:
        return [f"{stem}.xml"]
    n_parts = (n + max_per - 1) // max_per
    return [f"{stem}-part{i + 1:05d}.xml" for i in range(n_parts)]


def _remove_stale_sitemaps(out_dir: str, keep_basenames: set[str]) -> None:
    pattern = os.path.join(out_dir, "sitemap*.xml")
    for path in glob.glob(pattern):
        base = os.path.basename(path)
        if base not in keep_basenames:
            try:
                os.remove(path)
                LOG.info("sitemap_builder: removed stale %s", path)
            except OSError as e:
                LOG.warning("sitemap_builder: could not remove stale %s: %s", path, e)


def _dedupe_entries(
    entries: list[tuple[str, str]],
    seen: set[str],
) -> list[tuple[str, str]]:
    """Keep first occurrence of each path across the whole sitemap family."""
    out: list[tuple[str, str]] = []
    for path, lastmod in entries:
        if not path or path in seen:
            continue
        seen.add(path)
        out.append((path, lastmod))
    return out


def build_sitemap(
    db,
    *,
    output_path: str | None = None,
    base_url: str | None = None,
) -> dict[str, Any] | None:
    """
    Build sitemap index at output_path (default .../sitemap.xml) and child urlsets alongside it.
    Returns stats dict on success, None on failure.
    """
    output_path = output_path or os.path.join(
        os.getenv("SITEMAP_STATIC_DIR", DEFAULT_STATIC_DIR),
        SITEMAP_INDEX_FILENAME,
    )
    base_url = base_url or os.getenv("BASE_URL", BASE_URL_DEFAULT)
    if "localhost" in base_url or "127.0.0.1" in base_url:
        base_url = BASE_URL_DEFAULT
    # Canonical sitemap base is always HTTPS and non-www.
    try:
        p = urlsplit(base_url)
        host = (p.netloc or "").lower()
        if host.startswith("www."):
            host = host[4:]
        if not host:
            host = "sailingsa.co.za"
        base_url = urlunsplit(("https", host, "", "", ""))
    except Exception:
        base_url = BASE_URL_DEFAULT
    base = base_url.rstrip("/")
    out_dir = os.path.dirname(os.path.abspath(output_path))
    index_basename = os.path.basename(output_path)
    if not index_basename.endswith(".xml"):
        index_basename = SITEMAP_INDEX_FILENAME

    max_per = max(1, min(SITEMAP_MAX_URLS_PER_FILE, 50000))
    today = _utc_today_iso()

    try:
        cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    except Exception as e:
        LOG.warning("sitemap_builder: no cursor from db: %s", e)
        return None

    try:
        regattas = _fetch_regattas(cur, today)
        sailors = _fetch_sailors(cur, today)
        classes = _fetch_classes(cur, today)
        clubs = _fetch_clubs(cur, today)
    except Exception as e:
        LOG.warning("sitemap_builder: fetch failed: %s", e)
        return None
    finally:
        try:
            cur.close()
        except Exception:
            pass

    seen_paths: set[str] = set()

    reg_entries: list[tuple[str, str]] = []
    for regatta_id, lastmod in sorted(regattas, key=lambda x: x[1], reverse=True):
        path = f"/regatta/{regatta_id}"
        if path in seen_paths:
            continue
        seen_paths.add(path)
        reg_entries.append((path, lastmod))

    class_entries: list[tuple[str, str]] = []
    for cid, class_name, lastmod in sorted(classes, key=lambda x: x[2], reverse=True):
        path = _class_public_path(class_name)
        if not path or path in seen_paths:
            continue
        seen_paths.add(path)
        class_entries.append((path, lastmod))

    club_entries: list[tuple[str, str]] = []
    for cid, abbrev, fullname, lastmod in sorted(clubs, key=lambda x: x[3], reverse=True):
        # Canonical club_code: abbrev first (e.g. /club/hyc), fullname only when abbrev is empty.
        code = _club_slug_from_name(abbrev) if abbrev else _club_slug_from_name(fullname)
        if not code:
            continue
        path = f"/club/{code}"
        if path in seen_paths:
            continue
        seen_paths.add(path)
        club_entries.append((path, lastmod))

    sailor_entries: list[tuple[str, str]] = []
    for slug, lastmod in sorted(sailors, key=lambda x: x[1], reverse=True):
        path = f"/sailor/{slug}"
        if path in seen_paths:
            continue
        seen_paths.add(path)
        sailor_entries.append((path, lastmod))

    family_lastmod = _max_lastmod(
        reg_entries + class_entries + club_entries + sailor_entries,
        today=today,
    )
    core_entries = _dedupe_entries([(path, family_lastmod) for path in CORE_PATHS], seen_paths)

    if out_dir and not os.path.isdir(out_dir):
        try:
            os.makedirs(out_dir, exist_ok=True)
        except OSError as e:
            LOG.warning("sitemap_builder: mkdir %s: %s", out_dir, e)
            return None

    by_file: dict[str, int] = {}
    index_rows: list[tuple[str, str]] = []
    written_names: set[str] = {index_basename}

    def write_chunked(stem: str, entries: list[tuple[str, str]]) -> None:
        nonlocal index_rows, by_file, written_names
        names = _chunk_filenames(stem, len(entries), max_per)
        if not names:
            return
        if len(names) == 1:
            xml = _build_urlset_xml(base_url, entries)
            fn = names[0]
            path = os.path.join(out_dir, fn)
            _atomic_write(path, xml)
            by_file[fn] = len(entries)
            written_names.add(fn)
            index_rows.append((f"{base}/{fn}", _max_lastmod(entries, today=today)))
            return
        offset = 0
        for fn in names:
            chunk = entries[offset : offset + max_per]
            offset += max_per
            xml = _build_urlset_xml(base_url, chunk)
            path = os.path.join(out_dir, fn)
            _atomic_write(path, xml)
            by_file[fn] = len(chunk)
            written_names.add(fn)
            index_rows.append((f"{base}/{fn}", _max_lastmod(chunk, today=today)))

    write_chunked("sitemap-core", core_entries)
    write_chunked("sitemap-regattas", reg_entries)
    write_chunked("sitemap-classes", class_entries)
    write_chunked("sitemap-clubs", club_entries)
    write_chunked("sitemap-sailors", sailor_entries)

    index_rows.sort(key=lambda x: x[0])

    index_xml = _build_sitemap_index_xml(base_url, index_rows)
    if "<sitemapindex" not in index_xml or not index_rows:
        LOG.warning("sitemap_builder: invalid index (children=%s)", len(index_rows))
        return None

    index_full = os.path.join(out_dir, index_basename)
    _atomic_write(index_full, index_xml)

    _remove_stale_sitemaps(out_dir, written_names)

    all_paths = [p for p, _ in (core_entries + reg_entries + class_entries + club_entries + sailor_entries)]
    unique_n = len(set(all_paths))
    total_urls = sum(by_file.values())
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    LOG.info(
        "Sitemap index rebuilt at %s — files=%s total_urls=%s unique=%s",
        ts,
        len(by_file),
        total_urls,
        unique_n,
    )

    return {
        "ok": True,
        "index_path": index_full,
        "by_file": dict(sorted(by_file.items())),
        "total_urls": total_urls,
        "unique_urls": unique_n,
        "duplicate_locs": total_urls - unique_n,
        "child_sitemaps": len(index_rows),
    }


# Back-compat alias
SITEMAP_FILENAME = SITEMAP_INDEX_FILENAME
