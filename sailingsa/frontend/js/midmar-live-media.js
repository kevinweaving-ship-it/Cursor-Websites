/**
 * Midmar Cup Event URL — HMYC venue weather + club camera.
 * Place: between event header and fleet header.
 * Weather is identical to /club/hmyc (agromet-midmar).
 * Camera is the same HMYC JPEG snapshot, expanded to MP width, refresh 60s.
 */
(function () {
  'use strict';
  if (window.__SSA_MIDMAR_LIVE_MEDIA__) return;
  window.__SSA_MIDMAR_LIVE_MEDIA__ = true;

  var RID = '2026-09-19-hmyc-midmar-cup';
  var HOST_ID = 'midmar-live-media';
  var WX_ID = 'ssa-regatta-slot-card';
  var CAM_ID = 'midmar-hmyc-cam';
  var CSS_ID = 'midmar-live-media-css';
  var JS_VER = 'midmarwx2';
  var STILL = 'https://hmyccam1.nwsza.net/latest.jpg';
  var CAM_HREF = 'https://agromet.ukzn.ac.za/midmar/index.html#canvas_container';
  var POLL_MS = 60000;

  function onMidmar() {
    var path = String((window.location && window.location.pathname) || '')
      .replace(/\/+$/, '')
      .toLowerCase();
    return path === '/regatta/' + RID || path.indexOf('/regatta/' + RID + '/') === 0;
  }

  function injectCss() {
    if (document.getElementById(CSS_ID)) return;
    var s = document.createElement('style');
    s.id = CSS_ID;
    s.textContent =
      '.regatta-page > .midmar-live-media{width:100%;max-width:100%;box-sizing:border-box;display:flex;flex-direction:column;gap:0;margin:0;padding:0;border:0;background:transparent;box-shadow:none;}' +
      '.regatta-page > .midmar-live-media .ssa-regatta-slot-card{order:0;margin-top:10px;width:100%;max-width:100%;padding:0!important;}' +
      '.regatta-page > .midmar-live-media .midmar-hmyc-cam{order:1;margin-top:10px;width:100%;max-width:100%;padding:0!important;overflow:hidden;background:#000;}' +
      '.midmar-hmyc-cam .cam-frame{position:relative;display:block;width:100%;aspect-ratio:16/9;background:#000;overflow:hidden;}' +
      '.midmar-hmyc-cam .cam-frame img{display:block;width:100%;height:118%;margin-top:-10%;object-fit:cover;object-position:center bottom;background:#000;}' +
      '.midmar-hmyc-cam .mm-lipton-reels-cam-stamp{position:absolute;left:8px;top:8px;z-index:3;pointer-events:none;display:flex;flex-direction:row;align-items:center;gap:5px;padding:2px 8px;border-radius:4px;background:rgba(0,16,24,.72);color:#fff;white-space:nowrap;text-shadow:0 1px 2px rgba(0,0,0,.85);font:700 11px/1.2 Arial,Helvetica,sans-serif;}' +
      '.midmar-hmyc-cam .mm-lipton-reels-cam-stamp-dot{flex:0 0 auto;width:8px;height:8px;border-radius:50%;background:#94a3b8;}' +
      '.midmar-hmyc-cam .mm-lipton-reels-cam-stamp [data-mm-cam-stamp-label]{font-weight:800;letter-spacing:.03em;}' +
      '.midmar-hmyc-cam .mm-lipton-reels-cam-stamp [data-mm-cam-stamp-time]{font-weight:700;opacity:.95;}' +
      '@media screen and (orientation:portrait) and (max-width:767px){' +
      '.regatta-page > .midmar-live-media .midmar-hmyc-cam{width:100vw;max-width:100vw;margin-left:calc(50% - 50vw);margin-right:calc(50% - 50vw);border-left:0;border-right:0;border-radius:0;}' +
      '}' +
      '@media print{.midmar-live-media{display:none!important}}';
    document.head.appendChild(s);
  }

  function fmtHm(ms) {
    try {
      return new Date(ms).toLocaleTimeString('en-GB', {
        timeZone: 'Africa/Johannesburg',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
      });
    } catch (e) {
      var d = new Date(ms);
      var h = d.getHours();
      var m = d.getMinutes();
      return (h < 10 ? '0' : '') + h + ':' + (m < 10 ? '0' : '') + m;
    }
  }

  function makeWx() {
    var wx = document.getElementById(WX_ID);
    if (!wx) {
      wx = document.createElement('section');
      wx.id = WX_ID;
      wx.className = 'card ssa-wx-card ssa-regatta-slot-card';
    }
    wx.setAttribute('data-weather-club', 'HMYC');
    wx.setAttribute('data-weather-station', 'agromet-midmar');
    wx.setAttribute('data-weather-role', 'venue');
    wx.setAttribute('aria-label', 'HMYC venue wind');
    return wx;
  }

  function makeCam() {
    var cam = document.getElementById(CAM_ID);
    if (!cam) {
      cam = document.createElement('section');
      cam.id = CAM_ID;
    }
    cam.className = 'card midmar-hmyc-cam';
    cam.setAttribute('aria-label', 'HMYC club cam');
    cam.setAttribute('data-mm-cam-status', '/api/club-cam/hmyc');
    if (!cam.querySelector('.cam-frame')) {
      cam.innerHTML =
        '<a class="cam-frame" href="' +
        CAM_HREF +
        '" target="_blank" rel="noopener noreferrer">' +
        '<img alt="HMYC club cam" width="1600" height="900" decoding="async">' +
        '<div class="mm-lipton-reels-cam-stamp mm-lipton-reels-cam-stamp--off" data-mm-cam-stamp>' +
        '<span class="mm-lipton-reels-cam-stamp-dot" aria-hidden="true"></span>' +
        '<span data-mm-cam-stamp-label>SNAPSHOT</span>' +
        '<span data-mm-cam-stamp-time></span>' +
        '</div></a>';
    }
    return cam;
  }

  function paintCam(cam) {
    var img = cam.querySelector('img');
    var timeEl = cam.querySelector('[data-mm-cam-stamp-time]');
    var now = Date.now();
    if (img) img.src = STILL + '?t=' + now;
    if (timeEl) timeEl.textContent = 'as at ' + fmtHm(now);
  }

  function startCam(cam) {
    if (cam.getAttribute('data-cam-bound') === '1') return;
    cam.setAttribute('data-cam-bound', '1');
    paintCam(cam);
    window.setInterval(function () {
      if (!document.hidden) paintCam(cam);
    }, POLL_MS);
    document.addEventListener('visibilitychange', function () {
      if (!document.hidden) paintCam(cam);
    });
  }

  function placeHost() {
    var existing = document.getElementById(HOST_ID);
    var host = existing || document.createElement('div');
    host.id = HOST_ID;
    host.className = 'midmar-live-media club-live-media';
    host.setAttribute('aria-label', 'Live weather and club camera');

    var header = document.querySelector('.regatta-header-wrap');
    var fleet = document.querySelector('.fleet-section');
    var page = document.querySelector('.regatta-page');
    if (header && header.parentNode) {
      if (host.previousSibling !== header) header.parentNode.insertBefore(host, header.nextSibling);
    } else if (fleet && fleet.parentNode) {
      fleet.parentNode.insertBefore(host, fleet);
    } else if (page) {
      page.insertBefore(host, page.firstChild);
    } else {
      return null;
    }

    var wx = makeWx();
    var cam = makeCam();
    if (wx.parentNode !== host) host.appendChild(wx);
    if (cam.parentNode !== host) host.appendChild(cam);
    if (wx.nextSibling !== cam) host.insertBefore(wx, cam);
    startCam(cam);
    return host;
  }

  function loadScript(src) {
    return new Promise(function (resolve) {
      var base = src.split('?')[0];
      var found = document.querySelector('script[src*="' + base + '"]');
      if (found) {
        resolve();
        return;
      }
      var s = document.createElement('script');
      s.src = src;
      s.async = false;
      s.onload = function () {
        resolve();
      };
      s.onerror = function () {
        resolve();
      };
      document.head.appendChild(s);
    });
  }

  function boot() {
    if (!onMidmar()) return;
    injectCss();
    if (!placeHost()) return;
    loadScript('/js/regatta-slot-card.js?v=' + JS_VER).then(function () {
      var wx = document.getElementById(WX_ID);
      if (wx && typeof window.ssaMountWeatherCard === 'function') {
        window.ssaMountWeatherCard(wx, { club: 'HMYC', slug: 'agromet-midmar', role: 'venue' });
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
