#!/usr/bin/env python3
"""Replace class clubs table with event-style cards."""
from pathlib import Path
import shutil
import time

INDEX = Path("/var/www/sailingsa/index.sailor_spa.html")
MARK = "CLASS_CLUB_CARDS_v1"

OLD_ROWS = """            var clubRows = clubs.map(function(c, i) {
                var code = (c.club_code || '').trim().toUpperCase();
                var slug = (c.club_slug || code.toLowerCase() || '').trim();
                var img = (c.club_logo_url || (code ? '/api/club-logo/' + code : '')).trim();
                var label = (code && c.club_name) ? (esc(code) + ' — ' + esc(c.club_name)) : esc(code || c.club_name || '');
                var clubCell = rowLogo(img) + (slug ? '<a href="/club/' + encodeURIComponent(slug) + '">' + label + '</a>' : label);
                var lastUrl = c.last_regatta_slug ? '/regatta/' + encodeURIComponent(c.last_regatta_slug) : '';
                var lastCell = (c.last_regatta_name || '').trim()
                    ? (lastUrl ? '<a href="' + lastUrl + '">' + esc(c.last_regatta_name) + '</a>' : esc(c.last_regatta_name))
                    : '—';
                var search = esc(((code || '') + ' ' + (c.club_name || '') + ' ' + (c.last_regatta_name || '')).toLowerCase());
                return '<tr data-search="' + search + '"><td>' + (i + 1) + '</td><td class="cell-left">' + clubCell + '</td><td>' + (c.sailors != null ? c.sailors : '—') + '</td><td>' + (c.races != null ? c.races : '—') + '</td><td>' + lastCell + '</td><td class="cell-nowrap">' + esc(c.last_regatta_date || '—') + '</td></tr>';
            }).join('');"""

NEW_ROWS = """            function classClubCard(c) {
                var code = (c.club_code || '').trim().toUpperCase();
                var slug = (c.club_slug || code.toLowerCase() || '').trim();
                var url = slug ? '/club/' + encodeURIComponent(slug) : '';
                var name = (c.club_name || '').trim();
                var title = name ? (code ? (code + ' — ' + name) : name) : (code || 'Club');
                var img = (c.club_logo_url || (code ? ('/artwork/Club Logo/' + code + '.png') : '')).trim();
                var sailorsL = countLabel(c.sailors, 'sailor', 'sailors');
                var racesL = countLabel(c.races, 'race', 'races');
                var dateL = shortDate(c.last_regatta_date) || String(c.last_regatta_date || '').trim();
                var lastName = (c.last_regatta_name || '').trim();
                var lastUrl = c.last_regatta_slug ? '/regatta/' + encodeURIComponent(c.last_regatta_slug) : '';
                var logo = img
                    ? (url
                        ? '<a class="sa-home-regatta-event-logo-link" href="' + esc(url) + '"><img class="sa-home-regatta-event-logo" src="' + esc(img) + '" alt="" loading="lazy" decoding="async" onerror="this.onerror=null;this.src=\\'/api/club-logo/' + esc(code) + '\\';"></a>'
                        : '<img class="sa-home-regatta-event-logo" src="' + esc(img) + '" alt="" loading="lazy" decoding="async" onerror="this.onerror=null;this.src=\\'/api/club-logo/' + esc(code) + '\\';">')
                    : '';
                var titleHtml = url
                    ? '<a href="' + esc(url) + '" class="sa-home-regatta-title">' + esc(title) + '</a>'
                    : '<div class="sa-home-regatta-title">' + esc(title) + '</div>';
                var meta = '<div class="sa-home-regatta-meta">' + metaPill(sailorsL, 'users') + metaPill(racesL, 'flag') + metaPill(dateL, 'calendar') + '</div>';
                var lastInner = lastName
                    ? (lastUrl
                        ? '<a href="' + esc(lastUrl) + '" class="sa-home-regatta-host-code">' + esc(lastName) + '</a>'
                        : '<div class="sa-home-regatta-host-code">' + esc(lastName) + '</div>')
                    : '';
                var lastHtml = '<div class="sa-home-regatta-host">' + lastInner + '</div>';
                var actions = '<div class="sa-home-regatta-actions">' +
                    (url ? '<a class="sa-home-regatta-btn" href="' + esc(url) + '">Club</a>' : '') +
                    '</div>';
                var hay = esc((code + ' ' + name + ' ' + lastName).toLowerCase());
                return '<article class="sa-home-regatta-card" data-search="' + hay + '">' +
                    '<div class="sa-home-regatta-top">' + logo +
                    '<div class="sa-home-regatta-top-main">' + titleHtml + meta + '</div>' +
                    lastHtml + actions + '</div></article>';
            }
            var clubCards = clubs.map(classClubCard).join('');
            var clubsHtml = clubs.length
                ? ('<div class="card stats-section club-clubs-section" id="clubs">' +
                    classToggleTitle('Clubs sailing ' + className + ' (' + clubs.length + ')', 'class-clubs-cards') +
                    '<input type="search" class="club-home-card-filter" data-list="class-clubs-cards" placeholder="Search clubs sailing…" autocomplete="off">' +
                    '<div class="club-list-body" hidden>' +
                    '<div class="sa-home-regatta-wrap"><div class="sa-home-regatta-list" id="class-clubs-cards">' + clubCards + '</div></div>' +
                    '</div></div>')
                : '';"""

OLD_TABLE = """            var clubsTable = '<table class="table" id="class-clubs-table"><thead><tr><th>#</th><th>Club</th><th>Sailors</th><th>Races</th><th>Last regatta</th><th>Date</th></tr></thead><tbody>' +
                (clubRows || '<tr><td colspan="6">No clubs</td></tr>') + '</tbody></table>';"""

NEW_TABLE = ""

OLD_SECTION = """                (clubs.length ? section('clubs', 'Clubs sailing ' + className + ' (' + clubs.length + ')', 'class-clubs-table', clubsTable) : '') +"""

NEW_SECTION = """                clubsHtml +"""


def main() -> None:
    text = INDEX.read_text(encoding="utf-8")
    if MARK in text:
        print("ALREADY")
        return
    miss = []
    for name, old in (("ROWS", OLD_ROWS), ("TABLE", OLD_TABLE), ("SECTION", OLD_SECTION)):
        if old not in text:
            miss.append(name)
    if miss:
        raise SystemExit("MISSING:" + ",".join(miss))
    ts = time.strftime("%Y%m%d_%H%M%S")
    bak = INDEX.with_name(INDEX.name + ".bak.class_clubs." + ts)
    shutil.copy2(INDEX, bak)
    text = text.replace(OLD_ROWS, NEW_ROWS, 1)
    text = text.replace(OLD_TABLE, NEW_TABLE, 1)
    text = text.replace(OLD_SECTION, NEW_SECTION, 1)
    text = text.replace("</head>", "<!-- " + MARK + " --></head>", 1)
    INDEX.write_text(text)
    print("OK", MARK, "BAK", str(bak))


if __name__ == "__main__":
    main()
