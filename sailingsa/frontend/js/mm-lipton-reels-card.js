/**
 * Lipton-only Marine Megastore Event Reels card (#mmLiptonReels).
 * Compact: artwork + FB-source thumbs. Expand: muted autoplay immediately, no forced fullscreen.
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

  function metaHtml(text) {
    if (!text) return '';
    return '<div class="mm-lipton-reels-meta">' + esc(text) + '</div>';
  }

  function stopAllPlayback(root) {
    var iframes = root.querySelectorAll('iframe');
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
    var allow = 'autoplay; muted; encrypted-media; picture-in-picture';
    var fs = '';
    if (fullscreenOk) {
      allow += '; fullscreen';
      fs = ' allowfullscreen';
    }
    return (
      '<iframe src="' +
      esc(src) +
      '" title="Marine Megastore Event Reel" allow="' +
      allow +
      '"' +
      fs +
      ' referrerpolicy="strict-origin-when-cross-origin"></iframe>'
    );
  }

  function thumbHtml(v, autoplay) {
    return (
      '<div class="mm-lipton-reels-thumb" style="aspect-ratio:16 / 9">' +
      fbFrameHtml(v, autoplay, false) +
      '<button type="button" class="mm-lipton-reels-thumb-hit" data-mm-vid="' +
      esc((v && v.id) || '') +
      '" aria-label="' +
      esc((v && v.stamp) || 'Play reel') +
      '"></button>' +
      '</div>'
    );
  }

  function compactTileHtml(v, autoplay) {
    return (
      '<div class="mm-lipton-reels-tile">' +
      thumbHtml(v, autoplay) +
      metaHtml((v && v.stamp) || '') +
      '</div>'
    );
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

  function compactTilesHtml(videos, n) {
    var parts = [];
    var i;
    for (i = 0; i < n; i++) parts.push(compactTileHtml(videos[i], i === 0));
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
      '</div>' +
      metaHtml(v.stamp || '')
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
          thumbHtml(rest[i], false) +
          metaHtml(rest[i].stamp || '') +
          '</div>'
      );
    }
    parts.push('</div>');
    return parts.join('');
  }

  function layoutCompactStrip(root, videos) {
    var row = root.querySelector('.mm-lipton-reels-compact');
    var brand = root.querySelector('.mm-lipton-reels-brand');
    var compact = root.querySelector('[data-mm-compact]');
    if (!row || !brand || !compact || root.classList.contains('mm-lipton-reels--expanded')) return;
    var avail = row.clientWidth;
    if (avail <= 0) return;
    var n = thumbsThatFit(avail, videos.length);
    if (compact.getAttribute('data-mm-n') !== String(n)) {
      compact.innerHTML = compactTilesHtml(videos, n);
      compact.setAttribute('data-mm-n', String(n));
    }
    var art = ART_W / ART_H;
    var vid = VID_W / VID_H;
    var border = 4;
    var innerH = (avail - GAP * n - border * (1 + n)) / (art + n * vid);
    if (innerH < 40) innerH = 40;
    var outerH = innerH + border;
    brand.style.width = innerH * art + border + 'px';
    brand.style.height = outerH + 'px';
    var thumbs = compact.querySelectorAll('.mm-lipton-reels-thumb');
    var i;
    for (i = 0; i < thumbs.length; i++) {
      thumbs[i].style.width = innerH * vid + border + 'px';
      thumbs[i].style.height = outerH + 'px';
    }
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

  function paint(root, payload, state) {
    stopAllPlayback(root);
    var picked = currentVideo(payload, state);
    var compact = root.querySelector('[data-mm-compact]');
    var expanded = root.querySelector('[data-mm-expanded]');
    root.classList.toggle('mm-lipton-reels--expanded', !!state.expanded);
    root.classList.toggle('mm-lipton-reels--compact', !state.expanded);
    if (compact && state.expanded) {
      compact.innerHTML = '';
      compact.removeAttribute('data-mm-n');
    }
    if (expanded) {
      expanded.innerHTML = state.expanded
        ? stageHtml(picked.current) + gridHtml(picked.videos, picked.current && picked.current.id)
        : '';
    }
    if (!state.expanded) {
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
      var hide = ev.target.closest && ev.target.closest('[data-mm-hide]');
      if (hide) {
        ev.preventDefault();
        state.expanded = false;
        stopAllPlayback(root);
        paint(root, payload, state);
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
