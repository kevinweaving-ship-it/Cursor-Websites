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
    return role === "club_admin" || role === "clubadmin" || !!session.is_super_admin;
  }

  function injectStyles() {
    if (document.getElementById("clubScoreEditCss")) return;
    var st = document.createElement("style");
    st.id = "clubScoreEditCss";
    st.textContent =
      ".club-score-banner{margin:12px 0 0;padding:10px 12px;border:2px solid #1a2750;border-radius:8px;background:#f8fafc;color:#1a2750;font-weight:700;font-size:13px}" +
      ".club-score-input{box-sizing:border-box;width:2.4rem;min-width:2.2rem;height:22px;min-height:22px;max-height:22px;padding:0 2px;text-align:center;font:inherit;font-size:12px;line-height:20px;font-weight:700;border:1.5px solid #1a2750;border-radius:4px;background:#fff;color:#1a2750}" +
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
      "Type place, Enter = next boat. 1–n once each. 10 / OCS / DSQ for a code. Total, Nett, Rank auto.";
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

  function save(inp) {
    if (!inp || !inp.classList.contains("club-score-input")) return;
    var rid = inp.getAttribute("data-result-id");
    var race = inp.getAttribute("data-race");
    if (!rid || !race || race.charAt(0) !== "R") return;
    var v = (inp.value || "").trim();
    var orig = (inp.getAttribute("data-original") || "").trim();
    if (v === orig) return;
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
          return;
        }
        inp.setAttribute("data-original", v);
        inp.classList.add("club-score-input--saved");
        applyFleetRow({
          result_id: rid,
          total_points_raw: o.j.total_points_raw,
          nett_points_raw: o.j.nett_points_raw,
          rank: o.j.rank,
        });
        if (o.j.fleet && o.j.fleet.length) o.j.fleet.forEach(applyFleetRow);
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

  function applyFleetRow(row) {
    if (!row || row.result_id == null) return;
    var tr = document.querySelector('tr[data-result-id="' + row.result_id + '"]');
    if (!tr) return;
    setPlain(tr.querySelector("td.total-col"), row.total_points_raw);
    setPlain(tr.querySelector("td.nett-col"), row.nett_points_raw);
    setPlain(tr.querySelector("td.rank-col"), row.rank);
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
    inp.setAttribute("data-original", current);
    inp.setAttribute("aria-label", race + " position");
    inp.value = current;
    td.appendChild(inp);
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
    if (start) start.focus();
  }

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
