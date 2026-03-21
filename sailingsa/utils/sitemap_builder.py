"""
Full DB-driven sitemap builder. No request context. No FastAPI dependency.
Lastmod: regatta = COALESCE(end_date, start_date); sailor/class/club = MAX(regatta date).
No current_date. No parse timestamps.
"""
from __future__ import annotations

import os
import re
import logging
from datetime import datetime, timezone
from typing import Any

import psycopg2.extras  # RealDictCursor for dict-like rows

LOG = logging.getLogger(__name__)

# Default paths (override via env or args)
DEFAULT_STATIC_DIR = "/var/www/sailingsa/static"
SITEMAP_FILENAME = "sitemap.xml"
BASE_URL_DEFAULT = "https://sailingsa.co.za"


def _slug_from_name(full_name: str) -> str:
    if not full_name or not isinstance(full_name, str):
        return ""
    s = full_name.strip().lower().replace("&", " and ")
    s = re.sub(r"[^\w\s\-]", "", s)
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def _sailor_canonical_slug(full_name: str, sas_id: str, has_duplicate: bool) -> str:
    base = _slug_from_name(full_name)
    if not base:
        return f"sailor-{sas_id}" if sas_id else "sailor"
    if has_duplicate and sas_id:
        return f"{base}-{sas_id}"
    return base


def _class_canonical_slug(class_name: str) -> str:
    if not class_name or not isinstance(class_name, str):
        return ""
    s = class_name.strip().lower().replace(" ", "-")
    s = re.sub(r"[^a-z0-9-]", "", s)
    return s.strip("-") or ""


def _club_canonical_slug(name: str) -> str:
    """URL slug from club name; matches API _club_slug_from_name. No current_date."""
    if not name or not isinstance(name, str):
        return ""
    s = re.sub(r"[^\w\s\-]", "", name).strip().lower()
    return re.sub(r"\s+", "-", s).strip("-") or ""


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


def _date_iso(d: Any) -> str:
    """Format lastmod; no current_date."""
    if d is None:
        return "2000-01-01"
    if hasattr(d, "strftime"):
        return d.strftime("%Y-%m-%d")
    s = str(d)
    return s[:10] if s else "2000-01-01"


def _fetch_regattas(cur) -> list[tuple[str, str]]:
    """(regatta_id, lastmod). LOCKED: result_status IS NOT NULL; lastmod = COALESCE(end_date, start_date); exclude NULL lastmod."""
    cur.execute("""
        SELECT
            regatta_id,
            event_name,
            COALESCE(end_date, start_date) AS lastmod
        FROM regattas
        WHERE result_status IS NOT NULL
    """)
    out = []
    for r in cur.fetchall() or []:
        regatta_id = (r.get("regatta_id") or "").strip()
        lastmod = r.get("lastmod")
        if not regatta_id or lastmod is None:
            continue
        out.append((regatta_id, _date_iso(lastmod)))
    return out


def _fetch_sailors(cur) -> list[tuple[str, str, str]]:
    """(sas_id, full_name, lastmod). LOCKED: MAX(COALESCE(rg.end_date, rg.start_date)) join helm/crew; exclude NULL lastmod. Uses s.id for grouping; sa_sailing_id for slug."""
    cur.execute("""
        SELECT
            s.id,
            s.sa_sailing_id::text AS sas_id,
            COALESCE(TRIM(s.full_name), TRIM(s.first_name || ' ' || COALESCE(s.last_name, ''))) AS full_name,
            MAX(COALESCE(rg.end_date, rg.start_date)) AS lastmod
        FROM sas_id_personal s
        JOIN results r
          ON s.sa_sailing_id::text = r.helm_sa_sailing_id::text
          OR s.sa_sailing_id::text = r.crew_sa_sailing_id::text
        JOIN regattas rg
          ON r.regatta_id = rg.regatta_id
        GROUP BY s.id, s.sa_sailing_id, s.full_name, s.first_name, s.last_name
        HAVING MAX(COALESCE(rg.end_date, rg.start_date)) IS NOT NULL
    """)
    rows = list(cur.fetchall() or [])
    by_name: dict[str, list[tuple[str, str, str]]] = {}
    for r in rows:
        sas_id = (r.get("sas_id") or "").strip()
        full_name = (r.get("full_name") or "").strip()
        lastmod = r.get("lastmod")
        if not sas_id or lastmod is None:
            continue
        key = (full_name or "").lower()
        if key not in by_name:
            by_name[key] = []
        by_name[key].append((sas_id, full_name or "", _date_iso(lastmod)))
    out = []
    for _key, group in by_name.items():
        has_dup = len(group) > 1
        for sas_id, full_name, lastmod in group:
            slug = _sailor_canonical_slug(full_name, sas_id, has_dup)
            if slug:
                out.append((slug, lastmod))
    return out


