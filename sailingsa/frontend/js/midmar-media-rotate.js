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
    return !!(
      document.querySelector('.regatta-page--super-admin, .regatta-page--su, #midmar-mm-sa:not([hidden])') ||
      (window.sailingSessionIsSuperAdmin && window.__ssaSession && window.sailingSessionIsSuperAdmin(window.__ssaSession))
    );
  }

  function injectCss() {
    if (document.getElementById(CSS_ID)) return;
    var s = document.createElement('style');
    s.id = CSS_ID;
    s.textContent =
      '.mm-rot-btn{position:absolute;right:6px;bottom:6px;z-index:6;min-width:44px;min-height:44px;' +
      'padding:0 8px;border:1.5px solid #001f3f;border-radius:8px;background:rgba(255,255,255,.92);' +
      'color:#001f3f;font:700 11px/1 Arial,Helvetica,sans-serif;cursor:pointer;}' +
      '.mm-lipton-reels-thumb,.mm-lipton-reels-stage{position:relative;}' +
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

  function applyOne(box, clip) {
    if (!box || !clip || !clip.id) return;
    if (clip.kind === 'webcam' || clip.kind === 'snapshot' || clip.live_cam) return;
    var deg = normRot(clip.rotation != null ? clip.rotation : rotMap[clip.id]);
    rotMap[clip.id] = deg;
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
    document.querySelectorAll('[data-mm-vid]').forEach(function (el) {
      var id = el.getAttribute('data-mm-vid');
      var clip = byId[id] || clipById(id);
      var box = el.classList.contains('mm-lipton-reels-thumb')
        ? el
        : el.querySelector('.mm-lipton-reels-thumb') || el;
      applyOne(box, clip);
    });
    var stage = document.querySelector('[data-mm-stage]');
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
    sa.setAttribute('data-mm-rot-bound', '1');
    var saveBtn = sa.querySelector('[data-mm-sa-save]');
    if (!sa.querySelector('[data-mm-sa-rot]') && saveBtn) {
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'midmar-mm-sa-rot';
      btn.setAttribute('data-mm-sa-rot', '');
      btn.setAttribute('title', 'Rotate 90 degrees');
      btn.textContent = 'Rotate 90°';
      saveBtn.parentNode.insertBefore(btn, saveBtn);
    }
    var rotBtn = sa.querySelector('[data-mm-sa-rot]');
    if (!rotBtn) return;
    rotBtn.addEventListener('click', function (e) {
      e.preventDefault();
      e.stopPropagation();
      var cur = normRot(sa.getAttribute('data-mm-sa-rot') || 0);
      var next = (cur + 90) % 360;
      sa.setAttribute('data-mm-sa-rot', String(next));
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
      window.__mmSaRotation = next;
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
      var obs = new MutationObserver(function () {
        paint();
        bindSaCard();
      });
      obs.observe(host, { childList: true, subtree: true });
    }
    window.setInterval(function () {
      if (!document.hidden) {
        paint();
        bindSaCard();
      }
    }, 4000);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
