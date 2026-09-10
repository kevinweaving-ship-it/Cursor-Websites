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
      ".club-score-input{box-sizing:border-box;width:3.5rem;min-width:44px;min-height:44px;padding:8px 6px;text-align:center;font:inherit;font-weight:700;border:2px solid #1a2750;border-radius:6px;background:#fff;color:#1a2750}" +
      ".club-score-input.club-score-input--saved{background:#bbf7d0}" +
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
      "ZVYC club admin — type 1–n once each in R1. Type n+1 or OCS/DSQ/DNC for a code (can repeat). Total, Nett and Rank are automatic.";
    var firstFleet = page.querySelector(".fleet-section");
    if (firstFleet) page.insertBefore(el, firstFleet);
    else page.insertBefore(el, page.firstChild);
  }

  function save(inp) {
    if (!inp || !inp.classList.contains("club-score-input")) return;
    var rid = inp.getAttribute("data-result-id");
    var race = inp.getAttribute("data-race");
    if (!rid || !race || race.charAt(0) !== "R") return;
    var v = (inp.value || "").trim();
    var orig = (inp.getAttribute("data-original") || "").trim();
    if (v === orig) return;
    inp.disabled = true;
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
        inp.disabled = false;
        if (!o.ok) {
          alert((o.j && (o.j.detail || o.j.error)) || "Could not save score");
          inp.value = inp.getAttribute("data-original") || "";
          return;
        }
        inp.setAttribute("data-original", v);
        inp.value = v;
        inp.classList.add("club-score-input--saved");
        setTimeout(function () {
          location.reload();
        }, 400);
      })
      .catch(function () {
        inp.disabled = false;
        inp.value = inp.getAttribute("data-original") || "";
      });
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
      if (ev.key === "Enter") {
        ev.preventDefault();
        inp.blur();
      }
    });
  }

  function activate() {
    injectStyles();
    var page = document.querySelector(".regatta-page");
    if (!page) return;
    page.classList.add("regatta-page--club-score-edit");
    banner();
    page.querySelectorAll("tr[data-result-id]").forEach(function (tr) {
      var rid = tr.getAttribute("data-result-id");
      if (!rid) return;
      tr.querySelectorAll("td.race-col[data-race-key]").forEach(function (td) {
        wireCell(td, rid);
      });
    });
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
