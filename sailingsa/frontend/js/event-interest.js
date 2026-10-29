/**
 * Event Interest UI for Upcoming Event landing cards (Stage 3).
 *
 * Mounts on articles.landing-event-card[data-event-id].
 * Uses Stage 2 API contract. Never invents counts or classes.
 *
 * Layout: compact title-row cluster — logos (14px) + counts, total, + Interested.
 * On narrow cards the button (and total when possible) win over logos.
 */
(function (global) {
  "use strict";

  var API_BASE = "";
  var LOGO_SIZE = 14;
  var BTN_MIN = 104;
  var SELECTED = null; // { eventId, classIdentifier }

  function qs(root, sel) {
    return (root || document).querySelector(sel);
  }

  function qsa(root, sel) {
    return Array.prototype.slice.call((root || document).querySelectorAll(sel));
  }

  function glyphRight(el) {
    var r = document.createRange();
    r.selectNodeContents(el);
    var rects = r.getClientRects();
    var right = 0;
    for (var i = 0; i < rects.length; i++) right = Math.max(right, rects[i].right);
    if (!right) right = el.getBoundingClientRect().right;
    return right;
  }

  function apiUrl(path) {
    return (API_BASE || "") + path;
  }

  function fetchJson(path, opts) {
    opts = opts || {};
    return fetch(apiUrl(path), {
      method: opts.method || "GET",
      credentials: "same-origin",
      headers: opts.body
        ? { "Content-Type": "application/json", Accept: "application/json" }
        : { Accept: "application/json" },
      body: opts.body ? JSON.stringify(opts.body) : undefined,
    }).then(function (res) {
      return res.json().then(function (data) {
        if (!res.ok) {
          var err = new Error((data && data.detail) || res.statusText || "Request failed");
          err.status = res.status;
          err.data = data;
          throw err;
        }
        return data;
      });
    });
  }

  function stop(ev) {
    if (!ev) return;
    ev.preventDefault();
    ev.stopPropagation();
    if (ev.stopImmediatePropagation) ev.stopImmediatePropagation();
  }

  function ensureScrim() {
    var scrim = qs(document, "#eci-scrim");
    if (scrim) return scrim;
    scrim = document.createElement("div");
    scrim.id = "eci-scrim";
    scrim.className = "eci-scrim";
    scrim.setAttribute("aria-hidden", "true");
    scrim.innerHTML =
      '<div class="eci-popup" role="dialog" aria-modal="true" aria-labelledby="eci-popup-title">' +
      '<h3 class="eci-popup-title" id="eci-popup-title">Which class are you interested in?</h3>' +
      '<p class="eci-popup-sub" id="eci-popup-sub"></p>' +
      '<div class="eci-popup-grid" id="eci-popup-grid"></div>' +
      '<p class="eci-popup-empty" id="eci-popup-empty" hidden></p>' +
      '<p class="eci-popup-error" id="eci-popup-error" hidden></p>' +
      '<div class="eci-popup-actions">' +
      '<button type="button" class="eci-popup-withdraw" id="eci-popup-withdraw" hidden>Withdraw</button>' +
      '<button type="button" class="eci-popup-close" id="eci-popup-close">Close</button>' +
      '<button type="button" class="eci-popup-confirm" id="eci-popup-confirm" disabled>Confirm</button>' +
      "</div></div>";
    document.body.appendChild(scrim);
    scrim.addEventListener("click", function (e) {
      if (e.target === scrim) closePopup();
    });
    qs(scrim, "#eci-popup-close").addEventListener("click", function (e) {
      stop(e);
      closePopup();
    });
    qs(scrim, "#eci-popup-confirm").addEventListener("click", function (e) {
      stop(e);
      confirmSelection();
    });
    qs(scrim, "#eci-popup-withdraw").addEventListener("click", function (e) {
      stop(e);
      withdrawSelection();
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && scrim.classList.contains("is-open")) closePopup();
    });
    return scrim;
  }

  function closePopup() {
    var scrim = ensureScrim();
    scrim.classList.remove("is-open");
    scrim.setAttribute("aria-hidden", "true");
    SELECTED = null;
  }

  function setPopupError(msg) {
    var el = qs(document, "#eci-popup-error");
    if (!el) return;
    if (msg) {
      el.hidden = false;
      el.textContent = msg;
    } else {
      el.hidden = true;
      el.textContent = "";
    }
  }

  function openPopup(card, snap) {
    var eventId = card.getAttribute("data-event-id");
    var title =
      (qs(card, ".sa-home-regatta-title") || {}).textContent ||
      card.getAttribute("aria-label") ||
      "this event";
    title = String(title).replace(/\s+/g, " ").trim();

    var scrim = ensureScrim();
    qs(scrim, "#eci-popup-sub").textContent = title;
    qs(scrim, "#eci-popup-grid").innerHTML = "";
    qs(scrim, "#eci-popup-empty").hidden = true;
    setPopupError("");
    SELECTED = {
      eventId: eventId,
      classIdentifier: snap && snap.mine && snap.mine.interested ? snap.mine.class_identifier : null,
      card: card,
    };

    var withdrawBtn = qs(scrim, "#eci-popup-withdraw");
    withdrawBtn.hidden = !(snap && snap.mine && snap.mine.interested);
    var confirmBtn = qs(scrim, "#eci-popup-confirm");
    confirmBtn.disabled = !SELECTED.classIdentifier;
    confirmBtn.textContent = snap && snap.mine && snap.mine.interested ? "Update" : "Confirm";

    scrim.classList.add("is-open");
    scrim.setAttribute("aria-hidden", "false");

    fetchJson("/api/events/" + encodeURIComponent(eventId) + "/interest/classes")
      .then(function (data) {
        var grid = qs(scrim, "#eci-popup-grid");
        var classes = (data && data.classes) || [];
        if (!classes.length) {
          qs(scrim, "#eci-popup-empty").hidden = false;
          qs(scrim, "#eci-popup-empty").textContent =
            "Class options are not configured for this event yet.";
          confirmBtn.disabled = true;
          return;
        }
        classes.forEach(function (c) {
          var btn = document.createElement("button");
          btn.type = "button";
          btn.className = "eci-popup-item";
          if (SELECTED.classIdentifier === c.class_identifier) btn.classList.add("is-selected");
          btn.setAttribute("data-class-identifier", c.class_identifier);
          var label = c.class_display_name || c.class_identifier;
          var count = typeof c.interested_count === "number" ? c.interested_count : 0;
          if (c.logo_path) {
            var img = document.createElement("img");
            img.src = c.logo_path;
            img.alt = "";
            img.width = 40;
            img.height = 40;
            btn.appendChild(img);
          } else {
            var miss = document.createElement("span");
            miss.className = "eci-popup-missing";
            miss.textContent = (label || "?").slice(0, 2).toUpperCase();
            btn.appendChild(miss);
          }
          var span = document.createElement("span");
          span.textContent = label + (count ? " · " + count : "");
          btn.appendChild(span);
          btn.addEventListener("click", function (e) {
            stop(e);
            SELECTED.classIdentifier = c.class_identifier;
            qsa(grid, ".eci-popup-item").forEach(function (n) {
              n.classList.toggle("is-selected", n === btn);
            });
            confirmBtn.disabled = false;
          });
          grid.appendChild(btn);
        });
      })
      .catch(function (err) {
        setPopupError(err.message || "Could not load classes");
      });
  }

  function confirmSelection() {
    if (!SELECTED || !SELECTED.classIdentifier || !SELECTED.eventId) return;
    var confirmBtn = qs(document, "#eci-popup-confirm");
    confirmBtn.disabled = true;
    setPopupError("");
    fetchJson("/api/events/" + encodeURIComponent(SELECTED.eventId) + "/interest", {
      method: "POST",
      body: { class_identifier: SELECTED.classIdentifier },
    })
      .then(function (snap) {
        renderCard(SELECTED.card, snap);
        closePopup();
      })
      .catch(function (err) {
        setPopupError(err.message || "Could not save interest");
        confirmBtn.disabled = false;
      });
  }

  function withdrawSelection() {
    if (!SELECTED || !SELECTED.eventId) return;
    setPopupError("");
    fetchJson("/api/events/" + encodeURIComponent(SELECTED.eventId) + "/interest/withdraw", {
      method: "POST",
      body: {},
    })
      .then(function (snap) {
        renderCard(SELECTED.card, snap);
        closePopup();
      })
      .catch(function (err) {
        setPopupError(err.message || "Could not withdraw interest");
      });
  }

  function buildCluster(card, snap, maxWidth) {
    var wrap = document.createElement("div");
    wrap.className = "eci-interest";
    wrap.setAttribute("data-eci", "1");

    var mine = snap && snap.mine && snap.mine.interested;
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "eci-btn" + (mine ? " is-mine" : "");
    btn.textContent = mine ? "✓ Interested" : "+ Interested";
    btn.addEventListener("click", function (e) {
      stop(e);
      openPopup(card, snap);
    });

    // Budget layout (button first). Avoid off-DOM getBoundingClientRect flakiness.
    var budget = Math.max(0, Math.floor(maxWidth));
    var btnCost = mine ? 112 : 104;
    var totalCost = 34;
    var logoCost = 22;
    var moreCost = 20;
    budget = Math.max(0, budget - btnCost);

    var fragBefore = [];

    var total = Number(snap && snap.total_interested) || 0;
    if (total > 0 && budget >= totalCost) {
      var totalEl = document.createElement("span");
      totalEl.className = "eci-total";
      totalEl.innerHTML =
        '<span class="eci-total-ico" aria-hidden="true">👥</span><span>' + total + "</span>";
      fragBefore.push(totalEl);
      budget -= totalCost;
    }

    var active = ((snap && snap.classes) || [])
      .filter(function (c) {
        return (c.interested_count || 0) > 0 && c.logo_path;
      })
      .sort(function (a, b) {
        return (b.interested_count || 0) - (a.interested_count || 0);
      });

    // Classes with interest but no logo still count toward +N overflow, not dropped from totals.
    var activeAll = ((snap && snap.classes) || [])
      .filter(function (c) {
        return (c.interested_count || 0) > 0;
      })
      .sort(function (a, b) {
        return (b.interested_count || 0) - (a.interested_count || 0);
      });

    var logosWrap = document.createElement("div");
    logosWrap.className = "eci-logos";
    var shown = 0;
    var maxLogos = Math.floor(budget / logoCost);
    if (maxLogos > 0 && active.length) {
      var showN = Math.min(maxLogos, active.length);
      // Reserve room for +N only when more than one logo would remain visible.
      if (activeAll.length > showN && budget - showN * logoCost < moreCost && showN > 1) {
        showN -= 1;
      }
      for (var i = 0; i < showN; i++) {
        var c = active[i];
        var item = document.createElement("button");
        item.type = "button";
        item.className = "eci-logo-item";
        item.title =
          (c.class_display_name || c.class_identifier || "") + " · " + c.interested_count;
        item.addEventListener("click", function (e) {
          stop(e);
          openPopup(card, snap);
        });
        var img = document.createElement("img");
        img.className = "landing-event-inline-logo eci-logo-img";
        img.src = c.logo_path;
        img.alt = "";
        img.width = LOGO_SIZE;
        img.height = LOGO_SIZE;
        item.appendChild(img);
        var n = document.createElement("span");
        n.className = "eci-logo-n";
        n.textContent = String(c.interested_count);
        item.appendChild(n);
        logosWrap.appendChild(item);
        shown += 1;
        budget -= logoCost;
      }
    }

    var remain = activeAll.length - shown;
    if (remain > 0 && budget >= moreCost && shown >= 0) {
      var more = document.createElement("button");
      more.type = "button";
      more.className = "eci-more";
      more.textContent = "+" + remain;
      more.addEventListener("click", function (e) {
        stop(e);
        openPopup(card, snap);
      });
      logosWrap.appendChild(more);
    }

    fragBefore.forEach(function (node) {
      wrap.appendChild(node);
    });
    if (logosWrap.childNodes.length) wrap.appendChild(logosWrap);
    wrap.appendChild(btn);
    return wrap;
  }

  function renderCard(card, snap) {
    var main = qs(card, ".sa-home-regatta-top-main");
    var title = qs(card, ".sa-home-regatta-title");
    var host = qs(card, ".sa-home-regatta-host");
    if (!main || !title) return;

    qsa(main, ".eci-interest").forEach(function (n) {
      n.remove();
    });

    title.classList.add("eci-title-pad");

    var mainBox = main.getBoundingClientRect();
    var want = BTN_MIN;
    if (mainBox.width >= 220) want = Math.min(Math.floor(mainBox.width * 0.48), BTN_MIN + 110);
    else if (mainBox.width >= 160) want = Math.min(Math.floor(mainBox.width * 0.42), BTN_MIN + 36);

    title.style.setProperty("--eci-pad", Math.ceil(want) + "px");
    mainBox = main.getBoundingClientRect();
    var free = Math.max(BTN_MIN, mainBox.right - glyphRight(title) - 4);
    free = Math.min(free, want + 8);

    var rowH = 26;
    if (host) {
      rowH = Math.max(26, Math.min(34, host.getBoundingClientRect().top - mainBox.top - 2));
    }

    var cluster = buildCluster(card, snap || { total_interested: 0, classes: [], mine: null }, free);
    cluster.style.height = Math.floor(rowH) + "px";
    cluster.setAttribute("data-eci-free", String(Math.round(free)));
    cluster.setAttribute(
      "data-eci-total",
      String(Number(snap && snap.total_interested) || 0)
    );
    cluster.setAttribute(
      "data-eci-classes",
      String(((snap && snap.classes) || []).length)
    );
    main.appendChild(cluster);

    var cw = Math.ceil(cluster.getBoundingClientRect().width) + 6;
    title.style.setProperty("--eci-pad", cw + "px");

    card.__eciSnap = snap;
  }

  function emptySnap() {
    return { total_interested: 0, classes: [], mine: null };
  }

  function mountAll(root) {
    var cards = qsa(root || document, ".landing-event-card[data-event-id]");
    if (!cards.length) return;

    var ids = cards
      .map(function (c) {
        return c.getAttribute("data-event-id");
      })
      .filter(Boolean);

    // Always paint buttons first (even before fetch) so every card has CTA.
    cards.forEach(function (card) {
      renderCard(card, emptySnap());
    });

    if (!ids.length) return;

    fetchJson("/api/events/interest?ids=" + encodeURIComponent(ids.join(",")))
      .then(function (data) {
        var map = (data && data.events) || {};
        cards.forEach(function (card) {
          var id = card.getAttribute("data-event-id");
          var snap = map[String(id)] || emptySnap();
          // Never invent — only use server payload.
          renderCard(card, {
            event_id: snap.event_id || Number(id),
            total_interested: Number(snap.total_interested) || 0,
            classes: Array.isArray(snap.classes) ? snap.classes : [],
            mine: snap.mine || null,
          });
        });
      })
      .catch(function () {
        // Keep buttons; show zero state — do not fabricate activity.
        cards.forEach(function (card) {
          renderCard(card, emptySnap());
        });
      });
  }

  function init(opts) {
    opts = opts || {};
    if (opts.apiBase != null) API_BASE = String(opts.apiBase);
    ensureScrim();
    mountAll(opts.root || document);
    if (!global.__eciResizeBound) {
      global.__eciResizeBound = true;
      var t = null;
      global.addEventListener("resize", function () {
        global.clearTimeout(t);
        t = global.setTimeout(function () {
          qsa(document, ".landing-event-card[data-event-id]").forEach(function (card) {
            renderCard(card, card.__eciSnap || emptySnap());
          });
        }, 80);
      });
    }
  }

  global.EventInterest = {
    init: init,
    mountAll: mountAll,
    renderCard: renderCard,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      if (global.EventInterestAutoInit !== false) init();
    });
  } else if (global.EventInterestAutoInit !== false) {
    init();
  }
})(typeof window !== "undefined" ? window : this);
