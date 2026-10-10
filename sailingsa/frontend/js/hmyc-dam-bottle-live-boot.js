/**
 * Dam Bottle Sprints — Bottle logos, Open Fleet, R+/R−.
 * Admin edits ET only. ✓ = ET × 1000 ÷ PY. R place is not typed.
 * Click race: closed hides ET + ✓; open shows them again.
 * No observers. Does not change live api.py.
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
      ".regatta-page--club-score-edit .fleet-section[data-block-id='" + RID + ":open'] .club-race-step," +
      ".regatta-page--super-admin-edit .fleet-section[data-block-id='" + RID + ":open'] .club-race-step{" +
      "display:flex!important;visibility:visible!important;}" +
      ".fleet-section[data-block-id='" + RID + ":open'] th.dam-bottle-corr-col," +
      ".fleet-section[data-block-id='" + RID + ":open'] td.dam-bottle-corr-col{" +
      "text-align:center;min-width:4.4rem;color:#15803d;font-weight:700;font-variant-numeric:tabular-nums;}" +
      ".fleet-section[data-block-id='" + RID + ":open'] th.dam-bottle-corr-col .event-result-yes{" +
      "color:#15803d;font-weight:700;font-size:1.05rem;}" +
      ".fleet-section[data-block-id='" + RID + ":open'] .dam-bottle-et-input{" +
      "width:5.6rem;text-align:center;font:inherit;border:1px solid #94a3b8;border-radius:4px;padding:2px 5px;}" +
      ".fleet-section[data-block-id='" + RID + ":open'] td.race-col input," +
      ".fleet-section[data-block-id='" + RID + ":open'] td.race-col .club-score-input," +
      ".fleet-section[data-block-id='" + RID + ":open'] td.race-col .wc-result-field-input{" +
      "display:none!important;}" +
      ".regatta-page:not(.regatta-page--club-score-edit):not(.regatta-page--super-admin-edit) " +
      ".fleet-section[data-block-id='" + RID + ":open'] .dam-bottle-py-col," +
      ".regatta-page:not(.regatta-page--club-score-edit):not(.regatta-page--super-admin-edit) " +
      ".fleet-section[data-block-id='" + RID + ":open'] .dam-bottle-et-col," +
      ".regatta-page:not(.regatta-page--club-score-edit):not(.regatta-page--super-admin-edit) " +
      ".fleet-section[data-block-id='" + RID + ":open'] .dam-bottle-corr-col{display:none!important}" +
      ".fleet-section[data-block-id='" + RID + ":open'].fleet-section--et-hidden .dam-bottle-et-col," +
      ".fleet-section[data-block-id='" + RID + ":open'].fleet-section--et-hidden .dam-bottle-corr-col{display:none!important}";
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
    var k = String((el && (el.getAttribute("data-race-key") || el.textContent)) || "")
      .replace(/\s+/g, "")
      .toUpperCase();
    var m = k.match(/^(R\d+)/);
    return m ? m[1] : "";
  }

  function raceKeys(table) {
    var keys = [];
    if (!table) return keys;
    table.querySelectorAll("thead th.race-col").forEach(function (th) {
      var k = raceKeyOf(th);
      if (k && keys.indexOf(k) < 0) keys.push(k);
    });
    return keys;
  }

  function openRaceKey(table) {
    var keys = raceKeys(table);
    if (!keys.length) return adminEditOn() ? "R1" : "";
    var wait = [];
    var i;
    var th;
    for (i = 0; i < keys.length; i++) {
      th = table.querySelector('th.race-col[data-race-key="' + keys[i] + '"]');
      if (th && th.classList.contains("race-col--wait") && !th.classList.contains("race-col--closed")) {
        wait.push(keys[i]);
      }
    }
    if (wait.length) return wait[wait.length - 1];
    if (!adminEditOn()) return "";
    for (i = 0; i < keys.length; i++) {
      th = table.querySelector('th.race-col[data-race-key="' + keys[i] + '"]');
      if (th && th.classList.contains("race-col--closed")) return "";
    }
    return keys[keys.length - 1];
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

  function insertAfter(parent, newNode, afterNode) {
    if (!parent || !newNode) return;
    if (afterNode && afterNode.nextSibling) parent.insertBefore(newNode, afterNode.nextSibling);
    else parent.appendChild(newNode);
  }

  function ensureColAfter(table, afterLabel, label, className) {
    if (markCol(table, label, className) >= 0) return;
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
      insertAfter(tr, td, tr.children[after]);
    });
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

  function ensureR1(table) {
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
    lockRCells(table);
  }

  function ensureTickCol(table) {
    var etTh = null;
    table.querySelectorAll("thead th").forEach(function (th) {
      if (String(th.textContent || "").replace(/\s+/g, " ").trim() === "ET") etTh = th;
    });
    if (!etTh || table.querySelector("th.dam-bottle-corr-col")) {
      table.querySelectorAll("td.dam-bottle-corr-col .event-result-yes").forEach(function (n) {
        if (n.parentNode) n.parentNode.removeChild(n);
      });
      return;
    }
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

  var saveChain = Promise.resolve();
  var lastSavedByRace = {};

  function persistPlaces(items, race) {
    if (!race || !adminEditOn() || !sessionToken()) return;
    var last = lastSavedByRace[race] || {};
    var next = {};
    items.forEach(function (it) {
      next[it.rid] = it.place ? String(it.place) : "";
    });
    var changing = items.filter(function (it) {
      return String(last[it.rid] || "") !== String(next[it.rid] || "");
    });
    if (!changing.length) {
      lastSavedByRace[race] = next;
      return;
    }
    function patch(rid, value) {
      return fetch(withSession("/api/result/" + encodeURIComponent(rid) + "/race"), {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ race: race, value: value, session: sessionToken() }),
      }).then(function (r) {
        return r.json().then(function (j) {
          if (!r.ok) throw new Error("save failed");
          return j;
        });
      });
    }
    saveChain = saveChain
      .then(function () {
        var seq = Promise.resolve();
        changing.forEach(function (it) {
          if (!last[it.rid]) return;
          seq = seq.then(function () { return patch(it.rid, ""); });
        });
        return seq;
      })
      .then(function () {
        var seq = Promise.resolve();
        changing.forEach(function (it) {
          if (!it.place) return;
          seq = seq.then(function () { return patch(it.rid, String(it.place)); });
        });
        return seq;
      })
      .then(function () {
        lastSavedByRace[race] = next;
      })
      .catch(function () {});
  }

  function applyCorrection(table, doSort, doSave) {
    if (!table) return;
    var race = openRaceKey(table);
    if (!race) return;
    lockRCells(table);
    var items = [];
    table.querySelectorAll("tbody tr[data-result-id]").forEach(function (tr, idx) {
      var py = rowPy(tr);
      var etSec = parseET(rowEtRaw(tr));
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
      var corrTd = it.tr.querySelector("td.dam-bottle-corr-col");
      var rTd = it.tr.querySelector('td.race-col[data-race-key="' + race + '"]');
      var rankTd = it.tr.querySelector("td.rank-col");
      var shown = it.corr != null ? formatCorrected(it.corr) : "";
      if (corrTd && corrTd.textContent !== shown) corrTd.textContent = shown;
      if (rTd) {
        var p = it.place ? String(it.place) : "";
        if (rTd.textContent !== p) rTd.textContent = p;
      }
      if (it.place && rankTd && rankTd.textContent !== rankLabel(it.place)) {
        rankTd.textContent = rankLabel(it.place);
      }
    });
    if (doSort) {
      var tb = table.tBodies && table.tBodies[0];
      if (tb) {
        items
          .slice()
          .sort(function (a, b) { return (a.place || 9999) - (b.place || 9999) || a.idx - b.idx; })
          .forEach(function (it) { tb.appendChild(it.tr); });
      }
    }
    if (doSave) persistPlaces(items, race);
  }

  function wireEtInputs(table) {
    if (!table) return;
    var race = openRaceKey(table) || "R1";
    var admin = adminEditOn();
    table.querySelectorAll("tbody tr[data-result-id]").forEach(function (tr) {
      var td = tr.querySelector("td.dam-bottle-et-col");
      if (!td) return;
      var rid = tr.getAttribute("data-result-id");
      var kept = etFor(race, rid);
      var existing = td.querySelector(".dam-bottle-et-input");
      if (!admin) {
        if (existing && existing.parentNode && document.activeElement !== existing) existing.parentNode.removeChild(existing);
        return;
      }
      if (existing) {
        if (document.activeElement !== existing && td.getAttribute("data-et-race") !== race) {
          existing.value = kept;
          td.setAttribute("data-et-race", race);
          td.setAttribute("data-et", kept);
        }
        return;
      }
      var inp = document.createElement("input");
      inp.type = "text";
      inp.className = "dam-bottle-et-input";
      inp.setAttribute("placeholder", "m:ss");
      inp.setAttribute("aria-label", "Elapsed time");
      inp.value = kept;
      td.setAttribute("data-et", kept);
      td.setAttribute("data-et-race", race);
      td.textContent = "";
      td.appendChild(inp);
      inp.addEventListener("input", function () {
        td.setAttribute("data-et", String(inp.value || "").trim());
        saveEtValue(openRaceKey(table) || race, rid, inp.value);
        applyCorrection(table, false, false);
      });
      inp.addEventListener("blur", function () {
        saveEtValue(openRaceKey(table) || race, rid, inp.value);
        applyCorrection(table, true, true);
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
    if (!sec) return;
    var table = sec.querySelector("table.fleet-results-table");
    var hide = !openRaceKey(table);
    if (sec.classList.contains("fleet-section--et-hidden") !== hide) {
      sec.classList.toggle("fleet-section--et-hidden", hide);
    }
  }

  function findSec() {
    var table = document.querySelector(
      '.fleet-section[data-block-id="' + RID + ':open"] table.fleet-results-table'
    );
    return table ? table.closest(".fleet-section") : null;
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
    ensureColAfter(table, "Helm", "Crew", "crew-col");
    markCol(table, "PY", "dam-bottle-py-col");
    ensureColAfter(table, "PY", "ET", "dam-bottle-et-col");
    ensureTickCol(table);
    ensureR1(table);
    lockRCells(table);
    wireEtInputs(table);
    syncEtVisible(sec);
    bindRaceClicks(sec);
    if (
      adminEditOn() &&
      !(document.activeElement && document.activeElement.classList.contains("dam-bottle-et-input"))
    ) {
      applyCorrection(table, false, false);
    }
  }

  function bindRaceClicks(sec) {
    if (!sec) return;
    var table = sec.querySelector("table.fleet-results-table");
    sec.querySelectorAll("th.race-col").forEach(function (th) {
      if (th._dbsEtBound) return;
      th._dbsEtBound = true;
      th.addEventListener("click", function () {
        window.setTimeout(function () {
          lockRCells(table);
          wireEtInputs(table);
          syncEtVisible(sec);
        }, 0);
      });
    });
    function afterStep() {
      window.setTimeout(function () {
        paint();
      }, 150);
    }
    var add = sec.querySelector(".club-race-step-add");
    var sub = sec.querySelector(".club-race-step-sub");
    if (add && !add._dbsBound) {
      add._dbsBound = true;
      add.addEventListener("click", afterStep);
    }
    if (sub && !sub._dbsBound) {
      sub._dbsBound = true;
      sub.addEventListener("click", afterStep);
    }
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
  add("/js/club-score-edit.js?v=ccr38dbs4");
  [80, 250, 700, 1600, 3000, 5000].forEach(function (ms) {
    window.setTimeout(paint, ms);
  });
})();
