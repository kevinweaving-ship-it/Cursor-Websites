/**
 * Lipton-only Marine Megastore Event Reels card (#mmLiptonReels).
 * Compact: artwork + poster rail. One tap expands and plays a hosted mp4.
 * Facebook plugin iframes cannot start from a parent click — one persistent
 * HTML5 <video> is reused so play() stays inside the same user gesture.
 */
(function () {
  'use strict';

  var ART_W = 320;
  var ART_H = 213;
  var VID_W = 16;
  var VID_H = 9;
  var GAP = 6;

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

  function playUrl(v) {
    var u = String((v && v.play_url) || '').trim();
    if (u) return u;
    var id = String((v && v.id) || '').replace(/[^0-9]/g, '');
    return id ? '/assets/adverts/mm-lipton/' + id + '.mp4' : '';
  }

  function posterHtml(v) {
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

  function latestChromeHtml(v, extraClass) {
    var logo = (v && v.fb_owner_logo) || '';
    var title = (v && v.fb_title) || '';
    var sub = (v && v.fb_sub) || '';
    if (!logo && !title && !sub) return '';
    var extra = extraClass ? ' ' + extraClass : '';
    var img = logo
      ? '<img class="mm-lipton-reels-owner-logo" src="' +
        esc(logo) +
        '" alt="" width="40" height="40" decoding="async">'
      : '';
    var copy = '<div class="mm-lipton-reels-clip-copy">';
    if (title) copy += '<div class="mm-lipton-reels-clip-title">' + esc(title) + '</div>';
    if (sub) copy += '<div class="mm-lipton-reels-clip-sub">' + esc(sub) + '</div>';
    copy += '</div>';
    return '<div class="mm-lipton-reels-clip-chrome' + extra + '" aria-hidden="true">' + img + copy + '</div>';
  }

  function chromeSource(clip, videos) {
    var first = (videos && videos[0]) || {};
    return {
      fb_owner_logo: (clip && clip.fb_owner_logo) || first.fb_owner_logo || '',
      fb_title: (clip && (clip.fb_title || clip.title)) || first.fb_title || '',
      fb_sub: (clip && clip.fb_sub) || first.fb_sub || '',
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
      '</div></div></div>'
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
    });
    video.addEventListener('play', function () {
      syncPlayerUi(root, video);
      scheduleHidePlayerUi(root, state, video);
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

  function latestThumbHtml(v) {
    return (
      '<div class="mm-lipton-reels-thumb mm-lipton-reels-thumb--latest" style="aspect-ratio:16 / 9">' +
      posterHtml(v) +
      latestChromeHtml(v) +
      '<span class="mm-lipton-reels-play" aria-hidden="true"></span>' +
      thumbHit(v) +
      '</div>'
    );
  }

  function compactTileHtml(v, isLatest) {
    if (isLatest) {
      return '<div class="mm-lipton-reels-tile mm-lipton-reels-tile--latest">' + latestThumbHtml(v) + '</div>';
    }
    return '<div class="mm-lipton-reels-tile">' + thumbHtml(v) + '</div>';
  }

  function thumbsThatFit(avail, total) {
    var maxN = Math.min(total || 1, 5);
    if (avail <= 0) return 1;
    if (window.matchMedia('(max-width: 599px)').matches) return 1;
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
    for (i = 0; i < videos.length; i++) parts.push(compactTileHtml(videos[i], i === 0));
    return parts.join('');
  }

  function stageHtml(v, videos) {
    if (!v) return '<p class="mm-lipton-reels-waiting">No clip yet.</p>';
    return (
      '<div class="mm-lipton-reels-stage mm-lipton-reels-stage--playing" data-mm-stage style="--mm-aspect:' +
      aspectCss(v) +
      ';aspect-ratio:' +
      aspectCss(v) +
      '">' +
      latestChromeHtml(chromeSource(v, videos), 'mm-lipton-reels-clip-chrome--overlay') +
      playerUiHtml() +
      '</div>'
    );
  }

  function startHeroPlayback(root, clip) {
    var video = ensureHeroVideo(root);
    var stage = root.querySelector('[data-mm-stage]');
    if (!video || !clip) return;
    var src = playUrl(clip);
    video.muted = false;
    video.defaultMuted = false;
    video.volume = 1;
    video.playsInline = true;
    video.setAttribute('playsinline', '');
    video.setAttribute('webkit-playsinline', '');
    video.removeAttribute('muted');
    video.removeAttribute('controls');
    video.controls = false;
    if (clip.thumb) video.setAttribute('poster', clip.thumb);
    if (src && video.getAttribute('src') !== src) {
      video.src = src;
    }
    if (stage) {
      stage.classList.add('mm-lipton-reels-stage--playing');
      if (video.parentNode !== stage) stage.appendChild(video);
    }
    var playPromise = video.play();
    if (playPromise && playPromise.catch) {
      playPromise.catch(function () {});
    }
  }

  function gridHtml(videos, currentId) {
    var rest = (videos || []).filter(function (v) {
      return v && v.id !== currentId;
    });
    if (!rest.length) return '';
    var parts = ['<div class="mm-lipton-reels-grid" role="list">'];
    var i;
    for (i = 0; i < rest.length; i++) {
      parts.push(
        '<div class="mm-lipton-reels-grid-item" role="listitem">' +
          thumbHtml(rest[i]) +
          '</div>'
      );
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

  function finePointer() {
    return window.matchMedia('(hover: hover) and (pointer: fine)').matches;
  }

  function syncRailButtons(root) {
    var rail = root.querySelector('[data-mm-compact]');
    var prev = root.querySelector('[data-mm-rail-prev]');
    var next = root.querySelector('[data-mm-rail-next]');
    if (!rail || !prev || !next) return;
    var overflow = rail.scrollWidth - rail.clientWidth > 4;
    var show = overflow && finePointer() && !root.classList.contains('mm-lipton-reels--expanded');
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

  function scrollRail(root, dir) {
    var rail = root.querySelector('[data-mm-compact]');
    if (!rail) return;
    var tile = rail.querySelector('.mm-lipton-reels-tile');
    var step = tile ? tile.getBoundingClientRect().width + GAP : Math.max(120, rail.clientWidth * 0.8);
    rail.scrollBy({ left: dir * step, behavior: 'smooth' });
  }

  function layoutCompactStrip(root, videos) {
    var row = root.querySelector('.mm-lipton-reels-compact');
    var brand = root.querySelector('.mm-lipton-reels-brand');
    var compact = root.querySelector('[data-mm-compact]');
    if (!row || !brand || !compact || root.classList.contains('mm-lipton-reels--expanded')) return;
    var avail = row.clientWidth;
    if (avail <= 0) return;
    var nFit = thumbsThatFit(avail, videos.length);
    if (compact.getAttribute('data-mm-count') !== String(videos.length)) {
      compact.innerHTML = compactTilesHtml(videos);
      compact.setAttribute('data-mm-count', String(videos.length));
    }
    var art = ART_W / ART_H;
    var vid = VID_W / VID_H;
    var border = 4;
    var innerH = (avail - GAP * nFit - border * (1 + nFit)) / (art + nFit * vid);
    if (innerH < 40) innerH = 40;
    var outerH = innerH + border;
    var thumbW = innerH * vid + border;
    brand.style.width = innerH * art + border + 'px';
    brand.style.height = outerH + 'px';
    var wrap = root.querySelector('.mm-lipton-reels-rail-wrap');
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
      var video = ensureHeroVideo(root);
      if (stage && video) stage.appendChild(video);
      var playerUi = stage && stage.querySelector('[data-mm-player-ui]');
      if (stage && playerUi) stage.appendChild(playerUi);
      var overlay = stage && stage.querySelector('.mm-lipton-reels-clip-chrome--overlay');
      if (stage && overlay) stage.appendChild(overlay);
      applyFrozenChrome(root, state.chromeSnap);
      wirePlayer(root, state);
      hidePlayerUi(root, state);
    } else {
      removeExpanded(root);
      layoutCompactStrip(root, picked.videos);
    }
  }

  function init() {
    var root = cardEl();
    if (!root) return;
    var payload = readPayload(root);
    var state = { expanded: false, currentId: '', chromeSnap: null, hideTimer: null, playerWired: false };
    var video = ensureHeroVideo(root);
    var first = sortVideos(payload.videos || [])[0];
    if (first && video) {
      var src = playUrl(first);
      if (first.thumb) video.setAttribute('poster', first.thumb);
      if (src) video.src = src;
    }
    paint(root, payload, state);
    state.chromeSnap = snapshotChromeSize(root);

    root.addEventListener('click', function (ev) {
      var prev = ev.target.closest && ev.target.closest('[data-mm-rail-prev]');
      if (prev) {
        ev.preventDefault();
        ev.stopPropagation();
        scrollRail(root, -1);
        return;
      }
      var next = ev.target.closest && ev.target.closest('[data-mm-rail-next]');
      if (next) {
        ev.preventDefault();
        ev.stopPropagation();
        scrollRail(root, 1);
        return;
      }
      var hide = ev.target.closest && ev.target.closest('[data-mm-hide]');
      if (hide) {
        ev.preventDefault();
        collapse(root, payload, state);
        return;
      }
      var brand = ev.target.closest && ev.target.closest('.mm-lipton-reels-brand');
      if (brand) return;
      var playerUi = ev.target.closest && ev.target.closest('[data-mm-player-ui]');
      if (playerUi && root.contains(playerUi)) {
        ev.preventDefault();
        ev.stopPropagation();
        var video = root.querySelector('[data-mm-hero-video]');
        if (!video) return;
        var playHit = ev.target.closest('[data-mm-toggle-play]');
        var muteHit = ev.target.closest('[data-mm-mute]');
        var seekHit = ev.target.closest('[data-mm-seek]');
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
        state.chromeSnap = snapshotChromeSize(root) || state.chromeSnap;
        state.currentId = thumb.getAttribute('data-mm-vid') || state.currentId;
        state.expanded = true;
        paint(root, payload, state);
        startHeroPlayback(root, currentVideo(payload, state).current);
      }
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

    if (window.ResizeObserver) {
      var ro = new ResizeObserver(function () {
        if (!state.expanded) layoutCompactStrip(root, sortVideos(payload.videos || []));
      });
      ro.observe(root);
    } else {
      window.addEventListener('resize', function () {
        if (!state.expanded) layoutCompactStrip(root, sortVideos(payload.videos || []));
      });
    }
    window.addEventListener('orientationchange', function () {
      if (!state.expanded) {
        window.setTimeout(function () {
          layoutCompactStrip(root, sortVideos(payload.videos || []));
        }, 80);
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
