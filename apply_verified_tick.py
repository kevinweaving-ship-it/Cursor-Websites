#!/usr/bin/env python3
"""Apply Verified Sailor Tick (green) to /sailor/:slug profile pages.

Scope rules (PERMANENT — do not violate):
  - ONLY edit code inside the labelled AVATAR BLOCKS below.
  - NEVER edit Name rendering (sailor-name / sa-approved-sailor-name),
    NEVER edit Club / Province rendering (sailor-club-flag-box / province-icon-box),
    NEVER edit anything below <section class="sailor-profile-header"> or </div> after
    sa-approved-sailor-header.

Procedure:
  1. Save verified-tick SVG to /var/www/sailorset/icons/verified-sailor-v1.svg.
  2. Add @app.get("/api/sailor/has-valid-login") endpoint — checks if sas_id exists
     in user_accounts (any row = valid signed-up login).
  3. In index.sailorset.html:
       (A) CSS: inject SAILOR PROFILE AVATAR VERIFIED TICK CSS labelled block.
       (B) Profile header: wrap <div class="sailor-avatar"> with
           <div class="sailor-avatar-wrap"> (labelled AVATAR HTML BLOCK).
           Inside AVATAR block: async fetch /api/sailor/has-valid-login → if true,
           append verified tick <span class="sailor-verified-tick"> as
           position:absolute bottom-left child of .sailor-avatar-wrap.
       (C) SA-approved card: same wrap + tick logic inside AVATAR HTML BLOCK ONLY.
       (D) AVATAR CODE LABELLED COMMENTS around every line we added.
"""

import sys
import os
import subprocess
import shutil
import pathlib

SSH_KEY = "/Users/kevinweaving/.ssh/sailingsa_live_key"
SSH_OPTS = "-o IdentitiesOnly=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR"
SSH_USER_HOST = "root@102.218.215.253"
SCP = f"scp -i {SSH_KEY} {SSH_OPTS}"
SSH = f"ssh -i {SSH_KEY} {SSH_OPTS}"
LIVE_BASE = "/var/www/sailingsa"


def sh(cmd: str, check: bool = True) -> str:
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and r.returncode != 0:
        print(f"[SH FAIL] {cmd}")
        print(r.stdout)
        print(r.stderr, file=sys.stderr)
        raise SystemExit(r.returncode)
    return r.stdout


def main():
    # Step 0: Build verified-tick SVG locally based on user attached green
    # sail+checkmark circle art (simplified pure version: green circle +
    # white SailingSA sail glyph + small bottom-right checkmark).
    svg_local = "/tmp/verified-sailor-v1.svg"
    svg_content = r'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" width="128" height="128">
  <defs>
    <clipPath id="sailClip">
      <rect x="18" y="18" width="92" height="92" rx="46"/>
    </clipPath>
  </defs>
  <!-- Outer green ring + background -->
  <circle cx="64" cy="64" r="56" fill="#ffffff"/>
  <circle cx="64" cy="64" r="56" fill="none" stroke="#22c55e" stroke-width="6"/>
  <circle cx="64" cy="64" r="48" fill="#22c55e"/>
  <!-- Sail boat / logo simplified: 2 sails white + hull -->
  <g clip-path="url(#sailClip)" fill="#ffffff">
    <polygon points="50,28 50,82 38,82 64,36"/>
    <polygon points="66,22 66,82 92,82 68,44"/>
    <rect x="34" y="82" width="60" height="6" rx="3"/>
    <path d="M34 92 Q64 100 94 92 L90 88 L64 94 L38 88 Z" fill="#16a34a"/>
  </g>
  <!-- Small check badge circle bottom-right (overlapping) -->
  <circle cx="94" cy="94" r="22" fill="#ffffff" stroke="#22c55e" stroke-width="4"/>
  <circle cx="94" cy="94" r="17" fill="#22c55e"/>
  <polyline points="83,94 91,102 105,86" fill="none" stroke="#ffffff" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
