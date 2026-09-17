#!/usr/bin/env python3
"""Replace class sailors table with club-gold sailor cards + outer card."""
from pathlib import Path
import shutil
import time

INDEX = Path("/var/www/sailingsa/index.sailor_spa.html")
MARK = "CLASS_SAILOR_CARDS_v1"

OLD_ROWS = """            var sailorRows = sailors.map(function(s, i) {
                var slug = s.sailor_slug || '';
                var url = slug ? '/sailor/' + encodeURIComponent(slug) : '#';
                var clubCode = (s.club_code || '').trim().toUpperCase();
                var clubImg = (s.club_logo_url || (clubCode ? '/api/club-logo/' + clubCode : '')).trim();
                var clubCell = clubCode ? (rowLogo(clubImg) + '<a href="/club/' + encodeURIComponent(clubCode) + '">' + esc(clubCode) + '</a>') : '—';
                var rank = '';
                if (s.last_result_rank != null && s.last_fleet_size != null) {
                    rank = ordinal(s.last_result_rank) + '/' + s.last_fleet_size;
                } else if (s.last_result_rank != null) {
                    rank = ordinal(s.last_result_rank);
                } else {
                    rank = '—';
                }
                var lastUrl = s.last_regatta_slug ? '/regatta/' + encodeURIComponent(s.last_regatta_slug) : '';
                var lastCell = (s.last_regatta_name || '').trim()
                    ? (lastUrl ? '<a href="' + lastUrl + '">' + esc(s.last_regatta_name) + '</a>' : esc(s.last_regatta_name))
                    : '—';
                var search = esc(((s.sailor_name || '') + ' ' + clubCode + ' ' + (s.last_regatta_name || '')).toLowerCase());
                return '<tr data-search="' + search + '"><td>' + (i + 1) + '</td><td class="cell-left">' + rowAv(s.avatar_url) + '<a href="' + url + '">' + esc(s.sailor_name || s.sas_id || '') + '</a></td><td class="cell-left hide-mobile">' + clubCell + '</td><td>' + (s.races_in_class != null ? s.races_in_class : '—') + '</td><td>' + (s.regattas_in_class != null ? s.regattas_in_class : '—') + '</td><td class="cell-nowrap">' + esc(rank) + '</td><td>' + lastCell + '</td></tr>';
            }).join('');"""

