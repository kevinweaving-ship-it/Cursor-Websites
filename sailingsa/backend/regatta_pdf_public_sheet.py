"""Public results sheet for stored PDFs.

Parent `/regatta/{id}` is truth. The PDF must take logos and the public
fleet table from that page — never a second backend render that still has
Age / PY / Elapsed JSON / Open class marks CSS-hidden on the URL.
Class PY is admin-only on the parent; the public PDF drops it.
"""
from __future__ import annotations

import re
from typing import Any, Optional
from urllib.parse import unquote
from urllib.request import Request, urlopen

_SITE = "https://sailingsa.co.za"

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


_WC_CODE_RE = re.compile(
    r'<span class="wc-code">\s*([A-Za-z]{2,5})\s*</span>',
    re.I,
)
_CODE_TOKEN_RE = re.compile(
    r"\b(DNC|DNS|DNF|DNR|RET|DSQ|UFD|BFD|DPI|OCS|OCF|NSC|DNE|ZFP|SCP|RDG|TLE)\b",
    re.I,
)
_NUM_CODE_RE = re.compile(
    r"^\(?\s*(\d+(?:\.\d+)?)\s+([A-Za-z]{2,5})\s*\)?$",
    re.I,
)


def _entry_count(html: str) -> int:
    n = len(re.findall(r"<tr\b[^>]*data-result-id=", html or "", flags=re.I))
    if n:
        return n
    m = re.search(r"<tbody\b[^>]*>(.*?)</tbody>", html or "", flags=re.I | re.S)
    if not m:
        return 1
    return max(len(re.findall(r"<tr\b", m.group(1), flags=re.I)), 1)


def pdf_page_orientation(slug: str) -> str:
    """Empty = use the usual table-width rule (landscape if too wide for portrait)."""
    return ""


def _ensure_parent_code_cells(html: str) -> str:
    """Same gold cell as FS Youth: wc-score (points) over wc-code (DNS/DNC).

    Parent already has that when the stored score is '14 DNC'. Code-only cells
    (just DNC) get entries+1 so print CSS can overlay the code under the score.
    """
    pts_default = str(_entry_count(html) + 1)

    def _cell(m: re.Match) -> str:
        tag, attrs, inner = m.group(1), m.group(2), m.group(3)
        if tag.lower() != "td":
            return m.group(0)
        cls = attrs or ""
        if "race-col" not in cls and "code" not in cls:
            return m.group(0)
        if "wc-score" in inner:
            return m.group(0)
        discarded = " disc" in f" {cls}" or "disc" in (inner or "")
        txt = _plain(inner)
        if txt.startswith("(") and txt.endswith(")"):
            discarded = True
            txt = txt[1:-1].strip()
        nm = _NUM_CODE_RE.match(txt)
        if nm:
            points, code = nm.group(1), nm.group(2).upper()
        else:
            cm = _WC_CODE_RE.search(inner) or _CODE_TOKEN_RE.search(txt)
            if not cm:
                return m.group(0)
            code = cm.group(1).upper()
            points = pts_default
        score = f"({points})" if discarded else points
        wrap = "code disc" if discarded else "code"
        return (
            f"<{tag}{attrs}>"
            f'<span class="{wrap}">'
            f'<span class="wc-score">{score}</span>'
            f'<span class="wc-code">{code}</span>'
            f"</span></{tag}>"
        )

    return _CELL_RE.sub(_cell, html or "")


_CLOSED_BADGE_RE = re.compile(
    r'<span\b[^>]*class="[^"]*\bfleet-entries-closed-badge\b[^"]*"[^>]*>[\s\S]*?</span>',
    re.I,
)


def _strip_entries_closed_badge(html: str) -> str:
    """Gold api.py paints this when entries_closed; public Fleet/PDF never asked for it."""
    return _CLOSED_BADGE_RE.sub("", html or "")


def _abs_parent_url(raw: str) -> str:
    s = (raw or "").strip()
    if not s or s.startswith("#") or s.lower().startswith("javascript:") or s.startswith("data:"):
        return s
    if s.startswith("//"):
        return "https:" + s
    if s.startswith("http://") or s.startswith("https://"):
        return s
    if not s.startswith("/"):
        s = "/" + s
    return _SITE.rstrip("/") + s


