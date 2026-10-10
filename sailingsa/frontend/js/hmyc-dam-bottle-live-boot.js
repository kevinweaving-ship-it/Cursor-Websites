/**
 * Dam Bottle Sprints — clone Dart Nationals event URL stack.
 * Order: event header → Leader Board → Wind → Media → Live Cam → Open Fleet.
 * Admin types ET only. Corrected = ET seconds × 1000 ÷ PY (✓ cell).
 * R1 place and Rank sort from that result. R1 is not typed.
 * Click R1 closed: hide ET + ✓, leave rank / R1 position.
 * Public: Rank / Class / Sail No / Club / Helm / Crew / Cat + R scores only.
 * Does not change live api.py.
 */
(function () {
  "use strict";
  var RID = "2026-10-10-hmyc-dam-bottle-sprints";
  var ET_KEY = "ssa-dam-bottle-et";
  var path = String((window.location && window.location.pathname) || "")
    .replace(/\/+$/, "")
    .toLowerCase();
  if (path !== "/regatta/" + RID && path.indexOf("/regatta/" + RID + "/") !== 0) return;

  var page = document.querySelector(".regatta-page");
  if (page) {
    page.setAttribute("data-hmyc-live", "1");
    page.setAttribute("data-club-live-cards", "HMYC");
  }

  if (!document.getElementById("dam-bottle-dart-media-css")) {
    var css = document.createElement("style");
    css.id = "dam-bottle-dart-media-css";
    css.textContent =
      ".regatta-page > .midmar-live-media .mm-lipton-reels[data-regatta-id^='2026-10-10-hmyc-dam-bottle-sprints'] .mm-lipton-reels-brand{" +
      "display:block!important;cursor:pointer;flex:0 0 auto;}" +
      ".regatta-page > .midmar-live-media .mm-lipton-reels[data-regatta-id^='2026-10-10-hmyc-dam-bottle-sprints'] .mm-lipton-reels-brand img{" +
      "display:block!important;width:100%!important;height:100%!important;object-fit:contain!important;}" +
      ".regatta-page > .midmar-live-media .mm-lipton-reels[data-regatta-id^='2026-10-10-hmyc-dam-bottle-sprints'] .mm-lipton-reels-compact{" +
      "display:flex!important;}" +
      ".regatta-page > .midmar-live-media .mm-lipton-reels[data-regatta-id^='2026-10-10-hmyc-dam-bottle-sprints'] .mm-lipton-reels-expanded," +
      ".regatta-page > .midmar-live-media .mm-lipton-reels[data-regatta-id^='2026-10-10-hmyc-dam-bottle-sprints'] [data-mm-expanded]{" +
      "display:none!important;height:0!important;overflow:hidden!important;}" +
      ".fleet-section[data-block-id='" + RID + ":open'] th.dam-bottle-corr-col," +
      ".fleet-section[data-block-id='" + RID + ":open'] td.dam-bottle-corr-col{" +
      "text-align:center;min-width:4.4rem;color:#15803d;font-weight:700;" +
      "font-variant-numeric:tabular-nums;}" +
      ".fleet-section[data-block-id='" + RID + ":open'] th.dam-bottle-corr-col .event-result-yes{" +
      "color:#15803d;font-weight:700;font-size:1.05rem;line-height:1;}" +
      ".fleet-section[data-block-id='" + RID + ":open'] .dam-bottle-et-input{" +
      "width:5.6rem;max-width:100%;text-align:center;font:inherit;" +
      "border:1px solid #94a3b8;border-radius:4px;padding:2px 5px;box-sizing:border-box;}" +
      ".fleet-section[data-block-id='" + RID + ":open'] td.race-col[data-auto-from-et='1'] input{" +
      "display:none!important}" +
      ".regatta-page:not(.regatta-page--club-score-edit):not(.regatta-page--super-admin-edit) " +
      ".fleet-section[data-block-id='" + RID + ":open'] .dam-bottle-py-col," +
      ".regatta-page:not(.regatta-page--club-score-edit):not(.regatta-page--super-admin-edit) " +
      ".fleet-section[data-block-id='" + RID + ":open'] .dam-bottle-et-col," +
      ".regatta-page:not(.regatta-page--club-score-edit):not(.regatta-page--super-admin-edit) " +
      ".fleet-section[data-block-id='" + RID + ":open'] .dam-bottle-corr-col{" +
      "display:none!important}" +
      ".fleet-section[data-block-id='" + RID + ":open'].fleet-section--r1-closed .dam-bottle-et-col," +
      ".fleet-section[data-block-id='" + RID + ":open'].fleet-section--r1-closed .dam-bottle-corr-col{" +
      "display:none!important}";
    document.head.appendChild(css);
  }

  function adminEditOn() {
    var p = document.querySelector(".regatta-page");
    return !!(
      p &&
      (p.classList.contains("regatta-page--club-score-edit") ||
        p.classList.contains("regatta-page--super-admin-edit"))
    );
  }

  function sessionToken() {
    try {
      var a = localStorage.getItem("session");
      if (a && a.charAt(0) !== "{" && String(a).trim().length > 8) return String(a).trim();
      var b = localStorage.getItem("sailing_session");
      if (b) {
        var o = JSON.parse(b);
        var t = String((o && (o.session || o.session_token || o.session_id)) || "").trim();
        if (t) return t;
      }
    } catch (e) {}
    return "";
  }

  function withSession(url) {
    var t = sessionToken();
    if (!t) return url;
    return url + (url.indexOf("?") >= 0 ? "&" : "?") + "session=" + encodeURIComponent(t);
  }

  function loadEtMap() {
    try {
      return JSON.parse(localStorage.getItem(ET_KEY) || "{}") || {};
    } catch (e1) {
      return {};
    }
  }

  function saveEtValue(rid, val) {
    var m = loadEtMap();
    val = String(val || "").trim();
    if (val) m[String(rid)] = val;
    else delete m[String(rid)];
    try {
      localStorage.setItem(ET_KEY, JSON.stringify(m));
    } catch (e2) {}
  }

  function parseET(raw) {
    var s = String(raw || "").trim();
    if (!s) return null;
    if (/^\d+(\.\d+)?$/.test(s)) {
      var n = parseFloat(s);
      return n > 0 ? n : null;
    }
    var parts = s.split(":");
    var min;
    var sec;
    var hr;
    if (parts.length === 2) {
      min = parseInt(parts[0], 10);
      sec = parseFloat(parts[1]);
      if (!isFinite(min) || min < 0 || !isFinite(sec) || sec < 0 || sec >= 60) return null;
      return min * 60 + sec;
    }
    if (parts.length === 3) {
      hr = parseInt(parts[0], 10);
      min = parseInt(parts[1], 10);
      sec = parseFloat(parts[2]);
      if (
        !isFinite(hr) ||
        hr < 0 ||
        !isFinite(min) ||
        min < 0 ||
        min >= 60 ||
        !isFinite(sec) ||
        sec < 0 ||
        sec >= 60
      )
        return null;
      return hr * 3600 + min * 60 + sec;
    }
    return null;
  }

  function formatCorrected(sec) {
    if (sec == null || !isFinite(sec) || sec <= 0) return "";
    var s = Math.round(sec * 10) / 10;
    var h = Math.floor(s / 3600);
    var m = Math.floor((s % 3600) / 60);
    var rem = Math.round((s - h * 3600 - m * 60) * 10) / 10;
    var remStr = rem.toFixed(1);
    if (rem < 10) remStr = "0" + remStr;
    if (h > 0) return String(h) + ":" + (m < 10 ? "0" : "") + String(m) + ":" + remStr;
    return String(m) + ":" + remStr;
  }

  function rankLabel(rank) {
    var n = parseInt(rank, 10);
    if (!isFinite(n) || n < 1) return "";
    if (n === 1) return "1st";
    if (n === 2) return "2nd";
    if (n === 3) return "3rd";
    return String(n) + "th";
  }

  function markCol(table, label, className) {
    if (!table) return -1;
    var ths = table.querySelectorAll("thead th");
    var i;
    for (i = 0; i < ths.length; i++) {
      var txt = String(ths[i].textContent || "").replace(/\s+/g, " ").trim();
      if (txt === label) {
        ths[i].classList.add(className);
        table.querySelectorAll("tbody tr").forEach(function (tr) {
          if (tr.children[i]) tr.children[i].classList.add(className);
        });
        return i;
      }
    }
    return -1;
  }

  function insertAfter(parent, newNode, afterNode) {
    if (!parent || !newNode) return;
    if (afterNode && afterNode.nextSibling) parent.insertBefore(newNode, afterNode.nextSibling);
    else parent.appendChild(newNode);
  }

  function ensureColAfter(table, afterLabel, label, className, cellHtml) {
    if (!table || markCol(table, label, className) >= 0) return;
    var ths = table.querySelectorAll("thead th");
    var after = -1;
    var i;
    for (i = 0; i < ths.length; i++) {
      if (String(ths[i].textContent || "").replace(/\s+/g, " ").trim() === afterLabel) after = i;
    }
    if (after < 0) return;
    var th = document.createElement("th");
    th.className = className;
    th.textContent = label;
    insertAfter(ths[after].parentNode, th, ths[after]);
    table.querySelectorAll("tbody tr").forEach(function (tr) {
      var td = document.createElement("td");
      td.className = className;
      if (cellHtml) td.innerHTML = cellHtml;
      insertAfter(tr, td, tr.children[after]);
    });
  }

  function ensureR1(table) {
    if (!table) return;
    if (!table.querySelector('th.race-col[data-race-key="R1"]')) {
      var thead = table.querySelector("thead tr");
      if (!thead) return;
      var th = document.createElement("th");
      th.className = "race-col";
      th.setAttribute("data-race-key", "R1");
      th.textContent = "R1";
      var totalTh = thead.querySelector("th.total-col, th.nett-col");
      if (totalTh) thead.insertBefore(th, totalTh);
      else thead.appendChild(th);
    }
    table.querySelectorAll("tbody tr[data-result-id]").forEach(function (tr) {
      if (tr.querySelector('td.race-col[data-race-key="R1"]')) return;
      var td = document.createElement("td");
      td.className = "race-col";
      td.setAttribute("data-race-key", "R1");
      var totalTd = tr.querySelector("td.total-col, td.nett-col");
      if (totalTd) tr.insertBefore(td, totalTd);
      else tr.appendChild(td);
    });
    lockR1(table);
  }

  function lockR1(table) {
    if (!table) return;
    table
      .querySelectorAll('th.race-col[data-race-key="R1"], td.race-col[data-race-key="R1"]')
      .forEach(function (el) {
        el.setAttribute("data-auto-from-et", "1");
        el.classList.add("race-col--auto");
      });
    table
      .querySelectorAll(
        'td.race-col[data-race-key="R1"] .club-score-input, td.race-col[data-race-key="R1"] .wc-result-field-input'
      )
      .forEach(function (inp) {
        var td = inp.parentNode;
        var v = String(inp.value || "").trim();
        if (inp.parentNode) inp.parentNode.removeChild(inp);
        if (td && !String(td.textContent || "").trim() && v) td.textContent = v;
      });
  }

  function ensureTickCol(table) {
    if (!table) return;
    var etTh = null;
    table.querySelectorAll("thead th").forEach(function (th) {
      if (String(th.textContent || "").replace(/\s+/g, " ").trim() === "ET") etTh = th;
    });
    if (!etTh) return;
    if (!table.querySelector("th.dam-bottle-corr-col")) {
      var th = document.createElement("th");
      th.className = "dam-bottle-corr-col";
      th.innerHTML = '<span class="event-result-yes" title="Corrected = ET × 1000 ÷ PY">✓</span>';
      insertAfter(etTh.parentNode, th, etTh);
      var etIdx = [].indexOf.call(etTh.parentNode.children, etTh);
      table.querySelectorAll("tbody tr").forEach(function (tr) {
        var td = document.createElement("td");
        td.className = "dam-bottle-corr-col";
        insertAfter(tr, td, tr.children[etIdx]);
      });
    }
    table.querySelectorAll("td.dam-bottle-corr-col").forEach(function (td) {
      var tick = td.querySelector(".event-result-yes");
      if (tick) td.removeChild(tick);
    });
  }

  function r1Closed(sec) {
    var th = sec && sec.querySelector('th.race-col[data-race-key="R1"]');
    return !!(th && th.classList.contains("race-col--closed"));
  }

  function syncR1Closed(sec) {
    if (!sec) return;
    sec.classList.toggle("fleet-section--r1-closed", r1Closed(sec));
  }

  function rowPy(tr) {
    var td = tr.querySelector("td.dam-bottle-py-col");
    var n = parseFloat(String((td && td.textContent) || "").replace(/[^\d.]/g, ""));
    return isFinite(n) && n > 0 ? n : null;
  }

  function rowEtRaw(tr) {
    var inp = tr.querySelector(".dam-bottle-et-input");
    if (inp) return String(inp.value || "").trim();
    var td = tr.querySelector("td.dam-bottle-et-col");
    return String((td && td.getAttribute("data-et")) || "").trim();
  }

  function paintRowResult(tr, corrSec, place) {
    var corrTd = tr.querySelector("td.dam-bottle-corr-col");
    var r1 = tr.querySelector('td.race-col[data-race-key="R1"]');
    var rankTd = tr.querySelector("td.rank-col") || tr.children[0];
    var py = rowPy(tr);
    var etSec = parseET(rowEtRaw(tr));
    if (corrTd) {
      if (corrSec != null) {
        corrTd.textContent = formatCorrected(corrSec);
        corrTd.setAttribute("data-corr-sec", String(corrSec));
        if (etSec != null && py) {
          corrTd.title =
            String(etSec) + "s × 1000 ÷ " + String(py) + " = " + String(Math.round(corrSec * 10) / 10) + "s";
        }
      } else {
        corrTd.textContent = "";
        corrTd.removeAttribute("data-corr-sec");
        corrTd.removeAttribute("title");
      }
    }
    if (r1) {
      lockR1(tr.closest("table"));
      r1.textContent = place ? String(place) : "";
    }
    tr.classList.remove("medal-gold", "medal-silver", "medal-bronze");
    if (place) {
      tr.setAttribute("data-official-rank", String(place));
      tr.setAttribute("data-dbs-place", String(place));
      if (rankTd) rankTd.textContent = rankLabel(place);
      if (place === 1) tr.classList.add("medal-gold");
      else if (place === 2) tr.classList.add("medal-silver");
      else if (place === 3) tr.classList.add("medal-bronze");
    } else {
      tr.removeAttribute("data-official-rank");
      tr.removeAttribute("data-dbs-place");
      if (rankTd) rankTd.textContent = "";
    }
  }

  function scoredRows(table) {
    var items = [];
    table.querySelectorAll("tbody tr[data-result-id]").forEach(function (tr, idx) {
      var py = rowPy(tr);
      var etRaw = rowEtRaw(tr);
      var etSec = parseET(etRaw);
      var corr = py && etSec != null ? (etSec * 1000) / py : null;
      items.push({
        tr: tr,
        rid: tr.getAttribute("data-result-id"),
        py: py,
        etRaw: etRaw,
        etSec: etSec,
        corr: corr,
        idx: idx,
      });
    });
    var ranked = items.filter(function (it) {
      return it.corr != null;
    });
    ranked.sort(function (a, b) {
      if (a.corr !== b.corr) return a.corr - b.corr;
      return a.idx - b.idx;
    });
    ranked.forEach(function (it, i) {
      it.place = i + 1;
    });
    return items;
  }

  var saveChain = Promise.resolve();
  var lastSaved = {};

  function persistPlaces(items) {
    if (!adminEditOn() || !sessionToken()) return;
    var next = {};
    items.forEach(function (it) {
      next[it.rid] = it.place ? String(it.place) : "";
    });
    var same = true;
    items.forEach(function (it) {
      if (String(lastSaved[it.rid] || "") !== String(next[it.rid] || "")) same = false;
    });
    if (same && Object.keys(lastSaved).length) return;
    var changing = items.filter(function (it) {
      return String(lastSaved[it.rid] || "") !== String(next[it.rid] || "");
    });
    if (!changing.length) {
      lastSaved = next;
      return;
    }
    function patch(rid, value) {
      return fetch(withSession("/api/result/" + encodeURIComponent(rid) + "/race"), {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ race: "R1", value: value, session: sessionToken() }),
      }).then(function (r) {
        return r.json().then(function (j) {
          if (!r.ok) throw new Error((j && j.detail) || "R1 save failed");
          return j;
        });
      });
    }
    saveChain = saveChain
      .then(function () {
        var clears = changing.filter(function (it) {
          return lastSaved[it.rid];
        });
        var seq = Promise.resolve();
        clears.forEach(function (it) {
          seq = seq.then(function () {
            return patch(it.rid, "");
          });
        });
        return seq;
      })
      .then(function () {
        var seq = Promise.resolve();
        changing.forEach(function (it) {
          if (!it.place) return;
          seq = seq.then(function () {
            return patch(it.rid, String(it.place));
          });
        });
        return seq;
      })
      .then(function () {
        lastSaved = next;
      })
      .catch(function () {});
  }

  function applyCorrection(table, doSort, doSave) {
    if (!table) return;
    lockR1(table);
    var items = scoredRows(table);
    items.forEach(function (it) {
      paintRowResult(it.tr, it.corr, it.place || 0);
    });
    if (doSort) {
      var tb = table.tBodies && table.tBodies[0];
      if (tb) {
        items
          .slice()
          .sort(function (a, b) {
            if ((a.place || 9999) !== (b.place || 9999)) return (a.place || 9999) - (b.place || 9999);
            return a.idx - b.idx;
          })
          .forEach(function (it) {
            tb.appendChild(it.tr);
          });
      }
    }
    if (doSave) persistPlaces(items);
  }

  function wireEtInputs(table) {
    if (!table) return;
    var stored = loadEtMap();
    var admin = adminEditOn();
    table.querySelectorAll("tbody tr[data-result-id]").forEach(function (tr) {
      var td = tr.querySelector("td.dam-bottle-et-col");
      if (!td) return;
      var rid = tr.getAttribute("data-result-id");
      var kept = String(stored[rid] || td.getAttribute("data-et") || "").trim();
      var existing = td.querySelector(".dam-bottle-et-input");
      if (!admin) {
        if (existing && document.activeElement !== existing) {
          existing.parentNode.removeChild(existing);
        }
        td.setAttribute("data-et", kept);
        return;
      }
      if (existing) {
        if (document.activeElement !== existing && kept && !String(existing.value || "").trim()) {
          existing.value = kept;
        }
        return;
      }
      var inp = document.createElement("input");
      inp.type = "text";
      inp.className = "dam-bottle-et-input";
      inp.setAttribute("inputmode", "decimal");
      inp.setAttribute("autocomplete", "off");
      inp.setAttribute("maxlength", "16");
      inp.setAttribute("aria-label", "Elapsed time");
      inp.setAttribute("placeholder", "m:ss");
      inp.value = kept;
      td.setAttribute("data-et", kept);
      td.textContent = "";
      td.appendChild(inp);
      inp.addEventListener("input", function () {
        td.setAttribute("data-et", String(inp.value || "").trim());
        saveEtValue(rid, inp.value);
        applyCorrection(table, false, false);
      });
      inp.addEventListener("blur", function () {
        saveEtValue(rid, inp.value);
        applyCorrection(table, true, true);
      });
      inp.addEventListener("keydown", function (ev) {
        if (ev.key !== "Enter") return;
        ev.preventDefault();
        inp.blur();
      });
    });
  }

  function paintPublicFleetTable(sec) {
    var table = sec && sec.querySelector("table.fleet-results-table");
    if (!table) return;
    var ageTh = null;
    table.querySelectorAll("thead th").forEach(function (th) {
      if (String(th.textContent || "").trim() === "Age") ageTh = th;
    });
    if (ageTh) ageTh.textContent = "Cat";
    ensureColAfter(table, "Helm", "Crew", "crew-col", "");
    markCol(table, "PY", "dam-bottle-py-col");
    ensureColAfter(table, "PY", "ET", "dam-bottle-et-col", "");
    ensureTickCol(table);
    ensureR1(table);
    wireEtInputs(table);
    syncR1Closed(sec);
    var focused =
      document.activeElement &&
      document.activeElement.classList &&
      document.activeElement.classList.contains("dam-bottle-et-input");
    applyCorrection(table, !focused, false);
  }

  function bottleSrc() {
    return "/artwork/Event%20Logo/Dam-Bottle-Sprints.png";
  }

  function setBottleImg(img) {
    if (!img) return;
    img.src = bottleSrc();
    img.alt = "Dam Bottle Sprints";
    img.removeAttribute("title");
  }

  function dropDuplicateFleetHeaders() {
    document.querySelectorAll(".fleet-section").forEach(function (sec) {
      var bid = String(sec.getAttribute("data-block-id") || "");
      var ours = sec.id === "dam-bottle-open-fleet" || bid.indexOf(RID) === 0;
      if (!ours) return;
      if (!sec.querySelector("table.fleet-results-table") && sec.parentNode) {
        sec.parentNode.removeChild(sec);
      }
    });
  }

  function paintOpenFleetHeader(sec) {
    if (!sec) return;
    setBottleImg(sec.querySelector(".class-header-logo-col img"));
    var title = sec.querySelector(".fleet-title-with-logo");
    if (title) {
      setBottleImg(title.querySelector("img"));
      var hasText = false;
      Array.prototype.forEach.call(title.childNodes, function (n) {
        if (n.nodeType === 3) {
          n.nodeValue = " Open Fleet";
          hasText = true;
        }
      });
      if (!hasText) title.appendChild(document.createTextNode(" Open Fleet"));
    }
    var line = sec.querySelector(".sailed-line");
    if (line && !/Portsmouth Yardstick \(PY\)/.test(line.textContent || "")) {
      line.textContent =
        "Sailed: 0, Discards: 0, To count: 0, Entries: 3, Scoring system: Portsmouth Yardstick (PY)";
    }
    paintPublicFleetTable(sec);
  }

  function placeOpenFleetHeader() {
    var host = document.getElementById("midmar-live-media");
    if (!host || !host.parentNode) return;
    dropDuplicateFleetHeaders();
    var sec = document.querySelector(
      '.fleet-section[data-block-id="' + RID + ':open"] table.fleet-results-table'
    );
    sec = sec ? sec.closest(".fleet-section") : null;
    if (!sec) return;
    sec.id = "dam-bottle-open-fleet";
    sec.setAttribute("data-fleet-label", "Open");
    paintOpenFleetHeader(sec);
    if (sec.previousSibling !== host) host.parentNode.insertBefore(sec, host.nextSibling);
  }

  function syncDartStack() {
    var header = document.querySelector(".regatta-header-wrap");
    var host = document.getElementById("midmar-live-media");
    var lb = document.getElementById("midmar-leaderboard");
    var wx = document.getElementById("ssa-regatta-slot-card");
    if (header && host && host.parentNode && host.previousSibling !== header) {
      header.parentNode.insertBefore(host, header.nextSibling);
    }
    if (host && lb) {
      if (lb.parentNode !== host) host.insertBefore(lb, host.firstChild);
      if (wx && wx.parentNode === host && lb.nextSibling !== wx) host.insertBefore(lb, wx);
    }
    placeOpenFleetHeader();
  }

  function watchR1Close() {
    var sec = document.getElementById("dam-bottle-open-fleet");
    if (!sec || sec._dbsR1Bound) return;
    var th = sec.querySelector('th.race-col[data-race-key="R1"]');
    if (!th) return;
    sec._dbsR1Bound = true;
    th.addEventListener("click", function () {
      window.setTimeout(function () {
        syncR1Closed(sec);
      }, 0);
    });
  }

  function add(src) {
    var base = src.split("?")[0];
    if (document.querySelector('script[src*="' + base + '"]')) return;
    var s = document.createElement("script");
    s.src = src;
    s.defer = true;
    document.head.appendChild(s);
  }
  /* Same as Dart: live-media boots first and then loads leaderboard into the host. */
  add("/js/midmar-live-media.js?v=midmarwx60dbs3");
  add("/js/club-score-edit.js?v=ccr38dbs4");

  syncDartStack();
  watchR1Close();
  [50, 200, 600, 1200, 2500].forEach(function (ms) {
    window.setTimeout(function () {
      syncDartStack();
      watchR1Close();
      var table = document.querySelector(
        '.fleet-section[data-block-id="' + RID + ':open"] table.fleet-results-table'
      );
      if (table && adminEditOn()) applyCorrection(table, true, true);
    }, ms);
  });
  if (window.MutationObserver && page) {
    var obs = new MutationObserver(function () {
      if (
        document.activeElement &&
        document.activeElement.classList &&
        document.activeElement.classList.contains("dam-bottle-et-input")
      )
        return;
      syncDartStack();
      watchR1Close();
    });
    obs.observe(page, { childList: true, subtree: true, attributes: true, attributeFilter: ["class"] });
    window.setTimeout(function () {
      try {
        obs.disconnect();
      } catch (e) {}
    }, 8000);
    if (!page._dbsScoreObs) {
      var scoreObs = new MutationObserver(function () {
        var sec = document.getElementById("dam-bottle-open-fleet");
        if (!sec) return;
        lockR1(sec.querySelector("table.fleet-results-table"));
        wireEtInputs(sec.querySelector("table.fleet-results-table"));
        syncR1Closed(sec);
      });
      scoreObs.observe(page, { attributes: true, attributeFilter: ["class"] });
      page._dbsScoreObs = scoreObs;
    }
  }
})();
