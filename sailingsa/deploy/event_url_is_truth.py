"""Event URL is the only source of truth for child slugs and entry totals.

Child path: /regatta/{event_id}/class-{fleet_slug}
Fleet slug follows the name on the Event sheet (class_original / fleet_label),
not an independent {event}-{tail} shell and not the global classes table.
"""
from __future__ import annotations

import re
from typing import Optional


def _norm_slug(value: Optional[str]) -> str:
    s = str(value or "").strip().lower().replace("_", "-")
    s = re.sub(r"(?i)-fleet$", "", s)
    s = re.sub(r"[^a-z0-9.-]", "", s)
    return s.strip("-")


def event_child_slug_from_labels(
    fleet_label: Optional[str] = None,
    class_original: Optional[str] = None,
    class_canonical: Optional[str] = None,
    block_id: Optional[str] = None,
) -> str:
    """Public /class-{slug} tail from what the Event sheet shows."""
    display = (
        str(fleet_label or "").strip()
        or str(class_original or "").strip()
        or str(class_canonical or "").strip()
    )
    display = re.sub(r"(?i)\s+fleet$", "", display).strip()
    if not display and block_id:
        tail = str(block_id).split(":")[-1]
        display = re.sub(r"(?i)-fleet$", "", tail).replace("-", " ")
    s = display.strip().lower().replace(" ", "-")
    s = re.sub(r"[^a-z0-9.-]", "", s).strip("-")
    return s


def event_child_href(parent_regatta_id: str, class_slug: str) -> str:
    parent = str(parent_regatta_id or "").strip()
    slug = _norm_slug(class_slug) or str(class_slug or "").strip()
    if not parent or not slug:
        return ""
    return f"/regatta/{parent}/class-{slug}"


def slug_aliases_for_block(
    fleet_label: Optional[str] = None,
    class_original: Optional[str] = None,
    class_canonical: Optional[str] = None,
    block_id: Optional[str] = None,
    extra_class_names: Optional[list] = None,
) -> set[str]:
    """All URL tails that should resolve to this Event fleet (no leftovers)."""
    out: set[str] = set()
    canon = event_child_slug_from_labels(
        fleet_label, class_original, class_canonical, block_id
    )
    if canon:
        out.add(canon)
    for raw in (fleet_label, class_original, class_canonical):
        n = _norm_slug(raw)
        if n:
            out.add(n)
    if block_id and ":" in str(block_id):
        tail = _norm_slug(str(block_id).split(":", 1)[1])
        if tail:
            out.add(tail)
    for name in extra_class_names or []:
        n = _norm_slug(name)
        if n:
            out.add(n)
    return out
