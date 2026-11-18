/**
 * Start/end dates on homepage upcoming cards.
 * Days-to-go stays; calendar range is added so readers do not have to work it out.
 * Matches live landing cards (.landing-event-card[data-state=upcoming]) and any
 * future extra-upcoming articles that use the same shell.
 */
(function (root) {
  "use strict";

  var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  var EVENTS_CACHE = null;
  var EVENTS_PENDING = null;

  function ymdSlice(d) {
    if (d == null || d === "") return "";
    return String(d).slice(0, 10);
  }

  function todayYmdSast() {
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

  function parseYmd(d) {
    var s = ymdSlice(d);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(s)) return null;
    var y = parseInt(s.slice(0, 4), 10);
    var m = parseInt(s.slice(5, 7), 10) - 1;
    var day = parseInt(s.slice(8, 10), 10);
    if (m < 0 || m > 11 || !day || !y) return null;
    return { y: y, m: m, d: day, yy: String(y).slice(-2) };
  }

  function dateShort(d) {
    var p = parseYmd(d);
    if (!p) return ymdSlice(d) || "";
    return p.d + " " + MONTHS[p.m] + " " + p.yy;
  }

  /** Compact MP range: "28-29 Nov 26" / "28 Nov 26". */
  function formatRange(startDate, endDate) {
    var a = parseYmd(startDate);
    var b = parseYmd(endDate || startDate);
    if (!a && !b) return "";
    if (!a) return dateShort(endDate);
    if (!b || (a.y === b.y && a.m === b.m && a.d === b.d)) return dateShort(startDate);
    if (a.y === b.y && a.m === b.m) return a.d + "-" + b.d + " " + MONTHS[a.m] + " " + a.yy;
    if (a.y === b.y) return a.d + " " + MONTHS[a.m] + "-" + b.d + " " + MONTHS[b.m] + " " + a.yy;
    return dateShort(startDate) + "-" + dateShort(endDate);
  }

  function normName(s) {
    return String(s || "")
      .replace(/&amp;/gi, "&")
      .replace(/&#039;|&apos;/gi, "'")
      .replace(/\s+/g, " ")
      .trim()
      .toLowerCase();
  }

  function cardTitle(card) {
    if (!card || !card.querySelector) return "";
    var t = card.querySelector(".sa-home-regatta-title");
    return t ? String(t.textContent || "").replace(/\s+/g, " ").trim() : "";
  }

  function cardRegattaId(card) {
    if (!card || !card.querySelectorAll) return "";
    var links = card.querySelectorAll("a[href]");
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

  function eventsFromPayload(data) {
    if (Array.isArray(data)) return data;
    if (data && Array.isArray(data.events)) return data.events;
    return [];
  }

  /**
   * Prefer exact title + future start; then /regatta/ slug; then nearest future start.
   */
  function betterDate(sd, currentSd, today) {
    var a = ymdSlice(sd);
    var b = ymdSlice(currentSd);
    var aFut = !!(a && a >= today);
    var bFut = !!(b && b >= today);
    if (aFut !== bFut) return aFut;
    if (aFut && bFut && a && b && a !== b) return a < b;
    if (!aFut && !bFut && a && b && a !== b) return a > b;
    return false;
  }

  function pickEvent(events, card, todayYmd) {
    var today = todayYmd || todayYmdSast();
    var title = normName(cardTitle(card));
    var rid = String(cardRegattaId(card) || "").trim();
    var best = null;
    var i;
    for (i = 0; i < (events || []).length; i++) {
      var e = events[i];
      if (!e) continue;
      var name = normName(e.event_name);
      var erid = String(e.regatta_id || "").trim();
      var sd = ymdSlice(e.start_date);
      var score = 0;
      if (rid && erid && rid === erid) score += 100;
      if (title && name && title === name) score += 50;
      if (!score) continue;
      if (sd && sd >= today) score += 10;
      else if (sd) score -= 5;
      if (!best || score > best.score || (score === best.score && betterDate(sd, best.sd, today))) {
        best = { score: score, sd: sd, e: e };
      }
    }
    return best && best.score > 0 ? best.e : null;
  }

  function datesFromCard(card) {
    if (!card || !card.getAttribute) return null;
    var sd = ymdSlice(card.getAttribute("data-start-date"));
    var ed = ymdSlice(card.getAttribute("data-end-date"));
    if (sd || ed) return { start_date: sd, end_date: ed || sd };
    return null;
  }

  function isDaysPill(el) {
    return !!(el && String(el.className || "").indexOf("sa-home-regatta-days-pill") !== -1);
  }

  function daysToGo(startDate) {
    var a = parseYmd(startDate);
    var t = parseYmd(todayYmdSast());
    if (!a || !t) return null;
    var n = Math.round((Date.UTC(a.y, a.m, a.d) - Date.UTC(t.y, t.m, t.d)) / 86400000);
    if (n < 0) return null;
    var text = n === 0 ? "TODAY" : n === 1 ? "1 DAY TO GO" : n + " DAYS TO GO";
    var cls = "sa-home-regatta-meta-pill sa-home-regatta-days-pill";
    cls += n <= 7 ? " sa-home-regatta-days-pill--soon" : " sa-home-regatta-days-pill--later";
    return { text: text, className: cls };
  }

  function ensureDaysPill(meta, startDate, doc) {
    var days = meta.querySelector(".sa-home-regatta-days-pill");
    if (days) return days;
    var parts = daysToGo(startDate);
    if (!parts) return null;
    days = doc.createElement("div");
    days.className = parts.className;
    days.textContent = parts.text;
    meta.appendChild(days);
    return days;
  }

  function ensureDatePill(card, startDate, endDate) {
    if (!card || !card.querySelector) return false;
    var range = formatRange(startDate, endDate);
    if (!range) return false;
    var main = card.querySelector(".sa-home-regatta-top-main");
    if (!main) return false;
    var doc = card.ownerDocument || (typeof document !== "undefined" ? document : null);
    if (!doc) return false;
    var meta = card.querySelector(".sa-home-regatta-meta");
    if (!meta) {
      meta = doc.createElement("div");
      meta.className = "sa-home-regatta-meta";
      var title = card.querySelector(".sa-home-regatta-title");
      if (title) {
        if (title.nextSibling) main.insertBefore(meta, title.nextSibling);
        else main.appendChild(meta);
      } else {
        main.appendChild(meta);
      }
    }
    if (meta.className.indexOf("sa-home-regatta-meta--stacked") === -1) {
      meta.className += " sa-home-regatta-meta--stacked";
    }
    var existing = meta.querySelector("[data-eci-event-dates]");
    if (existing && isDaysPill(existing)) {
      existing.removeAttribute("data-eci-event-dates");
      existing = null;
    }
    var days = ensureDaysPill(meta, startDate, doc);
    if (existing) {
      existing.className = "sa-home-regatta-dates";
      existing.textContent = range;
      existing.removeAttribute("style");
      if (days && existing.nextSibling !== days) meta.insertBefore(existing, days);
      return true;
    }
    var line = doc.createElement("div");
    line.className = "sa-home-regatta-dates";
    line.setAttribute("data-eci-event-dates", "1");
    line.textContent = range;
    if (days) meta.insertBefore(line, days);
    else meta.insertBefore(line, meta.firstChild);
    if (startDate) card.setAttribute("data-start-date", ymdSlice(startDate));
    if (endDate || startDate) card.setAttribute("data-end-date", ymdSlice(endDate || startDate));
    stackHost(card);
    return true;
  }

  function stackHost(card) {
    if (!card || !card.querySelector) return;
    var main = card.querySelector(".sa-home-regatta-top-main");
    var host = card.querySelector(".sa-home-regatta-host");
    var meta = card.querySelector(".sa-home-regatta-meta");
    if (!main || !host) return;
    if (host.parentNode !== main) {
      if (meta && meta.parentNode === main) {
        if (meta.nextSibling) main.insertBefore(host, meta.nextSibling);
        else main.appendChild(host);
      } else {
        main.appendChild(host);
      }
    }
    host.style.gridArea = "auto";
  }

  function upcomingCards(root) {
    var doc = root && root.querySelectorAll ? root : (typeof document !== "undefined" ? document : null);
    if (!doc) return [];
    var nodes = doc.querySelectorAll(
      ".landing-event-card--upcoming, .landing-event-card[data-state='upcoming'], .sa-home-regatta-card[data-state='upcoming']"
    );
    return Array.prototype.slice.call(nodes);
  }

  function fetchUpcomingEvents() {
    if (EVENTS_CACHE) return Promise.resolve(EVENTS_CACHE);
    if (EVENTS_PENDING) return EVENTS_PENDING;
    var url = "/api/events?blank_hub=1";
    EVENTS_PENDING = fetch(url, { credentials: "same-origin", cache: "no-store", headers: { Accept: "application/json" } })
      .then(function (res) {
        if (!res.ok) throw new Error("events " + res.status);
        return res.json();
      })
      .then(function (data) {
        EVENTS_CACHE = eventsFromPayload(data);
        EVENTS_PENDING = null;
        return EVENTS_CACHE;
      })
      .catch(function () {
        EVENTS_PENDING = null;
        return [];
      });
    return EVENTS_PENDING;
  }

  function paintCard(card, events, todayYmd) {
    var fromAttr = datesFromCard(card);
    if (fromAttr && ensureDatePill(card, fromAttr.start_date, fromAttr.end_date)) return true;
    var ev = pickEvent(events, card, todayYmd);
    if (!ev) return false;
    return ensureDatePill(card, ev.start_date, ev.end_date || ev.start_date);
  }

  function paintAll(root) {
    var cards = upcomingCards(root);
    if (!cards.length) return Promise.resolve(0);
    var today = todayYmdSast();
    var nAttr = 0;
    var needFetch = false;
    cards.forEach(function (card) {
      var fromAttr = datesFromCard(card);
      if (fromAttr && ensureDatePill(card, fromAttr.start_date, fromAttr.end_date)) nAttr += 1;
      else needFetch = true;
    });
    if (!needFetch) return Promise.resolve(nAttr);
    return fetchUpcomingEvents().then(function (events) {
      var painted = nAttr;
      cards.forEach(function (card) {
        if (card.querySelector("[data-eci-event-dates]")) return;
        if (paintCard(card, events, today)) painted += 1;
      });
      return painted;
    });
  }

  var api = {
    formatRange: formatRange,
    dateShort: dateShort,
    pickEvent: pickEvent,
    paintAll: paintAll,
    todayYmdSast: todayYmdSast,
    ymdSlice: ymdSlice,
  };

  if (typeof module !== "undefined" && module.exports && typeof window === "undefined") {
    module.exports = api;
  }
  root.UpcomingEventDates = api;

  function boot() {
    if (root.EventInterest) return;
    try {
      paintAll();
    } catch (_) {}
  }
  if (typeof document !== "undefined") {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", boot);
    } else {
      boot();
    }
  }
})(typeof window !== "undefined" ? window : typeof globalThis !== "undefined" ? globalThis : this);
