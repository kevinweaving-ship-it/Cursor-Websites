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


def parent_page_left_logo(html: str) -> str:
    """Left header img on the parent page — Event Logo when the parent has one."""
    m = _LEFT_LOGO_RE.search(html or "")
    if not m:
        m2 = re.search(
            r'<img src="([^"]+)"[^>]*class="[^"]*regatta-header-left-logo-img',
            html or "",
            flags=re.I,
        )
        src = m2.group(1) if m2 else ""
    else:
        sm = _SRC_RE.search(m.group(0))
        src = sm.group(1) if sm else ""
    src = (src or "").strip()
    return src if _is_event_logo(src) else ""


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
    """PDF fleets + Event Logo from the parent URL. Fallback is sanitized caller HTML."""
    page = fetch_parent_page_html(slug)
    event_logo = parent_page_left_logo(page) or (left_logo if _is_event_logo(left_logo) else "")
    parent_chunks = extract_parent_fleet_htmls(page) if page else []
    out: list[dict[str, Any]] = []
    if parent_chunks:
        for i, chunk in enumerate(parent_chunks):
            fb = (fallback_fleets or [None])[i] if fallback_fleets and i < len(fallback_fleets) else {}
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
        if out:
            return out, event_logo or left_logo
    cleaned = []
    for f in fallback_fleets or []:
        item = dict(f)
        item["html"] = sanitize_public_fleet_html(item.get("html") or "", event_logo or left_logo)
        cleaned.append(item)
    return cleaned, event_logo or left_logo
