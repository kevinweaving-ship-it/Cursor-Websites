/**
 * TSC Theewater club cam.
 * Play only the SailingSA HLS proxy. Never fetch skylinewebcams.com or
 * hd-auth.skylinewebcams.com from the browser — that returns copyright_violation.
 */
(function () {
  'use strict';
  if (window.__SSA_TSC_CLUB_CAM__) return;
  window.__SSA_TSC_CLUB_CAM__ = true;

  var PLAY = '/api/regatta/2026-11-28-tsc-cape-classic/tsc-live-cam';
  var STATUS = '/api/regatta/2026-11-28-tsc-cape-classic/tsc-live-cam-status';
  var HLS_SRC = 'https://cdn.jsdelivr.net/npm/hls.js@1.5.20/dist/hls.min.js';
  var CSS_ID = 'tsc-club-cam-css';
  var hlsWait = null;

  function root() {
    return document.getElementById('tsc-club-cam') || document.querySelector('[data-tsc-club-cam]');
  }

  function injectCss() {
    if (document.getElementById(CSS_ID)) return;
    var s = document.createElement('style');
    s.id = CSS_ID;
    s.textContent =
      '.club-tsc-cam,.club-live-cam.club-tsc-cam{width:100%;max-width:100%;margin-top:10px;padding:0;overflow:hidden}' +
      '.club-tsc-cam .cam-shot,.club-tsc-cam .cam-cell{position:relative;aspect-ratio:16/9;width:100%;background:#000;overflow:hidden}' +
      '.club-tsc-cam video{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;background:#000}' +
      '.club-tsc-cam .cam-cap{position:absolute;left:8px;top:8px;z-index:2;color:#fff;font:700 12px Arial,Helvetica,sans-serif;text-shadow:0 1px 2px #000}' +
      '.club-tsc-cam .tsc-cam-stamp{position:absolute;right:8px;top:8px;z-index:2;display:flex;align-items:center;gap:6px;color:#fff;font:700 12px Arial,Helvetica,sans-serif;text-shadow:0 1px 2px #000}' +
      '.club-tsc-cam .tsc-cam-stamp-dot{width:8px;height:8px;border-radius:50%;background:#ef4444}' +
      '.club-tsc-cam .tsc-cam-stamp--off .tsc-cam-stamp-dot{background:#9ca3af}' +
      '.club-tsc-cam[hidden]{display:none!important}';
    document.head.appendChild(s);
  }

  function withHls(cb) {
    if (window.Hls) {
      cb(window.Hls);
      return;
    }
    if (hlsWait) {
      hlsWait.push(cb);
      return;
    }
    hlsWait = [cb];
    var s = document.createElement('script');
    s.src = HLS_SRC;
    s.async = true;
    s.onload = function () {
      var q = hlsWait;
      hlsWait = null;
      var i;
      for (i = 0; i < q.length; i++) q[i](window.Hls);
    };
    s.onerror = function () {
      var q = hlsWait;
      hlsWait = null;
      var i;
      for (i = 0; i < q.length; i++) q[i](null);
    };
    document.head.appendChild(s);
  }

  function playUrl() {
    return PLAY + '?t=' + Date.now() + '&fresh=1';
  }

  function setStamp(box, live) {
    var stamp = box.querySelector('[data-tsc-cam-stamp]');
    if (!stamp) {
      stamp = document.createElement('div');
      stamp.className = 'tsc-cam-stamp';
      stamp.setAttribute('data-tsc-cam-stamp', '');
      stamp.innerHTML =
        '<span class="tsc-cam-stamp-dot" aria-hidden="true"></span>' +
        '<span data-tsc-cam-stamp-label>LIVE</span>';
      var cell = box.querySelector('.cam-shot, .cam-cell') || box;
      cell.appendChild(stamp);
    }
    stamp.classList.toggle('tsc-cam-stamp--off', !live);
    var label = stamp.querySelector('[data-tsc-cam-stamp-label]');
    if (label) label.textContent = live ? 'LIVE' : 'Offline';
  }

  function pollStatus(box) {
    function tick() {
      fetch(STATUS + '?_=' + Date.now(), { credentials: 'same-origin', cache: 'no-store' })
        .then(function (r) {
          return r && r.ok ? r.json() : null;
        })
        .then(function (data) {
          setStamp(box, !!(data && data.live));
        })
        .catch(function () {
          setStamp(box, false);
        });
    }
    tick();
    window.setInterval(function () {
      if (!document.hidden) tick();
    }, 20000);
  }

  function start() {
    var box = root();
    if (!box || box.getAttribute('data-tsc-started') === '1') return;
    box.setAttribute('data-tsc-started', '1');
    injectCss();
    var cell = box.querySelector('.cam-shot, .cam-cell');
    if (!cell) {
      cell = document.createElement('div');
      cell.className = 'cam-shot cam-cell';
      box.appendChild(cell);
    }
    var video = box.querySelector('video');
    if (!video) {
      video = document.createElement('video');
      cell.appendChild(video);
    }
    video.muted = true;
    video.defaultMuted = true;
    video.playsInline = true;
    video.setAttribute('muted', '');
    video.setAttribute('playsinline', '');
    video.setAttribute('webkit-playsinline', '');
    video.controls = false;
    video.removeAttribute('controls');
    var src = playUrl();
    function goPlay() {
      var p = video.play();
      if (p && p.catch) p.catch(function () {});
    }
    withHls(function (Hls) {
      if (Hls && Hls.isSupported()) {
        var hls = new Hls({ enableWorker: true, lowLatencyMode: true });
        box._tscHls = hls;
        hls.loadSource(src);
        hls.attachMedia(video);
        hls.on(Hls.Events.MANIFEST_PARSED, goPlay);
        return;
      }
      video.src = src;
      goPlay();
    });
    pollStatus(box);
  }

  window.SSATscClubCam = { start: start, playUrl: PLAY, statusUrl: STATUS };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start);
  } else {
    start();
  }
})();
