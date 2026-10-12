/**
 * MAC TSL WC — compact Event URL results + admin. Same .card / .table / .section-title.
 * Only /regatta/2026-10-17-mac-tsl-wc-team-sailing. No club-score-edit.
 */
(function () {
  "use strict";
  if (window.__SSA_MAC_TSL_ADMIN__) return;
  window.__SSA_MAC_TSL_ADMIN__ = true;

  var RID = "2026-10-17-mac-tsl-wc-team-sailing";
  var JS_VER = "20261012p";
  var CSS_ID = "mac-tsl-admin-css";
  var ROOT_ID = "macTslAdmin";
  var MATCHES_ID = "macTslMatches";
  var SCHED_ID = "macTslSchedule";
  var state = { teams: [], matches: [], standings: [], format: "rr28", settings: {}, schedule: {} };
  var selectedMatchNo = 0;
  var KNOWN = {
    MATIES: {
      helms: [
        { name: "Corben Smith", sas_id: "20389" },
        { name: "Conrad Holm", sas_id: "8178" },
        { name: "Chiara Fruet", sas_id: "6497" }
      ],
      crews: [
        { name: "Shakur Abrahams", sas_id: "" },
        { name: "Nadia Bahnemann", sas_id: "" },
        { name: "Robyn Rosselli", sas_id: "" }
      ]
    },
    "Eden District": {
      sailors: [
        { name: "Lulonke Lenks", sas_id: "15711" },
        { name: "Christian Cilliers", sas_id: "13488" },
        { name: "Isabella Watson", sas_id: "27609" },
        { name: "Arthur Watson", sas_id: "27610" },
        { name: "Owen Conradie", sas_id: "23531" },
        { name: "Rainier Lamprecht", sas_id: "28588" }
      ]
    }
  };

  function pathRid() {
    var path = String((window.location && window.location.pathname) || "").replace(/\/+$/, "").toLowerCase();
    var m = path.match(/^\/regatta\/([^/]+)/);
    return m ? m[1] : "";
  }
  function onThisEvent() {
    var page = document.querySelector(".regatta-page");
    return pathRid() === RID || (page && page.getAttribute("data-mac-tsl") === "1");
  }
  function isSaEdit() {
    var p = document.querySelector(".regatta-page");
    return !!(p && p.classList.contains("regatta-page--super-admin-edit"));
  }
  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }
  function api(path, opts) {
    return fetch(path, Object.assign({ credentials: "same-origin" }, opts || {})).then(function (r) {
      return r.text().then(function (t) {
        var j = null;
        try { j = t ? JSON.parse(t) : null; } catch (e) {}
        if (!r.ok) {
          var d = j && (j.detail || j.error);
          throw new Error(typeof d === "string" ? d : "Save failed " + r.status);
        }
        return j;
      });
    });
  }
  function injectCss() {
    var s = document.getElementById(CSS_ID);
    if (!s) {
      s = document.createElement("style");
      s.id = CSS_ID;
      document.head.appendChild(s);
    }
    s.textContent = [
      ".regatta-page[data-mac-tsl=\"1\"]{overflow-x:hidden}",
      ".regatta-page[data-mac-tsl=\"1\"] .table-wrapper,.regatta-page[data-mac-tsl=\"1\"] .table-container{overflow-x:auto;-webkit-overflow-scrolling:touch}",
      "#macTslAdmin,#macTslSchedule{display:block;margin:12px 0}",
      "#macTslMatches{display:none;margin:12px 0}",
      ".regatta-page--super-admin-edit #macTslMatches{display:block}",
      "#macTslAdmin .tsl-edit{display:none}",
      ".regatta-page--super-admin-edit #macTslAdmin .tsl-edit{display:block}",
      "#macTslAdmin .tsl-public{display:block}",
      ".regatta-page--super-admin-edit #macTslAdmin .tsl-public{display:none}",
      "#macTslSchedule .tsl-edit{display:none}",
      ".regatta-page--super-admin-edit #macTslSchedule .tsl-edit{display:block}",
      "#macTslAdmin .section-title,#macTslMatches .section-title,#macTslSchedule .section-title{margin:0 0 0.4rem;padding-bottom:0.35rem}",
      ".tsl-team{margin:0 0 10px}",
      ".tsl-team-head{display:flex;align-items:center;gap:8px;margin:0 0 6px}",
      ".tsl-team-logo{width:36px;height:28px;object-fit:contain;background:#fff}",
      ".tsl-team-logo--empty{display:inline-block;width:36px;height:28px;background:#f5f7fa;border:1px dashed #cbd5e1}",
      ".tsl-team-head strong{color:#001f3f;font-size:0.9rem}",
      ".tsl-field{display:flex;flex-direction:column;gap:2px;min-width:0;flex:1 1 120px}",
      ".tsl-field label{font-size:0.85rem;font-weight:700;color:#001f3f;text-transform:uppercase;letter-spacing:.02em}",
      ".tsl-field input,.tsl-field select,.tsl-boats select{min-height:36px;padding:4px 8px;border:1.5px solid #001f3f;border-radius:6px;font-size:13px;color:#1e293b;background:#fff;width:100%;box-sizing:border-box}",
      ".tsl-boats th,.tsl-boats td{padding:0.4rem 0.6rem;border-bottom:1px solid #e0e0e0;vertical-align:top;text-align:left;overflow-wrap:anywhere;word-break:break-word}",
      ".tsl-sas{display:block;margin-top:2px;font-size:0.9rem;color:#334155;overflow-wrap:anywhere}",
      ".tsl-field input,.tsl-field select,.tsl-boats select{max-width:100%}",
      ".tsl-sas--missing{color:#b91c1c}",
      ".tsl-ac{position:relative}",
      ".tsl-ac-list{position:absolute;left:0;right:0;z-index:80;margin:2px 0 0;padding:4px 0;list-style:none;background:#fff;border:2px solid #001f3f;border-radius:8px;max-height:200px;overflow-y:auto}",
      ".tsl-ac-list li{margin:0;padding:6px 8px;cursor:pointer;font-size:0.9rem;color:#1a2750}",
      ".tsl-ac-list li:hover{background:#e0e7ff}",
      ".tsl-ac-list .tsl-ac-sub{display:block;font-size:0.85rem;color:#64748b}",
      ".tsl-add,.tsl-save,.tsl-del{min-height:36px;padding:6px 12px;border:2px solid #1a2750;border-radius:6px;background:#fff;color:#1a2750;font-weight:700;font-size:14px;cursor:pointer}",
      ".tsl-del{color:#DC143C;border-color:#DC143C}",
      ".tsl-warn{color:#b91c1c;font-size:0.9rem;margin:4px 0 0}",
      ".tsl-msg{color:#334155;font-size:0.9rem;margin:6px 0}",
      ".tsl-match{margin:0}",
      ".tsl-sides{display:flex;gap:8px;flex-wrap:wrap}",
      ".tsl-side{flex:1 1 220px;min-width:0}",
      ".tsl-side h3{margin:0 0 6px;color:#001f3f;font-size:0.85rem;font-weight:700;text-transform:uppercase}",
      ".tsl-row2{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 8px}",
      ".club-race-step.tsl-mstep{display:none;align-items:center;gap:6px;flex:0 0 auto}",
      ".regatta-page--super-admin-edit .club-race-step.tsl-mstep{display:inline-flex}",
      ".tsl-blue{color:#1d4ed8}",
      ".tsl-green{color:#15803d}",
      ".regatta-page[data-mac-tsl=\"1\"] th.tsl-hide-mp,.regatta-page[data-mac-tsl=\"1\"] td.tsl-hide-mp{display:none}",
      ".regatta-page[data-mac-tsl=\"1\"] .tsl-col-wins{font-weight:800;color:#1a2750;text-align:center}",
      ".regatta-page[data-mac-tsl=\"1\"] .tsl-mcol{text-align:center;font-weight:800}",
      "@media (max-width: 480px) and (orientation: portrait){",
      ".regatta-page[data-mac-tsl=\"1\"] th.tsl-ml-only,.regatta-page[data-mac-tsl=\"1\"] td.tsl-ml-only{display:none!important}",
      "}",
      "@media (orientation: landscape), (min-width: 600px){",
      ".regatta-page[data-mac-tsl=\"1\"] th.tsl-ml-only,.regatta-page[data-mac-tsl=\"1\"] td.tsl-ml-only{display:table-cell}",
      "}"
    ].join("");
  }

  function fleetSection() {
    return document.querySelector(".regatta-page[data-mac-tsl=\"1\"] .fleet-section") ||
      document.querySelector(".regatta-page .fleet-section") ||
      document.querySelector(".regatta-page");
  }
  function resultsTable() {
    var sec = fleetSection();
    return (sec && (sec.querySelector("table.fleet-results-table") || sec.querySelector("table"))) || null;
  }
  function knownFor(team) {
    var name = (team && (team.team_name || team.club_abbrev)) || "";
    return KNOWN[name] || KNOWN[String(name).toUpperCase()] || null;
  }
  function assignedIds(team) {
    var ids = {};
    ((team && team.boats) || []).forEach(function (b) {
      if (b.helm && b.helm.sas_id) ids[String(b.helm.sas_id)] = 1;
      if (b.crew && b.crew.sas_id) ids[String(b.crew.sas_id)] = 1;
    });
    return ids;
  }
  function unassignedLine(team) {
    var known = knownFor(team);
    if (!known) return "";
    var have = assignedIds(team);
    var pending = [];
    (known.helms || []).concat(known.crews || []).concat(known.sailors || []).forEach(function (s) {
      if (s.sas_id && have[String(s.sas_id)]) return;
      pending.push(s.sas_id ? (s.name + " " + s.sas_id) : s.name);
    });
    return pending.length ? pending.join(" · ") : "";
  }

  function bindTypeahead(input, kind, getUrl, onPick) {
    var wrap = input.closest(".tsl-ac") || input.parentNode;
    var list = wrap.querySelector(".tsl-ac-list");
    if (!list) {
      list = document.createElement("ul");
      list.className = "tsl-ac-list";
      list.hidden = true;
      wrap.appendChild(list);
    }
    var t = null;
    function hide() { list.hidden = true; list.innerHTML = ""; }
    function show(items) {
      list.innerHTML = "";
      if (!items.length) { hide(); return; }
      items.forEach(function (it) {
        var li = document.createElement("li");
        if (kind === "club") {
          li.innerHTML = esc(it.code || it.name) + '<span class="tsl-ac-sub">' + esc(it.name || "") + "</span>";
        } else {
          var sas = it.sas_id ? "SAS " + it.sas_id : "SAS missing — not invented";
          li.innerHTML = esc(it.name || it.full_name || "") + '<span class="tsl-ac-sub">' + esc(sas + (it.club ? " · " + it.club : "")) + "</span>";
        }
        li.addEventListener("mousedown", function (e) {
          e.preventDefault();
          onPick(it);
          hide();
        });
        list.appendChild(li);
      });
      list.hidden = false;
    }
    input.addEventListener("input", function () {
      var q = input.value.trim();
      clearTimeout(t);
      t = setTimeout(function () {
        api(getUrl(q)).then(function (d) {
          show(kind === "club" ? (d.clubs || []) : (d.sailors || []));
        }).catch(function () { hide(); });
      }, 180);
    });
    input.addEventListener("blur", function () { setTimeout(hide, 180); });
  }

  function sailorCell(boatNo, role, sailor) {
    var sid = sailor && sailor.sas_id ? String(sailor.sas_id) : "";
    var name = sailor && sailor.name ? sailor.name : "";
    var warn = name && !sid;
    return (
      '<div class="tsl-ac">' +
        '<input type="text" data-role="' + role + '" data-boat="' + boatNo + '" value="' + esc(name) + '" placeholder="' + role + '" autocomplete="off" />' +
        '<input type="hidden" data-sas-role="' + role + '" data-boat="' + boatNo + '" value="' + esc(sid) + '" />' +
        '<span class="tsl-sas' + (warn ? " tsl-sas--missing" : "") + '">' +
          (sid ? "SAS " + esc(sid) : (name ? "SAS missing — not invented" : "")) +
        "</span>" +
      "</div>"
    );
  }

  function teamPanelHtml(team) {
    team = team || {};
    var boats = team.boats || [{ boat_no: 1 }, { boat_no: 2 }, { boat_no: 3 }];
    var logo = team.club_logo
      ? '<img class="tsl-team-logo" src="' + esc(team.club_logo) + '" alt="">'
      : '<span class="tsl-team-logo--empty"></span>';
    var rows = "";
    for (var n = 1; n <= 3; n += 1) {
      var b = boats.filter(function (x) { return Number(x.boat_no) === n; })[0] || { boat_no: n };
      rows += "<tr><th>" + n + "</th><td>" + sailorCell(n, "helm", b.helm) + "</td><td>" + sailorCell(n, "crew", b.crew) + "</td></tr>";
    }
    var pending = unassignedLine(team);
    return (
      '<div class="tsl-team" data-team-id="' + esc(team.team_id || "") + '">' +
        '<div class="tsl-team-head">' + logo + "<strong>" + esc(team.team_name || team.club_name || "Team") + "</strong></div>" +
        '<div class="tsl-row2">' +
          '<div class="tsl-field tsl-ac"><label>Club</label>' +
            '<input type="text" data-field="club" value="' + esc(team.club_name || team.club_abbrev || "") + '" placeholder="Club" autocomplete="off" />' +
            '<input type="hidden" data-field="club_id" value="' + esc(team.club_id || "") + '" />' +
          "</div>" +
          '<div class="tsl-field"><label>Team</label>' +
            '<input type="text" data-field="team_name" value="' + esc(team.team_name || "") + '" />' +
          "</div>" +
        "</div>" +
        '<div class="table-container"><table class="table tsl-boats"><thead><tr><th></th><th>Helm</th><th>Crew</th></tr></thead><tbody>' +
        rows + "</tbody></table></div>" +
        (pending ? '<p class="tsl-msg">Assign: ' + esc(pending) + "</p>" : "") +
        '<div class="tsl-row2">' +
          '<button type="button" class="tsl-save">Save Team</button>' +
          (team.team_id ? '<button type="button" class="tsl-del">Remove</button>' : "") +
        "</div>" +
        '<div class="tsl-msg"></div>' +
      "</div>"
    );
  }

  function publicTeamHtml(team) {
    var logo = team.club_logo
      ? '<img class="tsl-team-logo" src="' + esc(team.club_logo) + '" alt="">'
      : '<span class="tsl-team-logo--empty"></span>';
    var rows = "";
    for (var n = 1; n <= 3; n += 1) {
      var b = (team.boats || []).filter(function (x) { return Number(x.boat_no) === n; })[0] || {};
      var h = b.helm && b.helm.name ? b.helm.name + (b.helm.sas_id ? " " + b.helm.sas_id : "") : "—";
      var c = b.crew && b.crew.name ? b.crew.name + (b.crew.sas_id ? " " + b.crew.sas_id : "") : "—";
      rows += "<tr><td>" + n + "</td><td>" + esc(h) + "</td><td>" + esc(c) + "</td></tr>";
    }
    var pending = unassignedLine(team);
    return (
      '<div class="tsl-team">' +
        '<div class="tsl-team-head">' + logo + "<strong>" + esc(team.team_name || "") + "</strong></div>" +
        '<div class="table-container"><table class="table tsl-boats"><thead><tr><th></th><th>Helm</th><th>Crew</th></tr></thead><tbody>' +
        rows + "</tbody></table></div>" +
        (pending ? '<p class="tsl-msg">Unassigned: ' + esc(pending) + "</p>" : "") +
      "</div>"
    );
  }

  function collectTeam(panel) {
    var boats = [];
    for (var n = 1; n <= 3; n += 1) {
      var helm = panel.querySelector('input[data-sas-role="helm"][data-boat="' + n + '"]');
      var crew = panel.querySelector('input[data-sas-role="crew"][data-boat="' + n + '"]');
      boats.push({
        boat_no: n,
        helm_sas_id: helm ? helm.value.trim() : "",
        crew_sas_id: crew ? crew.value.trim() : ""
      });
    }
    return {
      team_id: panel.getAttribute("data-team-id") ? Number(panel.getAttribute("data-team-id")) : null,
      club_id: Number((panel.querySelector('input[data-field="club_id"]') || {}).value || 0),
      team_name: ((panel.querySelector('input[data-field="team_name"]') || {}).value || "").trim(),
      boats: boats
    };
  }

  function wireTeamPanel(panel) {
    var clubInp = panel.querySelector('input[data-field="club"]');
    var clubId = panel.querySelector('input[data-field="club_id"]');
    if (clubInp) {
      bindTypeahead(clubInp, "club", function (q) {
        return "/api/tsl/" + encodeURIComponent(RID) + "/clubs-search?q=" + encodeURIComponent(q) + "&limit=40";
      }, function (it) {
        clubInp.value = it.name || it.code || "";
        clubId.value = it.club_id;
        var nameInp = panel.querySelector('input[data-field="team_name"]');
        if (nameInp && !nameInp.value.trim()) nameInp.value = it.name || it.code || "";
        var head = panel.querySelector(".tsl-team-head strong");
        if (head && !panel.getAttribute("data-team-id")) head.textContent = it.name || it.code || "";
        var img = panel.querySelector(".tsl-team-logo");
        if (it.logo) {
          if (!img || !img.tagName || img.tagName.toLowerCase() !== "img") {
            img = document.createElement("img");
            img.className = "tsl-team-logo";
            var empty = panel.querySelector(".tsl-team-logo--empty");
            if (empty && empty.parentNode) empty.parentNode.replaceChild(img, empty);
            else panel.querySelector(".tsl-team-head").insertBefore(img, panel.querySelector(".tsl-team-head").firstChild);
          }
          img.src = it.logo;
        }
      });
    }
    panel.querySelectorAll("input[data-role]").forEach(function (inp) {
      bindTypeahead(inp, "sailor", function (q) {
        return "/api/tsl/" + encodeURIComponent(RID) + "/sailors-search?q=" + encodeURIComponent(q) + "&limit=35";
      }, function (it) {
        inp.value = it.name || "";
        var hid = inp.parentNode.querySelector('input[data-sas-role="' + inp.getAttribute("data-role") + '"]');
        if (hid) hid.value = it.sas_id || "";
        var sas = inp.parentNode.querySelector(".tsl-sas");
        if (sas) {
          sas.textContent = it.sas_id ? "SAS " + it.sas_id : "SAS missing — not invented";
          sas.classList.toggle("tsl-sas--missing", !it.sas_id);
        }
      });
    });
    var save = panel.querySelector(".tsl-save");
    var msg = panel.querySelector(".tsl-msg:last-child");
    if (save) {
      save.addEventListener("click", function () {
        var body = collectTeam(panel);
        if (!body.club_id) {
          if (msg) msg.textContent = "Select a club from the list.";
          return;
        }
        var hasId = body.team_id;
        var url = "/api/tsl/" + encodeURIComponent(RID) + "/teams" + (hasId ? "/" + body.team_id : "");
        save.disabled = true;
        api(url, {
          method: hasId ? "PATCH" : "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body)
        }).then(function () {
          if (msg) msg.textContent = "Saved.";
          return loadState();
        }).catch(function (e) {
          if (msg) msg.textContent = e.message || "Save failed";
        }).then(function () { save.disabled = false; });
      });
    }
    var del = panel.querySelector(".tsl-del");
    if (del) {
      del.addEventListener("click", function () {
        var id = panel.getAttribute("data-team-id");
        if (!id || !window.confirm("Remove this team from the event?")) return;
        api("/api/tsl/" + encodeURIComponent(RID) + "/teams/" + encodeURIComponent(id), { method: "DELETE" })
          .then(loadState)
          .catch(function (e) { if (msg) msg.textContent = e.message; });
      });
    }
  }

  function renderTeams() {
    var root = document.getElementById(ROOT_ID);
    if (!root) return;
    var html = '<h2 class="section-title">Teams</h2>';
    html += '<div class="tsl-public">';
    if (!state.teams.length) html += '<p class="tsl-msg">No teams registered.</p>';
    state.teams.forEach(function (t) { html += publicTeamHtml(t); });
    html += "</div><div class=\"tsl-edit\">";
    state.teams.forEach(function (t) { html += teamPanelHtml(t); });
    html += '<button type="button" class="tsl-add" id="tslAddTeam">Add Team</button>';
    html += '<div id="tslAddSlot"></div></div>';
    root.innerHTML = html;
    root.querySelectorAll(".tsl-edit .tsl-team").forEach(wireTeamPanel);
    var add = document.getElementById("tslAddTeam");
    if (add) {
      add.addEventListener("click", function () {
        var slot = document.getElementById("tslAddSlot");
        if (!slot || slot.querySelector(".tsl-team")) return;
        slot.innerHTML = teamPanelHtml({ boats: [{ boat_no: 1 }, { boat_no: 2 }, { boat_no: 3 }] });
        wireTeamPanel(slot.querySelector(".tsl-team"));
      });
    }
  }

  function teamById(id) {
    return state.teams.filter(function (t) { return Number(t.team_id) === Number(id); })[0];
  }
  function teamName(id) {
    var t = teamById(id);
    return t ? (t.team_name || t.club_abbrev || id) : (id ? String(id) : "—");
  }
  function teamOptions(selected, excludeId) {
    var html = '<option value="">Select team</option>';
    state.teams.forEach(function (t) {
      if (excludeId && Number(t.team_id) === Number(excludeId)) return;
      html += '<option value="' + t.team_id + '"' + (Number(selected) === Number(t.team_id) ? " selected" : "") + ">" +
        esc(t.team_name || t.club_abbrev) + "</option>";
    });
    return html;
  }
  function sailorOptions(team, selected) {
    var html = '<option value="">Select</option>';
    if (!team) return html;
    (team.boats || []).forEach(function (b) {
      ["helm", "crew"].forEach(function (role) {
        var s = b[role];
        if (!s || !s.sas_id) return;
        html += '<option value="' + esc(s.sas_id) + '"' + (String(selected) === String(s.sas_id) ? " selected" : "") + ">" +
          esc(s.name) + "</option>";
      });
    });
    return html;
  }
  function findBoat(match, teamId, pairing) {
    return (match.boats || []).filter(function (b) {
      return Number(b.team_id) === Number(teamId) && Number(b.pairing_no) === Number(pairing);
    })[0] || {};
  }

  function boatRow(match, teamId, pairing) {
    var team = teamById(teamId);
    var b = findBoat(match, teamId, pairing);
    var roster = team && team.boats ? team.boats.filter(function (x) { return Number(x.boat_no) === pairing; })[0] : null;
    var helm = b.helm_sas_id || (roster && roster.helm && roster.helm.sas_id) || "";
    var crew = b.crew_sas_id || (roster && roster.crew && roster.crew.sas_id) || "";
    var places = "";
    for (var i = 1; i <= 6; i += 1) {
      places += '<option value="' + i + '"' + (Number(b.finish_place) === i ? " selected" : "") + ">" + i + "</option>";
    }
    return (
      "<tr data-team-id=\"" + esc(teamId || "") + "\" data-pairing=\"" + pairing + "\">" +
        "<td>" + pairing + "</td>" +
        '<td><select data-k="helm_sas_id">' + sailorOptions(team, helm) + "</select></td>" +
        '<td><select data-k="crew_sas_id">' + sailorOptions(team, crew) + "</select></td>" +
        '<td><select data-k="finish_place"><option value=""></option>' + places + "</select></td>" +
      "</tr>"
    );
  }

  function matchHtml(match) {
    return (
      '<div class="tsl-match" data-match-id="' + match.match_id + '">' +
        '<div class="tsl-sides">' +
          '<div class="tsl-side" data-side="a">' +
            "<h3 class=\"tsl-blue\">Team Blue</h3>" +
            '<div class="tsl-field"><label>Blue</label><select data-k="team_a_id">' + teamOptions(match.team_a_id) + "</select></div>" +
            '<div class="table-container"><table class="table tsl-boats"><thead><tr><th></th><th>Helm</th><th>Crew</th><th>Place</th></tr></thead><tbody class="tsl-a-boats">' +
            (match.team_a_id ? [1, 2, 3].map(function (n) { return boatRow(match, match.team_a_id, n); }).join("") : "") +
            "</tbody></table></div>" +
          "</div>" +
          '<div class="tsl-side" data-side="b">' +
            "<h3 class=\"tsl-green\">Team Green</h3>" +
            '<div class="tsl-field"><label>Green</label><select data-k="team_b_id">' + teamOptions(match.team_b_id, match.team_a_id) + "</select></div>" +
            '<div class="table-container"><table class="table tsl-boats"><thead><tr><th></th><th>Helm</th><th>Crew</th><th>Place</th></tr></thead><tbody class="tsl-b-boats">' +
            (match.team_b_id ? [1, 2, 3].map(function (n) { return boatRow(match, match.team_b_id, n); }).join("") : "") +
            "</tbody></table></div>" +
          "</div>" +
        "</div>" +
        '<div class="tsl-row2">' +
          '<div class="tsl-field"><label>Official override</label><select data-k="override_winner_team_id">' +
            '<option value="">No override</option>' + teamOptions(match.override_winner_team_id) +
          "</select></div>" +
          '<div class="tsl-field"><label>Reason</label><input type="text" data-k="override_reason" value="' + esc(match.override_reason || "") + '" /></div>' +
        "</div>" +
        '<div class="tsl-row2">' +
          '<button type="button" class="tsl-save" data-complete="0">Save match</button>' +
          '<button type="button" class="tsl-save" data-complete="1">Save and complete</button>' +
        "</div>" +
        '<div class="tsl-msg"></div>' +
      "</div>"
    );
  }

  function collectMatch(box) {
    var teamA = Number((box.querySelector('[data-k="team_a_id"]') || {}).value || 0);
    var teamB = Number((box.querySelector('[data-k="team_b_id"]') || {}).value || 0);
    var boats = [];
    box.querySelectorAll("tbody tr[data-pairing]").forEach(function (tr) {
      var o = {
        team_id: Number(tr.getAttribute("data-team-id")),
        pairing_no: Number(tr.getAttribute("data-pairing"))
      };
      tr.querySelectorAll("[data-k]").forEach(function (el) {
        o[el.getAttribute("data-k")] = el.value;
      });
      boats.push(o);
    });
    return {
      team_a_id: teamA || null,
      team_b_id: teamB || null,
      colour_a: "Blue",
      colour_b: "Green",
      team_blue_id: teamA || null,
      team_green_id: teamB || null,
      override_winner_team_id: Number((box.querySelector('[data-k="override_winner_team_id"]') || {}).value || 0) || null,
      override_reason: ((box.querySelector('[data-k="override_reason"]') || {}).value || "").trim(),
      boats: boats,
      round_label: "RR"
    };
  }

  function wireMatch(box) {
    function refreshSides() {
      var mid = Number(box.getAttribute("data-match-id"));
      var match = state.matches.filter(function (m) { return Number(m.match_id) === mid; })[0] || { boats: [] };
      match.team_a_id = Number((box.querySelector('[data-k="team_a_id"]') || {}).value || 0) || null;
      match.team_b_id = Number((box.querySelector('[data-k="team_b_id"]') || {}).value || 0) || null;
      var bSel = box.querySelector('[data-k="team_b_id"]');
      if (bSel) bSel.innerHTML = teamOptions(match.team_b_id, match.team_a_id);
      var aBody = box.querySelector(".tsl-a-boats");
      var bBody = box.querySelector(".tsl-b-boats");
      if (aBody) aBody.innerHTML = match.team_a_id ? [1, 2, 3].map(function (n) { return boatRow(match, match.team_a_id, n); }).join("") : "";
      if (bBody) bBody.innerHTML = match.team_b_id ? [1, 2, 3].map(function (n) { return boatRow(match, match.team_b_id, n); }).join("") : "";
    }
    var ta = box.querySelector('[data-k="team_a_id"]');
    if (ta) ta.addEventListener("change", refreshSides);
    var tb = box.querySelector('[data-k="team_b_id"]');
    if (tb) tb.addEventListener("change", refreshSides);
    box.querySelectorAll(".tsl-save").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var body = collectMatch(box);
        body.complete = btn.getAttribute("data-complete") === "1";
        var msg = box.querySelector(".tsl-msg");
        btn.disabled = true;
        api("/api/tsl/" + encodeURIComponent(RID) + "/matches/" + encodeURIComponent(box.getAttribute("data-match-id")), {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body)
        }).then(function (d) {
          if (d && d.state) state = d.state;
          if (msg) msg.textContent = body.complete ? "Match complete. Standings updated." : "Saved.";
          renderAll();
        }).catch(function (e) {
          if (msg) msg.textContent = e.message || "Save failed";
        }).then(function () { btn.disabled = false; });
      });
    });
  }

  function renderSchedule() {
    var root = document.getElementById(SCHED_ID);
    if (!root) return;
    var fmt = state.format || "rr28";
    var nTeams = (state.teams || []).length;
    var html = '<h2 class="section-title">Schedule</h2>';
    html += '<div class="tsl-edit tsl-row2"><div class="tsl-field"><label>Championship format</label><select id="tslFormat">' +
      '<option value="rr28"' + (fmt === "rr28" ? " selected" : "") + ">Full round robin (28 matches)</option>" +
      '<option value="flights16"' + (fmt === "flights16" ? " selected" : "") + ">Weather contingency (16 matches)</option>" +
      "</select></div></div>";
    if (fmt === "flights16") {
      html += '<div class="tsl-edit tsl-row2"><div class="tsl-field"><label>Flight A</label><select id="tslFa" multiple size="4">';
      (state.teams || []).forEach(function (t) {
        var sel = ((state.settings || {}).flight_a || []).indexOf(t.team_id) >= 0 || ((state.settings || {}).flight_a || []).indexOf(String(t.team_id)) >= 0;
        html += '<option value="' + t.team_id + '"' + (sel ? " selected" : "") + ">" + esc(t.team_name) + "</option>";
      });
      html += "</select></div><div class=\"tsl-field\"><label>Flight B</label><select id=\"tslFb\" multiple size=\"4\">";
      (state.teams || []).forEach(function (t) {
        var sel = ((state.settings || {}).flight_b || []).indexOf(t.team_id) >= 0 || ((state.settings || {}).flight_b || []).indexOf(String(t.team_id)) >= 0;
        html += '<option value="' + t.team_id + '"' + (sel ? " selected" : "") + ">" + esc(t.team_name) + "</option>";
      });
      html += "</select></div></div>";
    }
    html += '<div class="tsl-edit tsl-row2"><button type="button" class="tsl-save" id="tslGen">Generate schedule</button></div>';
    html += '<div class="tsl-msg tsl-edit" id="tslSchedMsg">' + (nTeams < 8 ? "Register eight teams before generating the championship schedule." : "") + "</div>";
    html += '<div class="table-container"><table class="table"><thead><tr><th>M</th><th>Round/Flight</th><th>Blue</th><th>Green</th><th>Status</th><th>Winner</th></tr></thead><tbody>';
    (state.matches || []).forEach(function (m) {
      html += "<tr><td>" + esc(m.label || ("M" + m.match_no)) + "</td><td>" + esc(m.round_label || "") + "</td><td>" +
        esc(teamName(m.team_a_id || m.team_blue_id)) + "</td><td>" + esc(teamName(m.team_b_id || m.team_green_id)) + "</td><td>" +
        esc(m.status || "") + "</td><td>" + esc(teamName(m.winner_team_id)) + "</td></tr>";
    });
    if (!(state.matches || []).length) html += '<tr><td colspan="6">No matches yet.</td></tr>';
    html += "</tbody></table></div>";
    root.innerHTML = html;
    var fmtSel = document.getElementById("tslFormat");
    if (fmtSel) {
      fmtSel.addEventListener("change", function () {
        state.format = fmtSel.value;
        renderSchedule();
      });
    }
    function selected(sel) {
      return Array.prototype.map.call((sel && sel.selectedOptions) || [], function (o) { return Number(o.value); });
    }
    var gen = document.getElementById("tslGen");
    if (gen) {
      gen.addEventListener("click", function () {
        var body = { format: (document.getElementById("tslFormat") || {}).value || "rr28", confirm: false };
        if (body.format === "flights16") {
          body.flight_a = selected(document.getElementById("tslFa"));
          body.flight_b = selected(document.getElementById("tslFb"));
        }
        var msg = document.getElementById("tslSchedMsg");
        api("/api/tsl/" + encodeURIComponent(RID) + "/schedule", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body)
        }).then(function (d) {
          if (d && d.needs_confirm) {
            if (!window.confirm("This replaces open matches and keeps completed ones. Continue?")) return;
            body.confirm = true;
            return api("/api/tsl/" + encodeURIComponent(RID) + "/schedule", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(body)
            });
          }
          return d;
        }).then(function (d) {
          if (d && d.state) state = d.state;
          if (msg) msg.textContent = (d && d.ok) ? "Schedule generated." : ((d && d.preview) ? "Confirm required." : "");
          renderAll();
        }).catch(function (e) { if (msg) msg.textContent = e.message; });
      });
    }
  }

  function renderMatches() {
    var root = document.getElementById(MATCHES_ID);
    if (!root) return;
    if (!isSaEdit()) {
      root.innerHTML = "";
      return;
    }
    var matches = state.matches || [];
    var html = '<h2 class="section-title">Match entry</h2>';
    if (!matches.length) {
      html += '<p class="tsl-msg">Use M+ on the fleet header to add M1, or generate a schedule after eight teams are registered.</p>';
      root.innerHTML = html;
      return;
    }
    if (!selectedMatchNo) selectedMatchNo = Number(matches[0].match_no);
    var current = matches.filter(function (m) { return Number(m.match_no) === Number(selectedMatchNo); })[0] || matches[0];
    selectedMatchNo = Number(current.match_no);
    html += '<div class="tsl-field"><label>Match</label><select id="tslMatchPick">';
    matches.forEach(function (m) {
      html += '<option value="' + m.match_no + '"' + (Number(m.match_no) === selectedMatchNo ? " selected" : "") + ">" +
        esc(m.label || ("M" + m.match_no)) + "</option>";
    });
    html += "</select></div>";
    html += matchHtml(current);
    root.innerHTML = html;
    var pick = document.getElementById("tslMatchPick");
    if (pick) {
      pick.addEventListener("change", function () {
        selectedMatchNo = Number(pick.value);
        renderMatches();
      });
    }
    var box = root.querySelector(".tsl-match");
    if (box) wireMatch(box);
  }

  function injectMButtons() {
    var sec = fleetSection();
    if (!sec || sec.querySelector(".tsl-mstep")) return;
    var box = document.createElement("div");
    box.className = "club-race-step tsl-mstep";
    box.setAttribute("role", "group");
    box.setAttribute("aria-label", "Add or remove match");
    box.innerHTML = '<button type="button" class="club-race-step-add" id="tslMPlus">M+</button>' +
      '<button type="button" class="club-race-step-sub" id="tslMMinus">M−</button>';
    var title = sec.querySelector(".fleet-title-row") || sec.querySelector(".class-header-main-col");
    if (title) title.appendChild(box);
    else {
      var hdr = sec.querySelector(".class-header");
      if (hdr) hdr.appendChild(box);
      else sec.insertBefore(box, sec.firstChild);
    }
    document.getElementById("tslMPlus").addEventListener("click", function () {
      if (!isSaEdit()) return;
      api("/api/tsl/" + encodeURIComponent(RID) + "/matches", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ round_label: "RR" })
      }).then(loadState).catch(function (e) { window.alert(e.message); });
    });
    document.getElementById("tslMMinus").addEventListener("click", function () {
      if (!isSaEdit()) return;
      if (!window.confirm("Remove the last match?")) return;
      api("/api/tsl/" + encodeURIComponent(RID) + "/matches/last?confirm=1", { method: "DELETE" })
        .then(loadState)
        .catch(function (e) { window.alert(e.message); });
    });
  }

  function tidyFleetHeader() {
    var line = fleetSection() && fleetSection().querySelector(".sailed-line");
    if (!line || line.getAttribute("data-tsl-tidy")) return;
    line.setAttribute("data-tsl-tidy", "1");
    line.textContent = String(line.textContent || "")
      .replace(/\s*,\s*Discards:\s*[^,]+/i, "")
      .replace(/\s*,\s*To count:\s*[^,]+/i, "");
  }

  function headerLabel(th) {
    return String(th.textContent || "").replace(/\s+/g, " ").trim().toLowerCase();
  }
  function applyStandingsTable() {
    var table = resultsTable();
    if (!table) return;
    var thead = table.tHead && table.tHead.rows[0];
    if (!thead) return;
    var hideNames = {
      class: 1, "sail no": 1, sailno: 1, total: 1, nett: 1, jib: 1, bow: 1, hull: 1,
      discards: 1, "to count": 1, colour: 1, club: 1, helm: 1, crew: 1, helms: 1, crews: 1
    };
    var mlNames = { losses: 1, "win %": 1, played: 1, matches: 1 };
    Array.prototype.forEach.call(thead.cells, function (th) {
      var lab = headerLabel(th);
      if (hideNames[lab]) th.classList.add("tsl-hide-mp");
      if (mlNames[lab]) th.classList.add("tsl-ml-only");
      if (lab === "boat name") th.textContent = "Team";
      if (lab === "wins") th.textContent = "W";
      var rm = lab.match(/^r(\d+)$/);
      if (rm) th.textContent = "M" + rm[1];
    });
    var matchNos = (state.matches || []).map(function (m) { return Number(m.match_no); });
    matchNos.forEach(function (n) {
      var label = "m" + n;
      var found = false;
      Array.prototype.forEach.call(thead.cells, function (th) {
        if (headerLabel(th) === label || headerLabel(th) === ("r" + n)) found = true;
      });
      if (!found) {
        var th = document.createElement("th");
        th.className = "tsl-mcol";
        th.textContent = "M" + n;
        var winsTh = Array.prototype.filter.call(thead.cells, function (c) { return headerLabel(c) === "w" || headerLabel(c) === "wins"; })[0];
        if (winsTh) thead.insertBefore(th, winsTh);
        else thead.appendChild(th);
        Array.prototype.forEach.call(table.tBodies[0] ? table.tBodies[0].rows : [], function (tr) {
          var td = document.createElement("td");
          td.className = "tsl-mcol";
          td.textContent = "—";
          if (winsTh) tr.insertBefore(td, tr.cells[winsTh.cellIndex]);
          else tr.appendChild(td);
        });
      }
    });
    var hasWins = Array.prototype.some.call(thead.cells, function (th) {
      var lab = headerLabel(th);
      return lab === "w" || lab === "wins";
    });
    if (!hasWins) {
      var wth = document.createElement("th");
      wth.className = "tsl-col-wins";
      wth.textContent = "W";
      thead.appendChild(wth);
      Array.prototype.forEach.call(table.tBodies[0] ? table.tBodies[0].rows : [], function (tr) {
        var td = document.createElement("td");
        td.className = "tsl-col-wins";
        td.textContent = "0";
        tr.appendChild(td);
      });
    }
    var hasPlayed = Array.prototype.some.call(thead.cells, function (th) { return headerLabel(th) === "played" || headerLabel(th) === "matches"; });
    if (!hasPlayed) {
      var pth = document.createElement("th");
      pth.className = "tsl-ml-only";
      pth.textContent = "Played";
      thead.appendChild(pth);
      Array.prototype.forEach.call(table.tBodies[0] ? table.tBodies[0].rows : [], function (tr) {
        var td = document.createElement("td");
        td.className = "tsl-ml-only";
        td.textContent = "0";
        tr.appendChild(td);
      });
    }
    var hasLoss = Array.prototype.some.call(thead.cells, function (th) { return headerLabel(th) === "losses"; });
    if (!hasLoss) {
      var lth = document.createElement("th");
      lth.className = "tsl-ml-only";
      lth.textContent = "Losses";
      thead.appendChild(lth);
      Array.prototype.forEach.call(table.tBodies[0] ? table.tBodies[0].rows : [], function (tr) {
        var a = document.createElement("td");
        a.className = "tsl-ml-only tsl-loss";
        a.textContent = "0";
        tr.appendChild(a);
      });
    }
    Array.prototype.forEach.call(thead.cells, function (th, i) {
      Array.prototype.forEach.call(table.tBodies[0] ? table.tBodies[0].rows : [], function (tr) {
        if (!tr.cells[i]) return;
        if (th.classList.contains("tsl-hide-mp")) tr.cells[i].classList.add("tsl-hide-mp");
        if (th.classList.contains("tsl-ml-only")) tr.cells[i].classList.add("tsl-ml-only");
      });
    });
    var idx = {};
    Array.prototype.forEach.call(thead.cells, function (th, i) { idx[headerLabel(th)] = i; });
    var body = table.tBodies[0];
    if (!body) return;
    Array.prototype.forEach.call(body.rows, function (tr) {
      var nameCell = tr.cells[idx.team] || tr.cells[idx["boat name"]];
      var clubCell = tr.cells[idx.club];
      var name = nameCell ? String(nameCell.textContent || "").replace(/\s+/g, " ").trim() : "";
      var club = clubCell ? String(clubCell.textContent || "").replace(/\s+/g, " ").trim() : "";
      var row = (state.standings || []).filter(function (s) {
        return String(s.team_name || "").trim() === name || String(s.club_abbrev || "") === club;
      })[0];
      if (nameCell && !nameCell.querySelector(".tsl-team-club")) {
        var wrap = document.createElement("span");
        wrap.className = "rs-club-with-logo tsl-team-club";
        var logo = (clubCell && clubCell.querySelector("img")) || (row && row.club_logo ? null : null);
        if (clubCell && clubCell.querySelector("img")) {
          var img = clubCell.querySelector("img").cloneNode(true);
          img.className = "rs-club-row-logo-sm";
          img.alt = "";
          wrap.appendChild(img);
        } else if (row && row.club_logo) {
          var img2 = document.createElement("img");
          img2.className = "rs-club-row-logo-sm";
          img2.src = row.club_logo;
          img2.alt = "";
          wrap.appendChild(img2);
        }
        var label = document.createElement("span");
        label.textContent = (row && row.team_name) || name || "";
        wrap.appendChild(label);
        nameCell.innerHTML = "";
        nameCell.appendChild(wrap);
      }
      if (!row) return;
      if (idx.rank != null && tr.cells[idx.rank]) tr.cells[idx.rank].textContent = row.rank || "";
      var wIdx = idx.w != null ? idx.w : idx.wins;
      if (wIdx != null && tr.cells[wIdx]) tr.cells[wIdx].textContent = row.wins;
      if (idx.played != null && tr.cells[idx.played]) tr.cells[idx.played].textContent = row.matches_played;
      if (idx.matches != null && tr.cells[idx.matches]) tr.cells[idx.matches].textContent = row.matches_played;
      if (idx.losses != null && tr.cells[idx.losses]) tr.cells[idx.losses].textContent = row.losses;
      Object.keys(row.cells || {}).forEach(function (k) {
        var i2 = idx[k.toLowerCase()] != null ? idx[k.toLowerCase()] : idx["r" + k.slice(1)];
        if (i2 != null && tr.cells[i2]) tr.cells[i2].textContent = row.cells[k];
      });
    });
  }

  function ensureRoots() {
    var page = document.querySelector(".regatta-page");
    if (!page) return;
    var fleet = fleetSection();
    var host = (fleet && fleet.parentNode) || page;
    var printRow = page.querySelector(".action-buttons");
    [["macTslAdmin", ROOT_ID], ["macTslSchedule", SCHED_ID], ["macTslMatches", MATCHES_ID]].forEach(function (pair) {
      var el = document.getElementById(pair[1]);
      if (!el) {
        el = document.createElement("div");
        el.id = pair[1];
        el.className = "card";
      }
      host.insertBefore(el, printRow || null);
    });
    var boats = document.getElementById("macTslBoats");
    if (boats && boats.parentNode) boats.parentNode.removeChild(boats);
  }

  function renderAll() {
    tidyFleetHeader();
    injectMButtons();
    applyStandingsTable();
    renderTeams();
    renderSchedule();
    renderMatches();
  }

  function loadState() {
    return api("/api/tsl/" + encodeURIComponent(RID) + "/state").then(function (d) {
      state = d || state;
      renderAll();
      return state;
    });
  }

  function start() {
    if (!onThisEvent()) return;
    injectCss();
    ensureRoots();
    loadState().catch(function () { renderAll(); });
    var tog = document.getElementById("regattaSaEditToggle");
    if (tog && !tog._tslBound) {
      tog.addEventListener("change", function () { renderAll(); });
      tog._tslBound = true;
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
  window.__ssaMacTslAdmin = JS_VER;
})();
