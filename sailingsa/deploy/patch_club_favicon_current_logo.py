#!/usr/bin/env python3
"""Point each club URL's favicon at the logo currently on that page.

A replaced club logo or public link must not keep a saved club page that still
advertises the old icon or the old website / Facebook / map / email.
Idempotent. Run on the live server. Does not restart the API.
"""
from __future__ import annotations

import pathlib
import sys

API = pathlib.Path("/var/www/sailingsa/api/api.py")
MARKER = "CLUB_FAVICON_CURRENT_v1"

HELPERS = r'''
# CLUB_FAVICON_CURRENT_v1 — favicon and paste preview follow the logo on the page
def _club_logo_public_src(code: str) -> str:
    """Artwork URL shown on /club/{slug}, versioned by the file so a replacement is a new URL."""
    path = _club_logo_disk_path(code)
    if not path or not os.path.isfile(path):
        return ""
    src = _regatta_host_club_logo_src_for_code(code) or ""
    if not src:
        return ""
    try:
        token = f"{int(os.stat(path).st_mtime_ns):x}"
    except OSError:
        return src.split("?", 1)[0]
    return src.split("?", 1)[0] + "?v=" + token


def _club_favicon_head(code: str) -> str:
    """Club URL icon. Falls back to the site icon when this club has no logo file."""
    src = _club_logo_public_src((code or "").strip())
    site = (
        "<link rel=\"icon\" href=\"/favicon.ico\" sizes=\"any\">"
        "<link rel=\"icon\" type=\"image/png\" sizes=\"16x16\" href=\"/favicon-16.png\">"
        "<link rel=\"icon\" type=\"image/png\" sizes=\"32x32\" href=\"/favicon-32.png\">"
        "<link rel=\"icon\" type=\"image/png\" sizes=\"48x48\" href=\"/favicon-48.png\">"
        "<link rel=\"icon\" type=\"image/png\" sizes=\"192x192\" href=\"/favicon-192.png\">"
        "<link rel=\"apple-touch-icon\" href=\"/apple-touch-icon.png\">"
        "<link rel=\"icon\" type=\"image/png\" sizes=\"192x192\" href=\"/favicon-192.png\">"
    )
    if not src:
        return site
    esc = html_module.escape(src, quote=True)
    return (
        f'<link rel="icon" type="image/png" href="{esc}">'
        f'<link rel="shortcut icon" type="image/png" href="{esc}">'
        f'<link rel="apple-touch-icon" href="{esc}">'
    )


def _club_cached_html_current(slug: str, body: bytes) -> bool:
    """False when saved HTML still has a logo or public link that was replaced."""
    try:
        text = body.decode("utf-8", "replace")
    except Exception:
        return False
    code = ""
    m = re.search(r'data-club-abbrev="([^"]*)"', text)
    if m:
        code = (m.group(1) or "").strip()
    if code:
        try:
            src = _club_logo_public_src(code)
        except Exception:
            src = ""
        if src and src not in text:
            return False
    key = (code or slug or "").strip().lower()
    if not key:
        return True
    conn = None
    cur = None
    row = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT COALESCE(website_url, ''), COALESCE(facebook_url, ''),
                   COALESCE(location_url, ''), COALESCE(email, '')
            FROM clubs
            WHERE lower(btrim(club_abbrev)) = %s
            LIMIT 1
            """,
            (key,),
        )
        row = cur.fetchone()
    except Exception as e:
        print(f"[club-cache] stamp {key}: {e}", flush=True)
        return True
    finally:
        try:
            if cur is not None:
                cur.close()
        except Exception:
            pass
        if conn is not None:
            return_db_connection(conn)
    if not row:
        return True
    for val in row:
        v = str(val or "").strip()
        if not v:
            continue
        if v in text or html_module.escape(v, quote=True) in text:
            continue
        return False
    return True


'''

OLD_MEM = '''    ent = _CLUB_PAGE_HTML_CACHE.get(key)
    if ent and (now - float(ent[0])) < _CLUB_PAGE_HTML_TTL_SEC:
        return HTMLResponse(content=ent[1], media_type="text/html")

    disk = os.path.join(_CLUB_PAGE_DISK_DIR, re.sub(r"[^a-z0-9_-]+", "_", key) + ".html")
'''