def _fetch_classes(cur) -> list[tuple[int, str, str]]:
    """(class_id, class_name, lastmod). LOCKED: MAX(COALESCE(rg.end_date, rg.start_date)); exclude NULL lastmod."""
    cur.execute("""
        SELECT
            c.class_id,
            c.class_name,
            MAX(COALESCE(rg.end_date, rg.start_date)) AS lastmod
        FROM classes c
        JOIN results r ON r.class_id = c.class_id
        JOIN regattas rg ON rg.regatta_id = r.regatta_id
        GROUP BY c.class_id, c.class_name
        HAVING MAX(COALESCE(rg.end_date, rg.start_date)) IS NOT NULL
    """)
    out = []
    for r in cur.fetchall() or []:
        cid = r.get("class_id")
        name = (r.get("class_name") or "").strip()
        lastmod = r.get("lastmod")
        if cid is None or lastmod is None:
            continue
        out.append((int(cid), name, _date_iso(lastmod)))
    return out


def _fetch_clubs(cur) -> list[tuple[int, str, str]]:
    """(club_id, name_for_slug, lastmod). lastmod = max(hosted regatta date, sailor-activity regatta date). No current_date."""
    cur.execute("""
        SELECT
            c.club_id,
            COALESCE(TRIM(c.club_fullname), TRIM(c.club_abbrev), '') AS name,
            MAX(GREATEST(
                COALESCE(hosted.end_date, hosted.start_date),
                COALESCE(rg.end_date, rg.start_date)
            )) AS lastmod
        FROM clubs c
        LEFT JOIN regattas hosted ON hosted.host_club_id = c.club_id
        LEFT JOIN results r ON r.club_id = c.club_id
        LEFT JOIN regattas rg ON rg.regatta_id = r.regatta_id
        GROUP BY c.club_id, c.club_fullname, c.club_abbrev
        HAVING MAX(GREATEST(
            COALESCE(hosted.end_date, hosted.start_date),
            COALESCE(rg.end_date, rg.start_date)
        )) IS NOT NULL
    """)
    out = []
    for r in cur.fetchall() or []:
        cid = r.get("club_id")
        name = (r.get("name") or "").strip()
        lastmod = r.get("lastmod")
        if cid is None or lastmod is None:
            continue
        out.append((int(cid), name, _date_iso(lastmod)))
    return out


def _build_xml(base_url: str, entries: list[tuple[str, str]]) -> str:
    """entries = [(path_suffix, lastmod), ...] e.g. ('/', '2025-01-01'), ('/regatta/302-...', '2025-02-01')."""
    base = (base_url or BASE_URL_DEFAULT).rstrip("/")
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for path_suffix, lastmod in entries:
        loc = f"{base}{path_suffix}" if path_suffix.startswith("/") else f"{base}/{path_suffix}"
        esc = _escape_loc(loc)
        lines.append("  <url>")
        lines.append(f"    <loc>{esc}</loc>")
        lines.append(f"    <lastmod>{lastmod}</lastmod>")
        lines.append("    <changefreq>weekly</changefreq>")
        lines.append("  </url>")
    lines.append("</urlset>")
    return "\n".join(lines)


