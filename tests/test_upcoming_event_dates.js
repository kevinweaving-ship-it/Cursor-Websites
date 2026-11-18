"use strict";

var path = require("path");
var dates = require(path.join(__dirname, "..", "js", "upcoming-event-dates.js"));

function assert(cond, msg) {
  if (!cond) throw new Error(msg || "assertion failed");
}

assert(dates.formatRange("2026-11-28", "2026-11-29") === "28-29 Nov 26", "range");
assert(dates.formatRange("2026-11-28", "2026-11-28") === "28 Nov 26", "same day");
assert(dates.formatRange("2026-12-09", "2026-12-15") === "9-15 Dec 26", "ussa");
assert(dates.formatRange("2026-11-28", "2026-12-02") === "28 Nov-2 Dec 26", "cross month");
assert(dates.formatRange("", "") === "", "empty");

var events = [
  { event_name: "TSC Cape Classic", start_date: "2025-12-06", end_date: "2025-12-07", regatta_id: "2025-12-08-tsc-cape-classic" },
  { event_name: "TSC Cape Classic", start_date: "2026-11-28", end_date: "2026-11-29", regatta_id: null },
  { event_name: "Dassen Island Race", start_date: "2026-11-28", end_date: "2026-11-28", regatta_id: "2026-11-28-sssa-dassen-island-race" },
  { event_name: "2026 USSA Sailing Championships", start_date: "2026-12-09", end_date: "2026-12-15", regatta_id: null },
  { event_name: "2026 SA Sailing Youth National Championship", start_date: "2026-12-16", end_date: "2026-12-21", regatta_id: null },
];

function fakeCard(title, href) {
  return {
    querySelector: function (sel) {
      if (sel === ".sa-home-regatta-title") return { textContent: title };
      return null;
    },
    querySelectorAll: function (sel) {
      if (sel === "a[href]" && href) return [{ getAttribute: function () { return href; } }];
      return [];
    },
  };
}

var today = "2026-11-18";
var tsc = dates.pickEvent(events, fakeCard("TSC Cape Classic"), today);
assert(tsc && tsc.start_date === "2026-11-28" && tsc.end_date === "2026-11-29", "tsc future dates");

var dassen = dates.pickEvent(
  events,
  fakeCard("Dassen Island Race", "/regatta/2026-11-28-sssa-dassen-island-race"),
  today
);
assert(dassen && dassen.start_date === "2026-11-28" && dassen.end_date === "2026-11-28", "dassen by slug");

var ussa = dates.pickEvent(events, fakeCard("2026 USSA Sailing Championships"), today);
assert(ussa && ussa.start_date === "2026-12-09" && ussa.end_date === "2026-12-15", "ussa");

var youth = dates.pickEvent(events, fakeCard("2026 SA Sailing Youth National Championship"), today);
assert(youth && youth.start_date === "2026-12-16" && youth.end_date === "2026-12-21", "youth");

var fs = require("fs");
var hubPath = "/tmp/cardcheck/events-hub.json";
if (fs.existsSync(hubPath)) {
  var hub = JSON.parse(fs.readFileSync(hubPath, "utf8"));
  var liveEvents = Array.isArray(hub) ? hub : hub.events || [];
  var liveTsc = dates.pickEvent(liveEvents, fakeCard("TSC Cape Classic"), today);
  assert(liveTsc && liveTsc.start_date === "2026-11-28" && liveTsc.end_date === "2026-11-29", "live hub tsc");
  var liveUssa = dates.pickEvent(liveEvents, fakeCard("2026 USSA Sailing Championships"), today);
  assert(liveUssa && liveUssa.start_date === "2026-12-09", "live hub ussa");
}

console.log("upcoming-event-dates tests passed");