'''
    with open(svg_local, "w") as f:
        f.write(svg_content)

    # Step 1: SCP SVG to icons dir on live
    sh(f"{SCP} {svg_local} {SSH_USER_HOST}:{LIVE_BASE}/icons/verified-sailor-v1.svg")
    sh(f"{SSH} {SSH_USER_HOST} 'chown www-data:www-data {LIVE_BASE}/icons/verified-sailor-v1.svg && chmod 0644 {LIVE_BASE}/icons/verified-sailor-v1.svg && ls -la {LIVE_BASE}/icons/verified-sailor-v1.svg'")

    # Step 2: Create Python patcher script and SCP / run remotely
    patch_remote = "/tmp/apply_verified_tick_remote.py"
    patch_local = "/tmp/apply_verified_tick_remote.py"

    patcher = r'''#!/usr/bin/env python3
"""Remote patcher — run on LIVE server. Atomic writes + verify."""
import os
import sys
import re
import shutil
import hashlib

BASE = "/var/www/sailingsa"
SAILOR_HTML = f"{BASE}/index.sailorset.html"
API_PY = f"{BASE}/api.py"
SVG = f"{BASE}/icons/verified-sailor-v1.svg"
STAMP = os.popen("date +%Y%m%d_%H%M%S").read().strip()

def bail(msg, code=1):
    print(f"[BAIL] {msg}", file=sys.stderr)
    sys.exit(code)

if not os.path.isfile(SAILOR_HTML): bail(f"missing {SAILOR_HTML}")
if not os.path.isfile(API_PY): bail(f"missing {API_PY}")
if not os.path.isfile(SVG): bail(f"missing {SVG}")

# ---------- BACKUPS ----------
shutil.copy2(SAILOR_HTML, f"{SAILOR_HTML}.BAK_VERIFIED_TICK_{STAMP}.bak")
shutil.copy2(API_PY, f"{API_PY}.BAK_VERIFIED_TICK_{STAMP}.bak")
print(f"[OK] backups written: .BAK_VERIFIED_TICK_{STAMP}.bak")

# ---------- (A) CSS injection into SAILOR_HTML ----------
# Find line: /* Club logo: height matches WC badge; width auto for wide logos */
# INSERT the avatar verified tick CSS block RIGHT BEFORE that comment.
with open(SAILOR_HTML, "r", encoding="utf-8", errors="replace") as f:
    html = f.read()

AVATAR_CSS_INJECT = """
        /* ================================================================
           SAILOR PROFILE AVATAR VERIFIED TICK CSS BLOCK START
           Scope: .sailor-avatar-wrap, .sailor-verified-tick, + sa-approved variant
           Isolated: NO selector overlap with Name / Club / Province code.
           ================================================================ */
        .sailor-avatar-wrap {
            position: relative;
            flex: 0 0 auto;
            width: auto;
            height: auto;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: 0;
            margin: 0;
        }
        .sailor-verified-tick {
            position: absolute;
            left: -4px;
            bottom: -2px;
            width: 24px;
            height: 24px;
            min-width: 24px;
            min-height: 24px;
            max-width: 24px;
            max-height: 24px;
            z-index: 5;
            padding: 0;
            margin: 0;
            line-height: 0;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            box-sizing: border-box;
            border: none;
            background: transparent;
        }
        .sailor-verified-tick img {
            width: 100% !important;
            height: 100% !important;
            min-width: 100% !important;
            min-height: 100% !important;
            max-width: 100% !important;
            max-height: 100% !important;
            object-fit: contain !important;
            display: block !important;
            border-radius: 0 !important;
            padding: 0 !important;
            margin: 0 !important;
            border: none !important;
            background: transparent !important;
        }
        /* SA-approved card: verified tick slightly larger, positioned bottom-left */
        .sa-approved-sailor-header .sailor-avatar-wrap .sailor-verified-tick {
            width: 30px;
            height: 30px;
            min-width: 30px;
            min-height: 30px;
            max-width: 30px;
            max-height: 30px;
            left: -4px;
            bottom: 2px;
        }
        @media (max-width: 480px) {
            .sailor-verified-tick {
                width: 20px;
                height: 20px;
                min-width: 20px;
                min-height: 20px;
                max-width: 20px;
                max-height: 20px;
                left: -2px;
                bottom: -2px;
            }
        }
        /* ================================================================
           SAILOR PROFILE AVATAR VERIFIED TICK CSS BLOCK END
           ================================================================ */
"""

