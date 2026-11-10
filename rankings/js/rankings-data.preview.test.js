#!/usr/bin/env node
'use strict';

var assert = require('assert');
var fs = require('fs');
var path = require('path');
var vm = require('vm');

var SOURCE = fs.readFileSync(path.join(__dirname, 'rankings-data.js'), 'utf8');
var passed = 0;
var failed = 0;

function pass(name) {
  passed += 1;
  console.log('PASS', name);
}

function fail(name, err) {
  failed += 1;
  console.error('FAIL', name);
  console.error(err && err.stack ? err.stack : err);
}

function syncTest(name, fn) {
  try {
    fn();
    pass(name);
  } catch (err) {
    fail(name, err);
  }
}

function asyncTest(name, fn) {
  return Promise.resolve()
    .then(fn)
    .then(function () { pass(name); })
    .catch(function (err) { fail(name, err); });
}

function makeContext(overrides) {
  var location = { search: '', pathname: '/rankings/', hash: '' };
  var fetchCalls = [];
  var ctx = {
    console: console,
    Date: Date,
    URLSearchParams: URLSearchParams,
    Array: Array,
    Object: Object,
    String: String,
    Number: Number,
    Promise: Promise,
    Error: Error,
    location: location,
    history: {
      replaceState: function (_state, _title, url) {
        var qs = String(url || '').split('?')[1] || '';
        location.search = qs ? '?' + qs.split('#')[0] : '';
      },
      pushState: function (_state, _title, url) {
        var qs = String(url || '').split('?')[1] || '';
        location.search = qs ? '?' + qs.split('#')[0] : '';
      }
    },
    fetch: function (url, opts) {
      fetchCalls.push({ url: url, opts: opts });
      return Promise.reject(new Error('fetch not stubbed: ' + url));
    },
    document: {
      getElementById: function () { return null; },
      querySelector: function () { return null; }
    },
    RankingsConfig: {
      USE_MOCK_DATA: false,
      PUBLISHED_DATA_URL: '/rankings/data/published.json'
    },
    RankingsUrlState: null,
    RankingsData: null,
    __fetchCalls: fetchCalls
  };
  if (overrides) Object.assign(ctx, overrides);
  vm.createContext(ctx);
  vm.runInContext(SOURCE, ctx);
  return ctx;
}

function validPreviewPayload() {
  return {
    auditVersion: 'ssa-v2-shadow-2026-08-19',
    formulaVersion: 'ssl-parity-v2',
    isPublished: false,
    sailors: [{ rank: 1, name: 'Preview Sailor', slug: 'preview-sailor', points: 100 }]
  };
}

function validLivePayload() {
  return {
    auditVersion: '2026-07-27-011',
    formulaVersion: 'ssl-parity-v1-shadow',
    isPublished: true,
    sailors: [{ rank: 1, name: 'Live Sailor', slug: 'live-sailor', points: 200 }]
  };
}

syncTest('wantSsaV2Preview matches preview=ssa-v2 only', function () {
  var ctx = makeContext();
  ctx.location.search = '?preview=ssa-v2';
  assert.strictEqual(ctx.RankingsData.wantSsaV2Preview(), true);
  ctx.location.search = '?preview=other';
  assert.strictEqual(ctx.RankingsData.wantSsaV2Preview(), false);
  ctx.location.search = '';
  assert.strictEqual(ctx.RankingsData.wantSsaV2Preview(), false);
});

syncTest('isValidPreviewPayload rejects missing sailors and empty auditVersion', function () {
  var ctx = makeContext();
  var valid = validPreviewPayload();
  assert.strictEqual(ctx.RankingsData.isValidPreviewPayload(valid), true);
  assert.strictEqual(ctx.RankingsData.isValidPreviewPayload({ auditVersion: 'x', sailors: [] }), false);
  assert.strictEqual(ctx.RankingsData.isValidPreviewPayload({ auditVersion: '', sailors: valid.sailors }), false);
  assert.strictEqual(ctx.RankingsData.isValidPreviewPayload(null), false);
});

