"""Left Event / class logo for landing and club cards.

Hard rule: the large left slot is required and must match the All Regattas
list card for the same event. Prefer a named Event Logo (same needles as
live api.py `_CLUB_EVENT_LOGO_RULES`), else sole class=fleet logo.
Never use a club / host burgee or the default Sailing SA mark.
"""
from __future__ import annotations

import html as html_module
import sys
from pathlib import Path as _Path
import re
from typing import Iterable

_HERE = _Path(__file__).resolve().parent
for _p in (_HERE, _HERE.parent, _HERE.parent.parent, _Path("/var/www/sailingsa")):
    _s = str(_p)
    if _s not in sys.path:
        sys.path.append(_s)

try:
    from event_logo_class_compat import (
        event_logo_src_compatible_with_event,
        named_event_logo_url,
    )
except Exception:  # pragma: no cover
    def event_logo_src_compatible_with_event(src: str, hay_flex: str) -> bool:
        return bool(src)

    def named_event_logo_url(regatta_id: str, event_name: str):
        return None

# Longest needle wins. Same named Event Logos as the regatta list (api.py).
EVENT_LOGO_NEEDLES: tuple[tuple[str, str], ...] = (
    ('2026 10 17 mac tsl wc team sailing', '/artwork/Event Logo/TSL-Team-Sailing.png'),
    ('team sailing league', '/artwork/Event Logo/TSL-Team-Sailing.png'),
    ('team sailing', '/artwork/Event Logo/TSL-Team-Sailing.png'),
    ('midmar cup', '/artwork/Event Logo/Midmar-Cup-Event.jpg'),
    ('the midmar cup', '/artwork/Event Logo/Midmar-Cup-Event.jpg'),
    ('leopard challenge', '/artwork/Class Logo/Hunter-19-Class-Logo.png'),
    ('lappard challenge', '/artwork/Class Logo/Hunter-19-Class-Logo.png'),
    ('cape classic', '/artwork/Event Logo/Cape-Classic-Series.png'),
    ('youth national championship', '/artwork/Event Logo/Youth-Nationals-Logo.png'),
    ('youth nationals', '/artwork/Event Logo/Youth-Nationals-Logo.png'),
    ('youth national', '/artwork/Event Logo/Youth-Nationals-Logo.png'),
    ('sa sailing youth', '/artwork/Event Logo/Youth-Nationals-Logo.png'),
    ('sonnet national', '/artwork/Event Logo/Sonnet-Nationals-2025.jpg'),
    ('overberg', '/artwork/Event Logo/Overberg-Regional-Champs.png'),
    ('wc dinghy', '/artwork/Event Logo/Western-Cape-Dinghy-Champs.png'),
    ('western cape dinghy', '/artwork/Event Logo/Western-Cape-Dinghy-Champs.png'),
    ('dinghy western cape', '/artwork/Event Logo/Western-Cape-Dinghy-Champs.png'),
    ('w. cape championships', '/artwork/Event Logo/Western-Cape-Dinghy-Champs.png'),
    ('w cape championships', '/artwork/Event Logo/Western-Cape-Dinghy-Champs.png'),
    ('wcapedinghychamps', '/artwork/Event Logo/Western-Cape-Dinghy-Champs.png'),
    ('dinghy champs', '/artwork/Event Logo/Western-Cape-Dinghy-Champs.png'),
    ('dinghy classes', '/artwork/Event Logo/Western-Cape-Dinghy-Champs.png'),
    ('wc extra', '/artwork/Event Logo/Western-Cape-Dinghy-Champs.png'),
    ('extra regionals', '/artwork/Event Logo/Western-Cape-Dinghy-Champs.png'),
    ('extra western cape', '/artwork/Event Logo/Western-Cape-Dinghy-Champs.png'),
    ('wc champs extra', '/artwork/Event Logo/Western-Cape-Dinghy-Champs.png'),
    ('champs extra', '/artwork/Event Logo/Western-Cape-Dinghy-Champs.png'),
    ('sa sailing wc youth', '/artwork/Event Logo/SA-Sailing-WC-Youth-Regatta.png'),
    ('western cape youth', '/artwork/Event Logo/SA-Sailing-WC-Youth-Regatta.png'),
    ('wc youth', '/artwork/Event Logo/SA-Sailing-WC-Youth-Regatta.png'),
    ('sas western cape youth', '/artwork/Event Logo/SA-Sailing-WC-Youth-Regatta.png'),
    ('lipton', '/artwork/Event Logo/Lipton-Challenge-Cup-2025.png'),
    ('double cape', '/artwork/Event Logo/Double-Cape-Race-2025.png'),
    ('gimco', '/artwork/Event Logo/Gimco-Regatta.png'),
    ('west coast offshore', '/artwork/Event Logo/West-Coast-Offshore.png'),
    ('west coast race', '/artwork/Event Logo/West-Coast-Offshore.png'),
    ('seajet', '/artwork/Event Logo/Seajet-West-Coast-Offshore.png'),
    ('canyon cup', '/artwork/Event Logo/Canyon-Cup-Offshore.png'),
    ('ullman', '/artwork/Event Logo/Ullman-Sails-Woman-Series.png'),
    ('j22 nationals', '/artwork/Event Logo/J22-Nationals.png'),
    ('north sails j22', '/artwork/Event Logo/J22-Nationals.png'),
    ('j22 champs', '/artwork/Event Logo/J22-Nationals.png'),
    ('j22 championships', '/artwork/Event Logo/J22-Nationals.png'),
    ('robben island', '/artwork/Event Logo/Round-Robben-Island-Race.png'),
    ('zhik', '/artwork/Event Logo/Zhik-Double-Handed-Series.png'),
    ('tuzi', '/artwork/Event Logo/Tuzi-Tekwini-Ocean-Race.png'),
    ('tuzitekwini', '/artwork/Event Logo/Tuzi-Tekwini-Ocean-Race.png'),
    ('admirals', '/artwork/Event Logo/Admirals-Regatta.png'),
    ('mykonos', '/artwork/Event Logo/Mykonos-Offshore.png'),
    ('cape point challenge', '/artwork/Event Logo/Cape-Point-Challenge.png'),
    ('tour de vlei', '/artwork/Event Logo/Tour-de-Vlei.jpg'),
    ('vasco', '/artwork/Event Logo/Vasco-da-Gama-Ocean-Race.png'),
    ('diamond coast', '/artwork/Event Logo/Diamond-Coast-Race.png'),
    ('port owen', '/artwork/Event Logo/Port-Owen-River-Race.png'),
    ('azalea', '/artwork/Event Logo/Azalea-Trophy.png'),
    ('brass monkey', '/artwork/Event Logo/Brass-Monkey-Sailing.png'),
    ('vulcan', '/artwork/Event Logo/Vulcan-Challenge-2026.png'),
    ('king of the vaal', '/artwork/Event Logo/King-of-the-Vaal.png'),
    ('frank lenz', '/artwork/Event Logo/Sailing-Legend-Frank-Lenz-Race.png'),
    ('shanes gaul', '/artwork/Event Logo/Shanes-Gaul-Regatta-2026.png'),
    ('von klemperer', '/artwork/Event Logo/Von-Klemperer-Regatta.png'),
    ('intasure', '/artwork/Event Logo/Intasure-Logo.png'),
    ('spring regatta', '/artwork/Event Logo/Intasure-Logo.png'),
    ('congella', '/artwork/Event Logo/Congella-Cup.png'),
    ('commodore', '/artwork/Event Logo/MSC.png'),
    ('commodores cup', '/artwork/Event Logo/MSC.png'),
    ('nks grand prix', '/artwork/Event Logo/NKS-Grand-Prix.png'),
    ('grand prix', '/artwork/Event Logo/NKS-Grand-Prix.png'),
    ('mod winter', '/artwork/Event Logo/MOD-Winter-Series.png'),
    ('winter series', '/artwork/Event Logo/MOD-Winter-Series.png'),
    ('frank-lenz', '/artwork/Event Logo/Sailing-Legend-Frank-Lenz-Race.png'),
    ('6&9 hour', '/artwork/Event Logo/HMYC-6hr-9hr-Race.png'),
    ('6&9', '/artwork/Event Logo/HMYC-6hr-9hr-Race.png'),
    ('ilca masters', '/artwork/Class Logo/ILCA-Class-Logo.png'),
    ('gauteng ilca', '/artwork/Class Logo/ILCA-Class-Logo.png'),
    ('msc week', '/artwork/Event Logo/MSC-Week-2024.png'),
    ('msc l26', '/artwork/Event Logo/MSC-Week-2024.png'),
    ('kzn grand slam', '/artwork/Event Logo/KZN-Grand-Slam.png'),
    ('sasnr grand slam', '/artwork/Event Logo/KZN-Grand-Slam.png'),
    ('grand slam', '/artwork/Event Logo/KZN-Grand-Slam.png'),
    ('hmyc grand slam', '/artwork/Event Logo/HMYC-Grand-Slam.png'),
    ('hmyc autumn', '/artwork/Event Logo/HMYC-Autumn-Series.png'),
    ('hmyc memorial', '/artwork/Event Logo/HMYC-Memorial-Series.png'),
    ('hmyc 9hr', '/artwork/Event Logo/HMYC-9hr.png'),
    ('hmyc 6hr', '/artwork/Event Logo/HMYC-6hr-9hr-Race.png'),
    ('twilight series', '/artwork/Event Logo/Twilight-Series.png'),
    ('triple crown', '/artwork/Event Logo/Triple-Crown.png'),
    ('tsc 9hr', '/artwork/Event Logo/TSC-9hr.png'),
    ('mac 24', '/artwork/Event Logo/MAC-24-Hour-Challenge.png'),
    ('mac 12', '/artwork/Event Logo/MAC-12-Hour-Challenge.png'),
    ('24-hour challenge', '/artwork/Event Logo/MAC-24-Hour-Challenge.png'),
    ('12-hour challenge', '/artwork/Event Logo/MAC-12-Hour-Challenge.png'),
    ('macs shipping', '/artwork/Event Logo/MACS-Shipping.png'),
    ('formula 1 national', '/artwork/Event Logo/Formula-1-Nationals.png'),
    ('formula one national', '/artwork/Event Logo/Formula-1-Nationals.png'),
    ('formula-one-nationals', '/artwork/Event Logo/Formula-1-Nationals.png'),
    ('dolphin', '/artwork/Event Logo/Dolphin-Finn-Tiger-Cup.png'),
    ('finn tiger', '/artwork/Event Logo/Dolphin-Finn-Tiger-Cup.png'),
    ('flying 15 national', '/artwork/Event Logo/Soling-Flying-15-National-Championships.png'),
    ('gauteng dinghy', '/artwork/Event Logo/Gauteng-Province-Regionals-2025.png'),
    ('gauteng province regional', '/artwork/Event Logo/Gauteng-Province-Regionals-2025.png'),
    ('gauteng regional', '/artwork/Event Logo/Gauteng-Province-Regionals-2025.png'),
    ('mpumalanga', '/artwork/Event Logo/Mpumalanga-Regional-Champs-2025.jpg'),
    ('free state youth', '/artwork/Event Logo/Free-State-Youth-Provincial-Champs-2025.png'),
    ('freestate dinghy', '/artwork/Event Logo/Dinghy-Provincials-Championship.png'),
    ('dinghy provincial', '/artwork/Event Logo/Dinghy-Provincials-Championship.png'),
    ('kzn regionals', '/artwork/Event Logo/KZN-Regionals-2025.png'),
    ('kzn mirror ilca', '/artwork/Event Logo/KZN-Mirror-ILCA-Regionals-Champs.png'),
    ('ilca regional', '/artwork/Event Logo/KZN-Mirror-ILCA-Regionals-Champs.png'),
    ('kzn ilca', '/artwork/Event Logo/KZN-Mirror-ILCA-Regionals-Champs.png'),
    ('zvyc interschool', '/artwork/Event Logo/Schools-Dinghy-Sailing.png'),
    ('schools dinghy', '/artwork/Event Logo/Schools-Dinghy-Sailing.png'),
    ('northern region interschool', '/artwork/Event Logo/Northern-Region-Interschools.png'),
    ('northern region keelboat', '/artwork/Event Logo/Northern-Region-Keelboat.png'),
    ('interschool gauteng', '/artwork/Event Logo/Interschool-Gauteng-Regional-Championships.png'),
    ('ec regional', '/artwork/Event Logo/SAS-EC-Champs-Eastern-Cape.png'),
    ('eastern cape', '/artwork/Event Logo/SAS-EC-Champs-Eastern-Cape.png'),
    ('sas-ec', '/artwork/Event Logo/SAS-EC-Champs-Eastern-Cape.png'),
    ('sas ec', '/artwork/Event Logo/SAS-EC-Champs-Eastern-Cape.png'),
    ('ec champs', '/artwork/Event Logo/SAS-EC-Champs-Eastern-Cape.png'),
    ('gauteng provincial', '/artwork/Event Logo/Gauteng-Province-Regionals-2025.png'),
    ('gauteng provincials', '/artwork/Event Logo/Gauteng-Province-Regionals-2025.png'),
    ('club class champ', '/artwork/Event Logo/Club-Championships.png'),
    ('hobie wc', '/artwork/Event Logo/Hobie-WC-Regionals.png'),
    ('iom national', '/artwork/Event Logo/IOM-Sailboat.png'),
    ('iom nr', '/artwork/Event Logo/DF95-IOM-Regionals-Radio-Sailing.png'),
    ('df95 & iom', '/artwork/Event Logo/DF95-IOM-Regionals-Radio-Sailing.png'),
    ('fbyc easter', '/artwork/Event Logo/FBYC-Easter-2026.png'),
    ('psc charity', '/artwork/Event Logo/PSC-Charity-Regatta.png'),
    ('stilbaai club challenge', '/artwork/Event Logo/Stilbaai-Club-Challenge.png'),
    ('zyc club fun', '/artwork/Event Logo/ZYC-Club-Fun-Race.png'),
    ('round the island', '/artwork/Event Logo/Round-the-Island-Regatta.png'),
    ('marriott', '/artwork/Event Logo/Marriott-IMCA-Worlds-2025.png'),
    ('imca world', '/artwork/Event Logo/Marriott-IMCA-Worlds-2025.png'),
    ('75th sa sailing', '/artwork/Event Logo/75th-SA-Sailing-Dart-Dragonfly-Halcat-Hobie14-Nationals.png'),
    ('kyc interclub', '/artwork/Event Logo/KYC-Interclub.png'),
    ('knysna yacht club interclub', '/artwork/Event Logo/Knysna-Yacht-Club-Interclub.png'),
    ('mbsc interclub', '/artwork/Event Logo/Interclub.png'),
    ('interclub', '/artwork/Event Logo/Interclub.png'),
    ('club champs', '/artwork/Event Logo/Club-Championships.png'),
    ('club championship', '/artwork/Event Logo/Club-Championships.png'),
    ('easter regatta and 9 hour', '/artwork/Event Logo/HMYC-6hr-9hr-Race.png'),
    ('easter regatta and 9', '/artwork/Event Logo/HMYC-6hr-9hr-Race.png'),
    ('9/6 hour', '/artwork/Event Logo/HMYC-6hr-9hr-Race.png'),
    ('6/9 hour', '/artwork/Event Logo/HMYC-6hr-9hr-Race.png'),
    ('6 & 9 hour', '/artwork/Event Logo/HMYC-6hr-9hr-Race.png'),
    ('9 hour endurance', '/artwork/Event Logo/HMYC-6hr-9hr-Race.png'),
    ('6hr 9hr', '/artwork/Event Logo/HMYC-6hr-9hr-Race.png'),
    ('9hr endurance', '/artwork/Event Logo/HMYC-9hr.png'),
    ('hmyc 9 hr', '/artwork/Event Logo/HMYC-9hr.png'),
    ('tsc 9 hr', '/artwork/Event Logo/TSC-9hr.png'),
    ('9 hour', '/artwork/Event Logo/HMYC-6hr-9hr-Race.png'),
    ('grandslam', '/artwork/Event Logo/HMYC-Grand-Slam.png'),
    ('saskzn grand slam', '/artwork/Event Logo/KZN-Grand-Slam.png'),
    ('ussa', '/artwork/Event Logo/TSL-Team-Sailing.png'),
    ('intervarsity', '/artwork/Event Logo/TSL-Team-Sailing.png'),
    ('inter varsity', '/artwork/Event Logo/TSL-Team-Sailing.png'),
)

