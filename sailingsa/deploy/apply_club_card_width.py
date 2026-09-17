#!/usr/bin/env python3
"""Constrain club Upcoming/Past cards to the same 52rem stack as story panels."""
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
MARK = "CLUB_HOME_CARDS_WIDTH_v1"
text = API.read_text()
if MARK in text:
    print("ALREADY")
    raise SystemExit(0)

css_old = (
    '            ".sa-home-regatta-btn{flex:1;min-height:44px;min-width:44px;padding:10px 12px;}"\n'
    '            "}"\n'
    '            "</style>"\n'
)
css_new = (
    '            ".sa-home-regatta-btn{flex:1;min-height:44px;min-width:44px;padding:10px 12px;}"\n'
    '            "}"\n'
    '            ".club-home-cards-stack{width:100%;max-width:52rem;margin:0 auto 1.5rem;box-sizing:border-box;}"\n'
    '            ".club-home-cards-stack .card.stats-section{width:100%;max-width:100%;box-sizing:border-box;}"\n'
    '            ".club-home-cards-stack .sa-home-regatta-card{width:100%;max-width:100%;box-sizing:border-box;}"\n'
    '            "@media (max-width:768px){.club-home-cards-stack{max-width:100%;padding:0;}}"\n'
    '            "</style>"\n'
    "            /* " + MARK + " */\n"
)

ret_old = """        return (
            css
            + _club_home_cards_section_html("Upcoming events", upcoming, club_abbrev, "upcoming", "club-upcoming-cards")
            + _club_home_cards_section_html(
                "Past Events / Regattas Hosted", past, club_abbrev, "past", "club-past-cards"
            )
            + js
        )
"""
ret_new = """        return (
            '<div class="club-home-cards-stack">'
            + css
            + _club_home_cards_section_html("Upcoming events", upcoming, club_abbrev, "upcoming", "club-upcoming-cards")
            + _club_home_cards_section_html(
                "Past Events / Regattas Hosted", past, club_abbrev, "past", "club-past-cards"
            )
            + js
            + "</div>"
        )
"""

missing = []
if css_old not in text:
    missing.append("CSS")
if ret_old not in text:
    missing.append("RET")
if missing:
    raise SystemExit("MISSING:" + ",".join(missing))
API.write_text(text.replace(css_old, css_new, 1).replace(ret_old, ret_new, 1))
print("OK", MARK)
