#!/usr/bin/env python3
"""Live-only: parent-truth Event Logo on baker, header JSON, hub cards, event JS."""
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

TS = datetime.now().strftime("%Y%m%d_%H%M%S")
ROOT = Path("/var/www/sailingsa")
BAKER = ROOT / "sailingsa/backend/landing_event_story_cards.py"
HEADER = ROOT / "data/wc_regatta_header_icons.json"
PDF = ROOT / "js/regatta-pdf-share.js"
HUBS = [ROOT / "index.html", ROOT / "blank.html"]
HELPER_MARK = "from parent_event_logo import"
JS_MARK = "PARENT_EVENT_LOGO_TRUTH_v1"
V5_MARK = "sa:regattaLogo:event:v5:"


def bak(p: Path) -> None:
    dest = Path(str(p) + f".bak_parenttruth_{TS}")
    if p.is_file() and not dest.exists():
        shutil.copy2(p, dest)
        print("backup", dest)


def patch_baker() -> None:
    txt = BAKER.read_text(encoding="utf-8")
    if HELPER_MARK not in txt:
        old = "from event_page_seo import compact_event_date_range, derive_event_lifecycle\n"
        new = (
            "from event_page_seo import compact_event_date_range, derive_event_lifecycle\n"
            "from parent_event_logo import is_event_logo_path, parent_event_logo_url\n"
        )
        if old not in txt:
            raise SystemExit("baker import anchor missing")
        txt = txt.replace(old, new, 1)
    old_logo = (
        "    class_logo = class_logo_src(classes[0]) if classes else \"\"\n"
        "    logo = series.get(\"logo\") or class_logo or \"\"\n"
    )
    new_logo = (
        "    class_logo = class_logo_src(classes[0]) if classes else \"\"\n"
        "    event_logo = parent_event_logo_url(rid, series)\n"
        "    if event_logo:\n"
        "        logo = event_logo\n"
        "        class_logo = \"\"\n"
        "    else:\n"
        "        logo = series.get(\"logo\") or class_logo or \"\"\n"
    )
    if "parent_event_logo_url(rid, series)" not in txt:
        if old_logo not in txt:
            raise SystemExit("baker card_from_row logo block missing")
        txt = txt.replace(old_logo, new_logo, 1)
    old_block = (
        "    class_block = \"\"\n"
        "    if class_logo:\n"
    )
    new_block = (
        "    class_block = \"\"\n"
        "    if logo and is_event_logo_path(logo):\n"
        "        class_block = \"\"\n"
        "    elif class_logo:\n"
    )
    if "is_event_logo_path(logo)" not in txt:
        if old_block not in txt:
            raise SystemExit("baker class_block anchor missing")
        txt = txt.replace(old_block, new_block, 1)
    BAKER.write_text(txt, encoding="utf-8")
    print("baker patched", BAKER)


def patch_header() -> None:
    data = json.loads(HEADER.read_text(encoding="utf-8"))
    updates = {
        "2026-10-10-hmyc-dam-bottle-sprints": {
            "left": "/artwork/Event Logo/Dam-Bottle-Sprints.png?v=20261010pt1"
        },
        "2026-09-24-ayc-dabchick-gauteng-regionals": {
            "left": "/artwork/Event Logo/Gauteng-Province-Regionals-2025.png"
        },
        "2026-09-13-vulcan-challenge": {
            "left": "/artwork/Event Logo/Vulcan-Challenge-2026.png"
        },
        "2026-09-13-zvyc-cape-classic": {
            "left": "/artwork/Event Logo/Cape-Classic-Series.png"
        },
    }
    for rid, patch in updates.items():
        cur = data.get(rid)
        if not isinstance(cur, dict):
            cur = {} if cur is None else {"left": cur} if cur else {}
        cur.update(patch)
        data[rid] = cur
        print("header", rid, "left=", cur.get("left"))
    HEADER.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("header written")


