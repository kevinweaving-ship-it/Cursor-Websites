/**
 * Lipton-only Marine Megastore Event Reels card (#mmLiptonReels).
 * Compact: muted autoplay, labels outside the video frame.
 * Expand: autoplay in place, no automatic fullscreen.
 */
(function () {
  'use strict';

  var ART_W = 320;
  var ART_H = 213;

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

  function vidSize(v) {
    var w = parseInt(v && v.width, 10) || 0;
    var h = parseInt(v && v.height, 10) || 0;
    if (w > 0 && h > 0) return { w: w, h: h };
    return { w: 16, h: 9 };
  }

  function pluginSrc(v, autoplay, mute) {
    var src = (v && v.embed_url) || '';
    if (!src && v && (v.url || v.permalink)) {
      src =
        'https://www.facebook.com/plugins/video.php?href=' +
        encodeURIComponent(v.url || v.permalink) +
        '&show_text=false';
    }
    if (!src) return '';
    src = src
      .replace(/&autoplay=(true|false|1|0)/gi, '')
      .replace(/&mute=\d+/gi, '')
      .replace(/&playsinline=\d+/gi, '');
    if (autoplay) src += '&autoplay=true';
    if (mute) src += '&mute=1';
    src += '&playsinline=1';
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

  function compactPreviewHtml(v) {
    if (!v) return '<p class="mm-lipton-reels-waiting">No clip yet.</p>';
    var size = vidSize(v);
    var src = pluginSrc(v, true, true);
    var stamp = v.stamp || '';
    var label = stamp ? 'Latest Reel · ' + stamp : 'Latest Reel';
    var frame =
      '<div class="mm-lipton-reels-compact-frame" data-mm-w="' +
      size.w +
      '" data-mm-h="' +
      size.h +
      '" style="aspect-ratio:' +
      aspectCss(v) +
      '">' +
      (src
        ? '<iframe src="' +
          esc(src) +
          '" title="Marine Megastore Event Reel" allow="autoplay; muted; encrypted-media" referrerpolicy="strict-origin-when-cross-origin"></iframe>'
        : '') +
      '<button type="button" class="mm-lipton-reels-compact-hit" data-mm-expand data-mm-vid="' +
      esc(v.id || '') +
      '" aria-label="' +
      esc(label) +
      '"></button>' +
      '</div>';
    return (
      '<div class="mm-lipton-reels-compact-preview">' +
      frame +
      metaHtml(label) +
      '</div>'
    );
  }

  function stageHtml(v) {
    if (!v) return '<p class="mm-lipton-reels-waiting">No clip yet.</p>';
    var src = pluginSrc(v, true, false);
    var stamp = v.stamp || '';
    return (
      '<div class="mm-lipton-reels-stage" data-mm-stage style="--mm-aspect:' +
      aspectCss(v) +
      ';aspect-ratio:' +
      aspectCss(v) +
      '">' +
      (src
        ? '<iframe src="' +
          esc(src) +
          '" title="Marine Megastore Event Reel" allow="autoplay; clipboard-write; encrypted-media; picture-in-picture; web-share; fullscreen" allowfullscreen referrerpolicy="strict-origin-when-cross-origin"></iframe>'
        : '') +
      '</div>' +
      metaHtml(stamp)
    );
  }

  function gridHtml(videos, currentId) {
    var rest = (videos || []).filter(function (v) {
      return v && v.id !== currentId;
    });
    if (!rest.length) return '';
    var parts = ['<div class="mm-lipton-reels-grid" role="list">'];
    var i;
    var v;
    for (i = 0; i < rest.length; i++) {
      v = rest[i];
      parts.push(
        '<div class="mm-lipton-reels-grid-item" role="listitem">' +
          '<button type="button" class="mm-lipton-reels-thumb" style="aspect-ratio:' +
          aspectCss(v) +
          '" data-mm-vid="' +
          esc(v.id || '') +
          '" aria-label="' +
          esc(v.stamp || v.title || 'Play reel') +
          '">' +
          (v.thumb
            ? '<img src="' + esc(v.thumb) + '" alt="" loading="lazy" decoding="async">'
            : '<span class="mm-lipton-reels-thumb-ph" aria-hidden="true"></span>') +
          '</button>' +
          metaHtml(v.stamp || '') +
          '</div>'
      );
    }
    parts.push('</div>');
    return parts.join('');
  }

  function layoutCompactPair(root) {
    var row = root.querySelector('.mm-lipton-reels-compact');
    var img = root.querySelector('.mm-lipton-reels-brand img');
    var frame = root.querySelector('.mm-lipton-reels-compact-frame');
    if (!row || !img || !frame || root.classList.contains('mm-lipton-reels--expanded')) return;
    var avail = row.clientWidth;
    if (avail <= 0) return;
    var gap = 8;
    var art = ART_W / ART_H;
    var sizeW = parseInt(frame.getAttribute('data-mm-w'), 10) || 16;
    var sizeH = parseInt(frame.getAttribute('data-mm-h'), 10) || 9;
    var vid = sizeW / sizeH;
    var h = (avail - gap) / (art + vid);
    if (window.matchMedia('(min-width: 600px)').matches) {
      h = Math.min(h, 120);
    }
    if (h < 44) h = 44;
    img.style.width = h * art + 'px';
    img.style.height = h + 'px';
    img.style.maxWidth = 'none';
    img.style.maxHeight = 'none';
    frame.style.width = h * vid + 'px';
    frame.style.height = h + 'px';
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
    if (compact) {
      compact.innerHTML = state.expanded ? '' : compactPreviewHtml(picked.current);
    }
    if (expanded) {
      expanded.innerHTML = state.expanded
        ? stageHtml(picked.current) + gridHtml(picked.videos, picked.current && picked.current.id)
        : '';
    }
    root.classList.toggle('mm-lipton-reels--expanded', !!state.expanded);
    root.classList.toggle('mm-lipton-reels--compact', !state.expanded);
    if (!state.expanded) {
      layoutCompactPair(root);
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
        return;
      }
      var expand = ev.target.closest && ev.target.closest('[data-mm-expand]');
      if (expand && root.contains(expand)) {
        ev.preventDefault();
        state.expanded = true;
        paint(root, payload, state);
      }
    });

    if (window.ResizeObserver) {
      var ro = new ResizeObserver(function () {
        if (!state.expanded) layoutCompactPair(root);
      });
      ro.observe(root);
    } else {
      window.addEventListener('resize', function () {
        if (!state.expanded) layoutCompactPair(root);
      });
    }
    window.addEventListener('orientationchange', function () {
      if (!state.expanded) {
        window.setTimeout(function () {
          layoutCompactPair(root);
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