# Find anchor comment for CSS insertion
CSS_ANCHOR = "/* Club logo: height matches WC badge; width auto for wide logos */"
if CSS_ANCHOR not in html:
    bail("CSS_ANCHOR 'Club logo: height matches WC badge...' not found in sailorset HTML")

html2 = html.replace(CSS_ANCHOR, AVATAR_CSS_INJECT + "\n        " + CSS_ANCHOR, 1)
if html2 == html: bail("CSS inject failed (no change)")

# ---------- (B) Profile header avatar builder ----------
# Original avatar build (single line quoted literal inside showSailorProfileFromResult):
# '<div class="sailor-avatar">' + ... + '</div>'  (profile header section)
# Rule: ONLY wrap in <div class="sailor-avatar-wrap">...</div>, AND
# right after closing </div> (sailor-avatar closing), APPEND placeholder
# <span class="sailor-verified-tick" data-sas-id="SID" style="display:none;"></span>
# then add a single inline script (STRICTLY INSIDE AVATAR LABELLED BLOCK)
# that fetches /api/sailor/has-valid-login and flips display when true.

OLD_PROFILE_AVATAR_START = "'<div class=\"sailor-avatar\">' +"
NEW_PROFILE_AVATAR_START = (
    "/* SAILOR PROFILE AVATAR HTML BLOCK START — avatar container wrap for verified tick */\n"
    "                                    '<div class=\"sailor-avatar-wrap\" data-sas-id=\"' + escapeHtml(String(sid || '')) + '\">' +\n"
    "                                    '<div class=\"sailor-avatar\">' +"
)
if OLD_PROFILE_AVATAR_START not in html2:
    bail(f"OLD_PROFILE_AVATAR_START anchor not found")
html3 = html2.replace(OLD_PROFILE_AVATAR_START, NEW_PROFILE_AVATAR_START, 1)
if html3 == html2: bail("Profile avatar START wrap inject failed")

# Now find the closing </div> of sailor-avatar inside profile header builder.
# Original pattern (profile header):
#   '<span class="avatar-fallback" style="display:none;">' + escapeHtml(initials) + '</span>' +
#   '</div>' +
#   '<div class="sailor-identity-text">' +
PROFILE_AVATAR_END_ANCHOR = (
    "'<span class=\"avatar-fallback\" style=\"display:none;\">' + escapeHtml(initials) + '</span>' +\n"
    "                                    '</div>' +\n"
    "                                    '<div class=\"sailor-identity-text\">' +"
)
PROFILE_AVATAR_END_NEW = (
    "'<span class=\"avatar-fallback\" style=\"display:none;\">' + escapeHtml(initials) + '</span>' +\n"
    "                                    '</div>' +\n"
    "                                    '<span class=\"sailor-verified-tick\" style=\"display:none;\" aria-label=\"Verified SailingSA login\"><img src=\"/icons/verified-sailor-v1.svg\" alt=\"Verified\" onerror=\"this.style.display=\\'none\\';\"></span>' +\n"
    "                                    '</div>' + /* close sailor-avatar-wrap */\n"
    "                                    /* SAILOR PROFILE AVATAR HTML BLOCK END */\n"
    "                                    '<div class=\"sailor-identity-text\">' +"
)
if PROFILE_AVATAR_END_ANCHOR not in html3:
    bail("PROFILE_AVATAR_END_ANCHOR not found — are line breaks different?")
html4 = html3.replace(PROFILE_AVATAR_END_ANCHOR, PROFILE_AVATAR_END_NEW, 1)
if html4 == html3: bail("Profile avatar END + tick span inject failed")

# ---------- (C) SA-approved card avatar builder ----------
# Original in sa-approved block (two lines):
# '<div class="sa-approved-sailor-avatar">' +
#   '<img src="..." onerror="...">' + '<span class="avatar-fallback">..</span>' +
# '</div>' +
# '<div class="sa-approved-sailor-main">' +
APPROVED_AVATAR_START_OLD = "'<div class=\"sa-approved-sailor-avatar\">' +"
APPROVED_AVATAR_START_NEW = (
    "/* SAILOR PROFILE AVATAR HTML BLOCK START — sa-approved card wrap for verified tick */\n"
    "                                                '<div class=\"sailor-avatar-wrap\" data-sas-id=\"' + escapeHtml(String(sid || '')) + '\">' +\n"
    "                                                '<div class=\"sa-approved-sailor-avatar\">' +"
)
if APPROVED_AVATAR_START_OLD not in html4:
    bail("APPROVED_AVATAR_START_OLD not found")
