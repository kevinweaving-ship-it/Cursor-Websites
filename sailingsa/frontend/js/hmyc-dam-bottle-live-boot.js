/**
 * Dam Bottle Sprints — clone Dart Nationals event URL stack.
 * Order: event header → Leader Board → Wind → Media → Live Cam → Open Fleet.
 * Public table: Rank Class Sail No Club Helm Crew Cat + R scores only.
 * PY / ET / green-tick corrected stay on club race-entry (hidden from public).
 * Does not change live api.py.
 */
(function () {
  "use strict";
  var RID = "2026-10-10-hmyc-dam-bottle-sprints";
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
      "text-align:center;width:2.2rem;}" +
      ".fleet-section[data-block-id='" + RID + ":open'] .event-result-yes{" +
      "color:#15803d;font-weight:700;font-size:1.05rem;line-height:1;}" +
      ".fleet-section[data-block-id='" + RID + ":open'] .fleet-section--r1-closed .dam-bottle-et-col," +
      ".fleet-section[data-block-id='" + RID + ":open'] .fleet-section--r1-closed .dam-bottle-corr-col{" +
      "display:none!important}";
    document.head.appendChild(css);
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
    if (!table || table.querySelector('th.race-col[data-race-key="R1"]')) return;
    var thead = table.querySelector("thead tr");
    if (!thead) return;
    var th = document.createElement("th");
    th.className = "race-col";
    th.setAttribute("data-race-key", "R1");
    th.textContent = "R1";
    var totalTh = thead.querySelector("th.total-col, th.nett-col");
    if (totalTh) thead.insertBefore(th, totalTh);
    else thead.appendChild(th);
    table.querySelectorAll("tbody tr[data-result-id]").forEach(function (tr) {
      if (tr.querySelector('td.race-col[data-race-key="R1"]')) return;
      var td = document.createElement("td");
      td.className = "race-col";
      td.setAttribute("data-race-key", "R1");
      var totalTd = tr.querySelector("td.total-col, td.nett-col");
      if (totalTd) tr.insertBefore(td, totalTd);
      else tr.appendChild(td);
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
    /* Open R1: ET + green tick sit on that race. Closed races drop both and keep R only. */
    ensureColAfter(table, "PY", "ET", "dam-bottle-et-col", "");
    var tick =
      '<span class="event-result-yes" title="Corrected" aria-label="Corrected">✓</span>';
    if (!table.querySelector("th.dam-bottle-corr-col")) {
      var etTh = null;
      table.querySelectorAll("thead th").forEach(function (th) {
        if (String(th.textContent || "").trim() === "ET") etTh = th;
      });
      if (etTh) {
        var th = document.createElement("th");
        th.className = "dam-bottle-corr-col";
        th.innerHTML = tick;
        insertAfter(etTh.parentNode, th, etTh);
        var etIdx = [].indexOf.call(etTh.parentNode.children, etTh);
        table.querySelectorAll("tbody tr").forEach(function (tr) {
          var td = document.createElement("td");
          td.className = "dam-bottle-corr-col";
          td.innerHTML = tick;
          insertAfter(tr, td, tr.children[etIdx]);
        });
      }
    }
    ensureR1(table);
  }

  function bottleSrc() {
    return "/artwork/Event%20Logo/Dam-Bottle-Sprints.png";
  }

  function setBottleImg(img) {
    if (!img) return;
    img.src = bottleSrc();
    img.alt = "Dam Bottle Sprints";
    img.removeAttribute("title");
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
          n.nodeValue = " Open Fleet";
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

  function placeOpenFleetHeader() {
    var host = document.getElementById("midmar-live-media");
    if (!host || !host.parentNode) return;
    dropDuplicateFleetHeaders();
    var sec = document.querySelector(
      '.fleet-section[data-block-id="' + RID + ':open"] table.fleet-results-table'
    );
    sec = sec ? sec.closest(".fleet-section") : null;
    if (!sec) return;
    sec.id = "dam-bottle-open-fleet";
    sec.setAttribute("data-fleet-label", "Open");
    paintOpenFleetHeader(sec);
    if (sec.previousSibling !== host) host.parentNode.insertBefore(sec, host.nextSibling);
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

  function add(src) {
    var base = src.split("?")[0];
    if (document.querySelector('script[src*="' + base + '"]')) return;
    var s = document.createElement("script");
    s.src = src;
    s.defer = true;
    document.head.appendChild(s);
  }
  /* Same as Dart: live-media boots first and then loads leaderboard into the host. */
  add("/js/midmar-live-media.js?v=midmarwx60dbs3");
  add("/js/club-score-edit.js?v=ccr38dbs3");

  syncDartStack();
  [50, 200, 600, 1200, 2500].forEach(function (ms) {
    window.setTimeout(syncDartStack, ms);
  });
  if (window.MutationObserver && page) {
    var obs = new MutationObserver(syncDartStack);
    obs.observe(page, { childList: true, subtree: true });
    window.setTimeout(function () {
      try {
        obs.disconnect();
      } catch (e) {}
    }, 8000);
  }
})();
