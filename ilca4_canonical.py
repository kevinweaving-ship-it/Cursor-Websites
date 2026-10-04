"""ILCA 4 is the canonical class. Historical 4.7 labels are aliases, not new classes.

Does not create classes or rewrite result rows. Callers match an existing class_id
or send the label to review when zero or several classes match.
"""
from __future__ import annotations

import re

CANONICAL_NAME = "ILCA 4"
LOGO_FILE = "ILCA-4-Class-Logo.png"
LOGO_URL = "/artwork/Class Logo/" + LOGO_FILE
# Same bytes as LOGO_FILE, kept so older /artwork paths still show the new logo.
LEGACY_LOGO_FILE = "ILCA-4.7-Class-Logo.png"

# Spaced forms after comma→dot and whitespace collapse.
_SPACED = frozenset({
    "ilca 4",
    "ilca 4.7",
    "laser 4",
    "laser 4.7",
    "laser radial 4.7",
})
# Punctuation removed, so ILCA4.7, ILCA 4,7 and ilca-47 share a key.
_COMPACT = frozenset({
    "ilca4",
    "ilca47",
    "laser4",
    "laser47",
    "laserradial47",
})
# Must not be pulled into ILCA 4. Laser Radial without 4.7 is ILCA 6.
_EXCLUDED_SPACED = frozenset({
    "ilca",
    "ilca 6",
    "ilca 7",
    "laser",
    "laser radial",
    "laser standard",
    "radial",
})
_EXCLUDED_COMPACT = frozenset({
    "ilca",
    "ilca6",
    "ilca7",
    "laser",
    "laserradial",
    "laserstandard",
    "radial",
})

HISTORICAL_ALIASES = (
    "ILCA 4.7",
    "Ilca 4.7",
    "ILCA4.7",
    "ILCA 4,7",
    "Laser 4.7",
    "Laser Radial 4.7",
)

# One class row. class_name and alias are both tested. ILCA 6/7 names are not in the lists.
ILCA4_CLASS_LOOKUP_SQL = r"""
SELECT DISTINCT c.class_id, c.class_name
FROM classes c
LEFT JOIN class_aliases a ON a.class_id = c.class_id
WHERE (
    lower(trim(regexp_replace(replace(coalesce(c.class_name, ''), ',', '.'), '\s+', ' ', 'g'))) = ANY(%s)
    OR regexp_replace(lower(trim(regexp_replace(replace(coalesce(c.class_name, ''), ',', '.'), '\s+', ' ', 'g'))), '[^a-z0-9]', '', 'g') = ANY(%s)
    OR lower(trim(regexp_replace(replace(coalesce(a.alias, ''), ',', '.'), '\s+', ' ', 'g'))) = ANY(%s)
    OR regexp_replace(lower(trim(regexp_replace(replace(coalesce(a.alias, ''), ',', '.'), '\s+', ' ', 'g'))), '[^a-z0-9]', '', 'g') = ANY(%s)
)
"""


def spaced_and_compact(raw: str) -> tuple[str, str]:
    if not raw or not isinstance(raw, str):
        return "", ""
    spaced = raw.strip().casefold().replace(",", ".")
    spaced = re.sub(r"\s+", " ", spaced)
    spaced = re.sub(r"\s+fleet$", "", spaced).strip()
    compact = re.sub(r"[^a-z0-9]", "", spaced)
    return spaced, compact


def is_ilca4_family_label(raw: str) -> bool:
    spaced, compact = spaced_and_compact(raw)
    if not spaced and not compact:
        return False
    if spaced in _EXCLUDED_SPACED or compact in _EXCLUDED_COMPACT:
        return False
    return spaced in _SPACED or compact in _COMPACT


def is_ilca4_family_slug(slug: str) -> bool:
    """URL slug such as ilca-4.7, ilca-47, or ilca-4-7. Not ilca-6 or ilca-7."""
    if not slug or not isinstance(slug, str):
        return False
    return is_ilca4_family_label(slug.strip().replace("-", " "))


def lookup_params() -> tuple[list[str], list[str], list[str], list[str]]:
    spaced = sorted(_SPACED)
    compact = sorted(_COMPACT)
    return (spaced, compact, spaced, compact)


def choose_single_class_row(rows) -> tuple[int, str] | None:
    """Return the only (class_id, class_name). None when missing or competing."""
    found: dict[int, str] = {}
    for row in rows or []:
        if isinstance(row, dict):
            cid = row.get("class_id")
            name = row.get("class_name")
        else:
            cid = row[0]
            name = row[1] if len(row) > 1 else ""
        if cid is None:
            continue
        found[int(cid)] = (name or "").strip()
    if len(found) != 1:
        return None
    cid, name = next(iter(found.items()))
    return cid, name


def search_aliases() -> list[str]:
    """Search phrases that must find the same ILCA 4 class. No bare 'radial'."""
    return [
        "ilca 4",
        "ilca 4.7",
        "ilca4",
        "ilca4.7",
        "ilca 4,7",
        "laser 4.7",
        "laser 4",
        "laser4",
        "laser radial 4.7",
    ]
