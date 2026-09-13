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
    var list = (videos || []).slice();
    function byRecent(a, b) {
      var al = mmFbLive(a) ? 1 : 0;
      var bl = mmFbLive(b) ? 1 : 0;
      if (bl !== al) return bl - al;
      return String((b && b.started_at) || '').localeCompare(String((a && a.started_at) || ''));
    }
    if (!isCapeClassic()) {
      list.sort(byRecent);
      return list;
    }
    var mm = [];
    var cam = [];
    var i;
    for (i = 0; i < list.length; i++) {
      if (isWebcam(list[i])) cam.push(list[i]);
      else mm.push(list[i]);
    }
    mm.sort(byRecent);
    return mm.concat(cam);
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

  function isAdvertFile(v) {
    return String((v && v.play_url) || '').indexOf('/assets/adverts/') === 0;
  }

  function hasFacebookEmbed(v) {
    var href = String((v && (v.embed_url || v.permalink || v.url)) || '').trim();
    return /facebook\.com/i.test(href);
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

  var LAST_CAM_STILL = '/assets/adverts/mm-cape-classic/zvyc-live-cam.jpg';
  var CAM_THUMB_API = '/api/regatta/2026-09-13-zvyc-cape-classic/zvyc-live-cam-thumb';
  var CAM_STATUS_API = '/api/regatta/2026-09-13-zvyc-cape-classic/zvyc-live-cam-status';

  function camStillSrc(v) {
    var snap = String((v && (v.live_snap || v.snap || v.thumb)) || '').split('?')[0];
    if (!snap || /4040\.jpg|skylinewebcams\.com\/temp\//i.test(snap) || snap.indexOf('/zvyc-live-cam-thumb') >= 0) {
      return LAST_CAM_STILL;
    }
    return snap;
  }

  function liveThumbSrc(v, fresh) {
    var root = cardEl();
    if (isWebcam(v) && root && root._mmLiveGrab && !fresh) return root._mmLiveGrab;
    // Compact thumb is a still + stamp, not a live stream. Do not cache-bust
    // on every layout — that re-downloads the jpg and slows the page.
    if (isWebcam(v)) return LAST_CAM_STILL;
    var base = String((v && v.thumb) || '').split('?')[0];
    return base || '';
  }

  function parseStillAt(value) {
    var ms = Date.parse(String(value || ''));
    return ms === ms ? ms : 0;
  }

  function fmtCamStamp(ms, withSec) {
    if (!ms) return '';
    var opts = {
      timeZone: 'Africa/Johannesburg',
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    };
    if (withSec) opts.second = '2-digit';
    try {
      return new Intl.DateTimeFormat('en-GB', opts).format(new Date(ms)).replace(/,/g, '');
    } catch (e) {
      return '';
    }
  }

  function fmtClock(ms) {
    if (!ms) return '';
    var opts = {
      timeZone: 'Africa/Johannesburg',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    };
    try {
      return new Intl.DateTimeFormat('en-GB', opts).format(new Date(ms));
    } catch (e) {
      return '';
    }
  }

  function fmtLastLive(ms) {
    if (!ms) return '';
    var opts = {
      timeZone: 'Africa/Johannesburg',
      weekday: 'short',
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    };
    try {
      return new Intl.DateTimeFormat('en-GB', opts).format(new Date(ms)).replace(/,/g, '');
    } catch (e) {
      return fmtCamStamp(ms, false);
    }
  }

  function camStampHtml() {
    return (
      '<div class="mm-lipton-reels-cam-stamp" data-mm-cam-stamp hidden>' +
      '<span class="mm-lipton-reels-cam-stamp-dot" aria-hidden="true"></span>' +
      '<span data-mm-cam-stamp-label></span>' +
      '<span data-mm-cam-stamp-time></span>' +
      '</div>'
    );
  }

  function ensureCamStampOn(box) {
    if (!box) return null;
    var el = box.querySelector('[data-mm-cam-stamp]');
    if (el && !el.querySelector('[data-mm-cam-stamp-label]')) {
      el.parentNode.removeChild(el);
      el = null;
    }
    if (el) return el;
    box.insertAdjacentHTML('beforeend', camStampHtml());
    return box.querySelector('[data-mm-cam-stamp]');
  }

  function setCamUpstream(root, live, stillMs, lastLiveMs) {
    if (!root) return;
    if (stillMs) root._mmCamStillAt = stillMs;
    if (lastLiveMs) root._mmCamLastLiveAt = lastLiveMs;
    root._mmCamUpstream = !!live;
    paintCamStamps(root);
  }

  function paintCamStamps(root) {
    if (!root) return;
    var live = !!root._mmCamUpstream;
    var lastMs = root._mmCamLastLiveAt || 0;
    var nowTxt = fmtClock(Date.now());
    var lastTxt = lastMs ? fmtLastLive(lastMs) : '';
    var hosts = [];
    var thumbs = root.querySelectorAll('.mm-lipton-reels-thumb');
    var i;
    for (i = 0; i < thumbs.length; i++) {
      if (thumbs[i].querySelector('[data-mm-webcam-live]')) hosts.push(thumbs[i]);
    }
    var stage = root.querySelector('[data-mm-stage]');
    var hud = root.querySelector('[data-mm-hud]');
    var stageCam =
      stage &&
      (stage.querySelector('[data-mm-webcam-live]') ||
        (root._mmCamReady && root.querySelector('[data-mm-hero-video]')) ||
        (hud && isCapeClassic()));
    if (hud && stageCam) hosts.push(hud);
    else if (stage && stageCam) hosts.push(stage);
    for (i = 0; i < hosts.length; i++) {
      var stamp = ensureCamStampOn(hosts[i]);
      if (!stamp) continue;
      stamp.hidden = false;
      stamp.classList.toggle('mm-lipton-reels-cam-stamp--live', live);
      stamp.classList.toggle('mm-lipton-reels-cam-stamp--off', !live);
      var label = stamp.querySelector('[data-mm-cam-stamp-label]');
      var timeEl = stamp.querySelector('[data-mm-cam-stamp-time]');
      if (label) label.textContent = live ? 'LIVE' : 'Offline';
      if (timeEl) timeEl.textContent = live ? nowTxt : lastTxt;
    }
  }

  function applyCamHeaders(root, r) {
    if (!root || !r) return;
    var stillMs =
      parseStillAt(r.headers.get('X-Zvyc-Cam-Still-At')) || parseStillAt(r.headers.get('Last-Modified'));
    var lastLiveMs = parseStillAt(r.headers.get('X-Zvyc-Cam-Last-Live'));
    var liveHdr = String(r.headers.get('X-Zvyc-Cam-Live') || '').trim();
    var live = liveHdr === '1' ? true : liveHdr === '0' ? false : false;
    if (!r.ok) live = false;
    setCamUpstream(root, live, stillMs, lastLiveMs);
  }

  function pollCamStatus(root) {
    if (!root || !isCapeClassic()) return Promise.resolve();
    return scrapeZvycCamToken().then(function (tok) {
      var url = CAM_STATUS_API + '?t=' + Date.now();
      if (tok) url += '&a=' + encodeURIComponent(tok);
      return fetch(url, { credentials: 'same-origin', cache: 'no-store' });
    })
      .then(function (r) {
        if (!r || !r.ok) return null;
        return r.json();
      })
      .then(function (data) {
        if (!data) return;
        var stillMs = parseStillAt(data.still_at);
        var lastLiveMs = parseStillAt(data.last_live_at);
        var live = !!data.live;
        if (live) lastLiveMs = lastLiveMs || Date.now();
        setCamUpstream(root, live, stillMs, lastLiveMs);
      })
      .catch(function () {});
  }

  function startCamStampClock(root) {
    if (!root || root._mmCamStampTimer) return;
    paintCamStamps(root);
    pollCamStatus(root);
    root._mmCamStampTimer = window.setInterval(function () {
      paintCamStamps(root);
    }, 1000);
    root._mmCamStatusTimer = window.setInterval(function () {
      pollCamStatus(root);
    }, 20000);
  }

  function refreshSavedCamStill(root) {
    if (!root) return Promise.resolve(false);
    var tok = camTokenOf(root);
    var url = CAM_THUMB_API + '?t=' + Date.now();
    if (tok) url += '&a=' + encodeURIComponent(tok);
    return fetch(url, { credentials: 'same-origin', cache: 'no-store' })
      .then(function (r) {
        applyCamHeaders(root, r);
        if (!r.ok) return false;
        var imgs = root.querySelectorAll('[data-mm-webcam-live]');
        var src = LAST_CAM_STILL + '?t=' + Date.now();
        var i;
        for (i = 0; i < imgs.length; i++) imgs[i].src = src;
        hideThumbCamLoad(root);
        return true;
      })
      .catch(function () {
        setCamUpstream(root, false);
        return false;
      });
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
      return withCamQuery(u, tok, true);
    }
    if (u) return u;
    var id = String((v && v.id) || '').replace(/[^0-9]/g, '');
    if (!id) return '';
    if (advertFolder() === 'mm-cape-classic') return '/assets/adverts/mm-cape-classic/' + id + '.mp4';
    return '/assets/adverts/mm-lipton/' + id + '.mp4';
  }

  function advertPoster(v) {
    var t = String((v && v.thumb) || '').trim();
    if (t) return t;
    var id = String((v && v.id) || '').replace(/[^0-9]/g, '');
    if (!id) return '';
    return '/assets/adverts/' + advertFolder() + '/' + id + '.jpg';
  }

  function facebookVideoHref(v) {
    var id = String((v && v.id) || '').replace(/[^0-9]/g, '');
    var href = String((v && (v.url || v.permalink)) || '').trim();
    if (href.charAt(0) === '/') href = 'https://www.facebook.com' + href;
    // Meta Embedded Video / Live player wants /{page}/videos/{id}/ or
    // video.php?v={id}. /reel/{id}/ is oEmbed-post for Reels, not Live.
    if (id && (!href || /\/reel\//i.test(href) || mmFbLive(v))) {
      href = 'https://www.facebook.com/marin.megastoresa/videos/' + id + '/';
    }
    return href;
  }

  function isPhone() {
    return window.matchMedia('(max-width: 599px)').matches;
  }

  function livePluginQuery() {
    return '&show_text=false&autoplay=1&mute=0&playsinline=1&width=476&height=280';
  }

  function liveStreamUrl(v) {
    var u = String((v && v.stream_url) || '').trim();
    if (!u || /\/assets\/adverts\//i.test(u)) return '';
    return u;
  }

  function armUnmute(video) {
    if (!video || video._mmArmUnmute) return;
    video._mmArmUnmute = true;
    function go() {
      video.muted = false;
      video.defaultMuted = false;
      video.volume = 1;
      video.removeAttribute('muted');
      var p = video.play();
      if (p && p.catch) p.catch(function () {});
    }
    document.addEventListener('touchend', go, { capture: true, passive: true });
    document.addEventListener('click', go, { capture: true });
  }

  function playNativeLive(root, clip, src) {
    var stage = root.querySelector('[data-mm-stage]');
    var video = ensureHeroVideo(root);
    if (!video || !src) return;
    pauseHero(root);
    var iframes = stage ? stage.querySelectorAll('iframe') : [];
    var i;
    for (i = 0; i < iframes.length; i++) {
      if (iframes[i].parentNode) iframes[i].parentNode.removeChild(iframes[i]);
    }
    video.muted = false;
    video.defaultMuted = false;
    video.volume = 1;
    video.playsInline = true;
    video.setAttribute('playsinline', '');
    video.setAttribute('webkit-playsinline', '');
    video.removeAttribute('muted');
    video.removeAttribute('controls');
    video.controls = false;
    if (video.getAttribute('src') !== src) video.src = src;
    if (stage) {
      stage.classList.add('mm-lipton-reels-stage--playing');
      if (video.parentNode !== stage) stage.appendChild(video);
    }
    var playPromise = video.play();
    if (playPromise && playPromise.catch) {
      playPromise.catch(function () {
        video.muted = true;
        video.setAttribute('muted', '');
        var retry = video.play();
        if (retry && retry.catch) retry.catch(function () {});
        armUnmute(video);
      });
    }
  }

  function kickCompactLive(root) {
    var nodes = root.querySelectorAll('video[data-mm-compact-live]');
    var i;
    for (i = 0; i < nodes.length; i++) {
      var el = nodes[i];
      el.playsInline = true;
      el.setAttribute('playsinline', '');
      el.setAttribute('webkit-playsinline', '');
      el.muted = false;
      el.volume = 1;
      var p = el.play();
      if (p && p.catch) {
        p.catch(function () {
          el.muted = true;
          var r = el.play();
          if (r && r.catch) r.catch(function () {});
          armUnmute(el);
        });
      }
    }
  }

  function embedUrl(v) {
    var href = facebookVideoHref(v);
    var u = '';
    if (mmFbLive(v) && href) {
      u =
        'https://www.facebook.com/plugins/video.php?href=' +
        encodeURIComponent(href) +
        livePluginQuery();
      return u;
    }
    u = String((v && v.embed_url) || '').trim();
    if (!u && href) {
      u =
        'https://www.facebook.com/plugins/video.php?href=' +
        encodeURIComponent(href) +
        '&show_text=false';
    }
    if (!u) return '';
    if (u.indexOf('autoplay=') < 0) u += (u.indexOf('?') >= 0 ? '&' : '?') + 'autoplay=1';
    if (u.indexOf('mute=') < 0) u += '&mute=0';
    if (u.indexOf('playsinline=') < 0) u += '&playsinline=1';
    if (u.indexOf('width=') < 0) u += '&width=476&height=280';
    return u;
  }

  function startEmbedPlayback(root, clip) {
    var stage = root.querySelector('[data-mm-stage]');
    var src = embedUrl(clip);
    if (!stage || !src) return;
    pauseHero(root);
    var iframes = stage.querySelectorAll('iframe');
    var i;
    for (i = 0; i < iframes.length; i++) {
      if (iframes[i].parentNode) iframes[i].parentNode.removeChild(iframes[i]);
    }
    var iframe = document.createElement('iframe');
    iframe.src = src;
    iframe.setAttribute('allow', 'autoplay; fullscreen; encrypted-media; picture-in-picture');
    iframe.setAttribute('allowfullscreen', '');
    iframe.setAttribute('scrolling', 'no');
    iframe.setAttribute('frameborder', '0');
    iframe.setAttribute('playsinline', '');
    iframe.setAttribute('webkit-playsinline', '');
    iframe.setAttribute('title', 'LIVE');
    iframe.style.cssText =
      'position:absolute;inset:0;width:100%;height:100%;border:0;background:#000;z-index:2;pointer-events:auto';
    stage.appendChild(iframe);
    stage.classList.add('mm-lipton-reels-stage--playing');
  }

  function posterHtml(v) {
    if (mmFbLive(v)) {
      return '';
    }
    if (isWebcam(v)) {
      return (
        '<img src="' +
        esc(LAST_CAM_STILL) +
        '" alt="ZVYC live cam" data-mm-webcam-live loading="lazy" decoding="async">' +
        camStampHtml()
      );
    }
    var src = advertPoster(v);
    if (src) {
      return '<img src="' + esc(src) + '" alt="" loading="lazy" decoding="async">';
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
        fb_title: 'ZVYC Cam',
        fb_sub: 'Zeekoevlei',
      };
    }
    if (mmFbLive(clip)) {
      return {
        fb_owner_logo: '/assets/adverts/mm-lipton/fb-page-marine-megastore.jpg',
        fb_title: 'LIVE',
        fb_sub: 'Marine Megastore LIVE',
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

  function liveEmbedIframeHtml(v) {
    if (!mmFbLive(v)) return '';
    var src = embedUrl(v);
    if (!src) return '';
    return (
      '<iframe data-mm-compact-live src="' +
      esc(src) +
      '" allow="autoplay; fullscreen; encrypted-media; picture-in-picture" allowfullscreen playsinline webkit-playsinline scrolling="no" frameborder="0" title="LIVE"></iframe>'
    );
  }

  function liveCompactPlayerHtml(v) {
    var stream = liveStreamUrl(v);
    if (stream) {
      return (
        '<video data-mm-compact-live autoplay playsinline webkit-playsinline preload="auto" src="' +
        esc(stream) +
        '" title="LIVE"></video>'
      );
    }
    return liveEmbedIframeHtml(v);
  }

  function liveCardHtml(v) {
    return (
      '<div class="mm-lipton-reels-tile mm-lipton-reels-tile--live">' +
      '<div class="mm-lipton-reels-thumb mm-lipton-reels-thumb--live" style="aspect-ratio:16 / 9">' +
      liveCompactPlayerHtml(v) +
      '<button type="button" class="mm-lipton-reels-thumb-hit" data-mm-vid="' +
      esc((v && v.id) || '') +
      '" aria-label="Play LIVE"></button>' +
      '</div></div>'
    );
  }

  function latestThumbHtml(v, videos, skipHit) {
    var cam = isWebcam(v);
    return (
      '<div class="mm-lipton-reels-thumb mm-lipton-reels-thumb--latest" style="aspect-ratio:16 / 9">' +
      posterHtml(v) +
      latestChromeHtml(chromeSource(v, videos), cam ? 'mm-lipton-reels-clip-chrome--zvyc' : '') +
      '<span class="mm-lipton-reels-play" aria-hidden="true"></span>' +
      (skipHit ? '' : thumbHit(v)) +
      '</div>'
    );
  }

  function compactTileHtml(v, videos, isLatest) {
    if (mmFbLive(v)) return '';
    var id = (v && v.id) || '';
    var label = isWebcam(v) ? 'Play live cam' : 'Play reel';
    return (
      '<button type="button" class="mm-lipton-reels-tile mm-lipton-reels-tile--reel' +
      (isLatest ? ' mm-lipton-reels-tile--latest' : '') +
      '" data-mm-vid="' +
      esc(id) +
      '" aria-label="' +
      esc(label) +
      '">' +
      latestThumbHtml(v, videos, true) +
      '</button>'
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
        if (this.getAttribute('data-mm-last-still') === '1') return;
        this.setAttribute('data-mm-last-still', '1');
        this.src = LAST_CAM_STILL;
        setCamUpstream(root, false);
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
    wireWebcamThumbLoad(root, clip);
    pollCamStatus(root);
  }

  function emptyReelSlotHtml() {
    return (
      '<div class="mm-lipton-reels-tile mm-lipton-reels-tile--slot">' +
      '<div class="mm-lipton-reels-thumb" style="aspect-ratio:16 / 9">' +
      '<span class="mm-lipton-reels-thumb-ph" aria-hidden="true"></span>' +
      '</div></div>'
    );
  }

  function thumbsThatFit(avail, total, liveN) {
    var count = total || 1;
    var extraLive = liveN ? 1 : 0;
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
      h = (avail - GAP * (k + extraLive) - 4 * (1 + k + extraLive)) / (art + (k + extraLive) * vid);
      if (h >= minH) n = k;
      else break;
    }
    return n;
  }

  function reelVideos(videos) {
    var out = [];
    var i;
    for (i = 0; i < (videos || []).length; i++) {
      if (!mmFbLive(videos[i])) out.push(videos[i]);
    }
    return out;
  }

  function ensureLiveSlot(root) {
    var slot = root.querySelector('[data-mm-live-slot]');
    if (slot) return slot;
    var row = root.querySelector('.mm-lipton-reels-compact');
    var brand = root.querySelector('.mm-lipton-reels-brand');
    if (!row || !brand) return null;
    slot = document.createElement('div');
    slot.className = 'mm-lipton-reels-live-slot';
    slot.setAttribute('data-mm-live-slot', '');
    slot.setAttribute('hidden', '');
    slot.setAttribute('aria-label', 'Marine Megastore LIVE');
    row.insertBefore(slot, brand.nextSibling);
    return slot;
  }

  function paintLiveSlot(root, videos) {
    var slot = ensureLiveSlot(root);
    if (!slot) return null;
    var live = firstMmFbLive(videos);
    if (!live) {
      slot.setAttribute('hidden', '');
      slot.innerHTML = '';
      slot.removeAttribute('data-mm-live-id');
      slot.style.display = 'none';
      slot.style.width = '';
      slot.style.height = '';
      return null;
    }
    slot.removeAttribute('hidden');
    slot.style.display = 'block';
    var key = String(live.id || '') + ':' + (liveStreamUrl(live) ? 's' : 'e');
    if (slot.getAttribute('data-mm-live-id') !== key) {
      slot.innerHTML = liveCardHtml(live);
      slot.setAttribute('data-mm-live-id', key);
    }
    kickCompactLive(root);
    return live;
  }

  function compactTilesHtml(videos) {
    var parts = [];
    var i;
    var reels = reelVideos(videos);
    if (reels.length) {
      for (i = 0; i < reels.length; i++) parts.push(compactTileHtml(reels[i], videos, i === 0));
    } else {
      parts.push(emptyReelSlotHtml());
    }
    var extra = placeholderCount(reels);
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
    ensureCamStampOn(stage);
    paintCamStamps(root);
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
      root._mmCamReady = false;
      video.style.opacity = '';
      showWebcamSnap(root, clip);
      setCamUpstream(root, false);
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
        var hud = root.querySelector('[data-mm-hud]');
        var snap = stage && stage.querySelector('[data-mm-webcam-live]');
        if (snap && snap.parentNode) snap.parentNode.removeChild(snap);
        if (hud) ensureCamStampOn(hud);
        else if (stage) ensureCamStampOn(stage);
        pollCamStatus(root);
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

  function startHeroPlayback(root, clip, state) {
    var stage = root.querySelector('[data-mm-stage]');
    if (isWebcam(clip) && stage) {
      stopTrackOverlay();
      root._mmLiveGrab = '';
      stage.classList.add('mm-lipton-reels-stage--playing');
      paintWebcamPoster(root, clip);
      showCamLoad(root);
      scrapeZvycCamToken(true).then(function () {
        var src = playUrl(clip);
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
    if (mmFbLive(clip)) {
      var stream = liveStreamUrl(clip);
      if (stream) {
        playNativeLive(root, clip, stream);
        if (state) {
          var liveVideo = root.querySelector('[data-mm-hero-video]');
          if (liveVideo) showPlayerUi(root, state, liveVideo);
        }
        return;
      }
      startEmbedPlayback(root, clip);
      return;
    }
    var video = ensureHeroVideo(root);
    if (!video || !clip) return;
    var src = playUrl(clip);
    var poster = advertPoster(clip);
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
    if (poster) video.setAttribute('poster', poster);
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
    var liveLogo = root.getAttribute('data-mm-brand-live') || '';
    if (!img || !soon) return;
    var liveOn = !!firstMmFbLive(videos);
    var has = hasRealReels(reelVideos(videos));
    var next;
    if (liveOn) next = liveLogo || '/assets/adverts/mm-powered-by-live.png?v=mmcc2';
    else if (has) next = '/assets/adverts/mm-powered-by-event-reels.png?v=mmr2';
    else next = soon;
    if (img.getAttribute('src') !== next) img.setAttribute('src', next);
    var alt = 'Powered by Marine Megastore Coming Soon';
    if (liveOn) alt = 'Powered by Marine Megastore Live Streaming';
    else if (has) alt = 'Powered by Marine Megastore Event Reels';
    img.setAttribute('alt', alt);
    var link = img.closest && img.closest('.mm-lipton-reels-brand');
    if (link) link.setAttribute('href', MM_STORE_HOME);
  }

  function videoKey(videos) {
    return (videos || [])
      .map(function (v) {
        return [
          String((v && (v.id || v.url)) || ''),
          v && v.is_live ? '1' : '0',
          String((v && v.thumb) || ''),
          String((v && v.play_url) || ''),
          String((v && v.fb_sub) || ''),
          String((v && v.stream_url) || ''),
        ].join('~');
      })
      .join('|');
  }

  function mmFbLive(v) {
    // Live is Facebook embed only. A file under /assets/adverts/ is a reel.
    return !!(v && v.is_live && !isWebcam(v) && !isAdvertFile(v) && hasFacebookEmbed(v));
  }

  function firstMmFbLive(videos) {
    var list = sortVideos(videos || []);
    var i;
    for (i = 0; i < list.length; i++) {
      if (mmFbLive(list[i])) return list[i];
    }
    return null;
  }

  function startFeedPoll(root, payload, state) {
    if (root.getAttribute('data-mm-poll') !== '1') return;
    var rid = root.getAttribute('data-regatta-id') || '';
    if (!rid) return;
    var url = '/api/regatta/' + encodeURIComponent(rid) + '/mm-live-fb-feed';
    function apply(data) {
      var videos = (data && data.videos) || [];
      var prevLive = firstMmFbLive(payload.videos);
      if (videoKey(videos) === videoKey(payload.videos)) return;
      payload.videos = videos;
      syncBrand(root, videos);
      var live = firstMmFbLive(videos);
      if (live && (!prevLive || String(prevLive.id) !== String(live.id))) {
        openClip(root, payload, state, live.id);
        return;
      }
      if (prevLive && !live) {
        collapse(root, payload, state);
        return;
      }
      if (!state.expanded) paint(root, payload, state);
    }
    function tick() {
      fetch(url, { credentials: 'same-origin', cache: 'no-store' })
        .then(function (r) {
          return r.ok ? r.json() : null;
        })
        .then(function (data) {
          if (data) apply(data);
        })
        .catch(function () {});
    }
    var pollMs = 60000;
    try {
      if (isCapeClassic()) pollMs = 2000;
      else if ((payload.videos || []).length) pollMs = 300000;
    } catch (e1) {}
    window.setInterval(tick, pollMs);
    tick();
  }

  function layoutCompactStrip(root, videos) {
    var row = root.querySelector('.mm-lipton-reels-compact');
    var brand = root.querySelector('.mm-lipton-reels-brand');
    var compact = root.querySelector('[data-mm-compact]');
    if (!row || !brand || !compact || root.classList.contains('mm-lipton-reels--expanded')) return;
    var avail = row.clientWidth;
    if (avail <= 0) return;
    syncBrand(root, videos);
    var live = paintLiveSlot(root, videos);
    var liveN = live ? 1 : 0;
    var reels = reelVideos(videos);
    var extra = placeholderCount(reels);
    var tileCount = (reels.length || 1) + extra;
    var nFit = thumbsThatFit(avail, tileCount, liveN);
    if (isCapeClassic() && !hasRealReels(reels) && !isMobilePortrait()) nFit = 5;
    var wrap = root.querySelector('.mm-lipton-reels-rail-wrap');
    if (wrap) wrap.style.display = '';
    var countKey =
      videoKey(videos) + ':' + extra + ':' + liveN + ':' + (isMobilePortrait() ? 'mp' : 'w');
    if (compact.getAttribute('data-mm-count') !== countKey) {
      compact.innerHTML = compactTilesHtml(videos);
      compact.setAttribute('data-mm-count', countKey);
      wireWebcamThumbLoad(root, (videos || []).filter(isWebcam)[0]);
    }
    var art = ART_W / ART_H;
    var vid = VID_W / VID_H;
    var border = 4;
    var cols = nFit + liveN;
    var innerH = (avail - GAP * cols - border * (1 + cols)) / (art + cols * vid);
    if (innerH < 40) innerH = 40;
    var outerH = innerH + border;
    var thumbW = innerH * vid + border;
    brand.style.width = innerH * art + border + 'px';
    brand.style.height = outerH + 'px';
    if (wrap) wrap.style.height = outerH + 'px';
    var liveSlot = root.querySelector('[data-mm-live-slot]');
    if (liveSlot && live) {
      liveSlot.style.width = thumbW + 'px';
      liveSlot.style.height = outerH + 'px';
      var liveThumbs = liveSlot.querySelectorAll('.mm-lipton-reels-thumb, .mm-lipton-reels-tile');
      var li;
      for (li = 0; li < liveThumbs.length; li++) {
        liveThumbs[li].style.width = thumbW + 'px';
        liveThumbs[li].style.height = outerH + 'px';
      }
    }
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
      if (!clip || isWebcam(clip) || mmFbLive(clip)) continue;
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
    startHeroPlayback(root, clip, state);
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
      if (isWebcam(picked.current)) startHeroPlayback(root, picked.current, state);
      revealPlayingClip(root);
      return;
    }
    if (!wasExpanded) {
      paint(root, payload, state);
      revealPlayingClip(root);
      startHeroPlayback(root, picked.current, state);
      preloadNeighbors(root, payload, state);
      revealPlayingClip(root);
      showPlayerUi(root, state, root.querySelector('[data-mm-hero-video]'));
      return;
    }
    var before = clipIndex(picked.videos, prevId);
    var after = clipIndex(picked.videos, picked.current.id);
    var dir = after >= before ? 1 : -1;
    state.sliding = true;
    revealPlayingClip(root);
    startHeroPlayback(root, picked.current, state);
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

  function stopCompactLive(root) {
    var nodes = root.querySelectorAll('video[data-mm-compact-live]');
    var i;
    for (i = 0; i < nodes.length; i++) {
      try {
        nodes[i].pause();
      } catch (e) {}
    }
  }

  function paint(root, payload, state) {
    var picked = currentVideo(payload, state);
    parkHeroVideo(root);
    root.classList.toggle('mm-lipton-reels--expanded', !!state.expanded);
    root.classList.toggle('mm-lipton-reels--compact', !state.expanded);
    if (state.expanded) {
      stopCompactLive(root);
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

  function injectHideCss() {
    var id = 'mm-lipton-reels-hide-css';
    var s = document.getElementById(id);
    if (!s) {
      s = document.createElement('style');
      s.id = id;
      document.head.appendChild(s);
    }
    s.textContent =
      '.mm-lipton-reels-hide{color:#dc2626!important;font-size:0.95rem!important;font-weight:800!important;letter-spacing:.02em;}' +
      '.mm-lipton-reels-cam-stamp{position:absolute;left:118px;right:76px;top:8px;z-index:7;pointer-events:none;' +
      'display:flex;flex-direction:row;align-items:center;justify-content:center;gap:5px;flex-wrap:nowrap;' +
      'padding:2px 8px;border-radius:4px;background:rgba(0,16,24,.72);color:#fff;white-space:nowrap;' +
      'overflow:hidden;text-overflow:ellipsis;max-width:calc(100% - 194px);' +
      'text-shadow:0 1px 2px rgba(0,0,0,.85);font:700 11px/1.2 Arial,Helvetica,sans-serif}' +
      '.mm-lipton-reels-thumb .mm-lipton-reels-cam-stamp{left:4px;right:4px;top:4px;padding:2px 6px;font-size:9px;' +
      'max-width:none;z-index:3;justify-content:flex-start}' +
      '.mm-lipton-reels-hud .mm-lipton-reels-cam-stamp{left:118px;right:76px;top:8px;max-width:none}' +
      '.mm-lipton-reels-cam-stamp[hidden]{display:none!important}' +
      '.mm-lipton-reels-cam-stamp-dot{flex:0 0 auto;width:8px;height:8px;border-radius:50%;background:#94a3b8}' +
      '.mm-lipton-reels-cam-stamp--live .mm-lipton-reels-cam-stamp-dot{background:#ef4444;box-shadow:0 0 6px #ef4444;' +
      'animation:mm-cam-live-pulse 1s ease-in-out infinite}' +
      '.mm-lipton-reels-cam-stamp--off .mm-lipton-reels-cam-stamp-dot{background:#94a3b8;box-shadow:none;animation:none}' +
      '@keyframes mm-cam-live-pulse{0%,100%{opacity:1}50%{opacity:.35}}' +
      '.mm-lipton-reels-cam-stamp [data-mm-cam-stamp-label]{font-weight:800;letter-spacing:.03em}' +
      '.mm-lipton-reels-cam-stamp [data-mm-cam-stamp-time]{font-weight:700;opacity:.95}' +
      '.mm-lipton-reels-compact{display:flex;flex-wrap:nowrap;align-items:stretch}' +
      '.mm-lipton-reels-brand{order:0}' +
      '.mm-lipton-reels-live-slot{flex:0 0 auto;min-width:0;align-self:stretch;order:1}' +
      '.mm-lipton-reels-tile--reel{display:block;margin:0;padding:0;border:0;background:transparent;cursor:pointer;min-width:44px;min-height:44px;flex:0 0 auto}' +
      '.mm-lipton-reels-clip-chrome{pointer-events:none}' +
      '.mm-lipton-reels-thumb-hit{z-index:8!important;pointer-events:auto}' +
      '.mm-lipton-reels-rail-wrap{order:2}' +
      '.mm-lipton-reels-live-slot[hidden]{display:none!important;width:0!important;min-width:0!important;margin:0!important;padding:0!important;border:0!important;overflow:hidden}' +
      '.mm-lipton-reels-live-slot .mm-lipton-reels-tile{display:block;width:100%;height:100%;margin:0}' +
      '.mm-lipton-reels-thumb--live{position:relative;overflow:hidden;background:#111;border:2px solid #ef4444}' +
      '.mm-lipton-reels-thumb--live iframe,.mm-lipton-reels-thumb--live video{position:absolute;inset:0;width:100%;height:100%;border:0;background:#000;z-index:1;object-fit:cover}' +
      '.mm-lipton-reels-thumb--live iframe{pointer-events:none}' +
      '@media (max-width:599px){.mm-lipton-reels-thumb--live iframe,.mm-lipton-reels-thumb--live video{pointer-events:auto}' +
      '.mm-lipton-reels-player-wrap{width:100%;max-width:100%}}' +
      '.mm-lipton-reels-stage{position:relative}' +
      '.mm-lipton-reels--expanded .mm-lipton-reels-hud{pointer-events:none}' +
      '.mm-lipton-reels--expanded .mm-lipton-reels-hide{pointer-events:auto}' +
      '.mm-lipton-reels--expanded .mm-lipton-reels-player-ui{pointer-events:auto!important;z-index:6}' +
      '.mm-lipton-reels--expanded .mm-lipton-reels-player-ui--on .mm-lipton-reels-player-hud{pointer-events:auto!important}' +
      '.mm-lipton-reels--expanded .mm-lipton-reels-stage video,.mm-lipton-reels--expanded .mm-lipton-reels-stage iframe{pointer-events:auto;z-index:2}' +
      '.mm-lipton-reels-live-ph{display:flex;align-items:center;justify-content:center;width:100%;height:100%;' +
      'background:#111;color:#ef4444;font:800 14px/1 Arial,Helvetica,sans-serif}';
  }

  function init() {
    var root = cardEl();
    if (!root) return;
    injectHideCss();
    var payload = readPayload(root);
    var state = { expanded: false, currentId: '', chromeSnap: null, hideTimer: null, playerWired: false, sliding: false, didSwipe: false };
    var video = ensureHeroVideo(root);
    var first = sortVideos(payload.videos || [])[0];
    if (first && video && !isWebcam(first) && !mmFbLive(first)) {
      var src = playUrl(first);
      if (first.thumb) video.setAttribute('poster', first.thumb);
      if (src) video.src = src;
    }
    paint(root, payload, state);
    syncBrand(root, payload.videos || []);
    kickCompactLive(root);
    if (isCapeClassic()) startCamStampClock(root);
    startFeedPoll(root, payload, state);
    state.chromeSnap = snapshotChromeSize(root);
    var bootLive = firstMmFbLive(payload.videos || []);
    if (bootLive) openClip(root, payload, state, bootLive.id);

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
