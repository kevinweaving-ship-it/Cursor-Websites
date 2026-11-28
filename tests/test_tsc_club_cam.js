"use strict";

var assert = require("assert");
var fs = require("fs");
var path = require("path");

var src = fs.readFileSync(
  path.join(__dirname, "..", "sailingsa", "frontend", "js", "tsc-club-cam.js"),
  "utf8"
);

assert.ok(src.indexOf("skylinewebcams.com") !== -1, "must document Skyline source");
assert.ok(src.indexOf("lowLatencyMode: true") !== -1, "must use low-latency HLS");
assert.ok(src.indexOf("liveSyncDurationCount: 1") !== -1, "must sit one segment off live");
assert.ok(src.indexOf("maxLiveSyncPlaybackRate: 1.5") !== -1, "must catch up when behind");
assert.ok(src.indexOf("tsc-live-cam") !== -1, "must play SSA HLS proxy");
assert.ok(src.indexOf("new Hls({ enableWorker: true, lowLatencyMode: false })") === -1);

var media = fs.readFileSync(
  path.join(__dirname, "..", "sailingsa", "frontend", "js", "club-live-media.js"),
  "utf8"
);
assert.ok(media.indexOf("wxlive3") !== -1, "club loader must cache-bust tsc-club-cam.js");
assert.ok(media.indexOf("tsc-club-cam.js?v=") !== -1);

console.log("PASS: tsc-club-cam");
