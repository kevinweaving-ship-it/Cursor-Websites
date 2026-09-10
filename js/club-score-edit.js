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
      ".regatta-page--club-score-edit td.rank-col input{display:none!important}" +
      ".club-race-step{display:flex;flex-direction:column;gap:3px;margin-right:6px;flex:0 0 auto;align-items:stretch}" +
      ".club-race-step button{box-sizing:border-box;min-width:44px;min-height:32px;padding:0 6px;border:1.5px solid #1a2750;border-radius:4px;background:#fff;color:#1a2750;font:inherit;font-size:12px;font-weight:700;line-height:1;cursor:pointer}" +
      ".club-race-step button:disabled{opacity:.45;cursor:not-allowed}" +
      ".class-header-club-logo-col .club-race-step{order:-1}" +
      ".cape-crew .club-race-step{display:none!important}";
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
      "Type a place or OCS/DSQ. Extra DSQ = 15 DSQ. Empty clears. Enter = next. Tab/arrows save.";
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

  function parseScore(raw, entries) {
    var v = String(raw || "").trim();
    if (!v) return { ok: true, value: "" };
    var bare = v.replace(/^\(|\)$/g, "").replace(/\s+/g, "").toUpperCase();
    var code = null;
    if (PENALTY_CODES.indexOf(bare) >= 0) code = bare;
    else {
      var m = bare.match(/^(\d+(?:\.\d+)?)([A-Z]+)$/);
      if (m && PENALTY_CODES.indexOf(m[2]) >= 0) code = m[2];
    }
    var n = Math.max(parseInt(entries, 10) || 0, 0);
    if (code) return { ok: true, value: n ? String(n + 1) + " " + code : code };
    var num = v.replace(/^\(|\)$/g, "").trim();
    if (/^\d+(\.0+)?$/.test(num)) {
      var place = parseInt(num, 10);
      if (place === 0) return { ok: true, value: "" };
      if (n && (place < 1 || place > n + 1)) {
        return { ok: false, value: "", error: "Use 1–" + n + " or " + (n + 1) + " / OCS / DSQ" };
      }
      if (place < 1) return { ok: false, value: "", error: "Use a place or a code" };
      return { ok: true, value: String(place) };
    }
    return {
      ok: false,
      value: "",
      error: "Use a place 1–" + (n || "n") + " or OCS/DSQ/DNC",
    };
  }

  function publicCell(raw, entries) {
    var p = parseScore(raw, entries);
    return p.ok ? p.value : String(raw || "").trim();
  }

  function boxBusy(box) {
    return !!(
      box &&
      (box === document.activeElement ||
        box.classList.contains("club-score-input--saving") ||
        box.getAttribute("data-dirty") === "1")
    );
  }

  function markDirty(inp) {
    var entries = entriesFor(inp);
    var now = parseScore(inp.value, entries);
    var orig = parseScore(inp.getAttribute("data-original") || "", entries);
    if (now.ok && now.value === orig.value) inp.removeAttribute("data-dirty");
    else inp.setAttribute("data-dirty", "1");
  }

  function wholeSelected(inp) {
    return inp.selectionStart === 0 && inp.selectionEnd === String(inp.value || "").length;
  }

  function save(inp) {
    if (!inp || !inp.classList.contains("club-score-input")) return;
    if (inp._wcSaving) return;
    var rid = inp.getAttribute("data-result-id");
    var race = inp.getAttribute("data-race");
    if (!rid || !race || race.charAt(0) !== "R") return;
    var entries = entriesFor(inp);
    var parsed = parseScore(inp.value, entries);
    var orig = String(inp.getAttribute("data-original") || "");
    if (!parsed.ok) {
      inp.value = orig;
      inp.removeAttribute("data-dirty");
      inp.title = parsed.error;
      return;
    }
    var v = parsed.value;
    if (v === parseScore(orig, entries).value) {
      inp.removeAttribute("data-dirty");
      inp.title = "";
      return;
    }
    var seq = String(Number(inp.getAttribute("data-save-seq") || 0) + 1);
    inp.setAttribute("data-save-seq", seq);
    inp._wcSaving = true;
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
        inp._wcSaving = false;
        inp.classList.remove("club-score-input--saving");
        if (!o.ok) {
          inp.value = orig;
          inp.removeAttribute("data-dirty");
          inp.classList.remove("club-score-input--saved");
          inp.title = (o.j && (o.j.detail || o.j.error)) || "Save failed";
          return;
        }
        inp.title = "";
        inp.removeAttribute("data-dirty");
        if (o.j && o.j.race_scores && o.j.race_scores[race] != null) {
          v = String(o.j.race_scores[race]);
        }
        inp.setAttribute("data-original", v);
        if (document.activeElement !== inp) inp.value = v;
        inp.classList.add("club-score-input--saved");
        applyServerFleet(o.j, fleetTable(inp));
        pushLive();
      })
      .catch(function () {
        if (inp.getAttribute("data-save-seq") !== seq) return;
        inp._wcSaving = false;
        inp.classList.remove("club-score-input--saving");
        inp.value = orig;
        inp.removeAttribute("data-dirty");
      });
  }

  function setPlain(td, val) {
    if (!td) return;
    if (val == null || val === "") {
      td.textContent = "";
      return;
    }
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
      tr.querySelectorAll(".club-score-input").forEach(function (box) {
        if (boxBusy(box)) return;
        var rk = box.getAttribute("data-race");
        var cell = String(row.race_scores[rk] == null ? "" : row.race_scores[rk]);
        box.value = cell;
        box.setAttribute("data-original", cell);
      });
      Object.keys(row.race_scores).forEach(function (rk) {
        var cell = String(row.race_scores[rk] == null ? "" : row.race_scores[rk]);
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
      var sec = document.querySelector('.fleet-section[data-block-id="' + bid + '"]');
      var table = fleetTable(sec) || (sec && sec.querySelector("table"));
      if (table && table.querySelector(".club-score-input[data-dirty='1'], .club-score-input--saving, .club-score-input:focus")) {
        return;
      }
      var rows = data.fleets[bid] || [];
      rows.forEach(applyFleetRow);
      rerankFleet(table);
    });
  }

  function pollLive() {
    if (document.hidden) return;
    if (document.activeElement && document.activeElement.classList.contains("club-score-input")) return;
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
    td.addEventListener("click", function (ev) {
      if (ev.target === inp) return;
      inp.focus();
    });
    inp.addEventListener("input", function () {
      markDirty(inp);
      inp.title = "";
    });
    inp.addEventListener("focus", function () {
      requestAnimationFrame(function () {
        if (document.activeElement === inp && typeof inp.select === "function") inp.select();
      });
    });
    inp.addEventListener("blur", function () {
      save(inp);
    });
    inp.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape") {
        ev.preventDefault();
        inp.value = inp.getAttribute("data-original") || "";
        inp.removeAttribute("data-dirty");
        inp.title = "";
        return;
      }
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
        return;
      }
      if (ev.key === "Tab") {
        ev.preventDefault();
        save(inp);
        focusOffset(inp, ev.shiftKey ? -1 : 1);
        return;
      }
      if (ev.key === "ArrowLeft" && (inp.selectionStart === 0 || wholeSelected(inp))) {
        ev.preventDefault();
        save(inp);
        focusOffset(inp, -1);
        return;
      }
      if (ev.key === "ArrowRight" && (inp.selectionEnd === String(inp.value || "").length || wholeSelected(inp))) {
        ev.preventDefault();
        save(inp);
        focusOffset(inp, 1);
      }
    });
  }

  function raceKeyNum(key) {
    var m = String(key || "").toUpperCase().match(/^R(\d+)$/);
    return m ? parseInt(m[1], 10) : 0;
  }

  function fleetRaceCount(table) {
    var n = 0;
    if (!table) return 1;
    table.querySelectorAll("th.race-col[data-race-key], td.race-col[data-race-key]").forEach(function (el) {
      n = Math.max(n, raceKeyNum(el.getAttribute("data-race-key")));
    });
    table.querySelectorAll("thead th").forEach(function (th) {
      n = Math.max(n, raceKeyNum(String(th.textContent || "").replace(/\s+/g, "")));
    });
    return Math.max(n, 1);
  }

  function totalAnchor(row) {
    return (
      row.querySelector("th.total-col, td.total-col") ||
      Array.prototype.find.call(row.children || [], function (el) {
        return String(el.textContent || "").trim().toUpperCase() === "TOTAL";
      })
    );
  }

  function hasRaceHead(thead, key) {
    if (thead.querySelector('th.race-col[data-race-key="' + key + '"]')) return true;
    return Array.prototype.some.call(thead.querySelectorAll("th"), function (th) {
      return String(th.textContent || "").replace(/\s+/g, "").toUpperCase() === key;
    });
  }

  function ensureRace(table, n) {
    if (!table) return;
    var key = "R" + n;
    var thead = table.querySelector("thead tr");
    if (!thead) return;
    if (!hasRaceHead(thead, key)) {
      var th = document.createElement("th");
      th.className = "race-col";
      th.setAttribute("data-race-key", key);
      th.textContent = key;
      var totalTh = totalAnchor(thead);
      if (totalTh) thead.insertBefore(th, totalTh);
      else thead.appendChild(th);
    }
    table.querySelectorAll("tbody tr[data-result-id]").forEach(function (tr) {
      if (tr.querySelector('td.race-col[data-race-key="' + key + '"]')) return;
      var td = document.createElement("td");
      td.className = "race-col";
      td.setAttribute("data-race-key", key);
      var totalTd = totalAnchor(tr);
      if (totalTd) tr.insertBefore(td, totalTd);
      else tr.appendChild(td);
      wireCell(td, tr.getAttribute("data-result-id"));
    });
  }

  function ensureR1(table) {
    ensureRace(table, 1);
  }

  function dropRaceCol(table, n) {
    if (!table || n < 2) return;
    var key = "R" + n;
    table.querySelectorAll('[data-race-key="' + key + '"]').forEach(function (el) {
      if (el.parentNode) el.parentNode.removeChild(el);
    });
    table.querySelectorAll("thead th").forEach(function (th) {
      if (String(th.textContent || "").replace(/\s+/g, "").toUpperCase() === key && th.parentNode) {
        th.parentNode.removeChild(th);
      }
    });
  }

  function scoredRaceCount(table) {
    var keys = {};
    if (!table) return 0;
    table.querySelectorAll(".club-score-input").forEach(function (box) {
      if (String(box.value || "").replace(/[()]/g, "").trim()) {
        keys[box.getAttribute("data-race")] = 1;
      }
    });
    return Object.keys(keys).length;
  }

  function setSailedLine(sec, n) {
    if (!sec) return;
    var line = sec.querySelector(".sailed-line");
    if (!line) return;
    if (n == null) n = scoredRaceCount(fleetTable(sec));
    var disc = Math.floor(n / 5);
    var to = Math.max(0, n - disc);
    var entries = sec.querySelectorAll("tr[data-result-id]").length;
    var text = line.textContent || "";
    var em = text.match(/Entries:\s*(\d+)/i);
    if (em) entries = parseInt(em[1], 10) || entries;
    var scoring = "Appendix A";
    var sm = text.match(/Scoring system:\s*(.+)$/i);
    if (sm) scoring = sm[1].trim();
    line.textContent =
      "Sailed: " + n + ", Discards: " + disc + ", To count: " + to + ", Entries: " + entries + ", Scoring system: " + scoring;
    sec.setAttribute("data-races-sailed", String(n));
  }

  function lastRaceFilled(table, n) {
    var key = "R" + n;
    return Array.prototype.some.call(table.querySelectorAll('.club-score-input[data-race="' + key + '"]'), function (box) {
      return String(box.value || "").trim();
    });
  }

  function stepRaces(sec, delta) {
    if (!sec) return;
    var table = fleetTable(sec);
    var ridEl = sec.querySelector("tr[data-result-id]");
    var rid = ridEl && ridEl.getAttribute("data-result-id");
    if (!table || !rid) return;
    var current = fleetRaceCount(table);
    var tok = sessionToken();
    var btns = sec.querySelectorAll(".club-race-step button");
    Array.prototype.forEach.call(btns, function (b) {
      b.disabled = true;
    });
    fetch(withSession("/api/result/" + encodeURIComponent(rid) + "/fleet-races"), {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ delta: delta, session: tok }),
    })
      .then(function (r) {
        return r.json().then(function (j) {
          return { ok: r.ok, j: j };
        });
      })
      .then(function (o) {
        Array.prototype.forEach.call(btns, function (b) {
          b.disabled = false;
          if (b.classList.contains("club-race-step-sub")) b.title = "Remove last race";
        });
        if (!o.ok) {
          var err = (o.j && (o.j.detail || o.j.error)) || "Could not change races";
          var minusBtn = sec.querySelector(".club-race-step-sub");
          if (minusBtn) minusBtn.title = err;
          return;
        }
        var n = parseInt((o.j && o.j.races_sailed) || current + delta, 10) || current;
        if (n > current) {
          for (var i = current + 1; i <= n; i++) ensureRace(table, i);
        } else if (n < current) {
          for (var d = current; d > n; d--) dropRaceCol(table, d);
        }
        setSailedLine(sec, scoredRaceCount(table));
        applyServerFleet(o.j, table);
        pushLive();
      })
      .catch(function () {
        Array.prototype.forEach.call(btns, function (b) {
          b.disabled = false;
        });
      });
  }

  function injectRaceStepper(sec) {
    if (!sec || sec.classList.contains("cape-crew") || sec.id === "capeClassicCrew") return;
    if (sec.querySelector(".club-race-step")) return;
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
    sub.textContent = "R−";
    box.appendChild(add);
    box.appendChild(sub);
    add.addEventListener("click", function () {
      stepRaces(sec, 1);
    });
    sub.addEventListener("click", function () {
      stepRaces(sec, -1);
    });
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

  function activate() {
    injectStyles();
    var page = document.querySelector(".regatta-page");
    if (!page) return;
    page.classList.add("regatta-page--club-score-edit");
    banner();
    page.querySelectorAll(".fleet-section").forEach(injectRaceStepper);
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
