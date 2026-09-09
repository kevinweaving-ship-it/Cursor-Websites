/**
 * Lipton-only Marine Megastore Event Reels card.
 * Bound to #mmLiptonReels on 2026-08-29-lipton-challenge-cup. No Fullscreen.
 */
(function () {
  'use strict';

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

  function thumbHtml(v, extraClass) {
    var cls = 'mm-lipton-reels-thumb';
    if (extraClass) cls += ' ' + extraClass;
    var stamp = v && v.stamp ? esc(v.stamp) : '';
    var img = v && v.thumb
      ? '<img src="' + esc(v.thumb) + '" alt="' + esc((v && v.title) || '') + '" loading="lazy" decoding="async">'
      : '<span class="mm-lipton-reels-thumb-ph" aria-hidden="true"></span>';
    return (
      '<button type="button" class="' +
      cls +
      '" style="aspect-ratio:' +
      aspectCss(v) +
      '" data-mm-vid="' +
      esc((v && v.id) || '') +
      '" aria-label="' +
      esc('Play ' + ((v && v.title) || stamp || 'reel')) +
      '">' +
      img +
      (stamp ? '<span class="mm-lipton-reels-stamp">' + stamp + '</span>' : '') +
      '</button>'
    );
  }

  function stageHtml(v) {
    if (!v) {
      return '<p class="mm-lipton-reels-waiting">No clip yet.</p>';
    }
    var src = v.embed_url || '';
    var href = v.url || v.permalink || '';
    var frame = src
      ? '<iframe src="' +
        esc(src) +
        '" title="' +
        esc(v.title || 'Facebook video') +
        '" allow="autoplay; clipboard-write; encrypted-media; picture-in-picture; web-share" allowfullscreen></iframe>'
      : '';
    var watch = href
      ? '<a class="mm-lipton-reels-watch" href="' +
        esc(href) +
        '" target="_blank" rel="noopener noreferrer">Watch on Facebook</a>'
      : '';
    return (
      '<div class="mm-lipton-reels-stage" data-mm-stage style="--mm-aspect:' +
      aspectCss(v) +
      ';aspect-ratio:' +
      aspectCss(v) +
      '">' +
      frame +
      '</div>' +
      watch
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
      parts.push('<div role="listitem">' + thumbHtml(rest[i], '') + '</div>');
    }
    parts.push('</div>');
    return parts.join('');
  }

  function paint(root, payload, state) {
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

    var compact = root.querySelector('[data-mm-compact]');
    var expanded = root.querySelector('[data-mm-expanded]');
    if (compact) {
      compact.innerHTML = current
        ? '<div class="mm-lipton-reels-compact-preview">' +
          thumbHtml(current, 'mm-lipton-reels-thumb--hero') +
          '</div>'
        : '<p class="mm-lipton-reels-waiting">No clip yet.</p>';
    }
    if (expanded) {
      expanded.innerHTML = stageHtml(current) + gridHtml(videos, current && current.id);
    }
    root.classList.toggle('mm-lipton-reels--expanded', !!state.expanded);
    root.classList.toggle('mm-lipton-reels--compact', !state.expanded);
  }

  function stopStage(root) {
    var iframes = root.querySelectorAll('[data-mm-expanded] iframe');
    var i;
    for (i = 0; i < iframes.length; i++) iframes[i].src = '';
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
        stopStage(root);
        paint(root, payload, state);
        return;
      }
      var thumb = ev.target.closest && ev.target.closest('[data-mm-vid]');
      if (thumb && root.contains(thumb)) {
        ev.preventDefault();
        state.currentId = thumb.getAttribute('data-mm-vid') || '';
        state.expanded = true;
        paint(root, payload, state);
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
