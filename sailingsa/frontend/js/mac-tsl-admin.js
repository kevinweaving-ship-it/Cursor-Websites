/**
 * MAC TSL WC — Event URL results + admin. Same .class-header / table / .action-button as the fleet sheet.
 * Only /regatta/2026-10-17-mac-tsl-wc-team-sailing. No club-score-edit.
 * Sailor search popup (reuse for Add Team / add sailors): docs/TSL_SAILOR_SEARCH_POPUP.md
 */
(function () {
  "use strict";
  if (window.__SSA_MAC_TSL_ADMIN__) return;
  window.__SSA_MAC_TSL_ADMIN__ = true;

  var RID = "2026-10-17-mac-tsl-wc-team-sailing";
  var JS_VER = "20261014k";
  var CSS_ID = "mac-tsl-admin-css";
  var ROOT_ID = "macTslAdmin";
  var MATCHES_ID = "macTslMatches";
  var SCHED_ID = "macTslSchedule";
  var state = { teams: [], matches: [], standings: [], format: "rr28", settings: {}, schedule: {} };
  var sexChoice = {};
  var pickState = {
    teamId: "",
    boat: 1,
    role: "",
    fromRole: "",
    sailor: null,
    club: "",
    mode: "",
    addLoop: false,
    addStep: 1,
    sex: "M",
    clubPick: null,
    original: null,
    selected: null,
    replacement: null,
    swapped: false,
    flight: "",
    bow: ""
  };
  var moveBurst = null;
  var moveSaveTimer = 0;
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
        { name: "Robyn Roselli", sas_id: "28089" }
      ]
    },
    "Eden District": {
      helms: [
        { name: "Lulonke Lenks", sas_id: "15711", sex: "M" },
        { name: "Isabella Watson", sas_id: "27609", sex: "F" },
        { name: "Owen Conradie", sas_id: "23531", sex: "M" }
      ],
      crews: [
        { name: "Christian Cilliers", sas_id: "13488", sex: "M" },
        { name: "Arthur Watson", sas_id: "27610", sex: "M" },
        { name: "Rainier Lamprecht", sas_id: "28588", sex: "M" }
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
      "#macTslAdmin{display:none}",
      "#macTslSchedule{display:block}",
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
      ".regatta-page[data-mac-tsl=\"1\"] .fleet-section:not(#macTslAdmin):not(#macTslSchedule):not(#macTslMatches)>.table-wrapper:not(#macTslGoldSheet){display:none}",
      "#macTslGoldSheet{border:2px solid #1a2750;border-radius:10px;background:#fff;box-sizing:border-box;overflow:hidden;margin-top:20px;margin-bottom:20px}",
      "#macTslGoldSheet .fleet-results-table{border:none;border-radius:8px}",
      "#macTslGoldSheet thead tr:first-child th{border-top:none}",
      "#macTslGoldSheet tbody tr:last-child td{border-bottom:none}",
      "#macTslGoldSheet th:first-child,#macTslGoldSheet td:first-child{border-left:none}",
      "#macTslGoldSheet th:last-child,#macTslGoldSheet td:last-child{border-right:none}",
      "#macTslGoldSheet thead tr:first-child th:first-child{border-top-left-radius:8px}",
      "#macTslGoldSheet thead tr:first-child th:last-child{border-top-right-radius:8px}",
      "#macTslGoldSheet tbody tr:last-child td:first-child{border-bottom-left-radius:8px}",
      "#macTslGoldSheet tbody tr:last-child td:last-child{border-bottom-right-radius:8px}",
      "@media (max-width:768px){#macTslGoldSheet{margin-top:12px;margin-bottom:12px}}",
      "@media (orientation:landscape) and (max-height:600px){#macTslGoldSheet{margin-top:6px;margin-bottom:6px}}",
      "#macTslFlightsCard{border:2px solid #1a2750;border-radius:8px;background:#fff;box-sizing:border-box;width:100%;max-width:100%;padding:8px;margin:0 0 8px;position:relative;overflow:hidden}",
      "#macTslFlightsCard .fleet-title-row{margin:0 0 8px;padding:0;font-weight:bold}",
      "#macTslFlightsCard .tsl-flight-cards{display:grid;grid-template-columns:1fr 1fr;gap:8px;width:100%;max-width:100%;min-width:0;box-sizing:border-box}",
      "#macTslFlightsCard .tsl-flight-card{border:2px solid #1a2750;border-radius:8px;background:#fff;box-sizing:border-box;margin:0;padding:8px;width:auto!important;max-width:100%!important;min-width:0;overflow:hidden}",
      "#macTslFlightsCard .tsl-flight-head{font-weight:bold;margin:0;text-align:left}",
      "#macTslFlightsCard .tsl-flight-card .table-wrapper{margin:8px 0 0;max-width:100%;overflow:hidden}",
      "#macTslFlightsCard .tsl-flight-card .fleet-results-table{transform-origin:top left}",
      "#macTslFlightsCard .tsl-flight-card .fleet-results-table th,#macTslFlightsCard .tsl-flight-card .fleet-results-table td,#macTslTeamsCard .tsl-team-card .fleet-results-table th,#macTslTeamsCard .tsl-team-card .fleet-results-table td{padding:2px 4px;line-height:1.2;vertical-align:middle}",
      "#macTslFlightsCard .fleet-results-table th{font-weight:bold}",
      "#macTslFlightsCard .tsl-colour-sq{display:inline-block;width:14px;height:14px;border:1px solid #1a2750;background:#fff;padding:0;margin:0;vertical-align:middle;box-sizing:border-box;cursor:default}",
      "#macTslFlightsCard .tsl-colour-sq.tsl-colour-blue{background:#1d4ed8;border-color:#1d4ed8}",
      "#macTslFlightsCard .tsl-colour-sq.tsl-colour-green{background:#15803d;border-color:#15803d}",
      ".regatta-page--super-admin-edit #macTslFlightsCard .tsl-colour-sq{cursor:pointer}",
      "#macTslFlightsCard .tsl-flight-top{display:block}",
      "#macTslFlightsCard .tsl-flight-team{display:inline-block;min-width:6em}",
      "#macTslFlightsCard .tsl-flight-team-hit{display:inline-flex;align-items:center;gap:4px;border:none;background:none;padding:0;margin:0;color:#1a2750;font:inherit;cursor:default;white-space:nowrap}",
      ".regatta-page--super-admin-edit #macTslFlightsCard .tsl-flight-team-hit{cursor:pointer}",
      "#macTslFlightsCard .tsl-rank,#macTslFlightsCard input.tsl-rank{width:1.4em;min-width:1.4em;max-width:2em;height:auto;min-height:0!important;padding:0!important;margin:0;border:none;border-radius:0;background:transparent;text-align:center;font:inherit;font-size:inherit;line-height:inherit;color:#1a2750;box-sizing:border-box}",
      "#macTslTeamsCard{border:2px solid #1a2750;border-radius:8px;background:#fff;box-sizing:border-box;width:100%;max-width:100%;padding:8px;margin-top:0;position:relative;overflow:hidden}",
      "#macTslTeamsCard .fleet-title-row{margin:0 0 8px;padding:0}",
      "#macTslTeamsCard .tsl-team-cards{display:grid;grid-template-columns:1fr 1fr;gap:8px;width:100%;max-width:100%;min-width:0;box-sizing:border-box}",
      "#macTslTeamsCard .tsl-team-card{border:2px solid #1a2750;border-radius:8px;background:#fff;box-sizing:border-box;margin:0;padding:8px;width:auto!important;max-width:100%!important;min-width:0;overflow:hidden}",
      "#macTslTeamsCard .tsl-team-card .table-wrapper{margin:8px 0 0;max-width:100%;overflow:hidden}",
      "#macTslTeamsCard .tsl-team-card .fleet-results-table{transform-origin:top left}",
      "#macTslTeamsCard .tsl-team-head{display:inline-flex;flex-direction:row;flex-wrap:nowrap;align-items:center;white-space:nowrap;font-weight:bold}",
      "#macTslTeamsCard .tsl-team-head .rs-club-row-logo-sm{margin:0 4px 0 0}",
      "#macTslTeamsCard .tsl-team-code{display:inline-flex;align-items:center;font-weight:bold}",
      "#macTslTeamsCard .tsl-team-dot{display:inline-flex;align-items:center;justify-content:center;line-height:1;height:1em;margin:0 4px;align-self:center;font-weight:bold}",
      "#macTslTeamsCard .tsl-team-full{display:inline-flex;align-items:center;font-weight:bold}",
      "#macTslTeamsCard .tsl-team-card .fleet-results-table th{font-weight:bold}",
      "#macTslTeamsCard .tsl-sex,#macTslTeamsCard .tsl-sailor-pick{display:inline;border:none;background:none;color:#1a2750;font:inherit;padding:0;margin:0;cursor:pointer;min-width:1em;text-align:left}",
      "#macTslTeamsCard .tsl-name-wrap{display:inline-flex;align-items:center;white-space:nowrap}",
      "#macTslTeamsCard .tsl-move{display:none;width:18px;height:18px;margin:0 4px 0 0;padding:0;border:none;background:url(/js/tsl-move-pad.png) center/contain no-repeat;vertical-align:middle;flex:0 0 auto;cursor:pointer}",
      ".regatta-page--super-admin-edit #macTslTeamsCard .tsl-move{display:inline-block}",
      ".regatta-page--super-admin-edit #macTslTeamsCard .tsl-sailor-name{cursor:pointer}",
      "#tslNamePop{position:fixed;left:50%;top:50%;transform:translate(-50%,-50%);right:auto;z-index:400;display:flex;flex-direction:column;gap:6px;margin:0;padding:8px;border:2px solid #1a2750;border-radius:8px;background:#fff;width:auto;max-width:28em;max-height:80vh;box-sizing:border-box;overflow:auto}",
      "#tslNamePop[hidden]{display:none}",
      "#tslNamePop .tsl-pop-row{display:flex;align-items:center;gap:6px;flex-wrap:wrap}",
      "#tslNamePop .tsl-pop-arrow{width:22px;height:16px;border:none;padding:0;margin:0;background:url(/js/tsl-swap-left.png) center/contain no-repeat;cursor:pointer;flex:0 0 auto}",
      "#tslNamePop #tslPopSearch{font-size:16px!important;line-height:1.25!important;min-width:8em;flex:1 1 10em;max-width:100%}",
      "#tslNamePop #tslPopSave{padding:2px 8px;min-height:0;line-height:1.2}",
      "#tslNamePop #tslPopList{display:block;position:relative;z-index:401;margin:0;padding:0;list-style:none;max-height:40vh;overflow-y:auto;background:#fff;border:1px solid #1d294d}",
      "#tslNamePop #tslPopList[hidden]{display:none}",
      "#tslNamePop #tslPopList li{margin:0;padding:4px 6px;cursor:pointer;color:#1a2750}",
      "#tslNamePop #tslPopList li:hover{background:#e9eefb}",
      "#tslNamePop .tsl-pop-hit,#tslNamePop .tsl-pop-sailor{display:inline-flex;align-items:center;gap:6px;white-space:nowrap}",
      "#tslNamePop .tsl-pop-sep{margin:0 2px}",
      "#tslNamePop #tslPopMsg{display:block;color:#1a2750;margin:0}",
      "#tslNamePop.tsl-pop--wide{max-width:42em}",
      "#tslNamePop .tsl-pop-split{display:flex;align-items:flex-start;gap:8px}",
      "#tslNamePop .tsl-pop-split-left{flex:1 1 12em;min-width:0;display:flex;flex-direction:column;gap:6px}",
      "#tslNamePop.tsl-pop--wide #tslPopList{flex:1 1 14em;min-width:10em;max-height:40vh;position:relative}",
      "#tslNamePop #tslPopTeamName{font-size:16px!important;line-height:1.25!important;min-width:8em;flex:1 1 12em;max-width:100%}",
      "#tslNamePop .tsl-pop-toggles{display:flex;flex-wrap:wrap;align-items:center;gap:6px}",
      "#tslNamePop .tsl-role-btn.tsl-role-on{text-decoration:underline}",
      "#tslNamePop #tslPopSave,#tslNamePop #tslPopTeamGo,#tslNamePop #tslPopDone{padding:2px 8px;min-height:0;line-height:1.2}",
      "#macTslTeamsCard .tsl-new-team-hit{cursor:pointer;display:inline-flex;flex-direction:row;flex-wrap:nowrap;align-items:center;gap:6px;white-space:nowrap;border:none;background:none;padding:0;margin:0;color:#1a2750;font:inherit;font-weight:bold}",
      "#macTslTeamsCard .tsl-new-team-card .club-race-step-add{display:inline-flex;flex:0 0 auto}",
      "#macTslTeamsCard .tsl-new-team-card .tsl-sailor-name{cursor:pointer}",
      ".regatta-page--super-admin-edit #macTslTeamsCard .tsl-team-edit-hit{cursor:pointer;border:none;background:none;padding:0;margin:0;color:#1a2750;font:inherit}",
      "#tslNamePop.tsl-pop--team{max-width:42em}",
      "#tslNamePop #tslPopRemove{color:#c62828;padding:2px 8px;min-height:0;line-height:1.2}",
      "#tslNamePop .tsl-pop-roster{max-width:100%;overflow:auto}",
      "#macTslTeamsCard .tsl-role-btn[disabled]{cursor:default;text-decoration:none}",
      "#macTslTeamsCard .tsl-role-on{text-decoration:underline}",
      "#macTslTeamsCard #tslSlotPick{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin:8px 0 0;padding:8px;border:2px solid #1a2750;border-radius:8px;background:#fff;max-width:100%;box-sizing:border-box}",
      "#macTslTeamsCard #tslSlotPick[hidden]{display:none}",
      "#macTslTeamsCard #tslPickName{min-width:12em;max-width:18em}",
      "#macTslTeamsCard #tslPickClub{max-width:12em}",
      "@media (max-width:900px){#macTslTeamsCard .tsl-team-cards,#macTslFlightsCard .tsl-flight-cards{grid-template-columns:1fr}#macTslTeamsCard,#macTslFlightsCard{padding:4px}#macTslTeamsCard .tsl-team-card,#macTslFlightsCard .tsl-flight-card{padding:4px}#macTslTeamsCard .tsl-move{width:14px;height:14px;margin:0 2px 0 0}}",
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
      "#macTslAdmin,#macTslAdmin *,#macTslSchedule,#macTslSchedule *,#macTslMatches,#macTslMatches *,#macTslTeamsCard,#macTslTeamsCard *,#macTslFlightsCard,#macTslFlightsCard *{",
      "font-size:" + tdCs.fontSize + "!important;",
      "line-height:" + tdCs.lineHeight + "!important;",
      "font-family:" + tdCs.fontFamily + "!important;",
      "}",
      "#macTslAdmin th,#macTslAdmin td,#macTslSchedule th,#macTslSchedule td,#macTslMatches th,#macTslMatches td,#macTslFlightsCard th,#macTslFlightsCard td{",
      "padding:" + tdCs.padding + "!important;",
      "}",
      "#macTslAdmin th,#macTslSchedule th,#macTslMatches th,#macTslFlightsCard th{font-weight:" + thCs.fontWeight + "!important;}"
    ].join("");
  }

  function clubCode(team) {
    return (team && (team.club_abbrev || team.club_code)) || "";
  }
  function teamFullName(team) {
    return String((team && team.team_name) || "").trim();
  }
  function teamHead(team) {
    var code = clubCode(team);
    var full = teamFullName(team) || code;
    var inner = logoImg(team && team.club_logo, code) +
      '<span class="tsl-team-code">' + esc(code) + "</span>" +
      '<span class="tsl-team-dot" aria-hidden="true">·</span>' +
      '<span class="tsl-team-full">' + esc(full) + "</span>";
    if (isSaEdit() && team && team.team_id) {
      return '<button type="button" class="rs-club-with-logo tsl-team-head tsl-team-edit-hit" data-team-id="' +
        esc(team.team_id) + '">' + inner + "</button>";
    }
    return '<span class="rs-club-with-logo tsl-team-head">' + inner + "</span>";
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

  function consistentName(s) {
    if (!s) return "";
    var first = String(s.first_name || "").trim();
    var last = String(s.last_name || "").trim();
    var name = String(s.name || "").trim();
    if (!first && name) {
      if (name.indexOf(",") !== -1) {
        var comma = name.split(",");
        first = String(comma[1] || "").trim();
        last = String(comma[0] || "").trim();
      } else {
        var bits = name.split(/\s+/).filter(Boolean);
        first = bits[0] || "";
        last = bits.length > 1 ? bits[bits.length - 1] : "";
      }
    }
    first = (first.split(/\s+/)[0] || "").trim();
    last = (last.split(/\s+/).pop() || last).trim();
    return (first + " " + last).trim();
  }

  function sailorName(s) {
    return consistentName(s) || "—";
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
    root.innerHTML = "";
    root.hidden = true;
  }

  function teamById(id) {
    return state.teams.filter(function (t) { return Number(t.team_id) === Number(id); })[0];
  }
  function teamByClub(code) {
    var want = String(code || "");
    if (!want) return null;
    return (state.teams || []).filter(function (t) { return clubCode(t) === want; })[0] || null;
  }
  function emptyPerson() {
    return { name: "", sas_id: "", sex: "" };
  }
  function slotEmpty(person) {
    return !(person && (person.sas_id || person.name));
  }
  function firstOpenSlotSameRole(team, preferBoat, role) {
    if (!team || !role) return null;
    if (roleFilled(team, role) >= 3) return null;
    var boats = rosterBoats(team);
    var i = Number(preferBoat) - 1;
    if (boats[i] && slotEmpty(boats[i][role])) return { boat: Number(preferBoat) || (i + 1), role: role };
    for (i = 0; i < boats.length; i += 1) {
      if (slotEmpty(boats[i][role])) return { boat: i + 1, role: role };
    }
    return null;
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
      openNewTeam();
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
    (state.teams || []).forEach(function (t) {
      rows.push({ code: clubCode(t), logo: t.club_logo || "" });
    });
    if (rows.length) return rows;
    var table = resultsTable();
    if (table && table.tBodies[0]) {
      Array.prototype.forEach.call(table.tBodies[0].rows, function (tr) {
        var logo = tr.querySelector(".rs-club-with-logo");
        var img = logo && logo.querySelector("img");
        var code = logo ? String(logo.textContent || "").replace(/\s+/g, " ").trim() : "";
        rows.push({ code: code, logo: img ? (img.getAttribute("src") || "") : "" });
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

  function goldRaceNos() {
    var nos = { 1: true };
    closedMatches().forEach(function (m) { nos[Number(m.match_no)] = true; });
    return Object.keys(nos).map(Number).sort(function (a, b) { return b - a; });
  }

  function matchByNo(n) {
    return (state.matches || []).filter(function (m) { return Number(m.match_no) === n; })[0] || null;
  }

  function goldRaceTableHtml() {
    var closed = closedMatches();
    var raceNos = goldRaceNos();
    var lastWin = closed.length ? Number(closed[0].winner_team_id || 0) : 0;
    var heads = '<th class="rank-col">Rank</th><th class="club-col">Club</th><th class="total-col">Total</th>';
    raceNos.forEach(function (n) {
      heads += '<th class="race-col">F' + n + "</th>";
    });
    var built = goldRaceRows().map(function (row) {
      var team = teamByCode(row.code);
      var total = 0;
      var races = [];
      raceNos.forEach(function (n) {
        var m = matchByNo(n);
        var sc = (m && String(m.status || "").toLowerCase() === "complete") ? closedRaceScore(m, team) : "";
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
      body = '<tr><td class="rank-col"></td><td class="club-col"></td><td class="total-col"></td><td class="race-col"></td></tr>';
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

  function sexLetter(s) {
    var id = String((s && s.sas_id) || "");
    if (id && sexChoice[id]) return sexChoice[id];
    var raw = String((s && (s.sex || s.gender)) || "").trim().toUpperCase();
    if (raw.charAt(0) === "M") return "M";
    if (raw.charAt(0) === "F") return "F";
    return "";
  }

  function rosterPerson(primary, fallback) {
    var a = primary || {};
    var b = fallback || {};
    var person = {
      name: consistentName(a) || consistentName(b),
      sas_id: a.sas_id || b.sas_id || "",
      sex: "",
      gender: a.gender || b.gender || ""
    };
    person.sex = sexLetter({ sas_id: person.sas_id, sex: a.sex || b.sex, gender: person.gender });
    return person;
  }

  function isGlycTeam(team) {
    var code = String(clubCode(team) || "").toUpperCase();
    var name = String(teamFullName(team) || "").toLowerCase();
    return code === "GLYC" || name.indexOf("eden") !== -1;
  }

  function rosterBoats(team) {
    var known = knownFor(team) || {};
    var boats = (team && team.boats) || [];
    var out = [];
    var n;
    for (n = 1; n <= 3; n += 1) {
      var b = boats.filter(function (x) { return Number(x.boat_no) === n; })[0] || {};
      var pairFromList = (known.sailors || []).length >= n * 2;
      out.push({
        helm: rosterPerson(b.helm, pairFromList ? known.sailors[n * 2 - 2] : (known.helms || [])[n - 1]),
        crew: rosterPerson(b.crew, pairFromList ? known.sailors[n * 2 - 1] : (known.crews || [])[n - 1])
      });
    }
    return out;
  }

  function roleFilled(team, role, exceptBoat, exceptRole) {
    var n = 0;
    rosterBoats(team).forEach(function (b, i) {
      if (exceptBoat && i + 1 === Number(exceptBoat) && exceptRole === role) return;
      if (b[role] && (b[role].sas_id || b[role].name)) n += 1;
    });
    return n;
  }

  function allowedRoles(team, boatNo, currentRole) {
    var out = [];
    if (roleFilled(team, "helm", boatNo, currentRole) < 3) out.push("helm");
    if (roleFilled(team, "crew", boatNo, currentRole) < 3) out.push("crew");
    return out;
  }

  function forcedRole(team, boatNo, currentRole) {
    var allow = allowedRoles(team, boatNo, currentRole);
    if (allow.length === 1) return allow[0];
    return currentRole || "helm";
  }

  function sexCell(person, teamId, boatNo, role) {
    var p = person || {};
    return '<td><button type="button" class="tsl-sex" data-sas="' + esc(p.sas_id || "") +
      '" data-team-id="' + esc(teamId) + '" data-boat="' + boatNo + '" data-role="' + role + '">' +
      esc(sexLetter(p) || "—") + "</button></td>";
  }

  function splitName(s) {
    s = s || {};
    var first = String(s.first_name || "").trim();
    var last = String(s.last_name || "").trim();
    var name = String(s.name || "").trim();
    if (!first && name) {
      if (name.indexOf(",") !== -1) {
        var comma = name.split(",");
        first = String(comma[1] || "").trim();
        last = String(comma[0] || "").trim();
      } else {
        var bits = name.split(/\s+/).filter(Boolean);
        first = bits[0] || "";
        last = bits.length > 1 ? bits.slice(1).join(" ") : "";
      }
    }
    first = (first.split(/\s+/)[0] || "").trim();
    last = String(last || "").trim();
    return { first: first, last: last, name: (first + " " + last).trim() || name || "—" };
  }

  function copyPerson(p) {
    p = p || {};
    var n = splitName(p);
    return {
      name: n.name,
      first_name: n.first,
      last_name: n.last,
      sas_id: p.sas_id || "",
      sex: p.sex || sexLetter(p),
      club: p.club || "",
      club_logo: p.club_logo || ""
    };
  }

  function movePad(teamId, boatNo, role) {
    return '<button type="button" class="tsl-move" data-team-id="' + esc(teamId) +
      '" data-boat="' + boatNo + '" data-role="' + role + '" aria-label="Move sailor"></button>';
  }

  function dirFromClick(e, el) {
    var box = el.getBoundingClientRect();
    var x = e.clientX - (box.left + box.width / 2);
    var y = e.clientY - (box.top + box.height / 2);
    if (Math.abs(x) >= Math.abs(y)) return x >= 0 ? "right" : "left";
    return y >= 0 ? "down" : "up";
  }

  function snapshotBoats(team) {
    return rosterBoats(team).map(function (b) {
      return { helm: copyPerson(b.helm), crew: copyPerson(b.crew) };
    });
  }

  function writeRoster(team, boats) {
    team.boats = boats.map(function (b, i) {
      return { boat_no: i + 1, helm: copyPerson(b.helm), crew: copyPerson(b.crew) };
    });
  }

  function paintAndSave(team) {
    insertTeamsCard();
    if (moveSaveTimer) clearTimeout(moveSaveTimer);
    moveSaveTimer = setTimeout(function () {
      moveSaveTimer = 0;
      saveBoatsQuiet(team, rosterBoats(team)).catch(function () {});
    }, 80);
  }

  function queueSailorMove(teamId, boat, role, dir) {
    var team = teamById(teamId);
    if (!team) return;
    var now = Date.now();
    var steps = 1;
    var fromBoat = Number(boat) || 1;
    if (
      moveBurst &&
      moveBurst.teamId === String(teamId) &&
      moveBurst.role === role &&
      moveBurst.dir === dir &&
      now - moveBurst.at < 400 &&
      (dir === "up" || dir === "down")
    ) {
      writeRoster(team, moveBurst.boats);
      fromBoat = moveBurst.boat;
      steps = 2;
    } else {
      moveBurst = {
        teamId: String(teamId || ""),
        boat: fromBoat,
        role: role,
        dir: dir,
        at: now,
        boats: snapshotBoats(team)
      };
    }
    swapSailorSlot(teamId, fromBoat, role, dir, steps);
  }

  function sailorPickCell(person, teamId, boatNo, role) {
    var p = person || {};
    var empty = slotEmpty(p);
    var label = empty ? "—" : (p.name || "—");
    return '<td class="' + (role === "crew" ? "crew-col" : "helm-col") + '">' +
      '<span class="tsl-name-wrap">' + movePad(teamId, boatNo, role) +
      '<span class="tsl-sailor-name" data-team-id="' + esc(teamId) + '" data-boat="' + boatNo +
      '" data-role="' + role + '" data-empty="' + (empty ? "1" : "0") + '">' + esc(label) + "</span></span></td>";
  }

  function sailorChip(s) {
    var n = splitName(s);
    return '<span class="rs-club-with-logo tsl-pop-sailor">' +
      logoImg((s && s.club_logo) || "", (s && s.club) || "") +
      '<span class="tsl-pop-first">' + esc(n.first || n.name) + "</span>" +
      (n.last ? ' <span class="tsl-pop-last">' + esc(n.last) + "</span>" : "") +
      "</span>";
  }

  function spaceCamel(q) {
    return String(q || "")
      .replace(/([a-z])([A-Z])/g, "$1 $2")
      .replace(/([A-Z]+)([A-Z][a-z])/g, "$1 $2")
      .replace(/\s+/g, " ")
      .trim();
  }

  function filterHits(rows, tokens) {
    if (!tokens.length) return rows;
    return (rows || []).filter(function (s) {
      var hay = [s.first_name, s.last_name, s.name, s.sas_id, s.club].join(" ").toLowerCase();
      return tokens.every(function (t) { return hay.indexOf(t) !== -1; });
    });
  }

  function normalizeSearchHit(it) {
    it = it || {};
    var first = String(it.first_name || it.first_names || "").trim();
    var last = String(it.last_name || it.surname || "").trim();
    var club = String(it.club || it.primary_club || "").trim();
    return {
      first_name: first,
      last_name: last,
      name: String(it.name || (first + " " + last).trim()),
      sas_id: String(it.sas_id || it.sa_sailing_id || ""),
      club: club,
      club_logo: String(it.club_logo || it.club_logo_url || (club ? "/api/club-logo/" + club : "")),
      sex: it.sex || ""
    };
  }

  function searchHitHtml(s) {
    s = s || {};
    var n = splitName(s);
    var name = (n.first + " " + n.last).trim() || n.name;
    return '<span class="tsl-pop-hit">' +
      '<span class="tsl-pop-name">' + esc(name) + "</span>" +
      '<span class="tsl-pop-sep"> | </span>' +
      logoImg(s.club_logo, s.club || "") +
      '<span class="tsl-pop-sep"> | </span>' +
      '<span class="tsl-pop-sas">' + esc(s.sas_id || "—") + "</span></span>";
  }

  function namePopHtml() {
    return '<div id="tslNamePop" class="card" hidden></div>';
  }

  function popInnerReplace() {
    return '<div class="tsl-pop-row">' +
      '<span id="tslPopLeft"></span>' +
      '<button type="button" class="tsl-pop-arrow" id="tslPopArrow" aria-label="Swap"></button>' +
      '<span class="tsl-ac"><input id="tslPopSearch" class="wc-result-field-input" type="text" autocomplete="off" placeholder="Name" /></span>' +
      '<span id="tslPopRight" hidden></span>' +
      '<button type="button" class="action-button" id="tslPopSave" hidden>Save</button>' +
      "</div>" +
      '<ul id="tslPopList" class="tsl-ac-list" hidden></ul>' +
      '<span class="tsl-msg" id="tslPopMsg"></span>';
  }

  function popInnerClub() {
    return '<div class="tsl-pop-split">' +
      '<div class="tsl-pop-split-left">' +
      '<span class="tsl-ac"><input id="tslPopSearch" class="wc-result-field-input" type="text" autocomplete="off" placeholder="Club" /></span>' +
      "</div>" +
      '<ul id="tslPopList" class="tsl-ac-list" hidden></ul>' +
      "</div>" +
      '<span class="tsl-msg" id="tslPopMsg"></span>';
  }

  function popInnerTeamName() {
    return '<div class="tsl-pop-row" id="tslPopClubChip"></div>' +
      '<div class="tsl-pop-row">' +
      '<input id="tslPopTeamName" class="wc-result-field-input" type="text" autocomplete="off" placeholder="Team name" />' +
      '<button type="button" class="action-button" id="tslPopTeamGo">Add team</button>' +
      "</div>" +
      '<span class="tsl-msg" id="tslPopMsg"></span>';
  }

  function popInnerAdd() {
    return '<div class="tsl-pop-split">' +
      '<div class="tsl-pop-split-left">' +
      '<span class="tsl-ac"><input id="tslPopSearch" class="wc-result-field-input" type="text" autocomplete="off" placeholder="Name" /></span>' +
      '<span id="tslPopChosen"></span>' +
      '<div class="tsl-pop-toggles">' +
      '<button type="button" class="action-button tsl-role-btn" id="tslPopSexM">M</button>' +
      '<button type="button" class="action-button tsl-role-btn" id="tslPopSexF">F</button>' +
      '<button type="button" class="action-button tsl-role-btn" id="tslPopHelm">Helm</button>' +
      '<button type="button" class="action-button tsl-role-btn" id="tslPopCrew">Crew</button>' +
      '<button type="button" class="action-button" id="tslPopSave">Save</button>' +
      '<button type="button" class="action-button" id="tslPopDone">Done</button>' +
      "</div></div>" +
      '<ul id="tslPopList" class="tsl-ac-list" hidden></ul>' +
      "</div>" +
      '<span class="tsl-msg" id="tslPopMsg"></span>';
  }

  function popInnerTeamEdit(team) {
    var code = clubCode(team);
    var full = teamFullName(team) || code;
    return '<div class="tsl-pop-row">' +
      clubHitHtml({
        club_id: team && team.club_id,
        code: code,
        name: (team && team.club_name) || full,
        logo: team && team.club_logo
      }) +
      "</div>" +
      '<div class="tsl-pop-row">' +
      '<input id="tslPopTeamName" class="wc-result-field-input" type="text" autocomplete="off" placeholder="Team name" value="' +
      esc(full) + '" />' +
      '<button type="button" class="action-button" id="tslPopSave">Save</button>' +
      "</div>" +
      '<div class="tsl-pop-roster">' + teamRosterTable(team) + "</div>" +
      '<div class="tsl-pop-row">' +
      '<button type="button" class="action-button tsl-del" id="tslPopRemove">Remove team</button>' +
      "</div>" +
      '<span class="tsl-msg" id="tslPopMsg"></span>';
  }

  function popCardBox(anchor) {
    if (anchor && anchor.closest) {
      return anchor.closest(".tsl-flight-card") ||
        anchor.closest(".tsl-team-card") ||
        anchor.closest("#macTslFlightsCard") ||
        anchor.closest("#macTslTeamsCard");
    }
    return document.getElementById("macTslFlightsCard") ||
      document.getElementById("macTslTeamsCard");
  }

  function placeNamePop(anchor) {
    var pop = ensureNamePop();
    var box = popCardBox(anchor);
    pop.style.right = "auto";
    pop.style.margin = "0";
    if (box) {
      var r = box.getBoundingClientRect();
      pop.style.left = (r.left + r.width / 2) + "px";
      pop.style.top = (r.top + r.height / 2) + "px";
    } else {
      pop.style.left = "50%";
      pop.style.top = "50%";
    }
    pop.style.transform = "translate(-50%, -50%)";
    requestAnimationFrame(function () {
      var pr = pop.getBoundingClientRect();
      var dx = 0;
      var dy = 0;
      if (pr.left < 8) dx += 8 - pr.left;
      if (pr.right > window.innerWidth - 8) dx -= pr.right - (window.innerWidth - 8);
      if (pr.top < 8) dy += 8 - pr.top;
      if (pr.bottom > window.innerHeight - 8) dy -= pr.bottom - (window.innerHeight - 8);
      if (dx || dy) {
        pop.style.transform = "translate(calc(-50% + " + dx + "px), calc(-50% + " + dy + "px))";
      }
    });
    return pop;
  }

  function showNamePop(anchor) {
    var pop = ensureNamePop();
    pop.hidden = false;
    placeNamePop(anchor);
    return pop;
  }

  function setPopBody(html, wide) {
    var pop = ensureNamePop();
    pop.innerHTML = html;
    pop.classList.toggle("tsl-pop--wide", !!wide);
    pop.classList.toggle("tsl-pop--team", pickState.mode === "teamedit");
    bindNamePopControls();
    return pop;
  }

  function bindNamePopControls() {
    if (!document._tslPopSearchDel) {
      var searchT = 0;
      document.addEventListener("input", function (e) {
        if (!e.target) return;
        if (e.target.id !== "tslPopSearch") return;
        var q = e.target.value;
        if (pickState.mode === "add" && pickState.selected) {
          pickState.selected = null;
          pickState.replacement = null;
          refreshAddPop();
        }
        clearTimeout(searchT);
        searchT = setTimeout(function () {
          if (pickState.mode === "club") runClubSearch(q);
          else runPopSearch(q);
        }, 80);
      });
      document.addEventListener("click", function (e) {
        var t = e.target && e.target.closest ? e.target.closest("[id]") : e.target;
        if (!t || !t.id) return;
        if (t.id === "tslPopArrow") { e.preventDefault(); swapNamePopSides(); }
        else if (t.id === "tslPopSave") {
          e.preventDefault();
          if (pickState.mode === "add") saveAddSailor();
          else if (pickState.mode === "teamedit") saveTeamEdit();
          else saveNameReplace();
        } else if (t.id === "tslPopTeamGo") { e.preventDefault(); createTeamFromPop(); }
        else if (t.id === "tslPopRemove") { e.preventDefault(); removeTeamFromPop(); }
        else if (t.id === "tslPopSexM") { e.preventDefault(); setPopSex("M"); }
        else if (t.id === "tslPopSexF") { e.preventDefault(); setPopSex("F"); }
        else if (t.id === "tslPopHelm") { e.preventDefault(); setPopRole("helm"); }
        else if (t.id === "tslPopCrew") { e.preventDefault(); setPopRole("crew"); }
        else if (t.id === "tslPopDone") { e.preventDefault(); closeNamePop(); }
      });
      document._tslPopSearchDel = true;
    }
    if (!document._tslNamePopDoc) {
      document.addEventListener("click", function (e) {
        var box = document.getElementById("tslNamePop");
        if (!box || box.hidden) return;
        if (box.contains(e.target)) return;
        if (e.target.closest && (
          e.target.closest(".tsl-sailor-name") ||
          e.target.closest(".tsl-new-team-hit") ||
          e.target.closest(".tsl-team-edit-hit") ||
          e.target.closest(".tsl-flight-team-hit") ||
          e.target.closest("#tslAddTeam") ||
          e.target.closest(".tsl-new-team-card")
        )) return;
        closeNamePop();
      });
      document.addEventListener("keydown", function (e) {
        if (e.key === "Escape") closeNamePop();
        if (e.key === "Enter" && pickState.mode === "teamname") {
          e.preventDefault();
          createTeamFromPop();
        }
        if (e.key === "Enter" && pickState.mode === "teamedit") {
          e.preventDefault();
          saveTeamEdit();
        }
      });
      document._tslNamePopDoc = true;
    }
  }

  function ensureNamePop() {
    var pop = document.getElementById("tslNamePop");
    if (!pop) {
      var wrap = document.createElement("div");
      wrap.innerHTML = namePopHtml();
      pop = wrap.firstChild;
      document.body.appendChild(pop);
    } else if (pop.parentNode !== document.body) {
      document.body.appendChild(pop);
    }
    bindNamePopControls();
    return pop;
  }

  function closeNamePop() {
    var pop = document.getElementById("tslNamePop");
    if (pop) pop.hidden = true;
    var list = document.getElementById("tslPopList");
    if (list) { list.hidden = true; list.innerHTML = ""; }
    pickState.replacement = null;
    pickState.selected = null;
    pickState.swapped = false;
    pickState.mode = "";
    pickState.addLoop = false;
    pickState.addStep = 1;
    pickState.clubPick = null;
    pickState.sex = "M";
    pickState.flight = "";
    pickState.bow = "";
  }

  function refreshNamePop() {
    var left = document.getElementById("tslPopLeft");
    var right = document.getElementById("tslPopRight");
    var searchWrap = document.getElementById("tslPopSearch");
    var save = document.getElementById("tslPopSave");
    var list = document.getElementById("tslPopList");
    var leftPerson = pickState.swapped ? pickState.selected : pickState.original;
    var rightPerson = pickState.swapped ? pickState.original : pickState.selected;
    if (left) left.innerHTML = sailorChip(leftPerson);
    if (pickState.selected) {
      if (right) { right.hidden = false; right.innerHTML = sailorChip(rightPerson); }
      if (searchWrap) searchWrap.parentNode.hidden = true;
      if (save) save.hidden = false;
      if (list) { list.hidden = true; list.innerHTML = ""; }
    } else {
      if (right) { right.hidden = true; right.innerHTML = ""; }
      if (searchWrap) searchWrap.parentNode.hidden = false;
      if (save) save.hidden = true;
    }
  }

  function openNameReplace(el) {
    if (!isSaEdit()) return;
    var teamId = el.getAttribute("data-team-id");
    var boat = el.getAttribute("data-boat");
    var role = el.getAttribute("data-role");
    var team = teamById(teamId);
    if (!team) return;
    var b = rosterBoats(team)[Number(boat) - 1] || {};
    pickState.teamId = String(teamId || "");
    pickState.boat = Number(boat) || 1;
    pickState.fromRole = role || "";
    pickState.role = "";
    pickState.original = copyPerson(b[role === "crew" ? "crew" : "helm"]);
    if (!pickState.original.club_logo && team.club_logo) pickState.original.club_logo = team.club_logo;
    if (!pickState.original.club && team.club_abbrev) pickState.original.club = team.club_abbrev;
    pickState.selected = null;
    pickState.replacement = null;
    pickState.swapped = false;
    pickState.mode = "replace";
    var pop = setPopBody(popInnerReplace(), false);
    if (!pop) return;
    refreshNamePop();
    var search = document.getElementById("tslPopSearch");
    if (search) search.value = "";
    showPopSearch([]);
    var msg = document.getElementById("tslPopMsg");
    if (msg) msg.textContent = "Type a name";
    showNamePop(el);
    if (search) search.focus();
  }

  function runPopSearch(raw) {
    var msg = document.getElementById("tslPopMsg");
    var q = spaceCamel(raw);
    var tokens = q.toLowerCase().split(/\s+/).filter(Boolean);
    if (q.length < 2) {
      showPopSearch([]);
      if (msg) msg.textContent = q ? "Type a name" : "Type a name";
      return;
    }
    if (msg) msg.textContent = "Searching…";
    var fetchQ = tokens[0] && tokens[0].length >= 2 ? tokens[0] : q;
    api("/api/search?q=" + encodeURIComponent(fetchQ) + "&hub=1&limit=80")
      .then(function (d) {
        var rows = (Array.isArray(d) ? d : ((d && d.sailors) || [])).map(normalizeSearchHit);
        var hits = filterHits(rows, tokens);
        showPopSearch(hits);
        if (msg) msg.textContent = hits.length ? "" : "No sailors found.";
      })
      .catch(function (e) {
        if (msg) msg.textContent = (e && e.message) || "Search failed";
        showPopSearch([]);
      });
  }

  function showPopSearch(items) {
    var list = document.getElementById("tslPopList");
    var msg = document.getElementById("tslPopMsg");
    if (!list) return;
    list.innerHTML = "";
    if (!items.length) {
      list.hidden = true;
      return;
    }
    if (msg) msg.textContent = "";
    items.forEach(function (it) {
      var li = document.createElement("li");
      li.className = "tsl-pop-hit";
      if (pickState.mode === "club") {
        li.innerHTML = clubHitHtml(it);
        li.addEventListener("mousedown", function (e) {
          e.preventDefault();
          chooseClub(it);
        });
      } else {
        li.innerHTML = searchHitHtml(it);
        li.addEventListener("mousedown", function (e) {
          e.preventDefault();
          if (!it.sas_id) {
            var msgEl = document.getElementById("tslPopMsg");
            if (msgEl) msgEl.textContent = "SAS missing — not invented";
            return;
          }
          pickState.selected = copyPerson(normalizeSearchHit(it));
          pickState.replacement = pickState.selected;
          pickState.swapped = false;
          if (sexLetter(pickState.selected)) pickState.sex = sexLetter(pickState.selected);
          if (pickState.mode === "add") refreshAddPop();
          else refreshNamePop();
        });
      }
      list.appendChild(li);
    });
    list.hidden = false;
  }

  function swapNamePopSides() {
    if (!pickState.selected) return;
    pickState.swapped = !pickState.swapped;
    refreshNamePop();
  }

  function saveNameReplace() {
    var incoming = pickState.selected || pickState.replacement;
    var msg = document.getElementById("tslPopMsg");
    if (!incoming || !incoming.sas_id) {
      if (msg) msg.textContent = "SAS missing — not invented";
      return;
    }
    var team = teamById(pickState.teamId);
    if (!team) return;
    var boats = rosterBoats(team);
    var idx = Number(pickState.boat) - 1;
    var role = pickState.fromRole === "crew" ? "crew" : "helm";
    if (!boats[idx]) return;
    boats[idx][role] = copyPerson(incoming);
    writeRoster(team, boats);
    closeNamePop();
    paintAndSave(team);
  }

  function normalizeClub(it) {
    it = it || {};
    var code = String(it.code || it.club_abbrev || "").trim();
    var name = String(it.name || it.club_name || it.club_fullname || "").trim();
    return {
      club_id: it.club_id ? Number(it.club_id) : 0,
      code: code,
      name: name,
      logo: String(it.logo || it.club_logo || (code ? "/api/club-logo/" + code : ""))
    };
  }

  function clubHitHtml(c) {
    c = normalizeClub(c);
    return '<span class="tsl-pop-hit">' +
      logoImg(c.logo, c.code) +
      '<span class="tsl-pop-sep"> | </span>' +
      '<span class="tsl-pop-code">' + esc(c.code || "—") + "</span>" +
      '<span class="tsl-pop-sep"> | </span>' +
      '<span class="tsl-pop-club-name">' + esc(c.name || c.code || "—") + "</span></span>";
  }

  function filterClubHits(rows, tokens) {
    if (!tokens.length) return rows;
    return (rows || []).filter(function (c) {
      var hay = [c.code, c.name].join(" ").toLowerCase();
      return tokens.every(function (t) { return hay.indexOf(t) !== -1; });
    });
  }

  function firstEmptyAny(team) {
    if (!team) return null;
    var boats = rosterBoats(team);
    var i;
    for (i = 0; i < boats.length; i += 1) {
      if (slotEmpty(boats[i].helm)) return { boat: i + 1, role: "helm" };
      if (slotEmpty(boats[i].crew)) return { boat: i + 1, role: "crew" };
    }
    return null;
  }

  function sailorOnTeam(team, sasId) {
    if (!team || !sasId) return false;
    var want = String(sasId);
    var found = false;
    rosterBoats(team).forEach(function (b) {
      if (b.helm && String(b.helm.sas_id || "") === want) found = true;
      if (b.crew && String(b.crew.sas_id || "") === want) found = true;
    });
    return found;
  }

  function newTeamCardHtml() {
    if (!isSaEdit()) return "";
    var dummy = { team_id: "", boats: [{ boat_no: 1 }, { boat_no: 2 }, { boat_no: 3 }] };
    return '<div class="card tsl-team-card tsl-new-team-card" data-team-id="">' +
      '<button type="button" class="tsl-new-team-hit" id="tslNewTeamHead">' +
      '<span class="club-race-step-add" id="tslNewTeam" aria-hidden="true">+</span>' +
      '<span class="tsl-team-full">New Team</span></button>' +
      teamRosterTable(dummy) +
      "</div>";
  }

  function openNewTeam() {
    if (!isSaEdit()) return;
    pickState.mode = "club";
    pickState.clubPick = null;
    pickState.selected = null;
    pickState.replacement = null;
    pickState.addLoop = true;
    pickState.addStep = 1;
    pickState.teamId = "";
    pickState.boat = 1;
    pickState.role = "helm";
    pickState.sex = "M";
    var pop = setPopBody(popInnerClub(), true);
    var search = document.getElementById("tslPopSearch");
    if (search) search.value = "";
    var msg = document.getElementById("tslPopMsg");
    if (msg) msg.textContent = "Type a club";
    showPopSearch([]);
    showNamePop(document.getElementById("tslNewTeamHead") || document.getElementById("macTslTeamsCard"));
    if (search) search.focus();
    runClubSearch("");
  }

  function runClubSearch(raw) {
    var msg = document.getElementById("tslPopMsg");
    var q = spaceCamel(raw);
    var tokens = q.toLowerCase().split(/\s+/).filter(Boolean);
    if (msg) msg.textContent = "Searching…";
    function paint(d) {
      var rows = ((d && d.clubs) || (Array.isArray(d) ? d : [])).map(normalizeClub);
      var hits = filterClubHits(rows, tokens);
      showPopSearch(hits);
      if (msg) msg.textContent = hits.length ? "" : (q ? "No clubs found." : "Type a club");
    }
    api("/api/tsl/" + encodeURIComponent(RID) + "/clubs-search?q=" + encodeURIComponent(q) + "&limit=40")
      .then(paint)
      .catch(function (e) {
        return api("/api/super-admin/clubs-search?q=" + encodeURIComponent(q) + "&limit=40")
          .then(paint)
          .catch(function (e2) {
            if (msg) msg.textContent = (e2 && e2.message) || (e && e.message) || "Search failed";
            showPopSearch([]);
          });
      });
  }

  function chooseClub(it) {
    var club = normalizeClub(it);
    if (!club.club_id) {
      var msg = document.getElementById("tslPopMsg");
      if (msg) msg.textContent = "Select a club from the list.";
      return;
    }
    pickState.clubPick = club;
    pickState.mode = "teamname";
    var pop = setPopBody(popInnerTeamName(), false);
    var chip = document.getElementById("tslPopClubChip");
    if (chip) chip.innerHTML = clubHitHtml(club);
    var inp = document.getElementById("tslPopTeamName");
    if (inp) {
      inp.value = club.name || club.code || "";
      inp.focus();
      inp.select();
    }
    var note = document.getElementById("tslPopMsg");
    if (note) {
      note.textContent = teamByClub(club.code)
        ? (club.code + " already has a team — enter a different team name.")
        : "Enter the team name, then Add team.";
    }
    showNamePop(document.getElementById("macTslTeamsCard"));
  }

  function createTeamFromPop() {
    var club = pickState.clubPick;
    var inp = document.getElementById("tslPopTeamName");
    var msg = document.getElementById("tslPopMsg");
    var name = inp ? String(inp.value || "").trim() : "";
    if (!club || !club.club_id) {
      if (msg) msg.textContent = "Select a club from the list.";
      return;
    }
    if (!name) {
      if (msg) msg.textContent = "Enter a team name.";
      return;
    }
    var abbrev = club.code || name;
    if (teamByClub(club.code)) abbrev = name;
    if (msg) msg.textContent = "Saving…";
    api("/api/tsl/" + encodeURIComponent(RID) + "/teams", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        club_id: club.club_id,
        team_name: name,
        team_abbrev: abbrev,
        boats: []
      })
    }).then(function (d) {
      return loadState().then(function () {
        var tid = d && d.team && d.team.team_id;
        var team = (tid && teamById(tid)) ||
          (state.teams || []).filter(function (t) { return String(t.team_name || "") === name; })[0] ||
          (d && d.team) ||
          null;
        if (!team) {
          if (msg) msg.textContent = "Team saved.";
          closeNamePop();
          return;
        }
        openAddSailorLoop(team);
      });
    }).catch(function (e) {
      if (msg) msg.textContent = (e && e.message) || "Save failed";
    });
  }

  function setPopSex(letter) {
    pickState.sex = letter === "F" ? "F" : "M";
    refreshAddPop();
  }

  function setPopRole(role) {
    var team = teamById(pickState.teamId);
    var allow = team ? allowedRoles(team, pickState.boat, pickState.role || "") : ["helm", "crew"];
    if (allow.indexOf(role) < 0) {
      var msg = document.getElementById("tslPopMsg");
      if (msg) msg.textContent = role === "helm" ? "No helm left — must be crew" : "No crew left — must be helm";
      return;
    }
    pickState.role = role === "crew" ? "crew" : "helm";
    refreshAddPop();
  }

  function refreshAddPop() {
    var chosen = document.getElementById("tslPopChosen");
    var search = document.getElementById("tslPopSearch");
    var list = document.getElementById("tslPopList");
    var save = document.getElementById("tslPopSave");
    var helmBtn = document.getElementById("tslPopHelm");
    var crewBtn = document.getElementById("tslPopCrew");
    var mBtn = document.getElementById("tslPopSexM");
    var fBtn = document.getElementById("tslPopSexF");
    var msg = document.getElementById("tslPopMsg");
    var team = teamById(pickState.teamId);
    var allow = team ? allowedRoles(team, pickState.boat, pickState.role || "") : ["helm", "crew"];
    if (chosen) chosen.innerHTML = pickState.selected ? sailorChip(pickState.selected) : "";
    if (search && search.parentNode) search.parentNode.hidden = false;
    if (save) save.hidden = !pickState.selected;
    if (list && pickState.selected) { list.hidden = true; list.innerHTML = ""; }
    if (helmBtn) {
      helmBtn.disabled = allow.indexOf("helm") < 0;
      helmBtn.classList.toggle("tsl-role-on", pickState.role === "helm");
    }
    if (crewBtn) {
      crewBtn.disabled = allow.indexOf("crew") < 0;
      crewBtn.classList.toggle("tsl-role-on", pickState.role === "crew");
    }
    if (mBtn) mBtn.classList.toggle("tsl-role-on", pickState.sex === "M");
    if (fBtn) fBtn.classList.toggle("tsl-role-on", pickState.sex === "F");
    if (msg) {
      if (allow.length === 1) {
        msg.textContent = allow[0] === "helm" ? "No crew left — must be helm" : "No helm left — must be crew";
      } else if (pickState.addLoop) {
        msg.textContent = "Sailor " + (pickState.addStep || 1) + " of 6 — type a name";
      } else {
        msg.textContent = pickState.selected ? "" : "Type a name";
      }
    }
  }

  function openAddSailorLoop(team) {
    if (!team) return;
    pickState.mode = "add";
    pickState.addLoop = true;
    pickState.addStep = pickState.addStep || 1;
    pickState.teamId = String(team.team_id || "");
    var slot = firstEmptyAny(team);
    pickState.boat = slot ? slot.boat : 1;
    pickState.role = slot ? slot.role : "helm";
    pickState.fromRole = pickState.role;
    pickState.selected = null;
    pickState.replacement = null;
    if (!pickState.sex) pickState.sex = "M";
    var pop = setPopBody(popInnerAdd(), true);
    var search = document.getElementById("tslPopSearch");
    if (search) search.value = "";
    showPopSearch([]);
    refreshAddPop();
    showNamePop(document.getElementById("macTslTeamsCard"));
    if (search) search.focus();
  }

  function openAddSailor(el) {
    if (!isSaEdit()) return;
    var teamId = el.getAttribute("data-team-id");
    var boat = el.getAttribute("data-boat");
    var role = el.getAttribute("data-role");
    var team = teamById(teamId);
    if (!team) return;
    pickState.mode = "add";
    pickState.addLoop = false;
    pickState.addStep = 1;
    pickState.teamId = String(teamId || "");
    pickState.boat = Number(boat) || 1;
    pickState.role = role === "crew" ? "crew" : "helm";
    pickState.fromRole = pickState.role;
    pickState.selected = null;
    pickState.replacement = null;
    pickState.sex = "M";
    var pop = setPopBody(popInnerAdd(), true);
    var search = document.getElementById("tslPopSearch");
    if (search) search.value = "";
    showPopSearch([]);
    refreshAddPop();
    showNamePop(el);
    if (search) search.focus();
  }

  function saveAddSailor() {
    var incoming = pickState.selected || pickState.replacement;
    var msg = document.getElementById("tslPopMsg");
    if (!incoming || !incoming.sas_id) {
      if (msg) msg.textContent = "SAS missing — not invented";
      return;
    }
    var team = teamById(pickState.teamId);
    if (!team) return;
    if (sailorOnTeam(team, incoming.sas_id)) {
      if (msg) msg.textContent = "Sailor already on this team";
      return;
    }
    var role = pickState.role === "crew" ? "crew" : "helm";
    var allow = allowedRoles(team, pickState.boat, pickState.role || "");
    if (allow.indexOf(role) < 0) {
      if (msg) msg.textContent = role === "helm" ? "No helm left — must be crew" : "No crew left — must be helm";
      refreshAddPop();
      return;
    }
    var slot = firstOpenSlotSameRole(team, pickState.boat, role) || firstEmptyAny(team);
    if (!slot) {
      if (msg) msg.textContent = "No slot left";
      return;
    }
    var boats = rosterBoats(team);
    var person = copyPerson(incoming);
    person.sex = pickState.sex === "F" ? "F" : "M";
    boats[slot.boat - 1][slot.role] = person;
    writeRoster(team, boats);
    var keepLoop = pickState.addLoop;
    var nextStep = (pickState.addStep || 1) + 1;
    if (keepLoop && nextStep <= 6 && firstEmptyAny(team)) {
      pickState.addStep = nextStep;
      pickState.selected = null;
      pickState.replacement = null;
      var next = firstEmptyAny(team);
      pickState.boat = next.boat;
      pickState.role = next.role;
      pickState.fromRole = next.role;
      pickState.sex = "M";
      paintAndSave(team);
      var pop = setPopBody(popInnerAdd(), true);
      var search = document.getElementById("tslPopSearch");
      if (search) search.value = "";
      showPopSearch([]);
      refreshAddPop();
      showNamePop(document.getElementById("macTslTeamsCard"));
      if (search) search.focus();
    } else {
      closeNamePop();
      paintAndSave(team);
    }
  }

  function bindRosterClicks(root) {
    if (!root) return;
    root.querySelectorAll(".tsl-sex").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var id = btn.getAttribute("data-sas") ||
          ("slot:" + (btn.getAttribute("data-team-id") || "") + ":" + (btn.getAttribute("data-boat") || "") + ":" + (btn.getAttribute("data-role") || ""));
        var cur = String(btn.textContent || sexChoice[id] || "").trim().toUpperCase();
        var next = cur === "F" ? "M" : "F";
        if (cur !== "M" && cur !== "F") next = "M";
        sexChoice[id] = next;
        btn.textContent = next;
        saveSlotSex(btn.getAttribute("data-team-id"), btn.getAttribute("data-boat"), btn.getAttribute("data-role"), next);
      });
    });
    root.querySelectorAll(".tsl-sailor-name").forEach(function (el) {
      el.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        if (!isSaEdit()) return;
        if (!el.getAttribute("data-team-id") || el.closest(".tsl-new-team-card")) {
          openNewTeam();
          return;
        }
        if (el.getAttribute("data-empty") === "1") {
          openAddSailor(el);
          return;
        }
        openNameReplace(el);
      });
    });
    root.querySelectorAll(".tsl-move").forEach(function (btn) {
      btn.addEventListener("mousedown", function (e) { e.preventDefault(); });
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        var dir = dirFromClick(e, btn);
        queueSailorMove(btn.getAttribute("data-team-id"), btn.getAttribute("data-boat"), btn.getAttribute("data-role"), dir);
      });
    });
  }

  function openTeamEdit(teamId) {
    if (!isSaEdit()) return;
    var team = teamById(teamId);
    if (!team) return;
    pickState.mode = "teamedit";
    pickState.teamId = String(team.team_id || "");
    pickState.selected = null;
    pickState.replacement = null;
    var pop = setPopBody(popInnerTeamEdit(team), true);
    bindRosterClicks(pop);
    var msg = document.getElementById("tslPopMsg");
    if (msg) msg.textContent = "Edit team name, sailors, or Remove team.";
    showNamePop(document.getElementById("macTslTeamsCard"));
    var inp = document.getElementById("tslPopTeamName");
    if (inp) inp.focus();
  }

  function saveTeamEdit() {
    var team = teamById(pickState.teamId);
    var inp = document.getElementById("tslPopTeamName");
    var msg = document.getElementById("tslPopMsg");
    if (!team) return;
    var name = inp ? String(inp.value || "").trim() : "";
    if (!name) {
      if (msg) msg.textContent = "Enter a team name.";
      return;
    }
    var body = boatsPayload(team, rosterBoats(team));
    body.team_name = name;
    if (msg) msg.textContent = "Saving…";
    api("/api/tsl/" + encodeURIComponent(RID) + "/teams/" + encodeURIComponent(team.team_id), {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    }).then(function () {
      closeNamePop();
      return loadState();
    }).catch(function (e) {
      if (msg) msg.textContent = (e && e.message) || "Save failed";
    });
  }

  function removeTeamFromPop() {
    var team = teamById(pickState.teamId);
    var msg = document.getElementById("tslPopMsg");
    if (!team || !team.team_id) return;
    var label = teamFullName(team) || clubCode(team) || "this team";
    if (!window.confirm("Remove " + label + " from the event?")) return;
    if (msg) msg.textContent = "Removing…";
    api("/api/tsl/" + encodeURIComponent(RID) + "/teams/" + encodeURIComponent(team.team_id), { method: "DELETE" })
      .then(function () {
        closeNamePop();
        return loadState();
      })
      .catch(function (e) {
        if (msg) msg.textContent = (e && e.message) || "Remove failed";
      });
  }

  function swapSailorSlot(teamId, boat, role, dir, steps) {
    var team = teamById(teamId);
    if (!team) return;
    var boats = rosterBoats(team);
    var fromBoat = Number(boat) || 1;
    var fromIdx = fromBoat - 1;
    var fromRole = role === "crew" ? "crew" : "helm";
    var jump = Number(steps) > 1 ? 2 : 1;
    var toIdx = fromIdx;
    var toRole = fromRole;
    if (dir === "right") {
      if (fromRole !== "helm") return;
      toRole = "crew";
    } else if (dir === "left") {
      if (fromRole !== "crew") return;
      toRole = "helm";
    } else if (dir === "up") {
      toIdx = fromIdx - jump;
      if (toIdx < 0) toIdx = 0;
      if (toIdx === fromIdx) return;
    } else if (dir === "down") {
      toIdx = fromIdx + jump;
      if (toIdx > 2) toIdx = 2;
      if (toIdx === fromIdx) return;
    } else {
      return;
    }
    if (!boats[fromIdx] || !boats[toIdx]) return;
    var a = copyPerson(boats[fromIdx][fromRole]);
    var b = copyPerson(boats[toIdx][toRole]);
    if (!a.sas_id && !a.name && !b.sas_id && !b.name) return;
    boats[fromIdx][fromRole] = b;
    boats[toIdx][toRole] = a;
    writeRoster(team, boats);
    paintAndSave(team);
  }

  function eventClubOptions(selected) {
    var html = '<option value="">All clubs</option>';
    (state.teams || []).forEach(function (t) {
      var code = clubCode(t);
      var full = teamFullName(t);
      html += '<option value="' + esc(code) + '"' + (selected === code ? " selected" : "") + ">" +
        esc(code + (full && full !== code ? " · " + full : "")) + "</option>";
    });
    return html;
  }

  function clubSailorRows(code) {
    var t = (state.teams || []).filter(function (x) { return clubCode(x) === code; })[0];
    if (!t) return "";
    var rows = "";
    rosterBoats(t).forEach(function (b) {
      ["helm", "crew"].forEach(function (role) {
        var s = b[role] || {};
        if (!s.name && !s.sas_id) return;
        rows += '<tr class="tsl-pick-row" data-sas="' + esc(s.sas_id || "") + '" data-name="' + esc(s.name || "") + '">' +
          "<td>" + esc(s.name || "") + "</td><td>" + esc(s.sas_id || "") + "</td><td>" + esc(role === "crew" ? "Crew" : "Helm") + "</td></tr>";
      });
    });
    return rows;
  }

  function pickPanelHtml() {
    return '<div id="tslSlotPick" class="card" hidden>' +
      '<span class="tsl-ac"><input id="tslPickName" class="wc-result-field-input" type="text" autocomplete="off" placeholder="Name" /></span>' +
      '<button type="button" class="action-button tsl-role-btn" id="tslPickHelm">Helm</button>' +
      '<button type="button" class="action-button tsl-role-btn" id="tslPickCrew">Crew</button>' +
      '<select id="tslPickClub" class="wc-result-field-input"></select>' +
      '<button type="button" class="action-button" id="tslPickDel">Delete</button>' +
      '<button type="button" class="action-button" id="tslPickClose">Close</button>' +
      '<span class="tsl-msg" id="tslPickMsg"></span></div>';
  }

  function currentPickPerson() {
    var team = teamById(pickState.teamId);
    if (!team) return {};
    var b = rosterBoats(team)[Number(pickState.boat) - 1] || {};
    return b[pickState.role] || {};
  }

  function refreshPickRoleButtons() {
    var team = teamById(pickState.teamId);
    var allow = team ? allowedRoles(team, pickState.boat, pickState.role || "") : ["helm", "crew"];
    var helmBtn = document.getElementById("tslPickHelm");
    var crewBtn = document.getElementById("tslPickCrew");
    var msg = document.getElementById("tslPickMsg");
    if (helmBtn) {
      helmBtn.disabled = allow.indexOf("helm") < 0;
      helmBtn.classList.toggle("tsl-role-on", pickState.role === "helm");
    }
    if (crewBtn) {
      crewBtn.disabled = allow.indexOf("crew") < 0;
      crewBtn.classList.toggle("tsl-role-on", pickState.role === "crew");
    }
    if (msg && allow.length === 1) {
      msg.textContent = allow[0] === "helm" ? "No crew left — must be helm" : "No helm left — must be crew";
    }
  }

  function openSailorPick(teamId, boat, role) {
    pickState = { teamId: String(teamId || ""), boat: Number(boat) || 1, role: "", fromRole: role || "", sailor: null, club: "" };
    var team = teamById(pickState.teamId);
    var box = document.getElementById("tslSlotPick");
    if (!box) return;
    box.hidden = false;
    var p = {};
    if (team && role) {
      var b = rosterBoats(team)[Number(pickState.boat) - 1] || {};
      p = b[role] || {};
      if (p.sas_id || p.name) pickState.sailor = { name: p.name || "", sas_id: p.sas_id || "" };
    }
    var nameEl = document.getElementById("tslPickName");
    var clubEl = document.getElementById("tslPickClub");
    if (nameEl) nameEl.value = p.name || "";
    pickState.club = clubCode(team) || "";
    if (clubEl) clubEl.innerHTML = eventClubOptions(pickState.club);
    var msg = document.getElementById("tslPickMsg");
    if (msg) msg.textContent = "";
    refreshPickRoleButtons();
  }

  function boatsPayload(team, boats) {
    return {
      team_id: team.team_id,
      club_id: team.club_id,
      team_name: team.team_name,
      boats: boats.map(function (b, i) {
        return {
          boat_no: i + 1,
          helm_sas_id: (b.helm && b.helm.sas_id) || "",
          crew_sas_id: (b.crew && b.crew.sas_id) || "",
          helm_sex: (b.helm && b.helm.sex) || "",
          crew_sex: (b.crew && b.crew.sex) || ""
        };
      })
    };
  }

  function saveBoatsQuiet(team, boats) {
    return api("/api/tsl/" + encodeURIComponent(RID) + "/teams/" + encodeURIComponent(team.team_id), {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(boatsPayload(team, boats))
    });
  }

  function saveBoats(team, boats, msg) {
    return saveBoatsQuiet(team, boats).then(function () { return loadState(); }).catch(function (e) {
      if (msg) msg.textContent = e.message || "Save failed";
    });
  }

  function saveSlotSex(teamId, boat, role, sex) {
    var letter = sex === "F" ? "F" : "M";
    var team = teamById(teamId);
    if (team) {
      var boats = rosterBoats(team);
      var idx = Number(boat) - 1;
      if (boats[idx]) {
        if (!boats[idx][role]) boats[idx][role] = emptyPerson();
        boats[idx][role].sex = letter;
      }
    }
    return api("/api/tsl/" + encodeURIComponent(RID) + "/teams/" + encodeURIComponent(teamId) + "/slot-sex", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ boat: Number(boat) || 1, role: role, sex: letter })
    }).then(function () { return loadState(); }).catch(function (e) {
      var btn = document.querySelector(
        '.tsl-sex[data-team-id="' + teamId + '"][data-boat="' + boat + '"][data-role="' + role + '"]'
      );
      if (btn) btn.title = e.message || "Save failed";
    });
  }

  function applyPickedSailor(sailor, role) {
    var team = teamById(pickState.teamId);
    var msg = document.getElementById("tslPickMsg");
    if (!team) return;
    if (!sailor || !sailor.sas_id) {
      if (msg) msg.textContent = "SAS missing — not invented";
      return;
    }
    var allow = allowedRoles(team, pickState.boat, role);
    if (allow.indexOf(role) < 0) {
      if (msg) msg.textContent = role === "helm" ? "No helm left — must be crew" : "No crew left — must be helm";
      refreshPickRoleButtons();
      return;
    }
    pickState.role = role;
    var boats = rosterBoats(team);
    var idx = Number(pickState.boat) - 1;
    if (!boats[idx]) return;
    var other = role === "helm" ? "crew" : "helm";
    boats[idx][role] = { name: sailor.name || "", sas_id: String(sailor.sas_id), sex: sexLetter(sailor) };
    if (boats[idx][other] && String(boats[idx][other].sas_id || "") === String(sailor.sas_id)) {
      boats[idx][other] = { name: "", sas_id: "", sex: "" };
    }
    saveBoats(team, boats, msg);
  }

  function chooseRole(role) {
    var sailor = pickState.sailor;
    if (sailor && sailor.sas_id) {
      applyPickedSailor(sailor, role);
      return;
    }
    moveSailorRole(role);
  }

  function pickedSailorOrSlot() {
    if (pickState.sailor && pickState.sailor.sas_id) return pickState.sailor;
    var team = teamById(pickState.teamId);
    if (!team) return null;
    var fromRole = pickState.fromRole || pickState.role;
    var b = rosterBoats(team)[Number(pickState.boat) - 1] || {};
    var p = (fromRole && b[fromRole]) || {};
    if (p.sas_id) return { name: p.name || "", sas_id: p.sas_id, sex: p.sex || sexLetter(p) };
    return null;
  }

  function changePickClubOnly() {
    var clubEl = document.getElementById("tslPickClub");
    var msg = document.getElementById("tslPickMsg");
    var newCode = clubEl ? String(clubEl.value || "") : "";
    pickState.club = newCode;
    if (msg) msg.textContent = "";
    var dest = teamByClub(newCode);
    var src = teamById(pickState.teamId);
    if (!dest || !src || Number(dest.team_id) === Number(src.team_id)) return;
    var sailor = pickedSailorOrSlot();
    if (!sailor || !sailor.sas_id) return;
    var preferRole = pickState.fromRole || pickState.role || "";
    var slot = firstOpenSlotSameRole(dest, pickState.boat, preferRole);
    if (!slot) {
      if (msg) msg.textContent = "No slot left at " + (clubCode(dest) || "that club");
      return;
    }
    var srcBoats = rosterBoats(src);
    srcBoats.forEach(function (b) {
      ["helm", "crew"].forEach(function (role) {
        if (b[role] && String(b[role].sas_id || "") === String(sailor.sas_id)) b[role] = emptyPerson();
      });
    });
    var destBoats = rosterBoats(dest);
    destBoats[slot.boat - 1][slot.role] = {
      name: sailor.name || "",
      sas_id: String(sailor.sas_id),
      sex: sailor.sex || sexLetter(sailor)
    };
    pickState.teamId = String(dest.team_id);
    pickState.boat = slot.boat;
    pickState.fromRole = slot.role;
    saveBoatsQuiet(src, srcBoats).then(function () {
      return saveBoatsQuiet(dest, destBoats);
    }).then(function () {
      return loadState();
    }).catch(function (e) {
      if (msg) msg.textContent = e.message || "Save failed";
    });
  }

  function deletePickedSailor() {
    var team = teamById(pickState.teamId);
    var msg = document.getElementById("tslPickMsg");
    if (!team) return;
    var boats = rosterBoats(team);
    var idx = Number(pickState.boat) - 1;
    if (!boats[idx]) return;
    boats[idx][pickState.role || pickState.fromRole || "helm"] = { name: "", sas_id: "", sex: "" };
    saveBoats(team, boats, msg);
  }

  function moveSailorRole(nextRole) {
    var team = teamById(pickState.teamId);
    var msg = document.getElementById("tslPickMsg");
    if (!team) return;
    var allow = allowedRoles(team, pickState.boat, pickState.role);
    if (allow.indexOf(nextRole) < 0) {
      if (msg) msg.textContent = nextRole === "helm" ? "No helm left — must be crew" : "No crew left — must be helm";
      refreshPickRoleButtons();
      return;
    }
    var boats = rosterBoats(team);
    var idx = Number(pickState.boat) - 1;
    var b = boats[idx];
    if (!b || nextRole === pickState.role) {
      refreshPickRoleButtons();
      return;
    }
    var from = pickState.role;
    var person = b[from];
    var other = b[nextRole];
    b[nextRole] = person;
    b[from] = other && (other.sas_id || other.name) ? other : { name: "", sas_id: "", sex: "" };
    pickState.role = nextRole;
    saveBoats(team, boats, msg);
  }

  function teamRosterTable(team) {
    var tid = (team && team.team_id) || "";
    var rows = "";
    rosterBoats(team).forEach(function (b, i) {
      var n = i + 1;
      var h = b.helm || {};
      var c = b.crew || {};
      rows += "<tr>" +
        "<td>" + n + "</td>" +
        sexCell(h, tid, n, "helm") +
        sailorPickCell(h, tid, n, "helm") +
        "<td>" + esc(h.sas_id || "") + "</td>" +
        sexCell(c, tid, n, "crew") +
        sailorPickCell(c, tid, n, "crew") +
        "<td>" + esc(c.sas_id || "") + "</td></tr>";
    });
    return '<div class="table-wrapper"><table class="fleet-results-table">' +
      "<thead><tr><th>No</th><th>S</th><th class=\"helm-col\">Helm</th><th>SAS ID</th>" +
      "<th>S</th><th class=\"crew-col\">Crew</th><th>SAS ID</th></tr></thead>" +
      "<tbody>" + rows + "</tbody></table></div>";
  }

  function teamCardsHtml() {
    var teams = (state.teams || []).slice().sort(function (a, b) {
      return String(clubCode(a) || a.team_name || "").localeCompare(
        String(clubCode(b) || b.team_name || ""),
        undefined,
        { sensitivity: "base" }
      );
    });
    var inner = "";
    teams.forEach(function (t) {
      inner += '<div class="card tsl-team-card" data-team-id="' + esc(t.team_id || "") + '">' +
        teamHead(t) +
        teamRosterTable(t) + "</div>";
    });
    inner += newTeamCardHtml();
    return '<div class="fleet-title-row">Teams</div><div class="tsl-team-cards">' + inner + "</div>" + pickPanelHtml();
  }

  function wireTeamCardClicks(card) {
    if (!card) return;
    bindRosterClicks(card);
    card.querySelectorAll(".tsl-team-edit-hit").forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        openTeamEdit(btn.getAttribute("data-team-id"));
      });
    });
    card.querySelectorAll(".tsl-new-team-hit").forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        openNewTeam();
      });
    });
    bindNamePopControls();
    var nameInp = document.getElementById("tslPickName");
    if (nameInp) {
      bindTypeahead(nameInp, "sailor", function (q) {
        var url = "/api/tsl/" + encodeURIComponent(RID) + "/sailors-search?q=" + encodeURIComponent(q) + "&limit=35";
        if (pickState.club) url += "&club=" + encodeURIComponent(pickState.club);
        return url;
      }, function (it) {
        nameInp.value = it.name || "";
        pickState.sailor = { name: it.name || "", sas_id: it.sas_id || "", club: it.club || "" };
        var msg = document.getElementById("tslPickMsg");
        if (msg) msg.textContent = it.sas_id ? "" : "SAS missing — not invented";
      });
    }
    var clubEl = document.getElementById("tslPickClub");
    if (clubEl) clubEl.addEventListener("change", changePickClubOnly);
    var helmBtn = document.getElementById("tslPickHelm");
    if (helmBtn) helmBtn.addEventListener("click", function () { chooseRole("helm"); });
    var crewBtn = document.getElementById("tslPickCrew");
    if (crewBtn) crewBtn.addEventListener("click", function () { chooseRole("crew"); });
    var delBtn = document.getElementById("tslPickDel");
    if (delBtn) delBtn.addEventListener("click", deletePickedSailor);
    var closeBtn = document.getElementById("tslPickClose");
    if (closeBtn) closeBtn.addEventListener("click", function () {
      var box = document.getElementById("tslSlotPick");
      if (box) box.hidden = true;
    });
  }

  function flightMatch(n) {
    var want = String(n);
    return (state.matches || []).filter(function (x) {
      return String(x.flight || "") === want ||
        String(x.round_label || "").toLowerCase().indexOf("flight " + want) >= 0 ||
        Number(x.match_no) === Number(n);
    })[0] || null;
  }

  function emptyFlightSheet() {
    var lines = function () {
      var o = {};
      var b;
      for (b = 1; b <= 6; b += 1) o[String(b)] = { colour: "", team_id: null, rank: null };
      return o;
    };
    return { boats_per_team: { "1": 3, "2": 3 }, "1": lines(), "2": lines() };
  }

  function flightSheet() {
    var src = (state.settings || {}).flight_sheet;
    return src || emptyFlightSheet();
  }

  function flightCell(fl, bow) {
    var sheet = flightSheet();
    return ((sheet[String(fl)] || {})[String(bow)]) || { colour: "", team_id: null, rank: null };
  }

  function allocatedBows(fl) {
    var n = 0;
    var bow;
    for (bow = 1; bow <= 6; bow += 1) {
      if (flightCell(fl, bow).team_id) n += 1;
    }
    return n;
  }

  function colourCap(fl) {
    var n = allocatedBows(fl);
    if (n < 2) return 3;
    return Math.min(3, Math.ceil(n / 2));
  }

  function flightColour(fl, bow) {
    return String(flightCell(fl, bow).colour || "");
  }

  function colourCount(fl, colour, exceptBow) {
    var n = 0;
    var bow;
    for (bow = 1; bow <= 6; bow += 1) {
      if (exceptBow && Number(bow) === Number(exceptBow)) continue;
      if (flightColour(fl, bow) === colour) n += 1;
    }
    return n;
  }

  function teamCount(fl, teamId, exceptBow) {
    var n = 0;
    var bow;
    if (!teamId) return 0;
    for (bow = 1; bow <= 6; bow += 1) {
      if (exceptBow && Number(bow) === Number(exceptBow)) continue;
      if (Number(flightCell(fl, bow).team_id) === Number(teamId)) n += 1;
    }
    return n;
  }

  function nextFlightColour(fl, bow) {
    var cur = flightColour(fl, bow);
    var order = ["", "Blue", "Green"];
    var i = order.indexOf(cur);
    if (i < 0) i = 0;
    var k;
    for (k = 1; k <= 3; k += 1) {
      var next = order[(i + k) % 3];
      if (!next) return "";
      if (colourCount(fl, next, bow) < colourCap(fl)) return next;
    }
    return "";
  }

  function paintColourSq(btn, colour) {
    btn.classList.toggle("tsl-colour-blue", colour === "Blue");
    btn.classList.toggle("tsl-colour-green", colour === "Green");
    btn.setAttribute("aria-label", colour || "Colour");
    btn.title = colour || "";
  }

  function setFlightCellLocal(fl, bow, patch) {
    if (!state.settings) state.settings = {};
    var sheet = flightSheet();
    if (!sheet[String(fl)]) sheet[String(fl)] = {};
    var cell = Object.assign({}, flightCell(fl, bow), patch || {});
    sheet[String(fl)][String(bow)] = cell;
    state.settings.flight_sheet = sheet;
  }

  function saveFlightLine(body) {
    return api("/api/tsl/" + encodeURIComponent(RID) + "/flight-colours", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    }).then(function (d) {
      if (!state.settings) state.settings = {};
      if (d && d.flight_sheet) state.settings.flight_sheet = d.flight_sheet;
      if (d && d.flight_colours) state.settings.flight_colours = d.flight_colours;
      return d;
    });
  }

  function enteredTeams() {
    return (state.teams || []).slice().sort(function (a, b) {
      return String(clubCode(a) || a.team_name || "").localeCompare(
        String(clubCode(b) || b.team_name || ""),
        undefined,
        { sensitivity: "base" }
      );
    });
  }

  function teamListLabel(team) {
    if (!team) return "—";
    var code = clubCode(team);
    var full = teamFullName(team) || code;
    return '<span class="rs-club-with-logo tsl-team-head">' +
      logoImg(team.club_logo, code) +
      '<span class="tsl-team-code">' + esc(code) + "</span>" +
      '<span class="tsl-team-dot" aria-hidden="true">·</span>' +
      '<span class="tsl-team-full">' + esc(full) + "</span></span>";
  }

  function flightTeamCell(n, bow, team) {
    return '<span class="tsl-flight-team">' +
      '<button type="button" class="tsl-flight-team-hit" data-flight="' + n + '" data-bow="' + bow + '">' +
      teamListLabel(team) + "</button></span>";
  }

  function popInnerFlightTeam(fl, bow) {
    return '<div class="tsl-pop-row"><span class="tsl-pop-flight-lab">Flight ' +
      esc(fl) + " · Bow " + esc(bow) + "</span></div>" +
      '<ul id="tslPopList" class="tsl-ac-list"></ul>' +
      '<span class="tsl-msg" id="tslPopMsg"></span>';
  }

  function openFlightTeamPick(btn) {
    if (!isSaEdit() || !btn) return;
    var fl = btn.getAttribute("data-flight");
    var bow = btn.getAttribute("data-bow");
    pickState.mode = "flightteam";
    pickState.flight = fl;
    pickState.bow = bow;
    setPopBody(popInnerFlightTeam(fl, bow), true);
    var list = document.getElementById("tslPopList");
    var msg = document.getElementById("tslPopMsg");
    var teams = enteredTeams();
    if (list) {
      list.innerHTML = "";
      var clear = document.createElement("li");
      clear.setAttribute("data-team-id", "");
      clear.textContent = "—";
      clear.addEventListener("mousedown", function (e) {
        e.preventDefault();
        chooseFlightTeam("");
      });
      list.appendChild(clear);
      teams.forEach(function (t) {
        var li = document.createElement("li");
        li.setAttribute("data-team-id", String(t.team_id || ""));
        li.innerHTML = teamListLabel(t);
        li.addEventListener("mousedown", function (e) {
          e.preventDefault();
          chooseFlightTeam(li.getAttribute("data-team-id") || "");
        });
        list.appendChild(li);
      });
      list.hidden = false;
    }
    if (msg) msg.textContent = teams.length ? "Select a team" : "Add a team first";
    showNamePop(btn);
  }

  function chooseFlightTeam(tid) {
    var fl = pickState.flight;
    var bow = pickState.bow;
    var msg = document.getElementById("tslPopMsg");
    if (!fl || !bow) return;
    if (tid && teamCount(fl, tid, bow) >= 3) {
      if (msg) msg.textContent = "Already 3 boats for that team";
      return;
    }
    var prev = flightCell(fl, bow).team_id;
    setFlightCellLocal(fl, bow, { team_id: tid ? Number(tid) : null });
    closeNamePop();
    insertFlightsCard();
    saveFlightLine({ flight: Number(fl), bow: Number(bow), team_id: tid ? Number(tid) : "" }).catch(function (err) {
      setFlightCellLocal(fl, bow, { team_id: prev || null });
      insertFlightsCard();
      window.alert((err && err.message) || "Save failed");
    });
  }

  function flightRankCell(n, bow, rank) {
    if (!isSaEdit()) return esc(rank || "");
    return '<input class="wc-result-field-input tsl-rank" type="text" inputmode="numeric" maxlength="1" data-flight="' +
      n + '" data-bow="' + bow + '" value="' + esc(rank || "") + '" aria-label="Rank" />';
  }

  function flightRows(n) {
    var out = [];
    var bow;
    for (bow = 1; bow <= 6; bow += 1) {
      var cell = flightCell(n, bow);
      out.push({
        rank: cell.rank || "",
        bow: String(bow),
        colour: cell.colour || "",
        team: cell.team_id ? teamById(cell.team_id) : null
      });
    }
    return out;
  }

  function flightCardHtml(n) {
    var rows = "";
    flightRows(n).forEach(function (r) {
      var sqClass = "tsl-colour-sq" +
        (r.colour === "Blue" ? " tsl-colour-blue" : r.colour === "Green" ? " tsl-colour-green" : "");
      rows += "<tr>" +
        '<td class="rank-col">' + flightRankCell(n, r.bow, r.rank) + "</td>" +
        "<td><button type=\"button\" class=\"" + sqClass + "\" data-flight=\"" + n +
        "\" data-bow=\"" + esc(r.bow) + "\" aria-label=\"" + esc(r.colour || "Colour") + "\"></button></td>" +
        "<td>" + esc(r.bow) + "</td>" +
        '<td class="club-col">' + flightTeamCell(n, r.bow, r.team) + "</td></tr>";
    });
    return '<div class="card tsl-flight-card">' +
      '<div class="tsl-flight-head">Flight ' + n + "</div>" +
      '<div class="table-wrapper"><table class="fleet-results-table">' +
      "<thead><tr><th class=\"rank-col\">Rank</th><th>Colour</th><th>Bow no</th><th class=\"club-col\">Team</th></tr></thead>" +
      "<tbody>" + rows + "</tbody></table></div></div>";
  }

  function flightsCardHtml() {
    return '<div class="fleet-title-row">Flights</div>' +
      '<div class="tsl-flight-cards">' + flightCardHtml(1) + flightCardHtml(2) + "</div>";
  }

  function insertFlightsCard() {
    var gold = document.getElementById("macTslGoldSheet");
    if (!gold || !gold.parentNode) return;
    var card = document.getElementById("macTslFlightsCard");
    if (!card) {
      card = document.createElement("div");
      card.id = "macTslFlightsCard";
      card.setAttribute("class", "card");
    }
    card.innerHTML = flightsCardHtml();
    wireFlightClicks(card);
    if (gold.nextSibling !== card) gold.parentNode.insertBefore(card, gold.nextSibling);
    requestAnimationFrame(function () { fitTeamCardTables(); });
  }

  function wireFlightClicks(card) {
    if (!card) return;
    card.querySelectorAll(".tsl-colour-sq").forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        if (!isSaEdit()) return;
        var fl = btn.getAttribute("data-flight");
        var bow = btn.getAttribute("data-bow");
        var prev = flightColour(fl, bow);
        var next = nextFlightColour(fl, bow);
        if (next === prev && prev) btn.title = "No more than " + colourCap(fl) + " " + prev;
        setFlightCellLocal(fl, bow, { colour: next });
        paintColourSq(btn, next);
        saveFlightLine({ flight: Number(fl), bow: Number(bow), colour: next }).catch(function (err) {
          setFlightCellLocal(fl, bow, { colour: prev });
          paintColourSq(btn, prev);
          btn.title = (err && err.message) || "Save failed";
        });
      });
    });
    card.querySelectorAll(".tsl-flight-team-hit").forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        if (!isSaEdit()) return;
        openFlightTeamPick(btn);
      });
    });
    card.querySelectorAll(".tsl-rank").forEach(function (inp) {
      inp.addEventListener("change", function () {
        if (!isSaEdit()) return;
        var fl = inp.getAttribute("data-flight");
        var bow = inp.getAttribute("data-bow");
        var raw = String(inp.value || "").trim();
        var prev = flightCell(fl, bow).rank;
        var rank = raw === "" ? "" : Number(raw);
        if (raw !== "" && (rank < 1 || rank > 6 || !/^[1-6]$/.test(raw))) {
          inp.value = prev || "";
          inp.title = "Rank must be 1 to 6";
          return;
        }
        setFlightCellLocal(fl, bow, { rank: rank === "" ? null : rank });
        saveFlightLine({ flight: Number(fl), bow: Number(bow), rank: rank }).catch(function (err) {
          setFlightCellLocal(fl, bow, { rank: prev || null });
          inp.value = prev || "";
          inp.title = (err && err.message) || "Save failed";
        });
      });
    });
  }

  function insertTeamsCard() {
    var after = document.getElementById("macTslFlightsCard") || document.getElementById("macTslGoldSheet");
    if (!after || !after.parentNode) return;
    var card = document.getElementById("macTslTeamsCard");
    if (!card) {
      card = document.createElement("div");
      card.id = "macTslTeamsCard";
      card.setAttribute("class", "card");
    }
    card.innerHTML = teamCardsHtml();
    wireTeamCardClicks(card);
    if (after.nextSibling !== card) after.parentNode.insertBefore(card, after.nextSibling);
    requestAnimationFrame(function () { fitTeamCardTables(); });
  }

  function fitTeamCardTables() {
    var teamRoot = document.getElementById("macTslTeamsCard");
    var flightRoot = document.getElementById("macTslFlightsCard");
    var wraps = [];
    if (teamRoot) wraps = wraps.concat(Array.prototype.slice.call(teamRoot.querySelectorAll(".tsl-team-card .table-wrapper")));
    if (flightRoot) wraps = wraps.concat(Array.prototype.slice.call(flightRoot.querySelectorAll(".tsl-flight-card .table-wrapper")));
    if (!wraps.length) return;
    var boxes = [];
    var maxNeed = 0;
    var minAvail = 0;
    for (var i = 0; i < wraps.length; i += 1) {
      var wrap = wraps[i];
      var table = wrap.querySelector("table");
      if (!table) continue;
      table.style.transform = "none";
      wrap.style.height = "";
      boxes.push({ wrap: wrap, table: table });
      if (table.scrollWidth > maxNeed) maxNeed = table.scrollWidth;
      var avail = wrap.clientWidth;
      if (avail > 0 && (!minAvail || avail < minAvail)) minAvail = avail;
    }
    if (!maxNeed || !minAvail) return;
    var scale = maxNeed > minAvail ? minAvail / maxNeed : 1;
    for (var j = 0; j < boxes.length; j += 1) {
      var box = boxes[j];
      if (scale < 0.999) {
        box.table.style.transform = "scale(" + scale + ")";
        box.wrap.style.height = Math.ceil(box.table.offsetHeight * scale) + "px";
      } else {
        box.table.style.transform = "none";
        box.wrap.style.height = "";
      }
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
      var fm = lab.match(/^f(\d+)$/);
      if (rm) th.textContent = "F" + rm[1];
      if (fm) th.textContent = "F" + fm[1];
    });
    var matchNos = (state.matches || []).map(function (m) { return Number(m.match_no); });
    matchNos.forEach(function (n) {
      var label = "m" + n;
      var found = false;
      Array.prototype.forEach.call(thead.cells, function (th) {
        if (headerLabel(th) === label || headerLabel(th) === ("r" + n) || headerLabel(th) === ("f" + n)) found = true;
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
    insertFlightsCard();
    insertTeamsCard();
    renderTeams();
    renderSchedule();
    renderMatches();
    syncSheetType();
    requestAnimationFrame(function () { fitTeamCardTables(); });
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
    if (!window._tslFitBound) {
      window.addEventListener("resize", function () {
        clearTimeout(fitTeamCardTables._t);
        fitTeamCardTables._t = setTimeout(fitTeamCardTables, 50);
      });
      window._tslFitBound = true;
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
  window.__ssaMacTslAdmin = JS_VER;
})();
