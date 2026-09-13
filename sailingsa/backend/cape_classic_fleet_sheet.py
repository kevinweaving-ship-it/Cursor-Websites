"""Cape Classic 2026-09-13 ZVYC fleet-sheet layout helpers.

Live api.py patches import these so the URL and product PDF stay in lockstep.
Do not apply to other events until this Cape Classic pass is signed off.
"""
from __future__ import annotations

import re
from typing import Iterable, Optional

CAPE_CLASSIC_2026_ZVY_ID = "2026-09-13-zvyc-cape-classic"
_STAFF_TITLES = {"staff", "event staff", "crew"}
_RACE_CODE = r"(DNC|DNS|DNF|DNR|RET|DSQ|UFD|BFD|DPI|OCS|NSC|DNE|ZFP|SCP|RDG|TLE)"
_SPLIT_NUM_CODE = re.compile(
    r'(<span\b[^>]*\bclass="[^"]*\bcode\b[^"]*"[^>]*>)\s*\(?\s*'
    r"(\d+(?:\.\d+)?)\s+"
    + _RACE_CODE
    + r"\s*\)?\s*(</span>)",
    re.I,
)


def is_cape_classic_2026_zvy_event(regatta_id: Optional[str]) -> bool:
    """Parent Event URL and every fleet-child slug for this Cape Classic only."""
    s = str(regatta_id or "").strip().lower()
    return s == CAPE_CLASSIC_2026_ZVY_ID or s.startswith(CAPE_CLASSIC_2026_ZVY_ID + "-")


def unique_row_class_names(rows: Iterable[dict] | None) -> set[str]:
    out: set[str] = set()
    for r in rows or []:
        n = str((r or {}).get("class_name") or "").strip()
        if n:
            out.add(n)
    return out


def fleet_header_title_without_class_dup(
    title: str,
    *,
    unique_classes: set[str],
    has_class_logo: bool,
) -> str:
    """If a fleet/class logo is shown, the logo is the name — title is 'Fleet'.

    Includes mixed Open / offshore: the Open mark already says Open.
    Class column still shows the boat class sailed.
    """
    raw = str(title or "").strip()
    if not raw:
        return raw
    core = re.sub(r"(?i)\s+fleet$", "", raw).strip()
    if core.casefold() in _STAFF_TITLES:
        return raw
    if has_class_logo:
        return "Fleet"
    return raw


def print_header_links_to_event_child(html: str, child_href: str) -> str:
    """Print/PDF: fleet header logo and Fleet title open the event child, not /class/."""
    href = str(child_href or "").strip()
    raw = html or ""
    if not raw or not href:
        return html or ""
    if not href.startswith("/"):
        href = "/" + href

    def _retarget_first_anchor(block: str) -> str:
        return re.sub(
            r'(<a\s[^>]*href=")[^"]*"',
            rf'\1{href}"',
            block,
            count=1,
            flags=re.I,
        )

    raw = re.sub(
        r'<div class="class-header-logo-col">[\s\S]*?</div>',
        lambda m: _retarget_first_anchor(m.group(0)),
        raw,
        count=1,
        flags=re.I,
    )
    raw = re.sub(
        r'<span class="fleet-title-with-logo">[\s\S]*?</span>',
        lambda m: _retarget_first_anchor(m.group(0)),
        raw,
        count=1,
        flags=re.I,
    )
    raw = re.sub(
        r'<div class="fleet-title-row[^"]*">[\s\S]*?</div>',
        lambda m: _retarget_first_anchor(m.group(0)),
        raw,
        count=1,
        flags=re.I,
    )
    return raw


