"""Cape Classic 2026-09-13 ZVYC fleet-sheet layout helpers.

Live api.py patches import these so the URL and product PDF stay in lockstep.
Do not apply to other events until this Cape Classic pass is signed off.
"""
from __future__ import annotations

import re
from typing import Iterable, Optional

CAPE_CLASSIC_2026_ZVY_ID = "2026-09-13-zvyc-cape-classic"
_STAFF_TITLES = {"staff", "event staff", "crew"}


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
    """Single-class fleet with a class logo: the logo is the name, title is 'Fleet'.

    Mixed fleets (Open / offshore) keep the fleet name so the header still reads
    'Open Fleet' while the Class column shows the boat class.
    """
    raw = str(title or "").strip()
    if not raw:
        return raw
    if len(unique_classes) > 1:
        return raw
    core = re.sub(r"(?i)\s+fleet$", "", raw).strip()
    if core.casefold() in _STAFF_TITLES:
        return raw
    if has_class_logo:
        return "Fleet"
    return raw


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
        == "Open Fleet"
    )
    wrapped = class_link_html_logo_only(
        '<a href="/class/420">420</a>',
        '<img class="rs-class-row-logo" alt="420">',
        "420",
    )
    assert "420</a>" not in wrapped
    assert 'href="/class/420"' in wrapped
    assert "rs-class-row-logo" in wrapped
    print("ok")
