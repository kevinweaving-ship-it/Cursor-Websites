/**
 * Same clip in three views: compact (next to MM logo), expanded (grid below),
 * and phone landscape. Expanded and landscape paint the same FB logo, labels,
 * arrows, and touch tools. Live / clip / reel rows use this player.
 */
(function () {
  'use strict';

  var ART_W = 320;
  var ART_H = 213;
  var VID_W = 16;
  var VID_H = 9;
  var GAP = 6;
  var TRACK_TEST_ID = '2622643364847262';
  var MM_STORE_HOME = 'https://www.marinemegastore.co.za/';
  var trackRaf = 0;
  var trackRoot = null;
  var trackClip = null;

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function cardEl() {
    return document.getElementById('mmLiptonReels');
  }

  function readPayload(root) {
    try {
      return JSON.parse(root.getAttribute('data-mm-initial') || '{}');
    } catch (e) {
      return {};
    }
  }

  function sortVideos(videos) {
    return (videos || []).slice().sort(function (a, b) {
      return String(b.started_at || '').localeCompare(String(a.started_at || ''));
    });
  }

  function aspectCss(v) {
    var w = parseInt(v && v.width, 10) || 0;
    var h = parseInt(v && v.height, 10) || 0;
    if (w > 0 && h > 0) return w + ' / ' + h;
    var a = String((v && v.aspect) || '').trim();
    if (/^\d+\s*[:/]\s*\d+$/.test(a)) return a.replace(':', ' / ');
    return '16 / 9';
  }

  function advertFolder() {
    var root = cardEl();
    var rid = (root && root.getAttribute('data-regatta-id')) || '';
    if (rid === '2026-09-13-zvyc-cape-classic') return 'mm-cape-classic';
    return 'mm-lipton';
  }

  function isWebcam(v) {
    return !!(v && (v.kind === 'webcam' || v.placeholder || v.id === 'zvyc-live-cam'));
  }

  function hasRealReels(videos) {
    var i;
    for (i = 0; i < (videos || []).length; i++) {
      if (!isWebcam(videos[i])) return true;
    }
    return false;
  }

  var HLS_SRC = 'https://cdn.jsdelivr.net/npm/hls.js@1.5.20/dist/hls.min.js';
  var CAM_PAGE =
    'https://www.skylinewebcams.com/en/webcam/south-africa/western-cape/cape-town/zeekoevlei.html';
  var CAM_SNAP = 'https://www.skylinewebcams.com/temp/4040.jpg';
  var CAM_TOKEN_TTL_MS = 240000;
  var hlsWait = null;

  function isCapeClassic() {
    var root = cardEl();
    return !!(root && root.getAttribute('data-regatta-id') === '2026-09-13-zvyc-cape-classic');
  }

  function isMobilePortrait() {
    return window.matchMedia('(max-width: 599px) and (orientation: portrait)').matches;
  }

  function placeholderCount(videos) {
    if (!isCapeClassic() || hasRealReels(videos)) return 0;
    if (isMobilePortrait()) return 0;
    return 4;
  }

  function camTokenOf(root) {
    if (!root || !root._mmCamToken) return '';
    if (Date.now() - (root._mmCamTokenAt || 0) >= CAM_TOKEN_TTL_MS) return '';
    return root._mmCamToken;
  }

  function withCamQuery(url, token, fresh) {
    var base = String(url || '').split('?')[0];
    if (!base) return '';
    var q = 't=' + Date.now();
    if (token) q += '&a=' + encodeURIComponent(token);
    if (fresh) q += '&fresh=1';
    return base + '?' + q;
  }

  function scrapeZvycCamToken(force) {
    var root = cardEl();
    if (!force) {
      var cached = camTokenOf(root);
      if (cached) return Promise.resolve(cached);
      if (root && root._mmCamTokenWait) return root._mmCamTokenWait;
    }
    var wait = fetch(CAM_PAGE, { mode: 'cors', credentials: 'omit', cache: 'no-store' })
      .then(function (r) {
        return r.text();
      })
      .then(function (html) {
        var m = String(html || '').match(/livee\.m3u8\?a=([A-Za-z0-9_\-=]+)/);
        var tok = m ? m[1] : '';
        if (tok && root) {
          root._mmCamToken = tok;
          root._mmCamTokenAt = Date.now();
        }
        return tok;
      })
      .catch(function () {
        return '';
      });
    if (root) root._mmCamTokenWait = wait;
    return wait.then(function (tok) {
      if (root && root._mmCamTokenWait === wait) root._mmCamTokenWait = null;
      return tok;
    });
  }

  function liveThumbSrc(v, fresh) {
    var root = cardEl();
    if (isWebcam(v) && root && root._mmLiveGrab && !fresh) return root._mmLiveGrab;
    if (isWebcam(v)) {
      var snap = String((v && (v.live_snap || v.snap)) || '').split('?')[0];
      if (!snap) snap = '/api/regatta/2026-09-13-zvyc-cape-classic/zvyc-live-cam-thumb';
      if (root && root._mmCamUseDirectSnap) return CAM_SNAP + '?t=' + Date.now();
      return withCamQuery(snap, camTokenOf(root), fresh);
    }
    var base = String((v && v.thumb) || '').split('?')[0];
    return base ? base + '?t=' + Date.now() : '';
  }

  function grabVideoFrame(video) {
    if (!video || video.readyState < 2 || video.videoWidth < 16) return '';
    var canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    try {
      canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
      return canvas.toDataURL('image/jpeg', 0.74);
    } catch (e) {
      return '';
    }
  }

  function hideThumbCamLoad(root) {
    if (!root) return;
    var boxes = root.querySelectorAll('.mm-lipton-reels-thumb [data-mm-cam-load]');
    var i;
    for (i = 0; i < boxes.length; i++) boxes[i].hidden = true;
    var thumbs = root.querySelectorAll('.mm-lipton-reels-thumb--cam-load');
    for (i = 0; i < thumbs.length; i++) thumbs[i].classList.remove('mm-lipton-reels-thumb--cam-load');
  }

  function showThumbCamLoad(root) {
    if (!root) return;
    var thumbs = root.querySelectorAll('.mm-lipton-reels-thumb--latest');
    var i;
    for (i = 0; i < thumbs.length; i++) {
      if (!thumbs[i].querySelector('[data-mm-webcam-live]')) continue;
      thumbs[i].classList.add('mm-lipton-reels-thumb--cam-load');
      var box = thumbs[i].querySelector('[data-mm-cam-load]');
      if (box) box.hidden = false;
    }
  }

  function applyLiveGrab(root, dataUrl) {
    if (!root || !dataUrl || dataUrl.indexOf('data:image') !== 0) return;
    root._mmLiveGrab = dataUrl;
    var imgs = root.querySelectorAll('[data-mm-webcam-live]');
    var i;
    for (i = 0; i < imgs.length; i++) imgs[i].src = dataUrl;
    hideThumbCamLoad(root);
  }

  function scheduleVideoGrab(root, video) {
    if (!root || !video) return;
    function shoot() {
      var grab = grabVideoFrame(video);
      if (grab) applyLiveGrab(root, grab);
    }
    window.setTimeout(shoot, 1000);
    window.setTimeout(shoot, 3000);
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

  function destroyWebcamHls(root) {
    if (root && root._mmHls) {
      try {
        root._mmHls.destroy();
      } catch (e0) {}
      root._mmHls = null;
    }
  }

  function playUrl(v) {
    var u = String((v && v.play_url) || '').trim();
    if (isWebcam(v)) {
      var root = cardEl();
      var tok = camTokenOf(root);
      if (tok) return 'https://hd-auth.skylinewebcams.com/live.m3u8?a=' + encodeURIComponent(tok);
      return '';
    }
    if (u) return u;
    var id = String((v && v.id) || '').replace(/[^0-9]/g, '');
    if (!id) return '';
    if (advertFolder() === 'mm-cape-classic') return '/assets/adverts/mm-cape-classic/' + id + '.mp4';
    return '/assets/adverts/mm-lipton/' + id + '.mp4';
  }

  function posterHtml(v) {
    if (isWebcam(v)) {
      return (
        '<img src="' +
        esc(liveThumbSrc(v)) +
        '" alt="ZVYC live cam" data-mm-webcam-live loading="lazy" decoding="async">'
      );
    }
    if (v && v.thumb) {
      return '<img src="' + esc(v.thumb) + '" alt="" loading="lazy" decoding="async">';
    }
    return '<span class="mm-lipton-reels-thumb-ph" aria-hidden="true"></span>';
  }

  function exitFsIfInside(root) {
    var fs = document.fullscreenElement || document.webkitFullscreenElement;
    if (!fs || !root.contains(fs)) return;
    var exit = document.exitFullscreen || document.webkitExitFullscreen;
    if (exit) {
      try {
        exit.call(document);
      } catch (e) {}
    }
  }

  function pauseHero(root) {
    var video = root.querySelector('[data-mm-hero-video]');
    if (!video) return;
    try {
      video.pause();
    } catch (e) {}
  }

  function stopAllPlayback(root) {
    exitFsIfInside(root);
    destroyWebcamHls(root);
    hideCamLoad(root);
    pauseHero(root);
    var iframes = root.querySelectorAll('[data-mm-expanded] iframe');
    var i;
    for (i = 0; i < iframes.length; i++) {
      iframes[i].src = 'about:blank';
      iframes[i].removeAttribute('src');
    }
  }

  function ensureHeroVideo(root) {
    var hold = root.querySelector('[data-mm-video-hold]');
    if (!hold) {
      hold = document.createElement('div');
      hold.className = 'mm-lipton-reels-video-hold';
      hold.setAttribute('data-mm-video-hold', '');
      hold.setAttribute('aria-hidden', 'true');
      root.appendChild(hold);
    }
    var video = root.querySelector('[data-mm-hero-video]');
    if (!video) {
      video = document.createElement('video');
      video.setAttribute('data-mm-hero-video', '');
      video.setAttribute('playsinline', '');
      video.setAttribute('webkit-playsinline', '');
      video.setAttribute('preload', 'auto');
      video.muted = false;
      video.defaultMuted = false;
      video.volume = 1;
      video.playsInline = true;
      video.playbackRate = 1;
      video.controls = false;
      video.removeAttribute('controls');
      video.preload = 'auto';
      hold.appendChild(video);
    }
    return video;
  }

  function parkHeroVideo(root) {
    var hold = root.querySelector('[data-mm-video-hold]');
    var video = root.querySelector('[data-mm-hero-video]');
    if (!hold) hold = ensureHeroVideo(root) && root.querySelector('[data-mm-video-hold]');
    if (hold && video && video.parentNode !== hold) hold.appendChild(video);
  }

  function thumbHit(v) {
    return (
      '<button type="button" class="mm-lipton-reels-thumb-hit" data-mm-vid="' +
      esc((v && v.id) || '') +
      '" aria-label="Play reel"></button>'
    );
  }

  function thumbHtml(v) {
    return (
      '<div class="mm-lipton-reels-thumb" style="aspect-ratio:16 / 9">' +
      posterHtml(v) +
      thumbHit(v) +
      '</div>'
    );
  }

  function overlayChromeClass(clip) {
    return (
      'mm-lipton-reels-clip-chrome--overlay' +
      (isWebcam(clip) ? ' mm-lipton-reels-clip-chrome--zvyc' : '')
    );
  }

  function latestChromeHtml(v, extraClass) {
    var logo = (v && v.fb_owner_logo) || '';
    var title = (v && v.fb_title) || '';
    var sub = (v && v.fb_sub) || '';
    if (!logo && !title && !sub) return '';
    var extra = extraClass ? ' ' + extraClass : '';
    var logoAlt = logo.indexOf('Club Logo/ZVYC') !== -1 ? 'ZVYC' : '';
    var img = logo
      ? '<img class="mm-lipton-reels-owner-logo" src="' +
        esc(logo) +
        '" alt="' +
        esc(logoAlt) +
        '" width="40" height="40" decoding="async">'
      : '';
    var copy = '<div class="mm-lipton-reels-clip-copy">';
    if (title) copy += '<div class="mm-lipton-reels-clip-title">' + esc(title) + '</div>';
    if (sub) copy += '<div class="mm-lipton-reels-clip-sub">' + esc(sub) + '</div>';
    copy += '</div>';
    return '<div class="mm-lipton-reels-clip-chrome' + extra + '" aria-hidden="true">' + img + copy + '</div>';
  }

  function chromeSource(clip, videos) {
    var first = (videos && videos[0]) || {};
    var root = cardEl();
    var isCape = root && root.getAttribute('data-regatta-id') === '2026-09-13-zvyc-cape-classic';
    if (isWebcam(clip) || (!clip && isWebcam(first))) {
      return {
        fb_owner_logo: '/artwork/Club Logo/ZVYC.png',
        fb_title: (clip && (clip.fb_title || clip.title)) || first.fb_title || 'ZVYC Live Cam',
        fb_sub: (clip && clip.fb_sub) || first.fb_sub || 'Zeekoevlei · live',
      };
    }
    return {
      fb_owner_logo:
        (clip && clip.fb_owner_logo) ||
        first.fb_owner_logo ||
        (isCape ? '/assets/adverts/mm-lipton/fb-page-marine-megastore.jpg' : ''),
      fb_title: (clip && (clip.fb_title || clip.title)) || first.fb_title || '',
      fb_sub: (clip && clip.fb_sub) || first.fb_sub || (isCape ? 'Marine Megastore' : ''),
    };
  }

  function snapshotChromeSize(root) {
    var chrome = root.querySelector('.mm-lipton-reels-thumb--latest .mm-lipton-reels-clip-chrome');
    if (!chrome) return null;
    var box = chrome.getBoundingClientRect();
    if (!box.width) return null;
    var logo = chrome.querySelector('.mm-lipton-reels-owner-logo');
    var title = chrome.querySelector('.mm-lipton-reels-clip-title');
    var sub = chrome.querySelector('.mm-lipton-reels-clip-sub');
    var cs = window.getComputedStyle(chrome);
    return {
      w: Math.round(box.width),
      pad: cs.padding,
      gap: cs.gap || cs.columnGap,
      logo: logo ? Math.round(logo.getBoundingClientRect().width) : 0,
      title: title ? window.getComputedStyle(title).fontSize : '',
      sub: sub ? window.getComputedStyle(sub).fontSize : '',
    };
  }

  function applyFrozenChrome(root, snap) {
    var el = root.querySelector('.mm-lipton-reels-clip-chrome--overlay');
    if (!el || !snap) return;
    el.style.width = 'auto';
    el.style.maxWidth = 'none';
    el.style.background = 'none';
    if (snap.gap) el.style.setProperty('--mm-chrome-gap', snap.gap);
    if (snap.pad) el.style.setProperty('--mm-chrome-pad', snap.pad);
    if (snap.logo) el.style.setProperty('--mm-chrome-logo', snap.logo + 'px');
    if (snap.title) el.style.setProperty('--mm-chrome-title', snap.title);
    if (snap.sub) el.style.setProperty('--mm-chrome-sub', snap.sub);
  }

  function fmtTime(secs) {
    secs = Math.max(0, Math.floor(Number(secs) || 0));
    var m = Math.floor(secs / 60);
    var r = secs % 60;
    return m + ':' + (r < 10 ? '0' : '') + r;
  }

  function playerUiHtml() {
    return (
      '<div class="mm-lipton-reels-player-ui" data-mm-player-ui>' +
      '<div class="mm-lipton-reels-player-hud" data-mm-player-hud>' +
      '<button type="button" class="mm-lipton-reels-player-toggle" data-mm-toggle-play aria-label="Pause">' +
      '<span class="mm-lipton-reels-icon-play" aria-hidden="true"></span>' +
      '<span class="mm-lipton-reels-icon-pause" aria-hidden="true"><span></span><span></span></span>' +
      '</button>' +
      '<div class="mm-lipton-reels-player-bar">' +
      '<span class="mm-lipton-reels-player-time" data-mm-time>0:00 / 0:00</span>' +
      '<input class="mm-lipton-reels-player-seek" data-mm-seek type="range" min="0" max="1000" value="0" step="1" aria-label="Seek">' +
      '<button type="button" class="mm-lipton-reels-player-mute" data-mm-mute aria-label="Mute">🔊</button>' +
      '</div></div>' +
      '<button type="button" class="mm-lipton-reels-skip mm-lipton-reels-skip--prev" data-mm-skip="-1" aria-label="Previous clip" hidden>‹</button>' +
      '<button type="button" class="mm-lipton-reels-skip mm-lipton-reels-skip--next" data-mm-skip="1" aria-label="Next clip" hidden>›</button>' +
      '</div>'
    );
  }

  function clearHideTimer(state) {
    if (state && state.hideTimer) {
      window.clearTimeout(state.hideTimer);
      state.hideTimer = null;
    }
  }

  function hidePlayerUi(root, state) {
    clearHideTimer(state);
    var ui = root.querySelector('[data-mm-player-ui]');
    if (ui) ui.classList.remove('mm-lipton-reels-player-ui--on');
  }

  function scheduleHidePlayerUi(root, state, video) {
    clearHideTimer(state);
    if (!video || video.paused) return;
    state.hideTimer = window.setTimeout(function () {
      state.hideTimer = null;
      if (video && !video.paused) hidePlayerUi(root, state);
    }, 3000);
  }

  function showPlayerUi(root, state, video) {
    var ui = root.querySelector('[data-mm-player-ui]');
    if (!ui) return;
    ui.classList.add('mm-lipton-reels-player-ui--on');
    syncPlayerUi(root, video);
    scheduleHidePlayerUi(root, state, video);
  }

  function syncPlayerUi(root, video) {
    if (!video) return;
    var toggle = root.querySelector('[data-mm-toggle-play]');
    var timeEl = root.querySelector('[data-mm-time]');
    var seek = root.querySelector('[data-mm-seek]');
    var mute = root.querySelector('[data-mm-mute]');
    var paused = !!video.paused;
    if (toggle) {
      toggle.classList.toggle('is-playing', !paused);
      toggle.setAttribute('aria-label', paused ? 'Play' : 'Pause');
    }
    if (timeEl) timeEl.textContent = fmtTime(video.currentTime) + ' / ' + fmtTime(video.duration);
    if (seek && !seek.hasAttribute('data-mm-seeking')) {
      var dur = video.duration;
      seek.value = dur ? String(Math.round((video.currentTime / dur) * 1000)) : '0';
    }
    if (mute) {
      mute.textContent = video.muted || video.volume === 0 ? '🔇' : '🔊';
      mute.setAttribute('aria-label', video.muted ? 'Unmute' : 'Mute');
    }
  }

  function wirePlayer(root, state) {
    if (state.playerWired) return;
    state.playerWired = true;
    var video = ensureHeroVideo(root);
    video.addEventListener('timeupdate', function () {
      syncPlayerUi(root, video);
      drawTrackFrame();
    });
    video.addEventListener('play', function () {
      syncPlayerUi(root, video);
      scheduleHidePlayerUi(root, state, video);
      loopTrack();
    });
    video.addEventListener('pause', function () {
      syncPlayerUi(root, video);
    });
    root.addEventListener('input', function (ev) {
      var seek = ev.target.closest && ev.target.closest('[data-mm-seek]');
      if (!seek || !root.contains(seek)) return;
      seek.setAttribute('data-mm-seeking', '');
      var dur = video.duration;
      if (dur) video.currentTime = (Number(seek.value) / 1000) * dur;
      scheduleHidePlayerUi(root, state, video);
    });
    root.addEventListener('change', function (ev) {
      var seek = ev.target.closest && ev.target.closest('[data-mm-seek]');
      if (!seek || !root.contains(seek)) return;
      seek.removeAttribute('data-mm-seeking');
    });
  }

  function camLoadHtml() {
    return (
      '<div class="mm-lipton-reels-cam-load" data-mm-cam-load aria-live="polite" aria-label="Loading">' +
      '<span class="mm-lipton-reels-cam-spin" aria-hidden="true"></span>' +
      '<span class="mm-lipton-reels-cam-load-txt">Loading</span>' +
      '</div>'
    );
  }

  function latestThumbHtml(v, videos) {
    var cam = isWebcam(v);
    return (
      '<div class="mm-lipton-reels-thumb mm-lipton-reels-thumb--latest" style="aspect-ratio:16 / 9">' +
      posterHtml(v) +
      latestChromeHtml(chromeSource(v, videos), cam ? 'mm-lipton-reels-clip-chrome--zvyc' : '') +
      '<span class="mm-lipton-reels-play" aria-hidden="true"></span>' +
      thumbHit(v) +
      '</div>'
    );
  }

  function compactTileHtml(v, videos, isLatest) {
    return (
      '<div class="mm-lipton-reels-tile' +
      (isLatest ? ' mm-lipton-reels-tile--latest' : '') +
      '">' +
      latestThumbHtml(v, videos) +
      '</div>'
    );
  }

  function stopWebcamLive(root) {
    if (root && root._mmCamTimer) {
      window.clearInterval(root._mmCamTimer);
      root._mmCamTimer = 0;
    }
  }

  function wireWebcamThumbLoad(root, clip) {
    var imgs = root.querySelectorAll('[data-mm-webcam-live]');
    var i;
    for (i = 0; i < imgs.length; i++) {
      if (imgs[i].getAttribute('data-mm-wired') === '1') continue;
      imgs[i].setAttribute('data-mm-wired', '1');
      imgs[i].addEventListener('load', function () {
        if (this.naturalWidth > 16) hideThumbCamLoad(root);
      });
      imgs[i].addEventListener('error', function () {
        var n = parseInt(this.getAttribute('data-mm-retry') || '0', 10);
        if (n >= 2) return;
        this.setAttribute('data-mm-retry', String(n + 1));
        var rootNow = cardEl();
        if (rootNow) rootNow._mmCamUseDirectSnap = true;
        this.src = CAM_SNAP + '?t=' + Date.now();
      });
    }
  }

  function startWebcamLive(root, clip) {
    if (!root || !isWebcam(clip)) {
      stopWebcamLive(root);
      return;
    }
    if (root._mmLiveGrab) {
      applyLiveGrab(root, root._mmLiveGrab);
      stopWebcamLive(root);
      return;
    }
    function bump() {
      var imgs = root.querySelectorAll('[data-mm-webcam-live]');
      if (root._mmLiveGrab) {
        applyLiveGrab(root, root._mmLiveGrab);
        stopWebcamLive(root);
        return;
      }
      var src = liveThumbSrc(clip, true);
      var i;
      for (i = 0; i < imgs.length; i++) {
        if (src) imgs[i].src = src;
      }
      wireWebcamThumbLoad(root, clip);
    }
    function go() {
      bump();
      stopWebcamLive(root);
      root._mmCamTimer = window.setInterval(function () {
        bump();
      }, 4000);
    }
    scrapeZvycCamToken();
    go();
  }

  function emptyReelSlotHtml() {
    return (
      '<div class="mm-lipton-reels-tile mm-lipton-reels-tile--slot">' +
      '<div class="mm-lipton-reels-thumb" style="aspect-ratio:16 / 9">' +
      '<span class="mm-lipton-reels-thumb-ph" aria-hidden="true"></span>' +
      '</div></div>'
    );
  }

  function thumbsThatFit(avail, total) {
    var count = total || 1;
    var maxN = Math.min(count, 5);
    if (avail <= 0) return 1;
    if (window.matchMedia('(max-width: 599px)').matches) {
      if (!isCapeClassic() || isMobilePortrait()) return 1;
    }
    var art = ART_W / ART_H;
    var vid = VID_W / VID_H;
    var minH = 76;
    var n = 1;
    var k;
    var h;
    for (k = 2; k <= maxN; k++) {
      h = (avail - GAP * k - 4 * (1 + k)) / (art + k * vid);
      if (h >= minH) n = k;
      else break;
    }
    return n;
  }

  function compactTilesHtml(videos) {
    var parts = [];
    var i;
    if (videos && videos.length) {
      for (i = 0; i < videos.length; i++) parts.push(compactTileHtml(videos[i], videos, i === 0));
    } else {
      parts.push(emptyReelSlotHtml());
    }
    var extra = placeholderCount(videos);
    for (i = 0; i < extra; i++) parts.push(emptyReelSlotHtml());
    return parts.join('') || emptyReelSlotHtml();
  }

  function stopTrackOverlay() {
    if (trackRaf) {
      window.cancelAnimationFrame(trackRaf);
      trackRaf = 0;
    }
    trackClip = null;
    if (!trackRoot) return;
    var box = trackRoot.querySelector('[data-mm-track]');
    if (box) box.removeAttribute('data-mm-track-on');
  }

  function drawTrackFrame() {
    if (!trackRoot || !trackClip) return;
    var overlay = window.mmLiptonTrackOverlay;
    if (!overlay || !overlay.draw) return;
    var box = trackRoot.querySelector('[data-mm-track]');
    var canvas = trackRoot.querySelector('[data-mm-track-canvas]');
    var video = trackRoot.querySelector('[data-mm-hero-video]');
    if (!box || !canvas || !video) return;
    if (overlay.kind && overlay.kind(trackClip.id) === 'start') {
      box.style.setProperty('--mm-track-h', '88%');
      void box.offsetHeight;
    } else if (overlay.kind && overlay.kind(trackClip.id) === 'round') {
      var hNow = box.style.getPropertyValue('--mm-track-h');
      if (hNow !== '88%') {
        box.style.setProperty('--mm-track-h', hNow || '74%');
        void box.offsetHeight;
      }
    }
    var cssW = box.clientWidth || 0;
    var cssH = box.clientHeight || 0;
    if (cssW < 8 || cssH < 8) return;
    var dpr = window.devicePixelRatio || 1;
    var pw = Math.round(cssW * dpr);
    var ph = Math.round(cssH * dpr);
    if (canvas.width !== pw) canvas.width = pw;
    if (canvas.height !== ph) canvas.height = ph;
    var ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    /* Stamp first (go-live / started_at), then offset from video vs tracking. */
    var startMs = Date.parse(String(trackClip.started_at || ''));
    if (startMs !== startMs) return;
    if (video.playbackRate !== 1) video.playbackRate = 1;
    var off = Number(trackClip.track_offset_ms);
    if (off !== off) {
      off = overlay.offsetMs ? overlay.offsetMs(trackClip.id) : String(trackClip.id) === TRACK_TEST_ID ? 36000 : 0;
    }
    var ts = startMs + (Number(video.currentTime) || 0) * 1000 + off;
    var dur = Number(video.duration);
    overlay.draw(canvas, ts, cssW, cssH, dur);
  }

  function loopTrack() {
    if (trackRaf) window.cancelAnimationFrame(trackRaf);
    function tick() {
      trackRaf = 0;
      drawTrackFrame();
      var video = trackRoot && trackRoot.querySelector('[data-mm-hero-video]');
      if (trackClip && video && !video.paused) {
        trackRaf = window.requestAnimationFrame(tick);
      }
    }
    trackRaf = window.requestAnimationFrame(tick);
  }

  function syncTrackOverlay(root, clip) {
    trackRoot = root;
    if (root && root.getAttribute('data-regatta-id') === '2026-09-13-zvyc-cape-classic') {
      stopTrackOverlay();
      return;
    }
    var box = root && root.querySelector('[data-mm-track]');
    if (!box) return;
    if (!clip || !window.mmLiptonTrackOverlay || !window.mmLiptonTrackOverlay.usesClip(clip.id)) {
      stopTrackOverlay();
      trackRoot = root;
      return;
    }
    trackClip = clip;
    box.setAttribute('data-mm-track-on', '');
    var overlay = window.mmLiptonTrackOverlay;
    if (!overlay || !overlay.load) return;
    overlay.load(String(clip.id), function () {
      drawTrackFrame();
      loopTrack();
    });
  }

  function stageHtml(v, videos) {
    if (!v) return '<p class="mm-lipton-reels-waiting">No clip yet.</p>';
    var root = cardEl();
    var isCape = root && root.getAttribute('data-regatta-id') === '2026-09-13-zvyc-cape-classic';
    var track = isCape
      ? ''
      : '<div class="mm-lipton-reels-track" data-mm-track aria-hidden="true"><canvas data-mm-track-canvas></canvas></div>';
    return (
      '<div class="mm-lipton-reels-player-wrap" data-mm-wrap style="--mm-aspect:' +
      aspectCss(v) +
      ';aspect-ratio:' +
      aspectCss(v) +
      '">' +
      '<div class="mm-lipton-reels-stage mm-lipton-reels-stage--playing" data-mm-stage></div>' +
      track +
      '<div class="mm-lipton-reels-hud" data-mm-hud>' +
      latestChromeHtml(chromeSource(v, videos), overlayChromeClass(v)) +
      playerUiHtml() +
      '</div></div>'
    );
  }

  function paintWebcamPoster(root, clip) {
    var stage = root.querySelector('[data-mm-stage]');
    if (!stage) return;
    var img = stage.querySelector('[data-mm-webcam-live]');
    if (!img) {
      img = document.createElement('img');
      img.setAttribute('data-mm-webcam-live', '');
      img.alt = 'ZVYC live cam';
      stage.appendChild(img);
    }
    stage.classList.add('mm-lipton-reels-stage--playing');
    startWebcamLive(root, clip);
  }

  function hideCamLoad(root) {
    if (root && root._mmCamLoadTimer) {
      window.clearTimeout(root._mmCamLoadTimer);
      root._mmCamLoadTimer = 0;
    }
    var boxes = root && root.querySelectorAll('[data-mm-cam-load]');
    var i;
    if (boxes) {
      for (i = 0; i < boxes.length; i++) boxes[i].hidden = true;
    }
    hideThumbCamLoad(root);
  }

  function showCamLoad(root) {
    var stage = root && root.querySelector('[data-mm-stage]');
    if (!stage) return;
    var box = stage.querySelector('[data-mm-cam-load]');
    if (!box) {
      box = document.createElement('div');
      box.className = 'mm-lipton-reels-cam-load';
      box.setAttribute('data-mm-cam-load', '');
      box.setAttribute('aria-live', 'polite');
      box.setAttribute('aria-label', 'Loading');
      box.innerHTML =
        '<span class="mm-lipton-reels-cam-spin" aria-hidden="true"></span>' +
        '<span class="mm-lipton-reels-cam-load-txt">Loading</span>';
      stage.appendChild(box);
    }
    box.hidden = false;
  }

  function showWebcamSnap(root, clip) {
    destroyWebcamHls(root);
    hideCamLoad(root);
    if (root) root._mmCamUseDirectSnap = true;
    var stage = root.querySelector('[data-mm-stage]');
    if (!stage) return;
    var video = root.querySelector('[data-mm-hero-video]');
    if (video && video.parentNode === stage) {
      try {
        video.pause();
      } catch (e) {}
      var hold = root.querySelector('[data-mm-video-hold]');
      if (hold) hold.appendChild(video);
    }
    paintWebcamPoster(root, clip);
    startWebcamLive(root, clip);
  }

  /* Timed 2026-09-10 live: playlist 2.0-3.2s, first seg 3.4-4.4s, playlist+2seg 9-11s. */
  var CAM_LOAD_MIN_MS = 600;
  var CAM_LOAD_HANG_MS = 15000;

  function playWebcamVideo(root, clip, video, src) {
    destroyWebcamHls(root);
    root._mmCamReady = false;
    paintWebcamPoster(root, clip);
    showCamLoad(root);
    video.muted = true;
    video.defaultMuted = true;
    video.setAttribute('muted', '');
    video.playsInline = true;
    video.style.opacity = '0';
    var poster = liveThumbSrc(clip);
    if (poster) video.setAttribute('poster', poster);
    var started = Date.now();
    function onFail() {
      video.style.opacity = '';
      showWebcamSnap(root, clip);
    }
    function reveal() {
      if (root._mmCamReady) return;
      var wait = CAM_LOAD_MIN_MS - (Date.now() - started);
      function go() {
        if (root._mmCamReady) return;
        root._mmCamReady = true;
        hideCamLoad(root);
        stopWebcamLive(root);
        video.style.opacity = '';
        var stage = root.querySelector('[data-mm-stage]');
        var snap = stage && stage.querySelector('[data-mm-webcam-live]');
        if (snap && snap.parentNode) snap.parentNode.removeChild(snap);
      }
      if (wait > 0) window.setTimeout(go, wait);
      else go();
    }
    function goPlay() {
      var p = video.play();
      if (p && p.catch) p.catch(onFail);
    }
    video.addEventListener('playing', function () {
      reveal();
      scheduleVideoGrab(root, video);
    }, { once: true });
    root._mmCamLoadTimer = window.setTimeout(function () {
      root._mmCamLoadTimer = 0;
      if (!root._mmCamReady) hideCamLoad(root);
    }, CAM_LOAD_HANG_MS);
    if (video.canPlayType && video.canPlayType('application/vnd.apple.mpegurl')) {
      video.src = src;
      goPlay();
      return;
    }
    withHls(function (Hls) {
      if (!Hls || !Hls.isSupported) {
        onFail();
        return;
      }
      var hls = new Hls({ enableWorker: true, lowLatencyMode: true });
      root._mmHls = hls;
      hls.loadSource(src);
      hls.attachMedia(video);
      hls.on(Hls.Events.MANIFEST_PARSED, goPlay);
      hls.on(Hls.Events.ERROR, function (_ev, data) {
        if (data && data.fatal) onFail();
      });
    });
  }

  function startHeroPlayback(root, clip) {
    var stage = root.querySelector('[data-mm-stage]');
    if (isWebcam(clip) && stage) {
      stopTrackOverlay();
      root._mmLiveGrab = '';
      stage.classList.add('mm-lipton-reels-stage--playing');
      paintWebcamPoster(root, clip);
      showCamLoad(root);
      scrapeZvycCamToken(true).then(function (tok) {
        var src = tok ? playUrl(clip) : '';
        var video = ensureHeroVideo(root);
        if (video && src) {
          if (video.parentNode !== stage) stage.appendChild(video);
          playWebcamVideo(root, clip, video, src);
          return;
        }
        showWebcamSnap(root, clip);
      });
      return;
    }
    var video = ensureHeroVideo(root);
    if (!video || !clip) return;
    var src = playUrl(clip);
    video.muted = false;
    video.defaultMuted = false;
    video.volume = 1;
    video.playsInline = true;
    video.setAttribute('playsinline', '');
    video.setAttribute('webkit-playsinline', '');
    video.playbackRate = 1;
    video.removeAttribute('muted');
    video.removeAttribute('controls');
    video.controls = false;
    if (clip.thumb) video.setAttribute('poster', clip.thumb);
    if (src && video.getAttribute('src') !== src) {
      video.src = src;
    } else {
      try {
        video.currentTime = 0;
      } catch (e) {}
    }
    if (stage) {
      stage.classList.add('mm-lipton-reels-stage--playing');
      if (video.parentNode !== stage) stage.appendChild(video);
    }
    try {
      video.load();
    } catch (e) {}
    var playPromise = video.play();
    if (playPromise && playPromise.catch) {
      playPromise.catch(function () {
        var retry = video.play();
        if (retry && retry.catch) retry.catch(function () {});
      });
    }
    syncTrackOverlay(root, clip);
  }

  function clipDayKey(v) {
    var raw = String((v && v.started_at) || '');
    var m = raw.match(/^(\d{4}-\d{2}-\d{2})/);
    return m ? m[1] : '';
  }

  function clipDayLabel(key) {
    var parts = String(key || '').split('-');
    if (parts.length !== 3) return key || '';
    var months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    var days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    var y = parseInt(parts[0], 10);
    var mo = parseInt(parts[1], 10) - 1;
    var da = parseInt(parts[2], 10);
    if (!y || mo < 0 || mo > 11 || !da) return key;
    var dt = new Date(y, mo, da);
    return days[dt.getDay()] + ' ' + da + ' ' + months[mo];
  }

  function clipRace(v) {
    var n = parseInt(v && v.race, 10);
    if (n >= 1 && n <= 10) return n;
    var t = String((v && (v.fb_title || v.title)) || '');
    var m = t.match(/\b(?:race|r)\s*(10|[1-9])\b/i);
    return m ? parseInt(m[1], 10) : 0;
  }

  function clipRaceLabel(v) {
    var custom = String((v && v.race_label) || '').trim();
    if (custom) return custom;
    var n = clipRace(v);
    if (n) return 'Race ' + n;
    var t = String((v && (v.fb_title || v.title)) || '');
    var day = t.match(/\bday\s*(\d+)\b/i);
    if (day) return 'Day ' + day[1];
    return 'Other';
  }

  function gridHtml(videos, currentId) {
    var rest = (videos || []).filter(function (v) {
      return v && v.id !== currentId;
    });
    if (!rest.length) return '';
    var days = [];
    var dayMap = {};
    var i;
    for (i = 0; i < rest.length; i++) {
      var clip = rest[i];
      var dayKey = clipDayKey(clip) || 'other';
      var raceKey = String(clipRace(clip));
      if (!dayMap[dayKey]) {
        dayMap[dayKey] = { key: dayKey, races: [], raceMap: {} };
        days.push(dayMap[dayKey]);
      }
      var day = dayMap[dayKey];
      if (!day.raceMap[raceKey]) {
        day.raceMap[raceKey] = { key: raceKey, label: clipRaceLabel(clip), items: [] };
        day.races.push(day.raceMap[raceKey]);
      }
      day.raceMap[raceKey].items.push(clip);
    }
    var parts = ['<div class="mm-lipton-reels-days" data-mm-days>'];
    for (i = 0; i < days.length; i++) {
      var d = days[i];
      parts.push('<section class="mm-lipton-reels-day">');
      parts.push('<div class="mm-lipton-reels-day-label">' + esc(clipDayLabel(d.key)) + '</div>');
      var r;
      for (r = 0; r < d.races.length; r++) {
        var g = d.races[r];
        parts.push('<section class="mm-lipton-reels-race">');
        parts.push('<div class="mm-lipton-reels-race-label">' + esc(g.label) + '</div>');
        parts.push('<div class="mm-lipton-reels-grid" role="list">');
        var j;
        for (j = 0; j < g.items.length; j++) {
          parts.push(
            '<div class="mm-lipton-reels-grid-item" role="listitem">' +
              latestThumbHtml(g.items[j], videos) +
              '</div>'
          );
        }
        parts.push('</div></section>');
      }
      parts.push('</section>');
    }
    parts.push('</div>');
    return parts.join('');
  }

  function expandedHtml(v, videos) {
    return (
      '<div class="mm-lipton-reels-expanded-bar">' +
      '<button type="button" class="mm-lipton-reels-hide" data-mm-hide>Hide</button>' +
      '</div>' +
      stageHtml(v, videos) +
      gridHtml(videos, v && v.id)
    );
  }

  function syncRailButtons(root) {
    var rail = root.querySelector('[data-mm-compact]');
    var prev = root.querySelector('[data-mm-rail-prev]');
    var next = root.querySelector('[data-mm-rail-next]');
    if (!rail || !prev || !next) return;
    var overflow = rail.scrollWidth - rail.clientWidth > 4;
    var show = overflow && !root.classList.contains('mm-lipton-reels--expanded');
    if (!show) {
      prev.setAttribute('hidden', '');
      next.setAttribute('hidden', '');
      return;
    }
    var sl = rail.scrollLeft;
    var max = rail.scrollWidth - rail.clientWidth;
    if (sl <= 2) prev.setAttribute('hidden', '');
    else prev.removeAttribute('hidden');
    if (sl >= max - 2) next.setAttribute('hidden', '');
    else next.removeAttribute('hidden');
  }

  function scrollRail(root, videos, dir) {
    layoutCompactStrip(root, videos || []);
    var rail = root.querySelector('[data-mm-compact]');
    if (!rail) return;
    var tile = rail.querySelector('.mm-lipton-reels-tile');
    var step = tile ? tile.getBoundingClientRect().width + GAP : 0;
    if (step < 8) step = Math.max(120, rail.clientWidth * 0.85);
    var max = Math.max(0, rail.scrollWidth - rail.clientWidth);
    var target = rail.scrollLeft + dir * step;
    if (target < 0) target = 0;
    if (target > max) target = max;
    function go() {
      if (typeof rail.scrollTo === 'function') {
        try {
          rail.scrollTo({ left: target, behavior: 'smooth' });
          return;
        } catch (e) {}
      }
      rail.scrollLeft = target;
    }
    go();
    window.requestAnimationFrame(function () {
      if (Math.abs(rail.scrollLeft - target) > 8) go();
    });
  }

  function syncBrand(root, videos) {
    var img = root.querySelector('.mm-lipton-reels-brand img');
    var soon = root.getAttribute('data-mm-brand-soon') || '';
    var live = root.getAttribute('data-mm-brand-live') || '';
    if (!img || !soon) return;
    var has = hasRealReels(videos);
    var next = has ? live || '/assets/adverts/mm-powered-by-event-reels.png?v=mmr2' : soon;
    if (img.getAttribute('src') !== next) img.setAttribute('src', next);
    img.setAttribute('alt', has ? 'Powered by Marine Megastore Event Reels' : 'Powered by Marine Megastore Coming Soon');
    var link = img.closest && img.closest('.mm-lipton-reels-brand');
    if (link) link.setAttribute('href', MM_STORE_HOME);
  }

  function videoKey(videos) {
    return (videos || [])
      .map(function (v) {
        return String((v && (v.id || v.url)) || '');
      })
      .join('|');
  }

  function startFeedPoll(root, payload, state) {
    if (root.getAttribute('data-mm-poll') !== '1') return;
    var rid = root.getAttribute('data-regatta-id') || '';
    if (!rid) return;
    var url = '/api/regatta/' + encodeURIComponent(rid) + '/mm-live-fb-feed';
    function apply(data) {
      var videos = (data && data.videos) || [];
      if (videoKey(videos) === videoKey(payload.videos)) return;
      payload.videos = videos;
      syncBrand(root, videos);
      if (!state.expanded) paint(root, payload, state);
    }
    function tick() {
      fetch(url, { credentials: 'same-origin' })
        .then(function (r) {
          return r.ok ? r.json() : null;
        })
        .then(function (data) {
          if (data) apply(data);
        })
        .catch(function () {});
    }
    window.setInterval(tick, (payload.videos || []).length ? 300000 : 60000);
  }

  function layoutCompactStrip(root, videos) {
    var row = root.querySelector('.mm-lipton-reels-compact');
    var brand = root.querySelector('.mm-lipton-reels-brand');
    var compact = root.querySelector('[data-mm-compact]');
    if (!row || !brand || !compact || root.classList.contains('mm-lipton-reels--expanded')) return;
    var avail = row.clientWidth;
    if (avail <= 0) return;
    syncBrand(root, videos);
    var extra = placeholderCount(videos);
    var tileCount = (videos.length || 1) + extra;
    var nFit = thumbsThatFit(avail, tileCount);
    if (isCapeClassic() && !hasRealReels(videos) && !isMobilePortrait()) nFit = 5;
    var wrap = root.querySelector('.mm-lipton-reels-rail-wrap');
    if (wrap) wrap.style.display = '';
    var countKey = String((videos || []).length) + ':' + extra + ':' + (isMobilePortrait() ? 'mp' : 'w');
    if (compact.getAttribute('data-mm-count') !== countKey) {
      compact.innerHTML = compactTilesHtml(videos);
      compact.setAttribute('data-mm-count', countKey);
    }
    startWebcamLive(root, (videos || []).filter(isWebcam)[0]);
    var art = ART_W / ART_H;
    var vid = VID_W / VID_H;
    var border = 4;
    var innerH = (avail - GAP * nFit - border * (1 + nFit)) / (art + nFit * vid);
    if (innerH < 40) innerH = 40;
    var outerH = innerH + border;
    var thumbW = innerH * vid + border;
    brand.style.width = innerH * art + border + 'px';
    brand.style.height = outerH + 'px';
    if (wrap) wrap.style.height = outerH + 'px';
    var thumbs = compact.querySelectorAll('.mm-lipton-reels-thumb');
    var tiles = compact.querySelectorAll('.mm-lipton-reels-tile');
    var i;
    for (i = 0; i < thumbs.length; i++) {
      thumbs[i].style.width = thumbW + 'px';
      thumbs[i].style.height = outerH + 'px';
    }
    for (i = 0; i < tiles.length; i++) {
      tiles[i].style.width = thumbW + 'px';
      tiles[i].style.height = outerH + 'px';
    }
    compact.style.height = outerH + 'px';
    syncRailButtons(root);
  }

  function currentVideo(payload, state) {
    var videos = sortVideos(payload.videos || []);
    var current = null;
    var i;
    for (i = 0; i < videos.length; i++) {
      if (videos[i] && videos[i].id === state.currentId) {
        current = videos[i];
        break;
      }
    }
    if (!current) current = videos[0] || null;
    if (current) state.currentId = current.id;
    return { videos: videos, current: current };
  }

  function clipIndex(videos, id) {
    var i;
    for (i = 0; i < (videos || []).length; i++) {
      if (videos[i] && videos[i].id === id) return i;
    }
    return 0;
  }

  function syncSkipButtons(root, payload, state) {
    var picked = currentVideo(payload, state);
    var idx = clipIndex(picked.videos, state.currentId);
    var prev = root.querySelector('[data-mm-skip="-1"]');
    var next = root.querySelector('[data-mm-skip="1"]');
    if (prev) {
      if (idx <= 0) prev.setAttribute('hidden', '');
      else prev.removeAttribute('hidden');
    }
    if (next) {
      if (idx >= picked.videos.length - 1) next.setAttribute('hidden', '');
      else next.removeAttribute('hidden');
    }
  }

  function bumpSlide(root, dir) {
    var stage = root.querySelector('[data-mm-stage]');
    if (!stage) return;
    stage.style.transition = 'none';
    stage.style.transform = 'translateX(' + (dir > 0 ? '18%' : '-18%') + ')';
    stage.offsetHeight;
    stage.style.transition = 'transform .28s ease';
    stage.style.transform = 'translateX(0)';
  }

  function setOverlayChrome(root, clip, videos, snap) {
    var hud = root.querySelector('[data-mm-hud]');
    if (!hud) return;
    var html = latestChromeHtml(chromeSource(clip, videos), overlayChromeClass(clip));
    var old = hud.querySelector('.mm-lipton-reels-clip-chrome--overlay');
    if (!html) {
      if (old && old.parentNode) old.parentNode.removeChild(old);
      return;
    }
    var box = document.createElement('div');
    box.innerHTML = html;
    var neu = box.firstChild;
    if (old && old.parentNode) old.parentNode.replaceChild(neu, old);
    else hud.insertBefore(neu, hud.firstChild);
    applyFrozenChrome(root, snap);
  }

  function updateExpandedGrid(root, videos, currentId) {
    var expanded = root.querySelector('[data-mm-expanded]');
    if (!expanded) return;
    var html = gridHtml(videos, currentId);
    var days = expanded.querySelector('[data-mm-days]');
    if (!html) {
      if (days && days.parentNode) days.parentNode.removeChild(days);
      return;
    }
    if (days) {
      days.outerHTML = html;
      return;
    }
    expanded.insertAdjacentHTML('beforeend', html);
  }

  function preloadNeighbors(root, payload, state) {
    var picked = currentVideo(payload, state);
    var idx = clipIndex(picked.videos, state.currentId);
    var hold = root.querySelector('[data-mm-video-hold]');
    if (!hold) return;
    var spots = [idx - 1, idx + 1];
    var s;
    for (s = 0; s < spots.length; s++) {
      var clip = picked.videos[spots[s]];
      if (!clip) continue;
      var src = playUrl(clip);
      if (!src) continue;
      var el = hold.querySelector('video[data-mm-pre="' + clip.id + '"]');
      if (!el) {
        el = document.createElement('video');
        el.setAttribute('data-mm-pre', clip.id);
        el.setAttribute('preload', 'auto');
        el.muted = true;
        el.playsInline = true;
        hold.appendChild(el);
      }
      if (el.getAttribute('src') !== src) el.src = src;
    }
  }

  function skipClip(root, payload, state, dir) {
    if (state.sliding) return;
    var picked = currentVideo(payload, state);
    var idx = clipIndex(picked.videos, state.currentId) + dir;
    if (idx < 0 || idx >= picked.videos.length || !picked.videos[idx]) return;
    var clip = picked.videos[idx];
    state.currentId = clip.id;
    state.expanded = true;
    state.sliding = true;
    startHeroPlayback(root, clip);
    setOverlayChrome(root, clip, picked.videos, state.chromeSnap);
    updateExpandedGrid(root, picked.videos, clip.id);
    syncSkipButtons(root, payload, state);
    showPlayerUi(root, state, root.querySelector('[data-mm-hero-video]'));
    bumpSlide(root, dir);
    preloadNeighbors(root, payload, state);
    window.setTimeout(function () {
      state.sliding = false;
    }, 280);
  }

  function revealTopInset() {
    var pad = 8;
    var header = document.querySelector('.site-header');
    if (header && header.getBoundingClientRect) {
      var hr = header.getBoundingClientRect();
      var viewH = (window.visualViewport && window.visualViewport.height) || window.innerHeight || 0;
      if (hr.height > 8 && hr.bottom > 0 && hr.top < viewH * 0.5) pad = Math.round(hr.bottom) + 8;
    }
    return pad;
  }

  function revealScrollParents(el) {
    var out = [];
    var n = el;
    while (n && n !== document.body && n !== document.documentElement) {
      n = n.parentElement;
      if (!n) break;
      var st = window.getComputedStyle ? window.getComputedStyle(n) : null;
      var oy = st ? String(st.overflowY || st.overflow || '') : '';
      if ((oy === 'auto' || oy === 'scroll' || oy === 'overlay') && n.scrollHeight > n.clientHeight + 4) {
        out.push(n);
      }
    }
    out.push(document.scrollingElement || document.documentElement);
    if (document.body && out.indexOf(document.body) < 0) out.push(document.body);
    return out;
  }

  function revealPlayingClip(root) {
    var wrap = (root && root.querySelector('[data-mm-wrap]')) || root;
    if (!wrap || !wrap.getBoundingClientRect) return;
    function go() {
      var cs = window.getComputedStyle ? window.getComputedStyle(wrap) : null;
      if (cs && cs.position === 'fixed') return;
      var pad = revealTopInset();
      try {
        wrap.style.scrollMarginTop = pad + 'px';
      } catch (e0) {}
      try {
        wrap.scrollIntoView({ block: 'start', inline: 'nearest', behavior: 'instant' });
      } catch (e1) {
        try {
          wrap.scrollIntoView({ block: 'start', inline: 'nearest', behavior: 'auto' });
        } catch (e2) {
          try {
            wrap.scrollIntoView(true);
          } catch (e3) {}
        }
      }
      var rect = wrap.getBoundingClientRect();
      var delta = rect.top - pad;
      if (Math.abs(delta) < 2) return;
      var parents = revealScrollParents(wrap);
      var i;
      for (i = 0; i < parents.length; i++) {
        try {
          parents[i].scrollTop = (parents[i].scrollTop || 0) + delta;
        } catch (e4) {}
      }
      try {
        window.scrollTo(0, (window.pageYOffset || 0) + delta);
      } catch (e5) {}
    }
    go();
    window.requestAnimationFrame(function () {
      go();
      window.requestAnimationFrame(go);
    });
    window.setTimeout(go, 50);
    window.setTimeout(go, 160);
    window.setTimeout(go, 320);
  }

  function openClip(root, payload, state, id) {
    var prevId = state.currentId;
    var wasExpanded = !!state.expanded && root.classList.contains('mm-lipton-reels--expanded');
    state.chromeSnap = snapshotChromeSize(root) || state.chromeSnap;
    state.currentId = id || state.currentId;
    state.expanded = true;
    var picked = currentVideo(payload, state);
    if (!picked.current) return;
    if (wasExpanded && picked.current.id === prevId) {
      if (isWebcam(picked.current)) startHeroPlayback(root, picked.current);
      revealPlayingClip(root);
      return;
    }
    if (!wasExpanded) {
      paint(root, payload, state);
      revealPlayingClip(root);
      startHeroPlayback(root, picked.current);
      preloadNeighbors(root, payload, state);
      revealPlayingClip(root);
      return;
    }
    var before = clipIndex(picked.videos, prevId);
    var after = clipIndex(picked.videos, picked.current.id);
    var dir = after >= before ? 1 : -1;
    state.sliding = true;
    revealPlayingClip(root);
    startHeroPlayback(root, picked.current);
    setOverlayChrome(root, picked.current, picked.videos, state.chromeSnap);
    updateExpandedGrid(root, picked.videos, picked.current.id);
    syncSkipButtons(root, payload, state);
    showPlayerUi(root, state, root.querySelector('[data-mm-hero-video]'));
    bumpSlide(root, dir);
    preloadNeighbors(root, payload, state);
    window.setTimeout(function () {
      state.sliding = false;
    }, 280);
    revealPlayingClip(root);
  }

  function ensureExpanded(root) {
    var el = root.querySelector('[data-mm-expanded]');
    if (el) return el;
    el = document.createElement('div');
    el.className = 'mm-lipton-reels-expanded';
    el.setAttribute('data-mm-expanded', '');
    root.appendChild(el);
    return el;
  }

  function removeExpanded(root) {
    parkHeroVideo(root);
    var el = root.querySelector('[data-mm-expanded]');
    if (!el) return;
    el.parentNode.removeChild(el);
  }

  function collapse(root, payload, state) {
    state.expanded = false;
    stopTrackOverlay();
    stopAllPlayback(root);
    hidePlayerUi(root, state);
    removeExpanded(root);
    root.classList.remove('mm-lipton-reels--expanded');
    root.classList.add('mm-lipton-reels--compact');
    layoutCompactStrip(root, sortVideos(payload.videos || []));
  }

  function paint(root, payload, state) {
    var picked = currentVideo(payload, state);
    parkHeroVideo(root);
    root.classList.toggle('mm-lipton-reels--expanded', !!state.expanded);
    root.classList.toggle('mm-lipton-reels--compact', !state.expanded);
    if (state.expanded) {
      var expanded = ensureExpanded(root);
      expanded.innerHTML = expandedHtml(picked.current, picked.videos);
      var stage = expanded.querySelector('[data-mm-stage]');
      var hud = expanded.querySelector('[data-mm-hud]');
      var video = ensureHeroVideo(root);
      if (stage && video) stage.appendChild(video);
      var playerUi = (hud || expanded).querySelector('[data-mm-player-ui]');
      if (hud && playerUi) hud.appendChild(playerUi);
      var overlay = (hud || expanded).querySelector('.mm-lipton-reels-clip-chrome--overlay');
      if (hud && overlay) hud.appendChild(overlay);
      applyFrozenChrome(root, state.chromeSnap);
      wirePlayer(root, state);
      syncSkipButtons(root, payload, state);
      hidePlayerUi(root, state);
      preloadNeighbors(root, payload, state);
      syncTrackOverlay(root, picked.current);
    } else {
      removeExpanded(root);
      layoutCompactStrip(root, picked.videos);
    }
  }

  function init() {
    var root = cardEl();
    if (!root) return;
    var payload = readPayload(root);
    var state = { expanded: false, currentId: '', chromeSnap: null, hideTimer: null, playerWired: false, sliding: false, didSwipe: false };
    var video = ensureHeroVideo(root);
    var first = sortVideos(payload.videos || [])[0];
    if (first && video && !isWebcam(first)) {
      var src = playUrl(first);
      if (first.thumb) video.setAttribute('poster', first.thumb);
      if (src) video.src = src;
    }
    paint(root, payload, state);
    syncBrand(root, payload.videos || []);
    startFeedPoll(root, payload, state);
    state.chromeSnap = snapshotChromeSize(root);

    root.addEventListener('click', function (ev) {
      var prev = ev.target.closest && ev.target.closest('[data-mm-rail-prev]');
      if (prev) {
        ev.preventDefault();
        ev.stopPropagation();
        scrollRail(root, sortVideos(payload.videos || []), -1);
        return;
      }
      var next = ev.target.closest && ev.target.closest('[data-mm-rail-next]');
      if (next) {
        ev.preventDefault();
        ev.stopPropagation();
        scrollRail(root, sortVideos(payload.videos || []), 1);
        return;
      }
      var hide = ev.target.closest && ev.target.closest('[data-mm-hide]');
      if (hide) {
        ev.preventDefault();
        collapse(root, payload, state);
        return;
      }
      var brand = ev.target.closest && ev.target.closest('.mm-lipton-reels-brand');
      if (brand) {
        ev.preventDefault();
        ev.stopPropagation();
        var href = (brand.getAttribute('href') || '').trim() || MM_STORE_HOME;
        window.open(href, '_blank', 'noopener,noreferrer');
        return;
      }
      var playerUi = ev.target.closest && ev.target.closest('[data-mm-player-ui]');
      if (playerUi && root.contains(playerUi)) {
        if (state.didSwipe) {
          state.didSwipe = false;
          return;
        }
        ev.preventDefault();
        ev.stopPropagation();
        var video = root.querySelector('[data-mm-hero-video]');
        if (!video) return;
        var playHit = ev.target.closest('[data-mm-toggle-play]');
        var muteHit = ev.target.closest('[data-mm-mute]');
        var seekHit = ev.target.closest('[data-mm-seek]');
        var skipHit = ev.target.closest('[data-mm-skip]');
        if (skipHit) {
          skipClip(root, payload, state, parseInt(skipHit.getAttribute('data-mm-skip'), 10) || 0);
          return;
        }
        if (playHit) {
          if (video.paused) {
            video.muted = false;
            video.volume = 1;
            var p = video.play();
            if (p && p.catch) p.catch(function () {});
          } else {
            video.pause();
          }
          showPlayerUi(root, state, video);
          return;
        }
        if (muteHit) {
          video.muted = !video.muted;
          if (!video.muted) video.volume = 1;
          showPlayerUi(root, state, video);
          return;
        }
        if (seekHit) {
          showPlayerUi(root, state, video);
          return;
        }
        if (playerUi.classList.contains('mm-lipton-reels-player-ui--on')) hidePlayerUi(root, state);
        else showPlayerUi(root, state, video);
        return;
      }
      var thumb = ev.target.closest && ev.target.closest('[data-mm-vid]');
      if (thumb && root.contains(thumb)) {
        ev.preventDefault();
        openClip(root, payload, state, thumb.getAttribute('data-mm-vid') || state.currentId);
      }
    });

    var ptr = { on: false, x: 0, y: 0 };
    root.addEventListener('pointerdown', function (ev) {
      if (!state.expanded) return;
      var ui = ev.target.closest && ev.target.closest('[data-mm-player-ui]');
      if (!ui || !root.contains(ui)) return;
      if (ev.target.closest('[data-mm-seek],[data-mm-toggle-play],[data-mm-mute],[data-mm-skip]')) return;
      ptr.on = true;
      ptr.x = ev.clientX;
      ptr.y = ev.clientY;
      state.didSwipe = false;
    });
    root.addEventListener('pointerup', function (ev) {
      if (!ptr.on) return;
      ptr.on = false;
      var dx = ev.clientX - ptr.x;
      var dy = ev.clientY - ptr.y;
      if (Math.abs(dx) > 48 && Math.abs(dx) > Math.abs(dy) * 1.35) {
        state.didSwipe = true;
        skipClip(root, payload, state, dx < 0 ? 1 : -1);
      }
    });
    root.addEventListener('pointercancel', function () {
      ptr.on = false;
    });

    var rail = root.querySelector('[data-mm-compact]');
    if (rail) {
      rail.addEventListener(
        'scroll',
        function () {
          syncRailButtons(root);
        },
        { passive: true }
      );
    }

    function afterRotate() {
      if (state.expanded) {
        applyFrozenChrome(root, state.chromeSnap);
        syncSkipButtons(root, payload, state);
      } else {
        layoutCompactStrip(root, sortVideos(payload.videos || []));
      }
    }
    if (window.ResizeObserver) {
      var ro = new ResizeObserver(function () {
        if (!state.expanded) layoutCompactStrip(root, sortVideos(payload.videos || []));
        else {
          applyFrozenChrome(root, state.chromeSnap);
          syncSkipButtons(root, payload, state);
        }
      });
      ro.observe(root);
    } else {
      window.addEventListener('resize', afterRotate);
    }
    window.addEventListener('orientationchange', function () {
      window.setTimeout(afterRotate, 80);
    });
    if (window.matchMedia) {
      var mq = window.matchMedia('(orientation: landscape)');
      if (mq.addEventListener) mq.addEventListener('change', afterRotate);
      else if (mq.addListener) mq.addListener(afterRotate);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
