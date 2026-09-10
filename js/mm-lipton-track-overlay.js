/**
 * MM Event Reels tracking overlay — boats/marks only on the video water.
 * No map tiles. Race 7 test clip races right → left across the bottom strip.
 * Clock is the live reel go-live stamp + video time. Boat noses follow the
 * on-screen GPS track. Icons/colours/tails match tracking-dev2. Each clip has
 * its own camera recipe. Rounding keeps one projection: boats approach
 * right → left. After rounding they sail left → right. Zoom on where
 * 60–70% of the fleet is; stragglers sail into view. 1st is always in
 * view. The mark being rounded stays on screen. Pin/RC, M1 and Fin come
 * from the GPS map. Scale is along-span only (true px/m). Do not shrink
 * X to fit Y. Marks never jump: they are frozen world points.
 */
(function (root) {
  'use strict';

  var COLORS = {
    HYC: '#2563eb',
    RCYC: '#e11d48',
    KYC: '#16a34a',
    RNYC: '#7c3aed',
    WBYC: '#ea580c',
    FBYC: '#0891b2',
    SBYC: '#ca8a04',
    PYC: '#db2777',
    LDYC: '#4f46e5',
    GLYC: '#65a30d',
    BYC: '#0d9488',
    TSC: '#9333ea',
    WYAC: '#f59e0b',
    RCYCA: '#64748b',
    'RCYC Academy': '#64748b',
    UCT: '#0284c7',
    UCTYC: '#0284c7',
    IZI: '#be123c',
    IZIVUNGUVUNGU: '#be123c',
    LYCN: '#15803d',
    LYC: '#15803d'
  };
  var OVERALL_STICKER = { 1: '#facc15', 2: '#2563eb', 3: '#dc2626' };
  var trail = null;
  var replay = null;
  var scores = null;
  var ready = false;
  var heldCam = null;
  var heldCamTs = 0;
  var clipId = '';
  var clipRule = null;
  var raceCache = {};
  var camPhase = '';
  var lockApproachHdg = null;
  var markLock = null;
  var loadGen = 0;
  var heldIconStep = 1;
  var tightMarkHold = false;
  var heldSceneScale = null;
  var startLock = null;

  function clipR(race, kind, extra) {
    var o = { race: race, kind: kind || 'round', approach: 'rtl', holdN: 6, offsetMs: 0 };
    var k;
    if (extra) {
      for (k in extra) {
        if (Object.prototype.hasOwnProperty.call(extra, k)) o[k] = extra[k];
      }
    }
    return o;
  }

  /* SYNC RULE — every clip:
   * 1. Start from the video date stamp (started_at).
   * 2. Find an event IN the video: on-screen text, STT countdown, gun horn,
   *    or commentary (“round 1st boat”).
   * 3. Tracking already has that event’s exact time (gun, 1st mark rounding).
   * 4. offsetMs = gpsEvent − (stamp + videoTimeOfEvent).
   *    That is how much the stamp was off. Use it for the whole clip.
   * Clock = stamp + video.currentTime + offsetMs. Always 1×.
   */
  var CLIP_RULES = {
    '2622643364847262': clipR(7, 'round', {
      offsetMs: 36000,
      stamp: '2026-08-28T16:19:00+02:00',
      videoEvent: 'STT around the mark ~3:07',
      gpsEvent: 'R7 1st at Pin 16:22:43',
      stampOff: '+36s'
    }),
    '2410502969472697': clipR(7, 'round'),
    '1014880974840710': clipR(7, 'start', {
      approach: 'ltr',
      offsetMs: 24200,
      durationSec: 175,
      stamp: '2026-08-28T15:55:00+02:00',
      videoEvent: 'STT 3-2-1 + gun horn 1:36.8',
      gpsEvent: 'R7 gun 15:57:01',
      stampOff: '+24.2s'
    }),
    '26023759437321260': clipR(5, 'round'),
    '1587763379559775': clipR(5, 'round'),
    '4518629078350390': clipR(5, 'start'),
    '1751846282795149': clipR(4, 'finish'),
    '2111285223132517': clipR(4, 'round'),
    '1588170962712352': clipR(4, 'round'),
    '1582165340314238': clipR(4, 'round'),
    '1079923421076157': clipR(4, 'start'),
    '825961863876577': clipR(3, 'round'),
    '1530770848344300': clipR(3, 'round'),
    '1802153794291569': clipR(3, 'round'),
    '1813350889838726': clipR(3, 'round'),
    '1025386753667866': clipR(3, 'start'),
    '940083808452432': clipR(2, 'finish'),
    '942850414812890': clipR(2, 'round'),
    '3239679922895545': clipR(2, 'round'),
    '1384453329808359': clipR(2, 'round')
  };
  /* Race files e.g. /js/lipton-dev-trail-r7.json /js/lipton-dev-replay-r7.json */

  function ruleFor(id) {
    return CLIP_RULES[String(id || '')] || null;
  }

  function usesClip(id) {
    return !!ruleFor(id);
  }

  function kindFor(id) {
    var r = ruleFor(id);
    return r && r.kind ? r.kind : '';
  }

  function offsetMsFor(id) {
    var r = ruleFor(id);
    return r && r.offsetMs != null ? r.offsetMs : 0;
  }

  function load(id, done) {
    if (typeof id === 'function') {
      done = id;
      id = clipId;
    }
    var rule = ruleFor(id);
    if (String(id || '') !== clipId) {
      heldCam = null;
      heldCamTs = 0;
      lockApproachHdg = null;
      markLock = null;
      camPhase = '';
      heldIconStep = 1;
      tightMarkHold = false;
      heldSceneScale = null;
      startLock = null;
    }
    clipId = String(id || '');
    clipRule = rule;
    if (!done) done = function () {};
    if (!rule) {
      ready = false;
      done();
      return;
    }
    if (raceCache[rule.race] && scores) {
      trail = raceCache[rule.race].trail;
      replay = raceCache[rule.race].replay;
      ready = true;
      done();
      return;
    }
    var gen = ++loadGen;
    Promise.all([
      fetch('/js/lipton-dev-trail-r' + rule.race + '.json').then(function (r) { return r.json(); }),
      fetch('/js/lipton-dev-replay-r' + rule.race + '.json').then(function (r) { return r.json(); }),
      scores
        ? Promise.resolve(scores)
        : fetch('/js/lipton-dev-series-scores.json').then(function (r) { return r.json(); })
    ])
      .then(function (pack) {
        if (gen !== loadGen) return;
        trail = pack[0];
        replay = pack[1];
        scores = pack[2];
        raceCache[rule.race] = { trail: trail, replay: replay };
        ready = true;
        done();
      })
      .catch(function () {
        if (gen !== loadGen) return;
        ready = false;
      });
  }

  function sampleAt(series, ts) {
    if (!series || series.lat == null) return null;
    if (typeof series.lat === 'number') return { lat: series.lat, lon: series.lon, i: 0 };
    var origin = Number(trail.grid_start_ts_ms);
    var step = Number(trail.step_ms) || 1000;
    var n = Number(trail.n) || series.lat.length;
    var i = Math.floor((ts - origin) / step);
    if (i < 0) i = 0;
    if (i > n - 1) i = n - 1;
    while (i >= 0 && series.lat[i] == null) i -= 1;
    if (i < 0) {
      i = 0;
      while (i < series.lat.length && series.lat[i] == null) i += 1;
      if (i >= series.lat.length) return null;
    }
    return { lat: series.lat[i], lon: series.lon[i], i: i };
  }

  function hitBack(series, i) {
    var k = i;
    while (k >= 0 && (!series || series.lat == null || series.lat[k] == null)) k -= 1;
    return k;
  }

  function ptAt(series, i) {
    if (i < 0 || !series || series.lat == null || series.lat[i] == null) return null;
    return { lat: series.lat[i], lon: series.lon[i], i: i };
  }

  function headingAt(series, pos) {
    if (!pos) return 0;
    var i = pos.i != null ? pos.i : 0;
    var k = hitBack(series, i - 1);
    if (k < 0 || !series) return 0;
    var dLat = pos.lat - series.lat[k];
    var dLon = pos.lon - series.lon[k];
    if (!dLat && !dLon) {
      k = hitBack(series, k - 1);
      if (k < 0) return 0;
      dLat = pos.lat - series.lat[k];
      dLon = pos.lon - series.lon[k];
    }
    if (!dLat && !dLon) return 0;
    var hdg = (Math.atan2(dLon * Math.cos((pos.lat * Math.PI) / 180), dLat) * 180) / Math.PI;
    return hdg < 0 ? hdg + 360 : hdg;
  }

  /* On-screen COG from the last few GPS seconds (same idea as tracking-dev2 headingAt). */
  function screenNoseRad(series, pos, cam, ts) {
    var hits = tailHits(series, ts);
    var a;
    var b;
    if (hits && hits.length >= 2) {
      var from = hits[Math.max(0, hits.length - 6)];
      a = xy(from.lat, from.lon, cam);
      b = xy(hits[hits.length - 1].lat, hits[hits.length - 1].lon, cam);
    } else if (pos && series) {
      var k = hitBack(series, (pos.i != null ? pos.i : 0) - 5);
      var prev = ptAt(series, k);
      if (!prev) return -90;
      a = xy(prev.lat, prev.lon, cam);
      b = xy(pos.lat, pos.lon, cam);
    } else {
      return -90;
    }
    var dx = b.x - a.x;
    var dy = b.y - a.y;
    if (dx * dx + dy * dy < 4) return -90;
    return (Math.atan2(dx, -dy) * 180) / Math.PI;
  }

  function distM(a, b) {
    if (!a || !b) return 1e9;
    var dlat = (a.lat - b.lat) * 110540;
    var dlon = (a.lon - b.lon) * 111320 * Math.cos((a.lat * Math.PI) / 180);
    return Math.sqrt(dlat * dlat + dlon * dlon);
  }

  function destPoint(from, brg, meters) {
    var R = 6371000;
    var d = meters / R;
    var br = (brg * Math.PI) / 180;
    var lat1 = (from.lat * Math.PI) / 180;
    var lon1 = (from.lon * Math.PI) / 180;
    var lat2 = Math.asin(Math.sin(lat1) * Math.cos(d) + Math.cos(lat1) * Math.sin(d) * Math.cos(br));
    var lon2 =
      lon1 +
      Math.atan2(
        Math.sin(br) * Math.sin(d) * Math.cos(lat1),
        Math.cos(d) - Math.sin(lat1) * Math.sin(lat2)
      );
    return { lat: (lat2 * 180) / Math.PI, lon: (lon2 * 180) / Math.PI };
  }

  function bearingDeg(a, b) {
    var y = Math.sin(((b.lon - a.lon) * Math.PI) / 180) * Math.cos((b.lat * Math.PI) / 180);
    var x =
      Math.cos((a.lat * Math.PI) / 180) * Math.sin((b.lat * Math.PI) / 180) -
      Math.sin((a.lat * Math.PI) / 180) *
        Math.cos((b.lat * Math.PI) / 180) *
        Math.cos(((b.lon - a.lon) * Math.PI) / 180);
    var br = (Math.atan2(y, x) * 180) / Math.PI;
    return br < 0 ? br + 360 : br;
  }

  function clubCode(sail) {
    var id = replay && replay.boats && replay.boats[sail];
    if (!id) return sail;
    return id.mapClub || id.club || sail;
  }

  function clubLabel(sail) {
    var c = clubCode(sail);
    if (c === 'IZIVUNGUVUNGU' || c === 'IZI') return 'IZI';
    if (c === 'RCYC Academy' || c === 'RCYCA') return 'RCYCA';
    return c;
  }

  function hexRgb(hex) {
    var n = parseInt(String(hex).replace('#', ''), 16);
    if (!(n >= 0)) return [148, 163, 184];
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  }

  function hexLuma(hex) {
    var c = hexRgb(hex);
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2];
  }

  function rgbaHex(hex, a) {
    var c = hexRgb(hex);
    return 'rgba(' + c[0] + ',' + c[1] + ',' + c[2] + ',' + a + ')';
  }

  function boatColor(sail) {
    return COLORS[sail] || COLORS[clubCode(sail)] || '#94a3b8';
  }

  function boatPaint(sail) {
    var fill = boatColor(sail);
    var dark = hexLuma(fill) < 165;
    return {
      fill: fill,
      stroke: 'rgba(15,23,42,0.75)',
      ink: dark ? '#ffffff' : '#0f172a',
      nose: dark ? '#ffffff' : '#0f172a'
    };
  }

  function passTs(pass, sail) {
    var boats = (pass && pass.boats) || [];
    var i;
    for (i = 0; i < boats.length; i++) {
      if (boats[i] && boats[i].boat === sail) {
        return boats[i].ts_ms != null ? Number(boats[i].ts_ms) : Number(boats[i].ts);
      }
    }
    return null;
  }

  function passList() {
    var raw = (replay && replay.passes) || [];
    var out = [];
    var i;
    for (i = 0; i < raw.length; i++) {
      if (!raw[i] || raw[i].id === 'ST' || raw[i].label === 'ST') continue;
      out.push(raw[i]);
    }
    var hasFin = false;
    for (i = 0; i < out.length; i++) {
      if (out[i] && (out[i].id === 'FIN' || out[i].label === 'Fin')) hasFin = true;
    }
    if (!hasFin && replay && replay.finish && replay.finish.length) {
      out.push({
        id: 'FIN',
        label: 'Fin',
        boats: replay.finish.map(function (b) {
          return { boat: b.boat, ts_ms: b.ts_ms != null ? b.ts_ms : b.ts };
        })
      });
    }
    return out;
  }

  function startRankMap() {
    var st = null;
    var raw = (replay && replay.passes) || [];
    var i;
    for (i = 0; i < raw.length; i++) {
      if (raw[i] && (raw[i].id === 'ST' || raw[i].label === 'ST')) {
        st = raw[i];
        break;
      }
    }
    var map = {};
    if (!st || !st.boats) return map;
    for (i = 0; i < st.boats.length; i++) {
      if (st.boats[i] && st.boats[i].boat) map[st.boats[i].boat] = i + 1;
    }
    return map;
  }

  function markKeyForPass(pass) {
    if (!pass) return '1';
    if (pass.id === 'FIN' || pass.label === 'Fin') return '3';
    if (pass.label === 'Pin' || Number(pass.mark) === 4) return '4';
    return String(pass.mark || '1');
  }

  function markPosForPass(pass, ts) {
    if (!pass) return null;
    /* Pin is the start-line pin. Do not sample drifting GPS mark 4 (it jumps ~74m). */
    if (pass.label === 'Pin' || Number(pass.mark) === 4) {
      if (trail.start_line && trail.start_line.left) {
        return {
          lat: trail.start_line.left.lat,
          lon: trail.start_line.left.lon,
          key: 'pin',
          pass: pass
        };
      }
    }
    var key = markKeyForPass(pass);
    var pos = sampleAt((trail.marks || {})[key], ts);
    if (pos) return { lat: pos.lat, lon: pos.lon, key: key, pass: pass };
    if ((pass.id === 'FIN' || pass.label === 'Fin') && trail.finish_line && trail.finish_line.left) {
      var fl = trail.finish_line;
      return {
        lat: (fl.left.lat + fl.right.lat) / 2,
        lon: (fl.left.lon + fl.right.lon) / 2,
        key: 'fin',
        pass: pass
      };
    }
    return null;
  }

  function priorNett(sail) {
    var pts = scores && scores.boats && scores.boats[sail] && scores.boats[sail].points;
    if (!pts) return 0;
    var n = 0;
    var r;
    for (r = 1; r <= 6; r++) n += Number(pts[String(r)] || 0);
    return n;
  }

  function ranksAt(ts) {
    var passes = passList();
    var sails = Object.keys((trail && trail.boats) || {});
    var start = startRankMap();
    var gun = Number((replay && replay.gun_ts_ms) || (trail && trail.gun_ts_ms) || 0);
    var rows = [];
    var i;
    var p;
    for (i = 0; i < sails.length; i++) {
      var sail = sails[i];
      var done = 0;
      var lastT = 0;
      for (p = 0; p < passes.length; p++) {
        var t = passTs(passes[p], sail);
        if (t != null && t <= ts) {
          done += 1;
          lastT = t;
        } else break;
      }
      var next = passes[done] || null;
      var nextPos = markPosForPass(next, ts);
      var pos = sampleAt(trail.boats[sail], ts);
      var toNext = nextPos && pos ? distM(pos, nextPos) : 1e8;
      rows.push({
        sail: sail,
        done: done,
        lastT: lastT,
        toNext: toNext,
        pos: pos,
        hdg: headingAt(trail.boats[sail], pos),
        start: start[sail] || null
      });
    }
    rows.sort(function (a, b) {
      if (b.done !== a.done) return b.done - a.done;
      if (a.done) return a.lastT - b.lastT;
      return a.toNext - b.toNext;
    });
    var bySail = {};
    var overall = [];
    for (i = 0; i < rows.length; i++) {
      rows[i].racePlace = i + 1;
      bySail[rows[i].sail] = rows[i];
      var livePts = rows[i].racePlace;
      overall.push({ sail: rows[i].sail, nett: priorNett(rows[i].sail) + livePts, racePlace: livePts });
    }
    overall.sort(function (a, b) {
      if (a.nett !== b.nett) return a.nett - b.nett;
      return a.racePlace - b.racePlace;
    });
    var overallBySail = {};
    for (i = 0; i < overall.length; i++) overallBySail[overall[i].sail] = i + 1;
    var front = rows[0] || null;
    var leaderSail = overall[0] && overall[0].sail;
    return {
      rows: rows,
      bySail: bySail,
      overallBySail: overallBySail,
      front: front,
      leader: leaderSail ? bySail[leaderSail] : front,
      gun: gun,
      ts: ts,
      nextMark: front ? markPosForPass(passList()[front.done], ts) : null,
      target: (function () {
        var mk = sampleAt((trail.marks || {})['1'], ts);
        return mk;
      })()
    };
  }

  function medianHdg(rows) {
    var hs = [];
    var i;
    for (i = 0; i < rows.length; i++) {
      if (rows[i] && rows[i].pos && rows[i].hdg) hs.push(rows[i].hdg);
    }
    if (!hs.length) return 90;
    hs.sort(function (a, b) {
      return a - b;
    });
    return hs[Math.floor(hs.length / 2)];
  }

  function angDiff(a, b) {
    var d = Math.abs((a || 0) - (b || 0)) % 360;
    return d > 180 ? 360 - d : d;
  }

  /* Race 7 test clip: travel maps to -X so boats run right → left across the strip. */
  function project(lat, lon, cam) {
    var north = (lat - cam.midLat) * 111000;
    var east = (lon - cam.midLon) * 111000 * cam.cos;
    var along = north * cam.cosH + east * cam.sinH;
    var across = east * cam.cosH - north * cam.sinH;
    var x = cam.flipX === false ? cam.cx + along * cam.scaleX : cam.cx - along * cam.scaleX;
    return {
      x: x,
      y: cam.cy - across * cam.scaleY
    };
  }

  function xy(lat, lon, cam) {
    return project(lat, lon, cam);
  }

  function copyCam(cam) {
    return {
      midLat: cam.midLat,
      midLon: cam.midLon,
      cos: cam.cos,
      cosH: cam.cosH,
      sinH: cam.sinH,
      scale: cam.scale,
      scaleX: cam.scaleX,
      scaleY: cam.scaleY,
      w: cam.w,
      h: cam.h,
      hdg: cam.hdg,
      cx: cam.cx,
      cy: cam.cy,
      flipX: cam.flipX,
      lockMark: cam.lockMark
    };
  }

  /* tracking-dev2: ease pan/zoom; zoom out faster than zoom in. Snap on seek. */
  function easeCam(target, ts) {
    if (
      !heldCam ||
      !heldCamTs ||
      Math.abs(ts - heldCamTs) > 1800 ||
      heldCam.w !== target.w ||
      !isFinite(heldCam.scaleX) ||
      heldCam.scaleX < target.scaleX * 0.35 ||
      heldCam.scaleX > target.scaleX * 3
    ) {
      heldCam = copyCam(target);
      heldCamTs = ts;
      return heldCam;
    }
    var aPan = 0.14;
    var aZoom = 0.09;
    if (target.scaleX < heldCam.scaleX || target.scaleY < heldCam.scaleY) aZoom = 0.26;
    heldCam.midLat += (target.midLat - heldCam.midLat) * aPan;
    heldCam.midLon += (target.midLon - heldCam.midLon) * aPan;
    heldCam.scaleX += (target.scaleX - heldCam.scaleX) * aZoom;
    heldCam.scaleY += (target.scaleY - heldCam.scaleY) * aZoom;
    var uni = Math.min(heldCam.scaleX, heldCam.scaleY);
    heldCam.scaleX = uni;
    heldCam.scaleY = uni;
    heldCam.cx += (target.cx - heldCam.cx) * aPan;
    heldCam.cy += (target.cy - heldCam.cy) * aPan;
    heldCam.cos = Math.cos((heldCam.midLat * Math.PI) / 180);
    heldCam.cosH = target.cosH;
    heldCam.sinH = target.sinH;
    heldCam.hdg = target.hdg;
    heldCam.flipX = target.flipX;
    if (target.lockMark) {
      heldCam.midLat = target.midLat;
      heldCam.midLon = target.midLon;
      heldCam.cy = target.cy;
      heldCam.lockMark = true;
    }
    heldCam.scale = heldCam.scaleX;
    heldCam.w = target.w;
    heldCam.h = target.h;
    heldCamTs = ts;
    return heldCam;
  }

  function fitCam(pts, w, h, hdg, opts) {
    opts = opts || {};
    var i;
    var midLat = 0;
    var midLon = 0;
    for (i = 0; i < pts.length; i++) {
      midLat += pts[i].lat;
      midLon += pts[i].lon;
    }
    midLat /= pts.length;
    midLon /= pts.length;
    var cos = Math.cos((midLat * Math.PI) / 180);
    var rad = ((hdg || 0) * Math.PI) / 180;
    var cosH = Math.cos(rad);
    var sinH = Math.sin(rad);
    var minA = Infinity;
    var maxA = -Infinity;
    var minC = Infinity;
    var maxC = -Infinity;
    for (i = 0; i < pts.length; i++) {
      var north = (pts[i].lat - midLat) * 111000;
      var east = (pts[i].lon - midLon) * 111000 * cos;
      var along = north * cosH + east * sinH;
      var across = east * cosH - north * sinH;
      if (along < minA) minA = along;
      if (along > maxA) maxA = along;
      if (across < minC) minC = across;
      if (across > maxC) maxC = across;
    }
    var minAlong = opts.minAlong != null ? opts.minAlong : 80;
    var minAcross = opts.minAcross != null ? opts.minAcross : 36;
    var spanAlong = Math.max(minAlong, maxA - minA) * (opts.padAlong || 1.22);
    var spanAcross = Math.max(minAcross, maxC - minC) * (opts.padAcross || 1.4);
    var padX = opts.padX != null ? opts.padX : 72;
    var padY = opts.padY != null ? opts.padY : 22;
    var scaleX = (w - padX * 2) / spanAlong;
    var scaleY = (h - padY * 2) / spanAcross;
    var scaleFit = Math.min(scaleX, scaleY);
    if (!(scaleFit > 0.08)) scaleFit = 0.08;
    scaleX = scaleFit;
    scaleY = scaleFit;
    var midAlong = (minA + maxA) / 2;
    var midAcross = (minC + maxC) / 2;
    var flipX = opts.flipX !== false;
    return {
      midLat: midLat,
      midLon: midLon,
      cos: cos,
      cosH: cosH,
      sinH: sinH,
      scale: scaleFit,
      scaleX: scaleX,
      scaleY: scaleY,
      w: w,
      h: h,
      hdg: hdg || 0,
      flipX: flipX,
      cx: flipX ? w / 2 + midAlong * scaleX : w / 2 - midAlong * scaleX,
      cy: h / 2 + midAcross * scaleY
    };
  }

  function alongAcross(pos, origin, hdg) {
    var cos = Math.cos((origin.lat * Math.PI) / 180);
    var north = (pos.lat - origin.lat) * 111000;
    var east = (pos.lon - origin.lon) * 111000 * cos;
    var rad = ((hdg || 0) * Math.PI) / 180;
    return {
      along: north * Math.cos(rad) + east * Math.sin(rad),
      across: east * Math.cos(rad) - north * Math.sin(rad)
    };
  }

  /* 60–70% of the fleet closest to the mark. 1st is always included. */
  function coreFleetAlong(mark, pack, live, hdg) {
    var rows = [];
    var i;
    var front = live && live.front;
    for (i = 0; i < (pack || []).length; i++) {
      if (!pack[i] || !pack[i].pos || !mark) continue;
      var aa = alongAcross(pack[i].pos, mark, hdg);
      rows.push({
        sail: pack[i].sail,
        dist: distM(pack[i].pos, mark),
        along: aa.along,
        across: aa.across
      });
    }
    rows.sort(function (a, b) {
      return a.dist - b.dist;
    });
    var k = Math.max(2, Math.ceil(rows.length * 0.65));
    if (k > rows.length) k = rows.length;
    var lo = Infinity;
    var hi = -Infinity;
    var minC = Infinity;
    var maxC = -Infinity;
    var seen = {};
    function eat(item) {
      if (!item || seen[item.sail]) return;
      seen[item.sail] = true;
      if (item.along < lo) lo = item.along;
      if (item.along > hi) hi = item.along;
      if (item.across < minC) minC = item.across;
      if (item.across > maxC) maxC = item.across;
    }
    for (i = 0; i < k; i++) eat(rows[i]);
    for (i = 0; i < rows.length; i++) {
      if (front && rows[i].sail === front.sail) eat(rows[i]);
    }
    if (lo === Infinity) {
      lo = 0;
      hi = 0;
      minC = 0;
      maxC = 0;
    }
    return { lo: lo, hi: hi, minC: minC, maxC: maxC };
  }

  function boatSpeedMps(sail, ts) {
    var series = trail.boats && trail.boats[sail];
    var now = sampleAt(series, ts);
    var prev = sampleAt(series, ts - 4000);
    if (!now || !prev) return 3;
    var v = distM(now, prev) / 4;
    return v > 0.5 ? v : 0.5;
  }

  function secsToMark(row, mark, ts) {
    if (!row || !row.pos || !mark) return 1e9;
    return distM(row.pos, mark) / boatSpeedMps(row.sail, ts);
  }

  function nRoundedPass(pass, ts) {
    var boats = (pass && pass.boats) || [];
    var n = 0;
    var i;
    for (i = 0; i < boats.length; i++) {
      var t = boats[i] && (boats[i].ts_ms != null ? Number(boats[i].ts_ms) : Number(boats[i].ts));
      if (t != null && t <= ts) n += 1;
    }
    return n;
  }

  function stillIncomingTo(row, mark, live) {
    if (!row || !mark) return false;
    var nxt = markPosForPass(passList()[row.done], live && live.ts);
    return !!(nxt && String(nxt.key) === String(mark.key));
  }

  function roundingMode(mark, live) {
    var front = live && live.front;
    var nR = nRoundedPass(mark && mark.pass, live && live.ts);
    var incoming = stillIncomingTo(front, mark, live);
    var tta = secsToMark(front, mark, live && live.ts);
    var wasTight = tightMarkHold;
    if (incoming && tta <= 10) tightMarkHold = true;
    if (nR >= 5) tightMarkHold = false;
    if (tightMarkHold && !wasTight) heldSceneScale = null;
    if (tightMarkHold) return 'tight';
    if (nR >= 5 || (front && !incoming)) return 'pack';
    return 'approach';
  }

  /* Mark stays upper-left — never against the bottom. 1st always in view.
   * Do not shrink X to fit Y. After rounding, boats stay on the right side instead of sailing down.
   * Zoom in when 1st is 10s from the mark. Hold until 4–5 boats round. Then zoom
   * out in small steps so 1st stays in view with 60–70% of the fleet. 1st sits
   * far right and the last of that pack sits left; the mark can leave left. */
  function pinLeftCam(mark, pack, live, w, h, hdg, mode) {
    var win = coreFleetAlong(mark, pack, live, hdg);
    var front = live && live.front;
    var frontAA = front && front.pos ? alongAcross(front.pos, mark, hdg) : null;
    var pinLeft = Math.max(28, w * 0.1);
    var rightPad = 52;
    var lo;
    var hi;
    if (mode === 'tight') {
      lo = frontAA ? Math.min(frontAA.along, -40) : -40;
      hi = 8;
    } else if (mode === 'pack') {
      lo = win.lo;
      hi = win.hi;
      if (frontAA && frontAA.along < lo) lo = frontAA.along;
    } else {
      lo = win.lo;
      hi = win.hi;
      if (lo > 0) lo = 0;
      if (hi < 0) hi = 0;
    }
    var spanAlong = Math.max(mode === 'tight' ? 52 : 48, (hi - lo) * 1.06);
    var scale = (w - pinLeft - rightPad) / spanAlong;
    if (!(scale > 0.08)) scale = 0.08;
    /* Mark in the upper third, never against the bottom. */
    var cy = Math.max(36, Math.min(h * 0.34, h * 0.4));
    var below = Math.max(36, h - cy - 24);
    var needAcross = Math.max(
      20,
      Math.abs(win.minC),
      Math.abs(win.maxC),
      frontAA ? Math.abs(frontAA.across) : 0
    );
    var scaleYfit = below / needAcross;
    if (scaleYfit > 0 && scale > scaleYfit) scale = scaleYfit;
    if (frontAA) {
      var alongNeed = Math.abs(frontAA.along);
      if (alongNeed > 8) {
        var scaleX1 = (w - pinLeft - rightPad) / alongNeed;
        if (scale > scaleX1) scale = scaleX1;
      }
    }
    if (heldSceneScale != null && mode !== 'approach' && scale > heldSceneScale) scale = heldSceneScale;
    heldSceneScale = scale;
    var rad = ((hdg || 0) * Math.PI) / 180;
    var cx = pinLeft;
    if (mode === 'pack' && frontAA) {
      cx = w - rightPad + frontAA.along * scale;
    }
    if (frontAA) {
      var x1 = cx - frontAA.along * scale;
      if (x1 > w - rightPad) cx -= x1 - (w - rightPad);
      if (mode !== 'pack' && x1 < pinLeft) cx += pinLeft - x1;
    }
    return {
      midLat: mark.lat,
      midLon: mark.lon,
      cos: Math.cos((mark.lat * Math.PI) / 180),
      cosH: Math.cos(rad),
      sinH: Math.sin(rad),
      scale: scale,
      scaleX: scale,
      scaleY: scale,
      w: w,
      h: h,
      hdg: hdg || 0,
      flipX: true,
      cx: cx,
      cy: cy,
      lockMark: true
    };
  }

  function startLineMid() {
    var sl = trail && trail.start_line;
    if (!sl || !sl.left || !sl.right) return null;
    return {
      lat: (sl.left.lat + sl.right.lat) / 2,
      lon: (sl.left.lon + sl.right.lon) / 2,
      key: 'start',
      pin: sl.left,
      rc: sl.right
    };
  }

  function signedDistToStart(pos) {
    var line = startLineMid();
    if (!line || !pos) return 0;
    var weather = sampleAt((trail.marks || {})['1'], (replay && replay.gun_ts_ms) || 0);
    var hdg = weather ? bearingDeg(line, weather) : 136;
    return alongAcross(pos, line, hdg).along;
  }

  function coreClosestToFirst(live, frac) {
    var front = live && live.front;
    var rows = [];
    var i;
    for (i = 0; i < (live.rows || []).length; i++) {
      if (!live.rows[i] || !live.rows[i].pos) continue;
      rows.push({
        row: live.rows[i],
        dist: front && front.pos ? distM(live.rows[i].pos, front.pos) : live.rows[i].racePlace || 99
      });
    }
    rows.sort(function (a, b) {
      return a.dist - b.dist;
    });
    var k = Math.max(2, Math.ceil(rows.length * (frac || 0.65)));
    if (k > rows.length) k = rows.length;
    var out = [];
    var seen = {};
    for (i = 0; i < k; i++) {
      out.push(rows[i].row);
      seen[rows[i].row.sail] = true;
    }
    if (front && front.pos && !seen[front.sail]) out.unshift(front);
    return out;
  }

  /* Race 7 Start: start line is VERTICAL. Course heading is perpendicular
   * to Pin–RC toward weather so boats sail horizontally LTR.
   * Line sits on the LEFT. Only enough width left of the line for boats
   * lining up. They cross and sail away to the RIGHT. */
  function startCourseHdg(live) {
    var line = startLineMid();
    if (!line) return 136;
    var weather = sampleAt((trail.marks || {})['1'], (live && live.ts) || 0);
    if (!weather || weather.lat == null) {
      weather = sampleAt((trail.marks || {})['1'], (replay && replay.gun_ts_ms) || 0);
    }
    if (weather && weather.lat != null) return bearingDeg(line, weather);
    if (line.pin && line.rc) {
      var alongLine = bearingDeg(line.pin, line.rc);
      return (alongLine + 90) % 360;
    }
    return 136;
  }

  function headingTowardMark(row, course) {
    if (!row || row.hdg == null) return false;
    return angDiff(row.hdg, course) < 55;
  }

  /* Keep boats that duck below the line until they tack back toward M1. */
  function startCamPack(live, hdg, origin) {
    var pack = coreClosestToFirst(live, 0.65);
    var seen = {};
    var i;
    for (i = 0; i < pack.length; i++) seen[pack[i].sail] = true;
    var sl = trail && trail.start_line;
    var pinA = sl && sl.left ? alongAcross(sl.left, origin, hdg).across : 0;
    var rcA = sl && sl.right ? alongAcross(sl.right, origin, hdg).across : 0;
    var lineLo = Math.min(pinA, rcA);
    for (i = 0; i < (live.rows || []).length; i++) {
      var row = live.rows[i];
      if (!row || !row.pos || seen[row.sail]) continue;
      var aa = alongAcross(row.pos, origin, hdg);
      if (aa.across < lineLo + 12 && !headingTowardMark(row, hdg)) {
        pack.push(row);
        seen[row.sail] = true;
      }
    }
    return pack;
  }

  function clipEndTs() {
    var rule = clipRule;
    if (!rule || !rule.stamp || !rule.durationSec) return 0;
    var stamp = Date.parse(rule.stamp);
    if (stamp !== stamp) return 0;
    return stamp + (rule.offsetMs || 0) + rule.durationSec * 1000;
  }

  /* How far 1st is at clip end — sizes X so they finish far right. */
  function startAheadM(live, origin, hdg) {
    var ahead = 80;
    var endTs = clipEndTs();
    if (endTs) {
      var endLive = ranksAt(endTs);
      if (endLive && endLive.front && endLive.front.pos) {
        ahead = Math.max(ahead, alongAcross(endLive.front.pos, origin, hdg).along);
      }
    }
    if (live && live.front && live.front.pos) {
      ahead = Math.max(ahead, alongAcross(live.front.pos, origin, hdg).along);
    }
    return ahead;
  }

  /* Start line stays LEFT and does not move. It can only shrink (zoom out).
   * Boats sail to the right. Line stays behind them. 1st is far right at end. */
  function startPackCam(live, w, h) {
    var line = startLineMid();
    var pin = line && line.pin;
    var rc = line && line.rc;
    var front = live && live.front;
    var hdg = startCourseHdg(live);
    var origin = line || (front && front.pos) || { lat: 0, lon: 0 };
    var lineX = Math.min(72, Math.max(22, w * 0.2));
    var lineY = h * 0.5;
    var ahead = startAheadM(live, origin, hdg);
    if (startLock && startLock.w === w && startLock.h === h && startLock.ahead > 0) {
      ahead = Math.max(ahead, startLock.ahead);
    }
    var scaleX = (w - lineX - 26) / Math.max(40, ahead);
    if (!(scaleX > 0.05)) scaleX = 0.05;
    var pinA = pin ? alongAcross(pin, origin, hdg).across : 40;
    var rcA = rc ? alongAcross(rc, origin, hdg).across : -40;
    var lineMin = Math.min(pinA, rcA);
    var lineMax = Math.max(pinA, rcA);
    var lineSpan = Math.max(40, lineMax - lineMin);
    var padT = 24;
    var padB = 30;
    var fullScaleY = (h - padT - padB) / lineSpan;
    var gun = live && live.gun;
    var signed = front && front.pos ? signedDistToStart(front.pos) : 0;
    var afterStart = (gun && live.ts >= gun) || signed > 8;
    var packMin = lineMin;
    var packMax = lineMax;
    var rows = (live && live.rows) || [];
    var i;
    for (i = 0; i < rows.length; i++) {
      if (!rows[i] || !rows[i].pos) continue;
      var ac = alongAcross(rows[i].pos, origin, hdg).across;
      if (ac < packMin) packMin = ac;
      if (ac > packMax) packMax = ac;
    }
    /* After the gun, shrink the line in place so ducks above and below
     * stay in view. Do not pan — scaleY is limited by room above/below
     * the locked line, not by fleet span alone. */
    var extraM = afterStart ? 16 : 0;
    var topA = Math.max(packMax, lineMax) + extraM;
    var botA = Math.min(packMin, lineMin) - extraM;
    var scaleY = fullScaleY;
    if (afterStart) {
      if (topA > 1) scaleY = Math.min(scaleY, (lineY - padT) / topA);
      if (botA < -1) scaleY = Math.min(scaleY, (h - padB - lineY) / -botA);
    }
    if (!(scaleY > 0.05)) scaleY = 0.05;
    if (fullScaleY > 0 && scaleY > fullScaleY) scaleY = fullScaleY;
    if (startLock && startLock.w === w && startLock.h === h && startLock.scaleY > 0) {
      if (scaleY > startLock.scaleY) scaleY = startLock.scaleY;
    }
    startLock = { w: w, h: h, ahead: ahead, scaleY: scaleY };
    return {
      midLat: origin.lat,
      midLon: origin.lon,
      cos: Math.cos((origin.lat * Math.PI) / 180),
      cosH: Math.cos((hdg * Math.PI) / 180),
      sinH: Math.sin((hdg * Math.PI) / 180),
      scale: scaleX,
      scaleX: scaleX,
      scaleY: scaleY,
      w: w,
      h: h,
      hdg: hdg,
      flipX: false,
      cx: lineX,
      cy: lineY,
      lockMark: true
    };
  }

  /* Fixed geographic window so the mark stays put and boats sail through it. */
  function frozenMarkScale(w, h) {
    var minAlong = 340;
    var minAcross = 260;
    return {
      scaleX: Math.max(0.05, (Math.max(64, w) - 112) / minAlong),
      scaleY: Math.max(0.05, (Math.max(48, h) - 36) / minAcross)
    };
  }

  function camFromMark(mark, w, h, hdg, flipX, markX, markY, scaleX, scaleY, panX) {
    var rad = ((hdg || 0) * Math.PI) / 180;
    var mx = markX != null ? markX : 0.2;
    var my = markY != null ? markY : 0.38;
    return {
      midLat: mark.lat,
      midLon: mark.lon,
      cos: Math.cos((mark.lat * Math.PI) / 180),
      cosH: Math.cos(rad),
      sinH: Math.sin(rad),
      scale: scaleX,
      scaleX: scaleX,
      scaleY: scaleY,
      w: w,
      h: h,
      hdg: hdg || 0,
      flipX: true,
      cx: w * mx + (panX || 0),
      cy: h * my
    };
  }

  function leaderOffRight(cam, leader, w) {
    if (!cam || !leader || !leader.pos) return false;
    var p = xy(leader.pos.lat, leader.pos.lon, cam);
    return p.x > w - 40;
  }

  function drawDelta(ctx, x, y, delta, align) {
    if (delta == null) return;
    var txt = delta > 0 ? '▲' + delta : delta < 0 ? '▼' + -delta : '■0';
    ctx.font = 'bold 8px sans-serif';
    ctx.textAlign = align || 'left';
    ctx.textBaseline = 'middle';
    ctx.fillStyle = delta > 0 ? '#4ade80' : delta < 0 ? '#f87171' : '#cbd5e1';
    ctx.fillText(txt, x, y);
  }

  function drawGate(ctx, cam, line, color, label, pinLabel, rcLabel) {
    if (!line || !line.left || !line.right) return;
    var a = xy(line.left.lat, line.left.lon, cam);
    var b = xy(line.right.lat, line.right.lon, cam);
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.setLineDash([6, 4]);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.beginPath();
    ctx.arc(a.x, a.y, 4.2, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.fill();
    ctx.fillStyle = '#e2e8f0';
    ctx.fillRect(b.x - 7, b.y - 5, 14, 10);
    ctx.strokeStyle = color;
    ctx.strokeRect(b.x - 7, b.y - 5, 14, 10);
    ctx.fillStyle = '#0b1b33';
    ctx.font = 'bold 8px sans-serif';
    ctx.textAlign = 'left';
    ctx.fillText(rcLabel || 'RC', b.x - 6, b.y + 3);
    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 9px sans-serif';
    ctx.fillText(pinLabel || 'Pin', a.x + 5, a.y - 5);
    if (label) ctx.fillText(label, (a.x + b.x) / 2 + 5, (a.y + b.y) / 2 - 5);
  }

  function markOnCanvas(p, w, h) {
    return p && p.x > -48 && p.x < w + 48 && p.y > -48 && p.y < h + 48;
  }

  function drawRoundArrow(ctx, cam, mark, fromPt, color) {
    if (!mark || !fromPt) return;
    var p = xy(mark.lat, mark.lon, cam);
    var f = xy(fromPt.lat, fromPt.lon, cam);
    var a0 = Math.atan2(f.y - p.y, f.x - p.x);
    var sweep = 1.85;
    var r = 16;
    var a1 = a0 - sweep;
    ctx.save();
    ctx.strokeStyle = color;
    ctx.fillStyle = color;
    ctx.lineWidth = 2.2;
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.arc(p.x, p.y, r, a0, a1, true);
    ctx.stroke();
    var ax = p.x + r * Math.cos(a1);
    var ay = p.y + r * Math.sin(a1);
    var tx = Math.sin(a1);
    var ty = -Math.cos(a1);
    ctx.beginPath();
    ctx.moveTo(ax + tx * 5, ay + ty * 5);
    ctx.lineTo(ax - tx * 4 - ty * 4.2, ay - ty * 4 + tx * 4.2);
    ctx.lineTo(ax - tx * 4 + ty * 4.2, ay - ty * 4 - tx * 4.2);
    ctx.closePath();
    ctx.fill();
    ctx.restore();
  }

  function drawCourseMarks(ctx, cam, ts, w, h, focus) {
    var m1 = sampleAt((trail.marks || {})['1'], ts);
    if (m1) {
      var mp = xy(m1.lat, m1.lon, cam);
      if (markOnCanvas(mp, w, h)) {
        ctx.beginPath();
        ctx.arc(mp.x, mp.y, 11, 0, Math.PI * 2);
        ctx.strokeStyle = 'rgba(251,191,36,0.85)';
        ctx.lineWidth = 2.2;
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(mp.x, mp.y, 4.2, 0, Math.PI * 2);
        ctx.fillStyle = '#fbbf24';
        ctx.fill();
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 11px sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('M1', mp.x, mp.y - 16);
      }
    }
    if (trail.start_line && trail.start_line.left && trail.start_line.right) {
      drawGate(ctx, cam, trail.start_line, 'rgba(56,189,248,0.95)', '', 'Pin', 'RC');
    }
    if (trail.finish_line && trail.finish_line.left && trail.finish_line.right) {
      var fl = trail.finish_line;
      var fm = xy((fl.left.lat + fl.right.lat) / 2, (fl.left.lon + fl.right.lon) / 2, cam);
      if (markOnCanvas(fm, w, h)) {
        drawGate(ctx, cam, fl, 'rgba(251,191,36,0.8)', 'Fin', 'Pin', 'RC');
      }
    }
    if (focus && focus.lat != null) {
      var fp = xy(focus.lat, focus.lon, cam);
      ctx.beginPath();
      ctx.arc(fp.x, fp.y, 22, 0, Math.PI * 2);
      ctx.strokeStyle = 'rgba(248,250,252,0.98)';
      ctx.lineWidth = 4;
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(fp.x, fp.y, 7, 0, Math.PI * 2);
      ctx.fillStyle = '#38bdf8';
      ctx.fill();
      var fromPt = m1 || (trail.start_line && trail.start_line.right);
      if (fromPt) drawRoundArrow(ctx, cam, focus, fromPt, '#38bdf8');
      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 14px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.shadowColor = 'rgba(0,0,0,0.85)';
      ctx.shadowBlur = 4;
      var lab = focus.key === 'pin' || focus.key === '4' ? 'Pin' : focus.key === 'fin' ? 'Fin' : focus.key === '1' ? 'M1' : 'Mark';
      ctx.fillText(lab, fp.x, fp.y - 32);
      ctx.shadowBlur = 0;
    }
  }

  function tailHits(series, ts) {
    var now = sampleAt(series, ts);
    if (!now) return [];
    var hits = [now];
    var acc = 0;
    var lastI = now.i != null ? now.i : 0;
    var idx = hitBack(series, lastI - 1);
    var stepMs = Number(trail.step_ms) || 1000;
    var maxM = 90;
    var maxMs = 20000;
    while (idx >= 0) {
      var gap = lastI - idx;
      var cur = ptAt(series, idx);
      if (!cur) break;
      var step = distM(hits[hits.length - 1], cur);
      if (gap > 45) break;
      if (step > 14 * Math.min(gap, 8)) break;
      acc += step;
      hits.push(cur);
      if (acc >= maxM) break;
      if ((now.i - idx) * stepMs >= maxMs) break;
      lastI = idx;
      idx = hitBack(series, idx - 1);
    }
    hits.reverse();
    return hits;
  }

  function drawTail(ctx, cam, sail, ts) {
    var series = trail.boats && trail.boats[sail];
    var hits = tailHits(series, ts);
    if (hits.length < 2) return;
    var fill = boatPaint(sail).fill;
    var boatR = cam.boatR || 7;
    var r = Math.max(1, boatR * 0.22);
    var d;
    for (d = 0; d < hits.length; d++) {
      var pt = xy(hits[d].lat, hits[d].lon, cam);
      var u = d / Math.max(1, hits.length - 1);
      ctx.beginPath();
      ctx.arc(pt.x, pt.y, r, 0, Math.PI * 2);
      ctx.fillStyle = rgbaHex(fill, 0.25 + 0.7 * u * u);
      ctx.fill();
    }
  }

  function isHycRow(row) {
    if (!row) return false;
    var c = clubCode(row.sail);
    return c === 'HYC' || row.sail === 'HYC';
  }

  function frontPack(live) {
    var rows = (live && live.rows) || [];
    var n = rows.length;
    var leadN = Math.max(6, Math.ceil(n * 0.5));
    var out = [];
    var seen = {};
    var i;
    for (i = 0; i < rows.length; i++) {
      if (rows[i] && rows[i].pos && rows[i].racePlace <= leadN) {
        out.push(rows[i]);
        seen[rows[i].sail] = true;
      }
    }
    for (i = 0; i < rows.length; i++) {
      if (rows[i] && rows[i].pos && isHycRow(rows[i]) && !seen[rows[i].sail]) {
        out.push(rows[i]);
        seen[rows[i].sail] = true;
      }
    }
    if (out.length) return out;
    return rows.slice(0, leadN);
  }

  /* Every boat with GPS — the video shows 6th onward rounding too. */
  function viewPack(live, mark) {
    var rows = [];
    var i;
    for (i = 0; i < (live.rows || []).length; i++) {
      if (live.rows[i] && live.rows[i].pos) rows.push(live.rows[i]);
    }
    rows.sort(function (a, b) {
      return (a.racePlace || 99) - (b.racePlace || 99);
    });
    return rows;
  }

  function roundingPack(live, mark) {
    return viewPack(live, mark);
  }

  function acrossM(pos, mark, hdg) {
    if (!pos || !mark) return 0;
    var cos = Math.cos((mark.lat * Math.PI) / 180);
    var north = (pos.lat - mark.lat) * 111000;
    var east = (pos.lon - mark.lon) * 111000 * cos;
    var rad = ((hdg || 0) * Math.PI) / 180;
    return east * Math.cos(rad) - north * Math.sin(rad);
  }

  function setTrackHeight(canvas, frac, maxFrac) {
    var box = canvas && canvas.parentNode;
    if (!box || !box.style) return;
    if (frac < 0.5) frac = 0.5;
    if (maxFrac == null) maxFrac = 0.78;
    if (frac > maxFrac) frac = maxFrac;
    var prev = box._mmTrackH;
    if (prev != null && Math.abs(frac - prev) < 0.015) return;
    box._mmTrackH = frac;
    box.style.setProperty('--mm-track-h', Math.round(frac * 1000) / 10 + '%');
  }

  /* Start strip stays tall. Do not resize it — that moves the line.
   * The line can only shrink (scaleY) inside this strip. */
  function startTrackFrac(live) {
    return 0.88;
  }

  /* Keep all leading boats on canvas; extra room at the bottom for camera-near boats (HYC). */
  function fitLockVertical(lock, pack, w, h) {
    if (!lock || !pack || h < 8) return;
    var mark = { lat: lock.lat, lon: lock.lon };
    var minA = 0;
    var maxA = 0;
    var i;
    for (i = 0; i < pack.length; i++) {
      if (!pack[i] || !pack[i].pos) continue;
      var a = acrossM(pack[i].pos, mark, lock.hdg);
      if (a < minA) minA = a;
      if (a > maxA) maxA = a;
    }
    var span = Math.max(140, maxA - minA) * 1.35;
    var padTop = 22;
    var padBot = 44;
    var need = Math.max(0.04, (h - padTop - padBot) / span);
    if (!lock.scaleY || Math.abs(lock.scaleY) > need + 0.001) lock.scaleY = need;
    var sy = lock.scaleY;
    var markY = (h - padBot + minA * sy) / h;
    if (markY > 0.68) markY = 0.68;
    if (markY < 0.2) markY = 0.2;
    if (lock.markY == null || markY < lock.markY) lock.markY = markY;
    var trackFrac = 0.5 + Math.min(0.28, Math.max(0, (span - 120) / 400) * 0.28);
    lock.trackFrac = trackFrac;
  }

  function packPoints(pack, ts) {
    var pts = [];
    var i;
    for (i = 0; i < pack.length; i++) {
      if (pack[i] && pack[i].pos) pts.push(pack[i].pos);
    }
    return pts;
  }

  function metersPx(m, cam) {
    return m * Math.min(cam.scaleX, cam.scaleY);
  }

  function minBoatGapPx(cam, pack) {
    var minG = Infinity;
    var i;
    var j;
    for (i = 0; i < pack.length; i++) {
      if (!pack[i] || !pack[i].pos) continue;
      var a = xy(pack[i].pos.lat, pack[i].pos.lon, cam);
      for (j = i + 1; j < pack.length; j++) {
        if (!pack[j] || !pack[j].pos) continue;
        var b = xy(pack[j].pos.lat, pack[j].pos.lon, cam);
        var g = Math.hypot(a.x - b.x, a.y - b.y);
        if (g < minG) minG = g;
      }
    }
    return minG;
  }

  /* One size for every boat in view. Step down when bunched so labels stay readable; step up together when there is gap. */
  var ICON_STEPS = [5, 7, 9];

  function collectiveBoatR(cam, pack) {
    var gap = minBoatGapPx(cam, pack);
    var i = heldIconStep;
    if (i < 0 || i >= ICON_STEPS.length) i = 1;
    if (gap < Infinity) {
      while (i > 0 && gap < ICON_STEPS[i] * 2 + 38) i -= 1;
      while (i < ICON_STEPS.length - 1 && gap > ICON_STEPS[i + 1] * 2 + 54) i += 1;
    }
    heldIconStep = i;
    return ICON_STEPS[i];
  }

  function boatRadius(cam, pack) {
    return collectiveBoatR(cam, pack);
  }

  function drawBoatIcon(ctx, p, hdg, paint, r) {
    ctx.beginPath();
    ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
    ctx.fillStyle = paint.fill;
    ctx.fill();
    ctx.strokeStyle = paint.stroke;
    ctx.lineWidth = Math.max(0.8, r * 0.2);
    ctx.stroke();
    ctx.save();
    ctx.translate(p.x, p.y);
    ctx.rotate(((hdg || 0) * Math.PI) / 180);
    var nose = Math.max(2.2, r * 0.52);
    ctx.beginPath();
    ctx.moveTo(0, -r - nose);
    ctx.lineTo(nose * 0.86, -r + nose * 0.33);
    ctx.lineTo(-nose * 0.86, -r + nose * 0.33);
    ctx.closePath();
    ctx.fillStyle = paint.nose || '#ffffff';
    ctx.fill();
    ctx.restore();
  }

  function drawBoat(ctx, cam, row, live, r) {
    if (!row.pos) return;
    var p = xy(row.pos.lat, row.pos.lon, cam);
    var sail = row.sail;
    var paint = boatPaint(sail);
    var overallPos = live.overallBySail[sail];
    var isLeader = live.leader && live.leader.sail === sail;
    var isFront = live.front && live.front.sail === sail;
    var sameLead = isLeader && isFront;
    var total = row.start != null && row.racePlace != null ? row.start - row.racePlace : null;
    var series = trail.boats && trail.boats[sail];
    var hdg = screenNoseRad(series, row.pos, cam, live.ts);
    var placePx = Math.max(8, Math.min(Math.round(r * 1.15), Math.round(r * 1.45)));
    var labPx = Math.max(10, Math.min(13, Math.round(r * 0.95)));
    if (overallPos && overallPos <= 3) {
      ctx.beginPath();
      ctx.arc(p.x, p.y, r + 2.2, 0, Math.PI * 2);
      ctx.strokeStyle = OVERALL_STICKER[overallPos];
      ctx.lineWidth = 2;
      ctx.stroke();
    }
    if (isFront) {
      ctx.beginPath();
      ctx.arc(p.x, p.y, r + 0.8, 0, Math.PI * 2);
      ctx.strokeStyle = 'rgba(250,204,21,0.95)';
      ctx.lineWidth = 1.6;
      ctx.stroke();
    }
    drawBoatIcon(ctx, p, hdg, paint, r);
    ctx.fillStyle = paint.ink;
    ctx.font = 'bold ' + placePx + 'px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(String(row.racePlace || ''), p.x, p.y + 0.4);
    var club = clubLabel(sail);
    var lx = p.x + r + 4;
    var ly = p.y - 1;
    ctx.font = 'bold ' + labPx + 'px sans-serif';
    ctx.textAlign = 'left';
    ctx.shadowColor = 'rgba(0,0,0,0.9)';
    ctx.shadowBlur = 3;
    ctx.fillStyle = paint.fill;
    ctx.fillText(club, lx, ly);
    ctx.shadowBlur = 0;
    var cw = ctx.measureText(club).width;
    drawDelta(ctx, lx + cw + 3, ly, total, 'left');
    if (isFront) {
      ctx.fillStyle = '#facc15';
      ctx.font = 'bold ' + labPx + 'px sans-serif';
      ctx.fillText('RACE', lx, ly - r - 8);
    }
    if (overallPos === 1) {
      ctx.fillStyle = '#facc15';
      ctx.font = 'bold ' + labPx + 'px sans-serif';
      ctx.fillText('OVERALL', lx, ly - r - (isFront ? 22 : 8));
    }
  }

  function countDoneAtLeast(live, n) {
    var c = 0;
    var i;
    for (i = 0; i < (live.rows || []).length; i++) {
      if (live.rows[i] && live.rows[i].done >= n) c += 1;
    }
    return c;
  }

  function incomingHdg(live, mark, leader) {
    var hs = [];
    var passes = passList();
    var i;
    for (i = 0; i < (live.rows || []).length; i++) {
      var row = live.rows[i];
      if (!row || !row.pos || !mark) continue;
      var nxt = markPosForPass(passes[row.done], live.ts);
      if (!nxt || String(nxt.key) !== String(mark.key)) continue;
      hs.push(bearingDeg(row.pos, mark));
    }
    if (hs.length) {
      hs.sort(function (a, b) {
        return a - b;
      });
      return hs[Math.floor(hs.length / 2)];
    }
    if (leader && leader.pos && mark) return bearingDeg(leader.pos, mark);
    return 90;
  }

  function courseHdgToMark(mark, live) {
    if (!mark) return incomingHdg(live, mark, live && live.front);
    var k = String(mark.key || '');
    var ts = live && live.ts;
    if (k === 'pin' || k === '4') {
      var m1 = sampleAt((trail.marks || {})['1'], ts);
      if (m1) return bearingDeg(m1, mark);
    }
    if (k === '1') {
      var pin = trail.start_line && trail.start_line.left;
      if (pin) return bearingDeg(pin, mark);
    }
    return incomingHdg(live, mark, live && live.front);
  }

  function camPlan(live, cssW, cssH) {
    var rule = clipRule || { kind: 'round', approach: 'rtl', holdN: 6 };
    var kind = rule.kind || 'round';
    var leader = live.front;
    var passes = passList();
    var next = leader ? markPosForPass(passes[leader.done], live.ts) : null;
    var last = leader && leader.done ? markPosForPass(passes[leader.done - 1], live.ts) : null;
    var distNext = next && leader && leader.pos ? distM(leader.pos, next) : 1e9;
    var distLast = last && leader && leader.pos ? distM(leader.pos, last) : 1e9;
    var markX = 0.2;
    var phase = 'leg';
    var focus = next;
    var hdg = lockApproachHdg != null ? lockApproachHdg : incomingHdg(live, next || last, leader);
    var flipX = true;
    var lastKey = last && last.key != null ? String(last.key) : '';
    var lockMatchesLast = !!(markLock && lastKey && String(markLock.key) === lastKey);

    if (kind === 'start' && (!leader || leader.done < 1) && distNext > 280) {
      phase = 'start';
      focus = trail.start_line && trail.start_line.left;
      hdg = startCourseHdg(live);
      flipX = false;
      lockApproachHdg = null;
      markLock = null;
    } else if (last && leader && leader.pos && (lockMatchesLast || distLast + 40 < distNext)) {
      /* Rounded this mark: keep it geographic, boats go LTR, pin 1st on the right. */
      phase = 'hold';
      focus = last;
      if (lockApproachHdg == null) lockApproachHdg = incomingHdg(live, last, leader);
      hdg = lockApproachHdg;
    } else if (next && leader && leader.pos && distNext <= distLast) {
      /* Still heading to this mark: RTL, mark pinned left. Do not lock the previous weather. */
      phase = 'approach-mark';
      focus = next;
      if (lockApproachHdg == null) lockApproachHdg = incomingHdg(live, next, leader);
      hdg = lockApproachHdg;
    } else {
      lockApproachHdg = null;
      markLock = null;
      hdg = medianHdg(frontPack(live));
    }

    if (phase === 'hold' || phase === 'approach-mark') {
      var key = focus && focus.key != null ? String(focus.key) : '';
      if (!markLock || markLock.key !== key) {
        var sc = frozenMarkScale(cssW, cssH);
        markLock = {
          key: key,
          lat: focus.lat,
          lon: focus.lon,
          hdg: hdg,
          flipX: true,
          markX: markX,
          markY: 0.34,
          scaleX: sc.scaleX,
          scaleY: sc.scaleY,
          panX: 0,
          pass: focus.pass || null
        };
      }
      if (markLock && focus && focus.pass) markLock.pass = focus.pass;
    }

    camPhase = phase;
    return {
      phase: phase,
      focus: focus,
      next: next,
      last: last,
      hdg: hdg,
      flipX: flipX,
      markX: phase === 'hold' || phase === 'approach-mark' ? markX : null,
      nRounded: last ? countDoneAtLeast(live, leader && leader.done ? leader.done : 1) : 0
    };
  }

  function draw(canvas, ts, cssW, cssH, vidFrac) {
    if (!ready || !trail || !canvas || cssW < 8 || cssH < 8) return;
    var ctx = canvas.getContext('2d');
    if (!ctx) return;
    if (heldCamTs && Math.abs(ts - heldCamTs) > 1800) {
      lockApproachHdg = null;
      markLock = null;
      camPhase = '';
      heldIconStep = 1;
      tightMarkHold = false;
      heldSceneScale = null;
    }
    var live = ranksAt(ts);
    var plan = camPlan(live, cssW, cssH);
    var focus = plan.focus;
    var pack = roundingPack(live, focus || plan.last || markLock);
    var pts = packPoints(pack, ts);
    if (!pts.length && plan.phase !== 'start') return;
    var nearRound = plan.phase === 'hold' || plan.phase === 'approach-mark';
    var cam;
    var camOpts = { minAlong: 40, minAcross: 28, padAlong: 1.18, padAcross: 1.35, padX: 70, padY: 28, flipX: true };
    if (plan.phase === 'start') {
      setTrackHeight(canvas, startTrackFrac(live), 0.88);
      cam = startPackCam(live, cssW, cssH);
      heldCam = copyCam(cam);
      heldCamTs = ts;
    } else if (nearRound && markLock) {
      setTrackHeight(canvas, 0.74);
      var mode = roundingMode(markLock, live);
      cam = pinLeftCam(markLock, pack, live, cssW, cssH, markLock.hdg, mode);
      cam.flipX = true;
      cam = easeCam(cam, ts);
    } else {
      setTrackHeight(canvas, pack.length > 6 ? 0.62 : 0.58);
      if (markLock) pts.push({ lat: markLock.lat, lon: markLock.lon });
      cam = fitCam(pts, cssW, cssH, plan.hdg, camOpts);
      cam.flipX = true;
      cam = easeCam(cam, ts);
    }
    cam.boatR = collectiveBoatR(cam, pack);
    ctx.clearRect(0, 0, cssW, cssH);
    drawCourseMarks(ctx, cam, ts, cssW, cssH, plan.phase === 'start' ? null : markLock || focus);

    var r = cam.boatR || 7;
    var i;
    for (i = 0; i < pack.length; i++) {
      if (pack[i] && pack[i].sail) drawTail(ctx, cam, pack[i].sail, ts);
    }
    for (i = pack.length - 1; i >= 0; i--) drawBoat(ctx, cam, pack[i], live, r);
  }

  root.mmLiptonTrackOverlay = { load: load, draw: draw, usesClip: usesClip, kind: kindFor, offsetMs: offsetMsFor };
})(window);