CLASS_LOGO_NEEDLES: tuple[tuple[str, str], ...] = (
    ("hunter", "/artwork/Class Logo/Hunter-19-Class-Logo.png"),
    ("leopard", "/artwork/Class Logo/Hunter-19-Class-Logo.png"),
    ("lappard", "/artwork/Class Logo/Hunter-19-Class-Logo.png"),
    ("dart 18", "/artwork/Class Logo/Dart-18-Class-Logo.png"),
    ("flying 15", "/artwork/Class Logo/Flying-Fifteen-Class-Logo.png"),
    ("flying fifteen", "/artwork/Class Logo/Flying-Fifteen-Class-Logo.png"),
    ("soling", "/artwork/Class Logo/Soling-Class-Logo.png"),
    ("dabchick", "/artwork/Class Logo/Dabchick-Class-Logo.png"),
    ("optimist", "/artwork/Class Logo/Optimist-Class-Logo.png"),
    ("ilca", "/artwork/Class Logo/ILCA-Class-Logo.png"),
    ("505", "/artwork/Class Logo/505-Class-Logo.png"),
    ("420", "/artwork/Class Logo/420-Class-Logo.png"),
    ("mirror", "/artwork/Class Logo/Mirror-Class-Logo.png"),
    ("29er", "/artwork/Class Logo/29er-Class-Logo.png"),
    ("df95", "/artwork/Class Logo/DF95-Class-Logo.png"),
    ("windsurfer", "/artwork/Class Logo/Windsurfer-LT-Class-Logo.png"),
    ("j22", "/artwork/Class Logo/J22-Class-Logo.png"),
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
                if not event_logo_src_compatible_with_event(src, hay_flex):
                    continue
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


def is_default_sailingsa_logo(path: str) -> bool:
    n = str(path or "").lower()
    return "sailingsa-logo" in n or "/assets/logos/sailingsa" in n


def is_landing_event_slot_logo(path: str) -> bool:
    s = str(path or "").strip()
    if not s or is_default_sailingsa_logo(s) or is_club_logo_path(s):
        return False
    return is_event_logo_path(s) or is_class_logo_path(s)


def preferred_event_slot_logo(
    name: str = "",
    regatta_id: str = "",
    host: str = "",
    event_logo: str = "",
    series_logo: str = "",
    class_logo: str = "",
    sole_fleet: bool = True,
    current: str = "",
) -> str:
    """Same rule as landing list `preferredEventSlotLogo`.

    Named Event Logo if it exists, else sole class=fleet logo.
    """
    ev = str(event_logo or "").strip()
    if ev and is_landing_event_slot_logo(ev):
        return ev if ev.startswith("/") else "/" + ev.lstrip("/")
    series = str(series_logo or "").strip()
    if series and is_event_logo_path(series) and is_landing_event_slot_logo(series):
        return series if series.startswith("/") else "/" + series.lstrip("/")
    resolved = resolve_card_left_logo(name, regatta_id, host, current=current)
    if resolved and is_event_logo_path(resolved):
        return resolved
    cls = str(class_logo or "").strip()
    if cls and is_class_logo_path(cls) and sole_fleet and is_landing_event_slot_logo(cls):
        return cls if cls.startswith("/") else "/" + cls.lstrip("/")
    if resolved and is_class_logo_path(resolved) and sole_fleet:
        return resolved
    return ""


def resolve_card_left_logo(
    name: str = "",
    regatta_id: str = "",
    host: str = "",
    current: str = "",
) -> str:
    """Event Logo from this or a prior year of the same series, else class logo.

    `current` is kept when it is already an Event or class path (not a club mark).
    """
    hay, hay_flex = _norm_hay(name, regatta_id, host)
    named = named_event_logo_url(regatta_id, name) or ""
    if named:
        named = str(named).strip()
        if named and not named.startswith("/") and not named.startswith("http"):
            named = "/" + named.lstrip("/")
        # Mirror-only class=fleet and Midmar named Event Logo win over generic regionals.
        if is_class_logo_path(named) or "midmar-cup-event" in named.lower():
            if event_logo_src_compatible_with_event(named, hay_flex):
                return named
    cur = str(current or "").strip()
    if cur and is_landing_event_slot_logo(cur):
        return cur if cur.startswith("/") else "/" + cur.lstrip("/")
    event = _best_needle(hay, hay_flex, EVENT_LOGO_NEEDLES)
    if event:
        return event
    return _best_needle(hay, hay_flex, CLASS_LOGO_NEEDLES)