NEW_MEM = '''    disk = os.path.join(_CLUB_PAGE_DISK_DIR, re.sub(r"[^a-z0-9_-]+", "_", key) + ".html")
    ent = _CLUB_PAGE_HTML_CACHE.get(key)
    if ent and (now - float(ent[0])) < _CLUB_PAGE_HTML_TTL_SEC and _club_cached_html_current(key, ent[1]):
        return HTMLResponse(content=ent[1], media_type="text/html")

'''

OLD_DISK = '''            if body:
                _CLUB_PAGE_HTML_CACHE[key] = (now, body)
'''

NEW_DISK = '''            if body and not _club_cached_html_current(key, body):
                body = b""
            if body:
                _CLUB_PAGE_HTML_CACHE[key] = (now, body)
'''

OLD_LOCK = '''        ent = _CLUB_PAGE_HTML_CACHE.get(key)
        if ent and (now - float(ent[0])) < _CLUB_PAGE_HTML_TTL_SEC:
            return HTMLResponse(content=ent[1], media_type="text/html")
'''

NEW_LOCK = '''        ent = _CLUB_PAGE_HTML_CACHE.get(key)
        if ent and (now - float(ent[0])) < _CLUB_PAGE_HTML_TTL_SEC and _club_cached_html_current(key, ent[1]):
            return HTMLResponse(content=ent[1], media_type="text/html")
'''

OLD_SRC = '''    _ensure_club_logo_cached(code, club_slug or None)
    if not _club_logo_file_exists_on_disk(code):
        return ""
    src = _regatta_host_club_logo_src_for_code(code)
'''

NEW_SRC = '''    _ensure_club_logo_cached(code, club_slug or None)
    if not _club_logo_file_exists_on_disk(code):
        return ""
    src = _club_logo_public_src(code)
'''

OLD_ICON = '''        + _fb_club_head +
        "<link rel=\\"icon\\" href=\\"/favicon.ico\\" sizes=\\"any\\"><link rel=\\"icon\\" type=\\"image/png\\" sizes=\\"16x16\\" href=\\"/favicon-16.png\\"><link rel=\\"icon\\" type=\\"image/png\\" sizes=\\"32x32\\" href=\\"/favicon-32.png\\"><link rel=\\"icon\\" type=\\"image/png\\" sizes=\\"48x48\\" href=\\"/favicon-48.png\\"><link rel=\\"icon\\" type=\\"image/png\\" sizes=\\"192x192\\" href=\\"/favicon-192.png\\"><link rel=\\"apple-touch-icon\\" href=\\"/apple-touch-icon.png\\">"
        "<link rel=\\"icon\\" type=\\"image/png\\" sizes=\\"192x192\\" href=\\"/favicon-192.png\\">"
'''

NEW_ICON = '''        + _fb_club_head +
        _club_favicon_head(ca) +
'''

ANCHOR = "def _club_page_header_logo_html(club_abbrev: str, club_slug: str) -> str:"


def main() -> int:
    text = API.read_text(encoding="utf-8")
    if MARKER in text:
        print("already patched")
        return 0
    missing = []
    for name, chunk in (
        ("mem", OLD_MEM),
        ("disk", OLD_DISK),
        ("lock", OLD_LOCK),
        ("src", OLD_SRC),
        ("icon", OLD_ICON),
    ):
        n = text.count(chunk)
        if n != 1:
            missing.append(f"{name} count={n}")
    if ANCHOR not in text:
        missing.append("anchor missing")
    if missing:
        print("REFUSING patch:", "; ".join(missing))
        return 1
    text = text.replace(OLD_MEM, NEW_MEM, 1)
    text = text.replace(OLD_DISK, NEW_DISK, 1)
    text = text.replace(OLD_LOCK, NEW_LOCK, 1)
    text = text.replace(OLD_SRC, NEW_SRC, 1)
    text = text.replace(OLD_ICON, NEW_ICON, 1)
    text = text.replace(ANCHOR, HELPERS + ANCHOR, 1)
    API.write_text(text, encoding="utf-8")
    print("patched", API)
    return 0


if __name__ == "__main__":
    sys.exit(main())
