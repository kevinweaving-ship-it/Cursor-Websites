/**
 * SailingSA SPA results engine — globals only (no IIFE / no module scope).
 * Inline HTML must use window.resolveResultsEngine() — never bare engine globals.
 */

window.resultsEngine = window.resultsEngine || {};
window.seriesResults = window.seriesResults || {};

Object.assign(window.seriesResults, {
  version: 1,
  name: 'seriesResults',
});

Object.assign(window.resultsEngine, {
  version: 1,
  name: 'sailingsa-results-engine',
});

/** engine.seriesResults() returns the series results data object */
window.resultsEngine.seriesResults = function () {
  return window.seriesResults;
};

if (typeof window.resultsEngine.render !== 'function') {
  window.resultsEngine.render = function () {
    console.warn('resultsEngine.render: no-op (wire implementation in results engine)');
  };
}

if (typeof window.showError !== 'function') {
  window.showError = function (message) {
    var m = message != null ? String(message) : 'Error';
    console.error(m);
    try {
      alert(m);
    } catch (e) {}
  };
}

/**
 * Resolve results engine: same window first, then parent frame (iframe).
 * @returns {object|null}
 */
window.resolveResultsEngine = function () {
  try {
    if (window.resultsEngine && window.resultsEngine.version !== undefined) {
      return window.resultsEngine;
    }
  } catch (e) {}
  try {
    if (window.parent && window.parent !== window) {
      var p = window.parent;
      if (p.resultsEngine && p.resultsEngine.version !== undefined) {
        return p.resultsEngine;
      }
    }
  } catch (e) {
    /* cross-origin parent */
  }
  return null;
};

/**
 * @returns {boolean} false if engine missing
 */
window.assertResultsEngineOrAbort = function () {
  const engine = typeof window.resolveResultsEngine === 'function' ? window.resolveResultsEngine() : null;
  if (!engine) {
    console.error('Results engine missing');
    if (typeof window.showError === 'function') {
      window.showError('Results engine not loaded');
    }
    return false;
  }
  return true;
};
