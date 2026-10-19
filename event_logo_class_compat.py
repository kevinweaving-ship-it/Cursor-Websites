"""Event Logo vs raced/named classes.

Combined Event Logos (e.g. KZN-Mirror-ILCA-Regionals-Champs.png) may only be
used when every class named in the artwork filename is in the event name or
slug. Sole-class events are class = fleet and fall back to that class logo.
"""
from __future__ import annotations

import re
from typing import Optional, Set

# Class names that may appear in Event Logo filenames.
_EVENT_LOGO_CLASS_TOKENS = (
    "ilca",
    "laser",
    "mirror",
    "optimist",
    "dabchick",
    "505",
    "420",
    "29er",
    "j22",
    "hobie",
    "sonnet",
    "windsurfer",
    "soling",
    "finn",
    "flying 15",
)
_EVENT_LOGO_ILCA_ALIASES = frozenset({"ilca", "laser"})

MIRROR_CLASS_LOGO = "/artwork/Class Logo/Mirror-Class-Logo.png"
KZN_MIRROR_ILCA_EVENT_LOGO = "/artwork/Event Logo/KZN-Mirror-ILCA-Regionals-Champs.png"


def _event_logo_norm_hay(text: str) -> str:
    s = (text or "").lower().replace("_", " ").replace("-", " ").replace("/", " ")
    s = re.sub(r"[^a-z0-9. ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = s.replace("j 22", "j22")
    return s


def _event_logo_class_tokens_in_text(text: str) -> Set[str]:
    hay = f" {_event_logo_norm_hay(text)} "
    found: Set[str] = set()
    for tok in _EVENT_LOGO_CLASS_TOKENS:
        if tok == "flying 15":
            if "flying 15" in hay or "flying15" in hay.replace(" ", ""):
                found.add(tok)
        elif tok == "29er":
            if "29er" in hay:
                found.add(tok)
        elif re.search(rf"\b{re.escape(tok)}\b", hay):
            found.add(tok)
    return found


def event_logo_src_compatible_with_event(src: str, hay_flex: str) -> bool:
    """False when Event/Class artwork names a class the event does not mention."""
    if not (src or "").strip():
        return False
    fname = str(src).rsplit("/", 1)[-1]
    file_classes = _event_logo_class_tokens_in_text(fname)
    if not file_classes:
        return True
    event_classes = _event_logo_class_tokens_in_text(hay_flex)
    event_canon = set(event_classes)
    if event_canon & _EVENT_LOGO_ILCA_ALIASES:
        event_canon |= _EVENT_LOGO_ILCA_ALIASES
    for tok in file_classes:
        if tok in _EVENT_LOGO_ILCA_ALIASES:
            if not (event_canon & _EVENT_LOGO_ILCA_ALIASES):
                return False
        elif tok not in event_canon:
            return False
    return True


def named_event_logo_url(regatta_id: str, event_name: str) -> Optional[str]:
    """Named-event left logo. Mirror-in-name without ILCA → Mirror class logo."""
    rid = str(regatta_id or "").strip().lower()
    en = str(event_name or "").lower()
    hay = f"{en} {rid}".replace("-", " ")
    if "lipton" in rid or "lipton" in en:
        src = "/js/lipton-dev-event-logo.png"
        return src if event_logo_src_compatible_with_event(src, hay) else None
    if "mirror" in hay and "ilca" not in hay and "laser" not in hay:
        return (
            MIRROR_CLASS_LOGO
            if event_logo_src_compatible_with_event(MIRROR_CLASS_LOGO, hay)
            else None
        )
    return None
