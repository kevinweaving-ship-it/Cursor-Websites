/**
 * Midmar Cup — compact live Leader Board between event header and weather.
 * 1st / 2nd / 3rd lines: medal, boat, club logo | code, helm & crew.
 * Polls /api/regatta/{id} so ranks stay current as scores arrive.
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

  function clubChip(code) {
    var c = String(code || '').trim().toUpperCase();
    if (!c) return '';
    var src = '/artwork/Club%20Logo/' + encodeURIComponent(c) + '.png?v=20260912c';
    var href = '/club/' + encodeURIComponent(c.toLowerCase());
    return (
      '<span class="rs-club-with-logo">' +
      '<img class="rs-club-row-logo-sm" src="' +
      src +
      '" alt="" title="' +
      esc(c) +
      '" loading="lazy" decoding="async">' +
      '<a href="' +
      href +
      '">' +
      esc(c) +
      '</a></span>'
    );
  }

  function peopleHtml(row) {
    var helm = String(row.helm_name || '').trim();
    var parts = [];
    if (row.crew_name) parts.push(String(row.crew_name).trim());
    if (row.crew2_name) parts.push(String(row.crew2_name).trim());
    if (row.crew3_name) parts.push(String(row.crew3_name).trim());
    var crew = parts.filter(Boolean).join(', ');
    var html = sailorLink(helm);
    if (crew) {
      html +=
        ' <span class="midmar-lb-amp">&amp;</span> ' +
        crew
          .split(/\s*,\s*/)
          .filter(Boolean)
          .map(sailorLink)
          .join(', ');
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
      '.regatta-page > .midmar-lb.card{margin:8px 0 0;padding:6px 10px;}' +
      '.regatta-page > .midmar-lb .section-title{margin:0 0 4px;padding:0 0 3px;font-size:0.75rem;line-height:1.2;}' +
      '.midmar-lb-list{margin:0;padding:0;}' +
      '.midmar-lb-row{display:flex;align-items:center;gap:8px;min-height:26px;padding:2px 0;border-bottom:1px solid #e0e0e0;font-size:0.85rem;line-height:1.2;color:#1e293b;}' +
      '.midmar-lb-row:last-child{border-bottom:0;}' +
      '.midmar-lb-rank{flex:0 0 auto;display:inline-flex;align-items:center;gap:4px;font-weight:700;color:#001f3f;white-space:nowrap;}' +
      '.midmar-lb-medal{font-size:1rem;line-height:1;}' +
      '.midmar-lb-boat{flex:0 1 auto;font-weight:700;color:#001f3f;min-width:0;}' +
      '.midmar-lb-boat a{color:#001f3f;text-decoration:none;}' +
      '.midmar-lb-club{flex:0 0 auto;}' +
      '.midmar-lb-club .rs-club-with-logo{display:inline-flex;align-items:center;}' +
      '.midmar-lb-club .rs-club-row-logo-sm{flex:0 0 22px;width:22px;max-width:22px;height:auto;max-height:16px;object-fit:contain;box-sizing:content-box;padding-right:4px;margin-right:4px;border-right:1px solid rgba(26,39,80,0.22);}' +
      '.midmar-lb-people{flex:1 1 auto;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}' +
      '.midmar-lb-people a{color:#001f3f;text-decoration:none;}' +
      '.midmar-lb-empty{margin:0;font-size:0.8rem;color:#334155;}' +
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
        '<div class="midmar-lb-list" data-mm-lb-list></div>';
    }
    var header = document.querySelector('.regatta-header-wrap');
    var host = document.getElementById('midmar-live-media');
    var wx = document.getElementById('ssa-regatta-slot-card');
    var page = document.querySelector('.regatta-page');
    if (host && host.parentNode) {
      if (card.nextSibling !== host) host.parentNode.insertBefore(card, host);
    } else if (wx && wx.parentNode && wx.parentNode !== host) {
      if (card.nextSibling !== wx) wx.parentNode.insertBefore(card, wx);
    } else if (header && header.parentNode) {
      if (card.previousSibling !== header) header.parentNode.insertBefore(card, header.nextSibling);
    } else if (page) {
      page.insertBefore(card, page.firstChild);
    }
    return card;
  }

  function boatHtml(row) {
    var bn = String(row.boat_name || '').trim();
    if (!bn) return '';
    if (bn.toLowerCase() === 'puffin') {
      return '<a href="/sponsors/ullman" title="Ullman Sails">' + esc(bn) + '</a>';
    }
    return esc(bn);
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
        var club = clubChip(row.club_abbrev || row.club_raw);
        return (
          '<div class="midmar-lb-row" data-rank="' +
          n +
          '">' +
          '<span class="midmar-lb-rank"><span class="midmar-lb-medal" aria-hidden="true">' +
          (MEDAL[n] || '') +
          '</span> ' +
          ORD[n] +
          '</span>' +
          (boat ? '<span class="midmar-lb-boat">' + boat + '</span>' : '') +
          (club ? '<span class="midmar-lb-club">' + club + '</span>' : '') +
          '<span class="midmar-lb-people">' +
          peopleHtml(row) +
          '</span></div>'
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
