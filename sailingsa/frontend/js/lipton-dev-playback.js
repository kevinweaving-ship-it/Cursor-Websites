/**
 * Lipton 2026 -dev only. Replay sandbox — not live, not Nett.
 * Rank re-sorts at each mark *pass* (M1 can appear again on lap 2+).
 * Place deltas sit between consecutive passes. Times are mm:ss, no T+.
 * Data: /js/lipton-dev-replay.json
 */
(function () {
  var CACHE = "20260827az";
  var RACE_Q = Number((new URLSearchParams(location.search)).get("race") || 0);
  function jsonUrl(kind, race) {
    if (!race || race === 4) return "/js/lipton-dev-" + kind + ".json?v=" + CACHE;
    return "/js/lipton-dev-" + kind + "-r" + race + ".json?v=" + CACHE;
  }
  var DATA_URL = jsonUrl("replay", RACE_Q);
  var TRAIL_URL = jsonUrl("trail", RACE_Q);

  function bindRaceButtons(active) {
    var want = Number(active || RACE_Q || 4);
    document.querySelectorAll("#lipton-dev-races [data-race]").forEach(function (btn) {
      var n = Number(btn.getAttribute("data-race"));
      btn.classList.toggle("is-active", n === want);
      btn.setAttribute("aria-pressed", n === want ? "true" : "false");
      if (btn.getAttribute("data-bound") === "1") return;
      btn.setAttribute("data-bound", "1");
      btn.addEventListener("click", function () {
        var u = new URL(location.href);
        u.searchParams.set("race", String(n));
        location.assign(u.pathname + "?" + u.searchParams.toString());
      });
    });
  }
  bindRaceButtons(RACE_Q || 4);
  fetch("/js/lipton-dev-races.json?v=" + CACHE, { cache: "no-store" })
    .then(function (res) { return res.ok ? res.json() : null; })
    .then(function (meta) {
      if (!meta) return;
      (meta.races || []).forEach(function (r) {
        var btn = document.querySelector('#lipton-dev-races [data-race="' + r.n + '"]');
        if (!btn) return;
        var gun = String(r.gun_sast || "").slice(11, 16);
        var ocs = (r.ocs || []).length ? " · OCS " + r.ocs.join(",") : "";
        var course = r.course ? " · " + r.course : "";
        btn.title = "Race " + r.n + course + " · gun " + gun + (r.packed ? "" : " · GPS not packed yet") + ocs;
        btn.classList.toggle("is-unpacked", !r.packed);
      });
    })
    .catch(function () {});

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
          ? ("Race " + RACE_Q + " GPS not packed on -dev yet. Choose R4.")
          : "Replay data failed to load";
      }
      console.error(err);
    });

  function start(data, trail) {
    var PASSES = loadPasses(data);
    var BOATS = data.boats || {};
    var GUN_TS = Number(data.gun_ts_ms);
    var PLAY_START_TS = GUN_TS - 10000;
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
    var RATE = Number(data.default_rate || 1);
    var SETTLE_MS = 2500;
    var playing = false;
    var trackerReady = false;
    var playTs = PLAY_START_TS;
    var lastWall = Date.now();
    var lastKey = "";
    var seen = {};
    var deltaSeen = {};

    var tbody = document.getElementById("lipton-dev-tbody");
    var clockEl = document.getElementById("lipton-dev-clock");
    var sailedEl = document.getElementById("lipton-dev-sailed");
    var checksumEl = document.getElementById("lipton-dev-checksum");
    var mapEl = document.getElementById("lipton-dev-map");
    var playBtn = document.getElementById("lipton-dev-play");
    var headRow = document.getElementById("lipton-dev-thead-row");
    if (!tbody) return;

    function ident(tracker) {
      return BOATS[tracker] || null;
    }
    function clubCode(sail) {
      var id = ident(sail);
      if (!id) return sail;
      return id.mapClub || id.club || sail;
    }
    function boatNameCell(id) {
      if (!id) return "";
      return "<a href=\"" + esc(id.nameHref) + "\" class=\"rs-boat-name-sponsors rs-boat-name-sponsors--link\" title=\"" + esc(id.title) + "\">" + id.nameInner + "</a>";
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
    function initChart() {
      var el = document.getElementById("lipton-dev-chart");
      if (!el || !window.L || chartMap) return;
      chartMap = L.map(el, {
        zoomControl: false,
        attributionControl: true,
        dragging: false,
        scrollWheelZoom: false,
        doubleClickZoom: false,
        boxZoom: false,
        keyboard: false,
        zoomSnap: 0,
        zoomAnimation: false,
        fadeAnimation: false,
        markerZoomAnimation: false,
        inertia: false
      }).setView([-33.901, 18.423], 15);
      L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {
        maxZoom: 19,
        attribution: "Tiles © Esri"
      }).addTo(chartMap);
      L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}", {
        maxZoom: 19,
        opacity: 0.85,
        attribution: "Labels © Esri"
      }).addTo(chartMap);
    }
    function syncChart() {
      if (!chartMap || !mapBounds) return;
      chartMap.invalidateSize({ animate: false });
      var lat = mapBounds.midLat;
      var lon = mapBounds.midLon;
      var cos = Math.max(0.2, Math.cos(lat * Math.PI / 180));
      var z = Math.log(mapBounds.scale * 156543.03392 * cos) / Math.LN2;
      if (!(z > 0)) z = 15;
      if (z < 13) z = 13;
      if (z > 19) z = 19;
      chartMap.setView([lat, lon], z, { animate: false });
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
    var BOAT_LEN_M = 6.71;
    var TAIL_M = BOAT_LEN_M * 10;
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
      } else {
        var aPan = playing ? 0.12 : 1;
        var aZoom = playing ? 0.08 : 1;
        if (playing && target.scale < cam.scale) aZoom = 0.22;
        cam.midLat += (target.midLat - cam.midLat) * aPan;
        cam.midLon += (target.midLon - cam.midLon) * aPan;
        cam.scale += (target.scale - cam.scale) * aZoom;
        cam.cos = Math.cos(cam.midLat * Math.PI / 180);
        cam.w = w;
        cam.h = h;
      }
      mapBounds = cam;
      syncChart();
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
      var ft = finishTs(sail);
      if (ft != null && ts >= ft && FIN_POS[sail]) {
        return { lat: FIN_POS[sail].lat, lon: FIN_POS[sail].lon, hdg: lastHdg[sail] || 0, i: 0, j: 0 };
      }
      var b = trail.boats[sail];
      var pos = sampleAt(b, ts);
      if (!pos) return null;
      pos.hdg = blendHdg(sail, headingAt(b, pos));
      return pos;
    }
    function markAt(k, ts) {
      return sampleAt(trail.marks[k], ts);
    }
    function metersPx(m) {
      return Math.max(4, m * mapBounds.scale);
    }
    function drawBoatIcon(p, hdg, fill, stroke) {
      var r = 7;
      mapCtx.beginPath();
      mapCtx.arc(p.x, p.y, r, 0, Math.PI * 2);
      mapCtx.fillStyle = fill;
      mapCtx.fill();
      mapCtx.strokeStyle = stroke;
      mapCtx.lineWidth = 0.9;
      mapCtx.stroke();
      mapCtx.save();
      mapCtx.translate(p.x, p.y);
      mapCtx.rotate((hdg || 0) * Math.PI / 180);
      mapCtx.beginPath();
      mapCtx.moveTo(0, -r - 3.6);
      mapCtx.lineTo(3.1, -r + 1.2);
      mapCtx.lineTo(-3.1, -r + 1.2);
      mapCtx.closePath();
      mapCtx.fillStyle = fill === "#16a34a" ? "#bbf7d0" : "#ffffff";
      mapCtx.fill();
      mapCtx.restore();
    }
    function tailHits(b, ts) {
      var now = sampleAt(b, ts);
      if (!now) return [];
      var hits = [now];
      var acc = 0;
      var lastI = now.i != null ? now.i : Math.floor((ts - GRID_ORIGIN) / trail.step_ms);
      var idx = hitBack(b, lastI - 1);
      var wantM = Math.max(TAIL_M, 28 / Math.max(mapBounds && mapBounds.scale ? mapBounds.scale : 0.4, 0.08));
      while (idx >= 0) {
        var gap = lastI - idx;
        var cur = { lat: b.lat[idx], lon: b.lon[idx], i: idx };
        var step = distM(hits[hits.length - 1], cur);
        if (gap > 45) break;
        if (step > 14 * Math.min(gap, 8)) break;
        acc += step;
        hits.push(cur);
        if (acc >= wantM) break;
        lastI = idx;
        idx = hitBack(b, idx - 1);
      }
      hits.reverse();
      if (hits.length < 2) return hits;
      var dense = [];
      for (var s = 0; s < hits.length - 1; s++) {
        var a = hits[s];
        var c = hits[s + 1];
        var span = (c.i != null && a.i != null) ? (c.i - a.i) : 1;
        dense.push(a);
        if (span <= 2) {
          var p0 = hits[s - 1] || a;
          var p3 = hits[s + 2] || c;
          var steps = 5;
          for (var u = 1; u < steps; u++) dense.push(catmull(p0, a, c, p3, u / steps));
        }
      }
      dense.push(hits[hits.length - 1]);
      return dense;
    }
    function drawTail(sail, ts) {
      var b = trail.boats[sail];
      if (!b) return;
      var hits = tailHits(b, ts);
      if (hits.length < 2) return;
      var screen = hits.map(function (pt) { return xy(pt.lat, pt.lon); });
      var left = [];
      var right = [];
      for (var i = 0; i < screen.length; i++) {
        var dx, dy;
        if (i === 0) {
          dx = screen[1].x - screen[0].x;
          dy = screen[1].y - screen[0].y;
        } else if (i === screen.length - 1) {
          dx = screen[i].x - screen[i - 1].x;
          dy = screen[i].y - screen[i - 1].y;
        } else {
          dx = screen[i + 1].x - screen[i - 1].x;
          dy = screen[i + 1].y - screen[i - 1].y;
        }
        var len = Math.sqrt(dx * dx + dy * dy) || 1;
        var nx = -dy / len;
        var ny = dx / len;
        var along = i / (screen.length - 1);
        var zoom = Math.max(1, 0.45 / Math.max(mapBounds.scale, 0.12));
        var w = (0.4 + along * along * 3.2) * Math.min(zoom, 2.2);
        left.push({ x: screen[i].x + nx * w, y: screen[i].y + ny * w });
        right.push({ x: screen[i].x - nx * w, y: screen[i].y - ny * w });
      }
      mapCtx.beginPath();
      mapCtx.moveTo(left[0].x, left[0].y);
      for (var L = 1; L < left.length; L++) mapCtx.lineTo(left[L].x, left[L].y);
      for (var R = right.length - 1; R >= 0; R--) mapCtx.lineTo(right[R].x, right[R].y);
      mapCtx.closePath();
      var hot = ocsPending(sail, ts);
      mapCtx.fillStyle = hot ? "rgba(252,165,165,0.22)" : "rgba(226,232,240,0.22)";
      mapCtx.fill();
      mapCtx.beginPath();
      mapCtx.moveTo(screen[0].x, screen[0].y);
      for (var s = 1; s < screen.length; s++) mapCtx.lineTo(screen[s].x, screen[s].y);
      mapCtx.strokeStyle = hot ? "rgba(254,202,202,0.85)" : "rgba(248,250,252,0.85)";
      mapCtx.lineWidth = Math.max(1.2, 0.5 / Math.max(mapBounds.scale, 0.12));
      mapCtx.lineJoin = "round";
      mapCtx.lineCap = "round";
      mapCtx.stroke();
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
      mapCtx.fillText(label, (a.x + b.x) / 2 + 6, (a.y + b.y) / 2 - 6);
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
      var fill = "#f8fafc";
      var stroke = "rgba(15,23,42,0.45)";
      var ink = "#0f172a";
      if (info.pending) {
        fill = "#fff7ed";
        stroke = "#dc2626";
        ink = "#dc2626";
      } else if (info.started && !info.onMark) {
        fill = "#16a34a";
        stroke = "#14532d";
        ink = "#ffffff";
      }
      drawBoatIcon(p, hdg, fill, stroke);
      if (info.place != null) {
        mapCtx.fillStyle = ink;
        mapCtx.font = "bold 8px sans-serif";
        mapCtx.textAlign = "center";
        mapCtx.textBaseline = "middle";
        mapCtx.fillText(String(info.place), p.x, p.y + 0.4);
      }
      if (info.onMark && !info.finished) drawDelta(p.x - 10, p.y - 1, info.leg, "right");
      var lx = p.x + 10;
      var ly = p.y - 1;
      mapCtx.font = "bold 8px sans-serif";
      mapCtx.textAlign = "left";
      mapCtx.textBaseline = "middle";
      mapCtx.fillStyle = info.pending ? "#f87171" : "#ffffff";
      mapCtx.fillText(club, lx, ly);
      if (info.onMark) {
        var cw = mapCtx.measureText(club).width;
        drawDelta(lx + cw + 3, ly, info.total, "left");
      }
      mapCtx.textAlign = "start";
      mapCtx.textBaseline = "alphabetic";
    }
    function drawMap(ts) {
      frameCam(ts);
      if (!mapCtx || !mapBounds) return;
      var w = mapBounds.w;
      var h = mapBounds.h;
      mapCtx.clearRect(0, 0, w, h);
      mapCtx.fillStyle = "rgba(0, 10, 24, 0.08)";
      mapCtx.fillRect(0, 0, w, h);
      var zone = Math.min(metersPx(20.1), 11);
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
        mapCtx.arc(p.x, p.y, focus ? 4 : 2.8, 0, Math.PI * 2);
        mapCtx.fillStyle = focus ? "#fbbf24" : "#f59e0b";
        mapCtx.fill();
        mapCtx.fillStyle = "#ffffff";
        mapCtx.font = focus ? "bold 12px sans-serif" : "bold 10px sans-serif";
        mapCtx.fillText("M" + k, p.x + 8, p.y + 4);
      });
      Object.keys(trail.boats || {}).forEach(function (sail) {
        drawTail(sail, ts);
      });
      drawGate(trail.start_line, focusGate === "start_line" ? "#38bdf8" : "rgba(56,189,248,0.4)", "START", "Pin", "RC");
      drawGate(trail.finish_line, focusGate === "finish_line" ? "#fbbf24" : "rgba(251,191,36,0.35)", "FINISH", "Pin", "RC");
      Object.keys(trail.boats || {}).forEach(function (sail) {
        var pos = posAt(sail, ts);
        if (!pos) return;
        var p = xy(pos.lat, pos.lon);
        drawBoatLabel(p, pos.hdg, sail, ts);
      });
      drawCourseLabel();
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
    function drawCourseLabel() {
      var label = courseFromTrail();
      if (!label || !mapCtx || !mapBounds) return;
      var pad = 10;
      mapCtx.save();
      mapCtx.font = "bold 13px sans-serif";
      mapCtx.textAlign = "right";
      mapCtx.textBaseline = "top";
      var text = label.toUpperCase();
      var tw = mapCtx.measureText(text).width;
      var x = mapBounds.w - pad;
      var y = pad;
      mapCtx.fillStyle = "rgba(0,31,63,0.62)";
      mapCtx.fillRect(x - tw - 8, y - 2, tw + 16, 22);
      mapCtx.fillStyle = "#ffffff";
      mapCtx.fillText(text, x, y);
      mapCtx.restore();
    }
    function setRateButtons() {
      [].forEach.call(document.querySelectorAll("[data-rate]"), function (btn) {
        btn.classList.toggle("is-active", Number(btn.getAttribute("data-rate")) === RATE);
        btn.disabled = !trackerReady;
      });
    }
    function setPlayLabel() {
      if (!playBtn) return;
      if (!trackerReady) {
        playBtn.disabled = true;
        playBtn.textContent = "Wait";
        return;
      }
      playBtn.disabled = false;
      playBtn.textContent = playing ? "Pause" : "Play";
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
      var n = 0;
      var mark = Number(p.mark);
      for (var i = 0; i <= idx; i++) {
        var q = PASSES[i];
        if (!q || q.id === "ST" || q.id === "FIN" || q.label === "ST" || q.label === "Fin") continue;
        if (Number(q.mark) === mark) n += 1;
      }
      var base = "M" + mark;
      return n <= 1 ? base : base + "·" + n;
    }
    var lastHeadLimit = -1;
    function fillHead(limit) {
      if (!headRow) return;
      if (limit == null) limit = PASSES.length - 1;
      if (limit === lastHeadLimit) return;
      lastHeadLimit = limit;
      var html = "<th class=\"rank-col\">Rank</th><th class=\"wc-meta-col\">Bow</th><th class=\"boat-name-col\">Boat</th><th class=\"club-col\">Club</th>";
      for (var i = 0; i <= limit; i++) {
        var p = PASSES[i];
        var lab = passHeadLabel(i);
        var title = "Lap " + p.lap + " mark " + p.mark;
        if (p.id === "FIN" || p.label === "Fin") title = "Finish";
        else if (p.id === "ST" || p.label === "ST") title = "Seconds after first legal start. OCS boats use the recross after they clear, not the OCS dip.";
        html += "<th class=\"timer-col\" title=\"" + esc(title) + "\">" + esc(lab) + "</th>";
        if (i < limit && !skipLastLegDelta(limit, i)) {
          var nlab = passHeadLabel(i + 1);
          html += "<th class=\"place-delta-col\" title=\"Places gained or lost " + esc(lab) + " to " + esc(nlab) + "\" aria-label=\"Place change " + esc(lab) + " to " + esc(nlab) + "\">±</th>";
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
    function deltaCell(boat, passIdx, prevMap, nextMap) {
      if (!prevMap || !nextMap) return "<td class=\"place-delta-col\"></td>";
      var prev = prevMap[boat];
      var next = nextMap[boat];
      if (prev == null || next == null) return "<td class=\"place-delta-col\"></td>";
      var gained = prev - next;
      var key = boat + "|" + passIdx;
      var flash = deltaSeen[key] !== gained;
      deltaSeen[key] = gained;
      var flashCls = flash && gained !== 0 ? " place-delta--flash" : "";
      if (gained > 0) {
        return "<td class=\"place-delta-col\"><span class=\"place-delta place-delta--up" + flashCls + "\" title=\"Gained " + gained + "\" aria-label=\"Gained " + gained + "\">▲" + gained + "</span></td>";
      }
      if (gained < 0) {
        var lost = -gained;
        return "<td class=\"place-delta-col\"><span class=\"place-delta place-delta--down" + flashCls + "\" title=\"Lost " + lost + "\" aria-label=\"Lost " + lost + "\">▼" + lost + "</span></td>";
      }
      return "<td class=\"place-delta-col\"><span class=\"place-delta place-delta--same\" title=\"No change\" aria-label=\"No change\">■0</span></td>";
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
      var rows = Object.keys(names).map(function (boat) {
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
    function stateKey(rows) {
      return rows.map(function (r) { return r.rank + ":" + r.boat + ":" + r.farIdx; }).join("|");
    }
    function rowHtml(r, unroll, rankMaps, passLimit) {
      var id = ident(r.boat);
      var pending = ocsPending(r.boat, viewTs);
      var medal = r.rank === 1 ? " medal-gold" : r.rank === 2 ? " medal-silver" : r.rank === 3 ? " medal-bronze" : "";
      var cls = medal + (unroll ? " lipton-unroll" : "") + (pending ? " ocs-pending" : "");
      var html = "<tr class=\"" + cls + "\" data-bow=\"" + esc(id ? id.bow : "") + "\" data-boat=\"" + esc(r.boat) + "\">";
      html += "<td class=\"rank-col\">" + r.rank + "</td>";
      html += "<td class=\"wc-meta-col\">" + bowCell(id) + "</td>";
      html += "<td class=\"boat-name-col\">" + boatNameCell(id) + "</td>";
      html += "<td class=\"club-col\">" + clubCell(id, pending) + "</td>";
      for (var i = 0; i <= passLimit; i++) {
        html += "<td class=\"timer-col\">" + splitCell(r.times, i, r.boat) + "</td>";
        if (i < passLimit && !skipLastLegDelta(passLimit, i)) {
          html += deltaCell(r.boat, i, rankMaps[i].prev, rankMaps[i].next);
        }
      }
      html += "</tr>";
      return html;
    }
    function setSailed(rows) {
      if (!sailedEl) return;
      if (viewTs < GUN_TS) {
        sailedEl.textContent = RACE_LAB + " · gun " + GUN_CLOCK + " · T−10 · approaching start";
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
        sailedEl.textContent = RACE_LAB + " · gun " + GUN_CLOCK + " · approaching start";
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
      var rows = rowsAt(ts);
      var rankMaps = pairRankMaps(ts);
      var passLimit = visiblePassLimit(ts);
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
      lastKey = stateKey(rows);
      drawMap(ts);
    }

    function jump(ts) {
      playTs = ts;
      lastWall = Date.now();
      lastKey = "";
      seen = {};
      deltaSeen = {};
      lastHdg = {};
      lastHdgAt = {};
      cam = null;
      lastHeadLimit = -1;
      render(ts);
    }

    function tick() {
      if (playing && trackerReady) {
        var now = Date.now();
        playTs += (now - lastWall) * RATE;
        lastWall = now;
        if (playTs > PLAY_END_TS) {
          playTs = PLAY_END_TS;
          playing = false;
          setPlayLabel();
        }
        var rows = rowsAt(playTs);
        var key = stateKey(rows);
        if (key !== lastKey) {
          render(playTs);
        } else if (clockEl) {
          clockEl.textContent = clockText(playTs, rows);
        }
        drawMap(playTs);
      } else {
        lastWall = Date.now();
      }
      window.requestAnimationFrame(tick);
    }

    function beginAfterTracker() {
      if (trackerReady) return;
      trackerReady = true;
      playTs = PLAY_START_TS;
      lastWall = Date.now();
      playing = false;
      frameCam(playTs);
      setPlayLabel();
      setRateButtons();
      render(playTs);
      if (sailedEl) sailedEl.textContent = RACE_LAB + " · gun " + GUN_CLOCK + " · T−10 · press Play";
      fillChecksum();
    }

    function waitForTracker() {
      if (sailedEl) sailedEl.textContent = "Loading GPS trail…";
      setPlayLabel();
      setRateButtons();
      beginAfterTracker();
    }

    document.querySelectorAll("[data-jump]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var key = btn.getAttribute("data-jump");
        var ts = key === "pre" ? PLAY_START_TS : key === "gun" ? GUN_TS : key === "finish" ? PLAY_END_TS : PLAY_START_TS;
        if (!ts) return;
        jump(ts);
      });
    });
    document.querySelectorAll("[data-rate]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        if (!trackerReady) return;
        RATE = Number(btn.getAttribute("data-rate")) || 1;
        lastWall = Date.now();
        setRateButtons();
      });
    });
    if (playBtn) {
      playBtn.addEventListener("click", function () {
        if (!trackerReady) return;
        playing = !playing;
        lastWall = Date.now();
        setPlayLabel();
      });
    }

    window.addEventListener("resize", function () {
      cam = null;
      frameCam(playTs);
      drawMap(playTs);
    });

    fillHead(0);
    setRateButtons();
    waitForTracker();
    window.requestAnimationFrame(tick);
  }
})();
