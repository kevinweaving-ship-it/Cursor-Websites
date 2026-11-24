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
  var HOST_ID = 'midmar-lb-host';
  var CSS_ID = 'midmar-leaderboard-css-v13';
  var POLL_MS = 15000;
  /* Historical Hunter names, temp until confirmed. 2013 Essex Girl + 442 Scout confirmed. */
  var TEMP_BOATS = {
  };
  var MEDAL = { 1: '\uD83E\uDD47', 2: '\uD83E\uDD48', 3: '\uD83E\uDD49' };
  var SPONSORS = [
    { test: function (n) { return n === 'puffin'; }, file: 'Ullman-Sails.png', alt: 'Ullman Sails', href: '/sponsors/ullman', rightFile: 'Puffin.svg', rightAlt: 'Puffin' },
    { re: /ullman(\s+sails)?/, file: 'Ullman-Sails.png', alt: 'Ullman Sails', href: '/sponsors/ullman' },
    { re: /north\s+sails/, file: 'North-Sails.png', alt: 'North Sails', href: '/sponsors/north' },
    { re: /cell\s*c\b/, file: 'Cell-C.png', alt: 'Cell C', href: '/sponsors/cell-c' },
    { re: /\bamtec\b/, file: 'AMTEC.png', alt: 'AMTEC', href: '/sponsors/amtec' },
    { re: /nitro/, file: 'Nitro.png', alt: 'Nitro', href: '/sponsors/nitro' },
    { re: /\bh2[0o]\b/, file: 'H2O.png', alt: 'H2O', href: '/sponsors/h2o' },
  ];

  function currentRid() {
    var path = String((window.location && window.location.pathname) || '')
      .replace(/\/+$/, '')
      .toLowerCase();
    var m = path.match(/^\/(?:regatta|event)\/([^/]+)/);
    if (m && m[1]) return m[1];
    var el = document.querySelector('#midmar-leaderboard[data-regatta-id], [data-mm-lb-list], .regatta-page');
    var fromDom = '';
    if (el) fromDom = String(el.getAttribute('data-regatta-id') || '').trim();
    if (!fromDom) {
      var page = document.querySelector('[data-regatta-id]');
      if (page) fromDom = String(page.getAttribute('data-regatta-id') || '').trim();
    }
    return fromDom || '';
  }
  function onMidmar() {
    if (document.getElementById(CARD_ID)) return true;
    var rid = currentRid();
    return rid === '2026-11-14-hmyc-flying-fifteen-soling-nationals' || rid === RID || rid === '2026-09-24-hmyc-dart-18-nationals' || rid === '2026-12-30-hyc-sonnet-nationals' || rid === '2026-10-10-hmyc-dam-bottle-sprints' || rid === '2026-10-24-hmyc-dam-bottle-sprints';
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

  function logoChip(src, title, href, label, logoHref, rightSrc, rightTitle) {
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
    var right='';
    if(rightSrc){right='<img class="rs-club-row-logo-sm rs-boat-logo-right" src="'+rightSrc+'" alt="" title="'+esc(rightTitle||'')+'" loading="lazy" decoding="async">';}
    return '<span class="rs-club-with-logo">' + img + text + right + '</span>';
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
          '/artwork/Sponsor%20Logo/' + encodeURIComponent(sp.file) + '?v=20260919p',
          sp.alt,
          href,
          bn,
          sp.href,
          sp.rightFile ? ('/artwork/Sponsor%20Logo/' + encodeURIComponent(sp.rightFile) + '?v=20260919p') : '',
          sp.rightAlt || ''
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
    ['midmar-leaderboard-css', 'midmar-leaderboard-css-v4', 'midmar-leaderboard-css-v5', 'midmar-leaderboard-css-v6', 'midmar-leaderboard-css-v7', 'midmar-leaderboard-css-v8', 'midmar-leaderboard-css-v9', 'midmar-leaderboard-css-v10', 'midmar-leaderboard-css-v11'].forEach(function (id) {
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
      '.midmar-lb-host{width:100%;max-width:100%;display:flex;flex-direction:column;gap:10px;margin:10px 0 0;box-sizing:border-box;}' +
      '.midmar-lb-host > .midmar-lb.card{border:2px solid #001f3f!important;border-radius:8px!important;' +
      'box-shadow:0 1px 3px rgba(0,31,63,0.08)!important;width:100%!important;max-width:100%!important;' +
      'box-sizing:border-box!important;margin:0!important;padding:6px 10px;background:#fff;overflow:hidden;}' +
      '.regatta-page > #midmar-leaderboard.card,' +
      '.regatta-page > .midmar-lb-host > .midmar-lb.card,' +
      '.regatta-page > .midmar-live-media > #midmar-leaderboard.card,' +
      '.regatta-page > .midmar-live-media > .midmar-lb-host > .midmar-lb.card,' +
      '.regatta-page > .midmar-live-media > #ssa-regatta-slot-card,' +
      '.regatta-page > .midmar-live-media > .mm-lipton-reels,' +
      '.regatta-page > .midmar-live-media .midmar-mm-row > .mm-lipton-reels{' +
      'border:2px solid #001f3f!important;border-radius:8px!important;' +
      'box-shadow:0 1px 3px rgba(0,31,63,0.08)!important;' +
      'width:100%!important;max-width:100%!important;box-sizing:border-box!important;' +
      'margin-left:0!important;margin-right:0!important;}' +
      '.regatta-page > #midmar-leaderboard.card,' +
      '.regatta-page > .midmar-lb-host > .midmar-lb.card,' +
      '.regatta-page > .midmar-live-media > #midmar-leaderboard.card,' +
      '.regatta-page > .midmar-live-media > .midmar-lb-host > .midmar-lb.card{' +
      'order:0;margin:0;padding:6px 10px;background:#fff;overflow:hidden;}' +
      '.regatta-page > #midmar-leaderboard.card{margin:10px 0 0;}' +
      '.regatta-page > .midmar-live-media > #ssa-regatta-slot-card{order:1;margin-top:10px;padding:0!important;}' +
      '.regatta-page > .midmar-live-media > .mm-lipton-reels,' +
      '.regatta-page > .midmar-live-media .midmar-mm-row > .mm-lipton-reels{order:2;margin-top:10px;overflow:hidden;}' +
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
      '.midmar-lb .section-title{margin:0 0 2px;padding:0 0 2px;font-size:0.75rem;line-height:1.2;white-space:nowrap;display:flex;align-items:baseline;gap:0;}' +
      '.midmar-lb-sheet-note{font-size:0.667em;font-weight:500;line-height:1.2;' +
      'color:#334155;text-transform:none;letter-spacing:0;}' +
      '.midmar-lb-list{margin:0;padding:0;}' +
      /* MP first: wrap. A rank may use two lines (meta + helm/crew). */
      '.midmar-lb-row{display:flex;flex-wrap:wrap;align-items:center;gap:4px 8px;' +
      'padding:4px 0;border-bottom:1px solid #000;font-size:0.85rem;line-height:1.25;color:#1e293b;}' +
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
      '@media print{.midmar-lb.card{break-inside:avoid}}' +
      '.fleet-section .table-wrapper{touch-action:pan-x pan-y pinch-zoom!important;}';
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
        (currentRid() === '2026-11-14-hmyc-flying-fifteen-soling-nationals' ? '<h2 class="section-title">Leader Board</h2>' : '<h2 class="section-title">Leader Board<span class="midmar-lb-sheet-note"> - Day 1 - After Race 1</span></h2>') +
        '<div class="midmar-lb-list" data-mm-lb-list></div>';
    } else {
      var oldNote = card.querySelector('p.midmar-lb-sheet-note');
      if (oldNote) oldNote.remove();
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

  function racesAfter(rows) {
    var max = 0;
    (rows || []).forEach(function (r) {
      var rs = r.race_scores;
      if (typeof rs === 'string') {
        try {
          rs = JSON.parse(rs);
        } catch (e) {
          rs = null;
        }
      }
      if (rs && typeof rs === 'object') {
        Object.keys(rs).forEach(function (k) {
          if (!/^R\d+$/i.test(k) || !String(rs[k] || '').trim()) return;
          var num = parseInt(k.slice(1), 10);
          if (num > max) max = num;
        });
      }
      var sailed = Number(r.races_sailed);
      if (sailed > max) max = sailed;
    });
    return max;
  }

  function ymdSlice(v) {
    var m = String(v || '').match(/(\d{4}-\d{2}-\d{2})/);
    return m ? m[1] : '';
  }

  function todayYmdSast() {
    try {
      return new Intl.DateTimeFormat('en-CA', {
        timeZone: 'Africa/Johannesburg',
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
      }).format(new Date());
    } catch (e) {
      var d = new Date();
      var mo = d.getMonth() + 1;
      var da = d.getDate();
      return d.getFullYear() + '-' + (mo < 10 ? '0' : '') + mo + '-' + (da < 10 ? '0' : '') + da;
    }
  }

  function eventDay(rows) {
    var start = '';
    var end = '';
    (rows || []).some(function (r) {
      if (!start) start = ymdSlice(r.start_date || r.startDate);
      if (!end) end = ymdSlice(r.end_date || r.endDate);
      return !!start && !!end;
    });
    if (!start) return 0;
    var cap = todayYmdSast();
    if (end && end < cap) cap = end;
    var d0 = new Date(start + 'T12:00:00');
    var d1 = new Date(cap + 'T12:00:00');
    if (isNaN(d0.getTime()) || isNaN(d1.getTime())) return 0;
    var diff = Math.round((d1.getTime() - d0.getTime()) / 86400000);
    if (diff < 0) return 0;
    return diff + 1;
  }

  function titleAfter(n, day) {
    if (n < 1) return 'Leader Board';
    var t = 'Leader Board after ' + n + (n === 1 ? ' Race' : ' Races');
    if (day >= 1) t += ' on Day ' + day;
    return t;
  }

  function isDartLb() {
    return currentRid() === '2026-09-24-hmyc-dart-18-nationals' || currentRid() === '2026-12-30-hyc-sonnet-nationals';
  }

  function rsOf(row) {
    var rs = row.race_scores;
    if (!rs) return {};
    if (typeof rs === 'string') {
      try { rs = JSON.parse(rs); } catch (e) { return {}; }
    }
    return rs && typeof rs === 'object' ? rs : {};
  }

  function cellFilled(v) {
    return String(v == null ? '' : v).trim() !== '';
  }

  function placeNum(v) {
    var s = String(v == null ? '' : v).replace(/[()]/g, '').trim();
    if (!/^\d+$/.test(s)) return 0;
    return parseInt(s, 10);
  }

  function raceInfo(rows, n) {
    var got = {};
    var filled = 0;
    rows.forEach(function (r) {
      var v = rsOf(r)['R' + n];
      if (!cellFilled(v)) return;
      filled += 1;
      var p = placeNum(v);
      if (p >= 1 && p <= 3) got[p] = 1;
    });
    return { filled: filled, podium: !!(got[1] && got[2] && got[3]) };
  }

  function dartFleetThrough(rows) {
    var max = 0;
    rows.forEach(function (r) {
      var rs = rsOf(r);
      Object.keys(rs).forEach(function (k) {
        var m = /^R(\d+)$/i.exec(k);
        if (m) max = Math.max(max, parseInt(m[1], 10));
      });
    });
    var need = Math.ceil(rows.length * 0.25);
    if (need < 1) need = 1;
    var through = 0;
    var n;
    for (n = 1; n <= max; n++) {
      var info = raceInfo(rows, n);
      if (!info.podium) continue;
      if (n === 1 || info.filled >= need) through = n;
    }
    return through;
  }

  function dartNett(row, through) {
    var rs = rsOf(row);
    var sum = 0;
    var any = false;
    var i;
    for (i = 1; i <= through; i++) {
      var v = rs['R' + i];
      if (!cellFilled(v)) continue;
      any = true;
      var p = placeNum(v);
      sum += p > 0 ? p : 0;
    }
    if (!any) return null;
    var server = Number(row.nett_points_raw);
    if (isFinite(server) && server > 0) return server;
    return sum;
  }

  function fleetLabelOf(r) {
    return String((r && (r.fleet_label || r.class_canonical || r.class_name)) || 'Fleet').trim() || 'Fleet';
  }

  function fleetKeyOf(r) {
    var block = String((r && r.block_id) || '').trim();
    if (block) return block;
    return fleetLabelOf(r).toLowerCase();
  }

  function groupFleets(rows) {
    var groups = {};
    var order = [];
    (rows || []).forEach(function (r) {
      if (!r) return;
      var key = fleetKeyOf(r);
      if (!groups[key]) {
        groups[key] = { key: key, label: fleetLabelOf(r), rows: [] };
        order.push(key);
      }
      groups[key].rows.push(r);
    });
    order.sort(function (a, b) {
      var al = groups[a].label.toLowerCase();
      var bl = groups[b].label.toLowerCase();
      return al < bl ? -1 : al > bl ? 1 : 0;
    });
    return order.map(function (k) {
      return groups[k];
    });
  }

  function podiumRows(rows) {
    return (rows || [])
      .filter(function (r) {
        var n = Number(r.rank);
        return n >= 1 && n <= 3 && hasScore(r);
      })
      .sort(function (a, b) {
        return Number(a.rank) - Number(b.rank);
      });
  }

  function setCardTitle(card, main, note) {
    var title = card.querySelector('.section-title');
    if (!title) {
      title = document.createElement('h2');
      title.className = 'section-title';
      card.insertBefore(title, card.firstChild);
    }
    title.textContent = main;
    if (note) {
      var sp = document.createElement('span');
      sp.className = 'midmar-lb-sheet-note';
      sp.textContent = ' ' + note;
      title.appendChild(sp);
    }
    card.setAttribute('aria-label', main + (note ? ' ' + note : ''));
  }

  function ensureHost(firstCard) {
    var host = document.getElementById(HOST_ID);
    if (host) return host;
    host = document.createElement('div');
    host.id = HOST_ID;
    host.className = 'midmar-lb-host';
    if (firstCard && firstCard.parentNode) {
      firstCard.parentNode.insertBefore(host, firstCard);
      host.appendChild(firstCard);
    } else {
      var header = document.querySelector('.regatta-header-wrap');
      var page = document.querySelector('.regatta-page');
      var wx = document.getElementById('ssa-regatta-slot-card');
      var live = document.getElementById('club-live-media') || document.getElementById('midmar-live-media');
      if (live && live.parentNode) live.parentNode.insertBefore(host, live.nextSibling);
      else if (wx && wx.parentNode) wx.parentNode.insertBefore(host, wx);
      else if (header && header.parentNode) header.parentNode.insertBefore(host, header.nextSibling);
      else if (page) page.insertBefore(host, page.firstChild);
    }
    return host;
  }

  function hostCards(host) {
    return Array.prototype.filter.call((host && host.children) || [], function (el) {
      return el.classList && el.classList.contains('midmar-lb');
    });
  }

  function fleetCard(host, idx) {
    var cards = hostCards(host);
    var card = cards[idx];
    if (card) return card;
    card = document.createElement('section');
    card.className = 'card midmar-lb';
    card.innerHTML = '<h2 class="section-title">Leader Board</h2><div class="midmar-lb-list" data-mm-lb-list></div>';
    host.appendChild(card);
    return card;
  }

  function rowHtml(row, n) {
    var boat = boatHtml(row);
    var sail = sailHtml(row);
    var club = clubChip(row.club_abbrev || row.club_raw);
    var medal = MEDAL[n] ? '<span class="midmar-lb-medal" aria-hidden="true">' + MEDAL[n] + '</span> ' : '';
    return (
      '<div class="midmar-lb-row" data-rank="' + n + '">' +
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
  }

  function dartRowHtml(row, n) {
    var boat = boatHtml(row);
    var sail = sailHtml(row);
    var club = clubChip(row.club_abbrev || row.club_raw);
    var medal = MEDAL[n] ? '<span class="midmar-lb-medal" aria-hidden="true">' + MEDAL[n] + '</span> ' : '';
    return (
      '<div class="midmar-lb-row" data-rank="' + n + '">' +
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
  }

  function dartPodium(rows) {
    var through = dartFleetThrough(rows);
    if (!through) return { through: 0, board: [] };
    var ranked = (rows || []).filter(function (r) {
      return dartNett(r, through) != null;
    }).sort(function (a, b) {
      var an = dartNett(a, through);
      var bn = dartNett(b, through);
      if (an !== bn) return an - bn;
      return (Number(a.rank) || 999) - (Number(b.rank) || 999);
    });
    return { through: through, board: ranked.slice(0, 3) };
  }

  function paintOneFleet(card, fleet, many, dart) {
    var list = card.querySelector('[data-mm-lb-list]');
    if (!list) {
      list = document.createElement('div');
      list.setAttribute('data-mm-lb-list', '');
      card.appendChild(list);
    }
    var board;
    var note = '';
    if (dart) {
      var d = dartPodium(fleet.rows);
      board = d.board;
      var dayN = eventDay(fleet.rows) || 0;
      if (d.through) note = 'after ' + d.through + (d.through === 1 ? ' race' : ' races');
      if (dayN) note += (note ? ' · ' : '') + 'day ' + dayN;
    } else {
      board = podiumRows(fleet.rows);
      var n = racesAfter(fleet.rows);
      var day = eventDay(fleet.rows);
      if (n >= 1) note = 'after ' + n + (n === 1 ? ' race' : ' races');
      if (day >= 1) note += (note ? ' · ' : '') + 'day ' + day;
    }
    if (many) setCardTitle(card, fleet.label, note);
    else setCardTitle(card, titleAfter(racesAfter(fleet.rows), eventDay(fleet.rows)), '');
    card.setAttribute('data-mm-lb-fleet', fleet.key);
    if (!board.length) {
      list.innerHTML = '<p class="midmar-lb-empty">Waiting for race scores</p>';
      return;
    }
    list.innerHTML = board
      .map(function (row, i) {
        var n = dart ? i + 1 : Number(row.rank);
        return dart ? dartRowHtml(row, n) : rowHtml(row, n);
      })
      .join('');
  }

  function paintFleets(anchor, rows) {
    var host = ensureHost(anchor);
    var dart = isDartLb();
    var groups = groupFleets(rows).filter(function (g) {
      if (dart) return dartPodium(g.rows).board.length > 0;
      return podiumRows(g.rows).length > 0;
    });
    var cards = hostCards(host);
    var i;
    for (i = groups.length; i < cards.length; i++) cards[i].remove();
    if (!groups.length) {
      var empty = fleetCard(host, 0);
      empty.id = CARD_ID;
      setCardTitle(empty, 'Leader Board', '');
      var list = empty.querySelector('[data-mm-lb-list]');
      if (list) list.innerHTML = '<p class="midmar-lb-empty">Waiting for race scores</p>';
      return;
    }
    var many = groups.length > 1;
    groups.forEach(function (g, idx) {
      var card = fleetCard(host, idx);
      if (idx === 0) card.id = CARD_ID;
      else card.removeAttribute('id');
      paintOneFleet(card, g, many, dart);
    });
  }

  function load(anchor) {
    fetch('/api/regatta/' + encodeURIComponent(currentRid()), {
      credentials: 'same-origin',
      cache: 'no-store',
    })
      .then(function (r) {
        return r && r.ok ? r.json() : null;
      })
      .then(function (data) {
        var rows = Array.isArray(data) ? data : (data && data.results) || [];
        paintFleets(anchor, rows);
        greyFleetTemps();
      })
      .catch(function () {});
  }

  function boot() {
    if (!onMidmar()) return;
    injectCss();
    var card = placeCard();
    if (!card) return;
    var host = ensureHost(card);
    load(host.querySelector('.midmar-lb') || card);
    greyFleetTemps();
    if (host.getAttribute('data-mm-lb-bound') === '1') return;
    host.setAttribute('data-mm-lb-bound', '1');
    window.setInterval(function () {
      if (!document.hidden) load(host.querySelector('.midmar-lb') || card);
    }, POLL_MS);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
