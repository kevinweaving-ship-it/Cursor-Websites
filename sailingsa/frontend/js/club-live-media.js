/**
 * Club-page venue weather + camera cards — same ZVYC MM compact layout.
 * Snapshot cams use that card (tap expands to full MP width). Not live.
 * Club logo on the cam card — not Marine Megastore.
 */
(function () {
  'use strict';
  if (window.__SSA_CLUB_LIVE_MEDIA__) return;
  window.__SSA_CLUB_LIVE_MEDIA__ = true;

  var HOST_ID = 'club-live-media';
  var WX_ID = 'ssa-regatta-slot-card';
  var MM_ID = 'mmLiptonReels';
  var CSS_ID = 'club-live-media-css';
  var JS_VER = 'clubwx7';

  var AGRO_CAM = 'https://hmyccam1.nwsza.net/latest.jpg';
  var AGRO_PAGE = 'https://agromet.ukzn.ac.za/midmar/index.html#canvas_container';

  var CLUBS = {
    zvyc: {
      code: 'ZVYC',
      weatherClub: 'ZVYC',
      weatherRole: 'venue',
      cam: 'mm',
      logo: '/artwork/Club Logo/ZVYC.png',
      logoHref: 'https://zvyc.co.za/',
      logoAlt: 'ZVYC',
      regattaId: '2026-09-13-zvyc-cape-classic',
    },
    hyc: {
      code: 'HYC',
      weatherClub: 'HYC',
      weatherStation: 'pws-iovers2',
      weatherRole: 'venue',
      cam: 'soon',
      logo: '/artwork/Club Logo/HYC.png',
      logoHref: 'https://www.hyc.co.za/',
      logoAlt: 'HYC',
      weatherHref: 'https://www.wunderground.com/dashboard/pws/IOVERS2',
    },
    hmyc: {
      code: 'HMYC',
      weatherClub: 'HMYC',
      weatherStation: 'agromet-midmar',
      weatherRole: 'venue',
      cam: 'still',
      still: AGRO_CAM,
      stillIntervalMs: 60000,
      camHref: AGRO_PAGE,
      camLabel: 'HMYC club cam',
      camStatusApi: '/api/club-cam/hmyc',
      logo: '/artwork/Club Logo/HMYC.png',
      logoHref: AGRO_PAGE,
      logoAlt: 'HMYC',
      weatherHref: AGRO_PAGE,
    },
  };

  function clubSlug() {
    var path = String((window.location && window.location.pathname) || '')
      .replace(/\/+$/, '')
      .toLowerCase();
    var m = path.match(/^\/club\/([^/]+)$/);
    return m ? decodeURIComponent(m[1]) : '';
  }

  function cfg() {
    return CLUBS[clubSlug()] || null;
  }

  function injectCss() {
    if (document.getElementById(CSS_ID)) return;
    var s = document.createElement('style');
    s.id = CSS_ID;
    s.textContent =
      '.club-page .club-live-media{width:100%;box-sizing:border-box;display:flex;flex-direction:column;gap:0;padding:0;border:0;background:transparent;box-shadow:none;}' +
      '.club-page .club-live-media .ssa-regatta-slot-card{order:0!important;margin-top:0;width:100%;max-width:100%;padding:0!important;}' +
      '.club-page .club-live-media .mm-lipton-reels{order:1!important;margin-top:10px;width:100%;}' +
      '.club-page .club-story-inner > .club-live-media{max-width:100%;}' +
      '.mm-lipton-reels[data-mm-snapshot] .mm-lipton-reels-brand{display:none!important}' +
      '.mm-lipton-reels[data-mm-snapshot] .mm-lipton-reels-clip-chrome{display:none!important}';
    document.head.appendChild(s);
  }

  function ensureCssLink() {
    var href = '/css/mm-lipton-reels.css?v=' + JS_VER;
    if (document.querySelector('link[href*="mm-lipton-reels.css"]')) return;
    var l = document.createElement('link');
    l.rel = 'stylesheet';
    l.href = href;
    document.head.appendChild(l);
  }

  function mmInnerHtml(club) {
    var brand = club.still
      ? ''
      : '<a class="mm-lipton-reels-brand" href="' +
        club.logoHref +
        '" target="_blank" rel="noopener noreferrer">' +
        '<img src="' +
        club.logo +
        '" alt="' +
        club.logoAlt +
        '" width="320" height="213" loading="lazy" decoding="async">' +
        '</a>';
    return (
      '<div class="mm-lipton-reels-compact">' +
      brand +
      '<div class="mm-lipton-reels-rail-wrap">' +
      '<button type="button" class="mm-lipton-reels-rail-btn mm-lipton-reels-rail-btn--prev" data-mm-rail-prev aria-label="Previous clips" hidden>‹</button>' +
      '<div class="mm-lipton-reels-rail" data-mm-compact></div>' +
      '<button type="button" class="mm-lipton-reels-rail-btn mm-lipton-reels-rail-btn--next" data-mm-rail-next aria-label="Next clips" hidden>›</button>' +
      '</div></div>'
    );
  }

  function snapshotVideo(club) {
    if (!club.still) return [];
    return [
      {
        id: String(club.code || 'club').toLowerCase() + '-club-cam',
        kind: 'webcam',
        snapshot: true,
        title: club.camLabel || 'Club cam',
        thumb: club.still,
        live_snap: club.still,
        url: club.camHref || '',
        status_api: club.camStatusApi || '',
        aspect: '16 / 9',
        width: 16,
        height: 9,
      },
    ];
  }

  function makeWx(club) {
    var wx = document.getElementById(WX_ID);
    if (!wx) {
      wx = document.createElement('section');
      wx.id = WX_ID;
      wx.className = 'card ssa-wx-card ssa-regatta-slot-card';
    }
    wx.setAttribute('data-weather-club', club.weatherClub);
    wx.setAttribute('data-weather-role', club.weatherRole || 'venue');
    if (club.weatherStation) wx.setAttribute('data-weather-station', club.weatherStation);
    wx.setAttribute('aria-label', club.code + ' venue wind');
    return wx;
  }

  function makeMmCam(club) {
    var mm = document.getElementById(MM_ID);
    if (!mm) {
      mm = document.createElement('section');
      mm.id = MM_ID;
      mm.className = 'card mm-lipton-reels mm-lipton-reels--compact';
    }
    if (club.regattaId) mm.setAttribute('data-regatta-id', club.regattaId);
    else mm.removeAttribute('data-regatta-id');
    if (club.regattaId) mm.setAttribute('data-mm-poll', '1');
    else mm.removeAttribute('data-mm-poll');
    mm.setAttribute('data-mm-club-page', '1');
    if (club.still) {
      mm.removeAttribute('data-mm-club-logo');
      mm.removeAttribute('data-mm-club-href');
      mm.removeAttribute('data-mm-club-alt');
      mm.removeAttribute('data-mm-brand-soon');
      mm.removeAttribute('data-mm-brand-live');
      mm.setAttribute('data-mm-snapshot', '1');
      mm.setAttribute('data-mm-cam-status', club.camStatusApi || '/api/club-cam/hmyc');
    } else {
      mm.setAttribute('data-mm-club-logo', club.logo);
      mm.setAttribute('data-mm-club-href', club.logoHref);
      mm.setAttribute('data-mm-club-alt', club.logoAlt);
      mm.setAttribute('data-mm-brand-soon', club.logo);
      mm.setAttribute('data-mm-brand-live', club.logo);
      mm.removeAttribute('data-mm-snapshot');
      mm.removeAttribute('data-mm-cam-status');
    }
    mm.setAttribute(
      'data-mm-initial',
      JSON.stringify({
        enabled: true,
        feed_source: 'club',
        videos: snapshotVideo(club),
      })
    );
    mm.innerHTML = mmInnerHtml(club);
    return mm;
  }

  function fillHost(host, club) {
    if (host.getAttribute('data-club-live-ready') === '1') {
      return orderCards(host);
    }
    host.appendChild(makeWx(club));
    host.appendChild(makeMmCam(club));
    host.setAttribute('data-club-live-ready', '1');
    return orderCards(host);
  }

  function orderCards(host) {
    var wx = document.getElementById(WX_ID);
    var cam = document.getElementById(MM_ID);
    if (host && wx && cam && wx.parentNode === host && cam.parentNode === host && wx.nextSibling !== cam) {
      host.insertBefore(wx, cam);
    }
    return host;
  }

  function placeHost(club) {
    var existing = document.getElementById(HOST_ID) || document.getElementById('club-zvyc-live-media');
    if (existing) {
      existing.id = HOST_ID;
      return fillHost(existing, club);
    }

    var host = document.createElement('div');
    host.id = HOST_ID;
    host.className = 'club-live-media';
    host.setAttribute('aria-label', 'Venue weather and club camera');

    var ident = document.querySelector('.club-story-identity');
    if (ident && ident.parentNode) {
      ident.parentNode.insertBefore(host, ident.nextSibling);
      return fillHost(host, club);
    }

    var about = document.querySelector('.club-story-about');
    var aboutPanel = about && (about.closest('.club-story-panel') || about);
    if (aboutPanel && aboutPanel.parentNode) {
      aboutPanel.parentNode.insertBefore(host, aboutPanel);
      return fillHost(host, club);
    }

    var inner = document.querySelector('.club-story-inner');
    if (inner) {
      var firstBlock = inner.querySelector('.club-story-block');
      if (firstBlock) {
        inner.insertBefore(host, firstBlock);
        return fillHost(host, club);
      }
      inner.appendChild(host);
      return fillHost(host, club);
    }

    var header = document.querySelector('.club-page .header, .club-page-header, .club-story-header');
    if (header && header.parentNode) {
      header.parentNode.insertBefore(host, header.nextSibling);
      return fillHost(host, club);
    }

    var page = document.querySelector('.club-page');
    if (page) {
      page.insertBefore(host, page.firstChild);
      return fillHost(host, club);
    }
    return null;
  }

  function loadScript(src) {
    return new Promise(function (resolve) {
      var base = src.split('?')[0];
      var found = document.querySelector('script[src*="' + base + '"]');
      if (found) {
        if (found.getAttribute('data-loaded') === '1' || found.readyState === 'complete') {
          resolve();
          return;
        }
        found.addEventListener('load', function () {
          resolve();
        });
        found.addEventListener('error', function () {
          resolve();
        });
        return;
      }
      var s = document.createElement('script');
      s.src = src;
      s.async = false;
      s.onload = function () {
        s.setAttribute('data-loaded', '1');
        resolve();
      };
      s.onerror = function () {
        resolve();
      };
      document.head.appendChild(s);
    });
  }

  function boot() {
    var club = cfg();
    if (!club) return;
    injectCss();
    ensureCssLink();
    if (!placeHost(club)) return;
    loadScript('/js/regatta-slot-card.js?v=' + JS_VER).catch(function () {});
    loadScript('/js/mm-lipton-reels-card.js?v=' + JS_VER).catch(function () {});
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
