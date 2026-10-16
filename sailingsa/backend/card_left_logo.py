"""Left Event / class logo for landing and club cards.

Hard rule: the left slot is required. Prefer a named Event Logo, including the
same series from a previous year (Easter Regatta and 9 Hour → HMYC 6&9 Hour).
Fall back to a class logo from the title. Never use a club / host burgee here.
"""
from __future__ import annotations

import html as html_module
import re
from typing import Iterable

# Longest needle wins. Keep TSC / MAC hour races longer than bare "9 hour".
EVENT_LOGO_NEEDLES: tuple[tuple[str, str], ...] = (
    ("easter regatta and 9 hour", "/artwork/Event Logo/HMYC-6hr-9hr-Race.png"),
    ("easter regatta and 9", "/artwork/Event Logo/HMYC-6hr-9hr-Race.png"),
    ("9/6 hour", "/artwork/Event Logo/HMYC-6hr-9hr-Race.png"),
    ("6/9 hour", "/artwork/Event Logo/HMYC-6hr-9hr-Race.png"),
    ("6&9 hour", "/artwork/Event Logo/HMYC-6hr-9hr-Race.png"),
    ("6 & 9 hour", "/artwork/Event Logo/HMYC-6hr-9hr-Race.png"),
    ("9 hour endurance", "/artwork/Event Logo/HMYC-6hr-9hr-Race.png"),
    ("6hr 9hr", "/artwork/Event Logo/HMYC-6hr-9hr-Race.png"),
    ("9hr endurance", "/artwork/Event Logo/HMYC-9hr.png"),
    ("hmyc 9hr", "/artwork/Event Logo/HMYC-9hr.png"),
    ("hmyc 9 hr", "/artwork/Event Logo/HMYC-9hr.png"),
    ("tsc 9hr", "/artwork/Event Logo/TSC-9hr.png"),
    ("tsc 9 hr", "/artwork/Event Logo/TSC-9hr.png"),
    ("9 hour", "/artwork/Event Logo/HMYC-6hr-9hr-Race.png"),
    ("grandslam", "/artwork/Event Logo/HMYC-Grand-Slam.png"),
    ("hmyc grand slam", "/artwork/Event Logo/HMYC-Grand-Slam.png"),
    ("kzn grand slam", "/artwork/Event Logo/KZN-Grand-Slam.png"),
    ("sasnr grand slam", "/artwork/Event Logo/KZN-Grand-Slam.png"),
    ("saskzn grand slam", "/artwork/Event Logo/KZN-Grand-Slam.png"),
    ("grand slam", "/artwork/Event Logo/KZN-Grand-Slam.png"),
    ("ussa", "/artwork/Event Logo/TSL-Team-Sailing.png"),
    ("team sailing league", "/artwork/Event Logo/TSL-Team-Sailing.png"),
    ("team sailing", "/artwork/Event Logo/TSL-Team-Sailing.png"),
    ("intervarsity", "/artwork/Event Logo/TSL-Team-Sailing.png"),
    ("inter varsity", "/artwork/Event Logo/TSL-Team-Sailing.png"),
)

CLASS_LOGO_NEEDLES: tuple[tuple[str, str], ...] = (
    ("hunter", "/artwork/Class Logo/Hunter-19-Class-Logo.png"),
    ("dart 18", "/artwork/Class Logo/Dart-18-Class-Logo.png"),
    ("flying 15", "/artwork/Class Logo/Flying-Fifteen-Class-Logo.png"),
    ("flying fifteen", "/artwork/Class Logo/Flying-Fifteen-Class-Logo.png"),
    ("soling", "/artwork/Class Logo/Soling-Class-Logo.png"),
    ("dabchick", "/artwork/Class Logo/Dabchick-Class-Logo.png"),
    ("optimist", "/artwork/Class Logo/Optimist-Class-Logo.png"),
    ("ilca", "/artwork/Class Logo/ILCA-Class-Logo.png"),
    ("505", "/artwork/Class Logo/505-Class-Logo.png"),
)


def _norm_hay(*parts: str) -> tuple[str, str]:
    raw = " ".join(str(p or "") for p in parts)
    raw = html_module.unescape(raw)
    raw = raw.replace("&amp;", "&").replace("&#039;", "'")
    raw = re.sub(r"\s+", " ", raw).strip().lower()
    flex = raw.replace("-", " ").replace("/", " ").replace("&", " ")
    flex = re.sub(r"\s+", " ", flex).strip()
    return raw, flex


def _best_needle(hay: str, hay_flex: str, rules: Iterable[tuple[str, str]]) -> str:
    best_src = ""
    best_len = -1
    for needle, src in rules:
        n = (needle or "").strip().lower()
        if not n:
            continue
        if n in hay or n in hay_flex:
            if len(n) > best_len:
                best_src = str(src or "").strip()
                best_len = len(n)
    if best_src and not best_src.startswith("/"):
        best_src = "/" + best_src.lstrip("/")
    return best_src


def is_event_logo_path(path: str) -> bool:
    return "/artwork/event logo/" in str(path or "").lower()


def is_class_logo_path(path: str) -> bool:
    return "/artwork/class logo/" in str(path or "").lower()


def is_club_logo_path(path: str) -> bool:
    p = str(path or "").lower()
    return "/club logo/" in p or "/api/club-logo/" in p


def resolve_card_left_logo(
    name: str = "",
    regatta_id: str = "",
    host: str = "",
    current: str = "",
) -> str:
    """Event Logo from this or a prior year of the same series, else class logo.

    `current` is kept when it is already an Event or class path (not a club mark).
    """
    cur = str(current or "").strip()
    if cur and not is_club_logo_path(cur) and (
        is_event_logo_path(cur) or is_class_logo_path(cur)
    ):
        return cur if cur.startswith("/") else "/" + cur.lstrip("/")
    hay, hay_flex = _norm_hay(name, regatta_id, host)
    event = _best_needle(hay, hay_flex, EVENT_LOGO_NEEDLES)
    if event:
        return event
    return _best_needle(hay, hay_flex, CLASS_LOGO_NEEDLES)
