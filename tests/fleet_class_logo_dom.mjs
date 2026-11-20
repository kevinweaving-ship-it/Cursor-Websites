import fs from "node:fs";
import assert from "node:assert/strict";

const src = fs.readFileSync(
  new URL("../sailingsa/frontend/js/parent-event-logo-truth.js", import.meta.url),
  "utf8"
);
const eventSrc = "/artwork/Event%20Logo/Sonnet-Nationals-2025.jpg";
const classSrc = "/artwork/Class%20Logo/Sonnet-Class-Logo.png?v=20261019";
const openSrc = "/artwork/Class%20Logo/Open-Class-Logo.png";

function img(start) {
  return {
    src: start,
    alt: "Fleet",
    style: {},
    getAttribute(name) {
      return name === "src" ? this.src : null;
    },
    setAttribute() {},
    removeAttribute() {},
    closest() {
      return null;
    },
  };
}

function boot(fleetSrcs) {
  const left = img(eventSrc);
  const nodes = fleetSrcs.map(img);
  const styleEl = { id: "", textContent: "" };
  globalThis.document = {
    readyState: "complete",
    getElementById() {
      return null;
    },
    createElement() {
      return styleEl;
    },
    querySelector(sel) {
      return String(sel).includes("regatta-header") ? left : null;
    },
    querySelectorAll() {
      return nodes;
    },
    addEventListener() {},
    head: { appendChild() {} },
    documentElement: { setAttribute() {}, appendChild() {} },
  };
  globalThis.MutationObserver = class {
    observe() {}
    disconnect() {}
  };
  eval(src);
  return { left, nodes, styleEl };
}

const sonnet = boot([classSrc]);
assert.equal(sonnet.nodes[0].src, classSrc);
assert.equal(sonnet.left.src, eventSrc);
assert.equal(sonnet.styleEl.textContent.includes("Class Logo"), false);

const openFleet = boot([openSrc]);
assert.equal(openFleet.nodes[0].src, eventSrc);

const multi = boot([classSrc, openSrc]);
assert.equal(multi.nodes[0].src, classSrc);
assert.equal(multi.nodes[1].src, openSrc);

console.log("fleet class logo kept");