def append_event_js() -> None:
    js_path = Path("/tmp/parent-event-logo-truth.js")
    extra = js_path.read_text(encoding="utf-8")
    txt = PDF.read_text(encoding="utf-8")
    if JS_MARK in txt:
        print("pdf-share already has parent-truth JS")
        return
    PDF.write_text(
        txt.rstrip() + "\n\n/* " + JS_MARK + " */\n" + extra + "\n",
        encoding="utf-8",
    )
    print("pdf-share appended", PDF, "bytes", PDF.stat().st_size)


def patch_hubs() -> None:
    old_k = "var k = 'sa:regattaLogo:event:v4:' + rid;"
    new_k = "var k = 'sa:regattaLogo:event:v5:' + rid;"
    old_cache = """                    if (cached && cached.trim()) {
                        window.__saRegattaEventLogoCache[rid] = Promise.resolve(cached.trim());
                        return window.__saRegattaEventLogoCache[rid];
                    }"""
    new_cache = """                    if (cached && isEventLogoArtworkPath(cached)) {
                        window.__saRegattaEventLogoCache[rid] = Promise.resolve(cached.trim());
                        return window.__saRegattaEventLogoCache[rid];
                    }"""
    old_store = """                            if (src) { try { localStorage.setItem('sa:regattaLogo:event:v4:' + rid, src); } catch (_) {} }
                            return src || null;"""
    new_store = """                            if (src && isEventLogoArtworkPath(src)) {
                                try { localStorage.setItem('sa:regattaLogo:event:v5:' + rid, src); } catch (_) {}
                                return src;
                            }
                            return null;"""
    old_slot = "localStorage.getItem('sa:regattaLogo:event:v4:'"
    new_slot = "localStorage.getItem('sa:regattaLogo:event:v5:'"
    old_apply = """                        if (!src || !next.img || !next.img.isConnected) {
                            if (next.kind === 'child' && chip) setFleetChipLogoState(chip, false);
                            return;
                        }
                        next.img.src = src;"""
    new_apply = """                        if (!src || !next.img || !next.img.isConnected) {
                            if (next.kind === 'child' && chip) setFleetChipLogoState(chip, false);
                            if (next.kind === 'event') {
                                var emptyCard = next.img.closest ? next.img.closest('.sa-home-regatta-card') : null;
                                if (emptyCard && typeof emptyCard.__saAddClassChip === 'function') emptyCard.__saAddClassChip();
                            }
                            return;
                        }
                        if (next.kind === 'event' && !isEventLogoArtworkPath(src)) {
                            var skipCard = next.img.closest ? next.img.closest('.sa-home-regatta-card') : null;
                            if (skipCard && typeof skipCard.__saAddClassChip === 'function') skipCard.__saAddClassChip();
                            return;
                        }
                        next.img.src = src;"""
    for hub in HUBS:
        txt = hub.read_text(encoding="utf-8")
        if V5_MARK in txt and "event' && !isEventLogoArtworkPath(src)" in txt:
            print("hub already v5", hub)
            continue
        n = 0
        if old_k in txt:
            txt = txt.replace(old_k, new_k)
            n += 1
        if old_cache in txt:
            txt = txt.replace(old_cache, new_cache)
            n += 1
        if old_store in txt:
            txt = txt.replace(old_store, new_store)
            n += 1
        if old_slot in txt:
            txt = txt.replace(old_slot, new_slot)
            n += 1
        if old_apply in txt:
            txt = txt.replace(old_apply, new_apply, 1)
            n += 1
        if n < 4:
            print("WARN hub partial", hub, "replacements", n)
        hub.write_text(txt, encoding="utf-8")
        print("hub patched", hub, "n", n, "v5", txt.count(V5_MARK))


def main() -> None:
    for p in [BAKER, HEADER, PDF, *HUBS]:
        bak(p)
    patch_baker()
    patch_header()
    append_event_js()
    patch_hubs()
    print("APPLY_OK")


if __name__ == "__main__":
    main()