NEW_ROWS = """            function splitSailorName(name) {
                var n = String(name || '').trim();
                if (!n) return { first: 'Sailor', last: '' };
                if (n.indexOf(',') !== -1) {
                    var bits = n.split(',');
                    return { first: bits[0].trim(), last: bits.slice(1).join(',').trim() };
                }
                var sp = n.split(/\\s+/);
                return { first: sp[0], last: sp.slice(1).join(' ') };
            }
            function classSailorCard(s) {
                var name = s.sailor_name || String(s.sas_id || 'Sailor');
                var parts = splitSailorName(name);
                var slug = s.sailor_slug || '';
                var href = slug ? '/sailor/' + encodeURIComponent(slug) : '';
                var sas = String(s.sas_id || '').trim();
                var av = (s.avatar_url || '/assets/avatars/default-youth.png').trim();
                var clubCode = (s.club_code || '').trim().toUpperCase();
                var clubImg = (s.club_logo_url || (clubCode ? '/api/club-logo/' + encodeURIComponent(clubCode) : '')).trim();
                var hay = esc((name + ' ' + sas + ' ' + clubCode).toLowerCase());
                var clubHtml = (clubImg || clubCode)
                    ? ('<span class="club-dev1-fallback-club">' +
                        (clubImg ? '<img src="' + esc(clubImg) + '" alt="" loading="lazy" decoding="async">' : '') +
                        (clubCode ? '<span>' + esc(clubCode) + '</span>' : '') +
                        '</span>')
                    : '';
                var fallback = '<a class="club-dev1-fallback" href="' + esc(href || '#') + '">' +
                    '<img class="club-dev1-fallback-av" src="' + esc(av) + '" alt="" loading="lazy" decoding="async">' +
                    '<span class="club-dev1-fallback-name"><b>' + esc(parts.first) + '</b><span>' + esc(parts.last) + '</span></span>' +
                    clubHtml + '</a>';
                return '<div class="ssa-dev1-inject club-home-sailor-slot" data-search="' + hay + '" data-sas-id="' + esc(sas) + '" data-href="' + esc(href) + '">' + fallback + '</div>';
            }
            var sailorCards = sailors.map(classSailorCard).join('');
            var sailorsHtml =
                '<div class="club-home-cards-stack class-gold-sailor-cards">' +
                '<style id="class-gold-sailor-cards-style">' +
                '.class-gold-page .club-home-sailor-list{display:flex;flex-direction:column;gap:10px;width:100%;}' +
                '.class-gold-page .club-home-sailor-slot,.class-gold-page .club-home-sailor-slot .sa-approved-sailor-card{width:100%;max-width:100%;box-sizing:border-box;}' +
                '.class-gold-page .club-home-sailor-slot .sa-approved-sailor-card{margin:0;}' +
                '.class-gold-page .club-dev1-fallback{display:grid;grid-template-columns:76px minmax(0,1fr) auto;gap:10px;align-items:center;min-height:76px;padding:8px 10px;border:3px solid #6c8ebd;border-radius:22px;text-decoration:none;color:#142b5f;background:#fff;box-sizing:border-box;}' +
                '.class-gold-page .club-dev1-fallback-av{width:76px;height:76px;border-radius:999px;object-fit:cover;background:#eef4fb;}' +
                '.class-gold-page .club-dev1-fallback-name{display:flex;flex-direction:column;min-width:0;overflow-wrap:anywhere;}' +
                '.class-gold-page .club-dev1-fallback-name b{font-size:1.05rem;}' +
                '.class-gold-page .club-dev1-fallback-club{display:inline-flex;flex-direction:column;align-items:center;gap:3px;}' +
                '.class-gold-page .club-dev1-fallback-club img{height:34px;width:auto;max-width:56px;object-fit:contain;}' +
                '@media (max-width:768px){' +
                '.class-gold-page .club-dev1-fallback{grid-template-columns:76px minmax(0,1fr);}' +
                '}' +
                '</style>' +
                '<div class="card stats-section club-sailors-section" id="sailors">' +
                classToggleTitle('Sailors (' + sailors.length + ')', 'class-home-sailors-list') +
                '<input type="search" class="club-home-card-filter" data-list="class-home-sailors-list" placeholder="Search sailors name…" autocomplete="off">' +
                '<div class="club-list-body" hidden>' +
                '<div class="club-home-sailor-list" id="class-home-sailors-list">' + sailorCards + '</div>' +
                '<p id="class-home-sailors-empty" role="status" style="display:none">No sailors match your search.</p>' +
                '</div></div></div>';"""

OLD_TABLE = """            var sailorsTable = '<table class="table" id="class-sailors-table"><thead><tr><th>#</th><th>Sailor</th><th class="hide-mobile">Club</th><th>Races</th><th>Regattas</th><th>Last result</th><th>Last regatta</th></tr></thead><tbody>' +
                (sailorRows || '<tr><td colspan="7">No sailors</td></tr>') + '</tbody></table>';"""

NEW_TABLE = ""

OLD_SECTION = """                (clubs.length ? section('clubs', 'Clubs sailing ' + className + ' (' + clubs.length + ')', 'class-clubs-table', clubsTable) : '') +
                section('sailors', 'Sailors (' + sailors.length + ')', 'class-sailors-table', sailorsTable) +"""

NEW_SECTION = """                (clubs.length ? section('clubs', 'Clubs sailing ' + className + ' (' + clubs.length + ')', 'class-clubs-table', clubsTable) : '') +
                sailorsHtml +"""

OLD_FILTER = """                    list.querySelectorAll('.sa-home-regatta-card').forEach(function(c) {
                        var hay = c.getAttribute('data-search') || '';
                        c.style.display = (!q || hay.indexOf(q) !== -1) ? '' : 'none';
                    });"""

NEW_FILTER = """                    var shown = 0;
                    list.querySelectorAll('.sa-home-regatta-card, .club-home-sailor-slot').forEach(function(c) {
                        var hay = c.getAttribute('data-search') || '';
                        var ok = (!q || hay.indexOf(q) !== -1);
                        c.style.display = ok ? '' : 'none';
                        if (ok) shown += 1;
                    });
                    var empty = document.getElementById('class-home-sailors-empty');
                    if (empty && list.id === 'class-home-sailors-list') empty.style.display = shown ? 'none' : 'block';"""

