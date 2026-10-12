#!/usr/bin/env python3
"""Put MAC TSL on the std Event Logo card + Team-only results HTML.

Run on the live box after snapshot + chattr -i. Does not replace api.py.

  python3 sailingsa/deploy/patch_live_mac_tsl_std_cards.py /var/www/sailingsa
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

SLUG = "2026-10-17-mac-tsl-wc-team-sailing"
CLASS_LOGO = "/artwork/Class Logo/TSL-Class-Logo.png"
EVENT_LOGO = "/artwork/Event Logo/TSL-Team-Sailing.png"
EVENT_LOGO_FILE = "TSL-Team-Sailing.png"
CARDS_OLD = "mac-tsl-live-cards.js?v=20261012i"
CARDS_NEW = "mac-tsl-live-cards.js?v=20261012k"

LANDING_IMG = (
    f'<img class="sa-home-regatta-event-logo" src="{EVENT_LOGO}?v=20261012j" '
    'alt="" width="78" height="58" loading="lazy" decoding="async">'
)

TEAM_ONLY_FN = '''
def _mac_tsl_team_only_results_html(html, regatta_id):
    """MAC TSL Event URL: Team + club logo, no Club column (std Event URL team line)."""
    if str(regatta_id or "").strip() != "2026-10-17-mac-tsl-wc-team-sailing" or not html:
        return html
    import re
    out = html.replace(">Boat Name</th>", ">Team</th>")
    out = re.sub(r'<th class="club-col">Club</th>', "", out)
    def _row(m):
        row = m.group(0)
        club = re.search(
            r'<td class="club-col">(<span class="rs-club-with-logo">.*?</span>)</td>',
            row,
            flags=re.S,
        )
        logo = ""
        if club:
            img = re.search(r'<img[^>]+class="rs-club-row-logo-sm"[^>]*>', club.group(1))
            if img:
                logo = img.group(0)
        def _team(tm):
            inner = tm.group(1)
            if "tsl-team-club" in inner:
                return tm.group(0)
            text = re.sub(r"<[^>]+>", "", inner).strip()
            wrap = (
                '<span class="rs-club-with-logo tsl-team-club">'
                + logo
                + "<span>"
                + text
                + "</span></span>"
            )
            return '<td class="wc-meta-col boat-col">' + wrap + "</td>"
        row = re.sub(
            r'<td class="wc-meta-col boat-col">(.*?)</td>',
            _team,
            row,
            count=1,
            flags=re.S,
        )
        row = re.sub(r'<td class="club-col">.*?</td>', "", row, count=1, flags=re.S)
        return row
    out = re.sub(r"<tr\\b[^>]*>.*?</tr>", _row, out, flags=re.S)
    return out
'''

TEAM_HOOK_ANCHOR = "return html"
# Applied by explicit call-site search below.


def copy_event_logo(root: Path) -> None:
    src = root / "artwork" / "Class Logo" / "TSL-Class-Logo.png"
    dest_dir = root / "artwork" / "Event Logo"
    dest = dest_dir / EVENT_LOGO_FILE
    dest_dir.mkdir(parents=True, exist_ok=True)
    if not src.is_file():
        raise SystemExit(f"ERROR: missing {src}")
    if dest.is_file() and dest.stat().st_size == src.stat().st_size:
        print(f"skip event logo copy: {dest} exists")
        return
    shutil.copy2(src, dest)
    print(f"copied {src} -> {dest} ({dest.stat().st_size} bytes)")


def patch_api(api: Path) -> None:
    text = api.read_text(encoding="utf-8")
    orig = text
    text = text.replace(CARDS_OLD, CARDS_NEW)
    # Named-event / listing rules must use Event Logo folder (hub rejects Class Logo).
    for needle in (
        f'("{SLUG.replace("-", " ")}", "{CLASS_LOGO}"',
        f'("2026 10 17 mac tsl wc team sailing", "{CLASS_LOGO}"',
        f'("team sailing league", "{CLASS_LOGO}"',
        f'("team sailing", "{CLASS_LOGO}"',
    ):
        if needle in text:
            text = text.replace(needle, needle.replace(CLASS_LOGO, EVENT_LOGO), 1)
            print(f"retarget rule {needle[:48]}...")
    # Header left logo helper used on this Event URL.
    named_return = f'        return "{CLASS_LOGO}"'
    if named_return in text and "team sailing" in text:
        text = text.replace(named_return, f'        return "{EVENT_LOGO}"', 1)
        print("retarget named event logo return")
    if EVENT_LOGO not in text and CLASS_LOGO in text:
        # Last-resort: only the TSL named-event assignment, not class-chip map.
        text = text.replace(
            f'or "team sailing" in en:\n        return "{CLASS_LOGO}"',
            f'or "team sailing" in en:\n        return "{EVENT_LOGO}"',
        )
        text = text.replace(
            f'or "team sailing" in en:\n            return "{CLASS_LOGO}"',
            f'or "team sailing" in en:\n            return "{EVENT_LOGO}"',
        )
    if "_mac_tsl_team_only_results_html" not in text:
        text = text.rstrip() + "\n\n# MAC_TSL_TEAM_ONLY_TABLE_v1\n" + TEAM_ONLY_FN
        print("append Team-only HTML helper")
    if text != orig:
        api.write_text(text, encoding="utf-8")
        print(f"wrote {api}")
    else:
        print("api.py: no text changes")
    print(f"  Event Logo path count: {text.count(EVENT_LOGO)}")
    print(f"  cards pin j: {text.count(CARDS_NEW)}")


def patch_landing_card(index: Path) -> None:
    if not index.is_file():
        print(f"skip landing: missing {index}")
        return
    text = index.read_text(encoding="utf-8")
    orig = text
    empty = (
        f'<a class="sa-home-regatta-event-logo-link" href="/regatta/{SLUG}" '
        f'aria-label="SA Sailing WC Team Sailing Event"></a>'
    )
    filled = (
        f'<a class="sa-home-regatta-event-logo-link" href="/regatta/{SLUG}" '
        f'aria-label="SA Sailing WC Team Sailing Event">{LANDING_IMG}</a>'
    )
    if LANDING_IMG in text:
        print("skip landing: event logo already in card")
        return
    if empty in text:
        text = text.replace(empty, filled)
        print("inject Event Logo into landing TSL card")
    else:
        print("note: landing empty-logo anchor not found")
    chip = (
        '<a class="sa-home-regatta-single-class" href="/class/tsl">'
        '<span class="sa-home-regatta-chip-text">TSL</span></a>'
    )
    if chip in text and LANDING_IMG in text:
        # Std listing hides the class chip once the left Event Logo is present.
        text = text.replace(chip, "", 1)
        print("remove superseded TSL class chip from landing card")
    if text != orig:
        index.write_text(text, encoding="utf-8")
        print(f"wrote {index}")


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: patch_live_mac_tsl_std_cards.py /var/www/sailingsa", file=sys.stderr)
        return 2
    root = Path(sys.argv[1])
    copy_event_logo(root)
    api = root / "api" / "api.py"
    if not api.is_file():
        raise SystemExit(f"ERROR: missing {api}")
    patch_api(api)
    patch_landing_card(root / "index.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
