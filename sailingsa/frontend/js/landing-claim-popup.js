/* Landing search: compact claim chip stays in the list card.
   Click opens a /pop-up overlay sized to the inner card: preview then Step 1.
   Quit Sign Up returns to the search list. */
(function () {
  window.__ssaLandingClaimPopup = true;

  var CSS_ID = "ssa-landing-claim-popup-css";
  var CSS_LINK_ID = "ssa-landing-claim-popup-css-link";
  var JS_VER = "20260911pw";
  var prevOverflow = "";

  var CLAIM_INNER =
    '<button type="button" class="sa-looked-claim" data-ssa-list-claim title="Claim your profile">' +
      '<span class="sa-looked-claim-top">' +
        '<span class="sa-looked-claim-ask">Is this your sailing profile?</span>' +
        '<span class="sa-looked-claim-sub">Unlock your full results and stats</span>' +
      "</span>" +
      '<span class="sa-looked-claim-bar">' +
        '<span class="sa-looked-claim-txt">Claim my profile</span>' +
        '<span class="sa-looked-claim-go" aria-hidden="true">∨</span>' +
      "</span>" +
    "</button>";

  var WA_SVG = '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path fill="#fff" d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.435 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>';
  var GOOGLE_SVG = '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>';
  var FB_SVG = '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="12" cy="12" r="12" fill="white"/><path d="M13.44 20V13.44H15.64L15.97 10.88H13.44V9.24C13.44 8.5 13.64 8 14.7 8H16V5.72C15.37 5.63 14.74 5.59 14.1 5.6C12.21 5.6 10.92 6.75 10.92 8.86V10.88H8.8V13.44H10.92V20H13.44Z" fill="#1877F2"/></svg>';
  var MAIL_SVG = '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M4 6.5H20C20.83 6.5 21.5 7.17 21.5 8V16C21.5 16.83 20.83 17.5 20 17.5H4C3.17 17.5 2.5 16.83 2.5 16V8C2.5 7.17 3.17 6.5 4 6.5Z" stroke="#fff" stroke-width="1.8"/><path d="M3 8L12 14L21 8" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  var BOAT_ICO = "/icons/assets/phosphor/fill/sailboat-fill.svg";
  var FLAG_ICO = "/icons/assets/phosphor/fill/flag-checkered-fill.svg";
  var CAL_ICO = "/icons/assets/phosphor/fill/calendar-blank-fill.svg";

  function injectCss() {
    var link = document.getElementById(CSS_LINK_ID);
    if (!link) {
      link = document.createElement("link");
      link.id = CSS_LINK_ID;
      link.rel = "stylesheet";
      link.href = "/js/landing-claim-popup.css?v=" + JS_VER;
      document.head.appendChild(link);
    }
    var s = document.getElementById(CSS_ID);
    if (s) s.parentNode.removeChild(s);
    s = document.createElement("style");
    s.id = CSS_ID;
    s.textContent = [
      ".ssa-dev1-inject .sa-header-mid-slot > .sa-claim-slot.ssa-popup-claim-slot,",
      ".ssa-dev1-inject .sa-header-mid-slot > #dev1-claim-slot.ssa-popup-claim-slot,",
      ".ssa-dev1-inject #dev1-claim-slot.ssa-popup-claim-slot,",
      ".ssa-dev1-inject .ssa-popup-claim-slot{display:flex!important;justify-content:center!important;align-items:center!important;align-self:stretch!important;width:100%!important;height:100%!important;max-height:100%!important;min-width:0;min-height:0;margin:0!important;padding:0!important;box-sizing:border-box;overflow:visible;position:relative;z-index:1;}",
      ".ssa-dev1-inject .ssa-popup-claim-slot .sa-looked-cta{display:flex;flex-direction:column;width:max-content;max-width:100%;height:auto!important;min-width:220px;margin:0 auto;padding:0;box-sizing:border-box;border:1px solid #c4a26f;border-radius:12px;overflow:hidden;background:#fefaf5;transform:none!important;transform-origin:center center!important;}",
      ".ssa-dev1-inject .ssa-popup-claim-slot .sa-looked-claim{display:flex!important;flex-direction:column;align-items:stretch;justify-content:flex-start;width:auto!important;height:auto!important;max-width:100%!important;margin:0;padding:0;box-sizing:border-box;background:transparent;border:0;text-decoration:none;color:inherit;line-height:1;cursor:pointer;font:inherit;transform:none!important;transform-origin:center center!important;}",
      ".ssa-dev1-inject .ssa-popup-claim-slot .sa-looked-claim-top{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:4px;flex:0 0 auto;width:100%;margin:0;padding:12px 14px 11px;box-sizing:border-box;background:#fefaf5;text-align:center;min-height:0;}",
      ".ssa-dev1-inject .ssa-popup-claim-slot .sa-looked-claim-ask{margin:0;padding:0;font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;font-weight:800;font-size:15px;line-height:1.15;color:#0a2351;letter-spacing:-0.01em;white-space:nowrap;}",
      ".ssa-dev1-inject .ssa-popup-claim-slot .sa-looked-claim-sub{margin:0;padding:0;font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;font-weight:500;font-size:12px;line-height:1.2;color:#0a2351;white-space:nowrap;}",
      ".ssa-dev1-inject .ssa-popup-claim-slot .sa-looked-claim-bar{display:flex;flex-direction:row;align-items:center;justify-content:center;gap:8px;flex:0 0 auto;width:100%;margin:0;padding:11px 40px 11px 14px;box-sizing:border-box;background:#0a2351;position:relative;}",
      ".ssa-dev1-inject .ssa-popup-claim-slot .sa-looked-claim-txt{flex:1 1 auto;min-width:0;font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;font-weight:800;font-size:12px;line-height:1;color:#fff;text-transform:uppercase;letter-spacing:.04em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;text-align:center;}",
      ".ssa-dev1-inject .ssa-popup-claim-slot .sa-looked-claim-go{position:absolute;right:10px;top:50%;transform:translateY(-50%);flex:0 0 auto;width:22px;height:22px;border-radius:999px;background:#c4a26f;color:#0a2351;display:inline-flex;align-items:center;justify-content:center;font-size:14px;font-weight:900;line-height:1;box-sizing:border-box;}",
      "@media screen and (orientation:portrait) and (max-width:767px){",
      ".ssa-dev1-inject .ssa-popup-claim-slot{justify-content:stretch!important;align-items:stretch!important;overflow:hidden;}",
      ".ssa-dev1-inject .ssa-popup-claim-slot .sa-looked-cta{width:100%;height:100%!important;min-width:0;}",
      ".ssa-dev1-inject .ssa-popup-claim-slot .sa-looked-claim{width:100%!important;height:100%!important;}",
      ".ssa-dev1-inject .ssa-popup-claim-slot .sa-looked-claim-top{flex:1 1 auto;padding:8px 8px 7px;gap:3px;}",
      ".ssa-dev1-inject .ssa-popup-claim-slot .sa-looked-claim-ask{font-size:13px;white-space:normal;}",
      ".ssa-dev1-inject .ssa-popup-claim-slot .sa-looked-claim-sub{font-size:11px;white-space:normal;}",
      ".ssa-dev1-inject .ssa-popup-claim-slot .sa-looked-claim-bar{padding:9px 32px 9px 10px;}",
      ".ssa-dev1-inject .ssa-popup-claim-slot .sa-looked-claim-txt{font-size:11px;}",
      ".ssa-dev1-inject .ssa-popup-claim-slot .sa-looked-claim-go{right:8px;width:18px;height:18px;font-size:12px;}",
      "}",
      "body.ssa-claim-modal-open .ssa-dev1-inject .ssa-popup-claim-slot,",
      "body.ssa-claim-modal-open .ssa-dev1-inject .ssa-popup-claim-slot .sa-looked-cta,",
      "body.ssa-claim-modal-open .ssa-dev1-inject .ssa-popup-claim-slot .sa-looked-claim{",
      "visibility:hidden!important;opacity:0!important;pointer-events:none!important;z-index:0!important;",
      "}",
      "#ssa-claim-modal .lab-card-wrap.is-password .sa-looked-auth,",
      "#ssa-claim-modal .lab-card-wrap.is-password .sa-looked-wa,",
      "#ssa-claim-modal .lab-card-wrap.is-password .sa-looked-signup-choose,",
      "#ssa-claim-modal .lab-card-wrap.is-password .sa-looked-signup-welcome{display:none!important;}",
      "#ssa-claim-modal .lab-card-wrap.is-done .sa-looked-auth,",
      "#ssa-claim-modal .lab-card-wrap.is-done .sa-looked-wa,",
      "#ssa-claim-modal .lab-card-wrap.is-done .sa-looked-pw,",
      "#ssa-claim-modal .lab-card-wrap.is-done .sa-looked-signup-choose,",
      "#ssa-claim-modal .lab-card-wrap.is-done .sa-looked-signup-welcome,",
      "#ssa-claim-modal .lab-card-wrap.is-done .ssa-claim-quit{display:none!important;}"
    ].join("");
    document.head.appendChild(s);
  }

  function esc(v) {
    return String(v == null ? "" : v)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function digits(v) {
    return String(v || "").replace(/\D/g, "");
  }

  function txt(root, sel) {
    if (!root || !root.querySelector) return "";
    var el = root.querySelector(sel);
    return el ? String(el.textContent || "").replace(/\s+/g, " ").trim() : "";
  }

  function attr(el, name) {
    return el && el.getAttribute ? String(el.getAttribute(name) || "") : "";
  }

  function safeHref(u, fallback) {
    var s = String(u || "");
    if (s.charAt(0) === "/" && s.charAt(1) !== "/") return s;
    if (/^https?:\/\//i.test(s)) return s;
    return fallback || "#";
  }

  function classSlug(n) {
    return String(n || "")
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "");
  }

  function classLogoUrl(name, fallback) {
    if (fallback) return fallback;
    var key = String(name || "").trim().toLowerCase();
    var ssot = window.__SSA_CLASS_LOGO_SSOT || {};
    if (ssot[key]) return ssot[key];
    if (ssot[classSlug(key)]) return ssot[classSlug(key)];
    var slug = classSlug(name);
    return slug ? "/artwork/Class Logo/" + slug.replace(/(^|-)(\w)/g, function (_, a, b) { return (a ? "-" : "") + b.toUpperCase(); }) + "-Class-Logo.png" : "";
  }

  function ordinal(n) {
    var v = parseInt(n, 10);
    if (!v || isNaN(v)) return "—";
    var d = v % 100;
    if (d >= 11 && d <= 13) return v + "th";
    return v + ({ 1: "st", 2: "nd", 3: "rd" }[v % 10] || "th");
  }

  function formatEventDates(start, end) {
    function parse(x) {
      var m = String(x || "").slice(0, 10).match(/^(\d{4})-(\d{2})-(\d{2})$/);
      if (!m) return null;
      return { y: +m[1], mo: +m[2], d: +m[3], raw: m[0] };
    }
    var mon = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    var s = parse(start);
    var e = parse(end || start) || s;
    if (!s) return "";
    if (!e || e.raw === s.raw) return s.d + " " + mon[s.mo - 1] + " " + s.y;
    if (s.y === e.y && s.mo === e.mo) return s.d + "–" + e.d + " " + mon[s.mo - 1] + " " + s.y;
    if (s.y === e.y) return s.d + " " + mon[s.mo - 1] + " – " + e.d + " " + mon[e.mo - 1] + " " + e.y;
    return s.d + " " + mon[s.mo - 1] + " " + s.y + " – " + e.d + " " + mon[e.mo - 1] + " " + e.y;
  }

  function raceCount(row) {
    var rs = row && row.race_scores;
    if (!rs) return 0;
    if (Array.isArray(rs)) return rs.length;
    if (typeof rs === "object") return Object.keys(rs).length;
    return 0;
  }

  function isSeries(row) {
    return !!(row && (row.is_series === true || row.regatta_number === "S" ||
      (row.event_name && String(row.event_name).indexOf("Series") >= 0 && String(row.event_name).indexOf("> Overall") >= 0)));
  }

  function extHref(provider, info) {
    var u = "/signup.html?signup=1&provider=" + encodeURIComponent(provider) + "&from=claim";
    if (info && info.sid) u += "&sas_id=" + encodeURIComponent(info.sid);
    if (info && info.name) u += "&name=" + encodeURIComponent(info.name);
    try {
      u += "&returnTo=" + encodeURIComponent(window.location.href || "/");
    } catch (_) {}
    return u;
  }

  function sailorInfo(slot, fallback) {
    var live = fallback ? { sid: fallback.sid || "", name: fallback.name || "", slug: fallback.slug || "" } : { sid: "", name: "", slug: "" };
    live.sid = live.sid || (slot && slot.dataset && slot.dataset.sasId) || "";
    if (!live.name && slot) {
      live.name = [txt(slot, ".sa-approved-sailor-name-first"), txt(slot, ".sa-approved-sailor-name-last")]
        .filter(Boolean)
        .join(" ");
    }
    if (!live.slug && slot) {
      var a = slot.querySelector('a[href^="/sailor/"]');
      if (a) live.slug = String(attr(a, "href") || "").replace(/^\/sailor\//, "").split("?")[0];
    }
    return live;
  }

  function extractProfile(slot, info) {
    var live = sailorInfo(slot, info);
    var first = txt(slot, ".sa-approved-sailor-name-first");
    var last = txt(slot, ".sa-approved-sailor-name-last");
    if (!first && live.name) {
      var parts = String(live.name).split(" ");
      first = parts.shift() || "";
      last = parts.join(" ");
    }
    var avatar = slot && slot.querySelector(".sa-approved-sailor-avatar-clip img, .sa-approved-sailor-avatar img");
    var club = txt(slot, ".sa-approved-sailor-club-code");
    var clubImg = slot && slot.querySelector(".sa-approved-sailor-club-icon img");
    var sslA = slot && slot.querySelector(".sa-ssl-brand-box, a.brand-box");
    var sslPoints = [];
    if (slot) {
      slot.querySelectorAll(".sa-ssl-point-box").forEach(function (el) {
        var t = String(el.textContent || "").trim();
        if (t) sslPoints.push(t);
      });
    }
    var podiumRoot = slot && slot.querySelector("[data-ns-podiums]");
    var gold = 0, silver = 0, bronze = 0;
    if (podiumRoot) {
      var ns = podiumRoot.querySelectorAll("[data-ns-medal-n]");
      gold = parseInt(ns[0] && ns[0].textContent, 10) || 0;
      silver = parseInt(ns[1] && ns[1].textContent, 10) || 0;
      bronze = parseInt(ns[2] && ns[2].textContent, 10) || 0;
    }
    var medalRate = podiumRoot ? txt(podiumRoot, "[data-ns-medal-rate-n]") : "";
    var regattas = "", races = "";
    if (slot) {
      slot.querySelectorAll("[data-ns-stat-line]").forEach(function (line) {
        var lbl = txt(line, "[data-ns-stat-lbl]").toLowerCase();
        var num = txt(line, "[data-ns-stat-num]");
        if (lbl.indexOf("regatta") >= 0 && !regattas) regattas = num;
        if (lbl.indexOf("race") >= 0 && !races) races = num;
      });
    }
    var classes = [];
    var classRoot = slot && slot.querySelector("[data-ns-classes]");
    if (classRoot) {
      classRoot.querySelectorAll("img").forEach(function (img) {
        var src = attr(img, "src");
        if (!src) return;
        var a = img.closest("a");
        classes.push({ src: src, alt: attr(img, "alt") || attr(img, "title"), href: a ? attr(a, "href") : "" });
      });
    }
    return {
      sid: live.sid,
      name: live.name || [first, last].filter(Boolean).join(" "),
      first: first,
      last: last,
      slug: live.slug || "",
      avatar: avatar ? attr(avatar, "src") : "/assets/avatars/default-youth.png",
      alt: avatar ? (attr(avatar, "alt") || live.name) : live.name,
      club: club,
      clubLogo: clubImg ? attr(clubImg, "src") : (club ? "/api/club-logo/" + encodeURIComponent(club) : ""),
      sslRank: txt(slot, ".sa-ssl-rank-digits") || txt(slot, ".sa-approved-ssl-rank-number"),
      sslPoints: sslPoints,
      sslHref: sslA ? attr(sslA, "href") : "",
      gold: gold,
      silver: silver,
      bronze: bronze,
      medalRate: medalRate,
      regattas: regattas,
      races: races,
      classes: classes
    };
  }

  function signupHtml(name) {
    return (
      '<div class="sa-looked-signup-card">' +
        '<span class="sa-looked-signup-step-lbl">Step 1</span>' +
        '<span class="sa-looked-signup-welcome">Welcome <span class="sa-looked-signup-welcome-name" data-ssa-claim-name>' + esc(name || "Sailor") + "</span></span>" +
        '<span class="sa-looked-signup-choose">Please choose method to register</span>' +
        '<button type="button" class="sa-looked-auth sa-looked-auth--whatsapp" data-wa-open>' +
          '<span class="sa-looked-auth-ico" aria-hidden="true">' + WA_SVG + "</span>" +
          '<span class="sa-looked-auth-txt">Signup With</span>' +
          '<span class="sa-looked-auth-go" aria-hidden="true">›</span>' +
        "</button>" +
        '<a class="sa-looked-auth sa-looked-auth--google" data-ssa-claim-ext="google" href="#">' +
          '<span class="sa-looked-auth-ico" aria-hidden="true">' + GOOGLE_SVG + "</span>" +
          '<span class="sa-looked-auth-txt">Sign up with Google</span>' +
          '<span class="sa-looked-auth-go" aria-hidden="true">›</span>' +
        "</a>" +
        '<a class="sa-looked-auth sa-looked-auth--facebook" data-ssa-claim-ext="facebook" href="#">' +
          '<span class="sa-looked-auth-ico" aria-hidden="true">' + FB_SVG + "</span>" +
          '<span class="sa-looked-auth-txt">Sign up with Facebook</span>' +
          '<span class="sa-looked-auth-go" aria-hidden="true">›</span>' +
        "</a>" +
        '<a class="sa-looked-auth sa-looked-auth--email" data-ssa-claim-ext="email" href="#">' +
          '<span class="sa-looked-auth-ico" aria-hidden="true">' + MAIL_SVG + "</span>" +
          '<span class="sa-looked-auth-txt">Sign up with email</span>' +
        "</a>" +
        '<div class="sa-looked-wa" data-wa-panel hidden>' +
          '<div class="sa-looked-wa-phone-step" data-wa-phone-step>' +
            '<span class="sa-looked-wa-label">Enter Your WhatsApp No</span>' +
            '<input class="sa-looked-wa-input" data-wa-phone type="tel" inputmode="tel" autocomplete="tel" placeholder="082 123 4567" maxlength="16">' +
            '<button type="button" class="sa-looked-wa-send" data-wa-send>Request Code</button>' +
          "</div>" +
          '<div class="sa-looked-wa-code-step" data-wa-code-step hidden>' +
            '<span class="sa-looked-wa-label">Enter your 4-digit code</span>' +
            '<div class="sa-looked-wa-boxes" data-wa-boxes>' +
              '<input class="sa-looked-wa-box" data-wa-digit="0" type="text" inputmode="numeric" maxlength="1" autocomplete="one-time-code" aria-label="Code digit 1">' +
              '<input class="sa-looked-wa-box" data-wa-digit="1" type="text" inputmode="numeric" maxlength="1" aria-label="Code digit 2">' +
              '<input class="sa-looked-wa-box" data-wa-digit="2" type="text" inputmode="numeric" maxlength="1" aria-label="Code digit 3">' +
              '<input class="sa-looked-wa-box" data-wa-digit="3" type="text" inputmode="numeric" maxlength="1" aria-label="Code digit 4">' +
            "</div>" +
          "</div>" +
          '<p class="sa-looked-wa-msg" data-wa-msg></p>' +
        "</div>" +
        '<div class="sa-looked-pw" data-pw-panel hidden>' +
          '<span class="sa-looked-wa-label">Create a password</span>' +
          '<input class="sa-looked-wa-input" data-pw-1 type="password" autocomplete="new-password" placeholder="Password">' +
          '<input class="sa-looked-wa-input" data-pw-2 type="password" autocomplete="new-password" placeholder="Confirm password">' +
          '<button type="button" class="sa-looked-wa-send sa-looked-pw-save" data-pw-save>Save</button>' +
          '<p class="sa-looked-wa-msg" data-pw-msg></p>' +
        "</div>" +
        '<div class="sa-looked-done" data-done-panel hidden>' +
          '<span class="sa-looked-signup-step-lbl">Well Done</span>' +
          '<span class="sa-looked-done-name" data-done-name></span>' +
          '<p class="sa-looked-done-copy">You have successfully<br>claimed your profile</p>' +
          '<p class="sa-looked-done-copy">Next time login with your<br>WhatsApp number<br>and password</p>' +
        "</div>" +
      "</div>"
    );
  }

  function medalHtml(title, ico, n) {
    return (
      '<span class="sa-looked-medal" title="' + esc(title) + '">' +
        '<span class="sa-looked-medal-ico" aria-hidden="true">' + ico + "</span>" +
        '<span class="sa-looked-medal-n-row" aria-label="' + esc(String(n)) + '">' +
          '<span class="sa-looked-medal-n">' + esc(String(n)) + "</span>" +
        "</span>" +
      "</span>"
    );
  }

  function classesHtml(list) {
    if (!list || !list.length) return "";
    return (
      '<div class="sa-looked-classes"><div class="sa-looked-classes-row">' +
      list.map(function (c, i) {
        var img = '<img class="sa-looked-class-logo' + (i < 2 ? " sa-looked-class-logo--top" : "") + '" src="' + esc(c.src) + '" alt="' + esc(c.alt || "") + '">';
        if (c.href) return '<a class="sa-looked-class-link" href="' + esc(safeHref(c.href, "#")) + '" title="' + esc(c.alt || "") + '">' + img + "</a>";
        return '<span class="sa-looked-class-link">' + img + "</span>";
      }).join("") +
      "</div></div>"
    );
  }

  function eventRowHtml(row) {
    var rank = parseInt(row.rank, 10);
    var cls = "sa-looked-ev";
    if (rank === 1) cls += " rank-1";
    else if (rank === 2) cls += " rank-2";
    var liveSt = String(row.live_board_status || "").toUpperCase();
    if (!liveSt && row.is_live) liveSt = "LIVE";
    var liveCls = "";
    if (liveSt === "RACING") liveCls = "racing";
    else if (liveSt === "POSTPONED") liveCls = "postponed";
    else if (liveSt === "LIVE" || row.is_live) liveCls = "live";
    if (liveCls) cls += " is-live-" + liveCls;
    var href = safeHref(row.event_url || (row.regatta_id ? "/regatta/" + row.regatta_id : ""), "#");
    var className = row.class_canonical || row.class_original || "";
    var classSrc = classLogoUrl(className, row.class_logo_url);
    var club = row.club || "";
    var liveBadge = liveCls
      ? '<span class="sa-looked-ev-live sa-looked-ev-live--' + liveCls + '" data-live-badge="1">' + (liveCls === "live" ? "Live" : liveSt) + "</span>"
      : "";
    var eventLogo = row.event_logo_url
      ? '<img class="sa-looked-ev-eventlogo" src="' + esc(row.event_logo_url) + '" alt="">'
      : "";
    return (
      '<a class="' + cls + '" href="' + esc(href) + '">' +
        '<div class="sa-looked-ev-left">' +
          '<div class="sa-looked-ev-rank"><div class="sa-looked-ev-rankstack">' +
            '<span class="sa-looked-ev-place">' + esc(ordinal(rank)) + "</span>" +
            '<span class="sa-looked-ev-rankline" aria-hidden="true"></span>' +
            '<span class="sa-looked-ev-fleet">' + esc(row.entries != null ? String(row.entries) : "—") + "</span>" +
          "</div></div>" +
          '<div class="sa-looked-ev-class">' +
            (classSrc ? '<img src="' + esc(classSrc) + '" alt="' + esc(className) + '">' : "") +
          "</div>" +
        "</div>" +
        '<div class="sa-looked-ev-main">' +
          '<div class="sa-looked-ev-title">' + esc(row.event_name || "Event") + "</div>" +
          '<div class="sa-looked-ev-date"><img src="' + CAL_ICO + '" alt="" aria-hidden="true"><span>' +
            esc(formatEventDates(row.start_date, row.end_date)) + "</span></div>" +
          liveBadge +
          '<div class="sa-looked-ev-logos">' +
            (club
              ? '<span class="sa-looked-ev-club"><img src="/api/club-logo/' + esc(club) + '" alt="' + esc(club) + '"><span class="sa-looked-ev-club-code">' + esc(club) + "</span></span>"
              : "") +
            eventLogo +
          "</div>" +
        "</div>" +
      "</a>"
    );
  }

  function cardHtml(p) {
    var clubHref = p.club ? "/club/" + encodeURIComponent(String(p.club).toLowerCase()) : "#";
    var sslHref = safeHref(p.sslHref, "#");
    var points = (p.sslPoints || []).map(function (d) {
      return '<span class="sa-ssl-point-box">' + esc(d) + "</span>";
    }).join("");
    return (
      '<div class="popup-card">' +
        '<div class="sa-approved-sailor-header">' +
          '<div class="sa-approved-sailor-avatar-col"><div class="sa-approved-sailor-avatar"><div class="sa-approved-sailor-avatar-clip">' +
            '<img src="' + esc(p.avatar || "/assets/avatars/default-youth.png") + '" alt="' + esc(p.alt || p.name) + '" width="76" height="76">' +
          "</div></div></div>" +
          '<div class="sa-approved-sailor-main">' +
            '<div class="sa-approved-sailor-id-band">' +
              '<h2 class="sa-approved-sailor-name"><span class="sa-approved-sailor-name-first">' + esc(p.first || "Sailor") + '</span>' +
              '<span class="sa-approved-sailor-name-last">' + esc(p.last || "") + "</span></h2>" +
              (p.club
                ? '<a class="sa-approved-sailor-club-link sa-approved-sailor-club-icon-link" href="' + esc(clubHref) + '" title="' + esc(p.club) + '"><span class="sa-approved-sailor-club-icon"><img src="' + esc(p.clubLogo) + '" alt="' + esc(p.club) + '"></span></a>'
                : "") +
            "</div>" +
            (p.club
              ? '<div class="sa-approved-sailor-club"><a class="sa-approved-sailor-club-link" href="' + esc(clubHref) + '" title="' + esc(p.club) + '"><span class="sa-approved-sailor-club-code">' + esc(p.club) + "</span></a></div>"
              : "") +
          "</div>" +
          '<div class="sa-header-ssl-col">' +
            '<a class="brand-box sa-ssl-brand-box" href="' + esc(sslHref) + '" target="_blank" rel="noopener noreferrer" title="SSL ranking / World of Sailors">' +
              '<img class="brand-icon sa-ssl-brand-icon" src="/artwork/SSL-Ranking-Star.png?v=20260811b" alt="SSL Ranking Star Icon">' +
              '<div class="sa-ssl-rank-stack">' +
                '<h2 class="brand-wordmark sa-ssl-wordmark">SSL RANK</h2>' +
                '<div class="rank-hero sa-ssl-rank-hero">' +
                  '<span class="sa-ssl-rank-line" aria-hidden="true"></span>' +
                  '<div class="rank-num sa-ssl-rank-num"><span class="sa-ssl-rank-wrap"><span class="sa-ssl-rank-digits">' + esc(p.sslRank || "—") + "</span></span></div>" +
                  '<span class="sa-ssl-rank-line" aria-hidden="true"></span>' +
                "</div>" +
                '<div class="sa-ssl-points-label">POINTS</div>' +
                '<div class="sa-ssl-points-row">' + points + "</div>" +
              "</div>" +
            "</a>" +
          "</div>" +
        "</div>" +
        '<div class="sa-looked-summary">' +
          '<div class="sa-looked-podiums" data-ns-podiums="1">' +
            '<span class="sa-looked-podiums-hdr">PODIUMS</span>' +
            '<span class="sa-looked-medal-row">' +
              medalHtml("1st", "🥇", p.gold || 0) +
              medalHtml("2nd", "🥈", p.silver || 0) +
              medalHtml("3rd", "🥉", p.bronze || 0) +
            "</span>" +
            '<span class="sa-looked-medal-rate"><span class="sa-looked-medal-rate-stack">' +
              '<span class="sa-looked-medal-rate-labels"><span class="sa-looked-medal-rate-lbl">Medal Rate</span></span>' +
              '<span class="sa-looked-medal-rate-val" data-ssa-medal-rate>' + esc(p.medalRate || "—") + "</span>" +
            "</span></span>" +
          "</div>" +
          '<div class="sa-looked-rule" role="separator" aria-hidden="true"></div>' +
          '<div class="sa-looked-stats"><div class="sa-looked-stats-rows">' +
            '<div class="sa-looked-stat-row"><span class="sa-looked-stat-lbl">Regattas</span><img class="sa-looked-stat-ico sa-looked-stat-ico--boat" src="' + BOAT_ICO + '" alt="" aria-hidden="true"><span class="sa-looked-stat-n" data-ssa-regattas>' + esc(p.regattas || "—") + "</span></div>" +
            '<div class="sa-looked-stat-row"><span class="sa-looked-stat-lbl">Races</span><img class="sa-looked-stat-ico sa-looked-stat-ico--flag" src="' + FLAG_ICO + '" alt="" aria-hidden="true"><span class="sa-looked-stat-n" data-ssa-races>' + esc(p.races || "—") + "</span></div>" +
          "</div></div>" +
          '<div data-ssa-classes-host>' + classesHtml(p.classes) + "</div>" +
        "</div>" +
        '<div class="sa-looked-events" data-ssa-events>' +
          '<span class="sa-looked-events-hdr">Last 2 <img class="sa-looked-events-hdr-ico" src="' + BOAT_ICO + '" alt="" aria-hidden="true"> Events of <span data-ssa-event-total>' + esc(p.regattas || "…") + '</span> <img class="sa-looked-events-hdr-ico" src="' + BOAT_ICO + '" alt="" aria-hidden="true"></span>' +
          '<div class="sa-looked-events-list" data-ssa-events-list>Loading…</div>' +
        "</div>" +
        '<div class="sa-looked-cta">' +
          '<button type="button" class="sa-looked-claim" data-ssa-modal-claim title="Claim your profile" aria-expanded="false">' +
            '<span class="sa-looked-claim-top"><span class="sa-looked-claim-ask">Is this your sailing profile?</span><span class="sa-looked-claim-sub">Unlock your full results and stats</span></span>' +
            '<span class="sa-looked-claim-bar"><span class="sa-looked-claim-txt">Claim my profile</span><span class="sa-looked-claim-go" aria-hidden="true">∨</span></span>' +
          "</button>" +
        "</div>" +
        '<div class="sa-looked-signup" hidden>' + signupHtml(p.name) + "</div>" +
      "</div>" +
      '<button type="button" class="ssa-claim-quit" data-ssa-quit>Quit Sign Up</button>'
    );
  }

  function resetWa(wrap) {
    var card = wrap.querySelector(".sa-looked-signup-card");
    var panel = wrap.querySelector("[data-wa-panel]");
    var phoneStep = wrap.querySelector("[data-wa-phone-step]");
    var codeStep = wrap.querySelector("[data-wa-code-step]");
    var phone = wrap.querySelector("[data-wa-phone]");
    var msg = wrap.querySelector("[data-wa-msg]");
    if (card) card.classList.remove("is-method-picked");
    wrap.querySelectorAll(".sa-looked-auth").forEach(function (a) {
      a.classList.remove("is-chosen");
    });
    if (panel) {
      panel.hidden = true;
      panel.classList.remove("is-open");
    }
    if (phoneStep) phoneStep.hidden = false;
    if (codeStep) codeStep.hidden = true;
    if (phone) phone.value = "";
    wrap.querySelectorAll("[data-wa-digit]").forEach(function (box) {
      box.value = "";
      box.disabled = false;
    });
    if (msg) {
      msg.textContent = "";
      msg.classList.remove("is-err", "is-ok");
    }
    wrap.classList.remove("is-password", "is-done");
    var pwPanel = wrap.querySelector("[data-pw-panel]");
    var donePanel = wrap.querySelector("[data-done-panel]");
    var pw1 = wrap.querySelector("[data-pw-1]");
    var pw2 = wrap.querySelector("[data-pw-2]");
    var pwMsg = wrap.querySelector("[data-pw-msg]");
    var stepLbl = wrap.querySelector(".sa-looked-signup-step-lbl");
    if (pwPanel) {
      pwPanel.hidden = true;
      pwPanel.classList.remove("is-open");
    }
    if (donePanel) {
      donePanel.hidden = true;
      donePanel.classList.remove("is-open");
    }
    if (pw1) pw1.value = "";
    if (pw2) pw2.value = "";
    if (pwMsg) {
      pwMsg.textContent = "";
      pwMsg.classList.remove("is-err", "is-ok");
    }
    if (stepLbl && !stepLbl.closest("[data-done-panel]")) stepLbl.textContent = "Step 1";
    if (wrap.__ssaDoneTimer) {
      try { clearTimeout(wrap.__ssaDoneTimer); } catch (_) {}
      wrap.__ssaDoneTimer = null;
    }
  }

  function showPreview(wrap) {
    wrap.classList.remove("is-step1");
    var panel = wrap.querySelector(".sa-looked-signup");
    var btn = wrap.querySelector("[data-ssa-modal-claim]");
    if (panel) {
      panel.hidden = true;
      panel.classList.remove("is-open");
    }
    if (btn) {
      btn.classList.remove("is-open");
      btn.setAttribute("aria-expanded", "false");
    }
    resetWa(wrap);
  }

  function showStep1(wrap) {
    wrap.classList.add("is-step1");
    var panel = wrap.querySelector(".sa-looked-signup");
    var btn = wrap.querySelector("[data-ssa-modal-claim]");
    if (panel) {
      panel.hidden = false;
      panel.removeAttribute("hidden");
      panel.classList.add("is-open");
    }
    if (btn) {
      btn.classList.add("is-open");
      btn.setAttribute("aria-expanded", "true");
    }
  }

  function wireSignup(wrap) {
    if (wrap.getAttribute("data-ssa-signup-wired") === "1") return;
    wrap.setAttribute("data-ssa-signup-wired", "1");
    var signupCard = wrap.querySelector(".sa-looked-signup-card");
    var panel = wrap.querySelector("[data-wa-panel]");
    var phoneStep = wrap.querySelector("[data-wa-phone-step]");
    var codeStep = wrap.querySelector("[data-wa-code-step]");
    var phone = wrap.querySelector("[data-wa-phone]");
    var sendBtn = wrap.querySelector("[data-wa-send]");
    var codeBoxes = wrap.querySelectorAll("[data-wa-digit]");
    var msg = wrap.querySelector("[data-wa-msg]");
    var pwPanel = wrap.querySelector("[data-pw-panel]");
    var donePanel = wrap.querySelector("[data-done-panel]");
    var pw1 = wrap.querySelector("[data-pw-1]");
    var pw2 = wrap.querySelector("[data-pw-2]");
    var pwSave = wrap.querySelector("[data-pw-save]");
    var pwMsg = wrap.querySelector("[data-pw-msg]");
    var stepLbl = wrap.querySelector(".sa-looked-signup-card > .sa-looked-signup-step-lbl");
    var verifying = false;
    function setMsg(text, kind) {
      if (!msg) return;
      msg.textContent = text || "";
      msg.classList.remove("is-err", "is-ok");
      if (kind) msg.classList.add(kind);
    }
    function setPwMsg(text, kind) {
      if (!pwMsg) return;
      pwMsg.textContent = text || "";
      pwMsg.classList.remove("is-err", "is-ok");
      if (kind) pwMsg.classList.add(kind);
    }
    function showPasswordStep() {
      wrap.classList.add("is-password");
      wrap.classList.remove("is-done");
      if (panel) {
        panel.hidden = true;
        panel.classList.remove("is-open");
      }
      if (pwPanel) {
        pwPanel.hidden = false;
        pwPanel.removeAttribute("hidden");
        pwPanel.classList.add("is-open");
      }
      if (stepLbl) stepLbl.textContent = "Step 2";
      if (pw1) pw1.focus();
    }
    function showDoneStep(name, url) {
      wrap.classList.add("is-done");
      wrap.classList.remove("is-password");
      if (pwPanel) {
        pwPanel.hidden = true;
        pwPanel.classList.remove("is-open");
      }
      if (donePanel) {
        donePanel.hidden = false;
        donePanel.removeAttribute("hidden");
        donePanel.classList.add("is-open");
        var nEl = donePanel.querySelector("[data-done-name]");
        if (nEl) nEl.textContent = name || "Sailor";
      }
      if (wrap.__ssaDoneTimer) {
        try { clearTimeout(wrap.__ssaDoneTimer); } catch (_) {}
      }
      wrap.__ssaDoneTimer = setTimeout(function () {
        window.location.href = url || "/";
      }, 5000);
    }
    function readCode() {
      var out = "";
      codeBoxes.forEach(function (box) {
        out += digits(box.value).slice(0, 1);
      });
      return out;
    }
    function fillBoxes(val) {
      var d = digits(val).slice(0, 4).split("");
      codeBoxes.forEach(function (box, i) {
        box.value = d[i] || "";
      });
    }
    function clearBoxes() {
      codeBoxes.forEach(function (box) {
        box.value = "";
        box.disabled = false;
      });
    }
    function setBoxesDisabled(on) {
      codeBoxes.forEach(function (box) {
        box.disabled = !!on;
      });
    }
    function focusBox(i) {
      if (codeBoxes[i]) codeBoxes[i].focus();
    }
    function pickMethod(el) {
      if (!signupCard) return;
      signupCard.classList.add("is-method-picked");
      signupCard.querySelectorAll(".sa-looked-auth").forEach(function (a) {
        a.classList.toggle("is-chosen", a === el);
      });
    }
    wrap.querySelectorAll(".sa-looked-auth").forEach(function (el) {
      el.addEventListener("click", function (e) {
        e.stopPropagation();
        pickMethod(el);
        if (!el.hasAttribute("data-wa-open")) return;
        e.preventDefault();
        if (!panel) return;
        panel.hidden = false;
        panel.classList.add("is-open");
        if (phoneStep) phoneStep.hidden = false;
        if (codeStep) codeStep.hidden = true;
        if (phone) phone.focus();
      });
    });
    function sailorPayload() {
      var info = wrap.__ssaClaimInfo || {};
      return {
        sas_id: info.sid || "",
        slug: info.slug || "",
        whatsapp: digits(phone && phone.value)
      };
    }
    if (sendBtn) {
      sendBtn.addEventListener("click", function (e) {
        e.stopPropagation();
        var n = digits(phone && phone.value);
        if (n.length !== 10 || n.charAt(0) !== "0") {
          setMsg("Enter a 10-digit WhatsApp number starting with 0", "is-err");
          return;
        }
        sendBtn.disabled = true;
        setMsg("Sending code…");
        fetch("/api/claim/whatsapp/send-code", {
          method: "POST",
          credentials: "same-origin",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(sailorPayload())
        })
          .then(function (r) { return r.json(); })
          .then(function (d) {
            sendBtn.disabled = false;
            if (!d || d.error) {
              setMsg((d && d.error) || "Could not send code", "is-err");
              return;
            }
            if (d.sas_id) {
              wrap.__ssaClaimInfo = wrap.__ssaClaimInfo || {};
              wrap.__ssaClaimInfo.sid = String(d.sas_id);
            }
            if (phoneStep) phoneStep.hidden = true;
            if (codeStep) codeStep.hidden = false;
            clearBoxes();
            focusBox(0);
            setMsg("Code sent on WhatsApp. Enter the 4 digits.", "is-ok");
          })
          .catch(function () {
            sendBtn.disabled = false;
            setMsg("Could not send code", "is-err");
          });
      });
    }
    function keepSession(token) {
      if (!token) return;
      try { localStorage.setItem("session", token); } catch (err) {}
      document.cookie = "session=" + encodeURIComponent(token) + "; path=/; max-age=" + 30 * 24 * 60 * 60 + "; SameSite=Lax";
    }
    if (pwSave) {
      pwSave.addEventListener("click", function (e) {
        e.stopPropagation();
        var a = pw1 ? String(pw1.value || "") : "";
        var b = pw2 ? String(pw2.value || "") : "";
        if (a.length < 6) {
          setPwMsg("Password must be at least 6 characters", "is-err");
          return;
        }
        if (a !== b) {
          setPwMsg("Passwords do not match", "is-err");
          return;
        }
        pwSave.disabled = true;
        setPwMsg("Saving…");
        var info = wrap.__ssaClaimInfo || {};
        fetch("/api/claim/whatsapp/set-password", {
          method: "POST",
          credentials: "same-origin",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            sas_id: info.sid || "",
            slug: info.slug || "",
            session_token: info.session || "",
            password: a,
            confirm: b
          })
        })
          .then(function (r) { return r.json(); })
          .then(function (d) {
            pwSave.disabled = false;
            if (!d || d.error) {
              setPwMsg((d && d.error) || "Could not save password", "is-err");
              return;
            }
            var name = (d && d.name) || info.name || "Sailor";
            var slug = (d && d.slug) || info.slug || "";
            var url = (d && d.profile_url) || info.profile_url || (slug ? "/sailor/" + slug : "/");
            showDoneStep(name, url);
          })
          .catch(function () {
            pwSave.disabled = false;
            setPwMsg("Could not save password", "is-err");
          });
      });
    }
    function verifyCode() {
      if (verifying) return;
      var c = readCode();
      if (c.length !== 4) return;
      verifying = true;
      setBoxesDisabled(true);
      setMsg("Checking code…");
      var body = sailorPayload();
      body.code = c;
      fetch("/api/claim/whatsapp/verify-code", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      })
        .then(function (r) { return r.json(); })
        .then(function (d) {
          if (!d || d.error) {
            verifying = false;
            setBoxesDisabled(false);
            clearBoxes();
            focusBox(0);
            setMsg((d && d.error) || "Code not accepted", "is-err");
            return;
          }
          keepSession(d.session_token || d.session);
          wrap.__ssaClaimInfo = wrap.__ssaClaimInfo || {};
          if (d.sas_id) wrap.__ssaClaimInfo.sid = String(d.sas_id);
          if (d.slug) wrap.__ssaClaimInfo.slug = d.slug;
          if (d.name) wrap.__ssaClaimInfo.name = d.name;
          wrap.__ssaClaimInfo.profile_url = d.profile_url || wrap.__ssaClaimInfo.profile_url;
          wrap.__ssaClaimInfo.session = d.session_token || d.session || wrap.__ssaClaimInfo.session;
          showPasswordStep();
        })
        .catch(function () {
          verifying = false;
          setBoxesDisabled(false);
          focusBox(0);
          setMsg("Code not accepted", "is-err");
        });
    }
    codeBoxes.forEach(function (box, idx) {
      box.addEventListener("input", function () {
        var extra = digits(box.value);
        if (!extra) { box.value = ""; return; }
        if (extra.length > 1) {
          fillBoxes((readCode().slice(0, idx) + extra).slice(0, 4));
          if (readCode().length === 4) verifyCode();
          else focusBox(Math.min(idx + extra.length, 3));
          return;
        }
        box.value = extra.slice(0, 1);
        if (idx < 3) focusBox(idx + 1);
        if (readCode().length === 4) verifyCode();
      });
      box.addEventListener("keydown", function (e) {
        if (e.key === "Backspace" && !digits(box.value) && idx > 0) {
          e.preventDefault();
          codeBoxes[idx - 1].value = "";
          focusBox(idx - 1);
        }
      });
      box.addEventListener("paste", function (e) {
        var text = (e.clipboardData && e.clipboardData.getData("text")) || "";
        var d = digits(text).slice(0, 4);
        if (!d) return;
        e.preventDefault();
        fillBoxes(d);
        if (d.length === 4) verifyCode();
        else focusBox(d.length);
      });
    });
  }

  function fillFromResults(wrap, profile) {
    if (!profile.sid) return;
    fetch("/api/member/" + encodeURIComponent(profile.sid) + "/results", { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) {
        var rows = (d && d.results) || [];
        var events = rows.filter(function (r) { return r && r.regatta_id && !isSeries(r); });
        var seen = {};
        var unique = [];
        events.forEach(function (r) {
          if (seen[r.regatta_id]) return;
          seen[r.regatta_id] = true;
          unique.push(r);
        });
        unique.sort(function (a, b) {
          return String(b.end_date || b.start_date || "").localeCompare(String(a.end_date || a.start_date || ""));
        });
        var last2 = unique.slice(0, 2);
        var list = wrap.querySelector("[data-ssa-events-list]");
        var host = wrap.querySelector("[data-ssa-events]");
        if (list) {
          if (!last2.length) {
            if (host) host.setAttribute("data-empty", "1");
            list.textContent = "No recent events";
          } else {
            if (host) host.removeAttribute("data-empty");
            list.innerHTML = last2.map(eventRowHtml).join("");
          }
        }
        var totalEl = wrap.querySelector("[data-ssa-event-total]");
        var nReg = unique.length;
        if (totalEl && (profile.regattas === "" || profile.regattas == null || profile.regattas === "—")) {
          totalEl.textContent = String(nReg);
        } else if (totalEl && profile.regattas) {
          totalEl.textContent = String(profile.regattas);
        }
        if (!profile.regattas) {
          var rg = wrap.querySelector("[data-ssa-regattas]");
          if (rg) rg.textContent = String(nReg || "—");
        }
        if (!profile.races) {
          var rc = wrap.querySelector("[data-ssa-races]");
          var nRace = rows.reduce(function (sum, r) { return sum + raceCount(r); }, 0);
          if (rc) rc.textContent = String(nRace || "—");
        }
        if (!profile.gold && !profile.silver && !profile.bronze) {
          var g = 0, s = 0, b = 0;
          unique.forEach(function (r) {
            if (r.rank === 1) g += 1;
            else if (r.rank === 2) s += 1;
            else if (r.rank === 3) b += 1;
          });
          var medals = wrap.querySelectorAll(".sa-looked-medal-n");
          if (medals[0]) medals[0].textContent = String(g);
          if (medals[1]) medals[1].textContent = String(s);
          if (medals[2]) medals[2].textContent = String(b);
          var rateEl = wrap.querySelector("[data-ssa-medal-rate]");
          if (rateEl && nReg) rateEl.textContent = Math.round(100 * (g + s + b) / nReg) + "%";
        }
        if (!profile.classes || !profile.classes.length) {
          var counts = {};
          unique.forEach(function (r) {
            var name = r.class_canonical || r.class_original || "";
            if (!name) return;
            if (!counts[name]) counts[name] = { n: 0, src: r.class_logo_url, alt: name };
            counts[name].n += 1;
            if (r.class_logo_url) counts[name].src = r.class_logo_url;
          });
          var listC = Object.keys(counts).map(function (name) {
            return {
              name: name,
              n: counts[name].n,
              src: classLogoUrl(name, counts[name].src),
              alt: name,
              href: "/class/" + classSlug(name)
            };
          }).sort(function (a, b) { return b.n - a.n; });
          var ch = wrap.querySelector("[data-ssa-classes-host]");
          if (ch) ch.innerHTML = classesHtml(listC);
        }
      })
      .catch(function () {
        var list = wrap.querySelector("[data-ssa-events-list]");
        var host = wrap.querySelector("[data-ssa-events]");
        if (host) host.setAttribute("data-empty", "1");
        if (list) list.textContent = "Could not load events";
      });
  }

  function closeModal() {
    var overlay = document.getElementById("ssa-claim-modal");
    if (overlay) {
      overlay.classList.remove("is-open");
      overlay.hidden = true;
      overlay.setAttribute("aria-hidden", "true");
      var wrap = overlay.querySelector(".lab-card-wrap");
      if (wrap) showPreview(wrap);
    }
    document.querySelectorAll(".ssa-dev1-inject.is-claim-popup-open").forEach(function (el) {
      el.classList.remove("is-claim-popup-open");
    });
    try {
      document.body.classList.remove("ssa-claim-modal-open");
      document.body.style.overflow = prevOverflow || "";
    } catch (_) {}
  }

  function onKey(e) {
    if (e.key === "Escape") closeModal();
  }

  function ensureModal() {
    var overlay = document.getElementById("ssa-claim-modal");
    if (overlay) return overlay;
    overlay = document.createElement("div");
    overlay.id = "ssa-claim-modal";
    overlay.hidden = true;
    overlay.setAttribute("aria-hidden", "true");
    overlay.innerHTML =
      '<div class="ssa-claim-modal-backdrop" data-ssa-quit></div>' +
      '<div class="ssa-claim-modal-panel" role="dialog" aria-modal="true" aria-label="Claim sailing profile">' +
        '<div class="lab-card-wrap" data-ssa-claim-wrap></div>' +
      "</div>";
    document.body.appendChild(overlay);
    overlay.addEventListener("click", function (e) {
      var quit = e.target && e.target.closest ? e.target.closest("[data-ssa-quit]") : null;
      if (quit) {
        e.preventDefault();
        closeModal();
      }
    });
    overlay.querySelector(".ssa-claim-modal-panel").addEventListener("click", function (e) {
      if (e.target && e.target.getAttribute && e.target.getAttribute("data-ssa-quit") != null) return;
      e.stopPropagation();
    });
    return overlay;
  }

  function openModal(slot, info) {
    injectCss();
    scrubListSlot(slot);
    var profile = extractProfile(slot, info);
    try { window.__ssaClaimSailor = { sid: profile.sid || "", name: profile.name || "" }; } catch (_) {}
    var overlay = ensureModal();
    var wrap = overlay.querySelector("[data-ssa-claim-wrap]");
    wrap.innerHTML = cardHtml(profile);
    wrap.__ssaClaimInfo = { sid: profile.sid, name: profile.name, slug: profile.slug };
    wrap.querySelectorAll("[data-ssa-claim-ext]").forEach(function (a) {
      a.setAttribute("href", extHref(a.getAttribute("data-ssa-claim-ext"), wrap.__ssaClaimInfo));
    });
    showPreview(wrap);
    wireSignup(wrap);
    var claimBtn = wrap.querySelector("[data-ssa-modal-claim]");
    if (claimBtn) {
      claimBtn.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        showStep1(wrap);
      });
    }
    fillFromResults(wrap, profile);
    document.querySelectorAll(".ssa-dev1-inject.is-claim-popup-open").forEach(function (el) {
      el.classList.remove("is-claim-popup-open");
    });
    if (slot) slot.classList.add("is-claim-popup-open");
    overlay.hidden = false;
    overlay.classList.add("is-open");
    overlay.setAttribute("aria-hidden", "false");
    try {
      document.body.classList.add("ssa-claim-modal-open");
      prevOverflow = document.body.style.overflow || "";
      document.body.style.overflow = "hidden";
    } catch (_) {}
    document.removeEventListener("keydown", onKey);
    document.addEventListener("keydown", onKey);
  }

  function scrubListSlot(slot) {
    if (!slot) return;
    slot.classList.remove("is-step1");
    var extra = slot.querySelector(":scope > .sa-looked-signup, .sa-approved-sailor-card > .sa-looked-signup");
    if (!extra) extra = slot.querySelector(".sa-looked-signup");
    if (extra && extra.parentNode && !extra.closest("#ssa-claim-modal")) extra.parentNode.removeChild(extra);
  }

  function neutralizeDev1Scale(slot) {
    var ban = slot && slot.querySelector("[data-ssa-list-claim], .ssa-popup-claim-slot .sa-looked-claim");
    if (!ban || !ban.style) return;
    ban.style.transform = "none";
    ban.style.transformOrigin = "center center";
    ban.style.top = "";
    ban.style.position = "";
  }

  function replaceLandingClaimBanner(root) {
    if (!root || !root.querySelector) return false;
    injectCss();
    var slotEl = root.querySelector("#dev1-claim-slot") || (root.id === "dev1-claim-slot" ? root : null);
    if (!slotEl) return false;
    var old = slotEl.querySelector("a.sa-claim-banner");
    if (!old) return false;
    slotEl.classList.add("ssa-popup-claim-slot");
    slotEl.innerHTML = '<div class="sa-looked-cta">' + CLAIM_INNER + "</div>";
    neutralizeDev1Scale(root);
    return true;
  }

  function killLegacyOverlay() {
    var old = document.getElementById("ssa-landing-claim-overlay");
    if (old && old.parentNode) old.parentNode.removeChild(old);
  }

  function mountLandingClaimPopup(slot, info) {
    if (!slot) return;
    injectCss();
    killLegacyOverlay();
    replaceLandingClaimBanner(slot);
    scrubListSlot(slot);
    neutralizeDev1Scale(slot);
    setTimeout(function () { neutralizeDev1Scale(slot); }, 60);
    setTimeout(function () { neutralizeDev1Scale(slot); }, 220);
    setTimeout(function () { neutralizeDev1Scale(slot); }, 520);
    var btn = slot.querySelector(".ssa-popup-claim-slot [data-ssa-list-claim]");
    if (!btn) return;
    if (btn.getAttribute("data-ssa-claim-wired") === "1") return;
    btn.setAttribute("data-ssa-claim-wired", "1");
    btn.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      if (e.stopImmediatePropagation) e.stopImmediatePropagation();
      openModal(slot, info);
    });
  }

  injectCss();
  killLegacyOverlay();

  window.replaceLandingClaimBanner = replaceLandingClaimBanner;
  window.mountLandingClaimPopup = mountLandingClaimPopup;
  window.openLandingClaimPopup = function (info) {
    var slot = null;
    if (info && info.sid) {
      slot = document.querySelector('.ssa-dev1-inject[data-sas-id="' + String(info.sid).replace(/"/g, "") + '"]');
    }
    slot = slot || document.querySelector(".ssa-dev1-inject");
    if (slot) openModal(slot, info);
  };
  window.closeLandingClaimPopup = closeModal;
  window.__ssaLandingClaimPopupVer = JS_VER;
})();
