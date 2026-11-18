/**
 * Event Interest UI for Upcoming Event landing cards (Stage 3).
 *
 * Mounts on articles.landing-event-card[data-event-id].
 * Uses Stage 2 API contract. Never invents counts or classes.
 *
 * Zero interest: + Interested only.
 * Genuine interest: total + button on the title row; 14px logos/counts wrap below.
 */
(function (global) {
  "use strict";
  if (global.EventInterest) return;

  var API_BASE = "";
  var LOGO_SIZE = 24;
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
      cache: "no-store",
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
      '<input type="search" class="eci-popup-search" id="eci-popup-search" aria-label="Search remaining classes" placeholder="Search remaining recognised classes" hidden>' +
      '<div class="eci-popup-grid" id="eci-popup-grid"></div>' +
      '<p class="eci-popup-empty" id="eci-popup-empty" hidden></p>' +
      '<p class="eci-popup-error" id="eci-popup-error" hidden></p>' +
      '<div class="eci-popup-actions">' +
      '<button type="button" class="eci-popup-withdraw" id="eci-popup-withdraw" hidden>Withdraw</button>' +
      '<button type="button" class="eci-popup-close" id="eci-popup-close">Close</button>' +
      "</div></div>";
    document.body.appendChild(scrim);
    scrim.addEventListener("click", function (e) {
      if (e.target === scrim) closePopup();
    });
    qs(scrim, "#eci-popup-close").addEventListener("click", function (e) {
      stop(e);
      closePopup();
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
    var search = qs(scrim, "#eci-popup-search");
    search.hidden = true;
    search.value = "";
    search.oninput = null;
    qs(scrim, "#eci-popup-empty").hidden = true;
    setPopupError("");
    SELECTED = {
      eventId: eventId,
      classIdentifier: snap && snap.mine && snap.mine.interested ? snap.mine.class_identifier : null,
      card: card,
    };

    var withdrawBtn = qs(scrim, "#eci-popup-withdraw");
    withdrawBtn.disabled = false;
    withdrawBtn.hidden = !(snap && snap.mine && snap.mine.interested);

    scrim.classList.add("is-open");
    scrim.setAttribute("aria-hidden", "false");

    fetchJson("/api/events/" + encodeURIComponent(eventId) + "/interest/classes")
      .then(function (data) {
        if (!SELECTED || SELECTED.eventId !== eventId) return;
        var grid = qs(scrim, "#eci-popup-grid");
        var classes = (data && data.classes) || [];
        var hasCatalogue = !!(data && Array.isArray(data.other_classes));
        var choicePolicy = (data && data.choice_policy) || {};
        var hostClasses = (data && data.host_classes) || [];
        var other = (data && data.other_classes) || [];
        var tier = 0;
        if (SELECTED.classIdentifier && hostClasses.some(function (c) { return c.class_identifier === SELECTED.classIdentifier; })) tier = 1;
        if (SELECTED.classIdentifier && other.some(function (c) { return c.class_identifier === SELECTED.classIdentifier; })) tier = 2;
        function paintChoices() {
          grid.innerHTML = "";
          search.hidden = tier !== 2;
          var term = tier === 2 ? search.value.trim().toLowerCase() : "";
          var visible = (tier === 2 ? other : tier === 1 ? hostClasses : classes).filter(function (c) {
            return !term || String(c.class_display_name || "").toLowerCase().indexOf(term) !== -1 ||
              String(c.class_identifier || "").replace(/-/g, " ").toLowerCase().indexOf(term) !== -1;
          });
        visible.forEach(function (c) {
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
            img.loading = "lazy";
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
            if (!SELECTED || SELECTED.saving) return;
            SELECTED.classIdentifier = c.class_identifier;
            qsa(grid, ".eci-popup-item").forEach(function (n) {
              n.classList.toggle("is-selected", n === btn);
            });
            confirmSelection();
          });
          grid.appendChild(btn);
        });

          if (tier < 2 && (hostClasses.length || other.length)) {
            var more = document.createElement("button");
            more.type = "button";
            more.className = "eci-popup-item eci-popup-other";
            more.textContent = "More";
            more.addEventListener("click", function (e) {
              stop(e);
              tier = tier === 0 && hostClasses.length ? 1 : 2;
              search.value = "";
              paintChoices();
              if (tier === 2) search.focus();
            });
            grid.appendChild(more);
          }
          if (tier > 0) {
            var back = document.createElement("button");
            back.type = "button";
            back.className = "eci-popup-item eci-popup-other";
            back.textContent = "Back";
            back.addEventListener("click", function (e) {
              stop(e);
              tier = tier === 2 && hostClasses.length ? 1 : 0;
              search.value = "";
              paintChoices();
            });
            grid.appendChild(back);
          }
          var empty = qs(scrim, "#eci-popup-empty");
          empty.hidden = visible.length > 0;
          empty.textContent = choicePolicy.mode === "non_racing" ? choicePolicy.reason : !hasCatalogue ? "Class options are not configured for this event yet." : tier === 2 ? "No matching class in the class register." :
            tier === 1 ? "No additional classes found at this host club. Choose More." :
            "No historical classes found for this event. Choose More.";
        }
        search.oninput = function () {
          if (!SELECTED || SELECTED.eventId !== eventId) return;
          SELECTED.classIdentifier = null;
          paintChoices();
        };
        paintChoices();
      })
      .catch(function (err) {
        setPopupError(err.message || "Could not load classes");
      });
  }

  function confirmSelection() {
    if (!SELECTED || SELECTED.saving || !SELECTED.classIdentifier || !SELECTED.eventId) return;
    var selection = SELECTED;
    selection.saving = true;
    function setSaving(busy) {
      qsa(document, "#eci-popup-grid button, #eci-popup-withdraw").forEach(function (btn) {
        btn.disabled = busy;
      });
    }
    setSaving(true);
    setPopupError("");
    fetchJson("/api/events/" + encodeURIComponent(selection.eventId) + "/interest", {
      method: "POST",
      body: { class_identifier: selection.classIdentifier },
    })
      .then(function (snap) {
        renderCard(selection.card, snap);
        if (SELECTED === selection) {
          setSaving(false);
          closePopup();
        }
      })
      .catch(function (err) {
        if (SELECTED !== selection) return;
        selection.saving = false;
        setSaving(false);
        setPopupError(err.message || "Could not save interest");
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

  function buildInterest(card, snap) {
    var mine = snap && snap.mine && snap.mine.interested;
    var total = Number(snap && snap.total_interested) || 0;

    var top = document.createElement("div");
    top.className = "eci-interest-top";
    top.setAttribute("data-eci", "1");
    var controls = document.createElement("div");
    controls.className = "eci-controls";
    top.appendChild(controls);

    // Zero interest: button only. Never show total/logos for empty genuine totals.
    if (total > 0) {
      var totalEl = document.createElement("span");
      totalEl.className = "eci-total";
      totalEl.innerHTML =
        '<span class="eci-total-ico" aria-hidden="true">👥</span><span>' + total + "</span>";
      controls.appendChild(totalEl);
    }

    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "eci-btn" + (mine ? " is-mine" : "");
    btn.textContent = mine ? "✓ Interested" : "+ Interested";
    btn.addEventListener("click", function (e) {
      stop(e);
      openPopup(card, snap);
    });
    controls.appendChild(btn);

    var logosWrap = null;
    if (total > 0) {
      var active = ((snap && snap.classes) || [])
        .filter(function (c) {
          return (c.interested_count || 0) > 0;
        })
        .sort(function (a, b) {
          return (b.interested_count || 0) - (a.interested_count || 0);
        });
      if (active.length) {
        logosWrap = document.createElement("div");
        logosWrap.className = "eci-logos";
        logosWrap.setAttribute("data-eci-logos", "1");
        var firstRow = document.createElement("div");
        firstRow.className = "eci-logos-row eci-logos-top";
        var scrollRow = document.createElement("div");
        scrollRow.className = "eci-logos-row eci-logos-scroll";
        scrollRow.tabIndex = 0;
        scrollRow.setAttribute("aria-label", "More interested classes; scroll left or right");
        active.forEach(function (c, index) {
          var item = document.createElement("button");
          item.type = "button";
          item.className = "eci-logo-item";
          item.title =
            (c.class_display_name || c.class_identifier || "") + " · " + c.interested_count;
          item.addEventListener("click", function (e) {
            stop(e);
            openPopup(card, snap);
          });
          if (c.logo_path) {
            var img = document.createElement("img");
            img.className = "landing-event-inline-logo eci-logo-img";
            img.src = c.logo_path;
            img.alt = "";
            img.width = LOGO_SIZE;
            img.height = LOGO_SIZE;
            item.appendChild(img);
          } else {
            var miss = document.createElement("span");
            miss.className = "eci-logo-miss";
            miss.textContent = String(c.class_display_name || c.class_identifier || "?")
              .slice(0, 2)
              .toUpperCase();
            item.appendChild(miss);
          }
          var n = document.createElement("span");
          n.className = "eci-logo-n";
          n.textContent = String(c.interested_count);
          item.appendChild(n);
          (index < 3 ? firstRow : scrollRow).appendChild(item);
        });
        logosWrap.appendChild(firstRow);
        if (active.length > 3) logosWrap.appendChild(scrollRow);
      }
    }

    top.setAttribute("data-eci-total", String(total));
    top.setAttribute(
      "data-eci-classes",
      String(logosWrap ? logosWrap.querySelectorAll(".eci-logo-item").length : 0)
    );
    return { top: top, logos: logosWrap };
  }

  function renderCard(card, snap) {
    var main = qs(card, ".sa-home-regatta-top-main");
    var title = qs(card, ".sa-home-regatta-title");
    var meta = qs(card, ".sa-home-regatta-meta");
    if (!main || !title) return;

    qsa(main, ".eci-interest-top, .eci-logos[data-eci-logos]").forEach(function (n) {
      n.remove();
    });
    // legacy single-cluster cleanup
    qsa(main, ".eci-interest").forEach(function (n) {
      n.remove();
    });

    title.classList.add("eci-title-pad");

    var parts = buildInterest(card, snap || { total_interested: 0, classes: [], mine: null });
    main.appendChild(parts.top);

    // Title pad reserves space for total+button only (top row).
    var pad = Math.ceil(parts.top.getBoundingClientRect().width) + 8;
    if (pad < BTN_MIN) pad = BTN_MIN;
    title.style.setProperty("--eci-pad", pad + "px");
    // Re-measure after pad so top bar stays clear of title glyphs.
    pad = Math.ceil(parts.top.getBoundingClientRect().width) + 8;
    title.style.setProperty("--eci-pad", Math.max(BTN_MIN, pad) + "px");

    if (parts.logos) {
      var interestButton = qs(parts.top, ".eci-btn");
      parts.logos.style.width = interestButton.getBoundingClientRect().width + "px";
      parts.top.appendChild(parts.logos);
    }

    card.__eciSnap = snap;
    eciLockDatePill(card);
  }

  function eciLockDatePill(card) {
    var pill = qs(card, "[data-eci-event-dates]");
    if (!pill) return;
    pill.className = "sa-home-regatta-meta-pill sa-home-regatta-date-pill";
    pill.removeAttribute("style");
    var meta = qs(card, ".sa-home-regatta-meta");
    if (meta && meta.className.indexOf("sa-home-regatta-meta--stacked") === -1) {
      meta.className += " sa-home-regatta-meta--stacked";
    }
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

  var ECI_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  var eciEventsCache = null;
  var eciEventsPending = null;

  function eciYmd(d) {
    if (d == null || d === "") return "";
    return String(d).slice(0, 10);
  }

  function eciTodaySast() {
    try {
      return new Intl.DateTimeFormat("en-CA", {
        timeZone: "Africa/Johannesburg",
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
      }).format(new Date());
    } catch (_) {
      var t = new Date();
      var m = t.getMonth() + 1;
      var d = t.getDate();
      return t.getFullYear() + "-" + (m < 10 ? "0" : "") + m + "-" + (d < 10 ? "0" : "") + d;
    }
  }

  function eciParseYmd(d) {
    var s = eciYmd(d);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(s)) return null;
    var y = parseInt(s.slice(0, 4), 10);
    var m = parseInt(s.slice(5, 7), 10) - 1;
    var day = parseInt(s.slice(8, 10), 10);
    if (m < 0 || m > 11 || !day || !y) return null;
    return { y: y, m: m, d: day, yy: String(y).slice(-2) };
  }

  function eciDateShort(d) {
    var p = eciParseYmd(d);
    if (!p) return eciYmd(d) || "";
    return p.d + " " + ECI_MONTHS[p.m] + " " + p.yy;
  }

  function eciFormatRange(startDate, endDate) {
    var a = eciParseYmd(startDate);
    var b = eciParseYmd(endDate || startDate);
    if (!a && !b) return "";
    if (!a) return eciDateShort(endDate);
    if (!b || (a.y === b.y && a.m === b.m && a.d === b.d)) return eciDateShort(startDate);
    if (a.y === b.y && a.m === b.m) return a.d + "-" + b.d + " " + ECI_MONTHS[a.m] + " " + a.yy;
    if (a.y === b.y) return a.d + " " + ECI_MONTHS[a.m] + "-" + b.d + " " + ECI_MONTHS[b.m] + " " + a.yy;
    return eciDateShort(startDate) + "-" + eciDateShort(endDate);
  }

  function eciNormName(s) {
    return String(s || "")
      .replace(/&amp;/gi, "&")
      .replace(/&#039;|&apos;/gi, "'")
      .replace(/\s+/g, " ")
      .trim()
      .toLowerCase();
  }

  function eciCardTitle(card) {
    var t = qs(card, ".sa-home-regatta-title");
    return t ? String(t.textContent || "").replace(/\s+/g, " ").trim() : "";
  }

  function eciCardRegattaId(card) {
    var links = qsa(card, "a[href]");
    var i;
    for (i = 0; i < links.length; i++) {
      var href = links[i].getAttribute("href") || "";
      var m = href.match(/\/regatta\/([^/?#]+)/);
      if (m) {
        try {
          return decodeURIComponent(m[1]);
        } catch (_) {
          return m[1];
        }
      }
    }
    return "";
  }

  function eciPickEvent(events, card, today) {
    var title = eciNormName(eciCardTitle(card));
    var rid = String(eciCardRegattaId(card) || "").trim();
    var best = null;
    var i;
    for (i = 0; i < (events || []).length; i++) {
      var e = events[i];
      if (!e) continue;
      var name = eciNormName(e.event_name);
      var erid = String(e.regatta_id || "").trim();
      var sd = eciYmd(e.start_date);
      var score = 0;
      if (rid && erid && rid === erid) score += 100;
      if (title && name && title === name) score += 50;
      if (!score) continue;
      if (sd && sd >= today) score += 10;
      else if (sd) score -= 5;
      if (!best || score > best.score) best = { score: score, e: e };
    }
    return best && best.score > 0 ? best.e : null;
  }

  function eciEnsureDatePill(card, startDate, endDate) {
    var range = eciFormatRange(startDate, endDate);
    if (!range) return false;
    var main = qs(card, ".sa-home-regatta-top-main");
    if (!main) return false;
    var meta = qs(card, ".sa-home-regatta-meta");
    if (!meta) {
      meta = document.createElement("div");
      meta.className = "sa-home-regatta-meta";
      var title = qs(card, ".sa-home-regatta-title");
      if (title && title.nextSibling) main.insertBefore(meta, title.nextSibling);
      else main.appendChild(meta);
    }
    if (meta.className.indexOf("sa-home-regatta-meta--stacked") === -1) {
      meta.className += " sa-home-regatta-meta--stacked";
    }
    var existing = qs(meta, "[data-eci-event-dates]");
    if (existing) {
      if (existing.textContent !== range) existing.textContent = range;
      existing.className = "sa-home-regatta-meta-pill sa-home-regatta-date-pill";
      existing.removeAttribute("style");
      return true;
    }
    var pill = document.createElement("div");
    pill.className = "sa-home-regatta-meta-pill sa-home-regatta-date-pill";
    pill.setAttribute("data-eci-event-dates", "1");
    pill.textContent = range;
    var days = qs(meta, ".sa-home-regatta-days-pill");
    if (days) meta.insertBefore(pill, days);
    else meta.insertBefore(pill, meta.firstChild);
    if (startDate) card.setAttribute("data-start-date", eciYmd(startDate));
    if (endDate || startDate) card.setAttribute("data-end-date", eciYmd(endDate || startDate));
    return true;
  }

  function paintUpcomingDates(root) {
    var cards = qsa(root || document, ".landing-event-card--upcoming, .landing-event-card[data-state='upcoming'], .sa-home-regatta-card[data-state='upcoming']");
    if (!cards.length) return;
    var today = eciTodaySast();
    function apply(events) {
      cards.forEach(function (card) {
        var sd = eciYmd(card.getAttribute("data-start-date"));
        var ed = eciYmd(card.getAttribute("data-end-date"));
        if (sd || ed) {
          eciEnsureDatePill(card, sd, ed || sd);
          return;
        }
        var ev = eciPickEvent(events, card, today);
        if (ev) eciEnsureDatePill(card, ev.start_date, ev.end_date || ev.start_date);
      });
    }
    if (eciEventsCache) {
      apply(eciEventsCache);
      return;
    }
    if (eciEventsPending) {
      eciEventsPending.then(apply);
      return;
    }
    eciEventsPending = fetch("/api/events?blank_hub=1", {
      credentials: "same-origin",
      cache: "no-store",
      headers: { Accept: "application/json" },
    })
      .then(function (res) {
        if (!res.ok) throw new Error("events " + res.status);
        return res.json();
      })
      .then(function (data) {
        eciEventsCache = Array.isArray(data) ? data : (data && data.events) || [];
        eciEventsPending = null;
        return eciEventsCache;
      })
      .catch(function () {
        eciEventsPending = null;
        return [];
      });
    eciEventsPending.then(apply);
  }

  function init(opts) {
    opts = opts || {};
    if (opts.apiBase != null) API_BASE = String(opts.apiBase);
    ensureScrim();
    mountAll(opts.root || document);
    paintUpcomingDates(opts.root || document);
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
