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
  var CSS_ID = 'midmar-leaderboard-css';
  var POLL_MS = 15000;
  var MEDAL = { 1: '\uD83E\uDD47', 2: '\uD83E\uDD48', 3: '\uD83E\uDD49' };
  var ORD = { 1: '1st', 2: '2nd', 3: '3rd' };
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
    return '<a href="/sailor/' + esc(sl) + '">' + esc(n) + '</a>';
  }

  function logoChip(src, title, href, label) {
    var img =
      '<img class="rs-club-row-logo-sm" src="' +
      src +
      '" alt="" title="' +
      esc(title) +
      '" loading="lazy" decoding="async">';
    var text = href
      ? '<a href="' + esc(href) + '" title="' + esc(title) + '">' + esc(label) + '</a>'
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

  function boatHtml(row) {
    var bn = String(row.boat_name || '').trim();
    if (!bn) return '';
    var sp = sponsorFor(bn);
    if (!sp) return esc(bn);
    return logoChip(
      '/artwork/Sponsor%20Logo/' + encodeURIComponent(sp.file) + '?v=20260912c',
      sp.alt,
      sp.href,
      bn
    );
  }

  function sailHtml(row) {
    var sn = String(row.sail_number || row.sail_no || '').trim();
    if (!sn) return '';
    return '<span class="midmar-lb-sail">' + esc(sn) + '</span>';
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
    if (document.getElementById(CSS_ID)) return;
    var s = document.createElement('style');
    s.id = CSS_ID;
    s.textContent =
      /* Same chrome as weather .card: 2px navy, 8px corners, light shadow. */
      '.regatta-page > .midmar-live-media .midmar-lb.card{' +
      'order:0;margin:10px 0 0;width:100%;max-width:100%;box-sizing:border-box;' +
      'padding:6px 10px;border:2px solid #001f3f!important;border-radius:8px!important;' +
      'box-shadow:0 1px 3px rgba(0,31,63,0.08);background:#fff;overflow:hidden;}' +
      '.regatta-page > .midmar-live-media .ssa-regatta-slot-card{order:1;}' +
      '.regatta-page > .midmar-live-media .midmar-mm-row{order:2;}' +
      '.regatta-page > .midmar-live-media .mm-lipton-reels.card{' +
      'border:2px solid #001f3f!important;border-radius:8px!important;' +
      'box-shadow:0 1px 3px rgba(0,31,63,0.08);box-sizing:border-box;width:100%;max-width:100%;}' +
      '.regatta-page > .midmar-lb.card{' +
      'margin:10px 0 0;width:100%;max-width:100%;box-sizing:border-box;' +
      'padding:6px 10px;border:2px solid #001f3f!important;border-radius:8px!important;' +
      'box-shadow:0 1px 3px rgba(0,31,63,0.08);background:#fff;overflow:hidden;}' +
      '.midmar-lb .section-title{margin:0 0 2px;padding:0 0 2px;font-size:0.75rem;line-height:1.2;}' +
      '.midmar-lb-sheet-note{margin:0 0 4px;font-size:0.7rem;line-height:1.2;font-weight:500;' +
      'color:#334155;text-transform:none;letter-spacing:0;}' +
      '.midmar-lb-list{margin:0;padding:0;}' +
      /* MP first: wrap. A rank may use two lines (meta + helm/crew). */
      '.midmar-lb-row{display:flex;flex-wrap:wrap;align-items:center;gap:4px 8px;' +
      'padding:4px 0;border-bottom:1px solid #e0e0e0;font-size:0.85rem;line-height:1.25;color:#1e293b;}' +
      '.midmar-lb-row:last-child{border-bottom:0;}' +
      '.midmar-lb-rank{flex:0 0 auto;display:inline-flex;align-items:center;gap:4px;font-weight:700;color:#001f3f;white-space:nowrap;}' +
      '.midmar-lb-medal{font-size:1rem;line-height:1;}' +
      '.midmar-lb-boat{flex:0 1 auto;font-weight:700;color:#001f3f;min-width:0;}' +
      '.midmar-lb-sail{flex:0 0 auto;font-weight:700;color:#001f3f;white-space:nowrap;}' +
      '.midmar-lb-boat a,.midmar-lb-club a,.midmar-lb-people a{color:#001f3f;text-decoration:none;}' +
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

  function paint(card, rows) {
    var list = card.querySelector('[data-mm-lb-list]');
    if (!list) return;
    var podium = (rows || [])
      .filter(function (r) {
        var n = Number(r.rank);
        return n >= 1 && n <= 3 && hasScore(r);
      })
      .sort(function (a, b) {
        return Number(a.rank) - Number(b.rank);
      });
    if (!podium.length) {
      list.innerHTML = '<p class="midmar-lb-empty">Waiting for race scores</p>';
      return;
    }
    list.innerHTML = podium
      .map(function (row) {
        var n = Number(row.rank);
        var boat = boatHtml(row);
        var sail = sailHtml(row);
        var club = clubChip(row.club_abbrev || row.club_raw);
        return (
          '<div class="midmar-lb-row" data-rank="' +
          n +
          '">' +
          joinSets([
            '<span class="midmar-lb-rank"><span class="midmar-lb-medal" aria-hidden="true">' +
              (MEDAL[n] || '') +
              '</span> ' +
              ORD[n] +
              '</span>',
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
      })
      .catch(function () {});
  }

  function boot() {
    if (!onMidmar()) return;
    injectCss();
    var card = placeCard();
    if (!card) return;
    load(card);
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
