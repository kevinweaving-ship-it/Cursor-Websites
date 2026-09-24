/* Cape Classic club-admin R1 boxes. Total / Nett / Rank stay auto. */
(function () {
  var path = String((window.location && window.location.pathname) || "");
  if (
    path.indexOf("2026-09-13-zvyc-cape-classic") === -1 &&
    path.indexOf("2026-09-24-hmyc-dart-18-nationals") === -1
  )
    return;

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
      role === "club_manager" ||
      role === "admin" ||
      role === "super_admin" ||
      role === "superadmin" ||
      !!session.is_super_admin
    );
  }

  function isSuperAdmin(session) {
    var role = String((session && session.role) || "")
      .toLowerCase()
      .replace(/[\s-]+/g, "_");
    return role === "super_admin" || role === "superadmin" || !!(session && session.is_super_admin);
  }

  function saEditOn() {
    var page = document.querySelector(".regatta-page");
    return !!(page && page.classList.contains("regatta-page--super-admin-edit"));
  }

  function raceHeadKey(th) {
    var k = String((th && (th.getAttribute("data-race-key") || th.textContent)) || "")
      .replace(/\s+/g, "")
      .toUpperCase();
    var m = k.match(/^(R\d+)/);
    return m ? m[1] : "";
  }

  function raceCellValue(td) {
    if (!td) return "";
    var box = td.querySelector && td.querySelector(".club-score-input, .wc-result-field-input");
    var hide = td.querySelector && td.querySelector(".wc-sa-edit-hide");
    var fromBox = box ? String(box.value || "").replace(/[()]/g, "").trim() : "";
    var fromHide = hide ? String(hide.textContent || "").replace(/[()]/g, "").trim() : "";
    if (fromBox) return fromBox;
    if (fromHide) return fromHide;
    if (box) return "";
    return String(td.textContent || "").replace(/[()]/g, "").trim();
  }

  function paintRaceClosedState(table, closedSet, waitKey) {
    if (!table) return;
    var thead = table.querySelector("thead tr");
    if (!thead) return;
    thead.querySelectorAll("th.race-col").forEach(function (th) {
      var key = raceHeadKey(th);
      if (!key) return;
      th.setAttribute("data-race-key", key);
      var closed = !!(closedSet && closedSet[key]);
      var wait = key === waitKey;
      th.classList.toggle("race-col--closed", closed);
      th.classList.toggle("race-col--wait", wait);
      var idx = [].indexOf.call(thead.children, th);
      table.querySelectorAll("tbody tr").forEach(function (tr) {
        var td =
          tr.querySelector('td.race-col[data-race-key="' + key + '"]') ||
          (idx >= 0 ? tr.children[idx] : null);
        if (!td || !td.classList || !td.classList.contains("race-col")) return;
        td.setAttribute("data-race-key", key);
        td.classList.toggle("race-col--closed", closed);
        td.classList.toggle("race-col--wait", wait);
      });
    });
  }

  function closedFromDom(table) {
    var thead = table && table.querySelector("thead tr");
    var out = { closed: {}, waitKey: "", keys: [] };
    if (!thead) return out;
    thead.querySelectorAll("th.race-col").forEach(function (th) {
      var key = raceHeadKey(th);
      if (key) out.keys.push(key);
    });
    var rows = table.querySelectorAll("tbody tr[data-result-id]");
    if (!rows.length) rows = table.querySelectorAll("tbody tr");
    out.keys.forEach(function (key) {
      var th = thead.querySelector('th.race-col[data-race-key="' + key + '"]');
      if (!th) {
        Array.prototype.some.call(thead.querySelectorAll("th.race-col"), function (h) {
          if (raceHeadKey(h) === key) {
            th = h;
            return true;
          }
          return false;
        });
      }
      var idx = th ? [].indexOf.call(thead.children, th) : -1;
      var n = 0;
      var scored = 0;
      Array.prototype.forEach.call(rows, function (tr) {
        var td =
          tr.querySelector('td.race-col[data-race-key="' + key + '"]') ||
          (idx >= 0 ? tr.children[idx] : null);
        if (!td) return;
        n += 1;
        if (raceCellValue(td)) scored += 1;
      });
      if (n > 0 && scored >= n) out.closed[key] = 1;
      else if (!out.waitKey) out.waitKey = key;
    });
    return out;
  }

  function closedFromLiveRows(rows, keys) {
    var out = { closed: {}, waitKey: "" };
    var n = (rows || []).length;
    var scored = {};
    (rows || []).forEach(function (r) {
      var rs = r.race_scores || {};
      Object.keys(rs).forEach(function (k) {
        var key = String(k || "").toUpperCase();
        if (!/^R\d+$/.test(key)) return;
        if (String(rs[k] == null ? "" : rs[k]).replace(/[()]/g, "").trim()) {
          scored[key] = (scored[key] || 0) + 1;
        }
      });
    });
    (keys || Object.keys(scored).sort()).forEach(function (key) {
      if (n > 0 && (scored[key] || 0) >= n) out.closed[key] = 1;
      else if (!out.waitKey) out.waitKey = key;
    });
    return out;
  }

  function applySaRaceClosed(table, liveRows) {
    if (!table) return;
    var dom = closedFromDom(table);
    var live = liveRows ? closedFromLiveRows(liveRows, dom.keys) : { closed: {}, waitKey: "" };
    var closed = {};
    dom.keys.forEach(function (key) {
      if (dom.closed[key] || live.closed[key]) closed[key] = 1;
    });
    Object.keys(live.closed).forEach(function (key) {
      closed[key] = 1;
    });
    var waitKey = live.waitKey || dom.waitKey || "";
    if (waitKey && closed[waitKey]) waitKey = "";
    paintRaceClosedState(table, closed, waitKey);
  }

  function wireSaWaitOnly(table) {
    if (!table) return;
    applySaRaceClosed(table);
    table.querySelectorAll("tbody tr[data-result-id]").forEach(function (tr) {
      var rid = tr.getAttribute("data-result-id");
      if (!rid) return;
      tr.querySelectorAll("td.race-col.race-col--wait").forEach(function (td) {
        if (td.querySelector(".wc-result-field-input, .club-score-input")) return;
        wireCell(td, rid);
      });
    });
  }

  function watchSaToggle() {
    var page = document.querySelector(".regatta-page");
    if (!page || page._saRaceObs) return;
    var mo = new MutationObserver(function () {
      page.querySelectorAll("table.fleet-results-table").forEach(function (table) {
        applySaRaceClosed(table);
        if (saEditOn()) wireSaWaitOnly(table);
      });
    });
    mo.observe(page, { attributes: true, attributeFilter: ["class"] });
    page._saRaceObs = mo;
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
      ".club-score-input.club-score-input--dup{background:#fecaca;border-color:#b91c1c}" +
      ".regatta-page--club-score-edit th.race-col,.regatta-page--super-admin-edit th.race-col{font-size:inherit!important}" +
      ".regatta-page--club-score-edit th.race-col:not(.race-col--wait),.regatta-page--super-admin-edit th.race-col:not(.race-col--wait){color:#15803d!important;font-weight:700}" +
      ".regatta-page--club-score-edit th.race-col.race-col--wait,.regatta-page--super-admin-edit th.race-col.race-col--wait{color:inherit!important;font-weight:700}" +
      ".regatta-page--club-score-edit th.race-col:not(.race-col--wait) .wc-clear-race,.regatta-page--super-admin-edit th.race-col:not(.race-col--wait) .wc-clear-race,.regatta-page--club-score-edit th.race-col:not(.race-col--wait) input,.regatta-page--super-admin-edit th.race-col:not(.race-col--wait) input{display:none!important}" +
      ".regatta-page--club-score-edit td.race-col:not(.race-col--wait) .club-score-input,.regatta-page--club-score-edit td.race-col:not(.race-col--wait) .wc-result-field-input,.regatta-page--super-admin-edit td.race-col:not(.race-col--wait) .wc-result-field-input,.regatta-page--super-admin-edit td.race-col:not(.race-col--wait) .wc-result-field-input.wc-sa-edit-only{display:none!important}" +
      ".regatta-page--club-score-edit td.race-col:not(.race-col--wait) .wc-sa-edit-hide,.regatta-page--super-admin-edit td.race-col:not(.race-col--wait) .wc-sa-edit-hide{display:inline!important;font-size:inherit!important;font-weight:inherit}" +
      ".regatta-page--club-score-edit td.race-col.race-col--wait .club-score-input,.regatta-page--super-admin-edit td.race-col.race-col--wait .wc-result-field-input{font-size:calc(1em + 2px)!important;font-weight:700!important;height:auto;min-height:0;max-height:none;line-height:1.2}" +
      "@media (max-width:768px), (max-width:768px) and (orientation:portrait), (max-width:768px) and (max-aspect-ratio:1/1){" +
      ".regatta-page--club-score-edit th.race-col:not(.race-col--wait),.regatta-page--super-admin-edit th.race-col:not(.race-col--wait){color:#15803d!important;font-weight:700}" +
      ".regatta-page--club-score-edit td.race-col:not(.race-col--wait) .club-score-input,.regatta-page--club-score-edit td.race-col:not(.race-col--wait) .wc-result-field-input,.regatta-page--super-admin-edit td.race-col:not(.race-col--wait) .wc-result-field-input.wc-sa-edit-only{display:none!important}" +
      ".regatta-page--club-score-edit td.race-col:not(.race-col--wait) .wc-sa-edit-hide,.regatta-page--super-admin-edit td.race-col:not(.race-col--wait) .wc-sa-edit-hide{display:inline!important}" +
      "}" +
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
      if (n && (place < 1 || place > n)) {
        return { ok: false, value: "", error: "Use 1–" + n + " or OCS/DSQ" };
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

  function uniquePlace(raw, entries) {
    var p = parseScore(raw, entries);
    if (!p.ok || !p.value || /[A-Z]/.test(p.value)) return null;
    if (!/^\d+$/.test(p.value)) return null;
    var n = parseInt(p.value, 10);
    var max = Math.max(parseInt(entries, 10) || 0, 0);
    if (max && n === max + 1) return null;
    if (n >= 1 && (!max || n <= max)) return n;
    return null;
  }

  function placeTaken(inp, place) {
    if (place == null) return false;
    var race = inp.getAttribute("data-race");
    var entries = entriesFor(inp);
    return fleetInputs(inp).some(function (box) {
      if (box === inp) return false;
      if (box.getAttribute("data-race") !== race) return false;
      return uniquePlace(box.getAttribute("data-original") || box.value, entries) === place;
    });
  }

  function rejectDup(inp) {
    inp.value = inp.getAttribute("data-original") || "";
    inp.removeAttribute("data-dirty");
    inp.title = "";
    inp.classList.remove("club-score-input--saving", "club-score-input--saved");
    inp.classList.add("club-score-input--dup");
    if (inp._dupFlash) window.clearTimeout(inp._dupFlash);
    inp._dupFlash = window.setTimeout(function () {
      inp.classList.remove("club-score-input--dup");
      inp._dupFlash = null;
    }, 700);
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
      rejectDup(inp);
      return;
    }
    var v = parsed.value;
    if (v === parseScore(orig, entries).value) {
      inp.removeAttribute("data-dirty");
      inp.title = "";
      return;
    }
    if (placeTaken(inp, uniquePlace(v, entries))) {
      rejectDup(inp);
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
          rejectDup(inp);
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

  /* Poll used to wipe race cells with textContent ("20 DNC"), which killed
     wc-score/wc-code so the code flashed small then went full-size. Paint
     the same split HTML the sheet shipped with. Skip if already correct. */
  var RACE_CODE_RE = /^(DNC|DNS|DNF|DNR|RET|DSQ|UFD|BFD|DPI|OCS|NSC|DNE|ZFP|SCP|RDG|TLE)$/i;
  var NUM_CODE_RE = /^(\d+(?:\.\d+)?)\s+(DNC|DNS|DNF|DNR|RET|DSQ|UFD|BFD|DPI|OCS|NSC|DNE|ZFP|SCP|RDG|TLE)$/i;

  function fmtScoreNum(s) {
    var raw = String(s == null ? "" : s).trim();
    if (!raw) return "";
    var n = Number(raw);
    if (isFinite(n) && n === Math.floor(n)) return String(Math.floor(n));
    return raw;
  }

  function racePaintKey(raw) {
    var cell = String(raw == null ? "" : raw).trim();
    var discarded = cell.charAt(0) === "(" && cell.slice(-1) === ")";
    var src = discarded ? cell.slice(1, -1).trim() : cell;
    var m = src.match(NUM_CODE_RE);
    if (m) return (discarded ? "D|" : "C|") + (discarded ? "(" + fmtScoreNum(m[1]) + ")" : fmtScoreNum(m[1])) + "|" + m[2].toUpperCase();
    if (src && RACE_CODE_RE.test(src)) return (discarded ? "D|" : "C|") + "|" + src.toUpperCase();
    return (discarded ? "N|" : "S|") + fmtScoreNum(src.replace(/[()]/g, "").trim());
  }

  function raceDomKey(td) {
    if (!td) return "";
    var discarded = td.classList.contains("disc");
    var codeEl = td.querySelector(".wc-code");
    var scoreEl = td.querySelector(".wc-score");
    if (codeEl) {
      return (discarded ? "D|" : "C|") + ((scoreEl && scoreEl.textContent) || "").trim() + "|" + (codeEl.textContent || "").trim().toUpperCase();
    }
    return (discarded ? "N|" : "S|") + ((td.textContent || "").replace(/[()]/g, "").trim());
  }

  function paintRaceCell(td, raw) {
    if (!td || td.querySelector("input")) return;
    var cell = String(raw == null ? "" : raw).trim();
    if (raceDomKey(td) === racePaintKey(cell)) {
      td.setAttribute("data-live-cell", cell);
      return;
    }
    var discarded = cell.charAt(0) === "(" && cell.slice(-1) === ")";
    var src = discarded ? cell.slice(1, -1).trim() : cell;
    td.classList.remove("disc", "code", "score-counts");
    td.classList.add("race-col");
    var html = "";
    var m = src.match(NUM_CODE_RE);
    if (!src) {
      html = "";
    } else if (m) {
      td.classList.add("code");
      if (discarded) td.classList.add("disc");
      var shown = fmtScoreNum(m[1]);
      if (discarded) shown = "(" + shown + ")";
      html =
        '<span class="' +
        (discarded ? "code disc" : "code") +
        '"><span class="wc-score">' +
        shown +
        '</span><span class="wc-code">' +
        m[2].toUpperCase() +
        "</span></span>";
    } else if (RACE_CODE_RE.test(src)) {
      td.classList.add("code");
      if (discarded) td.classList.add("disc");
      html =
        '<span class="' +
        (discarded ? "code disc" : "code") +
        '"><span class="wc-code">' +
        src.toUpperCase() +
        "</span></span>";
    } else if (discarded) {
      td.classList.add("disc");
      html = '<span class="disc">(' + fmtScoreNum(src.replace(/[()]/g, "").trim()) + ")</span>";
    } else {
      td.classList.add("score-counts");
      html = '<span class="score-counts">' + fmtScoreNum(src) + "</span>";
    }
    td.innerHTML = html;
    td.setAttribute("data-live-cell", cell);
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
      tr.setAttribute("data-official-rank", String(row.rank));
      rankTd.textContent = rankLabel(row.rank);
      tr.classList.remove("medal-gold", "medal-silver", "medal-bronze");
      var painted = parseInt(row.rank, 10);
      if (painted === 1) tr.classList.add("medal-gold");
      else if (painted === 2) tr.classList.add("medal-silver");
      else if (painted === 3) tr.classList.add("medal-bronze");
    } else {
      tr.removeAttribute("data-official-rank");
      if (rankTd) rankTd.textContent = "";
      tr.classList.remove("medal-gold", "medal-silver", "medal-bronze");
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
        if (td && !td.querySelector("input")) paintRaceCell(td, cell);
      });
    }
  }

  function fleetTable(from) {
    var sec = from && from.closest ? from.closest(".fleet-section") : null;
    if (sec) return sec.querySelector("table.fleet-results-table") || sec.querySelector("table");
    return from && from.closest ? from.closest("table") : null;
  }

  function paintAsAt(iso) {
    var el = document.querySelector(".regatta-status-as-at-date");
    if (!el || !iso) return;
    var d = new Date(iso);
    if (isNaN(d.getTime())) return;
    var parts = new Intl.DateTimeFormat("en-GB", {
      timeZone: "Africa/Johannesburg",
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }).formatToParts(d);
    var get = function (t) {
      var x = parts.find(function (p) {
        return p.type === t;
      });
      return x ? x.value : "";
    };
    el.textContent = [get("day"), get("month"), get("year"), get("hour") + ":" + get("minute")].join("\u00a0");
  }

  function applyLiveFleets(data) {
    if (!data || !data.fleets) return;
    paintAsAt(data.as_at_time);
    Object.keys(data.fleets).forEach(function (bid) {
      var sec = document.querySelector('.fleet-section[data-block-id="' + bid + '"]');
      var table = fleetTable(sec) || (sec && sec.querySelector("table"));
      if (table && table.querySelector(".club-score-input[data-dirty='1'], .club-score-input--saving, .club-score-input:focus")) {
        return;
      }
      var rows = data.fleets[bid] || [];
      rows.forEach(applyFleetRow);
      /* Official A8 order on the sheet: rerankFleet restores it and rejects result_id order. */
      rerankFleet(table);
      applySaRaceClosed(table, rows);
      wireSaWaitOnly(table);
    });
  }

  function liveFleetsUrl() {
    var m = path.match(/\/regatta\/([^/?#]+)/);
    var slug = m ? m[1] : "";
    if (!slug) return "";
    return "/api/regatta/" + encodeURIComponent(slug) + "/cape-live-fleets";
  }

  function pollLive() {
    if (document.hidden) return;
    if (document.activeElement && document.activeElement.classList.contains("club-score-input")) return;
    var url = liveFleetsUrl();
    if (!url) return;
    fetch(url, {
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

  function cellScore(el) {
    if (!el) return "";
    if (el.classList && el.classList.contains("club-score-input")) {
      return String(el.value || "").replace(/[()]/g, "").trim();
    }
    if (el.querySelector && el.querySelector("input")) return "";
    return String(el.textContent || "").replace(/[()]/g, "").trim();
  }

  function busyRaceKey(table) {
    var n = 0;
    if (!table) return "";
    table.querySelectorAll(".club-score-input, td.race-col[data-race-key]").forEach(function (el) {
      var key = el.getAttribute("data-race") || el.getAttribute("data-race-key");
      if (cellScore(el)) n = Math.max(n, raceKeyNum(key));
    });
    return n ? "R" + n : "";
  }

  function rowHasRace(tr, key) {
    if (!key || !tr) return false;
    var box = tr.querySelector('.club-score-input[data-race="' + key + '"]');
    if (box) return !!cellScore(box);
    return !!cellScore(tr.querySelector('td.race-col[data-race-key="' + key + '"]'));
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

  function racePlacesSailOrder(tr) {
    var out = [];
    tr.querySelectorAll("td.race-col[data-race-key]").forEach(function (td) {
      var box = td.querySelector(".club-score-input");
      var raw = box ? String(box.value || "") : String(td.textContent || "");
      var n = parseFloat(raw.replace(/[()]/g, "").trim());
      if (isFinite(n)) out.push(n);
    });
    return out;
  }

  /* Appendix A8: A8.1 best→worst, then A8.2 last race in sail order. Never result_id. */
  function a8cmp(trA, trB) {
    var a = racePlacesSailOrder(trA);
    var b = racePlacesSailOrder(trB);
    var as = a.slice().sort(function (x, y) { return x - y; });
    var bs = b.slice().sort(function (x, y) { return x - y; });
    var n = Math.max(as.length, bs.length);
    var i, va, vb;
    for (i = 0; i < n; i++) {
      va = i < as.length ? as[i] : 9999;
      vb = i < bs.length ? bs[i] : 9999;
      if (va !== vb) return va - vb;
    }
    va = a.length ? a[a.length - 1] : 9999;
    vb = b.length ? b[b.length - 1] : 9999;
    return va - vb;
  }

  function fleetHasScores(table) {
    if (!table) return false;
    var any = false;
    table.querySelectorAll(".club-score-input, td.race-col[data-race-key]").forEach(function (el) {
      if (cellScore(el)) any = true;
    });
    return any;
  }

  function paintOfficialRanks(tb) {
    var all = Array.prototype.slice.call(tb.querySelectorAll("tr[data-result-id]"));
    var locked = all.filter(function (tr) { return tr.hasAttribute("data-official-rank"); });
    var rest = all.filter(function (tr) { return !tr.hasAttribute("data-official-rank"); });
    locked.sort(function (a, b) {
      return (Number(a.getAttribute("data-official-rank")) || 9999) -
        (Number(b.getAttribute("data-official-rank")) || 9999);
    });
    locked.forEach(function (tr) {
      var rankTd = tr.querySelector("td.rank-col") || tr.children[0];
      var n = Number(tr.getAttribute("data-official-rank"));
      tr.classList.remove("medal-gold", "medal-silver", "medal-bronze");
      if (rankTd) {
        rankTd.textContent = n >= 1 ? rankLabel(n) : "";
      }
      if (n === 1) tr.classList.add("medal-gold");
      else if (n === 2) tr.classList.add("medal-silver");
      else if (n === 3) tr.classList.add("medal-bronze");
      tb.appendChild(tr);
    });
    rest.forEach(function (tr) {
      var rankTd = tr.querySelector("td.rank-col") || tr.children[0];
      tr.classList.remove("medal-gold", "medal-silver", "medal-bronze");
      if (rankTd) rankTd.textContent = "";
      tb.appendChild(tr);
    });
  }

  function rerankFleet(table) {
    if (!table) return;
    var tb = table.tBodies && table.tBodies[0];
    if (!tb) return;
    var official = tb.querySelectorAll("tr[data-official-rank]");
    if (official.length && fleetHasScores(table)) {
      /* Server A8 order — still paint 1st/2nd. Empty rank cells were the Dart bug. */
      paintOfficialRanks(tb);
      return;
    }
    if (official.length && !fleetHasScores(table)) {
      /* Entry list / empty R1 must not lock Rank blank. */
      Array.prototype.forEach.call(official, function (tr) {
        tr.removeAttribute("data-official-rank");
        var rankTd = tr.querySelector("td.rank-col") || tr.children[0];
        if (rankTd) rankTd.textContent = "";
        tr.classList.remove("medal-gold", "medal-silver", "medal-bronze");
      });
    }
    var busy = busyRaceKey(table);
    var items = Array.prototype.map.call(tb.querySelectorAll("tr[data-result-id]"), function (tr) {
      return { tr: tr, nett: rowNett(tr), qual: !busy || rowHasRace(tr, busy) };
    });
    items.sort(function (a, b) {
      if (a.qual !== b.qual) return a.qual ? -1 : 1;
      if (a.nett !== b.nett) return a.nett - b.nett;
      return a8cmp(a.tr, b.tr);
    });
    var q = 0;
    items.forEach(function (it) {
      var rankTd = it.tr.querySelector("td.rank-col") || it.tr.children[0];
      it.tr.classList.remove("medal-gold", "medal-silver", "medal-bronze");
      if (it.qual && it.nett < 9999) {
        q += 1;
        if (rankTd) rankTd.textContent = rankLabel(q);
        if (q === 1) it.tr.classList.add("medal-gold");
        else if (q === 2) it.tr.classList.add("medal-silver");
        else if (q === 3) it.tr.classList.add("medal-bronze");
      } else if (rankTd) {
        rankTd.textContent = "";
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
    paintAsAt(j.as_at_time);
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

  function activate(session) {
    injectStyles();
    var page = document.querySelector(".regatta-page");
    if (!page) return;
    page.classList.add("regatta-page--club-score-edit");
    var crew = page.querySelector("#capeClassicCrew");
    if (crew) crew.classList.add("cape-crew--admin");
    banner();
    watchSaToggle();
    if (isSuperAdmin(session)) {
      var tog = document.getElementById("regattaSaEditToggle");
      if (tog) {
        page.classList.toggle("regatta-page--super-admin-edit", !!tog.checked);
        if (!tog._saBound) {
          tog.addEventListener("change", function () {
            page.classList.toggle("regatta-page--super-admin-edit", !!tog.checked);
          });
          tog._saBound = true;
        }
      } else {
        page.classList.add("regatta-page--super-admin-edit");
      }
      page.querySelectorAll(".fleet-section").forEach(injectRaceStepper);
      page.querySelectorAll("table.fleet-results-table").forEach(function (table) {
        ensureR1(table);
        applySaRaceClosed(table);
        wireSaWaitOnly(table);
        rerankFleet(table);
      });
      return;
    }
    page.querySelectorAll(".fleet-section").forEach(injectRaceStepper);
    page.querySelectorAll("table.fleet-results-table").forEach(function (table) {
      ensureR1(table);
      applySaRaceClosed(table);
      wireSaWaitOnly(table);
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
      if (canScore(session)) activate(session);
    })
    .catch(function () {});
})();
