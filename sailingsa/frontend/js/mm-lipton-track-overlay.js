/**
 * MM Event Reels tracking overlay — boats/marks only on the video water.
 * No map tiles. Race 7 test clip races right → left across the bottom strip.
 * Clock is the live reel go-live stamp + video time. Boat noses follow the
 * on-screen GPS track. Icons/colours/tails match tracking-dev2, drawn smaller.
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
  var wait = [];

  function load(done) {
    if (ready) {
      done();
      return;
    }
    wait.push(done);
    if (wait.length > 1) return;
    Promise.all([
      fetch('/js/lipton-dev-trail-r7.json').then(function (r) { return r.json(); }),
      fetch('/js/lipton-dev-replay-r7.json').then(function (r) { return r.json(); }),
      fetch('/js/lipton-dev-series-scores.json').then(function (r) { return r.json(); })
    ])
      .then(function (pack) {
        trail = pack[0];
        replay = pack[1];
        scores = pack[2];
        ready = true;
        var cbs = wait;
        wait = [];
        var i;
        for (i = 0; i < cbs.length; i++) cbs[i]();
      })
      .catch(function () {
        wait = [];
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

  /* Nose follows the on-screen GPS track (after RTL + width stretch), not raw geo heading. */
  function screenNoseRad(series, pos, cam) {
    if (!pos || !series) return (3 * Math.PI) / 2;
    var k = hitBack(series, (pos.i != null ? pos.i : 0) - 1);
    var n = 0;
    while (k >= 0 && n < 16) {
      var prev = ptAt(series, k);
      if (prev && distM(prev, pos) >= 3) {
        var a = xy(prev.lat, prev.lon, cam);
        var b = xy(pos.lat, pos.lon, cam);
        var dx = b.x - a.x;
        var dy = b.y - a.y;
        if (dx * dx + dy * dy > 0.4) return Math.atan2(dy, dx) + Math.PI / 2;
      }
      k = hitBack(series, k - 1);
      n += 1;
    }
    return Math.atan2(0, -1) + Math.PI / 2;
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
      var nextPos = null;
      if (next && trail.marks) {
        nextPos = sampleAt(trail.marks[markKeyForPass(next)], ts);
      }
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
      if (rows[i] && rows[i].pos) hs.push(rows[i].hdg || 0);
    }
    if (!hs.length) return 90;
    hs.sort(function (a, b) {
      return a - b;
    });
    return hs[Math.floor(hs.length / 2)];
  }

  /* Race 7 test clip: travel maps to -X so boats run right → left across the strip. */
  function project(lat, lon, cam) {
    var north = (lat - cam.midLat) * 111000;
    var east = (lon - cam.midLon) * 111000 * cam.cos;
    var along = north * cam.cosH + east * cam.sinH;
    var across = east * cam.cosH - north * cam.sinH;
    return {
      x: cam.cx - along * cam.scaleX,
      y: cam.cy - across * cam.scaleY
    };
  }

  function xy(lat, lon, cam) {
    return project(lat, lon, cam);
  }

  function fitCam(pts, w, h, hdg) {
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
    var spanAlong = Math.max(50, maxA - minA) * 1.12;
    var spanAcross = Math.max(22, maxC - minC) * 1.28;
    var padX = 40;
    var padY = 16;
    var scaleX = (w - padX * 2) / spanAlong;
    var scaleY = (h - padY * 2) / spanAcross;
    var midAlong = (minA + maxA) / 2;
    var midAcross = (minC + maxC) / 2;
    return {
      midLat: midLat,
      midLon: midLon,
      cos: cos,
      cosH: cosH,
      sinH: sinH,
      scale: scaleX,
      scaleX: scaleX,
      scaleY: scaleY,
      w: w,
      h: h,
      hdg: hdg || 0,
      cx: w / 2 + midAlong * scaleX,
      cy: h / 2 + midAcross * scaleY
    };
  }

  function drawDelta(ctx, x, y, delta, align) {
    if (delta == null) return;
    var txt = delta > 0 ? '▲' + delta : delta < 0 ? '▼' + -delta : '■0';
    ctx.font = 'bold 7px sans-serif';
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
    ctx.arc(a.x, a.y, 3.2, 0, Math.PI * 2);
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
    var r = 1.15;
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

  function drawBoatIcon(ctx, p, noseRad, paint, r) {
    ctx.beginPath();
    ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
    ctx.fillStyle = paint.fill;
    ctx.fill();
    ctx.strokeStyle = paint.stroke;
    ctx.lineWidth = 1.1;
    ctx.stroke();
    ctx.save();
    ctx.translate(p.x, p.y);
    ctx.rotate(noseRad);
    ctx.beginPath();
    ctx.moveTo(0, -r - 2.4);
    ctx.lineTo(2.1, -r + 0.8);
    ctx.lineTo(-2.1, -r + 0.8);
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
    var total = row.start != null && row.racePlace != null ? row.start - row.racePlace : null;
    var series = trail.boats && trail.boats[sail];
    var noseRad = screenNoseRad(series, row.pos, cam);
    if (overallPos && overallPos <= 3) {
      ctx.beginPath();
      ctx.arc(p.x, p.y, r + 6, 0, Math.PI * 2);
      ctx.strokeStyle = OVERALL_STICKER[overallPos];
      ctx.lineWidth = 2;
      ctx.stroke();
    }
    if (isLeader) {
      ctx.beginPath();
      ctx.arc(p.x, p.y, r + 4, 0, Math.PI * 2);
      ctx.strokeStyle = 'rgba(250,204,21,0.95)';
      ctx.lineWidth = 1.8;
      ctx.stroke();
    } else if (isFront) {
      ctx.beginPath();
      ctx.arc(p.x, p.y, r + 4, 0, Math.PI * 2);
      ctx.strokeStyle = 'rgba(248,113,113,0.95)';
      ctx.lineWidth = 1.8;
      ctx.stroke();
    }
    drawBoatIcon(ctx, p, noseRad, paint, r);
    ctx.fillStyle = paint.ink;
    ctx.font = 'bold 7px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(String(row.racePlace || ''), p.x, p.y + 0.4);
    var club = clubCode(sail);
    var lx = p.x + r + 4;
    var ly = p.y - 1;
    ctx.font = 'bold 8px sans-serif';
    ctx.textAlign = 'left';
    ctx.shadowColor = 'rgba(0,0,0,0.9)';
    ctx.shadowBlur = 3;
    ctx.fillStyle = paint.fill;
    ctx.fillText(club, lx, ly);
    ctx.shadowBlur = 0;
    var cw = ctx.measureText(club).width;
    drawDelta(ctx, lx + cw + 2, ly, total, 'left');
    if (overallPos) {
      ctx.font = 'bold 7px sans-serif';
      ctx.fillStyle = '#e2e8f0';
      ctx.fillText('O' + overallPos, lx, ly + 8);
    }
  }

  function draw(canvas, ts, cssW, cssH) {
    if (!ready || !trail || !canvas || cssW < 8 || cssH < 8) return;
    var ctx = canvas.getContext('2d');
    if (!ctx) return;
    var live = ranksAt(ts);
    var pts = [];
    var i;
    for (i = 0; i < live.rows.length; i++) {
      if (live.rows[i].pos) pts.push(live.rows[i].pos);
    }
    if (!pts.length) return;
    var near = [];
    function maybe(pt) {
      if (!pt) return;
      var n;
      for (n = 0; n < pts.length; n++) {
        if (distM(pt, pts[n]) < 280) {
          near.push(pt);
          return;
        }
      }
    }
    var mk;
    for (mk in trail.marks || {}) {
      if (Object.prototype.hasOwnProperty.call(trail.marks, mk)) maybe(sampleAt(trail.marks[mk], ts));
    }
    if (trail.start_line) {
      maybe(trail.start_line.left);
      maybe(trail.start_line.right);
    }
    if (trail.finish_line) {
      maybe(trail.finish_line.left);
      maybe(trail.finish_line.right);
    }
    var cam = fitCam(pts.concat(near), cssW, cssH, medianHdg(live.rows));
    ctx.clearRect(0, 0, cssW, cssH);

    var gun = live.gun;
    var startName = ts < gun + 5 * 60 * 1000 ? 'START' : '';
    var finishName = ts >= gun ? 'FINISH' : '';
    drawGate(ctx, cam, trail.start_line, 'rgba(56,189,248,0.9)', startName, 'Pin', 'RC');
    drawGate(ctx, cam, trail.finish_line, 'rgba(251,191,36,0.9)', finishName, 'Pin', 'RC');

    for (mk in trail.marks || {}) {
      if (!Object.prototype.hasOwnProperty.call(trail.marks, mk)) continue;
      var pos = sampleAt(trail.marks[mk], ts);
      if (!pos) continue;
      var p = xy(pos.lat, pos.lon, cam);
      ctx.beginPath();
      ctx.arc(p.x, p.y, 2.4, 0, Math.PI * 2);
      ctx.fillStyle = '#fbbf24';
      ctx.fill();
      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 9px sans-serif';
      ctx.textAlign = 'left';
      ctx.fillText('M' + mk, p.x + 6, p.y + 3);
    }

    if (live.front && live.front.pos && live.target) {
      var courseBrg = bearingDeg(live.front.pos, live.target);
      var leftPt = destPoint(live.front.pos, courseBrg - 90, 220);
      var rightPt = destPoint(live.front.pos, courseBrg + 90, 220);
      var a = xy(leftPt.lat, leftPt.lon, cam);
      var b = xy(rightPt.lat, rightPt.lon, cam);
      ctx.save();
      ctx.setLineDash([2, 4]);
      ctx.strokeStyle = 'rgba(248,113,113,0.9)';
      ctx.lineWidth = 1.8;
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.restore();
    }
    if (live.leader && live.leader.pos && live.target) {
      var lp = xy(live.leader.pos.lat, live.leader.pos.lon, cam);
      var mp = xy(live.target.lat, live.target.lon, cam);
      ctx.save();
      ctx.setLineDash([5, 5]);
      ctx.strokeStyle = 'rgba(250,204,21,0.95)';
      ctx.lineWidth = 1.8;
      ctx.beginPath();
      ctx.moveTo(lp.x, lp.y);
      ctx.lineTo(mp.x, mp.y);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.restore();
    }

    var r = 4.5;
    for (i = 0; i < live.rows.length; i++) {
      if (live.rows[i] && live.rows[i].sail) drawTail(ctx, cam, live.rows[i].sail, ts);
    }
    for (i = live.rows.length - 1; i >= 0; i--) drawBoat(ctx, cam, live.rows[i], live, r);
  }

  root.mmLiptonTrackOverlay = { load: load, draw: draw };
})(window);
