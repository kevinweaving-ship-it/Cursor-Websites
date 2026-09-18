#!/usr/bin/env python3
"""Inject Hero 1 / Hero 2 event story cards into live landing HTML.

Slots: #temp-landing-hero-image and #landing-event-hero-2.
Never use #temp-landing-claim-profile-banner for Hero 2 — auth JS hides that id.
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
HIDECLAIM_OLD = """  function hideClaim(){
    var claim=document.getElementById('temp-landing-claim-profile-banner');
    if(claim) claim.style.display='none';
  }"""
HIDECLAIM_NEW = """  function hideClaim(){
    var claim=document.getElementById('temp-landing-claim-profile-banner');
    if(claim && !claim.querySelector('.landing-event-card')) claim.style.display='none';
  }"""
DEV1_INSERT_OLD = """      var claim=document.getElementById('temp-landing-claim-profile-banner');
      if(claim&&claim.parentNode) claim.parentNode.insertBefore(slot, claim);"""
DEV1_INSERT_NEW = """      var claim=document.getElementById('temp-landing-claim-profile-banner');
      if(claim&&claim.parentNode){
        if(claim.querySelector('.landing-event-card')){
          if(claim.nextSibling) claim.parentNode.insertBefore(slot, claim.nextSibling);
          else claim.parentNode.appendChild(slot);
        } else {
          claim.parentNode.insertBefore(slot, claim);
        }
      }"""

SLOT1 = ("temp-landing-hero-image", "temp-landing-hero-image")
SLOT2 = ("landing-event-hero-2", "temp-landing-secondary-image")
CLAIM_ID = "temp-landing-claim-profile-banner"
CLAIM_RESTORE = (
    '<section id="temp-landing-claim-profile-banner" class="temp-landing-secondary-image" '
    'aria-label="Claim your SailingSA profile banner">\n'
    '    <img src="assets/temp-landing-claim-profile-banner.png" alt="Claim your Sailing profile banner">\n'
    "</section>"
)


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
    m = found[0]
    return html[: m.start()] + new_section + html[m.end() :]


def _upsert_after(html: str, section_id: str, new_section: str, after_id: str) -> str:
    pat = re.compile(
        rf'<section\b[^>]*\bid="{re.escape(section_id)}"[^>]*>.*?</section>',
        re.I | re.S,
    )
    found = list(pat.finditer(html))
    if found:
        m = found[0]
        return html[: m.start()] + new_section + html[m.end() :]
    after = re.compile(
        rf'<section\b[^>]*\bid="{re.escape(after_id)}"[^>]*>.*?</section>',
        re.I | re.S,
    )
    m = after.search(html)
    if not m:
        raise SystemExit(f"anchor section {after_id} missing")
    return html[: m.end()] + "\n" + new_section + html[m.end() :]


def _detach_hero2_from_claim(html: str) -> str:
    """Claim banner must not contain the 420 card — hideClaim() hides that id."""
    pat = re.compile(
        rf'<section\b[^>]*\bid="{re.escape(CLAIM_ID)}"[^>]*>.*?</section>',
        re.I | re.S,
    )
    m = pat.search(html)
    if not m:
        return html
    body = m.group(0)
    if "landing-event-card" in body or "LANDING_EVENT_CARD_BEGIN slot=2" in body:
        return html[: m.start()] + CLAIM_RESTORE + html[m.end() :]
    return html


def _ensure_css(html: str) -> str:
    gold = "/* ================================================================\n   GOLD HEADER"
    block = CSS_MARK + "\n" + LANDING_CARD_CSS + "\n"
    if CSS_MARK in html:
        pat = re.compile(re.escape(CSS_MARK) + r".*?(?=\/\* =+\s*\n\s*GOLD HEADER)", re.S)
        if pat.search(html):
            return pat.sub(block, html, count=1)
        start = html.find(CSS_MARK)
        end = html.find(gold, start)
        if end > start:
            return html[:start] + block + html[end:]
        return html
    needle = ".temp-landing-secondary-image ~ .temp-landing-secondary-image {\n    display: none !important;\n}"
    if needle in html:
        return html.replace(needle, needle + "\n" + block, 1)
    if gold in html:
        return html.replace(gold, block + gold, 1)
    raise SystemExit("could not insert landing card CSS")


def _ensure_signup_guard(html: str) -> str:
    if SIGNUP_NEW in html:
        pass
    elif SIGNUP_OLD in html:
        html = html.replace(SIGNUP_OLD, SIGNUP_NEW, 1)
    insert_new = (
        "var h2=document.getElementById('landing-event-hero-2');\n"
        "      var claim=document.getElementById('temp-landing-claim-profile-banner');\n"
        "      if(h2&&h2.parentNode){\n"
        "        if(h2.nextSibling) h2.parentNode.insertBefore(slot, h2.nextSibling);\n"
        "        else h2.parentNode.appendChild(slot);\n"
        "      } else if(claim&&claim.parentNode) claim.parentNode.insertBefore(slot, claim);"
    )
    if "getElementById('landing-event-hero-2')" not in html:
        html = re.sub(
            r"var claim=document\.getElementById\('temp-landing-claim-profile-banner'\);\s*if\(claim&&claim\.parentNode\)(?: claim\.parentNode\.insertBefore\(slot, claim\);|\{[\s\S]*?else \{\s*claim\.parentNode\.insertBefore\(slot, claim\);\s*\}\s*\})",
            insert_new,
            html,
            count=1,
        )
    return html


def _place_profile_after_heroes(html: str) -> str:
    """Logged-in sailor profile must not sit on / hide Hero 2."""
    html = re.sub(r'\s*<div id="landing-dev1-home"></div>', "", html)
    marker = "<!-- LANDING_EVENT_CARD_END slot=2 -->\n</section>"
    if marker in html:
        return html.replace(marker, marker + '\n<div id="landing-dev1-home"></div>', 1)
    if 'id="landing-event-hero-2"' in html:
        html = re.sub(
            r'(<section\b[^>]*\bid="landing-event-hero-2"[^>]*>.*?</section>)',
            r'\1\n<div id="landing-dev1-home"></div>',
            html,
            count=1,
            flags=re.I | re.S,
        )
    return html


def build_sections(cur) -> tuple[str, str, dict]:
    today = date.today()
    rows = fetch_hero_candidates(cur, today=today)
    idx = load_catalogue_index()
    h1, h2 = select_hero_events(rows, today=today, catalogue=idx)
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
    html = _detach_hero2_from_claim(html)
    html = _replace_section(html, SLOT1[0], s1)
    html = _upsert_after(html, SLOT2[0], s2, SLOT1[0])
    html = _place_profile_after_heroes(html)
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
