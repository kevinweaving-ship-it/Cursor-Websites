"""ILCA 4 is the canonical class. Historical 4.7 labels are aliases, not new classes.

Does not create classes or rewrite result rows. Callers match an existing class_id
or send the label to review when zero or several classes match.
"""
from __future__ import annotations

import re

CANONICAL_NAME = "ILCA 4"
# Canonical new asset. Same bytes as the production filename below.
LOGO_FILE = "ILCA-4-Class-Logo.png"
# Existing production path. Maps keep this filename so live references do not move.
LEGACY_LOGO_FILE = "ILCA-4.7-Class-Logo.png"
LOGO_URL = "/artwork/Class Logo/" + LEGACY_LOGO_FILE
# Query string on the fleet-header logo. The path stays LEGACY_LOGO_FILE.
LOGO_CACHE_BUST = "20261004ilca4"
PUBLIC_CLASS_PATH = "/class/ilca-4"

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


def normalise_class_slug(slug: str) -> str:
    """Lowercase a URL slug and turn hyphens into spaces.

    Live /class/ilca-4.7, /class/ilca-47 and /class/ilca-4-7 are the same class
    as /class/ilca-4. Other slugs, including ilca-6 and ilca-7, are unchanged.
    """
    if not slug or not isinstance(slug, str):
        return ""
    norm = slug.strip().lower().replace("-", " ")
    if norm in ("ilca 47", "ilca 4.7", "ilca 4 7"):
        return "ilca 4"
    return norm


def public_class_path(class_name: str) -> str | None:
    """Canonical public path for the ILCA 4 class. None for every other class."""
    if is_ilca4_family_label(class_name):
        return PUBLIC_CLASS_PATH
    return None


def catalogue_class_name_for_fleet(fleet_label: str = "", block_tail: str = "") -> str | None:
    """Catalogue name for an ILCA fleet header.

    Same compact labels and block tails as the live fleet matcher. Returns the
    display name only. Historical fleet URL tails are a separate map and are
    not rewritten here.
    """
    fl = str(fleet_label or "").strip()
    tail_slug = re.sub(r"-fleet$", "", str(block_tail or "").strip().lower().replace(" ", "-"))
    compact = re.sub(r"[^a-z0-9]+", "", fl.lower())
    if compact in ("ilca4", "ilca47", "laser4", "laser47", "laserradial47"):
        return CANONICAL_NAME
    if tail_slug in (
        "ilca-4-16",
        "ilca-4-7",
        "ilca-4.7",
        "ilca-47",
        "ilca-4",
        "laser-4",
        "laser-4.7",
        "laser-47",
    ):
        return CANONICAL_NAME
    if tail_slug in ("ilca-6", "ilca-6-16"):
        return "ILCA 6"
    if tail_slug == "ilca-7":
        return "ILCA 7"
    return None


def artwork_url_with_cache_bust(src_path: str, display_url: str, bust: str = LOGO_CACHE_BUST) -> str:
    """Append the logo cache token after the path is encoded. Leave other URLs alone."""
    if src_path and "?v=" not in src_path and "/artwork/" in str(display_url or "").lower():
        return f"{src_path}?v={bust}"
    return src_path


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
        "ilca47",
        "ilca 4,7",
        "laser 4.7",
        "laser 4",
        "laser4",
        "laser radial 4.7",
    ]
