#!/usr/bin/env python3
"""Landing sailor search: names first, list shrinks as you type, keep /dev-1 cards.

Run on live. Marker: LANDING_SAILOR_SEARCH_NAMES_FIRST_v4
Never overwrite live api.py with the repo copy.
Never replace rich /dev-1 cards with the old PROFILE sheet.
"""
from __future__ import annotations

from pathlib import Path

HTMLS = [
    Path("/var/www/sailingsa/blank.html"),
    Path("/var/www/sailingsa/index.html"),
]
MARKER = "LANDING_SAILOR_SEARCH_NAMES_FIRST_v4"

HELPERS = """                function sailorSearchRowSid(row) {
                    if (!row) return '';
                    return row.sa_sailing_id != null ? String(row.sa_sailing_id) : String(row.sas_id || row.sa_id || '');
                }
                function sailorSearchRowName(row) {
                    if (!row) return '';
                    return [row.first_names || row.first_name, row.surname || row.last_name].filter(Boolean).join(' ') || String(row.full_name || '').trim();
                }
                function sailorSearchRowMatches(row, q) {
                    var tokens = String(q || '').toLowerCase().replace(/\\s+/g, ' ').trim().split(' ').filter(Boolean);
                    if (!tokens.length) return true;
                    var fn = String(row.first_names || row.first_name || '').toLowerCase();
                    var ln = String(row.surname || row.last_name || '').toLowerCase();
                    var full = (fn + ' ' + ln).replace(/\\s+/g, ' ').trim();
                    var club = String(row.club || row.primary_club || row.club_1 || '').toLowerCase();
                    return tokens.every(function(tok) {
                        return full.indexOf(tok) !== -1 || fn.indexOf(tok) === 0 || ln.indexOf(tok) === 0 || club.indexOf(tok) !== -1;
                    });
                }
                function instantFilterSailorResults(q) {
                    if (!sailorSearchResults) return;
                    var src = window.__ssaSailorLastList;
                    if (!Array.isArray(src) || !src.length) return;
                    sailorSearchResults.querySelectorAll('.ssa-dev1-inject').forEach(function(el) {
                        var sid = String(el.getAttribute('data-sas-id') || '');
                        var row = null;
                        for (var i = 0; i < src.length; i++) {
                            if (sailorSearchRowSid(src[i]) === sid) { row = src[i]; break; }
                        }
                        var ok = row ? sailorSearchRowMatches(row, q) : false;
                        el.style.display = ok ? '' : 'none';
                    });
                    sailorSearchResults.style.display = 'block';
                }
                /* """ + MARKER + """ */
                function runSailorSearch() {
"""

SLOTS = """                        list.forEach(function(row) {
                            var sid = sailorSearchRowSid(row);
                            var wrap = document.createElement('div');
                            wrap.className = 'ssa-dev1-inject';
                            wrap.setAttribute('role', 'listitem');
                            wrap.dataset.sasId = sid;
                            wrap.style.display = '';
                            var pendingName = sailorSearchRowName(row) || 'Sailor';
                            function escPend(s) { return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
                            wrap.innerHTML = '<div class="profile-card" style="cursor:pointer;"><div class="profile-card-body"><span class="profile-card-value">' + escPend(pendingName) + '</span></div></div>';
                            sailorSearchResults.appendChild(wrap);
                            slots.push({ wrap: wrap, sid: sid, row: row });
                        });
"""