def absolutize_parent_urls(html: str) -> str:
    """Parent relative /class /sailor /club /boat links must stay clickable in the PDF."""

    def _attr(m: re.Match) -> str:
        return f"{m.group(1)}{_abs_parent_url(m.group(2))}{m.group(3)}"

    out = re.sub(r'(href=["\'])([^"\']+)(["\'])', _attr, html or "", flags=re.I)
    out = re.sub(r'(src=["\'])([^"\']+)(["\'])', _attr, out, flags=re.I)
    out = re.sub(r"""\sloading=["']lazy["']""", "", out, flags=re.I)
    return out


def _mirror_open_fleet_title(html: str) -> str:
    """Parent Dam Bottle JS paints 'Open Fleet' + Event Logo. Gold HTML still says Fleet."""

    def _span(m: re.Match) -> str:
        inner = m.group(2)
        if not re.search(r"(^|>)(\s*)Fleet(\s*)(<|$)", inner):
            return m.group(0)
        if not re.search(r"Event Logo|Dam-Bottle|Open", inner, flags=re.I):
            return m.group(0)
        inner = re.sub(r"(>)(\s*)Fleet(\s*)(<|$)", r"\1\2Open Fleet\3\4", inner, count=1)
        return f"{m.group(1)}{inner}{m.group(3)}"

    return re.sub(
        r'(<span\b[^>]*class="[^"]*fleet-title-with-logo[^"]*"[^>]*>)([\s\S]*?)(</span>)',
        _span,
        html or "",
        count=1,
        flags=re.I,
    )


def sanitize_public_fleet_html(html: str, event_logo: str = "") -> str:
    """Keep Rank / Class / Sail / Club / Helm / races / Total / Nett only."""
    out = html or ""
    out = _strip_entries_closed_badge(out)
    out = _strip_hidden_columns(out)
    out = _ensure_parent_code_cells(out)
    out = _replace_fleet_header_class_logos(out, event_logo)
    out = _mirror_open_fleet_title(out)
    out = absolutize_parent_urls(out)
    return out


def _strip_media_print(css: str) -> str:
    """Drop @media print — that is invented print chrome, not the parent screen."""
    out = []
    i = 0
    src = css or ""
    low = src.lower()
    while True:
        j = low.find("@media print", i)
        if j < 0:
            out.append(src[i:])
            break
        out.append(src[i:j])
        k = src.find("{", j)
        if k < 0:
            break
        depth = 0
        end = k
        for n, ch in enumerate(src[k:], k):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = n + 1
                    break
        i = end
    return "".join(out)


def parent_page_style_html(html: str) -> str:
    """Parent main.css only. Gold inline sheet CSS squashes Fleet into the header card."""
    parts: list[str] = []
    for m in re.finditer(r"<link\b[^>]*rel=[\"']stylesheet[\"'][^>]*>", html or "", flags=re.I):
        parts.append(absolutize_parent_urls(m.group(0)))
    return "\n".join(parts)