html5 = html4.replace(APPROVED_AVATAR_START_OLD, APPROVED_AVATAR_START_NEW, 1)
if html5 == html4: bail("Approved avatar START wrap inject failed")

APPROVED_AVATAR_END_OLD = (
    "'<span class=\"avatar-fallback\" style=\"display:none;\">' + escapeHtml(initials) + '</span>' +\n"
    "                                                '</div>' +\n"
    "                                                '<div class=\"sa-approved-sailor-main\">' +"
)
APPROVED_AVATAR_END_NEW = (
    "'<span class=\"avatar-fallback\" style=\"display:none;\">' + escapeHtml(initials) + '</span>' +\n"
    "                                                '</div>' +\n"
    "                                                '<span class=\"sailor-verified-tick\" style=\"display:none;\" aria-label=\"Verified SailingSA login\"><img src=\"/icons/verified-sailor-v1.svg\" alt=\"Verified\" onerror=\"this.style.display=\\'none\\';\"></span>' +\n"
    "                                                '</div>' + /* close sailor-avatar-wrap */\n"
    "                                                /* SAILOR PROFILE AVATAR HTML BLOCK END */\n"
    "                                                '<div class=\"sa-approved-sailor-main\">' +"
)
if APPROVED_AVATAR_END_OLD not in html5:
    bail("APPROVED_AVATAR_END_OLD anchor not found")
html6 = html5.replace(APPROVED_AVATAR_END_OLD, APPROVED_AVATAR_END_NEW, 1)
if html6 == html5: bail("Approved avatar END + tick span inject failed")