syncTest('applySsaV2PreviewChrome sets banner notice and robots noindex', function () {
  var noticeEl = { textContent: 'old' };
  var bannerEl = { hidden: true, removeAttribute: function (name) { this.removed = name; } };
  var robotsEl = { content: 'index, follow', setAttribute: function (_k, v) { this.content = v; } };
  var ctx = makeContext({
    document: {
      getElementById: function (id) {
        if (id === 'rkBetaNoticeText') return noticeEl;
        if (id === 'rkBetaBanner') return bannerEl;
        return null;
      },
      querySelector: function (sel) {
        if (sel === 'meta[name="robots"]') return robotsEl;
        return null;
      }
    }
  });
  ctx.RankingsData.applySsaV2PreviewChrome();
  assert.strictEqual(noticeEl.textContent, ctx.RankingsData.SSA_V2_PREVIEW_NOTICE);
  assert.strictEqual(bannerEl.hidden, false);
  assert.strictEqual(bannerEl.removed, 'aria-hidden');
  assert.strictEqual(robotsEl.content, 'noindex, nofollow');
});

syncTest('wrapPreviewUrlState re-appends preview=ssa-v2 after writeState', function () {
  var ctx = makeContext();
  ctx.location.search = '?q=blake&sort=rank';
  ctx.RankingsUrlState = {
    writeState: function (state, replace) {
      var p = new URLSearchParams();
      if (state.q) p.set('q', state.q);
      if (state.sort) p.set('sort', state.sort);
      var qs = p.toString();
      var url = '/rankings/' + (qs ? '?' + qs : '');
      if (replace) ctx.history.replaceState(state, '', url);
      else ctx.history.pushState(state, '', url);
    }
  };
  ctx.RankingsData.wrapPreviewUrlState();
  ctx.RankingsUrlState.writeState({ q: 'blake', sort: 'points' }, true);
  assert.match(ctx.location.search, /preview=ssa-v2/);
  assert.match(ctx.location.search, /q=blake/);
  assert.match(ctx.location.search, /sort=points/);
});

