#!/usr/bin/env python3
"""After typing stops: names list only, then one best-match /dev-1 card.

Never pre-build the rest of the list. Marker: LANDING_SAILOR_SEARCH_TOP1_AFTER_IDLE_v6
"""
from __future__ import annotations

from pathlib import Path

HTMLS = [
    Path("/var/www/sailingsa/blank.html"),
    Path("/var/www/sailingsa/index.html"),
]
MARKER = "LANDING_SAILOR_SEARCH_TOP1_AFTER_IDLE_v6"

OLD_DEBOUNCE_A = """                        if (q === '') {
                            runSailorSearch();
                        } else {
                            if (q.length >= 2) instantFilterSailorResults(q);
                            var _tokN = q.split(/\\s+/).filter(Boolean).length;
                            sailorSearchDebounce = setTimeout(runSailorSearch, _tokN >= 2 ? 0 : 180);
                        }"""
OLD_DEBOUNCE_B = """                        if (q === '') {
                            runSailorSearch();
                        } else {
                            sailorSearchDebounce = setTimeout(runSailorSearch, 280);
                        }"""
NEW_DEBOUNCE = """                        if (q === '') {
                            runSailorSearch();
                        } else {
                            if (sailorSearchAbort) sailorSearchAbort.abort();
                            if (q.length >= 2 && typeof instantFilterSailorResults === 'function') instantFilterSailorResults(q);
                            sailorSearchDebounce = setTimeout(runSailorSearch, 350);
                        }"""


def _strip_preload(text: str) -> str:
    start = text.find("                        window.__ssaDev1CardCache = window.__ssaDev1CardCache || {};")
    if start < 0:
        start = text.find("                        function fetchOne(item) {")
    if start < 0:
        raise SystemExit("fetchOne block missing")
    end = text.find("                    var url = API + '/api/search?q='", start)
    if end < 0:
        raise SystemExit("search url missing")
    fetch_start = text.find("                        function fetchOne(item) {", start)
    if fetch_start < 0 or fetch_start > end:
        raise SystemExit("fetchOne missing in block")
    load_start = text.find("                        function loadRange", fetch_start)
    if load_start < 0 or load_start > end:
        fetch_end = text.find("                        if (window.__ssaSailorCardIO)", fetch_start)
        if fetch_end < 0 or fetch_end > end:
            fetch_end = end
    else:
        fetch_end = load_start
    fetch_fn = text[fetch_start:fetch_end]
    new = (
        "                        window.__ssaDev1CardCache = window.__ssaDev1CardCache || {};\n"
        + fetch_fn
        + """                        if (window.__ssaSailorCardIO) {
                            try { window.__ssaSailorCardIO.disconnect(); } catch (_) {}
                            window.__ssaSailorCardIO = null;
                        }
                        /* """
        + MARKER
        + """ only #1 card after typing stops */
                        return slots[0] ? fetchOne(slots[0]) : Promise.resolve();
                    }

"""
    )
    return text[:start] + new + text[end:]


def patch_html(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    orig = text
    if OLD_DEBOUNCE_A in text:
        text = text.replace(OLD_DEBOUNCE_A, NEW_DEBOUNCE, 1)
    elif OLD_DEBOUNCE_B in text:
        text = text.replace(OLD_DEBOUNCE_B, NEW_DEBOUNCE, 1)
    elif "setTimeout(runSailorSearch, 350)" not in text:
        # already patched with abort+instant? try 0/180 variant without instantFilter prefix
        old = """                            if (q.length >= 2) instantFilterSailorResults(q);
                            var _tokN = q.split(/\\s+/).filter(Boolean).length;
                            sailorSearchDebounce = setTimeout(runSailorSearch, _tokN >= 2 ? 0 : 180);"""
        new = """                            if (sailorSearchAbort) sailorSearchAbort.abort();
                            if (q.length >= 2) instantFilterSailorResults(q);
                            sailorSearchDebounce = setTimeout(runSailorSearch, 350);"""
        if old in text:
            text = text.replace(old, new, 1)
    text = _strip_preload(text)
    if "/dev-1?embed=1" not in text:
        raise SystemExit(f"dev-1 missing {path}")
    if "only #1 card after typing stops" not in text and MARKER not in text:
        raise SystemExit(f"top1 marker missing {path}")
    if text == orig:
        raise SystemExit(f"no html changes {path}")
    path.write_text(text, encoding="utf-8")
    print("HTML", path, "ok")


def main() -> int:
    for p in HTMLS:
        if p.is_file():
            patch_html(p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