OLD_BIND_END = """                if (inp) inp.addEventListener('input', sync);
                sync();
            });
            if (typeof attachSortableTables === 'function') attachSortableTables(cv);"""

NEW_BIND_END = """                if (inp) inp.addEventListener('input', sync);
                sync();
            });
            (function loadClassSailorCards() {
                var list = document.getElementById('class-home-sailors-list');
                if (!list) return;
                function mount(slot, html) {
                    var box = document.createElement('div');
                    box.innerHTML = html;
                    var lock = box.querySelector('#dev1-viewport-locks');
                    if (lock) {
                        if (!document.getElementById('dev1-viewport-locks')) document.head.appendChild(lock);
                        else if (lock.parentNode) lock.parentNode.removeChild(lock);
                    }
                    box.querySelectorAll('script').forEach(function(sc) { if (sc.parentNode) sc.parentNode.removeChild(sc); });
                    slot.innerHTML = '';
                    while (box.firstChild) slot.appendChild(box.firstChild);
                    var href = slot.getAttribute('data-href') || '';
                    var sid = slot.getAttribute('data-sas-id') || '';
                    slot.querySelectorAll('a.sa-claim-banner').forEach(function(a) {
                        var u = '/signup.html?signup=1';
                        if (sid) u += '&sas_id=' + encodeURIComponent(sid);
                        a.setAttribute('href', u);
                    });
                    var card = slot.querySelector('.sa-approved-sailor-card');
                    if (card && href) {
                        card.style.cursor = 'pointer';
                        card.addEventListener('click', function(ev) {
                            if (ev.target.closest('a')) return;
                            location.href = href;
                        });
                    }
                }
                function load(slot) {
                    if (!slot || slot.getAttribute('data-card-loaded') === '1') return;
                    slot.setAttribute('data-card-loaded', '1');
                    var sid = slot.getAttribute('data-sas-id') || '';
                    if (!sid) return;
                    fetch('/dev-1?embed=1&sas_id=' + encodeURIComponent(sid), { credentials: 'same-origin' })
                        .then(function(r) { if (!r.ok) throw new Error('x'); return r.text(); })
                        .then(function(html) { if (html && html.charAt(0) !== '{') mount(slot, html); })
                        .catch(function() {});
                }
                var slots = [].slice.call(list.querySelectorAll('.club-home-sailor-slot[data-sas-id]'));
                slots.slice(0, 3).forEach(load);
                if (typeof IntersectionObserver === 'function') {
                    var io = new IntersectionObserver(function(entries) {
                        entries.forEach(function(en) {
                            if (!en.isIntersecting) return;
                            io.unobserve(en.target);
                            load(en.target);
                        });
                    }, { root: null, rootMargin: '500px 0px', threshold: 0.01 });
                    slots.slice(3).forEach(function(s) { io.observe(s); });
                } else {
                    slots.slice(3).forEach(load);
                }
            })();
            if (typeof attachSortableTables === 'function') attachSortableTables(cv);"""


def main() -> None:
    text = INDEX.read_text(encoding="utf-8")
    if MARK in text:
        print("ALREADY")
        return
    miss = []
    for name, old in (
        ("ROWS", OLD_ROWS),
        ("TABLE", OLD_TABLE),
        ("SECTION", OLD_SECTION),
        ("FILTER", OLD_FILTER),
        ("BIND", OLD_BIND_END),
    ):
        if old not in text:
            miss.append(name)
    if miss:
        raise SystemExit("MISSING:" + ",".join(miss))
    ts = time.strftime("%Y%m%d_%H%M%S")
    bak = INDEX.with_name(INDEX.name + ".bak.class_sailors." + ts)
    shutil.copy2(INDEX, bak)
    text = text.replace(OLD_ROWS, NEW_ROWS, 1)
    text = text.replace(OLD_TABLE, NEW_TABLE, 1)
    text = text.replace(OLD_SECTION, NEW_SECTION, 1)
    text = text.replace(OLD_FILTER, NEW_FILTER, 1)
    text = text.replace(OLD_BIND_END, NEW_BIND_END, 1)
    text = text.replace("</head>", "<!-- " + MARK + " --></head>", 1)
    INDEX.write_text(text)
    print("OK", MARK, "BAK", str(bak))


if __name__ == "__main__":
    main()