def _parent_screen_tokens_css(paper: str) -> str:
    """Parent URL screen tokens only — gold _RESULT_SHEET_CSS + table LinkText.

    Do not invent print fonts, thead greys, or helm blues that are not on the parent.
    """
    return (
        f"@page {{ size: A4 {paper}; margin: 8mm; }}"
        "html,body{background:#ffffff;color:#1a2750;margin:0;padding:0;"
        "font-family:system-ui,sans-serif;"
        "-webkit-print-color-adjust:exact;print-color-adjust:exact}"
        ".site-header,.admin-v10-second-header,.regatta-sa-toolbar,"
        ".midmar-live-media,.print-share-bar,.fleet-entries-closed-badge,"
        ".club-race-step,.dam-bottle-py-math{display:none!important}"
        "body.regatta-page,.regatta-page{border:none!important;box-shadow:none!important;"
        "background:#ffffff!important;max-width:none!important;padding:0!important;margin:0!important}"
        ".regatta-header-wrap{width:100%;margin:0 0 10px 0}"
        ".regatta-header-wrap .header{display:grid;"
        "grid-template-columns:minmax(0,auto) minmax(0,3fr) minmax(0,auto);align-items:center;"
        "column-gap:6px;border:2px solid #1a2750;border-radius:10px;"
        "padding:4px 6px;background:#ffffff;width:100%;box-sizing:border-box}"
        ".regatta-header-main-col{text-align:center}"
        ".regatta-name{font-size:24px;font-weight:bold;margin:0 0 8px 0;color:#1a2750}"
        ".host-club{font-size:18px;color:#1a2750;margin-bottom:8px}"
        ".host-club a,.host-club a:visited{color:#1a2750;font-weight:600;text-decoration:none}"
        ".status-line{font-size:14px;color:#1a2750;margin-top:8px}"
        ".entry-total-line{font-size:12px;font-weight:600;color:#1a2750;margin:1px 0;"
        "display:inline-flex;align-items:center;gap:6px}"
        ".fleet-section{border:none;background:transparent;padding:0;margin:0;width:100%}"
        ".class-header,.class-header--with-logos{display:grid;"
        "grid-template-columns:minmax(0,auto) minmax(0,1fr) minmax(0,auto);align-items:center;"
        "column-gap:8px;border:2px solid #1a2750;border-radius:10px;"
        "padding:10px 12px;background:#ffffff;width:100%;box-sizing:border-box;"
        "margin:0 0 14px 0;font-size:20px;font-weight:bold;color:#1a2750;text-align:center}"
        ".class-header-logo-col,.class-header-club-logo-col,.regatta-header-logo-col,"
        ".regatta-header-club-logo-col{display:flex;align-items:center}"
        ".class-header-club-logo-col,.regatta-header-club-logo-col{justify-content:flex-end}"
        ".class-header-main-col{display:flex;flex-direction:column;align-items:center;"
        "text-align:center;color:#1a2750}"
        ".fleet-title-with-logo{display:inline-flex;align-items:center;gap:6px;"
        "font-size:20px;font-weight:bold;color:#1a2750}"
        ".sailed-line{display:block;margin:10px 0 0 0;font-size:12px;color:#1a2750;"
        "text-align:center}"
        ".class-header-logo-col img,.class-header-club-logo-col img,"
        ".regatta-header-left-logo-img,.regatta-header-club-logo-img{"
        "max-height:104px;max-width:320px;width:auto;height:auto;object-fit:contain;display:block}"
        ".rs-fleet-title-logo{height:1.1em;width:auto;max-height:1.1em;object-fit:contain}"
        ".fleet-section .table-wrapper,.fleet-section .table-container{"
        "display:block;overflow:visible;width:100%;margin:20px 0 0 0;padding:0 2pt;"
        "box-sizing:border-box;border:0}"
        ".fleet-results-table{display:table;width:100%;border-collapse:separate;border-spacing:0;"
        "table-layout:auto;background:#ffffff;margin:0;box-sizing:border-box}"
        ".fleet-results-table th,.fleet-results-table td{padding:8px;vertical-align:middle;"
        "text-align:center;color:#1a2750;border:0;border-right:1px solid #1d294d;"
        "border-bottom:1px solid #1d294d;box-sizing:border-box}"
        ".fleet-results-table thead th{border-top:1px solid #1d294d;background:#e9eefb;"
        "color:#1a2750;font-weight:700}"
        ".fleet-results-table th:first-child,.fleet-results-table td:first-child{"
        "border-left:1px solid #1d294d}"
        ".fleet-results-table th:last-child,.fleet-results-table td:last-child{"
        "border-right:1px solid #1d294d}"
        ".rank-col,.sail-col,.club-col,.helm-col,.nett-col{font-weight:bold}"
        ".fleet-results-table th.race-col,.fleet-results-table td.race-col,"
        ".fleet-results-table th.class-col,.fleet-results-table td.class-col,"
        ".fleet-results-table th.rank-col,.fleet-results-table td.rank-col,"
        ".fleet-results-table th.total-col,.fleet-results-table td.total-col,"
        ".fleet-results-table th.nett-col,.fleet-results-table td.nett-col{"
        "display:table-cell!important;text-align:center}"
        ".fleet-results-table th.helm-col,.fleet-results-table td.helm-col{text-align:left}"
        ".fleet-results-table .rs-class-row-logo{display:inline-block;vertical-align:middle;"
        "height:16px;width:auto;max-height:16px}"
        ".fleet-results-table .rs-club-row-logo-sm,.fleet-results-table .rs-club-with-logo>img{"
        "display:inline-block!important;vertical-align:middle;height:auto;width:auto;"
        "max-height:16px;max-width:28px}"
        ".fleet-results-table .helm-col .wc-sailor-linked a,"
        ".fleet-results-table .helm-col .wc-sailor-linked a:visited,"
        ".fleet-results-table .sail-col .wc-boat-linked a,"
        ".fleet-results-table .sail-col .wc-boat-linked a:visited,"
        ".fleet-results-table .class-col a,.fleet-results-table .class-col a:visited,"
        ".fleet-results-table .club-col a,.fleet-results-table .club-col a:visited{"
        "color:#0000ee;color:LinkText;font-weight:700;text-decoration:underline}"
        ".code{color:#c62828;font-weight:bold}"
        ".dam-bottle-code-stack,.code{display:flex;flex-direction:column;align-items:center;"
        "line-height:1.15;white-space:pre-line}"
        ".wc-score{font-size:1em;font-weight:600;color:#1a2750}"
        ".wc-code{font-size:0.55em;font-weight:700;color:#c62828}"
        "tr.medal-gold,tr.medal-gold td{background-color:#D4AF37}"
        "tr.medal-silver,tr.medal-silver td{background-color:#D7D7D7}"
        "tr.medal-bronze,tr.medal-bronze td{background-color:#CE8946}"
        ".fleet-section,.fleet-section[data-block-id]{visibility:visible!important}"
    )


