"""
Full DB-driven sitemap builder. No request context. No FastAPI dependency.
Writes sitemap.xml (index) + child urlsets: core, regattas, sailors, classes, clubs.
Lastmod: regatta = COALESCE(end_date, start_date); sailor/class/club = MAX(regatta date).
No current_date. No parse timestamps.
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

CHILD_STEMS = ("sitemap-core", "sitemap-regattas", "sitemap-sailors", "sitemap-classes", "sitemap-clubs")


def _slug_from_name(full_name: str) -> str:
    if not full_name or not isinstance(full_name, str):
        return ""
    s = full_name.strip().lower().replace("&", " and ")
    s = re.sub(r"[^\w\s\-]", "", s)
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def _class_canonical_slug(class_name: str) -> str:
    if not class_name or not isinstance(class_name, str):
        return ""
    s = class_name.strip().lower().replace(" ", "-")
    s = re.sub(r"[^a-z0-9-]", "", s)
    return s.strip("-") or ""


def _club_canonical_slug(name: str) -> str:
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
    if d is None:
        return "2000-01-01"
    if hasattr(d, "strftime"):
        return d.strftime("%Y-%m-%d")
    s = str(d)
    return s[:10] if s else "2000-01-01"


def _max_lastmod(entries: list[tuple[str, str]]) -> str:
    m = "2000-01-01"
    for _p, lm in entries:
        if lm and lm > m:
            m = lm
    return m


def _fetch_regattas(cur) -> list[tuple[str, str]]:
    cur.execute("""
        SELECT
            regatta_id,
            COALESCE(end_date, start_date) AS lastmod
        FROM regattas
        WHERE regatta_id IS NOT NULL
          AND BTRIM(regatta_id::text) <> ''
          AND EXISTS (
              SELECT 1
              FROM results r
              WHERE r.regatta_id = regattas.regatta_id
                AND r.raced IS TRUE
          )
    """)
    out = []
    for r in cur.fetchall() or []:
        regatta_id = (str(r.get("regatta_id") or "")).strip()
        if not regatta_id:
            continue
        lastmod = r.get("lastmod")
        out.append((regatta_id, _date_iso(lastmod)))
    return out


def _fetch_sailors(cur) -> list[tuple[str, str]]:
    """Sailor URLs only from results (raced helm/crew names); slug from name. No sas_id_personal."""
    cur.execute("""
        SELECT
            LOWER(TRIM(t.nm)) AS name_key,
            MIN(TRIM(t.nm)) AS name_sample,
            MAX(COALESCE(rg.end_date, rg.start_date)) AS lastmod
        FROM (
            SELECT DISTINCT TRIM(r.helm_name) AS nm, r.regatta_id
            FROM results r
            WHERE r.helm_name IS NOT NULL
              AND BTRIM(r.helm_name) <> ''
              AND r.raced IS TRUE
            UNION
            SELECT DISTINCT TRIM(r.crew_name) AS nm, r.regatta_id
            FROM results r
            WHERE r.crew_name IS NOT NULL
              AND BTRIM(r.crew_name) <> ''
              AND r.raced IS TRUE
        ) t
        INNER JOIN regattas rg ON rg.regatta_id = t.regatta_id
        GROUP BY LOWER(TRIM(t.nm))
    """)
    out = []
    for r in cur.fetchall() or []:
        sample = (r.get("name_sample") or "").strip()
        if not sample:
            continue
        slug = _slug_from_name(sample)
        if slug:
            out.append((slug, _date_iso(r.get("lastmod"))))
    return out


def _fetch_classes(cur) -> list[tuple[int, str, str]]:
    cur.execute("""
        SELECT
            c.class_id,
            c.class_name,
            COALESCE(
                (SELECT MAX(COALESCE(rg.end_date, rg.start_date))
                 FROM results r
                 JOIN regattas rg ON rg.regatta_id = r.regatta_id
                 WHERE r.class_id = c.class_id
                   AND r.raced IS TRUE),
                DATE '2000-01-01'
            ) AS lastmod
        FROM classes c
        WHERE c.class_id IS NOT NULL
          AND EXISTS (
              SELECT 1
              FROM results r
              WHERE r.class_id = c.class_id
                AND r.raced IS TRUE
          )
    """)
    out = []
    for r in cur.fetchall() or []:
        cid = r.get("class_id")
        name = (r.get("class_name") or "").strip()
        lastmod = r.get("lastmod")
        if cid is None:
            continue
        out.append((int(cid), name, _date_iso(lastmod)))
    return out


def _fetch_clubs(cur) -> list[tuple[int, str, str]]:
    cur.execute("""
        SELECT
            c.club_id,
            COALESCE(NULLIF(TRIM(c.club_fullname), ''), NULLIF(TRIM(c.club_abbrev), ''), '') AS name,
            GREATEST(
                COALESCE(MAX(COALESCE(hosted.end_date, hosted.start_date)), DATE '2000-01-01'),
                COALESCE(MAX(COALESCE(rg.end_date, rg.start_date)), DATE '2000-01-01')
            ) AS lastmod
        FROM clubs c
        LEFT JOIN regattas hosted ON hosted.host_club_id = c.club_id
        LEFT JOIN results r ON r.club_id = c.club_id AND r.raced IS TRUE
        LEFT JOIN regattas rg ON rg.regatta_id = r.regatta_id
        WHERE c.club_id IS NOT NULL
          AND EXISTS (
              SELECT 1
              FROM results rr
              WHERE rr.club_id = c.club_id
                AND rr.raced IS TRUE
          )
        GROUP BY c.club_id, c.club_fullname, c.club_abbrev
    """)
    out = []
    for r in cur.fetchall() or []:
        cid = r.get("club_id")
        name = (r.get("name") or "").strip()
        lastmod = r.get("lastmod")
        if cid is None:
            continue
        out.append((int(cid), name, _date_iso(lastmod)))
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

    try:
        cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    except Exception as e:
        LOG.warning("sitemap_builder: no cursor from db: %s", e)
        return None

    try:
        regattas = _fetch_regattas(cur)
        sailors = _fetch_sailors(cur)
        classes = _fetch_classes(cur)
        clubs = _fetch_clubs(cur)
    except Exception as e:
        LOG.warning("sitemap_builder: fetch failed: %s", e)
        return None
    finally:
        try:
            cur.close()
        except Exception:
            pass

    reg_entries: list[tuple[str, str]] = []
    seen_reg: set[str] = set()
    for regatta_id, lastmod in sorted(regattas, key=lambda x: x[1], reverse=True):
        path = f"/regatta/{regatta_id}"
        if path in seen_reg:
            continue
        seen_reg.add(path)
        reg_entries.append((path, lastmod))

    class_entries: list[tuple[str, str]] = []
    seen_c: set[str] = set()
    for cid, class_name, lastmod in sorted(classes, key=lambda x: x[2], reverse=True):
        slug = _class_canonical_slug(class_name)
        path = f"/class/{cid}-{slug}" if slug else f"/class/{cid}"
        if path in seen_c:
            continue
        seen_c.add(path)
        class_entries.append((path, lastmod))

    club_entries: list[tuple[str, str]] = []
    seen_cl: set[str] = set()
    for cid, name, lastmod in sorted(clubs, key=lambda x: x[2], reverse=True):
        slug = _club_canonical_slug(name)
        path = f"/club/{slug}" if slug else f"/club/club-{cid}"
        if path in seen_cl:
            continue
        seen_cl.add(path)
        club_entries.append((path, lastmod))

    sailor_entries: list[tuple[str, str]] = []
    seen_s: set[str] = set()
    for slug, lastmod in sorted(sailors, key=lambda x: x[1], reverse=True):
        path = f"/sailor/{slug}"
        if path in seen_s:
            continue
        seen_s.add(path)
        sailor_entries.append((path, lastmod))

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
            index_rows.append((f"{base}/{fn}", _max_lastmod(entries)))
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
            index_rows.append((f"{base}/{fn}", _max_lastmod(chunk)))

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

    total_urls = sum(by_file.values())
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    LOG.info(
        "Sitemap index rebuilt at %s — files=%s total_urls=%s",
        ts,
        len(by_file),
        total_urls,
    )

    return {
        "ok": True,
        "index_path": index_full,
        "by_file": dict(sorted(by_file.items())),
        "total_urls": total_urls,
        "child_sitemaps": len(index_rows),
    }


# Back-compat alias
SITEMAP_FILENAME = SITEMAP_INDEX_FILENAME
