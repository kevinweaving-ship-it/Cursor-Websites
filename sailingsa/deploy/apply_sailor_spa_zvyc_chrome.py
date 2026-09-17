#!/usr/bin/env python3
"""Patch sailor_spa class cards to ZVYC gold: host club logo + orange show/hide."""
from pathlib import Path
import shutil
import time

INDEX = Path("/var/www/sailingsa/index.sailor_spa.html")
MARK = "CLASS_ZVYC_CHROME_v1"

OLD_HOST = """                var hostInner = '<div class="sa-home-regatta-host-text">' +
                    (hostCode ? '<div class="sa-home-regatta-host-code">' + esc(hostCode) + '</div>' : '') +
                    '</div>';"""

NEW_HOST = """                var hostLogoSrc = (r.club_logo_url || (hostCode ? ('/artwork/Club Logo/' + hostCode + '.png') : '')).trim();
                var hostLogo = hostLogoSrc
                    ? '<img class="sa-home-regatta-host-logo" src="' + esc(hostLogoSrc) + '" alt="" loading="lazy" decoding="async" onerror="this.onerror=null;this.src=\\'/api/club-logo/' + esc(hostCode) + '\\';">'
                    : '';
                var hostInner = hostLogo + '<div class="sa-home-regatta-host-text">' +
                    (hostCode ? '<div class="sa-home-regatta-host-code">' + esc(hostCode) + '</div>' : '') +
                    '</div>';"""

OLD_SECTION = """            function eventSection(title, list, panel, listId) {
                if (!list.length) return '';
                var cards = list.map(function(r) { return classEventCard(r, panel); }).join('');
                return '<div class="card stats-section club-' + panel + '-events-section">' +
                    '<h2 class="section-title">' + esc(title) + ' (' + list.length + ')</h2>' +
                    '<input type="search" class="club-home-card-filter" data-list="' + listId + '" placeholder="Search ' + esc(title.toLowerCase()) + '…" autocomplete="off">' +
                    '<div class="sa-home-regatta-wrap"><div class="sa-home-regatta-list" id="' + listId + '">' + cards + '</div></div></div>';
            }"""

NEW_SECTION = """            function classToggleTitle(title, listId) {
                return '<h2 class="section-title club-section-title-row">' + esc(title) +
                    '<button type="button" class="sa-avatar-expand-btn club-list-expand-btn" aria-expanded="false" aria-controls="' + esc(listId) + '" title="Show/Hide List">' +
                    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="18" height="18" aria-hidden="true">' +
                    '<path fill="#FF5A00" d="M231.39,132.94A8,8,0,0,0,224,128H184V104a8,8,0,0,0-8-8H80a8,8,0,0,0-8,8v24H32a8,8,0,0,0-5.66,13.66l96,96a8,8,0,0,0,11.32,0l96-96A8,8,0,0,0,231.39,132.94ZM72,40a8,8,0,0,1,8-8h96a8,8,0,0,1,0,16H80A8,8,0,0,1,72,40Zm0,32a8,8,0,0,1,8-8h96a8,8,0,0,1,0,16H80A8,8,0,0,1,72,72Z"></path>' +
                    '</svg></button>' +
                    '<span class="club-list-expand-label">Show/Hide List</span></h2>';
            }
            function eventSection(title, list, panel, listId) {
                if (!list.length) return '';
                var cards = list.map(function(r) { return classEventCard(r, panel); }).join('');
                var heading = (panel === 'past')
                    ? classToggleTitle(title + ' (' + list.length + ')', listId)
                    : '<h2 class="section-title">' + esc(title) + ' (' + list.length + ')</h2>';
                var bodyOpen = (panel === 'past') ? '<div class="club-list-body" hidden>' : '';
                var bodyClose = (panel === 'past') ? '</div>' : '';
                return '<div class="card stats-section club-' + panel + '-events-section">' +
                    heading +
                    '<input type="search" class="club-home-card-filter" data-list="' + listId + '" placeholder="Search ' + esc(title.toLowerCase()) + '…" autocomplete="off">' +
                    bodyOpen + '<div class="sa-home-regatta-wrap"><div class="sa-home-regatta-list" id="' + listId + '">' + cards + '</div></div>' + bodyClose + '</div>';
            }"""

OLD_CSS_TOP = ".class-gold-page .sa-home-regatta-top{display:grid;grid-template-columns:104px minmax(0,1fr) minmax(72px,120px) auto;grid-template-areas:\"logo main host actions\";gap:14px;align-items:center;}"
NEW_CSS_TOP = ".class-gold-page .sa-home-regatta-top{display:grid;grid-template-columns:104px minmax(0,1fr) minmax(200px,252px) auto;grid-template-areas:\"logo main host actions\";gap:14px;align-items:center;}"

OLD_CSS_HOST = """.class-gold-page .sa-home-regatta-host{grid-area:host;display:flex;align-items:center;text-decoration:none;color:inherit;min-height:44px;}' +
                '.class-gold-page .sa-home-regatta-host-code{font-weight:900;color:#21356b;font-size:14px;}' +"""

