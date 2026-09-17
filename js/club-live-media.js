/**
 * Club-page live media: venue weather card + live-cam card (MM compact layout).
 * ZVYC / HYC / HMYC. Club logo on the cam card — not Marine Megastore, the
 * feed belongs to the club. No-op on other club slugs.
 */
(function () {
  'use strict';
  if (window.__SSA_CLUB_LIVE_MEDIA__) return;
  window.__SSA_CLUB_LIVE_MEDIA__ = true;

  var HOST_ID = 'club-live-media';
  var WX_ID = 'ssa-regatta-slot-card';
  var CAM_ID = 'clubLiveCam';
  var MM_ID = 'mmLiptonReels';
  var CSS_ID = 'club-live-media-css';
  var JS_VER = 'clubwx3';
  var ART_W = 320;
  var ART_H = 213;
  var VID_W = 16;
  var VID_H = 9;
  var GAP = 6;

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
      logoAlt: 'ZVYC live cam',
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
      camHref: AGRO_PAGE,
      camLabel: 'HMYC live cam',
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
      '.club-page .club-live-media .ssa-regatta-slot-card{order:0!important;margin-top:0;width:100%;max-width:100%;}' +
      '.club-page .club-live-media .mm-lipton-reels,.club-page .club-live-media .club-live-cam{order:1!important;margin-top:10px;width:100%;}' +
      '.club-page .club-story-inner > .club-live-media{max-width:100%;}' +
      '.club-page .mm-lipton-reels-brand{background:#fff;}' +
      '.club-page .mm-lipton-reels-brand img{object-fit:contain;background:#fff;}' +
      '.club-live-cam.mm-lipton-reels{display:block;width:100%;margin:10px 0 0;padding:6px;background:#dce6ef;border:2px solid #001f3f;border-radius:8px;box-shadow:0 1px 3px rgba(0,31,63,.08);box-sizing:border-box;}' +
      '.club-live-cam .mm-lipton-reels-brand{background:#fff;}' +
      '.club-live-cam .mm-lipton-reels-brand img{object-fit:contain;background:#fff;}' +
      '.club-live-cam .club-cam-soon{display:flex;align-items:center;justify-content:center;width:100%;height:100%;padding:8px;box-sizing:border-box;background:#0b1c33;color:#e2e8f0;font:700 13px/1.25 Arial,Helvetica,sans-serif;text-align:center;}' +
      '.club-live-cam .mm-lipton-reels-thumb img{object-fit:cover;}';
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
    return (
      '<div class="mm-lipton-reels-compact">' +
      '<a class="mm-lipton-reels-brand" href="' +
      club.logoHref +
      '" target="_blank" rel="noopener noreferrer">' +
      '<img src="' +
      club.logo +
      '" alt="' +
      club.logoAlt +
      '" width="320" height="213" loading="lazy" decoding="async">' +
      '</a>' +
      '<div class="mm-lipton-reels-rail-wrap">' +
      '<button type="button" class="mm-lipton-reels-rail-btn mm-lipton-reels-rail-btn--prev" data-mm-rail-prev aria-label="Previous clips" hidden>‹</button>' +
      '<div class="mm-lipton-reels-rail" data-mm-compact></div>' +
      '<button type="button" class="mm-lipton-reels-rail-btn mm-lipton-reels-rail-btn--next" data-mm-rail-next aria-label="Next clips" hidden>›</button>' +
      '</div></div>'
    );
  }

  function camTileHtml(club) {
    if (club.cam === 'still') {
      return (
        '<a class="mm-lipton-reels-tile" href="' +
        club.camHref +
        '" target="_blank" rel="noopener noreferrer">' +
        '<div class="mm-lipton-reels-thumb">' +
        '<img data-club-cam-still src="' +
        club.still +
        '" alt="' +
        (club.camLabel || club.logoAlt) +
        '" loading="lazy" decoding="async">' +
        '</div></a>'
      );
    }
    return (
      '<div class="mm-lipton-reels-tile">' +
      '<div class="mm-lipton-reels-thumb" aria-label="Live cam coming soon">' +
      '<div class="club-cam-soon">Live cam coming soon</div>' +
      '</div></div>'
    );
  }

  function camInnerHtml(club) {
    return (
      '<div class="mm-lipton-reels-compact">' +
      '<a class="mm-lipton-reels-brand" href="' +
      club.logoHref +
      '" target="_blank" rel="noopener noreferrer">' +
      '<img src="' +
      club.logo +
      '" alt="' +
      club.logoAlt +
      '" width="320" height="213" loading="lazy" decoding="async">' +
      '</a>' +
      '<div class="mm-lipton-reels-rail-wrap">' +
      '<div class="mm-lipton-reels-rail" data-club-cam-rail>' +
      camTileHtml(club) +
      '</div></div></div>'
    );
  }

  function layoutCam(host) {
    var cam = document.getElementById(CAM_ID);
    if (!cam) return;
    var row = cam.querySelector('.mm-lipton-reels-compact');
    var brand = cam.querySelector('.mm-lipton-reels-brand');
    var wrap = cam.querySelector('.mm-lipton-reels-rail-wrap');
    var thumbs = cam.querySelectorAll('.mm-lipton-reels-thumb, .mm-lipton-reels-tile');
    if (!row || !brand) return;
    var avail = row.clientWidth;
    if (avail <= 0) return;
    var art = ART_W / ART_H;
    var vid = VID_W / VID_H;
    var border = 4;
    var cols = 1;
    var innerH = (avail - GAP * cols - border * (1 + cols)) / (art + cols * vid);
    if (innerH < 40) innerH = 40;
    var outerH = innerH + border;
    var thumbW = innerH * vid + border;
    brand.style.width = innerH * art + border + 'px';
    brand.style.height = outerH + 'px';
    if (wrap) wrap.style.height = outerH + 'px';
    var i;
    for (i = 0; i < thumbs.length; i++) {
      thumbs[i].style.width = thumbW + 'px';
      thumbs[i].style.height = outerH + 'px';
    }
  }

  function tickStill(club) {
    var img = document.querySelector('#clubLiveCam [data-club-cam-still]');
    if (!img || !club.still) return;
    img.src = club.still + (club.still.indexOf('?') >= 0 ? '&' : '?') + 't=' + Date.now();
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
    mm.setAttribute('data-regatta-id', club.regattaId);
    mm.setAttribute('data-mm-poll', '1');
    mm.setAttribute('data-mm-club-page', '1');
    mm.setAttribute('data-mm-club-logo', club.logo);
    mm.setAttribute('data-mm-club-href', club.logoHref);
    mm.setAttribute('data-mm-club-alt', club.logoAlt);
    mm.setAttribute('data-mm-brand-soon', club.logo);
    mm.setAttribute('data-mm-brand-live', club.logo);
    mm.setAttribute(
      'data-mm-initial',
      JSON.stringify({
        enabled: true,
        feed_source: 'club',
        videos: [],
      })
    );
    mm.innerHTML = mmInnerHtml(club);
    return mm;
  }

  function makeClubCam(club) {
    var cam = document.getElementById(CAM_ID);
    if (!cam) {
      cam = document.createElement('section');
      cam.id = CAM_ID;
      cam.className = 'card mm-lipton-reels mm-lipton-reels--compact club-live-cam';
    }
    cam.setAttribute('data-club-cam', club.cam);
    cam.setAttribute('aria-label', club.code + ' live camera');
    cam.innerHTML = camInnerHtml(club);
    return cam;
  }

  function fillHost(host, club) {
    if (host.getAttribute('data-club-live-ready') === '1') {
      return orderCards(host);
    }
    var wx = makeWx(club);
    host.appendChild(wx);
    if (club.cam === 'mm') host.appendChild(makeMmCam(club));
    else host.appendChild(makeClubCam(club));
    host.setAttribute('data-club-live-ready', '1');
    return orderCards(host);
  }

  function orderCards(host) {
    var wx = document.getElementById(WX_ID);
    var cam = document.getElementById(CAM_ID) || document.getElementById(MM_ID);
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
    host.setAttribute('aria-label', 'Live weather and club camera');

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
    layoutCam();
    window.addEventListener('resize', layoutCam);
    if (club.cam === 'still') {
      window.setInterval(function () {
        tickStill(club);
      }, 10000);
    }
    var wxSrc = '/js/regatta-slot-card.js?v=' + JS_VER;
    if (club.cam === 'mm') {
      loadScript('/js/mm-lipton-reels-card.js?v=' + JS_VER)
        .then(function () {
          return loadScript(wxSrc);
        })
        .catch(function () {});
    } else {
      loadScript(wxSrc).catch(function () {});
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
