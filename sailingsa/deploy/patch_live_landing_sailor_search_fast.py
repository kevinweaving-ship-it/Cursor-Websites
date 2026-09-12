#!/usr/bin/env python3
"""Landing sailor search: cap hub results, skip /dev-1 cards, skip hub sail/boat scan.

Run on live. Marker: LANDING_SAILOR_SEARCH_FAST_v1
Never overwrite live api.py with the repo copy.
"""
from __future__ import annotations

from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
HTMLS = [
    Path("/var/www/sailingsa/blank.html"),
    Path("/var/www/sailingsa/index.html"),
]
MARKER = "LANDING_SAILOR_SEARCH_FAST_v1"


def patch_html(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    orig = text
    text = text.replace("var limitParam = '&hub=1&limit=500';", "var limitParam = '&hub=1&limit=12';")
    old_fetch = """                            return fetch('/dev-1?embed=1&sas_id=' + encodeURIComponent(item.sid), { credentials: 'same-origin' })
                                .then(function(r) { return r.text(); })
                                .then(function(html) {
                                    if (gen !== (window.__sailorSearchGen || 0)) return;
                                    window.__ssaDev1CardCache[item.sid] = html;
                                    mountDev1Card(item.wrap, html);
                                })"""
    new_fetch = """                            mountSimpleSailorCard(item);
                            return Promise.resolve();
                            /* """ + MARKER + """ skip /dev-1 embed on landing list */
                            if (false) fetch('/dev-1?embed=1&sas_id=' + encodeURIComponent(item.sid), { credentials: 'same-origin' })
                                .then(function(r) { return r.text(); })
                                .then(function(html) {
                                    if (gen !== (window.__sailorSearchGen || 0)) return;
                                    window.__ssaDev1CardCache[item.sid] = html;
                                    mountDev1Card(item.wrap, html);
                                })"""
    if old_fetch in text:
        text = text.replace(old_fetch, new_fetch, 1)
    old_gen = """                    if (q !== '') {
                        window.__sailorSearchGen = (window.__sailorSearchGen || 0) + 1;
                        if (q.length >= 2 && regattaInput && (regattaInput.value || '').trim()) {
                            regattaInput.value = '';
                        }
                        // Hard-hide logged-in profile immediately so the full search list owns the space."""
    new_gen = """                    if (q !== '') {
                        if (q.length >= 2 && regattaInput && (regattaInput.value || '').trim()) {
                            regattaInput.value = '';
                        }
                        // Hard-hide logged-in profile immediately so the full search list owns the space."""
    if old_gen in text:
        text = text.replace(old_gen, new_gen, 1)
    if text == orig:
        raise SystemExit(f"no html changes in {path}")
    path.write_text(text, encoding="utf-8")
    print("HTML", path, "ok")


def patch_api() -> None:
    text = API.read_text(encoding="utf-8")
    if MARKER in text:
        print("api already marked")
        return
    old_cap = "    max_cap = 500 if int(hub or 0) == 1 else 200\n"
    new_cap = "    max_cap = 24 if int(hub or 0) == 1 else 200  # " + MARKER + "\n"
    if old_cap not in text:
        raise SystemExit("max_cap missing")
    text = text.replace(old_cap, new_cap, 1)
    old_sb = "if needs_sail_boat_search and q and len(q.strip()) >= 4 and len(q.strip().split()) == 1:"
    new_sb = "if needs_sail_boat_search and int(hub or 0) != 1 and q and len(q.strip()) >= 4 and len(q.strip().split()) == 1:"
    if old_sb not in text:
        old_sb2 = "if needs_sail_boat_search and q and len(q.strip()) >= 2:"
        new_sb2 = "if needs_sail_boat_search and int(hub or 0) != 1 and q and len(q.strip()) >= 2:"
        if old_sb2 not in text:
            raise SystemExit("sail_boat if missing")
        text = text.replace(old_sb2, new_sb2, 1)
    else:
        text = text.replace(old_sb, new_sb, 1)
    old_tmp = "                elif q:\n                    # Name / sail / boat (not temp-ID listing)."
    new_tmp = "                elif q and int(hub or 0) != 1:\n                    # Name / sail / boat (not temp-ID listing)."
    if old_tmp in text:
        text = text.replace(old_tmp, new_tmp, 1)
    if MARKER not in text:
        raise SystemExit("marker failed")
    API.write_text(text, encoding="utf-8")
    print("API patched", API.stat().st_size)


def main() -> int:
    for p in HTMLS:
        if p.is_file():
            patch_html(p)
    patch_api()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
