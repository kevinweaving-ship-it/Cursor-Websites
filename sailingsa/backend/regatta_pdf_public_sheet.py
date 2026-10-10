"""Public results sheet for stored PDFs.

The parent URL may still carry admin/calc columns (Age, PY, Elapsed JSON,
Corrected JSON) and a superseded Class Logo. Those are not the public page.
Strip them before Chrome prints /results.pdf.
"""
from __future__ import annotations

import re
from urllib.parse import unquote

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
