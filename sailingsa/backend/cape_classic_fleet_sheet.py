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
    print("ok")
