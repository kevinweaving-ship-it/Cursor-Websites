/* Cape Classic slot: Voelklip wind dial + Wind2Speed Zeekoevlei (station 35).
   Dial copied from live /voelklip/index.html.bak_shared_202609070100:
   72-tick compass, 16-point history marks (not min–max blob), inward FROM arrow,
   BANDS colours on arc/arrow/values. */
(function () {
  var CSS_ID = "ssa-regatta-slot-card-css";
  var ROOT_ID = "ssa-regatta-slot-card";
  var CAPE_CLASSIC_ID = "2026-09-13-zvyc-cape-classic";
  var JS_VER = "20260912wa4";
  var WA_FEED = "/js/event-whatsapp-live.json";
  var WA_ICON = '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="#25D366" d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.435 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413Z"/></svg>';
  var PTS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"];
  var BANDS = [[0, 5, "#12b028"], [5, 11, "#2563eb"], [11, 17, "#e67e00"], [17, 23, "#7c3aed"], [23, 60, "#DC143C"]];

  function injectCss() {
    var s = document.getElementById(CSS_ID);
    if (!s) {
      s = document.createElement("style");
      s.id = CSS_ID;
      document.head.appendChild(s);
    }
    s.textContent = [
      ".regatta-page:has(#ssa-regatta-slot-card)>.regatta-header-wrap .header{margin-bottom:0!important;}",
      ".ssa-regatta-slot-card{position:relative;display:flex;width:100%;order:2;align-self:start;margin:10px 0 0;padding:0;box-sizing:border-box;height:122px!important;min-height:122px!important;max-height:122px!important;flex:0 0 122px!important;background:#fff;border:1.5px solid #1a2750;border-radius:8px;box-shadow:0 1px 3px rgba(0,31,63,.08);overflow:hidden;}",
      ".regatta-page:has(.mm-lipton-reels--expanded) .ssa-regatta-slot-card{height:122px!important;min-height:122px!important;max-height:122px!important;flex:0 0 122px!important;align-self:start!important;}",
      ".ssa-regatta-slot-card .wx-wp-top{display:flex;align-items:stretch;flex:1;height:100%;width:100%;padding:0 6px 0 0;gap:4px;box-sizing:border-box;}",
      ".ssa-regatta-slot-card .wx-wp-comp{flex:0 0 122px;width:122px!important;height:122px!important;max-width:122px;max-height:122px;aspect-ratio:1/1;overflow:hidden;}",
      ".ssa-regatta-slot-card .wx-dial{display:block;width:100%;height:100%;overflow:visible;}",
      ".ssa-regatta-slot-card .wx-spark{flex:1 1 0;min-width:48px;height:100%;display:flex;flex-direction:column;padding:6px 2px 4px;box-sizing:border-box;min-height:0;}",
      ".ssa-regatta-slot-card .wx-spark-row{flex:1 1 auto;min-height:0;display:flex;align-items:stretch;gap:3px;}",
      ".ssa-regatta-slot-card .wx-scale{flex:0 0 16px;display:flex;flex-direction:column;justify-content:space-between;align-items:flex-end;padding:1px 0;box-sizing:border-box;}",
      ".ssa-regatta-slot-card .wx-scale span{font:700 9px/1 Arial,Helvetica,sans-serif;color:#64748b;}",
      ".ssa-regatta-slot-card .wx-plot{flex:1 1 auto;min-width:0;height:100%;display:block;}",
      ".ssa-regatta-slot-card .wx-spark-x{flex:0 0 auto;display:flex;justify-content:space-between;padding:2px 0 0 19px;}",
      ".ssa-regatta-slot-card .wx-spark-x span{font:700 9px/1 Arial,Helvetica,sans-serif;color:#64748b;}",
      ".ssa-regatta-slot-card .wx-info{flex:0 0 auto;min-width:118px;height:100%;display:flex;flex-direction:column;justify-content:stretch;gap:6px;padding:10px 8px 10px 4px;box-sizing:border-box;}",
      ".ssa-regatta-slot-card .wx-dial .dt{stroke:#9ca3af;stroke-width:1;}",
      ".ssa-regatta-slot-card .wx-dial .dt.card{stroke:#111;stroke-width:1.4;}",
      ".ssa-regatta-slot-card .wx-dial .darc{fill:none;stroke:#93c5fd;stroke-width:7;stroke-linecap:butt;}",
      ".ssa-regatta-slot-card .wx-dial .darc.prev{opacity:.45;}",
      ".ssa-regatta-slot-card .wx-dial .dhead{fill:#3b82f6;}",
      ".ssa-regatta-slot-card .wx-dial .dpt{font:700 24px Arial,Helvetica,sans-serif;fill:#15803d;}",
      ".ssa-regatta-slot-card .wx-dial .ddeg{font:700 18px Arial,Helvetica,sans-serif;fill:#166534;}",
      ".ssa-regatta-slot-card .wx-ir{flex:1 1 0;display:flex;flex-direction:row;justify-content:flex-end;align-items:baseline;gap:6px;min-width:0;min-height:0;}",
      ".ssa-regatta-slot-card .wx-il,.ssa-regatta-slot-card .wx-iv,.ssa-regatta-slot-card .wx-iv small{font:800 18px/1 Arial,Helvetica,sans-serif;white-space:nowrap;}",
      ".ssa-regatta-slot-card .wx-il{color:#334155;letter-spacing:0;text-transform:none;}",
      ".ssa-regatta-slot-card .wx-iv{color:#1a2750;text-align:right;}",
      ".ssa-regatta-slot-card .wx-iv small{margin-left:4px;color:inherit;}",
      ".ssa-regatta-slot-card .wx-wa-btn{position:absolute;top:2px;left:124px;z-index:6;width:44px;height:44px;margin:0;border:0;background:transparent;cursor:pointer;display:flex;align-items:flex-start;justify-content:flex-start;padding:2px 0 0 2px;box-sizing:border-box;-webkit-tap-highlight-color:transparent;}",
      ".ssa-regatta-slot-card .wx-wa-btn svg{width:14px;height:14px;display:block;filter:drop-shadow(0 1px 1px rgba(0,0,0,.28));}",
      ".ssa-regatta-slot-card .wx-wa-layer{display:none;position:absolute;inset:0;z-index:5;background:#ece5dd;overflow:auto;-webkit-overflow-scrolling:touch;padding:6px 8px;box-sizing:border-box;}",
      ".ssa-regatta-slot-card.ssa-wa-open .wx-wa-layer{display:block;}",
      ".ssa-regatta-slot-card.ssa-wa-off .wx-wa-btn,.ssa-regatta-slot-card.ssa-wa-off .wx-wa-layer{display:none!important;}",
      ".ssa-regatta-slot-card .wx-wa-row{display:flex;margin:0 0 4px;}",
      ".ssa-regatta-slot-card .wx-wa-row.is-out{justify-content:flex-end;}",
      ".ssa-regatta-slot-card .wx-wa-b{max-width:92%;border-radius:10px;padding:5px 7px 3px;font:600 11px/1.25 -apple-system,BlinkMacSystemFont,Arial,sans-serif;box-shadow:0 1px 0 rgba(0,0,0,.08);}",
      ".ssa-regatta-slot-card .wx-wa-row.is-in .wx-wa-b{background:#fff;color:#111;border-top-left-radius:3px;}",
      ".ssa-regatta-slot-card .wx-wa-row.is-out .wx-wa-b{background:#d9fdd3;color:#111;border-top-right-radius:3px;}",
      ".ssa-regatta-slot-card .wx-wa-who{display:block;font:700 10px/1.2 Arial,sans-serif;color:#075e54;margin:0 0 2px;}",
      ".ssa-regatta-slot-card .wx-wa-text{white-space:pre-wrap;word-break:break-word;}",
      ".ssa-regatta-slot-card .wx-wa-meta{display:block;text-align:right;font:500 9px/1 Arial,sans-serif;color:#667781;margin-top:2px;}",
      ".ssa-regatta-slot-card .wx-wa-empty{font:600 12px/1.3 Arial,sans-serif;color:#54656f;padding:18px 8px;}",
      ".ssa-regatta-slot-card .wx-wa-voice{display:flex;align-items:center;gap:5px;min-width:108px;}",
      ".ssa-regatta-slot-card .wx-wa-play{flex:0 0 20px;height:20px;border-radius:50%;background:#00a884;color:#fff;font:700 9px/20px Arial,sans-serif;text-align:center;}",
      ".ssa-regatta-slot-card .wx-wa-wave{flex:1 1 auto;height:14px;border-radius:2px;background:repeating-linear-gradient(90deg,#8696a0 0 1px,transparent 1px 3px);}",
      ".ssa-regatta-slot-card .wx-wa-dur{flex:0 0 auto;font:700 10px/1 Arial,sans-serif;color:#54656f;}",
      ".ssa-wa-gate{display:none;position:fixed;inset:0;z-index:4000;background:rgba(0,0,0,.55);align-items:center;justify-content:center;padding:20px;box-sizing:border-box;}",
      ".ssa-wa-gate.is-open{display:flex;}",
      ".ssa-wa-gate-card{background:#fff;border:1.5px solid #1a2750;border-radius:8px;padding:16px 18px;max-width:300px;width:100%;box-shadow:0 8px 28px rgba(0,0,0,.28);box-sizing:border-box;}",
      ".ssa-wa-gate-card p{margin:0 0 14px;font:600 14px/1.35 Arial,Helvetica,sans-serif;color:#1a2750;}",
      ".ssa-wa-gate-actions{display:flex;flex-direction:column;gap:8px;}",
      ".ssa-wa-gate-actions a,.ssa-wa-gate-actions button{display:flex;align-items:center;justify-content:center;min-height:44px;padding:10px 12px;border-radius:6px;font:700 14px/1.2 Arial,Helvetica,sans-serif;text-decoration:none;box-sizing:border-box;cursor:pointer;}",
      ".ssa-wa-gate-actions a.ssa-wa-gate-in{background:#1a2750;color:#fff;border:1px solid #1a2750;}",
      ".ssa-wa-gate-actions a.ssa-wa-gate-up{background:#e65100;color:#fff;border:1px solid #e65100;}",
      ".ssa-wa-gate-actions button{background:#fff;color:#1a2750;border:1px solid #1a2750;}",
      "@media screen and (orientation:portrait) and (max-width:767px){",
      ".ssa-regatta-slot-card{margin-top:10px;}",
      ".ssa-regatta-slot-card .wx-il,.ssa-regatta-slot-card .wx-iv,.ssa-regatta-slot-card .wx-iv small{font-size:17px;}",
      "}"
    ].join("");
  }

  function n1(x) {
    return x == null || isNaN(x) ? "—" : String(Math.round(Number(x) * 10) / 10);
  }
  function pol(cx, cy, r, a) {
    var t = (a - 90) * Math.PI / 180;
    return [cx + r * Math.cos(t), cy + r * Math.sin(t)];
  }
  function bandCol(kn) {
    if (kn == null || isNaN(kn)) return "#94a3b8";
    var i;
    for (i = 0; i < BANDS.length; i += 1) {
      if (kn < BANDS[i][1]) return BANDS[i][2];
    }
    return "#DC143C";
  }
  function dirIdx(deg) {
    if (deg == null || isNaN(deg)) return null;
    return Math.round((((Number(deg) % 360) + 360) % 360) / 22.5) % 16;
  }
  function recentIdx(data) {
    var last = dirIdx(data.wind_dir);
    var out = [];
    var wds = data.wds;
    var i;
    if (Array.isArray(wds)) {
      for (i = 0; i < wds.length && i < 16; i += 1) {
        if (Number(wds[i]) > 0) out.push(i);
      }
    }
    if (last != null && out.indexOf(last) === -1) out.push(last);
    return { last: last, uniq: out };
  }

  function drawDial(data) {
    var CX = 50, CY = 50, R = 44;
    var lastDeg = data.wind_dir;
    var rec = recentIdx(data);
    var dirLast = rec.last;
    var deg = lastDeg != null && !isNaN(lastDeg) ? Number(lastDeg) : (dirLast != null ? dirLast * 22.5 : null);
    var pt = data.wind_dir_name || (dirLast != null ? PTS[dirLast] : "");
    var col = bandCol(data.wind_kt);
    var svg = '<svg class="wx-dial" viewBox="-10 -10 120 120" aria-hidden="true">';
    var k;
    for (k = 0; k < 72; k += 1) {
      var card = k % 18 === 0;
      var q0 = pol(CX, CY, R - (card ? 7 : 4.5), k * 5);
      var q1 = pol(CX, CY, R + (card ? 2 : 0), k * 5);
      svg += '<line class="' + (card ? "dt card" : "dt") + '" x1="' + q0[0].toFixed(1) + '" y1="' + q0[1].toFixed(1) + '" x2="' + q1[0].toFixed(1) + '" y2="' + q1[1].toFixed(1) + '"/>';
    }
    if (dirLast != null) {
      rec.uniq.forEach(function (idx) {
        var a0 = idx * 22.5 - 11.25;
        var a1 = idx * 22.5 + 11.25;
        var p0 = pol(CX, CY, R - 2, a0);
        var p1 = pol(CX, CY, R - 2, a1);
        svg += '<path class="darc' + (idx === dirLast ? "" : " prev") + '" style="stroke:' + col + '" d="M' + p0[0].toFixed(1) + " " + p0[1].toFixed(1) + " A" + (R - 2) + " " + (R - 2) + " 0 0 1 " + p1[0].toFixed(1) + " " + p1[1].toFixed(1) + '"/>';
      });
      if (deg != null) {
        var hp = pol(CX, CY, R + 4, deg);
        svg += '<g transform="translate(' + hp[0].toFixed(1) + " " + hp[1].toFixed(1) + ") rotate(" + (deg + 180) + ')"><path class="dhead" style="fill:' + col + '" d="M0 -14L11 7L0 2.5L-11 7Z"/></g>';
      }
    }
    svg += '<text class="dpt" x="50" y="45" text-anchor="middle" dominant-baseline="central">' + (pt || "—") + "</text>";
    if (deg != null) {
      svg += '<text class="ddeg" x="50" y="70" text-anchor="middle">' + Math.round(deg) + "°</text>";
    }
    svg += "</svg>";
    return svg;
  }

  function drawSpark(data) {
    var pts = (data.hour || []).filter(function (p) { return p && p.avg_kt != null && !isNaN(p.avg_kt); });
    var html = '<div class="wx-spark" aria-label="Wind last hour">';
    if (pts.length < 2) {
      return html + "</div>";
    }
    var W = 100, H = 100, i;
    var maxKn = 10;
    for (i = 0; i < pts.length; i += 1) {
      var hi = pts[i].high_kt != null ? Number(pts[i].high_kt) : Number(pts[i].avg_kt);
      if (hi > maxKn) maxKn = hi;
    }
    maxKn = Math.max(10, Math.ceil(maxKn / 5) * 5);
    var ticks = [];
    var step = maxKn <= 20 ? 5 : 10;
    for (i = maxKn; i >= 0; i -= step) ticks.push(i);
    function x(idx) { return (W * idx) / (pts.length - 1); }
    function y(kn) { return H * (1 - Math.max(0, Math.min(maxKn, Number(kn))) / maxKn); }
    var svg = '<svg class="wx-plot" viewBox="0 0 ' + W + " " + H + '" preserveAspectRatio="none" aria-hidden="true">';
    BANDS.forEach(function (b) {
      var y0 = y(Math.min(maxKn, b[1]));
      var y1 = y(Math.min(maxKn, b[0]));
      if (y1 <= y0) return;
      svg += '<rect x="0" y="' + y0.toFixed(1) + '" width="' + W + '" height="' + (y1 - y0).toFixed(1) + '" fill="' + b[2] + '" opacity=".22"/>';
    });
    ticks.forEach(function (t) {
      if (t === 0 || t === maxKn) return;
      var yy = y(t).toFixed(1);
      svg += '<line x1="0" y1="' + yy + '" x2="' + W + '" y2="' + yy + '" stroke="#fff" stroke-width="0.6" vector-effect="non-scaling-stroke"/>';
    });
    var highD = "", avgD = "";
    for (i = 0; i < pts.length; i += 1) {
      var xi = x(i).toFixed(1);
      avgD += (i ? "L" : "M") + xi + " " + y(pts[i].avg_kt).toFixed(1);
      highD += (i ? "L" : "M") + xi + " " + y(pts[i].high_kt != null ? pts[i].high_kt : pts[i].avg_kt).toFixed(1);
    }
    var last = pts[pts.length - 1];
    var area = highD + "L" + x(pts.length - 1).toFixed(1) + " " + H + "L0 " + H + "Z";
    svg += '<path d="' + area + '" fill="#1a2750" opacity=".12"/>';
    svg += '<path d="' + highD + '" fill="none" stroke="#64748b" stroke-width="1.4" stroke-dasharray="3 2" vector-effect="non-scaling-stroke"/>';
    svg += '<path d="' + avgD + '" fill="none" stroke="#1a2750" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke"/>';
    svg += '<circle cx="' + x(pts.length - 1).toFixed(1) + '" cy="' + y(last.avg_kt).toFixed(1) + '" r="1.8" fill="' + bandCol(last.avg_kt) + '" vector-effect="non-scaling-stroke"/>';
    svg += "</svg>";
    var scale = '<div class="wx-scale">' + ticks.map(function (t) { return "<span>" + t + "</span>"; }).join("") + "</div>";
    html += '<div class="wx-spark-row">' + scale + svg + "</div>";
    html += '<div class="wx-spark-x"><span>1h</span><span>now</span></div>';
    return html + "</div>";
  }

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function waClock(iso) {
    if (!iso) return "";
    var d = new Date(iso);
    if (isNaN(d.getTime())) return "";
    var h = d.getHours();
    var m = d.getMinutes();
    return (h < 10 ? "0" : "") + h + ":" + (m < 10 ? "0" : "") + m;
  }

  function fmtDur(sec) {
    var n = Number(sec);
    if (!n || n < 0 || isNaN(n)) return "0:00";
    var m = Math.floor(n / 60);
    var s = Math.floor(n % 60);
    return m + ":" + (s < 10 ? "0" : "") + s;
  }

  function waBubble(m) {
    var out = !!(m && m.from_me);
    var kind = String((m && m.kind) || "text");
    var body = String((m && m.body) || "");
    var cap = String((m && m.caption) || "");
    var inner = "";
    if (!out && m && m.sender_name) {
      inner += '<span class="wx-wa-who">' + esc(m.sender_name) + "</span>";
    }
    if (kind === "voice" || kind === "audio") {
      inner += '<span class="wx-wa-voice"><span class="wx-wa-play" aria-hidden="true">▶</span><span class="wx-wa-wave"></span><span class="wx-wa-dur">' + esc(fmtDur(m.duration_sec)) + "</span></span>";
    } else if (kind === "photo") {
      inner += '<span class="wx-wa-text">' + esc(cap || "Photo") + "</span>";
    } else if (kind === "video") {
      inner += '<span class="wx-wa-text">' + esc(cap || "Video") + "</span>";
    } else {
      inner += '<span class="wx-wa-text">' + esc(body || cap || "") + "</span>";
    }
    inner += '<span class="wx-wa-meta">' + esc(waClock(m && m.occurred_at)) + "</span>";
    return '<div class="wx-wa-row ' + (out ? "is-out" : "is-in") + '"><div class="wx-wa-b">' + inner + "</div></div>";
  }

  function paintWa(slot, data) {
    var layer = slot.querySelector(".wx-wa-layer");
    if (!layer) return;
    var msgs = (data && data.messages) || [];
    var html = "";
    var i;
    for (i = 0; i < msgs.length; i += 1) {
      html += waBubble(msgs[i]);
    }
    layer.innerHTML = html || '<div class="wx-wa-empty">No group messages yet.</div>';
    layer.scrollTop = layer.scrollHeight;
  }

  function loadWa(slot) {
    fetch("/api/regatta/" + encodeURIComponent(CAPE_CLASSIC_ID) + "/event-whatsapp?_=" + Date.now(), {
      cache: "no-store",
      credentials: "same-origin"
    })
      .then(function (res) { return res.ok ? res.json() : Promise.reject(res.status); })
      .then(function (data) { paintWa(slot, data); })
      .catch(function () {
        var layer = slot.querySelector(".wx-wa-layer");
        if (layer) layer.innerHTML = '<div class="wx-wa-empty">WhatsApp feed unavailable.</div>';
      });
  }

  function hideWaGate() {
    var el = document.getElementById("ssaWaGate");
    if (el) el.classList.remove("is-open");
  }

  function showWaGate() {
    var el = document.getElementById("ssaWaGate");
    if (!el) {
      var ret = encodeURIComponent(String(location.href || "/"));
      el = document.createElement("div");
      el.id = "ssaWaGate";
      el.className = "ssa-wa-gate";
      el.setAttribute("role", "dialog");
      el.setAttribute("aria-modal", "true");
      el.setAttribute("aria-label", "Sign in required");
      el.innerHTML =
        '<div class="ssa-wa-gate-card">' +
          "<p>You must be signed up and logged in to see WhatsApp messages.</p>" +
          '<div class="ssa-wa-gate-actions">' +
            '<a class="ssa-wa-gate-in" href="/login.html?returnTo=' + ret + '">Sign In</a>' +
            '<a class="ssa-wa-gate-up" href="/signup.html?signup=1&amp;returnTo=' + ret + '">Sign Up</a>' +
            '<button type="button" data-wa-gate-close="1">Close</button>' +
          "</div>" +
        "</div>";
      document.body.appendChild(el);
      el.addEventListener("click", function (e) {
        if (e.target === el) hideWaGate();
      });
      var close = el.querySelector("[data-wa-gate-close]");
      if (close) close.addEventListener("click", hideWaGate);
    }
    el.classList.add("is-open");
  }

  function sessionIsRegistered() {
    return fetch("/auth/session?path=" + encodeURIComponent(location.pathname || "/"), {
      credentials: "include",
      cache: "no-store"
    })
      .then(function (res) { return res.ok ? res.json() : { valid: false }; })
      .then(function (s) { return !!(s && s.valid === true); })
      .catch(function () { return false; });
  }

  function bindWa(slot) {
    var btn = slot.querySelector(".wx-wa-btn");
    if (!btn || btn.getAttribute("data-bound") === "1") return;
    btn.setAttribute("data-bound", "1");
    btn.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      if (waShow === false) return;
      if (slot.classList.contains("ssa-wa-open")) {
        slot.classList.remove("ssa-wa-open");
        btn.setAttribute("aria-pressed", "false");
        return;
      }
      sessionIsRegistered().then(function (ok) {
        if (!ok) {
          showWaGate();
          return;
        }
        slot.classList.add("ssa-wa-open");
        btn.setAttribute("aria-pressed", "true");
        loadWa(slot);
      });
    });
  }

  function render(slot, data) {
    var wnow = data.wind_kt;
    var wavg = data.avg_kt;
    var whigh = data.high_kt != null ? data.high_kt : data.gust_kt;
    var colN = bandCol(wnow);
    var colA = bandCol(wavg);
    var colH = bandCol(whigh);
    slot.innerHTML =
      '<div class="wx-wp-top">' +
        '<div class="wx-wp-comp">' + drawDial(data) + "</div>" +
        drawSpark(data) +
        '<div class="wx-info">' +
          '<div class="wx-ir"><span class="wx-il">Now</span><span class="wx-iv" style="color:' + colN + '">' + n1(wnow) + " <small>kn</small></span></div>" +
          '<div class="wx-ir"><span class="wx-il">Avg</span><span class="wx-iv" style="color:' + colA + '">' + n1(wavg) + " <small>kn</small></span></div>" +
          '<div class="wx-ir"><span class="wx-il">High</span><span class="wx-iv" style="color:' + colH + '">' + n1(whigh) + " <small>kn</small></span></div>" +
        "</div>" +
      "</div>" +
      '<button type="button" class="wx-wa-btn" aria-label="Cape Classic WhatsApp" aria-pressed="false">' + WA_ICON + "</button>" +
      '<div class="wx-wa-layer" aria-label="Cape Classic WhatsApp"></div>';
    bindWa(slot);
    applyWaShow(slot);
    refreshWaShow(slot);
  }

  function fitGauge(slot) {
    var comp = slot && slot.querySelector(".wx-wp-comp");
    if (!slot || !comp) return;
    slot.style.height = "122px";
    slot.style.minHeight = "122px";
    slot.style.maxHeight = "122px";
    comp.style.height = "122px";
    comp.style.width = "122px";
    comp.style.maxHeight = "122px";
    comp.style.maxWidth = "122px";
  }

  function syncToMarine(slot, marine) {
    if (!slot || !marine) return;
    slot.style.height = "122px";
    slot.style.minHeight = "122px";
    slot.style.maxHeight = "122px";
    var mt = getComputedStyle(marine).marginTop;
    if (mt) slot.style.marginTop = mt;
    fitGauge(slot);
  }

  var loading = false;
  var pollTimer = null;
  var POLL_MS = 40000;
  var waShow = true;

  function applyWaShow(slot) {
    if (!slot) return;
    if (waShow === false) {
      slot.classList.add("ssa-wa-off");
      slot.classList.remove("ssa-wa-open");
    } else {
      slot.classList.remove("ssa-wa-off");
    }
  }

  function refreshWaShow(slot) {
    fetch(WA_FEED + "?_=" + Date.now(), { cache: "no-store", credentials: "same-origin" })
      .then(function (res) { return res.ok ? res.json() : null; })
      .then(function (data) {
        if (data && data.show === false) waShow = false;
        else if (data && data.show === true) waShow = true;
        applyWaShow(slot);
      })
      .catch(function () {});
  }

  async function load(slot) {
    if (loading) return;
    loading = true;
    try {
      var res = await fetch("/api/wind2speed/zeekoevlei?_=" + Date.now(), {
        cache: "no-store",
        credentials: "same-origin"
      });
      if (!res.ok) throw new Error("w2s " + res.status);
      var data = await res.json();
      if (!data || data.ok === false) throw new Error((data && data.err) || "w2s fail");
      if (slot.classList.contains("ssa-wa-open")) {
        loadWa(slot);
      } else {
        render(slot, data);
        fitGauge(slot);
      }
      var next = Number(data.interval);
      if (next >= 10000 && next <= 120000 && next !== POLL_MS) {
        POLL_MS = next;
        if (pollTimer) {
          clearInterval(pollTimer);
          pollTimer = setInterval(function () { if (!document.hidden) load(slot); }, POLL_MS);
        }
      }
    } catch (err) {
      try { console.warn(err); } catch (e) {}
    } finally {
      loading = false;
    }
  }

  function mount() {
    if (document.getElementById(ROOT_ID)) return;
    var marine = document.getElementById("mmLiptonReels");
    if (!marine) return;
    if ((marine.getAttribute("data-regatta-id") || "").trim() !== CAPE_CLASSIC_ID) return;
    injectCss();
    var el = document.createElement("section");
    el.id = ROOT_ID;
    el.className = "card ssa-regatta-slot-card";
    el.setAttribute("aria-label", "Zeekoevlei wind");
    marine.parentNode.insertBefore(el, marine);
    syncToMarine(el, marine);
    window.addEventListener("resize", function () { fitGauge(el); });
    if (typeof MutationObserver === "function") {
      new MutationObserver(function () { fitGauge(el); }).observe(marine, {
        attributes: true,
        attributeFilter: ["class"]
      });
    }
    load(el);
    pollTimer = setInterval(function () { if (!document.hidden) load(el); }, POLL_MS);
    document.addEventListener("visibilitychange", function () { if (!document.hidden) load(el); });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }
  window.__ssaRegattaSlotCard = JS_VER;
})();