def race_points_and_code_html(
    score_display: str, cell_class: str = "", extra_style: str = ""
) -> str:
    """Split '20 DNC' / '(20 DNC)' so the score stays full size and the code can shrink."""
    raw = str(score_display or "").strip()
    if not raw:
        return ""
    src = raw[1:-1].strip() if raw.startswith("(") and raw.endswith(")") else raw
    m = re.match(rf"^(\d+(?:\.\d+)?)\s+{_RACE_CODE}$", src, re.I)
    if m:
        score, code = m.group(1), m.group(2).upper()
    else:
        m2 = re.match(rf"^{_RACE_CODE}$", src, re.I)
        if not m2:
            return ""
        score, code = "", m2.group(1).upper()
    inner = ""
    if score:
        inner += f'<span class="wc-score">{score}</span>'
    inner += f'<span class="wc-code">{code}</span>'
    cls = str(cell_class or "code").strip() or "code"
    return f'<span class="{cls}"{extra_style}>{inner}</span>'


def split_plain_race_code_spans(html: str) -> str:
    """Rewrite already-rendered '20 DNC' spans into score + code (print/PDF width)."""

    def _sub(m: re.Match[str]) -> str:
        return (
            f'{m.group(1)}<span class="wc-score">{m.group(2)}</span>'
            f'<span class="wc-code">{m.group(3).upper()}</span>{m.group(4)}'
        )

    return _SPLIT_NUM_CODE.sub(_sub, html or "")


def class_link_html_logo_only(class_link_html: str, img_html: str, class_name: str = "") -> str:
    """Put the class logo inside the existing class <a>; drop the duplicated word."""
    link = str(class_link_html or "").strip()
    img = str(img_html or "").strip()
    if not img:
        return class_link_html or ""
    m = re.match(r"(?is)(<a\s[^>]*>).*?(</a>)\s*$", link)
    if m:
        open_a, close_a = m.group(1), m.group(2)
        cn = str(class_name or "").strip()
        if cn and " title=" not in open_a.lower():
            cn_esc = (
                cn.replace("&", "&amp;")
                .replace('"', "&quot;")
                .replace("<", "&lt;")
            )
            open_a = re.sub(r"<a\s", f'<a title="{cn_esc}" ', open_a, count=1, flags=re.I)
        return f'<span class="rs-class-with-logo">{open_a}{img}{close_a}</span>'
    return f'<span class="rs-class-with-logo">{img}</span>'


if __name__ == "__main__":
    assert is_cape_classic_2026_zvy_event("2026-09-13-zvyc-cape-classic-420-fleet")
    assert not is_cape_classic_2026_zvy_event("2026-02-16-hyc-cape-classic")
    assert (
        fleet_header_title_without_class_dup(
            "420 Fleet", unique_classes={"420"}, has_class_logo=True
        )
        == "Fleet"
    )
    assert (
        fleet_header_title_without_class_dup(
            "Open Fleet",
            unique_classes={"Sonnet", "Fireball"},
            has_class_logo=True,
        )
        == "Fleet"
    )
    wrapped = class_link_html_logo_only(
        '<a href="/class/420">420</a>',
        '<img class="rs-class-row-logo" alt="420">',
        "420",
    )
    assert "420</a>" not in wrapped
    assert 'href="/class/420"' in wrapped
    assert "rs-class-row-logo" in wrapped
    child = print_header_links_to_event_child(
        '<div class="class-header-logo-col"><a href="/class/420" class="regatta-header-logo-link"><img></a></div>'
        '<div class="fleet-title-row"><a href="/class/420">Fleet</a></div>'
        '<td class="class-col"><a href="/class/sonnet">x</a></td>',
        "/regatta/2026-09-13-zvyc-cape-classic-420-fleet",
    )
    assert "/class/420" not in child
    assert "/regatta/2026-09-13-zvyc-cape-classic-420-fleet" in child
    assert 'href="/class/sonnet"' in child
    split_cell = race_points_and_code_html("(20 DNC)", "code disc")
    assert 'class="wc-score">20</span>' in split_cell
    assert 'class="wc-code">DNC</span>' in split_cell
    assert "(20" not in split_cell
    rewritten = split_plain_race_code_spans(
        '<td class="code disc race-col"><span class="code disc">(20 DNC)</span></td>'
    )
    assert 'class="wc-score">20</span>' in rewritten
    assert 'class="wc-code">DNC</span>' in rewritten
    print("ok")
