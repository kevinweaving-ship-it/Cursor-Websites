/**
 * Midmar Cup — compact live Leader Board between event header and weather.
 * Same card chrome as weather: 2px #001f3f, 8px corners. MP first: a rank may wrap to 2 lines.
 * Each dataset (rank | boat | sail | club | helm & crew) is separated by a divider.
 * Boat name uses sponsor logo | divider | name when a brand is known (same as results).
 */
(function () {
  'use strict';
  if (window.__SSA_MIDMAR_LEADERBOARD__) return;
  window.__SSA_MIDMAR_LEADERBOARD__ = true;

  var RID = '2026-09-19-hmyc-midmar-cup';
  var CARD_ID = 'midmar-leaderboard';
  var CSS_ID = 'midmar-leaderboard-css-v10';
  var POLL_MS = 15000;
  /* Historical Hunter names, temp until confirmed. 2013 Essex Girl + 442 Scout confirmed. */
  var TEMP_BOATS = {
    '741': 'Bueno Vento',
    '40': "Odin's Eye",
  };
  var MEDAL = { 1: '\uD83E\uDD47', 2: '\uD83E\uDD48', 3: '\uD83E\uDD49' };
  var SPONSORS = [
    { test: function (n) { return n === 'puffin'; }, file: 'Ullman-Sails.png', alt: 'Ullman Sails', href: '/sponsors/ullman' },
    { re: /ullman(\s+sails)?/, file: 'Ullman-Sails.png', alt: 'Ullman Sails', href: '/sponsors/ullman' },
    { re: /north\s+sails/, file: 'North-Sails.png', alt: 'North Sails', href: '/sponsors/north' },
    { re: /cell\s*c\b/, file: 'Cell-C.png', alt: 'Cell C', href: '/sponsors/cell-c' },
    { re: /\bamtec\b/, file: 'AMTEC.png', alt: 'AMTEC', href: '/sponsors/amtec' },
    { re: /nitro/, file: 'Nitro.png', alt: 'Nitro', href: '/sponsors/nitro' },
    { re: /\bh2[0o]\b/, file: 'H2O.png', alt: 'H2O', href: '/sponsors/h2o' },
  ];

  function onMidmar() {
    var path = String((window.location && window.location.pathname) || '')
      .replace(/\/+$/, '')
      .toLowerCase();
    return path === '/regatta/' + RID || path.indexOf('/regatta/' + RID + '/') === 0;
  }

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function slug(name) {
    return String(name || '')
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '');
  }

  function sailorLink(name) {
    var n = String(name || '').trim();
    if (!n) return '';
    var sl = slug(n);
    if (!sl) return esc(n);
    return '<a class="class-link-valid" href="/sailor/' + esc(sl) + '">' + esc(n) + '</a>';
  }

  function logoChip(src, title, href, label, logoHref) {
    var img =
      '<img class="rs-club-row-logo-sm" src="' +
      src +
      '" alt="" title="' +
      esc(title) +
      '" loading="lazy" decoding="async">';
    var imgHref = logoHref || href;
    if (imgHref) {
      img =
        '<a class="midmar-lb-logo-link" href="' +
        esc(imgHref) +
        '" title="' +
        esc(title) +
        '">' +
        img +
        '</a>';
    }
    var text = href
      ? '<a class="class-link-valid" href="' + esc(href) + '" title="' + esc(label) + '">' + esc(label) + '</a>'
      : esc(label);
    return '<span class="rs-club-with-logo">' + img + text + '</span>';
  }

  function clubChip(code) {
    var c = String(code || '').trim().toUpperCase();
    if (!c) return '';
    return logoChip(
      '/artwork/Club%20Logo/' + encodeURIComponent(c) + '.png?v=20260912c',
      c,
      '/club/' + encodeURIComponent(c.toLowerCase()),
      c
    );
  }

  function sponsorFor(name) {
    var n = String(name || '').trim();
    var low = n.toLowerCase();
    var i;
    for (i = 0; i < SPONSORS.length; i++) {
      var s = SPONSORS[i];
      if (s.test && s.test(low)) return s;
      if (s.re && s.re.test(low)) return s;
    }
    return null;
  }

  function isTempBoat(row) {
    var sn = String(row.sail_number || row.sail_no || row.sail || '').trim();
    var bn = String(row.boat_name || '').trim();
    var expected = TEMP_BOATS[sn];
    return !!(expected && bn && expected.toLowerCase() === bn.toLowerCase());
  }

  function boatHref(row) {
    var sn = String(row.sail_number || row.sail_no || row.sail || '').trim();
    var bn = String(row.boat_name || '').trim();
    if (!sn && !bn) return '';
    var q = 'class=' + encodeURIComponent('Hunter 19');
    if (sn) q += '&sail=' + encodeURIComponent(sn);
    if (bn) q += '&name=' + encodeURIComponent(bn);
    return '/boat_pedigree.html?' + q;
  }

  function boatHtml(row) {
    var bn = String(row.boat_name || '').trim();
    if (!bn) return '';
    var href = boatHref(row);
    var sp = sponsorFor(bn);
    var inner = sp
      ? logoChip(
          '/artwork/Sponsor%20Logo/' + encodeURIComponent(sp.file) + '?v=20260912c',
          sp.alt,
          href,
          bn,
          sp.href
        )
      : href
        ? '<a class="class-link-valid" href="' + esc(href) + '" title="' + esc(bn) + '">' + esc(bn) + '</a>'
        : esc(bn);
    if (!isTempBoat(row)) return inner;
    return (
      '<span class="midmar-lb-boat-temp" title="Temporary name — unconfirmed">' +
      inner +
      '</span>'
    );
  }

  function ord(n) {
    var v = Number(n);
    if (v === 1) return '1st';
    if (v === 2) return '2nd';
    if (v === 3) return '3rd';
    if (!v) return '';
    return v + 'th';
  }

  function nettHtml(row) {
    var n = Number(row.nett_points_raw);
    if (!isFinite(n) || n <= 0) return '';
    var shown = Math.abs(n - Math.round(n)) < 0.05 ? String(Math.round(n)) : String(n);
    return '<span class="midmar-lb-nett">' + esc(shown) + 'pt</span>';
  }

  function sailHtml(row) {
    var sn = String(row.sail_number || row.sail_no || row.sail || '').trim();
    if (!sn) return '';
    var sl = slug(row.helm_name);
    var href = sl ? '/sailor/' + sl : boatHref(row);
    var inner = href
      ? '<a class="class-link-valid" href="' + esc(href) + '" title="Sail number">' + esc(sn) + '</a>'
      : esc(sn);
    return '<span class="midmar-lb-sail">' + inner + '</span>';
  }

  function sepHtml() {
    return '<span class="midmar-lb-sep" aria-hidden="true"></span>';
  }

  function joinSets(parts) {
    return parts.filter(Boolean).join(sepHtml());
  }

  function peopleHtml(row) {
    var helm = String(row.helm_name || '').trim();
    var parts = [];
    if (row.crew_name) parts.push(String(row.crew_name).trim());
    if (row.crew2_name) parts.push(String(row.crew2_name).trim());
    if (row.crew3_name) parts.push(String(row.crew3_name).trim());
    var crew = parts.filter(Boolean);
    var html = sailorLink(helm);
    if (crew.length) {
      html +=
        ' <span class="midmar-lb-amp">&amp;</span> ' + crew.map(sailorLink).join(', ');
    }
    return html;
  }

  function hasScore(row) {
    if (row.nett_points_raw != null && Number(row.nett_points_raw) > 0) return true;
    var rs = row.race_scores;
    if (!rs) return false;
    if (typeof rs === 'string') {
      try {
        rs = JSON.parse(rs);
      } catch (e) {
        return false;
      }
    }
    if (typeof rs !== 'object') return false;
    var k;
    for (k in rs) {
      if (Object.prototype.hasOwnProperty.call(rs, k) && String(rs[k] || '').trim()) return true;
    }
    return false;
  }

  function injectCss() {
    ['midmar-leaderboard-css', 'midmar-leaderboard-css-v4', 'midmar-leaderboard-css-v5', 'midmar-leaderboard-css-v6', 'midmar-leaderboard-css-v7', 'midmar-leaderboard-css-v8', 'midmar-leaderboard-css-v9'].forEach(function (id) {
      var prev = document.getElementById(id);
      if (prev && prev.parentNode) prev.parentNode.removeChild(prev);
    });
    if (document.getElementById(CSS_ID)) return;
    var s = document.createElement('style');
    s.id = CSS_ID;
    s.textContent =
      /* Undo the extra wrap border. Event header card keeps its own chrome. */
      '.regatta-page > .regatta-header-wrap{' +
      'border:0!important;box-shadow:none!important;border-radius:0!important;' +
      'background:transparent!important;}' +
      /* One navy card each: Leader Board, Weather, Media. Do not style header/admin. */
      '.regatta-page > .midmar-live-media > #midmar-leaderboard.card,' +
      '.regatta-page > .midmar-live-media > #ssa-regatta-slot-card,' +
      '.regatta-page > .midmar-live-media > .mm-lipton-reels{' +
      'border:2px solid #001f3f!important;border-radius:8px!important;' +
      'box-shadow:0 1px 3px rgba(0,31,63,0.08)!important;' +
      'width:100%!important;max-width:100%!important;box-sizing:border-box!important;' +
      'margin-left:0!important;margin-right:0!important;}' +
      '.regatta-page > .midmar-live-media > #midmar-leaderboard.card{' +
      'order:0;margin:10px 0 0;padding:6px 10px;background:#fff;overflow:hidden;}' +
      '.regatta-page > .midmar-live-media > #ssa-regatta-slot-card{order:1;margin-top:10px;padding:0!important;}' +
      '.regatta-page > .midmar-live-media > .mm-lipton-reels{order:2;margin-top:10px;overflow:hidden;}' +
      '.regatta-page > .midmar-live-media .ssa-wx-card .card,' +
      '.regatta-page > .midmar-live-media .mm-lipton-reels .card,' +
      '.regatta-page > .midmar-live-media .mm-lipton-reels-compact{' +
      'border:0!important;box-shadow:none!important;}' +
      '@media screen and (orientation:portrait) and (max-width:767px){' +
      '.regatta-page > .midmar-live-media > #ssa-regatta-slot-card,' +
      '.regatta-page > .midmar-live-media > .mm-lipton-reels,' +
      '.regatta-page > .midmar-live-media > .midmar-hmyc-cam:not(.is-open){' +
      'width:100%!important;max-width:100%!important;' +
      'margin-left:0!important;margin-right:0!important;}' +
      '}' +
      '.midmar-lb .section-title{margin:0 0 2px;padding:0 0 2px;font-size:0.75rem;line-height:1.2;}' +
      '.midmar-lb-sheet-note{margin:0 0 4px;font-size:0.7rem;line-height:1.2;font-weight:500;' +
      'color:#334155;text-transform:none;letter-spacing:0;}' +
      '.midmar-lb-list{margin:0;padding:0;}' +
      /* MP first: wrap. A rank may use two lines (meta + helm/crew). */
      '.midmar-lb-row{display:flex;flex-wrap:wrap;align-items:center;gap:4px 8px;' +
      'padding:4px 0;border-bottom:1px solid #e0e0e0;font-size:0.85rem;line-height:1.25;color:#1e293b;}' +
      '.midmar-lb-row:last-child{border-bottom:0;}' +
      '.midmar-lb-rank{flex:0 0 auto;display:inline-flex;align-items:center;gap:4px;font-weight:700;color:#001f3f;white-space:nowrap;}' +
      '.midmar-lb-nett{flex:0 0 auto;font-weight:800;color:#001f3f;white-space:nowrap;font-variant-numeric:tabular-nums;}' +
      '.midmar-lb-medal{font-size:1rem;line-height:1;}' +
      '.midmar-lb-boat{flex:0 1 auto;font-weight:700;color:#001f3f;min-width:0;}' +
      '.midmar-lb-boat-temp,.midmar-lb-boat-temp a,.fleet-results-table td.midmar-boat-temp,' +
      '.fleet-results-table td.midmar-boat-temp a{color:#94a3b8!important;font-weight:600;text-decoration:underline;}' +
      '.midmar-lb-sail{flex:0 0 auto;font-weight:800;color:#001f3f;white-space:nowrap;font-variant-numeric:tabular-nums;}' +
      '.midmar-lb-boat a,.midmar-lb-club a,.midmar-lb-people a,.midmar-lb-sail a,' +
      '.midmar-lb .rs-club-with-logo a,.midmar-lb a.class-link-valid{' +
      'color:#0000ee!important;text-decoration:underline!important;font-weight:600!important;}' +
      '.midmar-lb-boat a:visited,.midmar-lb-club a:visited,.midmar-lb-people a:visited,' +
      '.midmar-lb-sail a:visited,.midmar-lb .rs-club-with-logo a:visited,' +
      '.midmar-lb a.class-link-valid:visited{color:#0000ee!important;}' +
      '.midmar-lb-logo-link,.midmar-lb-logo-link:visited{display:inline-flex;align-items:center;text-decoration:none!important;}' +
      '.midmar-lb-logo-link img{cursor:pointer;}' +
      '.midmar-lb-club{flex:0 0 auto;}' +
      '.midmar-lb-sep{flex:0 0 auto;align-self:stretch;width:0;margin:0 1px;' +
      'border-left:1px solid rgba(26,39,80,0.22);}' +
      '.midmar-lb .rs-club-with-logo{display:inline-flex;align-items:center;}' +
      '.midmar-lb .rs-club-row-logo-sm{flex:0 0 22px;width:22px;max-width:22px;height:auto;max-height:16px;' +
      'object-fit:contain;box-sizing:content-box;padding-right:4px;margin-right:4px;' +
      'border-right:1px solid rgba(26,39,80,0.22);}' +
      '.midmar-lb-people{flex:1 1 100%;min-width:0;white-space:normal;}' +
      '.midmar-lb-empty{margin:0;font-size:0.8rem;color:#334155;}' +
      '@media screen and (orientation:landscape) and (min-width:768px){' +
      '.midmar-lb-people{flex:1 1 auto;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}' +
      '}' +
      '@media print{.midmar-lb.card{break-inside:avoid}}';
    document.head.appendChild(s);
  }

  function placeCard() {
    var card = document.getElementById(CARD_ID);
    if (!card) {
      card = document.createElement('section');
      card.id = CARD_ID;
      card.className = 'card midmar-lb';
      card.setAttribute('aria-label', 'Leader Board');
      card.innerHTML =
        '<h2 class="section-title">Leader Board</h2>' +
        '<p class="midmar-lb-sheet-note">Full Results sheet below on page</p>' +
        '<div class="midmar-lb-list" data-mm-lb-list></div>';
    } else {
      var title = card.querySelector('.section-title');
      if (title) title.textContent = 'Leader Board';
      if (!card.querySelector('.midmar-lb-sheet-note')) {
        var note = document.createElement('p');
        note.className = 'midmar-lb-sheet-note';
        note.textContent = 'Full Results sheet below on page';
        if (title && title.nextSibling) title.parentNode.insertBefore(note, title.nextSibling);
        else card.insertBefore(note, card.firstChild);
      }
    }
    var host = document.getElementById('midmar-live-media');
    var wx = document.getElementById('ssa-regatta-slot-card');
    var header = document.querySelector('.regatta-header-wrap');
    var page = document.querySelector('.regatta-page');
    if (host) {
      if (card.parentNode !== host) host.insertBefore(card, host.firstChild);
      if (wx && wx.parentNode === host && card.nextSibling !== wx) host.insertBefore(card, wx);
    } else if (wx && wx.parentNode) {
      if (card.nextSibling !== wx) wx.parentNode.insertBefore(card, wx);
    } else if (header && header.parentNode) {
      if (card.previousSibling !== header) header.parentNode.insertBefore(card, header.nextSibling);
    } else if (page) {
      page.insertBefore(card, page.firstChild);
    }
    return card;
  }

  function ensureTempCss(doc) {
    if (!doc || doc.getElementById('midmar-boat-temp-css')) return;
    var s = doc.createElement('style');
    s.id = 'midmar-boat-temp-css';
    s.textContent =
      '.fleet-results-table td.midmar-boat-temp,.fleet-results-table td.midmar-boat-temp a{' +
      'color:#94a3b8!important;font-weight:600;}';
    (doc.head || doc.documentElement).appendChild(s);
  }

  function eachFleetTable(fn) {
    document.querySelectorAll('.fleet-results-table').forEach(fn);
    document.querySelectorAll('iframe').forEach(function (fr) {
      try {
        var doc = fr.contentDocument;
        if (!doc) return;
        ensureTempCss(doc);
        doc.querySelectorAll('.fleet-results-table').forEach(fn);
      } catch (e) {}
    });
  }

  function greyFleetTemps() {
    eachFleetTable(function (table) {
      var headers = table.querySelectorAll('thead th');
      var boatIdx = -1;
      var sailIdx = -1;
      headers.forEach(function (th, i) {
        var t = String(th.textContent || '')
          .trim()
          .toLowerCase();
        if (t === 'boat name' || t === 'boat') boatIdx = i;
        if (t === 'sail no' || t === 'sail' || t === 'sail number') sailIdx = i;
      });
      if (boatIdx < 0) return;
      Array.prototype.forEach.call(table.querySelectorAll('tbody tr'), function (tr) {
        var tds = tr.children;
        if (!tds[boatIdx]) return;
        var bn = String(tds[boatIdx].textContent || '').trim();
        var sn = sailIdx >= 0 ? String(tds[sailIdx].textContent || '').trim() : '';
        var expected = TEMP_BOATS[sn];
        if (expected && bn && expected.toLowerCase() === bn.toLowerCase()) {
          tds[boatIdx].classList.add('midmar-boat-temp');
          tds[boatIdx].setAttribute('title', 'Temporary name — unconfirmed');
        } else {
          tds[boatIdx].classList.remove('midmar-boat-temp');
        }
      });
    });
  }

  function paint(card, rows) {
    var list = card.querySelector('[data-mm-lb-list]');
    if (!list) return;
    var board = (rows || [])
      .filter(function (r) {
        var n = Number(r.rank);
        return n >= 1 && n <= 3 && hasScore(r);
      })
      .sort(function (a, b) {
        return Number(a.rank) - Number(b.rank);
      });
    if (!board.length) {
      list.innerHTML = '<p class="midmar-lb-empty">Waiting for race scores</p>';
      return;
    }
    list.innerHTML = board
      .map(function (row) {
        var n = Number(row.rank);
        var boat = boatHtml(row);
        var sail = sailHtml(row);
        var club = clubChip(row.club_abbrev || row.club_raw);
        var medal = MEDAL[n]
          ? '<span class="midmar-lb-medal" aria-hidden="true">' + MEDAL[n] + '</span> '
          : '';
        return (
          '<div class="midmar-lb-row" data-rank="' +
          n +
          '">' +
          joinSets([
            '<span class="midmar-lb-rank">' + medal + ord(n) + '</span>',
            nettHtml(row),
            boat ? '<span class="midmar-lb-boat">' + boat + '</span>' : '',
            sail,
            club ? '<span class="midmar-lb-club">' + club + '</span>' : '',
            '<span class="midmar-lb-people">' + peopleHtml(row) + '</span>',
          ]) +
          '</div>'
        );
      })
      .join('');
  }

  function load(card) {
    fetch('/api/regatta/' + encodeURIComponent(RID), {
      credentials: 'same-origin',
      cache: 'no-store',
    })
      .then(function (r) {
        return r && r.ok ? r.json() : null;
      })
      .then(function (data) {
        var rows = Array.isArray(data) ? data : (data && data.results) || [];
        paint(card, rows);
        greyFleetTemps();
      })
      .catch(function () {});
  }

  function boot() {
    if (!onMidmar()) return;
    injectCss();
    var card = placeCard();
    if (!card) return;
    load(card);
    greyFleetTemps();
    if (card.getAttribute('data-mm-lb-bound') === '1') return;
    card.setAttribute('data-mm-lb-bound', '1');
    window.setInterval(function () {
      if (!document.hidden) load(card);
      placeCard();
    }, POLL_MS);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
