#!/usr/bin/env python3
"""Surgical in-place patch of live /var/www/sailingsa/api/api.py. Do not replace the whole file."""
from __future__ import annotations

from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")


def once(text: str, old: str, new: str, label: str) -> str:
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"FAIL {label}: expected 1 occurrence, found {n}")
    return text.replace(old, new, 1)


def main() -> None:
    text = API.read_text(encoding="utf-8")
    orig_len = len(text)

    text = once(
        text,
        '''@app.get("/club/{slug}")
@app.head("/club/{slug}")
def _club_standalone(slug: str):
''',
        '''@app.get("/club/{a}/{b}")
@app.head("/club/{a}/{b}")
def _club_slash_alias(a: str, b: str):
    """Legacy dual-club paths e.g. /club/VLC/AEOLIANS → club_aliases 'VLC/Aeolians'."""
    return _club_standalone(f"{a}/{b}")


@app.get("/club/{slug}")
@app.head("/club/{slug}")
def _club_standalone(slug: str):
''',
        "club slash route",
    )

    text = once(
        text,
        '''@app.get("/test/class/{class_ref}", response_class=HTMLResponse)
def test_class_aggregate_page(class_ref: str):
''',
        '''@app.get("/test/class/{class_ref}", response_class=HTMLResponse)
@app.head("/test/class/{class_ref}")
def test_class_aggregate_page(class_ref: str):
    """Legacy internal test URL. 301 to public /class/{slug} or 404. Not a public class page."""
    try:
        data = api_class_by_id(str(class_ref))
    except HTTPException as e:
        return HTMLResponse(
            f"<html><body><p>{html_module.escape(str(e.detail or 'Not found'))}</p></body></html>",
            status_code=int(getattr(e, "status_code", 404) or 404),
        )
    class_name = (data.get("class_name") or "").strip()
    cslug = (data.get("class_slug") or _class_canonical_slug(class_name)).strip()
    path = (data.get("path") or _class_public_path(None, class_name, cslug) or "").strip()
    if path.startswith("/class/") and path != "/classes":
        return RedirectResponse(url=path, status_code=301)
    return HTMLResponse(
        "<html><body><p>Class not found</p></body></html>",
        status_code=404,
    )


def _gsc_phase1_removed_test_class_harness_placeholder():
''',
        "test_class new handler prefix",
    )
    # Drop the old harness body: from placeholder through the line before /api/sa-id-stats.
    start = text.find("def _gsc_phase1_removed_test_class_harness_placeholder():")
    end = text.find('@app.get("/api/sa-id-stats")', start if start >= 0 else 0)
    if start < 0 or end < 0 or end <= start:
        raise SystemExit(
            f"FAIL could not locate old test_class body to remove start={start} end={end}"
        )
    text = text[:start] + text[end:]

    text = once(
        text,
        '''    if not slug or not slug.strip():
        return None, None
    slug = slug.strip()
    _slug_need_results_fb = None
''',
        '''    if not slug or not slug.strip():
        return None, None
    slug = slug.strip()
    _SAILOR_SLUG_ALIASES = {
        "celia-hogan": "cecilia-hogan",
        "bella-keytel": "isabella-keytel",
    }
    slug = _SAILOR_SLUG_ALIASES.get(slug.lower(), slug)
    _slug_need_results_fb = None
''',
        "sailor slug aliases",
    )

    text = once(
        text,
        '''_REGATTA_STANDALONE_SLUG_REDIRECTS: Dict[str, str] = {
    "live-2026-29er-rsa-nationals-sbyc": "/regatta/2026-03-30-29er-rsa-nationals",
''',
        '''_REGATTA_STANDALONE_SLUG_REDIRECTS: Dict[str, str] = {
    "2024-08-17-ullman-sails-womens-cruise": "/regatta/2024-08-17-ullman-sails-women-039-s-series",
    "msc-results-l26-and-orc-nationals": "/regatta/2023-07-07-msc-l26-orc-nationals",
    "df95-wc-regional-championships-final-results": "/regatta/2025-10-12-df95-wc-regional-championships",
    "2025-10-12-df95-wc-regional-championships---final-results": "/regatta/2025-10-12-df95-wc-regional-championships",
    "live-2026-29er-rsa-nationals-sbyc": "/regatta/2026-03-30-29er-rsa-nationals",
''',
        "legacy regatta slug aliases",
    )

    text = once(
        text,
            '''            if numeric_club_id is not None:
                for row in rows:
                    if int(row.get("club_id") or 0) == numeric_club_id:
                        club_abbrev = (row.get("club_abbrev") or "").strip()
                        club_fullname = (row.get("club_fullname") or club_abbrev or "").strip()
                        return (numeric_club_id, club_fullname, club_abbrev)
            return None
''',
            '''            if numeric_club_id is not None:
                for row in rows:
                    if int(row.get("club_id") or 0) == numeric_club_id:
                        club_abbrev = (row.get("club_abbrev") or "").strip()
                        club_fullname = (row.get("club_fullname") or club_abbrev or "").strip()
                        return (numeric_club_id, club_fullname, club_abbrev)
            if table_exists("club_aliases"):
                cur.execute(
                    """
                    SELECT c.club_id, c.club_abbrev, c.club_fullname
                    FROM club_aliases a
                    JOIN clubs c ON c.club_id = a.club_id
                    WHERE lower(trim(a.alias)) = %s
                       OR lower(replace(trim(a.alias), ' ', '-')) = %s
                    LIMIT 1
                    """,
                    (slug, slug),
                )
                alias_row = cur.fetchone()
                if alias_row:
                    club_abbrev = (alias_row.get("club_abbrev") or "").strip()
                    club_fullname = (alias_row.get("club_fullname") or club_abbrev or "").strip()
                    return (int(alias_row.get("club_id") or 0), club_fullname, club_abbrev)
            return None
''',
        "club_aliases public lookup",
    )

    text = once(
        text,
        '''def serve_regatta_class_standalone(slug: str, class_slug: str, request: Request):
    """Child of the Event URL. Current event blocks are the only source of truth."""
    reg = _get_regatta_by_slug(slug)
    if not reg:
        return RedirectResponse(url="/events", status_code=301)
''',
        '''def serve_regatta_class_standalone(slug: str, class_slug: str, request: Request):
    """Child of the Event URL. Current event blocks are the only source of truth."""
    reg = _get_regatta_by_slug(slug)
    if not reg:
        _alias = _regatta_slug_redirect_target(str(slug).strip())
        if _alias:
            _canon = str(_alias).rstrip("/").rsplit("/", 1)[-1]
            if _canon:
                reg = _get_regatta_by_slug(_canon)
        if not reg:
            return HTMLResponse(content=_REGATTA_404_HTML, status_code=404, media_type="text/html")
''',
        "class-* never /events",
    )

    text = once(
        text,
        '''    body = f"User-agent: *\\nAllow: /\\nSitemap: {base}/sitemap.xml\\n"
''',
        '''    body = f"User-agent: *\\nAllow: /\\nDisallow: /test/\\nSitemap: {base}/sitemap.xml\\n"
''',
        "robots.txt Disallow /test/",
    )

    if text.count('return RedirectResponse(url="/events", status_code=301)') and "serve_regatta_class_standalone" in text:
        # Remaining /events redirects must not be inside serve_regatta_class_standalone.
        fn = text.split("def serve_regatta_class_standalone", 1)[1]
        fn = fn.split("\ndef ", 1)[0]
        if 'RedirectResponse(url="/events"' in fn:
            raise SystemExit("FAIL class standalone still redirects to /events")

    if orig_len == len(text):
        raise SystemExit("FAIL patch produced no size change")
    API.write_text(text, encoding="utf-8")
    print(f"OK patched {API} bytes {orig_len} -> {len(text)}")


if __name__ == "__main__":
    main()
