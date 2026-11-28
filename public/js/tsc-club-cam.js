/**
 * TSC Theewater club cam.
 * Play only the SailingSA HLS proxy. Never fetch skylinewebcams.com or
 * hd-auth.skylinewebcams.com from the browser — that returns copyright_violation.
 * Buffer one 3s Skyline segment, then play at 1x. Target is 2–3s behind live
 * (one TARGETDURATION). Do not chase the live edge — that skips.
 */
(function () {
  'use strict';
  if (window.__SSA_TSC_CLUB_CAM__) return;
  window.__SSA_TSC_CLUB_CAM__ = true;

  var HLS_SRC = 'https://cdn.jsdelivr.net/npm/hls.js@1.5.20/dist/hls.min.js';
  var CSS_ID = 'tsc-club-cam-css';
  var hlsWait = null;
  var CANON_RID = '2026-11-28-tsc-cape-classic';
  var START_BUFFER_S = 2.5;
  var HLS_LIVE = {
    enableWorker: true,
    lowLatencyMode: false,
    liveSyncDurationCount: 1,
    liveMaxLatencyDurationCount: 3,
    liveDurationInfinity: true,
    maxLiveSyncPlaybackRate: 1,
    startFragPrefetch: true,
    maxBufferLength: 6,
    maxMaxBufferLength: 9,
    backBufferLength: 9
  };

  function camRid() {
    var path = String((window.location && window.location.pathname) || '')
      .replace(/\/+$/, '')
      .toLowerCase();
    var m = path.match(/^\/(?:regatta|event)\/([^/]*tsc-cape-classic[^/]*)/);
    if (m && m[1]) return m[1];
    var el = document.querySelector('[data-regatta-id]');
    var rid = el ? String(el.getAttribute('data-regatta-id') || '').trim().toLowerCase() : '';
    if (rid.indexOf('tsc-cape-classic') !== -1) return rid;
    return CANON_RID;
  }

  function playPath() {
    return '/api/regatta/' + encodeURIComponent(camRid()) + '/tsc-live-cam';
  }

  function statusPath() {
    return '/api/regatta/' + encodeURIComponent(camRid()) + '/tsc-live-cam-status';
  }

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
      '.club-tsc-cam .tsc-cam-clock{position:absolute;left:8px;bottom:8px;z-index:2;color:#fff;font:700 13px/1.2 Arial,Helvetica,sans-serif;letter-spacing:.02em;text-shadow:0 1px 2px #000;background:rgba(0,0,0,.55);padding:4px 8px;border-radius:4px}' +
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
    return playPath() + '?t=' + Date.now() + '&fresh=1';
  }

  function formatWhen(ms) {
    try {
      return new Intl.DateTimeFormat('en-GB', {
        timeZone: 'Africa/Johannesburg',
        weekday: 'short',
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hourCycle: 'h23'
      }).format(new Date(ms));
    } catch (e) {
      return '';
    }
  }

  function setStamp(box, online) {
    var stamp = box.querySelector('[data-tsc-cam-stamp]');
    if (!stamp) {
      stamp = document.createElement('div');
      stamp.className = 'tsc-cam-stamp';
      stamp.setAttribute('data-tsc-cam-stamp', '');
      stamp.innerHTML =
        '<span class="tsc-cam-stamp-dot" aria-hidden="true"></span>' +
        '<span data-tsc-cam-stamp-label>Offline</span>';
      var cell = box.querySelector('.cam-shot, .cam-cell') || box;
      cell.appendChild(stamp);
    }
    stamp.classList.toggle('tsc-cam-stamp--off', !online);
    var label = stamp.querySelector('[data-tsc-cam-stamp-label]');
    if (label) label.textContent = online ? 'LIVE' : 'Offline';
  }

  function watchPicture(box, video) {
    var lastT = -1;
    var lastMove = 0;
    var shown = 0;
    function clockEl() {
      var el = box.querySelector('[data-tsc-cam-clock]');
      if (!el) {
        el = document.createElement('div');
        el.className = 'tsc-cam-clock';
        el.setAttribute('data-tsc-cam-clock', '');
        var cell = box.querySelector('.cam-shot, .cam-cell') || box;
        cell.appendChild(el);
      }
      return el;
    }
    function tick() {
      var moving = false;
      if (video && video.videoWidth > 1 && video.readyState >= 2 && video.currentTime > lastT + 0.04) {
        lastT = video.currentTime;
        lastMove = Date.now();
        moving = true;
      }
      var online = moving || (lastMove && Date.now() - lastMove < 4000 && video && video.videoWidth > 1);
      setStamp(box, online);
      var clock = clockEl();
      if (online) {
        shown = Date.now();
        clock.textContent = formatWhen(shown);
      } else if (shown) {
        clock.textContent = formatWhen(shown);
      } else {
        clock.textContent = '';
      }
    }
    tick();
    window.setInterval(function () {
      if (!document.hidden) tick();
    }, 1000);
  }

  function bufferedAhead(video) {
    try {
      var t = video.currentTime || 0;
      var b = video.buffered;
      var i;
      var end = 0;
      for (i = 0; i < b.length; i += 1) {
        if (b.start(i) <= t + 0.2 && b.end(i) > end) end = b.end(i);
      }
      return Math.max(0, end - t);
    } catch (e) {
      return 0;
    }
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
    video.removeAttribute('poster');
    var retryTimer = 0;
    var started = false;
    function goPlay() {
      var p = video.play();
      if (p && p.catch) p.catch(function () {});
    }
    function playWhenBuffered() {
      if (started) {
        if (video.paused) goPlay();
        return;
      }
      if (bufferedAhead(video) < START_BUFFER_S) return;
      started = true;
      goPlay();
    }
    function armRetry(delay) {
      if (retryTimer) window.clearTimeout(retryTimer);
      retryTimer = window.setTimeout(function () {
        retryTimer = 0;
        if (video.videoWidth > 0) return;
        if (video.readyState >= 2 || (video.buffered && video.buffered.length)) {
          armRetry(4000);
          return;
        }
        begin();
      }, delay || 12000);
    }
    function begin() {
      started = false;
      if (box._tscHls) {
        try { box._tscHls.destroy(); } catch (e) {}
        box._tscHls = null;
      }
      var src = playUrl();
      withHls(function (Hls) {
        if (Hls && Hls.isSupported()) {
          var hls = new Hls(HLS_LIVE);
          box._tscHls = hls;
          hls.loadSource(src);
          hls.attachMedia(video);
          hls.on(Hls.Events.FRAG_BUFFERED, playWhenBuffered);
          hls.on(Hls.Events.BUFFER_APPENDED, playWhenBuffered);
          hls.on(Hls.Events.ERROR, function (_ev, data) {
            if (data && data.fatal) armRetry(3000);
          });
          armRetry(12000);
          return;
        }
        video.onerror = function () { armRetry(3000); };
        video.src = src;
        video.addEventListener('canplay', playWhenBuffered);
        armRetry(12000);
      });
    }
    video.addEventListener('waiting', playWhenBuffered);
    begin();
    watchPicture(box, video);
  }

  window.SSATscClubCam = { start: start, playUrl: playPath(), statusUrl: statusPath(), HLS_LIVE: HLS_LIVE };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start);
  } else {
    start();
  }
})();