# ---------- (D) Single shared tick-painter IIFE — inject once at END of <script>
# that contains showSailorProfileFromResult. Find function showSailorProfileFromResult
# or nearby closing, then append. We append as LAST child of <body> (before </body>):
# a tiny script tag that exports __paintVerifiedTick(wrapEl). Paint logic is:
#  1. Read wrapEl.dataset.sasId → sid
#  2. If no sid: return
#  3. Fetch /api/sailor/has-valid-login?sas_id=sid (cache 1h)
#  4. If ok.valid === true → find first .sailor-verified-tick in wrapEl, set display:flex
# We call __paintVerifiedTick() AUTOMATICALLY on any .sailor-avatar-wrap node:
#   - MutationObserver watches body for added nodes (profile header builder,
#     sa-approved builder, search results rows, etc.)
PAINTER_SCRIPT = r"""
<script>
/* ================================================================
   SAILOR PROFILE AVATAR VERIFIED TICK PAINTER BLOCK START
   Strictly limited scope: ONLY touches .sailor-avatar-wrap → .sailor-verified-tick
   Never reads / edits Name, Club, Province, Sailing For, or any sibling elements.
   ================================================================ */
(function() {
  'use strict';
  var CACHE_KEY = '__sa_verified_sailors_cache_v1';
  var CACHE_TTL_MS = 3600 * 1000; // 1 hour cache per sas_id

  function _cache() {
    try {
      var raw = window.sessionStorage ? sessionStorage.getItem(CACHE_KEY) : null;
      if (raw) return JSON.parse(raw);
    } catch (e) {}
    return {};
  }
  function _cacheSave(c) {
    try {
      if (window.sessionStorage) sessionStorage.setItem(CACHE_KEY, JSON.stringify(c));
    } catch (e) {}
  }
  function _hasCachedValid(sid) {
    if (!sid) return null;
    var c = _cache();
    var entry = c[String(sid)];
    if (!entry) return null;
    if (Date.now() - (entry.ts || 0) > CACHE_TTL_MS) return null;
    return !!entry.valid;
  }
  function _cacheSet(sid, valid) {
    if (!sid) return;
    var c = _cache();
    c[String(sid)] = { valid: !!valid, ts: Date.now() };
    _cacheSave(c);
  }
  function _apiBase() {
    if (typeof window.API === 'string' && window.API.trim()) return window.API.trim();
    return '';
  }
  function _paintTickNode(wrapEl) {
    try {
      if (!wrapEl || wrapEl.__saTickCheckDone === true) return;
      var sid = String((wrapEl.dataset && (wrapEl.dataset.sasId || wrapEl.dataset.sas_id)) || '').trim();
      if (!sid) { wrapEl.__saTickCheckDone = true; return; }
      var tickEl = wrapEl.querySelector ? wrapEl.querySelector('.sailor-verified-tick') : null;
      if (!tickEl) { wrapEl.__saTickCheckDone = true; return; }
      var cached = _hasCachedValid(sid);
      if (cached === true) {
        tickEl.style.setProperty('display', 'inline-flex', 'important');
        wrapEl.__saTickCheckDone = true;
        return;
      }
      if (cached === false) {
        wrapEl.__saTickCheckDone = true;
        return;
      }
      var url = _apiBase() + '/api/sailor/has-valid-login?sas_id=' + encodeURIComponent(sid);
      fetch(url, { credentials: 'same-origin', cache: 'force-cache' })
        .then(function(r) { return (r && r.ok) ? r.json() : null; })
        .then(function(data) {
          var valid = !!(data && (data.valid === true || data.has_valid_login === true));
          _cacheSet(sid, valid);
          if (valid) tickEl.style.setProperty('display', 'inline-flex', 'important');
          wrapEl.__saTickCheckDone = true;
        })
        .catch(function() {
          wrapEl.__saTickCheckDone = true;
        });
    } catch (e) {
      try { wrapEl.__saTickCheckDone = true; } catch (_) {}
    }
  }
  function _scanAll() {
    try {
      var list = document.querySelectorAll('.sailor-avatar-wrap');
      for (var i = 0; i < list.length; i++) _paintTickNode(list[i]);
    } catch (e) {}
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', _scanAll, { once: true });
  } else {
    _scanAll();
  }
  // Future dynamic nodes (profile rebuilds, approved-card rebuilds, search results)
  try {
    if (typeof MutationObserver === 'function') {
      var mo = new MutationObserver(function(mutations) {
        var scannedAny = false;
        for (var m = 0; m < mutations.length; m++) {
          var added = mutations[m].addedNodes;
          if (!added || !added.length) continue;
          for (var n = 0; n < added.length; n++) {
            var node = added[n];
            if (!node) continue;
            if (node.nodeType === 1) {
              if (node.classList && node.classList.contains('sailor-avatar-wrap')) _paintTickNode(node);
              if (node.querySelectorAll) {
                var childWraps = node.querySelectorAll('.sailor-avatar-wrap');
                for (var c = 0; c < childWraps.length; c++) _paintTickNode(childWraps[c]);
              }
              scannedAny = true;
            }
          }
        }
        if (scannedAny === false) _scanAll();
      });
      mo.observe(document.documentElement, { childList: true, subtree: true });
    } else {
      setInterval(_scanAll, 800);
    }
  } catch (e) {}
  // Expose for manual use if needed
  window.__saPaintVerifiedTick = _paintTickNode;
  window.__saPaintVerifiedTickScanAll = _scanAll;
})();
/* ================================================================
   SAILOR PROFILE AVATAR VERIFIED TICK PAINTER BLOCK END
   ================================================================ */
</script>
"""

if "</body>" in html6:
    html7 = html6.replace("</body>", PAINTER_SCRIPT + "\n</body>", 1)
else:
    html7 = html6 + PAINTER_SCRIPT

# ---------- Write SAILOR_HTML atomically ----------
new_html = SAILOR_HTML + ".new"
with open(new_html, "w", encoding="utf-8") as f:
    f.write(html7)
expected_sha = hashlib.sha256(html7.encode("utf-8")).hexdigest()
with open(new_html, "rb") as f:
    actual_sha = hashlib.sha256(f.read()).hexdigest()
