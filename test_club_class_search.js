#!/usr/bin/env node
/**
 * Manual test for Club/Class search logic (normalize + filter).
 * Run: node test_club_class_search.js
 * No server needed; validates the logic used in index.html.
 */
'use strict';

// Simulate: API returns string array (live server)
const stringArrayResponse = ['HYC', 'ZVYC', 'TSC', 'Hermanus Yacht Club'];
// Normalize like index.html
const raw = stringArrayResponse;
const clubListCache = raw.map(function(code) {
  const s = (code || '').toString().trim().toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '');
  return { code: code, name: code, slug: s || (code || '').toString().trim().toLowerCase() };
});

// Filter by q
const q = 'hyc';
const filtered = clubListCache.filter(function(c) {
  const code = (c.code || '').toString().toLowerCase();
  const name = (c.name || '').toString().toLowerCase();
  return code.indexOf(q) !== -1 || name.indexOf(q) !== -1;
});

const ok1 = filtered.length >= 1 && filtered[0].slug && filtered[0].code === 'HYC';
console.log('Club (string array): normalized', clubListCache.length, 'filtered', filtered.length, 'q="' + q + '"', filtered[0] ? filtered[0].code : '');
if (!ok1) {
  console.error('FAIL: Club filter expected at least HYC');
  process.exit(1);
}

// Class: names-only fallback
const classNamesResponse = { classes: ['420', 'ILCA 6', 'Optimist'] };
const names = classNamesResponse.classes;
const classListCache = names.map(function(n) { return { class_id: null, class_name: (n != null ? String(n) : '') }; });
const q2 = 'ilca';
const filtered2 = classListCache.filter(function(c) {
  const name = (c.class_name || '').toString().toLowerCase();
  return name.indexOf(q2) !== -1;
});
const ok2 = filtered2.length === 1 && filtered2[0].class_name === 'ILCA 6';
console.log('Class (names fallback): normalized', classListCache.length, 'filtered q="' + q2 + '"', filtered2.length, filtered2[0] ? filtered2[0].class_name : '');
if (!ok2) {
  console.error('FAIL: Class filter expected ILCA 6');
  process.exit(1);
}

console.log('OK: Club and Class search logic passed.');
process.exit(0);
