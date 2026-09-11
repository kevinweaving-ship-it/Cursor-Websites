/* Landing /dev-1 claim slot: replace countdown banner with /pop-up claim card. */
(function () {
  if (window.__ssaLandingClaimPopup) return;
  window.__ssaLandingClaimPopup = true;

  var CSS_ID = "ssa-landing-claim-popup-css";
  var OVERLAY_ID = "ssa-landing-claim-overlay";

  var CLAIM_INNER =
    '<button type="button" class="sa-looked-claim" id="dev1-claim-banner" title="Claim your profile" aria-expanded="false" aria-controls="' + OVERLAY_ID + '">' +
      '<span class="sa-looked-claim-top">' +
        '<span class="sa-looked-claim-ask">Is this your sailing profile?</span>' +
        '<span class="sa-looked-claim-sub">Unlock your full results and stats</span>' +
      "</span>" +
      '<span class="sa-looked-claim-bar">' +
        '<span class="sa-looked-claim-txt">Claim my profile</span>' +
        '<span class="sa-looked-claim-go" aria-hidden="true">∨</span>' +
      "</span>" +
    "</button>";

  function injectCss() {
    if (document.getElementById(CSS_ID)) return;
    var s = document.createElement("style");
    s.id = CSS_ID;
    s.textContent = [
      "#dev1-claim-slot.ssa-popup-claim-slot{display:flex;justify-content:stretch;align-items:stretch;width:100%;height:100%;min-width:0;min-height:0;box-sizing:border-box;overflow:hidden;}",
      "#dev1-claim-slot.ssa-popup-claim-slot .sa-looked-cta{display:flex;flex-direction:column;width:100%;height:100%;max-width:100%;min-width:0;margin:0;padding:0;box-sizing:border-box;border:1px solid #c4a26f;border-radius:12px;overflow:hidden;background:#fefaf5;}",
      "#dev1-claim-slot.ssa-popup-claim-slot .sa-looked-claim{display:flex!important;flex-direction:column;align-items:stretch;justify-content:flex-start;width:100%!important;height:100%!important;max-width:100%!important;margin:0;padding:0;box-sizing:border-box;background:transparent;border:0;text-decoration:none;color:inherit;line-height:1;cursor:pointer;font:inherit;transform:none!important;}",
      "#dev1-claim-slot.ssa-popup-claim-slot .sa-looked-claim-top{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3px;flex:1 1 auto;width:100%;margin:0;padding:8px 8px 7px;box-sizing:border-box;background:#fefaf5;text-align:center;min-height:0;}",
      "#dev1-claim-slot.ssa-popup-claim-slot .sa-looked-claim-ask{margin:0;padding:0;font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;font-weight:800;font-size:13px;line-height:1.15;color:#0a2351;letter-spacing:-0.01em;}",
      "#dev1-claim-slot.ssa-popup-claim-slot .sa-looked-claim-sub{margin:0;padding:0;font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;font-weight:500;font-size:11px;line-height:1.2;color:#0a2351;}",
      "#dev1-claim-slot.ssa-popup-claim-slot .sa-looked-claim-bar{display:flex;flex-direction:row;align-items:center;justify-content:center;gap:8px;flex:0 0 auto;width:100%;margin:0;padding:9px 32px 9px 10px;box-sizing:border-box;background:#0a2351;position:relative;}",
      "#dev1-claim-slot.ssa-popup-claim-slot .sa-looked-claim-txt{flex:1 1 auto;min-width:0;font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;font-weight:800;font-size:11px;line-height:1;color:#fff;text-transform:uppercase;letter-spacing:.04em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;text-align:center;}",
      "#dev1-claim-slot.ssa-popup-claim-slot .sa-looked-claim-go{position:absolute;right:8px;top:50%;transform:translateY(-50%);flex:0 0 auto;width:18px;height:18px;border-radius:999px;background:#c4a26f;color:#0a2351;display:inline-flex;align-items:center;justify-content:center;font-size:12px;font-weight:900;line-height:1;box-sizing:border-box;}",
      "#" + OVERLAY_ID + "{display:none;position:fixed;inset:0;z-index:120000;align-items:center;justify-content:center;padding:16px;box-sizing:border-box;}",
      "#" + OVERLAY_ID + ".is-open{display:flex;}",
      "#" + OVERLAY_ID + " .ssa-claim-pop-back{position:absolute;inset:0;background:rgba(10,35,81,.45);}",
      "#" + OVERLAY_ID + " .ssa-claim-pop-panel{position:relative;z-index:1;width:100%;max-width:340px;max-height:calc(100dvh - 32px);overflow:auto;}",
      "#" + OVERLAY_ID + " .sa-looked-signup{display:block;width:100%;margin:0;padding:0;box-sizing:border-box;}",
      "#" + OVERLAY_ID + " .sa-looked-signup-card{display:flex;flex-direction:column;align-items:stretch;gap:10px;width:100%;margin:0;padding:12px 10px;box-sizing:border-box;background:#0a2351;border:1px solid #142b5f;border-radius:12px;}",
      "#" + OVERLAY_ID + " .sa-looked-signup-step-lbl{display:block;margin:0;font-size:11px;font-weight:900;letter-spacing:.08em;text-transform:uppercase;color:#c4a26f;text-align:center;}",
      "#" + OVERLAY_ID + " .sa-looked-signup-welcome{display:block;margin:2px 0 0;font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;font-size:15px;font-weight:800;line-height:1.2;color:#fff;text-align:center;}",
      "#" + OVERLAY_ID + " .sa-looked-signup-welcome-name{color:#c4a26f;}",
      "#" + OVERLAY_ID + " .sa-looked-signup-choose{display:block;margin:0 0 2px;font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;font-size:12px;font-weight:600;line-height:1.25;color:rgba(255,255,255,.88);text-align:center;}",
      "#" + OVERLAY_ID + " .sa-looked-auth{display:flex;flex-direction:row;align-items:center;gap:10px;width:100%;margin:0;padding:8px 10px;box-sizing:border-box;border-radius:999px;border:3px solid transparent;text-decoration:none;cursor:pointer;font:inherit;line-height:1;appearance:none;-webkit-appearance:none;background:transparent;}",
      "#" + OVERLAY_ID + " .sa-looked-auth-ico{flex:0 0 auto;width:22px;height:22px;display:inline-flex;align-items:center;justify-content:center;}",
      "#" + OVERLAY_ID + " .sa-looked-auth-ico svg{display:block;width:22px;height:22px;}",
      "#" + OVERLAY_ID + " .sa-looked-auth-txt{flex:1 1 auto;min-width:0;font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;font-weight:800;font-size:13px;line-height:1.1;text-align:center;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}",
      "#" + OVERLAY_ID + " .sa-looked-auth-go{flex:0 0 auto;width:22px;height:22px;border-radius:999px;background:#0a2351;color:#fff;display:inline-flex;align-items:center;justify-content:center;font-size:14px;font-weight:900;line-height:1;}",
      "#" + OVERLAY_ID + " .sa-looked-auth--google{background:#fff;border-color:#c4a26f;color:#0a2351;}",
      "#" + OVERLAY_ID + " .sa-looked-auth--google .sa-looked-auth-txt{color:#0a2351;}",
      "#" + OVERLAY_ID + " .sa-looked-auth--facebook{background:#1877f2;border-color:#0f5ecf;color:#fff;}",
      "#" + OVERLAY_ID + " .sa-looked-auth--facebook .sa-looked-auth-txt{color:#fff;}",
      "#" + OVERLAY_ID + " .sa-looked-auth--email{background:#0a2351;border:1.5px solid #e2e8f0;color:#fff;padding:10px 14px;}",
      "#" + OVERLAY_ID + " .sa-looked-auth--email .sa-looked-auth-txt{color:#fff;}",
      "#" + OVERLAY_ID + " .sa-looked-auth--email .sa-looked-auth-go{display:none;}",
      "#" + OVERLAY_ID + " .sa-looked-auth--whatsapp{background:#25D366;border-color:#128C7E;color:#fff;}",
      "#" + OVERLAY_ID + " .sa-looked-auth--whatsapp .sa-looked-auth-txt{color:#fff;}",
      "#" + OVERLAY_ID + " .sa-looked-auth--whatsapp .sa-looked-auth-go{background:#075E54;color:#fff;}",
      "#" + OVERLAY_ID + " .sa-looked-signup-card.is-method-picked .sa-looked-auth:not(.is-chosen){display:none;}",
      "#" + OVERLAY_ID + " .sa-looked-wa{display:none;flex-direction:column;gap:8px;width:100%;margin:2px 0 0;}",
      "#" + OVERLAY_ID + " .sa-looked-wa.is-open{display:flex;}",
      "#" + OVERLAY_ID + " .sa-looked-wa-phone-step,#" + OVERLAY_ID + " .sa-looked-wa-code-step{display:flex;flex-direction:column;gap:8px;width:100%;}",
      "#" + OVERLAY_ID + " .sa-looked-wa-phone-step[hidden],#" + OVERLAY_ID + " .sa-looked-wa-code-step[hidden]{display:none!important;}",
      "#" + OVERLAY_ID + " .sa-looked-wa-label{margin:0;font-size:11px;font-weight:800;letter-spacing:.06em;text-transform:uppercase;color:#c4a26f;text-align:center;}",
      "#" + OVERLAY_ID + " .sa-looked-wa-input{width:100%;box-sizing:border-box;margin:0;padding:10px 12px;border-radius:999px;border:1.5px solid #e2e8f0;background:#fff;color:#0a2351;font:inherit;font-size:15px;font-weight:700;text-align:center;}",
      "#" + OVERLAY_ID + " .sa-looked-wa-send{width:100%;margin:0;padding:10px 12px;border:0;border-radius:999px;background:#25D366;color:#fff;font:inherit;font-size:13px;font-weight:800;cursor:pointer;}",
      "#" + OVERLAY_ID + " .sa-looked-wa-boxes{display:flex;flex-direction:row;justify-content:stretch;align-items:stretch;gap:6px;width:100%;box-sizing:border-box;}",
      "#" + OVERLAY_ID + " .sa-looked-wa-box{flex:1 1 0;width:0;min-width:0;height:38px;min-height:38px;box-sizing:border-box;margin:0;padding:0;border-radius:10px;border:1.5px solid #e2e8f0;background:#fff;color:#0a2351;font:inherit;font-size:18px;font-weight:800;line-height:36px;text-align:center;appearance:none;-webkit-appearance:none;}",
      "#" + OVERLAY_ID + " .sa-looked-wa-box:focus{outline:none;border-color:#25D366;}",
      "#" + OVERLAY_ID + " .sa-looked-wa-msg{margin:0;min-height:1.2em;font-size:12px;font-weight:600;line-height:1.3;color:#fff;text-align:center;}",
      "#" + OVERLAY_ID + " .sa-looked-wa-msg.is-err{color:#fecaca;}",
      "#" + OVERLAY_ID + " .sa-looked-wa-msg.is-ok{color:#bbf7d0;}",
      "#" + OVERLAY_ID + " .ssa-claim-pop-close{position:absolute;top:8px;right:10px;z-index:2;width:28px;height:28px;border:0;border-radius:999px;background:rgba(255,255,255,.12);color:#fff;font-size:18px;line-height:1;cursor:pointer;}"
    ].join("");
    document.head.appendChild(s);
  }

  function overlayHtml() {
    return (
      '<div class="ssa-claim-pop-back" data-ssa-claim-close="1"></div>' +
      '<div class="ssa-claim-pop-panel" role="dialog" aria-modal="true" aria-labelledby="ssa-claim-pop-welcome">' +
        '<button type="button" class="ssa-claim-pop-close" data-ssa-claim-close="1" aria-label="Close">×</button>' +
        '<div class="sa-looked-signup is-open">' +
          '<div class="sa-looked-signup-card">' +
            '<span class="sa-looked-signup-step-lbl">Step 1</span>' +
            '<span class="sa-looked-signup-welcome" id="ssa-claim-pop-welcome">Welcome <span class="sa-looked-signup-welcome-name" data-ssa-claim-name>Sailor</span></span>' +
            '<span class="sa-looked-signup-choose">Please choose method to register</span>' +
            '<button type="button" class="sa-looked-auth sa-looked-auth--whatsapp" data-wa-open>' +
              '<span class="sa-looked-auth-ico" aria-hidden="true"><svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path fill="#fff" d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.435 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg></span>' +
              '<span class="sa-looked-auth-txt">Signup With</span>' +
              '<span class="sa-looked-auth-go" aria-hidden="true">›</span>' +
            "</button>" +
            '<a class="sa-looked-auth sa-looked-auth--google" data-ssa-claim-ext="google" href="/signup.html?signup=1&amp;provider=google&amp;from=claim">' +
              '<span class="sa-looked-auth-ico" aria-hidden="true"><svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg></span>' +
              '<span class="sa-looked-auth-txt">Sign up with Google</span>' +
              '<span class="sa-looked-auth-go" aria-hidden="true">›</span>' +
            "</a>" +
            '<a class="sa-looked-auth sa-looked-auth--facebook" data-ssa-claim-ext="facebook" href="/signup.html?signup=1&amp;provider=facebook&amp;from=claim">' +
              '<span class="sa-looked-auth-ico" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="12" cy="12" r="12" fill="white"/><path d="M13.44 20V13.44H15.64L15.97 10.88H13.44V9.24C13.44 8.5 13.64 8 14.7 8H16V5.72C15.37 5.63 14.74 5.59 14.1 5.6C12.21 5.6 10.92 6.75 10.92 8.86V10.88H8.8V13.44H10.92V20H13.44Z" fill="#1877F2"/></svg></span>' +
              '<span class="sa-looked-auth-txt">Sign up with Facebook</span>' +
              '<span class="sa-looked-auth-go" aria-hidden="true">›</span>' +
            "</a>" +
            '<a class="sa-looked-auth sa-looked-auth--email" data-ssa-claim-ext="email" href="/signup.html?signup=1&amp;provider=email&amp;from=claim">' +
              '<span class="sa-looked-auth-ico" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M4 6.5H20C20.83 6.5 21.5 7.17 21.5 8V16C21.5 16.83 20.83 17.5 20 17.5H4C3.17 17.5 2.5 16.83 2.5 16V8C2.5 7.17 3.17 6.5 4 6.5Z" stroke="#fff" stroke-width="1.8"/><path d="M3 8L12 14L21 8" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></span>' +
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
          "</div>" +
        "</div>" +
      "</div>"
    );
  }

  function digits(v) {
    return String(v || "").replace(/\D/g, "");
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

  function resetWa(overlay) {
    var card = overlay.querySelector(".sa-looked-signup-card");
    var panel = overlay.querySelector("[data-wa-panel]");
    var phoneStep = overlay.querySelector("[data-wa-phone-step]");
    var codeStep = overlay.querySelector("[data-wa-code-step]");
    var phone = overlay.querySelector("[data-wa-phone]");
    var msg = overlay.querySelector("[data-wa-msg]");
    if (card) card.classList.remove("is-method-picked");
    overlay.querySelectorAll(".sa-looked-auth").forEach(function (a) {
      a.classList.remove("is-chosen");
    });
    if (panel) {
      panel.hidden = true;
      panel.classList.remove("is-open");
    }
    if (phoneStep) phoneStep.hidden = false;
    if (codeStep) codeStep.hidden = true;
    if (phone) phone.value = "";
    overlay.querySelectorAll("[data-wa-digit]").forEach(function (box) {
      box.value = "";
      box.disabled = false;
    });
    if (msg) {
      msg.textContent = "";
      msg.classList.remove("is-err", "is-ok");
    }
  }

  function closeOverlay() {
    var overlay = document.getElementById(OVERLAY_ID);
    if (!overlay) return;
    overlay.classList.remove("is-open");
    overlay.setAttribute("hidden", "");
    document.body.style.removeProperty("overflow");
    resetWa(overlay);
  }

  function openOverlay(info) {
    ensureOverlay();
    var overlay = document.getElementById(OVERLAY_ID);
    if (!overlay) return;
    overlay.__ssaClaimInfo = info || {};
    var nameEl = overlay.querySelector("[data-ssa-claim-name]");
    if (nameEl) nameEl.textContent = (info && info.name) || "Sailor";
    overlay.querySelectorAll("[data-ssa-claim-ext]").forEach(function (a) {
      a.setAttribute("href", extHref(a.getAttribute("data-ssa-claim-ext"), info));
    });
    resetWa(overlay);
    overlay.removeAttribute("hidden");
    overlay.classList.add("is-open");
    document.body.style.overflow = "hidden";
  }

  function wireOverlay(overlay) {
    if (overlay.getAttribute("data-wired") === "1") return;
    overlay.setAttribute("data-wired", "1");
    overlay.addEventListener("click", function (e) {
      var t = e.target;
      if (t && t.closest && t.closest("[data-ssa-claim-close]")) {
        e.preventDefault();
        closeOverlay();
      }
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && overlay.classList.contains("is-open")) closeOverlay();
    });

    var signupCard = overlay.querySelector(".sa-looked-signup-card");
    var panel = overlay.querySelector("[data-wa-panel]");
    var phoneStep = overlay.querySelector("[data-wa-phone-step]");
    var codeStep = overlay.querySelector("[data-wa-code-step]");
    var phone = overlay.querySelector("[data-wa-phone]");
    var sendBtn = overlay.querySelector("[data-wa-send]");
    var codeBoxes = overlay.querySelectorAll("[data-wa-digit]");
    var msg = overlay.querySelector("[data-wa-msg]");
    var verifying = false;

    function setMsg(text, kind) {
      if (!msg) return;
      msg.textContent = text || "";
      msg.classList.remove("is-err", "is-ok");
      if (kind) msg.classList.add(kind);
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
    overlay.querySelectorAll(".sa-looked-auth").forEach(function (el) {
      el.addEventListener("click", function (e) {
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
      var info = overlay.__ssaClaimInfo || {};
      return {
        sas_id: info.sid || "",
        slug: info.slug || "",
        whatsapp: digits(phone && phone.value)
      };
    }
    if (sendBtn) {
      sendBtn.addEventListener("click", function () {
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
          .then(function (r) {
            return r.json();
          })
          .then(function (d) {
            sendBtn.disabled = false;
            if (!d || d.error) {
              setMsg((d && d.error) || "Could not send code", "is-err");
              return;
            }
            if (d.sas_id) {
              overlay.__ssaClaimInfo = overlay.__ssaClaimInfo || {};
              overlay.__ssaClaimInfo.sid = String(d.sas_id);
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
      try {
        localStorage.setItem("session", token);
      } catch (err) {}
      document.cookie =
        "session=" + encodeURIComponent(token) + "; path=/; max-age=" + 30 * 24 * 60 * 60 + "; SameSite=Lax";
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
        .then(function (r) {
          return r.json();
        })
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
          setMsg("Profile claimed. Opening your sailor page…", "is-ok");
          var slug = (d && d.slug) || (overlay.__ssaClaimInfo && overlay.__ssaClaimInfo.slug) || "";
          var url = (d && d.profile_url) || (slug ? "/sailor/" + slug : "/");
          window.location.href = url;
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
        if (!extra) {
          box.value = "";
          return;
        }
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

  function ensureOverlay() {
    injectCss();
    var overlay = document.getElementById(OVERLAY_ID);
    if (!overlay) {
      overlay = document.createElement("div");
      overlay.id = OVERLAY_ID;
      overlay.setAttribute("hidden", "");
      overlay.innerHTML = overlayHtml();
      document.body.appendChild(overlay);
    }
    wireOverlay(overlay);
    return overlay;
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
    return true;
  }

  function mountLandingClaimPopup(slot, info) {
    if (!slot) return;
    injectCss();
    replaceLandingClaimBanner(slot);
    var btn = slot.querySelector("#dev1-claim-slot .sa-looked-claim");
    if (!btn) return;
    if (btn.getAttribute("data-ssa-claim-wired") === "1") return;
    btn.setAttribute("data-ssa-claim-wired", "1");
    btn.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      var live = info || {};
      if (!live.name) {
        var firstEl = slot.querySelector(".sa-approved-sailor-name-first");
        var lastEl = slot.querySelector(".sa-approved-sailor-name-last");
        live = {
          sid: live.sid || (slot.dataset && slot.dataset.sasId) || "",
          name: [firstEl && firstEl.textContent, lastEl && lastEl.textContent]
            .filter(Boolean)
            .join(" ")
            .replace(/\s+/g, " ")
            .trim()
        };
      }
      try {
        window.__ssaClaimSailor = { sid: live.sid || "", name: live.name || "" };
      } catch (_) {}
      openOverlay(live);
    });
  }

  window.replaceLandingClaimBanner = replaceLandingClaimBanner;
  window.mountLandingClaimPopup = mountLandingClaimPopup;
  window.openLandingClaimPopup = openOverlay;
  window.closeLandingClaimPopup = closeOverlay;
})();
