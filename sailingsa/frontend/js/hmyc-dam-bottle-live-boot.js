/**
 * Dam Bottle Sprints — each race has its own ET + ✓ + R.
 * Click that R header to show/hide its ET/✓. R+ adds a race block. R- drops the last.
 * Admin types ET only. No observers. Does not change live api.py.
 */
(function () {
  "use strict";
  var RID = "2026-10-10-hmyc-dam-bottle-sprints";
  var ET_KEY = "ssa-dam-bottle-et";
  var SRC = "/artwork/Event%20Logo/Dam-Bottle-Sprints.png";
  var path = String((window.location && window.location.pathname) || "")
    .replace(/\/+$/, "")
    .toLowerCase();
  if (path !== "/regatta/" + RID && path.indexOf("/regatta/" + RID + "/") !== 0) return;

  var page = document.querySelector(".regatta-page");
  if (page) {
    page.setAttribute("data-hmyc-live", "1");
    page.setAttribute("data-club-live-cards", "HMYC");
  }

  if (!document.getElementById("dam-bottle-score-css")) {
    var css = document.createElement("style");
    css.id = "dam-bottle-score-css";
    css.textContent =
      ".regatta-page > .midmar-live-media .mm-lipton-reels[data-regatta-id^='" + RID + "'] .mm-lipton-reels-brand{display:block!important;cursor:pointer;flex:0 0 auto;}" +
      ".regatta-page > .midmar-live-media .mm-lipton-reels[data-regatta-id^='" + RID + "'] .mm-lipton-reels-brand img{display:block!important;width:100%!important;height:100%!important;object-fit:contain!important;}" +
      ".regatta-page > .midmar-live-media .mm-lipton-reels[data-regatta-id^='" + RID + "'] .mm-lipton-reels-compact{display:flex!important;}" +
      ".regatta-page > .midmar-live-media .mm-lipton-reels[data-regatta-id^='" + RID + "'] .mm-lipton-reels-expanded," +
      ".regatta-page > .midmar-live-media .mm-lipton-reels[data-regatta-id^='" + RID + "'] [data-mm-expanded]{display:none!important;height:0!important;overflow:hidden!important;}" +
      ".regatta-page--club-score-edit .fleet-section[data-block-id='" + RID + ":open'] .club-race-step," +
      ".regatta-page--super-admin-edit .fleet-section[data-block-id='" + RID + ":open'] .club-race-step{display:flex!important;visibility:visible!important;}" +
      ".fleet-section[data-block-id='" + RID + ":open'] th.dam-bottle-corr-col," +
      ".fleet-section[data-block-id='" + RID + ":open'] td.dam-bottle-corr-col{text-align:center;min-width:4.4rem;color:#15803d;font-weight:700;font-variant-numeric:tabular-nums;}" +
      ".fleet-section[data-block-id='" + RID + ":open'] th.dam-bottle-corr-col .event-result-yes{color:#15803d;font-weight:700;font-size:1.05rem;}" +
      ".fleet-section[data-block-id='" + RID + ":open'] .dam-bottle-et-input{width:5.6rem;text-align:center;font:inherit;border:1px solid #94a3b8;border-radius:4px;padding:2px 5px;}" +
      ".fleet-section[data-block-id='" + RID + ":open'] td.race-col input," +
      ".fleet-section[data-block-id='" + RID + ":open'] td.race-col .club-score-input," +
      ".fleet-section[data-block-id='" + RID + ":open'] td.race-col .wc-result-field-input{display:none!important;}" +
      ".regatta-page:not(.regatta-page--club-score-edit):not(.regatta-page--super-admin-edit) " +
      ".fleet-section[data-block-id='" + RID + ":open'] .dam-bottle-py-col," +
      ".regatta-page:not(.regatta-page--club-score-edit):not(.regatta-page--super-admin-edit) " +
      ".fleet-section[data-block-id='" + RID + ":open'] .dam-bottle-et-col," +
      ".regatta-page:not(.regatta-page--club-score-edit):not(.regatta-page--super-admin-edit) " +
      ".fleet-section[data-block-id='" + RID + ":open'] .dam-bottle-corr-col{display:none!important}" +
      ".fleet-section[data-block-id='" + RID + ":open'] .dam-bottle-et-hidden{display:none!important}" +
      ".fleet-section[data-block-id='" + RID + ":open'] td.total-col," +
      ".fleet-section[data-block-id='" + RID + ":open'] td.nett-col{min-width:2.4rem;text-align:center;font-weight:700;}";
    document.head.appendChild(css);
  }

  function adminEditOn() {
    return !!(
      page &&
      (page.classList.contains("regatta-page--club-score-edit") ||
        page.classList.contains("regatta-page--super-admin-edit"))
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

  function loadEtStore() {
    var raw;
    try {
      raw = JSON.parse(localStorage.getItem(ET_KEY) || "{}") || {};
    } catch (e1) {
      raw = {};
    }
    var keys = Object.keys(raw);
    if (!keys.length) return {};
    if (keys.some(function (k) { return /^R\d+$/.test(k); })) return raw;
    return { R1: raw };
  }

  function saveEtValue(race, rid, val) {
    if (!race || !rid) return;
    var s = loadEtStore();
    if (!s[race]) s[race] = {};
    val = String(val || "").trim();
    if (val) s[race][String(rid)] = val;
    else delete s[race][String(rid)];
    try {
      localStorage.setItem(ET_KEY, JSON.stringify(s));
    } catch (e2) {}
  }

  function clearEtRace(race) {
    var s = loadEtStore();
    delete s[race];
    try {
      localStorage.setItem(ET_KEY, JSON.stringify(s));
    } catch (e2) {}
  }

  function etFor(race, rid) {
    var s = loadEtStore();
    return String((s[race] && s[race][String(rid)]) || "").trim();
  }

  function parseET(raw) {
    var s = String(raw || "").trim();
    if (!s) return null;
    if (/^\d+(\.\d+)?$/.test(s)) {
      var n = parseFloat(s);
      return n > 0 ? n : null;
    }
    var parts = s.split(":");
    if (parts.length === 2) {
      var min = parseInt(parts[0], 10);
      var sec = parseFloat(parts[1]);
      if (!isFinite(min) || min < 0 || !isFinite(sec) || sec < 0 || sec >= 60) return null;
      return min * 60 + sec;
    }
    if (parts.length === 3) {
      var hr = parseInt(parts[0], 10);
      var min2 = parseInt(parts[1], 10);
      var sec2 = parseFloat(parts[2]);
      if (!isFinite(hr) || hr < 0 || !isFinite(min2) || min2 < 0 || min2 >= 60 || !isFinite(sec2) || sec2 < 0 || sec2 >= 60)
        return null;
      return hr * 3600 + min2 * 60 + sec2;
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

  function rankLabel(n) {
    n = parseInt(n, 10);
    if (!isFinite(n) || n < 1) return "";
    if (n === 1) return "1st";
    if (n === 2) return "2nd";
    if (n === 3) return "3rd";
    return String(n) + "th";
  }

  function raceKeyOf(el) {
    var k = String((el && (el.getAttribute("data-race-key") || el.getAttribute("data-for-race") || el.textContent)) || "")
      .replace(/\s+/g, "")
      .toUpperCase();
    var m = k.match(/^(R\d+)/);
    return m ? m[1] : "";
  }

  function raceKeys(table) {
    var keys = [];
    if (!table) return keys;
    table.querySelectorAll("thead th.race-col, thead th[data-for-race], thead th[data-race-key]").forEach(function (th) {
      var k = raceKeyOf(th) || String(th.getAttribute("data-for-race") || "");
      if (/^R\d+$/.test(k) && keys.indexOf(k) < 0) keys.push(k);
    });
    keys.sort(function (a, b) {
      return parseInt(a.slice(1), 10) - parseInt(b.slice(1), 10);
    });
    return keys;
  }

  function raceCount(table) {
    var n = 0;
    raceKeys(table).forEach(function (k) {
      n = Math.max(n, parseInt(k.slice(1), 10) || 0);
    });
    return n;
  }

  function sessionPatchRace(rid, race, value) {
    return fetch(withSession("/api/result/" + encodeURIComponent(rid) + "/race"), {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ race: race, value: value, session: sessionToken() }),
    }).then(function (r) {
      return r.json().then(function (j) {
        return { ok: r.ok, j: j };
      });
    });
  }

  function sessionPatchFleet(rid, delta) {
    return fetch(withSession("/api/result/" + encodeURIComponent(rid) + "/fleet-races"), {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ delta: delta, session: sessionToken() }),
    }).then(function (r) {
      return r.json().then(function () {
        return r.ok;
      });
    }).catch(function () {
      return false;
    });
  }

  function markCol(table, label, className) {
    var ths = table.querySelectorAll("thead th");
    var i;
    for (i = 0; i < ths.length; i++) {
      if (String(ths[i].textContent || "").replace(/\s+/g, " ").trim() === label) {
        ths[i].classList.add(className);
        table.querySelectorAll("tbody tr").forEach(function (tr) {
          if (tr.children[i]) tr.children[i].classList.add(className);
        });
        return i;
      }
    }
    return -1;
  }

  function insertBeforeAnchor(row, node, anchor) {
    if (!row || !node) return;
    if (anchor) row.insertBefore(node, anchor);
    else row.appendChild(node);
  }

  function totalAnchor(row) {
    return row && row.querySelector("th.total-col, td.total-col, th.nett-col, td.nett-col");
  }

  function lockRCells(table) {
    if (!table) return;
    table.querySelectorAll("th.race-col, td.race-col").forEach(function (el) {
      if (!raceKeyOf(el)) return;
      el.setAttribute("data-auto-from-et", "1");
      el.classList.add("race-col--auto");
    });
    table.querySelectorAll("td.race-col input, td.race-col .club-score-input, td.race-col .wc-result-field-input").forEach(function (inp) {
      var td = inp.parentNode;
      var v = String(inp.value || "").trim();
      if (inp.parentNode) inp.parentNode.removeChild(inp);
      if (td && !String(td.textContent || "").trim() && v) td.textContent = v;
    });
  }

  function removeColAt(table, idx) {
    var thead = table.querySelector("thead tr");
    if (!thead || idx < 0 || !thead.children[idx]) return;
    thead.removeChild(thead.children[idx]);
    table.querySelectorAll("tbody tr").forEach(function (tr) {
      if (tr.children[idx]) tr.removeChild(tr.children[idx]);
    });
  }

  function dropRaceBlock(table, key) {
    if (!table || !key) return;
    var thead = table.querySelector("thead tr");
    if (!thead) return;
    var doomed = [];
    [].forEach.call(thead.children, function (th, i) {
      var forRace = th.getAttribute("data-for-race") || raceKeyOf(th);
      if (forRace === key) doomed.push(i);
    });
    doomed.sort(function (a, b) { return b - a; });
    doomed.forEach(function (i) {
      removeColAt(table, i);
    });
    clearEtRace(key);
    if (adminEditOn() && sessionToken()) {
      table.querySelectorAll("tbody tr[data-result-id]").forEach(function (tr) {
        sessionPatchRace(tr.getAttribute("data-result-id"), key, "");
      });
    }
  }

  function ensurePairAndRace(table, n) {
    if (!table || n < 1) return;
    var key = "R" + n;
    var thead = table.querySelector("thead tr");
    if (!thead) return;
    function has(sel) {
      return !!table.querySelector(sel);
    }
    if (!has('th.dam-bottle-et-col[data-for-race="' + key + '"]')) {
      var etTh = document.createElement("th");
      etTh.className = "dam-bottle-et-col";
      etTh.setAttribute("data-for-race", key);
      etTh.textContent = "ET";
      insertBeforeAnchor(thead, etTh, totalAnchor(thead));
      table.querySelectorAll("tbody tr").forEach(function (tr) {
        var td = document.createElement("td");
        td.className = "dam-bottle-et-col";
        td.setAttribute("data-for-race", key);
        insertBeforeAnchor(tr, td, totalAnchor(tr));
      });
    }
    if (!has('th.dam-bottle-corr-col[data-for-race="' + key + '"]')) {
      var cTh = document.createElement("th");
      cTh.className = "dam-bottle-corr-col";
      cTh.setAttribute("data-for-race", key);
      cTh.innerHTML = '<span class="event-result-yes" title="Corrected = ET × 1000 ÷ PY">✓</span>';
      insertBeforeAnchor(thead, cTh, totalAnchor(thead));
      table.querySelectorAll("tbody tr").forEach(function (tr) {
        var td = document.createElement("td");
        td.className = "dam-bottle-corr-col";
        td.setAttribute("data-for-race", key);
        insertBeforeAnchor(tr, td, totalAnchor(tr));
      });
    }
    if (!has('th.race-col[data-race-key="' + key + '"]')) {
      var rTh = document.createElement("th");
      rTh.className = "race-col race-col--wait";
      rTh.setAttribute("data-race-key", key);
      rTh.textContent = key;
      insertBeforeAnchor(thead, rTh, totalAnchor(thead));
      table.querySelectorAll("tbody tr[data-result-id]").forEach(function (tr) {
        var td = document.createElement("td");
        td.className = "race-col race-col--wait";
        td.setAttribute("data-race-key", key);
        insertBeforeAnchor(tr, td, totalAnchor(tr));
      });
    }
    lockRCells(table);
  }

  function keepOneLabeled(table, cls, label) {
    var thead = table.querySelector("thead tr");
    if (!thead) return;
    var hits = [].filter.call(thead.children, function (th) {
      return th.classList.contains(cls) || String(th.textContent || "").trim() === label;
    });
    var i;
    for (i = hits.length - 1; i >= 1; i--) {
      removeColAt(table, [].indexOf.call(thead.children, hits[i]));
    }
    if (hits[0]) {
      hits[0].classList.add(cls);
      var idx = [].indexOf.call(thead.children, hits[0]);
      table.querySelectorAll("tbody tr").forEach(function (tr) {
        if (tr.children[idx]) tr.children[idx].classList.add(cls);
      });
      return;
    }
    var th = document.createElement("th");
    th.className = cls;
    th.textContent = label;
    thead.appendChild(th);
    table.querySelectorAll("tbody tr").forEach(function (tr) {
      var td = document.createElement("td");
      td.className = cls;
      tr.appendChild(td);
    });
  }

  function colKind(el) {
    if (!el) return "x-other";
    if (el.classList.contains("rank-col")) return "a-rank";
    if (el.classList.contains("class-col")) return "b-class";
    if (el.classList.contains("sail-col")) return "c-sail";
    if (el.classList.contains("club-col")) return "d-club";
    if (el.classList.contains("helm-col")) return "e-helm";
    if (el.classList.contains("crew-col")) return "f-crew";
    if (el.classList.contains("dam-bottle-cat-col") || String(el.textContent || "").trim() === "Cat") return "g-cat";
    if (el.classList.contains("dam-bottle-py-col") || String(el.textContent || "").trim() === "PY") return "h-py";
    var race = el.getAttribute("data-for-race") || raceKeyOf(el);
    var n = race ? ("000" + race.replace("R", "")).slice(-3) : "999";
    if (el.classList.contains("dam-bottle-et-col")) return "k-" + n + "-1-et";
    if (el.classList.contains("dam-bottle-corr-col")) return "k-" + n + "-2-corr";
    if (el.classList.contains("race-col")) return "k-" + n + "-3-r";
    if (el.classList.contains("total-col") || String(el.textContent || "").trim() === "Total") return "y-total";
    if (el.classList.contains("nett-col") || String(el.textContent || "").trim() === "Nett") return "z-nett";
    return "x-other";
  }

  function orderCols(table) {
    var thead = table && table.querySelector("thead tr");
    if (!thead) return;
    if (document.activeElement && document.activeElement.classList.contains("dam-bottle-et-input")) return;
    var ths = [].slice.call(thead.children);
    var order = ths.map(function (th, i) {
      return { th: th, i: i, k: colKind(th) };
    });
    order.sort(function (a, b) {
      if (a.k === b.k) return a.i - b.i;
      return a.k < b.k ? -1 : 1;
    });
    if (order.every(function (o, idx) { return thead.children[idx] === o.th; })) return;
    order.forEach(function (o) { thead.appendChild(o.th); });
    table.querySelectorAll("tbody tr").forEach(function (tr) {
      var cells = [].slice.call(tr.children);
      order.forEach(function (o) {
        if (cells[o.i]) tr.appendChild(cells[o.i]);
      });
    });
  }

  function dropOrphanAndDup(table) {
    var thead = table.querySelector("thead tr");
    if (!thead) return;
    var seen = { et: {}, corr: {}, r: {} };
    var keys = {};
    [].slice.call(thead.children).forEach(function (th) {
      if (th.classList.contains("race-col")) {
        var k = raceKeyOf(th);
        if (k) keys[k] = true;
      }
    });
    [].slice.call(thead.children).reverse().forEach(function (th) {
      var race = th.getAttribute("data-for-race") || raceKeyOf(th);
      var idx = [].indexOf.call(thead.children, th);
      var bag = th.classList.contains("dam-bottle-et-col")
        ? "et"
        : th.classList.contains("dam-bottle-corr-col")
          ? "corr"
          : th.classList.contains("race-col")
            ? "r"
            : "";
      if (!bag) return;
      if (!race || !keys[race] && bag !== "r") {
        removeColAt(table, idx);
        return;
      }
      if (seen[bag][race]) {
        removeColAt(table, idx);
        return;
      }
      seen[bag][race] = true;
    });
  }

  function fillTotalNett(tr) {
    var sum = 0;
    var n = 0;
    tr.querySelectorAll("td.race-col").forEach(function (td) {
      var v = parseInt(String(td.textContent || "").replace(/[^\d]/g, ""), 10);
      if (isFinite(v) && v > 0) {
        sum += v;
        n += 1;
      }
    });
    var txt = n ? String(sum) : "";
    var tot = tr.querySelector("td.total-col");
    var nett = tr.querySelector("td.nett-col");
    if (tot) {
      tot.classList.remove("strike-out");
      tot.textContent = txt;
    }
    if (nett) {
      nett.classList.remove("strike-out");
      nett.textContent = txt;
    }
  }

  function rowPy(tr) {
    var td = tr.querySelector("td.dam-bottle-py-col");
    var n = parseFloat(String((td && td.textContent) || "").replace(/[^\d.]/g, ""));
    return isFinite(n) && n > 0 ? n : null;
  }

  function etRaw(tr, race) {
    var td = tr.querySelector('td.dam-bottle-et-col[data-for-race="' + race + '"]');
    if (!td) return "";
    var inp = td.querySelector(".dam-bottle-et-input");
    if (inp) return String(inp.value || "").trim();
    return String(td.getAttribute("data-et") || "").trim();
  }

  var saveChain = Promise.resolve();
  var lastSaved = {};

  function persistPlaces(table, race, items) {
    if (!adminEditOn() || !sessionToken() || !race) return;
    var last = lastSaved[race] || {};
    var next = {};
    items.forEach(function (it) {
      next[it.rid] = it.place ? String(it.place) : "";
    });
    var changing = items.filter(function (it) {
      return String(last[it.rid] || "") !== String(next[it.rid] || "");
    });
    if (!changing.length) {
      lastSaved[race] = next;
      return;
    }
    saveChain = saveChain
      .then(function () {
        var seq = Promise.resolve();
        changing.forEach(function (it) {
          if (!last[it.rid]) return;
          seq = seq.then(function () { return sessionPatchRace(it.rid, race, ""); });
        });
        return seq;
      })
      .then(function () {
        var seq = Promise.resolve();
        changing.forEach(function (it) {
          if (!it.place) return;
          seq = seq.then(function () { return sessionPatchRace(it.rid, race, String(it.place)); });
        });
        return seq;
      })
      .then(function () {
        lastSaved[race] = next;
      })
      .catch(function () {});
  }

  function applyRace(table, race, doSave) {
    if (!table || !race) return;
    lockRCells(table);
    var items = [];
    table.querySelectorAll("tbody tr[data-result-id]").forEach(function (tr, idx) {
      var py = rowPy(tr);
      var etSec = parseET(etRaw(tr, race));
      items.push({
        tr: tr,
        rid: tr.getAttribute("data-result-id"),
        corr: py && etSec != null ? (etSec * 1000) / py : null,
        idx: idx,
      });
    });
    var ranked = items.filter(function (it) { return it.corr != null; });
    ranked.sort(function (a, b) {
      if (a.corr !== b.corr) return a.corr - b.corr;
      return a.idx - b.idx;
    });
    ranked.forEach(function (it, i) { it.place = i + 1; });
    items.forEach(function (it) {
      var corrTd = it.tr.querySelector('td.dam-bottle-corr-col[data-for-race="' + race + '"]');
      var rTd = it.tr.querySelector('td.race-col[data-race-key="' + race + '"]');
      var shown = it.corr != null ? formatCorrected(it.corr) : "";
      if (corrTd && corrTd.textContent !== shown) corrTd.textContent = shown;
      if (rTd) {
        var p = it.place ? String(it.place) : "";
        if (rTd.textContent !== p) rTd.textContent = p;
      }
      fillTotalNett(it.tr);
    });
    if (doSave) persistPlaces(table, race, items);
  }

  function applyAllRaces(table, doSave) {
    raceKeys(table).forEach(function (race) {
      applyRace(table, race, doSave);
    });
    var first = table.querySelector("tbody tr[data-result-id] td.rank-col");
    if (!first) return;
    var rows = [].map.call(table.querySelectorAll("tbody tr[data-result-id]"), function (tr, idx) {
      var nett = parseInt(String((tr.querySelector("td.nett-col") && tr.querySelector("td.nett-col").textContent) || "9999"), 10);
      return { tr: tr, nett: isFinite(nett) ? nett : 9999, idx: idx };
    });
    rows.sort(function (a, b) { return a.nett - b.nett || a.idx - b.idx; });
    rows.forEach(function (it, i) {
      var rankTd = it.tr.querySelector("td.rank-col");
      var place = it.nett < 9999 ? i + 1 : 0;
      if (rankTd) rankTd.textContent = place ? rankLabel(place) : "";
    });
  }

  function wireEtInputs(table) {
    if (!table || !adminEditOn()) return;
    table.querySelectorAll("td.dam-bottle-et-col").forEach(function (td) {
      var race = td.getAttribute("data-for-race");
      var tr = td.closest("tr");
      if (!race || !tr) return;
      var rid = tr.getAttribute("data-result-id");
      var kept = etFor(race, rid);
      var existing = td.querySelector(".dam-bottle-et-input");
      if (existing) {
        if (document.activeElement !== existing && String(existing.value || "") !== kept && !String(existing.value || "").trim()) {
          existing.value = kept;
        }
        return;
      }
      var inp = document.createElement("input");
      inp.type = "text";
      inp.className = "dam-bottle-et-input";
      inp.setAttribute("placeholder", "m:ss");
      inp.setAttribute("aria-label", race + " elapsed time");
      inp.value = kept;
      td.setAttribute("data-et", kept);
      td.textContent = "";
      td.appendChild(inp);
      inp.addEventListener("input", function () {
        td.setAttribute("data-et", String(inp.value || "").trim());
        saveEtValue(race, rid, inp.value);
        applyRace(table, race, false);
      });
      inp.addEventListener("blur", function () {
        saveEtValue(race, rid, inp.value);
        applyRace(table, race, true);
        applyAllRaces(table, false);
      });
      inp.addEventListener("keydown", function (ev) {
        if (ev.key === "Enter") {
          ev.preventDefault();
          inp.blur();
        }
      });
    });
  }

  function syncEtVisible(sec) {
    var table = sec && sec.querySelector("table.fleet-results-table");
    if (!table) return;
    raceKeys(table).forEach(function (key) {
      var th = table.querySelector('th.race-col[data-race-key="' + key + '"]');
      var closed = !!(th && th.classList.contains("race-col--closed"));
      table.querySelectorAll('[data-for-race="' + key + '"]').forEach(function (el) {
        if (el.classList.contains("race-col")) return;
        el.classList.toggle("dam-bottle-et-hidden", closed);
      });
    });
  }

  function findSec() {
    var table = document.querySelector(
      '.fleet-section[data-block-id="' + RID + ':open"] table.fleet-results-table'
    );
    return table ? table.closest(".fleet-section") : null;
  }

  function placeStack() {
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
    var sec = findSec();
    if (host && host.parentNode && sec && sec.previousSibling !== host) {
      host.parentNode.insertBefore(sec, host.nextSibling);
    }
  }

  function addRace(table) {
    ensurePairAndRace(table, raceCount(table) + 1);
    orderCols(table);
    lockRCells(table);
    wireEtInputs(table);
    var ridEl = table.querySelector("tr[data-result-id]");
    if (ridEl && sessionToken()) sessionPatchFleet(ridEl.getAttribute("data-result-id"), 1);
  }

  function removeLastRace(table) {
    var n = raceCount(table);
    if (n >= 2) {
      dropRaceBlock(table, "R" + n);
    } else {
      dropRaceBlock(table, "R1");
      ensurePairAndRace(table, 1);
    }
    orderCols(table);
    lockRCells(table);
    table.querySelectorAll("tbody tr[data-result-id]").forEach(fillTotalNett);
    applyAllRaces(table, false);
    var ridEl = table.querySelector("tr[data-result-id]");
    if (ridEl && sessionToken() && n >= 2) sessionPatchFleet(ridEl.getAttribute("data-result-id"), -1);
  }

  function paint() {
    var sec = findSec();
    if (!sec) return;
    sec.id = "dam-bottle-open-fleet";
    sec.querySelectorAll(".class-header-logo-col img, .fleet-title-with-logo img").forEach(function (img) {
      if (img.getAttribute("src") !== SRC) img.src = SRC;
      img.alt = "Dam Bottle Sprints";
      img.removeAttribute("title");
    });
    var title = sec.querySelector(".fleet-title-with-logo");
    if (title) {
      var hasText = false;
      Array.prototype.forEach.call(title.childNodes, function (n) {
        if (n.nodeType === 3) {
          if (n.nodeValue !== " Open Fleet") n.nodeValue = " Open Fleet";
          hasText = true;
        }
      });
      if (!hasText) title.appendChild(document.createTextNode(" Open Fleet"));
    }
    var table = sec.querySelector("table.fleet-results-table");
    if (!table) return;
    table.querySelectorAll("thead th").forEach(function (th) {
      if (String(th.textContent || "").trim() === "Age") th.textContent = "Cat";
    });
    markCol(table, "Cat", "dam-bottle-cat-col");
    if (markCol(table, "Crew", "crew-col") < 0) {
      var helm = table.querySelector("thead th.helm-col");
      if (helm) {
        var cth = document.createElement("th");
        cth.className = "crew-col";
        cth.textContent = "Crew";
        helm.parentNode.insertBefore(cth, helm.nextSibling);
        var hidx = [].indexOf.call(helm.parentNode.children, helm);
        table.querySelectorAll("tbody tr").forEach(function (tr) {
          var td = document.createElement("td");
          td.className = "crew-col";
          if (tr.children[hidx]) tr.insertBefore(td, tr.children[hidx].nextSibling);
          else tr.appendChild(td);
        });
      }
    }
    markCol(table, "PY", "dam-bottle-py-col");
    keepOneLabeled(table, "total-col", "Total");
    keepOneLabeled(table, "nett-col", "Nett");
    var existing = raceCount(table);
    if (existing < 1) existing = 1;
    var i;
    for (i = 1; i <= existing; i++) ensurePairAndRace(table, i);
    dropOrphanAndDup(table);
    orderCols(table);
    lockRCells(table);
    wireEtInputs(table);
    syncEtVisible(sec);
    applyAllRaces(table, false);
    bindUi(sec);
    placeStack();
  }

  function ensureRaceStepper(sec) {
    if (!adminEditOn() || !sec || sec.querySelector(".club-race-step")) return;
    var box = document.createElement("div");
    box.className = "club-race-step";
    box.setAttribute("role", "group");
    box.setAttribute("aria-label", "Add or remove race");
    var add = document.createElement("button");
    add.type = "button";
    add.className = "club-race-step-add";
    add.setAttribute("aria-label", "Add race");
    add.textContent = "R+";
    var sub = document.createElement("button");
    sub.type = "button";
    sub.className = "club-race-step-sub";
    sub.setAttribute("aria-label", "Remove last race");
    sub.title = "Remove last race";
    sub.textContent = "R\u2212";
    box.appendChild(add);
    box.appendChild(sub);
    var club = sec.querySelector(".class-header-club-logo-col");
    if (club) {
      club.insertBefore(box, club.firstChild);
      return;
    }
    var hdr = sec.querySelector(".class-header");
    var logo = hdr && hdr.querySelector(".class-header-logo-col");
    if (logo) hdr.insertBefore(box, logo);
    else if (hdr) hdr.insertBefore(box, hdr.firstChild);
  }

  function bindUi(sec) {
    if (!sec) return;
    var table = sec.querySelector("table.fleet-results-table");
    ensureRaceStepper(sec);
    sec.querySelectorAll("th.race-col").forEach(function (th) {
      if (th._dbsEtBound) return;
      th._dbsEtBound = true;
      th.addEventListener("click", function () {
        window.setTimeout(function () {
          lockRCells(table);
          syncEtVisible(sec);
        }, 0);
      });
    });
    if (sec._dbsStepCapture) return;
    sec._dbsStepCapture = true;
    sec.addEventListener(
      "click",
      function (ev) {
        var t = ev.target;
        if (!t || !t.closest) return;
        var add = t.closest(".club-race-step-add");
        var sub = t.closest(".club-race-step-sub");
        if (!add && !sub) return;
        ev.preventDefault();
        ev.stopImmediatePropagation();
        var tbl = sec.querySelector("table.fleet-results-table");
        if (!tbl) return;
        if (add) addRace(tbl);
        else removeLastRace(tbl);
        syncEtVisible(sec);
        bindUi(sec);
      },
      true
    );
  }

  function add(src) {
    var base = src.split("?")[0];
    if (document.querySelector('script[src*="' + base + '"]')) return;
    var s = document.createElement("script");
    s.src = src;
    s.defer = true;
    document.head.appendChild(s);
  }

  paint();
  add("/js/midmar-live-media.js?v=midmarwx60dbs3");
  add("/js/club-score-edit.js?v=ccr38dbs4");
  [80, 250, 700, 1600, 3500].forEach(function (ms) {
    window.setTimeout(paint, ms);
  });
})();
