#!/usr/bin/env python3
"""Canonical class names from nicknames / abbreviations / typos.

Keep the original label in results.class_original for search.
Display, prediction, and matching use the real class name.
"""
from __future__ import annotations

import re
from difflib import get_close_matches

# nickname / typo / abbrev (lower) -> official display name
# Longer keys first when matching phrases.
EXACT: dict[str, str] = {
    # Optimist
    "opi": "Optimist",
    "opti": "Optimist",
    "oppie": "Optimist",
    "oppies": "Optimist",
    "optmist": "Optimist",
    "optimist": "Optimist",
    "optimist a": "Optimist A",
    "optimist b": "Optimist B",
    "optimist c": "Optimist C",
    "opti a": "Optimist A",
    "opti b": "Optimist B",
    "opti c": "Optimist C",
    "opi a": "Optimist A",
    "opi b": "Optimist B",
    "opi c": "Optimist C",
    "oppie a": "Optimist A",
    "oppie b": "Optimist B",
    # Dabchick
    "dab": "Dabchick",
    "dabs": "Dabchick",
    "dabchick": "Dabchick",
    "dabchicks": "Dabchick",
    # ILCA / Laser
    "laser": "ILCA",
    "laser std": "ILCA 7",
    "laser standard": "ILCA 7",
    "ilca": "ILCA",
    "ilca 7": "ILCA 7",
    "ilca7": "ILCA 7",
    "ilca 6": "ILCA 6",
    "ilca6": "ILCA 6",
    "laser radial": "ILCA 6",
    "radial": "ILCA 6",
    "ilca 4.7": "ILCA 4",
    "ilca 4": "ILCA 4",
    "ilca4": "ILCA 4",
    "ilca47": "ILCA 4",
    "ilcs": "ILCA",
    "ilcs 4": "ILCA 4",
    "ilcs 4.7": "ILCA 4",
    "laser 4.7": "ILCA 4",
    "laser 4": "ILCA 4",
    # Hobie
    "h16": "Hobie 16",
    "hobie16": "Hobie 16",
    "hobie 16": "Hobie 16",
    "h14": "Hobie 14",
    "hobie14": "Hobie 14",
    "hobie 14": "Hobie 14",
    "tiger": "Hobie Tiger",
    "hobie tiger": "Hobie Tiger",
    # Hunter
    "hunter": "Hunter 19",
    "hunters": "Hunter 19",
    "h19": "Hunter 19",
    "hunter 19": "Hunter 19",
    # JPK 1010 (aka JPK 10.10)
    "jpk": "JPK 1010",
    "jpk 1010": "JPK 1010",
    "jpk1010": "JPK 1010",
    "jpk 10.10": "JPK 1010",
    "jpk10.10": "JPK 1010",
    "jpk 10 10": "JPK 1010",
    # Pacer 27
    "pacer": "Pacer 27",
    "pacer 27": "Pacer 27",
    "pacer27": "Pacer 27",
    # Flying 15
    "f15": "Flying 15",
    "flying fifteen": "Flying 15",
    "flying 15": "Flying 15",
    "flying15": "Flying 15",
    "f15 classic": "Flying 15 Classic",
    # Radio
    "df95": "DF95",
    "df 95": "DF95",
    "dragonflite": "DF95",
    "dragonflite 95": "DF95",
    "iom": "IOM",
    # Other dinghies / cats
    "dart": "Dart 18",
    "dart18": "Dart 18",
    "dart 18": "Dart 18",
    "tera": "RS Tera",
    "rs tera": "RS Tera",
    "rstera": "RS Tera",
    "feva": "RS Feva",
    "pico": "Laser Pico",
    "mirror": "Mirror",
    "sonnet": "Sonnet",
    "finn": "Finn",
    "halcat": "Halcat",
    "sprog": "Sprog",
    "420": "420",
    "29er": "29er",
    "49er": "49er",
    "505": "505",
    "gp14": "GP14",
    "gp 14": "GP14",
    "j22": "J22",
    "j 22": "J22",
    "l26": "L26",
    "cape 31": "Cape 31",
    "c31": "Cape 31",
    "stadt 23": "Stadt 23",
    "soling": "Soling",
    "topper": "Topper",
    "topaz": "Topaz",
}

# For search: canonical -> extra query tokens
def search_alias_map() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for nick, canon in EXACT.items():
        key = canon.lower()
        out.setdefault(key, [key])
        if nick not in out[key]:
            out[key].append(nick)
        out.setdefault(nick, [nick, key])
    return out


def _nums(s: str) -> list[str]:
    return re.findall(r"\d+(?:\.\d+)?", s or "")


def _same_hull_number(src: str, dest: str) -> bool:
    """Do not map Stadt 26 → Stadt 23, ILCA 6 → ILCA 7, etc."""
    a, b = _nums(src), _nums(dest)
    if a and b and a != b:
        return False
    return True


def _norm(name: str) -> str:
    s = (name or "").strip().lower()
    s = s.replace("&amp;", "&")
    s = re.sub(r"\s+", " ", s)
    return s


def canonical_class_name(raw: str) -> str:
    """Map nickname/typo/abbrev to official class display name. Unknown → cleaned original."""
    s = _norm(raw)
    if not s:
        return (raw or "").strip()
    if s in EXACT:
        return EXACT[s]
    # "opi-a" / "opti_a"
    s2 = s.replace("-", " ").replace("_", " ")
    s2 = re.sub(r"\s+", " ", s2).strip()
    if s2 in EXACT:
        return EXACT[s2]
    # Leading nickname + fleet letter: "opi a", "opti-b"
    m = re.match(r"^(opi|opti|oppie|oppies|optmist|optimist)\s*[-_]?\s*([abc])\b", s2)
    if m:
        return f"Optimist {m.group(2).upper()}"
    m = re.match(r"^(laser|ilca)\s*[-_]?\s*(4\.7|4|6|7|radial|standard|std)\b", s2)
    if m:
        rig = m.group(2)
        if rig in ("4.7", "4"):
            return "ILCA 4"
        if rig in ("6", "radial"):
            return "ILCA 6"
        return "ILCA 7"
    m = re.match(r"^(f15|flying\s*15|flying\s*fifteen)\b(.*)$", s2)
    if m:
        rest = (m.group(2) or "").strip(" -_")
        return f"Flying 15 {rest}".strip() if rest else "Flying 15"
    # Typos vs known nicknames / official names (skip short tokens: opi/dab/h16 are exact)
    if len(s2) >= 5:
        keys = list(EXACT.keys())
        hit = get_close_matches(s2, keys, n=1, cutoff=0.86)
        if hit and _same_hull_number(s2, hit[0]):
            return EXACT[hit[0]]
        official = list(dict.fromkeys(EXACT.values()))
        hit = get_close_matches(s2, [o.lower() for o in official], n=1, cutoff=0.88)
        if hit and _same_hull_number(s2, hit[0]):
            for o in official:
                if o.lower() == hit[0]:
                    return o
    return (raw or "").strip()


def canonical_class_identifier(raw: str) -> str:
    name = canonical_class_name(raw)
    s = name.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "unknown"
