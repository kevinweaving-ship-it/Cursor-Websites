#!/usr/bin/env python3
"""Landing sailor search: keep working /dev-1 profile cards. Cap list at 30 (API 100).

Run on live. Marker: LANDING_SAILOR_SEARCH_RESTORE_CARDS_v3
Never overwrite live api.py with the repo copy.
Never replace the rich sailor cards with the old Name/Club/Classes sheet.
"""
from __future__ import annotations

from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
HTMLS = [
    Path("/var/www/sailingsa/blank.html"),
    Path("/var/www/sailingsa/index.html"),
]
MARKER = "LANDING_SAILOR_SEARCH_RESTORE_CARDS_v3"

WORKING_FETCH_ONE = """                        function fetchOne(item) {
                            if (!item || item.wrap.getAttribute('data-card-loaded') === '1') return Promise.resolve();
                            item.wrap.setAttribute('data-card-loaded', '1');
                            if (!item.sid) {
                                item.wrap.innerHTML = '<div class="profile-card" style="cursor:default;">No SAS ID.</div>';
                                return Promise.resolve();
                            }
                            window.__ssaDev1CardCache = window.__ssaDev1CardCache || {};
                            var cached = window.__ssaDev1CardCache[item.sid];
                            if (cached) {
                                mountDev1Card(item.wrap, cached);
                                return Promise.resolve();
                            }
                            return fetch('/dev-1?embed=1&sas_id=' + encodeURIComponent(item.sid), { credentials: 'same-origin' })
                                .then(function(r) { return r.text(); })
                                .then(function(html) {
                                    if (gen !== (window.__sailorSearchGen || 0)) return;
                                    window.__ssaDev1CardCache[item.sid] = html;
                                    mountDev1Card(item.wrap, html);
                                })
                                .catch(function() {
                                    if (gen !== (window.__sailorSearchGen || 0)) return;
                                    item.wrap.innerHTML = '<div class="profile-card" style="cursor:default;">Could not load card.</div>';
                                });
                        }
                        /* """ + MARKER + """ keep /dev-1 cards; hub list 30 */
"""


def _restore_fetch_one(text: str) -> str:
    load = text.find("function loadRange(start, end, conc)")
    if load < 0:
        raise SystemExit("loadRange missing")
    start = text.find("function mountSimpleSailorCard(item)")
    if start < 0:
        start = text.find("function fetchOne(item)")
    if start < 0:
        raise SystemExit("fetchOne missing")
    return text[:start] + WORKING_FETCH_ONE + text[load:]


def patch_html(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    orig = text
    for old in (
        "var limitParam = '&hub=1&limit=500';",
        "var limitParam = '&hub=1&limit=12';",
        "var limitParam = '&hub=1&limit=24';",
    ):
        text = text.replace(old, "var limitParam = '&hub=1&limit=30';")
    text = _restore_fetch_one(text)
    if "function mountSimpleSailorCard" in text:
        raise SystemExit(f"simple card still present {path}")
    if "/dev-1?embed=1" not in text:
        raise SystemExit(f"dev-1 fetch missing {path}")
    if text == orig:
        raise SystemExit(f"no html changes in {path}")
    path.write_text(text, encoding="utf-8")
    print("HTML", path, "ok")


def patch_api() -> None:
    text = API.read_text(encoding="utf-8")
    if "max_cap = 100 if int(hub or 0) == 1 else 200" in text:
        print("api cap already 100")
        return
    replaced = False
    for old in (
        "    max_cap = 24 if int(hub or 0) == 1 else 200  # LANDING_SAILOR_SEARCH_FAST_v1\n",
        "    max_cap = 24 if int(hub or 0) == 1 else 200\n",
        "    max_cap = 500 if int(hub or 0) == 1 else 200\n",
        "    max_cap = 100 if int(hub or 0) == 1 else 200  # LANDING_SAILOR_SEARCH_FAST_v2\n",
    ):
        if old in text:
            text = text.replace(old, "    max_cap = 100 if int(hub or 0) == 1 else 200  # " + MARKER + "\n", 1)
            replaced = True
            break
    if not replaced:
        print("api max_cap left as-is")
        return
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
