#!/usr/bin/env python3
"""Inject Hero 1 / Hero 2 event story cards into live landing HTML.

Slots: #temp-landing-hero-image and #temp-landing-claim-profile-banner.
Does not touch the gold/master header.
"""
from __future__ import annotations

import os
import re
import sys
from datetime import date
from pathlib import Path

import psycopg2
import psycopg2.extras

sys.path.insert(0, "/var/www/sailingsa/sailingsa/backend")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from landing_event_story_cards import (  # noqa: E402
    LANDING_CARD_CSS,
    card_from_row,
    fetch_hero_candidates,
    load_catalogue_index,
    render_card_html,
    select_hero_events,
    wrap_section,
)

WEB_ROOT = Path(os.environ.get("SAILINGS_WEB_ROOT", "/var/www/sailingsa"))
TARGETS = [WEB_ROOT / "index.html", WEB_ROOT / "blank.html"]
CSS_MARK = "/* LANDING_EVENT_CARD_CSS */"
SIGNUP_OLD = "            if (signUpBanner) {"
SIGNUP_NEW = "            if (signUpBanner && !signUpBanner.querySelector('.landing-event-card')) {"

SLOT1 = ("temp-landing-hero-image", "temp-landing-hero-image")
SLOT2 = ("temp-landing-claim-profile-banner", "temp-landing-secondary-image")


def _db():
    url = os.environ.get("DB_URL") or os.environ.get("DATABASE_URL")
    if not url:
        ev = os.popen("systemctl show sailingsa-api -p Environment --value").read()
        for part in ev.split():
            if part.startswith("DB_URL="):
                url = part.split("=", 1)[1]
                break
    if not url:
        raise SystemExit("DB_URL missing")
    return psycopg2.connect(url)


def _replace_section(html: str, section_id: str, new_section: str) -> str:
    pat = re.compile(
        rf'<section\b[^>]*\bid="{re.escape(section_id)}"[^>]*>.*?</section>',
        re.I | re.S,
    )
    found = list(pat.finditer(html))
    if not found:
        raise SystemExit(f"section {section_id} missing")
    # replace first occurrence only; CSS hides duplicates
    m = found[0]
    return html[: m.start()] + new_section + html[m.end() :]


def _ensure_css(html: str) -> str:
    if CSS_MARK in html:
        return html
    needle = ".temp-landing-secondary-image ~ .temp-landing-secondary-image {\n    display: none !important;\n}"
    block = needle + "\n" + CSS_MARK + "\n" + LANDING_CARD_CSS
    if needle in html:
        return html.replace(needle, block, 1)
    # fallback: before gold header comment
    gold = "/* ================================================================\n   GOLD HEADER"
    if gold in html:
        return html.replace(gold, CSS_MARK + "\n" + LANDING_CARD_CSS + "\n" + gold, 1)
    raise SystemExit("could not insert landing card CSS")


def _ensure_signup_guard(html: str) -> str:
    if SIGNUP_NEW in html:
        return html
    if SIGNUP_OLD not in html:
        return html
    return html.replace(SIGNUP_OLD, SIGNUP_NEW, 1)


def build_sections(cur) -> tuple[str, str, dict]:
    today = date.today()
    rows = fetch_hero_candidates(cur, today=today)
    idx = load_catalogue_index()
    h1, h2 = select_hero_events(rows, today=today)
    stats = {"hero1": None, "hero2": None}
    inner1 = inner2 = ""
    aria1 = "Upcoming event"
    aria2 = "Next upcoming event"
    if h1:
        c1 = card_from_row(h1, cur=cur, today=today, idx=idx)
        inner1 = render_card_html(c1, slot=1)
        aria1 = c1["name"]
        stats["hero1"] = {"id": c1["regatta_id"], "entries": c1["entries"], "countdown": c1["countdown"]}
    if h2:
        c2 = card_from_row(h2, cur=cur, today=today, idx=idx)
        inner2 = render_card_html(c2, slot=2)
        aria2 = c2["name"]
        stats["hero2"] = {"id": c2["regatta_id"], "entries": c2["entries"], "countdown": c2["countdown"]}
    s1 = wrap_section(1, inner1, aria1, SLOT1[0], SLOT1[1])
    s2 = wrap_section(2, inner2, aria2, SLOT2[0], SLOT2[1])
    return s1, s2, stats


def patch_file(path: Path, s1: str, s2: str) -> None:
    html = path.read_text(encoding="utf-8", errors="replace")
    html = _ensure_css(html)
    html = _ensure_signup_guard(html)
    html = _replace_section(html, SLOT1[0], s1)
    html = _replace_section(html, SLOT2[0], s2)
    tmp = path.with_suffix(path.suffix + ".hero.tmp")
    tmp.write_text(html, encoding="utf-8")
    tmp.replace(path)
    print("patched", path)


def main() -> int:
    conn = _db()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        s1, s2, stats = build_sections(cur)
        print("stats", stats)
        for path in TARGETS:
            if path.is_file():
                patch_file(path, s1, s2)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