if actual_sha != expected_sha: bail(f"new html sha mismatch build:{expected_sha} file:{actual_sha}")
os.chmod(new_html, 0o644)
shutil.chown(new_html, "www-data", "www-data")
shutil.move(new_html, SAILOR_HTML)
post_sha = hashlib.sha256(open(SAILOR_HTML, "rb").read()).hexdigest()
if post_sha != expected_sha: bail(f"post-move sha mismatch build:{expected_sha} live:{post_sha}")
print(f"[OK] {SAILOR_HTML} updated. SHA256={post_sha[:16]}… size={os.path.getsize(SAILOR_HTML)} bytes")

# ---------- (E) Inject endpoint /api/sailor/has-valid-login into api.py ----------
with open(API_PY, "r", encoding="utf-8", errors="replace") as f:
    api_txt = f.read()

ENDPOINT_CODE = r"""
# ====================================================================
# SAILOR PROFILE AVATAR VERIFIED TICK: /api/sailor/has-valid-login
# Scope: single endpoint. Only reads user_accounts table.
# Does not touch any other route. No shared state mutations.
# ====================================================================
@app.get("/api/sailor/has-valid-login")
def api_sailor_has_valid_login(sas_id: Optional[str] = Query(None, alias="sas_id")):
    sid = str(sas_id or "").strip()
    out = {"valid": False, "sas_id": sid}
    if not sid or not sid.isdigit():
        return out
    if not table_exists("user_accounts"):
        return out
    try:
        conn = get_db_connection("has_valid_login")
        cur = conn.cursor()
        try:
            cur.execute("SELECT 1 FROM public.user_accounts WHERE sas_id::text = %s LIMIT 1", (sid,))
            row = cur.fetchone()
            out["valid"] = bool(row)
            return out
        finally:
            cur.close()
            return_db_connection(conn)
    except Exception as e:
        print(f"[has-valid-login] {sid}: {e}", flush=True)
        return out
# ====================================================================
# SAILOR PROFILE AVATAR VERIFIED TICK ENDPOINT END
# ====================================================================
"""

# Insert endpoint RIGHT BEFORE line: @app.get("/api/sailor/resolve")
RESOLVE_ANCHOR = '@app.get("/api/sailor/resolve")'
if RESOLVE_ANCHOR not in api_txt:
    bail(f"RESOLVE_ANCHOR not found in {API_PY}")
if ENDPOINT_CODE.strip() in api_txt:
    print("[WARN] endpoint already present — skipping api.py inject")
    api2 = api_txt
else:
    api2 = api_txt.replace(RESOLVE_ANCHOR, ENDPOINT_CODE + "\n\n" + RESOLVE_ANCHOR, 1)
    if api2 == api_txt: bail("endpoint inject failed")

new_api = API_PY + ".new"
with open(new_api, "w", encoding="utf-8") as f:
    f.write(api2)
exp_api_sha = hashlib.sha256(api2.encode("utf-8")).hexdigest()
with open(new_api, "rb") as f:
    got_api_sha = hashlib.sha256(f.read()).hexdigest()
if got_api_sha != exp_api_sha: bail(f"new api.py sha mismatch")
os.chmod(new_api, 0o644)
shutil.chown(new_api, "www-data", "www-data")
shutil.move(new_api, API_PY)
post_api_sha = hashlib.sha256(open(API_PY, "rb").read()).hexdigest()
if post_api_sha != exp_api_sha: bail(f"post-move api sha mismatch")
print(f"[OK] {API_PY} updated. SHA256={post_api_sha[:16]}… size={os.path.getsize(API_PY)} bytes")

# ---------- SANITY CHECKS on SAILOR_HTML ----------
with open(SAILOR_HTML, "r", encoding="utf-8", errors="replace") as f:
    liveh = f.read()