def build_parent_mirror_document(
    *,
    header_html: str,
    fleets: list[dict[str, Any]],
    orient: str = "landscape",
    event_name: str = "",
    style_html: str = "",
    sheet_url: str = "",
) -> str:
    """Print the parent header + fleet + table. Keep parent links clickable."""
    paper = "landscape" if str(orient or "").lower() != "portrait" else "portrait"
    name = event_name or "Results"
    styles = style_html or '<link rel="stylesheet" href="https://sailingsa.co.za/css/main.css">'
    extra = _parent_screen_tokens_css(paper)
    header = absolutize_parent_urls(_strip_entries_closed_badge(header_html or ""))
    body = "".join(absolutize_parent_urls(f.get("html") or "") for f in fleets or [])
    base = (sheet_url or _SITE).rstrip("/") + "/"
    return (
        '<!DOCTYPE html><html data-dbs-ready="1"><head><meta charset="UTF-8">'
        f'<base href="{base}">'
        f"<title>{name}</title>"
        f"{styles}<style>{extra}</style></head>"
        f'<body class="regatta-page">{header}{body}</body></html>'
    )


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


_MONTHS = {
    "jan": "January",
    "feb": "February",
    "mar": "March",
    "apr": "April",
    "may": "May",
    "jun": "June",
    "jul": "July",
    "aug": "August",
    "sep": "September",
    "oct": "October",
    "nov": "November",
    "dec": "December",
}


def parent_page_event_name(html: str) -> str:
    m = re.search(
        r'<h1 class="[^"]*\bregatta-name\b[^"]*"[^>]*>(.*?)</h1>',
        html or "",
        flags=re.I | re.S,
    )
    if m:
        return _plain(m.group(1))
    return _div_plain(html, "regatta-name")


def parent_page_host(html: str) -> str:
    return _div_plain(html, "host-club")


def _format_as_at(raw: str) -> str:
    s = re.sub(r"\s+", " ", (raw or "").replace("\xa0", " ")).strip()
    m = re.search(
        r"(\d{1,2})\s+([A-Za-z]{3,9})\s+(\d{4})\s+(\d{1,2}:\d{2})",
        s,
    )
    if not m:
        return s
    day, mon, year, hm = m.group(1), m.group(2), m.group(3), m.group(4)
    full = _MONTHS.get(mon[:3].lower(), mon)
    return f"{int(day):02d} {full} {year} at {hm}"