Promise.all([
  asyncTest('loadSsaV2Preview uses preview URL with cache-bust and no-store', function () {
    var ctx = makeContext();
    var preview = validPreviewPayload();
    ctx.fetch = function (url, opts) {
      ctx.__fetchCalls.push({ url: url, opts: opts });
      return Promise.resolve({
        ok: true,
        json: function () { return Promise.resolve(preview); }
      });
    };
    return ctx.RankingsData.loadSsaV2Preview().then(function (bundle) {
      assert.strictEqual(ctx.__fetchCalls.length, 1);
      assert.match(ctx.__fetchCalls[0].url, /^\/rankings\/data\/published\.ssa-v2\.preview\.json\?cb=\d+$/);
      assert.strictEqual(ctx.__fetchCalls[0].opts.cache, 'no-store');
      assert.strictEqual(bundle.isSsaV2Preview, true);
      assert.strictEqual(bundle.isPublished, false);
    });
  }),

  asyncTest('load() preview valid uses preview bundle', function () {
    var ctx = makeContext();
    ctx.location.search = '?preview=ssa-v2';
    var preview = validPreviewPayload();
    ctx.fetch = function (url) {
      if (String(url).indexOf('published.ssa-v2.preview.json') !== -1) {
        return Promise.resolve({ ok: true, json: function () { return Promise.resolve(preview); } });
      }
      if (String(url).indexOf('audit-popup-capability') !== -1) {
        return Promise.resolve({ ok: false });
      }
      throw new Error('unexpected fetch ' + url);
    };
    return ctx.RankingsData.load().then(function (bundle) {
      assert.strictEqual(bundle.isSsaV2Preview, true);
      assert.strictEqual(bundle.sailors[0].name, 'Preview Sailor');
    });
  }),

  asyncTest('load() preview missing falls back to live published.json', function () {
    var ctx = makeContext();
    ctx.location.search = '?preview=ssa-v2';
    var live = validLivePayload();
    ctx.fetch = function (url) {
      if (String(url).indexOf('published.ssa-v2.preview.json') !== -1) {
        return Promise.resolve({ ok: false, status: 403 });
      }
      if (String(url) === '/rankings/data/published.json') {
        return Promise.resolve({ ok: true, json: function () { return Promise.resolve(live); } });
      }
      if (String(url).indexOf('audit-popup-capability') !== -1) {
        return Promise.resolve({ ok: false });
      }
      throw new Error('unexpected fetch ' + url);
    };
    return ctx.RankingsData.load().then(function (bundle) {
      assert.strictEqual(bundle.isSsaV2Preview, undefined);
      assert.strictEqual(bundle.isPublished, true);
      assert.strictEqual(bundle.sailors[0].name, 'Live Sailor');
    });
  }),

  asyncTest('load() preview corrupt payload falls back to live published.json', function () {
    var ctx = makeContext();
    ctx.location.search = '?preview=ssa-v2';
    var live = validLivePayload();
    ctx.fetch = function (url) {
      if (String(url).indexOf('published.ssa-v2.preview.json') !== -1) {
        return Promise.resolve({
          ok: true,
          json: function () { return Promise.resolve({ auditVersion: 'bad', sailors: [] }); }
        });
      }
      if (String(url) === '/rankings/data/published.json') {
        return Promise.resolve({ ok: true, json: function () { return Promise.resolve(live); } });
      }
      if (String(url).indexOf('audit-popup-capability') !== -1) {
        return Promise.resolve({ ok: false });
      }
      throw new Error('unexpected fetch ' + url);
    };
    return ctx.RankingsData.load().then(function (bundle) {
      assert.strictEqual(bundle.isSsaV2Preview, undefined);
      assert.strictEqual(bundle.sailors[0].name, 'Live Sailor');
    });
  }),

  asyncTest('load() normal rankings unchanged without preview param', function () {
    var ctx = makeContext();
    var live = validLivePayload();
    ctx.fetch = function (url, opts) {
      ctx.__fetchCalls.push({ url: url, opts: opts });
      if (String(url) === '/rankings/data/published.json') {
        return Promise.resolve({ ok: true, json: function () { return Promise.resolve(live); } });
      }
      if (String(url).indexOf('audit-popup-capability') !== -1) {
        return Promise.resolve({ ok: false });
      }
      throw new Error('unexpected fetch ' + url);
    };
    return ctx.RankingsData.load().then(function (bundle) {
      assert.strictEqual(bundle.isSsaV2Preview, undefined);
      assert.strictEqual(bundle.isPublished, true);
      assert.strictEqual(ctx.__fetchCalls.some(function (c) {
        return String(c.url).indexOf('published.ssa-v2.preview.json') !== -1;
      }), false);
    });
  }),

  asyncTest('load() mock=1 unchanged and skips preview fetch', function () {
    var ctx = makeContext({
      RankingsMockData: {
        AUDIT_VERSION: 'mock-v1',
        sailors: [{ rank: 1, name: 'Mock Sailor', slug: 'mock', points: 1 }],
        audits: []
      }
    });
    ctx.location.search = '?preview=ssa-v2&mock=1';
    ctx.fetch = function () {
      throw new Error('fetch should not run in mock mode');
    };
    return ctx.RankingsData.load().then(function (bundle) {
      assert.strictEqual(bundle.isMock, true);
      assert.strictEqual(bundle.sailors[0].name, 'Mock Sailor');
    });
  })
]).then(function () {
  console.log('\n' + passed + ' passed, ' + failed + ' failed');
  process.exit(failed ? 1 : 0);
});