checks = [
    ("AVATAR_CSS_BLOCK_PRESENT", "SAILOR PROFILE AVATAR VERIFIED TICK CSS BLOCK START" in liveh),
    ("TICK_SPAN_IN_PROFILE_HEADER", 'class="sailor-verified-tick" style="display:none;" aria-label="Verified SailingSA login"' in liveh),
    ("WRAP_IN_PROFILE_HEADER", 'sailor-avatar-wrap" data-sas-id=' in liveh),
    ("WRAP_IN_SA_APPROVED", "sailor-avatar-wrap" in liveh and "sa-approved-sailor-main" in liveh),
    ("PAINTER_IIFE_PRESENT", "__saPaintVerifiedTick = _paintTickNode" in liveh),
    ("SVG_URL_REF_PRESENT", "/icons/verified-sailor-v1.svg" in liveh),
    ("NAME_CODE_UNTOUCHED", "<h1 class=\"sailor-name\">" in liveh and "<h2 class=\"sa-approved-sailor-name\">" in liveh),
    ("CLUB_CODE_UNTOUCHED", "sailor-club-flag-box" in liveh and "sa-approved-sailor-club-code" in liveh),
]
all_ok = True
for name, ok in checks:
    print(f"[CHECK] {name}: {'PASS' if ok else 'FAIL'}")
    if not ok: all_ok = False

# Sanity on API: endpoint exists + table_exists / get_db_connection imports ok
with open(API_PY, "r", encoding="utf-8", errors="replace") as f:
    livea = f.read()
api_checks = [
    ("ENDPOINT_DECORATOR", '@app.get("/api/sailor/has-valid-login")' in livea),
    ("ENDPOINT_USER_ACCOUNTS_QUERY", "FROM public.user_accounts WHERE sas_id::text = %s" in livea),
    ("ENDPOINT_RETURNS_VALID", '"valid": False' in livea and "out[\"valid\"] = bool(row)" in livea),
    ("NO_BANNED_STRINGS_ADDED", "padding-top: 80px" not in livea and "logout-pill-auto-login-popup-v1" not in livea and "renderLoggedIn" not in livea),
]
for name, ok in api_checks:
    print(f"[API CHECK] {name}: {'PASS' if ok else 'FAIL'}")
    if not ok: all_ok = False

if not all_ok:
    bail("sanity check list contains FAIL — inspect above. Live was replaced but API reload NOT triggered.")

# ---------- Soft-reload API (if systemd service exists) ----------
import subprocess as _sp
svc_check = _sp.run("command -v systemctl >/dev/null 2>&1 && systemctl list-units --type=service --full | grep -E 'sailingsa|api|uvicorn|gunicorn|fastapi' | head -5",
                    shell=True, capture_output=True, text=True)
print(f"[INFO] detected services: {(svc_check.stdout or '').strip() or '(none found)'}")
# Try common service names
for svc in ["sailingsa-api", "sailingsa", "sailingsa_app", "uvicorn-sailingsa", "gunicorn-sailingsa", "api-sailingsa"]:
    _ = _sp.run(f"systemctl is-active {svc} >/dev/null 2>&1", shell=True)
    if _.returncode == 0:
        r = _sp.run(f"systemctl reload-or-restart {svc} 2>&1", shell=True, capture_output=True, text=True)
        print(f"[INFO] reload/restart {svc}: exit={r.returncode} out={(r.stdout+r.stderr).strip()[:300]}")
        break

print("[DONE] All injections complete.")
print(f"[HINT] Verify endpoint: curl -s 'https://sailingsa.co.za/api/sailor/has-valid-login?sas_id=21172'")
print(f"[HINT] Timothy profile: https://sailingsa.co.za/sailor/timothy-weaving?v=TICK{STAMP}")

if not all_ok: sys.exit(2)
sys.exit(0)
'''

    with open(patch_local, "w") as f:
        # Sanitize: no Unicode em-dashes / smart quotes / arrows in code
        import re as _re
        patcher = (patcher
            .replace("\u2014", "--")
            .replace("\u2013", "-")
            .replace("\u2019", "'")
            .replace("\u2018", "'")
            .replace("\u201c", '"')
            .replace("\u201d", '"')
            .replace("\u2192", "->"))
        f.write(patcher)

    sh(f"chmod +x {patch_local}")
    sh(f"{SCP} {patch_local} {SSH_USER_HOST}:{patch_remote}")
    out = sh(f"{SSH} {SSH_USER_HOST} 'chmod +x {patch_remote} && python3 {patch_remote} 2>&1'")
    print(out)


if __name__ == "__main__":
    main()
