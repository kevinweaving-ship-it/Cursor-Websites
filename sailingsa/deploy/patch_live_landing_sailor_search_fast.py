#!/usr/bin/env python3
"""Landing sailor search: ~30 results (cap 100), JSON cards, no /dev-1.

Run on live. Marker: LANDING_SAILOR_SEARCH_FAST_v2
Never overwrite live api.py with the repo copy.
"""
from __future__ import annotations

from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
HTMLS = [
    Path("/var/www/sailingsa/blank.html"),
    Path("/var/www/sailingsa/index.html"),
]
MARKER = "LANDING_SAILOR_SEARCH_FAST_v2"

SIMPLE_CARD = """                        function mountSimpleSailorCard(item) {
                            var row = item.row || {};
                            var sid = String(item.sid || '').trim();
                            var name = [row.first_names || row.first_name, row.surname || row.last_name].filter(Boolean).join(' ') || row.full_name || 'Sailor';
                            var club = row.club || row.primary_club || row.club_1 || '—';
                            var classesSailed = row.class_name || row.primary_class || '—';
                            function esc(s) { return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
                            var card = document.createElement('div');
                            card.className = 'profile-card';
                            card.setAttribute('role', 'listitem');
                            card.dataset.sasId = sid;
                            card.innerHTML = '<div class="profile-card-header">Profile</div><div class="profile-card-body">' +
                                '<span class="profile-card-label">Name</span><span class="profile-card-value">' + esc(name) + '</span>' +
                                '<span class="profile-card-label">Club</span><span class="profile-card-value">' + esc(club) + '</span>' +
                                '<span class="profile-card-label">Classes Sailed</span><span class="profile-card-value">' + esc(classesSailed) + '</span></div>';
                            card.style.cursor = 'pointer';
                            card.addEventListener('click', function(ev) {
                                ev.preventDefault();
                                if (!sid) return;
                                if (typeof window.showSailorStatsInResults === 'function') {
                                    window.showSailorStatsInResults(sid, name, club, classesSailed);
                                }
                            });
                            item.wrap.innerHTML = '';
                            item.wrap.appendChild(card);
                        }
"""

FETCH_ONE = """                        function fetchOne(item) {
                            if (!item || !item.wrap || item.wrap.getAttribute('data-card-loaded') === '1') return Promise.resolve();
                            item.wrap.setAttribute('data-card-loaded', '1');
                            if (!item.sid) {
                                item.wrap.innerHTML = '<div class="profile-card" style="cursor:default;">No SAS ID.</div>';
                                return Promise.resolve();
                            }
                            try {
                                mountSimpleSailorCard(item);
                            } catch (e) {
                                try { console.warn('sailor card', e); } catch (_) {}
                                item.wrap.innerHTML = '<div class="profile-card" style="cursor:default;">Could not load card.</div>';
                            }
                            return Promise.resolve();
                        }
"""


def _replace_fetch_one_block(text: str) -> str:
    start = text.find("function fetchOne(item)")
    if start < 0:
        raise SystemExit("fetchOne missing")
    # Keep any already-correct fetchOne.
    if MARKER in text[start : start + 900] or (
        "mountSimpleSailorCard(item);" in text[start : start + 700]
        and "function mountSimpleSailorCard" in text
        and "if (false) fetch" not in text[start : start + 1200]
        and "/dev-1?embed=1" not in text[start : start + 1200]
    ):
        return text
    end = text.find("function loadRange(start, end, conc)", start)
    if end < 0:
        raise SystemExit("loadRange missing")
    # Drop a leftover simple-card function immediately before fetchOne so we do not duplicate it.
    before = text[:start]
    marker = "function mountSimpleSailorCard(item)"
    m = before.rfind(marker)
    if m >= 0 and start - m < 2500:
        start = m
        before = text[:start]
    return before + SIMPLE_CARD + FETCH_ONE + "                        /* " + MARKER + " */\n" + text[end:]


def patch_html(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    orig = text
    for old in (
        "var limitParam = '&hub=1&limit=500';",
        "var limitParam = '&hub=1&limit=12';",
        "var limitParam = '&hub=1&limit=24';",
    ):
        text = text.replace(old, "var limitParam = '&hub=1&limit=30';")
    old_fetch = """                    function fetchSearch(u) {
                        return fetch(u, { signal: sailorSearchAbort.signal })
                            .then(function(res) { return res.ok ? res.json() : Promise.resolve([]); })
                            .then(function(data) { return Array.isArray(data) ? data : []; });
                    }"""
    new_fetch = """                    function fetchSearch(u) {
                        return fetch(u, { signal: sailorSearchAbort.signal })
                            .then(function(res) { return res.ok ? res.json() : Promise.resolve([]); })
                            .then(function(data) { return Array.isArray(data) ? data : []; })
                            .catch(function() { return []; });
                    }"""
    if old_fetch in text:
        text = text.replace(old_fetch, new_fetch, 1)
    old_score = """                        function score(row) {
                            var fn = String(row.first_names || row.first_name || '').toLowerCase();"""
    new_score = """                        function score(row) {
                            if (!row) return 9;
                            var fn = String(row.first_names || row.first_name || '').toLowerCase();"""
    if old_score in text:
        text = text.replace(old_score, new_score, 1)
    old_sort = """                        if (typeof setSearchInteractionActive === 'function') setSearchInteractionActive(true);
                        list = sortSailorList(list);"""
    new_sort = """                        if (typeof setSearchInteractionActive === 'function') setSearchInteractionActive(true);
                        try {
                            list = sortSailorList(Array.isArray(list) ? list : []);
                        } catch (_) {
                            list = Array.isArray(list) ? list.slice() : [];
                        }"""
    if old_sort in text:
        text = text.replace(old_sort, new_sort, 1)
    text = _replace_fetch_one_block(text)
    if "function mountSimpleSailorCard" not in text:
        raise SystemExit(f"simple card missing after patch {path}")
    if text == orig:
        raise SystemExit(f"no html changes in {path}")
    path.write_text(text, encoding="utf-8")
    print("HTML", path, "ok")


def patch_api() -> None:
    text = API.read_text(encoding="utf-8")
    if MARKER in text:
        print("api already marked")
        return
    replaced = False
    for old in (
        "    max_cap = 24 if int(hub or 0) == 1 else 200  # LANDING_SAILOR_SEARCH_FAST_v1\n",
        "    max_cap = 24 if int(hub or 0) == 1 else 200\n",
        "    max_cap = 500 if int(hub or 0) == 1 else 200\n",
    ):
        if old in text:
            text = text.replace(old, "    max_cap = 100 if int(hub or 0) == 1 else 200  # " + MARKER + "\n", 1)
            replaced = True
            break
    if not replaced:
        raise SystemExit("max_cap missing")
    old_sb = "if needs_sail_boat_search and q and len(q.strip()) >= 4 and len(q.strip().split()) == 1:"
    new_sb = "if needs_sail_boat_search and int(hub or 0) != 1 and q and len(q.strip()) >= 4 and len(q.strip().split()) == 1:"
    if old_sb in text:
        text = text.replace(old_sb, new_sb, 1)
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
