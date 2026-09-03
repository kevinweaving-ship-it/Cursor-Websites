/**
 * Lipton 2026 -dev only. Replay sandbox — not live, not Nett.
 * Rank re-sorts at each mark *pass* (M1 can appear again on lap 2+).
 * Place deltas sit between consecutive passes. Times are mm:ss, no T+.
 * Data: /js/lipton-dev-replay.json
 */
(function () {
  var CACHE = "20260903track";
  var params = new URLSearchParams(location.search);
  if (!params.has("race") || params.has("live")) {
    params.delete("live");
    if (!params.get("race")) params.set("race", "10");
    history.replaceState({}, "", location.pathname + "?race=" + encodeURIComponent(params.get("race")));
  }
  var RACE_Q = Number(params.get("race") || 10) || 10;
  var LIVE_Q = false;
  var liveTablePhase = "armed10";
  var liveHeldN = 0;
  var raceMeta = { races: [] };
  function heldRaceFromMeta(meta) {
    var races = ((meta && meta.races) || []);
    var i;
    for (i = races.length - 1; i >= 0; i--) {
      if (races[i].held_live && !races[i].packed) return Number(races[i].n) || 0;
    }
    return 0;
  }
  function jsonUrl(kind, race) {
    if (!race || race === 4) return "/js/lipton-dev-" + kind + ".json?v=" + CACHE;
    return "/js/lipton-dev-" + kind + "-r" + race + ".json?v=" + CACHE;
  }
  var DATA_URL = jsonUrl("replay", RACE_Q);
  var TRAIL_URL = jsonUrl("trail", RACE_Q);
  function startLineGeom(pin, rc) {
    if (!pin || !rc) return null;
    var R = 6371000;
    var lat0 = (pin.lat + rc.lat) / 2;
    var lon0 = (pin.lon + rc.lon) / 2;
    var cos = Math.cos(lat0 * Math.PI / 180);
    function toxy(lat, lon) {
      return {
        x: (lon - lon0) * Math.PI / 180 * cos * R,
        y: (lat - lat0) * Math.PI / 180 * R
      };
    }
    function fromxy(x, y) {
      return {
        lat: lat0 + (y / R) * 180 / Math.PI,
        lon: lon0 + (x / (R * cos)) * 180 / Math.PI
      };
    }
    var a = toxy(pin.lat, pin.lon);
    var b = toxy(rc.lat, rc.lon);
    var lx = b.x - a.x;
    var ly = b.y - a.y;
    var len = Math.hypot(lx, ly) || 1;
    return {
      a: a,
      ux: lx / len,
      uy: ly / len,
      nx: -ly / len,
      ny: lx / len,
      len: len,
      fromxy: fromxy,
      toxy: toxy
    };
  }
  function startCourseNormal(g, m1, boatPts) {
    if (!g) return g;
    var nx = g.nx;
    var ny = g.ny;
    var mid = { x: g.a.x + g.ux * g.len / 2, y: g.a.y + g.uy * g.len / 2 };
    if (m1 && m1.lat != null) {
      var m = g.toxy(m1.lat, m1.lon);
      if ((m.x - mid.x) * nx + (m.y - mid.y) * ny < 0) {
        nx = -nx;
        ny = -ny;
      }
    } else if (boatPts && boatPts.length) {
      var scores = [];
      boatPts.forEach(function (p) {
        if (!p) return;
        var q = g.toxy(p.lat, p.lon);
        scores.push((q.x - g.a.x) * nx + (q.y - g.a.y) * ny);
      });
      scores.sort(function (u, v) { return u - v; });
      if (scores.length && scores[Math.floor(scores.length / 2)] < 0) {
        nx = -nx;
        ny = -ny;
      }
    }
    g.nx = nx;
    g.ny = ny;
    return g;
  }
  function drawStartDirArrows(ctx, xyFn, pin, rc, m1, boatPts) {
    if (!ctx || !xyFn || !pin || !rc) return;
    var g = startCourseNormal(startLineGeom(pin, rc), m1, boatPts);
    if (!g) return;
    var phase = Date.now() / 280;
    var slots = [0.22, 0.5, 0.78];
    slots.forEach(function (f, i) {
      var alpha = 0.12 + 0.78 * (0.5 + 0.5 * Math.sin(phase - i * 0.95));
      var along = f * g.len;
      var base = g.fromxy(g.a.x + g.ux * along, g.a.y + g.uy * along);
      var ahead = g.fromxy(g.a.x + g.ux * along + g.nx * 28, g.a.y + g.uy * along + g.ny * 28);
      var p0 = xyFn(base.lat, base.lon);
      var p1 = xyFn(ahead.lat, ahead.lon);
      var dx = p1.x - p0.x;
      var dy = p1.y - p0.y;
      var L = Math.hypot(dx, dy) || 1;
      dx /= L;
      dy /= L;
      var px = p0.x + dx * 10;
      var py = p0.y + dy * 10;
      var s = 12;
      var px2 = -dy;
      var py2 = dx;
      ctx.beginPath();
      ctx.moveTo(px + dx * s, py + dy * s);
      ctx.lineTo(px - dx * s * 0.45 + px2 * s * 0.72, py - dy * s * 0.45 + py2 * s * 0.72);
      ctx.lineTo(px - dx * s * 0.15, py - dy * s * 0.15);
      ctx.lineTo(px - dx * s * 0.45 - px2 * s * 0.72, py - dy * s * 0.45 - py2 * s * 0.72);
      ctx.closePath();
      ctx.fillStyle = "rgba(56,189,248," + alpha.toFixed(3) + ")";
      ctx.fill();
      ctx.strokeStyle = "rgba(255,255,255," + (0.18 + 0.45 * alpha).toFixed(3) + ")";
      ctx.lineWidth = 1;
      ctx.stroke();
    });
  }

  var resetPlaybackAudio = function () {};
  function goRace(n) {
    try { resetPlaybackAudio(); } catch (err) {}
    var u = new URL(location.href);
    u.searchParams.delete("live");
    u.searchParams.set("race", String(n));
    location.assign(u.pathname + "?" + u.searchParams.toString());
  }
  function setRaceTableLabel(n, isLive, tag) {
    var el = document.getElementById("lipton-dev-race-label");
    if (!el) return;
    if (n && tag) el.textContent = "Race " + n + " — " + tag;
    else if (n) el.textContent = "Race " + n;
    else el.textContent = "";
  }
  setRaceTableLabel(RACE_Q, false);
  function bindRaceButtons(active) {
    var want = Number(active || RACE_Q || 10);
    document.querySelectorAll("#lipton-dev-race-boxes [data-race]").forEach(function (btn) {
      var n = Number(btn.getAttribute("data-race"));
      btn.classList.toggle("is-active", n === want);
      btn.setAttribute("aria-pressed", n === want ? "true" : "false");
    });
  }
  function renderRaceBoxes(meta) {
    var host = document.getElementById("lipton-dev-race-boxes");
    if (!host) return;
    if (meta) raceMeta = meta;
    var byN = {};
    ((raceMeta && raceMeta.races) || []).forEach(function (r) { byN[r.n] = r; });
    var races = [];
    var i;
    for (i = 1; i <= 10; i++) {
      races.push(byN[i] || { n: i, packed: false, stage: "finished", ocs: [], gun_sast: "", course: "" });
    }
    host.innerHTML = "";
    var activeN = Number(RACE_Q || 10);
    races.forEach(function (r) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = "lipton-dev-race-box";
      b.setAttribute("data-race", String(r.n));
      b.textContent = "R" + r.n;
      if (r.n === activeN) b.classList.add("is-active");
      if (!r.packed) b.disabled = true;
      var gun = String(r.gun_sast || "").slice(11, 16);
      var ocs = (r.ocs || []).length ? " · OCS " + r.ocs.join(",") : "";
      var course = r.course ? " · " + r.course : "";
      b.title = "Race " + r.n + course + " · gun " + gun + (r.packed ? "" : " · GPS not packed yet") + ocs;
      b.addEventListener("click", function () {
        if (r.packed) goRace(r.n);
      });
      host.appendChild(b);
    });
  }
  bindRaceButtons(RACE_Q || 10);
  (function wireSiteHeader() {
    ["menuBtn", "navMenuOverlay", "menuToggle"].forEach(function (id) {
      var el = document.getElementById(id);
      if (el && el.parentNode) el.parentNode.removeChild(el);
    });
    document.querySelectorAll(".site-header .menu-btn, .site-header .nav-menu-overlay, .site-header .menu-dropdown-toggle, .site-header .mobile-dropdown").forEach(function (el) {
      if (el && el.parentNode) el.parentNode.removeChild(el);
    });
    if (typeof window.updateHeaderAuthStatus === "function") {
      window.updateHeaderAuthStatus();
    }
  })();
  fetch("/js/lipton-dev-races.json?v=" + CACHE, { cache: "no-store" })
    .then(function (res) { return res.ok ? res.json() : null; })
    .then(function (meta) {
      renderRaceBoxes(meta);
      setRaceTableLabel(RACE_Q, false);
    })
    .catch(function () { renderRaceBoxes({ races: [] }); });

  function pad(n) {
    return n < 10 ? "0" + n : String(n);
  }
  function fmtClock(ms) {
    if (ms < 0) {
      var a = Math.abs(ms);
      var s = Math.floor(a / 1000);
      return "−" + pad(Math.floor(s / 60)) + ":" + pad(s % 60);
    }
    var s2 = Math.floor(ms / 1000);
    return Math.floor(s2 / 60) + ":" + pad(s2 % 60);
  }
  function tailBudget(map) {
    var z = 15;
    try {
      if (map && map.getZoom) z = map.getZoom();
    } catch (e) {}
    if (!(z > 0)) z = 15;
    if (z < 12) z = 12;
    if (z > 19) z = 19;
    var t = (z - 12) / 7;
    return {
      m: 16 + t * 204,
      ms: 6000 + t * 56000,
      w: 1.5 + t * 2.4
    };
  }
  function fmtLiveClock(ms) {
    var a = Math.abs(Number(ms) || 0);
    var tenths = Math.floor(a / 100);
    var s = Math.floor(tenths / 10);
    var t = tenths % 10;
    return (ms < 0 ? "T−" : "T+") + Math.floor(s / 60) + ":" + pad(s % 60) + "." + t;
  }
  function esc(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
  }
  function watchUrl(data, ts) {
    var q = [];
    if (Number(data.race_day) !== 1) q.push("race-day=" + Number(data.race_day));
    q.push("ts=" + Math.floor(ts));
    return data.watch_path + "?" + q.join("&");
  }
  function asBoats(list) {
    return (list || []).map(function (b) {
      return { boat: b.boat, ts: b.ts_ms != null ? Number(b.ts_ms) : Number(b.ts) };
    });
  }
  function loadPasses(data) {
    if (Array.isArray(data.passes) && data.passes.length) {
      return data.passes.filter(function (p) {
        return p && (p.id === "FIN" || (p.boats && p.boats.length));
      }).map(function (p, i) {
        return {
          id: p.id || ("P" + i),
          label: p.label || ("M" + (p.mark || i + 1)),
          lap: Number(p.lap || 1),
          mark: Number(p.mark || i + 1),
          boats: asBoats(p.boats)
        };
      });
    }
    var labels = data.mark_labels || Object.keys(data.marks || {});
    return labels.map(function (lab, i) {
      var n = parseInt(String(lab).replace(/^M/i, ""), 10);
      if (isNaN(n)) n = i + 1;
      return {
        id: "L1-" + n,
        label: lab,
        lap: 1,
        mark: n,
        boats: asBoats((data.marks || {})[lab])
      };
    });
  }

  var LIVE_BOAT_COLORS = {
    HYC: "#2563eb", RCYC: "#e11d48", KYC: "#16a34a", RNYC: "#7c3aed",
    WBYC: "#ea580c", FBYC: "#0891b2", SBYC: "#ca8a04", PYC: "#db2777",
    LDYC: "#4f46e5", GLYC: "#65a30d", BYC: "#0d9488", TSC: "#9333ea",
    WYAC: "#f59e0b", RCYCA: "#64748b", "RCYC Academy": "#64748b",
    UCT: "#0284c7", UCTYC: "#0284c7", IZI: "#be123c", IZIVUNGUVUNGU: "#be123c",
    LYCN: "#15803d", LYC: "#15803d"
  };

  if (LIVE_Q) {
    startLive();
  } else {
  Promise.all([
    fetch(DATA_URL, { cache: "no-store" }).then(function (res) {
      if (!res.ok) throw new Error("replay json " + res.status);
      return res.json();
    }),
    fetch(TRAIL_URL, { cache: "no-store" }).then(function (res) {
      if (!res.ok) throw new Error("trail json " + res.status);
      return res.json();
    })
  ])
    .then(function (pair) { start(pair[0], pair[1]); })
    .catch(function (err) {
      var sailed = document.getElementById("lipton-dev-sailed");
      if (sailed) {
        sailed.textContent = RACE_Q && RACE_Q !== 4
          ? ("Race " + RACE_Q + " GPS not packed on -dev yet. Choose a packed race.")
          : "Replay data failed to load";
      }
      console.error(err);
    });
  }

  function startLive() {
    bindRaceButtons(liveHeldN || heldRaceFromMeta(raceMeta) || -1);
    var gunTs = null;
    var snap = null;
    var liveRaceN = 10;
    var R9_FINISH_ORDER = ["KYC", "RCYC", "PYC", "SBYC", "UCTYC", "RCYC Academy", "WBYC", "FBYC", "HYC", "GLYC", "RNYC", "BYC", "LDYC", "LYC", "IZIVUNGUVUNGU", "TSC", "WYAC"];
    var FLEET_17 = ["RCYC Academy", "GLYC", "KYC", "RCYC", "RNYC", "UCTYC", "HYC", "PYC", "WYAC", "BYC", "LDYC", "FBYC", "SBYC", "LYC", "WBYC", "TSC", "IZIVUNGUVUNGU"];
    var ROUND_LEGS = ["M1", "PIN", "M1b", "PINb", "M1c", "FIN"];
    var armedLegIdx = 0;
    var devHoldR9 = false;
    var devArmed = true;
    var devLiveR10 = false;
    liveTablePhase = "armed10";
    setRaceTableLabel(10, true, "ARMED");
    var chartMap = null;
    var mapEl = document.getElementById("lipton-dev-map");
    var mapCtx = null;
    var followFleet = true;
    var chartSyncing = false;
    var drawingMap = false;
    var identity = {};
    var hud = document.getElementById("lipton-dev-map-hud");
    var nameEl = document.getElementById("lipton-dev-map-hud-name");
    var clockHud = document.getElementById("lipton-dev-map-hud-clock");
    var playBtn = document.getElementById("lipton-dev-play");
    var LIVE_CLOCK_LAG_MS = 2000;
    var atLive = true;
    var livePlaying = false;
    var livePlayWall = Date.now();
    var LIVE_REPLAY_RATE = 10;
    var scrubbing = false;
    var playTs = Date.now() - LIVE_CLOCK_LAG_MS;
    var hist = { boats: {}, marks: {}, pin: [], rc: [] };
    var didFit = false;
    var loadedHistory = false;
    var slowerBtn = document.getElementById("lipton-dev-slower");
    var fasterBtn = document.getElementById("lipton-dev-faster");
    var scrubEl = document.getElementById("lipton-dev-scrub");
    if (slowerBtn) slowerBtn.disabled = true;
    if (fasterBtn) fasterBtn.disabled = true;
    if (playBtn) {
      playBtn.disabled = false;
      playBtn.title = "Play";
      playBtn.setAttribute("aria-label", "Play");
      playBtn.addEventListener("pointerdown", unlockLiveHorn);
      playBtn.addEventListener("click", function () {
        unlockLiveHorn();
        if (liveHeldN) {
          if (livePlaying) {
            livePlaying = false;
          } else {
            atLive = false;
            if (playTs >= liveNow() - 2000) playTs = playStart();
            livePlaying = true;
            livePlayWall = Date.now();
          }
        } else {
          livePlaying = false;
          atLive = true;
          playTs = liveNow();
        }
        paintClock();
        syncScrub();
        drawLiveMap();
      });
    }
    if (scrubEl) {
      scrubEl.disabled = false;
      scrubEl.addEventListener("pointerdown", function () { scrubbing = true; atLive = false; });
      scrubEl.addEventListener("input", function () {
        atLive = false;
        var span = Math.max(1, liveNow() - playStart());
        playTs = playStart() + (Number(scrubEl.value) / 1000) * span;
        if (Number(scrubEl.value) >= 990) {
          atLive = true;
          playTs = liveNow();
        }
        paintClock();
        drawLiveMap();
      });
      window.addEventListener("pointerup", function () { scrubbing = false; });
    }
    var GUN_HORN_SRC = "/js/lipton-dev-start-airhorn.mp3?v=20260828t";
    var RECALL_HORN_SRC = "/js/lipton-dev-recall-horn.wav?v=20260828t";
    var GUN_HORN_ONSET = 0.05;
    var liveGunHorn = null;
    var liveRecallHorn = null;
    var liveHornCtx = null;
    var liveGunBuf = null;
    var liveRecallBuf = null;
    var liveGunFired = false;
    var liveSoundOn = false;
    var liveOcs = [];
    var liveRecallTimer = null;
    var livePrevTs = 0;
    fetch(GUN_HORN_SRC).then(function (res) { return res.ok ? res.arrayBuffer() : null; }).then(function (buf) {
      if (!buf || !liveHornCtx) { liveGunBuf = buf; return; }
      liveHornCtx.decodeAudioData(buf.slice(0), function (b) { liveGunBuf = b; }, function () {});
    }).catch(function () {});
    fetch(RECALL_HORN_SRC).then(function (res) { return res.ok ? res.arrayBuffer() : null; }).then(function (buf) {
      if (!buf || !liveHornCtx) { liveRecallBuf = buf; return; }
      liveHornCtx.decodeAudioData(buf.slice(0), function (b) { liveRecallBuf = b; }, function () {});
    }).catch(function () {});
    function prepLiveHorn(el) {
      el.preload = "auto";
      el.playsInline = true;
      el.setAttribute("playsinline", "");
      el.volume = 1;
      try { el.load(); } catch (err) {}
      return el;
    }
    function unlockLiveHorn() {
      liveSoundOn = true;
      var AC = window.AudioContext || window.webkitAudioContext;
      if (AC && !liveHornCtx) liveHornCtx = new AC();
      if (liveHornCtx && liveHornCtx.state === "suspended") liveHornCtx.resume();
      if (!liveGunHorn) liveGunHorn = prepLiveHorn(new Audio(GUN_HORN_SRC));
      if (!liveRecallHorn) liveRecallHorn = prepLiveHorn(new Audio(RECALL_HORN_SRC));
      [liveGunHorn, liveRecallHorn].forEach(function (el) {
        el.muted = true;
        var p = el.play();
        if (p && p.then) p.then(function () { el.pause(); el.muted = false; try { el.currentTime = 0; } catch (err) {} }).catch(function () { el.muted = false; });
      });
    }
    function playLiveBuf(buf, onset) {
      if (!liveSoundOn || !liveHornCtx || !buf) return false;
      if (liveHornCtx.state === "suspended") { liveHornCtx.resume(); return false; }
      try {
        var src = liveHornCtx.createBufferSource();
        src.buffer = buf;
        src.connect(liveHornCtx.destination);
        src.start(0, Math.min(onset || 0, Math.max(0, buf.duration - 0.02)));
        return true;
      } catch (err) { return false; }
    }
    function fireLiveRecall() {
      if (!liveSoundOn || !liveOcs.length) return;
      if (playLiveBuf(liveRecallBuf, 0)) return;
      if (!liveRecallHorn) return;
      liveRecallHorn.muted = false;
      try { liveRecallHorn.currentTime = 0; } catch (err) {}
      var p = liveRecallHorn.play();
      if (p && p.catch) p.catch(function () {});
    }
    function fireLiveGun() {
      if (!liveSoundOn || liveGunFired || !gunTs) return;
      liveGunFired = true;
      if (!playLiveBuf(liveGunBuf, GUN_HORN_ONSET) && liveGunHorn) {
        liveGunHorn.muted = false;
        try { liveGunHorn.currentTime = GUN_HORN_ONSET; } catch (err) {}
        var p = liveGunHorn.play();
        if (p && p.catch) p.catch(function () {});
      }
      if (liveOcs.length) {
        if (liveRecallTimer) clearTimeout(liveRecallTimer);
        liveRecallTimer = setTimeout(function () { liveRecallTimer = null; fireLiveRecall(); }, 1550);
      }
    }
    function tickLiveHorns() {
      if (!gunTs) return;
      var prev = livePrevTs;
      livePrevTs = playTs;
      if (!prev) return;
      if (!liveGunFired && prev < gunTs - 100 && playTs >= gunTs - 100) fireLiveGun();
    }
    document.addEventListener("pointerdown", unlockLiveHorn, { once: true });
    resetPlaybackAudio = function () {
      liveSoundOn = false;
      liveGunFired = false;
      if (liveRecallTimer) { clearTimeout(liveRecallTimer); liveRecallTimer = null; }
      [liveGunHorn, liveRecallHorn].forEach(function (el) {
        if (!el) return;
        try { el.pause(); } catch (err) {}
      });
    };
    function liveFill(sail) {
      return LIVE_BOAT_COLORS[sail] || "#94a3b8";
    }
    function rgbaHex(hex, a) {
      var n = parseInt(String(hex).replace("#", ""), 16);
      if (!(n >= 0)) return "rgba(148,163,184," + a + ")";
      return "rgba(" + ((n >> 16) & 255) + "," + ((n >> 8) & 255) + "," + (n & 255) + "," + a + ")";
    }
    function liveNow() {
      return Date.now() - LIVE_CLOCK_LAG_MS;
    }
    function playStart() {
      if (gunTs) return gunTs - 5 * 60 * 1000;
      return liveNow() - 8 * 60 * 1000;
    }
    var liveCam = null;
    var lastChartSyncAt = 0;
    var lastHdg = {};
    var lastHdgAt = {};
    var chartPointerDown = false;
    function blendHdg(sail, target) {
      if (target == null || isNaN(target)) return lastHdg[sail] || 0;
      var prev = lastHdg[sail];
      var now = Date.now();
      if (prev == null) {
        lastHdg[sail] = target;
        lastHdgAt[sail] = now;
        return target;
      }
      var dt = Math.min(0.05, (now - (lastHdgAt[sail] || now)) / 1000);
      lastHdgAt[sail] = now;
      var d = target - prev;
      while (d > 180) d -= 360;
      while (d < -180) d += 360;
      var out = prev + d * (1 - Math.exp(-dt * 9));
      lastHdg[sail] = out;
      return out;
    }
    function atTs(arr, ts) {
      if (!arr || !arr.length) return null;
      var n = arr.length;
      if (ts <= arr[0].ts_ms) {
        var f = arr[0];
        return { lat: f.lat, lon: f.lon, hdg: f.hdg, ts_ms: ts };
      }
      if (ts >= arr[n - 1].ts_ms) {
        var last = arr[n - 1];
        var holdHdg = last.hdg;
        if (n > 1) holdHdg = Math.atan2(last.lon - arr[n - 2].lon, last.lat - arr[n - 2].lat) * 180 / Math.PI;
        return { lat: last.lat, lon: last.lon, hdg: holdHdg, ts_ms: ts };
      }
      var lo = 0;
      var hi = n - 1;
      while (hi - lo > 1) {
        var mid = (lo + hi) >> 1;
        if (arr[mid].ts_ms <= ts) lo = mid;
        else hi = mid;
      }
      var prev = arr[lo];
      var next = arr[hi];
      if (!next || next.ts_ms === prev.ts_ms) {
        return { lat: prev.lat, lon: prev.lon, hdg: prev.hdg, ts_ms: ts };
      }
      var span = next.ts_ms - prev.ts_ms;
      var u = span ? (ts - prev.ts_ms) / span : 0;
      if (u < 0) u = 0;
      if (u > 1) u = 1;
      return {
        lat: prev.lat + (next.lat - prev.lat) * u,
        lon: prev.lon + (next.lon - prev.lon) * u,
        hdg: Math.atan2(next.lon - prev.lon, next.lat - prev.lat) * 180 / Math.PI,
        ts_ms: ts
      };
    }
    function posLive(sail, ts) {
      var pos = atTs(hist.boats[sail], ts);
      if (!pos) return null;
      pos.hdg = blendHdg(sail, pos.hdg);
      return pos;
    }
    function tailUntil(arr, ts) {
      if (!arr || !arr.length) return [];
      var bud = tailBudget(chartMap);
      var hits = [];
      var acc = 0;
      var last = null;
      for (var i = arr.length - 1; i >= 0; i--) {
        var p = arr[i];
        if (p.ts_ms > ts) continue;
        if (last) {
          acc += distM(last, p);
          if (acc >= bud.m) break;
          if (ts - p.ts_ms >= bud.ms) break;
        }
        hits.push(p);
        last = p;
      }
      hits.reverse();
      return hits;
    }
    function slimTrail(arr) {
      if (!arr || !arr.length) return [];
      var out = [];
      var last = -1e12;
      var i;
      for (i = 0; i < arr.length; i++) {
        var p = arr[i];
        if (!p || p.ts_ms == null) continue;
        if (p.ts_ms - last >= 900 || i === arr.length - 1) {
          out.push({ lat: p.lat, lon: p.lon, ts_ms: p.ts_ms, hdg: p.hdg });
          last = p.ts_ms;
        }
      }
      return out;
    }
    function persistHist() {
      if (!gunTs) return;
      try {
        var payload = { boats: {}, marks: {}, pin: slimTrail(hist.pin), rc: slimTrail(hist.rc) };
        Object.keys(hist.boats).forEach(function (s) {
          payload.boats[s] = slimTrail(hist.boats[s]);
        });
        Object.keys(hist.marks).forEach(function (k) {
          payload.marks[k] = slimTrail(hist.marks[k]);
        });
        sessionStorage.setItem("lipton-live-hist-v1-" + gunTs, JSON.stringify(payload));
      } catch (eH) {}
    }
    function loadHist() {
      if (!gunTs) return;
      try {
        var raw = sessionStorage.getItem("lipton-live-hist-v1-" + gunTs);
        if (!raw) return;
        var d = JSON.parse(raw);
        Object.keys((d && d.boats) || {}).forEach(function (s) {
          hist.boats[s] = mergeTrail(hist.boats[s] || [], d.boats[s]);
        });
        Object.keys((d && d.marks) || {}).forEach(function (k) {
          hist.marks[k] = mergeTrail(hist.marks[k] || [], d.marks[k]);
        });
        if (d.pin) hist.pin = mergeTrail(hist.pin, d.pin);
        if (d.rc) hist.rc = mergeTrail(hist.rc, d.rc);
      } catch (eL) {}
    }
    function mergeTrail(dest, pts) {
      if (!pts || !pts.length) return dest || [];
      dest = dest || [];
      var by = {};
      dest.forEach(function (p) {
        if (p && p.ts_ms != null) by[p.ts_ms] = p;
      });
      pts.forEach(function (p) {
        if (p && p.ts_ms != null) by[p.ts_ms] = p;
      });
      return Object.keys(by).map(Number).sort(function (a, b) { return a - b; }).map(function (k) { return by[k]; });
    }
    function syncScrub() {
      if (!scrubEl || scrubbing) return;
      var span = Math.max(1, liveNow() - playStart());
      var v = atLive ? 1000 : Math.round(1000 * (playTs - playStart()) / span);
      if (v < 0) v = 0;
      if (v > 1000) v = 1000;
      scrubEl.value = String(v);
    }
    function gunClockDelta() {
      var g = (snap && snap.gun_ts_ms != null) ? Number(snap.gun_ts_ms) : gunTs;
      if (!(g > 0)) return null;
      return Date.now() - g;
    }
    function paintClock() {
      if (!clockHud || !hud) return;
      if (atLive) playTs = liveNow();
      var delta = gunClockDelta();
      if (delta == null) {
        return;
      }
      clockHud.textContent = fmtLiveClock(delta);
      hud.classList.toggle("is-after", delta >= 0);
      if (playBtn) {
        var showPause = liveHeldN ? livePlaying : atLive;
        playBtn.classList.toggle("is-playing", showPause);
        var lab = showPause ? "Pause" : "Play";
        playBtn.title = lab;
        playBtn.setAttribute("aria-label", lab);
      }
    }
    function initChart() {
      var el = document.getElementById("lipton-dev-chart");
      if (!el || !window.L || chartMap) return;
      chartMap = L.map(el, {
        zoomControl: true,
        attributionControl: true,
        dragging: true,
        scrollWheelZoom: true,
        doubleClickZoom: true,
        boxZoom: true,
        keyboard: true,
        touchZoom: true,
        zoomSnap: 0,
        zoomAnimation: false,
        fadeAnimation: false,
        markerZoomAnimation: false,
        inertia: true
      }).setView([-33.886, 18.43], 15);
      var tileOpts = {
        minZoom: 12, maxZoom: 19, keepBuffer: 8,
        updateWhenIdle: false, updateWhenZooming: false, updateInterval: 400, crossOrigin: true
      };
      L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", Object.assign({
        maxZoom: 19, attribution: "Tiles © Esri"
      }, tileOpts)).addTo(chartMap);
      L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}", Object.assign({
        maxZoom: 18, opacity: 0.85, attribution: "Labels © Esri"
      }, tileOpts)).addTo(chartMap);
      chartMap.on("dragstart zoomstart boxzoomstart", function () {
        followFleet = false;
      });
      chartMap.on("move zoom zoomend", function () {
        if (!chartSyncing) drawLiveMap();
      });
      var track = el.closest(".lipton-dev-track") || el.parentNode;
      var ctrls = el.querySelector(".leaflet-control-container");
      if (track && ctrls) track.appendChild(ctrls);
      window.requestAnimationFrame(function () {
        if (chartMap) chartMap.invalidateSize({ animate: false });
      });
    }
    function sizeCanvas() {
      if (!mapEl) return;
      initChart();
      var w = mapEl.clientWidth || 0;
      var h = mapEl.clientHeight || 0;
      if (w < 32 || h < 32) return;
      var dpr = window.devicePixelRatio || 1;
      var needW = Math.round(w * dpr);
      var needH = Math.round(h * dpr);
      if (mapCtx && Math.abs(mapEl.width - needW) < 3 && Math.abs(mapEl.height - needH) < 3) {
        return;
      }
      mapEl.width = needW;
      mapEl.height = needH;
      mapCtx = mapEl.getContext("2d");
      mapCtx.setTransform(dpr, 0, 0, dpr, 0, 0);
      mapCtx.imageSmoothingEnabled = true;
    }
    function xy(lat, lon) {
      if (!chartMap) return { x: 0, y: 0 };
      var pt = chartMap.latLngToContainerPoint([lat, lon]);
      return { x: pt.x, y: pt.y };
    }
    function armedPid() {
      return ROUND_LEGS[Math.max(0, Math.min(armedLegIdx, ROUND_LEGS.length - 1))] || "M1";
    }
    function armedIsWindward() {
      var p = armedPid();
      return p === "M1" || p === "M1b" || p === "M1c";
    }
    function armedIsPinGate() {
      var p = armedPid();
      return p === "PIN" || p === "PINb" || p === "FIN";
    }
    function armedToPos(ts, startMid, pin, rc) {
      var p = armedPid();
      if (p === "PIN" || p === "PINb") return atTs(hist.pin, ts) || pin;
      if (p === "FIN") return startMid || pin || rc;
      return atTs(hist.marks["1"], ts);
    }
    function armedFromPos(ts, startMid, pin) {
      var p = armedPid();
      if (p === "M1") return startMid;
      if (p === "PIN" || p === "PINb") return atTs(hist.marks["1"], ts);
      if (p === "M1b" || p === "M1c") return pin;
      if (p === "FIN") return atTs(hist.marks["1"], ts) || pin;
      return startMid;
    }
    function applyCourseOrientation() {
      var chart = document.getElementById("lipton-dev-chart");
      if (chart) {
        chart.style.transform = "";
        chart.style.transformOrigin = "";
      }
    }
    function drawBoatIcon(p, hdg, fill) {
      var r = 7;
      mapCtx.beginPath();
      mapCtx.arc(p.x, p.y, r, 0, Math.PI * 2);
      mapCtx.fillStyle = fill;
      mapCtx.fill();
      mapCtx.strokeStyle = "rgba(15,23,42,0.75)";
      mapCtx.lineWidth = 1.4;
      mapCtx.stroke();
      mapCtx.save();
      mapCtx.translate(p.x, p.y);
      mapCtx.rotate((hdg || 0) * Math.PI / 180);
      mapCtx.beginPath();
      mapCtx.moveTo(0, -r - 3.6);
      mapCtx.lineTo(3.1, -r + 1.2);
      mapCtx.lineTo(-3.1, -r + 1.2);
      mapCtx.closePath();
      mapCtx.fillStyle = "#ffffff";
      mapCtx.fill();
      mapCtx.restore();
    }
    function meterOffset(lat, lon, northM, eastM) {
      return {
        lat: lat + northM / 111000,
        lon: lon + eastM / (111000 * Math.max(0.2, Math.cos(lat * Math.PI / 180)))
      };
    }
    function startGrid(pin, rc, boatPts) {
      var m1 = hist.marks["1"] ? atTs(hist.marks["1"], playTs) : null;
      return startCourseNormal(startLineGeom(pin, rc), m1, boatPts);
    }
    function drawStartGrid(pin, rc) {
      var boats = [];
      Object.keys(hist.boats).forEach(function (sail) {
        var b = atTs(hist.boats[sail], playTs);
        if (b) boats.push(b);
      });
      var g = startGrid(pin, rc, boats);
      if (!g || !mapCtx) return;
      function lineAt(d, width, color) {
        var p1 = g.fromxy(g.a.x + g.nx * d, g.a.y + g.ny * d);
        var p2 = g.fromxy(g.a.x + g.ux * g.len + g.nx * d, g.a.y + g.uy * g.len + g.ny * d);
        var a = xy(p1.lat, p1.lon);
        var b = xy(p2.lat, p2.lon);
        mapCtx.beginPath();
        mapCtx.moveTo(a.x, a.y);
        mapCtx.lineTo(b.x, b.y);
        mapCtx.strokeStyle = color;
        mapCtx.lineWidth = width;
        mapCtx.setLineDash([]);
        mapCtx.stroke();
        return { a: a, b: b };
      }
      var over = lineAt(-2, 3.2, "rgba(239,68,68,0.85)");
      var base = lineAt(0, 3.4, "#38bdf8");
      var m1p = hist.marks["1"] ? atTs(hist.marks["1"], playTs) : null;
      drawStartDirArrows(mapCtx, xy, pin, rc, m1p, boats);
      return { g: g, over: over, base: base };
    }
    function liveFitLatLngs(ts) {
      var pts = [];
      FLEET_17.forEach(function (sail) {
        var b = atTs(hist.boats[sail], ts);
        if (b) pts.push(L.latLng(b.lat, b.lon));
      });
      Object.keys(hist.boats).forEach(function (sail) {
        if (FLEET_17.indexOf(sail) >= 0) return;
        var b = atTs(hist.boats[sail], ts);
        if (b) pts.push(L.latLng(b.lat, b.lon));
      });
      var pin = atTs(hist.pin, ts);
      var rc = atTs(hist.rc, ts);
      var startMid = (pin && rc)
        ? { lat: (pin.lat + rc.lat) / 2, lon: (pin.lon + rc.lon) / 2 }
        : (pin || rc);
      var toMk = armedToPos(ts, startMid, pin, rc);
      var fromMk = armedFromPos(ts, startMid, pin);
      if (toMk) pts.push(L.latLng(toMk.lat, toMk.lon));
      if (fromMk) pts.push(L.latLng(fromMk.lat, fromMk.lon));
      return pts;
    }
    function fitLive() {
      if (!chartMap || !followFleet || !window.L) return;
      var latlngs = liveFitLatLngs(playTs);
      if (latlngs.length < 2) return;
      chartSyncing = true;
      if (chartMap.invalidateSize) chartMap.invalidateSize({ animate: false });
      chartMap.fitBounds(L.latLngBounds(latlngs), { padding: [48, 48], maxZoom: 16, animate: false });
      chartSyncing = false;
      didFit = true;
    }
    function drawLiveMap() {
      if (drawingMap) return;
      drawingMap = true;
      sizeCanvas();
      if (!mapCtx || !mapEl) {
        drawingMap = false;
        return;
      }
      var ts = playTs;
      var w = mapEl.clientWidth || 0;
      var h = mapEl.clientHeight || 0;
      mapCtx.clearRect(0, 0, w, h);
      var pin = atTs(hist.pin, ts);
      var rc = atTs(hist.rc, ts);
      var startMid = (pin && rc)
        ? { lat: (pin.lat + rc.lat) / 2, lon: (pin.lon + rc.lon) / 2 }
        : (pin || rc);
      var toMk = armedToPos(ts, startMid, pin, rc);
      var fromMk = armedFromPos(ts, startMid, pin);
      applyCourseOrientation();
      Object.keys(hist.marks).forEach(function (k) {
        if (k !== "1") return;
        var arr = hist.marks[k];
        if (!markValid(arr, ts) && !atTs(arr, ts)) return;
        var pos = atTs(arr, ts);
        if (!pos) return;
        var p = xy(pos.lat, pos.lon);
        mapCtx.beginPath();
        mapCtx.arc(p.x, p.y, 11, 0, Math.PI * 2);
        mapCtx.strokeStyle = "rgba(251,191,36,0.85)";
        mapCtx.lineWidth = 2.2;
        mapCtx.stroke();
        mapCtx.beginPath();
        mapCtx.arc(p.x, p.y, 4.2, 0, Math.PI * 2);
        mapCtx.fillStyle = "#fbbf24";
        mapCtx.fill();
        var m1From = fromMk || startMid;
        var m1Spec = roundArr.M1 || defaultPortSpec(pos, m1From);
        if (m1Spec && armedIsWindward()) drawRoundArrow(pos, m1Spec, "#fbbf24");
        var m1Lab = markLabelAway(pos, m1Spec, m1From);
        mapCtx.fillStyle = "#ffffff";
        mapCtx.font = "bold 13px sans-serif";
        mapCtx.textAlign = "center";
        mapCtx.textBaseline = "middle";
        mapCtx.fillText("M1", m1Lab.x, m1Lab.y);
        mapCtx.textAlign = "start";
        mapCtx.textBaseline = "alphabetic";
      });
      if (pin && rc) {
        drawStartGrid(pin, rc);
        var a = xy(pin.lat, pin.lon);
        var b = xy(rc.lat, rc.lon);
        mapCtx.beginPath();
        mapCtx.arc(a.x, a.y, 4, 0, Math.PI * 2);
        mapCtx.fillStyle = "#38bdf8";
        mapCtx.fill();
        mapCtx.fillStyle = "#e2e8f0";
        mapCtx.font = "bold 9px sans-serif";
        mapCtx.fillRect(b.x - 7, b.y - 5, 14, 10);
        mapCtx.strokeStyle = "#38bdf8";
        mapCtx.lineWidth = 1;
        mapCtx.strokeRect(b.x - 7, b.y - 5, 14, 10);
        var pinFrom = atTs(hist.marks["1"], ts) || startMid;
        var pinArmed = armedIsPinGate();
        var pinSpec = roundArr.PIN || defaultPortSpec(pin, pinFrom);
        var labBoats = [];
        Object.keys(hist.boats).forEach(function (sail) {
          var lb = atTs(hist.boats[sail], ts);
          if (lb) labBoats.push(lb);
        });
        var pinLab = pinArmed
          ? markLabelAway(pin, pinSpec, pinFrom)
          : linePassingLabel(pin, pin, rc, pinFrom, labBoats);
        var rcLab = linePassingLabel(rc, pin, rc, pinFrom, labBoats);
        mapCtx.fillStyle = "#ffffff";
        mapCtx.font = "bold 10px sans-serif";
        mapCtx.textAlign = "center";
        mapCtx.textBaseline = "middle";
        mapCtx.fillText("RC", rcLab.x, rcLab.y);
        mapCtx.fillText("Pin", pinLab.x, pinLab.y);
        mapCtx.textAlign = "start";
        mapCtx.textBaseline = "alphabetic";
        if (pinArmed && pinSpec) drawRoundArrow(pin, pinSpec, "#38bdf8");
        var sg = startCourseNormal(startLineGeom(pin, rc), pinFrom, null);
        var midX = (a.x + b.x) / 2;
        var midY = (a.y + b.y) / 2;
        if (sg) {
          var ahead = sg.fromxy(sg.a.x + sg.ux * sg.len / 2 + sg.nx * 36, sg.a.y + sg.uy * sg.len / 2 + sg.ny * 36);
          var ap = xy(ahead.lat, ahead.lon);
          midX = ap.x;
          midY = ap.y;
        }
        mapCtx.fillStyle = "#ffffff";
        mapCtx.font = "bold 10px sans-serif";
        mapCtx.textAlign = "center";
        mapCtx.textBaseline = "middle";
        mapCtx.fillText("START", midX, midY);
        mapCtx.textAlign = "start";
        mapCtx.textBaseline = "alphabetic";
      }
      if (fromMk && toMk && liveTablePhase !== "hold9") {
        drawActiveLegChevrons(fromMk, toMk, armedIsPinGate() ? "56,189,248" : "251,191,36");
      }
      var liveTailW = tailBudget(chartMap).w;
      Object.keys(hist.boats).forEach(function (sail) {
        var trail = tailUntil(hist.boats[sail], ts);
        if (trail.length < 2) return;
        var fill = liveFill(sail);
        var n = trail.length - 1;
        for (var s = 0; s < n; s++) {
          var ta = xy(trail[s].lat, trail[s].lon);
          var tc = xy(trail[s + 1].lat, trail[s + 1].lon);
          var u = (s + 1) / n;
          mapCtx.beginPath();
          mapCtx.moveTo(ta.x, ta.y);
          mapCtx.lineTo(tc.x, tc.y);
          mapCtx.strokeStyle = rgbaHex(fill, 0.25 + 0.7 * u * u);
          mapCtx.lineWidth = liveTailW + 1.6 * u;
          mapCtx.lineCap = "round";
          mapCtx.lineJoin = "round";
          mapCtx.stroke();
        }
      });
      Object.keys(hist.boats).forEach(function (sail) {
        var pos = posLive(sail, ts);
        if (!pos) return;
        var p = xy(pos.lat, pos.lon);
        var info = liveMapBadge(sail);
        var ocs = info.pending;
        var fill = liveFill(sail);
        drawBoatIcon(p, pos.hdg, fill);
        if (info.place != null) {
          mapCtx.fillStyle = "#ffffff";
          mapCtx.font = "bold 9px sans-serif";
          mapCtx.textAlign = "center";
          mapCtx.textBaseline = "middle";
          mapCtx.fillText(String(info.place), p.x, p.y + 0.4);
        }
        function drawDelta(x, y, delta, align) {
          if (delta == null) return 0;
          var txt = delta > 0 ? "▲" + delta : delta < 0 ? "▼" + (-delta) : "■0";
          mapCtx.font = "bold 8px sans-serif";
          mapCtx.textAlign = align || "left";
          mapCtx.textBaseline = "middle";
          mapCtx.fillStyle = delta > 0 ? "#4ade80" : delta < 0 ? "#f87171" : "#cbd5e1";
          mapCtx.fillText(txt, x, y);
          return mapCtx.measureText(txt).width;
        }
        if (info.onMark) drawDelta(p.x - 12, p.y - 1, info.leg, "right");
        var club = (identity[sail] && (identity[sail].mapClub || identity[sail].club)) || sail;
        var lx = p.x + 12;
        var ly = p.y - 1;
        mapCtx.font = "bold 10px sans-serif";
        mapCtx.textAlign = "left";
        mapCtx.textBaseline = "middle";
        mapCtx.shadowColor = "rgba(0,0,0,0.9)";
        mapCtx.shadowBlur = 3;
        mapCtx.fillStyle = fill;
        mapCtx.fillText(club, lx, ly);
        mapCtx.shadowBlur = 0;
        if (info.onMark) {
          var cw = mapCtx.measureText(club).width;
          drawDelta(lx + cw + 3, ly, info.total, "left");
        }
      });
      drawingMap = false;
    }
    function distM(a, b) {
      if (!a || !b) return 1e9;
      var R = 6371000;
      var p1 = a.lat * Math.PI / 180;
      var p2 = b.lat * Math.PI / 180;
      var dphi = (b.lat - a.lat) * Math.PI / 180;
      var dl = (b.lon - a.lon) * Math.PI / 180;
      var x = Math.sin(dphi / 2) * Math.sin(dphi / 2) + Math.cos(p1) * Math.cos(p2) * Math.sin(dl / 2) * Math.sin(dl / 2);
      return 2 * R * Math.asin(Math.sqrt(x));
    }
    function lastPt(arr) {
      return arr && arr.length ? arr[arr.length - 1] : null;
    }
    function lineGeom(pin, rc, m1) {
      if (!pin || !rc) return null;
      var R = 6371000;
      var lat0 = (pin.lat + rc.lat) / 2;
      var lon0 = (pin.lon + rc.lon) / 2;
      var cos = Math.cos(lat0 * Math.PI / 180);
      function toxy(lat, lon) {
        return { x: (lon - lon0) * Math.PI / 180 * cos * R, y: (lat - lat0) * Math.PI / 180 * R };
      }
      var a = toxy(pin.lat, pin.lon);
      var b = toxy(rc.lat, rc.lon);
      var lx = b.x - a.x, ly = b.y - a.y;
      var len = Math.hypot(lx, ly) || 1;
      var ux = lx / len, uy = ly / len;
      var nx = -uy, ny = ux;
      if (m1) {
        var q = toxy(m1.lat, m1.lon);
        if ((q.x - a.x) * nx + (q.y - a.y) * ny > 0) { nx = -nx; ny = -ny; }
      }
      return {
        len: len,
        signed: function (lat, lon) {
          var q = toxy(lat, lon);
          return { d: (q.x - a.x) * nx + (q.y - a.y) * ny, along: (q.x - a.x) * ux + (q.y - a.y) * uy };
        }
      };
    }
    var PASS_ORDER = ["ST", "M1", "PIN", "M1b", "PINb", "M1c", "FIN"];
    var PASS_LAB = { ST: "ST", M1: "M1", PIN: "Pin", M1b: "M1", PINb: "Pin", M1c: "M1", FIN: "Finish" };
    var passTs = { ST: {}, M1: {}, PIN: {}, M1b: {}, PINb: {}, M1c: {}, FIN: {} };
    var roundArr = { M1: null, PIN: null };
    function enuOf(mark, pos) {
      var lat0 = mark.lat * Math.PI / 180;
      return {
        e: (pos.lon - mark.lon) * Math.PI / 180 * Math.cos(lat0) * 6371000,
        n: (pos.lat - mark.lat) * Math.PI / 180 * 6371000
      };
    }
    function defaultPortSpec(mark, fromPt) {
      if (!mark || !fromPt) return null;
      var e = enuOf(mark, fromPt);
      var mag = Math.hypot(e.e, e.n) || 1;
      return { ie: e.e / mag, inn: e.n / mag, sweep: 1.85 };
    }
    function markLabelAway(mark, spec, fromPt) {
      if (!mark) return { x: 0, y: 0 };
      var back = fromPt ? enuOf(mark, fromPt) : { e: 0, n: -1 };
      var mag = Math.hypot(back.e, back.n) || 1;
      var be = back.e / mag;
      var bn = back.n / mag;
      var boatE = bn;
      var boatN = -be;
      var sweep = spec && spec.sweep != null ? Number(spec.sweep) : 1.85;
      var sign = sweep >= 0 ? -1 : 1;
      var ll = meterOffset(mark.lat, mark.lon, sign * boatN * 28, sign * boatE * 28);
      return xy(ll.lat, ll.lon);
    }
    function linePassingLabel(pt, pin, rc, m1, boats) {
      if (!pt) return { x: 0, y: 0 };
      if (!pin || !rc) return xy(pt.lat, pt.lon);
      var g = startCourseNormal(startLineGeom(pin, rc), m1, boats);
      if (!g) return xy(pt.lat, pt.lon);
      var ll = meterOffset(pt.lat, pt.lon, -g.ny * 26, -g.nx * 26);
      return xy(ll.lat, ll.lon);
    }
    function markLabelBack(mark, fromPt) {
      return markLabelAway(mark, defaultPortSpec(mark, fromPt), fromPt);
    }
    function ccwDelta(a, b) {
      var d = b - a;
      while (d < 0) d += Math.PI * 2;
      while (d >= Math.PI * 2) d -= Math.PI * 2;
      return d;
    }
    function voteRound(markTrail, times, dt) {
      var rows = [];
      Object.keys(times || {}).forEach(function (sail) {
        var t = times[sail];
        if (t == null) return;
        var pts = hist.boats[sail];
        var mk = atTs(markTrail, t);
        var inn = atTs(pts, t - dt);
        var mid = atTs(pts, t);
        var out = atTs(pts, t + dt);
        if (!mk || !inn || !mid || !out) return;
        var a = enuOf(mk, inn);
        var c = enuOf(mk, mid);
        var b = enuOf(mk, out);
        var ia = Math.hypot(a.e, a.n);
        var ic = Math.hypot(c.e, c.n);
        var ib = Math.hypot(b.e, b.n);
        if (ia < 8 || ib < 8 || ic < 0.4) return;
        var a0 = Math.atan2(a.n, a.e);
        var am = Math.atan2(c.n, c.e);
        var a1 = Math.atan2(b.n, b.e);
        var onCcw = ccwDelta(a0, am) <= ccwDelta(a0, a1) + 1e-6;
        var sweep = onCcw ? ccwDelta(a0, a1) : ccwDelta(a0, a1) - Math.PI * 2;
        if (Math.abs(sweep) < 0.35) return;
        rows.push({ ie: a.e / ia, inn: a.n / ia, sweep: sweep });
      });
      if (rows.length < 2) return null;
      rows.sort(function (u, v) { return u.sweep - v.sweep; });
      var mid = rows[Math.floor(rows.length / 2)];
      return { ie: mid.ie, inn: mid.inn, sweep: mid.sweep };
    }
    function drawRoundArrow(mark, spec, color) {
      if (!mark || !spec || !mapCtx || spec.sweep == null) return;
      var inn = meterOffset(mark.lat, mark.lon, spec.inn * 24, spec.ie * 24);
      var p = xy(mark.lat, mark.lon);
      var i = xy(inn.lat, inn.lon);
      var a0 = Math.atan2(i.y - p.y, i.x - p.x);
      var a1 = a0 - spec.sweep;
      var ccw = spec.sweep > 0;
      var r = 16;
      mapCtx.save();
      mapCtx.strokeStyle = color;
      mapCtx.fillStyle = color;
      mapCtx.lineWidth = 2.4;
      mapCtx.lineCap = "round";
      mapCtx.beginPath();
      mapCtx.arc(p.x, p.y, r, a0, a1, ccw);
      mapCtx.stroke();
      var ax = p.x + r * Math.cos(a1);
      var ay = p.y + r * Math.sin(a1);
      var cw = spec.sweep < 0;
      var tx = cw ? -Math.sin(a1) : Math.sin(a1);
      var ty = cw ? Math.cos(a1) : -Math.cos(a1);
      mapCtx.beginPath();
      mapCtx.moveTo(ax + tx * 5, ay + ty * 5);
      mapCtx.lineTo(ax - tx * 4 - ty * 4.2, ay - ty * 4 + tx * 4.2);
      mapCtx.lineTo(ax - tx * 4 + ty * 4.2, ay - ty * 4 - tx * 4.2);
      mapCtx.closePath();
      mapCtx.fill();
      mapCtx.restore();
    }
    function drawActiveLegChevrons(fromPt, toPt, rgb) {
      if (!fromPt || !toPt || !mapCtx) return;
      var a = xy(fromPt.lat, fromPt.lon);
      var b = xy(toPt.lat, toPt.lon);
      var dx = b.x - a.x;
      var dy = b.y - a.y;
      var L = Math.hypot(dx, dy);
      if (L < 28) return;
      dx /= L;
      dy /= L;
      var px = -dy;
      var py = dx;
      var phase = (Date.now() % 1100) / 1100;
      var n = Math.max(5, Math.min(12, Math.floor(L / 30)));
      var sz = 11;
      rgb = rgb || "251,191,36";
      var i;
      for (i = 0; i < n; i++) {
        var f = ((i / n) + phase) % 1;
        if (f < 0.14 || f > 0.86) continue;
        var x = a.x + dx * L * f;
        var y = a.y + dy * L * f;
        var alpha = 0.22 + 0.7 * (0.5 + 0.5 * Math.sin((phase + i / n) * Math.PI * 2));
        mapCtx.beginPath();
        mapCtx.moveTo(x + dx * sz, y + dy * sz);
        mapCtx.lineTo(x - dx * sz * 0.45 + px * sz * 0.72, y - dy * sz * 0.45 + py * sz * 0.72);
        mapCtx.lineTo(x - dx * sz * 0.15, y - dy * sz * 0.15);
        mapCtx.lineTo(x - dx * sz * 0.45 - px * sz * 0.72, y - dy * sz * 0.45 - py * sz * 0.72);
        mapCtx.closePath();
        mapCtx.fillStyle = "rgba(" + rgb + "," + alpha.toFixed(3) + ")";
        mapCtx.fill();
        mapCtx.strokeStyle = "rgba(255,255,255," + (0.18 + 0.4 * alpha).toFixed(3) + ")";
        mapCtx.lineWidth = 1;
        mapCtx.stroke();
      }
    }
    function markValid(arr, ts) {
      if (!arr || arr.length < 2) return false;
      var b = atTs(arr, ts) || lastPt(arr);
      if (!b) return false;
      var a = atTs(arr, b.ts_ms - 20000) || atTs(arr, b.ts_ms - 8000);
      if (!a) return false;
      return distM(a, b) <= 8;
    }
    function stillEnough(arr, ts) {
      var b = atTs(arr, ts) || lastPt(arr);
      if (!b) return false;
      var a = atTs(arr, b.ts_ms - 20000) || atTs(arr, b.ts_ms - 8000);
      if (!a) return true;
      return distM(a, b) <= 20;
    }
    function markTravelM(arr) {
      if (!arr || arr.length < 2) return 0;
      return distM(arr[0], arr[arr.length - 1]);
    }
    function markClustered(k, ts) {
      var pos = atTs(hist.marks[k], ts);
      if (!pos) return true;
      var travel = markTravelM(hist.marks[k]);
      var keys = Object.keys(hist.marks);
      for (var i = 0; i < keys.length; i++) {
        var o = keys[i];
        if (o === k) continue;
        if (!markValid(hist.marks[o], ts)) continue;
        var op = atTs(hist.marks[o], ts);
        if (op && distM(pos, op) < 80 && markTravelM(hist.marks[o]) < travel - 40) return true;
      }
      return false;
    }
    function trailMoving(arr, ts) {
      return !stillEnough(arr, ts);
    }
    function angDiffDeg(a, b) {
      var d = (b - a) % 360;
      if (d > 180) d -= 360;
      if (d < -180) d += 360;
      return d;
    }
    function bearingDeg(lat1, lon1, lat2, lon2) {
      var p1 = lat1 * Math.PI / 180;
      var p2 = lat2 * Math.PI / 180;
      var dl = (lon2 - lon1) * Math.PI / 180;
      var x = Math.sin(dl) * Math.cos(p2);
      var y = Math.cos(p1) * Math.sin(p2) - Math.sin(p1) * Math.cos(p2) * Math.cos(dl);
      return (Math.atan2(x, y) * 180 / Math.PI + 360) % 360;
    }
    function roundingCandidates(pts, markTrail, afterTs, enterM) {
      enterM = enterM || 80;
      var leaveExtra = 8;
      var gapInbound = 15000;
      if (!pts || !markTrail || !markTrail.length) return [];
      var series = [];
      var prevTs = null;
      var i;
      for (i = 0; i < pts.length; i++) {
        var p = pts[i];
        if (afterTs != null && p.ts_ms < afterTs) continue;
        var mk = atTs(markTrail, p.ts_ms);
        if (!mk) continue;
        series.push({ p: p, d: distM(p, mk), gap: prevTs == null ? null : p.ts_ms - prevTs });
        prevTs = p.ts_ms;
      }
      var out = [];
      i = 0;
      var n = series.length;
      while (i < n) {
        var d = series[i].d;
        p = series[i].p;
        var gap = series[i].gap;
        if (d > enterM) { i += 1; continue; }
        var inbound = gap == null || gap >= gapInbound;
        if (!inbound) {
          var k = i - 1;
          while (k >= 0 && (p.ts_ms - series[k].p.ts_ms) <= 180000) {
            if (series[k].d >= enterM) { inbound = true; break; }
            k -= 1;
          }
        }
        if (p.hdg != null && !inbound) {
          mk = atTs(markTrail, p.ts_ms);
          if (mk) {
            var brg = bearingDeg(p.lat, p.lon, mk.lat, mk.lon);
            if (Math.abs(angDiffDeg(p.hdg, brg)) <= 95) inbound = true;
          }
        }
        var bestD = d;
        var bestP = p;
        var j = i;
        var left = false;
        while (j < n && (series[j].p.ts_ms - p.ts_ms) < 180000) {
          var dj = series[j].d;
          if (dj < bestD) { bestD = dj; bestP = series[j].p; }
          if (dj >= bestD + leaveExtra) { left = true; break; }
          j += 1;
        }
        if (!left && inbound && bestD <= 40 && j >= n) left = true;
        if (inbound && left && bestD <= enterM) {
          out.push(bestP.ts_ms);
          var skipUntil = bestP.ts_ms + 120000;
          while (i < n && series[i].p.ts_ms < skipUntil) i += 1;
          continue;
        }
        i += 1;
      }
      return out;
    }
    function boatHdg(pts) {
      var pos = lastPt(pts);
      if (!pos) return null;
      if (pos.hdg != null && pos.hdg !== "") return Number(pos.hdg);
      if (pts && pts.length >= 2) {
        var prev = pts[pts.length - 2];
        if (prev && prev.lat != null) return bearingDeg(prev.lat, prev.lon, pos.lat, pos.lon);
      }
      return null;
    }
    function onExitSide(pos, mark, next) {
      if (!pos || !mark || !next) return false;
      var a = enuOf(mark, next);
      var b = enuOf(mark, pos);
      return a.e * b.e + a.n * b.n > 0;
    }
    function leavingMark(pts, mark, next) {
      var pos = lastPt(pts);
      if (!pos || !mark || !next) return false;
      var d = distM(pos, mark);
      if (d < 45) return false;
      if (!onExitSide(pos, mark, next)) return false;
      var hdg = boatHdg(pts);
      if (hdg != null && !isNaN(hdg)) {
        var toNext = bearingDeg(pos.lat, pos.lon, next.lat, next.lon);
        var toMark = bearingDeg(pos.lat, pos.lon, mark.lat, mark.lon);
        if (Math.abs(angDiffDeg(hdg, toNext)) <= 90) return true;
        if (Math.abs(angDiffDeg(hdg, toMark)) >= 95) return true;
        return false;
      }
      if (pts.length >= 2) {
        return d > distM(pts[pts.length - 2], mark) + 6;
      }
      return false;
    }
    function closestAfter(pts, markTrail, afterTs) {
      var bestTs = null;
      var bestD = 1e9;
      var i;
      if (!pts || !markTrail) return { ts: null, d: bestD };
      for (i = 0; i < pts.length; i++) {
        var p = pts[i];
        if (afterTs != null && p.ts_ms < afterTs) continue;
        var mk = atTs(markTrail, p.ts_ms);
        if (!mk) continue;
        var d = distM(p, mk);
        if (d < bestD) {
          bestD = d;
          bestTs = p.ts_ms;
        }
      }
      return { ts: bestTs, d: bestD };
    }
    function trailForPass(id) {
      return id.indexOf("PIN") === 0 ? hist.pin : hist.marks["1"];
    }
    function m1Separated(ts) {
      var m1 = atTs(hist.marks["1"], ts) || lastPt(hist.marks["1"]);
      var pin = atTs(hist.pin, ts) || lastPt(hist.pin);
      if (!m1 || !pin) return false;
      return distM(m1, pin) >= 250;
    }
    function gateTimes(pts, markTrail, afterTs, enterM) {
      if (!pts || pts.length < 3 || !markTrail || !markTrail.length) return [];
      enterM = enterM || 110;
      var out = [];
      var i = 0;
      while (i < pts.length) {
        var p = pts[i];
        if (afterTs != null && p.ts_ms < afterTs) { i += 1; continue; }
        var mk = atTs(markTrail, p.ts_ms);
        if (!mk) { i += 1; continue; }
        var d = distM(p, mk);
        if (d > enterM) { i += 1; continue; }
        var approached = i === 0;
        var k = i - 1;
        while (k >= 0 && (p.ts_ms - pts[k].ts_ms) <= 120000) {
          var mkb = atTs(markTrail, pts[k].ts_ms);
          if (mkb && distM(pts[k], mkb) >= enterM - 5) { approached = true; break; }
          k -= 1;
        }
        var bestD = d;
        var bestP = p;
        var j = i;
        var left = false;
        while (j < pts.length && (pts[j].ts_ms - p.ts_ms) < 180000) {
          var mkj = atTs(markTrail, pts[j].ts_ms);
          if (mkj) {
            var dj = distM(pts[j], mkj);
            if (dj < bestD) { bestD = dj; bestP = pts[j]; }
            if (dj >= bestD + 8 && dj >= 28) { left = true; break; }
          }
          j += 1;
        }
        if (!left && approached && bestD <= 45 && j >= pts.length) left = true;
        if (approached && left && bestD <= 70) {
          var inn = atTs(pts, bestP.ts_ms - 6000) || atTs(pts, bestP.ts_ms - 3000);
          var outp = atTs(pts, bestP.ts_ms + 6000) || atTs(pts, bestP.ts_ms + 3000);
          var mkc = atTs(markTrail, bestP.ts_ms);
          var ok = true;
          if (inn && outp && mkc) {
            var dIn = distM(inn, mkc);
            var dOut = distM(outp, mkc);
            var a = enuOf(mkc, inn);
            var b = enuOf(mkc, outp);
            var magA = Math.hypot(a.e, a.n) || 1;
            var magB = Math.hypot(b.e, b.n) || 1;
            var dot = (a.e * b.e + a.n * b.n) / (magA * magB);
            if (dot > 1) dot = 1;
            if (dot < -1) dot = -1;
            var ang = Math.acos(dot);
            if (!(dIn > bestD + 3 && dOut > bestD + 3) && ang < 0.18 && bestD > 42) ok = false;
          }
          if (ok) {
            out.push(bestP.ts_ms);
            var skipUntil = bestP.ts_ms + 80000;
            while (i < pts.length && pts[i].ts_ms < skipUntil) i += 1;
            continue;
          }
        }
        i += 1;
      }
      if (!out.length) {
        var close = closestAfter(pts, markTrail, afterTs);
        var closeLim = Math.max(90, enterM - 20);
        if (close.ts != null && close.d <= closeLim) {
          var last = lastPt(pts);
          var mkL = last ? atTs(markTrail, last.ts_ms) : null;
          var leaving = mkL && distM(last, mkL) >= close.d + 6;
          var atMark = close.d <= Math.max(55, enterM * 0.4);
          if (leaving || atMark) out.push(close.ts);
        }
      }
      return out;
    }
    function localMinGates(pts, markTrail, afterTs, maxD) {
      maxD = maxD || 130;
      if (!pts || pts.length < 5 || !markTrail || !markTrail.length) return [];
      var ds = [];
      var i;
      for (i = 0; i < pts.length; i++) {
        var p = pts[i];
        if (afterTs != null && p.ts_ms < afterTs) continue;
        var mk = atTs(markTrail, p.ts_ms);
        if (!mk) continue;
        ds.push({ t: p.ts_ms, d: distM(p, mk) });
      }
      var out = [];
      for (i = 1; i < ds.length - 1; i++) {
        if (ds[i].d > maxD) continue;
        if (ds[i].d <= ds[i - 1].d && ds[i].d <= ds[i + 1].d) {
          if (!out.length || ds[i].t - out[out.length - 1] >= 80000) out.push(ds[i].t);
        }
      }
      return out;
    }
    function mergeGateList(a, b) {
      var all = (a || []).concat(b || []).sort(function (x, y) { return x - y; });
      var out = [];
      var i;
      for (i = 0; i < all.length; i++) {
        if (!out.length || all[i] - out[out.length - 1] >= 80000) out.push(all[i]);
      }
      return out;
    }
    function lineExitTimes(pts, geom, fromTs) {
      if (!geom || !pts) return [];
      return collectLineHits(pts, geom, fromTs, null).filter(function (h) {
        return h.kind === "exit";
      }).map(function (h) { return h.t; });
    }
    function firstRounding(pts, markTrail, afterTs, needM1Sep) {
      var vs = gateTimes(pts, markTrail, afterTs);
      var i;
      for (i = 0; i < vs.length; i++) {
        if (needM1Sep && !m1Separated(vs[i])) continue;
        return vs[i];
      }
      return null;
    }
    function slotM1(t) {
      var age = gunTs ? t - gunTs : 0;
      if (age < 18 * 60 * 1000) return "M1";
      if (age < 40 * 60 * 1000) return "M1b";
      return "M1c";
    }
    function slotPIN(t) {
      var age = gunTs ? t - gunTs : 0;
      if (age < 30 * 60 * 1000) return "PIN";
      return "PINb";
    }
    function nextSameSlot(id) {
      if (id === "M1") return "M1b";
      if (id === "M1b") return "M1c";
      if (id === "PIN") return "PINb";
      return null;
    }
    function placeKind(lock, kind, t) {
      if (t == null || !lock) return;
      var ids = kind === "M1" ? ["M1", "M1b", "M1c"] : ["PIN", "PINb"];
      var i;
      for (i = 0; i < ids.length; i++) {
        if (lock[ids[i]] != null && Math.abs(lock[ids[i]] - t) < 50000) return;
      }
      var id = kind === "M1" ? slotM1(t) : slotPIN(t);
      while (id && lock[id] != null) id = nextSameSlot(id);
      if (id) lock[id] = t;
    }
    function trailFromStart(pts) {
      return !!(pts && pts.length && gunTs && pts[0].ts_ms <= gunTs + 40000);
    }
    function stValid(t) {
      t = Number(t);
      return !!(gunTs && t && t >= gunTs - 90000 && t <= gunTs + 4 * 60 * 1000);
    }
    function collectLineHits(pts, geom, fromTs, toTs) {
      var hits = [];
      var prev = null;
      var i;
      for (i = 0; i < pts.length; i++) {
        var p = pts[i];
        if (fromTs != null && p.ts_ms < fromTs) continue;
        if (toTs != null && p.ts_ms > toTs) break;
        var sg = geom.signed(p.lat, p.lon);
        if (prev) {
          var on = (sg.along >= -80 && sg.along <= geom.len + 80) || (prev.along >= -80 && prev.along <= geom.len + 80);
          if (on) {
            if (prev.d > 0 && sg.d <= 0) {
              var frac = prev.d === sg.d ? 1 : prev.d / (prev.d - sg.d);
              hits.push({ t: Math.round(prev.ts + (p.ts_ms - prev.ts) * frac), kind: "enter" });
            } else if (prev.d <= 0 && sg.d > 0) {
              var frac = sg.d === prev.d ? 1 : (-prev.d) / (sg.d - prev.d);
              hits.push({ t: Math.round(prev.ts + (p.ts_ms - prev.ts) * frac), kind: "exit" });
            }
          }
        }
        prev = { d: sg.d, ts: p.ts_ms, along: sg.along };
      }
      return hits;
    }
    function courseEnters(pts, geom, fromTs, toTs) {
      var hits = [];
      var prev = null;
      var i;
      if (!pts || !geom) return hits;
      for (i = 0; i < pts.length; i++) {
        var p = pts[i];
        if (fromTs != null && p.ts_ms < fromTs) continue;
        if (toTs != null && p.ts_ms > toTs) break;
        var sg = geom.signed(p.lat, p.lon);
        if (prev && prev.d > 0 && sg.d <= 0) {
          var frac = prev.d === sg.d ? 1 : prev.d / (prev.d - sg.d);
          var t = Math.round(prev.ts + (p.ts_ms - prev.ts) * frac);
          var along = prev.along + (sg.along - prev.along) * frac;
          if (along >= -80 && along <= geom.len + 80) hits.push(t);
        }
        prev = { d: sg.d, along: sg.along, ts: p.ts_ms };
      }
      return hits;
    }
    function liveStartGeom() {
      var pin = gunTs ? atTs(hist.pin, gunTs) : lastPt(hist.pin);
      var rc = gunTs ? atTs(hist.rc, gunTs) : lastPt(hist.rc);
      if (!pin || !rc) return null;
      var base = lineGeom(pin, rc, null);
      if (!base) return null;
      var ds = [];
      Object.keys(hist.boats).forEach(function (sail) {
        var pts = hist.boats[sail] || [];
        var p = gunTs ? atTs(pts, gunTs) : lastPt(pts);
        if (!p) return;
        ds.push(base.signed(p.lat, p.lon).d);
      });
      ds.sort(function (a, b) { return a - b; });
      var flip = ds.length ? ds[Math.floor(ds.length / 2)] < 0 : false;
      return {
        len: base.len,
        signed: function (lat, lon) {
          var s = base.signed(lat, lon);
          if (flip) s.d = -s.d;
          return s;
        }
      };
    }
    function packedStartOf(sail) {
      if (!sail || !packedStarts) return null;
      if (packedStarts[sail]) return packedStarts[sail];
      function n(s) { return String(s || "").toUpperCase().replace(/\s+/g, ""); }
      var want = n(sail);
      var keys = Object.keys(packedStarts);
      var i, kn;
      for (i = 0; i < keys.length; i++) {
        kn = n(keys[i]);
        if (kn === want) return packedStarts[keys[i]];
      }
      var id = identity[sail] || {};
      var alts = [id.mapClub, id.clubRaw, id.club].map(n).filter(Boolean);
      for (i = 0; i < keys.length; i++) {
        kn = n(keys[i]);
        if (alts.indexOf(kn) >= 0) return packedStarts[keys[i]];
      }
      var academy = want.indexOf("ACADEMY") >= 0 || want === "RCYCA" || alts.indexOf("RCYCA") >= 0 || alts.some(function (t) { return t.indexOf("ACADEMY") >= 0; });
      if (academy) {
        for (i = 0; i < keys.length; i++) {
          kn = n(keys[i]);
          if (kn.indexOf("ACADEMY") >= 0 || kn === "RCYCA") return packedStarts[keys[i]];
        }
      }
      return null;
    }
    function startTsForSail(sail, pts, geom) {
      var packed = packedStartOf(sail);
      if (packed && packed.st_ms != null && stValid(packed.st_ms)) return Number(packed.st_ms);
      if (!geom || !gunTs || !pts || pts.length < 2) return null;
      var ocs = liveOcsOn(sail);
      var hits = courseEnters(pts, geom, ocs ? gunTs - 90000 : gunTs - 5000, gunTs + 180000);
      if (ocs) return hits.length >= 2 ? hits[1] : null;
      var i;
      for (i = 0; i < hits.length; i++) {
        if (hits[i] >= gunTs - 500) return hits[i];
      }
      return null;
    }
    var packedStarts = {};
    var packedStartsGun = null;
    var lockedSt = {};
    var lockedPass = {};
    function persistSt() {
      if (!gunTs) return;
      try { sessionStorage.setItem("lipton-live-st-v3-" + gunTs, JSON.stringify(lockedSt)); } catch (e2) {}
    }
    function loadSt() {
      if (!gunTs) return;
      try {
        var raw = sessionStorage.getItem("lipton-live-st-v3-" + gunTs);
        if (raw) {
          var parsed = JSON.parse(raw);
          if (parsed && typeof parsed === "object") {
            lockedSt = parsed;
            Object.keys(lockedSt).forEach(function (s) {
              if (!stValid(lockedSt[s])) delete lockedSt[s];
            });
          }
        }
      } catch (e3) {}
      try {
        var rawP = sessionStorage.getItem("lipton-live-pass-v1-" + gunTs);
        if (rawP) {
          var parsedP = JSON.parse(rawP);
          if (parsedP && parsedP.lockedPass) lockedPass = parsedP.lockedPass;
          if (parsedP && parsedP.armedLegIdx != null) armedLegIdx = Number(parsedP.armedLegIdx) || 0;
        }
      } catch (e4) {}
      loadHist();
    }
    function persistPass() {
      if (!gunTs) return;
      try {
        sessionStorage.setItem("lipton-live-pass-v1-" + gunTs, JSON.stringify({
          lockedPass: lockedPass,
          armedLegIdx: armedLegIdx
        }));
      } catch (e5) {}
    }
    function gpsRoster() {
      return FLEET_17.filter(function (sail) {
        var pts = hist.boats[sail];
        return pts && pts.length >= 2;
      });
    }
    function afterTsForPid(lock, pid) {
      if (pid === "M1") return (lock.ST != null ? lock.ST + 6000 : (gunTs ? gunTs + 6000 : 0));
      if (pid === "PIN") return lock.M1 != null ? lock.M1 + 25000 : null;
      if (pid === "M1b") return lock.PIN != null ? lock.PIN + 25000 : null;
      if (pid === "PINb") return lock.M1b != null ? lock.M1b + 25000 : null;
      if (pid === "M1c") return lock.PINb != null ? lock.PINb + 25000 : null;
      if (pid === "FIN") return lock.M1c != null ? lock.M1c + 20000 : (lock.PINb != null ? lock.PINb + 45000 : null);
      return null;
    }
    function finishTsFor(pts, lock, geom, pinNow) {
      if (!geom) return null;
      var after = null;
      if (lock.M1c) after = lock.M1c + 20000;
      else if (lock.PINb) after = lock.PINb + 45000;
      if (after == null) return null;
      var finHits = lineExitTimes(pts, geom, after);
      if (!finHits.length) finHits = courseEnters(pts, geom, after, null);
      var fi;
      for (fi = 0; fi < finHits.length; fi++) {
        var ft = finHits[fi];
        var fp = atTs(pts, ft) || lastPt(pts);
        if (!fp) continue;
        var sg = geom.signed(fp.lat, fp.lon);
        var alongOk = true;
        if (sg && (sg.along < -80 || sg.along > geom.len + 80)) alongOk = false;
        if (alongOk) return ft;
      }
      return null;
    }
    function detectPidTs(sail, pts, pid, geom, pinNow) {
      var lock = lockedPass[sail] || {};
      var after = afterTsForPid(lock, pid);
      if (after == null) return null;
      if (pid === "FIN") return finishTsFor(pts, lock, geom, pinNow);
      var windward = pid.indexOf("M1") === 0;
      var trail = pid.indexOf("PIN") === 0 ? hist.pin : hist.marks["1"];
      return firstRounding(pts, trail, after, windward);
    }
    function captureArmedMark(geom, pinNow) {
      gpsRoster().forEach(function (sail) {
        if (!lockedPass[sail]) lockedPass[sail] = {};
        var lock = lockedPass[sail];
        var pts = hist.boats[sail] || [];
        var afterLast = lock.PINb || lock.M1b || lock.PIN || lock.M1 || (gunTs ? gunTs + 4000 : 0);
        if (lock.M1c == null) {
          mergeGateList(
            gateTimes(pts, hist.marks["1"], afterLast + 25000).filter(function (t) { return m1Separated(t); }),
            localMinGates(pts, hist.marks["1"], afterLast + 25000, 120)
          ).forEach(function (t) { placeKind(lock, "M1", t); });
        }
        if (lock.PINb == null) {
          mergeGateList(
            gateTimes(pts, hist.pin, afterLast + 25000, 150),
            localMinGates(pts, hist.pin, afterLast + 25000, 150)
          ).forEach(function (t) { placeKind(lock, "PIN", t); });
        }
        if (lock.FIN == null) {
          var ft = finishTsFor(pts, lock, geom, pinNow);
          if (ft != null) lock.FIN = ft;
        }
      });
      var roster = gpsRoster();
      var i;
      armedLegIdx = 0;
      for (i = 0; i < ROUND_LEGS.length; i++) {
        var id = ROUND_LEGS[i];
        var n = roster.filter(function (sail) {
          return lockedPass[sail] && lockedPass[sail][id] != null;
        }).length;
        var elapsed = gunTs ? Date.now() - gunTs : 0;
        var skipEmpty = n === 0 && (
          (id === "M1" && elapsed > 20 * 60 * 1000) ||
          (id === "PIN" && elapsed > 32 * 60 * 1000) ||
          (id === "M1b" && elapsed > 50 * 60 * 1000) ||
          (id === "PINb" && elapsed > 62 * 60 * 1000)
        );
        if (n > 0 && n < roster.length) {
          if (id === "M1b" && elapsed > 38 * 60 * 1000) {
            armedLegIdx = Math.min(i + 1, ROUND_LEGS.length - 1);
            continue;
          }
          armedLegIdx = i;
          break;
        }
        if (n === 0 && !skipEmpty) {
          armedLegIdx = i;
          break;
        }
        armedLegIdx = Math.min(i + 1, ROUND_LEGS.length - 1);
      }
    }
    function detectLivePasses() {
      passTs = { ST: {}, M1: {}, PIN: {}, M1b: {}, PINb: {}, M1c: {}, FIN: {} };
      var pinNow = lastPt(hist.pin);
      var rcNow = lastPt(hist.rc);
      var pinGun = gunTs ? atTs(hist.pin, gunTs) : null;
      var rcGun = gunTs ? atTs(hist.rc, gunTs) : null;
      var pin = pinGun || pinNow;
      var rc = rcGun || rcNow;
      var m1now = lastPt(hist.marks["1"]);
      var geom = liveStartGeom() || lineGeom(pin, rc, stillEnough(hist.marks["1"], playTs) ? m1now : null);
      Object.keys(hist.boats).forEach(function (sail) {
        var pts = hist.boats[sail] || [];
        var st = startTsForSail(sail, pts, geom);
        if (st != null && !stValid(st)) st = null;
        if (st != null) {
          lockedSt[sail] = st;
        } else if (stValid(lockedSt[sail])) {
          st = lockedSt[sail];
        } else {
          delete lockedSt[sail];
        }
        if (st != null) passTs.ST[sail] = st;
        if (!lockedPass[sail]) lockedPass[sail] = {};
        if (st != null) lockedPass[sail].ST = st;
      });
      FLEET_17.forEach(function (sail) {
        if (!lockedPass[sail]) lockedPass[sail] = {};
      });
      captureArmedMark(geom, pinNow);
      Object.keys(lockedPass).forEach(function (sail) {
        var lock = lockedPass[sail] || {};
        delete lock.PINc;
        delete lock.M1d;
        delete lock.PINd;
        Object.keys(lock).forEach(function (id) {
          if (passTs[id]) passTs[id][sail] = lock[id];
        });
      });
      persistSt();
      persistPass();
      var startMid = (pin && rc)
        ? { lat: (pin.lat + rc.lat) / 2, lon: (pin.lon + rc.lon) / 2 }
        : pin;
      roundArr.M1 = voteRound(hist.marks["1"], passTs.M1, 25000) || defaultPortSpec(m1now, startMid);
      roundArr.PIN = voteRound(hist.pin, passTs.PIN, 28000) || defaultPortSpec(pinNow, m1now || startMid);
    }
    function rankMap(id) {
      return Object.keys(passTs[id] || {}).sort(function (a, b) {
        return passTs[id][a] - passTs[id][b];
      }).reduce(function (m, s, i) { m[s] = i + 1; return m; }, {});
    }
    function livePassAt(sail, id) {
      var t = passTs[id] && passTs[id][sail];
      if (t == null) return null;
      var cut = atLive ? Date.now() + 4000 : playTs;
      return t <= cut ? t : null;
    }
    function liveMapBadge(sail) {
      var last = -1;
      for (var i = 0; i < PASS_ORDER.length; i++) {
        if (livePassAt(sail, PASS_ORDER[i]) != null) last = i;
      }
      var stR = rankMap("ST");
      var lastId = last >= 0 ? PASS_ORDER[last] : null;
      var place = lastId ? rankMap(lastId)[sail] : null;
      if (place == null) place = stR[sail] || null;
      var leg = null;
      var total = null;
      if (last > 0 && place != null) {
        var prevId = PASS_ORDER[last - 1];
        var prevR = rankMap(prevId)[sail];
        if (prevR != null) leg = prevR - place;
        if (stR[sail] != null) total = stR[sail] - place;
      }
      return {
        place: place,
        pending: liveOcsPending(sail),
        onMark: last > 0,
        leg: leg,
        total: total
      };
    }
    var wrapEl = document.getElementById("lipton-dev-table-wrap");
    var tbody = document.getElementById("lipton-dev-tbody");
    var headRow = document.getElementById("lipton-dev-thead-row");
    var lastLiveTableKey = "";
    if (wrapEl) wrapEl.hidden = false;
    function liveIdent(sail) {
      if (identity[sail]) return identity[sail];
      var keys = Object.keys(identity);
      var i;
      for (i = 0; i < keys.length; i++) {
        var id = identity[keys[i]] || {};
        if (id.mapClub === sail || id.club === sail || id.clubRaw === sail) return id;
      }
      return {};
    }
    function liveBowCell(id) {
      if (!id || id.bow == null || id.bow === "") return "";
      if (id.boatHref) return "<span class=\"wc-boat-linked\"><a href=\"" + esc(id.boatHref) + "\">" + esc(id.bow) + "</a></span>";
      return esc(id.bow);
    }
    function liveNameCell(id, sail) {
      if (id && id.nameHref) {
        return "<a href=\"" + esc(id.nameHref) + "\" class=\"rs-boat-name-sponsors rs-boat-name-sponsors--link\" title=\"" + esc(id.title || "") + "\">" + (id.nameInner || esc(id.title || sail)) + "</a>";
      }
      if (id && id.nameInner) return id.nameInner;
      return esc((id && id.title) || sail);
    }
    function liveClubCell(id, pending) {
      if (!id) return "";
      var club = id.club || id.mapClub || "";
      if (id.clubLogo) {
        var cls = "rs-club-with-logo" + (pending ? " ocs-club" : "");
        var name = id.clubHref ? ("<a href=\"" + esc(id.clubHref) + "\">" + esc(club) + "</a>") : esc(club);
        return "<span class=\"" + cls + "\">" + name + "<img class=\"rs-club-row-logo\" src=\"" + esc(id.clubLogo) + "\" alt=\"" + esc(club) + "\" title=\"" + esc(club) + "\"></span>";
      }
      return esc(club);
    }
    function liveOcsOn(sail) {
      var packed = packedStartOf(sail);
      if (packed && typeof packed.ocs === "boolean") return packed.ocs === true;
      var id = liveIdent(sail);
      var self = [sail, id.mapClub, id.clubRaw].map(function (x) {
        return String(x || "").toUpperCase().replace(/\s+/g, "");
      }).filter(Boolean);
      var academy = self.indexOf("RCYCA") >= 0 || self.some(function (t) { return t.indexOf("ACADEMY") >= 0; });
      var i;
      for (i = 0; i < liveOcs.length; i++) {
        var o = String(liveOcs[i] || "").toUpperCase().replace(/\s+/g, "");
        if (!o) continue;
        if (academy && o === "RCYC") continue;
        if (self.indexOf(o) >= 0) return true;
      }
      return false;
    }
    function liveOcsPending(sail) {
      if (!liveOcsOn(sail)) return false;
      if (livePassAt(sail, "ST") != null) return false;
      var marks = ["M1", "PIN", "M1b", "PINb", "M1c", "FIN"];
      var i;
      for (i = 0; i < marks.length; i++) {
        if (livePassAt(sail, marks[i]) != null) return false;
      }
      return true;
    }
    function fmtBehindFirst(t, first) {
      if (t == null || first == null) return "";
      var sec = (t - first) / 1000;
      if (sec <= -0.05) return sec.toFixed(1);
      if (sec < 0.05) return "0.0";
      return "+" + sec.toFixed(1);
    }
    function liveBoatIcon(sail, rank) {
      var fill = (LIVE_BOAT_COLORS && LIVE_BOAT_COLORS[sail]) || "#94a3b8";
      var label = rank != null ? String(rank) : "";
      return "<svg class=\"lipton-boat-dot r10-live-icon\" viewBox=\"0 0 24 24\" width=\"36\" height=\"36\" aria-hidden=\"true\"><circle cx=\"12\" cy=\"13.2\" r=\"8.1\" fill=\"" + fill + "\" stroke=\"#fff\" stroke-width=\"1.5\"/><polygon points=\"12,3 15.8,8.4 8.2,8.4\" fill=\"" + fill + "\" stroke=\"#fff\" stroke-width=\"1.1\"/><text x=\"12\" y=\"16\" text-anchor=\"middle\" fill=\"#fff\" font-size=\"8\" font-weight=\"800\">" + esc(label) + "</text></svg>";
    }
    function deltaSpan(gained) {
      if (gained == null) return "";
      var n, cls, label, tri;
      if (gained > 0) { n = String(gained); cls = "place-delta--up"; label = "Gained " + gained; tri = "up"; }
      else if (gained < 0) { n = String(-gained); cls = "place-delta--down"; label = "Lost " + n; tri = "down"; }
      else { n = "0"; cls = "place-delta--same"; label = "No change"; tri = "same"; }
      return "<span class=\"place-delta " + cls + "\" title=\"" + label + "\" aria-label=\"" + label + "\"><i class=\"ld-tri ld-tri--" + tri + "\" aria-hidden=\"true\"></i>" + n + "</span>";
    }
    function usedPassIds() {
      return PASS_ORDER.slice();
    }
    function fillHoldHead() {
      if (!headRow) return;
      headRow.innerHTML = "<th class=\"rank-col\">Rank</th><th class=\"wc-meta-col\">Bow</th><th class=\"boat-name-col\">Boat Name</th><th class=\"club-col\">Club</th><th class=\"timer-col\" title=\"Start\"><span class=\"ld-mark-lab\">ST</span></th>";
    }
    function renderHoldOrArmedTable() {
      if (!tbody) return;
      if (wrapEl) wrapEl.hidden = false;
      fillHoldHead();
      var sails;
      if (devHoldR9) {
        sails = R9_FINISH_ORDER.slice();
      } else {
        sails = FLEET_17.slice();
      }
      Object.keys(identity).forEach(function (s) {
        if (sails.indexOf(s) < 0) sails.push(s);
      });
      sails = sails.slice(0, 17);
      var key = (devHoldR9 ? "hold9" : "armed10") + "|" + sails.join(",");
      if (key === lastLiveTableKey) return;
      lastLiveTableKey = key;
      var html = "";
      sails.forEach(function (sail, i) {
        var id = liveIdent(sail);
        var rank = i + 1;
        var medal = "";
        if (devHoldR9) {
          if (rank === 1) medal = " medal-gold";
          else if (rank === 2) medal = " medal-silver";
          else if (rank === 3) medal = " medal-bronze";
        }
        html += "<tr class=\"" + medal + "\" data-boat=\"" + esc(sail) + "\">";
        html += "<td class=\"rank-col rank-col--live-icon\">" + liveBoatIcon(sail, rank || null) + "</td>";
        html += "<td class=\"wc-meta-col\">" + liveBowCell(id) + "</td>";
        html += "<td class=\"boat-name-col\">" + liveNameCell(id, sail) + "</td>";
        html += "<td class=\"club-col\">" + liveClubCell(id, false) + "</td>";
        html += "<td class=\"timer-col\"></td>";
        html += "</tr>";
      });
      tbody.innerHTML = html;
    }
    function syncDevRacePhase(data) {
      data = data || snap || {};
      var n = Number(data.race_number || liveRaceN || 0) || 0;
      var d = (data.delta_ms != null && data.delta_ms !== "") ? Number(data.delta_ms) : null;
      if (d == null && data.gun_ts_ms != null) d = Date.now() - Number(data.gun_ts_ms);
      var isArmed = n === 10 && (!!data.armed || (d != null && d < 0) || data.sign === "T-");
      var isLive10 = n === 10 && !isArmed && (d != null && d >= 0);
      devArmed = isArmed;
      devLiveR10 = isLive10;
      devHoldR9 = !isArmed && !isLive10;
      liveTablePhase = devArmed ? "armed10" : (devLiveR10 ? "live10" : "hold9");
      if (devHoldR9) setRaceTableLabel(9, true);
      else if (devArmed) setRaceTableLabel(10, true, "ARMED");
      else setRaceTableLabel(10, true, "LIVE");
    }
    function fillLiveHead(used) {
      if (!headRow) return;
      var html = "<th class=\"rank-col\">Rank</th><th class=\"wc-meta-col\">Bow</th><th class=\"boat-name-col\">Boat Name</th><th class=\"club-col\">Club</th>";
      used.forEach(function (id, i) {
        var lab = PASS_LAB[id] || id;
        var prevLab = i > 0 ? (PASS_LAB[used[i - 1]] || used[i - 1]) : "Start";
        if (i > 0) html += "<th class=\"place-delta-col\" title=\"Places gained or lost " + prevLab + " → " + lab + "\">±</th>";
        html += "<th class=\"timer-col\" title=\"" + (id === "ST" ? "Start" : prevLab + " → " + lab) + "\"><span class=\"ld-mark-lab\">" + lab + "</span></th>";
      });
      if (used.length > 1) {
        html += "<th class=\"place-delta-col ld-overall-head\" title=\"Overall places vs start\"><span class=\"ld-fin-legend\" aria-hidden=\"true\"><i class=\"ld-tri ld-tri--up\"></i><i class=\"ld-tri ld-tri--down\"></i></span></th>";
      }
      headRow.innerHTML = html;
    }
    function renderLiveTable() {
      if (!tbody) return;
      if (wrapEl) wrapEl.hidden = false;
      if (devHoldR9) {
        renderHoldOrArmedTable();
        return;
      }
      var raceOver = !!(snap && (snap.holding_last || /finish/i.test(String(snap.stage || ""))));
      var used = PASS_ORDER.slice();
      var ranks = {};
      PASS_ORDER.forEach(function (id) { ranks[id] = rankMap(id); });
      var firstSt = null;
      Object.keys(passTs.ST).forEach(function (s) {
        if (liveOcsOn(s)) return;
        var t = livePassAt(s, "ST");
        if (t == null) return;
        if (firstSt == null || t < firstSt) firstSt = t;
      });
      var rowSails = FLEET_17.slice();
      Object.keys(hist.boats).forEach(function (s) {
        if (rowSails.indexOf(s) < 0) rowSails.push(s);
      });
      var rows = rowSails.map(function (sail) {
        var times = {};
        var far = 0;
        var farTs = null;
        PASS_ORDER.forEach(function (id, i) {
          var t = livePassAt(sail, id);
          times[id] = t;
          if (t != null) { far = i + 1; farTs = t; }
        });
        var pts = hist.boats[sail] || [];
        var m1 = lastPt(hist.marks["1"]);
        var pinPt = lastPt(hist.pin);
        var pos = lastPt(pts);
        var elapsed = gunTs ? ((atLive ? Date.now() : playTs) - gunTs) : 0;
        if (!raceOver && far === 3 && leavingMark(pts, m1, pinPt)) {
          far = 4;
          farTs = null;
        }
        if (times.FIN != null) {
          far = 8;
          farTs = times.FIN;
        } else if (!raceOver && times.M1c != null) {
          if (pos && m1 && distM(pos, m1) > 55) {
            far = 7;
            farTs = null;
          }
        } else if (!raceOver && pos && m1 && pinPt && elapsed > 28 * 60 * 1000) {
          var dM1 = distM(pos, m1);
          var dPin = distM(pos, pinPt);
          if (times.PIN == null && times.PINb == null && dM1 > 350 && dPin < dM1 - 40 && far < 4) {
            far = 4;
            farTs = null;
          }
        }
        return { sail: sail, times: times, far: far, farTs: farTs };
      });
      function distToFinishLine(pos) {
        var pin = lastPt(hist.pin);
        var rc = lastPt(hist.rc);
        if (!pos || !pin || !rc) return 9e9;
        var R = 6371000;
        var cos = Math.cos(((pin.lat + rc.lat) / 2) * Math.PI / 180);
        function xyOf(p) {
          return {
            x: (p.lon - pin.lon) * Math.PI / 180 * cos * R,
            y: (p.lat - pin.lat) * Math.PI / 180 * R
          };
        }
        var a = xyOf(pin);
        var b = xyOf(rc);
        var p = xyOf(pos);
        var vx = b.x - a.x;
        var vy = b.y - a.y;
        var len2 = vx * vx + vy * vy || 1;
        var t = ((p.x - a.x) * vx + (p.y - a.y) * vy) / len2;
        if (t < 0) t = 0;
        if (t > 1) t = 1;
        return Math.hypot(p.x - a.x - t * vx, p.y - a.y - t * vy);
      }
      function distNext(sail, far) {
        var pos = lastPt(hist.boats[sail]);
        if (!pos) return 9e9;
        if (far >= 7) return distToFinishLine(pos);
        var mk = (far <= 1 || far === 3 || far === 5) ? lastPt(hist.marks["1"]) : lastPt(hist.pin);
        if (!mk) return 9e9;
        return distM(pos, mk);
      }
      rows.sort(function (a, b) {
        if (b.far !== a.far) return b.far - a.far;
        if (a.farTs != null && b.farTs != null && a.farTs !== b.farTs) return a.farTs - b.farTs;
        if (a.farTs != null && b.farTs == null) return -1;
        if (b.farTs != null && a.farTs == null) return 1;
        if (raceOver) return String(a.sail).localeCompare(String(b.sail));
        return distNext(a.sail, a.far) - distNext(b.sail, b.far);
      });
      rows.forEach(function (r, i) { r.rank = i + 1; });
      var key = used.join(",") + "|" + rows.map(function (r) {
        var distBit = raceOver ? "x" : String(Math.round(distNext(r.sail, r.far) / 8));
        return r.sail + ":" + r.rank + ":" + r.far + ":" + distBit + ":" + PASS_ORDER.map(function (id) { return r.times[id] || ""; }).join(":");
      }).join("|");
      if (key === lastLiveTableKey) return;
      lastLiveTableKey = key;
      fillLiveHead(used);
      var showOverall = used.length > 1;
      var html = "";
      rows.forEach(function (r) {
        var id = liveIdent(r.sail);
        var ocs = liveOcsPending(r.sail);
        var medal = "";
        if (r.rank === 1) medal = " medal-gold";
        else if (r.rank === 2) medal = " medal-silver";
        else if (r.rank === 3) medal = " medal-bronze";
        html += "<tr class=\"" + medal + (ocs ? " ocs-pending" : "") + "\" data-boat=\"" + esc(r.sail) + "\">";
        html += "<td class=\"rank-col rank-col--live-icon\">" + liveBoatIcon(r.sail, r.rank) + "</td>";
        html += "<td class=\"wc-meta-col\">" + liveBowCell(id) + "</td>";
        html += "<td class=\"boat-name-col\">" + liveNameCell(id, r.sail) + "</td>";
        html += "<td class=\"club-col\">" + liveClubCell(id, ocs) + "</td>";
        used.forEach(function (pid, i) {
          if (i > 0) {
            var prev = used[i - 1];
            var d = (r.times[prev] && r.times[pid] && ranks[prev][r.sail] && ranks[pid][r.sail]) ? (ranks[prev][r.sail] - ranks[pid][r.sail]) : null;
            html += "<td class=\"place-delta-col\">" + deltaSpan(d) + "</td>";
          }
          var cell = "";
          if (pid === "ST") {
            var hasGps = hist.boats[r.sail] && hist.boats[r.sail].length;
            var hasMarks = r.times.ST != null || r.times.M1 != null || r.times.PIN != null;
            if (!hasGps && !hasMarks) cell = "NO GPS";
            else if (r.times.ST == null) cell = liveOcsOn(r.sail) ? "OCS" : "";
            else {
              var gap = fmtBehindFirst(r.times.ST, firstSt);
              cell = liveOcsOn(r.sail) ? ("OCS " + gap) : gap;
            }
          }
          else if (pid === "FIN" && r.times.FIN && gunTs) {
            cell = fmtClock(r.times.FIN - gunTs);
          }
          else if (r.times[pid]) {
            var prevId = i > 0 ? used[i - 1] : null;
            var prevT = prevId ? r.times[prevId] : null;
            if (prevT) cell = fmtClock(r.times[pid] - prevT);
          }
          html += "<td class=\"timer-col\">" + cell + "</td>";
        });
        if (showOverall) {
          var lastId = null;
          for (var p = used.length - 1; p >= 0; p--) {
            if (used[p] !== "ST" && r.times[used[p]] != null) { lastId = used[p]; break; }
          }
          var overall = (lastId && ranks.ST[r.sail] && ranks[lastId][r.sail]) ? (ranks.ST[r.sail] - ranks[lastId][r.sail]) : null;
          html += "<td class=\"place-delta-col\">" + deltaSpan(overall) + "</td>";
        }
        html += "</tr>";
      });
      tbody.innerHTML = html;
    }
    function applySnap(data) {
      if (!data) return;
      var incomingGun = data.gun_ts_ms != null ? Number(data.gun_ts_ms) : null;
      var newRaceGun = incomingGun && gunTs && incomingGun !== gunTs;
      if (gunTs && liveRaceN && Number(data.race_number) !== 10 && (data.waiting || !incomingGun) && !newRaceGun) {
        data = Object.assign({}, data, {
          waiting: false,
          gun_ts_ms: gunTs,
          race_number: liveRaceN
        });
      }
      if (!data.ok && !(data.boats && Object.keys(data.boats).length)) return;
      var n = data.race_number || null;
      if (n && liveRaceN && n !== liveRaceN && !newRaceGun && Number(data.race_number) !== 10) n = liveRaceN;
      if (n && liveRaceN && n !== liveRaceN && newRaceGun) {
        hist = { boats: {}, marks: {}, pin: [], rc: [] };
        loadedHistory = false;
        catchupOk = false;
        lockedSt = {};
        lockedPass = {};
        gunTs = null;
        didFit = false;
      }
      liveRaceN = n || liveRaceN;
      syncDevRacePhase(data);
      if (data.holding_last || /finish/i.test(String(data.stage || ""))) {
        liveHeldN = Number(data.race_number || liveRaceN || 0) || liveHeldN;
      } else {
        liveHeldN = 0;
      }
      renderRaceBoxes(raceMeta);
      if (Array.isArray(data.ocs)) liveOcs = data.ocs.slice();
      if (data.clock_lag_ms != null && Number(data.clock_lag_ms) < 5000) {
        LIVE_CLOCK_LAG_MS = Number(data.clock_lag_ms);
      } else {
        LIVE_CLOCK_LAG_MS = 2000;
      }
      snap = data;
      if (data.waiting && !data.gun_ts_ms && !gunTs) gunTs = null;
      else if (data.gun_ts_ms) {
        var nextGun = Number(data.gun_ts_ms);
        if (nextGun !== gunTs) {
          gunTs = nextGun;
          lockedSt = {};
          loadSt();
        } else {
          gunTs = nextGun;
        }
      }
      Object.keys(data.boats || {}).forEach(function (sail) {
        var b = data.boats[sail];
        hist.boats[sail] = mergeTrail(hist.boats[sail] || [], b.trail && b.trail.length ? b.trail : [b]);
      });
      Object.keys(data.marks || {}).forEach(function (k) {
        var m = data.marks[k];
        hist.marks[k] = mergeTrail(hist.marks[k] || [], m.trail && m.trail.length ? m.trail : [m]);
      });
      if (data.pin) hist.pin = mergeTrail(hist.pin, data.pin.trail && data.pin.trail.length ? data.pin.trail : [data.pin]);
      if (data.committee) hist.rc = mergeTrail(hist.rc, data.committee.trail && data.committee.trail.length ? data.committee.trail : [data.committee]);
      paintClock();
      syncScrub();
      var label = "";
      if (data.race_number) label = "RACE " + data.race_number;
      if (nameEl) {
        nameEl.textContent = label;
        hud.classList.toggle("is-nameless", !label);
      }
      if (!didFit && pinReady()) {
        fitLive();
        didFit = true;
      }
      applyPackedPasses();
      maybeDetect();
    }
    function pinReady() {
      return hist.pin.length && hist.rc.length && Object.keys(hist.boats).length;
    }
    var lastDetectAt = 0;
    var lastPersistAt = 0;
    function maybeDetect() {
      var now = Date.now();
      if (now - lastDetectAt < 100) return;
      lastDetectAt = now;
      detectLivePasses();
      renderLiveTable();
      if (now - lastPersistAt > 2000) {
        lastPersistAt = now;
        persistHist();
      }
    }
    var lastPassesDoc = null;
    function applyPackedPasses(data) {
      if (data) lastPassesDoc = data;
      data = data || lastPassesDoc;
      if (!data) return false;
      var pg = data.gun_ts_ms != null ? Number(data.gun_ts_ms) : null;
      if (!pg) return false;
      if (!gunTs) {
        gunTs = pg;
        loadSt();
      } else if (Math.abs(pg - gunTs) > 120000) {
        return false;
      }
      packedStartsGun = pg;
      if (Array.isArray(data.ocs) && !liveOcs.length) liveOcs = data.ocs.slice();
      if (data.starts) {
        packedStarts = data.starts;
        Object.keys(packedStarts).forEach(function (sail) {
          var st = packedStarts[sail] && packedStarts[sail].st_ms;
          if (stValid(st)) lockedSt[sail] = Number(st);
        });
      }
      Object.keys(data.lockedPass || {}).forEach(function (sail) {
        if (!lockedPass[sail]) lockedPass[sail] = {};
        var src = data.lockedPass[sail] || {};
        Object.keys(src).forEach(function (id) {
          if (src[id] == null) return;
          if (lockedPass[sail][id] == null || id === "FIN" || id === "M1c") {
            lockedPass[sail][id] = Number(src[id]);
          }
        });
      });
      var delta = Date.now() - gunTs;
      syncDevRacePhase({
        race_number: Number(data.race_number || 10),
        gun_ts_ms: gunTs,
        delta_ms: delta,
        sign: delta >= 0 ? "T+" : "T-"
      });
      fillLiveChecksum(data.checksum);
      return true;
    }
    function fillLiveChecksum(cs) {
      var el = document.getElementById("lipton-dev-checksum");
      if (!el) return;
      cs = cs || (lastPassesDoc && lastPassesDoc.checksum) || {};
      var bits = [];
      if (cs.ok) bits.push("marks ok");
      else if (cs.gaps && cs.gaps.length) {
        bits.push("gaps " + cs.gaps.map(function (g) {
          return g.id + " " + (g.missing || []).join(" ");
        }).join(" · "));
      }
      var san = cs.sanity || {};
      if (san.ok) {
        bits.push("± ok");
        bits.push("times ok");
      } else {
        if (san.place_fail && san.place_fail.length) bits.push("± fail " + san.place_fail.join(" "));
        else bits.push("± ok");
        if (san.time_fail && san.time_fail.length) bits.push("times " + san.time_fail.join(" "));
        else if (san.leg_fail && san.leg_fail.length) bits.push("legs " + san.leg_fail.join(" "));
        else bits.push("times ok");
      }
      if (cs.sha256) bits.push(cs.sha256);
      el.textContent = bits.length ? "checksum " + bits.join(" · ") : "";
    }
    var pollInFlight = false;
    var catchupInFlight = false;
    var catchupOk = false;
    var lastCatchupAt = 0;
    var CATCHUP_LAG_MS = 2000;
    function boatsFromGun() {
      if (!gunTs) return 0;
      var n = 0;
      var sails = Object.keys(hist.boats);
      var i;
      for (i = 0; i < sails.length; i++) {
        var t = hist.boats[sails[i]];
        if (t && t.length && t[0].ts_ms <= gunTs + 15000) n += 1;
      }
      return n;
    }
    function stCount() {
      var n = 0;
      Object.keys(hist.boats).forEach(function (s) {
        if ((passTs.ST && passTs.ST[s] != null) || lockedSt[s] != null) n += 1;
      });
      return n;
    }
    function needCatchup() {
      if (catchupOk) return false;
      if (!gunTs || (snap && snap.waiting && !snap.gun_ts_ms)) return false;
      var now = Date.now();
      if (now < gunTs + CATCHUP_LAG_MS) return false;
      if (now - lastCatchupAt < CATCHUP_LAG_MS) return false;
      return true;
    }
    function poll() {
      if (pollInFlight) return;
      pollInFlight = true;
      var ac = typeof AbortController !== "undefined" ? new AbortController() : null;
      var to = setTimeout(function () { if (ac) ac.abort(); }, 8000);
      fetch("/api/lipton-dev/live", { cache: "no-store", signal: ac ? ac.signal : undefined })
        .then(function (res) {
          if (!res.ok) throw new Error("live " + res.status);
          return res.json();
        })
        .then(applySnap)
        .catch(function () {})
        .then(function () {
          clearTimeout(to);
          pollInFlight = false;
        });
    }
    function pollCatchup() {
      if (catchupInFlight || !needCatchup()) return;
      catchupInFlight = true;
      lastCatchupAt = Date.now();
      fetch("/js/lipton-dev-live-history.json?v=" + Date.now(), { cache: "no-store" })
        .then(function (res) { return res.ok ? res.json() : null; })
        .then(function (data) {
          if (!data || !data.boats) return;
          applySnap(data);
          if (boatsFromGun() >= 12) {
            catchupOk = true;
            loadedHistory = true;
          }
        })
        .catch(function () {})
        .then(function () { catchupInFlight = false; });
    }
    function pollStarts() {
      fetch("/js/lipton-dev-live-starts.json?v=" + Date.now(), { cache: "no-store" })
        .then(function (res) { return res.ok ? res.json() : null; })
        .then(function (data) {
          if (!data || !data.starts) return;
          var pg = data.gun_ts_ms != null ? Number(data.gun_ts_ms) : null;
          packedStarts = data.starts;
          packedStartsGun = pg;
          if (gunTs && pg && Math.abs(pg - gunTs) > 120000) return;
          if (!gunTs) return;
          Object.keys(packedStarts).forEach(function (sail) {
            var st = packedStarts[sail] && packedStarts[sail].st_ms;
            if (stValid(st)) lockedSt[sail] = Number(st);
          });
          maybeDetect();
        })
        .catch(function () {});
    }
    function pollPasses() {
      fetch("/js/lipton-dev-live-passes.json?v=" + Date.now(), { cache: "no-store" })
        .then(function (res) { return res.ok ? res.json() : null; })
        .then(function (data) {
          if (!applyPackedPasses(data)) return;
          maybeDetect();
        })
        .catch(function () {});
    }
    fetch("/js/lipton-dev-replay.json?v=" + CACHE, { cache: "no-store" })
      .then(function (res) { return res.ok ? res.json() : null; })
      .then(function (data) {
        identity = (data && data.boats) || {};
        renderLiveTable();
      })
      .catch(function () { renderLiveTable(); });
    try { paintClock(); } catch (e0) {}
    try { renderLiveTable(); } catch (e1) {}
    poll();
    pollCatchup();
    pollStarts();
    pollPasses();
    function liveTick() {
      if (livePlaying && !atLive && !scrubbing) {
        var now = Date.now();
        playTs += (now - livePlayWall) * LIVE_REPLAY_RATE;
        livePlayWall = now;
        if (playTs >= liveNow()) {
          playTs = liveNow();
          livePlaying = false;
          atLive = true;
        }
      } else {
        livePlayWall = Date.now();
      }
      paintClock();
      tickLiveHorns();
      drawLiveMap();
      window.requestAnimationFrame(liveTick);
    }
    window.requestAnimationFrame(liveTick);
    setInterval(poll, 1500);
    setInterval(pollCatchup, 2000);
    setInterval(pollStarts, 5000);
    setInterval(pollPasses, 5000);
    window.addEventListener("resize", function () {
      if (chartMap) chartMap.invalidateSize({ animate: false });
      drawLiveMap();
    });
  }

  function start(data, trail) {
    var PASSES = loadPasses(data);
    var BOATS = data.boats || {};
    var GUN_TS = Number(data.gun_ts_ms);
    var PLAY_START_TS = GUN_TS - 5000;
    var START_LABEL_MS = 5 * 60 * 1000;
    var PLAY_END_TS = Number(data.play_end_ts_ms || data.end_ts_ms);
    var GRID_ORIGIN = trail.grid_start_ts_ms != null ? Number(trail.grid_start_ts_ms) : Number(trail.gun_ts_ms);
    var FINISH = asBoats(data.finish);
    if (FINISH.length) {
      PASSES.push({
        id: "FIN",
        label: "Fin",
        lap: 0,
        mark: 0,
        boats: FINISH
      });
    }
    if (!PLAY_END_TS || !isFinite(PLAY_END_TS)) {
      var lastFin = 0;
      FINISH.forEach(function (b) {
        var t = Number(b && b.ts);
        if (t > lastFin) lastFin = t;
      });
      PLAY_END_TS = lastFin || (GUN_TS + 2 * 60 * 60 * 1000);
    }
    var OCS = {};
    (data.ocs || []).forEach(function (name) { OCS[name] = true; });
    var EXONERATED = {};
    (data.exonerated || []).forEach(function (name) { EXONERATED[name] = true; });
    function startLineGeom() {
      var sl = trail.start_line;
      if (!sl || !sl.left || !sl.right) return null;
      var lat0 = (sl.left.lat + sl.right.lat) / 2;
      var lon0 = (sl.left.lon + sl.right.lon) / 2;
      var R = 6371000;
      function xy(lat, lon) {
        return {
          x: (lon - lon0) * Math.PI / 180 * Math.cos(lat0 * Math.PI / 180) * R,
          y: (lat - lat0) * Math.PI / 180 * R
        };
      }
      var a = xy(sl.left.lat, sl.left.lon);
      var b = xy(sl.right.lat, sl.right.lon);
      var abx = b.x - a.x;
      var aby = b.y - a.y;
      var abLen = Math.hypot(abx, aby) || 1;
      function signed(lat, lon) {
        var p = xy(lat, lon);
        var apx = p.x - a.x;
        var apy = p.y - a.y;
        return { d: (abx * apy - aby * apx) / abLen, along: (apx * abx + apy * aby) / abLen };
      }
      var ds = [];
      Object.keys(trail.boats || {}).forEach(function (sail) {
        var s = trail.boats[sail];
        if (!s || s.lat[0] == null) return;
        ds.push(signed(s.lat[0], s.lon[0]).d);
      });
      ds.sort(function (u, v) { return u - v; });
      var flip = ds.length ? ds[Math.floor(ds.length / 2)] < 0 : false;
      return { signed: signed, abLen: abLen, flip: flip };
    }
    function courseCrossings(sail, geom) {
      var s = trail.boats[sail];
      if (!s || !geom) return [];
      var hits = [];
      var prev = null;
      var n = Math.min(s.lat.length, 180);
      for (var i = 0; i < n; i++) {
        if (s.lat[i] == null) continue;
        var sg = geom.signed(s.lat[i], s.lon[i]);
        var dist = geom.flip ? -sg.d : sg.d;
        var ts = GRID_ORIGIN + i * trail.step_ms;
        if (prev && prev.d > 0 && dist <= 0) {
          var frac = prev.d === dist ? 1 : prev.d / (prev.d - dist);
          var t = Math.round(prev.ts + (ts - prev.ts) * frac);
          var along = prev.along + (sg.along - prev.along) * frac;
          if (along >= -25 && along <= geom.abLen + 25) hits.push(t);
        }
        prev = { d: dist, along: sg.along, ts: ts };
      }
      return hits;
    }
    var geom = startLineGeom();
    var LEGAL_TS = {};
    var OCS_TS = {};
    Object.keys(trail.boats || {}).forEach(function (sail) {
      var hits = courseCrossings(sail, geom);
      if (OCS[sail]) {
        if (hits[0] != null) OCS_TS[sail] = hits[0];
        if (hits[1] != null) LEGAL_TS[sail] = hits[1];
      } else if (hits[0] != null) {
        LEGAL_TS[sail] = hits[0];
      }
    });
    var packedOcsTs = data.ocs_ts || {};
    PASSES.forEach(function (p) {
      if (p.id !== "ST" && p.label !== "ST") return;
      p.boats.forEach(function (b) {
        if (OCS[b.boat]) {
          if (packedOcsTs[b.boat] != null) OCS_TS[b.boat] = Number(packedOcsTs[b.boat]);
          else if (b.ocs_ts_ms != null) OCS_TS[b.boat] = Number(b.ocs_ts_ms);
          LEGAL_TS[b.boat] = b.ts;
        } else if (LEGAL_TS[b.boat] == null) {
          LEGAL_TS[b.boat] = b.ts;
        }
      });
    });
    var START_RANK = {};
    Object.keys(LEGAL_TS).sort(function (a, b) {
      return LEGAL_TS[a] - LEGAL_TS[b];
    }).forEach(function (sail, i) {
      START_RANK[sail] = i + 1;
    });
    var ST_LEAD_TS = null;
    Object.keys(LEGAL_TS).forEach(function (sail) {
      if (OCS[sail] && START_RANK[sail] == null) return;
      if (ST_LEAD_TS == null || LEGAL_TS[sail] < ST_LEAD_TS) ST_LEAD_TS = LEGAL_TS[sail];
    });
    function liveStartRank(sail, ts) {
      if (LEGAL_TS[sail] == null || ts < LEGAL_TS[sail]) return null;
      var earlier = 0;
      Object.keys(LEGAL_TS).forEach(function (other) {
        if (LEGAL_TS[other] < LEGAL_TS[sail] || (LEGAL_TS[other] === LEGAL_TS[sail] && other < sail)) earlier += 1;
      });
      return earlier + 1;
    }
    bindRaceButtons(data.race_number || RACE_Q || 4);
    var GUN_CLOCK = String(data.gun_sast || "").slice(11, 19) || "13:55:01";
    var RACE_NO = Number(data.race_number || RACE_Q || 4);
    var RACE_LAB = "Race " + RACE_NO;
    setRaceTableLabel(RACE_NO, false);
    var RATE = Number(data.default_rate || 1);
    var RATES = [1, 2, 5, 10, 25, 50];
    var SETTLE_MS = 2500;
    var playing = false;
    var trackerReady = false;
    var playTs = PLAY_END_TS;
    var GUN_HORN_SRC = "/js/lipton-dev-start-airhorn.mp3?v=20260828t";
    var RECALL_HORN_SRC = "/js/lipton-dev-recall-horn.wav?v=20260828t";
    var GUN_HORN_ONSET = 0.05;
    var GUN_HORN_LEAD_MS = 100;
    var GUN_HORN_EARLY_MS = 500;
    var gunHorn = null;
    var recallHorn = null;
    var gunCtx = null;
    var gunBuf = null;
    var gunBytes = null;
    var gunDecode = false;
    var recallBuf = null;
    var recallBytes = null;
    var recallDecode = false;
    var recallTimer = null;
    var hornSources = [];
    var gunFired = false;
    var soundOn = false;
    var soundBtn = document.getElementById("lipton-dev-sound");
    fetch(GUN_HORN_SRC).then(function (res) { return res.ok ? res.arrayBuffer() : null; }).then(function (buf) { gunBytes = buf; decodeHorns(); }).catch(function () {});
    fetch(RECALL_HORN_SRC).then(function (res) { return res.ok ? res.arrayBuffer() : null; }).then(function (buf) { recallBytes = buf; decodeHorns(); }).catch(function () {});
    function raceHasOcs() {
      return Object.keys(OCS).length > 0;
    }
    function prepHornEl(el) {
      el.preload = "auto";
      el.playsInline = true;
      el.setAttribute("playsinline", "");
      el.setAttribute("webkit-playsinline", "true");
      el.crossOrigin = "anonymous";
      el.volume = 1;
      try { el.load(); } catch (err) {}
      return el;
    }
    function gunHornEl() {
      if (!gunHorn) gunHorn = prepHornEl(new Audio(GUN_HORN_SRC));
      return gunHorn;
    }
    function recallHornEl() {
      if (!recallHorn) recallHorn = prepHornEl(new Audio(RECALL_HORN_SRC));
      return recallHorn;
    }
    function decodeOne(bytes, hasBuf, decoding, setBuf, setDecoding) {
      if (!gunCtx || !bytes || hasBuf || decoding) return;
      setDecoding(true);
      var copy = bytes.slice(0);
      var done = function (buf) { setBuf(buf); };
      var fail = function () { setDecoding(false); };
      var p = gunCtx.decodeAudioData(copy, done, fail);
      if (p && p.then) p.then(done).catch(fail);
    }
    function decodeHorns() {
      decodeOne(gunBytes, gunBuf, gunDecode, function (b) { gunBuf = b; }, function (v) { gunDecode = v; });
      decodeOne(recallBytes, recallBuf, recallDecode, function (b) { recallBuf = b; }, function (v) { recallDecode = v; });
    }
    function setSoundLabel() {
      if (!soundBtn) return;
      soundBtn.textContent = "♪";
      soundBtn.classList.toggle("is-active", soundOn);
      soundBtn.setAttribute("aria-pressed", soundOn ? "true" : "false");
      soundBtn.title = soundOn ? "Sound on" : "Enable start and recall horns";
    }
    function tickSilentBuffer() {
      if (!gunCtx) return;
      try {
        var n = Math.max(1, Math.floor((gunCtx.sampleRate || 22050) * 0.02));
        var buf = gunCtx.createBuffer(1, n, gunCtx.sampleRate || 22050);
        var src = gunCtx.createBufferSource();
        src.buffer = buf;
        src.connect(gunCtx.destination);
        src.start(0);
      } catch (err) {}
    }
    function unlockAudioEl(el) {
      if (!el) return;
      el.muted = true;
      el.volume = 1;
      var p = el.play();
      if (p && p.then) {
        p.then(function () {
          el.pause();
          try { el.currentTime = 0; } catch (err) {}
          el.muted = false;
        }).catch(function () { el.muted = false; });
      } else {
        try { el.pause(); } catch (err2) {}
        el.muted = false;
      }
    }
    function unlockGunHorn() {
      soundOn = true;
      setSoundLabel();
      var AC = window.AudioContext || window.webkitAudioContext;
      if (AC) {
        if (!gunCtx) gunCtx = new AC();
        var go = function () {
          decodeHorns();
          tickSilentBuffer();
        };
        if (gunCtx.state === "suspended") {
          var r = gunCtx.resume();
          if (r && r.then) r.then(go).catch(go);
          else go();
        } else {
          go();
        }
      }
      unlockAudioEl(gunHornEl());
      unlockAudioEl(recallHornEl());
    }
    function playBuf(buf, onset) {
      if (!soundOn || !playing || !gunCtx || !buf) return false;
      if (gunCtx.state === "suspended") {
        gunCtx.resume();
        return false;
      }
      var src = gunCtx.createBufferSource();
      src.buffer = buf;
      src.connect(gunCtx.destination);
      src.start(0, Math.min(onset || 0, Math.max(0, buf.duration - 0.02)));
      hornSources.push(src);
      src.onended = function () {
        var i = hornSources.indexOf(src);
        if (i >= 0) hornSources.splice(i, 1);
      };
      return true;
    }
    function stopHornEls() {
      [gunHorn, recallHorn].forEach(function (el) {
        if (!el) return;
        try { el.pause(); } catch (err) {}
        try { el.currentTime = 0; } catch (err2) {}
      });
    }
    function stopHornSources() {
      hornSources.forEach(function (src) {
        try { src.stop(); } catch (err) {}
        try { src.disconnect(); } catch (err2) {}
      });
      hornSources = [];
    }
    function cancelRecallHorn() {
      if (recallTimer) {
        clearTimeout(recallTimer);
        recallTimer = null;
      }
    }
    function resetHorns() {
      gunFired = false;
      cancelRecallHorn();
      stopHornSources();
      stopHornEls();
    }
    function fireRecallHorn() {
      if (!soundOn || !playing || !raceHasOcs()) return;
      try {
        if (playBuf(recallBuf, 0)) return;
        var el = recallHornEl();
        el.muted = false;
        el.volume = 1;
        try { el.currentTime = 0; } catch (err) {}
        var p = el.play();
        if (p && p.catch) p.catch(function () {});
      } catch (err2) {}
    }
    function scheduleRecallHorn() {
      cancelRecallHorn();
      if (!soundOn || !raceHasOcs()) return;
      var wait = gunBuf ? Math.max(400, Math.round((gunBuf.duration - GUN_HORN_ONSET) * 1000)) : 1550;
      recallTimer = setTimeout(function () {
        recallTimer = null;
        fireRecallHorn();
      }, wait);
    }
    function fireGunHorn() {
      if (!soundOn || !playing || gunFired) return;
      gunFired = true;
      try {
        if (!playBuf(gunBuf, GUN_HORN_ONSET)) {
          var el = gunHornEl();
          el.muted = false;
          el.volume = 1;
          try { el.currentTime = GUN_HORN_ONSET; } catch (err) {}
          var p = el.play();
          if (p && p.catch) p.catch(function () {});
        }
      } catch (err2) {}
      scheduleRecallHorn();
    }
    resetPlaybackAudio = function () {
      playing = false;
      resetHorns();
    };
    window.addEventListener("pagehide", resetPlaybackAudio);
    window.addEventListener("beforeunload", resetPlaybackAudio);
    var lastWall = Date.now();
    var lastKey = "";
    var seen = {};
    var posted = {};
    var postQueue = [];
    var lastPostWall = 0;
    var POST_GAP_MS = 1500;
    var VISIBLE_BEFORE_SCROLL = 5;
    var POST_HOLD_MS = 7000;
    var postHoldTimer = null;
    var scrolledHome = false;
    var deltaSeen = {};

    var tbody = document.getElementById("lipton-dev-tbody");
    var wrapEl = document.getElementById("lipton-dev-table-wrap");
    var clockEl = document.getElementById("lipton-dev-clock");
    var sailedEl = document.getElementById("lipton-dev-sailed");
    var checksumEl = document.getElementById("lipton-dev-checksum");
    var mapEl = document.getElementById("lipton-dev-map");
    var playBtn = document.getElementById("lipton-dev-play");
    var slowerBtn = document.getElementById("lipton-dev-slower");
    var fasterBtn = document.getElementById("lipton-dev-faster");
    var rateEl = document.getElementById("lipton-dev-rate");
    var scrubEl = document.getElementById("lipton-dev-scrub");
    var scrubbing = false;
    var headRow = document.getElementById("lipton-dev-thead-row");
    if (!tbody) return;
    if (wrapEl) wrapEl.hidden = true;
    tbody.innerHTML = "";
    var lastTableOn = false;
    function setTableVisible(on) {
      if (!wrapEl) return;
      wrapEl.hidden = !on;
      if (on === lastTableOn) return;
      lastTableOn = on;
      window.requestAnimationFrame(function () {
        if (chartMap) chartMap.invalidateSize({ animate: false });
      });
    }

    function ident(tracker) {
      return BOATS[tracker] || null;
    }
    function clubCode(sail) {
      var id = ident(sail);
      if (!id) return sail;
      return id.mapClub || id.club || sail;
    }
    var EVENT_BOAT_COLORS = {
      HYC: "#2563eb",
      RCYC: "#e11d48",
      KYC: "#16a34a",
      RNYC: "#7c3aed",
      WBYC: "#ea580c",
      FBYC: "#0891b2",
      SBYC: "#ca8a04",
      PYC: "#db2777",
      LDYC: "#4f46e5",
      GLYC: "#65a30d",
      BYC: "#0d9488",
      TSC: "#9333ea",
      WYAC: "#f59e0b",
      RCYCA: "#64748b",
      "RCYC Academy": "#64748b",
      UCT: "#0284c7",
      UCTYC: "#0284c7",
      IZI: "#be123c",
      IZIVUNGUVUNGU: "#be123c",
      LYCN: "#15803d",
      LYC: "#15803d"
    };
    function hexRgb(hex) {
      var n = parseInt(String(hex).replace("#", ""), 16);
      if (!(n >= 0)) return [148, 163, 184];
      return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
    }
    function hexLuma(hex) {
      var c = hexRgb(hex);
      return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2];
    }
    function rgbaHex(hex, a) {
      var c = hexRgb(hex);
      return "rgba(" + c[0] + "," + c[1] + "," + c[2] + "," + a + ")";
    }
    function eventFill(sail) {
      return EVENT_BOAT_COLORS[sail] || EVENT_BOAT_COLORS[clubCode(sail)] || "#94a3b8";
    }
    function boatPaint(sail, pending) {
      if (pending) {
        return { fill: "#dc2626", stroke: "#7f1d1d", ink: "#ffffff", nose: "#fecaca" };
      }
      var fill = eventFill(sail);
      var dark = hexLuma(fill) < 165;
      return {
        fill: fill,
        stroke: "rgba(15,23,42,0.75)",
        ink: dark ? "#ffffff" : "#0f172a",
        nose: dark ? "#ffffff" : "#0f172a"
      };
    }
    function boatNameCell(id) {
      if (!id) return "";
      return "<a href=\"" + esc(id.nameHref) + "\" class=\"rs-boat-name-sponsors rs-boat-name-sponsors--link\" title=\"" + esc(id.title) + "\">" + (id.nameInner || esc(id.title || "")) + "</a>";
    }
    function clubCell(id, pending) {
      if (!id) return "";
      var cls = "rs-club-with-logo" + (pending ? " ocs-club" : "");
      return "<span class=\"" + cls + "\"><a href=\"" + esc(id.clubHref) + "\">" + esc(id.club) + "</a><img class=\"rs-club-row-logo\" src=\"" + esc(id.clubLogo) + "\" alt=\"" + esc(id.club) + "\" title=\"" + esc(id.club) + "\"></span>";
    }
    function bowCell(id) {
      if (!id) return "";
      return "<span class=\"wc-boat-linked\"><a href=\"" + esc(id.boatHref) + "\">" + esc(id.bow) + "</a></span>";
    }
    var mapCtx = null;
    var mapBounds = null;
    var cam = null;
    var chartMap = null;
    var followFleet = true;
    var chartSyncing = false;
    var chartPointerDown = false;
    var drawingMap = false;
    function userFreedMap() {
      if (chartSyncing || !followFleet) return;
      followFleet = false;
    }
    function initChart() {
      var el = document.getElementById("lipton-dev-chart");
      if (!el || !window.L || chartMap) return;
      chartMap = L.map(el, {
        zoomControl: false,
        attributionControl: true,
        dragging: true,
        scrollWheelZoom: true,
        doubleClickZoom: true,
        boxZoom: true,
        keyboard: true,
        touchZoom: true,
        zoomSnap: 0,
        zoomAnimation: false,
        fadeAnimation: false,
        markerZoomAnimation: false,
        inertia: true
      }).setView([-33.901, 18.423], 15);
      var tileOpts = {
        minZoom: 12,
        maxZoom: 19,
        keepBuffer: 8,
        updateWhenIdle: false,
        updateWhenZooming: false,
        updateInterval: 400,
        crossOrigin: true
      };
      L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", Object.assign({
        maxZoom: 19,
        attribution: "Tiles © Esri"
      }, tileOpts)).addTo(chartMap);
      L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}", Object.assign({
        maxZoom: 18,
        opacity: 0.85,
        attribution: "Labels © Esri"
      }, tileOpts)).addTo(chartMap);
      chartMap.on("dragstart zoomstart boxzoomstart", userFreedMap);
      chartMap.on("movestart", function () {
        if (!chartSyncing) userFreedMap();
      });
      chartMap.on("move zoom zoomend", function () {
        if (chartSyncing || drawingMap) return;
        drawMap(playTs);
      });
      el.addEventListener("pointerdown", function () {
        chartPointerDown = true;
      });
      window.addEventListener("pointerup", function () {
        chartPointerDown = false;
      });
      window.addEventListener("pointercancel", function () {
        chartPointerDown = false;
      });
      window.requestAnimationFrame(function () {
        if (chartMap) chartMap.invalidateSize({ animate: false });
      });
      var track = el.parentNode;
      var ctrls = el.querySelector(".leaflet-control-container");
      if (track && ctrls) track.appendChild(ctrls);
    }
    var lastChartSyncAt = 0;
    function syncChart() {
      if (!followFleet || !chartMap || !mapBounds || chartPointerDown) return;
      var lat = mapBounds.midLat;
      var lon = mapBounds.midLon;
      var cos = Math.max(0.2, Math.cos(lat * Math.PI / 180));
      var z = Math.log(mapBounds.scale * 156543.03392 * cos) / Math.LN2;
      if (!(z > 0)) z = 15;
      if (z < 14) z = 14;
      if (z > 17) z = 17;
      var cur = chartMap.getCenter();
      var curZ = chartMap.getZoom();
      var dz = Math.abs(curZ - z);
      var now = Date.now();
      var boatsNearEdge = false;
      if (mapEl && trail && trail.boats) {
        var w = mapEl.clientWidth || 0;
        var h = mapEl.clientHeight || 0;
        var pad = 48;
        Object.keys(trail.boats).some(function (sail) {
          var pos = sampleAt(trail.boats[sail], playTs);
          if (!pos) return false;
          var p = chartMap.latLngToContainerPoint([pos.lat, pos.lon]);
          if (p.x < pad || p.y < pad || p.x > w - pad || p.y > h - pad) {
            boatsNearEdge = true;
            return true;
          }
          return false;
        });
      }
      var moved = Math.abs(cur.lat - lat) > 0.00012 || Math.abs(cur.lng - lon) > 0.00012;
      if (!boatsNearEdge && dz < 0.2 && !moved) return;
      if (!boatsNearEdge && playing && now - lastChartSyncAt < 450 && dz < 0.35) return;
      lastChartSyncAt = now;
      chartSyncing = true;
      chartMap.setView([lat, lon], z, { animate: false });
      chartSyncing = false;
    }
    function expandBounds(lat, lon, box) {
      if (lat == null || lon == null) return;
      if (lat < box.minLat) box.minLat = lat;
      if (lat > box.maxLat) box.maxLat = lat;
      if (lon < box.minLon) box.minLon = lon;
      if (lon > box.maxLon) box.maxLon = lon;
    }
    function distM(a, b) {
      var c = Math.cos(((a.lat + b.lat) / 2) * Math.PI / 180);
      var y = (a.lat - b.lat) * 111000;
      var x = (a.lon - b.lon) * 111000 * c;
      return Math.sqrt(x * x + y * y);
    }
    var TAIL_CLEAR_MS = 5000;
    var tailsUntil = 0;
    var finishFlashUntil = {};
    var focusMarkKey = null;
    var focusGate = null;
    function sizeCanvas() {
      if (!mapEl) return;
      initChart();
      var w = mapEl.clientWidth || 640;
      var h = mapEl.clientHeight || 480;
      var dpr = window.devicePixelRatio || 1;
      var needW = Math.floor(w * dpr);
      var needH = Math.floor(h * dpr);
      if (!mapCtx || mapEl.width !== needW || mapEl.height !== needH) {
        mapEl.width = needW;
        mapEl.height = needH;
        mapCtx = mapEl.getContext("2d");
      }
      mapCtx.setTransform(dpr, 0, 0, dpr, 0, 0);
      mapCtx.imageSmoothingEnabled = true;
      mapCtx.imageSmoothingQuality = "high";
      mapCtx.lineJoin = "round";
      mapCtx.lineCap = "round";
      if (!mapBounds) {
        mapBounds = { w: w, h: h, midLat: -33.87, midLon: 18.46, cos: Math.cos(-33.87 * Math.PI / 180), scale: 0.2 };
      } else {
        mapBounds.w = w;
        mapBounds.h = h;
      }
    }
    function bboxOf(pts) {
      var box = { minLat: 90, maxLat: -90, minLon: 180, maxLon: -180 };
      pts.forEach(function (p) { expandBounds(p.lat, p.lon, box); });
      var midLat = (box.minLat + box.maxLat) / 2;
      var midLon = (box.minLon + box.maxLon) / 2;
      var cos = Math.cos(midLat * Math.PI / 180);
      var heightM = (box.maxLat - box.minLat) * 111000;
      var widthM = (box.maxLon - box.minLon) * 111000 * cos;
      return { box: box, midLat: midLat, midLon: midLon, cos: cos, heightM: heightM, widthM: widthM, spanM: Math.max(widthM, heightM) };
    }
    function boundsFromPts(pts, w, h, opts) {
      opts = opts || {};
      var minSpan = opts.minSpan != null ? opts.minSpan : 80;
      var padPx = opts.padPx != null ? opts.padPx : 44;
      var padM = opts.padM != null ? opts.padM : 0;
      var s = bboxOf(pts);
      var heightM = Math.max(s.heightM + 2 * padM, minSpan * 0.35);
      var widthM = Math.max(s.widthM + 2 * padM, minSpan * 0.35);
      var span = Math.max(heightM, widthM, minSpan);
      if (span > Math.max(heightM, widthM)) {
        var grow = (span - Math.max(heightM, widthM)) / 2;
        heightM += grow;
        widthM += grow;
      }
      var innerW = Math.max(64, w - 2 * padPx);
      var innerH = Math.max(64, h - 2 * padPx);
      var scale = Math.min(innerW / Math.max(widthM, 1e-3), innerH / Math.max(heightM, 1e-3));
      return { w: w, h: h, midLat: s.midLat, midLon: s.midLon, cos: s.cos, scale: scale };
    }
    function pinTrio() {
      var pts = [];
      var sl = trail.start_line;
      var fl = trail.finish_line;
      if (sl && sl.left) pts.push(sl.left);
      if (sl && sl.right) pts.push(sl.right);
      if (fl && fl.left) pts.push(fl.left);
      return pts;
    }
    function fleetNearStart(boatPts, ts) {
      if (ts != null && trail.gun_ts_ms != null && ts < trail.gun_ts_ms + 25000) return true;
      var pin = trail.start_line && trail.start_line.left;
      if (!pin || !boatPts.length) return true;
      var maxD = 0;
      for (var i = 0; i < boatPts.length; i++) {
        var d = distM(boatPts[i], pin);
        if (d > maxD) maxD = d;
      }
      return maxD < 420;
    }
    function pointNearBoatBox(pt, boatPts, padM) {
      if (!pt || !boatPts.length) return false;
      var s = bboxOf(boatPts);
      var padLat = padM / 111000;
      var padLon = padM / (111000 * Math.max(s.cos, 0.2));
      return pt.lat >= s.box.minLat - padLat && pt.lat <= s.box.maxLat + padLat &&
        pt.lon >= s.box.minLon - padLon && pt.lon <= s.box.maxLon + padLon;
    }
    function countPassed(pass, ts) {
      var n = 0;
      for (var i = 0; i < pass.boats.length; i++) {
        if (pass.boats[i].ts <= ts) n += 1;
      }
      return n;
    }
    function focusForFleet(ts, fleet) {
      var lastKey = null;
      var nextKey = null;
      var lastGate = null;
      var nextGate = null;
      var onWater = 0;
      Object.keys(trail.boats || {}).forEach(function (sail) {
        if (sampleAt(trail.boats[sail], ts)) onWater += 1;
      });
      for (var i = 0; i < PASSES.length; i++) {
        var p = PASSES[i];
        var n = countPassed(p, ts);
        if (p.id === "ST" || p.label === "ST") {
          if (n > 0) lastGate = "start_line";
          continue;
        }
        if (p.id === "FIN" || p.label === "Fin") {
          if (n > 0) lastGate = "finish_line";
          if (n < onWater) nextGate = "finish_line";
          continue;
        }
        var key = String(p.mark);
        if (n > 0) lastKey = key;
        if (n < onWater) {
          nextKey = key;
          break;
        }
      }
      var lastPos = lastKey ? markAt(lastKey, ts) : null;
      var nextPos = nextKey ? markAt(nextKey, ts) : null;
      var pickKey = null;
      var pickGate = null;
      function gateMid(name) {
        var ln = trail[name];
        if (!ln || !ln.left || !ln.right) return null;
        return { lat: (ln.left.lat + ln.right.lat) / 2, lon: (ln.left.lon + ln.right.lon) / 2 };
      }
      var candidates = [];
      if (lastPos) candidates.push({ mark: lastKey, pos: lastPos });
      if (nextPos && nextKey !== lastKey) candidates.push({ mark: nextKey, pos: nextPos });
      if (!lastKey && trail.start_line) {
        var sm = gateMid("start_line");
        if (sm) candidates.push({ gate: "start_line", pos: sm });
      }
      if (nextGate === "finish_line" || lastGate === "finish_line") {
        var fm = gateMid("finish_line");
        if (fm) candidates.push({ gate: "finish_line", pos: fm });
      }
      if (!candidates.length && trail.start_line) {
        pickGate = "start_line";
      } else if (candidates.length) {
        var best = candidates[0];
        var bestD = distM(fleet, best.pos);
        for (var c = 1; c < candidates.length; c++) {
          var d = distM(fleet, candidates[c].pos);
          if (d < bestD) { best = candidates[c]; bestD = d; }
        }
        pickKey = best.mark || null;
        pickGate = best.gate || null;
      }
      return { mark: pickKey, gate: pickGate };
    }
    function frameCam(ts) {
      sizeCanvas();
      if (!mapEl) return;
      var w = mapEl.clientWidth || 640;
      var h = mapEl.clientHeight || 480;
      var boatPts = [];
      Object.keys(trail.boats || {}).forEach(function (sail) {
        var pos = sampleAt(trail.boats[sail], ts);
        if (pos) boatPts.push(pos);
      });
      if (!boatPts.length) return;
      var cx = 0;
      var cy = 0;
      boatPts.forEach(function (p) { cx += p.lat; cy += p.lon; });
      var fleet = { lat: cx / boatPts.length, lon: cy / boatPts.length };
      var focus = focusForFleet(ts, fleet);
      focusMarkKey = focus.mark;
      focusGate = focus.gate;
      var nearStart = fleetNearStart(boatPts, ts);
      var pts = boatPts.slice();
      if (nearStart) {
        pinTrio().forEach(function (p) { pts.push(p); });
        focusGate = "start_line";
      } else {
        if (focus.mark) {
          var mk = markAt(focus.mark, ts);
          if (mk && pointNearBoatBox(mk, boatPts, 220)) pts.push(mk);
        }
        if (focus.gate && trail[focus.gate]) {
          var ln = trail[focus.gate];
          if (ln.left && pointNearBoatBox(ln.left, boatPts, 220)) pts.push(ln.left);
          if (ln.right && pointNearBoatBox(ln.right, boatPts, 220)) pts.push(ln.right);
        }
      }
      var target = boundsFromPts(pts, w, h, {
        minSpan: nearStart ? 70 : 90,
        padPx: nearStart ? 32 : 40,
        padM: nearStart ? 18 : 24
      });
      if (!cam) {
        cam = target;
      } else if (followFleet) {
        var aPan = playing ? 0.12 : 1;
        var aZoom = playing ? 0.08 : 1;
        if (playing && target.scale < cam.scale) aZoom = 0.22;
        cam.midLat += (target.midLat - cam.midLat) * aPan;
        cam.midLon += (target.midLon - cam.midLon) * aPan;
        cam.scale += (target.scale - cam.scale) * aZoom;
        cam.cos = Math.cos(cam.midLat * Math.PI / 180);
        cam.w = w;
        cam.h = h;
      } else {
        cam.w = w;
        cam.h = h;
      }
      mapBounds = cam;
      if (followFleet) syncChart();
    }
    function xy(lat, lon) {
      if (chartMap) {
        var pt = chartMap.latLngToContainerPoint([lat, lon]);
        return { x: pt.x, y: pt.y };
      }
      var b = mapBounds;
      return {
        x: (lon - b.midLon) * 111000 * b.cos * b.scale + b.w / 2,
        y: -(lat - b.midLat) * 111000 * b.scale + b.h / 2
      };
    }
    var lastHdg = {};
    var lastHdgAt = {};
    function hitBack(series, i) {
      var k = i;
      while (k >= 0 && series.lat[k] == null) k -= 1;
      return k;
    }
    function hitFwd(series, i) {
      var k = i;
      while (k < series.lat.length && series.lat[k] == null) k += 1;
      return k < series.lat.length ? k : -1;
    }
    function ptAt(series, i) {
      if (i < 0 || !series || series.lat[i] == null) return null;
      return { lat: series.lat[i], lon: series.lon[i], i: i };
    }
    function catmull(p0, p1, p2, p3, t) {
      var t2 = t * t;
      var t3 = t2 * t;
      function axis(a, b, c, d) {
        return 0.5 * ((2 * b) + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t2 + (-a + 3 * b - 3 * c + d) * t3);
      }
      return {
        lat: axis(p0.lat, p1.lat, p2.lat, p3.lat),
        lon: axis(p0.lon, p1.lon, p2.lon, p3.lon)
      };
    }
    function sampleAt(series, ts) {
      if (!series) return null;
      if (typeof series.lat === "number") return { lat: series.lat, lon: series.lon, i: 0, j: 0 };
      var t = (ts - GRID_ORIGIN) / trail.step_ms;
      var i = hitBack(series, Math.min(series.lat.length - 1, Math.max(0, Math.floor(t))));
      if (i < 0) {
        var fwd = hitFwd(series, 0);
        if (fwd < 0) return null;
        return { lat: series.lat[fwd], lon: series.lon[fwd], i: fwd, j: fwd };
      }
      var j = hitFwd(series, i + 1);
      if (j < 0 || j - i > 2) {
        return { lat: series.lat[i], lon: series.lon[i], i: i, j: i };
      }
      var f = (t - i) / (j - i);
      if (f < 0) f = 0;
      if (f > 1) f = 1;
      return {
        lat: series.lat[i] + (series.lat[j] - series.lat[i]) * f,
        lon: series.lon[i] + (series.lon[j] - series.lon[i]) * f,
        i: i,
        j: j
      };
    }
    function headingAt(b, sample) {
      if (!b || !sample) return 0;
      if (sample.j != null && sample.j > sample.i && b.lat[sample.j] != null && b.lat[sample.i] != null) {
        return Math.atan2(b.lon[sample.j] - b.lon[sample.i], b.lat[sample.j] - b.lat[sample.i]) * 180 / Math.PI;
      }
      var k = hitBack(b, sample.i - 1);
      if (k < 0) return 0;
      return Math.atan2(b.lon[sample.i] - b.lon[k], b.lat[sample.i] - b.lat[k]) * 180 / Math.PI;
    }
    function blendHdg(sail, target) {
      if (target == null || isNaN(target)) return lastHdg[sail] || 0;
      var prev = lastHdg[sail];
      var now = Date.now();
      if (prev == null) {
        lastHdg[sail] = target;
        lastHdgAt[sail] = now;
        return target;
      }
      var dt = Math.min(0.05, (now - (lastHdgAt[sail] || now)) / 1000);
      lastHdgAt[sail] = now;
      var d = target - prev;
      while (d > 180) d -= 360;
      while (d < -180) d += 360;
      var k = playing ? (1 - Math.exp(-dt * 9)) : 1;
      var out = prev + d * k;
      lastHdg[sail] = out;
      return out;
    }
    var FIN_POS = {};
    (data.finish || []).forEach(function (f) {
      if (f && f.lat != null && f.lon != null) {
        FIN_POS[f.boat] = { lat: Number(f.lat), lon: Number(f.lon) };
      }
    });
    function posAt(sail, ts) {
      var b = trail.boats[sail];
      var pos = sampleAt(b, ts);
      if (!pos) return null;
      pos.hdg = blendHdg(sail, headingAt(b, pos));
      var ft = finishTs(sail);
      if (ft != null && ts >= ft) {
        if (!finishFlashUntil[sail]) finishFlashUntil[sail] = Date.now() + 10000;
        pos.finished = true;
      }
      return pos;
    }
    function markAt(k, ts) {
      return sampleAt(trail.marks[k], ts);
    }
    function metersPx(m) {
      return Math.max(4, m * mapBounds.scale);
    }
    function drawBoatIcon(p, hdg, fill, stroke, nose) {
      var r = 7;
      mapCtx.beginPath();
      mapCtx.arc(p.x, p.y, r, 0, Math.PI * 2);
      mapCtx.fillStyle = fill;
      mapCtx.fill();
      mapCtx.strokeStyle = stroke;
      mapCtx.lineWidth = 1.4;
      mapCtx.stroke();
      mapCtx.save();
      mapCtx.translate(p.x, p.y);
      mapCtx.rotate((hdg || 0) * Math.PI / 180);
      mapCtx.beginPath();
      mapCtx.moveTo(0, -r - 3.6);
      mapCtx.lineTo(3.1, -r + 1.2);
      mapCtx.lineTo(-3.1, -r + 1.2);
      mapCtx.closePath();
      mapCtx.fillStyle = nose || "#ffffff";
      mapCtx.fill();
      mapCtx.restore();
    }
    function tailHits(b, ts) {
      var now = sampleAt(b, ts);
      if (!now) return [];
      var bud = tailBudget(chartMap);
      var hits = [now];
      var acc = 0;
      var lastI = now.i != null ? now.i : Math.floor((ts - GRID_ORIGIN) / trail.step_ms);
      var idx = hitBack(b, lastI - 1);
      var stepMs = trail.step_ms || 1000;
      while (idx >= 0) {
        var gap = lastI - idx;
        var cur = { lat: b.lat[idx], lon: b.lon[idx], i: idx };
        var step = distM(hits[hits.length - 1], cur);
        if (gap > 45) break;
        if (step > 14 * Math.min(gap, 8)) break;
        acc += step;
        hits.push(cur);
        if (acc >= bud.m) break;
        if ((now.i - idx) * stepMs >= bud.ms) break;
        lastI = idx;
        idx = hitBack(b, idx - 1);
      }
      hits.reverse();
      return hits;
    }
    function tailsCleared() {
      return tailsUntil < 0;
    }
    function armTailClear() {
      if (!tailsUntil) tailsUntil = Date.now() + TAIL_CLEAR_MS;
    }
    function resetTails(ts) {
      if (ts != null && ts >= PLAY_END_TS) {
        armTailClear();
        return;
      }
      tailsUntil = 0;
    }
    function finishPulseActive(sail) {
      var until = finishFlashUntil[sail];
      return until && Date.now() < until;
    }
    function anyFinishPulse() {
      var now = Date.now();
      return Object.keys(finishFlashUntil).some(function (sail) {
        return finishFlashUntil[sail] > now;
      });
    }
    function drawFinishHalo(p, sail) {
      if (!finishPulseActive(sail)) return;
      var u = (Date.now() % 1600) / 1600;
      var wave = 0.5 - 0.5 * Math.cos(u * Math.PI * 2);
      mapCtx.beginPath();
      mapCtx.arc(p.x, p.y, 9 + 6 * wave, 0, Math.PI * 2);
      mapCtx.strokeStyle = "rgba(251,191,36," + (0.9 - 0.55 * wave) + ")";
      mapCtx.lineWidth = 2.6;
      mapCtx.stroke();
    }
    function drawTail(sail, ts) {
      if (tailsCleared()) return;
      if (tailsUntil > 0 && Date.now() >= tailsUntil) {
        tailsUntil = -1;
        return;
      }
      var b = trail.boats[sail];
      var hits = tailHits(b, ts);
      if (hits.length < 2) return;
      var hot = ocsPending(sail, ts);
      var fill = boatPaint(sail, hot).fill;
      var n = hits.length - 1;
      var tailW = tailBudget(chartMap).w;
      for (var s = 0; s < n; s++) {
        var a = xy(hits[s].lat, hits[s].lon);
        var c = xy(hits[s + 1].lat, hits[s + 1].lon);
        var u = (s + 1) / n;
        var alpha = 0.35 + 0.65 * u * u;
        mapCtx.beginPath();
        mapCtx.moveTo(a.x, a.y);
        mapCtx.lineTo(c.x, c.y);
        mapCtx.strokeStyle = rgbaHex(fill, alpha);
        mapCtx.lineWidth = tailW + 1.6 * u;
        mapCtx.lineCap = "round";
        mapCtx.lineJoin = "round";
        mapCtx.stroke();
      }
    }
    function drawGate(line, color, label, pinLabel, rcLabel) {
      if (!line || !line.left || !line.right) return;
      var a = xy(line.left.lat, line.left.lon);
      var b = xy(line.right.lat, line.right.lon);
      mapCtx.beginPath();
      mapCtx.moveTo(a.x, a.y);
      mapCtx.lineTo(b.x, b.y);
      mapCtx.strokeStyle = color;
      mapCtx.lineWidth = 2.4;
      mapCtx.setLineDash([7, 4]);
      mapCtx.stroke();
      mapCtx.setLineDash([]);
      mapCtx.beginPath();
      mapCtx.arc(a.x, a.y, 4, 0, Math.PI * 2);
      mapCtx.fillStyle = color;
      mapCtx.fill();
      mapCtx.fillStyle = "#e2e8f0";
      mapCtx.font = "bold 9px sans-serif";
      mapCtx.fillRect(b.x - 7, b.y - 5, 14, 10);
      mapCtx.strokeStyle = color;
      mapCtx.lineWidth = 1;
      mapCtx.strokeRect(b.x - 7, b.y - 5, 14, 10);
      mapCtx.fillStyle = "#0b1b33";
      mapCtx.fillText(rcLabel || "RC", b.x - 6, b.y + 3);
      mapCtx.fillStyle = "#ffffff";
      mapCtx.font = "bold 10px sans-serif";
      mapCtx.fillText(pinLabel || "Pin", a.x + 6, a.y - 6);
      if (label) mapCtx.fillText(label, (a.x + b.x) / 2 + 6, (a.y + b.y) / 2 - 6);
    }
    function passRankOf(pass, sail) {
      if (!pass || !pass.boats) return null;
      if (pass.id === "ST" || pass.label === "ST") {
        return START_RANK[sail] != null ? START_RANK[sail] : null;
      }
      for (var i = 0; i < pass.boats.length; i++) {
        if (pass.boats[i].boat === sail) return i + 1;
      }
      return null;
    }
    function stTime(sail) {
      for (var i = 0; i < PASSES.length; i++) {
        if (PASSES[i].id === "ST" || PASSES[i].label === "ST") return tsAtPass(PASSES[i], sail);
      }
      return null;
    }
    function ocsPending(sail, ts) {
      if (!OCS[sail]) return false;
      if (ts < GUN_TS) return false;
      var markedAt = OCS_TS[sail] != null ? OCS_TS[sail] : GUN_TS;
      if (ts < markedAt) return false;
      if (LEGAL_TS[sail] == null) return true;
      return ts < LEGAL_TS[sail];
    }
    function mapBadge(sail, ts) {
      var startNo = START_RANK[sail] != null ? START_RANK[sail] : null;
      var liveNo = liveStartRank(sail, ts);
      var last = -1;
      var pending = ocsPending(sail, ts);
      for (var i = 0; i < PASSES.length; i++) {
        var p = PASSES[i];
        if ((p.id === "ST" || p.label === "ST") && pending) continue;
        var t = tsAtPass(p, sail);
        if ((p.id === "ST" || p.label === "ST") && LEGAL_TS[sail] != null) t = LEGAL_TS[sail];
        if (t != null && t <= ts) last = i;
      }
      var place = liveNo;
      if (last > 0) place = passRankOf(PASSES[last], sail);
      var started = liveNo != null;
      var leg = null;
      var total = null;
      if (last > 0 && place != null) {
        var prev = passRankOf(PASSES[last - 1], sail);
        if (prev != null) leg = prev - place;
        if (startNo != null) total = startNo - place;
      }
      return { place: place, pending: pending, started: started, onMark: last > 0, finished: last > 0 && PASSES[last] && (PASSES[last].id === "FIN" || PASSES[last].label === "Fin"), leg: leg, total: total };
    }
    function drawDelta(x, y, delta, align) {
      if (delta == null) return x;
      var txt = delta > 0 ? "▲" + delta : delta < 0 ? "▼" + (-delta) : "■0";
      mapCtx.font = "bold 8px sans-serif";
      mapCtx.textAlign = align || "left";
      mapCtx.textBaseline = "middle";
      mapCtx.fillStyle = delta > 0 ? "#4ade80" : delta < 0 ? "#f87171" : "#cbd5e1";
      mapCtx.fillText(txt, x, y);
      return mapCtx.measureText(txt).width;
    }
    function drawBoatLabel(p, hdg, sail, ts) {
      var club = clubCode(sail);
      var info = mapBadge(sail, ts);
      var paint = boatPaint(sail, info.pending);
      mapCtx.save();
      drawFinishHalo(p, sail);
      drawBoatIcon(p, hdg, paint.fill, paint.stroke, paint.nose);
      if (info.place != null) {
        mapCtx.fillStyle = paint.ink;
        mapCtx.font = "bold 9px sans-serif";
        mapCtx.textAlign = "center";
        mapCtx.textBaseline = "middle";
        mapCtx.fillText(String(info.place), p.x, p.y + 0.4);
      }
      if (info.onMark && !info.finished) drawDelta(p.x - 12, p.y - 1, info.leg, "right");
      var lx = p.x + 12;
      var ly = p.y - 1;
      mapCtx.font = "bold 10px sans-serif";
      mapCtx.textAlign = "left";
      mapCtx.textBaseline = "middle";
      mapCtx.shadowColor = "rgba(0,0,0,0.9)";
      mapCtx.shadowBlur = 3;
      mapCtx.fillStyle = info.pending ? "#f87171" : paint.fill;
      mapCtx.fillText(club, lx, ly);
      mapCtx.shadowBlur = 0;
      if (info.onMark) {
        var cw = mapCtx.measureText(club).width;
        drawDelta(lx + cw + 3, ly, info.total, "left");
      }
      mapCtx.textAlign = "start";
      mapCtx.textBaseline = "alphabetic";
      mapCtx.restore();
    }
    function drawMap(ts) {
      if (drawingMap) return;
      drawingMap = true;
      frameCam(ts);
      if (!mapCtx || !mapBounds) {
        drawingMap = false;
        return;
      }
      var w = mapBounds.w;
      var h = mapBounds.h;
      mapCtx.clearRect(0, 0, w, h);
      mapCtx.fillStyle = "rgba(0, 10, 24, 0.08)";
      mapCtx.fillRect(0, 0, w, h);
      var zone = Math.min(metersPx(20.1), 8);
      Object.keys(trail.marks || {}).forEach(function (k) {
        var pos = markAt(k, ts);
        if (!pos) return;
        var p = xy(pos.lat, pos.lon);
        var focus = k === focusMarkKey;
        mapCtx.beginPath();
        mapCtx.arc(p.x, p.y, zone, 0, Math.PI * 2);
        mapCtx.strokeStyle = focus ? "rgba(251,191,36,0.7)" : "rgba(245,158,11,0.28)";
        mapCtx.lineWidth = focus ? 2 : 1;
        mapCtx.stroke();
        mapCtx.beginPath();
        mapCtx.arc(p.x, p.y, focus ? 3.2 : 2.2, 0, Math.PI * 2);
        mapCtx.fillStyle = focus ? "#fbbf24" : "#f59e0b";
        mapCtx.fill();
        mapCtx.fillStyle = "#ffffff";
        mapCtx.font = focus ? "bold 12px sans-serif" : "bold 10px sans-serif";
        mapCtx.fillText("M" + k, p.x + 8, p.y + 4);
      });
      Object.keys(trail.boats || {}).forEach(function (sail) {
        drawTail(sail, ts);
      });
      var startName = ts < PLAY_START_TS + START_LABEL_MS ? "START" : "";
      var finishName = ts >= GUN_TS ? "FINISH" : "";
      drawGate(trail.start_line, focusGate === "start_line" ? "#38bdf8" : "rgba(56,189,248,0.4)", startName, "Pin", "RC");
      if (trail.start_line && ts < GUN_TS + 5 * 60 * 1000) {
        var boatPts = [];
        Object.keys(trail.boats || {}).forEach(function (sail) {
          var bp = posAt(sail, ts);
          if (bp) boatPts.push(bp);
        });
        drawStartDirArrows(mapCtx, xy, trail.start_line.left, trail.start_line.right, markAt("1", ts), boatPts);
      }
      drawGate(trail.finish_line, focusGate === "finish_line" ? "#fbbf24" : "rgba(251,191,36,0.35)", finishName, "Pin", "RC");
      Object.keys(trail.boats || {}).forEach(function (sail) {
        var pos = posAt(sail, ts);
        if (!pos) return;
        var p = xy(pos.lat, pos.lon);
        drawBoatLabel(p, pos.hdg, sail, ts);
      });
      drawCourseLabel(ts);
      drawingMap = false;
    }
    function courseFromTrail() {
      if (data.course && data.course.label) return data.course.label;
      var sl = trail.start_line;
      var fl = trail.finish_line;
      if (!sl || !sl.left || !trail.marks) return "";
      function mid(a, b) {
        return { lat: (a.lat + b.lat) / 2, lon: (a.lon + b.lon) / 2 };
      }
      function hav(a, b) {
        if (!a || !b) return null;
        var R = 6371000;
        var p1 = a.lat * Math.PI / 180;
        var p2 = b.lat * Math.PI / 180;
        var dphi = (b.lat - a.lat) * Math.PI / 180;
        var dl = (b.lon - a.lon) * Math.PI / 180;
        var x = Math.sin(dphi / 2) * Math.sin(dphi / 2) + Math.cos(p1) * Math.cos(p2) * Math.sin(dl / 2) * Math.sin(dl / 2);
        return 2 * R * Math.asin(Math.sqrt(x));
      }
      function markMid(k) {
        var s = trail.marks[k];
        if (!s || !s.lat) return null;
        var pts = [];
        for (var i = 0; i < s.lat.length; i++) {
          if (s.lat[i] != null) pts.push({ lat: s.lat[i], lon: s.lon[i] });
        }
        if (!pts.length) return null;
        var lo = Math.floor(pts.length * 0.2);
        var hi = Math.max(lo + 1, Math.floor(pts.length * 0.8));
        var slc = pts.slice(lo, hi);
        var lat = 0, lon = 0;
        for (var j = 0; j < slc.length; j++) { lat += slc[j].lat; lon += slc[j].lon; }
        return { lat: lat / slc.length, lon: lon / slc.length };
      }
      var start = mid(sl.left, sl.right);
      var finish = fl && fl.left && fl.right ? mid(fl.left, fl.right) : null;
      var m1 = markMid("1");
      var m2 = markMid("2");
      var d12 = hav(m1, m2);
      var d1s = hav(m1, start);
      var d2s = hav(m2, start);
      var sf = hav(start, finish);
      if (sf != null && sf < 50 && d12 != null && d12 < 250) return "Windward / Leeward";
      if (d12 != null && d12 > 400 && d1s != null && d2s != null && d1s > 800 && d2s > 800) return "Quadrangle";
      if (d1s != null && d1s > 800 && d2s != null && d2s < 800) return "Triangle";
      return "";
    }
    function fmtLiveClock(ms) {
      var a = Math.abs(Number(ms) || 0);
      var tenths = Math.floor(a / 100);
      var s = Math.floor(tenths / 10);
      var t = tenths % 10;
      return (ms < 0 ? "T−" : "T+") + Math.floor(s / 60) + ":" + pad(s % 60) + "." + t;
    }
    function fitHudName(el, text) {
      if (!el) return;
      var t = (text || "").trim();
      var lines = /\s+\/\s+/.test(t) ? t.split(/\s+\/\s+/) : t.split(/\s+/);
      el.textContent = lines.length === 2 ? (lines[0] + "\n" + lines[1]) : t;
      el.style.fontSize = "";
    }
    function drawCourseLabel(ts) {
      var hud = document.getElementById("lipton-dev-map-hud");
      var nameEl = document.getElementById("lipton-dev-map-hud-name");
      var clockHud = document.getElementById("lipton-dev-map-hud-clock");
      if (!hud || !clockHud) return;
      var name = (courseFromTrail() || "").toUpperCase();
      var after = ts >= GUN_TS;
      clockHud.textContent = fmtLiveClock(ts - GUN_TS);
      hud.classList.toggle("is-after", after);
      hud.classList.toggle("is-nameless", !name);
      fitHudName(nameEl, name);
    }
    function setRateButtons() {
      if (rateEl) rateEl.textContent = RATE + "×";
      if (slowerBtn) slowerBtn.disabled = !trackerReady || RATE <= RATES[0];
      if (fasterBtn) fasterBtn.disabled = !trackerReady || RATE >= RATES[RATES.length - 1];
    }
    function bumpRate(dir) {
      var i = 0;
      var best = 0;
      for (i = 0; i < RATES.length; i++) {
        if (RATES[i] <= RATE) best = i;
      }
      var next = best + (dir > 0 ? 1 : -1);
      if (next < 0 || next >= RATES.length) return;
      RATE = RATES[next];
      lastWall = Date.now();
      setRateButtons();
    }
    function raceSpanMs() {
      return Math.max(1, PLAY_END_TS - PLAY_START_TS);
    }
    function syncScrub() {
      if (scrubbing || !scrubEl) return;
      var u = (playTs - PLAY_START_TS) / raceSpanMs();
      if (u < 0) u = 0;
      if (u > 1) u = 1;
      scrubEl.value = String(Math.round(u * 1000));
    }
    function applyScrub() {
      if (!scrubEl || !trackerReady) return;
      var ts = PLAY_START_TS + (Number(scrubEl.value) / 1000) * raceSpanMs();
      cancelRecallHorn();
      jump(ts);
    }
    function setPlayLabel() {
      if (!playBtn) return;
      playBtn.disabled = !trackerReady;
      playBtn.classList.toggle("is-playing", !!(trackerReady && playing));
      var lab = !trackerReady ? "Wait" : (playing ? "Pause" : "Play");
      playBtn.title = lab;
      playBtn.setAttribute("aria-label", lab);
    }
    function visiblePassLimit(ts) {
      var max = 0;
      for (var i = 0; i < PASSES.length; i++) {
        for (var b = 0; b < PASSES[i].boats.length; b++) {
          if (PASSES[i].boats[b].ts <= ts) max = i;
        }
      }
      return max;
    }
    function skipLastLegDelta(limit, i) {
      return false;
    }
    function passHeadLabel(idx) {
      var p = PASSES[idx];
      if (!p) return "";
      if (p.id === "ST" || p.label === "ST") return "ST";
      if (p.id === "FIN" || p.label === "Fin") return "Fin";
      var pin = p.label === "Pin" || Number(p.mark) === 4;
      var n = 0;
      var mark = Number(p.mark);
      for (var i = 0; i <= idx; i++) {
        var q = PASSES[i];
        if (!q || q.id === "ST" || q.id === "FIN" || q.label === "ST" || q.label === "Fin") continue;
        if (pin) {
          if (q.label === "Pin" || Number(q.mark) === 4) n += 1;
        } else if (Number(q.mark) === mark) n += 1;
      }
      if (pin) return n <= 1 ? "Pin" : "Pin·" + n;
      var base = "M" + mark;
      return n <= 1 ? base : base + "·" + n;
    }
    var lastHeadKey = "";
    var marksDetailOpen = false;
    function passIsMark(p) {
      if (!p) return false;
      if (p.id === "ST" || p.label === "ST") return false;
      if (p.id === "FIN" || p.label === "Fin") return false;
      return true;
    }
    function passIsFin(p) {
      return p && (p.id === "FIN" || p.label === "Fin");
    }
    function fleetN() {
      return Object.keys(BOATS).length;
    }
    function boatsAtPass(passIdx, ts) {
      var n = 0;
      var last = null;
      var p = PASSES[passIdx];
      if (!p) return { n: 0, last: null };
      Object.keys(BOATS).forEach(function (boat) {
        var t = tsAtPass(p, boat);
        if (t != null && t <= ts) {
          n += 1;
          if (last == null || t > last) last = t;
        }
      });
      return { n: n, last: last };
    }
    var FOLD_AFTER_MS = 10000;
    function passFolded(passIdx, ts) {
      if (passIdx < 1 || !PASSES[passIdx]) return false;
      var info = boatsAtPass(passIdx, ts);
      if (info.n < fleetN() || info.last == null) return false;
      return ts >= info.last + FOLD_AFTER_MS;
    }
    function showStCol(ts) {
      return !passFolded(1, ts);
    }
    function showDeltaAfter(i, ts, limit) {
      if (i >= limit) return false;
      if (passIsFin(PASSES[i + 1])) return true;
      return !passFolded(i + 1, ts);
    }
    function fillHead(limit) {
      if (!headRow) return;
      if (limit == null) limit = PASSES.length - 1;
      var ts = viewTs;
      var key = String(limit) + (showStCol(ts) ? "|ST" : "|noST") + (marksDetailOpen ? "|md1" : "|md0");
      for (var i = 0; i < limit; i++) key += showDeltaAfter(i, ts, limit) ? "|d" : "|f";
      if (key === lastHeadKey) return;
      lastHeadKey = key;
      var html = "<th class=\"rank-col\">Rank</th><th class=\"wc-meta-col\">Bow</th><th class=\"boat-name-col\">Boat Name</th><th class=\"club-col\">Club</th>";
      for (i = 0; i <= limit; i++) {
        if (i === 0 && !showStCol(ts)) continue;
        var p = PASSES[i];
        var lab = passHeadLabel(i);
        var title = "Lap " + p.lap + " mark " + p.mark;
        if (p.id === "FIN" || p.label === "Fin") title = "Finish time. Overall places are in the column to the left.";
        else if (p.id === "ST" || p.label === "ST") title = "Seconds after first legal start. OCS boats use the recross after they clear, not the OCS dip.";
        else if (passFolded(i, ts)) title = lab + " places vs previous mark";
        html += "<th class=\"timer-col" + (passIsFin(p) ? " timer-col--fin" : "") + (passIsMark(p) ? " timer-col--mark" : "") + (!marksDetailOpen && passIsMark(p) && passFolded(i, ts) ? " timer-col--tight" : "") + "\" title=\"" + esc(title) + "\"><span class=\"ld-mark-lab\">" + esc(lab) + "</span></th>";
        if (showDeltaAfter(i, ts, limit)) {
          if (passIsFin(PASSES[i + 1])) {
            html += "<th class=\"place-delta-col ld-overall-head\" title=\"Overall places vs start (sum of mark gains and losses). Arrow shows or hides mark times.\" aria-label=\"Overall place change. Show or hide mark times.\">" +
              "<span class=\"ld-fin-legend\" aria-hidden=\"true\"><i class=\"ld-tri ld-tri--up\"></i><i class=\"ld-tri ld-tri--down\"></i></span>" +
              "<button type=\"button\" class=\"ld-mark-twist\" data-mark-twist=\"1\" aria-expanded=\"" + (marksDetailOpen ? "true" : "false") + "\" title=\"" + (marksDetailOpen ? "Hide mark times" : "Show mark times") + "\" aria-label=\"" + (marksDetailOpen ? "Hide mark times" : "Show mark times") + "\">" + (marksDetailOpen ? "▾" : "▸") + "</button></th>";
          } else {
            var nlab = passHeadLabel(i + 1);
            html += "<th class=\"place-delta-col\" title=\"Places gained or lost " + esc(lab) + " to " + esc(nlab) + "\" aria-label=\"Place change " + esc(lab) + " to " + esc(nlab) + "\">±</th>";
          }
        }
      }
      headRow.innerHTML = html;
    }
    function tsAtPass(pass, boat) {
      if ((pass.id === "ST" || pass.label === "ST") && LEGAL_TS[boat] != null) {
        return LEGAL_TS[boat];
      }
      for (var i = 0; i < pass.boats.length; i++) {
        if (pass.boats[i].boat === boat) return pass.boats[i].ts;
      }
      return null;
    }
    function boatTimes(boat, ts) {
      var out = [];
      for (var i = 0; i < PASSES.length; i++) {
        var t = tsAtPass(PASSES[i], boat);
        out.push(t != null && t <= ts ? t : null);
      }
      return out;
    }
    function furthest(times) {
      var k = -1;
      for (var i = 0; i < times.length; i++) {
        if (times[i] != null) k = i;
      }
      if (k < 0) return { idx: -1, lab: null, ts: null, lap: 1 };
      var p = PASSES[k];
      return { idx: k, lab: passHeadLabel(k), ts: times[k], lap: p.lap };
    }
    function finishTs(boat) {
      for (var i = 0; i < FINISH.length; i++) {
        if (FINISH[i].boat === boat) return FINISH[i].ts;
      }
      return null;
    }
    function finCell(r, ts) {
      var ft = finishTs(r.boat);
      if (ft != null && ft <= ts) return fmtClock(ft - GUN_TS);
      return "";
    }
    function fmtBehindFirst(t) {
      if (ST_LEAD_TS == null) return "";
      var sec = (t - ST_LEAD_TS) / 1000;
      if (sec <= -0.05) return sec.toFixed(1);
      if (sec < 0.05) return "0.0";
      return "+" + sec.toFixed(1);
    }
    function knownLegSum(times) {
      var s = 0;
      for (var i = 1; i < times.length; i++) {
        if (times[i] != null && times[i - 1] != null) s += times[i] - times[i - 1];
      }
      return s;
    }
    function holeRemainder(times) {
      var st = times[0];
      var fin = times[times.length - 1];
      if (st == null || fin == null) return null;
      var rem = (fin - st) - knownLegSum(times);
      if (rem < 1500) return null;
      return rem;
    }
    function missingMarkIdx(times) {
      var miss = [];
      for (var i = 1; i < times.length - 1; i++) {
        if (times[i] == null) miss.push(i);
      }
      return miss;
    }
    var viewTs = PLAY_START_TS;
    function fleetMedianLeg(passIdx) {
      if (passIdx < 1 || !PASSES[passIdx - 1]) return null;
      var xs = [];
      var boats = PASSES[passIdx].boats || [];
      for (var k = 0; k < boats.length; k++) {
        var sail = boats[k].boat;
        var t = tsAtPass(PASSES[passIdx], sail);
        var p = tsAtPass(PASSES[passIdx - 1], sail);
        if (t == null || p == null || t > viewTs) continue;
        var d = t - p;
        if (d > 2000 && d < 2 * 3600 * 1000) xs.push(d);
      }
      if (xs.length < 3) return null;
      xs.sort(function (a, b) { return a - b; });
      return xs[Math.floor(xs.length / 2)];
    }
    function prevKnown(times, i) {
      for (var j = i - 1; j >= 0; j--) {
        if (times[j] != null) return { i: j, t: times[j] };
      }
      return null;
    }
    function nextKnown(times, i) {
      for (var k = i + 1; k < times.length; k++) {
        if (times[k] != null) return { i: k, t: times[k] };
      }
      return null;
    }
    function splitCell(times, i, boat) {
      var t = times[i];
      if (PASSES[i] && (PASSES[i].id === "ST" || PASSES[i].label === "ST")) {
        if (t == null) {
          return ocsPending(boat, viewTs) ? "OCS" : "";
        }
        var gap = fmtBehindFirst(t);
        if (OCS[boat]) return "OCS " + gap;
        return gap;
      }
      if (PASSES[i] && (PASSES[i].id === "FIN" || PASSES[i].label === "Fin")) {
        if (t == null) return "";
        return fmtClock(t - GUN_TS);
      }
      var med = fleetMedianLeg(i);
      if (t != null) {
        var prev = i > 0 ? times[i - 1] : null;
        if (prev != null) return fmtClock(t - prev);
        if (med != null) return fmtClock(med);
        return "";
      }
      var before = prevKnown(times, i);
      var after = nextKnown(times, i);
      if (before && after && after.i === i + 1) {
        var mashed = after.t - before.t;
        var nextMed = fleetMedianLeg(after.i);
        if (nextMed != null && mashed > nextMed * 1.8) return fmtClock(mashed - nextMed);
        if (med != null) return fmtClock(med);
        return fmtClock(mashed);
      }
      var miss = missingMarkIdx(times);
      if (miss.length === 1 && miss[0] === i) {
        var rem = holeRemainder(times);
        if (rem != null) return fmtClock(rem);
      }
      return "";
    }
    function pairRankMaps(ts) {
      var out = [];
      for (var i = 0; i < PASSES.length - 1; i++) {
        var a = PASSES[i];
        var b = PASSES[i + 1];
        var both = {};
        for (var x = 0; x < a.boats.length; x++) {
          var t1 = tsAtPass(a, a.boats[x].boat);
          if (t1 == null || t1 > ts) continue;
          var t2 = tsAtPass(b, a.boats[x].boat);
          if (t2 != null && t2 <= ts) both[a.boats[x].boat] = true;
        }
        function rankOf(pass) {
          var hit = [];
          for (var k = 0; k < pass.boats.length; k++) {
            var boat = pass.boats[k].boat;
            var t = tsAtPass(pass, boat);
            if (both[boat] && t != null && t <= ts) hit.push({ boat: boat, ts: t });
          }
          hit.sort(function (p, q) { return p.ts - q.ts; });
          var map = {};
          for (var n = 0; n < hit.length; n++) map[hit[n].boat] = n + 1;
          return map;
        }
        out.push({ prev: rankOf(a), next: rankOf(b) });
      }
      return out;
    }
    function deltaSpan(gained, flash) {
      if (gained == null) return "";
      var flashCls = flash && gained !== 0 ? " place-delta--flash" : "";
      var n;
      var cls;
      var label;
      var tri;
      if (gained > 0) {
        n = String(gained);
        cls = "place-delta--up";
        label = "Gained " + gained;
        tri = "up";
      } else if (gained < 0) {
        n = String(-gained);
        cls = "place-delta--down";
        label = "Lost " + n;
        tri = "down";
      } else {
        n = "0";
        cls = "place-delta--same";
        label = "No change";
        tri = "same";
      }
      return "<span class=\"place-delta " + cls + flashCls + "\" title=\"" + label + "\" aria-label=\"" + label + "\"><i class=\"ld-tri ld-tri--" + tri + "\" aria-hidden=\"true\"></i>" + n + "</span>";
    }
    function deltaGain(prevMap, nextMap, boat) {
      if (!prevMap || !nextMap) return null;
      var prev = prevMap[boat];
      var next = nextMap[boat];
      if (prev == null || next == null) return null;
      return prev - next;
    }
    function totalGain(boat, rankMaps) {
      if (!rankMaps || !rankMaps.length) return null;
      var sum = 0;
      var any = false;
      var i;
      for (i = 0; i < rankMaps.length; i++) {
        var g = deltaGain(rankMaps[i].prev, rankMaps[i].next, boat);
        if (g == null) continue;
        sum += g;
        any = true;
      }
      return any ? sum : null;
    }
    function rememberDelta(key, gained) {
      var flash = deltaSeen[key] !== gained;
      deltaSeen[key] = gained;
      return flash;
    }
    function deltaCell(boat, passIdx, prevMap, nextMap) {
      var gained = deltaGain(prevMap, nextMap, boat);
      if (gained == null) return "<td class=\"place-delta-col\"></td>";
      return "<td class=\"place-delta-col\">" + deltaSpan(gained, rememberDelta(boat + "|" + passIdx, gained)) + "</td>";
    }
    function foldMask(ts) {
      var mask = 0;
      var i;
      for (i = 1; i < PASSES.length; i++) {
        if (passFolded(i, ts)) mask |= (1 << i);
      }
      return mask;
    }
    function timerTd(r, i, rankMaps, ts) {
      var time = splitCell(r.times, i, r.boat);
      var p = PASSES[i];
      var isFin = passIsFin(p);
      var finCls = isFin ? " timer-col--fin" : "";
      if (isFin) return "<td class=\"timer-col" + finCls + "\">" + time + "</td>";
      if (!passFolded(i, ts)) return "<td class=\"timer-col\">" + time + "</td>";
      var gained = deltaGain(
        rankMaps[i - 1] && rankMaps[i - 1].prev,
        rankMaps[i - 1] && rankMaps[i - 1].next,
        r.boat
      );
      var flash = rememberDelta(r.boat + "|fold|" + i, gained);
      if (!marksDetailOpen) {
        return "<td class=\"timer-col timer-col--places\">" + deltaSpan(gained, flash) + "</td>";
      }
      return "<td class=\"timer-col timer-col--folded\">" + time + deltaSpan(gained, flash) + "</td>";
    }
    function boatHasStarted(boat, ts) {
      if (ts < GUN_TS) return false;
      if (ocsPending(boat, ts)) return true;
      return LEGAL_TS[boat] != null && ts >= LEGAL_TS[boat];
    }
    function boatStartTs(boat, ts) {
      if (ocsPending(boat, ts)) return GUN_TS;
      return LEGAL_TS[boat] != null ? LEGAL_TS[boat] : ts;
    }
    function resetRankPosts() {
      posted = {};
      postQueue = [];
      lastPostWall = 0;
      scrolledHome = false;
      if (postHoldTimer) {
        clearTimeout(postHoldTimer);
        postHoldTimer = null;
      }
      if (wrapEl) wrapEl.scrollTop = 0;
    }
    function syncPostQueue(rows, ts) {
      for (var i = 0; i < rows.length; i++) {
        var boat = rows[i].boat;
        if (posted[boat]) continue;
        var st = boatStartTs(boat, ts);
        if (!playing || scrubbing || ts - st > 3000) {
          posted[boat] = true;
          continue;
        }
        if (postQueue.indexOf(boat) < 0) postQueue.push(boat);
      }
    }
    function postIsDue() {
      if (!postQueue.length) return false;
      if (!playing || scrubbing) return true;
      return !lastPostWall || (Date.now() - lastPostWall >= POST_GAP_MS);
    }
    function takeDuePost() {
      if (!playing || scrubbing) {
        for (var i = 0; i < postQueue.length; i++) posted[postQueue[i]] = true;
        postQueue = [];
        return null;
      }
      if (!postIsDue()) return null;
      var boat = postQueue.shift();
      posted[boat] = true;
      lastPostWall = Date.now();
      return boat;
    }
    function rowByBoat(boat) {
      if (!tbody) return null;
      var nodes = tbody.querySelectorAll("tr[data-boat]");
      for (var i = 0; i < nodes.length; i++) {
        if (nodes[i].getAttribute("data-boat") === boat) return nodes[i];
      }
      return null;
    }
    function scrollTableTop() {
      if (!wrapEl) return;
      if (wrapEl.scrollTo) wrapEl.scrollTo({ top: 0, behavior: "smooth" });
      else wrapEl.scrollTop = 0;
    }
    function scrollNewRankIntoView(boat, shownN) {
      if (!wrapEl || !boat) return;
      if (shownN <= VISIBLE_BEFORE_SCROLL) {
        wrapEl.scrollTop = 0;
        return;
      }
      var row = rowByBoat(boat);
      if (!row) return;
      var wrapRect = wrapEl.getBoundingClientRect();
      var rowRect = row.getBoundingClientRect();
      var nextTop = wrapEl.scrollTop + (rowRect.bottom - wrapRect.bottom) + 6;
      if (nextTop < 0) nextTop = 0;
      if (wrapEl.scrollTo) wrapEl.scrollTo({ top: nextTop, behavior: "smooth" });
      else wrapEl.scrollTop = nextTop;
    }
    function holdThenScrollToRankOne(shownN) {
      if (!playing || scrubbing || scrolledHome || postHoldTimer) return;
      if (shownN < 17) return;
      postHoldTimer = setTimeout(function () {
        postHoldTimer = null;
        scrolledHome = true;
        scrollTableTop();
      }, POST_HOLD_MS);
    }
    function rowsAt(ts) {
      var names = {};
      Object.keys(BOATS).forEach(function (boat) { names[boat] = true; });
      Object.keys(trail.boats || {}).forEach(function (boat) { names[boat] = true; });
      PASSES.forEach(function (pass) {
        pass.boats.forEach(function (b) {
          names[b.boat] = true;
        });
      });
      var rows = Object.keys(names).filter(function (boat) {
        return boatHasStarted(boat, ts);
      }).map(function (boat) {
        var times = boatTimes(boat, ts);
        var far = furthest(times);
        return {
          boat: boat,
          times: times,
          farIdx: far.idx,
          farTs: far.ts,
          farLab: far.lab,
          farLap: far.lap
        };
      });
      rows.sort(function (a, b) {
        if (b.farIdx !== a.farIdx) return b.farIdx - a.farIdx;
        if (a.farTs != null && b.farTs != null && a.farTs !== b.farTs) return a.farTs - b.farTs;
        var ia = ident(a.boat);
        var ib = ident(b.boat);
        var ba = ia && ia.bow != null ? Number(ia.bow) : 99;
        var bb = ib && ib.bow != null ? Number(ib.bow) : 99;
        if (ba !== bb) return ba - bb;
        return String(a.boat).localeCompare(String(b.boat));
      });
      rows.forEach(function (r, i) { r.rank = i + 1; });
      return rows;
    }
    function leadMark(rows) {
      return rows.length ? rows[0].farLab : null;
    }
    function stateKey(rows, ts) {
      var passLimit = visiblePassLimit(ts);
      return "p" + passLimit + "|f" + foldMask(ts) + (marksDetailOpen ? "|md1" : "|md0") + "|" + rows.map(function (r) {
        var pending = ocsPending(r.boat, ts);
        var badge = mapBadge(r.boat, ts);
        var place = badge.place == null ? "" : badge.place;
        return [r.boat, pending ? "O" : "S", place, r.farIdx, r.farTs || ""].join(":");
      }).join("|");
    }
    function boatIconHtml(sail, ts, rank) {
      var pending = ocsPending(sail, ts);
      var paint = boatPaint(sail, false);
      var label = rank != null ? String(rank) : (pending ? "OCS" : "");
      var fs = label === "OCS" ? "5.2" : "8";
      var title = label ? (label === "OCS" ? "OCS" : "Rank " + label) : "Boat";
      return "<svg class=\"lipton-boat-dot r10-live-icon\" viewBox=\"0 0 24 24\" width=\"36\" height=\"36\" aria-hidden=\"true\" title=\"" + esc(title) + "\">" +
        "<circle cx=\"12\" cy=\"13.2\" r=\"8.1\" fill=\"" + paint.fill + "\" stroke=\"#fff\" stroke-width=\"1.5\"/>" +
        "<polygon points=\"12,3 15.8,8.4 8.2,8.4\" fill=\"" + paint.fill + "\" stroke=\"#fff\" stroke-width=\"1.1\"/>" +
        "<text x=\"12\" y=\"16\" text-anchor=\"middle\" fill=\"" + paint.ink + "\" font-size=\"" + fs + "\" font-weight=\"800\">" + esc(label) + "</text>" +
        "</svg>";
    }
    function rowHtml(r, unroll, rankMaps, passLimit) {
      var id = ident(r.boat);
      var pending = ocsPending(r.boat, viewTs);
      var medal = "";
      if (r.rank === 1) medal = " medal-gold";
      else if (r.rank === 2) medal = " medal-silver";
      else if (r.rank === 3) medal = " medal-bronze";
      var cls = medal + (unroll ? " lipton-unroll" : "") + (pending ? " ocs-pending" : "");
      var html = "<tr class=\"" + cls + "\" data-bow=\"" + esc(id ? id.bow : "") + "\" data-boat=\"" + esc(r.boat) + "\">";
      html += "<td class=\"rank-col rank-col--live-icon\">" + boatIconHtml(r.boat, viewTs, r.rank) + "</td>";
      html += "<td class=\"wc-meta-col\">" + bowCell(id) + "</td>";
      html += "<td class=\"boat-name-col\">" + boatNameCell(id) + "</td>";
      html += "<td class=\"club-col\">" + clubCell(id, pending) + "</td>";
      for (var i = 0; i <= passLimit; i++) {
        if (i === 0 && !showStCol(viewTs)) continue;
        html += timerTd(r, i, rankMaps, viewTs);
        if (showDeltaAfter(i, viewTs, passLimit)) {
          if (passIsFin(PASSES[i + 1])) {
            var net = totalGain(r.boat, rankMaps);
            html += "<td class=\"place-delta-col ld-overall-col\">" + deltaSpan(net, rememberDelta(r.boat + "|net", net)) + "</td>";
          } else {
            html += deltaCell(r.boat, i, rankMaps[i].prev, rankMaps[i].next);
          }
        }
      }
      html += "</tr>";
      return html;
    }
    function setSailed(rows) {
      if (!sailedEl) {
        fillChecksum();
        return;
      }
      if (viewTs < GUN_TS) {
        sailedEl.textContent = RACE_LAB + " · gun " + GUN_CLOCK + " · T−5 · approaching start";
        fillChecksum();
        return;
      }
      if (!rows.length) {
        sailedEl.textContent = "Race " + RACE_NO + " · gun " + GUN_CLOCK + " · approaching start";
        fillChecksum();
        return;
      }
      var lead = rows[0];
      if (lead.farIdx < 0) {
        var ocsN = 0;
        rows.forEach(function (r) { if (ocsPending(r.boat, viewTs)) ocsN += 1; });
        if (ocsN) {
          sailedEl.textContent = RACE_LAB + " · gun " + GUN_CLOCK + " · OCS " + ocsN;
        } else {
          sailedEl.textContent = RACE_LAB + " · gun " + GUN_CLOCK + " · approaching start";
        }
        fillChecksum();
        return;
      }
      var n = 0;
      rows.forEach(function (r) { if (r.farIdx === lead.farIdx) n += 1; });
      var tot = PASSES[lead.farIdx] ? PASSES[lead.farIdx].boats.length : n;
      var p = PASSES[lead.farIdx];
      var isFin = p && (p.id === "FIN" || p.label === "Fin");
      var isSt = p && (p.id === "ST" || p.label === "ST");
      var lapBit = !isFin && !isSt && lead.farLap > 1 ? " · lap " + lead.farLap : "";
      var ocsBit = isSt && Object.keys(OCS).length ? " · OCS " + Object.keys(OCS).join(",") : "";
      var rankLab = isSt ? "start" : lead.farLab;
      sailedEl.textContent = (isSt ? RACE_LAB + " · gun " + GUN_CLOCK : RACE_LAB + " replay") + " · " + lead.farLab + lapBit + " · " + n + " of " + tot + " · rank by " + rankLab + ocsBit;
      fillChecksum();
    }
    function sanityReport() {
      var maps = pairRankMaps(PLAY_END_TS);
      var names = {};
      PASSES.forEach(function (p) {
        (p.boats || []).forEach(function (b) { names[b.boat] = true; });
      });
      var timeFail = [];
      var placeFail = [];
      var legFail = [];
      Object.keys(names).forEach(function (sail) {
        var times = boatTimes(sail, PLAY_END_TS);
        var last = null;
        for (var i = 0; i < times.length; i++) {
          if (times[i] == null) continue;
          if (last != null && times[i] <= last) {
            timeFail.push(clubCode(sail));
            break;
          }
          last = times[i];
        }
        var complete = times.length && times.every(function (t) { return t != null; });
        if (!complete) return;
        var deltaSum = 0;
        var deltaN = 0;
        for (var j = 0; j < maps.length; j++) {
          var a = maps[j].prev[sail];
          var b = maps[j].next[sail];
          if (a == null || b == null) continue;
          deltaSum += a - b;
          deltaN += 1;
        }
        var stRank = maps.length ? maps[0].prev[sail] : null;
        var finRank = maps.length ? maps[maps.length - 1].next[sail] : null;
        if (stRank != null && finRank != null && deltaN === maps.length && deltaSum !== stRank - finRank) {
          placeFail.push(clubCode(sail) + " " + stRank + "→" + finRank);
        }
        if (Math.abs((times[times.length - 1] - times[0]) - knownLegSum(times)) > 1) {
          legFail.push(clubCode(sail));
        }
      });
      return { timeFail: timeFail, placeFail: placeFail, legFail: legFail };
    }
    function fillChecksum() {
      if (!checksumEl) return;
      var cs = data.checksum || {};
      var bits = [];
      if (cs.ok) {
        bits.push("marks ok");
      } else if (cs.gaps && cs.gaps.length) {
        bits.push("gaps " + cs.gaps.map(function (g) {
          return g.id + " " + (g.missing || []).map(clubCode).join(" ");
        }).join(" · "));
      }
      var san = sanityReport();
      if (!san.placeFail.length) bits.push("± ok");
      else bits.push("± fail " + san.placeFail.join(" "));
      if (!san.timeFail.length && !san.legFail.length) bits.push("times ok");
      else {
        if (san.timeFail.length) bits.push("times " + san.timeFail.join(" "));
        if (san.legFail.length) bits.push("legs " + san.legFail.join(" "));
      }
      checksumEl.textContent = bits.length ? "checksum " + bits.join(" · ") : "";
    }
    function clockText(ts, rows) {
      var clock = fmtClock(ts - GUN_TS);
      if (!rows.length) return clock + " → start";
      return clock;
    }
    function render(ts) {
      viewTs = ts;
      var all = rowsAt(ts);
      syncPostQueue(all, ts);
      var justPosted = takeDuePost();
      var rows = all.filter(function (r) { return posted[r.boat]; });
      rows.forEach(function (r, i) { r.rank = i + 1; });
      var rankMaps = pairRankMaps(ts);
      var passLimit = visiblePassLimit(ts);
      if (!rows.length) {
        tbody.innerHTML = "";
        if (wrapEl) setTableVisible(false);
        lastHeadKey = "";
        if (clockEl) clockEl.textContent = clockText(ts, rows);
        setSailed(rows);
        lastKey = stateKey(all, ts);
        drawMap(ts);
        syncScrub();
        return;
      }
      if (wrapEl) setTableVisible(true);
      fillHead(passLimit);
      var html = "";
      for (var i = 0; i < rows.length; i++) {
        var first = !seen[rows[i].boat];
        seen[rows[i].boat] = true;
        html += rowHtml(rows[i], first, rankMaps, passLimit);
      }
      tbody.innerHTML = html;
      if (clockEl) clockEl.textContent = clockText(ts, rows);
      setSailed(rows);
      lastKey = stateKey(all, ts);
      drawMap(ts);
      syncScrub();
      if (justPosted) {
        window.requestAnimationFrame(function () {
          scrollNewRankIntoView(justPosted, rows.length);
          holdThenScrollToRankOne(rows.length);
        });
      }
    }

    function jump(ts) {
      playTs = ts;
      lastWall = Date.now();
      lastKey = "";
      seen = {};
      resetRankPosts();
      deltaSeen = {};
      lastHdg = {};
      lastHdgAt = {};
      if (followFleet) cam = null;
      lastHeadKey = "";
      finishFlashUntil = {};
      resetTails(ts);
      var gunAt = GUN_TS - GUN_HORN_EARLY_MS - GUN_HORN_LEAD_MS * (RATE > 0 ? RATE : 1);
      if (ts < gunAt) {
        gunFired = false;
        cancelRecallHorn();
        stopHornSources();
        stopHornEls();
      } else {
        gunFired = true;
        cancelRecallHorn();
      }
      render(ts);
      syncScrub();
    }

    function tick() {
      if (playing && trackerReady) {
        var now = Date.now();
        var prevTs = playTs;
        playTs += (now - lastWall) * RATE;
        lastWall = now;
        var gunAt = GUN_TS - GUN_HORN_EARLY_MS - GUN_HORN_LEAD_MS * (RATE > 0 ? RATE : 1);
        if (prevTs < gunAt && playTs >= gunAt) fireGunHorn();
        if (playTs > PLAY_END_TS) {
          playTs = PLAY_END_TS;
          playing = false;
          setPlayLabel();
          armTailClear();
        }
        var rows = rowsAt(playTs);
        syncPostQueue(rows, playTs);
        var key = stateKey(rows, playTs);
        if (key !== lastKey || postIsDue()) {
          render(playTs);
        } else if (clockEl) {
          clockEl.textContent = clockText(playTs, rows);
        }
        drawMap(playTs);
        syncScrub();
      } else {
        lastWall = Date.now();
        if ((tailsUntil > 0 && Date.now() >= tailsUntil) || anyFinishPulse()) {
          if (tailsUntil > 0 && Date.now() >= tailsUntil) tailsUntil = -1;
          drawMap(playTs);
        }
      }
      window.requestAnimationFrame(tick);
    }

    function beginAfterTracker() {
      if (trackerReady) return;
      trackerReady = true;
      playTs = PLAY_END_TS;
      lastWall = Date.now();
      playing = false;
      resetHorns();
      frameCam(playTs);
      setPlayLabel();
      setRateButtons();
      render(playTs);
      if (sailedEl) sailedEl.textContent = RACE_LAB + " · gun " + GUN_CLOCK + " · finish · press Play to replay";
      fillChecksum();
    }

    function waitForTracker() {
      if (sailedEl) sailedEl.textContent = "Loading GPS trail…";
      setPlayLabel();
      setRateButtons();
      beginAfterTracker();
    }

    if (slowerBtn) slowerBtn.addEventListener("click", function () { if (trackerReady) bumpRate(-1); });
    if (fasterBtn) fasterBtn.addEventListener("click", function () { if (trackerReady) bumpRate(1); });
    if (scrubEl) {
      scrubEl.addEventListener("pointerdown", function () { scrubbing = true; });
      scrubEl.addEventListener("input", applyScrub);
      scrubEl.addEventListener("change", function () {
        applyScrub();
        scrubbing = false;
      });
    }
    window.addEventListener("pointerup", function () { scrubbing = false; });
    if (playBtn) {
      playBtn.addEventListener("pointerdown", function () { unlockGunHorn(); });
      playBtn.addEventListener("click", function () {
        if (!trackerReady) return;
        if (!playing) {
          unlockGunHorn();
          if (playTs >= PLAY_END_TS - 250) jump(PLAY_START_TS);
          playing = true;
        } else {
          playing = false;
        }
        lastWall = Date.now();
        setPlayLabel();
      });
    }
    if (soundBtn) {
      setSoundLabel();
      soundBtn.addEventListener("click", function () {
        if (soundOn) {
          soundOn = false;
          cancelRecallHorn();
          setSoundLabel();
          return;
        }
        unlockGunHorn();
      });
    }
    document.addEventListener("visibilitychange", function () {
      if (!document.hidden && gunCtx && gunCtx.state === "suspended") gunCtx.resume();
    });

    window.addEventListener("resize", function () {
      if (chartMap) chartMap.invalidateSize({ animate: false });
      if (followFleet) cam = null;
      frameCam(playTs);
      drawMap(playTs);
    });

    if (headRow) {
      headRow.addEventListener("click", function (ev) {
        var th = ev.target && ev.target.closest ? ev.target.closest("th.ld-overall-head") : null;
        if (!th || !th.querySelector("[data-mark-twist]")) return;
        ev.preventDefault();
        ev.stopPropagation();
        marksDetailOpen = !marksDetailOpen;
        lastHeadKey = "";
        lastKey = "";
        render(viewTs);
      });
    }
    fillHead(0);
    setRateButtons();
    waitForTracker();
    window.requestAnimationFrame(tick);
  }
})();
