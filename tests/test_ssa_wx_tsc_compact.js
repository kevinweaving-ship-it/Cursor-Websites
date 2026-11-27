"use strict";

var assert = require("assert");
var fs = require("fs");
var path = require("path");
var src = path.join(__dirname, "..", "sailingsa", "frontend", "js", "ssa-wx-tsc-compact.js");
var wx = require(src);

assert.strictEqual(wx.JS_VER, "tscv1");
assert.strictEqual(wx.shouldRun({ pathname: "/club/tsc", search: "?wx=v2" }), true);
assert.strictEqual(wx.shouldRun({ pathname: "/club/tsc/", search: "?wx=v2&x=1" }), true);
assert.strictEqual(wx.shouldRun({ pathname: "/club/tsc", search: "" }), false);
assert.strictEqual(wx.shouldRun({ pathname: "/club/zvyc", search: "?wx=v2" }), false);
assert.strictEqual(wx.shouldRun({ pathname: "/regatta/2026-11-28-tsc-cape-classic", search: "?wx=v2" }), false);

assert.strictEqual(wx.bandCol(3), "#12b028");
assert.strictEqual(wx.bandCol(9), "#2563eb");
assert.strictEqual(wx.bandCol(14), "#e67e00");
assert.strictEqual(wx.rateSail(10, 12, false).lvl, 2);
assert.strictEqual(wx.rateSail(2, 2, false).lvl, 1);
assert.strictEqual(wx.rateSail(24, 30, false).lvl, 0);
assert.strictEqual(wx.rateSail(10, 10, true).lvl, 0);
assert.strictEqual(wx.ratePower(8, 10, false).lvl, 2);
assert.strictEqual(wx.ratePower(14, 16, false).lvl, 1);
assert.strictEqual(wx.ratePower(20, 24, false).lvl, 0);

var hybrid = wx.parseHybrid({
  time: [Math.floor(Date.now() / 1000) + 3600],
  models: { hybrid: { wind: [12], gust: [16], dir: [270], day: [1], code: [1] } }
});
assert.strictEqual(hybrid.hours.length, 1);
assert.strictEqual(hybrid.hours[0].w, 12);
assert.ok(hybrid.source.indexOf("Theewater") !== -1);

var om = wx.parseOpenMeteo({
  hourly: {
    time: [new Date().toISOString()],
    wind_speed_10m: [8],
    wind_gusts_10m: [11],
    wind_direction_10m: [180],
    is_day: [1],
    weather_code: [0]
  }
});
assert.strictEqual(om.hours.length, 1);
assert.ok(om.source.indexOf("Open-Meteo") !== -1);

var text = fs.readFileSync(src, "utf8");
["tww-", "Montserrat", "#1f6e9e", "dam-map.webp", "Good sailing breeze", "theewater.co.za/wp-content"].forEach(function (bad) {
  assert.ok(text.indexOf(bad) === -1, "must not copy Theewater UI token: " + bad);
});
assert.ok(text.indexOf("ssa-regatta-slot-card") !== -1, "must keep the existing station card");

console.log("PASS: ssa-wx-tsc-compact");
