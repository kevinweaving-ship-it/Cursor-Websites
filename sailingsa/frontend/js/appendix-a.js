/* World Sailing RRS Appendix A — every result sheet.
   Low score wins. A tie is last race (then previous). Never result_id. */
(function (w) {
  function parsePlace(raw) {
    var t = String(raw == null ? "" : raw).replace(/[()]/g, " ").trim();
    var m = t.match(/[-+]?\d+(?:\.\d+)?/);
    if (!m) return null;
    var n = parseFloat(m[0]);
    return isFinite(n) ? n : null;
  }

  function racePlacesSailOrder(scores) {
    var d = scores;
    if (typeof d === "string") {
      try { d = JSON.parse(d); } catch (e) { d = {}; }
    }
    if (!d || typeof d !== "object") d = {};
    var keys = Object.keys(d).filter(function (k) { return /^R\d+$/i.test(String(k).trim()); });
    keys.sort(function (a, b) {
      return parseInt(String(a).replace(/\D/g, ""), 10) - parseInt(String(b).replace(/\D/g, ""), 10);
    });
    var counted = [];
    var all = [];
    keys.forEach(function (k) {
      var raw = d[k];
      var p = parsePlace(raw);
      if (p == null) return;
      all.push(p);
      if (!(typeof raw === "string" && raw.indexOf("(") >= 0 && raw.indexOf(")") >= 0)) counted.push(p);
    });
    return { counted: counted, all: all };
  }

  function a8cmpPlaces(aAll, aCounted, bAll, bCounted) {
    var as = aCounted.slice().sort(function (x, y) { return x - y; });
    var bs = bCounted.slice().sort(function (x, y) { return x - y; });
    var n = Math.max(as.length, bs.length);
    var i, va, vb;
    for (i = 0; i < n; i++) {
      va = i < as.length ? as[i] : 9999;
      vb = i < bs.length ? bs[i] : 9999;
      if (va !== vb) return va - vb;
    }
    for (i = Math.max(aAll.length, bAll.length) - 1; i >= 0; i--) {
      va = i < aAll.length ? aAll[i] : 9999;
      vb = i < bAll.length ? bAll[i] : 9999;
      if (va !== vb) return va - vb;
    }
    return 0;
  }

  function cmpResultRows(a, b) {
    var na = Number(a && a.nett_points_raw);
    var nb = Number(b && b.nett_points_raw);
    if (!isFinite(na)) na = 9999;
    if (!isFinite(nb)) nb = 9999;
    if (na !== nb) return na - nb;
    var pa = racePlacesSailOrder(a && a.race_scores);
    var pb = racePlacesSailOrder(b && b.race_scores);
    return a8cmpPlaces(pa.all, pa.counted, pb.all, pb.counted);
  }

  w.ssaAppendixA = {
    parsePlace: parsePlace,
    racePlacesSailOrder: racePlacesSailOrder,
    a8cmpPlaces: a8cmpPlaces,
    cmpResultRows: cmpResultRows
  };
})(window);
