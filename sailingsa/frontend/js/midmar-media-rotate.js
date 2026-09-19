/**
 * Midmar media — 90° rotate toggle per video/photo.
 * Click rotates 90°. Last angle is saved on the clip (super admin).
 * Portrait clips can be shown landscape by rotating once.
 */
(function () {
  'use strict';
  if (window.__SSA_MIDMAR_MEDIA_ROTATE__) return;
  window.__SSA_MIDMAR_MEDIA_ROTATE__ = true;

  var RID = '2026-09-19-hmyc-midmar-cup';
  var CSS_ID = 'midmar-media-rotate-css';
  var rotMap = {};

  function onMidmar() {
    var path = String((window.location && window.location.pathname) || '')
      .replace(/\/+$/, '')
      .toLowerCase();
    return path === '/regatta/' + RID || path.indexOf('/regatta/' + RID + '/') === 0;
  }

  function normRot(v) {
    var n = parseInt(v, 10);
    if (isNaN(n)) n = 0;
    n = ((n % 360) + 360) % 360;
    n = Math.round(n / 90) * 90;
    if (n === 360) n = 0;
    return n === 90 || n === 180 || n === 270 ? n : 0;
  }

  function isAdmin() {
    return !!document.querySelector('.regatta-page--super-admin-edit');
  }

  function rotBox(el) {
    if (!el || (el.closest && el.closest('#midmar-mm-sa'))) return null;
    if (el.classList && el.classList.contains('mm-lipton-reels-thumb-hit')) {
      el = el.parentNode;
    }
    if (el.classList && (el.classList.contains('mm-lipton-reels-thumb') || el.classList.contains('mm-lipton-reels-stage'))) {
      return el;
    }
    return (el.querySelector && (el.querySelector('.mm-lipton-reels-thumb') || el.querySelector('.mm-lipton-reels-stage'))) || null;
  }

  function injectCss() {
    if (document.getElementById(CSS_ID)) return;
    var s = document.createElement('style');
    s.id = CSS_ID;
    s.textContent =
      '.mm-rot-btn{position:absolute;right:6px;bottom:6px;z-index:6;min-width:44px;min-height:44px;' +
      'padding:0 8px;border:1.5px solid #001f3f;border-radius:8px;background:rgba(255,255,255,.92);' +
      'color:#001f3f;font:700 11px/1 Arial,Helvetica,sans-serif;cursor:pointer;}' +
      '.regatta-page:not(.regatta-page--super-admin-edit) .mm-rot-btn{display:none!important;}' +
      '.mm-rot-media{transform-origin:center center;}' +
      '.midmar-mm-sa-rot{display:inline-flex;align-items:center;justify-content:center;' +
      'min-height:44px;min-width:44px;margin:8px 8px 0 0;padding:0 12px;border:1.5px solid #001f3f;' +
      'border-radius:8px;background:#fff;color:#001f3f;font:700 12px/1 Arial,Helvetica,sans-serif;cursor:pointer;}' +
      '.midmar-mm-sa-drop-visual img.mm-sa-rotating,.midmar-mm-sa-drop-visual video.mm-sa-rotating{' +
      'transform-origin:center center;}';
    document.head.appendChild(s);
  }

  function fitRotated(box, media, deg) {
    if (!box || !media) return;
    box.style.position = 'relative';
    box.style.overflow = 'hidden';
    if (!deg) {
      media.classList.remove('mm-rot-media');
      media.style.position = '';
      media.style.left = '';
      media.style.top = '';
      media.style.margin = '';
      media.style.maxWidth = '';
      media.style.maxHeight = '';
      media.style.width = '';
      media.style.height = '';
      media.style.transform = '';
      media.style.objectFit = '';
      return;
    }
    var bw = box.clientWidth || 0;
    var bh = box.clientHeight || 0;
    if (bw < 8 || bh < 8) return;
    media.classList.add('mm-rot-media');
    media.style.position = 'absolute';
    media.style.left = '50%';
    media.style.top = '50%';
    media.style.margin = '0';
    media.style.maxWidth = 'none';
    media.style.maxHeight = 'none';
    media.style.objectFit = 'cover';
    if (deg === 90 || deg === 270) {
      media.style.width = bh + 'px';
      media.style.height = bw + 'px';
    } else {
      media.style.width = bw + 'px';
      media.style.height = bh + 'px';
    }
    media.style.transform = 'translate(-50%,-50%) rotate(' + deg + 'deg)';
  }

  function swapAspect(box, clip, deg) {
    if (!box || !clip) return;
    var w = parseInt(clip.width, 10) || 0;
    var h = parseInt(clip.height, 10) || 0;
    if (w < 1 || h < 1) {
      var a = String(clip.aspect || '');
      var m = a.match(/(\d+)\s*[/\:]\s*(\d+)/);
      if (m) {
        w = parseInt(m[1], 10);
        h = parseInt(m[2], 10);
      }
    }
    if (w < 1 || h < 1) {
      w = 16;
      h = 9;
    }
    if (deg === 90 || deg === 270) {
      var t = w;
      w = h;
      h = t;
    }
    box.style.aspectRatio = w + ' / ' + h;
    box.setAttribute('data-mm-rot', String(deg));
  }

  function ensureBtn(box, id) {
    if (!isAdmin() || !id) return;
    var btn = box.querySelector('[data-mm-rot-btn]');
    if (!btn) {
      btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'mm-rot-btn';
      btn.setAttribute('data-mm-rot-btn', id);
      btn.setAttribute('title', 'Rotate 90 degrees');
      btn.textContent = '90°';
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        cycle(id);
      });
      box.appendChild(btn);
    }
    btn.textContent = (rotMap[id] || 0) + '°';
  }

  function revertBox(box) {
    if (!box) return;
    box.style.aspectRatio = '';
    box.style.position = '';
    box.style.overflow = '';
    box.removeAttribute('data-mm-rot');
    var media = box.querySelector('img, video');
    if (!media) return;
    media.classList.remove('mm-rot-media');
    media.style.position = '';
    media.style.left = '';
    media.style.top = '';
    media.style.margin = '';
    media.style.maxWidth = '';
    media.style.maxHeight = '';
    media.style.width = '';
    media.style.height = '';
    media.style.objectFit = '';
    var deg = normRot(rotMap[box.getAttribute('data-mm-vid')] || media.getAttribute('data-mm-rot') || 0);
    media.style.transform = deg ? 'rotate(' + deg + 'deg)' : '';
  }

  function applyOne(box, clip) {
    if (!box || !clip || !clip.id) return;
    if (clip.kind === 'webcam' || clip.kind === 'snapshot' || clip.live_cam) return;
    var deg = normRot(clip.rotation != null ? clip.rotation : rotMap[clip.id]);
    rotMap[clip.id] = deg;
    if (!isAdmin()) {
      revertBox(box);
      var media = box.querySelector('img, video');
      if (media && deg) media.style.transform = 'rotate(' + deg + 'deg)';
      return;
    }
    swapAspect(box, clip, deg);
    var media = box.querySelector('img, video');
    if (media) fitRotated(box, media, deg);
    ensureBtn(box, clip.id);
  }

  function clipsFromDom() {
    var host = document.getElementById('mmLiptonReels');
    if (!host) return [];
    try {
      var raw = host.getAttribute('data-mm-initial');
      var data = raw ? JSON.parse(raw) : null;
      return (data && data.videos) || [];
    } catch (e) {
      return [];
    }
  }

  function clipById(id) {
    var list = clipsFromDom();
    var i;
    for (i = 0; i < list.length; i++) {
      if (String(list[i].id) === String(id)) return list[i];
    }
    return { id: id, rotation: rotMap[id] || 0, width: 16, height: 9 };
  }

  function paint(videos) {
    if (videos && videos.length) {
      videos.forEach(function (v) {
        if (v && v.id) rotMap[v.id] = normRot(v.rotation);
      });
    }
    var list = videos && videos.length ? videos : clipsFromDom();
    var byId = {};
    list.forEach(function (v) {
      if (v && v.id) byId[String(v.id)] = v;
    });
    document.querySelectorAll('.mm-lipton-reels-thumb-hit').forEach(function (hit) {
      hit.style.aspectRatio = '';
      hit.removeAttribute('data-mm-rot');
      var stray = hit.querySelector('[data-mm-rot-btn]');
      if (stray && stray.parentNode) stray.parentNode.removeChild(stray);
    });
    document.querySelectorAll('[data-mm-vid]').forEach(function (el) {
      var id = el.getAttribute('data-mm-vid');
      var clip = byId[id] || clipById(id);
      var box = rotBox(el);
      if (box) applyOne(box, clip);
    });
    var stage = document.querySelector('#mmLiptonReels [data-mm-stage], .mm-lipton-reels-stage[data-mm-stage]');
    if (stage) {
      var playing = document.querySelector('.mm-lipton-reels-tile--on[data-mm-vid], [data-mm-current]');
      var pid = playing ? playing.getAttribute('data-mm-vid') : '';
      if (!pid) {
        var img = stage.querySelector('[data-mm-photo], video, img');
        var src = img && (img.currentSrc || img.src);
        list.forEach(function (v) {
          if (src && v.play_url && src.indexOf(String(v.play_url).split('?')[0]) !== -1) pid = v.id;
        });
      }
      if (pid) applyOne(stage, byId[pid] || clipById(pid));
    }
  }

  function save(id, deg) {
    return fetch('/api/super-admin/regatta/' + encodeURIComponent(RID) + '/mm-clips/' + encodeURIComponent(id), {
      method: 'PATCH',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rotation: deg }),
    }).then(function (r) {
      return r.ok;
    }).catch(function () {
      return false;
    });
  }

  function cycle(id) {
    var next = (normRot(rotMap[id] || 0) + 90) % 360;
    rotMap[id] = next;
    var host = document.getElementById('mmLiptonReels');
    if (host) {
      try {
        var data = JSON.parse(host.getAttribute('data-mm-initial') || '{}');
        (data.videos || []).forEach(function (v) {
          if (v && String(v.id) === String(id)) v.rotation = next;
        });
        host.setAttribute('data-mm-initial', JSON.stringify(data));
      } catch (e) {}
    }
    paint();
    save(id, next);
  }

  function bindSaCard() {
    var sa = document.getElementById('midmar-mm-sa');
    if (!sa || sa.getAttribute('data-mm-rot-bound') === '1') return;
    var rotBtn = sa.querySelector('[data-mm-sa-rot]');
    if (!rotBtn) return;
    sa.setAttribute('data-mm-rot-bound', '1');
    rotBtn.addEventListener('click', function (e) {
      e.preventDefault();
      e.stopPropagation();
      var cur = normRot(sa.getAttribute('data-mm-sa-rot') || window.__mmSaRotation || 0);
      var next = (cur + 90) % 360;
      sa.setAttribute('data-mm-sa-rot', String(next));
      window.__mmSaRotation = next;
      rotBtn.textContent = 'Rotate ' + next + '°';
      var drop = sa.querySelector('[data-mm-sa-drop], .midmar-mm-sa-drop');
      var media = sa.querySelector('.midmar-mm-sa-drop-visual img, .midmar-mm-sa-drop-visual video');
      if (media) {
        media.classList.add('mm-sa-rotating');
        media.style.transform = 'rotate(' + next + 'deg)';
      }
      if (drop) {
        var orient = drop.getAttribute('data-mm-sa-orient') || '';
        if (next === 90 || next === 270) {
          drop.setAttribute('data-mm-sa-orient', orient === 'portrait' ? 'landscape' : 'portrait');
        }
      }
    });
  }

  window.mmApplyClipRotations = function (videos) {
    injectCss();
    if (videos && videos.length) {
      videos.forEach(function (v) {
        if (v && v.id) rotMap[v.id] = normRot(v.rotation);
      });
    }
    paint(videos);
  };

  function boot() {
    if (!onMidmar()) return;
    injectCss();
    bindSaCard();
    fetch('/api/regatta/' + encodeURIComponent(RID) + '/mm-clips', {
      credentials: 'same-origin',
      cache: 'no-store',
    })
      .then(function (r) {
        return r && r.ok ? r.json() : null;
      })
      .then(function (data) {
        paint((data && data.videos) || []);
      })
      .catch(function () {
        paint();
      });
    var host = document.getElementById('mmLiptonReels');
    if (host && host.getAttribute('data-mm-rot-obs') !== '1') {
      host.setAttribute('data-mm-rot-obs', '1');
      var t = 0;
      var obs = new MutationObserver(function () {
        window.clearTimeout(t);
        t = window.setTimeout(function () {
          paint();
          bindSaCard();
        }, 80);
      });
      obs.observe(host, { childList: true, subtree: true });
    }
    var page = document.querySelector('.regatta-page');
    if (page && page.getAttribute('data-mm-rot-tog') !== '1') {
      page.setAttribute('data-mm-rot-tog', '1');
      new MutationObserver(function () {
        paint();
        if (!isAdmin()) {
          document.querySelectorAll('[data-mm-rot-btn]').forEach(function (b) {
            if (b.parentNode) b.parentNode.removeChild(b);
          });
        }
      }).observe(page, { attributes: true, attributeFilter: ['class'] });
    }
    var tog = document.getElementById('regattaSaEditToggle');
    if (tog && tog.getAttribute('data-mm-rot-tog') !== '1') {
      tog.setAttribute('data-mm-rot-tog', '1');
      tog.addEventListener('change', function () {
        paint();
        if (!tog.checked) {
          document.querySelectorAll('[data-mm-rot-btn]').forEach(function (b) {
            if (b.parentNode) b.parentNode.removeChild(b);
          });
        }
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
