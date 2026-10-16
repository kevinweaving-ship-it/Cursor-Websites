/**
 * Fill empty left Event / class logo slots on landing and club cards.
 * Prior-year Event Logo first (Easter Regatta and 9 Hour → HMYC 6&9 Hour),
 * then class logo from the title. Never paints a club burgee in this slot.
 */
(function () {
  'use strict';
  if (window.__SSA_CARD_LEFT_LOGO__) return;
  window.__SSA_CARD_LEFT_LOGO__ = true;

  var EVENT_NEEDLES = [
    ['easter regatta and 9 hour', '/artwork/Event Logo/HMYC-6hr-9hr-Race.png'],
    ['easter regatta and 9', '/artwork/Event Logo/HMYC-6hr-9hr-Race.png'],
    ['9/6 hour', '/artwork/Event Logo/HMYC-6hr-9hr-Race.png'],
    ['6/9 hour', '/artwork/Event Logo/HMYC-6hr-9hr-Race.png'],
    ['6&9 hour', '/artwork/Event Logo/HMYC-6hr-9hr-Race.png'],
    ['6 & 9 hour', '/artwork/Event Logo/HMYC-6hr-9hr-Race.png'],
    ['9 hour endurance', '/artwork/Event Logo/HMYC-6hr-9hr-Race.png'],
    ['6hr 9hr', '/artwork/Event Logo/HMYC-6hr-9hr-Race.png'],
    ['9hr endurance', '/artwork/Event Logo/HMYC-9hr.png'],
    ['hmyc 9hr', '/artwork/Event Logo/HMYC-9hr.png'],
    ['hmyc 9 hr', '/artwork/Event Logo/HMYC-9hr.png'],
    ['tsc 9hr', '/artwork/Event Logo/TSC-9hr.png'],
    ['tsc 9 hr', '/artwork/Event Logo/TSC-9hr.png'],
    ['9 hour', '/artwork/Event Logo/HMYC-6hr-9hr-Race.png'],
    ['grandslam', '/artwork/Event Logo/HMYC-Grand-Slam.png'],
    ['hmyc grand slam', '/artwork/Event Logo/HMYC-Grand-Slam.png'],
    ['kzn grand slam', '/artwork/Event Logo/KZN-Grand-Slam.png'],
    ['sasnr grand slam', '/artwork/Event Logo/KZN-Grand-Slam.png'],
    ['saskzn grand slam', '/artwork/Event Logo/KZN-Grand-Slam.png'],
    ['grand slam', '/artwork/Event Logo/KZN-Grand-Slam.png'],
    ['ussa', '/artwork/Event Logo/TSL-Team-Sailing.png'],
    ['team sailing league', '/artwork/Event Logo/TSL-Team-Sailing.png'],
    ['team sailing', '/artwork/Event Logo/TSL-Team-Sailing.png'],
    ['intervarsity', '/artwork/Event Logo/TSL-Team-Sailing.png'],
    ['inter varsity', '/artwork/Event Logo/TSL-Team-Sailing.png']
  ];

  var CLASS_NEEDLES = [
    ['hunter', '/artwork/Class Logo/Hunter-19-Class-Logo.png'],
    ['dart 18', '/artwork/Class Logo/Dart-18-Class-Logo.png'],
    ['flying 15', '/artwork/Class Logo/Flying-Fifteen-Class-Logo.png'],
    ['flying fifteen', '/artwork/Class Logo/Flying-Fifteen-Class-Logo.png'],
    ['soling', '/artwork/Class Logo/Soling-Class-Logo.png'],
    ['dabchick', '/artwork/Class Logo/Dabchick-Class-Logo.png'],
    ['optimist', '/artwork/Class Logo/Optimist-Class-Logo.png'],
    ['ilca', '/artwork/Class Logo/ILCA-Class-Logo.png'],
    ['505', '/artwork/Class Logo/505-Class-Logo.png']
  ];

  function hayOf(card) {
    var titleEl = card.querySelector('.sa-home-regatta-title');
    var title = titleEl ? String(titleEl.textContent || '') : '';
    var search = String(card.getAttribute('data-search') || '');
    var raw = (title + ' ' + search).toLowerCase().replace(/\s+/g, ' ').trim();
    var flex = raw.replace(/[-/&]/g, ' ').replace(/\s+/g, ' ').trim();
    return [raw, flex];
  }

  function best(hay, flex, rules) {
    var src = '';
    var nlen = -1;
    for (var i = 0; i < rules.length; i++) {
      var needle = rules[i][0];
      if ((hay.indexOf(needle) !== -1 || flex.indexOf(needle) !== -1) && needle.length > nlen) {
        src = rules[i][1];
        nlen = needle.length;
      }
    }
    return src;
  }

  function resolve(card) {
    var parts = hayOf(card);
    return best(parts[0], parts[1], EVENT_NEEDLES) || best(parts[0], parts[1], CLASS_NEEDLES);
  }

  function slotEmpty(link) {
    if (!link) return true;
    var img = link.querySelector('img.sa-home-regatta-event-logo, img');
    if (!img) return true;
    var src = String(img.getAttribute('src') || '').trim();
    if (!src) return true;
    if (img.style && img.style.display === 'none') return true;
    return false;
  }

  function paint(link, src) {
    if (!link || !src) return;
    var img = link.querySelector('img.sa-home-regatta-event-logo');
    if (!img) {
      img = document.createElement('img');
      img.className = 'sa-home-regatta-event-logo';
      img.alt = '';
      img.loading = 'lazy';
      img.decoding = 'async';
      link.appendChild(img);
    }
    img.onerror = function () {
      img.style.display = 'none';
    };
    img.src = src;
    img.style.display = '';
  }

  function fill(root) {
    var scope = root && root.querySelectorAll ? root : document;
    var cards = scope.querySelectorAll('.sa-home-regatta-card');
    for (var i = 0; i < cards.length; i++) {
      var card = cards[i];
      var link = card.querySelector('.sa-home-regatta-event-logo-link');
      if (!slotEmpty(link)) continue;
      var src = resolve(card);
      if (src) paint(link, src);
    }
  }

  function boot() {
    fill(document);
    if (typeof MutationObserver === 'undefined') return;
    var obs = new MutationObserver(function (muts) {
      for (var i = 0; i < muts.length; i++) {
        if (muts[i].addedNodes && muts[i].addedNodes.length) {
          fill(document);
          return;
        }
      }
    });
    obs.observe(document.body || document.documentElement, { childList: true, subtree: true });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }

  window.ssaFillCardLeftLogos = fill;
})();
