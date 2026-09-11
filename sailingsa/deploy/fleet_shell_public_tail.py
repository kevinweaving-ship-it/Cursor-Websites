"""Canonical public fleet-shell tails.

Child URLs are ``{parent}-{tail}``. Never publish a truncated block_id tail
(e.g. ``ilca-4-fleet`` for ILCA 4.7) when the class slug is more specific.

There is **no class "Ilca 4"**. ``classes.class_name`` is ``Ilca 4.7``.
``ilca-4`` is only a broken/truncated URL tail alias → ``ilca-4.7-fleet``.

Used by live ``api.py`` (copied in by patch_live_api_auto_fleet_shells.py).
"""
from __future__ import annotations

import re
from typing import Optional

# Truncated / alias block tails → catalogue class slug (no -fleet).
_FLEET_TAIL_CLASS_SLUG_ALIASES = {
    "ilca-4": "ilca-4.7",
    "ilca-4-7": "ilca-4.7",
    "ilca-47": "ilca-4.7",
    "ilca-4-16": "ilca-4.7",
    "laser-4": "ilca-4.7",
    "laser-47": "ilca-4.7",
    "laser-4.7": "ilca-4.7",
    "ilca-6-16": "ilca-6",
}

_MIXED_FLEET_SHELL_TAILS = frozenset(
    {
        "open",
        "overall",
        "fast",
        "slow",
        "mixed",
        "handicap",
    }
)


def class_canonical_slug(class_name: Optional[str]) -> str:
    if not class_name or not isinstance(class_name, str):
        return ""
    s = class_name.strip().lower().replace(" ", "-")
    s = re.sub(r"[^a-z0-9.-]", "", s)
    return s.strip("-") or ""


def block_id_raw_tail(block_id: Optional[str]) -> str:
    bid = str(block_id or "").strip()
    if ":" in bid:
        return bid.split(":", 1)[1].strip()
    return bid


def _date_iso_day(value) -> str:
    if value is None:
        return ""
    if hasattr(value, "date"):
        try:
            value = value.date()
        except Exception:
            pass
    if hasattr(value, "isoformat"):
        try:
            return str(value.isoformat())[:10]
        except Exception:
            pass
    s = str(value).strip()
    return s[:10] if len(s) >= 10 else s


def regatta_is_upcoming_or_happening(end_date=None, start_date=None) -> bool:
    """True while the event has not yet ended (upcoming or in progress)."""
    from datetime import date as date_cls

    day = _date_iso_day(end_date or start_date)
    if not day:
        return False
    try:
        return day >= date_cls.today().isoformat()
    except Exception:
        return False


def fleet_shell_public_tail(
    block_id: Optional[str] = None,
    fleet_label: Optional[str] = None,
    class_canonical: Optional[str] = None,
    class_name: Optional[str] = None,
) -> str:
    """Public child-URL tail for a fleet block.

    Keep mixed/handicap tails (open / fast / slow). Keep a more-specific
    raw tail (optimist-a vs class Optimist). Upgrade truncated tails when
    the class slug is longer (ilca-4 → ilca-4.7-fleet).
    """
    raw = block_id_raw_tail(block_id)
    raw_l = raw.lower().strip("-")
    raw_base = re.sub(r"-fleet$", "", raw_l)
    had_fleet = bool(raw_l.endswith("-fleet"))

    display = (
        str(class_canonical or "").strip()
        or str(class_name or "").strip()
        or str(fleet_label or "").strip()
    )
    display_slug = class_canonical_slug(re.sub(r"(?i)\s+fleet$", "", display)) if display else ""
    mixed = (
        raw_l in _MIXED_FLEET_SHELL_TAILS
        or raw_base in _MIXED_FLEET_SHELL_TAILS
        or display_slug in _MIXED_FLEET_SHELL_TAILS
    )
    if mixed:
        return raw_l or display_slug

    class_slug = display_slug
    alias = _FLEET_TAIL_CLASS_SLUG_ALIASES.get(raw_base)
    if alias and (not class_slug or class_slug in ("ilca", "laser") or alias.startswith(class_slug) or class_slug.startswith(raw_base)):
        class_slug = alias

    if class_slug and raw_base and class_slug != raw_base:
        if class_slug.startswith(raw_base) and len(class_slug) > len(raw_base):
            return f"{class_slug}-fleet" if had_fleet or not raw_l else class_slug
        # raw is more specific than the class (optimist-a vs optimist)
        return raw_l

    if class_slug and not raw_l:
        return f"{class_slug}-fleet"

    return raw_l


def fleet_shell_public_slug(
    parent_regatta_id: Optional[str],
    block_id: Optional[str] = None,
    fleet_label: Optional[str] = None,
    class_canonical: Optional[str] = None,
    class_name: Optional[str] = None,
) -> Optional[str]:
    parent = str(parent_regatta_id or "").strip()
    tail = fleet_shell_public_tail(
        block_id,
        fleet_label=fleet_label,
        class_canonical=class_canonical,
        class_name=class_name,
    )
    if not parent or not tail:
        return None
    return f"{parent}-{tail}"
