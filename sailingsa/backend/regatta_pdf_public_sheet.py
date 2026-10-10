"""Public results sheet for stored PDFs.

Parent `/regatta/{id}` is truth. The PDF must take logos and the public
fleet table from that page — never a second backend render that still has
Age / PY / Elapsed JSON / Open class marks CSS-hidden on the URL.
"""
from __future__ import annotations

import re
from typing import Any, Optional
from urllib.parse import unquote
from urllib.request import Request, urlopen

_DROP_LABELS = frozenset(
    {
        "age",
        "cat",
        "py",
        "elapsed",
        "corrected",
        "elapsed time",
        "corrected time",
    }
)
_CLASS_LOGO_RE = re.compile(r"/artwork/class(?:%20| )logo/", re.I)
_TABLE_RE = re.compile(r"(<table\b[^>]*>)(.*?)(</table>)", re.I | re.S)
_ROW_RE = re.compile(r"<tr\b[^>]*>.*?</tr>", re.I | re.S)
_CELL_RE = re.compile(r"<(th|td)(\b[^>]*)>(.*?)</\1>", re.I | re.S)
_IMG_RE = re.compile(r"<img\b[^>]*>", re.I)


def _plain(html: str) -> str:
    txt = re.sub(r"<[^>]+>", " ", html or "")
    txt = re.sub(r"&quot;", '"', txt)
    txt = re.sub(r"&#39;", "'", txt)
    return re.sub(r"\s+", " ", txt).strip()


def _is_event_logo(path: str) -> bool:
    raw = unquote(str(path or "").split("?", 1)[0]).lower()
    return "/artwork/event logo/" in raw


def _is_class_logo(path: str) -> bool:
    return bool(_CLASS_LOGO_RE.search(str(path or "")))


def _is_json_blob(text: str) -> bool:
    s = (text or "").strip()
    if not s:
        return False
    low = s.lower().replace("&quot;", '"')
    return ('{"r' in low) or (low.startswith("{") and '"r1"' in low)


def _drop_indexes(header_cells: list[tuple[str, str, str]]) -> set[int]:
    drop: set[int] = set()
    for i, (_tag, attrs, inner) in enumerate(header_cells):
        lab = _plain(inner).lower()
        if lab in _DROP_LABELS:
            drop.add(i)
            continue
        if _is_json_blob(_plain(inner)):
            drop.add(i)
            continue
        cls = ""
        m = re.search(r'class="([^"]*)"', attrs or "", flags=re.I)
        if m:
            cls = m.group(1).lower()
        if "dam-bottle-json" in cls or "dam-bottle-et" in cls or "dam-bottle-corr" in cls:
            drop.add(i)
        if "dam-bottle-py" in cls or "dam-bottle-cat" in cls:
            drop.add(i)
    return drop


def _strip_table(table_inner: str, drop: set[int]) -> str:
    if not drop:
        return table_inner

    def _row(m: re.Match) -> str:
        row = m.group(0)
        cells = list(_CELL_RE.finditer(row))
        if not cells:
            return row
        kept = []
        for i, cell in enumerate(cells):
            if i in drop:
                continue
            kept.append(cell.group(0))
        if not kept:
            return row
        start = cells[0].start()
        end = cells[-1].end()
        return row[:start] + "".join(kept) + row[end:]

    return _ROW_RE.sub(_row, table_inner)


def _strip_hidden_columns(html: str) -> str:
    def _one(m: re.Match) -> str:
        open_tag, inner, close_tag = m.group(1), m.group(2), m.group(3)
        first = _ROW_RE.search(inner)
        if not first:
            return m.group(0)
        heads = _CELL_RE.findall(first.group(0))
        if not heads:
            return m.group(0)
        drop = _drop_indexes(heads)
        if not drop:
            # still drop body cells that are JSON blobs if header missed
            return m.group(0)
        return open_tag + _strip_table(inner, drop) + close_tag

    return _TABLE_RE.sub(_one, html or "")


def _replace_fleet_header_class_logos(html: str, event_logo: str) -> str:
    if not event_logo or not _is_event_logo(event_logo):
        return html or ""

    def _img(m: re.Match) -> str:
        tag = m.group(0)
        low = tag.lower()
        if "rs-class-row-logo" in low or "rs-club-row" in low:
            return tag
        if "class-header-logo-img" in low or "rs-fleet-title-logo" in low:
            src_m = re.search(r'src="([^"]*)"', tag, flags=re.I)
            if src_m and _is_class_logo(src_m.group(1)):
                tag = re.sub(r'src="[^"]*"', f'src="{event_logo}"', tag, count=1, flags=re.I)
                tag = re.sub(r'alt="[^"]*"', 'alt="Event"', tag, count=1, flags=re.I)
        return tag

    return _IMG_RE.sub(_img, html or "")


def sanitize_public_fleet_html(html: str, event_logo: str = "") -> str:
    """Keep Rank / Class / Sail / Club / Helm / races / Total / Nett only."""
    out = html or ""
    out = _strip_hidden_columns(out)
    out = _replace_fleet_header_class_logos(out, event_logo)
    return out


