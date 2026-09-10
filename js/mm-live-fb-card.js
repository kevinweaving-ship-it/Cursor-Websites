/**
 * Compact / expand MM video card (manual Facebook URLs, no Graph).
 * Compact: branding left + newest or LIVE thumb right. Tap expands. Hide collapses.
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
    return document.getElementById('mmLiveFbCard');
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
      if (!!a.is_live !== !!b.is_live) return a.is_live ? -1 : 1;
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

  function isPortrait(v) {
    var w = parseInt(v && v.width, 10) || 0;
    var h = parseInt(v && v.height, 10) || 0;
    if (w > 0 && h > 0) return h > w;
    return String((v && v.aspect) || '').replace(/\s/g, '') === '9:16';
  }

  function thumbHtml(v, extraClass) {
    var cls = 'mm-live-fb-thumb' + (isPortrait(v) ? ' mm-live-fb-thumb--portrait' : ' mm-live-fb-thumb--landscape');
    if (extraClass) cls += ' ' + extraClass;
    var hero = extraClass && extraClass.indexOf('mm-live-fb-thumb--hero') >= 0;
    var stamp = v && v.stamp ? esc(v.stamp) : '';
    var live = v && v.is_live;
    var img = v && v.thumb
      ? '<img src="' + esc(v.thumb) + '" alt="' + esc((v && v.title) || '') + '" loading="lazy">'
      : '<span class="mm-live-fb-thumb-ph" aria-hidden="true"></span>';
    return (
      '<button type="button" class="' +
      cls +
      '"' +
      (hero ? '' : ' style="aspect-ratio:' + aspectCss(v) + '"') +
      ' data-mm-vid="' +
      esc((v && v.id) || '') +
      '" aria-label="' +
      esc(live ? 'Play LIVE video' : 'Play ' + ((v && v.title) || stamp || 'clip')) +
      '">' +
      img +
      (live ? '<span class="mm-live-fb-live-flag">LIVE</span>' : '') +
      (stamp ? '<span class="mm-live-fb-thumb-stamp">' + stamp + '</span>' : '') +
      '</button>'
    );
  }

  function stageHtml(v) {
    if (!v) {
      return '<p class="mm-live-fb-waiting">No clip yet.</p>';
    }
    var src = v.embed_url || '';
    var href = v.url || v.permalink || '';
    var orient = isPortrait(v) ? ' mm-live-fb-stage--portrait' : ' mm-live-fb-stage--landscape';
    var frame = src
      ? '<iframe src="' +
        esc(src) +
        '" title="' +
        esc(v.title || 'Facebook video') +
        '" allow="autoplay; clipboard-write; encrypted-media; picture-in-picture; web-share" allowfullscreen></iframe>'
      : '';
    var watch = href
      ? '<a class="mm-live-fb-watch" href="' +
        esc(href) +
        '" target="_blank" rel="noopener noreferrer">Watch on Facebook</a>'
      : '';
    return (
      '<div class="mm-live-fb-stage' +
      orient +
      '" data-mm-stage style="--mm-aspect:' +
      aspectCss(v) +
      '">' +
      frame +
      '</div>' +
      watch
    );
  }

  function carouselHtml(videos, currentId) {
    var rest = (videos || []).filter(function (v) {
      return v && v.id !== currentId;
    });
    if (!rest.length) return '';
    var parts = ['<div class="mm-live-fb-carousel" role="list">'];
    var i;
    for (i = 0; i < rest.length; i++) {
      parts.push('<div role="listitem">' + thumbHtml(rest[i], '') + '</div>');
    }
    parts.push('</div>');
    return parts.join('');
  }

  function paint(root, payload, state) {
    var videos = sortVideos(payload.videos || []);
    var live = null;
    var i;
    for (i = 0; i < videos.length; i++) {
      if (videos[i] && videos[i].is_live) {
        live = videos[i];
        break;
      }
    }
    var current = null;
    if (live && !state.currentId) current = live;
    else {
      for (i = 0; i < videos.length; i++) {
        if (videos[i] && videos[i].id === state.currentId) {
          current = videos[i];
          break;
        }
      }
      if (!current) current = live || videos[0] || null;
    }
    if (current) state.currentId = current.id;

    var compact = root.querySelector('[data-mm-compact]');
    var expanded = root.querySelector('[data-mm-expanded]');
    if (compact) {
      compact.innerHTML = current
        ? thumbHtml(current, 'mm-live-fb-thumb--hero')
        : '<p class="mm-live-fb-waiting">No clip yet.</p>';
    }
    if (expanded) {
      expanded.innerHTML =
        stageHtml(current) + carouselHtml(videos, current && current.id);
    }
    root.classList.toggle('mm-live-fb-card--live', !!(current && current.is_live));
    root.classList.toggle('mm-live-fb-card--expanded', !!state.expanded);
    root.classList.toggle('mm-live-fb-card--compact', !state.expanded);
  }

  function stopStage(root) {
    var iframes = root.querySelectorAll('[data-mm-expanded] iframe');
    var i;
    for (i = 0; i < iframes.length; i++) iframes[i].src = '';
  }

  function enterFs(root) {
    var stage = root.querySelector('[data-mm-stage]') || root;
    var req =
      stage.requestFullscreen ||
      stage.webkitRequestFullscreen ||
      stage.msRequestFullscreen;
    if (req) {
      try {
        req.call(stage);
        return;
      } catch (e) {}
    }
    root.classList.add('mm-live-fb-card--fs-fallback');
  }

  function exitFs(root) {
    var exit =
      document.exitFullscreen ||
      document.webkitExitFullscreen ||
      document.msExitFullscreen;
    if (document.fullscreenElement || document.webkitFullscreenElement) {
      try {
        exit.call(document);
      } catch (e) {}
    }
    root.classList.remove('mm-live-fb-card--fs-fallback');
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
        exitFs(root);
        paint(root, payload, state);
        return;
      }
      var fs = ev.target.closest && ev.target.closest('[data-mm-fs]');
      if (fs) {
        ev.preventDefault();
        if (!state.expanded) {
          state.expanded = true;
          paint(root, payload, state);
        }
        enterFs(root);
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
