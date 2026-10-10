/**
 * Dam Bottle Sprints — clone Dart Nationals event URL stack.
 * Order: event header → Leader Board → Wind → Media → Live Cam → Open Fleet.
 * Admin types ET only. ✓ cell = ET seconds × 1000 ÷ PY.
 * That result fills the open R column and sorts the fleet. R places are not typed.
 * Click a race closed: hide ET + ✓, leave R positions. R+ / R− stay in the header.
 * Next race from R+ shows ET + ✓ again, then that R place after calc.
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
      ".regatta-page--club-score-edit .fleet-section[data-block-id='" + RID + ":open'] .club-race-step," +
      ".regatta-page--super-admin-edit .fleet-section[data-block-id='" + RID + ":open'] .club-race-step{" +
      "display:flex!important;visibility:visible!important;}" +
      ".regatta-page:not(.regatta-page--club-score-edit):not(.regatta-page--super-admin-edit) " +
      ".fleet-section[data-block-id='" + RID + ":open'] .dam-bottle-py-col," +
      ".regatta-page:not(.regatta-page--club-score-edit):not(.regatta-page--super-admin-edit) " +
      ".fleet-section[data-block-id='" + RID + ":open'] .dam-bottle-et-col," +
      ".regatta-page:not(.regatta-page--club-score-edit):not(.regatta-page--super-admin-edit) " +
      ".fleet-section[data-block-id='" + RID + ":open'] .dam-bottle-corr-col{" +
      "display:none!important}" +
      ".fleet-section[data-block-id='" + RID + ":open'].fleet-section--et-hidden .dam-bottle-et-col," +
      ".fleet-section[data-block-id='" + RID + ":open'].fleet-section--et-hidden .dam-bottle-corr-col{" +
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

  function raceKeyOf(el) {
    if (!el) return "";
    var k = String(el.getAttribute("data-race-key") || el.textContent || "")
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
    lockAutoRaces(table);
  }

  function lockAutoRaces(table) {
    if (!table) return;
    table.querySelectorAll("th.race-col, td.race-col").forEach(function (el) {
      if (!raceKeyOf(el)) return;
      el.setAttribute("data-auto-from-et", "1");
      el.classList.add("race-col--auto");
    });
    table
      .querySelectorAll("td.race-col .club-score-input, td.race-col .wc-result-field-input")
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
    table.querySelectorAll("td.dam-bottle-corr-col .event-result-yes").forEach(function (tick) {
      if (tick.parentNode) tick.parentNode.removeChild(tick);
    });
  }

  function syncEtVisible(sec) {
    if (!sec) return;
    var table = sec.querySelector("table.fleet-results-table");
    var open = !!(table && openRaceKey(table));
    var hide = adminEditOn() ? !open : true;
    if (sec.classList.contains("fleet-section--et-hidden") !== hide) {
      sec.classList.toggle("fleet-section--et-hidden", hide);
    }
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

  function paintRowResult(tr, race, corrSec, place) {
    var corrTd = tr.querySelector("td.dam-bottle-corr-col");
    var rTd = race ? tr.querySelector('td.race-col[data-race-key="' + race + '"]') : null;
    var rankTd = tr.querySelector("td.rank-col") || tr.children[0];
    var py = rowPy(tr);
    var etSec = parseET(rowEtRaw(tr));
    if (corrTd) {
      var shown = corrSec != null ? formatCorrected(corrSec) : "";
      if (corrTd.textContent !== shown) corrTd.textContent = shown;
      if (corrSec != null) {
        corrTd.setAttribute("data-corr-sec", String(corrSec));
        if (etSec != null && py) {
          corrTd.title =
            String(etSec) + "s × 1000 ÷ " + String(py) + " = " + String(Math.round(corrSec * 10) / 10) + "s";
        }
      } else {
        corrTd.removeAttribute("data-corr-sec");
        corrTd.removeAttribute("title");
      }
    }
    if (rTd) {
      var placeTxt = place ? String(place) : "";
      if (rTd.textContent !== placeTxt) rTd.textContent = placeTxt;
    }
    var wantGold = place === 1;
    var wantSil = place === 2;
    var wantBro = place === 3;
    if (tr.classList.contains("medal-gold") !== wantGold) tr.classList.toggle("medal-gold", wantGold);
    if (tr.classList.contains("medal-silver") !== wantSil) tr.classList.toggle("medal-silver", wantSil);
    if (tr.classList.contains("medal-bronze") !== wantBro) tr.classList.toggle("medal-bronze", wantBro);
    if (place) {
      var placeStr = String(place);
      if (tr.getAttribute("data-official-rank") !== placeStr) tr.setAttribute("data-official-rank", placeStr);
      var lab = rankLabel(place);
      if (rankTd && rankTd.textContent !== lab) rankTd.textContent = lab;
    } else {
      if (tr.hasAttribute("data-official-rank")) tr.removeAttribute("data-official-rank");
      if (rankTd && rankTd.textContent) rankTd.textContent = "";
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
  var lastSavedByRace = {};

  function persistPlaces(items, race) {
    if (!race || !adminEditOn() || !sessionToken()) return;
    var lastSaved = lastSavedByRace[race] || {};
    var next = {};
    items.forEach(function (it) {
      next[it.rid] = it.place ? String(it.place) : "";
    });
    var changing = items.filter(function (it) {
      return String(lastSaved[it.rid] || "") !== String(next[it.rid] || "");
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
          if (!r.ok) throw new Error((j && j.detail) || "race save failed");
          return j;
        });
      });
    }
    saveChain = saveChain
      .then(function () {
        var seq = Promise.resolve();
        changing.forEach(function (it) {
          if (!lastSaved[it.rid]) return;
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
        lastSavedByRace[race] = next;
      })
      .catch(function () {});
  }

  function applyCorrection(table, doSort, doSave) {
    if (!table) return;
    var race = openRaceKey(table);
    if (!race) return;
    lockAutoRaces(table);
    var items = scoredRows(table);
    items.forEach(function (it) {
      paintRowResult(it.tr, race, it.corr, it.place || 0);
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
            if (it.tr.parentNode === tb && tb.lastElementChild === it.tr) return;
            tb.appendChild(it.tr);
          });
      }
    }
    if (doSave) persistPlaces(items, race);
  }

  function wireEtInputs(table) {
    if (!table) return;
    var admin = adminEditOn();
    var race = openRaceKey(table) || "R1";
    table.querySelectorAll("tbody tr[data-result-id]").forEach(function (tr) {
      var td = tr.querySelector("td.dam-bottle-et-col");
      if (!td) return;
      var rid = tr.getAttribute("data-result-id");
      var kept = etFor(race, rid) || String(td.getAttribute("data-et") || "").trim();
      if (td.getAttribute("data-et-race") !== race) {
        kept = etFor(race, rid);
        td.setAttribute("data-et-race", race);
      }
      var existing = td.querySelector(".dam-bottle-et-input");
      if (!admin) {
        if (existing && document.activeElement !== existing && existing.parentNode) {
          existing.parentNode.removeChild(existing);
        }
        if (td.getAttribute("data-et") !== kept) td.setAttribute("data-et", kept);
        return;
      }
      if (existing) {
        if (document.activeElement !== existing && String(existing.value || "") !== kept) {
          existing.value = kept;
        }
        if (td.getAttribute("data-et") !== kept) td.setAttribute("data-et", kept);
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
      td.setAttribute("data-et-race", race);
      while (td.firstChild) td.removeChild(td.firstChild);
      td.appendChild(inp);
      inp.addEventListener("input", function () {
        td.setAttribute("data-et", String(inp.value || "").trim());
        saveEtValue(race, rid, inp.value);
        applyCorrection(table, false, false);
      });
      inp.addEventListener("blur", function () {
        var liveRace = openRaceKey(table) || race;
        saveEtValue(liveRace, rid, inp.value);
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
    syncEtVisible(sec);
    var focused =
      document.activeElement &&
      document.activeElement.classList &&
      document.activeElement.classList.contains("dam-bottle-et-input");
    applyCorrection(table, false, false);
    if (!focused && adminEditOn()) applyCorrection(table, true, false);
  }

  function bottleSrc() {
    return "/artwork/Event%20Logo/Dam-Bottle-Sprints.png";
  }

  function setBottleImg(img) {
    if (!img) return;
    if (img.getAttribute("src") !== bottleSrc()) img.src = bottleSrc();
    if (img.getAttribute("alt") !== "Dam Bottle Sprints") img.alt = "Dam Bottle Sprints";
    if (img.hasAttribute("title")) img.removeAttribute("title");
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
          if (n.nodeValue !== " Open Fleet") n.nodeValue = " Open Fleet";
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

  function findFleetSec() {
    var table = document.querySelector(
      '.fleet-section[data-block-id="' + RID + ':open"] table.fleet-results-table'
    );
    return table ? table.closest(".fleet-section") : null;
  }

  function placeOpenFleetHeader() {
    dropDuplicateFleetHeaders();
    var sec = findFleetSec();
    if (!sec) return;
    if (sec.id !== "dam-bottle-open-fleet") sec.id = "dam-bottle-open-fleet";
    if (sec.getAttribute("data-fleet-label") !== "Open") sec.setAttribute("data-fleet-label", "Open");
    paintOpenFleetHeader(sec);
    var host = document.getElementById("midmar-live-media");
    if (host && host.parentNode && sec.previousSibling !== host) {
      host.parentNode.insertBefore(sec, host.nextSibling);
    }
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

  function bindRaceUi(sec) {
    if (!sec) return;
    var table = sec.querySelector("table.fleet-results-table");
    sec.querySelectorAll("th.race-col").forEach(function (th) {
      if (th._dbsCloseBound) return;
      th._dbsCloseBound = true;
      th.addEventListener("click", function () {
        window.setTimeout(function () {
          lockAutoRaces(table);
          wireEtInputs(table);
          syncEtVisible(sec);
        }, 0);
      });
    });
    function afterStep() {
      window.setTimeout(function () {
        var t = sec.querySelector("table.fleet-results-table");
        lockAutoRaces(t);
        ensureTickCol(t);
        wireEtInputs(t);
        syncEtVisible(sec);
      }, 120);
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

  add("/js/midmar-live-media.js?v=midmarwx60dbs3");
  add("/js/club-score-edit.js?v=ccr38dbs4");

  var painting = false;
  function safePaint() {
    if (painting) return;
    painting = true;
    try {
      syncDartStack();
      bindRaceUi(document.getElementById("dam-bottle-open-fleet") || findFleetSec());
    } finally {
      painting = false;
    }
  }

  safePaint();
  [80, 250, 700, 1600, 3200].forEach(function (ms) {
    window.setTimeout(safePaint, ms);
  });
  if (page && !page._dbsAdminObs) {
    page._dbsAdminObs = true;
    var lastAdmin = adminEditOn();
    var adminObs = new MutationObserver(function () {
      var now = adminEditOn();
      if (now === lastAdmin) return;
      lastAdmin = now;
      window.setTimeout(safePaint, 0);
    });
    adminObs.observe(page, { attributes: true, attributeFilter: ["class"] });
  }
})();
