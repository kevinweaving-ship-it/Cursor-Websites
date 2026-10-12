/**
 * MAC TSL WC — Teams register, M+/M− matches, match entry, overall W/L table.
 * Only /regatta/2026-10-17-mac-tsl-wc-team-sailing. Reuses .card / .table / .section-title.
 * Does not load club-score-edit (Dart / Midmar / Appendix A stay untouched).
 */
(function () {
  "use strict";
  if (window.__SSA_MAC_TSL_ADMIN__) return;
  window.__SSA_MAC_TSL_ADMIN__ = true;

  var RID = "2026-10-17-mac-tsl-wc-team-sailing";
  var JS_VER = "20261012a";
  var CSS_ID = "mac-tsl-admin-css";
  var ROOT_ID = "macTslAdmin";
  var MATCHES_ID = "macTslMatches";
  var SCHED_ID = "macTslSchedule";
  var BOATS_ID = "macTslBoats";
  var state = { teams: [], matches: [], standings: [], boats: [], colours: ["Blue", "Green"], format: "rr28", settings: {}, schedule: {} };
  var saveTimer = null;

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
        try {
          j = t ? JSON.parse(t) : null;
        } catch (e) {}
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
      "#macTslAdmin,#macTslMatches,#macTslSchedule,#macTslBoats{margin:16px 0}",
      "#macTslAdmin .section-title,#macTslMatches .section-title,#macTslSchedule .section-title,#macTslBoats .section-title{margin:0 0 0.4rem;padding-bottom:0.35rem}",
      ".tsl-team{display:flex;flex-direction:column;gap:8px;padding:0.5rem 0.75rem;margin:0 0 12px;border:2px solid #001f3f;border-radius:8px;background:#fff}",
      ".tsl-team-head{display:flex;align-items:center;gap:10px;flex-wrap:wrap}",
      ".tsl-team-logo{width:56px;height:40px;object-fit:contain;background:#fff;border:1px solid #e0e0e0;border-radius:4px}",
      ".tsl-team-logo--empty{display:inline-block;width:56px;height:40px;background:#f5f7fa;border:1px dashed #cbd5e1;border-radius:4px}",
      ".tsl-team-head strong{color:#001f3f}",
      ".tsl-field{display:flex;flex-direction:column;gap:4px;min-width:0;flex:1 1 140px}",
      ".tsl-field label{font:700 0.75rem/1.2 Arial,Helvetica,sans-serif;color:#001f3f;text-transform:uppercase;letter-spacing:.02em}",
      ".tsl-field input,.tsl-field select{min-height:44px;padding:8px 10px;border:1.5px solid #001f3f;border-radius:6px;font:600 14px/1.2 Arial,Helvetica,sans-serif;color:#1e293b;background:#fff;width:100%;box-sizing:border-box}",
      ".tsl-boats{width:100%;border-collapse:collapse}",
      ".tsl-boats th,.tsl-boats td{padding:0.4rem 0.4rem;border-bottom:1px solid #e0e0e0;vertical-align:top;text-align:left}",
      ".tsl-boats th{font:700 0.75rem/1.2 Arial,Helvetica,sans-serif;color:#001f3f;text-transform:uppercase}",
      ".tsl-sas{display:block;margin-top:4px;font:700 12px/1.2 Arial,Helvetica,sans-serif;color:#334155}",
      ".tsl-sas--missing{color:#b91c1c}",
      ".tsl-ac{position:relative}",
      ".tsl-ac-list{position:absolute;left:0;right:0;z-index:80;margin:2px 0 0;padding:4px 0;list-style:none;background:#fff;border:2px solid #001f3f;border-radius:8px;max-height:240px;overflow-y:auto}",
      ".tsl-ac-list li{margin:0;padding:8px 10px;cursor:pointer;font:600 13px/1.3 Arial,Helvetica,sans-serif;color:#1a2750}",
      ".tsl-ac-list li:hover{background:#e0e7ff}",
      ".tsl-ac-list .tsl-ac-sub{display:block;font:500 11px/1.3 Arial,Helvetica,sans-serif;color:#64748b}",
      ".tsl-add,.tsl-save,.tsl-del,.club-race-step-add,.club-race-step-sub{min-height:44px;min-width:44px;padding:8px 12px;border:1.5px solid #001f3f;border-radius:8px;background:#001f3f;color:#fff;font:700 14px/1.2 Arial,Helvetica,sans-serif;cursor:pointer}",
      ".tsl-del{background:#fff;color:#DC143C;border-color:#DC143C}",
      ".tsl-warn{color:#b91c1c;font:700 12px/1.4 Arial,Helvetica,sans-serif;margin:4px 0 0}",
      ".tsl-msg{color:#334155;font:600 13px/1.4 Arial,Helvetica,sans-serif;margin:8px 0}",
      ".tsl-match{margin:0 0 16px;padding:0.5rem 0.75rem;border:2px solid #001f3f;border-radius:8px;background:#fff}",
      ".tsl-match-h{display:flex;align-items:baseline;justify-content:space-between;gap:8px;flex-wrap:wrap;margin-bottom:8px}",
      ".tsl-match-h strong{color:#001f3f;font-size:1rem}",
      ".tsl-sides{display:flex;gap:12px;flex-wrap:wrap}",
      ".tsl-side{flex:1 1 260px;min-width:0}",
      ".tsl-side h3{margin:0 0 8px;color:#001f3f;font:700 0.85rem/1.2 Arial,Helvetica,sans-serif;text-transform:uppercase}",
      ".tsl-row2{display:flex;gap:8px;flex-wrap:wrap}",
      ".tsl-override{margin-top:8px}",
      ".club-race-step.tsl-mstep{display:none;align-items:center;gap:6px}",
      ".regatta-page--super-admin-edit .club-race-step.tsl-mstep{display:inline-flex}",
      "#macTslAdmin,#macTslMatches,#macTslSchedule,#macTslBoats{display:none}",
      ".regatta-page--super-admin-edit #macTslAdmin,.regatta-page--super-admin-edit #macTslMatches,.regatta-page--super-admin-edit #macTslSchedule,.regatta-page--super-admin-edit #macTslBoats{display:block}",
      ".tsl-blue{color:#1d4ed8}",
      ".tsl-green{color:#15803d}",
      ".regatta-page[data-mac-tsl=\"1\"] th.tsl-hide-mp,.regatta-page[data-mac-tsl=\"1\"] td.tsl-hide-mp{display:none}",
      ".regatta-page[data-mac-tsl=\"1\"] .tsl-col-wins{font-weight:800;color:#1a2750;text-align:center}",
      ".regatta-page[data-mac-tsl=\"1\"] .race-col,.regatta-page[data-mac-tsl=\"1\"] .tsl-mcol{text-align:center;font-weight:800}",
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
    function hide() {
      list.hidden = true;
      list.innerHTML = "";
    }
    function show(items) {
      list.innerHTML = "";
      if (!items.length) {
        hide();
        return;
      }
      items.forEach(function (it) {
        var li = document.createElement("li");
        if (kind === "club") {
          li.innerHTML = esc(it.code || it.name) + '<span class="tsl-ac-sub">' + esc(it.name || "") + "</span>";
        } else {
          var sas = it.sas_id ? "SAS " + it.sas_id : "SAS missing";
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

  function sailorCell(team, boatNo, role, sailor) {
    var sid = sailor && sailor.sas_id ? String(sailor.sas_id) : "";
    var name = sailor && sailor.name ? sailor.name : "";
    var warn = name && !sid;
    return (
      '<div class="tsl-ac">' +
        '<input type="text" data-role="' + role + '" data-boat="' + boatNo + '" value="' + esc(name) + '" placeholder="Name or SAS ID" autocomplete="off" />' +
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
      rows +=
        "<tr><th>Boat " + n + "</th><td>" +
        sailorCell(team, n, "helm", b.helm) +
        "</td><td>" +
        sailorCell(team, n, "crew", b.crew) +
        "</td></tr>";
    }
    var warns = (team.warnings || []).map(function (w) { return '<div class="tsl-warn">' + esc(w) + "</div>"; }).join("");
    return (
      '<div class="tsl-team" data-team-id="' + esc(team.team_id || "") + '">' +
        '<div class="tsl-team-head">' + logo +
          "<strong>" + esc(team.club_name || team.club_abbrev || "Select a club") + "</strong>" +
          (team.club_id ? '<span class="tsl-sas">Club ID ' + esc(team.club_id) + "</span>" : "") +
        "</div>" +
        '<div class="tsl-row2">' +
          '<div class="tsl-field tsl-ac"><label>Club</label>' +
            '<input type="text" data-field="club" value="' + esc(team.club_name || team.club_abbrev || "") + '" placeholder="Type club name" autocomplete="off" />' +
            '<input type="hidden" data-field="club_id" value="' + esc(team.club_id || "") + '" />' +
          "</div>" +
          '<div class="tsl-field"><label>Team name</label>' +
            '<input type="text" data-field="team_name" value="' + esc(team.team_name || "") + '" placeholder="Defaults to club name" />' +
          "</div>" +
          '<div class="tsl-field"><label>Colour / abbrev</label>' +
            '<input type="text" data-field="team_abbrev" value="' + esc(team.team_abbrev || "") + '" maxlength="8" />' +
          "</div>" +
        "</div>" +
        '<table class="table tsl-boats"><thead><tr><th></th><th>Helm</th><th>Crew</th></tr></thead><tbody>' +
        rows +
        "</tbody></table>" +
        warns +
        '<div class="tsl-row2">' +
          '<button type="button" class="tsl-save">Save team</button>' +
          (team.team_id ? '<button type="button" class="tsl-del">Remove</button>' : "") +
        "</div>" +
        '<div class="tsl-msg"></div>' +
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
      team_abbrev: ((panel.querySelector('input[data-field="team_abbrev"]') || {}).value || "").trim(),
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
        var abInp = panel.querySelector('input[data-field="team_abbrev"]');
        if (nameInp && !nameInp.value.trim()) nameInp.value = it.name || it.code || "";
        if (abInp && !abInp.value.trim()) abInp.value = it.code || "";
        var head = panel.querySelector(".tsl-team-head strong");
        if (head) head.textContent = it.name || it.code || "";
        var img = panel.querySelector(".tsl-team-logo");
        if (it.logo) {
          if (!img) {
            img = document.createElement("img");
            img.className = "tsl-team-logo";
            panel.querySelector(".tsl-team-head").insertBefore(img, panel.querySelector(".tsl-team-head").firstChild);
          }
          img.src = it.logo;
        }
      });
    }
    panel.querySelectorAll('input[data-role]').forEach(function (inp) {
      bindTypeahead(inp, "sailor", function (q) {
        var cid = (clubId && clubId.value) || "";
        return "/api/tsl/" + encodeURIComponent(RID) + "/sailors-search?q=" + encodeURIComponent(q) +
          (cid ? "&club_id=" + encodeURIComponent(cid) : "") + "&limit=35";
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
    var html = '<h2 class="section-title">Teams</h2>';
    if (!state.teams.length) {
      html += '<p class="tsl-msg">No second team is stored. Add a team from an existing club — do not invent sailors.</p>';
    }
    state.teams.forEach(function (t) { html += teamPanelHtml(t); });
    html += '<button type="button" class="tsl-add" id="tslAddTeam">Add Team</button>';
    html += '<div id="tslAddSlot"></div>';
    root.innerHTML = html;
    root.querySelectorAll(".tsl-team").forEach(wireTeamPanel);
    var add = document.getElementById("tslAddTeam");
    if (add) {
      add.addEventListener("click", function () {
        var slot = document.getElementById("tslAddSlot");
        if (!slot || slot.querySelector(".tsl-team")) return;
        slot.innerHTML = teamPanelHtml({ boats: [{ boat_no: 1 }, { boat_no: 2 }, { boat_no: 3 }] });
        wireTeamPanel(slot.querySelector(".tsl-team"));
        var club = slot.querySelector('input[data-field="club"]');
        if (club) club.focus();
      });
    }
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
  function colourOptions(selected, exclude) {
    var html = '<option value="">Colour</option>';
    (state.colours || ["Blue", "Green"]).forEach(function (c) {
      if (exclude && c === exclude) return;
      html += '<option value="' + esc(c) + '"' + (selected === c ? " selected" : "") + ">" + esc(c) + "</option>";
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
          esc(s.name) + " · " + esc(s.sas_id) + "</option>";
      });
    });
    return html;
  }
  function findBoat(match, teamId, pairing) {
    return (match.boats || []).filter(function (b) {
      return Number(b.team_id) === Number(teamId) && Number(b.pairing_no) === Number(pairing);
    })[0] || {};
  }
  function teamById(id) {
    return state.teams.filter(function (t) { return Number(t.team_id) === Number(id); })[0];
  }

  function boatRow(match, teamId, pairing, pairingColour) {
    var team = teamById(teamId);
    var b = findBoat(match, teamId, pairing);
    var roster = team && team.boats ? team.boats.filter(function (x) { return Number(x.boat_no) === pairing; })[0] : null;
    var helm = b.helm_sas_id || (roster && roster.helm && roster.helm.sas_id) || "";
    var crew = b.crew_sas_id || (roster && roster.crew && roster.crew.sas_id) || "";
    var places = "";
    for (var i = 1; i <= 6; i += 1) {
      places += '<option value="' + i + '"' + (Number(b.finish_place) === i ? " selected" : "") + ">" + i + "</option>";
    }
    var pens = ["", "DNS", "DNF", "DSQ", "OCS", "RET", "NSC", "DNE"];
    var pen = pens.map(function (p) {
      return '<option value="' + p + '"' + ((b.penalty_status || "") === p ? " selected" : "") + ">" + (p || "—") + "</option>";
    }).join("");
    var colour = pairingColour || "";
    var phys = (state.boats || []).filter(function (pb) { return !colour || pb.colour === colour; });
    var psel = '<option value="">Boat</option>';
    phys.forEach(function (pb) {
      psel += '<option value="' + pb.boat_id + '"' + (Number(b.physical_boat_id) === Number(pb.boat_id) ? " selected" : "") + ">" +
        esc(pb.colour + " " + pb.boat_no) + (pb.bow_number ? " · bow " + esc(pb.bow_number) : "") + "</option>";
    });
    return (
      "<tr data-team-id=\"" + esc(teamId || "") + "\" data-pairing=\"" + pairing + "\">" +
        "<td>" + esc(colour || "Boat") + " " + pairing + "</td>" +
        '<td><select data-k="physical_boat_id">' + psel + "</select></td>" +
        '<td><input type="text" data-k="bow_number" value="' + esc(b.bow_number || "") + '" maxlength="8" /></td>' +
        '<td><input type="text" data-k="sail_number" value="' + esc(b.sail_number || "") + '" maxlength="16" /></td>' +
        '<td><select data-k="helm_sas_id">' + sailorOptions(team, helm) + "</select></td>" +
        '<td><select data-k="crew_sas_id">' + sailorOptions(team, crew) + "</select></td>" +
        '<td><select data-k="finish_place"><option value=""></option>' + places + "</select></td>" +
        '<td><select data-k="penalty_status">' + pen + "</select></td>" +
      "</tr>"
    );
  }

  function matchHtml(match) {
    var st = match.status === "complete" ? "Official" : (match.status === "scheduled" ? "Scheduled" : "Open");
    return (
      '<div class="tsl-match" data-match-id="' + match.match_id + '">' +
        '<div class="tsl-match-h"><strong>' + esc(match.label || ("M" + match.match_no)) + "</strong>" +
          "<span>" + esc(st) + " · " + esc(match.round_label || "RR") + "</span></div>" +
        '<div class="tsl-sides">' +
          '<div class="tsl-side" data-side="a">' +
            "<h3 class=\"tsl-blue\">Team Blue</h3>" +
            '<div class="tsl-row2">' +
              '<div class="tsl-field"><label>Blue team</label><select data-k="team_a_id">' + teamOptions(match.team_a_id) + "</select></div>" +
            "</div>" +
            '<div class="table-container"><table class="table tsl-boats"><thead><tr><th></th><th>Boat</th><th>Bow</th><th>Sail</th><th>Helm</th><th>Crew</th><th>Place</th><th>Pen</th></tr></thead><tbody class="tsl-a-boats">' +
            (match.team_a_id ? [1, 2, 3].map(function (n) { return boatRow(match, match.team_a_id, n, "Blue"); }).join("") : "") +
            "</tbody></table></div>" +
          "</div>" +
          '<div class="tsl-side" data-side="b">' +
            "<h3 class=\"tsl-green\">Team Green</h3>" +
            '<div class="tsl-row2">' +
              '<div class="tsl-field"><label>Green team</label><select data-k="team_b_id">' + teamOptions(match.team_b_id, match.team_a_id) + "</select></div>" +
            "</div>" +
            '<div class="table-container"><table class="table tsl-boats"><thead><tr><th></th><th>Boat</th><th>Bow</th><th>Sail</th><th>Helm</th><th>Crew</th><th>Place</th><th>Pen</th></tr></thead><tbody class="tsl-b-boats">' +
            (match.team_b_id ? [1, 2, 3].map(function (n) { return boatRow(match, match.team_b_id, n, "Green"); }).join("") : "") +
            "</tbody></table></div>" +
          "</div>" +
        "</div>" +
        '<div class="tsl-row2 tsl-override">' +
          '<div class="tsl-field"><label>Official override winner</label><select data-k="override_winner_team_id">' +
            '<option value="">No override</option>' + teamOptions(match.override_winner_team_id) +
          "</select></div>" +
          '<div class="tsl-field"><label>Override reason</label><input type="text" data-k="override_reason" value="' + esc(match.override_reason || "") + '" /></div>' +
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
      if (aBody) aBody.innerHTML = match.team_a_id ? [1, 2, 3].map(function (n) { return boatRow(match, match.team_a_id, n, "Blue"); }).join("") : "";
      if (bBody) bBody.innerHTML = match.team_b_id ? [1, 2, 3].map(function (n) { return boatRow(match, match.team_b_id, n, "Green"); }).join("") : "";
    }
    box.querySelector('[data-k="team_a_id"]').addEventListener("change", refreshSides);
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

  function teamName(id) {
    var t = teamById(id);
    return t ? (t.team_name || t.club_abbrev || id) : (id ? String(id) : "—");
  }

  function renderBoats() {
    var root = document.getElementById(BOATS_ID);
    if (!root) return;
    var html = '<h2 class="section-title">Physical boats</h2><p class="tsl-msg">Six SAS TSL boats — three Blue, three Green. Bow and sail identify the boat for a match, not a sailor.</p><table class="table tsl-boats"><thead><tr><th>Boat</th><th>Bow</th><th>Sail</th></tr></thead><tbody>';
    (state.boats || []).forEach(function (b) {
      html += '<tr data-boat-id="' + b.boat_id + '"><td>' + esc(b.colour + " " + b.boat_no) + '</td>' +
        '<td><input type="text" data-k="bow_number" value="' + esc(b.bow_number || "") + '" maxlength="8" /></td>' +
        '<td><input type="text" data-k="sail_number" value="' + esc(b.sail_number || "") + '" maxlength="16" /></td></tr>';
    });
    html += '</tbody></table><button type="button" class="tsl-save" id="tslSaveBoats">Save boats</button><div class="tsl-msg" id="tslBoatsMsg"></div>';
    root.innerHTML = html;
    var btn = document.getElementById("tslSaveBoats");
    if (btn) {
      btn.addEventListener("click", function () {
        var boats = [];
        root.querySelectorAll("tr[data-boat-id]").forEach(function (tr) {
          boats.push({
            boat_id: Number(tr.getAttribute("data-boat-id")),
            bow_number: (tr.querySelector('[data-k="bow_number"]') || {}).value || "",
            sail_number: (tr.querySelector('[data-k="sail_number"]') || {}).value || ""
          });
        });
        api("/api/tsl/" + encodeURIComponent(RID) + "/boats", {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ boats: boats })
        }).then(function () {
          var m = document.getElementById("tslBoatsMsg");
          if (m) m.textContent = "Saved.";
          return loadState();
        }).catch(function (e) {
          var m = document.getElementById("tslBoatsMsg");
          if (m) m.textContent = e.message;
        });
      });
    }
  }

  function renderSchedule() {
    var root = document.getElementById(SCHED_ID);
    if (!root) return;
    var fmt = state.format || "rr28";
    var html = '<h2 class="section-title">Schedule</h2>';
    html += '<div class="tsl-row2"><div class="tsl-field"><label>Championship format</label><select id="tslFormat">' +
      '<option value="rr28"' + (fmt === "rr28" ? " selected" : "") + ">Full round robin (28 matches)</option>" +
      '<option value="flights16"' + (fmt === "flights16" ? " selected" : "") + ">Two flights + sail-offs (16 matches)</option>" +
      "</select></div>";
    if (fmt === "flights16" || true) {
      html += '<div class="tsl-field"><label>Flight A (4 teams)</label><select id="tslFa" multiple size="4">';
      (state.teams || []).forEach(function (t) {
        var sel = ((state.settings || {}).flight_a || []).indexOf(t.team_id) >= 0 || ((state.settings || {}).flight_a || []).indexOf(String(t.team_id)) >= 0;
        html += '<option value="' + t.team_id + '"' + (sel ? " selected" : "") + ">" + esc(t.team_name) + "</option>";
      });
      html += "</select></div><div class=\"tsl-field\"><label>Flight B (4 teams)</label><select id=\"tslFb\" multiple size=\"4\">";
      (state.teams || []).forEach(function (t) {
        var sel = ((state.settings || {}).flight_b || []).indexOf(t.team_id) >= 0 || ((state.settings || {}).flight_b || []).indexOf(String(t.team_id)) >= 0;
        html += '<option value="' + t.team_id + '"' + (sel ? " selected" : "") + ">" + esc(t.team_name) + "</option>";
      });
      html += "</select></div>";
    }
    html += "</div>";
    html += '<div class="tsl-row2"><button type="button" class="tsl-save" id="tslGen">Generate schedule</button>' +
      '<button type="button" class="tsl-save" id="tslVal">Validate schedule</button></div>';
    html += '<div class="tsl-msg" id="tslSchedMsg"></div>';
    var warns = ((state.schedule || {}).warnings || []);
    warns.forEach(function (w) { html += '<div class="tsl-warn">' + esc(w) + "</div>"; });
    html += '<div class="table-container"><table class="table"><thead><tr><th>Match</th><th>Round</th><th>Blue</th><th>Green</th><th>Status</th><th>Winner</th></tr></thead><tbody>';
    (state.matches || []).forEach(function (m) {
      html += "<tr><td>" + esc(m.label || ("M" + m.match_no)) + "</td><td>" + esc(m.round_label || "") + "</td><td>" +
        esc(teamName(m.team_a_id)) + "</td><td>" + esc(teamName(m.team_b_id)) + "</td><td>" + esc(m.status || "") +
        "</td><td>" + esc(teamName(m.winner_team_id)) + "</td></tr>";
    });
    html += "</tbody></table></div>";
    root.innerHTML = html;
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
    var val = document.getElementById("tslVal");
    if (val) {
      val.addEventListener("click", function () {
        var msg = document.getElementById("tslSchedMsg");
        var w = ((state.schedule || {}).warnings || []);
        if (msg) msg.textContent = w.length ? w.join(" · ") : "Schedule is valid.";
      });
    }
  }

  function renderMatches() {
    var root = document.getElementById(MATCHES_ID);
    if (!root) return;
    var html = '<h2 class="section-title">Match entry</h2>';
    if (!state.matches.length) {
      html += '<p class="tsl-msg">Generate a schedule or use M+ on the fleet header to create M1.</p>';
    }
    state.matches.forEach(function (m) { html += matchHtml(m); });
    root.innerHTML = html;
    root.querySelectorAll(".tsl-match").forEach(wireMatch);
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
    var club = sec.querySelector(".class-header-club-logo-col");
    var hdr = sec.querySelector(".class-header");
    if (club) club.insertBefore(box, club.firstChild);
    else if (hdr) hdr.insertBefore(box, hdr.firstChild);
    else sec.insertBefore(box, sec.firstChild);
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

  function headerLabel(th) {
    return String(th.textContent || "").replace(/\s+/g, " ").trim().toLowerCase();
  }
  function applyStandingsTable() {
    var table = resultsTable();
    if (!table) return;
    var thead = table.tHead && table.tHead.rows[0];
    if (!thead) return;
    var hideNames = { class: 1, "sail no": 1, "sailno": 1, total: 1, nett: 1, "jib": 1, "bow": 1, "hull": 1, discards: 1, "to count": 1, colour: 1 };
    var mlNames = { "boat name": 1, team: 1, helm: 1, crew: 1, helms: 1, crews: 1, losses: 1, "win %": 1, played: 1, matches: 1 };
    Array.prototype.forEach.call(thead.cells, function (th) {
      var lab = headerLabel(th);
      if (hideNames[lab]) th.classList.add("tsl-hide-mp");
      if (mlNames[lab]) th.classList.add("tsl-ml-only");
      if (lab === "boat name") th.textContent = "Team";
      var rm = lab.match(/^r(\d+)$/);
      if (rm) th.textContent = "M" + rm[1];
    });
    var matchNos = (state.matches || []).map(function (m) { return Number(m.match_no); });
    matchNos.forEach(function (n) {
      var label = "M" + n;
      var found = false;
      Array.prototype.forEach.call(thead.cells, function (th) {
        if (headerLabel(th) === label.toLowerCase() || headerLabel(th) === ("r" + n)) found = true;
      });
      if (!found) {
        var th = document.createElement("th");
        th.className = "tsl-mcol";
        th.textContent = label;
        var winsTh = Array.prototype.filter.call(thead.cells, function (c) { return headerLabel(c) === "wins"; })[0];
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
    var hasWins = Array.prototype.some.call(thead.cells, function (th) { return headerLabel(th) === "wins"; });
    if (!hasWins) {
      var wth = document.createElement("th");
      wth.className = "tsl-col-wins";
      wth.textContent = "Wins";
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
      var pct = document.createElement("th");
      pct.className = "tsl-ml-only";
      pct.textContent = "Win %";
      thead.appendChild(pct);
      Array.prototype.forEach.call(table.tBodies[0] ? table.tBodies[0].rows : [], function (tr) {
        var a = document.createElement("td");
        a.className = "tsl-ml-only tsl-loss";
        a.textContent = "0";
        tr.appendChild(a);
        var b = document.createElement("td");
        b.className = "tsl-ml-only tsl-wpct";
        b.textContent = "0";
        tr.appendChild(b);
      });
    }
    Array.prototype.forEach.call(thead.cells, function (th, i) {
      var lab = headerLabel(th);
      Array.prototype.forEach.call(table.tBodies[0] ? table.tBodies[0].rows : [], function (tr) {
        if (!tr.cells[i]) return;
        if (th.classList.contains("tsl-hide-mp")) tr.cells[i].classList.add("tsl-hide-mp");
        if (th.classList.contains("tsl-ml-only")) tr.cells[i].classList.add("tsl-ml-only");
        if (lab === "helm" || lab === "crew" || lab === "helms" || lab === "crews" || lab === "team" || lab === "boat name") {
          tr.cells[i].classList.add("tsl-ml-only");
        }
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
      if (!row) return;
      if (idx.rank != null && tr.cells[idx.rank]) tr.cells[idx.rank].textContent = row.rank || "";
      if (idx.wins != null && tr.cells[idx.wins]) tr.cells[idx.wins].textContent = row.wins;
      if (idx.played != null && tr.cells[idx.played]) tr.cells[idx.played].textContent = row.matches_played;
      if (idx.matches != null && tr.cells[idx.matches]) tr.cells[idx.matches].textContent = row.matches_played;
      if (idx.losses != null && tr.cells[idx.losses]) tr.cells[idx.losses].textContent = row.losses;
      if (idx["win %"] != null && tr.cells[idx["win %"]]) tr.cells[idx["win %"]].textContent = row.win_pct;
      Object.keys(row.cells || {}).forEach(function (k) {
        var i2 = idx[k.toLowerCase()] != null ? idx[k.toLowerCase()] : idx["r" + k.slice(1)];
        if (i2 != null && tr.cells[i2]) tr.cells[i2].textContent = row.cells[k];
      });
    });
  }

  function ensureRoots() {
    var page = document.querySelector(".regatta-page");
    if (!page) return;
    var host = page.querySelector(".container") || page;
    [["macTslSchedule", SCHED_ID], ["macTslBoats", BOATS_ID], ["macTslMatches", MATCHES_ID], ["macTslAdmin", ROOT_ID]].forEach(function (pair) {
      if (!document.getElementById(pair[1])) {
        var el = document.createElement("div");
        el.id = pair[1];
        el.className = "card";
        host.appendChild(el);
      }
    });
  }

  function renderAll() {
    injectMButtons();
    applyStandingsTable();
    renderSchedule();
    renderBoats();
    renderMatches();
    renderTeams();
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
    loadState().catch(function () {
      renderAll();
    });
    var tog = document.getElementById("regattaSaEditToggle");
    if (tog && !tog._tslBound) {
      tog.addEventListener("change", function () { renderAll(); });
      tog._tslBound = true;
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
