/**
 * Lipton-only Marine Megastore Event Reels card (#mmLiptonReels).
 * Compact: fixed artwork + swipeable FB clip rail. Expand: muted autoplay, Hide only while open.
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

  function pluginSrc(v, autoplay) {
    var href = (v && (v.url || v.permalink)) || '';
    var src = (v && v.embed_url) || '';
    if (!src && href) {
      src =
        'https://www.facebook.com/plugins/video.php?href=' +
        encodeURIComponent(href) +
        '&show_text=false';
    }
    if (!src) return '';
    src = src
      .replace(/&autoplay=(true|false|1|0)/gi, '')
      .replace(/&mute=\d+/gi, '')
      .replace(/&muted=\d+/gi, '')
      .replace(/&playsinline=\d+/gi, '');
    if (autoplay) src += '&autoplay=true';
    src += '&mute=1&muted=1&playsinline=1';
    if (autoplay) src += '&_mm=' + Date.now();
    return src;
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

  function stopAllPlayback(root) {
    exitFsIfInside(root);
    var iframes = root.querySelectorAll('[data-mm-expanded] iframe');
    var i;
    for (i = 0; i < iframes.length; i++) {
      iframes[i].src = 'about:blank';
      iframes[i].removeAttribute('src');
    }
  }

  function fbFrameHtml(v, autoplay, fullscreenOk) {
    var src = pluginSrc(v, autoplay);
    if (!src) {
      return v && v.thumb
        ? '<img src="' + esc(v.thumb) + '" alt="" loading="lazy" decoding="async">'
        : '<span class="mm-lipton-reels-thumb-ph" aria-hidden="true"></span>';
    }
    var allow = 'autoplay; muted; encrypted-media; picture-in-picture; fullscreen';
    var fs = fullscreenOk ? ' allowfullscreen webkitallowfullscreen' : '';
    return (
      '<iframe src="' +
      esc(src) +
      '" title="Marine Megastore Event Reel" allow="' +
      allow +
      '"' +
      fs +
      ' referrerpolicy="strict-origin-when-cross-origin" playsinline></iframe>'
    );
  }

  function thumbHtml(v) {
    return (
      '<div class="mm-lipton-reels-thumb" style="aspect-ratio:16 / 9">' +
      fbFrameHtml(v, false, false) +
      '<button type="button" class="mm-lipton-reels-thumb-hit" data-mm-vid="' +
      esc((v && v.id) || '') +
      '" aria-label="' +
      esc((v && v.title) || (v && v.stamp) || 'Play reel') +
      '"></button>' +
      '</div>'
    );
  }

  function compactTileHtml(v) {
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
    for (i = 0; i < videos.length; i++) parts.push(compactTileHtml(videos[i]));
    return parts.join('');
  }

  function stageHtml(v) {
    if (!v) return '<p class="mm-lipton-reels-waiting">No clip yet.</p>';
    return (
      '<div class="mm-lipton-reels-stage" data-mm-stage style="--mm-aspect:' +
      aspectCss(v) +
      ';aspect-ratio:' +
      aspectCss(v) +
      '">' +
      fbFrameHtml(v, true, true) +
      '</div>'
    );
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
      stageHtml(v) +
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
    var el = root.querySelector('[data-mm-expanded]');
    if (!el) return;
    var iframes = el.querySelectorAll('iframe');
    var i;
    for (i = 0; i < iframes.length; i++) {
      iframes[i].src = 'about:blank';
      iframes[i].removeAttribute('src');
    }
    el.parentNode.removeChild(el);
  }

  function collapse(root, payload, state) {
    state.expanded = false;
    stopAllPlayback(root);
    removeExpanded(root);
    root.classList.remove('mm-lipton-reels--expanded');
    root.classList.add('mm-lipton-reels--compact');
    layoutCompactStrip(root, sortVideos(payload.videos || []));
  }

  function paint(root, payload, state) {
    var picked = currentVideo(payload, state);
    root.classList.toggle('mm-lipton-reels--expanded', !!state.expanded);
    root.classList.toggle('mm-lipton-reels--compact', !state.expanded);
    if (state.expanded) {
      stopAllPlayback(root);
      var expanded = ensureExpanded(root);
      expanded.innerHTML = expandedHtml(picked.current, picked.videos);
    } else {
      removeExpanded(root);
      layoutCompactStrip(root, picked.videos);
    }
  }

  function init() {
    var root = cardEl();
    if (!root) return;
    var payload = readPayload(root);
    var state = { expanded: false, currentId: '' };
    paint(root, payload, state);

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
      var thumb = ev.target.closest && ev.target.closest('[data-mm-vid]');
      if (thumb && root.contains(thumb)) {
        ev.preventDefault();
        state.currentId = thumb.getAttribute('data-mm-vid') || state.currentId;
        state.expanded = true;
        paint(root, payload, state);
      }
    });

    var rail = root.querySelector('[data-mm-compact]');
    if (rail) {
      rail.addEventListener('scroll', function () {
        syncRailButtons(root);
      }, { passive: true });
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
