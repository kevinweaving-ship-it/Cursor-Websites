"use strict";

var assert = require("assert");
var fs = require("fs");
var path = require("path");

var src = fs.readFileSync(
  path.join(__dirname, "..", "sailingsa", "frontend", "js", "tsc-club-cam.js"),
  "utf8"
);

assert.ok(src.indexOf("skylinewebcams.com") !== -1, "must document Skyline source");
assert.ok(src.indexOf("lowLatencyMode: false") !== -1, "classic 3s HLS must buffer, not LL-chase");
assert.ok(src.indexOf("liveSyncDurationCount: 1") !== -1, "must sit one segment (~3s) off live");
assert.ok(src.indexOf("maxLiveSyncPlaybackRate: 1") !== -1, "must play 1x — no speed-up skip");
assert.ok(src.indexOf("START_BUFFER_S = 2.5") !== -1, "must wait ~2.5s buffered before play");
assert.ok(src.indexOf("maxStarvationDelay: 20") !== -1, "must wait on stall, not skip after 4s");
assert.ok(src.indexOf("nudgeMaxRetry: 0") !== -1, "must not nudge-jump the playhead");
assert.ok(src.indexOf("liveMaxLatencyDurationCount") === -1, "must not snap back to live");
assert.ok(src.indexOf("jumpLive") === -1, "must not seek to live edge");
assert.ok(src.indexOf("tsc-live-cam") !== -1, "must play SSA HLS proxy");

var media = fs.readFileSync(
  path.join(__dirname, "..", "sailingsa", "frontend", "js", "club-live-media.js"),
  "utf8"
);
assert.ok(media.indexOf("wxlive5") !== -1, "club loader must cache-bust tsc-club-cam.js");
assert.ok(media.indexOf("tsc-club-cam.js?v=") !== -1);

console.log("PASS: tsc-club-cam");