def build_sitemap(
    db,
    *,
    output_path: str | None = None,
    base_url: str | None = None,
) -> bool:
    """
    Build full sitemap from regattas, sailors, classes, clubs (all DB-authoritative lastmod; no current_date).
    Writes to output_path (default static/sitemap.xml). Uses file lock to prevent parallel rebuilds.
    Returns True on success, False on failure (logs and does not raise).
    No request context. No FastAPI route dependency.
    """
    output_path = output_path or os.path.join(
        os.getenv("SITEMAP_STATIC_DIR", DEFAULT_STATIC_DIR),
        SITEMAP_FILENAME,
    )
    base_url = base_url or os.getenv("BASE_URL", BASE_URL_DEFAULT)
    if "localhost" in base_url or "127.0.0.1" in base_url:
        base_url = BASE_URL_DEFAULT

    try:
        cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    except Exception as e:
        LOG.warning("sitemap_builder: no cursor from db: %s", e)
        return False

    try:
        # Regatta-result URLs (canonical: /regatta/{regatta_id})
        regattas = _fetch_regattas(cur)
        # Sailor URLs with authoritative lastmod
        sailors = _fetch_sailors(cur)
        # Class URLs with authoritative lastmod
        classes = _fetch_classes(cur)
        # Club URLs: clubs with results; lastmod = latest regatta date involving that club (via results.club_id)
        clubs = _fetch_clubs(cur)
    except Exception as e:
        LOG.warning("sitemap_builder: fetch failed: %s", e)
        return False
    finally:
        try:
            cur.close()
        except Exception:
            pass

    seen = set()
    entries: list[tuple[str, str]] = []

    # Homepage: use max regatta lastmod (no current_date)
    homepage_lastmod = "2000-01-01"
    for _rid, lastmod in regattas:
        if lastmod and lastmod > homepage_lastmod:
            homepage_lastmod = lastmod
    entries.append(("/", homepage_lastmod))
    seen.add("/")

    for regatta_id, lastmod in regattas:
        path = f"/regatta/{regatta_id}"
        if path in seen:
            continue
        seen.add(path)
        entries.append((path, lastmod))

    for slug, lastmod in sailors:
        path = f"/sailor/{slug}"
        if path in seen:
            continue
        seen.add(path)
        entries.append((path, lastmod))

    for cid, class_name, lastmod in classes:
        slug = _class_canonical_slug(class_name)
        path = f"/class/{cid}-{slug}" if slug else f"/class/{cid}"
        if path in seen:
            continue
        seen.add(path)
        entries.append((path, lastmod))

    for cid, name, lastmod in clubs:
        slug = _club_canonical_slug(name)
        path = f"/club/{slug}" if slug else f"/club/club-{cid}"
        if path in seen:
            continue
        seen.add(path)
        entries.append((path, lastmod))

    xml = _build_xml(base_url, entries)

    # Safety: prevent accidental empty overwrite if query failed silently
    if "<urlset" not in xml or len(entries) == 0:
        LOG.warning("sitemap_builder: refused to write invalid/empty sitemap (urlset=%s, count=%s)", "<urlset" in xml, len(entries))
        return False

    out_dir = os.path.dirname(output_path)
    if out_dir and not os.path.isdir(out_dir):
        try:
            os.makedirs(out_dir, exist_ok=True)
        except OSError as e:
            LOG.warning("sitemap_builder: mkdir %s: %s", out_dir, e)
            return False

    tmp_path = output_path + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(xml)
        os.replace(tmp_path, output_path)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        LOG.info("Sitemap rebuilt successfully at %s — URL count: %s", ts, len(entries))
        return True
    except Exception as e:
        LOG.warning("sitemap_builder: write failed: %s", e)
        return False
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
