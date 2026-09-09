/**
 * Marine Megastore Live FB card on standalone /regatta/{id}.
 * Polls /api/regatta/{id}/mm-live-fb: LIVE is the primary stage; prior same-event clips stay as thumbs.
 */
(function () {
  'use strict';

  var POLL_MS = 20000;

  function cardEl() {
    return document.getElementById('mmLiveFbCard');
  }

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function stageHtml(primary) {
    if (primary && primary.embed_url) {
      var live = !!primary.is_live;
      var badge = live
        ? '<span class="mm-live-fb-badge mm-live-fb-badge--live">LIVE</span>'
        : '<span class="mm-live-fb-badge">REPLAY</span>';
      var stamp = primary.stamp ? '<span class="mm-live-fb-stage-stamp">' + esc(primary.stamp) + '</span>' : '';
      return (
        '<div class="mm-live-fb-stage-frame">' +
        badge +
        stamp +
        '<iframe src="' +
        esc(primary.embed_url) +
        '" title="' +
        esc(primary.title || 'Marine Megastore video') +
        '" allow="autoplay; clipboard-write; encrypted-media; picture-in-picture; web-share" allowfullscreen loading="lazy"></iframe></div>'
      );
    }
    return (
      '<div class="mm-live-fb-waiting">' +
      '<p class="mm-live-fb-waiting-kicker">Waiting for Facebook Live</p>' +
      '<p>When Marine Megastore goes live, that stream becomes the primary video here. Earlier same-event clips stay below as replays.</p>' +
      '<a class="mm-live-fb-waiting-link" href="https://www.facebook.com/marin.megastoresa" target="_blank" rel="noopener noreferrer">Open Marine Megastore on Facebook</a>' +
      '</div>'
    );
  }

  function thumbsHtml(replays) {
    if (!replays || !replays.length) return '';
    var parts = ['<h3 class="mm-live-fb-replays-title">Earlier videos</h3><div class="mm-live-fb-replays-row">'];
    var i;
    for (i = 0; i < replays.length; i++) {
      var v = replays[i] || {};
      var href = v.url || '#';
      var stamp = v.stamp || '';
      var title = v.title || 'Replay';
      var thumb = v.thumb
        ? '<img src="' + esc(v.thumb) + '" alt="" width="160" height="90" loading="lazy">'
        : '<span class="mm-live-fb-thumb-ph" aria-hidden="true"></span>';
      parts.push(
        '<a class="mm-live-fb-thumb" href="' +
          esc(href) +
          '" target="_blank" rel="noopener noreferrer">' +
          thumb +
          '<span class="mm-live-fb-thumb-stamp">' +
          esc(stamp || title) +
          '</span></a>'
      );
    }
    parts.push('</div>');
    return parts.join('');
  }

  function paint(payload) {
    var root = cardEl();
    if (!root || !payload) return;
    if (payload.enabled === false) {
      root.hidden = true;
      return;
    }
    root.hidden = false;
    var stage = root.querySelector('[data-mm-stage]');
    var replaysEl = root.querySelector('[data-mm-replays]');
    if (stage) stage.innerHTML = stageHtml(payload.live || null);
    if (replaysEl) replaysEl.innerHTML = thumbsHtml(payload.replays || []);
    root.classList.toggle('mm-live-fb-card--live', !!(payload.live && payload.live.is_live));
  }

  function load(rid) {
    return fetch('/api/regatta/' + encodeURIComponent(rid) + '/mm-live-fb', {
      credentials: 'same-origin',
      cache: 'no-store'
    })
      .then(function (r) {
        return r.ok ? r.json() : null;
      })
      .then(function (j) {
        if (j) paint(j);
      })
      .catch(function () {});
  }

  function init() {
    var root = cardEl();
    if (!root) return;
    var rid = (root.getAttribute('data-regatta-id') || '').trim();
    if (!rid) return;
    var raw = root.getAttribute('data-mm-initial');
    if (raw) {
      try {
        paint(JSON.parse(raw));
      } catch (e) {}
    }
    load(rid);
    setInterval(function () {
      load(rid);
    }, POLL_MS);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