def patch_html(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    orig = text
    if MARKER in text and "function instantFilterSailorResults" in text:
        print("already patched", path)
        return
    if "function sailorSearchRowSid" not in text:
        if "                function runSailorSearch() {" not in text:
            raise SystemExit(f"runSailorSearch missing {path}")
        text = text.replace("                function runSailorSearch() {", HELPERS, 1)
    text = text.replace(
        """                    sailorSearchResults.style.display = 'block';
                    sailorSearchResults.innerHTML = '<div class="profile-card" style="cursor:default;">Searching…</div>';""",
        """                    sailorSearchResults.style.display = 'block';
                    if (!sailorSearchResults.querySelector('.ssa-dev1-inject')) {
                        sailorSearchResults.innerHTML = '<div class="profile-card" style="cursor:default;">Searching…</div>';
                    }""",
        1,
    )
    old_slots_a = """                        list.forEach(function(row) {
                            var sid = row.sa_sailing_id != null ? String(row.sa_sailing_id) : String(row.sas_id || row.sa_id || '');
                            var wrap = document.createElement('div');
                            wrap.className = 'ssa-dev1-inject';
                            wrap.setAttribute('role', 'listitem');
                            wrap.dataset.sasId = sid;
                            wrap.innerHTML = '<div class="profile-card" style="cursor:default;">Loading…</div>';
                            sailorSearchResults.appendChild(wrap);
                            slots.push({ wrap: wrap, sid: sid });
                        });"""
    old_slots_b = old_slots_a.replace("slots.push({ wrap: wrap, sid: sid });", "slots.push({ wrap: wrap, sid: sid, row: row });")
    if old_slots_a in text:
        text = text.replace(old_slots_a, SLOTS, 1)
    elif old_slots_b in text:
        text = text.replace(old_slots_b, SLOTS, 1)
    else:
        raise SystemExit(f"slots loop missing {path}")
    text = text.replace(
        """                    fetchSearch(url)
                        .then(function(list) { return renderSailorList(list); })""",
        """                    fetchSearch(url)
                        .then(function(list) {
                            window.__ssaSailorLastList = Array.isArray(list) ? list : [];
                            return renderSailorList(list);
                        })""",
        1,
    )
    text = text.replace(
        """                        if (q === '') {
                            runSailorSearch();
                        } else {
                            sailorSearchDebounce = setTimeout(runSailorSearch, 280);
                        }""",
        """                        if (q === '') {
                            runSailorSearch();
                        } else {
                            if (q.length >= 2) instantFilterSailorResults(q);
                            var _tokN = q.split(/\\s+/).filter(Boolean).length;
                            sailorSearchDebounce = setTimeout(runSailorSearch, _tokN >= 2 ? 0 : 180);
                        }""",
        1,
    )
    text = text.replace("rootMargin: '600px 0px'", "rootMargin: '80px 0px'", 1)
    text = text.replace(
        """                                .catch(function() {
                                    if (gen !== (window.__sailorSearchGen || 0)) return;
                                    item.wrap.innerHTML = '<div class="profile-card" style="cursor:default;">Could not load card.</div>';
                                });""",
        """                                .catch(function() {
                                    if (gen !== (window.__sailorSearchGen || 0)) return;
                                    var keepName = sailorSearchRowName(item.row) || 'Sailor';
                                    function escE(s) { return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
                                    item.wrap.innerHTML = '<div class="profile-card" style="cursor:pointer;"><div class="profile-card-body"><span class="profile-card-value">' + escE(keepName) + '</span></div></div>';
                                });""",
        1,
    )
    if "function fetchOne(item)" in text and "window.__ssaDev1CardCache[item.sid]) fetchOne(item)" not in text:
        text = text.replace(
            "                        function fetchOne(item) {",
            """                        window.__ssaDev1CardCache = window.__ssaDev1CardCache || {};
                        slots.forEach(function(item) {
                            if (item.sid && window.__ssaDev1CardCache[item.sid]) fetchOne(item);
                        });
                        function fetchOne(item) {""",
            1,
        )
    if "function instantFilterSailorResults" not in text:
        raise SystemExit(f"helpers missing after patch {path}")
    if "/dev-1?embed=1" not in text:
        raise SystemExit(f"dev-1 fetch missing {path}")
    if text == orig:
        raise SystemExit(f"no html changes in {path}")
    path.write_text(text, encoding="utf-8")
    print("HTML", path, "ok")


def main() -> int:
    for p in HTMLS:
        if p.is_file():
            patch_html(p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
