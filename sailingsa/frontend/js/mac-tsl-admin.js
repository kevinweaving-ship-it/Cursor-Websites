/**
 * MAC TSL WC — Event URL results + admin. Same .class-header / table / .action-button as the fleet sheet.
 * Only /regatta/2026-10-17-mac-tsl-wc-team-sailing. No club-score-edit.
 */
(function () {
  "use strict";
  if (window.__SSA_MAC_TSL_ADMIN__) return;
  window.__SSA_MAC_TSL_ADMIN__ = true;

  var RID = "2026-10-17-mac-tsl-wc-team-sailing";
  var JS_VER = "20261013e";
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
      ".regatta-page[data-mac-tsl=\"1\"] .table-wrapper{overflow-x:auto;-webkit-overflow-scrolling:touch}",
      "#macTslAdmin,#macTslSchedule{display:block}",
      "#macTslMatches{display:none}",
      ".regatta-page--super-admin-edit #macTslMatches{display:block}",
      "#macTslAdmin .tsl-edit{display:none}",
      ".regatta-page--super-admin-edit #macTslAdmin .tsl-edit{display:block}",
      "#macTslAdmin .tsl-public{display:block}",
      ".regatta-page--super-admin-edit #macTslAdmin .tsl-public{display:none}",
      "#macTslSchedule .tsl-edit{display:none}",
      ".regatta-page--super-admin-edit #macTslSchedule .tsl-edit{display:block}",
      "#macTslAdmin input.wc-result-field-input,#macTslAdmin select.wc-result-field-input,#macTslMatches select.wc-result-field-input,#macTslSchedule select.wc-result-field-input{font:inherit;color:#1a2750;margin:0;min-height:0;width:auto;max-width:100%;box-sizing:border-box}",
      "#macTslAdmin .tsl-sas{display:inline;color:#1a2750;font:inherit;margin-left:4px}",
      "#macTslAdmin .tsl-sas--missing{color:#c62828}",
      "#macTslAdmin .tsl-ac{position:relative;display:inline;white-space:nowrap}",
      "#macTslAdmin .fleet-results-table th,#macTslAdmin .fleet-results-table td,#macTslSchedule .fleet-results-table th,#macTslSchedule .fleet-results-table td,#macTslMatches .fleet-results-table th,#macTslMatches .fleet-results-table td{white-space:nowrap}",
      "#macTslAdmin .rs-club-with-logo,#macTslSchedule .rs-club-with-logo{display:inline-flex;flex-direction:row;flex-wrap:nowrap;align-items:center;white-space:nowrap}",
      "#macTslAdmin .tsl-ac-list{position:absolute;left:0;right:0;z-index:80;margin:0;padding:0;list-style:none;background:#fff;border:1px solid #1d294d;max-height:180px;overflow-y:auto}",
      "#macTslAdmin .tsl-ac-list li{margin:0;padding:4px 6px;cursor:pointer;color:#1a2750;font:inherit}",
      "#macTslAdmin .tsl-ac-list li:hover{background:#e9eefb}",
      "#macTslAdmin .tsl-ac-sub{display:block;font:inherit;color:#1a2750}",
      ".regatta-page[data-mac-tsl=\"1\"] .rs-club-row-logo-sm,#macTslAdmin .rs-club-row-logo-sm{display:inline-block;height:auto;width:auto;max-height:16px;max-width:28px;object-fit:contain;vertical-align:middle;flex:0 0 auto}",
      "#macTslAdmin .tsl-team,#macTslMatches .tsl-match{margin:0;padding:0;border:none;background:none;box-shadow:none}",
      "#macTslAdmin .tsl-del{color:#c62828}",
      "#macTslAdmin .tsl-msg,#macTslSchedule .tsl-msg,#macTslMatches .tsl-msg{color:#1a2750;margin:6px 0;font:inherit}",
      "#macTslAdmin .tsl-warn{color:#c62828;margin:4px 0 0}",
      "#macTslMatches .tsl-sides{display:flex;gap:0;flex-wrap:wrap}",
      "#macTslMatches .tsl-side{flex:1 1 220px;min-width:0}",
      "#macTslAdmin .tsl-row2,#macTslSchedule .tsl-row2,#macTslMatches .tsl-row2{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0}",
      ".club-race-step.tsl-mstep{display:none;align-items:center;gap:6px;flex:0 0 auto}",
      ".regatta-page--super-admin-edit .club-race-step.tsl-mstep{display:inline-flex}",
      ".tsl-blue{color:#1d4ed8}",
      ".tsl-green{color:#15803d}",
      ".regatta-page[data-mac-tsl=\"1\"] th.tsl-hide-mp,.regatta-page[data-mac-tsl=\"1\"] td.tsl-hide-mp{display:none}",
      ".regatta-page[data-mac-tsl=\"1\"] .tsl-col-wins,.regatta-page[data-mac-tsl=\"1\"] .tsl-mcol{text-align:center;font-weight:bold}",
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
    var sec = firstFleet() || fleetSection();
    if (!sec) return null;
    var tables = sec.querySelectorAll("table.fleet-results-table, table");
    for (var i = 0; i < tables.length; i += 1) {
      if (tables[i].id !== "tslGoldTable") return tables[i];
    }
    return null;
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

  function firstFleet() {
    return document.querySelector(".regatta-page[data-mac-tsl=\"1\"] .fleet-section:not(#macTslAdmin):not(#macTslSchedule):not(#macTslMatches)");
  }
  function fleetHead(title, line, extraHtml) {
    var src = firstFleet() && firstFleet().querySelector(".class-header");
    var left = src && src.querySelector(".class-header-logo-col");
    var right = src && src.querySelector(".class-header-club-logo-col");
    return (
      '<div class="class-header class-header--with-logos">' +
        (left ? left.outerHTML : "") +
        '<div class="class-header-main-col">' +
          '<div class="fleet-title-row">' + esc(title) + "</div>" +
          '<div class="sailed-line">' + esc(line || "") + (extraHtml || "") + "</div>" +
        "</div>" +
        (right ? right.outerHTML : "") +
      "</div>"
    );
  }

  function syncSheetType() {
    var page = document.querySelector(".regatta-page[data-mac-tsl=\"1\"]");
    var first = page && page.querySelector(".fleet-section:not(#macTslAdmin):not(#macTslSchedule):not(#macTslMatches)");
    var th = first && first.querySelector("th");
    var td = first && first.querySelector("td");
    if (!th) return;
    var thCs = getComputedStyle(th);
    var tdCs = getComputedStyle(td || th);
    var style = document.getElementById("mac-tsl-type-sync");
    if (!style) {
      style = document.createElement("style");
      style.id = "mac-tsl-type-sync";
      document.head.appendChild(style);
    }
    style.textContent = [
      "#macTslAdmin,#macTslAdmin *,#macTslSchedule,#macTslSchedule *,#macTslMatches,#macTslMatches *{",
      "font-size:" + tdCs.fontSize + "!important;",
      "line-height:" + tdCs.lineHeight + "!important;",
      "font-family:" + tdCs.fontFamily + "!important;",
      "}",
      "#macTslAdmin th,#macTslAdmin td,#macTslSchedule th,#macTslSchedule td,#macTslMatches th,#macTslMatches td{",
      "padding:" + tdCs.padding + "!important;",
      "}",
      "#macTslAdmin th,#macTslSchedule th,#macTslMatches th{font-weight:" + thCs.fontWeight + "!important;}"
    ].join("");
  }

  function clubCode(team) {
    return (team && (team.club_abbrev || team.club_code)) || "";
  }
  function logoImg(src, code) {
    if (!src) return "";
    return '<img class="rs-club-row-logo-sm" src="' + esc(src) + '" alt="" title="' + esc(code || "") +
      '" style="height:auto;width:auto;max-height:16px;max-width:28px;object-fit:contain;display:inline-block;vertical-align:middle;flex:0 0 auto">';
  }
  function clubCell(team) {
    var code = clubCode(team);
    return '<span class="rs-club-with-logo">' + logoImg(team && team.club_logo, code) + esc(code) + "</span>";
  }

  function sailorName(s) {
    return s && s.name ? s.name : "—";
  }

  function pendingNote() {
    var bits = [];
    (state.teams || []).forEach(function (t) {
      var p = unassignedLine(t);
      if (p) bits.push((t.team_name || t.club_abbrev || "Team") + ": " + p);
    });
    return bits.join(" · ");
  }

  function publicTeamsTable() {
    var html = '<div class="table-wrapper"><table class="fleet-results-table"><thead><tr>' +
      '<th class="club-col">Team</th><th>1 Helm</th><th>1 Crew</th><th>2 Helm</th><th>2 Crew</th><th>3 Helm</th><th>3 Crew</th>' +
      (isSaEdit() ? "<th></th>" : "") +
      "</tr></thead><tbody>";
    if (!(state.teams || []).length) {
      html += '<tr><td colspan="' + (isSaEdit() ? "8" : "7") + '">No teams registered.</td></tr>';
    }
    (state.teams || []).forEach(function (t) { html += teamRowHtml(t); });
    html += "</tbody></table></div>";
    return html;
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
    var show = name || "—";
    return (
      '<span class="tsl-ac">' +
        '<span class="wc-sa-edit-hide">' + esc(show) + "</span>" +
        '<input class="wc-result-field-input wc-sa-edit-only" type="text" data-role="' + role + '" data-boat="' + boatNo + '" value="' + esc(name) + '" autocomplete="off" />' +
        '<input type="hidden" data-sas-role="' + role + '" data-boat="' + boatNo + '" value="' + esc(sid) + '" />' +
      "</span>"
    );
  }

  function teamRowHtml(team) {
    team = team || {};
    var boats = team.boats || [{ boat_no: 1 }, { boat_no: 2 }, { boat_no: 3 }];
    var code = clubCode(team);
    var cells = "";
    for (var n = 1; n <= 3; n += 1) {
      var b = boats.filter(function (x) { return Number(x.boat_no) === n; })[0] || { boat_no: n };
      cells += "<td>" + sailorCell(n, "helm", b.helm) + "</td><td>" + sailorCell(n, "crew", b.crew) + "</td>";
    }
    return (
      '<tr class="tsl-team" data-team-id="' + esc(team.team_id || "") + '">' +
        '<td class="club-col"><span class="rs-club-with-logo tsl-ac">' +
          logoImg(team.club_logo, code) +
          '<span class="wc-sa-edit-hide">' + esc(code) + "</span>" +
          '<input class="wc-result-field-input wc-sa-edit-only" type="text" data-field="club" value="' + esc(code) + '" autocomplete="off" />' +
          '<input type="hidden" data-field="club_id" value="' + esc(team.club_id || "") + '" />' +
          '<input type="hidden" data-field="team_name" value="' + esc(team.team_name || code) + '" />' +
        "</span></td>" +
        cells +
        (isSaEdit() ? '<td class="tsl-edit"><button type="button" class="fleet-sa-edit-hit tsl-save">Save Team</button>' +
          (team.team_id ? '<button type="button" class="fleet-sa-edit-hit tsl-del">Remove</button>' : "") +
          '<span class="tsl-msg"></span></td>' : "") +
      "</tr>"
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
      team_name: ((panel.querySelector('input[data-field="team_name"]') || {}).value || (panel.querySelector('input[data-field="club"]') || {}).value || "").trim(),
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
        clubInp.value = it.code || it.name || "";
        clubId.value = it.club_id;
        var nameInp = panel.querySelector('input[data-field="team_name"]');
        if (nameInp) nameInp.value = nameInp.value.trim() || it.code || it.name || "";
        var img = panel.querySelector(".rs-club-row-logo-sm");
        if (it.logo) {
          if (!img || !img.tagName || img.tagName.toLowerCase() !== "img") {
            img = document.createElement("img");
            img.className = "rs-club-row-logo-sm";
            img.setAttribute("style", "height:auto;width:auto;max-height:16px;max-width:28px;object-fit:contain;display:inline-block;vertical-align:middle;flex:0 0 auto");
            var ac = panel.querySelector(".tsl-ac");
            if (ac) ac.insertBefore(img, ac.firstChild);
          }
          img.src = it.logo;
          img.title = it.code || "";
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
    var msg = panel.querySelector(".tsl-msg");
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
    var n = (state.teams || []).length;
    var html = fleetHead("Teams", "Entries: " + n) + publicTeamsTable().replace("<tbody>", '<tbody id="tslTeamBody">');
    root.innerHTML = html;
    root.querySelectorAll(".tsl-team").forEach(wireTeamPanel);
  }

  function teamById(id) {
    return state.teams.filter(function (t) { return Number(t.team_id) === Number(id); })[0];
  }
  function teamName(id) {
    var t = teamById(id);
    return t ? (clubCode(t) || t.team_name || id) : (id ? String(id) : "—");
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

  function boatCells(match, teamId, pairing) {
    var team = teamById(teamId);
    var b = findBoat(match, teamId, pairing);
    var roster = team && team.boats ? team.boats.filter(function (x) { return Number(x.boat_no) === pairing; })[0] : null;
    var helm = b.helm_sas_id || (roster && roster.helm && roster.helm.sas_id) || "";
    var crew = b.crew_sas_id || (roster && roster.crew && roster.crew.sas_id) || "";
    var places = "";
    for (var i = 1; i <= 6; i += 1) {
      places += '<option value="' + i + '"' + (Number(b.finish_place) === i ? " selected" : "") + ">" + i + "</option>";
    }
    var attr = ' data-team-id="' + esc(teamId || "") + '" data-pairing="' + pairing + '"';
    return (
      '<td><select class="wc-result-field-input" data-k="helm_sas_id"' + attr + ">" + sailorOptions(team, helm) + "</select></td>" +
      '<td><select class="wc-result-field-input" data-k="crew_sas_id"' + attr + ">" + sailorOptions(team, crew) + "</select></td>" +
      '<td><select class="wc-result-field-input" data-k="finish_place"' + attr + '><option value=""></option>' + places + "</select></td>"
    );
  }

  function matchHtml(match) {
    var empty = "<td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td>";
    return (
      '<div class="tsl-match" data-match-id="' + match.match_id + '">' +
        fleetHead("Matches", (state.matches || []).length ? (state.matches.length + " matches") : "") +
        '<div class="table-wrapper"><table class="fleet-results-table"><thead><tr>' +
          "<th>M</th><th class=\"tsl-blue\">Team Blue</th><th>1 Helm</th><th>1 Crew</th><th>P</th><th>2 Helm</th><th>2 Crew</th><th>P</th><th>3 Helm</th><th>3 Crew</th><th>P</th>" +
          "<th class=\"tsl-green\">Team Green</th><th>1 Helm</th><th>1 Crew</th><th>P</th><th>2 Helm</th><th>2 Crew</th><th>P</th><th>3 Helm</th><th>3 Crew</th><th>P</th>" +
          "<th>Override</th><th>Reason</th><th></th></tr></thead><tbody><tr>" +
          "<td><select id=\"tslMatchPick\">" +
          (state.matches || []).map(function (m) {
            return '<option value="' + m.match_no + '"' + (Number(m.match_no) === Number(match.match_no) ? " selected" : "") + ">" +
              esc(m.label || ("M" + m.match_no)) + "</option>";
          }).join("") +
          "</select></td>" +
          '<td class="club-col"><select class="wc-result-field-input" data-k="team_a_id">' + teamOptions(match.team_a_id) + "</select></td>" +
          (match.team_a_id ? [1, 2, 3].map(function (n) { return boatCells(match, match.team_a_id, n); }).join("") : empty) +
          '<td class="club-col"><select class="wc-result-field-input" data-k="team_b_id">' + teamOptions(match.team_b_id, match.team_a_id) + "</select></td>" +
          (match.team_b_id ? [1, 2, 3].map(function (n) { return boatCells(match, match.team_b_id, n); }).join("") : empty) +
          "<td><select class=\"wc-result-field-input\" data-k=\"override_winner_team_id\"><option value=\"\">No override</option>" + teamOptions(match.override_winner_team_id) + "</select></td>" +
          '<td><input class="wc-result-field-input" type="text" data-k="override_reason" value="' + esc(match.override_reason || "") + '" /></td>' +
          '<td><button type="button" class="fleet-sa-edit-hit tsl-save" data-complete="0">Save match</button>' +
          '<button type="button" class="fleet-sa-edit-hit tsl-save" data-complete="1">Save and complete</button>' +
          '<span class="tsl-msg"></span></td>' +
        "</tr></tbody></table></div>" +
      "</div>"
    );
  }

  function collectMatch(box) {
    var teamA = Number((box.querySelector('[data-k="team_a_id"]') || {}).value || 0);
    var teamB = Number((box.querySelector('[data-k="team_b_id"]') || {}).value || 0);
    var map = {};
    box.querySelectorAll("[data-pairing][data-k]").forEach(function (el) {
      var key = el.getAttribute("data-team-id") + ":" + el.getAttribute("data-pairing");
      if (!map[key]) {
        map[key] = {
          team_id: Number(el.getAttribute("data-team-id")),
          pairing_no: Number(el.getAttribute("data-pairing"))
        };
      }
      map[key][el.getAttribute("data-k")] = el.value;
    });
    var boats = Object.keys(map).map(function (k) { return map[k]; });
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
      var match = state.matches.filter(function (m) { return Number(m.match_id) === mid; })[0];
      if (!match) return;
      match.team_a_id = Number((box.querySelector('[data-k="team_a_id"]') || {}).value || 0) || null;
      match.team_b_id = Number((box.querySelector('[data-k="team_b_id"]') || {}).value || 0) || null;
      renderMatches();
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
    var extra = '<span class="tsl-edit"> <select id="tslFormat" class="wc-result-field-input">' +
      '<option value="rr28"' + (fmt === "rr28" ? " selected" : "") + ">Full round robin (28 matches)</option>" +
      '<option value="flights16"' + (fmt === "flights16" ? " selected" : "") + ">Weather contingency (16 matches)</option>" +
      "</select>";
    if (fmt === "flights16") {
      extra += ' <select id="tslFa" class="wc-result-field-input" multiple size="1">';
      (state.teams || []).forEach(function (t) {
        var sel = ((state.settings || {}).flight_a || []).indexOf(t.team_id) >= 0 || ((state.settings || {}).flight_a || []).indexOf(String(t.team_id)) >= 0;
        extra += '<option value="' + t.team_id + '"' + (sel ? " selected" : "") + ">" + esc(clubCode(t) || t.team_name) + "</option>";
      });
      extra += '</select> <select id="tslFb" class="wc-result-field-input" multiple size="1">';
      (state.teams || []).forEach(function (t) {
        var sel = ((state.settings || {}).flight_b || []).indexOf(t.team_id) >= 0 || ((state.settings || {}).flight_b || []).indexOf(String(t.team_id)) >= 0;
        extra += '<option value="' + t.team_id + '"' + (sel ? " selected" : "") + ">" + esc(clubCode(t) || t.team_name) + "</option>";
      });
      extra += "</select>";
    }
    extra += ' <button type="button" class="fleet-sa-edit-hit" id="tslGen">Generate schedule</button> <span class="tsl-msg" id="tslSchedMsg">' +
      (nTeams < 8 ? "Register eight teams before generating the championship schedule." : "") + "</span></span>";
    var html = fleetHead("Schedule", (state.matches || []).length ? (state.matches.length + " matches") : "No matches yet.", extra);
    html += '<div class="table-wrapper"><table class="fleet-results-table"><thead><tr><th>M</th><th>Round/Flight</th><th class="club-col">Blue</th><th class="club-col">Green</th><th>Status</th><th>Winner</th></tr></thead><tbody>';
    (state.matches || []).forEach(function (m) {
      html += "<tr><td>" + esc(m.label || ("M" + m.match_no)) + "</td><td>" + esc(m.round_label || "") + '</td><td class="club-col">' +
        clubCell(teamById(m.team_a_id || m.team_blue_id) || {}) + '</td><td class="club-col">' + clubCell(teamById(m.team_b_id || m.team_green_id) || {}) + "</td><td>" +
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
    if (!matches.length) {
      root.innerHTML = "";
      return;
    }
    if (!selectedMatchNo) selectedMatchNo = Number(matches[0].match_no);
    var current = matches.filter(function (m) { return Number(m.match_no) === Number(selectedMatchNo); })[0] || matches[0];
    selectedMatchNo = Number(current.match_no);
    var html = matchHtml(current);
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
      '<button type="button" class="club-race-step-sub" id="tslMMinus">M−</button>' +
      '<button type="button" class="club-race-step-add" id="tslAddTeam" aria-label="Add Team">T+</button>';
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
    document.getElementById("tslAddTeam").addEventListener("click", function () {
      if (!isSaEdit()) return;
      var body = document.getElementById("tslTeamBody");
      if (!body || body.querySelector('.tsl-team[data-team-id=""]')) return;
      body.insertAdjacentHTML("beforeend", teamRowHtml({ boats: [{ boat_no: 1 }, { boat_no: 2 }, { boat_no: 3 }] }));
      wireTeamPanel(body.querySelector(".tsl-team:last-child"));
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
  function goldRaceRows() {
    var rows = [];
    var table = resultsTable();
    if (table && table.tBodies[0]) {
      Array.prototype.forEach.call(table.tBodies[0].rows, function (tr) {
        var rankEl = tr.querySelector(".rank-col") || tr.cells[0];
        var logo = tr.querySelector(".rs-club-with-logo");
        var img = logo && logo.querySelector("img");
        var code = logo ? String(logo.textContent || "").replace(/\s+/g, " ").trim() : "";
        rows.push({
          rank: rankEl ? String(rankEl.textContent || "").replace(/\s+/g, " ").trim() : "",
          code: code,
          logo: img ? (img.getAttribute("src") || "") : ""
        });
      });
    }
    if (!rows.length) {
      (state.teams || []).forEach(function (t, i) {
        rows.push({ rank: String(i + 1), code: clubCode(t), logo: t.club_logo || "" });
      });
    }
    return rows;
  }

  function closedMatches() {
    return (state.matches || []).filter(function (m) {
      return String(m.status || "").toLowerCase() === "complete";
    }).slice().sort(function (a, b) {
      return Number(b.match_no) - Number(a.match_no);
    });
  }

  function teamByCode(code) {
    var c = String(code || "").replace(/\s+/g, " ").trim().toUpperCase();
    return (state.teams || []).filter(function (t) {
      return String(clubCode(t) || "").toUpperCase() === c ||
        String(t.team_name || "").toUpperCase() === c;
    })[0];
  }

  function closedRaceScore(m, team) {
    if (!team) return "";
    var id = Number(team.team_id);
    if (Number(m.team_a_id) === id || Number(m.team_blue_id) === id) {
      return m.score_a == null || m.score_a === "" ? "" : String(m.score_a);
    }
    if (Number(m.team_b_id) === id || Number(m.team_green_id) === id) {
      return m.score_b == null || m.score_b === "" ? "" : String(m.score_b);
    }
    return "";
  }

  function goldRaceTableHtml() {
    var closed = closedMatches();
    var lastWin = closed.length ? Number(closed[0].winner_team_id || 0) : 0;
    var heads = '<th class="rank-col">Rank</th><th class="club-col">Club</th><th class="total-col">Total</th>';
    closed.forEach(function (m) {
      heads += '<th class="race-col">R' + Number(m.match_no) + "</th>";
    });
    var built = goldRaceRows().map(function (row) {
      var team = teamByCode(row.code);
      var total = 0;
      var races = [];
      closed.forEach(function (m) {
        var sc = closedRaceScore(m, team);
        if (sc !== "" && !isNaN(Number(sc))) total += Number(sc);
        races.push(sc);
      });
      return {
        row: row,
        team: team,
        total: total,
        races: races,
        wonLast: !!(team && lastWin && Number(team.team_id) === lastWin)
      };
    });
    if (closed.length) {
      built.sort(function (a, b) {
        if (a.total !== b.total) return a.total - b.total;
        if (a.wonLast !== b.wonLast) return a.wonLast ? -1 : 1;
        return 0;
      });
      built.forEach(function (item, i) { item.rank = i + 1; });
    }
    var body = "";
    built.forEach(function (item) {
      var races = "";
      item.races.forEach(function (sc) {
        races += '<td class="race-col' + (sc !== "" ? " score-counts" : "") + '">' + esc(sc) + "</td>";
      });
      var medal = "";
      if (closed.length && item.rank === 1) medal = "medal-gold";
      else if (closed.length && item.rank === 2) medal = "medal-silver";
      else if (closed.length && item.rank === 3) medal = "medal-bronze";
      body += "<tr" + (medal ? ' class="' + medal + '"' : "") + ">" +
        '<td class="rank-col">' + (closed.length ? String(item.rank) : "") + "</td>" +
        '<td class="club-col"><span class="rs-club-with-logo">' + logoImg(item.row.logo, item.row.code) + esc(item.row.code) + "</span></td>" +
        '<td class="total-col">' + (closed.length ? String(item.total) : "") + "</td>" +
        races +
        "</tr>";
    });
    if (!body) {
      body = '<tr><td class="rank-col"></td><td class="club-col"></td><td class="total-col"></td></tr>';
    }
    return (
      '<div class="table-wrapper" id="macTslGoldSheet">' +
        '<table class="fleet-results-table rs-compact-row-logos" id="tslGoldTable">' +
          "<thead><tr>" + heads + "</tr></thead><tbody>" + body + "</tbody>" +
        "</table>" +
      "</div>"
    );
  }

  function insertGoldRaceTable() {
    var sec = firstFleet();
    if (!sec) return;
    var html = goldRaceTableHtml();
    var existing = document.getElementById("macTslGoldSheet");
    if (existing) {
      existing.outerHTML = html;
      return;
    }
    var box = document.createElement("div");
    box.innerHTML = html;
    var node = box.firstChild;
    var oldWrap = sec.querySelector(".table-wrapper");
    if (oldWrap) oldWrap.parentNode.insertBefore(node, oldWrap);
    else {
      var hdr = sec.querySelector(".class-header");
      if (hdr) hdr.parentNode.insertBefore(node, hdr.nextSibling);
      else sec.appendChild(node);
    }
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
        return String(s.team_name || "").trim() === name || String(s.club_abbrev || "") === club || String(s.club_abbrev || "") === name;
      })[0];
      if (nameCell) {
        var code = (row && row.club_abbrev) || club || "";
        var existing = nameCell.querySelector(".rs-club-with-logo");
        if (existing) {
          var keep = existing.querySelector("img");
          existing.innerHTML = "";
          if (keep) existing.appendChild(keep);
          existing.appendChild(document.createTextNode(code || name));
        } else if (!nameCell.querySelector(".tsl-team-club")) {
          var wrap = document.createElement("span");
          wrap.className = "rs-club-with-logo tsl-team-club";
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
          wrap.appendChild(document.createTextNode(code || name));
          nameCell.innerHTML = "";
          nameCell.appendChild(wrap);
        }
        nameCell.classList.add("club-col");
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
      }
      el.className = "fleet-section";
      host.insertBefore(el, printRow || null);
    });
    var boats = document.getElementById("macTslBoats");
    if (boats && boats.parentNode) boats.parentNode.removeChild(boats);
  }

  function renderAll() {
    tidyFleetHeader();
    injectMButtons();
    applyStandingsTable();
    insertGoldRaceTable();
    renderTeams();
    renderSchedule();
    renderMatches();
    syncSheetType();
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
