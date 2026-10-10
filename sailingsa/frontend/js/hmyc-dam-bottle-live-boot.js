/**
 * Dam Bottle Sprints — each race has its own ET + ✓ + R.
 * Click that R header to show/hide its ET/✓. R+ adds a race block. R- drops the last.
 * Admin types ET only. 0:00 is DNC. No observers. Does not change live api.py.
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
      ".regatta-page > .midmar-live-media .mm-lipton-reels[data-regatta-id^='" + RID + "']:not(.mm-lipton-reels--expanded) .mm-lipton-reels-compact{display:flex!important;}" +
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
      ".fleet-section[data-block-id='" + RID + ":open'] .dam-bottle-py-col{display:none!important}" +
      ".fleet-section[data-block-id='" + RID + ":open'] .dam-bottle-et-hidden{display:none!important}" +
      ".fleet-section[data-block-id='" + RID + ":open'] td.total-col," +
      ".fleet-section[data-block-id='" + RID + ":open'] td.nett-col{min-width:2.4rem;text-align:center;font-weight:700;}" +
      ".fleet-section[data-block-id='" + RID + ":open'] tr.medal-gold," +
      ".fleet-section[data-block-id='" + RID + ":open'] tr.medal-gold td{background-color:#D4AF37}" +
      ".fleet-section[data-block-id='" + RID + ":open'] tr.medal-silver," +
      ".fleet-section[data-block-id='" + RID + ":open'] tr.medal-silver td{background-color:#D7D7D7}" +
      ".fleet-section[data-block-id='" + RID + ":open'] tr.medal-bronze," +
      ".fleet-section[data-block-id='" + RID + ":open'] tr.medal-bronze td{background-color:#CE8946}" +
      ".fleet-section[data-block-id='" + RID + ":open'] .dam-bottle-et-input.club-score-input--saving{background:#fef08a}" +
      ".fleet-section[data-block-id='" + RID + ":open'] .dam-bottle-et-input.club-score-input--saved{background:#bbf7d0}" +
      "#dam-bottle-open-fleet .table-container{overflow-x:auto;-webkit-overflow-scrolling:touch;max-width:100%}" +
      "#dam-bottle-open-fleet table.fleet-results-table{width:max-content;min-width:100%;max-width:none}" +
      "#dam-bottle-open-fleet table.fleet-results-table th," +
      "#dam-bottle-open-fleet table.fleet-results-table td{white-space:nowrap}" +
      ".fleet-section[data-block-id='" + RID + ":open'] td.race-col.disc," +
      ".fleet-section[data-block-id='" + RID + ":open'] td.race-col.strike-out{text-decoration:line-through;opacity:0.6}" +
      ".fleet-section[data-block-id='" + RID + ":open'] .dam-bottle-json-col{display:none!important}";
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
    function fromObj(o) {
      if (!o) return "";
      return String((o.session || o.session_token || o.session_id || o.token) || "").trim();
    }
    try {
      var a = localStorage.getItem("session") || sessionStorage.getItem("session");
      if (a && a.charAt(0) === "{") {
        var ta = fromObj(JSON.parse(a));
        if (ta) return ta;
      } else if (a && String(a).trim().length > 8) return String(a).trim();
      var b = localStorage.getItem("sailing_session") || sessionStorage.getItem("sailing_session");
      if (b) {
        if (b.charAt(0) === "{") {
          var tb = fromObj(JSON.parse(b));
          if (tb) return tb;
        } else if (String(b).trim().length > 8) return String(b).trim();
      }
      var cookie = String(document.cookie || "");
      var m = cookie.match(/(?:^|;\s*)(?:session|session_token)=([^;]+)/);
      if (m && m[1]) return decodeURIComponent(m[1]).trim();
    } catch (e) {}
    return "";
  }

  function withSession(url) {
    var t = sessionToken();
    if (!t) return url;
    return url + (url.indexOf("?") >= 0 ? "&" : "?") + "session=" + encodeURIComponent(t);
  }

  var ET_MARK = "ETJ:";
  var ET_API = "/api/hmyc-dam-bottle-et";
  var etHydrated = false;
  var etServerTimer = {};

  function asRec(v) {
    if (!v) return { et: "", corr: "", place: "" };
    if (typeof v === "string") {
      var s = v.trim();
      if (!s) return { et: "", corr: "", place: "" };
      if (s.charAt(0) === "{") {
        try {
          return asRec(JSON.parse(s));
        } catch (e0) {
          return { et: s, corr: "", place: "" };
        }
      }
      return { et: s, corr: "", place: "" };
    }
    return {
      et: String(v.et || "").trim(),
      corr: String(v.corr || "").trim(),
      place: String(v.place || "").trim(),
    };
  }

  function normalizeEtStore(raw) {
    raw = raw && typeof raw === "object" ? raw : {};
    var keys = Object.keys(raw);
    if (!keys.length) return {};
    if (keys.some(function (k) { return /^R\d+$/.test(k); })) return raw;
    return { R1: raw };
  }

  function readEtCookie() {
    try {
      var m = String(document.cookie || "").match(new RegExp("(?:^|;\\s*)" + ET_KEY + "=([^;]+)"));
      if (!m || !m[1]) return {};
      return normalizeEtStore(JSON.parse(decodeURIComponent(m[1])));
    } catch (e) {
      return {};
    }
  }

  function writeEtCookie(s) {
    try {
      document.cookie = ET_KEY + "=" + encodeURIComponent(JSON.stringify(s || {})) + ";path=/;max-age=2592000;SameSite=Lax";
    } catch (e3) {}
  }

  function mergeEtStore(into, extra) {
    into = into || {};
    extra = extra || {};
    Object.keys(extra).forEach(function (race) {
      if (!/^R\d+$/.test(race) || !extra[race] || typeof extra[race] !== "object") return;
      if (!into[race]) into[race] = {};
      Object.keys(extra[race]).forEach(function (rid) {
        var have = asRec(into[race][rid]);
        var add = asRec(extra[race][rid]);
        if (!have.et && add.et) into[race][rid] = add;
        else if (have.et) {
          if (!have.corr && add.corr) have.corr = add.corr;
          if (!have.place && add.place) have.place = add.place;
          into[race][rid] = have;
        }
      });
    });
    return into;
  }

  function loadEtStore() {
    var raw = {};
    try {
      raw = normalizeEtStore(JSON.parse(localStorage.getItem(ET_KEY) || "{}") || {});
    } catch (e1) {
      raw = {};
    }
    return mergeEtStore(raw, readEtCookie());
  }

  function persistEtStore(s) {
    try {
      localStorage.setItem(ET_KEY, JSON.stringify(s || {}));
    } catch (e2) {}
    writeEtCookie(s);
  }

  function etRecord(race, rid) {
    var s = loadEtStore();
    return asRec(s[race] && s[race][String(rid)]);
  }

  function etFor(race, rid) {
    return etRecord(race, rid).et;
  }

  function saveEtRecord(race, rid, rec, fromServer) {
    if (!race || !rid) return;
    var s = loadEtStore();
    if (!s[race]) s[race] = {};
    rec = asRec(rec);
    if (!rec.et) delete s[race][String(rid)];
    else s[race][String(rid)] = rec;
    persistEtStore(s);
    if (!fromServer) schedulePersistEt(rid);
  }

  function saveEtValue(race, rid, val, fromServer) {
    var cur = etRecord(race, rid);
    cur.et = String(val || "").trim();
    saveEtRecord(race, rid, cur, fromServer);
  }

  function clearEtRace(race) {
    var s = loadEtStore();
    var rids = Object.keys(s[race] || {});
    delete s[race];
    persistEtStore(s);
    rids.forEach(schedulePersistEt);
  }

  function etFromHull(raw) {
    var s = String(raw || "").trim();
    if (s.indexOf(ET_MARK) !== 0) return {};
    try {
      var o = JSON.parse(s.slice(ET_MARK.length));
      return o && typeof o === "object" ? o : {};
    } catch (e) {
      return {};
    }
  }

  function persistEtServer(rid) {
    var s = loadEtStore();
    var jobs = [];
    if (rid && adminEditOn()) {
      var mine = {};
      Object.keys(s).forEach(function (race) {
        var rec = asRec(s[race] && s[race][String(rid)]);
        if (rec.et) mine[race] = rec;
      });
      jobs.push(
        fetch(withSession("/api/result/" + encodeURIComponent(rid)), {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({
            hull_no: Object.keys(mine).length ? ET_MARK + JSON.stringify(mine) : "",
            session: sessionToken(),
          }),
        }).catch(function () {
          return null;
        })
      );
    }
    if (adminEditOn()) {
      jobs.push(
        fetch(ET_API, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ rid: RID, store: s, updated: Date.now() }),
        }).catch(function () {
          return null;
        })
      );
    }
    return jobs.length ? Promise.all(jobs) : Promise.resolve();
  }

  function schedulePersistEt(rid) {
    if (!adminEditOn()) return;
    window.clearTimeout(etServerTimer[rid || "*"]);
    etServerTimer[rid || "*"] = window.setTimeout(function () {
      persistEtServer(rid);
    }, 400);
  }

  function applyRemoteEt(rid, recs) {
    Object.keys(recs || {}).forEach(function (race) {
      if (!/^R\d+$/.test(race) || !recs[race]) return;
      var add = asRec(recs[race]);
      if (!add.et) return;
      saveEtRecord(race, rid, add, true);
    });
  }

  function applyHullEt(rid, hull) {
    applyRemoteEt(rid, etFromHull(hull));
  }

  function hydrateEtFromApi(done) {
    if (etHydrated) {
      if (done) done();
      return;
    }
    var pending = 2;
    function finish() {
      pending -= 1;
      if (pending > 0) return;
      etHydrated = true;
      if (done) done();
    }
    fetch(ET_API, { credentials: "include" })
      .then(function (r) {
        return r.json();
      })
      .then(function (j) {
        mergeEtStore(loadEtStore(), (j && j.store) || {});
        persistEtStore(mergeEtStore(loadEtStore(), (j && j.store) || {}));
      })
      .catch(function () {})
      .then(finish);
    fetch("/api/regatta/" + encodeURIComponent(RID), { credentials: "include" })
      .then(function (r) {
        return r.json();
      })
      .then(function (rows) {
        (Array.isArray(rows) ? rows : []).forEach(function (row) {
          if (row && row.result_id) applyHullEt(row.result_id, row.hull_no);
        });
      })
      .catch(function () {})
      .then(finish);
  }

  function snapshotEtFromDom(table) {
    if (!table) return;
    table.querySelectorAll("tbody tr[data-result-id]").forEach(function (tr) {
      var rid = tr.getAttribute("data-result-id");
      tr.querySelectorAll("td.dam-bottle-et-col").forEach(function (td) {
        var race = td.getAttribute("data-for-race");
        var raw = etRaw(tr, race);
        if (!race || !raw) return;
        var corrTd = tr.querySelector('td.dam-bottle-corr-col[data-for-race="' + race + '"]');
        var rTd = tr.querySelector('td.race-col[data-race-key="' + race + '"]');
        saveEtRecord(race, rid, {
          et: raw,
          corr: String((corrTd && corrTd.textContent) || etRecord(race, rid).corr || "").trim(),
          place: cellPlaceText(rTd) || etRecord(race, rid).place,
        });
      });
    });
  }

  function paintEtCells(table) {
    if (!table) return;
    table.querySelectorAll("td.dam-bottle-et-col").forEach(function (td) {
      var race = td.getAttribute("data-for-race");
      var tr = td.closest("tr");
      var rid = tr && tr.getAttribute("data-result-id");
      if (!race || !rid) return;
      var rec = etRecord(race, rid);
      td.setAttribute("data-et", rec.et);
      if (adminEditOn()) return;
      if (td.querySelector(".dam-bottle-et-input")) return;
      if (String(td.textContent || "").trim() !== rec.et) td.textContent = rec.et;
    });
    table.querySelectorAll("td.dam-bottle-corr-col").forEach(function (td) {
      var race = td.getAttribute("data-for-race");
      var tr = td.closest("tr");
      var rid = tr && tr.getAttribute("data-result-id");
      if (!race || !rid) return;
      var rec = etRecord(race, rid);
      var shown = rec.corr;
      if (!shown && rec.et && !isDnsEt(rec.et)) {
        var py = rowPy(tr);
        var sec = parseET(rec.et);
        if (py && sec) shown = formatCorrected((sec * 1000) / py);
      }
      if (shown && String(td.textContent || "").trim() !== shown) td.textContent = shown;
    });
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

  function isZeroEt(raw) {
    var s = String(raw || "").trim();
    if (!s) return false;
    if (/^0+([:.]0+)*$/.test(s)) return true;
    return parseET(s) === 0;
  }

  function etCode(raw, keptPlace) {
    var s = String(raw || "").trim();
    if (!s) return "";
    if (/^(dnc|dns|dnf|ret|dsq|ufd|bfd|ocs)$/i.test(s)) return s.toUpperCase();
    if (isZeroEt(s)) {
      if (keptPlace && /^(DNC|DNS|DNF|RET|DSQ|UFD|BFD|OCS)$/i.test(String(keptPlace))) {
        return String(keptPlace).toUpperCase();
      }
      return "DNC";
    }
    return "";
  }

  function isDnsEt(raw) {
    return !!etCode(raw);
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

  var placeSnap = {};

  function cellPlaceText(td) {
    if (!td) return "";
    var span = td.querySelector("span");
    var raw = String(((span && span.textContent) || td.textContent) || "").trim();
    raw = raw.replace(/^\(|\)$/g, "").trim();
    if (!raw || raw === "—" || raw === "-" || raw === "–") return "";
    return raw;
  }

  function snappedPlace(rid, race) {
    return String((placeSnap[rid] && placeSnap[rid][race]) || "").trim();
  }

  function rememberPlace(rid, race, place) {
    if (!rid || !race) return;
    var v = String(place || "").trim();
    if (!v) return;
    if (!placeSnap[rid]) placeSnap[rid] = {};
    placeSnap[rid][race] = v;
  }

  function snapshotPlaces(table) {
    if (!table) return;
    table.querySelectorAll("tbody tr[data-result-id]").forEach(function (tr) {
      var rid = tr.getAttribute("data-result-id");
      if (!rid) return;
      if (!placeSnap[rid]) placeSnap[rid] = {};
      tr.querySelectorAll("td.race-col").forEach(function (td) {
        var k = raceKeyOf(td);
        if (!/^R\d+$/.test(k)) return;
        var v = cellPlaceText(td);
        if (v) placeSnap[rid][k] = v;
      });
    });
  }

  function stampExistingRaceKeys(table) {
    if (!table) return;
    var thead = table.querySelector("thead tr");
    if (!thead) return;
    [].forEach.call(thead.children, function (th, i) {
      if (!th.classList.contains("race-col")) return;
      var k = raceKeyOf(th);
      if (!/^R\d+$/.test(k)) return;
      th.setAttribute("data-race-key", k);
      table.querySelectorAll("tbody tr").forEach(function (tr) {
        var td = tr.children[i];
        if (!td) return;
        td.classList.add("race-col");
        if (!td.getAttribute("data-race-key")) td.setAttribute("data-race-key", k);
      });
    });
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
        if (!r.ok) throw new Error((j && (j.detail || j.error)) || "save failed");
        return { ok: true, j: j };
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
      if (td && !cellPlaceText(td) && v) td.textContent = v;
    });
    table.querySelectorAll("td.race-col").forEach(function (td) {
      var k = raceKeyOf(td);
      var tr = td.closest("tr");
      var rid = tr && tr.getAttribute("data-result-id");
      if (!k || !rid) return;
      var shown = cellPlaceText(td);
      if (shown) {
        rememberPlace(rid, k, shown);
        return;
      }
      var snap = snappedPlace(rid, k);
      if (snap) td.textContent = snap;
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
    if (adminEditOn()) {
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
    var existingTh = null;
    table.querySelectorAll("thead th.race-col").forEach(function (th) {
      if (raceKeyOf(th) === key && !existingTh) existingTh = th;
    });
    if (existingTh) {
      existingTh.setAttribute("data-race-key", key);
      var rIdx = [].indexOf.call(thead.children, existingTh);
      table.querySelectorAll("tbody tr").forEach(function (tr) {
        var td = tr.children[rIdx];
        if (!td) return;
        td.classList.add("race-col");
        td.setAttribute("data-race-key", key);
      });
    } else if (!has('th.race-col[data-race-key="' + key + '"]')) {
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

  function dropJsonDumpCols(table) {
    if (!table) return;
    var thead = table.querySelector("thead tr");
    if (!thead) return;
    var doomed = [];
    [].forEach.call(thead.children, function (th, i) {
      var lab = String(th.textContent || "").replace(/\s+/g, " ").trim();
      if (lab === "Elapsed" || lab === "Corrected") doomed.push(i);
    });
    doomed.sort(function (a, b) { return b - a; });
    doomed.forEach(function (i) { removeColAt(table, i); });
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
    var doomed = [];
    [].slice.call(thead.children).forEach(function (th) {
      if (th.classList.contains("race-col")) {
        var k = raceKeyOf(th);
        if (k) keys[k] = true;
      }
    });
    [].slice.call(thead.children).forEach(function (th, idx) {
      var race = th.getAttribute("data-for-race") || raceKeyOf(th);
      var bag = th.classList.contains("dam-bottle-et-col")
        ? "et"
        : th.classList.contains("dam-bottle-corr-col")
          ? "corr"
          : th.classList.contains("race-col")
            ? "r"
            : "";
      if (!bag) return;
      if (!race || (!keys[race] && bag !== "r")) {
        doomed.push(idx);
        return;
      }
      if (seen[bag][race]) {
        doomed.push(idx);
        return;
      }
      seen[bag][race] = true;
    });
    doomed.sort(function (a, b) { return b - a; });
    doomed.forEach(function (i) {
      removeColAt(table, i);
    });
  }

  function fleetSize(tr) {
    var table = tr && tr.closest("table");
    var n = table ? table.querySelectorAll("tbody tr[data-result-id]").length : 0;
    return n > 0 ? n : 1;
  }

  function isCodeScore(raw) {
    return /^(DNC|DNS|DNF|RET|DSQ|UFD|BFD|OCS|DPI)$/i.test(String(raw || "").trim());
  }

  function scorePts(raw, dnsPts) {
    var t = String(raw || "").replace(/^\(|\)$/g, "").trim();
    if (!t) return null;
    if (isCodeScore(t)) return dnsPts;
    var v = parseInt(t.replace(/[^\d]/g, ""), 10);
    return isFinite(v) && v > 0 ? v : null;
  }

  function seriesScoredCount(table) {
    var n = 0;
    if (!table) return 0;
    raceKeys(table).forEach(function (k) {
      var any = false;
      table.querySelectorAll('td.race-col[data-race-key="' + k + '"]').forEach(function (td) {
        if (cellPlaceText(td)) any = true;
      });
      if (any) n += 1;
    });
    return n;
  }

  function updateSailedLine(table) {
    var sec = table && table.closest(".fleet-section");
    var line = sec && sec.querySelector(".sailed-line");
    if (!line) return;
    var sailed = seriesScoredCount(table);
    var disc = Math.floor(sailed / 5);
    var toCount = Math.max(0, sailed - disc);
    var entries = table.querySelectorAll("tbody tr[data-result-id]").length;
    var sys = "Portsmouth Yardstick (PY)";
    var m = String(line.textContent || "").match(/Scoring system:\s*(.+)$/i);
    if (m && String(m[1] || "").trim()) sys = String(m[1]).trim();
    line.textContent =
      "Sailed: " + sailed +
      ", Discards: " + disc +
      ", To count: " + toCount +
      ", Entries: " + entries +
      ", Scoring system: " + sys;
  }

  function fillTotalNett(tr) {
    var table = tr && tr.closest("table");
    var dnsPts = fleetSize(tr) + 1;
    var discN = table ? Math.floor(seriesScoredCount(table) / 5) : 0;
    var scored = [];
    tr.querySelectorAll("td.race-col").forEach(function (td, i) {
      var raw = cellPlaceText(td);
      var pts = scorePts(raw, dnsPts);
      if (pts == null) {
        td.classList.remove("disc", "strike-out");
        return;
      }
      scored.push({ td: td, raw: raw, pts: pts, i: i });
    });
    var discardAt = {};
    if (discN > 0 && scored.length) {
      var order = scored.slice();
      order.sort(function (a, b) {
        if (b.pts !== a.pts) return b.pts - a.pts;
        return a.i - b.i;
      });
      var dropN = Math.min(discN, order.length);
      var j;
      for (j = 0; j < dropN; j++) discardAt[order[j].i] = true;
    }
    var total = 0;
    var dropped = 0;
    scored.forEach(function (s) {
      total += s.pts;
      var discarded = !!discardAt[s.i];
      if (discarded) dropped += s.pts;
      var shown = discarded ? "(" + s.raw + ")" : s.raw;
      if (s.td.textContent !== shown) s.td.textContent = shown;
      s.td.classList.toggle("disc", discarded && !isCodeScore(s.raw));
      s.td.classList.toggle("strike-out", discarded);
      s.td.classList.toggle("code", isCodeScore(s.raw));
    });
    var tot = tr.querySelector("td.total-col");
    var nett = tr.querySelector("td.nett-col");
    var totTxt = scored.length ? String(total) : "";
    var nettTxt = scored.length ? String(total - dropped) : "";
    if (tot) {
      tot.classList.remove("strike-out");
      tot.textContent = totTxt;
    }
    if (nett) {
      nett.classList.remove("strike-out");
      nett.textContent = nettTxt;
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

  function markEtState(table, race, cls) {
    if (!table || !race) return;
    table.querySelectorAll('td.dam-bottle-et-col[data-for-race="' + race + '"] .dam-bottle-et-input').forEach(function (inp) {
      inp.classList.remove("club-score-input--saving", "club-score-input--saved");
      if (cls) inp.classList.add(cls);
    });
  }

  function persistPlaces(table, race, items) {
    if (!adminEditOn() || !race) return;
    var typed = items.filter(function (it) {
      return String(etRaw(it.tr, race) || "").trim();
    });
    if (!typed.length) return;
    var last = lastSaved[race] || {};
    var next = {};
    typed.forEach(function (it) {
      next[it.rid] = it.place ? String(it.place) : "";
    });
    var same =
      Object.keys(next).length &&
      typed.every(function (it) {
        return String(last[it.rid] || "") === String(next[it.rid] || "");
      }) &&
      Object.keys(last).length === Object.keys(next).length;
    typed.forEach(function (it) {
      saveEtRecord(race, it.rid, {
        et: etRaw(it.tr, race) || etFor(race, it.rid),
        corr: it.corr != null ? formatCorrected(it.corr) : etRecord(race, it.rid).corr,
        place: it.place ? String(it.place) : etRecord(race, it.rid).place,
      });
    });
    if (same) {
      typed.forEach(function (it) {
        persistEtServer(it.rid);
      });
      return;
    }
    markEtState(table, race, "club-score-input--saving");
    saveChain = saveChain
      .then(function () {
        var seq = Promise.resolve();
        typed.forEach(function (it) {
          seq = seq.then(function () {
            return sessionPatchRace(it.rid, race, "");
          });
        });
        return seq;
      })
      .then(function () {
        var seq = Promise.resolve();
        typed.forEach(function (it) {
          if (!it.place) return;
          seq = seq.then(function () {
            return sessionPatchRace(it.rid, race, String(it.place));
          });
        });
        return seq;
      })
      .then(function () {
        lastSaved[race] = next;
        typed.forEach(function (it) {
          persistEtServer(it.rid);
        });
        markEtState(table, race, "club-score-input--saved");
        window.setTimeout(function () {
          markEtState(table, race, "");
        }, 900);
      })
      .catch(function () {
        markEtState(table, race, "");
      });
  }

  function applyRace(table, race, doSave) {
    if (!table || !race) return;
    lockRCells(table);
    var items = [];
    table.querySelectorAll("tbody tr[data-result-id]").forEach(function (tr, idx) {
      var rid = tr.getAttribute("data-result-id");
      var raw = etRaw(tr, race) || etFor(race, rid);
      var dns = isDnsEt(raw);
      var py = rowPy(tr);
      var etSec = dns ? null : parseET(raw);
      items.push({
        tr: tr,
        rid: rid,
        dns: dns,
        keep: !dns && !String(raw || "").trim(),
        corr: !dns && py && etSec != null && etSec > 0 ? (etSec * 1000) / py : null,
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
      var src = etRaw(it.tr, race) || etFor(race, it.rid);
      var code = etCode(src, etRecord(race, it.rid).place);
      if (it.dns) {
        it.place = code || "DNC";
        if (src && !isZeroEt(src)) {
          var etTd = it.tr.querySelector('td.dam-bottle-et-col[data-for-race="' + race + '"]');
          var inp = etTd && etTd.querySelector(".dam-bottle-et-input");
          if (inp) inp.value = "0:00";
          if (etTd) etTd.setAttribute("data-et", "0:00");
          src = "0:00";
        }
      }
      var corrTd = it.tr.querySelector('td.dam-bottle-corr-col[data-for-race="' + race + '"]');
      var rTd = it.tr.querySelector('td.race-col[data-race-key="' + race + '"]');
      if (it.keep) {
        var kept = rTd ? cellPlaceText(rTd) : "";
        if (!kept) kept = snappedPlace(it.rid, race);
        if (kept) {
          it.place = kept;
          if (rTd && cellPlaceText(rTd) !== kept) rTd.textContent = kept;
          rememberPlace(it.rid, race, kept);
        }
        var keptCorr = etRecord(race, it.rid).corr;
        if (corrTd && keptCorr && corrTd.textContent !== keptCorr) corrTd.textContent = keptCorr;
        fillTotalNett(it.tr);
        return;
      }
      var shown = it.corr != null ? formatCorrected(it.corr) : "";
      if (!shown && it.dns) shown = "";
      if (!shown) shown = etRecord(race, it.rid).corr;
      if (corrTd && corrTd.textContent !== shown) corrTd.textContent = shown;
      saveEtRecord(race, it.rid, {
        et: it.dns ? "0:00" : src,
        corr: shown,
        place: it.place ? String(it.place) : etRecord(race, it.rid).place,
      });
      if (rTd) {
        var p = it.place ? String(it.place) : "";
        if (p) {
          if (cellPlaceText(rTd) !== p) rTd.textContent = p;
          rememberPlace(it.rid, race, p);
        } else {
          var snap = snappedPlace(it.rid, race);
          if (snap) {
            it.place = snap;
            if (cellPlaceText(rTd) !== snap) rTd.textContent = snap;
          } else if (rTd.textContent !== "") {
            rTd.textContent = "";
          }
        }
        rTd.classList.toggle("code", it.dns);
      }
      fillTotalNett(it.tr);
    });
    if (doSave) persistPlaces(table, race, items);
  }

  function applyAllRaces(table, doSave) {
    raceKeys(table).forEach(function (race) {
      applyRace(table, race, doSave);
    });
    if (table) {
      table.querySelectorAll("tbody tr[data-result-id]").forEach(fillTotalNett);
      updateSailedLine(table);
    }
    sortPodium(table);
  }

  function sortPodium(table) {
    if (!table) return;
    if (document.activeElement && document.activeElement.classList.contains("dam-bottle-et-input")) return;
    var tbody = table.tBodies && table.tBodies[0];
    if (!tbody) return;
    var medals = ["medal-gold", "medal-silver", "medal-bronze"];
    var rows = [].map.call(tbody.querySelectorAll("tr[data-result-id]"), function (tr, idx) {
      var nett = parseInt(String((tr.querySelector("td.nett-col") && tr.querySelector("td.nett-col").textContent) || ""), 10);
      return { tr: tr, nett: isFinite(nett) && nett > 0 ? nett : 9999, idx: idx };
    });
    rows.sort(function (a, b) { return a.nett - b.nett || a.idx - b.idx; });
    rows.forEach(function (it, i) {
      var place = it.nett < 9999 ? i + 1 : 0;
      var rankTd = it.tr.querySelector("td.rank-col");
      var shown = place ? rankLabel(place) : "";
      if (rankTd && rankTd.textContent !== shown) rankTd.textContent = shown;
      it.tr.classList.remove("medal-gold", "medal-silver", "medal-bronze");
      if (place >= 1 && place <= 3) it.tr.classList.add(medals[place - 1]);
      if (place) it.tr.setAttribute("data-official-rank", String(place));
      else it.tr.removeAttribute("data-official-rank");
      tbody.appendChild(it.tr);
    });
  }

  function wireEtInputs(table) {
    paintEtCells(table);
    if (!table || !adminEditOn()) return;
    table.querySelectorAll("td.dam-bottle-et-col").forEach(function (td) {
      var race = td.getAttribute("data-for-race");
      var tr = td.closest("tr");
      if (!race || !tr) return;
      var rid = tr.getAttribute("data-result-id");
      var kept = etFor(race, rid);
      var existing = td.querySelector(".dam-bottle-et-input");
      if (existing) {
        if (document.activeElement !== existing) {
          if (kept && String(existing.value || "").trim() !== kept) existing.value = kept;
          else if (!String(existing.value || "").trim() && kept) existing.value = kept;
        }
        td.setAttribute("data-et", String(existing.value || kept || "").trim());
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
        window.clearTimeout(inp._dbsSave);
        inp._dbsSave = window.setTimeout(function () {
          applyRace(table, race, true);
        }, 350);
        window.setTimeout(function () { sortPodium(table); }, 0);
      });
      inp.addEventListener("blur", function () {
        window.clearTimeout(inp._dbsSave);
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
      var hasTime = false;
      table.querySelectorAll('td.dam-bottle-et-col[data-for-race="' + key + '"]').forEach(function (td) {
        var tr = td.closest("tr");
        var rid = tr && tr.getAttribute("data-result-id");
        if (etRaw(tr, key) || etFor(key, rid)) hasTime = true;
      });
      var hide = closed || (!adminEditOn() && !hasTime);
      table.querySelectorAll('[data-for-race="' + key + '"]').forEach(function (el) {
        if (el.classList.contains("race-col")) return;
        el.classList.toggle("dam-bottle-et-hidden", hide);
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
    snapshotEtFromDom(table);
    if (!table.parentNode.classList.contains("table-container")) {
      var wrap = document.createElement("div");
      wrap.className = "table-container";
      table.parentNode.insertBefore(wrap, table);
      wrap.appendChild(table);
    }
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
    markCol(table, "Class", "class-col");
    markCol(table, "PY", "dam-bottle-py-col");
    table.querySelectorAll("tbody tr[data-result-id]").forEach(function (tr) {
      var sail = String((tr.querySelector("td.sail-col") && tr.querySelector("td.sail-col").textContent) || "").trim();
      var bySail = { "520": "Dart 18", "2": "ILCA 7", "741": "Hunter 19", "222": "Hunter 19" };
      var td = tr.querySelector("td.class-col");
      if (td && bySail[sail] && !String(td.textContent || "").trim()) td.textContent = bySail[sail];
    });
    dropJsonDumpCols(table);
    keepOneLabeled(table, "total-col", "Total");
    keepOneLabeled(table, "nett-col", "Nett");
    stampExistingRaceKeys(table);
    snapshotPlaces(table);
    var existing = raceCount(table);
    if (existing < 1) existing = 1;
    var i;
    for (i = 1; i <= existing; i++) ensurePairAndRace(table, i);
    dropOrphanAndDup(table);
    orderCols(table);
    lockRCells(table);
    wireEtInputs(table);
    paintEtCells(table);
    syncEtVisible(sec);
    applyAllRaces(table, false);
    bindUi(sec);
    placeStack();
    document.documentElement.setAttribute("data-dbs-ready", "1");
    return true;
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

  var paintedOk = false;
  function paintOnce() {
    if (paint()) paintedOk = true;
    return paintedOk;
  }
  function fillTimesOnly() {
    var sec = findSec();
    var table = sec && sec.querySelector("table.fleet-results-table");
    if (!table) return;
    wireEtInputs(table);
    paintEtCells(table);
    applyAllRaces(table, false);
    syncEtVisible(sec);
  }
  paintOnce();
  hydrateEtFromApi(function () {
    fillTimesOnly();
    if (!paintedOk) paintOnce();
  });
  add("/js/midmar-live-media.js?v=midmarwx60dbs5");
  add("/js/club-score-edit.js?v=ccr38dbs4");
  [80, 250, 700].forEach(function (ms) {
    window.setTimeout(function () {
      if (!paintedOk) paintOnce();
    }, ms);
  });
  var filledAdmin = false;
  [400, 1000, 1800].forEach(function (ms) {
    window.setTimeout(function () {
      if (filledAdmin || !adminEditOn()) return;
      filledAdmin = true;
      fillTimesOnly();
    }, ms);
  });
})();
