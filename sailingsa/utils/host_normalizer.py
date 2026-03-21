"""
Single source of truth for host string normalization (association ·/•/| club -> club only).
Used for club resolution and display in events loader and api.

Test cases (canonical):
  "LASA (Laser Association of South Africa) · Club Mykonos" -> "Club Mykonos"
  "29er Class Association · Saldanha Bay Yacht Club" -> "Saldanha Bay Yacht Club"
  "Foo Association • Royal Cape Yacht Club" -> "Royal Cape Yacht Club"
  "Foo | Hermanus Yacht Club" -> "Hermanus Yacht Club"
  ">Details" -> ""
  "Teams" -> ""
  "Club Mykonos" -> "Club Mykonos"
"""
from __future__ import annotations

import re

_HOST_JUNK = frozenset(
    s.strip().lower()
    for s in (
        "",
        "-",
        "—",
        "details",
        ">details",
        "teams",
        "team",
        "online",
        "tbc",
        "unknown",
        "unk",
    )
)
_HOST_SEP_RE = re.compile(r"[\u00b7\u2022|]")  # · • |
_HOST_RESOLUTION_ALIASES = {
    "witbank yacht club": (
        "Witbank Yacht and Sailing Club",
        "Witbank Yacht and Aquatic Club",
        "WYACE",
    ),
    "witbank yacht and sailing club": (
        "Witbank Yacht Club",
        "Witbank Yacht and Aquatic Club",
        "WYACE",
    ),
    "witbank yacht and aquatic club": (
        "Witbank Yacht Club",
        "Witbank Yacht and Sailing Club",
        "WYACE",
    ),
    "wyace": (
        "Witbank Yacht and Aquatic Club",
        "Witbank Yacht Club",
        "Witbank Yacht and Sailing Club",
    ),
}


def normalize_host_for_resolution(raw_host: str) -> str:
    """
    Single source of truth for host string used for club resolution and display.
    - Strip leading ">" and whitespace; reject junk (Details, Teams, TBC, etc.).
    - Split on ·, •, |; trim segments; discard empty/junk; return LAST valid segment if 2+.
    - One valid segment -> return it. Final cleanup: strip trailing punctuation, collapse spaces.
    """
    s = (raw_host or "").strip().lstrip(">").strip()
    if not s:
        return ""
    low = s.lower()
    if low in _HOST_JUNK:
        return ""
    parts = _HOST_SEP_RE.split(s)
    segments = []
    for p in parts:
        t = (p or "").strip().strip(".,;:-").strip()
        if not t:
            continue
        if t.lower() in _HOST_JUNK:
            continue
        segments.append(t)
    if not segments:
        return ""
    out = segments[-1] if len(segments) >= 2 else segments[0]
    out = out.strip(".,;:—-\u00b7\u2022| \t").strip()
    out = re.sub(r"\s+", " ", out).strip()
    return out or ""


def host_resolution_candidates(raw_host: str) -> tuple[str, ...]:
    """
    Return the normalized host plus any known lookup aliases for club resolution.
    This keeps display normalization separate from club-name synonym handling.
    """
    normalized = normalize_host_for_resolution(raw_host)
    if not normalized:
        return tuple()
    out = [normalized]
    seen = {normalized.lower()}
    for alias in _HOST_RESOLUTION_ALIASES.get(normalized.lower(), ()):
        alias_norm = re.sub(r"\s+", " ", (alias or "").strip())
        if not alias_norm:
            continue
        key = alias_norm.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(alias_norm)
    return tuple(out)


# Tiny local test block (run: python3 -m sailingsa.utils.host_normalizer)
if __name__ == "__main__":
    tests = [
        ("LASA (Laser Association of South Africa) · Club Mykonos", "Club Mykonos"),
        ("29er Class Association · Saldanha Bay Yacht Club", "Saldanha Bay Yacht Club"),
        ("Foo Association • Royal Cape Yacht Club", "Royal Cape Yacht Club"),
        ("Foo | Hermanus Yacht Club", "Hermanus Yacht Club"),
        (">Details", ""),
        ("Teams", ""),
        ("Club Mykonos", "Club Mykonos"),
        ("-", ""),
        ("—", ""),
    ]
    for raw, want in tests:
        got = normalize_host_for_resolution(raw)
        ok = "ok" if got == want else f"FAIL want {want!r}"
        print(f"  {raw!r} -> {got!r}  {ok}")
    print("  Witbank candidates ->", host_resolution_candidates("Witbank Yacht Club"))
