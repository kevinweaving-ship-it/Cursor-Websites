"use strict";

var assert = require("assert");
var fs = require("fs");
var path = require("path");
global.window = global;
var src = path.join(__dirname, "..", "sailingsa", "frontend", "js", "regatta-slot-card.js");
var wx = require(src);

assert.strictEqual(wx.JS_VER, "wxlive2");
assert.strictEqual(wx.LIVE_MS, 15000);

var tww = wx.twwToReading({
  wind_kt: 30.5,
  wind_10min_kt: 25.1,
  gust_kt: 32,
  gust_max_10min_kt: 29.2,
  dir: 288,
  dir_10min: 285,
  fetched_at: 1795849400
});
assert.strictEqual(tww.wind_kt, 25.1);
assert.strictEqual(tww.wind_gust_kt, 29.2);
assert.strictEqual(tww.wind_dir_deg, 285);

var forced = wx.applyLive({ wind_kt: 16.74, avg_kt: 16.74, high_kt: 20 }, tww);
assert.strictEqual(forced.wind_kt, 25.1);
assert.strictEqual(forced.avg_kt, 25.1);
assert.strictEqual(forced.high_kt, 29.2);

var stale = {
  observed_at: "2026-11-28T03:12:47+00:00",
  wind_kt: 16.74,
  wind_avg_kt: 16.74,
  wind_gust_kt: 20.03,
  wind_dir_deg: 319
};
var live = {
  observed_at: "2026-11-28T06:04:24+00:00",
  wind_kt: 25.49,
  wind_avg_kt: 25.49,
  wind_gust_kt: 29.37,
  wind_dir_deg: 307
};

var merged = wx.mergeLiveReading([stale], live);
assert.strictEqual(merged.length, 2);
assert.strictEqual(merged[merged.length - 1].wind_kt, 25.49);

var sameTs = wx.mergeLiveReading([live], {
  observed_at: live.observed_at,
  wind_kt: 26.1,
  wind_avg_kt: 26.1,
  wind_gust_kt: 30,
  wind_dir_deg: 300
});
assert.strictEqual(sameTs.length, 1);
assert.strictEqual(sameTs[0].wind_kt, 26.1);

var older = wx.mergeLiveReading([live], stale);
assert.strictEqual(older.length, 1);
assert.strictEqual(older[0].wind_kt, 25.49);

var data = wx.viewFromReadings(merged);
assert.strictEqual(data.wind_kt, 25.49);

var text = fs.readFileSync(src, "utf8");
assert.ok(text.indexOf("/latest?_=") !== -1, "must poll station /latest");
assert.ok(text.indexOf("theewater-weather/v1/current") !== -1, "TSC must live-fetch Theewater current");
assert.ok(text.indexOf("var LIVE_MS = 15000") !== -1);
assert.ok(text.indexOf("history?hours=12") !== -1, "sparkline still uses history");

var media = fs.readFileSync(path.join(__dirname, "..", "sailingsa", "frontend", "js", "club-live-media.js"), "utf8");
assert.ok(media.indexOf("wxlive3") !== -1, "club loader must cache-bust the live slot card");

console.log("PASS: ssa-wx-live-card");