def parent_page_as_at(html: str) -> str:
    m = re.search(
        r'<span class="regatta-status-as-at-date">([^<]+)</span>',
        html or "",
        flags=re.I,
    )
    return _plain(m.group(1)) if m else ""


def parent_page_entries_count(html: str) -> str:
    m = re.search(
        r'<div class="entry-total-line[^"]*"[^>]*>(.*?)</div>',
        html or "",
        flags=re.I | re.S,
    )
    if m:
        nm = re.search(r"(\d+)\s*Entries?", _plain(m.group(1)), flags=re.I)
        if nm:
            return nm.group(1)
    return ""


def parent_page_status_line(html: str) -> str:
    txt = _div_plain(html, "status-line")
    if re.search(r"Results are \w+ as at ", txt, flags=re.I):
        return txt
    word = ""
    m = re.search(r"Results are\s+([A-Za-z]+)", txt, flags=re.I)
    if m:
        word = m.group(1)
    asat = _format_as_at(parent_page_as_at(html))
    if word and asat:
        if " at " not in asat:
            asat = asat
        return f"Results are {word} as at {asat}"
    m2 = re.search(r"Results are [A-Za-z]+ as at [^<]{6,80}", html or "")
    if m2:
        return _plain(m2.group(0))
    return txt


def _extract_div_by_class(html: str, class_token: str) -> str:
    """Match a classed div with balanced inner divs — do not cut at the first close."""
    m = re.search(
        rf'<div\b[^>]*class="[^"]*\b{re.escape(class_token)}\b[^"]*"[^>]*>',
        html or "",
        flags=re.I,
    )
    if not m:
        return ""
    src = html or ""
    i = m.end()
    depth = 1
    low = src.lower()
    while i < len(src) and depth:
        nxt_open = low.find("<div", i)
        nxt_close = low.find("</div>", i)
        if nxt_close < 0:
            break
        if nxt_open >= 0 and nxt_open < nxt_close:
            depth += 1
            i = nxt_open + 4
        else:
            depth -= 1
            i = nxt_close + 6
    return src[m.start() : i].strip()


def extract_parent_header_html(html: str) -> str:
    """Exact parent `.regatta-header-wrap` so the PDF header matches the URL."""
    return _extract_div_by_class(html, "regatta-header-wrap")


def extract_parent_fleet_htmls(html: str) -> list[str]:
    found: list[str] = []
    src = html or ""
    pos = 0
    while True:
        m = re.search(r'<div\b[^>]*class="[^"]*\bfleet-section\b', src[pos:], flags=re.I)
        if not m:
            break
        abs_i = pos + m.start()
        chunk = _extract_div_by_class(src[abs_i:], "fleet-section")
        if not chunk:
            break
        found.append(chunk)
        pos = abs_i + len(chunk)
    return found


def fetch_parent_page_html(slug: str, timeout: int = 20) -> str:
    rid = str(slug or "").strip().strip("/")
    if not rid:
        return ""
    headers = {
        "User-Agent": "SailingSA-parent-truth-pdf",
        "Cache-Control": "no-cache",
        "Host": "sailingsa.co.za",
    }
    for url in (
        f"http://127.0.0.1/regatta/{rid}",
        f"https://sailingsa.co.za/regatta/{rid}",
    ):
        try:
            req = Request(url, headers=headers)
            with urlopen(req, timeout=timeout) as resp:
                html = resp.read().decode("utf-8", "replace")
                if html and "regatta-header-wrap" in html:
                    return html
        except Exception:
            continue
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
    use_header = absolutize_parent_urls(extract_parent_header_html(page) if page else "")
    use_entries = parent_page_entries_count(page) if page else ""
    use_styles = parent_page_style_html(page) if page else ""
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
        "header_html": use_header,
        "entries_count": use_entries,
        "style_html": use_styles,
    }
