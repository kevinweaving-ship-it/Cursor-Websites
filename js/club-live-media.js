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
  var JS_VER = 'clubwx10';

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
      cam: 'live',
      livePass: true,
      stream: '/api/club-cam/hyc/live',
      camHref: 'https://www.hyc.co.za/',
      camLabel: 'HYC club cam',
      camStatusApi: '/api/club-cam/hyc',
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
      '.mm-lipton-reels[data-mm-snapshot] .mm-lipton-reels-clip-chrome{display:none!important}' +
      '.mm-lipton-reels[data-mm-live-pass] .mm-lipton-reels-brand{display:none!important}' +
      '.mm-lipton-reels[data-mm-live-pass] .mm-lipton-reels-clip-chrome{display:none!important}' +
      '.mm-lipton-reels[data-mm-live-pass] .mm-lipton-reels-play{display:none!important}' +
      '.club-live-media .club-cam-sa-toggle{display:none;margin:8px 0 0;min-height:44px;min-width:44px;padding:10px 14px;border:1.5px solid #1a2750;border-radius:8px;background:#fff;color:#1a2750;font:700 14px/1.2 Arial,Helvetica,sans-serif;cursor:pointer;}' +
      '.club-live-media.club-live-media--sa .club-cam-sa-toggle{display:inline-flex;align-items:center;justify-content:center;}' +
      '.club-live-media.club-live-media--cam-off:not(.club-live-media--sa) .mm-lipton-reels{display:none!important}' +
      '.mm-lipton-reels[data-mm-live-pass]{min-height:120px}' +
      '.mm-lipton-reels[data-mm-live-pass] .mm-lipton-reels-thumb{width:100%;aspect-ratio:16/9;background:#111}';
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
    var brand = club.still || club.livePass
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

  function livePassVideo(club) {
    if (!club.livePass) return [];
    return [
      {
        id: String(club.code || 'club').toLowerCase() + '-club-cam',
        kind: 'webcam',
        live_pass: true,
        title: club.camLabel || 'Club cam',
        stream_url: club.stream || '/api/club-cam/hyc/live',
        stream_kind: 'hls',
        url: club.camHref || '',
        status_api: club.camStatusApi || '',
        aspect: '16 / 9',
        width: 16,
        height: 9,
      },
    ];
  }

  function snapshotVideo(club) {
    if (club.livePass) return livePassVideo(club);
    if (!club.still) return [];
    return [
      {
        id: String(club.code || 'club').toLowerCase() + '-club-cam',
        kind: 'webcam',
        snapshot: true,
        live_still: !!club.liveStill,
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
    if (club.livePass) {
      mm.removeAttribute('data-mm-club-logo');
      mm.removeAttribute('data-mm-club-href');
      mm.removeAttribute('data-mm-club-alt');
      mm.removeAttribute('data-mm-brand-soon');
      mm.removeAttribute('data-mm-brand-live');
      mm.removeAttribute('data-mm-snapshot');
      mm.removeAttribute('data-mm-live-still');
      mm.setAttribute('data-mm-live-pass', '1');
      mm.setAttribute('data-mm-cam-status', club.camStatusApi || '/api/club-cam/hyc');
    } else if (club.still) {
      mm.removeAttribute('data-mm-club-logo');
      mm.removeAttribute('data-mm-club-href');
      mm.removeAttribute('data-mm-club-alt');
      mm.removeAttribute('data-mm-brand-soon');
      mm.removeAttribute('data-mm-brand-live');
      mm.setAttribute('data-mm-snapshot', '1');
      mm.removeAttribute('data-mm-live-still');
      mm.removeAttribute('data-mm-live-pass');
      mm.setAttribute('data-mm-cam-status', club.camStatusApi || '/api/club-cam/hmyc');
    } else {
      mm.setAttribute('data-mm-club-logo', club.logo);
      mm.setAttribute('data-mm-club-href', club.logoHref);
      mm.setAttribute('data-mm-club-alt', club.logoAlt);
      mm.setAttribute('data-mm-brand-soon', club.logo);
      mm.setAttribute('data-mm-brand-live', club.logo);
      mm.removeAttribute('data-mm-snapshot');
      mm.removeAttribute('data-mm-live-pass');
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
    mountSaCamToggle(host, club);
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

  function saToggleHtml() {
    return (
      '<button type="button" class="club-cam-sa-toggle" data-club-cam-sa hidden>' +
      'Hide live cam from public</button>'
    );
  }

  function paintSaToggle(btn, visible) {
    if (!btn) return;
    btn.hidden = false;
    btn.textContent = visible ? 'Hide live cam from public' : 'Show live cam to public';
    btn.setAttribute('aria-pressed', visible ? 'true' : 'false');
  }

  function isSaSession(session) {
    if (typeof window.sailingSessionIsSuperAdmin === 'function') {
      return !!window.sailingSessionIsSuperAdmin(session);
    }
    if (!session || session.valid !== true) return false;
    if (session.is_super_admin === true) return true;
    var r = session.role;
    if ((r == null || r === '') && session.user) r = session.user.role;
    var n = String(r || '')
      .trim()
      .toLowerCase()
      .replace(/[\s\-]+/g, '_');
    return n === 'super_admin' || n === 'superadmin';
  }

  function applyCamPublic(host, data, sa) {
    if (!host) return;
    var visible = !(data && data.visible === false);
    var can = !!(sa || (data && data.can_toggle));
    host.classList.toggle('club-live-media--sa', can);
    host.classList.toggle('club-live-media--cam-off', !visible);
    var mm = document.getElementById(MM_ID);
    if (mm) {
      if (!visible && !can) mm.setAttribute('hidden', '');
      else mm.removeAttribute('hidden');
    }
    var btn = host.querySelector('[data-club-cam-sa]');
    if (can) paintSaToggle(btn, visible);
    else if (btn) btn.hidden = true;
    if (typeof window.dispatchEvent === 'function') window.dispatchEvent(new Event('resize'));
  }

  function fetchCamStatus() {
    return fetch('/api/club-cam/hyc?_=' + Date.now(), { credentials: 'include', cache: 'no-store' }).then(function (r) {
      return r && r.ok ? r.json() : null;
    });
  }

  function mountSaCamToggle(host, club) {
    if (!host || !club || !club.livePass) return;
    var btn = host.querySelector('[data-club-cam-sa]');
    if (!btn) {
      host.insertAdjacentHTML('beforeend', saToggleHtml());
      btn = host.querySelector('[data-club-cam-sa]');
    }
    if (!btn || btn.getAttribute('data-wired') === '1') return;
    btn.setAttribute('data-wired', '1');

    function refresh() {
      return Promise.all([
        fetchCamStatus(),
        fetch('/auth/session?path=' + encodeURIComponent((window.location && window.location.pathname) || '/'), {
          credentials: 'include',
          cache: 'no-store',
        })
          .then(function (r) {
            return r && r.ok ? r.json() : null;
          })
          .catch(function () {
            return null;
          }),
      ]).then(function (pair) {
        var data = pair[0];
        var sa = !!(data && data.can_toggle) || isSaSession(pair[1]);
        applyCamPublic(host, data, sa);
        return data;
      });
    }

    btn.addEventListener('click', function () {
      var next = btn.getAttribute('aria-pressed') !== 'true';
      btn.disabled = true;
      fetch('/api/super-admin/club-cam/hyc', {
        method: 'PATCH',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ visible: next }),
      })
        .then(function (r) {
          return r && r.ok ? r.json() : null;
        })
        .then(function (out) {
          applyCamPublic(host, out, true);
        })
        .finally(function () {
          btn.disabled = false;
        });
    });
    refresh().catch(function () {});
    window.setInterval(function () {
      refresh().catch(function () {});
    }, 20000);
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
    loadScript('/js/regatta-slot-card.js?v=' + JS_VER)
      .then(function () {
        return loadScript('/js/mm-lipton-reels-card.js?v=' + JS_VER);
      })
      .then(function () {
        if (typeof window.dispatchEvent === 'function') window.dispatchEvent(new Event('resize'));
      })
      .catch(function () {});
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