NEW_CSS_HOST = """.class-gold-page .sa-home-regatta-host{grid-area:host;display:flex;align-items:center;gap:10px;min-width:0;color:inherit;text-decoration:none;min-height:44px;}' +
                '.class-gold-page .sa-home-regatta-host-logo{display:block;width:84px;height:44px;object-fit:contain;border:none;background:transparent;flex:0 0 auto;}' +
                '.class-gold-page .sa-home-regatta-host-text{display:flex;flex-direction:column;gap:2px;min-width:0;}' +
                '.class-gold-page .sa-home-regatta-host-code{font-weight:900;color:#21356b;font-size:14px;line-height:1.05;}' +
                '.class-gold-page .club-section-title-row{display:flex;flex-wrap:wrap;align-items:center;gap:8px;}' +
                '.class-gold-page .club-list-expand-btn{display:inline-flex;align-items:center;justify-content:center;width:44px;height:44px;min-width:44px;min-height:44px;margin:0;padding:0;border:0;background:transparent;color:#FF5A00;cursor:pointer;}' +
                '.class-gold-page .club-list-expand-btn svg{display:block;width:18px;height:18px;fill:#FF5A00;transition:transform .18s ease;}' +
                '.class-gold-page .club-list-expand-btn[aria-expanded="true"] svg{transform:rotate(180deg);}' +
                '.class-gold-page .club-list-expand-label{font-size:.85rem;font-weight:700;color:#475569;}' +
                '.class-gold-page .club-list-body[hidden]{display:none!important;}' +"""

OLD_TABLE_SECTION = """            function section(id, title, filterId, tableHtml) {
                return '<div class="section-heading-row" id="' + id + '">' +
                    '<h2 class="section-title">' + esc(title) + '</h2>' +
                    '<input type="search" class="club-table-filter" data-table="' + filterId + '" placeholder="Search…" autocomplete="off">' +
                    '</div><div class="table-container club-table-scroll">' + tableHtml + '</div>';
            }"""

NEW_TABLE_SECTION = """            function section(id, title, filterId, tableHtml) {
                return '<div class="card stats-section" id="' + id + '">' +
                    classToggleTitle(title, filterId) +
                    '<input type="search" class="club-table-filter" data-table="' + filterId + '" placeholder="Search…" autocomplete="off">' +
                    '<div class="club-list-body" hidden><div class="table-container club-table-scroll">' + tableHtml + '</div></div></div>';
            }"""

OLD_BIND = """            cv.querySelectorAll('.club-home-card-filter').forEach(function(inp) {
                inp.addEventListener('input', function() {
                    var list = document.getElementById(inp.getAttribute('data-list'));"""

NEW_BIND_PREFIX = """            cv.querySelectorAll('.club-list-expand-btn').forEach(function(btn) {
                if (btn.getAttribute('data-bound') === '1') return;
                btn.setAttribute('data-bound', '1');
                var sec = btn.closest('.card') || btn.closest('.stats-section') || btn.parentElement;
                function sync() {
                    var body = sec && sec.querySelector('.club-list-body');
                    if (!btn || !body) return;
                    var inp = sec.querySelector('.club-home-card-filter, .club-table-filter');
                    var q = ((inp && inp.value) || '').trim();
                    var open = btn.getAttribute('aria-expanded') === 'true';
                    if (open || q) body.removeAttribute('hidden');
                    else body.setAttribute('hidden', '');
                }
                btn.addEventListener('click', function() {
                    btn.setAttribute('aria-expanded', btn.getAttribute('aria-expanded') === 'true' ? 'false' : 'true');
                    sync();
                });
                var inp = sec && sec.querySelector('.club-home-card-filter, .club-table-filter');
                if (inp) inp.addEventListener('input', sync);
                sync();
            });
            cv.querySelectorAll('.club-home-card-filter').forEach(function(inp) {
                inp.addEventListener('input', function() {
                    var list = document.getElementById(inp.getAttribute('data-list'));"""


def main() -> None:
    text = INDEX.read_text(encoding="utf-8")
    if MARK in text:
        print("ALREADY")
        return
    miss = []
    for name, old in (
        ("HOST", OLD_HOST),
        ("SECTION", OLD_SECTION),
        ("CSS_TOP", OLD_CSS_TOP),
        ("CSS_HOST", OLD_CSS_HOST),
        ("TABLE", OLD_TABLE_SECTION),
        ("BIND", OLD_BIND),
    ):
        if old not in text:
            miss.append(name)
    if miss:
        raise SystemExit("MISSING:" + ",".join(miss))
    ts = time.strftime("%Y%m%d_%H%M%S")
    bak = INDEX.with_name(INDEX.name + ".bak.zvyc_chrome." + ts)
    shutil.copy2(INDEX, bak)
    text = text.replace(OLD_HOST, NEW_HOST, 1)
    text = text.replace(OLD_SECTION, NEW_SECTION, 1)
    text = text.replace(OLD_CSS_TOP, NEW_CSS_TOP, 1)
    text = text.replace(OLD_CSS_HOST, NEW_CSS_HOST, 1)
    text = text.replace(OLD_TABLE_SECTION, NEW_TABLE_SECTION, 1)
    text = text.replace(OLD_BIND, NEW_BIND_PREFIX, 1)
    text = text.replace("</head>", "<!-- " + MARK + " --></head>", 1)
    INDEX.write_text(text, encoding="utf-8")
    print("OK", MARK, "BAK", str(bak))


if __name__ == "__main__":
    main()