_LEFT_LOGO_RE = re.compile(
    r'<img[^>]+class="[^"]*regatta-header-left-logo-img[^"]*"[^>]*>',
    re.I,
)
_SRC_RE = re.compile(r'src="([^"]+)"', re.I)
_FLEET_RE = re.compile(
    r'<div class="fleet-section\b[^>]*>[\s\S]*?</table>\s*</div>\s*</div>',
    re.I,
)


def _img_src_with_class(html: str, class_token: str) -> str:
    pat = re.compile(
        rf'<img[^>]+class="[^"]*{re.escape(class_token)}[^"]*"[^>]*>',
        re.I,
    )
    m = pat.search(html or "")
    if not m:
        m = re.search(
            rf'<img src="([^"]+)"[^>]*class="[^"]*{re.escape(class_token)}',
            html or "",
            flags=re.I,
        )
        return (m.group(1) if m else "").strip()
    sm = _SRC_RE.search(m.group(0))
    return (sm.group(1) if sm else "").strip()


def parent_page_left_logo(html: str) -> str:
    """Parent header left src as served — Event Logo or class mark."""
    return _img_src_with_class(html, "regatta-header-left-logo-img")


def parent_page_right_logo(html: str) -> str:
    """Parent header host/club src."""
    return _img_src_with_class(html, "regatta-header-club-logo-img")


def parent_event_logo(html: str) -> str:
    src = parent_page_left_logo(html)
    return src if _is_event_logo(src) else ""


def _div_plain(html: str, class_token: str) -> str:
    m = re.search(
        rf'<div class="[^"]*\b{re.escape(class_token)}\b[^"]*"[^>]*>(.*?)</div>',
        html or "",
        flags=re.I | re.S,
    )
    if not m:
        return ""
    txt = _plain(m.group(1))
    txt = re.sub(r"^Host:\s*", "", txt, flags=re.I).strip()
    return txt


def parent_page_event_name(html: str) -> str:
    return _div_plain(html, "regatta-name")


def parent_page_host(html: str) -> str:
    return _div_plain(html, "host-club")


def parent_page_status_line(html: str) -> str:
    txt = _div_plain(html, "status-line")
    if txt.lower().startswith("results are"):
        return txt
    m = re.search(r"Results are [A-Za-z]+ as at [^<]{6,80}", html or "")
    if m:
        return _plain(m.group(0))
    return txt


def extract_parent_fleet_htmls(html: str) -> list[str]:
    return [m.group(0) for m in _FLEET_RE.finditer(html or "")]


def fetch_parent_page_html(slug: str, timeout: int = 20) -> str:
    rid = str(slug or "").strip().strip("/")
    if not rid:
        return ""
    url = f"https://sailingsa.co.za/regatta/{rid}"
    try:
        req = Request(url, headers={"User-Agent": "SailingSA-parent-truth-pdf", "Cache-Control": "no-cache"})
        with urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", "replace")
    except Exception:
        return ""


def fleets_from_parent_truth(
    slug: str,
    fallback_fleets: Optional[list[dict[str, Any]]] = None,
    left_logo: str = "",
) -> tuple[list[dict[str, Any]], str]:
    """PDF fleets from the parent URL. Event Logo is parent left when it is one."""
    packet = apply_parent_truth_to_pdf(
        slug,
        fleets=fallback_fleets,
        left_logo=left_logo,
    )
    return packet["fleets"], packet["left_logo"]


def apply_parent_truth_to_pdf(
    slug: str,
    *,
    fleets: Optional[list[dict[str, Any]]] = None,
    left_logo: str = "",
    right_logo: str = "",
    event_name: str = "",
    host: str = "",
    status_line: str = "",
    page_html: Optional[str] = None,
) -> dict[str, Any]:
    """Logos + public results from parent. Caller keeps PDF layout/CSS."""
    page = page_html if page_html is not None else fetch_parent_page_html(slug)
    parent_left = parent_page_left_logo(page) if page else ""
    parent_right = parent_page_right_logo(page) if page else ""
    event_logo = parent_event_logo(page) if page else (left_logo if _is_event_logo(left_logo) else "")
    use_left = parent_left or left_logo
    use_right = parent_right or right_logo
    use_name = parent_page_event_name(page) if page else ""
    use_host = parent_page_host(page) if page else ""
    use_status = parent_page_status_line(page) if page else ""
    parent_chunks = extract_parent_fleet_htmls(page) if page else []
    out: list[dict[str, Any]] = []
    if parent_chunks:
        for i, chunk in enumerate(parent_chunks):
            fb = (fleets or [None])[i] if fleets and i < len(fleets) else {}
            html = sanitize_public_fleet_html(chunk, event_logo)
            n_rows = max(len(re.findall(r"<tr\b", html, flags=re.I)) - 1, 0)
            out.append(
                {
                    "class_slug": str((fb or {}).get("class_slug") or "").strip(),
                    "pdf_slug": str((fb or {}).get("pdf_slug") or "").strip(),
                    "html": html,
                    "n_rows": n_rows or int((fb or {}).get("n_rows") or 0),
                }
            )
    if not out:
        for f in fleets or []:
            item = dict(f)
            item["html"] = sanitize_public_fleet_html(item.get("html") or "", event_logo)
            out.append(item)
    return {
        "fleets": out,
        "left_logo": use_left,
        "right_logo": use_right,
        "event_name": use_name or event_name,
        "host": use_host or host,
        "status_line": use_status or status_line,
    }
