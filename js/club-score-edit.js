/* Cape Classic club-admin R1 boxes. Total / Nett / Rank stay auto. */
(function () {
  var path = String((window.location && window.location.pathname) || "");
  if (path.indexOf("2026-09-13-zvyc-cape-classic") === -1) return;

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

  function canScore(session) {
    if (!session || !session.valid) return false;
    var role = String(session.role || "")
      .toLowerCase()
      .replace(/[\s-]+/g, "_");
    return (
      role === "club_admin" ||
      role === "clubadmin" ||
      role === "admin" ||
      role === "super_admin" ||
      role === "superadmin" ||
      !!session.is_super_admin
    );
  }

  function injectStyles() {
    if (document.getElementById("clubScoreEditCss")) return;
    var st = document.createElement("style");
    st.id = "clubScoreEditCss";
    st.textContent =
      ".club-score-banner{margin:12px 0 0;padding:10px 12px;border:2px solid #1a2750;border-radius:8px;background:#f8fafc;color:#1a2750;font-weight:700;font-size:13px}" +
      ".club-score-input{box-sizing:border-box;width:4.8rem;min-width:4.4rem;height:22px;min-height:22px;max-height:22px;padding:0 3px;text-align:center;font:inherit;font-size:12px;line-height:20px;font-weight:700;border:1.5px solid #1a2750;border-radius:4px;background:#fff;color:#1a2750}" +
      ".club-score-input.club-score-input--saving{background:#fef08a}" +
      ".club-score-input.club-score-input--saved{background:#bbf7d0}" +
      ".regatta-page--club-score-edit .fleet-results-table td.race-col{padding:2px 3px;vertical-align:middle}" +
      ".regatta-page--club-score-edit td.total-col," +
      ".regatta-page--club-score-edit td.nett-col," +
      ".regatta-page--club-score-edit td.rank-col{pointer-events:none;user-select:none}" +
      ".regatta-page--club-score-edit td.total-col input," +
      ".regatta-page--club-score-edit td.nett-col input," +
      ".regatta-page--club-score-edit td.rank-col input{display:none!important}";
    document.head.appendChild(st);
  }

  function banner() {
    if (document.getElementById("clubScoreBanner")) return;
    var page = document.querySelector(".regatta-page");
    if (!page) return;
    var el = document.createElement("div");
    el.className = "club-score-banner";
    el.id = "clubScoreBanner";
    el.textContent =
      "Type place or DSQ. Extra DSQ = 15 DSQ; discarded is (15 DSQ). Enter = next. Rank live.";
    var firstFleet = page.querySelector(".fleet-section");
    if (firstFleet) page.insertBefore(el, firstFleet);
    else page.insertBefore(el, page.firstChild);
  }

  function fleetInputs(from) {
    var root = (from && from.closest(".fleet-section")) || document;
    return Array.prototype.slice.call(root.querySelectorAll(".club-score-input"));
  }

  function focusOffset(inp, dir) {
    var list = fleetInputs(inp);
    var i = list.indexOf(inp);
    var next = i >= 0 ? list[i + dir] : null;
    if (!next) return;
    next.focus();
    if (typeof next.select === "function") next.select();
  }

  var PENALTY_CODES = ["DNC", "DNS", "DNF", "RET", "DSQ", "UFD", "BFD", "DPI", "OCS", "NSC", "DNE"];

  function entriesFor(inp) {
    var n = parseInt(inp.getAttribute("data-entries") || "0", 10);
    if (n > 0) return n;
    var fleet = inp.closest(".fleet-section");
    return fleet ? fleet.querySelectorAll("tr[data-result-id]").length : 0;
  }

  function publicCell(raw, entries) {
    var v = String(raw || "").trim();
    if (!v) return "";
    var bare = v.replace(/^\(|\)$/g, "").replace(/\s+/g, "").toUpperCase();
    var code = null;
    if (PENALTY_CODES.indexOf(bare) >= 0) code = bare;
    else {
      var m = bare.match(/^(\d+(?:\.\d+)?)([A-Z]+)$/);
      if (m && PENALTY_CODES.indexOf(m[2]) >= 0) code = m[2];
    }
    var n = Math.max(parseInt(entries, 10) || 0, 0);
    if (code) return String(n + 1) + " " + code;
    var num = v.replace(/^\(|\)$/g, "").trim();
    if (/^\d+(\.0+)?$/.test(num)) return String(parseInt(num, 10));
    return v;
  }

  function save(inp) {
    if (!inp || !inp.classList.contains("club-score-input")) return;
    var rid = inp.getAttribute("data-result-id");
    var race = inp.getAttribute("data-race");
    if (!rid || !race || race.charAt(0) !== "R") return;
    var entries = entriesFor(inp);
    var v = publicCell(inp.value, entries);
    inp.value = v;
    var orig = (inp.getAttribute("data-original") || "").trim();
    if (v === orig) return;
    var instantPts = /[A-Z]/.test(v) ? entries + 1 : parseFloat(v);
    if (isFinite(instantPts)) {
      applyFleetRow({
        result_id: rid,
        total_points_raw: instantPts,
        nett_points_raw: instantPts,
      });
    }
    rerankFleet(fleetTable(inp));
    var seq = String(Number(inp.getAttribute("data-save-seq") || 0) + 1);
    inp.setAttribute("data-save-seq", seq);
    inp.classList.add("club-score-input--saving");
    inp.classList.remove("club-score-input--saved");
    var tok = sessionToken();
    fetch(withSession("/api/result/" + encodeURIComponent(rid) + "/race"), {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ race: race, value: v, session: tok }),
    })
      .then(function (r) {
        return r.json().then(function (j) {
          return { ok: r.ok, j: j };
        });
      })
      .then(function (o) {
        if (inp.getAttribute("data-save-seq") !== seq) return;
        inp.classList.remove("club-score-input--saving");
        if (!o.ok) {
          inp.value = inp.getAttribute("data-original") || "";
          inp.classList.remove("club-score-input--saved");
          inp.title = (o.j && (o.j.detail || o.j.error)) || "Save failed";
          return;
        }
        inp.title = "";
        if (o.j && o.j.race_scores && o.j.race_scores[race] != null) {
          v = String(o.j.race_scores[race]);
          inp.value = v;
        }
        inp.setAttribute("data-original", v);
        inp.classList.add("club-score-input--saved");
        applyServerFleet(o.j, fleetTable(inp));
        pushLive();
      })
      .catch(function () {
        if (inp.getAttribute("data-save-seq") !== seq) return;
        inp.classList.remove("club-score-input--saving");
        inp.value = inp.getAttribute("data-original") || "";
      });
  }

  function setPlain(td, val) {
    if (!td || val == null || val === "") return;
    var n = Number(val);
    td.textContent = isFinite(n) ? String(n) : String(val);
  }

  function rankLabel(rank) {
    var n = parseInt(rank, 10);
    if (!isFinite(n) || n < 1) return "";
    if (n === 1) return "1st";
    if (n === 2) return "2nd";
    if (n === 3) return "3rd";
    return String(n) + "th";
  }

  function applyFleetRow(row) {
    if (!row || row.result_id == null) return;
    var tr = document.querySelector('tr[data-result-id="' + row.result_id + '"]');
    if (!tr) return;
    setPlain(tr.querySelector("td.total-col"), row.total_points_raw);
    setPlain(tr.querySelector("td.nett-col"), row.nett_points_raw);
    var rankTd = tr.querySelector("td.rank-col") || tr.children[0];
    if (rankTd && row.rank != null && row.rank !== "") {
      rankTd.textContent = rankLabel(row.rank);
    }
    if (row.race_scores && typeof row.race_scores === "object") {
      Object.keys(row.race_scores).forEach(function (rk) {
        var cell = String(row.race_scores[rk] == null ? "" : row.race_scores[rk]);
        var box = tr.querySelector('.club-score-input[data-race="' + rk + '"]');
        if (box) {
          if (document.activeElement === box) return;
          box.value = cell;
          box.setAttribute("data-original", cell);
          return;
        }
        var td = tr.querySelector('td.race-col[data-race-key="' + rk + '"]');
        if (td && !td.querySelector("input")) td.textContent = cell;
      });
    }
  }

  function fleetTable(from) {
    var sec = from && from.closest ? from.closest(".fleet-section") : null;
    if (sec) return sec.querySelector("table.fleet-results-table") || sec.querySelector("table");
    return from && from.closest ? from.closest("table") : null;
  }

  function applyLiveFleets(data) {
    if (!data || !data.fleets) return;
    Object.keys(data.fleets).forEach(function (bid) {
      var rows = data.fleets[bid] || [];
      rows.forEach(applyFleetRow);
      var sec = document.querySelector('.fleet-section[data-block-id="' + bid + '"]');
      rerankFleet(fleetTable(sec) || (sec && sec.querySelector("table")));
    });
    document.querySelectorAll("table.fleet-results-table").forEach(rerankFleet);
  }

  function pollLive() {
    if (document.hidden) return;
    fetch("/api/regatta/2026-09-13-zvyc-cape-classic/cape-live-fleets", {
      credentials: "include",
      cache: "no-store",
    })
      .then(function (r) {
        return r.ok ? r.json() : null;
      })
      .then(function (j) {
        if (j && j.ok) applyLiveFleets(j);
      })
      .catch(function () {});
  }

  function pushLive() {
    pollLive();
    try {
      if (window.__capeLiveCh) window.__capeLiveCh.postMessage({ t: Date.now() });
    } catch (e) {}
  }

  function rowNett(tr) {
    var nettTd = tr.querySelector("td.nett-col");
    var n = parseFloat((nettTd && nettTd.textContent) || "");
    if (isFinite(n) && n > 0) return n;
    var totTd = tr.querySelector("td.total-col");
    n = parseFloat((totTd && totTd.textContent) || "");
    if (isFinite(n) && n > 0) return n;
    var sum = 0;
    var any = false;
    Array.prototype.forEach.call(tr.querySelectorAll(".club-score-input"), function (box) {
      var v = (box.value || "").trim();
      if (!v) return;
      any = true;
      var lead = parseFloat(v);
      if (isFinite(lead)) sum += lead;
      else if (/[A-Za-z]/.test(v)) sum += entriesFor(box) + 1;
    });
    return any ? sum : 9999;
  }

  function rerankFleet(table) {
    if (!table) return;
    var tb = table.tBodies && table.tBodies[0];
    if (!tb) return;
    var items = Array.prototype.map.call(tb.querySelectorAll("tr[data-result-id]"), function (tr) {
      return { tr: tr, nett: rowNett(tr) };
    });
    items.sort(function (a, b) {
      if (a.nett !== b.nett) return a.nett - b.nett;
      return Number(a.tr.getAttribute("data-result-id")) - Number(b.tr.getAttribute("data-result-id"));
    });
    items.forEach(function (it, i) {
      var rankTd = it.tr.querySelector("td.rank-col") || it.tr.children[0];
      if (rankTd) rankTd.textContent = it.nett >= 9999 ? "" : rankLabel(i + 1);
      it.tr.classList.remove("medal-gold", "medal-silver", "medal-bronze");
      if (it.nett < 9999) {
        if (i === 0) it.tr.classList.add("medal-gold");
        else if (i === 1) it.tr.classList.add("medal-silver");
        else if (i === 2) it.tr.classList.add("medal-bronze");
      }
      tb.appendChild(it.tr);
    });
  }

  function applyServerFleet(j, table) {
    if (!j) return;
    if (j.fleet && j.fleet.length) j.fleet.forEach(applyFleetRow);
    else {
      applyFleetRow({
        result_id: j.result_id,
        total_points_raw: j.total_points_raw,
        nett_points_raw: j.nett_points_raw,
        rank: j.rank,
        race_scores: j.race_scores,
      });
    }
    rerankFleet(table);
  }

  function wireCell(td, resultId) {
    if (!td || td.querySelector(".club-score-input")) return;
    if (td.closest(".total-col, .nett-col, .rank-col")) return;
    var race = (td.getAttribute("data-race-key") || "").trim().toUpperCase();
    if (!/^R\d+$/.test(race)) return;
    var current = (td.textContent || "").trim();
    td.textContent = "";
    var inp = document.createElement("input");
    inp.type = "text";
    inp.className = "club-score-input";
    inp.setAttribute("inputmode", "text");
    inp.setAttribute("autocomplete", "off");
    inp.setAttribute("maxlength", "48");
    inp.setAttribute("data-result-id", resultId);
    inp.setAttribute("data-race", race);
    var fleet = td.closest(".fleet-section");
    var entries = fleet ? fleet.querySelectorAll("tr[data-result-id]").length : 0;
    inp.setAttribute("data-entries", String(entries));
    inp.setAttribute("data-original", current);
    inp.setAttribute("aria-label", race + " position");
    inp.value = current;
    td.appendChild(inp);
    td.addEventListener("click", function () {
      inp.focus();
    });
    inp.addEventListener("blur", function () {
      save(inp);
    });
    inp.addEventListener("keydown", function (ev) {
      if (ev.key === "Enter" || ev.key === "ArrowDown") {
        ev.preventDefault();
        save(inp);
        focusOffset(inp, 1);
        return;
      }
      if (ev.key === "ArrowUp") {
        ev.preventDefault();
        save(inp);
        focusOffset(inp, -1);
      }
    });
  }

  function ensureR1(table) {
    if (!table) return;
    var thead = table.querySelector("thead tr");
    if (!thead) return;
    var hasR1 =
      thead.querySelector('th.race-col[data-race-key="R1"]') ||
      Array.prototype.some.call(thead.querySelectorAll("th"), function (th) {
        return String(th.textContent || "").replace(/\s+/g, "").toUpperCase() === "R1";
      });
    if (!hasR1) {
      var th = document.createElement("th");
      th.className = "race-col";
      th.setAttribute("data-race-key", "R1");
      th.textContent = "R1";
      var totalTh = thead.querySelector("th.total-col");
      if (totalTh) thead.insertBefore(th, totalTh);
      else thead.appendChild(th);
    }
    table.querySelectorAll("tbody tr[data-result-id]").forEach(function (tr) {
      if (tr.querySelector('td.race-col[data-race-key="R1"]')) return;
      var td = document.createElement("td");
      td.className = "race-col";
      td.setAttribute("data-race-key", "R1");
      var totalTd = tr.querySelector("td.total-col");
      if (totalTd) tr.insertBefore(td, totalTd);
      else tr.appendChild(td);
    });
  }

  function activate() {
    injectStyles();
    var page = document.querySelector(".regatta-page");
    if (!page) return;
    page.classList.add("regatta-page--club-score-edit");
    banner();
    page.querySelectorAll("table.fleet-results-table").forEach(ensureR1);
    page.querySelectorAll("tr[data-result-id]").forEach(function (tr) {
      var rid = tr.getAttribute("data-result-id");
      if (!rid) return;
      tr.querySelectorAll("td.race-col[data-race-key]").forEach(function (td) {
        wireCell(td, rid);
      });
    });
    var boxes = page.querySelectorAll(".club-score-input");
    var start = null;
    Array.prototype.forEach.call(boxes, function (box) {
      if (!start && !(box.value || "").trim()) start = box;
    });
    if (!start && boxes[0]) start = boxes[0];
    page.querySelectorAll("table.fleet-results-table").forEach(rerankFleet);
    if (start) start.focus();
  }

  pollLive();
  setInterval(function () {
    if (!document.hidden) pollLive();
  }, 2000);
  try {
    window.__capeLiveCh = new BroadcastChannel("cape-classic-live");
    window.__capeLiveCh.onmessage = function () {
      pollLive();
    };
  } catch (e) {}

  fetch(withSession("/auth/session?path=" + encodeURIComponent(path)), {
    credentials: "include",
    cache: "no-store",
  })
    .then(function (r) {
      return r.json();
    })
    .then(function (session) {
      if (canScore(session)) activate();
    })
    .catch(function () {});
})();
